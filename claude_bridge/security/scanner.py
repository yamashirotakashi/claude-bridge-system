"""
Claude Bridge System - Vulnerability Scanner
脆弱性スキャンシステム
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class VulnerabilityLevel(Enum):
    """脆弱性レベル"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScanType(Enum):
    """スキャン種別"""
    DEPENDENCY = "dependency"
    CODE_ANALYSIS = "code_analysis"
    CONFIG_ANALYSIS = "config_analysis"
    NETWORK_SCAN = "network_scan"
    CONTAINER_SCAN = "container_scan"
    SECRETS_SCAN = "secrets_scan"


@dataclass
class Vulnerability:
    """脆弱性情報"""
    id: str
    title: str
    description: str
    level: VulnerabilityLevel
    scan_type: ScanType
    location: Optional[str] = None
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    cve_id: Optional[str] = None
    cvss_score: Optional[float] = None
    remediation: Optional[str] = None
    references: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.references is None:
            self.references = []
        if self.metadata is None:
            self.metadata = {}
        if self.id is None:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """脆弱性ID生成"""
        content = f"{self.title}{self.scan_type.value}{self.location or ''}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'level': self.level.value,
            'scan_type': self.scan_type.value,
            'location': self.location,
            'line_number': self.line_number,
            'file_path': self.file_path,
            'cve_id': self.cve_id,
            'cvss_score': self.cvss_score,
            'remediation': self.remediation,
            'references': self.references,
            'metadata': self.metadata
        }


