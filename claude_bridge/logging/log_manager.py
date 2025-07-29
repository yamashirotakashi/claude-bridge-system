"""
Claude Bridge System - Log Manager
ログローテーション、アーカイブ、管理機能
"""

import gzip
import shutil
import threading
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class RotationPolicy(Enum):
    """ローテーションポリシー"""
    SIZE = "size"           # サイズベース
    TIME = "time"           # 時間ベース
    DAILY = "daily"         # 日次
    WEEKLY = "weekly"       # 週次
    MONTHLY = "monthly"     # 月次


class CompressionType(Enum):
    """圧縮タイプ"""
    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"


@dataclass
class LogRotationConfig:
    """ログローテーション設定"""
    policy: RotationPolicy
    max_size_mb: int = 100              # サイズベースの場合の最大サイズ(MB)
    rotation_hour: int = 0              # 時間ベースローテーションの時刻
    max_files: int = 10                 # 保持するファイル数
    compression: CompressionType = CompressionType.GZIP
    backup_extension: str = ".bak"
    
    def __post_init__(self):
        if self.rotation_hour < 0 or self.rotation_hour > 23:
            raise ValueError("rotation_hour must be between 0 and 23")


@dataclass
class LogArchiveConfig:
    """ログアーカイブ設定"""
    enabled: bool = True
    archive_after_days: int = 30        # アーカイブまでの日数
    delete_after_days: int = 365        # 削除までの日数
    archive_path: Optional[Path] = None
    compression: CompressionType = CompressionType.GZIP


