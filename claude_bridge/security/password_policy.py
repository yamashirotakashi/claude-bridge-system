#!/usr/bin/env python3
"""
Claude Bridge System - Password Policy and Validation
Implements secure password policies and validation rules
"""

import re
import hashlib
import secrets
import string
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import json


class PasswordStrength(Enum):
    """Password strength levels"""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    FAIR = "fair"
    GOOD = "good"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class PasswordRequirement:
    """Password requirement definition"""
    name: str
    description: str
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    required: bool = True
    weight: float = 1.0


@dataclass
class PasswordValidationResult:
    """Password validation result"""
    is_valid: bool
    strength: PasswordStrength
    score: int
    max_score: int
    failed_requirements: List[str]
    suggestions: List[str]
    entropy: float


class PasswordPolicy:
    """Enhanced password policy manager"""

    # Common weak passwords and patterns
    COMMON_PASSWORDS = {
        "password", "123456", "123456789", "qwerty", "abc123", "password123",
        "admin", "letmein", "welcome", "monkey", "login", "dragon", "ninja",
        "football", "baseball", "master", "shadow", "michael", "jennifer",
        "123123", "000000", "111111", "password1", "qwerty123", "123qwe"
    }

    # Common patterns to avoid
    WEAK_PATTERNS = [
        r'^(.)\1{3,}$',  # Repeating characters
        r'^(012|123|234|345|456|567|678|789|890)+$',  # Sequential numbers
        r'^(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)+$',  # Sequential letters
        r'^(qwe|wer|ert|rty|tyu|yui|uio|iop|asd|sdf|dfg|fgh|ghj|hjk|jkl|zxc|xcv|cvb|vbn|bnm)+$',  # Keyboard patterns
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize password policy"""
        self.config = config or {}
        self._setup_requirements()
        self._load_breach_database()

    def _setup_requirements(self):
        """Setup password requirements"""
        self.requirements = [
            PasswordRequirement(
                name="min_length",
                description="Minimum 12 characters",
                min_length=12,
                weight=2.0
            ),
            PasswordRequirement(
                name="max_length",
                description="Maximum 128 characters",
                max_length=128,
                required=False,
                weight=0.5
            ),
            PasswordRequirement(
                name="uppercase",
                description="At least 2 uppercase letters",
                pattern=r'(?=.*[A-Z].*[A-Z])',
                weight=1.0
            ),
            PasswordRequirement(
                name="lowercase",
                description="At least 2 lowercase letters",
                pattern=r'(?=.*[a-z].*[a-z])',
                weight=1.0
            ),
            PasswordRequirement(
                name="digits",
                description="At least 2 digits",
                pattern=r'(?=.*\d.*\d)',
                weight=1.0
            ),
            PasswordRequirement(
                name="special_chars",
                description="At least 2 special characters",
                pattern=r'(?=.*[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?].*[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?])',
                weight=1.5
            ),
            PasswordRequirement(
                name="no_common_words",
                description="No common dictionary words",
                required=True,
                weight=2.0
            ),
            PasswordRequirement(
                name="no_personal_info",
                description="No personal information",
                required=True,
                weight=2.0
            ),
            PasswordRequirement(
                name="no_sequential",
                description="No sequential characters",
                required=True,
                weight=1.5
            ),
            PasswordRequirement(
                name="mixed_case_numbers",
                description="Mix of upper, lower, numbers, symbols in different positions",
                required=False,
                weight=1.0
            )
        ]

    def _load_breach_database(self):
        """Load known breached passwords (simplified for demo)"""
        # In production, this would load from a real breach database
        self.breached_passwords = set()
        # Add some example breached password hashes
        common_breached = [
            "password", "123456", "password123", "admin", "qwerty123",
            "letmein", "welcome123", "password1", "123456789", "qwerty"
        ]
        for pwd in common_breached:
            self.breached_passwords.add(self._hash_password(pwd))

    def _hash_password(self, password: str) -> str:
        """Hash password for comparison"""
        return hashlib.sha256(password.lower().encode()).hexdigest()

    def validate_password(self, password: str, user_info: Optional[Dict[str, str]] = None) -> PasswordValidationResult:
        """Comprehensive password validation"""
        if not password:
            return PasswordValidationResult(
                is_valid=False,
                strength=PasswordStrength.VERY_WEAK,
                score=0,
                max_score=100,
                failed_requirements=["Password is required"],
                suggestions=["Please provide a password"],
                entropy=0.0
            )

        score = 0
        max_score = 100
        failed_requirements = []
        suggestions = []

        # Check basic requirements
        for req in self.requirements:
            req_met = True
            req_score = int(req.weight * 10)  # Convert weight to score
            
            if req.min_length and len(password) < req.min_length:
                req_met = False
                if req.required:
                    failed_requirements.append(f"Password must be at least {req.min_length} characters")
                    suggestions.append(f"Add more characters (need {req.min_length - len(password)} more)")

            if req.max_length and len(password) > req.max_length:
                req_met = False
                if req.required:
                    failed_requirements.append(f"Password must be no more than {req.max_length} characters")
                    suggestions.append(f"Reduce length by {len(password) - req.max_length} characters")

            if req.pattern and not re.search(req.pattern, password):
                req_met = False
                if req.required:
                    failed_requirements.append(req.description)
                    suggestions.append(self._get_pattern_suggestion(req.name))

            # Special checks
            if req.name == "no_common_words":
                if password.lower() in self.COMMON_PASSWORDS:
                    req_met = False
                    failed_requirements.append("Password is too common")
                    suggestions.append("Use a unique password that's not commonly used")

            if req.name == "no_personal_info" and user_info:
                if self._contains_personal_info(password, user_info):
                    req_met = False
                    failed_requirements.append("Password contains personal information")
                    suggestions.append("Don't use personal information like name, email, or birthday")

            if req.name == "no_sequential":
                if self._has_sequential_chars(password):
                    req_met = False
                    failed_requirements.append("Password contains sequential characters")
                    suggestions.append("Avoid sequences like '123', 'abc', or keyboard patterns")

            if req_met:
                score += req_score

        # Check against breach database
        pwd_hash = self._hash_password(password)
        if pwd_hash in self.breached_passwords:
            failed_requirements.append("Password found in data breach database")
            suggestions.append("This password has been compromised. Choose a different one.")
            score = max(0, score - 20)  # Heavy penalty for breached passwords

        # Calculate entropy
        entropy = self._calculate_entropy(password)
        if entropy < 50:
            suggestions.append("Increase password complexity for better security")
        elif entropy > 80:
            score += 5  # Bonus for high entropy

        # Determine strength
        strength = self._calculate_strength(score, max_score, entropy)
        is_valid = score >= 70 and len(failed_requirements) == 0  # At least 70% score and no critical failures

        return PasswordValidationResult(
            is_valid=is_valid,
            strength=strength,
            score=score,
            max_score=max_score,
            failed_requirements=failed_requirements,
            suggestions=suggestions,
            entropy=entropy
        )

    def _get_pattern_suggestion(self, requirement_name: str) -> str:
        """Get helpful suggestion for pattern requirements"""
        suggestions = {
            "uppercase": "Add at least 2 uppercase letters (A-Z)",
            "lowercase": "Add at least 2 lowercase letters (a-z)",  
            "digits": "Add at least 2 numbers (0-9)",
            "special_chars": "Add at least 2 special characters (!@#$%^&*)",
            "mixed_case_numbers": "Mix uppercase, lowercase, numbers, and symbols throughout"
        }
        return suggestions.get(requirement_name, f"Satisfy {requirement_name} requirement")

    def _contains_personal_info(self, password: str, user_info: Dict[str, str]) -> bool:
        """Check if password contains personal information"""
        password_lower = password.lower()
        
        # Check against user info
        for key, value in user_info.items():
            if value and len(value) >= 3:
                if value.lower() in password_lower:
                    return True
                    
        return False

    def _has_sequential_chars(self, password: str) -> bool:
        """Check for sequential characters"""
        # Check for weak patterns
        for pattern in self.WEAK_PATTERNS:
            if re.search(pattern, password.lower()):
                return True
                
        # Check for sequential runs of 3+ characters
        for i in range(len(password) - 2):
            # Ascending sequence
            if ord(password[i]) + 1 == ord(password[i+1]) and ord(password[i+1]) + 1 == ord(password[i+2]):
                return True
            # Descending sequence  
            if ord(password[i]) - 1 == ord(password[i+1]) and ord(password[i+1]) - 1 == ord(password[i+2]):
                return True
                
        return False

    def _calculate_entropy(self, password: str) -> float:
        """Calculate password entropy in bits"""
        if not password:
            return 0.0
            
        # Character set size
        charset_size = 0
        if re.search(r'[a-z]', password):
            charset_size += 26
        if re.search(r'[A-Z]', password):
            charset_size += 26
        if re.search(r'[0-9]', password):
            charset_size += 10
        if re.search(r'[^a-zA-Z0-9]', password):
            charset_size += 32  # Approximate special chars
            
        # Calculate entropy: log2(charset_size^length)
        import math
        if charset_size > 0:
            entropy = len(password) * math.log2(charset_size)
        else:
            entropy = 0.0
            
        # Reduce entropy for patterns and repetition
        unique_chars = len(set(password.lower()))
        repetition_penalty = unique_chars / len(password)
        entropy *= repetition_penalty
        
        return entropy

    def _calculate_strength(self, score: int, max_score: int, entropy: float) -> PasswordStrength:
        """Calculate overall password strength"""
        percentage = (score / max_score) * 100
        
        # Factor in entropy
        if entropy < 30:
            percentage *= 0.7  # Reduce score for low entropy
        elif entropy > 70:
            percentage *= 1.1  # Boost score for high entropy
            
        if percentage >= 90:
            return PasswordStrength.VERY_STRONG
        elif percentage >= 80:
            return PasswordStrength.STRONG
        elif percentage >= 70:
            return PasswordStrength.GOOD
        elif percentage >= 50:
            return PasswordStrength.FAIR
        elif percentage >= 30:
            return PasswordStrength.WEAK
        else:
            return PasswordStrength.VERY_WEAK

    def generate_secure_password(self, length: int = 16, include_symbols: bool = True) -> str:
        """Generate a cryptographically secure password"""
        if length < 12:
            length = 12  # Enforce minimum
        if length > 128:
            length = 128  # Enforce maximum
            
        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?" if include_symbols else ""
        
        # Ensure at least 2 of each required type
        password_chars = []
        password_chars.extend(secrets.choice(lowercase) for _ in range(2))
        password_chars.extend(secrets.choice(uppercase) for _ in range(2))
        password_chars.extend(secrets.choice(digits) for _ in range(2))
        
        if include_symbols:
            password_chars.extend(secrets.choice(symbols) for _ in range(2))
            
        # Fill remaining length with random chars from all sets
        all_chars = lowercase + uppercase + digits + symbols
        remaining_length = length - len(password_chars)
        password_chars.extend(secrets.choice(all_chars) for _ in range(remaining_length))
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password_chars)
        
        password = ''.join(password_chars)
        
        # Verify it meets our own policy
        result = self.validate_password(password)
        if not result.is_valid:
            # Recursively try again if somehow invalid
            return self.generate_secure_password(length, include_symbols)
            
        return password

    def check_password_age(self, password_created: float, max_age_days: int = 90) -> Tuple[bool, int]:
        """Check if password is too old"""
        current_time = time.time()
        age_seconds = current_time - password_created
        age_days = age_seconds / (24 * 3600)
        
        is_expired = age_days > max_age_days
        days_remaining = max(0, max_age_days - int(age_days))
        
        return is_expired, days_remaining

    def get_policy_summary(self) -> Dict[str, Any]:
        """Get human-readable policy summary"""
        return {
            "minimum_length": 12,
            "maximum_length": 128,
            "required_character_types": [
                "At least 2 uppercase letters",
                "At least 2 lowercase letters", 
                "At least 2 digits",
                "At least 2 special characters"
            ],
            "prohibited": [
                "Common passwords",
                "Personal information",
                "Sequential characters",
                "Keyboard patterns",
                "Previously breached passwords"
            ],
            "recommendations": [
                "Use a unique password for each account",
                "Consider using a password manager",
                "Change passwords every 90 days",
                "Enable two-factor authentication when available"
            ]
        }


# Account lockout management
class AccountLockoutManager:
    """Manages account lockout after failed authentication attempts"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.max_attempts = self.config.get('max_failed_attempts', 5)
        self.lockout_duration = self.config.get('lockout_duration_minutes', 15)
        self.attempt_window = self.config.get('attempt_window_minutes', 10)
        
        # In-memory storage (use Redis/database in production)
        self.failed_attempts: Dict[str, List[float]] = {}
        self.locked_accounts: Dict[str, float] = {}

    def record_failed_attempt(self, username: str) -> bool:
        """Record a failed login attempt. Returns True if account should be locked."""
        current_time = time.time()
        
        # Initialize if new user
        if username not in self.failed_attempts:
            self.failed_attempts[username] = []
            
        # Add current attempt
        self.failed_attempts[username].append(current_time)
        
        # Clean old attempts outside the window
        window_start = current_time - (self.attempt_window * 60)
        self.failed_attempts[username] = [
            attempt for attempt in self.failed_attempts[username] 
            if attempt >= window_start
        ]
        
        # Check if should be locked
        if len(self.failed_attempts[username]) >= self.max_attempts:
            self.locked_accounts[username] = current_time
            return True
            
        return False

    def is_account_locked(self, username: str) -> Tuple[bool, int]:
        """Check if account is locked. Returns (is_locked, minutes_remaining)"""
        if username not in self.locked_accounts:
            return False, 0
            
        current_time = time.time()
        locked_time = self.locked_accounts[username]
        elapsed_minutes = (current_time - locked_time) / 60
        
        if elapsed_minutes >= self.lockout_duration:
            # Lockout expired
            del self.locked_accounts[username]
            if username in self.failed_attempts:
                del self.failed_attempts[username]
            return False, 0
        else:
            minutes_remaining = int(self.lockout_duration - elapsed_minutes)
            return True, minutes_remaining

    def unlock_account(self, username: str) -> bool:
        """Manually unlock an account"""
        if username in self.locked_accounts:
            del self.locked_accounts[username]
        if username in self.failed_attempts:
            del self.failed_attempts[username]
        return True

    def reset_failed_attempts(self, username: str) -> bool:
        """Reset failed attempts for successful login"""
        if username in self.failed_attempts:
            del self.failed_attempts[username]
        return True

    def get_lockout_status(self, username: str) -> Dict[str, Any]:
        """Get detailed lockout status"""
        is_locked, minutes_remaining = self.is_account_locked(username)
        failed_count = len(self.failed_attempts.get(username, []))
        
        return {
            "is_locked": is_locked,
            "minutes_remaining": minutes_remaining,
            "failed_attempts": failed_count,
            "max_attempts": self.max_attempts,
            "attempts_remaining": max(0, self.max_attempts - failed_count)
        }


def main():
    """Demo password policy functionality"""
    policy = PasswordPolicy()
    lockout_manager = AccountLockoutManager()
    
    # Test passwords
    test_passwords = [
        "123456",  # Very weak
        "password123",  # Weak
        "MySecure@Pass2024!",  # Strong
        "Tr0ub4dor&3",  # Good
        "correct horse battery staple"  # Passphrase
    ]
    
    print("🔐 Password Policy Validation Demo")
    print("=" * 50)
    
    for password in test_passwords:
        result = policy.validate_password(password, {"username": "testuser", "email": "test@example.com"})
        print(f"\nPassword: {password}")
        print(f"Valid: {result.is_valid}")
        print(f"Strength: {result.strength.value}")
        print(f"Score: {result.score}/{result.max_score}")
        print(f"Entropy: {result.entropy:.1f} bits")
        
        if result.failed_requirements:
            print("Failed requirements:")
            for req in result.failed_requirements:
                print(f"  - {req}")
                
        if result.suggestions:
            print("Suggestions:")
            for suggestion in result.suggestions:
                print(f"  - {suggestion}")
    
    # Test password generation
    print(f"\n🔑 Generated secure password: {policy.generate_secure_password(16)}")
    
    # Test account lockout
    print(f"\n🔒 Account Lockout Demo")
    print("=" * 30)
    
    username = "testuser"
    for i in range(7):
        should_lock = lockout_manager.record_failed_attempt(username)
        status = lockout_manager.get_lockout_status(username)
        print(f"Attempt {i+1}: Locked={should_lock}, Status={status}")


if __name__ == "__main__":
    main()