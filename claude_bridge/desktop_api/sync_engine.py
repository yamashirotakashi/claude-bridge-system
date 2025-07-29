"""
Claude Bridge System - Sync Engine
リアルタイム同期エンジン
"""

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Set, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

import aiofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .desktop_connector import DesktopConnector
from .bridge_protocol import MessageType, BridgeMessage
from ..core import BridgeFileSystem, ProjectRegistry
from ..exceptions import BridgeException

logger = logging.getLogger(__name__)


@dataclass
class SyncState:
    """同期状態"""
    file_path: str
    last_sync_time: str
    checksum: str
    source: str  # "cli" or "desktop"
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncState':
        return cls(**data)


class ConflictResolutionError(BridgeException):
    """競合解決エラー"""
    pass


class SyncEngine:
    """リアルタイム同期エンジン"""
    
    def __init__(
        self,
        bridge_fs: BridgeFileSystem,
        project_registry: ProjectRegistry,
        desktop_connector: DesktopConnector,
        sync_interval: int = 5,
        conflict_resolution: str = "manual"  # "manual", "cli_wins", "desktop_wins", "latest_wins" 
    ):
        """
        同期エンジンの初期化
        
        Args:
            bridge_fs: ブリッジファイルシステム
            project_registry: プロジェクトレジストリ
            desktop_connector: デスクトップコネクター
            sync_interval: 同期間隔（秒）
            conflict_resolution: 競合解決方法
        """
        self.bridge_fs = bridge_fs
        self.project_registry = project_registry
        self.desktop_connector = desktop_connector
        self.sync_interval = sync_interval
        self.conflict_resolution = conflict_resolution
        
        # 同期状態管理
        self.sync_states: Dict[str, SyncState] = {}
        self.watched_paths: Set[Path] = set()
        self.sync_queue: asyncio.Queue = asyncio.Queue()
        self.conflict_queue: asyncio.Queue = asyncio.Queue()
        
        # ファイル監視
        self.file_observer: Optional[Observer] = None
        self.file_handler: Optional[FileSystemEventHandler] = None
        
        # 同期タスク
        self.sync_tasks: List[asyncio.Task] = []
        self.is_running = False
        
        # 統計情報
        self.sync_stats = {
            "files_synced": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "sync_errors": 0,
            "last_sync_time": None,
            "sync_start_time": None
        }
        
        # コールバック
        self.conflict_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.sync_callbacks: List[Callable[[str, str], None]] = []
        
        # Desktop connector にハンドラー登録
        self.desktop_connector.add_message_handler(
            MessageType.FILE_CHANGE,
            self._handle_desktop_file_change
        )
        self.desktop_connector.add_message_handler(
            MessageType.FILE_SYNC,
            self._handle_desktop_file_sync
        )
        self.desktop_connector.add_message_handler(
            MessageType.FILE_CONFLICT,
            self._handle_desktop_file_conflict
        )
        
        logger.info(f"SyncEngine initialized with {conflict_resolution} conflict resolution")
    
    async def start(self) -> None:
        """同期エンジン開始"""
        if self.is_running:
            logger.warning("Sync engine is already running")
            return
        
        self.is_running = True
        self.sync_stats["sync_start_time"] = datetime.now().isoformat()
        
        # 監視対象パス設定
        await self._setup_watched_paths()
        
        # ファイル監視開始
        self._start_file_watcher()
        
        # 同期タスク開始
        await self._start_sync_tasks()
        
        logger.info("Sync engine started successfully")
    
    async def stop(self) -> None:
        """同期エンジン停止"""
        if not self.is_running:
            logger.warning("Sync engine is not running")
            return
        
        self.is_running = False
        
        # ファイル監視停止
        self._stop_file_watcher()
        
        # 同期タスク停止
        await self._stop_sync_tasks()
        
        logger.info("Sync engine stopped")
    
    async def sync_file(
        self,
        file_path: Path,
        source: str = "cli",
        force: bool = False
    ) -> bool:
        """
        ファイル同期
        
        Args:
            file_path: ファイルパス
            source: 同期元 ("cli" or "desktop")
            force: 強制同期
        
        Returns:
            同期成功可否
        """
        try:
            file_str = str(file_path.resolve())
            
            # ファイル存在チェック
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return False
            
            # チェックサム計算
            checksum = await self._calculate_checksum(file_path)
            
            # 既存の同期状態チェック
            existing_state = self.sync_states.get(file_str)
            
            if not force and existing_state:
                # 変更がない場合はスキップ
                if existing_state.checksum == checksum:
                    logger.debug(f"No changes detected: {file_path}")
                    return True
                
                # 競合チェック
                if await self._detect_conflict(file_path, checksum, source):
                    logger.warning(f"Conflict detected: {file_path}")
                    await self._handle_conflict(file_path, checksum, source)
                    return False
            
            # ファイル内容読み込み
            content = await self._read_file_content(file_path)
            
            # Desktop に変更通知
            await self.desktop_connector.send_file_change(
                file_str, 
                "modified",
                content
            )
            
            # 同期状態更新
            self.sync_states[file_str] = SyncState(
                file_path=file_str,
                last_sync_time=datetime.now().isoformat(),
                checksum=checksum,
                source=source
            )
            
            self.sync_stats["files_synced"] += 1
            self.sync_stats["last_sync_time"] = datetime.now().isoformat()
            
            # コールバック実行
            for callback in self.sync_callbacks:
                try:
                    callback(file_str, source)
                except Exception as e:
                    logger.error(f"Sync callback error: {e}")
            
            logger.info(f"Successfully synced: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync file {file_path}: {e}")
            self.sync_stats["sync_errors"] += 1
            return False
    
    async def resolve_conflict(
        self,
        file_path: Path,
        resolution: str,
        content: Optional[str] = None
    ) -> bool:
        """
        競合解決
        
        Args:
            file_path: ファイルパス
            resolution: 解決方法 ("cli", "desktop", "merge", "manual")
            content: マニュアル解決時の内容
        
        Returns:
            解決成功可否
        """
        try:
            file_str = str(file_path.resolve())
            
            if resolution == "cli":
                # CLI側を採用
                await self.sync_file(file_path, "cli", force=True)
                
            elif resolution == "desktop":
                # Desktop側を採用 - Desktop からの更新を要求
                sync_request = self.desktop_connector.protocol.create_message(
                    MessageType.FILE_SYNC,
                    {
                        "file_path": file_str,
                        "action": "pull",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                await self.desktop_connector.send_message(sync_request)
                
            elif resolution == "manual" and content is not None:
                # マニュアル解決
                await self._write_file_content(file_path, content)
                await self.sync_file(file_path, "manual", force=True)
                
            else:
                raise ConflictResolutionError(f"Invalid resolution method: {resolution}")
            
            self.sync_stats["conflicts_resolved"] += 1
            logger.info(f"Conflict resolved for {file_path} using {resolution}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict for {file_path}: {e}")
            return False
    
    def add_conflict_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """競合発生コールバック追加"""
        self.conflict_callbacks.append(callback)
    
    def add_sync_callback(self, callback: Callable[[str, str], None]) -> None:
        """同期完了コールバック追加"""
        self.sync_callbacks.append(callback)
    
    async def _setup_watched_paths(self) -> None:
        """監視対象パス設定"""
        # プロジェクトディレクトリ
        projects = self.project_registry.list_projects()
        for project_id, project_config in projects.items():
            project_path = Path(project_config.path)
            if project_path.exists():
                self.watched_paths.add(project_path)
        
        # ブリッジディレクトリ
        bridge_root = Path(self.bridge_fs.bridge_root)
        if bridge_root.exists():
            self.watched_paths.add(bridge_root)
        
        logger.info(f"Watching {len(self.watched_paths)} paths")
    
    def _start_file_watcher(self) -> None:
        """ファイル監視開始"""
        class SyncEventHandler(FileSystemEventHandler):
            def __init__(self, sync_engine: 'SyncEngine'):
                self.sync_engine = sync_engine
            
            def on_modified(self, event: FileSystemEvent):
                if not event.is_directory:
                    asyncio.create_task(
                        self.sync_engine.sync_queue.put((Path(event.src_path), "cli"))
                    )
            
            def on_created(self, event: FileSystemEvent):
                if not event.is_directory:
                    asyncio.create_task(
                        self.sync_engine.sync_queue.put((Path(event.src_path), "cli"))
                    )
        
        self.file_handler = SyncEventHandler(self)
        self.file_observer = Observer()
        
        for path in self.watched_paths:
            self.file_observer.schedule(self.file_handler, str(path), recursive=True)
        
        self.file_observer.start()
        logger.info("File watcher started")
    
    def _stop_file_watcher(self) -> None:
        """ファイル監視停止"""
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            self.file_observer = None
        
        self.file_handler = None
        logger.info("File watcher stopped")
    
    async def _start_sync_tasks(self) -> None:
        """同期タスク開始"""
        # 同期キュー処理タスク
        sync_processor = asyncio.create_task(self._process_sync_queue())
        self.sync_tasks.append(sync_processor)
        
        # 競合処理タスク
        conflict_processor = asyncio.create_task(self._process_conflict_queue())
        self.sync_tasks.append(conflict_processor)
        
        # 定期同期タスク
        periodic_sync = asyncio.create_task(self._periodic_sync())
        self.sync_tasks.append(periodic_sync)
        
        logger.info("Sync tasks started")
    
    async def _stop_sync_tasks(self) -> None:
        """同期タスク停止"""
        for task in self.sync_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.sync_tasks.clear()
        logger.info("Sync tasks stopped")
    
    async def _process_sync_queue(self) -> None:
        """同期キュー処理"""
        while self.is_running:
            try:
                # キューから同期要求を取得
                file_path, source = await asyncio.wait_for(
                    self.sync_queue.get(),
                    timeout=1.0
                )
                
                # 同期実行
                await self.sync_file(file_path, source)
                
            except asyncio.TimeoutError:
                # タイムアウトは正常
                continue
            except Exception as e:
                logger.error(f"Sync queue processing error: {e}")
    
    async def _process_conflict_queue(self) -> None:
        """競合キュー処理"""
        while self.is_running:
            try:
                # キューから競合情報を取得
                conflict_info = await asyncio.wait_for(
                    self.conflict_queue.get(),
                    timeout=1.0
                )
                
                # 自動解決試行
                if self.conflict_resolution != "manual":
                    await self._auto_resolve_conflict(conflict_info)
                else:
                    # コールバック通知
                    for callback in self.conflict_callbacks:
                        try:
                            callback(conflict_info)
                        except Exception as e:
                            logger.error(f"Conflict callback error: {e}")
                
            except asyncio.TimeoutError:
                # タイムアウトは正常
                continue
            except Exception as e:
                logger.error(f"Conflict queue processing error: {e}")
    
    async def _periodic_sync(self) -> None:
        """定期同期"""
        while self.is_running:
            try:
                # すべての監視ファイルの同期状態チェック
                for path in self.watched_paths:
                    if path.is_file():
                        await self.sync_queue.put((path, "cli"))
                    elif path.is_dir():
                        # ディレクトリ内のファイルをチェック
                        for file_path in path.rglob("*"):
                            if file_path.is_file() and not self._should_ignore_file(file_path):
                                await self.sync_queue.put((file_path, "cli"))
                
                await asyncio.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Periodic sync error: {e}")
                await asyncio.sleep(self.sync_interval)
    
    async def _detect_conflict(
        self,
        file_path: Path,
        current_checksum: str,
        source: str
    ) -> bool:
        """競合検出"""
        file_str = str(file_path.resolve())
        existing_state = self.sync_states.get(file_str)
        
        if not existing_state:
            return False
        
        # 同一ソースからの変更は競合なし
        if existing_state.source == source:
            return False
        
        # チェックサムが異なる場合は競合
        return existing_state.checksum != current_checksum
    
    async def _handle_conflict(
        self,
        file_path: Path,
        checksum: str,
        source: str
    ) -> None:
        """競合処理"""
        conflict_info = {
            "file_path": str(file_path.resolve()),
            "current_checksum": checksum,
            "current_source": source,
            "existing_state": self.sync_states.get(str(file_path.resolve())),
            "timestamp": datetime.now().isoformat()
        }
        
        self.sync_stats["conflicts_detected"] += 1
        await self.conflict_queue.put(conflict_info)
        
        # Desktop に競合通知
        conflict_msg = self.desktop_connector.protocol.create_message(
            MessageType.FILE_CONFLICT,
            conflict_info
        )
        await self.desktop_connector.send_message(conflict_msg)
    
    async def _auto_resolve_conflict(self, conflict_info: Dict[str, Any]) -> None:
        """自動競合解決"""
        file_path = Path(conflict_info["file_path"])
        
        if self.conflict_resolution == "cli_wins":
            await self.resolve_conflict(file_path, "cli")
            
        elif self.conflict_resolution == "desktop_wins":
            await self.resolve_conflict(file_path, "desktop")
            
        elif self.conflict_resolution == "latest_wins":
            # タイムスタンプ比較
            existing_state = conflict_info["existing_state"]
            if existing_state:
                existing_time = datetime.fromisoformat(existing_state["last_sync_time"])
                current_time = datetime.fromisoformat(conflict_info["timestamp"])
                
                if current_time > existing_time:
                    await self.resolve_conflict(file_path, conflict_info["current_source"])
                else:
                    # 既存状態を維持
                    logger.info(f"Keeping existing version for {file_path}")
    
    async def _handle_desktop_file_change(self, message: BridgeMessage) -> None:
        """Desktop からのファイル変更処理"""
        try:
            payload = message.payload
            file_path = Path(payload["file_path"])
            change_type = payload["change_type"]
            content = payload.get("content")
            
            if content and change_type in ["created", "modified"]:
                # ファイル内容を更新
                await self._write_file_content(file_path, content)
                
                # 同期状態更新
                checksum = await self._calculate_checksum(file_path)
                file_str = str(file_path.resolve())
                
                self.sync_states[file_str] = SyncState(
                    file_path=file_str,
                    last_sync_time=datetime.now().isoformat(),
                    checksum=checksum,
                    source="desktop"
                )
                
                logger.info(f"Applied desktop changes: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to handle desktop file change: {e}")
    
    async def _handle_desktop_file_sync(self, message: BridgeMessage) -> None:
        """Desktop からの同期要求処理"""
        try:
            payload = message.payload
            file_path = Path(payload["file_path"])
            action = payload["action"]
            
            if action == "push":
                # Desktop から CLI への同期
                content = payload.get("content")
                if content:
                    await self._write_file_content(file_path, content)
                    await self.sync_file(file_path, "desktop", force=True)
                    
            elif action == "pull":
                # CLI から Desktop への同期
                if file_path.exists():
                    await self.sync_file(file_path, "cli", force=True)
                    
        except Exception as e:
            logger.error(f"Failed to handle desktop sync request: {e}")
    
    async def _handle_desktop_file_conflict(self, message: BridgeMessage) -> None:
        """Desktop からの競合解決処理"""
        try:
            payload = message.payload
            file_path = Path(payload["file_path"])
            resolution = payload["resolution"]
            content = payload.get("content")
            
            await self.resolve_conflict(file_path, resolution, content)
            
        except Exception as e:
            logger.error(f"Failed to handle desktop conflict resolution: {e}")
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """ファイルチェックサム計算"""
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    async def _read_file_content(self, file_path: Path) -> str:
        """ファイル内容読み込み"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return ""
    
    async def _write_file_content(self, file_path: Path, content: str) -> None:
        """ファイル内容書き込み"""
        try:
            # ディレクトリ作成
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
                
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            raise
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """ファイル無視判定"""
        ignore_patterns = {
            '.git', '.gitignore', 
            '__pycache__', '*.pyc', '*.pyo',
            '.DS_Store', 'Thumbs.db',
            '*.log', '*.tmp', '*.swp'
        }
        
        # パターンマッチング
        for pattern in ignore_patterns:
            if pattern.startswith('*.'):
                if file_path.suffix == pattern[1:]:
                    return True
            elif pattern in str(file_path):
                return True
        
        return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        同期状態を取得
        
        Returns:
            同期状態情報
        """
        uptime = None
        if self.sync_stats["sync_start_time"] and self.is_running:
            start_time = datetime.fromisoformat(self.sync_stats["sync_start_time"])
            uptime = (datetime.now() - start_time).total_seconds()
        
        return {
            "is_running": self.is_running,
            "sync_interval": self.sync_interval,
            "conflict_resolution": self.conflict_resolution,
            "watched_paths_count": len(self.watched_paths),
            "tracked_files_count": len(self.sync_states),
            "uptime_seconds": uptime,
            "sync_stats": self.sync_stats,
            "queue_sizes": {
                "sync_queue": self.sync_queue.qsize(),
                "conflict_queue": self.conflict_queue.qsize()
            },
            "callbacks": {
                "conflict_callbacks": len(self.conflict_callbacks),
                "sync_callbacks": len(self.sync_callbacks)
            }
        }