class LogManager:
    """ログ管理システム"""
    
    def __init__(self, 
                 log_directory: Path,
                 rotation_config: Optional[LogRotationConfig] = None,
                 archive_config: Optional[LogArchiveConfig] = None):
        """
        初期化
        
        Args:
            log_directory: ログディレクトリ
            rotation_config: ローテーション設定
            archive_config: アーカイブ設定
        """
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        self.rotation_config = rotation_config or LogRotationConfig(
            policy=RotationPolicy.SIZE
        )
        self.archive_config = archive_config or LogArchiveConfig()
        
        # アーカイブディレクトリ設定
        if self.archive_config.archive_path is None:
            self.archive_config.archive_path = self.log_directory / "archive"
        self.archive_config.archive_path.mkdir(parents=True, exist_ok=True)
        
        # 管理用のデータ
        self.managed_files: Dict[str, Dict[str, Any]] = {}
        self.last_rotation_check = datetime.now()
        
        # バックグラウンドタスク制御
        self.management_active = False
        self.management_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        logger.info(f"LogManager initialized: {self.log_directory}")
    
    def register_log_file(self, 
                         file_path: Path, 
                         logger_name: str = "default") -> None:
        """ログファイルを管理対象に登録"""
        file_key = str(file_path.resolve())
        
        with self._lock:
            self.managed_files[file_key] = {
                "path": file_path,
                "logger_name": logger_name,
                "created_at": datetime.now(),
                "last_rotated": datetime.now(),
                "rotation_count": 0
            }
        
        logger.info(f"Log file registered: {file_path}")
    
    def start_management(self) -> None:
        """ログ管理を開始"""
        if self.management_active:
            logger.warning("Log management already running")
            return
        
        self.management_active = True
        self.management_thread = threading.Thread(target=self._management_loop)
        self.management_thread.daemon = True
        self.management_thread.start()
        
        logger.info("Log management started")
    
    def stop_management(self) -> None:
        """ログ管理を停止"""
        self.management_active = False
        if self.management_thread and self.management_thread.is_alive():
            self.management_thread.join(timeout=5.0)
        
        logger.info("Log management stopped")
    
    def _management_loop(self) -> None:
        """ログ管理ループ"""
        while self.management_active:
            try:
                current_time = datetime.now()
                
                # ローテーションチェック
                if self._should_check_rotation(current_time):
                    self._check_and_rotate_logs()
                    self.last_rotation_check = current_time
                
                # アーカイブチェック（1日1回）
                if current_time.hour == 1 and current_time.minute < 5:
                    self._check_and_archive_logs()
                
                # 5分間隔でチェック
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in log management loop: {e}")
                time.sleep(60)  # エラー時は1分待機
    
    def _should_check_rotation(self, current_time: datetime) -> bool:
        """ローテーションチェックが必要かどうか"""
        time_diff = current_time - self.last_rotation_check
        
        if self.rotation_config.policy == RotationPolicy.SIZE:
            # サイズベースは5分間隔
            return time_diff.total_seconds() >= 300
        elif self.rotation_config.policy == RotationPolicy.DAILY:
            # 日次は指定時刻をチェック
            return (current_time.hour == self.rotation_config.rotation_hour and 
                   current_time.minute < 5)
        elif self.rotation_config.policy == RotationPolicy.WEEKLY:
            # 週次は日曜日の指定時刻
            return (current_time.weekday() == 6 and 
                   current_time.hour == self.rotation_config.rotation_hour and
                   current_time.minute < 5)
        elif self.rotation_config.policy == RotationPolicy.MONTHLY:
            # 月次は1日の指定時刻
            return (current_time.day == 1 and 
                   current_time.hour == self.rotation_config.rotation_hour and
                   current_time.minute < 5)
        
        return False
    
    def _check_and_rotate_logs(self) -> None:
        """ログローテーションチェックと実行"""
        with self._lock:
            files_to_rotate = []
            
            for file_key, file_info in self.managed_files.items():
                file_path = file_info["path"]
                
                if self._needs_rotation(file_path, file_info):
                    files_to_rotate.append((file_key, file_info))
            
            # ローテーション実行
            for file_key, file_info in files_to_rotate:
                try:
                    self._rotate_log_file(file_info)
                    file_info["last_rotated"] = datetime.now()
                    file_info["rotation_count"] += 1
                except Exception as e:
                    logger.error(f"Failed to rotate log file {file_info['path']}: {e}")
    
    def _needs_rotation(self, file_path: Path, file_info: Dict[str, Any]) -> bool:
        """ローテーションが必要かどうか判定"""
        if not file_path.exists():
            return False
        
        if self.rotation_config.policy == RotationPolicy.SIZE:
            # サイズベース
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            return file_size_mb >= self.rotation_config.max_size_mb
        
        elif self.rotation_config.policy in [
            RotationPolicy.DAILY, RotationPolicy.WEEKLY, RotationPolicy.MONTHLY
        ]:
            # 時間ベース（最後のローテーションから時間が経過したか）
            last_rotated = file_info["last_rotated"]
            current_time = datetime.now()
            
            if self.rotation_config.policy == RotationPolicy.DAILY:
                return (current_time - last_rotated).days >= 1
            elif self.rotation_config.policy == RotationPolicy.WEEKLY:
                return (current_time - last_rotated).days >= 7
            elif self.rotation_config.policy == RotationPolicy.MONTHLY:
                return (current_time - last_rotated).days >= 30
        
        return False
    
    def _rotate_log_file(self, file_info: Dict[str, Any]) -> None:
        """ログファイルをローテーション"""
        file_path = file_info["path"]
        logger_name = file_info["logger_name"]
        
        if not file_path.exists():
            return
        
        # バックアップファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{self.rotation_config.backup_extension}"
        backup_path = file_path.parent / backup_name
        
        # ファイルを移動
        shutil.move(str(file_path), str(backup_path))
        
        # 圧縮
        if self.rotation_config.compression == CompressionType.GZIP:
            compressed_path = backup_path.with_suffix(backup_path.suffix + ".gz")
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_path.unlink()  # 元ファイルを削除
            backup_path = compressed_path
        
        # 古いバックアップファイルを削除
        self._cleanup_old_backups(file_path)
        
        logger.info(f"Log file rotated: {file_path} -> {backup_path}")
    
    def _cleanup_old_backups(self, original_file: Path) -> None:
        """古いバックアップファイルを削除"""
        pattern = f"{original_file.stem}_*{self.rotation_config.backup_extension}*"
        backup_files = list(original_file.parent.glob(pattern))
        
        # 作成日時でソート
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # 保持数を超えるファイルを削除
        if len(backup_files) > self.rotation_config.max_files:
            for old_file in backup_files[self.rotation_config.max_files:]:
                try:
                    old_file.unlink()
                    logger.info(f"Deleted old backup: {old_file}")
                except Exception as e:
                    logger.error(f"Failed to delete old backup {old_file}: {e}")
    
    def _check_and_archive_logs(self) -> None:
        """ログアーカイブチェックと実行"""
        if not self.archive_config.enabled:
            return
        
        current_time = datetime.now()
        archive_cutoff = current_time - timedelta(days=self.archive_config.archive_after_days)
        delete_cutoff = current_time - timedelta(days=self.archive_config.delete_after_days)
        
        # すべてのログファイルをチェック
        for log_file in self.log_directory.glob("**/*"):
            if not log_file.is_file():
                continue
            
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            # 削除対象
            if file_mtime < delete_cutoff:
                try:
                    log_file.unlink()
                    logger.info(f"Deleted old log file: {log_file}")
                except Exception as e:
                    logger.error(f"Failed to delete old log file {log_file}: {e}")
            
            # アーカイブ対象
            elif file_mtime < archive_cutoff and not self._is_archived(log_file):
                try:
                    self._archive_log_file(log_file)
                except Exception as e:
                    logger.error(f"Failed to archive log file {log_file}: {e}")
    
    def _is_archived(self, log_file: Path) -> bool:
        """ファイルがすでにアーカイブされているかチェック"""
        # アーカイブディレクトリ内に同名ファイルがあるかチェック
        relative_path = log_file.relative_to(self.log_directory)
        archive_path = self.archive_config.archive_path / relative_path
        
        # 圧縮ファイルも含めてチェック
        if archive_path.exists():
            return True
        if (archive_path.parent / f"{archive_path.name}.gz").exists():
            return True
        
        return False
    
    def _archive_log_file(self, log_file: Path) -> None:
        """ログファイルをアーカイブ"""
        relative_path = log_file.relative_to(self.log_directory)
        archive_path = self.archive_config.archive_path / relative_path
        
        # アーカイブディレクトリを作成
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.archive_config.compression == CompressionType.GZIP:
            # GZIP圧縮してアーカイブ
            compressed_path = archive_path.with_suffix(archive_path.suffix + ".gz")
            with open(log_file, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 元ファイルを削除
            log_file.unlink()
            logger.info(f"Archived and compressed log file: {log_file} -> {compressed_path}")
        else:
            # 単純移動
            shutil.move(str(log_file), str(archive_path))
            logger.info(f"Archived log file: {log_file} -> {archive_path}")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """ログ統計情報を取得"""
        with self._lock:
            stats = {
                "managed_files": len(self.managed_files),
                "total_size_mb": 0,
                "files_info": [],
                "archive_info": {
                    "enabled": self.archive_config.enabled,
                    "archive_path": str(self.archive_config.archive_path),
                    "archived_files": 0,
                    "archive_size_mb": 0
                }
            }
            
            # 管理対象ファイルの統計
            for file_key, file_info in self.managed_files.items():
                file_path = file_info["path"]
                
                if file_path.exists():
                    file_size = file_path.stat().st_size / (1024 * 1024)
                    stats["total_size_mb"] += file_size
                    
                    stats["files_info"].append({
                        "path": str(file_path),
                        "logger_name": file_info["logger_name"],
                        "size_mb": file_size,
                        "created_at": file_info["created_at"].isoformat(),
                        "last_rotated": file_info["last_rotated"].isoformat(),
                        "rotation_count": file_info["rotation_count"]
                    })
            
            # アーカイブ統計
            if self.archive_config.enabled and self.archive_config.archive_path.exists():
                for archive_file in self.archive_config.archive_path.glob("**/*"):
                    if archive_file.is_file():
                        stats["archive_info"]["archived_files"] += 1
                        stats["archive_info"]["archive_size_mb"] += (
                            archive_file.stat().st_size / (1024 * 1024)
                        )
            
            return stats
    
    def force_rotation(self, logger_name: Optional[str] = None) -> int:
        """強制ローテーション実行"""
        rotated_count = 0
        
        with self._lock:
            for file_key, file_info in self.managed_files.items():
                if logger_name is None or file_info["logger_name"] == logger_name:
                    try:
                        self._rotate_log_file(file_info)
                        file_info["last_rotated"] = datetime.now()
                        file_info["rotation_count"] += 1
                        rotated_count += 1
                    except Exception as e:
                        logger.error(f"Failed to force rotate {file_info['path']}: {e}")
        
        logger.info(f"Force rotation completed: {rotated_count} files rotated")
        return rotated_count
    
    def cleanup_logs(self, older_than_days: int = 30) -> int:
        """指定日数より古いログを削除"""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        deleted_count = 0
        
        for log_file in self.log_directory.glob("**/*"):
            if not log_file.is_file():
                continue
            
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                try:
                    log_file.unlink()
                    deleted_count += 1
                    logger.info(f"Cleaned up old log file: {log_file}")
                except Exception as e:
                    logger.error(f"Failed to cleanup log file {log_file}: {e}")
        
        logger.info(f"Log cleanup completed: {deleted_count} files deleted")
        return deleted_count