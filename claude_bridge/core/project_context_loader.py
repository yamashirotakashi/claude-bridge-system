"""
Claude Bridge System - Project Context Loader
プロジェクトコンテキストの検出・読み込み・生成
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .project_registry import ProjectRegistry, ProjectConfig
from ..exceptions import ProjectNotFoundError, FileSystemError

logger = logging.getLogger(__name__)


class ProjectContextLoader:
    """プロジェクトコンテキストの検出・読み込みクラス
    
    Claude Codeのプロジェクトショートカット（[techzip]等）を検出し、
    関連する詳細情報を自動的に読み込んでコンテキストとして提供する。
    """
    
    def __init__(self, registry: Optional[ProjectRegistry] = None):
        """
        初期化
        
        Args:
            registry: プロジェクトレジストリ。Noneの場合は新規作成
        """
        self.registry = registry if registry else ProjectRegistry()
        self.context_cache: Dict[str, Dict] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        logger.info("ProjectContextLoader initialized")
    
    def detect_project_shortcuts(self, message: str) -> List[str]:
        """
        メッセージからプロジェクトショートカットを検出
        
        Args:
            message: ユーザーからの入力メッセージ
            
        Returns:
            検出されたプロジェクトIDのリスト
        """
        # ショートカットパターンの検出（例: [tech], [techzip]）
        pattern = r'\[(\w+)\]'
        shortcuts = re.findall(pattern, message)
        
        valid_project_ids = []
        projects = self.registry.list_projects()
        
        for shortcut in shortcuts:
            shortcut_with_brackets = f"[{shortcut}]"
            
            # ショートカットに対応するプロジェクトを検索
            for project_id, project_config in projects.items():
                if project_config.shortcut == shortcut_with_brackets:
                    valid_project_ids.append(project_id)
                    logger.debug(f"Detected project: {project_id} ({shortcut_with_brackets})")
                    break
        
        # 重複を除去
        unique_project_ids = list(dict.fromkeys(valid_project_ids))
        
        logger.info(f"Detected {len(unique_project_ids)} projects: {unique_project_ids}")
        return unique_project_ids
    
    def load_project_context(self, project_id: str, use_cache: bool = True) -> Dict:
        """
        指定されたプロジェクトの詳細コンテキストを読み込み
        
        Args:
            project_id: プロジェクトID
            use_cache: キャッシュを使用するか
            
        Returns:
            プロジェクトコンテキストの辞書
            
        Raises:
            ProjectNotFoundError: プロジェクトが見つからない場合
        """
        # キャッシュチェック
        if use_cache and self._is_cache_valid(project_id):
            logger.debug(f"Using cached context for project: {project_id}")
            return self.context_cache[project_id]
        
        project_config = self.registry.get_project(project_id)
        if not project_config:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        
        context = {
            "project_id": project_id,
            "basic_info": self._extract_basic_info(project_config),
            "claude_md_content": self._read_claude_md(project_config.claude_md),
            "project_structure": self._analyze_project_structure(project_config.path),
            "related_projects": self._get_related_contexts(project_id),
            "integration_analysis": self._analyze_integration_points(project_config),
            "last_loaded": datetime.now().isoformat()
        }
        
        # キャッシュに保存
        self.context_cache[project_id] = context
        self.cache_timestamps[project_id] = datetime.now()
        
        logger.info(f"Loaded context for project: {project_id}")
        return context
    
    def _is_cache_valid(self, project_id: str) -> bool:
        """キャッシュの有効性をチェック"""
        if project_id not in self.context_cache:
            return False
        
        if project_id not in self.cache_timestamps:
            return False
        
        # キャッシュの有効期限（デフォルト1時間）
        global_settings = self.registry.get_global_settings()
        cache_duration = global_settings.cache_duration
        
        cache_age = (datetime.now() - self.cache_timestamps[project_id]).seconds
        return cache_age < cache_duration
    
    def _extract_basic_info(self, project_config: ProjectConfig) -> Dict:
        """プロジェクト基本情報の抽出"""
        return {
            "name": project_config.name,
            "shortcut": project_config.shortcut,
            "description": project_config.description,
            "tech_stack": project_config.tech_stack,
            "path": project_config.path,
            "active": project_config.active,
            "dependencies": project_config.dependencies,
            "related_projects": project_config.related_projects,
            "integration_points": project_config.integration_points
        }
    
    def _read_claude_md(self, claude_md_path: str) -> Dict[str, str]:
        """Claude.mdファイルの内容を読み込み"""
        result = {
            "status": "success",
            "content": "",
            "summary": "",
            "error": None
        }
        
        if not claude_md_path.strip():
            result["status"] = "error"
            result["error"] = "Claude.mdファイルのパスが設定されていません"
            return result
        
        try:
            path = Path(claude_md_path).expanduser().resolve()
            if path.exists() and path.is_file():
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                result["content"] = content
                result["summary"] = self._summarize_claude_md(content)
                
                logger.debug(f"Successfully read Claude.md: {path}")
            else:
                result["status"] = "error"
                result["error"] = f"Claude.mdファイルが見つかりません: {claude_md_path}"
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = f"Claude.mdファイルの読み込みに失敗: {str(e)}"
            logger.error(f"Failed to read Claude.md {claude_md_path}: {e}")
        
        return result
    
    def _summarize_claude_md(self, content: str) -> str:
        """Claude.mdの内容を要約"""
        if not content.strip():
            return "空のファイル"
        
        lines = content.split('\\n')
        summary_parts = []
        
        # ヘッダーを抽出
        for line in lines[:20]:  # 最初の20行をチェック
            line = line.strip()
            if line.startswith('#'):
                summary_parts.append(line)
                if len(summary_parts) >= 3:  # 最大3つのヘッダー
                    break
        
        if summary_parts:
            return ' / '.join(summary_parts)
        else:
            # ヘッダーがない場合は最初の100文字
            return content[:100].replace('\\n', ' ') + '...'
    
    def _analyze_project_structure(self, project_path: str) -> Dict:
        """プロジェクト構造の基本分析"""
        result = {
            "status": "success",
            "main_files": [],
            "directories": [],
            "python_files": [],
            "config_files": [],
            "total_files": 0,
            "error": None
        }
        
        if not project_path.strip():
            result["status"] = "error"
            result["error"] = "プロジェクトパスが設定されていません"
            return result
        
        try:
            path = Path(project_path).expanduser().resolve()
            if not path.exists():
                result["status"] = "error"
                result["error"] = f"プロジェクトパスが見つかりません: {project_path}"
                return result
            
            if not path.is_dir():
                result["status"] = "error"
                result["error"] = f"指定されたパスはディレクトリではありません: {project_path}"
                return result
            
            # ファイル・ディレクトリの分析
            file_count = 0
            
            for item in path.iterdir():
                if item.is_file():
                    file_count += 1
                    
                    # Pythonファイル
                    if item.suffix == '.py':
                        result["python_files"].append(item.name)
                    
                    # 主要ファイル
                    if item.name in ['README.md', 'requirements.txt', 'setup.py', 
                                   'pyproject.toml', 'Pipfile', 'poetry.lock', 'CLAUDE.md']:
                        result["main_files"].append(item.name)
                    
                    # 設定ファイル
                    if item.suffix in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg']:
                        result["config_files"].append(item.name)
                        
                elif item.is_dir() and not item.name.startswith('.'):
                    result["directories"].append(item.name)
            
            result["total_files"] = file_count
            
            logger.debug(f"Analyzed project structure: {path}")
            
        except Exception as e:
            result["status"] = "error"  
            result["error"] = f"プロジェクト構造の分析に失敗: {str(e)}"
            logger.error(f"Failed to analyze project structure {project_path}: {e}")
        
        return result
    
    def _get_related_contexts(self, project_id: str) -> Dict[str, Dict]:
        """関連プロジェクトの基本情報を取得"""
        related = {}
        
        try:
            related_projects = self.registry.find_related_projects(project_id)
            
            for related_id, related_config in related_projects:
                related[related_id] = {
                    "name": related_config.name,
                    "shortcut": related_config.shortcut,
                    "description": related_config.description,
                    "tech_stack": related_config.tech_stack,
                    "relationship_type": self._determine_relationship_type(
                        project_id, related_id, related_config
                    )
                }
                
        except Exception as e:
            logger.error(f"Error getting related contexts for {project_id}: {e}")
        
        return related
    
    def _determine_relationship_type(self, project_id: str, related_id: str, 
                                   related_config: ProjectConfig) -> str:
        """プロジェクト間の関係タイプを判定"""
        project_config = self.registry.get_project(project_id)
        if not project_config:
            return "unknown"
        
        if related_id in project_config.dependencies:
            return "dependency"
        elif project_id in related_config.dependencies:
            return "dependent"
        elif related_id in project_config.related_projects:
            return "related"
        else:
            return "indirect"
    
    def _analyze_integration_points(self, project_config: ProjectConfig) -> Dict:
        """統合ポイントの分析"""
        return {
            "explicit_points": project_config.integration_points,
            "dependency_based": [
                f"{dep}との依存関係統合" 
                for dep in project_config.dependencies
            ],
            "tech_stack_overlap": self._find_tech_stack_overlaps(project_config),
            "suggested_integrations": self._suggest_integrations(project_config)
        }
    
    def _find_tech_stack_overlaps(self, project_config: ProjectConfig) -> List[str]:
        """技術スタックの重複を検出"""
        overlaps = []
        
        try:
            for related_id in project_config.related_projects:
                related_config = self.registry.get_project(related_id)
                if related_config:
                    common_tech = set(project_config.tech_stack) & set(related_config.tech_stack)
                    if common_tech:
                        overlaps.append(f"{related_id}: {', '.join(common_tech)}")
                        
        except Exception as e:
            logger.error(f"Error finding tech stack overlaps: {e}")
        
        return overlaps
    
    def _suggest_integrations(self, project_config: ProjectConfig) -> List[str]:
        """統合提案の生成"""
        suggestions = []
        
        # 共通の技術スタックに基づく提案
        if "Python" in project_config.tech_stack:
            suggestions.append("共通Pythonライブラリの利用")
        
        if "API" in project_config.description or "FastAPI" in project_config.tech_stack:
            suggestions.append("API エンドポイントの統合")
        
        if "データベース" in project_config.description or any(
            db in project_config.tech_stack 
            for db in ["PostgreSQL", "MySQL", "SQLite", "MongoDB"]
        ):
            suggestions.append("データベーススキーマの共有")
        
        return suggestions
    
    def generate_context_summary(self, project_ids: List[str]) -> str:
        """
        複数プロジェクトの統合コンテキストサマリを生成
        
        Args:
            project_ids: プロジェクトIDのリスト
            
        Returns:
            統合されたコンテキストサマリ（Markdown形式）
        """
        if not project_ids:
            return "## プロジェクト情報\\n\\n検出されたプロジェクトはありません。"
        
        summary_parts = ["## 検出されたプロジェクト情報\\n"]
        
        for project_id in project_ids:
            try:
                context = self.load_project_context(project_id)
                basic_info = context.get("basic_info", {})
                
                # プロジェクト基本情報
                summary_parts.append(f"### {basic_info.get('name', project_id)} {basic_info.get('shortcut', '')}")
                summary_parts.append(f"**概要**: {basic_info.get('description', 'N/A')}")
                summary_parts.append(f"**技術スタック**: {', '.join(basic_info.get('tech_stack', []))}")
                
                # Claude.md要約
                claude_md = context.get("claude_md_content", {})
                if claude_md.get("status") == "success" and claude_md.get("summary"):
                    summary_parts.append(f"**プロジェクト詳細**: {claude_md['summary']}")
                
                # プロジェクト構造
                structure = context.get("project_structure", {})
                if structure.get("status") == "success":
                    py_count = len(structure.get("python_files", []))
                    dir_count = len(structure.get("directories", []))
                    summary_parts.append(
                        f"**構成**: {py_count}個のPythonファイル、{dir_count}個のディレクトリ"
                    )
                
                # 関連プロジェクト
                related = context.get("related_projects", {})
                if related:
                    related_names = [info.get("name", rid) for rid, info in related.items()]
                    summary_parts.append(f"**関連プロジェクト**: {', '.join(related_names)}")
                
                summary_parts.append("")
                
            except Exception as e:
                logger.error(f"Error generating summary for project {project_id}: {e}")
                summary_parts.append(f"### {project_id}")
                summary_parts.append(f"**エラー**: プロジェクト情報の読み込みに失敗しました")
                summary_parts.append("")
        
        # プロジェクト間の関係性分析
        if len(project_ids) > 1:
            summary_parts.append("## プロジェクト間の関係性")
            relationship_analysis = self._analyze_multi_project_relationships(project_ids)
            summary_parts.extend(relationship_analysis)
        
        return "\\n".join(summary_parts)
    
    def _analyze_multi_project_relationships(self, project_ids: List[str]) -> List[str]:
        """複数プロジェクト間の関係性を分析"""
        analysis = []
        
        try:
            # 依存関係の分析
            dependencies = []
            for project_id in project_ids:
                context = self.load_project_context(project_id)
                basic_info = context.get("basic_info", {})
                project_deps = basic_info.get("dependencies", [])
                
                for dep in project_deps:
                    if dep in project_ids:
                        dependencies.append(f"{project_id} → {dep}")
            
            if dependencies:
                analysis.append("**依存関係**:")
                for dep in dependencies:
                    analysis.append(f"- {dep}")
                analysis.append("")
            
            # 統合ポイントの分析
            integration_points = []
            for project_id in project_ids:
                context = self.load_project_context(project_id)
                integration = context.get("integration_analysis", {})
                points = integration.get("explicit_points", [])
                
                if points:
                    integration_points.append(f"**{project_id}の統合ポイント**:")
                    for point in points:
                        integration_points.append(f"- {point}")
            
            if integration_points:
                analysis.extend(integration_points)
                analysis.append("")
            
            # 技術スタックの重複
            tech_overlaps = self._find_cross_project_tech_overlaps(project_ids)
            if tech_overlaps:
                analysis.append("**共通技術**:")
                for overlap in tech_overlaps:
                    analysis.append(f"- {overlap}")
                analysis.append("")
                
        except Exception as e:
            logger.error(f"Error analyzing multi-project relationships: {e}")
            analysis.append("**関係性分析エラー**: 分析に失敗しました")
        
        return analysis
    
    def _find_cross_project_tech_overlaps(self, project_ids: List[str]) -> List[str]:
        """プロジェクト間の技術スタック重複を検出"""
        tech_counts = {}
        project_techs = {}
        
        # 各プロジェクトの技術スタックを収集
        for project_id in project_ids:
            try:
                context = self.load_project_context(project_id)
                basic_info = context.get("basic_info", {})
                tech_stack = basic_info.get("tech_stack", [])
                project_techs[project_id] = tech_stack
                
                for tech in tech_stack:
                    tech_counts[tech] = tech_counts.get(tech, 0) + 1
                    
            except Exception:
                continue
        
        # 複数プロジェクトで使用されている技術を特定
        overlaps = []
        for tech, count in tech_counts.items():
            if count > 1:
                using_projects = [
                    project_id for project_id, techs in project_techs.items()
                    if tech in techs
                ]
                overlaps.append(f"{tech} (使用: {', '.join(using_projects)})")
        
        return overlaps
    
    def clear_cache(self, project_id: Optional[str] = None) -> None:
        """
        キャッシュのクリア
        
        Args:
            project_id: 特定のプロジェクトのキャッシュをクリア。Noneの場合は全キャッシュクリア
        """
        if project_id:
            if project_id in self.context_cache:
                del self.context_cache[project_id]
            if project_id in self.cache_timestamps:
                del self.cache_timestamps[project_id]
            logger.info(f"Cache cleared for project: {project_id}")
        else:
            self.context_cache.clear()
            self.cache_timestamps.clear()
            logger.info("All cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Union[int, List[str]]]:
        """
        キャッシュ統計情報の取得
        
        Returns:
            キャッシュ統計情報
        """
        return {
            "cached_projects": len(self.context_cache),
            "project_list": list(self.context_cache.keys()),
            "oldest_cache": min(self.cache_timestamps.values()).isoformat() 
                          if self.cache_timestamps else None,
            "newest_cache": max(self.cache_timestamps.values()).isoformat()
                          if self.cache_timestamps else None
        }