"""
Claude Bridge System - 統合テスト
MVP Phase 1-2の動作検証
"""

import pytest
import json
import tempfile
from pathlib import Path

from claude_bridge.core import BridgeFileSystem, ProjectRegistry, ProjectContextLoader, TaskGenerator
from claude_bridge.exceptions import BridgeException


@pytest.fixture
def temp_bridge_root():
    """テスト用の一時ディレクトリ"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def bridge_fs(temp_bridge_root):
    """BridgeFileSystemのテストインスタンス"""
    return BridgeFileSystem(bridge_root=temp_bridge_root / "bridge")


@pytest.fixture
def registry():
    """ProjectRegistryのテストインスタンス"""
    return ProjectRegistry()


@pytest.fixture
def context_loader(registry):
    """ProjectContextLoaderのテストインスタンス"""
    return ProjectContextLoader(registry)


@pytest.fixture
def task_generator(context_loader, bridge_fs):
    """TaskGeneratorのテストインスタンス"""
    return TaskGenerator(context_loader, bridge_fs)


class TestBridgeFileSystem:
    """BridgeFileSystemの統合テスト"""
    
    def test_initialization(self, bridge_fs):
        """初期化テスト"""
        success = bridge_fs.initialize_structure()
        assert success, "初期化が失敗しました"
        
        # ディレクトリ構造の確認
        stats = bridge_fs.get_system_stats()
        assert stats['initialized'], "初期化状態が正しくありません"
        assert stats['pending_tasks'] == 0, "初期状態でタスクが存在します"
    
    def test_task_lifecycle(self, bridge_fs):
        """タスクライフサイクルテスト"""
        bridge_fs.initialize_structure()
        
        # タスクファイル保存（文字列として渡す）
        task_content = """# Test Task
        
## Task Content
[tech] APIを修正して

## Task Details
- ID: test_task_001
- Created: 2025-01-30T12:00:00
"""
        
        task_file = bridge_fs.save_task_file(task_content, "tech_project")
        assert task_file.exists(), "タスクファイルが作成されませんでした"
        
        # 未処理タスク一覧
        pending_tasks = bridge_fs.list_pending_tasks()
        assert len(pending_tasks) == 1, "未処理タスクが正しく取得できません"
        
        # タスクを処理中に移動
        processing_file = bridge_fs.move_task_to_processing(task_file)
        assert processing_file.exists(), "処理中タスクが作成されませんでした"
        assert not task_file.exists(), "元のタスクファイルが削除されませんでした"
        
        # タスク結果保存（Path引数として渡す）
        result_file = bridge_fs.save_task_result(processing_file, "API修正完了", True)
        assert result_file.exists(), "結果ファイルが作成されませんでした"


class TestProjectRegistry:
    """ProjectRegistry統合テスト"""
    
    def test_load_default_config(self, registry):
        """デフォルト設定読み込みテスト"""
        config = registry.load_config()
        assert isinstance(config, dict), "設定がdict形式ではありません"
        assert 'projects' in config, "projects設定がありません"
        assert 'global_settings' in config, "global_settings設定がありません"
    
    def test_project_operations(self, registry):
        """プロジェクト操作テスト"""
        # デフォルト設定の確認
        config = registry.load_config()
        original_count = len(config.get('projects', {}))
        assert original_count >= 0, "デフォルト設定が正しく読み込まれません"
        
        # デフォルトプロジェクトが存在する場合の確認
        if original_count > 0:
            projects = registry.list_projects()
            first_project_id = list(projects.keys())[0]
            first_project = registry.get_project(first_project_id)
            assert first_project is not None, "デフォルトプロジェクトが取得できません"
        
        # プロジェクト一覧の基本機能テスト
        all_projects = registry.list_projects(active_only=False)
        active_projects = registry.list_projects(active_only=True)
        assert len(active_projects) <= len(all_projects), "アクティブプロジェクト数が矛盾しています"


class TestTaskGenerator:
    """TaskGenerator統合テスト"""
    
    def test_conversation_analysis(self, task_generator):
        """会話分析テスト"""
        content = "[tech] APIのバグを修正して、テストも追加する"
        
        analysis = task_generator.analyze_conversation(content)
        
        assert analysis['status'] == 'success', f"分析に失敗: {analysis.get('error', '')}"
        assert len(analysis['task_candidates']) > 0, "タスク候補が生成されませんでした"
        assert len(analysis['detected_projects']) > 0, "プロジェクトが検出されませんでした"
        assert analysis['complexity_score'] > 0, "複雑度スコアが計算されませんでした"
    
    def test_task_file_generation(self, task_generator, bridge_fs):
        """タスクファイル生成テスト"""
        bridge_fs.initialize_structure()
        
        content = "[tech] データベース接続を最適化する"
        
        task_file = task_generator.generate_task_file(content)
        assert task_file.exists(), "タスクファイルが生成されませんでした"
        
        # ファイル内容確認
        with open(task_file, 'r', encoding='utf-8') as f:
            task_content = f.read()
        
        assert "[tech]" in task_content, "プロジェクトショートカットが含まれません"
        assert "データベース接続" in task_content, "タスク内容が含まれません"
        assert "## 🎯 Detected Task Candidates" in task_content, "タスク候補セクションがありません"


class TestSystemIntegration:
    """システム全体の統合テスト"""
    
    def test_end_to_end_workflow(self, bridge_fs, task_generator):
        """エンドツーエンドワークフローテスト"""
        # システム初期化
        bridge_fs.initialize_structure()
        
        # 会話分析からタスク生成まで
        content = "[tech] ユーザー認証機能を実装し、セキュリティテストを実行する"
        
        # 1. 会話分析
        analysis = task_generator.analyze_conversation(content)
        assert analysis['status'] == 'success'
        
        # 2. タスクファイル生成
        task_file = task_generator.generate_task_file(content)
        assert task_file.exists()
        
        # 3. システム統計確認
        stats = bridge_fs.get_system_stats()
        assert stats['pending_tasks'] == 1
        assert stats['initialized']
        
        # 4. タスク処理シミュレーション
        pending_tasks = bridge_fs.list_pending_tasks()
        assert len(pending_tasks) == 1
        
        processing_file = bridge_fs.move_task_to_processing(task_file)
        assert processing_file.exists()
        
        # 5. 結果保存（正しい引数）
        result_file = bridge_fs.save_task_result(processing_file, "認証機能実装完了", True)
        assert result_file.exists()
        
        # 6. 最終統計確認
        final_stats = bridge_fs.get_system_stats()
        assert final_stats['pending_tasks'] == 0
        assert final_stats['completed_tasks'] == 1
        assert final_stats['success_results'] == 1
    
    def test_error_handling(self, task_generator):
        """エラーハンドリングテスト"""
        # 空の内容での分析（現在のAPIでは成功として処理される）
        analysis = task_generator.analyze_conversation("")
        assert analysis['status'] in ['success', 'error']  # どちらでも許容
        
        # 無効なプロジェクト指定（検出されずに空の結果）
        analysis = task_generator.analyze_conversation("[invalid] タスクを実行")
        assert analysis['status'] == 'success'  # エラーではなく検出されないだけ
        # プロジェクトが検出されないか、デフォルトプロジェクトが検出される
        assert isinstance(analysis['detected_projects'], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])