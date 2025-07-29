"""
Claude Bridge System - Context Bridge System Tests
双方向コンテキスト転送システムのテスト
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from claude_bridge.mis_integration import (
    ContextBridgeSystem,
    ContextTransferResult,
    CrossPlatformContext,
    MISMemoryBridge,
    MISMemoryEntry,
    MISMemoryQuery
)
from claude_bridge.mis_integration.desktop_context_collector import (
    DesktopContextCollector,
    DesktopConversation,
    ContextTransferRequest
)
from claude_bridge.mis_integration.code_development_tracker import (
    CodeDevelopmentTracker,
    DevelopmentSession,
    ProjectStatus
)


class TestContextBridgeSystem:
    """ContextBridgeSystemのテストクラス"""
    
    def setup_method(self):
        """テスト用セットアップ"""
        # テンポラリディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.memory_file = Path(self.temp_dir) / "test_memory.json"
        
        # MISMemoryBridgeをモック
        self.mock_memory_bridge = Mock(spec=MISMemoryBridge)
        
        # ContextBridgeSystemを初期化
        self.bridge_system = ContextBridgeSystem(self.mock_memory_bridge)
    
    def test_init_context_bridge_system(self):
        """ContextBridgeSystemの初期化テスト"""
        assert self.bridge_system.memory_bridge == self.mock_memory_bridge
        assert isinstance(self.bridge_system.desktop_collector, DesktopContextCollector)
        assert isinstance(self.bridge_system.code_tracker, CodeDevelopmentTracker)
        assert isinstance(self.bridge_system.active_transfers, dict)
        assert isinstance(self.bridge_system.cross_platform_contexts, dict)
    
    def test_transfer_desktop_to_code_success(self):
        """Desktop→Code転送成功テスト"""
        # テストデータ
        conversation_content = """
        プロジェクト: test_project
        実装したい機能:
        ```python
        def hello_world():
            print("Hello, World!")
        ```
        TODO: テストケースを追加する
        ファイル: main.py
        """
        target_project = "test_project"
        
        # モック設定
        self.mock_memory_bridge.save_memory.return_value = "mock_memory_id"
        
        # DesktopContextCollectorをモック
        mock_conversation = DesktopConversation(
            session_id="test_session",
            timestamp=datetime.now().isoformat(),
            user_messages=[conversation_content],
            assistant_messages=[],
            detected_projects=["test_project"],
            key_topics=["implementation", "testing"],
            action_items=["テストケースを追加する"],
            code_snippets=[{"language": "python", "code": 'def hello_world():\n    print("Hello, World!")'}],
            file_references=["main.py"],
            importance_score=0.8,
            summary="Test conversation about implementation"
        )
        
        # desktop_collectorのメソッドをモック
        self.bridge_system.desktop_collector.start_conversation_tracking = Mock(return_value="conv_123")
        self.bridge_system.desktop_collector.add_message = Mock()
        self.bridge_system.desktop_collector.finalize_conversation = Mock(return_value=mock_conversation)
        
        # 転送実行
        result = self.bridge_system.transfer_desktop_to_code(
            conversation_content=conversation_content,
            target_project=target_project,
            include_code_snippets=True,
            include_context_history=True
        )
        
        # 検証
        assert isinstance(result, ContextTransferResult)
        assert result.success is True
        assert result.source_environment == "desktop"
        assert result.target_environment == "code"
        assert result.transfer_type == "conversation"
        assert len(result.transferred_items) > 0
        assert result.error_message is None
        
        # save_memoryが適切に呼ばれているか確認
        assert self.mock_memory_bridge.save_memory.call_count >= 1
    
    def test_transfer_desktop_to_code_failure(self):
        """Desktop→Code転送失敗テスト"""
        # desktop_collectorをモックして失敗させる
        self.bridge_system.desktop_collector.start_conversation_tracking = Mock(return_value="conv_123")
        self.bridge_system.desktop_collector.add_message = Mock()
        self.bridge_system.desktop_collector.finalize_conversation = Mock(return_value=None)  # 失敗
        
        # 転送実行
        result = self.bridge_system.transfer_desktop_to_code(
            conversation_content="test content",
            target_project="test_project"
        )
        
        # 検証
        assert result.success is False
        assert result.error_message == "Failed to process conversation"
        assert len(result.transferred_items) == 0
    
    def test_transfer_code_to_desktop_success(self):
        """Code→Desktop転送成功テスト"""
        project_id = "test_project"
        
        # モック設定
        self.mock_memory_bridge.save_memory.return_value = "mock_memory_id"
        
        # CodeDevelopmentTrackerをモック
        mock_project_status = ProjectStatus(
            project_id=project_id,
            project_name="Test Project",
            current_phase="実装",
            last_activity=datetime.now().isoformat(),
            completion_percentage=75.0,
            active_files=["main.py", "test.py"],
            recent_commits=[{"hash": "abc123", "message": "Add feature"}],
            open_issues=["Bug in function X"],
            next_tasks=["Add tests", "Fix documentation"],
            dependencies=["pytest", "click"],
            health_score=0.8,
            last_updated=datetime.now().isoformat()
        )
        
        self.bridge_system.code_tracker.analyze_project_status = Mock(return_value=mock_project_status)
        
        # 転送実行
        result = self.bridge_system.transfer_code_to_desktop(
            project_id=project_id,
            include_recent_sessions=True,
            include_project_status=True
        )
        
        # 検証
        assert isinstance(result, ContextTransferResult)
        assert result.success is True
        assert result.source_environment == "code"
        assert result.target_environment == "desktop"
        assert result.transfer_type == "development_status"
        assert len(result.transferred_items) > 0
        assert result.error_message is None
        
        # analyze_project_statusが呼ばれているか確認
        self.bridge_system.code_tracker.analyze_project_status.assert_called_once_with(project_id)
    
    def test_transfer_code_to_desktop_with_session_id(self):
        """特定セッションIDでのCode→Desktop転送テスト"""
        project_id = "test_project"
        session_id = "test_session_123"
        
        # モック設定
        self.mock_memory_bridge.save_memory.return_value = "mock_memory_id"
        
        mock_session_status = {
            "session_id": session_id,
            "project_id": project_id,
            "start_time": datetime.now().isoformat(),
            "working_directory": "/test/dir",
            "git_branch": "main",
            "files_modified_count": 5,
            "commands_executed_count": 10,
            "progress_notes_count": 3,
            "issues_encountered_count": 1,
            "completion_status": "completed"
        }
        
        self.bridge_system.code_tracker.get_session_status = Mock(return_value=mock_session_status)
        
        # 転送実行
        result = self.bridge_system.transfer_code_to_desktop(
            project_id=project_id,
            session_id=session_id,
            include_project_status=False
        )
        
        # 検証
        assert result.success is True
        assert len(result.transferred_items) > 0
        
        # get_session_statusが呼ばれているか確認
        self.bridge_system.code_tracker.get_session_status.assert_called_once_with(session_id)
    
    def test_get_context_for_code_session(self):
        """Code環境向けコンテキスト取得テスト"""
        project_id = "test_project"
        
        # モック記憶エントリー
        mock_memories = [
            MISMemoryEntry(
                id="mem_1",
                content="Desktop conversation about feature X",
                metadata={},
                timestamp=datetime.now().isoformat(),
                tags=["desktop_context"],
                project_id=project_id,
                entry_type="desktop_conversation"
            ),
            MISMemoryEntry(
                id="mem_2",
                content="TODO: Implement feature Y",
                metadata={},
                timestamp=datetime.now().isoformat(),
                tags=["action_items"],
                project_id=project_id,
                entry_type="transferred_actions"
            )
        ]
        
        self.mock_memory_bridge.recall_memory.return_value = mock_memories
        
        # コンテキスト取得
        context = self.bridge_system.get_context_for_code_session(
            project_id=project_id,
            context_types=["desktop_conversations", "action_items"]
        )
        
        # 検証
        assert context["project_id"] == project_id
        assert "timestamp" in context
        assert "available_contexts" in context
        
        available_contexts = context["available_contexts"]
        assert "desktop_conversations" in available_contexts
        assert "action_items" in available_contexts
        
        # recall_memoryが適切に呼ばれているか確認
        assert self.mock_memory_bridge.recall_memory.call_count == 2
    
    def test_get_context_for_desktop_session(self):
        """Desktop環境向けコンテキスト取得テスト"""
        project_hint = "test_project"
        
        # モック記憶エントリー
        mock_memories = [
            MISMemoryEntry(
                id="mem_1",
                content="Recent development status",
                metadata={},
                timestamp=datetime.now().isoformat(),
                tags=["project_status"],
                project_id=project_hint,
                entry_type="project_status"
            )
        ]
        
        self.mock_memory_bridge.recall_memory.return_value = mock_memories
        
        # コンテキスト取得
        context = self.bridge_system.get_context_for_desktop_session(project_hint)
        
        # 検証
        assert "timestamp" in context
        assert "available_contexts" in context
        
        available_contexts = context["available_contexts"]
        assert "recent_development" in available_contexts
        assert "recent_issues" in available_contexts
        assert "active_projects" in available_contexts
        
        # recall_memoryが適切に呼ばれているか確認
        assert self.mock_memory_bridge.recall_memory.call_count >= 3
    
    def test_create_code_context_from_conversation(self):
        """会話からCodeコンテキスト作成テスト"""
        mock_conversation = DesktopConversation(
            session_id="test_session",
            timestamp=datetime.now().isoformat(),
            user_messages=["Test message"],
            assistant_messages=["Test response"],
            detected_projects=["test_project"],
            key_topics=["implementation"],
            action_items=["TODO: Add tests"],
            code_snippets=[],
            file_references=["main.py"],
            importance_score=0.8,
            summary="Test conversation"
        )
        
        target_project = "test_project"
        
        # プライベートメソッドを直接テスト
        context = self.bridge_system._create_code_context_from_conversation(
            mock_conversation, target_project
        )
        
        # 検証
        assert isinstance(context, str)
        assert "Desktop会話からのコンテキスト転送" in context
        assert target_project in context
        assert mock_conversation.summary in context
        assert "test_project" in context
        assert "implementation" in context
        assert "main.py" in context
    
    def test_create_desktop_context_from_project_status(self):
        """プロジェクト状況からDesktopコンテキスト作成テスト"""
        mock_status = ProjectStatus(
            project_id="test_project",
            project_name="Test Project",
            current_phase="実装",
            last_activity=datetime.now().isoformat(),
            completion_percentage=75.0,
            active_files=["main.py", "test.py"],
            recent_commits=[{"hash": "abc123", "message": "Add feature"}],
            open_issues=["Bug in function X"],
            next_tasks=["Add tests"],
            dependencies=["pytest"],
            health_score=0.8,
            last_updated=datetime.now().isoformat()
        )
        
        # プライベートメソッドを直接テスト
        context = self.bridge_system._create_desktop_context_from_project_status(mock_status)
        
        # 検証
        assert isinstance(context, str)
        assert "Code開発状況レポート" in context
        assert "Test Project" in context
        assert "実装" in context
        assert "75.0%" in context
        assert "main.py" in context
        assert "Add feature" in context
        assert "Bug in function X" in context
    
    def test_error_handling_in_transfer_desktop_to_code(self):
        """Desktop→Code転送でのエラーハンドリングテスト"""
        # memory_bridgeにエラーを発生させる
        self.mock_memory_bridge.save_memory.side_effect = Exception("Memory save failed")
        
        # desktop_collectorを正常にモック
        mock_conversation = DesktopConversation(
            session_id="test_session",
            timestamp=datetime.now().isoformat(),
            user_messages=["test"],
            assistant_messages=[],
            detected_projects=["test_project"],
            key_topics=[],
            action_items=[],
            code_snippets=[],
            file_references=[],
            importance_score=0.5,
            summary="Test"
        )
        
        self.bridge_system.desktop_collector.start_conversation_tracking = Mock(return_value="conv_123")
        self.bridge_system.desktop_collector.add_message = Mock()
        self.bridge_system.desktop_collector.finalize_conversation = Mock(return_value=mock_conversation)
        
        # 転送実行
        result = self.bridge_system.transfer_desktop_to_code(
            conversation_content="test content",
            target_project="test_project"
        )
        
        # 検証
        assert result.success is False
        assert "Memory save failed" in result.error_message
    
    def test_error_handling_in_transfer_code_to_desktop(self):
        """Code→Desktop転送でのエラーハンドリングテスト"""
        # code_trackerにエラーを発生させる
        self.bridge_system.code_tracker.analyze_project_status = Mock(side_effect=Exception("Analysis failed"))
        
        # 転送実行
        result = self.bridge_system.transfer_code_to_desktop(
            project_id="test_project"
        )
        
        # 検証
        assert result.success is False
        assert "Analysis failed" in result.error_message
    
    def test_get_context_with_exception(self):
        """コンテキスト取得時の例外ハンドリングテスト"""
        # memory_bridgeにエラーを発生させる
        self.mock_memory_bridge.recall_memory.side_effect = Exception("Recall failed")
        
        # コンテキスト取得
        context = self.bridge_system.get_context_for_code_session("test_project")
        
        # 検証
        assert "error" in context
        assert "Recall failed" in context["error"]
    
    def test_cross_platform_context_integration(self):
        """クロスプラットフォームコンテキスト統合テスト"""
        # 複数の転送を実行して統合を確認
        
        # 1. Desktop→Code転送
        mock_conversation = DesktopConversation(
            session_id="test_session",
            timestamp=datetime.now().isoformat(),
            user_messages=["Implement feature"],
            assistant_messages=[],
            detected_projects=["test_project"],
            key_topics=["implementation"],
            action_items=["Add feature X"],
            code_snippets=[],
            file_references=["main.py"],
            importance_score=0.8,
            summary="Feature implementation discussion"
        )
        
        self.bridge_system.desktop_collector.start_conversation_tracking = Mock(return_value="conv_123")
        self.bridge_system.desktop_collector.add_message = Mock()
        self.bridge_system.desktop_collector.finalize_conversation = Mock(return_value=mock_conversation)
        self.mock_memory_bridge.save_memory.return_value = "mock_memory_id"
        
        desktop_result = self.bridge_system.transfer_desktop_to_code(
            conversation_content="Implement feature X",
            target_project="test_project"
        )
        
        # 2. Code→Desktop転送
        mock_project_status = ProjectStatus(
            project_id="test_project",
            project_name="Test Project",
            current_phase="実装",
            last_activity=datetime.now().isoformat(),
            completion_percentage=80.0,
            active_files=["main.py"],
            recent_commits=[{"hash": "def456", "message": "Implement feature X"}],
            open_issues=[],
            next_tasks=["Add tests for feature X"],
            dependencies=["pytest"],
            health_score=0.9,
            last_updated=datetime.now().isoformat()
        )
        
        self.bridge_system.code_tracker.analyze_project_status = Mock(return_value=mock_project_status)
        
        code_result = self.bridge_system.transfer_code_to_desktop(
            project_id="test_project"
        )
        
        # 検証
        assert desktop_result.success is True
        assert code_result.success is True
        
        # 双方向でコンテキストが転送されていることを確認
        assert desktop_result.transfer_type == "conversation"
        assert code_result.transfer_type == "development_status"
        assert len(desktop_result.transferred_items) > 0
        assert len(code_result.transferred_items) > 0


if __name__ == "__main__":
    pytest.main([__file__])