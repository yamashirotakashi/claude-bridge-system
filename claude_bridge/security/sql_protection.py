#!/usr/bin/env python3
"""
Claude Bridge System - SQL Injection Protection
Advanced SQL injection prevention and query sanitization
"""

import re
import sqlite3
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import hashlib
import time


class SQLOperationType(Enum):
    """SQL operation types"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"
    UNKNOWN = "UNKNOWN"


@dataclass
class QueryAnalysis:
    """SQL query analysis result"""
    operation_type: SQLOperationType
    is_safe: bool
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    detected_patterns: List[str]
    sanitized_query: Optional[str]
    parameters: Dict[str, Any]
    warnings: List[str]
    metadata: Dict[str, Any]


class SQLProtectionManager:
    """Advanced SQL injection protection manager"""

    # Dangerous SQL keywords that should be restricted
    DANGEROUS_KEYWORDS = {
        'EXEC', 'EXECUTE', 'EVAL', 'SP_', 'XP_', 'OPENROWSET', 'OPENDATASOURCE',
        'BULK', 'BFILE', 'JAVA_OBJECT', 'XMLTYPE', 'URIType', 'HTTPURIType',
        'DBMS_JAVA', 'DBMS_LOB', 'DBMS_XMLGEN', 'UTL_FILE', 'UTL_HTTP',
        'WAITFOR', 'DELAY', 'SLEEP', 'BENCHMARK', 'PG_SLEEP', 'GENERATE_SERIES'
    }

    # SQL injection attack patterns
    INJECTION_PATTERNS = [
        # Basic SQL injection
        r"('\s*(OR|AND)\s*'[^']*'?\s*=\s*'[^']*'?)",
        r"('\s*(OR|AND)\s*\d+\s*=\s*\d+)",
        r"('\s*(OR|AND)\s*(TRUE|FALSE))",
        
        # Union-based injection
        r"(\bUNION\s+(ALL\s+)?SELECT\b)",
        r"(\bUNION\s+\w+)",
        
        # Comment-based injection
        r"(--[^\r\n]*)",
        r"(/\*.*?\*/)",
        r"(#[^\r\n]*)",
        
        # Blind SQL injection
        r"(\b(SUBSTRING|SUBSTR|MID|LEFT|RIGHT)\s*\([^)]*\))",
        r"(\bIF\s*\([^)]*,[^)]*,[^)]*\))",
        r"(\bCASE\s+WHEN\b)",
        
        # Time-based injection
        r"(\b(WAITFOR|DELAY|SLEEP|BENCHMARK|PG_SLEEP)\s*\([^)]*\))",
        
        # Error-based injection
        r"(\bCASTAS\b)",
        r"(\bCONVERT\s*\([^)]*\))",
        r"(\bEXTRACTVALUE\s*\([^)]*\))",
        
        # Stacked queries
        r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
        
        # Information schema attacks
        r"(\bINFORMATION_SCHEMA\b)",
        r"(\bSYSOBJECTS\b)",
        r"(\bSYSCOLUMNS\b)",
        r"(\bSYSTABLES\b)",
        
        # Privilege escalation
        r"(\bGRANT\s+(ALL|SELECT|INSERT|UPDATE|DELETE)\b)",
        r"(\bREVOKE\s+(ALL|SELECT|INSERT|UPDATE|DELETE)\b)",
        
        # Data exfiltration
        r"(\bLOAD_FILE\s*\([^)]*\))",
        r"(\bINTO\s+OUTFILE\b)",
        r"(\bINTO\s+DUMPFILE\b)",
        
        # Function-based attacks
        r"(\b(USER|DATABASE|VERSION|@@VERSION|@@HOSTNAME)\s*\(\))",
        r"(\bCHAR\s*\([^)]*\))",
        r"(\bASCII\s*\([^)]*\))",
        r"(\bCONCAT\s*\([^)]*\))",
        
        # Hex encoding attacks
        r"(0x[0-9a-fA-F]+)",
        
        # Boolean-based attacks
        r"(\b(TRUE|FALSE)\s*(AND|OR)\s*(TRUE|FALSE)\b)",
        
        # Mathematical injection
        r"(\b\d+\s*[+\-*/]\s*\d+\s*=\s*\d+)",
        
        # Nested queries
        r"(\(\s*SELECT\b[^)]*\))",
        
        # Administrative commands
        r"(\b(SHUTDOWN|RESTART|KILL)\b)",
        
        # Multiple statement separators
        r"(;\s*;)",
        
        # Quote manipulation
        r"('')+",
        r"(\\[x'\"\\])",
        
        # URL encoded injection
        r"(%27|%22|%2D%2D|%23|%2F%2A|%2A%2F)",
        
        # Double URL encoded
        r"(%2527|%2522|%252D%252D|%2523)"
    ]

    # Allowed functions (whitelist approach)
    ALLOWED_FUNCTIONS = {
        'ABS', 'ACOS', 'ASIN', 'ATAN', 'ATAN2', 'CEILING', 'COS', 'COT', 'DEGREES',
        'EXP', 'FLOOR', 'LOG', 'LOG10', 'PI', 'POWER', 'RADIANS', 'RAND', 'ROUND',
        'SIGN', 'SIN', 'SQRT', 'TAN', 'TRUNCATE', 'ASCII', 'CHAR_LENGTH', 'CHARACTER_LENGTH',
        'CONCAT', 'CONCAT_WS', 'FIELD', 'FIND_IN_SET', 'FORMAT', 'INSERT', 'INSTR',
        'LCASE', 'LEFT', 'LENGTH', 'LOCATE', 'LOWER', 'LPAD', 'LTRIM', 'MID',
        'POSITION', 'REPEAT', 'REPLACE', 'REVERSE', 'RIGHT', 'RPAD', 'RTRIM',
        'SPACE', 'STRCMP', 'SUBSTR', 'SUBSTRING', 'TRIM', 'UCASE', 'UPPER',
        'ADDDATE', 'ADDTIME', 'CURDATE', 'CURRENT_DATE', 'CURRENT_TIME',
        'CURRENT_TIMESTAMP', 'CURTIME', 'DATE', 'DATEDIFF', 'DATE_ADD', 'DATE_FORMAT',
        'DATE_SUB', 'DAY', 'DAYNAME', 'DAYOFMONTH', 'DAYOFWEEK', 'DAYOFYEAR',
        'EXTRACT', 'FROM_DAYS', 'FROM_UNIXTIME', 'HOUR', 'LAST_DAY', 'MAKEDATE',
        'MAKETIME', 'MICROSECOND', 'MINUTE', 'MONTH', 'MONTHNAME', 'NOW',
        'PERIOD_ADD', 'PERIOD_DIFF', 'QUARTER', 'SECOND', 'SEC_TO_TIME',
        'STR_TO_DATE', 'SUBDATE', 'SUBTIME', 'SYSDATE', 'TIME', 'TIME_FORMAT',
        'TIME_TO_SEC', 'TIMEDIFF', 'TIMESTAMP', 'TIMESTAMPADD', 'TIMESTAMPDIFF',
        'TO_DAYS', 'UNIX_TIMESTAMP', 'UTC_DATE', 'UTC_TIME', 'UTC_TIMESTAMP',
        'WEEK', 'WEEKDAY', 'WEEKOFYEAR', 'YEAR', 'YEARWEEK'
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize SQL protection manager"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.max_query_length = self.config.get('max_query_length', 10000)
        self.allow_dynamic_queries = self.config.get('allow_dynamic_queries', False)
        self.strict_mode = self.config.get('strict_mode', True)
        
        # Compile patterns for performance
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for pattern in self.INJECTION_PATTERNS
        ]

    def analyze_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> QueryAnalysis:
        """Analyze SQL query for injection attempts"""
        if not query or not isinstance(query, str):
            return QueryAnalysis(
                operation_type=SQLOperationType.UNKNOWN,
                is_safe=False,
                risk_level="CRITICAL",
                detected_patterns=["Empty or invalid query"],
                sanitized_query=None,
                parameters=parameters or {},
                warnings=["Query is empty or not a string"],
                metadata={"analysis_time": time.time()}
            )

        query = query.strip()
        parameters = parameters or {}
        detected_patterns = []
        warnings = []
        metadata = {"analysis_time": time.time(), "original_length": len(query)}

        # Check query length
        if len(query) > self.max_query_length:
            warnings.append(f"Query exceeds maximum length ({len(query)} > {self.max_query_length})")
            metadata["oversized"] = True

        # Determine operation type
        operation_type = self._detect_operation_type(query)
        metadata["operation_type"] = operation_type.value

        # Check for dangerous keywords
        dangerous_found = self._check_dangerous_keywords(query)
        if dangerous_found:
            detected_patterns.extend([f"Dangerous keyword: {kw}" for kw in dangerous_found])
            metadata["dangerous_keywords"] = dangerous_found

        # Check for injection patterns
        injection_patterns = self._check_injection_patterns(query)
        if injection_patterns:
            detected_patterns.extend(injection_patterns)
            metadata["injection_patterns"] = injection_patterns

        # Check parameters for injection
        param_issues = self._check_parameters(parameters)
        if param_issues:
            detected_patterns.extend(param_issues)
            metadata["parameter_issues"] = param_issues

        # Check for encoding attacks
        encoding_attacks = self._check_encoding_attacks(query)
        if encoding_attacks:
            detected_patterns.extend(encoding_attacks)
            metadata["encoding_attacks"] = encoding_attacks

        # Calculate risk level
        risk_level = self._calculate_risk_level(detected_patterns, operation_type)
        metadata["risk_score"] = len(detected_patterns)

        # Determine if query is safe
        is_safe = len(detected_patterns) == 0 or (not self.strict_mode and risk_level in ["LOW", "MEDIUM"])

        # Generate sanitized query if possible
        sanitized_query = None
        if is_safe or not self.strict_mode:
            sanitized_query = self._sanitize_query(query, parameters)

        return QueryAnalysis(
            operation_type=operation_type,
            is_safe=is_safe,
            risk_level=risk_level,
            detected_patterns=detected_patterns,
            sanitized_query=sanitized_query,
            parameters=parameters,
            warnings=warnings,
            metadata=metadata
        )

    def _detect_operation_type(self, query: str) -> SQLOperationType:
        """Detect SQL operation type"""
        query_upper = query.upper().strip()
        
        if query_upper.startswith('SELECT'):
            return SQLOperationType.SELECT
        elif query_upper.startswith('INSERT'):
            return SQLOperationType.INSERT
        elif query_upper.startswith('UPDATE'):
            return SQLOperationType.UPDATE
        elif query_upper.startswith('DELETE'):
            return SQLOperationType.DELETE
        elif query_upper.startswith('CREATE'):
            return SQLOperationType.CREATE
        elif query_upper.startswith('DROP'):
            return SQLOperationType.DROP
        elif query_upper.startswith('ALTER'):
            return SQLOperationType.ALTER
        else:
            return SQLOperationType.UNKNOWN

    def _check_dangerous_keywords(self, query: str) -> List[str]:
        """Check for dangerous SQL keywords"""
        found_keywords = []
        query_upper = query.upper()
        
        for keyword in self.DANGEROUS_KEYWORDS:
            if re.search(rf'\b{re.escape(keyword)}\b', query_upper):
                found_keywords.append(keyword)
                
        return found_keywords

    def _check_injection_patterns(self, query: str) -> List[str]:
        """Check for SQL injection patterns"""
        detected = []
        
        for i, pattern in enumerate(self._compiled_patterns):
            matches = pattern.findall(query)
            if matches:
                detected.append(f"Pattern {i+1}: {matches[0] if isinstance(matches[0], str) else matches[0][0]}")
                
        return detected

    def _check_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Check parameters for injection attempts"""
        issues = []
        
        for key, value in parameters.items():
            if isinstance(value, str):
                # Check each parameter value for injection patterns
                for i, pattern in enumerate(self._compiled_patterns):
                    if pattern.search(value):
                        issues.append(f"Parameter '{key}' contains suspicious pattern")
                        break
                        
                # Check for dangerous keywords in parameters
                value_upper = value.upper()
                for keyword in self.DANGEROUS_KEYWORDS:
                    if re.search(rf'\b{re.escape(keyword)}\b', value_upper):
                        issues.append(f"Parameter '{key}' contains dangerous keyword: {keyword}")
                        
        return issues

    def _check_encoding_attacks(self, query: str) -> List[str]:
        """Check for encoding-based attacks"""
        attacks = []
        
        # Check for hex encoding
        if re.search(r'0x[0-9a-fA-F]{2,}', query):
            attacks.append("Hex encoding detected")
            
        # Check for URL encoding
        if re.search(r'%[0-9a-fA-F]{2}', query):
            attacks.append("URL encoding detected")
            
        # Check for Unicode escaping
        if re.search(r'\\u[0-9a-fA-F]{4}', query):
            attacks.append("Unicode escaping detected")
            
        # Check for HTML entities
        if re.search(r'&[a-zA-Z0-9]+;|&#[0-9]+;|&#x[0-9a-fA-F]+;', query):
            attacks.append("HTML entities detected")
            
        return attacks

    def _calculate_risk_level(self, detected_patterns: List[str], operation_type: SQLOperationType) -> str:
        """Calculate risk level based on detected patterns"""
        pattern_count = len(detected_patterns)
        
        # Critical risk conditions
        if any("UNION" in pattern for pattern in detected_patterns):
            return "CRITICAL"
        if any("DROP" in pattern for pattern in detected_patterns):
            return "CRITICAL"
        if any("EXEC" in pattern for pattern in detected_patterns):
            return "CRITICAL"
        if any("--" in pattern for pattern in detected_patterns):
            return "CRITICAL"
        
        # High risk conditions
        if pattern_count >= 5:
            return "CRITICAL"
        elif pattern_count >= 3:
            return "HIGH"
        elif pattern_count >= 2:
            return "HIGH" if operation_type in [SQLOperationType.DELETE, SQLOperationType.DROP] else "MEDIUM"
        elif pattern_count >= 1:
            return "MEDIUM" if operation_type in [SQLOperationType.SELECT] else "HIGH"
        else:
            return "LOW"

    def _sanitize_query(self, query: str, parameters: Dict[str, Any]) -> str:
        """Sanitize SQL query (basic implementation)"""
        # Remove comments
        query = re.sub(r'--[^\r\n]*', '', query)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        query = re.sub(r'#[^\r\n]*', '', query)
        
        # Remove multiple semicolons
        query = re.sub(r';\s*;+', ';', query)
        
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query

    def create_parameterized_query(self, base_query: str, parameters: Dict[str, Any]) -> Tuple[str, Tuple]:
        """Create parameterized query from base query and parameters"""
        # Convert named parameters to positional parameters
        param_values = []
        parameterized_query = base_query
        
        # Sort parameters by length (longest first) to avoid partial replacements
        sorted_params = sorted(parameters.items(), key=lambda x: len(x[0]), reverse=True)
        
        for param_name, param_value in sorted_params:
            placeholder = f":{param_name}"
            if placeholder in parameterized_query:
                parameterized_query = parameterized_query.replace(placeholder, "?")
                param_values.append(param_value)
                
        return parameterized_query, tuple(param_values)

    def execute_safe_query(self, connection: sqlite3.Connection, query: str, 
                          parameters: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any, List[str]]:
        """Execute query with safety checks"""
        parameters = parameters or {}
        errors = []
        
        try:
            # Analyze query first
            analysis = self.analyze_query(query, parameters)
            
            if not analysis.is_safe:
                errors.extend(analysis.detected_patterns)
                return False, None, errors
                
            # Use sanitized query if available
            if analysis.sanitized_query:
                query = analysis.sanitized_query
                
            # Create parameterized query
            if parameters:
                param_query, param_values = self.create_parameterized_query(query, parameters)
                cursor = connection.execute(param_query, param_values)
            else:
                cursor = connection.execute(query)
                
            # Get results based on operation type
            if analysis.operation_type == SQLOperationType.SELECT:
                results = cursor.fetchall()
            else:
                results = cursor.rowcount
                connection.commit()
                
            return True, results, []
            
        except sqlite3.Error as e:
            errors.append(f"Database error: {str(e)}")
            return False, None, errors
        except Exception as e:
            errors.append(f"Execution error: {str(e)}")
            return False, None, errors

    def get_security_report(self, queries: List[str]) -> Dict[str, Any]:
        """Generate security report for multiple queries"""
        total_queries = len(queries)
        safe_queries = 0
        risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        operation_types = {}
        all_patterns = []
        
        for query in queries:
            analysis = self.analyze_query(query)
            
            if analysis.is_safe:
                safe_queries += 1
                
            risk_distribution[analysis.risk_level] += 1
            
            op_type = analysis.operation_type.value
            operation_types[op_type] = operation_types.get(op_type, 0) + 1
            
            all_patterns.extend(analysis.detected_patterns)
        
        # Calculate statistics
        safety_rate = (safe_queries / total_queries * 100) if total_queries > 0 else 0
        most_common_patterns = {}
        for pattern in all_patterns:
            most_common_patterns[pattern] = most_common_patterns.get(pattern, 0) + 1
        
        # Sort by frequency
        most_common_patterns = dict(sorted(most_common_patterns.items(), 
                                         key=lambda x: x[1], reverse=True)[:10])
        
        return {
            "total_queries": total_queries,
            "safe_queries": safe_queries,
            "unsafe_queries": total_queries - safe_queries,
            "safety_rate": round(safety_rate, 2),
            "risk_distribution": risk_distribution,
            "operation_distribution": operation_types,
            "most_common_attack_patterns": most_common_patterns,
            "recommendations": self._generate_recommendations(risk_distribution, safety_rate)
        }

    def _generate_recommendations(self, risk_distribution: Dict[str, int], safety_rate: float) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        if safety_rate < 50:
            recommendations.append("URGENT: Less than 50% of queries are safe. Immediate security review required.")
        elif safety_rate < 80:
            recommendations.append("WARNING: Query safety rate is below 80%. Review and improve input validation.")
        
        if risk_distribution["CRITICAL"] > 0:
            recommendations.append("CRITICAL: Critical risk queries detected. Block these immediately.")
        
        if risk_distribution["HIGH"] > 0:
            recommendations.append("HIGH: High risk queries found. Implement additional security measures.")
        
        if risk_distribution["MEDIUM"] > 5:
            recommendations.append("MEDIUM: Multiple medium risk queries. Consider implementing stricter validation.")
        
        # General recommendations
        recommendations.extend([
            "Always use parameterized queries",
            "Implement input validation and sanitization",
            "Use principle of least privilege for database access",
            "Regular security audits and penetration testing",
            "Keep database software updated",
            "Monitor and log database access"
        ])
        
        return recommendations


