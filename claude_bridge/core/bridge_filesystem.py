"""
Claude Bridge System - Bridge File System
ファイルベース連携システムの実装
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..exceptions import FileSystemError, ValidationError

logger = logging.getLogger(__name__)


class BridgeFileSystem:
    """Bridge ファイルシステム管理クラス
    
    Claude DesktopとClaude Code間のファイルベース連携を管理する。
    タスクファイル、設定ファイル、結果ファイルの作成・管理を担当。
    """
    
    def __init__(self, bridge_root: Optional[Union[str, Path]] = None):
        """
        初期化
        
        Args:
            bridge_root: Bridgeシステムのルートディレクトリ
                        Noneの場合はデフォルトパスを使用
        """
        if bridge_root is None:
            # デフォルトパス: プロジェクトディレクトリ/bridge_data
            bridge_root = Path(__file__).parent.parent.parent / "bridge_data"
        
        self.bridge_root = Path(bridge_root).resolve()
        self.initialized = False
        
        logger.info(f"BridgeFileSystem initialized with root: {self.bridge_root}")
    
    def initialize_structure(self, force: bool = False) -> bool:
        """
        必要なディレクトリ構造を初期化
        
        Args:
            force: 既存ディレクトリを強制的に再作成するか
            
        Returns:
            初期化が成功したかどうか
            
        Raises:
            FileSystemError: ディレクトリ作成に失敗した場合
        """
        if self.initialized and not force:
            logger.info("Bridge structure already initialized")
            return True
        
        dirs_to_create = [
            "config",
            "tasks/pending",
            "tasks/processing", 
            "tasks/completed",
            "results/success",
            "results/errors", 
            "cache",
            "logs",
            "backup"
        ]
        
        try:
            logger.info(f"Initializing bridge directory structure: {self.bridge_root}")
            
            for dir_path in dirs_to_create:
                full_path = self.bridge_root / dir_path
                full_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {dir_path}")
            
            # 初期設定ファイルの作成
            self._create_initial_config()
            
            self.initialized = True
            logger.info("Bridge structure initialization completed successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize bridge structure: {str(e)}"
            logger.error(error_msg)
            raise FileSystemError(error_msg, str(e))
    
    def _create_initial_config(self) -> None:
        """初期設定ファイルの作成"""
        config_dir = self.bridge_root / "config"
        
        # Bridge設定ファイル
        bridge_config = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "settings": {
                "auto_cleanup": True,
                "max_task_retention_days": 30,
                "max_cache_size_mb": 100,
                "log_level": "INFO"
            },
            "directories": {
                "tasks": "tasks",
                "results": "results", 
                "cache": "cache",
                "logs": "logs",
                "backup": "backup"
            }
        }
        
        config_file = config_dir / "bridge_config.json"
        if not config_file.exists():
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(bridge_config, f, ensure_ascii=False, indent=2)
            logger.debug(f"Created initial bridge config: {config_file}")
    
    def save_task_file(self, task_content: str, project_id: str, 
                       task_type: str = "general") -> Path:
        """
        タスクファイルの保存
        
        Args:
            task_content: タスクの内容（Markdown形式）
            project_id: プロジェクトID
            task_type: タスクタイプ
            
        Returns:
            保存されたタスクファイルのパス
            
        Raises:
            FileSystemError: ファイル保存に失敗した場合
            ValidationError: タスク内容が無効な場合
        """
        if not task_content.strip():
            raise ValidationError("Task content cannot be empty")
        
        if not project_id.strip():
            raise ValidationError("Project ID cannot be empty")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{project_id}_{task_type}_{timestamp}.md"
            task_file = self.bridge_root / "tasks" / "pending" / filename
            
            # ディレクトリが存在しない場合は作成
            task_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(task_content)
            
            logger.info(f"Task file saved: {task_file}")
            return task_file
            
        except Exception as e:
            error_msg = f"Failed to save task file: {str(e)}"
            logger.error(error_msg)
            raise FileSystemError(error_msg, str(e))
    
    def list_pending_tasks(self) -> List[Dict[str, Union[str, Path]]]:
        """
        未処理タスクの一覧を取得
        
        Returns:
            タスク情報の辞書リスト
        """
        pending_dir = self.bridge_root / "tasks" / "pending"
        if not pending_dir.exists():
            return []
        
        tasks = []
        try:
            for task_file in pending_dir.glob("*.md"):
                # ファイル名からメタデータを抽出
                name_parts = task_file.stem.split("_")
                if len(name_parts) >= 3:
                    project_id = name_parts[0]
                    task_type = name_parts[1]
                    timestamp = "_".join(name_parts[2:])
                else:
                    project_id = "unknown"
                    task_type = "general"
                    timestamp = task_file.stem
                
                task_info = {
                    "file_path": task_file,
                    "project_id": project_id,
                    "task_type": task_type,
                    "timestamp": timestamp,
                    "created_at": datetime.fromtimestamp(task_file.stat().st_mtime).isoformat()
                }
                tasks.append(task_info)
            
            # 作成日時順でソート（新しい順）
            tasks.sort(key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing pending tasks: {e}")
        
        return tasks
    
    def move_task_to_processing(self, task_file: Path) -> Path:
        """
        タスクを処理中ディレクトリに移動
        
        Args:
            task_file: 移動するタスクファイル
            
        Returns:
            移動後のファイルパス
            
        Raises:
            FileSystemError: ファイル移動に失敗した場合
        """
        try:
            processing_dir = self.bridge_root / "tasks" / "processing"
            processing_dir.mkdir(parents=True, exist_ok=True)
            
            new_path = processing_dir / task_file.name
            task_file.rename(new_path)
            
            logger.info(f"Task moved to processing: {new_path}")
            return new_path
            
        except Exception as e:
            error_msg = f"Failed to move task to processing: {str(e)}"
            logger.error(error_msg)
            raise FileSystemError(error_msg, str(e))
    
    def save_task_result(self, task_file: Path, result_content: str, 
                        success: bool = True) -> Path:
        """
        タスク実行結果の保存
        
        Args:
            task_file: 元のタスクファイル
            result_content: 実行結果の内容
            success: 実行が成功したかどうか
            
        Returns:
            保存された結果ファイルのパス
            
        Raises:
            FileSystemError: ファイル保存に失敗した場合
        """
        try:
            result_dir = self.bridge_root / "results" / ("success" if success else "errors")
            result_dir.mkdir(parents=True, exist_ok=True)
            
            # 結果ファイル名の生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_filename = f"result_{task_file.stem}_{timestamp}.md"
            result_file = result_dir / result_filename
            
            # 結果内容の生成
            result_header = f"""# Task Result
