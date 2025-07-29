"""
Claude Bridge System - Phase 3統合テスト
Desktop API、同期エンジン、WebSocket通信の統合テスト
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from claude_bridge.desktop_api import (
    DesktopConnector, 
    SyncEngine, 
    BridgeProtocol, 
    MessageType, 
    BridgeMessage
)
from claude_bridge.core import BridgeFileSystem, ProjectRegistry
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
def bridge_protocol():
    """BridgeProtocolのテストインスタンス"""
    return BridgeProtocol("test_client")


@pytest.fixture
def mock_websocket():
    """モックWebSocket"""
    websocket = AsyncMock()
    websocket.send = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture 
def desktop_connector(mock_websocket):
    """DesktopConnectorのテストインスタンス"""
    connector = DesktopConnector(websocket_url="ws://localhost:8765")
    
    # WebSocket接続をモック
    connector.websocket = mock_websocket
    connector.is_connected = True
    return connector


@pytest.fixture
def sync_engine(bridge_fs, registry, desktop_connector):
    """SyncEngineのテストインスタンス"""
    return SyncEngine(bridge_fs, registry, desktop_connector)


class TestBridgeProtocol:
    """BridgeProtocol単体テスト"""
    
    def test_message_creation(self, bridge_protocol):
        """メッセージ作成テスト"""
        message = bridge_protocol.create_message(
            MessageType.PROJECT_SWITCH,
            {"project_id": "test_project", "context": {}}
        )
        
        assert message.message_type == MessageType.PROJECT_SWITCH
        assert message.payload["project_id"] == "test_project"
        assert message.source == "test_client"
        assert message.target == "claude_desktop"
        assert message.message_id is not None
        assert message.timestamp is not None
    
    def test_response_creation(self, bridge_protocol):
        """レスポンスメッセージ作成テスト"""
        original = bridge_protocol.create_message(
            MessageType.PING,
            {"test": "data"}
        )
        
        response = bridge_protocol.create_response(
            original,
            MessageType.PONG,
            {"response": "ok"}
        )
        
        assert response.message_type == MessageType.PONG
        assert response.correlation_id == original.message_id
        assert response.target == original.source
    
    def test_error_response_creation(self, bridge_protocol):
        """エラーレスポンス作成テスト"""
        original = bridge_protocol.create_message(
            MessageType.PROJECT_SWITCH,
            {"project_id": "invalid"}
        )
        
        error_response = bridge_protocol.create_error_response(
            original,
            "INVALID_PROJECT",
            "Project not found"
        )
        
        assert error_response.message_type == MessageType.ERROR
        assert error_response.payload["error_code"] == "INVALID_PROJECT"
        assert error_response.payload["error_message"] == "Project not found"
        assert error_response.correlation_id == original.message_id
    
    def test_message_serialization(self, bridge_protocol):
        """メッセージシリアライゼーションテスト"""
        message = bridge_protocol.create_ping()
        
        # JSON変換
        json_str = message.to_json()
        assert isinstance(json_str, str)
        
        # JSONから復元
        restored = BridgeMessage.from_json(json_str)
        assert restored.message_type == message.message_type
        assert restored.message_id == message.message_id
        assert restored.source == message.source
    
    def test_message_validation(self, bridge_protocol):
        """メッセージ妥当性検証テスト"""
        # 正常なメッセージ
        valid_message = bridge_protocol.create_ping()
        assert bridge_protocol.validate_message(valid_message)
        
        # 不正なメッセージ（message_typeなし）
        invalid_message = BridgeMessage(
            message_type=None,
            payload={"test": "data"}
        )
        assert not bridge_protocol.validate_message(invalid_message)


class TestDesktopConnector:
    """DesktopConnector単体テスト"""
    
    @pytest.mark.asyncio
    async def test_connection_establishment(self, mock_websocket):
        """接続確立テスト"""
        connector = DesktopConnector()
        
        # ハンドシェイクレスポンスをモック
        handshake_response = BridgeMessage(
            message_type=MessageType.HANDSHAKE,
            payload={"status": "success"}
        )
        
        # ハンドシェイクレスポンス待機のモック
        connector._wait_for_response = AsyncMock(return_value=handshake_response)
        
        with patch('websockets.connect') as mock_connect:
            # websockets.connectをasyncにして、mock_websocketを返すように修正
            async def mock_websocket_connect(*args, **kwargs):
                return mock_websocket
            mock_connect.side_effect = mock_websocket_connect
            
            success = await connector.connect()
            assert success
            assert connector.is_connected
    
    @pytest.mark.asyncio
    async def test_message_sending(self, desktop_connector):
        """メッセージ送信テスト"""
        message = desktop_connector.protocol.create_ping()
        
        # レスポンス不要メッセージ
        result = await desktop_connector.send_message(message)
        assert result is None
        
        # WebSocketに送信されたことを確認
        desktop_connector.websocket.send.assert_called()
    
    @pytest.mark.asyncio
    async def test_project_switch_notification(self, desktop_connector):
        """プロジェクト切り替え通知テスト"""
        project_context = {
            "project_id": "test_project",
            "name": "Test Project",
            "path": "/test/path"
        }
        
        await desktop_connector.send_project_switch("test_project", project_context)
        
        # メッセージが送信されたことを確認
        desktop_connector.websocket.send.assert_called()
        
        # 送信されたメッセージの内容確認
        call_args = desktop_connector.websocket.send.call_args[0][0]
        message_data = json.loads(call_args)
        assert message_data["message_type"] == "project_switch"
        assert message_data["payload"]["project_id"] == "test_project"
    
    @pytest.mark.asyncio
    async def test_file_change_notification(self, desktop_connector):
        """ファイル変更通知テスト"""
        await desktop_connector.send_file_change(
            "/test/file.py",
            "modified",
            "print('Hello World')"
        )
        
        # メッセージが送信されたことを確認
        desktop_connector.websocket.send.assert_called()
        
        # 送信されたメッセージの内容確認
        call_args = desktop_connector.websocket.send.call_args[0][0]
        message_data = json.loads(call_args)
        assert message_data["message_type"] == "file_change"
        assert message_data["payload"]["file_path"] == "/test/file.py"
        assert message_data["payload"]["change_type"] == "modified"
    
    @pytest.mark.asyncio
    async def test_message_handler_registration(self, desktop_connector):
        """メッセージハンドラー登録テスト"""
        handler_called = False
        
        def test_handler(message):
            nonlocal handler_called
            handler_called = True
        
        # ハンドラー登録
        desktop_connector.add_message_handler(MessageType.PING, test_handler)
        
        # ハンドラーが登録されたことを確認
        assert MessageType.PING in desktop_connector.message_handlers
        assert test_handler in desktop_connector.message_handlers[MessageType.PING]
        
        # ハンドラー削除
        desktop_connector.remove_message_handler(MessageType.PING, test_handler)
        assert len(desktop_connector.message_handlers.get(MessageType.PING, [])) == 0
    
    def test_connection_status(self, desktop_connector):
        """接続状態取得テスト"""
        status = desktop_connector.get_connection_status()
        
        assert isinstance(status, dict)
        assert "is_connected" in status
        assert "websocket_url" in status
        assert "connection_stats" in status
        assert "active_handlers" in status


class TestSyncEngine:
    """SyncEngine単体テスト"""
    
    @pytest.mark.asyncio
    async def test_sync_engine_startup(self, sync_engine):
        """同期エンジン起動テスト"""
        # ファイル監視をモック（実際のファイル監視は行わない）
        with patch.object(sync_engine, '_start_file_watcher'), \
             patch.object(sync_engine, '_start_sync_tasks'):
            
            await sync_engine.start()
            assert sync_engine.is_running
    
    @pytest.mark.asyncio
    async def test_file_sync_simulation(self, sync_engine, temp_bridge_root):
        """ファイル同期シミュレーションテスト"""
        # テストファイル作成
        test_file = temp_bridge_root / "test.txt"
        test_file.write_text("Hello, World!")
        
        # 同期メソッドをモック
        with patch.object(sync_engine, '_calculate_checksum', return_value="test_checksum"), \
             patch.object(sync_engine, '_read_file_content', return_value="Hello, World!"):
            
            # Desktop connector のsend_file_changeをモック
            sync_engine.desktop_connector.send_file_change = AsyncMock()
            
            success = await sync_engine.sync_file(test_file, "cli")
            assert success
            
            # Desktop に通知されたことを確認
            sync_engine.desktop_connector.send_file_change.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_conflict_detection(self, sync_engine, temp_bridge_root):
        """競合検出テスト"""
        test_file = temp_bridge_root / "conflict_test.txt"
        test_file.write_text("Original content")
        
        file_str = str(test_file.resolve())
        
        # 既存の同期状態を設定
        from claude_bridge.desktop_api.sync_engine import SyncState
        sync_engine.sync_states[file_str] = SyncState(
            file_path=file_str,
            last_sync_time="2025-01-01T00:00:00",
            checksum="original_checksum",
            source="desktop"
        )
        
        # 競合検出
        conflict = await sync_engine._detect_conflict(
            test_file,
            "new_checksum", 
            "cli"
        )
        
        assert conflict  # 異なるソースからの異なるチェックサムなので競合
    
    @pytest.mark.asyncio
    async def test_desktop_message_handling(self, sync_engine, temp_bridge_root):
        """Desktop メッセージ処理テスト"""
        # ファイル変更メッセージ
        test_file = temp_bridge_root / "desktop_change.txt"
        
        file_change_message = BridgeMessage(
            message_type=MessageType.FILE_CHANGE,
            payload={
                "file_path": str(test_file),
                "change_type": "modified",
                "content": "Desktop modified content"
            }
        )
        
        # _write_file_content をモック
        with patch.object(sync_engine, '_write_file_content') as mock_write, \
             patch.object(sync_engine, '_calculate_checksum', return_value="desktop_checksum"):
            
            await sync_engine._handle_desktop_file_change(file_change_message)
            
            # ファイル書き込みが呼ばれたことを確認
            mock_write.assert_called_once_with(test_file, "Desktop modified content")
            
            # 同期状態が更新されたことを確認
            file_str = str(test_file.resolve())
            assert file_str in sync_engine.sync_states
            assert sync_engine.sync_states[file_str].source == "desktop"
    
    def test_sync_status(self, sync_engine):
        """同期状態取得テスト"""
        status = sync_engine.get_sync_status()
        
        assert isinstance(status, dict)
        assert "is_running" in status
        assert "sync_interval" in status
        assert "conflict_resolution" in status
        assert "sync_stats" in status
        assert "queue_sizes" in status


class TestSystemIntegration:
    """システム統合テスト（Phase 3）"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_desktop_integration(
        self, 
        bridge_fs, 
        registry, 
        desktop_connector,
        temp_bridge_root
    ):
        """エンドツーエンドDesktop統合テスト"""
        # システム初期化
        bridge_fs.initialize_structure()
        
        # 同期エンジン作成とモック
        sync_engine = SyncEngine(bridge_fs, registry, desktop_connector)
        
        with patch.object(sync_engine, '_start_file_watcher'), \
             patch.object(sync_engine, '_start_sync_tasks'):
            
            await sync_engine.start()
            
            # テストファイル作成
            test_file = temp_bridge_root / "integration_test.py"
            test_content = """
# Integration Test File
def hello_world():
    print("Hello from Claude Bridge!")
"""
            test_file.write_text(test_content)
            
            # ファイル同期シミュレーション
            with patch.object(sync_engine, '_calculate_checksum', return_value="integration_checksum"), \
                 patch.object(sync_engine, '_read_file_content', return_value=test_content):
                
                success = await sync_engine.sync_file(test_file, "cli")
                assert success
                
                # Desktop に通知されたことを確認
                desktop_connector.websocket.send.assert_called()
                
                # 送信されたメッセージの確認
                call_args = desktop_connector.websocket.send.call_args[0][0]
                message_data = json.loads(call_args)
                assert message_data["message_type"] == "file_change"
                assert message_data["payload"]["change_type"] == "modified"
            
            await sync_engine.stop()
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_workflow(
        self,
        bridge_fs,
        registry, 
        desktop_connector,
        temp_bridge_root
    ):
        """競合解決ワークフローテスト"""
        sync_engine = SyncEngine(
            bridge_fs, 
            registry, 
            desktop_connector,
            conflict_resolution="manual"
        )
        
        # テストファイル
        test_file = temp_bridge_root / "conflict_file.txt"
        test_file.write_text("CLI content")
        
        file_str = str(test_file.resolve())
        
        # Desktop からの競合状態設定
        from claude_bridge.desktop_api.sync_engine import SyncState
        sync_engine.sync_states[file_str] = SyncState(
            file_path=file_str,
            last_sync_time="2025-01-01T00:00:00", 
            checksum="desktop_checksum",
            source="desktop"
        )
        
        # 競合検出と処理
        with patch.object(sync_engine, '_calculate_checksum', return_value="cli_checksum"):
            
            conflict_detected = await sync_engine._detect_conflict(
                test_file,
                "cli_checksum",
                "cli"
            )
            
            assert conflict_detected
            
            # 競合解決（CLI側を採用）
            with patch.object(sync_engine, 'sync_file', return_value=True) as mock_sync:
                success = await sync_engine.resolve_conflict(test_file, "cli")
                assert success
                mock_sync.assert_called_once_with(test_file, "cli", force=True)
    
    @pytest.mark.asyncio
    async def test_protocol_message_flow(self, bridge_protocol, desktop_connector):
        """プロトコルメッセージフローテスト"""
        # 各種メッセージタイプのテスト
        test_cases = [
            (MessageType.PROJECT_SWITCH, {"project_id": "test", "context": {}}),
            (MessageType.TASK_CREATE, {"task": "test task", "priority": "high"}),
            (MessageType.FILE_CHANGE, {"file_path": "/test.txt", "change_type": "modified"}),
            (MessageType.NOTIFICATION, {"title": "Test", "message": "Test notification"})
        ]
        
        for message_type, payload in test_cases:
            message = bridge_protocol.create_message(message_type, payload)
            
            # メッセージ妥当性確認
            assert bridge_protocol.validate_message(message)
            
            # JSON シリアライゼーション確認
            json_str = message.to_json()
            restored = BridgeMessage.from_json(json_str)
            assert restored.message_type == message.message_type
            assert restored.payload == message.payload
            
            # Desktop connector 経由送信テスト
            await desktop_connector.send_message(message)
            desktop_connector.websocket.send.assert_called()
    
    def test_error_handling_and_recovery(self, bridge_protocol):
        """エラーハンドリングと復旧テスト"""
        # 不正なJSONからの復元
        with pytest.raises(ValueError):
            BridgeMessage.from_json("invalid json")
        
        # 不正なメッセージ形式
        with pytest.raises(ValueError):
            BridgeMessage.from_dict({"invalid": "format"})
        
        # エラーレスポンス作成
        original = bridge_protocol.create_ping()
        error_response = bridge_protocol.create_error_response(
            original,
            "TEST_ERROR",
            "Test error message",
            {"detail": "Additional info"}
        )
        
        assert error_response.message_type == MessageType.ERROR
        assert error_response.payload["error_code"] == "TEST_ERROR"
        assert error_response.payload["details"]["detail"] == "Additional info"


if __name__ == "__main__":
    # 非同期テスト実行
    pytest.main([__file__, "-v", "--tb=short"])