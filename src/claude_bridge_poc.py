# Proof of Concept: Claude Bridge System
# Claude Bridge System - 概念実証版

from typing import Dict, List, Optional
import re
import json
from pathlib import Path
from datetime import datetime

class ProjectContextLoader:
    """
    プロジェクトコンテキストの検出・読み込みを担当するメインクラス
    Claude Bridge Systemの概念実証版実装
    """
    
    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: プロジェクト設定ファイルのパス
        """
        if config_path is None:
            # 制限環境を考慮したパス設定
            config_path = Path(__file__).parent.parent / "config" / "projects.json"
        
        self.config_path = Path(config_path)
        self.projects = self._load_projects()
        self.context_cache = {}
    
    def _load_projects(self) -> Dict:
        """プロジェクト設定ファイルを読み込み"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # デフォルト設定を返す
                return self._get_default_config()
        except Exception as e:
            print(f"Warning: Failed to load projects config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """デフォルトプロジェクト設定"""
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
                    "dependencies": ["common-lib"],
                    "related_projects": ["techzip"],
                    "integration_points": [
                        "共通認証システム",
                        "データベース共有",
                        "API エンドポイント統合"
                    ]
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
                    ]
                }
            },
            "global_settings": {
                "auto_load_context": True,
                "max_context_size": 5000,
                "cache_duration": 3600,
                "default_analysis_depth": "detailed"
            }
        }
    
    def detect_project_shortcuts(self, message: str) -> List[str]:
        """
        メッセージからプロジェクトショートカットを検出
        
        Args:
            message: ユーザーからの入力メッセージ
            
        Returns:
            検出されたプロジェクトIDのリスト
        """
        pattern = r'\[(\w+)\]'
        shortcuts = re.findall(pattern, message)
        
        # 有効なプロジェクトショートカットのみを返す
        valid_shortcuts = []
        for shortcut in shortcuts:
            for project_id, project_info in self.projects.get("projects", {}).items():
                if project_info.get("shortcut") == f"[{shortcut}]":
                    valid_shortcuts.append(project_id)
                    break
        
        return valid_shortcuts
    
    def load_project_context(self, project_id: str) -> Dict:
        """指定されたプロジェクトの詳細コンテキストを読み込み"""
        project = self.projects.get("projects", {}).get(project_id)
        if not project:
            return {}
        
        context = {
            "basic_info": project,
            "claude_md_content": self._read_claude_md(project.get("claude_md")),
            "project_structure": self._analyze_project_structure(project.get("path")),
            "related_projects": self._get_related_contexts(project.get("related_projects", []))
        }
        
        return context
    
    def _read_claude_md(self, claude_md_path: str) -> str:
        """Claude.mdファイルの内容を読み込み"""
        if not claude_md_path:
            return "Claude.mdファイルのパスが設定されていません"
        
        try:
            path = Path(claude_md_path).expanduser()
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return f"Claude.mdファイルが見つかりません: {claude_md_path}"
        except Exception as e:
            return f"Claude.mdファイルの読み込みに失敗: {str(e)}"
    
    def _analyze_project_structure(self, project_path: str) -> Dict:
        """プロジェクト構造の基本分析"""
        if not project_path:
            return {"error": "プロジェクトパスが設定されていません"}
        
        try:
            path = Path(project_path).expanduser()
            if not path.exists():
                return {"error": f"プロジェクトパスが見つかりません: {project_path}"}
            
            structure = {
                "main_files": [],
                "directories": [],
                "python_files": []
            }
            
            # ファイル・ディレクトリの分析
            for item in path.iterdir():
                if item.is_file():
                    if item.suffix == '.py':
                        structure["python_files"].append(item.name)
                    if item.name in ['README.md', 'requirements.txt', 'setup.py', 'pyproject.toml']:
                        structure["main_files"].append(item.name)
                elif item.is_dir() and not item.name.startswith('.'):
                    structure["directories"].append(item.name)
            
            return structure
        except Exception as e:
            return {"error": f"プロジェクト構造の分析に失敗: {str(e)}"}
    
    def _get_related_contexts(self, related_project_ids: List[str]) -> Dict:
        """関連プロジェクトの基本情報を取得"""
        related = {}
        for project_id in related_project_ids:
            if project_id in self.projects.get("projects", {}):
                project_info = self.projects["projects"][project_id]
                related[project_id] = {
                    "name": project_info.get("name"),
                    "description": project_info.get("description"),
                    "tech_stack": project_info.get("tech_stack", []),
                    "shortcut": project_info.get("shortcut")
                }
        return related
    
    def generate_context_summary(self, project_ids: List[str]) -> str:
        """複数プロジェクトの統合コンテキストサマリを生成"""
        if not project_ids:
            return ""
        
        summary_parts = []
        summary_parts.append("## 検出されたプロジェクト情報\n")
        
        for project_id in project_ids:
            context = self.load_project_context(project_id)
            basic_info = context.get("basic_info", {})
            
            summary_parts.append(f"### {basic_info.get('name', project_id)} {basic_info.get('shortcut', '')}")
            summary_parts.append(f"**概要**: {basic_info.get('description', 'N/A')}")
            summary_parts.append(f"**技術スタック**: {', '.join(basic_info.get('tech_stack', []))}")
            
            # Claude.md内容の要約
            claude_md_content = context.get("claude_md_content", "")
            if claude_md_content and not claude_md_content.startswith("Claude.mdファイル"):
                summary_parts.append(f"**プロジェクト詳細**: {claude_md_content[:300]}...")
            
            # プロジェクト構造
            structure = context.get("project_structure", {})
            if not structure.get("error"):
                summary_parts.append(f"**ファイル構成**: {len(structure.get('python_files', []))}個のPythonファイル、{len(structure.get('directories', []))}個のディレクトリ")
            
            if basic_info.get("related_projects"):
                summary_parts.append(f"**関連プロジェクト**: {', '.join(basic_info['related_projects'])}")
            
            summary_parts.append("")
        
        # プロジェクト間の関係性分析
        if len(project_ids) > 1:
            summary_parts.append("## プロジェクト間の関係性")
            for project_id in project_ids:
                context = self.load_project_context(project_id)
                integration_points = context.get("basic_info", {}).get("integration_points", [])
                if integration_points:
                    summary_parts.append(f"**{project_id}の統合ポイント**:")
                    for point in integration_points:
                        summary_parts.append(f"- {point}")
            summary_parts.append("")
        
        return "\n".join(summary_parts)


class TaskGenerator:
    """タスク生成の概念実証クラス"""
    
    def __init__(self):
        self.task_patterns = {
            "implement": ["実装", "開発", "作成", "追加", "構築"],
            "analyze": ["分析", "検討", "調査", "評価", "確認"],
            "test": ["テスト", "検証", "試験"],
            "refactor": ["リファクタリング", "改善", "最適化"],
            "document": ["ドキュメント", "文書化", "説明"]
        }
    
    def analyze_conversation(self, content: str, project_context: Dict) -> Dict:
        """会話内容の分析"""
        analysis = {
            "task_type": self._determine_task_type(content),
            "complexity": self._estimate_complexity(content),
            "mentioned_projects": project_context.get("project_ids", []),
            "key_requirements": self._extract_requirements(content),
            "estimated_effort": 30  # デフォルト30分
        }
        
        return analysis
    
    def _determine_task_type(self, content: str) -> str:
        """タスクタイプの判定"""
        for task_type, keywords in self.task_patterns.items():
            if any(keyword in content for keyword in keywords):
                return task_type
        return "analyze"  # デフォルト
    
    def _estimate_complexity(self, content: str) -> str:
        """複雑度の推定"""
        if any(word in content for word in ["簡単", "単純", "基本"]):
            return "simple"
        elif any(word in content for word in ["複雑", "高度", "統合"]):
            return "complex"
        else:
            return "medium"
    
    def _extract_requirements(self, content: str) -> List[str]:
        """要件の抽出（簡易版）"""
        requirements = []
        
        # 基本的なキーワードベースの抽出
        if "認証" in content:
            requirements.append("認証システムの実装")
        if "API" in content:
            requirements.append("API設計・実装")
        if "データベース" in content:
            requirements.append("データベース設計")
        if "テスト" in content:
            requirements.append("テストケース作成")
        if "連携" in content:
            requirements.append("システム間連携の実装")
        if "ファイル処理" in content:
            requirements.append("ファイル処理機能の実装")
        
        return requirements if requirements else ["一般的な開発タスク"]
    
    def generate_task_markdown(self, analysis: Dict, project_id: str) -> str:
        """タスクマークダウンの生成"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        markdown = f"""## CLAUDE_TASK: {analysis['task_type']}
### Project
{project_id}

### Context
{analysis.get('context', 'タスクコンテキスト')}

### Task
以下の要件を満たす実装を行ってください：
"""
        
        for req in analysis['key_requirements']:
            markdown += f"- {req}\n"
        
        markdown += f"""
### Files
- 実装対象ファイルを特定してください

### Priority
{self._determine_priority(analysis['complexity'])}

### Metadata
- created_at: {datetime.now().isoformat()}
- task_id: {task_id}
- complexity: {analysis['complexity']}
- estimated_time: {analysis['estimated_effort']}
---"""
        
        return markdown
    
    def _determine_priority(self, complexity: str) -> str:
        """優先度の決定"""
        priority_map = {
            "simple": "low",
            "medium": "medium", 
            "complex": "high"
        }
        return priority_map.get(complexity, "medium")


class BridgeFileSystem:
    """Bridge ファイルシステムの概念実証クラス"""
    
    def __init__(self, bridge_root: str = None):
        if bridge_root is None:
            # 概念実証用のパス
            bridge_root = Path(__file__).parent.parent / "bridge_data"
        
        self.bridge_root = Path(bridge_root)
    
    def initialize_structure(self):
        """必要なディレクトリ構造を初期化"""
        dirs_to_create = [
            "config",
            "tasks/pending",
            "tasks/processing", 
            "tasks/completed",
            "results/success",
            "results/errors",
            "cache",
            "logs"
        ]
        
        print(f"Bridge ディレクトリ構造を初期化中: {self.bridge_root}")
        
        for dir_path in dirs_to_create:
            full_path = self.bridge_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ 作成: {dir_path}")
        
        # 設定ファイルのテンプレートを作成
        self._create_config_template()
        
        print("✅ 初期化完了！")
    
    def _create_config_template(self):
        """設定ファイルテンプレートの作成"""
        config_dir = self.bridge_root / "config"
        
        # プロジェクト設定テンプレート
        loader = ProjectContextLoader()
        default_config = loader._get_default_config()
        
        config_file = config_dir / "projects.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ 設定テンプレート作成: {config_file}")
    
    def save_task_file(self, task_content: str, project_id: str) -> Path:
        """タスクファイルの保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_file = self.bridge_root / "tasks" / "pending" / f"{project_id}_{timestamp}.md"
        
        with open(task_file, 'w', encoding='utf-8') as f:
            f.write(task_content)
        
        print(f"💾 タスクファイル保存: {task_file}")
        return task_file
    
    def list_pending_tasks(self) -> List[Path]:
        """未処理タスクの一覧"""
        pending_dir = self.bridge_root / "tasks" / "pending"
        if pending_dir.exists():
            return list(pending_dir.glob("*.md"))
        return []


def demo_project_context_loader():
    """ProjectContextLoaderのデモンストレーション"""
    print("=== Project Context Loader デモ ===\n")
    
    # ローダーの初期化
    loader = ProjectContextLoader()
    
    # デモ用メッセージ
    demo_messages = [
        "[tech]プロジェクトについて教えて",
        "[techzip]の現在の実装状況は？",
        "[tech]と[techzip]の連携について検討したい"
    ]
    
    for i, message in enumerate(demo_messages, 1):
        print(f"--- デモ {i}: {message} ---")
        
        # 1. プロジェクトショートカットの検出
        detected_projects = loader.detect_project_shortcuts(message)
        print(f"🔍 検出されたプロジェクト: {detected_projects}")
        
        # 2. コンテキストサマリの生成
        if detected_projects:
            context_summary = loader.generate_context_summary(detected_projects)
            print("📋 生成されたコンテキスト:")
            print(context_summary[:500] + "..." if len(context_summary) > 500 else context_summary)
        else:
            print("❌ プロジェクトショートカットが検出されませんでした")
        
        print("\n" + "="*50 + "\n")


def demo_task_generator():
    """TaskGeneratorのデモンストレーション"""
    print("=== Task Generator デモ ===\n")
    
    generator = TaskGenerator()
    loader = ProjectContextLoader()
    
    # デモシナリオ
    scenarios = [
        {
            "message": "[tech]プロジェクトに認証機能を実装したい",
            "context": "新しい認証システムの実装"
        },
        {
            "message": "[techzip]と[tech]の連携APIを分析してください",
            "context": "プロジェクト間連携の分析"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"--- シナリオ {i}: {scenario['message']} ---")
        
        # プロジェクト検出
        projects = loader.detect_project_shortcuts(scenario['message'])
        
        # 分析実行
        analysis = generator.analyze_conversation(scenario['message'], {
            "project_ids": projects,
            "context": scenario['context']
        })
        
        print(f"📊 分析結果:")
        print(f"  - タスクタイプ: {analysis['task_type']}")
        print(f"  - 複雑度: {analysis['complexity']}")
        print(f"  - 要件: {analysis['key_requirements']}")
        
        # タスクマークダウン生成
        if projects:
            task_md = generator.generate_task_markdown(analysis, projects[0])
            print(f"\n📝 生成されたタスク:")
            print(task_md[:300] + "..." if len(task_md) > 300 else task_md)
        
        print("\n" + "="*50 + "\n")


def integrated_workflow_demo(bridge_fs: BridgeFileSystem):
    """統合ワークフローのデモンストレーション"""
    loader = ProjectContextLoader()
    generator = TaskGenerator()
    
    # 実際のVIBEcodingシナリオ
    scenario = {
        "message": "[tech]プロジェクトと[techzip]プロジェクトの連携機能を実装してください。ファイル処理の共通化を行いたい。",
        "expected_outcome": "両プロジェクトの連携実装タスク"
    }
    
    print("🎯 VIBEcodingワークフローシミュレーション")
    print(f"シナリオ: {scenario['message']}")
    print()
    
    # Step 1: プロジェクト検出
    projects = loader.detect_project_shortcuts(scenario['message'])
    print(f"✅ 検出されたプロジェクト: {projects}")
    
    # Step 2: コンテキスト生成
    context_summary = loader.generate_context_summary(projects)
    print(f"✅ コンテキスト生成完了 ({len(context_summary)}文字)")
    
    # Step 3: タスク分析
    analysis = generator.analyze_conversation(scenario['message'], {
        "project_ids": projects,
        "context": "プロジェクト間連携の実装"
    })
    print(f"✅ タスク分析完了: {analysis['task_type']} ({analysis['complexity']})")
    
    # Step 4: タスクファイル生成・保存
    for project_id in projects:
        task_md = generator.generate_task_markdown(analysis, project_id)
        task_file = bridge_fs.save_task_file(task_md, project_id)
        print(f"✅ タスクファイル生成: {task_file.name}")
    
    # Step 5: 結果確認
    pending_tasks = bridge_fs.list_pending_tasks()
    print(f"✅ 未処理タスク数: {len(pending_tasks)}")
    
    print("\n📋 生成されたコンテキスト情報:")
    print(context_summary[:500] + "..." if len(context_summary) > 500 else context_summary)


def main():
    """メイン実行関数 - 全体的なデモ"""
    print("🚀 Claude Bridge System - 完全デモンストレーション")
    print("=" * 60)
    
    # 1. ファイルシステム初期化
    print("\n1️⃣ Bridge ファイルシステムの初期化")
    bridge_fs = BridgeFileSystem()
    bridge_fs.initialize_structure()
    
    # 2. プロジェクト認識デモ
    print("\n2️⃣ プロジェクト認識機能のデモ")
    demo_project_context_loader()
    
    # 3. タスク生成デモ
    print("\n3️⃣ タスク生成機能のデモ")
    demo_task_generator()
    
    # 4. 統合ワークフローデモ
    print("\n4️⃣ 統合ワークフローのデモ")
    integrated_workflow_demo(bridge_fs)
    
    print("\n🎉 デモ完了！")
    print("\n📚 この概念実証で実装された機能:")
    print("  ✓ プロジェクトショートカット検出")
    print("  ✓ Claude.md自動読み込み（シミュレーション）")
    print("  ✓ マルチプロジェクトコンテキスト生成")
    print("  ✓ 会話分析とタスク抽出")
    print("  ✓ 構造化マークダウンタスク生成")
    print("  ✓ ファイルベースタスク管理")
    print("  ✓ 統合ワークフローシミュレーション")
    
    print("\n🔄 次のステップ:")
    print("  - ファイル監視・自動実行機能")
    print("  - パフォーマンス最適化とキャッシュ")
    print("  - エラーハンドリングとセキュリティ")
    print("  - 運用監視とバックアップ機能")
    print("  - Claude Code との実際の連携")


if __name__ == "__main__":
    main()