def main():
    """Demo SQL protection functionality"""
    sql_protection = SQLProtectionManager()
    
    # Test queries with various injection attempts
    test_queries = [
        # Safe queries
        "SELECT * FROM users WHERE id = :user_id",
        "INSERT INTO logs (message, timestamp) VALUES (:message, :timestamp)",
        
        # SQL injection attempts
        "SELECT * FROM users WHERE name = 'admin' OR '1'='1'",
        "SELECT * FROM users WHERE id = 1; DROP TABLE users; --",
        "SELECT * FROM users WHERE name = '' UNION SELECT password FROM admin_users --",
        "SELECT * FROM users WHERE id = 1 AND (SELECT COUNT(*) FROM admin_users) > 0",
        "'; EXEC xp_cmdshell('format c:'); --",
        "SELECT * FROM users WHERE name = 'user' AND SLEEP(10)",
        "SELECT * FROM users WHERE id = 1 OR BENCHMARK(10000000,MD5(1))",
        "SELECT * FROM products WHERE category = 'electronics' AND (1=1)",
        
        # Encoded attacks
        "SELECT * FROM users WHERE name = 0x61646D696E",
        "SELECT * FROM users WHERE id = %27%20OR%20%271%27=%271",
        
        # Function-based attacks
        "SELECT * FROM users WHERE name = CONCAT(CHAR(97),CHAR(100),CHAR(109),CHAR(105),CHAR(110))",
        "SELECT user(), database(), version()",
        
        # Comment-based
        "SELECT * FROM users /* WHERE id = 1 */ OR 1=1 --",
        "SELECT * FROM users # comment here\n OR 1=1",
        
        # Stacked queries
        "SELECT * FROM users; INSERT INTO logs VALUES ('hacked', NOW())",
        
        # Time-based blind injection
        "SELECT * FROM users WHERE id = 1 AND IF(1=1, SLEEP(5), 0)",
        
        # Boolean-based blind injection
        "SELECT * FROM users WHERE id = 1 AND SUBSTRING(user(),1,1) = 'r'",
        
        # Error-based injection
        "SELECT * FROM users WHERE id = 1 AND EXTRACTVALUE(1, CONCAT(0x7e, user(), 0x7e))"
    ]
    
    print("🛡️ SQL Injection Protection Demo")
    print("=" * 50)
    
    # Analyze each query
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query[:80]}{'...' if len(query) > 80 else ''}")
        
        analysis = sql_protection.analyze_query(query, {"user_id": 123, "message": "test log"})
        
        print(f"   Operation: {analysis.operation_type.value}")
        print(f"   Safe: {analysis.is_safe}")
        print(f"   Risk Level: {analysis.risk_level}")
        
        if analysis.detected_patterns:
            print(f"   Detected Patterns: {len(analysis.detected_patterns)}")
            for pattern in analysis.detected_patterns[:3]:  # Show first 3
                print(f"     - {pattern}")
            if len(analysis.detected_patterns) > 3:
                print(f"     ... and {len(analysis.detected_patterns) - 3} more")
        
        if analysis.warnings:
            print(f"   Warnings: {analysis.warnings}")
    
    # Generate security report
    print(f"\n📊 Security Report")
    print("=" * 30)
    
    report = sql_protection.get_security_report(test_queries)
    
    print(f"Total Queries: {report['total_queries']}")
    print(f"Safe Queries: {report['safe_queries']}")
    print(f"Unsafe Queries: {report['unsafe_queries']}")
    print(f"Safety Rate: {report['safety_rate']}%")
    
    print(f"\nRisk Distribution:")
    for risk, count in report['risk_distribution'].items():
        print(f"  {risk}: {count}")
    
    print(f"\nOperation Distribution:")
    for op, count in report['operation_distribution'].items():
        print(f"  {op}: {count}")
    
    print(f"\nTop Attack Patterns:")
    for pattern, count in list(report['most_common_attack_patterns'].items())[:5]:
        print(f"  {pattern}: {count}")
    
    print(f"\nRecommendations:")
    for rec in report['recommendations'][:5]:
        print(f"  - {rec}")
    
    # Test safe execution
    print(f"\n🔐 Safe Query Execution Test")
    print("=" * 35)
    
    # Create in-memory database for testing
    conn = sqlite3.connect(':memory:')
    conn.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)''')
    conn.execute('''INSERT INTO users (name, email) VALUES ('admin', 'admin@example.com')''')
    conn.execute('''INSERT INTO users (name, email) VALUES ('user', 'user@example.com')''')
    
    # Test safe query
    safe_query = "SELECT * FROM users WHERE name = :name"
    success, results, errors = sql_protection.execute_safe_query(
        conn, safe_query, {"name": "admin"}
    )
    
    print(f"Safe Query Result: Success={success}, Results={results}, Errors={errors}")
    
    # Test unsafe query
    unsafe_query = "SELECT * FROM users WHERE name = 'admin' OR '1'='1'"
    success, results, errors = sql_protection.execute_safe_query(conn, unsafe_query)
    
    print(f"Unsafe Query Result: Success={success}, Results={results}, Errors={errors}")
    
    conn.close()


if __name__ == "__main__":
    main()