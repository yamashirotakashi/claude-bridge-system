"""
Claude Bridge System - Desktop Connector
Claude Desktopとの連携を管理するコネクター
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta

import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from .bridge_protocol import BridgeProtocol, BridgeMessage, MessageType
from ..exceptions import BridgeException

logger = logging.getLogger(__name__)


class DesktopConnectionError(BridgeException):
    """Desktop接続エラー"""
    pass


class DesktopConnector:
    """Claude Desktop連携コネクター"""
    
    def __init__(
        self,
        websocket_url: str = "ws://localhost:8765",
        connection_timeout: int = 30,
        heartbeat_interval: int = 30,
        max_reconnect_attempts: int = 5
    ):
        """
        Desktop コネクターの初期化
        
        Args:
            websocket_url: WebSocketサーバーURL
            connection_timeout: 接続タイムアウト（秒）
            heartbeat_interval: ハートビート間隔（秒）
            max_reconnect_attempts: 最大再接続試行回数
        """
        self.websocket_url = websocket_url
        self.connection_timeout = connection_timeout
        self.heartbeat_interval = heartbeat_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # プロトコル管理
        self.protocol = BridgeProtocol("claude_bridge_connector")
        
        # 接続状態
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.is_connecting = False
        self.reconnect_attempts = 0
        self.last_ping_time = None
        self.last_pong_time = None
        
        # メッセージハンドラー
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        self.response_waiters: Dict[str, asyncio.Future] = {}
        
        # 統計情報
        self.connection_stats = {
            "total_connections": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "last_connection_time": None,
            "uptime_start": None
        }
        
        # バックグラウンドタスク
        self.background_tasks: List[asyncio.Task] = []
        
        logger.info(f"DesktopConnector initialized with URL: {websocket_url}")
    
    async def connect(self) -> bool:
        """
        Claude Desktopに接続
        
        Returns:
            接続成功可否
        """
        if self.is_connected or self.is_connecting:
            logger.warning("Already connected or connecting")
            return self.is_connected
        
        self.is_connecting = True
        self.connection_stats["total_connections"] += 1
        
        try:
            logger.info(f"Connecting to Claude Desktop at {self.websocket_url}")
            
            # WebSocket接続確立
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    ping_interval=self.heartbeat_interval,
                    ping_timeout=self.connection_timeout,
                    close_timeout=10
                ),
                timeout=self.connection_timeout
            )
            
            self.is_connected = True
            self.is_connecting = False
            self.reconnect_attempts = 0
            self.connection_stats["successful_connections"] += 1
            self.connection_stats["last_connection_time"] = datetime.now().isoformat()
            self.connection_stats["uptime_start"] = datetime.now().isoformat()
            
            # ハンドシェイク実行
            await self._perform_handshake()
            
            # バックグラウンドタスク開始
            await self._start_background_tasks()
            
            logger.info("Successfully connected to Claude Desktop")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout after {self.connection_timeout} seconds")
            self.connection_stats["failed_connections"] += 1
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to Claude Desktop: {e}")
            self.connection_stats["failed_connections"] += 1
            return False
            
        finally:
            self.is_connecting = False
    
    async def disconnect(self) -> None:
        """Claude Desktopから切断"""
        if not self.is_connected:
            logger.warning("Not connected")
            return
        
        logger.info("Disconnecting from Claude Desktop")
        
        try:
            # 切断メッセージ送信
            disconnect_msg = self.protocol.create_message(
                MessageType.DISCONNECT,
                {"reason": "client_disconnect", "timestamp": datetime.now().isoformat()}
            )
            await self._send_message(disconnect_msg)
            
            # バックグラウンドタスク停止
            await self._stop_background_tasks()
            
            # WebSocket接続クローズ
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            self.is_connected = False
            logger.info("Successfully disconnected from Claude Desktop")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self.is_connected = False
    
    async def send_message(self, message: BridgeMessage) -> Optional[BridgeMessage]:
        """
        メッセージ送信
        
        Args:
            message: 送信するメッセージ
        
        Returns:
            レスポンス（必要に応じて）
        """
        if not self.is_connected:
            raise DesktopConnectionError("Not connected to Claude Desktop")
        
        # メッセージ妥当性チェック
        if not self.protocol.validate_message(message):
            raise ValueError("Invalid message format")
        
        try:
            await self._send_message(message)
            self.connection_stats["messages_sent"] += 1
            
            # レスポンスが必要な場合は待機
            if self._needs_response(message.message_type):
                return await self._wait_for_response(message.message_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise DesktopConnectionError(f"Message send failed: {e}")
    
    async def send_project_switch(
        self,
        project_id: str,
        project_context: Dict[str, Any]
    ) -> Optional[BridgeMessage]:
        """
        プロジェクト切り替え通知
        
        Args:
            project_id: プロジェクトID
            project_context: プロジェクトコンテキスト
        
        Returns:
            レスポンス
        """
        message = self.protocol.create_project_switch(project_id, project_context)
        return await self.send_message(message)
    
    async def send_task_update(
        self,
        task_data: Dict[str, Any]
    ) -> Optional[BridgeMessage]:
        """
        タスク更新通知
        
        Args:
            task_data: タスクデータ
        
        Returns:
            レスポンス
        """
        message = self.protocol.create_message(MessageType.TASK_UPDATE, task_data)
        return await self.send_message(message)
    
    async def send_file_change(
        self,
        file_path: str,
        change_type: str,
        content: Optional[str] = None
    ) -> Optional[BridgeMessage]:
        """
        ファイル変更通知
        
        Args:
            file_path: ファイルパス
            change_type: 変更タイプ
            content: ファイル内容
        
        Returns:
            レスポンス
        """
        message = self.protocol.create_file_change(file_path, change_type, content)
        return await self.send_message(message)
    
    async def send_notification(
        self,
        title: str,
        message: str,
        level: str = "info"
    ) -> Optional[BridgeMessage]:
        """
        通知送信
        
        Args:
            title: タイトル
            message: メッセージ
            level: レベル
        
        Returns:
            レスポンス
        """
        notification = self.protocol.create_notification(title, message, level)
        return await self.send_message(notification)
    
    def add_message_handler(
        self,
        message_type: MessageType, 
        handler: Callable[[BridgeMessage], None]
    ) -> None:
        """
        メッセージハンドラーを追加
        
        Args:
            message_type: メッセージタイプ
            handler: ハンドラー関数
        """
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
        logger.info(f"Added handler for {message_type.value}")
    
    def remove_message_handler(
        self,
        message_type: MessageType,
        handler: Callable[[BridgeMessage], None]
    ) -> None:
        """
        メッセージハンドラーを削除
        
        Args:
            message_type: メッセージタイプ
            handler: ハンドラー関数
        """
        if message_type in self.message_handlers:
            try:
                self.message_handlers[message_type].remove(handler)
                logger.info(f"Removed handler for {message_type.value}")
            except ValueError:
                logger.warning(f"Handler not found for {message_type.value}")
    
    async def _perform_handshake(self) -> None:
        """ハンドシェイク実行"""
        client_info = {
            "client_name": "Claude Bridge Connector",
            "version": "1.0.0",
            "platform": os.name,
            "features": [
                "project_management",
                "task_management",
                "file_sync",
                "notifications"
            ]
        }
        
        handshake_msg = self.protocol.create_handshake(client_info)
        await self._send_message(handshake_msg)
        
        # ハンドシェイクレスポンス待機
        response = await self._wait_for_response(handshake_msg.message_id, timeout=10)
        if response and response.message_type == MessageType.HANDSHAKE:
            logger.info("Handshake completed successfully")
        else:
            raise DesktopConnectionError("Handshake failed")
    
    async def _send_message(self, message: BridgeMessage) -> None:
        """内部メッセージ送信"""
        if not self.websocket:
            raise DesktopConnectionError("WebSocket not available")
        
        try:
            json_data = message.to_json()
            await self.websocket.send(json_data)
            logger.debug(f"Sent message: {message.message_type.value}")
            
        except (ConnectionClosedError, ConnectionClosedOK) as e:
            logger.error(f"Connection lost during send: {e}")
            self.is_connected = False
            raise DesktopConnectionError("Connection lost")
    
    async def _wait_for_response(
        self,
        message_id: str,
        timeout: int = 30
    ) -> Optional[BridgeMessage]:
        """レスポンス待機"""
        future = asyncio.Future()
        self.response_waiters[message_id] = future
        
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            logger.warning(f"Response timeout for message {message_id}")
            return None
            
        finally:
            self.response_waiters.pop(message_id, None)
    
    async def _message_listener(self) -> None:
        """メッセージリスナー"""
        if not self.websocket:
            return
        
        try:
            async for message_data in self.websocket:
                try:
                    message = BridgeMessage.from_json(message_data)
                    self.connection_stats["messages_received"] += 1
                    
                    # レスポンス待機者がいる場合は通知
                    if message.correlation_id in self.response_waiters:
                        future = self.response_waiters[message.correlation_id]
                        if not future.done():
                            future.set_result(message)
                        continue
                    
                    # ハンドラー実行
                    await self._handle_message(message)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except (ConnectionClosedError, ConnectionClosedOK):
            logger.info("WebSocket connection closed")
            self.is_connected = False
            
        except Exception as e:
            logger.error(f"Message listener error: {e}")
            self.is_connected = False
    
    async def _handle_message(self, message: BridgeMessage) -> None:
        """メッセージハンドリング"""
        logger.debug(f"Received message: {message.message_type.value}")
        
        # 組み込みハンドラー
        if message.message_type == MessageType.PING:
            pong = self.protocol.create_pong(message)
            await self._send_message(pong)
            return
        
        elif message.message_type == MessageType.PONG:
            self.last_pong_time = time.time()
            return
        
        # カスタムハンドラー実行
        if message.message_type in self.message_handlers:
            for handler in self.message_handlers[message.message_type]:
                try:
                    # 非同期ハンドラーの場合
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                        
                except Exception as e:
                    logger.error(f"Handler error for {message.message_type.value}: {e}")
    
    async def _heartbeat_task(self) -> None:
        """ハートビートタスク"""
        while self.is_connected:
            try:
                if self.websocket:
                    ping_msg = self.protocol.create_ping()
                    await self._send_message(ping_msg)
                    self.last_ping_time = time.time()
                    
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
    
    async def _start_background_tasks(self) -> None:
        """バックグラウンドタスク開始"""
        # メッセージリスナー
        listener_task = asyncio.create_task(self._message_listener())
        self.background_tasks.append(listener_task)
        
        # ハートビート
        heartbeat_task = asyncio.create_task(self._heartbeat_task())
        self.background_tasks.append(heartbeat_task)
        
        logger.info("Background tasks started")
    
    async def _stop_background_tasks(self) -> None:
        """バックグラウンドタスク停止"""
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.background_tasks.clear()
        logger.info("Background tasks stopped")
    
    def _needs_response(self, message_type: MessageType) -> bool:
        """レスポンスが必要なメッセージタイプかチェック"""
        response_required = {
            MessageType.HANDSHAKE,
            MessageType.PROJECT_SWITCH,
            MessageType.PROJECT_STATUS,
            MessageType.PROJECT_LIST,
            MessageType.TASK_CREATE,
            MessageType.TASK_LIST
        }
        return message_type in response_required
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        接続状態を取得
        
        Returns:
            接続状態情報
        """
        uptime = None
        if self.connection_stats["uptime_start"] and self.is_connected:
            start_time = datetime.fromisoformat(self.connection_stats["uptime_start"])
            uptime = (datetime.now() - start_time).total_seconds()
        
        return {
            "is_connected": self.is_connected,
            "is_connecting": self.is_connecting,
            "websocket_url": self.websocket_url,
            "reconnect_attempts": self.reconnect_attempts,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "uptime_seconds": uptime,
            "last_ping_time": self.last_ping_time,
            "last_pong_time": self.last_pong_time,
            "connection_stats": self.connection_stats,
            "active_handlers": {
                mt.value: len(handlers) 
                for mt, handlers in self.message_handlers.items()
            },
            "pending_responses": len(self.response_waiters)
        }
    
    async def reconnect(self) -> bool:
        """
        再接続試行
        
        Returns:
            再接続成功可否
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return False
        
        self.reconnect_attempts += 1
        logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        # 既存接続をクリーンアップ
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None
        
        self.is_connected = False
        
        # 指数バックオフで待機
        wait_time = min(2 ** (self.reconnect_attempts - 1), 60)
        await asyncio.sleep(wait_time)
        
        return await self.connect()