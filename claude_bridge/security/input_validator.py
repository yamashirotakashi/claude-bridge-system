#!/usr/bin/env python3
"""
Claude Bridge System - Advanced Input Validation
Comprehensive input validation to prevent injection attacks
"""

import re
import html
import urllib.parse
import json
import base64
import binascii
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import unicodedata
import ipaddress
import logging


class ValidationError(Exception):
    """Custom validation error"""
    pass


class InputType(Enum):
    """Supported input types for validation"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    EMAIL = "email"
    URL = "url"
    IP_ADDRESS = "ip_address"
    PHONE = "phone"
    USERNAME = "username"
    PASSWORD = "password"
    FILE_PATH = "file_path"
    SQL_QUERY = "sql_query"
    COMMAND = "command"
    JSON = "json"
    BASE64 = "base64"
    UUID = "uuid"
    DATE = "date"
    TIME = "time"
    REGEX = "regex"


@dataclass
class ValidationRule:
    """Input validation rule"""
    input_type: InputType
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    allowed_chars: Optional[str] = None
    forbidden_chars: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    required: bool = True
    sanitize: bool = True
    allow_empty: bool = False


@dataclass
class ValidationResult:
    """Validation result"""
    is_valid: bool
    sanitized_value: Any
    original_value: Any
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class AdvancedInputValidator:
    """Advanced input validation with security focus"""

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT)\b)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\b(OR|AND)\s+\w+\s*=\s*\w+)",
        r"(--|#|/\*|\*/)",
        r"(\b(WAITFOR|DELAY|SLEEP)\b)",
        r"(\b(XP_|SP_)\w+)",
        r"(\b(INFORMATION_SCHEMA|SYSOBJECTS|SYSCOLUMNS)\b)",
        r"(\')(;|--|\s+(OR|AND)\s+)",
        r"(\bunion\s+select\b)",
        r"(\bdrop\s+table\b)"
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]<>]",
        r"\b(rm|del|format|fdisk|dd|mkfs)\b",
        r"\b(cat|type|more|less|head|tail)\s+/",
        r"\b(wget|curl|nc|netcat|telnet|ssh)\b",
        r"\b(chmod|chown|sudo|su)\b",
        r"(\$\(|\`)",
        r"(\|\s*(rm|del|cat|wget|curl))",
        r"(;|\|)\s*(ls|dir|ps|netstat|ifconfig)"
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<embed[^>]*>",
        r"<object[^>]*>.*?</object>",
        r"<applet[^>]*>.*?</applet>",
        r"<meta[^>]*>",
        r"<link[^>]*>",
        r"<style[^>]*>.*?</style>",
        r"expression\s*\(",
        r"url\s*\(",
        r"@import"
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
        r"..%2f",
        r"..%5c",
        r"%252e%252e%252f",
        r"%252e%252e%255c"
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize validator"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default validation rules"""
        self.default_rules = {
            InputType.STRING: ValidationRule(
                input_type=InputType.STRING,
                max_length=1000,
                forbidden_chars="\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f"
            ),
            InputType.INTEGER: ValidationRule(
                input_type=InputType.INTEGER,
                min_value=-2147483648,
                max_value=2147483647
            ),
            InputType.FLOAT: ValidationRule(
                input_type=InputType.FLOAT
            ),
            InputType.EMAIL: ValidationRule(
                input_type=InputType.EMAIL,
                max_length=254,
                pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            ),
            InputType.URL: ValidationRule(
                input_type=InputType.URL,
                max_length=2048,
                pattern=r'^https?://[^\s/$.?#].[^\s]*$'
            ),
            InputType.USERNAME: ValidationRule(
                input_type=InputType.USERNAME,
                min_length=3,
                max_length=32,
                pattern=r'^[a-zA-Z0-9_-]+$'
            ),
            InputType.FILE_PATH: ValidationRule(
                input_type=InputType.FILE_PATH,
                max_length=260,
                forbidden_chars="<>:\"|?*\x00"
            ),
            InputType.UUID: ValidationRule(
                input_type=InputType.UUID,
                pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
            )
        }

    def validate_input(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate input against rule"""
        errors = []
        warnings = []
        metadata = {}
        original_value = value

        try:
            # Handle None/empty values
            if value is None or (isinstance(value, str) and not value.strip()):
                if rule.required and not rule.allow_empty:
                    errors.append("Value is required")
                    return ValidationResult(False, None, original_value, errors, warnings, metadata)
                elif rule.allow_empty:
                    return ValidationResult(True, value, original_value, errors, warnings, metadata)

            # Type-specific validation
            validated_value = self._validate_by_type(value, rule, errors, warnings, metadata)
            
            if errors:
                return ValidationResult(False, None, original_value, errors, warnings, metadata)

            # Security checks
            self._security_checks(validated_value, rule, errors, warnings, metadata)
            
            # Sanitization
            if rule.sanitize and isinstance(validated_value, str):
                validated_value = self._sanitize_string(validated_value, rule)

            is_valid = len(errors) == 0
            return ValidationResult(is_valid, validated_value, original_value, errors, warnings, metadata)

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            errors.append(f"Internal validation error: {str(e)}")
            return ValidationResult(False, None, original_value, errors, warnings, metadata)

    def _validate_by_type(self, value: Any, rule: ValidationRule, errors: List[str], 
                         warnings: List[str], metadata: Dict[str, Any]) -> Any:
        """Type-specific validation"""
        
        if rule.input_type == InputType.STRING:
            return self._validate_string(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.INTEGER:
            return self._validate_integer(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.FLOAT:
            return self._validate_float(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.BOOLEAN:
            return self._validate_boolean(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.EMAIL:
            return self._validate_email(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.URL:
            return self._validate_url(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.IP_ADDRESS:
            return self._validate_ip_address(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.USERNAME:
            return self._validate_username(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.FILE_PATH:
            return self._validate_file_path(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.JSON:
            return self._validate_json(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.BASE64:
            return self._validate_base64(value, rule, errors, warnings, metadata)
        elif rule.input_type == InputType.UUID:
            return self._validate_uuid(value, rule, errors, warnings, metadata)
        else:
            return str(value)  # Default string conversion

    def _validate_string(self, value: Any, rule: ValidationRule, errors: List[str], 
                        warnings: List[str], metadata: Dict[str, Any]) -> str:
        """Validate string input"""
        if not isinstance(value, str):
            value = str(value)

        # Length checks
        if rule.min_length and len(value) < rule.min_length:
            errors.append(f"String too short (minimum {rule.min_length} characters)")
        if rule.max_length and len(value) > rule.max_length:
            errors.append(f"String too long (maximum {rule.max_length} characters)")

        # Character restrictions
        if rule.allowed_chars:
            invalid_chars = set(value) - set(rule.allowed_chars)
            if invalid_chars:
                errors.append(f"Contains invalid characters: {', '.join(invalid_chars)}")

        if rule.forbidden_chars:
            forbidden_found = set(value) & set(rule.forbidden_chars)
            if forbidden_found:
                errors.append(f"Contains forbidden characters: {', '.join(forbidden_found)}")

        # Pattern matching
        if rule.pattern:
            if not re.match(rule.pattern, value, re.IGNORECASE):
                errors.append("String does not match required pattern")

        # Unicode normalization
        value = unicodedata.normalize('NFKC', value)
        
        return value

    def _validate_integer(self, value: Any, rule: ValidationRule, errors: List[str], 
                         warnings: List[str], metadata: Dict[str, Any]) -> int:
        """Validate integer input"""
        try:
            if isinstance(value, str):
                # Remove whitespace and check for suspicious patterns
                value = value.strip()
                if not value.isdigit() and not (value.startswith('-') and value[1:].isdigit()):
                    raise ValueError("Not a valid integer")
            
            int_value = int(value)
            
            if rule.min_value is not None and int_value < rule.min_value:
                errors.append(f"Value too small (minimum {rule.min_value})")
            if rule.max_value is not None and int_value > rule.max_value:
                errors.append(f"Value too large (maximum {rule.max_value})")
                
            if rule.allowed_values and int_value not in rule.allowed_values:
                errors.append(f"Value not in allowed list: {rule.allowed_values}")
                
            return int_value
            
        except (ValueError, TypeError):
            errors.append("Invalid integer value")
            return 0

    def _validate_float(self, value: Any, rule: ValidationRule, errors: List[str], 
                       warnings: List[str], metadata: Dict[str, Any]) -> float:
        """Validate float input"""
        try:
            float_value = float(value)
            
            if rule.min_value is not None and float_value < rule.min_value:
                errors.append(f"Value too small (minimum {rule.min_value})")
            if rule.max_value is not None and float_value > rule.max_value:
                errors.append(f"Value too large (maximum {rule.max_value})")
                
            return float_value
            
        except (ValueError, TypeError):
            errors.append("Invalid float value")
            return 0.0

    def _validate_boolean(self, value: Any, rule: ValidationRule, errors: List[str], 
                         warnings: List[str], metadata: Dict[str, Any]) -> bool:
        """Validate boolean input"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ('true', '1', 'yes', 'on'):
                return True
            elif value_lower in ('false', '0', 'no', 'off'):
                return False
            else:
                errors.append("Invalid boolean value")
                return False
        elif isinstance(value, (int, float)):
            return bool(value)
        else:
            errors.append("Invalid boolean value")
            return False

    def _validate_email(self, value: Any, rule: ValidationRule, errors: List[str], 
                       warnings: List[str], metadata: Dict[str, Any]) -> str:
        """Validate email input"""
        if not isinstance(value, str):
            errors.append("Email must be a string")
            return str(value)

        value = value.strip().lower()
        
        # Basic format check
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            errors.append("Invalid email format")
            
        # Additional security checks
        if '..' in value or value.startswith('.') or value.endswith('.'):
            errors.append("Invalid email format (consecutive dots)")
            
        # Check for suspicious patterns
        suspicious_patterns = ['script', 'javascript', 'data:', 'vbscript']
        for pattern in suspicious_patterns:
            if pattern in value.lower():
                warnings.append(f"Email contains suspicious pattern: {pattern}")
                
        return value

    def _validate_url(self, value: Any, rule: ValidationRule, errors: List[str], 
                     warnings: List[str], metadata: Dict[str, Any]) -> str:
        """Validate URL input"""
        if not isinstance(value, str):
            errors.append("URL must be a string")
            return str(value)

        value = value.strip()
        
        # Basic URL format
        if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', value, re.IGNORECASE):
            errors.append("Invalid URL format")
            
        # Security checks - only allow HTTP/HTTPS
        if not (value.lower().startswith('http://') or value.lower().startswith('https://')):
            errors.append("Only HTTP and HTTPS URLs are allowed")
            
        # Check for suspicious patterns
        suspicious_patterns = ['javascript:', 'data:', 'file:', 'ftp:', 'vbscript:']
        for pattern in suspicious_patterns:
            if pattern in value.lower():
                errors.append(f"Suspicious URL scheme detected: {pattern}")
                
        return value

    def _validate_ip_address(self, value: Any, rule: ValidationRule, errors: List[str], 
                           warnings: List[str], metadata: Dict[str, Any]) -> str:
        """Validate IP address input"""
        if not isinstance(value, str):
            value = str(value)

        value = value.strip()
        
        try:
            ip = ipaddress.ip_address(value)
            
            # Check for private/reserved addresses
            if ip.is_private:
                metadata['is_private'] = True
            if ip.is_reserved:
                metadata['is_reserved'] = True
            if ip.is_loopback:
                metadata['is_loopback'] = True
                
            return str(ip)
            
        except ValueError:
            errors.append("Invalid IP address format")
            return value

    def _validate_username(self, value: Any, rule: ValidationRule, errors: List[str], 
                          warnings: List[str], metadata: Dict[str, Any]) -> str:
        """Validate username input"""
        if not isinstance(value, str):
            value = str(value)

        value = value.strip()
        
        # Length checks
        if len(value) < 3:
            errors.append("Username too short (minimum 3 characters)")
        if len(value) > 32:
            errors.append("Username too long (maximum 32 characters)")
            
        # Character checks
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            errors.append("Username contains invalid characters (only letters, numbers, _ and - allowed)")
            
        # Reserved usernames
        reserved = ['admin', 'root', 'system', 'administrator', 'test', 'guest', 'anonymous']
        if value.lower() in reserved:
            warnings.append("Username is commonly reserved")
            
        return value

    def _validate_file_path(self, value: Any, rule: ValidationRule, errors: List[str], 
                           warnings: List[str], metadata: Dict[str, Any]) -> str:
        """Validate file path input"""
        if not isinstance(value, str):
            value = str(value)

        value = value.strip()
        
        # Path traversal check
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                errors.append("Path traversal attempt detected")
                break
                
        # Forbidden characters
        forbidden_chars = '<>:"|?*\x00'
        if any(char in value for char in forbidden_chars):
            errors.append("File path contains forbidden characters")
            
        # Absolute path check
        if value.startswith('/') or (len(value) > 1 and value[1] == ':'):
            warnings.append("Absolute path detected")
            metadata['is_absolute'] = True
            
        return value

    def _validate_json(self, value: Any, rule: ValidationRule, errors: List[str], 
                      warnings: List[str], metadata: Dict[str, Any]) -> Any:
        """Validate JSON input"""
        if isinstance(value, (dict, list)):
            return value
            
        if not isinstance(value, str):
            value = str(value)

        try:
            parsed = json.loads(value)
            return parsed
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {str(e)}")
            return None

    def _validate_base64(self, value: Any, rule: ValidationRule, errors: List[str], 
                        warnings: List[str], metadata: Dict[str, Any]) -> str:
        """Validate Base64 input"""
        if not isinstance(value, str):
            value = str(value)

        value = value.strip()
        
        try:
            decoded = base64.b64decode(value, validate=True)
            metadata['decoded_size'] = len(decoded)
            return value
        except (binascii.Error, ValueError):
            errors.append("Invalid Base64 encoding")
            return value

    def _validate_uuid(self, value: Any, rule: ValidationRule, errors: List[str], 
                      warnings: List[str], metadata: Dict[str, Any]) -> str:
        """Validate UUID input"""
        if not isinstance(value, str):
            value = str(value)

        value = value.strip().lower()
        
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, value):
            errors.append("Invalid UUID format")
            
        return value

    def _security_checks(self, value: Any, rule: ValidationRule, errors: List[str], 
                        warnings: List[str], metadata: Dict[str, Any]):
        """Perform security-focused checks"""
        if not isinstance(value, str):
            return

        value_lower = value.lower()
        
        # SQL injection check
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE | re.MULTILINE):
                errors.append("Potential SQL injection detected")
                metadata['security_threat'] = 'sql_injection'
                break

        # Command injection check
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                errors.append("Potential command injection detected")
                metadata['security_threat'] = 'command_injection'
                break

        # XSS check
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE | re.DOTALL):
                errors.append("Potential XSS detected")
                metadata['security_threat'] = 'xss'
                break

        # Path traversal check
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, value_lower):
                errors.append("Potential path traversal detected")
                metadata['security_threat'] = 'path_traversal'
                break

    def _sanitize_string(self, value: str, rule: ValidationRule) -> str:
        """Sanitize string input"""
        # HTML encode
        value = html.escape(value)
        
        # Remove null bytes and control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        # Normalize unicode
        value = unicodedata.normalize('NFKC', value)
        
        return value

    def validate_batch(self, inputs: Dict[str, Any], rules: Dict[str, ValidationRule]) -> Dict[str, ValidationResult]:
        """Validate multiple inputs at once"""
        results = {}
        
        for key, value in inputs.items():
            if key in rules:
                results[key] = self.validate_input(value, rules[key])
            else:
                # Use default string validation
                default_rule = self.default_rules.get(InputType.STRING, ValidationRule(InputType.STRING))
                results[key] = self.validate_input(value, default_rule)
                
        return results

    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get summary of validation results"""
        total = len(results)
        valid = sum(1 for r in results.values() if r.is_valid)
        invalid = total - valid
        
        all_errors = []
        all_warnings = []
        security_threats = []
        
        for key, result in results.items():
            for error in result.errors:
                all_errors.append(f"{key}: {error}")
            for warning in result.warnings:
                all_warnings.append(f"{key}: {warning}")
            if 'security_threat' in result.metadata:
                security_threats.append(f"{key}: {result.metadata['security_threat']}")
        
        return {
            'total_inputs': total,
            'valid_inputs': valid,
            'invalid_inputs': invalid,
            'validation_rate': (valid / total * 100) if total > 0 else 0,
            'errors': all_errors,
            'warnings': all_warnings,
            'security_threats': security_threats,
            'has_security_issues': len(security_threats) > 0
        }


def main():
    """Demo input validation functionality"""
    validator = AdvancedInputValidator()
    
    # Test various inputs
    test_inputs = {
        'username': 'test_user123',
        'email': 'user@example.com',
        'age': '25',
        'password': 'SecurePass123!',
        'sql_query': "'; DROP TABLE users; --",
        'file_path': '../../../etc/passwd',
        'script_tag': '<script>alert("xss")</script>',
        'command': 'ls -la; rm -rf /',
        'url': 'https://example.com/page?id=1',
        'json_data': '{"name": "test", "value": 123}',
        'uuid': '123e4567-e89b-12d3-a456-426614174000'
    }
    
    # Define rules
    validation_rules = {
        'username': ValidationRule(InputType.USERNAME),
        'email': ValidationRule(InputType.EMAIL),
        'age': ValidationRule(InputType.INTEGER, min_value=0, max_value=150),
        'password': ValidationRule(InputType.STRING, min_length=8),
        'sql_query': ValidationRule(InputType.STRING),
        'file_path': ValidationRule(InputType.FILE_PATH),
        'script_tag': ValidationRule(InputType.STRING),
        'command': ValidationRule(InputType.COMMAND),
        'url': ValidationRule(InputType.URL),
        'json_data': ValidationRule(InputType.JSON),
        'uuid': ValidationRule(InputType.UUID)
    }
    
    print("🔍 Advanced Input Validation Demo")
    print("=" * 50)
    
    # Validate inputs
    results = validator.validate_batch(test_inputs, validation_rules)
    
    for key, result in results.items():
        print(f"\nInput: {key} = '{test_inputs[key]}'")
        print(f"Valid: {result.is_valid}")
        print(f"Sanitized: '{result.sanitized_value}'")
        
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")
                
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
                
        if result.metadata:
            print(f"Metadata: {result.metadata}")
    
    # Summary
    summary = validator.get_validation_summary(results)
    print(f"\n📊 Validation Summary:")
    print(f"Total inputs: {summary['total_inputs']}")
    print(f"Valid: {summary['valid_inputs']}")
    print(f"Invalid: {summary['invalid_inputs']}")
    print(f"Validation rate: {summary['validation_rate']:.1f}%")
    print(f"Security threats detected: {len(summary['security_threats'])}")
    
    if summary['security_threats']:
        print("\n🚨 Security Threats:")
        for threat in summary['security_threats']:
            print(f"  ⚠️ {threat}")


if __name__ == "__main__":
    main()