## Original Task: {task_file.name}
## Status: {'SUCCESS' if success else 'ERROR'}
## Completed At: {datetime.now().isoformat()}

---

"""
            
            full_content = result_header + result_content
            
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            # 完了タスクディレクトリに移動
            completed_dir = self.bridge_root / "tasks" / "completed"
            completed_dir.mkdir(parents=True, exist_ok=True)
            completed_file = completed_dir / task_file.name
            task_file.rename(completed_file)
            
            logger.info(f"Task result saved: {result_file}")
            return result_file
            
        except Exception as e:
            error_msg = f"Failed to save task result: {str(e)}"
            logger.error(error_msg)
            raise FileSystemError(error_msg, str(e))
    
    def cleanup_old_files(self, days_threshold: int = 30) -> Dict[str, int]:
        """
        古いファイルのクリーンアップ
        
        Args:
            days_threshold: 削除する日数閾値
            
        Returns:
            削除されたファイル数の辞書
        """
        cleanup_stats = {"completed_tasks": 0, "results": 0, "cache": 0}
        cutoff_time = datetime.now().timestamp() - (days_threshold * 24 * 3600)
        
        # 完了タスクのクリーンアップ
        completed_dir = self.bridge_root / "tasks" / "completed"
        if completed_dir.exists():
            for file_path in completed_dir.glob("*.md"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleanup_stats["completed_tasks"] += 1
        
        # 結果ファイルのクリーンアップ
        for result_type in ["success", "errors"]:
            result_dir = self.bridge_root / "results" / result_type
            if result_dir.exists():
                for file_path in result_dir.glob("*.md"):
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        cleanup_stats["results"] += 1
        
        # キャッシュのクリーンアップ
        cache_dir = self.bridge_root / "cache"
        if cache_dir.exists():
            for file_path in cache_dir.glob("*"):
                if file_path.stat().st_mtime < cutoff_time:
                    if file_path.is_file():
                        file_path.unlink()
                        cleanup_stats["cache"] += 1
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
    
    def get_system_stats(self) -> Dict[str, Union[int, str]]:
        """
        システム統計情報の取得
        
        Returns:
            システム統計情報の辞書
        """
        stats = {
            "bridge_root": str(self.bridge_root),
            "initialized": self.initialized,
            "pending_tasks": len(self.list_pending_tasks()),
            "processing_tasks": 0,
            "completed_tasks": 0,
            "success_results": 0,
            "error_results": 0
        }
        
        try:
            # 処理中タスク数
            processing_dir = self.bridge_root / "tasks" / "processing"
            if processing_dir.exists():
                stats["processing_tasks"] = len(list(processing_dir.glob("*.md")))
            
            # 完了タスク数
            completed_dir = self.bridge_root / "tasks" / "completed"
            if completed_dir.exists():
                stats["completed_tasks"] = len(list(completed_dir.glob("*.md")))
            
            # 結果ファイル数
            success_dir = self.bridge_root / "results" / "success"
            if success_dir.exists():
                stats["success_results"] = len(list(success_dir.glob("*.md")))
            
            error_dir = self.bridge_root / "results" / "errors"
            if error_dir.exists():
                stats["error_results"] = len(list(error_dir.glob("*.md")))
                
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
        
        return stats