"""
Claude Bridge System - Bridge Protocol
Claude Code CLI と Claude Desktop 間の通信プロトコル
"""

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict

import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """メッセージタイプ定義"""
    # 基本制御
    PING = "ping"
    PONG = "pong"
    HANDSHAKE = "handshake"
    DISCONNECT = "disconnect"
    
    # プロジェクト管理
    PROJECT_SWITCH = "project_switch"
    PROJECT_STATUS = "project_status"
    PROJECT_LIST = "project_list"
    
    # タスク管理
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_COMPLETE = "task_complete"
    TASK_DELETE = "task_delete"
    TASK_LIST = "task_list"
    
    # ファイル同期
    FILE_CHANGE = "file_change"
    FILE_SYNC = "file_sync"
    FILE_CONFLICT = "file_conflict"
    
    # セッション管理
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SESSION_STATE = "session_state"
    
    # エラーハンドリング
    ERROR = "error"
    WARNING = "warning"
    
    # 通知
    NOTIFICATION = "notification"
    STATUS_UPDATE = "status_update"


@dataclass
class BridgeMessage:
    """ブリッジメッセージ基本構造"""
    message_type: MessageType
    payload: Dict[str, Any]
    message_id: str = None
    timestamp: str = None
    source: str = "claude_bridge"
    target: str = "claude_desktop"
    correlation_id: str = None
    
    def __post_init__(self):
        """初期化後処理"""
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = asdict(self)
        result['message_type'] = self.message_type.value
        return result
    
    def to_json(self) -> str:
        """JSON文字列に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BridgeMessage':
        """辞書からメッセージを作成"""
        try:
            message_type = MessageType(data['message_type'])
            return cls(
                message_type=message_type,
                payload=data['payload'],
                message_id=data.get('message_id'),
                timestamp=data.get('timestamp'),
                source=data.get('source', 'unknown'),
                target=data.get('target', 'unknown'),
                correlation_id=data.get('correlation_id')
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse BridgeMessage: {e}")
            raise ValueError(f"Invalid message format: {e}")
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BridgeMessage':
        """JSON文字列からメッセージを作成"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError(f"Invalid JSON format: {e}")


