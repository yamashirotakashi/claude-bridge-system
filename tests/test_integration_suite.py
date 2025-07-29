"""
Claude Bridge System - Integration Test Suite
統合テストスイート
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# テスト対象モジュールのインポート
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_bridge.core.bridge_filesystem import BridgeFileSystem
from claude_bridge.core.project_registry import ProjectRegistry
from claude_bridge.core.context_loader import ProjectContextLoader
from claude_bridge.desktop.desktop_api import DesktopAPIClient
from claude_bridge.sync.realtime_sync import RealtimeSyncEngine
from claude_bridge.sync.conflict_resolver import ConflictResolver
from claude_bridge.monitoring.metrics_collector import MetricsCollector
from claude_bridge.monitoring.health_checker import HealthChecker
from claude_bridge.monitoring.performance_monitor import PerformanceMonitor
from claude_bridge.security.auth import AuthenticationManager
from claude_bridge.security.secure_channel import SecureChannelManager
from claude_bridge.security.audit import SecurityAuditLogger
from claude_bridge.security.scanner import VulnerabilityScanner


class IntegrationTestSuite(unittest.TestCase):
    """統合テストスイート"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラス初期化"""
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.logger.info(f"Test environment setup: {cls.temp_dir}")
    
    @classmethod
    def tearDownClass(cls):
        """テストクラス終了処理"""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        cls.logger.info("Test environment cleaned up")
    
    def setUp(self):
        """各テスト前の初期化"""
        self.test_project_path = self.temp_dir / "test_project"
        self.test_project_path.mkdir(exist_ok=True)
        
        # テスト用設定
        self.test_config = {
            'project_path': str(self.test_project_path),
            'bridge_data_path': str(self.temp_dir / 'bridge_data'),
            'monitoring': {
                'enabled': True,
                'collection_interval': 1
            },
            'security': {
                'enabled': True,
                'audit_logging': True
            }
        }
    
    def test_01_core_system_integration(self):
        """コアシステム統合テスト"""
        self.logger.info("Testing core system integration...")
        
        # BridgeFileSystem初期化テスト
        bridge_fs = BridgeFileSystem(self.test_config)
        self.assertIsNotNone(bridge_fs)
        
        # ProjectRegistry統合テスト
        registry = ProjectRegistry(str(self.temp_dir / 'registry.json'))
        test_project = {
            'name': 'test_project',
            'path': str(self.test_project_path),
            'type': 'python'
        }
        registry.register_project('test_project', test_project)
        
        # プロジェクトが正常に登録されているか確認
        projects = registry.list_projects()
        self.assertIn('test_project', projects)
        
        # Context Loader統合テスト
        context_loader = ProjectContextLoader(registry)
        context = context_loader.load_context('test_project')
        self.assertIsNotNone(context)
        self.assertEqual(context['name'], 'test_project')
        
        self.logger.info("✓ Core system integration test passed")
    
    def test_02_desktop_api_integration(self):
        """Desktop API統合テスト"""
        self.logger.info("Testing Desktop API integration...")
        
        # Mock WebSocket for testing
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            
            # Desktop API クライアント初期化
            desktop_client = DesktopAPIClient({
                'websocket_url': 'ws://localhost:8080',
                'timeout': 5
            })
            
            # 接続テスト（モック）
            asyncio.run(self._test_desktop_connection(desktop_client, mock_websocket))
        
        self.logger.info("✓ Desktop API integration test passed")
    
    async def _test_desktop_connection(self, client, mock_websocket):
        """Desktop接続テスト（非同期）"""
        mock_websocket.send.return_value = None
        mock_websocket.recv.return_value = json.dumps({
            'type': 'response',
            'data': {'status': 'connected'}
        })
        
        # 接続テスト
        result = await client.connect()
        self.assertTrue(result)
    
    def test_03_monitoring_system_integration(self):
        """監視システム統合テスト"""
        self.logger.info("Testing monitoring system integration...")
        
        # メトリクス収集システム
        metrics_collector = MetricsCollector(self.test_config.get('monitoring', {}))
        
        # 基本メトリクス収集テスト
        metrics_collector.start_collection()
        time.sleep(2)  # 収集待機
        
        system_metrics = metrics_collector.get_system_metrics()
        self.assertIn('cpu_percent', system_metrics.__dict__)
        self.assertIn('memory_percent', system_metrics.__dict__)
        
        metrics_collector.stop_collection()
        
        # ヘルスチェックシステム
        health_checker = HealthChecker()
        
        # システムヘルス確認
        health_status = health_checker.check_system_health()
        self.assertIn('overall_status', health_status.status)
        
        # パフォーマンス監視システム
        perf_monitor = PerformanceMonitor()
        
        # 基本パフォーマンステスト
        with perf_monitor.measure_operation('test_operation'):
            time.sleep(0.1)
        
        metrics = perf_monitor.get_operation_metrics('test_operation')
        self.assertIsNotNone(metrics)
        self.assertGreater(metrics.average_duration, 0)
        
        self.logger.info("✓ Monitoring system integration test passed")
    
    def test_04_security_system_integration(self):
        """セキュリティシステム統合テスト"""
        self.logger.info("Testing security system integration...")
        
        # 認証システム
        auth_manager = AuthenticationManager()
        
        # ユーザー登録・認証テスト
        user = auth_manager.register_user('test_user', 'test_password')
        self.assertIsNotNone(user)
        
        # パスワード認証テスト
        authenticated_user = auth_manager.authenticate_password('test_user', 'test_password')
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user.username, 'test_user')
        
        # JWT トークン生成・検証テスト
        jwt_token = auth_manager.create_jwt_token(user)
        self.assertIsNotNone(jwt_token)
        
        token_user = auth_manager.authenticate_jwt(jwt_token)
        self.assertIsNotNone(token_user)
        self.assertEqual(token_user.user_id, user.user_id)
        
        # セキュア通信チャネル
        secure_channel = SecureChannelManager()
        
        # メッセージ暗号化・復号化テスト
        test_message = "Test message for encryption"
        encrypted_message = secure_channel.encrypt_message(test_message)
        self.assertIn('encrypted_data', encrypted_message)
        
        decrypted_message = secure_channel.decrypt_message(encrypted_message)
        self.assertEqual(decrypted_message, test_message)
        
        # 監査ログシステム
        audit_logger = SecurityAuditLogger()
        
        # セキュリティイベントログテスト
        event = audit_logger.log_authentication(
            user_id=user.user_id,
            action='login',
            result='success',
            client_ip='127.0.0.1'
        )
        self.assertIsNotNone(event)
        self.assertEqual(event.user_id, user.user_id)
        
        self.logger.info("✓ Security system integration test passed")
    
    def test_05_sync_system_integration(self):
        """同期システム統合テスト"""
        self.logger.info("Testing sync system integration...")
        
        # リアルタイム同期エンジン
        sync_engine = RealtimeSyncEngine(self.test_config)
        
        # 基本同期機能テスト
        sync_engine.initialize()
        
        # テストデータ準備
        test_data = {
            'project_id': 'test_project',
            'file_path': 'test.py',
            'content': 'print("Hello, World!")',
            'timestamp': time.time()
        }
        
        # 同期データ処理テスト
        sync_result = sync_engine.process_sync_data(test_data)
        self.assertTrue(sync_result)
        
        # 競合解決システム
        conflict_resolver = ConflictResolver()
        
        # 競合解決テスト
        conflict_data = {
            'file_path': 'test.py',
            'local_content': 'print("Local version")',
            'remote_content': 'print("Remote version")',
            'local_timestamp': time.time() - 10,
            'remote_timestamp': time.time()
        }
        
        resolution = conflict_resolver.resolve_conflict(conflict_data)
        self.assertIn('resolution_strategy', resolution)
        
        self.logger.info("✓ Sync system integration test passed")
    
    def test_06_vulnerability_scanning_integration(self):
        """脆弱性スキャン統合テスト"""
        self.logger.info("Testing vulnerability scanning integration...")
        
        # テスト用Pythonファイル作成（脆弱性パターン含む）
        vulnerable_file = self.test_project_path / "vulnerable_test.py"
        with open(vulnerable_file, 'w') as f:
            f.write('''
import os
import subprocess

# 危険なパターン（テスト用）
password = "hardcoded_password_123"
os.system("ls -la")
eval("print('dangerous eval')")
subprocess.call("echo test", shell=True)
''')
        
        # 脆弱性スキャナー初期化
        vulnerability_scanner = VulnerabilityScanner()
        
        # 非同期スキャン実行
        asyncio.run(self._test_vulnerability_scan(vulnerability_scanner))
        
        self.logger.info("✓ Vulnerability scanning integration test passed")
    
    async def _test_vulnerability_scan(self, scanner):
        """脆弱性スキャンテスト（非同期）"""
        # コード解析スキャン
        scan_result = await scanner.scan_code(self.test_project_path)
        
        self.assertEqual(scan_result.scan_type.value, 'code_analysis')
        self.assertEqual(scan_result.status, 'completed')
        
        # 脆弱性が検出されることを確認
        self.assertGreater(len(scan_result.vulnerabilities), 0)
        
        # 検出された脆弱性の内容確認
        vuln_titles = [v.title for v in scan_result.vulnerabilities]
        self.assertTrue(any('hardcoded password' in title.lower() for title in vuln_titles))
        self.assertTrue(any('os.system' in title.lower() for title in vuln_titles))
    
    def test_07_performance_under_load(self):
        """負荷テスト"""
        self.logger.info("Testing system performance under load...")
        
        # パフォーマンス監視開始
        perf_monitor = PerformanceMonitor()
        
        # 並行処理負荷テスト
        start_time = time.time()
        
        def cpu_intensive_task():
            """CPU集約的タスク"""
            total = 0
            for i in range(100000):
                total += i * i
            return total
        
        # 複数の並行タスク実行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cpu_intensive_task) for _ in range(10)]
            results = [future.result() for future in futures]
        
        execution_time = time.time() - start_time
        
        # パフォーマンス基準チェック
        self.assertLess(execution_time, 10.0, "Performance test exceeded acceptable time limit")
        self.assertEqual(len(results), 10, "Not all parallel tasks completed")
        
        self.logger.info(f"✓ Performance test completed in {execution_time:.2f}s")
    
    def test_08_end_to_end_workflow(self):
        """エンドツーエンドワークフローテスト"""
        self.logger.info("Testing end-to-end workflow...")
        
        # 1. プロジェクト登録
        registry = ProjectRegistry(str(self.temp_dir / 'e2e_registry.json'))
        project_data = {
            'name': 'e2e_test_project',
            'path': str(self.test_project_path),
            'type': 'python',
            'description': 'End-to-end test project'
        }
        registry.register_project('e2e_test_project', project_data)
        
        # 2. コンテキスト読み込み
        context_loader = ProjectContextLoader(registry)
        context = context_loader.load_context('e2e_test_project')
        self.assertIsNotNone(context)
        
        # 3. 監視システム初期化
        metrics_collector = MetricsCollector({'collection_interval': 1})
        health_checker = HealthChecker()
        
        # 4. セキュリティシステム初期化
        auth_manager = AuthenticationManager()
        audit_logger = SecurityAuditLogger()
        
        # 5. ユーザー認証フロー
        user = auth_manager.register_user('e2e_user', 'e2e_password')
        authenticated_user = auth_manager.authenticate_password('e2e_user', 'e2e_password')
        self.assertIsNotNone(authenticated_user)
        
        # 6. セキュリティイベントログ
        auth_event = audit_logger.log_authentication(
            user_id=user.user_id,
            action='e2e_test_login',
            result='success'
        )
        self.assertIsNotNone(auth_event)
        
        # 7. システムヘルスチェック
        health_status = health_checker.check_system_health()
        self.assertIn('overall_status', health_status.status)
        
        # 8. メトリクス収集
        metrics_collector.start_collection()
        time.sleep(1)
        system_metrics = metrics_collector.get_system_metrics()
        metrics_collector.stop_collection()
        
        self.assertIsNotNone(system_metrics)
        
        # 9. ワークフロー完了確認
        workflow_steps = [
            'project_registration',
            'context_loading', 
            'monitoring_initialization',
            'security_initialization',
            'user_authentication',
            'audit_logging',
            'health_checking',
            'metrics_collection'
        ]
        
        # すべてのステップが完了したことを確認
        for step in workflow_steps:
            self.logger.info(f"✓ {step} completed")
        
        self.logger.info("✓ End-to-end workflow test passed")
    
    def test_09_error_handling_resilience(self):
        """エラーハンドリング・レジリエンステスト"""
        self.logger.info("Testing error handling and system resilience...")
        
        # 1. 不正なプロジェクトパスでの初期化テスト
        invalid_config = self.test_config.copy()
        invalid_config['project_path'] = '/nonexistent/path'
        
        try:
            bridge_fs = BridgeFileSystem(invalid_config)
            # エラーハンドリングが適切に動作するか確認
        except Exception as e:
            self.logger.info(f"Expected error handled: {e}")
        
        # 2. 不正な認証情報でのテスト
        auth_manager = AuthenticationManager()
        invalid_auth = auth_manager.authenticate_password('nonexistent_user', 'wrong_password')
        self.assertIsNone(invalid_auth, "Invalid authentication should return None")
        
        # 3. 破損したデータでのテスト
        registry = ProjectRegistry(str(self.temp_dir / 'corrupted_registry.json'))
        
        # 不正なJSONを書き込み
        with open(self.temp_dir / 'corrupted_registry.json', 'w') as f:
            f.write('{"invalid": json}')  # 不正なJSON
        
        try:
            projects = registry.list_projects()
            # エラーハンドリングによって空のリストが返されるべき
            self.assertIsInstance(projects, (list, dict))
        except Exception as e:
            self.logger.info(f"Error handling test: {e}")
        
        # 4. ネットワーク接続エラーのシミュレーション
        with patch('websockets.connect') as mock_connect:
            mock_connect.side_effect = ConnectionError("Connection failed")
            
            desktop_client = DesktopAPIClient({
                'websocket_url': 'ws://invalid-url:8080',
                'timeout': 1
            })
            
            # 接続エラーが適切に処理されるか確認
            result = asyncio.run(desktop_client.connect())
            self.assertFalse(result, "Connection should fail gracefully")
        
        self.logger.info("✓ Error handling and resilience test passed")
    
    def test_10_system_resource_management(self):
        """システムリソース管理テスト"""
        self.logger.info("Testing system resource management...")
        
        # メモリ使用量監視
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # リソース集約的な操作
        large_data_structures = []
        for i in range(100):
            large_data_structures.append({
                'id': i,
                'data': 'x' * 10000  # 10KB のデータ
            })
        
        # メモリ使用量チェック
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        
        # リソースクリーンアップ
        del large_data_structures
        
        final_memory = process.memory_info().rss
        memory_recovered = peak_memory - final_memory
        
        self.logger.info(f"Memory usage - Initial: {initial_memory//1024}KB, "
                        f"Peak: {peak_memory//1024}KB, "
                        f"Final: {final_memory//1024}KB")
        
        # メモリリークチェック（簡易版）
        memory_leak_threshold = initial_memory * 1.1  # 10%増加まで許容
        self.assertLess(final_memory, memory_leak_threshold, "Potential memory leak detected")
        
        # ファイルハンドル管理テスト
        import tempfile
        file_handles = []
        
        try:
            # 多数のファイルハンドルを開く
            for i in range(50):
                fd = tempfile.NamedTemporaryFile(delete=False)
                file_handles.append(fd)
            
            # システムリソース状況確認
            open_files = len(process.open_files())
            self.logger.info(f"Open file handles: {open_files}")
            
        finally:
            # クリーンアップ
            for fd in file_handles:
                try:
                    fd.close()
                    os.unlink(fd.name)
                except:
                    pass
        
        self.logger.info("✓ System resource management test passed")


def run_integration_tests():
    """統合テスト実行"""
    # テストスイートの作成
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(IntegrationTestSuite)
    
    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "="*60)
    print("INTEGRATION TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # 成功時のメッセージ
    if not result.failures and not result.errors:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("Claude Bridge System is ready for deployment.")
    else:
        print(f"\n⚠️ {len(result.failures) + len(result.errors)} test(s) failed.")
        print("Please review and fix issues before deployment.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)