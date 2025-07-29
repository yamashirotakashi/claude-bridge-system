"""
Claude Bridge System - MIS Integration Tests
MIS特殊プロンプト機能の統合テスト
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from claude_bridge.mis_integration import (
    MISPromptHandler, 
    MISMemoryBridge, 
    MISCommandProcessor,
    MISPromptType,
    MISPromptResult,
    MISMemoryEntry,
    MISMemoryQuery
)


class TestMISPromptHandler:
    """MIS特殊プロンプトハンドラーのテスト"""
    
    def setup_method(self):
        """テスト前の準備"""
        self.handler = MISPromptHandler()
    
    def test_detect_memory_save_prompts(self):
        """記憶保存プロンプトの検出テスト"""
        test_text = """
        これは重要な情報です。
        [MISに記憶]この機能は非常に重要で、後で参照する必要がある。
        その他のテキスト。
        [記憶]この部分も保存したい。
        """
        
        detected = self.handler.detect_mis_prompts(test_text)
        
        assert len(detected) == 2
        assert detected[0][0] == MISPromptType.MEMORY_SAVE
        assert "重要で、後で参照する必要がある" in detected[0][1]
        assert detected[1][0] == MISPromptType.MEMORY_SAVE
        assert "この部分も保存したい" in detected[1][1]
    
    def test_detect_memory_recall_prompts(self):
        """記憶呼び出しプロンプトの検出テスト"""
        test_text = """
        [MIS記憶呼び出し]以前に保存した実装方法を確認したい
        [呼び出し]API設計に関する記憶
        """
        
        detected = self.handler.detect_mis_prompts(test_text)
        
        assert len(detected) == 2
        assert detected[0][0] == MISPromptType.MEMORY_RECALL
        assert "実装方法を確認したい" in detected[0][1]
        assert detected[1][0] == MISPromptType.MEMORY_RECALL
        assert "API設計に関する記憶" in detected[1][1]
    
    def test_detect_mixed_prompts(self):
        """複数種類のプロンプトが混在するテスト"""
        test_text = """
        プロジェクトの進捗について。
        [MISに記憶]今日の会議で決まった新しい要件
        [MIS仕様更新]APIエンドポイントを/v2/usersに変更
        [MIS記憶呼び出し]前回の仕様書の内容
        [MISコンテキスト共有]現在のプロジェクト状態
        """
        
        detected = self.handler.detect_mis_prompts(test_text)
        
        assert len(detected) == 4
        prompt_types = [prompt[0] for prompt in detected]
        assert MISPromptType.MEMORY_SAVE in prompt_types
        assert MISPromptType.SPEC_UPDATE in prompt_types
        assert MISPromptType.MEMORY_RECALL in prompt_types
        assert MISPromptType.CONTEXT_SHARE in prompt_types
    
    def test_process_memory_save(self):
        """記憶保存処理のテスト"""
        content = "重要な実装詳細について"
        result = self.handler.process_memory_save(content)
        
        assert isinstance(result, MISPromptResult)
        assert result.success is True
        assert result.prompt_type == MISPromptType.MEMORY_SAVE
        assert result.content == content
        assert result.desktop_action is not None
        assert result.desktop_action["type"] == "memory_save"
    
    def test_process_memory_recall(self):
        """記憶呼び出し処理のテスト"""
        query = "API設計について"
        result = self.handler.process_memory_recall(query)
        
        assert isinstance(result, MISPromptResult)
        assert result.success is True
        assert result.prompt_type == MISPromptType.MEMORY_RECALL
        assert result.content == query
        assert result.desktop_action is not None
        assert result.desktop_action["type"] == "memory_recall"
    
    def test_content_classification(self):
        """コンテンツ分類のテスト"""
        # 仕様関連
        spec_content = "この機能の仕様を変更する必要がある"
        assert self.handler._classify_content(spec_content) == "specification"
        
        # 実装関連
        impl_content = "このコードの実装を改善する"
        assert self.handler._classify_content(impl_content) == "implementation"
        
        # バグ関連
        bug_content = "このバグを修正する必要がある"
        assert self.handler._classify_content(bug_content) == "issue"
        
        # 長文
        long_content = "a" * 1500
        assert self.handler._classify_content(long_content) == "long_text"


class TestMISMemoryBridge:
    """MIS記憶ブリッジのテスト"""
    
    def setup_method(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.memory_file = Path(self.temp_dir) / "test_memory.json"
        self.bridge = MISMemoryBridge(self.memory_file)
    
    def test_save_and_recall_memory(self):
        """記憶の保存と呼び出しテスト"""
        # 記憶を保存
        content = "テスト用の重要な情報"
        tags = ["test", "important"]
        project_id = "test_project"
        
        memory_id = self.bridge.save_memory(
            content=content,
            tags=tags,
            project_id=project_id,
            entry_type="test"
        )
        
        assert memory_id is not None
        assert memory_id.startswith("mis_mem_")
        
        # 記憶を検索
        query = MISMemoryQuery(query="重要な情報", max_results=10)
        memories = self.bridge.recall_memory(query)
        
        assert len(memories) == 1
        memory = memories[0]
        assert memory.content == content
        assert memory.tags == tags
        assert memory.project_id == project_id
        assert memory.entry_type == "test"
    
    def test_memory_search_with_filters(self):
        """フィルター条件での記憶検索テスト"""
        # 複数の記憶を保存
        self.bridge.save_memory("プロジェクトA情報", ["projectA"], "project_a", "info")
        self.bridge.save_memory("プロジェクトB情報", ["projectB"], "project_b", "info")
        self.bridge.save_memory("テスト情報", ["test"], "project_a", "test")
        
        # プロジェクトAの記憶のみ検索
        query = MISMemoryQuery(
            query="情報",
            project_id="project_a",
            max_results=10
        )
        memories = self.bridge.recall_memory(query)
        
        assert len(memories) == 2
        for memory in memories:
            assert memory.project_id == "project_a"
        
        # タグフィルターで検索
        query = MISMemoryQuery(
            query="情報",
            tags=["projectA"],
            max_results=10
        )
        memories = self.bridge.recall_memory(query)
        
        assert len(memories) == 1
        assert "projectA" in memories[0].tags
    
    def test_memory_update(self):
        """記憶更新のテスト"""
        # 記憶を保存
        memory_id = self.bridge.save_memory(
            content="元の内容",
            tags=["original"],
            entry_type="test"
        )
        
        # 記憶を更新
        updates = {
            "content": "更新された内容",
            "tags": ["updated"],
            "metadata": {"updated": True}
        }
        success = self.bridge.update_memory(memory_id, updates)
        
        assert success is True
        
        # 更新された内容を確認
        updated_memory = self.bridge.memories[memory_id]
        assert updated_memory.content == "更新された内容"
        assert updated_memory.tags == ["updated"]
        assert updated_memory.metadata.get("updated") is True
        assert "last_updated" in updated_memory.metadata
    
    def test_memory_deletion(self):
        """記憶削除のテスト"""
        # 記憶を保存
        memory_id = self.bridge.save_memory("削除テスト", ["delete"], entry_type="test")
        
        # 記憶が存在することを確認
        assert memory_id in self.bridge.memories
        
        # 記憶を削除
        success = self.bridge.delete_memory(memory_id)
        
        assert success is True
        assert memory_id not in self.bridge.memories
    
    def test_memory_stats(self):
        """記憶統計のテスト"""
        # 複数の記憶を保存
        self.bridge.save_memory("内容1", tags=["tag1"], project_id="project1", entry_type="type1")
        self.bridge.save_memory("内容2", tags=["tag1", "tag2"], project_id="project1", entry_type="type2")
        self.bridge.save_memory("内容3", tags=["tag2"], project_id="project2", entry_type="type1")
        
        stats = self.bridge.get_memory_stats()
        
        assert stats["total_memories"] == 3
        assert stats["type_distribution"]["type1"] == 2
        assert stats["type_distribution"]["type2"] == 1
        assert stats["tag_distribution"]["tag1"] == 2
        assert stats["tag_distribution"]["tag2"] == 2
        assert stats["project_distribution"]["project1"] == 2
        assert stats["project_distribution"]["project2"] == 1
    
    def test_memory_export_import(self):
        """記憶のエクスポート・インポートテスト"""
        # 記憶を保存
        self.bridge.save_memory("エクスポートテスト", ["export"], "test_project", "export_test")
        
        # JSON形式でエクスポート
        export_path = Path(self.temp_dir) / "export.json"
        success = self.bridge.export_memories(export_path, "json")
        
        assert success is True
        assert export_path.exists()
        
        # エクスポートファイルの内容確認
        with open(export_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        assert "export_info" in export_data
        assert "memories" in export_data
        assert len(export_data["memories"]) == 1
        
        # 新しいブリッジでインポート
        new_memory_file = Path(self.temp_dir) / "new_memory.json"
        new_bridge = MISMemoryBridge(new_memory_file)
        
        imported_count = new_bridge.import_memories(export_path, "json")
        
        assert imported_count == 1
        assert len(new_bridge.memories) == 1


class TestMISCommandProcessor:
    """MISコマンドプロセッサーのテスト"""
    
    def setup_method(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.memory_file = Path(self.temp_dir) / "test_memory.json"
        self.memory_bridge = MISMemoryBridge(self.memory_file)
        self.processor = MISCommandProcessor(self.memory_bridge)
    
    def test_process_conversation_with_memory_save(self):
        """記憶保存プロンプトを含む会話処理テスト"""
        conversation = """
        今日のミーティングについて。
        [MISに記憶]新しいAPI設計の方針が決まった。RESTfulな設計を採用し、認証にJWTを使用する。
        その他の内容。
        """
        
        result = self.processor.process_conversation(conversation, "test_project")
        
        assert result["status"] == "success"
        assert result["detected_prompts"] == 1
        assert result["processed_prompts"] == 1
        assert result["failed_prompts"] == 0
        
        # 記憶が保存されたことを確認
        query = MISMemoryQuery(query="API設計", max_results=10)
        memories = self.memory_bridge.recall_memory(query)
        assert len(memories) == 1
        assert "RESTfulな設計" in memories[0].content
    
    def test_process_conversation_with_memory_recall(self):
        """記憶呼び出しプロンプトを含む会話処理テスト"""
        # 事前に記憶を保存
        self.memory_bridge.save_memory(
            "API設計についての重要な決定事項",
            tags=["api", "design"],
            project_id="test_project",
            entry_type="design_decision"
        )
        
        conversation = """
        [MIS記憶呼び出し]API設計について以前に決めたことを確認したい
        """
        
        result = self.processor.process_conversation(conversation, "test_project")
        
        assert result["status"] == "success"
        assert result["detected_prompts"] == 1
        assert result["processed_prompts"] == 1
        
        # 処理結果に記憶呼び出しの結果が含まれていることを確認
        processing_results = result["processing_results"]
        assert len(processing_results) == 1
        
        memory_operation = processing_results[0]["memory_operation"]
        assert memory_operation["operation"] == "recall"
        assert memory_operation["success"] is True
        assert memory_operation["results_count"] == 1
    
    def test_process_conversation_with_multiple_prompts(self):
        """複数のプロンプトを含む会話処理テスト"""
        conversation = """
        プロジェクトの状況について。
        [MISに記憶]今日実装したログイン機能は正常に動作している。
        [MIS記憶呼び出し]以前のセキュリティ要件について
        [MIS仕様更新]パスワードポリシーを8文字以上に変更
        [MISコンテキスト共有]現在のプロジェクト進捗状況
        """
        
        result = self.processor.process_conversation(conversation, "test_project")
        
        assert result["status"] == "success"
        assert result["detected_prompts"] == 4
        assert result["processed_prompts"] == 4
        assert result["failed_prompts"] == 0
        
        # Desktop アクションが生成されていることを確認
        assert len(result["desktop_actions"]) == 4
        
        action_types = [action["type"] for action in result["desktop_actions"]]
        assert "memory_save" in action_types
        assert "memory_recall" in action_types
        assert "spec_update" in action_types
        assert "context_share" in action_types
    
    def test_processing_history(self):
        """処理履歴のテスト"""
        # 複数の会話を処理
        self.processor.process_conversation("[MISに記憶]テスト1", "project1")
        self.processor.process_conversation("[MISに記憶]テスト2", "project2")
        
        history = self.processor.get_processing_history()
        
        assert len(history) >= 2
        assert all("timestamp" in record for record in history)
        assert all("prompt_type" in record for record in history)
    
    def test_memory_statistics(self):
        """記憶統計のテスト"""
        # 複数の処理を実行
        self.processor.process_conversation("[MISに記憶]統計テスト1", "project1")
        self.processor.process_conversation("[MIS記憶呼び出し]検索テスト", "project1")
        
        stats = self.processor.get_memory_statistics()
        
        assert "memory_stats" in stats
        assert "processing_stats" in stats
        assert "prompt_type_distribution" in stats
        
        processing_stats = stats["processing_stats"]
        assert processing_stats["total_processed"] >= 2
        assert processing_stats["successful_operations"] >= 2
    
    @pytest.mark.asyncio
    async def test_desktop_action_processing(self):
        """Desktop アクション処理のテスト（非同期）"""
        action = {
            "type": "memory_save",
            "payload": {
                "content": "テスト内容",
                "metadata": {"test": True}
            }
        }
        
        result = await self.processor.process_desktop_action(action)
        
        assert result["action_type"] == "memory_save"
        assert result["success"] is True
        assert "Memory saved to Desktop session" in result["message"]
    
    def test_tag_extraction(self):
        """タグ自動抽出のテスト"""
        # 仕様関連
        spec_content = "この機能の仕様を確認する必要がある"
        tags = self.processor._extract_tags_from_content(spec_content)
        assert "仕様" in tags
        
        # 実装関連
        impl_content = "コードの実装を改善したい"
        tags = self.processor._extract_tags_from_content(impl_content)
        assert "実装" in tags
        
        # バグ関連
        bug_content = "このバグを修正する必要がある"
        tags = self.processor._extract_tags_from_content(bug_content)
        assert "バグ" in tags
        
        # 長文
        long_content = "a" * 1500
        tags = self.processor._extract_tags_from_content(long_content)
        assert "長文" in tags
    
    def test_export_processing_history(self):
        """処理履歴エクスポートのテスト"""
        # 処理を実行
        self.processor.process_conversation("[MISに記憶]エクスポートテスト", "test_project")
        
        # JSON形式でエクスポート
        export_path = Path(self.temp_dir) / "history.json"
        success = self.processor.export_processing_history(export_path, "json")
        
        assert success is True
        assert export_path.exists()
        
        # エクスポートファイルの内容確認
        with open(export_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        assert "export_info" in export_data
        assert "processing_history" in export_data
        assert len(export_data["processing_history"]) >= 1


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v"])