class BridgeProtocol:
    """ブリッジプロトコル管理クラス"""
    
    def __init__(self, source_name: str = "claude_bridge"):
        """
        プロトコル管理の初期化
        
        Args:
            source_name: このクライアントの名前
        """
        self.source_name = source_name
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"BridgeProtocol initialized for {source_name}")
    
    def create_message(
        self,
        message_type: MessageType,
        payload: Dict[str, Any],
        target: str = "claude_desktop",
        correlation_id: Optional[str] = None
    ) -> BridgeMessage:
        """
        新しいメッセージを作成
        
        Args:
            message_type: メッセージタイプ
            payload: メッセージデータ
            target: 送信先
            correlation_id: 関連メッセージID
        
        Returns:
            作成されたメッセージ
        """
        return BridgeMessage(
            message_type=message_type,
            payload=payload,
            source=self.source_name,
            target=target,
            correlation_id=correlation_id
        )
    
    def create_response(
        self,
        original_message: BridgeMessage,
        response_type: MessageType,
        payload: Dict[str, Any]
    ) -> BridgeMessage:
        """
        レスポンスメッセージを作成
        
        Args:
            original_message: 元のメッセージ
            response_type: レスポンスタイプ
            payload: レスポンスデータ
        
        Returns:
            レスポンスメッセージ
        """
        return BridgeMessage(
            message_type=response_type,
            payload=payload,
            source=self.source_name,
            target=original_message.source,
            correlation_id=original_message.message_id
        )
    
    def create_error_response(
        self,
        original_message: BridgeMessage,
        error_code: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> BridgeMessage:
        """
        エラーレスポンスを作成
        
        Args:
            original_message: 元のメッセージ
            error_code: エラーコード
            error_message: エラーメッセージ
            details: 詳細情報
        
        Returns:
            エラーメッセージ
        """
        payload = {
            "error_code": error_code,
            "error_message": error_message,
            "original_message": original_message.to_dict()
        }
        
        if details:
            payload["details"] = details
        
        return self.create_response(
            original_message,
            MessageType.ERROR,
            payload
        )
    
    def create_ping(self) -> BridgeMessage:
        """Pingメッセージを作成"""
        return self.create_message(
            MessageType.PING,
            {
                "timestamp": datetime.now().isoformat(),
                "source": self.source_name
            }
        )
    
    def create_pong(self, ping_message: BridgeMessage) -> BridgeMessage:
        """Pongメッセージを作成"""
        return self.create_response(
            ping_message,
            MessageType.PONG,
            {
                "timestamp": datetime.now().isoformat(),
                "source": self.source_name
            }
        )
    
    def create_handshake(
        self,
        client_info: Dict[str, Any]
    ) -> BridgeMessage:
        """
        ハンドシェイクメッセージを作成
        
        Args:
            client_info: クライアント情報
        
        Returns:
            ハンドシェイクメッセージ
        """
        payload = {
            "client_info": client_info,
            "protocol_version": "1.0.0",
            "supported_features": [
                "project_management",
                "task_management", 
                "file_sync",
                "real_time_sync"
            ]
        }
        
        return self.create_message(MessageType.HANDSHAKE, payload)
    
    def create_project_switch(
        self,
        project_id: str,
        project_context: Dict[str, Any]
    ) -> BridgeMessage:
        """
        プロジェクト切り替えメッセージを作成
        
        Args:
            project_id: プロジェクトID
            project_context: プロジェクトコンテキスト
        
        Returns:
            プロジェクト切り替えメッセージ
        """
        payload = {
            "project_id": project_id,
            "project_context": project_context,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.create_message(MessageType.PROJECT_SWITCH, payload)
    
    def create_task_create(
        self,
        task_data: Dict[str, Any]
    ) -> BridgeMessage:
        """
        タスク作成メッセージを作成
        
        Args:
            task_data: タスクデータ
        
        Returns:
            タスク作成メッセージ
        """
        return self.create_message(MessageType.TASK_CREATE, task_data)
    
    def create_file_change(
        self,
        file_path: str,
        change_type: str,
        content: Optional[str] = None
    ) -> BridgeMessage:
        """
        ファイル変更メッセージを作成
        
        Args:
            file_path: ファイルパス
            change_type: 変更タイプ (created, modified, deleted)
            content: ファイル内容（必要に応じて）
        
        Returns:
            ファイル変更メッセージ
        """
        payload = {
            "file_path": file_path,
            "change_type": change_type,
            "timestamp": datetime.now().isoformat()
        }
        
        if content is not None:
            payload["content"] = content
        
        return self.create_message(MessageType.FILE_CHANGE, payload)
    
    def create_notification(
        self,
        title: str,
        message: str,
        level: str = "info",
        actions: Optional[list] = None
    ) -> BridgeMessage:
        """
        通知メッセージを作成
        
        Args:
            title: 通知タイトル
            message: 通知メッセージ
            level: 通知レベル (info, warning, error)
            actions: アクションボタン
        
        Returns:
            通知メッセージ
        """
        payload = {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }
        
        if actions:
            payload["actions"] = actions
        
        return self.create_message(MessageType.NOTIFICATION, payload)
    
    def validate_message(self, message: BridgeMessage) -> bool:
        """
        メッセージの妥当性を検証
        
        Args:
            message: 検証するメッセージ
        
        Returns:
            妥当性チェック結果
        """
        try:
            # 必須フィールドの確認
            if not message.message_type:
                logger.error("Message type is missing")
                return False
            
            if not message.payload:
                logger.error("Payload is missing")
                return False
            
            if not message.message_id:
                logger.error("Message ID is missing")
                return False
            
            # タイムスタンプの形式確認
            try:
                datetime.fromisoformat(message.timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.error(f"Invalid timestamp format: {message.timestamp}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Message validation failed: {e}")
            return False
    
    def get_message_stats(self) -> Dict[str, Any]:
        """
        メッセージ統計を取得
        
        Returns:
            統計情報
        """
        return {
            "protocol_version": "1.0.0",
            "source_name": self.source_name,
            "active_sessions": len(self.active_sessions),
            "supported_message_types": [mt.value for mt in MessageType],
            "total_message_types": len(MessageType)
        }