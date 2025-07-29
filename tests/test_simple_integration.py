"""
Claude Bridge System - Simple Integration Test
簡易統合テスト
"""

import sys
import tempfile
import time
from pathlib import Path

# テスト対象モジュールのインポート
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_basic_imports():
    """基本的なインポートテスト"""
    try:
        from claude_bridge.core.project_registry import ProjectRegistry
        from claude_bridge.monitoring.metrics_collector import MetricsCollector
        from claude_bridge.security.auth import AuthenticationManager
        print("✓ All core modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_basic_functionality():
    """基本機能テスト"""
    try:
        # ProjectRegistry テスト
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = f.name
        
        from claude_bridge.core.project_registry import ProjectRegistry
        registry = ProjectRegistry(registry_path)
        
        test_project = {
            'name': 'test_project',
            'path': '/tmp/test',
            'type': 'python'
        }
        
        registry.register_project('test_project', test_project)
        projects = registry.list_projects()
        
        assert 'test_project' in projects
        print("✓ ProjectRegistry basic functionality works")
        
        # AuthenticationManager テスト
        from claude_bridge.security.auth import AuthenticationManager
        auth_manager = AuthenticationManager()
        
        user = auth_manager.register_user('test_user', 'test_password')
        assert user is not None
        assert user.username == 'test_user'
        
        authenticated_user = auth_manager.authenticate_password('test_user', 'test_password')
        assert authenticated_user is not None
        assert authenticated_user.username == 'test_user'
        print("✓ AuthenticationManager basic functionality works")
        
        # MetricsCollector テスト
        from claude_bridge.monitoring.metrics_collector import MetricsCollector
        metrics_collector = MetricsCollector()
        
        system_metrics = metrics_collector.get_system_metrics()
        assert hasattr(system_metrics, 'cpu_percent')
        assert hasattr(system_metrics, 'memory_percent')
        print("✓ MetricsCollector basic functionality works")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False

def test_security_features():
    """セキュリティ機能テスト"""
    try:
        from claude_bridge.security.secure_channel import SecureChannelManager
        from claude_bridge.security.audit import SecurityAuditLogger
        
        # セキュア通信テスト
        secure_channel = SecureChannelManager()
        test_message = "Test secure message"
        
        encrypted_message = secure_channel.encrypt_message(test_message)
        assert 'encrypted_data' in encrypted_message
        
        decrypted_message = secure_channel.decrypt_message(encrypted_message)
        assert decrypted_message == test_message
        print("✓ Secure communication works")
        
        # 監査ログテスト
        audit_logger = SecurityAuditLogger()
        
        event = audit_logger.log_system_event(
            action='test_action',
            result='success',
            details={'test': 'data'}
        )
        
        assert event is not None
        assert event.action == 'test_action'
        print("✓ Security audit logging works")
        
        return True
        
    except Exception as e:
        print(f"✗ Security features test failed: {e}")
        return False

def run_simple_tests():
    """簡易テスト実行"""
    print("Claude Bridge System - Simple Integration Test")
    print("=" * 50)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Basic Functionality", test_basic_functionality),
        ("Security Features", test_security_features)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"Failed: {test_name}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("Claude Bridge System basic functionality verified")
        return True
    else:
        print(f"⚠️ {total - passed} test(s) failed")
        return False

if __name__ == '__main__':
    success = run_simple_tests()
    sys.exit(0 if success else 1)