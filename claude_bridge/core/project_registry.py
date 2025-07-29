"""
Claude Bridge System - Project Registry
プロジェクト設定の管理とバリデーション
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from ..exceptions import ConfigurationError, ProjectNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class ProjectConfig(BaseModel):
    """プロジェクト設定のデータモデル"""
    
    shortcut: str = Field(..., description="プロジェクトショートカット ([tech]等)")
    name: str = Field(..., description="プロジェクト名")
    path: str = Field(..., description="プロジェクトディレクトリパス")
    claude_md: str = Field(..., description="Claude.mdファイルパス")
    description: str = Field(..., description="プロジェクト説明")
    tech_stack: List[str] = Field(default_factory=list, description="技術スタック")
    dependencies: List[str] = Field(default_factory=list, description="依存プロジェクト")
    related_projects: List[str] = Field(default_factory=list, description="関連プロジェクト")
    integration_points: List[str] = Field(default_factory=list, description="統合ポイント")
    active: bool = Field(default=True, description="プロジェクトが有効かどうか")
    
    @validator('shortcut')
    def validate_shortcut(cls, v):
        """ショートカットのバリデーション"""
        if not v.startswith('[') or not v.endswith(']'):
            raise ValueError("Shortcut must be in format [name]")
        if len(v) < 3:  # [x] minimum
            raise ValueError("Shortcut must have at least one character inside brackets")
        return v
    
    @validator('path')
    def validate_path(cls, v):
        """パスのバリデーション"""
        if not v.strip():
            raise ValueError("Path cannot be empty")
        return v.strip()
    
    @validator('name')
    def validate_name(cls, v):
        """名前のバリデーション"""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class GlobalSettings(BaseModel):
    """グローバル設定のデータモデル"""
    
    auto_load_context: bool = Field(default=True, description="コンテキスト自動読み込み")
    max_context_size: int = Field(default=5000, description="最大コンテキストサイズ")
    cache_duration: int = Field(default=3600, description="キャッシュ保持時間（秒）")
    default_analysis_depth: str = Field(default="detailed", description="デフォルト分析深度")
    
    @validator('max_context_size')
    def validate_context_size(cls, v):
        """コンテキストサイズのバリデーション"""
        if v <= 0:
            raise ValueError("Context size must be positive")
        if v > 50000:
            raise ValueError("Context size cannot exceed 50000")
        return v
    
    @validator('cache_duration')
    def validate_cache_duration(cls, v):
        """キャッシュ持続時間のバリデーション"""
        if v < 0:
            raise ValueError("Cache duration cannot be negative")
        return v


class ProjectRegistry:
    """プロジェクト設定レジストリ
    
    プロジェクト設定の読み込み、保存、バリデーション、
    および設定ファイルの管理を担当する。
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス。Noneの場合はデフォルトパスを使用
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "projects.json"
        
        self.config_path = Path(config_path).resolve()
        self._projects: Dict[str, ProjectConfig] = {}
        self._global_settings: GlobalSettings = GlobalSettings()
        self._config_version: str = "1.0.0"
        self._last_loaded: Optional[datetime] = None
        
        logger.info(f"ProjectRegistry initialized with config: {self.config_path}")
    
    def load_config(self, reload: bool = False) -> Dict[str, Any]:
        """
        設定ファイルの読み込み
        
        Args:
            reload: 強制的に再読み込みするか
            
        Returns:
            読み込まれた設定データ
            
        Raises:
            ConfigurationError: 設定ファイルの読み込みに失敗した場合
            ValidationError: 設定データのバリデーションに失敗した場合
        """
        if self._last_loaded and not reload:
            logger.debug("Config already loaded, skipping reload")
            return self._export_config()
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                logger.info(f"Config loaded from: {self.config_path}")
            else:
                config_data = self._get_default_config()
                logger.info("Using default configuration")
            
            self._validate_and_load_config(config_data)
            self._last_loaded = datetime.now()
            
            return config_data
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in config file: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg, str(e))
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg, str(e))
    
    def _validate_and_load_config(self, config_data: Dict[str, Any]) -> None:
        """設定データのバリデーションと読み込み"""
        try:
            # バージョン情報の確認
            self._config_version = config_data.get("version", "1.0.0")
            
            # グローバル設定の読み込み
            global_settings_data = config_data.get("global_settings", {})
            self._global_settings = GlobalSettings(**global_settings_data)
            
            # プロジェクト設定の読み込み
            projects_data = config_data.get("projects", {})
            self._projects = {}
            
            for project_id, project_data in projects_data.items():
                try:
                    project_config = ProjectConfig(**project_data)
                    self._projects[project_id] = project_config
                    logger.debug(f"Loaded project: {project_id}")
                except Exception as e:
                    logger.warning(f"Failed to load project {project_id}: {e}")
                    continue
            
            logger.info(f"Successfully loaded {len(self._projects)} projects")
            
        except Exception as e:
            error_msg = f"Configuration validation failed: {str(e)}"
            logger.error(error_msg)
            raise ValidationError(error_msg, str(e))
    
    def save_config(self) -> None:
        """
        現在の設定をファイルに保存
        
        Raises:
            ConfigurationError: 設定ファイルの保存に失敗した場合
        """
        try:
            # ディレクトリが存在しない場合は作成
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = self._export_config()
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Config saved to: {self.config_path}")
            
        except Exception as e:
            error_msg = f"Failed to save configuration: {str(e)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg, str(e))
    
    def _export_config(self) -> Dict[str, Any]:
        """設定データのエクスポート"""
        return {
            "version": self._config_version,
            "last_updated": datetime.now().isoformat(),
            "projects": {
                project_id: project_config.dict()
                for project_id, project_config in self._projects.items()
            },
            "global_settings": self._global_settings.dict()
        }
    
    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """
        プロジェクト設定の取得
        
        Args:
            project_id: プロジェクトID
            
        Returns:
            プロジェクト設定。見つからない場合はNone
        """
        if not self._projects:
            self.load_config()
        
        return self._projects.get(project_id)
    
    def get_project_by_shortcut(self, shortcut: str) -> Optional[tuple[str, ProjectConfig]]:
        """
        ショートカットによるプロジェクト設定の取得
        
        Args:
            shortcut: プロジェクトショートカット
            
        Returns:
            (project_id, ProjectConfig)のタプル。見つからない場合はNone
        """
        if not self._projects:
            self.load_config()
        
        for project_id, project_config in self._projects.items():
            if project_config.shortcut == shortcut:
                return (project_id, project_config)
        
        return None
    
    def list_projects(self, active_only: bool = True) -> Dict[str, ProjectConfig]:
        """
        プロジェクト一覧の取得
        
        Args:
            active_only: アクティブなプロジェクトのみ取得するか
            
        Returns:
            プロジェクト設定の辞書
        """
        if not self._projects:
            self.load_config()
        
        if active_only:
            return {
                project_id: project_config
                for project_id, project_config in self._projects.items()
                if project_config.active
            }
        else:
            return self._projects.copy()
    
    def add_project(self, project_id: str, project_config: ProjectConfig) -> None:
        """
        プロジェクトの追加
        
        Args:
            project_id: プロジェクトID
            project_config: プロジェクト設定
            
        Raises:
            ValidationError: プロジェクトIDが既に存在する場合
        """
        if project_id in self._projects:
            raise ValidationError(f"Project already exists: {project_id}")
        
        self._projects[project_id] = project_config
        logger.info(f"Project added: {project_id}")
    
    def update_project(self, project_id: str, project_config: ProjectConfig) -> None:
        """
        プロジェクトの更新
        
        Args:
            project_id: プロジェクトID
            project_config: 更新するプロジェクト設定
            
        Raises:
            ProjectNotFoundError: プロジェクトが見つからない場合
        """
        if project_id not in self._projects:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        
        self._projects[project_id] = project_config
        logger.info(f"Project updated: {project_id}")
    
    def remove_project(self, project_id: str) -> None:
        """
        プロジェクトの削除
        
        Args:
            project_id: プロジェクトID
            
        Raises:
            ProjectNotFoundError: プロジェクトが見つからない場合
        """
        if project_id not in self._projects:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        
        del self._projects[project_id]
        logger.info(f"Project removed: {project_id}")
    
    def get_global_settings(self) -> GlobalSettings:
        """
        グローバル設定の取得
        
        Returns:
            グローバル設定
        """
        if not self._global_settings:
            self.load_config()
        
        return self._global_settings
    
    def update_global_settings(self, settings: GlobalSettings) -> None:
        """
        グローバル設定の更新
        
        Args:
            settings: 新しいグローバル設定
        """
        self._global_settings = settings
        logger.info("Global settings updated")
    
    def find_related_projects(self, project_id: str) -> List[tuple[str, ProjectConfig]]:
        """
        関連プロジェクトの検索
        
        Args:
            project_id: 検索対象のプロジェクトID
            
        Returns:
            関連プロジェクトのリスト
        """
        if not self._projects:
            self.load_config()
        
        project_config = self._projects.get(project_id)
        if not project_config:
            return []
        
        related = []
        
        # 明示的に関連付けられたプロジェクト
        for related_id in project_config.related_projects:
            if related_id in self._projects:
                related.append((related_id, self._projects[related_id]))
        
        # 依存プロジェクト
        for dep_id in project_config.dependencies:
            if dep_id in self._projects:
                related.append((dep_id, self._projects[dep_id]))
        
        # このプロジェクトに依存している他のプロジェクト
        for other_id, other_config in self._projects.items():
            if other_id != project_id and project_id in other_config.dependencies:
                related.append((other_id, other_config))
        
        # 重複を除去
        seen = set()
        unique_related = []
        for rel_id, rel_config in related:
            if rel_id not in seen:
                seen.add(rel_id)
                unique_related.append((rel_id, rel_config))
        
        return unique_related
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定の取得"""
        return {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "projects": {
                "tech": {
                    "shortcut": "[tech]",
                    "name": "メインテックプロジェクト",
                    "path": "~/projects/tech",
                    "claude_md": "~/projects/tech/Claude.md",
                    "description": "メインのテクノロジープロジェクト",
                    "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
                    "dependencies": [],
                    "related_projects": ["techzip"],
                    "integration_points": [
                        "共通認証システム",
                        "データベース共有",
                        "API エンドポイント統合"
                    ],
                    "active": True
                },
                "techzip": {
                    "shortcut": "[techzip]",
                    "name": "ZIP処理ライブラリ",
                    "path": "~/projects/techzip",
                    "claude_md": "~/projects/techzip/Claude.md",
                    "description": "ZIP ファイル処理専用ライブラリ",
                    "tech_stack": ["Python", "zipfile", "pathlib"],
                    "dependencies": ["tech"],
                    "related_projects": ["tech"],
                    "integration_points": [
                        "techプロジェクトのファイル処理モジュール",
                        "共通のエラーハンドリング"
                    ],
                    "active": True
                }
            },
            "global_settings": {
                "auto_load_context": True,
                "max_context_size": 5000,
                "cache_duration": 3600,
                "default_analysis_depth": "detailed"
            }
        }
    
    def validate_config_file(self) -> Dict[str, Any]:
        """
        設定ファイルのバリデーション
        
        Returns:
            バリデーション結果の辞書
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "project_count": 0,
            "active_projects": 0
        }
        
        try:
            self.load_config(reload=True)
            validation_result["project_count"] = len(self._projects)
            validation_result["active_projects"] = len([
                p for p in self._projects.values() if p.active
            ])
            
            # プロジェクト間の依存関係チェック
            for project_id, project_config in self._projects.items():
                for dep_id in project_config.dependencies:
                    if dep_id not in self._projects:
                        validation_result["warnings"].append(
                            f"Project {project_id} depends on non-existent project: {dep_id}"
                        )
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(str(e))
        
        return validation_result