@dataclass
class ScanResult:
    """スキャン結果"""
    scan_id: str
    scan_type: ScanType
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    vulnerabilities: List[Vulnerability] = None
    summary: Optional[Dict[str, Any]] = None
    scan_config: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.vulnerabilities is None:
            self.vulnerabilities = []
        if self.errors is None:
            self.errors = []
        if self.scan_id is None:
            self.scan_id = self._generate_scan_id()
    
    def _generate_scan_id(self) -> str:
        """スキャンID生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{self.scan_type.value}_{timestamp}"
    
    def add_vulnerability(self, vulnerability: Vulnerability) -> None:
        """脆弱性追加"""
        self.vulnerabilities.append(vulnerability)
    
    def get_summary(self) -> Dict[str, Any]:
        """サマリー生成"""
        if self.summary:
            return self.summary
        
        level_counts = {}
        for vuln in self.vulnerabilities:
            level = vuln.level.value
            level_counts[level] = level_counts.get(level, 0) + 1
        
        total_vulnerabilities = len(self.vulnerabilities)
        high_critical_count = level_counts.get('high', 0) + level_counts.get('critical', 0)
        
        self.summary = {
            'total_vulnerabilities': total_vulnerabilities,
            'by_level': level_counts,
            'high_critical_count': high_critical_count,
            'scan_duration': self._calculate_duration(),
            'risk_score': self._calculate_risk_score()
        }
        
        return self.summary
    
    def _calculate_duration(self) -> Optional[float]:
        """スキャン時間計算"""
        if not self.completed_at:
            return None
        
        try:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            return (end - start).total_seconds()
        except ValueError:
            return None
    
    def _calculate_risk_score(self) -> int:
        """リスクスコア計算"""
        score = 0
        for vuln in self.vulnerabilities:
            if vuln.level == VulnerabilityLevel.CRITICAL:
                score += 20
            elif vuln.level == VulnerabilityLevel.HIGH:
                score += 10
            elif vuln.level == VulnerabilityLevel.MEDIUM:
                score += 5
            elif vuln.level == VulnerabilityLevel.LOW:
                score += 2
            else:
                score += 1
        
        return min(score, 100)


@dataclass
class VulnerabilityReport:
    """脆弱性レポート"""
    report_id: str
    generated_at: str
    scan_results: List[ScanResult]
    summary: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.report_id is None:
            self.report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def generate_summary(self) -> Dict[str, Any]:
        """総合サマリー生成"""
        total_vulnerabilities = 0
        level_counts = {}
        scan_types = set()
        
        for scan_result in self.scan_results:
            total_vulnerabilities += len(scan_result.vulnerabilities)
            scan_types.add(scan_result.scan_type.value)
            
            for vuln in scan_result.vulnerabilities:
                level = vuln.level.value
                level_counts[level] = level_counts.get(level, 0) + 1
        
        high_critical_count = level_counts.get('high', 0) + level_counts.get('critical', 0)
        
        self.summary = {
            'total_scans': len(self.scan_results),
            'scan_types': list(scan_types),
            'total_vulnerabilities': total_vulnerabilities,
            'by_level': level_counts,
            'high_critical_count': high_critical_count,
            'overall_risk_score': min(sum(sr.get_summary().get('risk_score', 0) 
                                        for sr in self.scan_results), 100)
        }
        
        return self.summary


class VulnerabilityScanner:
    """脆弱性スキャナー"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            config: スキャナー設定
        """
        self.config = config or {}
        self.scan_results: Dict[str, ScanResult] = {}
        
        # スキャン設定
        self.enabled_scanners = set(self.config.get('enabled_scanners', [
            'dependency', 'code_analysis', 'secrets_scan'
        ]))
        
        # 除外設定
        self.exclude_paths = set(self.config.get('exclude_paths', [
            '.git', '__pycache__', 'node_modules', '.venv', 'venv'
        ]))
        
        self.exclude_files = set(self.config.get('exclude_files', [
            '*.pyc', '*.pyo', '*.log', '*.tmp'
        ]))
        
        # 外部ツール設定
        self.external_tools = self.config.get('external_tools', {})
        
        logger.info("VulnerabilityScanner initialized")
    
    async def scan_project(self, 
                          project_path: Path,
                          scan_types: Optional[List[ScanType]] = None) -> VulnerabilityReport:
        """プロジェクト全体スキャン"""
        project_path = Path(project_path)
        scan_types = scan_types or [ScanType.DEPENDENCY, ScanType.CODE_ANALYSIS, ScanType.SECRETS_SCAN]
        
        logger.info(f"Starting vulnerability scan for project: {project_path}")
        
        scan_results = []
        
        # 各スキャンタイプを並行実行
        tasks = []
        for scan_type in scan_types:
            if scan_type.value in self.enabled_scanners:
                task = asyncio.create_task(self._run_scan(project_path, scan_type))
                tasks.append(task)
        
        if tasks:
            scan_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 例外を除去
            scan_results = [result for result in scan_results 
                          if isinstance(result, ScanResult)]
        
        # レポート生成
        report = VulnerabilityReport(
            report_id=None,  # 自動生成
            generated_at=datetime.now().isoformat(),
            scan_results=scan_results
        )
        
        report.generate_summary()
        report.recommendations = self._generate_recommendations(report)
        
        logger.info(f"Vulnerability scan completed: {len(scan_results)} scans, "
                   f"{report.summary['total_vulnerabilities']} vulnerabilities found")
        
        return report
    
    async def scan_dependencies(self, project_path: Path) -> ScanResult:
        """依存関係スキャン"""
        return await self._run_scan(project_path, ScanType.DEPENDENCY)
    
    async def scan_code(self, project_path: Path) -> ScanResult:
        """コード解析スキャン"""
        return await self._run_scan(project_path, ScanType.CODE_ANALYSIS)
    
    async def scan_secrets(self, project_path: Path) -> ScanResult:
        """シークレットスキャン"""
        return await self._run_scan(project_path, ScanType.SECRETS_SCAN)
    
    async def scan_config(self, project_path: Path) -> ScanResult:
        """設定ファイルスキャン"""
        return await self._run_scan(project_path, ScanType.CONFIG_ANALYSIS)
    
    async def _run_scan(self, project_path: Path, scan_type: ScanType) -> ScanResult:
        """スキャン実行"""
        scan_result = ScanResult(
            scan_id=None,  # 自動生成
            scan_type=scan_type,
            started_at=datetime.now().isoformat()
        )
        
        try:
            if scan_type == ScanType.DEPENDENCY:
                await self._scan_dependencies(project_path, scan_result)
            elif scan_type == ScanType.CODE_ANALYSIS:
                await self._scan_code_analysis(project_path, scan_result)
            elif scan_type == ScanType.SECRETS_SCAN:
                await self._scan_secrets(project_path, scan_result)
            elif scan_type == ScanType.CONFIG_ANALYSIS:
                await self._scan_config_analysis(project_path, scan_result)
            else:
                scan_result.errors.append(f"Unsupported scan type: {scan_type}")
            
            scan_result.status = "completed"
            
        except Exception as e:
            logger.error(f"Scan failed for {scan_type}: {e}")
            scan_result.status = "failed"
            scan_result.errors.append(str(e))
        
        finally:
            scan_result.completed_at = datetime.now().isoformat()
            self.scan_results[scan_result.scan_id] = scan_result
        
        return scan_result
    
    async def _scan_dependencies(self, project_path: Path, scan_result: ScanResult) -> None:
        """依存関係脆弱性スキャン"""
        # Python (pip/requirements.txt)
        await self._scan_python_dependencies(project_path, scan_result)
        
        # Node.js (package.json)
        await self._scan_nodejs_dependencies(project_path, scan_result)
    
    async def _scan_python_dependencies(self, project_path: Path, scan_result: ScanResult) -> None:
        """Python依存関係スキャン"""
        requirements_files = [
            project_path / 'requirements.txt',
            project_path / 'requirements-dev.txt',
            project_path / 'pyproject.toml',
            project_path / 'Pipfile'
        ]
        
        for req_file in requirements_files:
            if req_file.exists():
                await self._check_python_packages(req_file, scan_result)
    
    async def _check_python_packages(self, requirements_file: Path, scan_result: ScanResult) -> None:
        """Pythonパッケージチェック"""
        try:
            # safety ツールを使用した脆弱性チェック（簡略化実装）
            if requirements_file.name == 'requirements.txt':
                with open(requirements_file, 'r', encoding='utf-8') as f:
                    packages = f.readlines()
                
                # 既知の脆弱性パッケージ（例）
                vulnerable_packages = {
                    'pillow': {
                        'versions': ['<8.3.2'],
                        'cve': 'CVE-2021-34552',
                        'description': 'Buffer overflow in Pillow'
                    },
                    'requests': {
                        'versions': ['<2.20.0'],
                        'cve': 'CVE-2018-18074',
                        'description': 'Improper Certificate Validation'
                    }
                }
                
                for package_line in packages:
                    package_line = package_line.strip()
                    if not package_line or package_line.startswith('#'):
                        continue
                    
                    package_name = package_line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                    
                    if package_name.lower() in vulnerable_packages:
                        vuln_info = vulnerable_packages[package_name.lower()]
                        vulnerability = Vulnerability(
                            id=None,  # 自動生成
                            title=f"Vulnerable dependency: {package_name}",
                            description=vuln_info['description'],
                            level=VulnerabilityLevel.HIGH,
                            scan_type=ScanType.DEPENDENCY,
                            location=str(requirements_file),
                            cve_id=vuln_info['cve'],
                            remediation=f"Update {package_name} to a secure version",
                            metadata={'package': package_name, 'file': str(requirements_file)}
                        )
                        scan_result.add_vulnerability(vulnerability)
        
        except Exception as e:
            scan_result.errors.append(f"Error checking Python packages: {e}")
    
    async def _scan_nodejs_dependencies(self, project_path: Path, scan_result: ScanResult) -> None:
        """Node.js依存関係スキャン"""
        package_json = project_path / 'package.json'
        
        if package_json.exists():
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                
                dependencies = package_data.get('dependencies', {})
                dev_dependencies = package_data.get('devDependencies', {})
                
                # 既知の脆弱性パッケージ（例）
                vulnerable_packages = {
                    'lodash': {
                        'versions': ['<4.17.21'],
                        'cve': 'CVE-2021-23337',
                        'description': 'Command injection via template'
                    }
                }
                
                all_deps = {**dependencies, **dev_dependencies}
                
                for package_name, version in all_deps.items():
                    if package_name in vulnerable_packages:
                        vuln_info = vulnerable_packages[package_name]
                        vulnerability = Vulnerability(
                            id=None,  # 自動生成
                            title=f"Vulnerable Node.js dependency: {package_name}",
                            description=vuln_info['description'],
                            level=VulnerabilityLevel.HIGH,
                            scan_type=ScanType.DEPENDENCY,
                            location=str(package_json),
                            cve_id=vuln_info['cve'],
                            remediation=f"Update {package_name} to a secure version",
                            metadata={'package': package_name, 'version': version}
                        )
                        scan_result.add_vulnerability(vulnerability)
            
            except Exception as e:
                scan_result.errors.append(f"Error checking Node.js packages: {e}")
    
    async def _scan_code_analysis(self, project_path: Path, scan_result: ScanResult) -> None:
        """コード解析スキャン"""
        # Python ファイルの静的解析
        python_files = list(project_path.rglob('*.py'))
        
        for py_file in python_files:
            if self._should_exclude_path(py_file):
                continue
            
            await self._analyze_python_file(py_file, scan_result)
    
    async def _analyze_python_file(self, file_path: Path, scan_result: ScanResult) -> None:
        """Pythonファイル解析"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # 危険なパターンの検出
            dangerous_patterns = [
                (r'eval\s*\(', 'Use of eval() function', VulnerabilityLevel.HIGH),
                (r'exec\s*\(', 'Use of exec() function', VulnerabilityLevel.HIGH),
                (r'os\.system\s*\(', 'Use of os.system()', VulnerabilityLevel.MEDIUM),
                (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', 'Shell injection risk', VulnerabilityLevel.HIGH),
                (r'pickle\.loads?\s*\(', 'Insecure deserialization', VulnerabilityLevel.MEDIUM),
                (r'input\s*\([^)]*\)\s*\)', 'Direct input() usage', VulnerabilityLevel.LOW),
                (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password', VulnerabilityLevel.CRITICAL),
                (r'api_key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key', VulnerabilityLevel.CRITICAL)
            ]
            
            for line_num, line in enumerate(lines, 1):
                for pattern, title, level in dangerous_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        vulnerability = Vulnerability(
                            id=None,  # 自動生成
                            title=title,
                            description=f"Potentially dangerous code pattern detected: {pattern}",
                            level=level,
                            scan_type=ScanType.CODE_ANALYSIS,
                            location=f"{file_path}:{line_num}",
                            line_number=line_num,
                            file_path=str(file_path),
                            remediation=self._get_remediation_for_pattern(pattern),
                            metadata={'pattern': pattern, 'code_line': line.strip()}
                        )
                        scan_result.add_vulnerability(vulnerability)
        
        except Exception as e:
            scan_result.errors.append(f"Error analyzing file {file_path}: {e}")
    
    async def _scan_secrets(self, project_path: Path, scan_result: ScanResult) -> None:
        """シークレットスキャン"""
        # 各種ファイルからシークレットを検出
        file_patterns = ['*.py', '*.js', '*.ts', '*.json', '*.yaml', '*.yml', '*.env', '*.conf']
        
        for pattern in file_patterns:
            for file_path in project_path.rglob(pattern):
                if self._should_exclude_path(file_path):
                    continue
                
                await self._scan_file_for_secrets(file_path, scan_result)
    
    async def _scan_file_for_secrets(self, file_path: Path, scan_result: ScanResult) -> None:
        """ファイル内シークレット検出"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # シークレットパターン
            secret_patterns = [
                (r'(?i)password\s*[=:]\s*["\'][^"\']{8,}["\']', 'Hardcoded password', VulnerabilityLevel.CRITICAL),
                (r'(?i)api[_-]?key\s*[=:]\s*["\'][^"\']{20,}["\']', 'API key', VulnerabilityLevel.CRITICAL),
                (r'(?i)secret[_-]?key\s*[=:]\s*["\'][^"\']{20,}["\']', 'Secret key', VulnerabilityLevel.CRITICAL),
                (r'(?i)access[_-]?token\s*[=:]\s*["\'][^"\']{20,}["\']', 'Access token', VulnerabilityLevel.CRITICAL),
                (r'(?i)private[_-]?key\s*[=:]\s*["\'][^"\']{20,}["\']', 'Private key', VulnerabilityLevel.CRITICAL),
                (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API key', VulnerabilityLevel.CRITICAL),
                (r'xoxb-[0-9]{11}-[0-9]{11}-[a-zA-Z0-9]{24}', 'Slack Bot token', VulnerabilityLevel.CRITICAL),
                (r'AKIA[0-9A-Z]{16}', 'AWS Access Key', VulnerabilityLevel.CRITICAL),
                (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token', VulnerabilityLevel.CRITICAL)
            ]
            
            for line_num, line in enumerate(lines, 1):
                for pattern, title, level in secret_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        vulnerability = Vulnerability(
                            id=None,  # 自動生成
                            title=f"Exposed secret: {title}",
                            description=f"Potentially exposed secret detected in code",
                            level=level,
                            scan_type=ScanType.SECRETS_SCAN,
                            location=f"{file_path}:{line_num}",
                            line_number=line_num,
                            file_path=str(file_path),
                            remediation="Remove hardcoded secrets and use environment variables or secure vault",
                            metadata={
                                'secret_type': title,
                                'pattern': pattern,
                                'matched_text': match.group()[:10] + '...'  # 一部のみ表示
                            }
                        )
                        scan_result.add_vulnerability(vulnerability)
        
        except Exception as e:
            scan_result.errors.append(f"Error scanning secrets in {file_path}: {e}")
    
    async def _scan_config_analysis(self, project_path: Path, scan_result: ScanResult) -> None:
        """設定ファイル解析"""
        config_files = [
            project_path / 'config.py',
            project_path / 'settings.py',
            project_path / 'docker-compose.yml',
            project_path / '.env'
        ]
        
        for config_file in config_files:
            if config_file.exists():
                await self._analyze_config_file(config_file, scan_result)
    
    async def _analyze_config_file(self, config_file: Path, scan_result: ScanResult) -> None:
        """設定ファイル解析"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 設定の問題パターン
            config_issues = [
                (r'(?i)debug\s*=\s*True', 'Debug mode enabled', VulnerabilityLevel.MEDIUM),
                (r'(?i)ssl_verify\s*=\s*False', 'SSL verification disabled', VulnerabilityLevel.HIGH),
                (r'(?i)host\s*=\s*["\']0\.0\.0\.0["\']', 'Service exposed on all interfaces', VulnerabilityLevel.MEDIUM),
                (r'(?i)CORS_ALLOW_ALL_ORIGINS\s*=\s*True', 'CORS allows all origins', VulnerabilityLevel.MEDIUM)
            ]
            
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern, title, level in config_issues:
                    if re.search(pattern, line):
                        vulnerability = Vulnerability(
                            id=None,  # 自動生成
                            title=f"Configuration issue: {title}",
                            description=f"Insecure configuration detected",
                            level=level,
                            scan_type=ScanType.CONFIG_ANALYSIS,
                            location=f"{config_file}:{line_num}",
                            line_number=line_num,
                            file_path=str(config_file),
                            remediation=self._get_config_remediation(title),
                            metadata={'config_issue': title, 'pattern': pattern}
                        )
                        scan_result.add_vulnerability(vulnerability)
        
        except Exception as e:
            scan_result.errors.append(f"Error analyzing config file {config_file}: {e}")
    
    def _should_exclude_path(self, path: Path) -> bool:
        """パス除外判定"""
        path_str = str(path)
        
        # 除外パスチェック
        for exclude_path in self.exclude_paths:
            if exclude_path in path_str:
                return True
        
        # 除外ファイルチェック
        for exclude_file in self.exclude_files:
            if path.match(exclude_file):
                return True
        
        return False
    
    def _get_remediation_for_pattern(self, pattern: str) -> str:
        """パターン別修正提案"""
        remediation_map = {
            r'eval\s*\(': "Avoid eval(). Use safer alternatives like ast.literal_eval() for simple cases.",
            r'exec\s*\(': "Avoid exec(). Consider safer alternatives or input validation.",
            r'os\.system\s*\(': "Use subprocess.run() with shell=False instead of os.system().",
            r'subprocess\.call\s*\([^)]*shell\s*=\s*True': "Set shell=False and pass command as list.",
            r'pickle\.loads?\s*\(': "Use safer serialization like JSON, or validate pickle input.",
            r'password\s*=\s*["\'][^"\']+["\']': "Use environment variables or secure vault for passwords.",
            r'api_key\s*=\s*["\'][^"\']+["\']': "Use environment variables for API keys."
        }
        
        return remediation_map.get(pattern, "Review and secure this code pattern.")
    
    def _get_config_remediation(self, issue: str) -> str:
        """設定問題別修正提案"""
        remediation_map = {
            'Debug mode enabled': "Set DEBUG=False in production environments.",
            'SSL verification disabled': "Enable SSL verification for security.",
            'Service exposed on all interfaces': "Bind to specific interface (e.g., 127.0.0.1) if not needed.",
            'CORS allows all origins': "Specify allowed origins explicitly."
        }
        
        return remediation_map.get(issue, "Review and secure this configuration.")
    
    def _generate_recommendations(self, report: VulnerabilityReport) -> List[str]:
        """推奨事項生成"""
        recommendations = []
        summary = report.summary
        
        if summary['high_critical_count'] > 0:
            recommendations.append(
                f"Address {summary['high_critical_count']} high/critical vulnerabilities immediately."
            )
        
        if 'critical' in summary['by_level']:
            recommendations.append(
                "Critical vulnerabilities require immediate attention and should be fixed before deployment."
            )
        
        if 'secrets_scan' in summary['scan_types']:
            secret_count = sum(1 for sr in report.scan_results 
                             if sr.scan_type == ScanType.SECRETS_SCAN 
                             for _ in sr.vulnerabilities)
            if secret_count > 0:
                recommendations.append(
                    "Remove all hardcoded secrets and use environment variables or secure vault."
                )
        
        if summary['total_vulnerabilities'] > 10:
            recommendations.append(
                "Consider implementing automated security scanning in CI/CD pipeline."
            )
        
        recommendations.append("Regularly update dependencies to latest secure versions.")
        recommendations.append("Implement security code review process.")
        
        return recommendations
    
    def export_report(self, 
                     report: VulnerabilityReport, 
                     format_type: str = 'json',
                     output_file: Optional[Path] = None) -> str:
        """レポートエクスポート"""
        if format_type == 'json':
            report_data = {
                'report_id': report.report_id,
                'generated_at': report.generated_at,
                'summary': report.summary,
                'recommendations': report.recommendations,
                'scan_results': [
                    {
                        'scan_id': sr.scan_id,
                        'scan_type': sr.scan_type.value,
                        'status': sr.status,
                        'summary': sr.get_summary(),
                        'vulnerabilities': [vuln.to_dict() for vuln in sr.vulnerabilities]
                    }
                    for sr in report.scan_results
                ]
            }
            
            data = json.dumps(report_data, indent=2)
        
        elif format_type == 'html':
            data = self._generate_html_report(report)
        
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(data)
            return str(output_file)
        
        return data
    
    def _generate_html_report(self, report: VulnerabilityReport) -> str:
        """HTMLレポート生成"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Vulnerability Report - {report.report_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .critical {{ color: #d32f2f; }}
                .high {{ color: #f57c00; }}
                .medium {{ color: #fbc02d; }}
                .low {{ color: #388e3c; }}
                .info {{ color: #1976d2; }}
                .vulnerability {{ border: 1px solid #ddd; margin: 10px 0; padding: 10px; }}
                .summary {{ background: #f5f5f5; padding: 15px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>Vulnerability Report</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p>Report ID: {report.report_id}</p>
                <p>Generated: {report.generated_at}</p>
                <p>Total Vulnerabilities: {report.summary['total_vulnerabilities']}</p>
                <p>High/Critical: {report.summary['high_critical_count']}</p>
            </div>
            
            <h2>Recommendations</h2>
            <ul>
        """
        
        for rec in report.recommendations:
            html += f"<li>{rec}</li>"
        
        html += "</ul><h2>Vulnerabilities</h2>"
        
        for scan_result in report.scan_results:
            for vuln in scan_result.vulnerabilities:
                level_class = vuln.level.value
                html += f"""
                <div class="vulnerability">
                    <h3 class="{level_class}">{vuln.title} ({vuln.level.value.upper()})</h3>
                    <p>{vuln.description}</p>
                    <p><strong>Location:</strong> {vuln.location or 'N/A'}</p>
                    <p><strong>Remediation:</strong> {vuln.remediation or 'No remediation provided'}</p>
                </div>
                """
        
        html += "</body></html>"
        return html


class SecurityScanner:
    """セキュリティスキャナー統合管理"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初期化"""
        self.config = config or {}
        self.vulnerability_scanner = VulnerabilityScanner(config.get('vulnerability_scanner', {}))
        
        # スキャン履歴
        self.scan_history: List[VulnerabilityReport] = []
        
        logger.info("SecurityScanner initialized")
    
    async def comprehensive_scan(self, project_path: Path) -> VulnerabilityReport:
        """包括的セキュリティスキャン"""
        logger.info(f"Starting comprehensive security scan: {project_path}")
        
        report = await self.vulnerability_scanner.scan_project(project_path)
        self.scan_history.append(report)
        
        return report
    
    def get_scan_history(self, limit: Optional[int] = None) -> List[VulnerabilityReport]:
        """スキャン履歴取得"""
        if limit:
            return self.scan_history[-limit:]
        return self.scan_history
    
    def get_trend_analysis(self) -> Dict[str, Any]:
        """トレンド分析"""
        if len(self.scan_history) < 2:
            return {'message': 'Insufficient data for trend analysis'}
        
        recent = self.scan_history[-1]
        previous = self.scan_history[-2]
        
        recent_total = recent.summary['total_vulnerabilities']
        previous_total = previous.summary['total_vulnerabilities']
        
        change = recent_total - previous_total
        
        return {
            'total_vulnerabilities': {
                'current': recent_total,
                'previous': previous_total,
                'change': change,
                'trend': 'improving' if change < 0 else 'worsening' if change > 0 else 'stable'
            },
            'high_critical_vulnerabilities': {
                'current': recent.summary['high_critical_count'],
                'previous': previous.summary['high_critical_count'],
                'change': recent.summary['high_critical_count'] - previous.summary['high_critical_count']
            }
        }


# グローバルインスタンス（遅延初期化用）
global_vulnerability_scanner = None
global_security_scanner = None

def get_global_vulnerability_scanner():
    global global_vulnerability_scanner
    if global_vulnerability_scanner is None:
        global_vulnerability_scanner = VulnerabilityScanner()
    return global_vulnerability_scanner

def get_global_security_scanner():
    global global_security_scanner
    if global_security_scanner is None:
        global_security_scanner = SecurityScanner()
    return global_security_scanner