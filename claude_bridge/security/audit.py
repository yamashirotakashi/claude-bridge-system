"""
Claude Bridge System - Security Audit Logging
セキュリティ監査ログシステム
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import gzip

logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """監査レベル"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    SECURITY = "security"


class AuditCategory(Enum):
    """監査カテゴリ"""
    AUTH = "authentication"
    AUTHZ = "authorization"
    ACCESS = "access"
    SYSTEM = "system"
    NETWORK = "network"
    DATA = "data"
    CONFIG = "configuration"
    SECURITY = "security"


@dataclass
class AuditEvent:
    """監査イベント"""
    timestamp: str
    event_id: str
    level: AuditLevel
    category: AuditCategory
    action: str
    resource: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    result: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    risk_score: Optional[int] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.event_id is None:
            self.event_id = self._generate_event_id()
    
    def _generate_event_id(self) -> str:
        """イベントID生成"""
        content = f"{self.timestamp}{self.action}{self.user_id or ''}{self.client_ip or ''}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'timestamp': self.timestamp,
            'event_id': self.event_id,
            'level': self.level.value,
            'category': self.category.value,
            'action': self.action,
            'resource': self.resource,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'client_ip': self.client_ip,
            'user_agent': self.user_agent,
            'result': self.result,
            'details': self.details,
            'risk_score': self.risk_score
        }


@dataclass
class AuditFilter:
    """監査フィルター"""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    levels: Optional[List[AuditLevel]] = None
    categories: Optional[List[AuditCategory]] = None
    user_ids: Optional[List[str]] = None
    actions: Optional[List[str]] = None
    client_ips: Optional[List[str]] = None
    min_risk_score: Optional[int] = None
    max_risk_score: Optional[int] = None
    
    def matches(self, event: AuditEvent) -> bool:
        """イベントがフィルターにマッチするかチェック"""
        # 時間範囲チェック
        if self.start_time:
            if event.timestamp < self.start_time:
                return False
        
        if self.end_time:
            if event.timestamp > self.end_time:
                return False
        
        # レベルチェック
        if self.levels and event.level not in self.levels:
            return False
        
        # カテゴリチェック
        if self.categories and event.category not in self.categories:
            return False
        
        # ユーザーIDチェック
        if self.user_ids and event.user_id not in self.user_ids:
            return False
        
        # アクションチェック
        if self.actions and event.action not in self.actions:
            return False
        
        # クライアントIPチェック
        if self.client_ips and event.client_ip not in self.client_ips:
            return False
        
        # リスクスコアチェック
        if self.min_risk_score is not None and (event.risk_score or 0) < self.min_risk_score:
            return False
        
        if self.max_risk_score is not None and (event.risk_score or 0) > self.max_risk_score:
            return False
        
        return True


class SecurityAuditLogger:
    """セキュリティ監査ログシステム"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            config: 監査ログ設定
        """
        self.config = config or {}
        
        # ログ設定
        self.log_directory = Path(self.config.get('log_directory', './logs/audit'))
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        self.max_file_size = self.config.get('max_file_size_mb', 100) * 1024 * 1024
        self.retention_days = self.config.get('retention_days', 90)
        self.compress_old_logs = self.config.get('compress_old_logs', True)
        
        # インメモリキャッシュ
        self.recent_events: List[AuditEvent] = []
        self.max_recent_events = self.config.get('max_recent_events', 1000)
        
        # アラート設定
        self.alert_thresholds = self.config.get('alert_thresholds', {})
        self.alert_callbacks: List[callable] = []
        
        # 統計情報
        self.stats = {
            'total_events': 0,
            'events_by_level': {},
            'events_by_category': {},
            'high_risk_events': 0
        }
        
        # 現在のログファイル
        self.current_log_file = None
        self.current_file_size = 0
        
        # リアルタイム監視
        self.monitoring_enabled = self.config.get('enable_monitoring', True)
        self.monitoring_task = None
        
        logger.info("SecurityAuditLogger initialized")
    
    async def start_monitoring(self) -> None:
        """リアルタイム監視開始"""
        if self.monitoring_enabled and not self.monitoring_task:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Audit monitoring started")
    
    async def stop_monitoring(self) -> None:
        """リアルタイム監視停止"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
            logger.info("Audit monitoring stopped")
    
    def log_event(self, 
                  level: AuditLevel,
                  category: AuditCategory,
                  action: str,
                  resource: Optional[str] = None,
                  user_id: Optional[str] = None,
                  session_id: Optional[str] = None,
                  client_ip: Optional[str] = None,
                  user_agent: Optional[str] = None,
                  result: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None,
                  risk_score: Optional[int] = None) -> AuditEvent:
        """監査イベントをログ"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_id=None,  # 自動生成
            level=level,
            category=category,
            action=action,
            resource=resource,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            result=result,
            details=details,
            risk_score=risk_score
        )
        
        # ログファイルに書き込み
        self._write_to_file(event)
        
        # インメモリキャッシュに追加
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)
        
        # 統計更新
        self._update_stats(event)
        
        # アラートチェック
        self._check_alerts(event)
        
        logger.debug(f"Audit event logged: {event.event_id}")
        return event
    
    def log_authentication(self, 
                          user_id: str,
                          action: str,
                          result: str,
                          client_ip: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """認証イベントをログ"""
        risk_score = self._calculate_auth_risk_score(action, result, client_ip)
        
        return self.log_event(
            level=AuditLevel.SECURITY if result == 'failed' else AuditLevel.INFO,
            category=AuditCategory.AUTH,
            action=action,
            user_id=user_id,
            client_ip=client_ip,
            result=result,
            details=details,
            risk_score=risk_score
        )
    
    def log_authorization(self,
                         user_id: str,
                         resource: str,
                         action: str,
                         result: str,
                         details: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """認可イベントをログ"""
        return self.log_event(
            level=AuditLevel.WARNING if result == 'denied' else AuditLevel.INFO,
            category=AuditCategory.AUTHZ,
            action=action,
            resource=resource,
            user_id=user_id,
            result=result,
            details=details,
            risk_score=50 if result == 'denied' else 10
        )
    
    def log_access(self,
                   user_id: str,
                   resource: str,
                   action: str,
                   client_ip: Optional[str] = None,
                   details: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """アクセスイベントをログ"""
        return self.log_event(
            level=AuditLevel.INFO,
            category=AuditCategory.ACCESS,
            action=action,
            resource=resource,
            user_id=user_id,
            client_ip=client_ip,
            details=details,
            risk_score=5
        )
    
    def log_system_event(self,
                        action: str,
                        result: str,
                        details: Optional[Dict[str, Any]] = None,
                        risk_score: Optional[int] = None) -> AuditEvent:
        """システムイベントをログ"""
        level = AuditLevel.ERROR if result == 'failed' else AuditLevel.INFO
        
        return self.log_event(
            level=level,
            category=AuditCategory.SYSTEM,
            action=action,
            result=result,
            details=details,
            risk_score=risk_score or (70 if result == 'failed' else 20)
        )
    
    def log_security_incident(self,
                             action: str,
                             severity: str,
                             user_id: Optional[str] = None,
                             client_ip: Optional[str] = None,
                             details: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """セキュリティインシデントをログ"""
        risk_score = {
            'low': 30,
            'medium': 60,
            'high': 80,
            'critical': 95
        }.get(severity, 50)
        
        return self.log_event(
            level=AuditLevel.CRITICAL,
            category=AuditCategory.SECURITY,
            action=action,
            user_id=user_id,
            client_ip=client_ip,
            result='incident',
            details={**(details or {}), 'severity': severity},
            risk_score=risk_score
        )
    
    def search_events(self, filter_obj: AuditFilter, limit: Optional[int] = None) -> List[AuditEvent]:
        """イベント検索"""
        matching_events = []
        
        # インメモリキャッシュから検索
        for event in reversed(self.recent_events):
            if filter_obj.matches(event):
                matching_events.append(event)
                if limit and len(matching_events) >= limit:
                    break
        
        return matching_events
    
    async def search_events_async(self, 
                                filter_obj: AuditFilter,
                                limit: Optional[int] = None) -> AsyncGenerator[AuditEvent, None]:
        """非同期イベント検索"""
        count = 0
        
        # ログファイルから検索
        for log_file in self._get_log_files():
            if limit and count >= limit:
                break
            
            try:
                async for event in self._read_log_file_async(log_file):
                    if filter_obj.matches(event):
                        yield event
                        count += 1
                        if limit and count >= limit:
                            break
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
                continue
    
    def get_statistics(self, 
                      start_time: Optional[str] = None,
                      end_time: Optional[str] = None) -> Dict[str, Any]:
        """統計情報取得"""
        stats = {
            'total_events': self.stats['total_events'],
            'events_by_level': dict(self.stats['events_by_level']),
            'events_by_category': dict(self.stats['events_by_category']),
            'high_risk_events': self.stats['high_risk_events'],
            'recent_events_count': len(self.recent_events)
        }
        
        # 時間範囲が指定された場合のフィルタリング
        if start_time or end_time:
            filter_obj = AuditFilter(start_time=start_time, end_time=end_time)
            filtered_events = self.search_events(filter_obj)
            
            stats['filtered_events_count'] = len(filtered_events)
            stats['filtered_events_by_level'] = {}
            stats['filtered_events_by_category'] = {}
            
            for event in filtered_events:
                level_key = event.level.value
                category_key = event.category.value
                
                stats['filtered_events_by_level'][level_key] = \
                    stats['filtered_events_by_level'].get(level_key, 0) + 1
                
                stats['filtered_events_by_category'][category_key] = \
                    stats['filtered_events_by_category'].get(category_key, 0) + 1
        
        return stats
    
    def add_alert_callback(self, callback: callable) -> None:
        """アラートコールバック追加"""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: callable) -> None:
        """アラートコールバック削除"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    def export_events(self, 
                     filter_obj: Optional[AuditFilter] = None,
                     format_type: str = 'json',
                     output_file: Optional[Path] = None) -> Optional[str]:
        """イベントエクスポート"""
        events = self.search_events(filter_obj or AuditFilter())
        
        if format_type == 'json':
            data = json.dumps([event.to_dict() for event in events], indent=2)
        elif format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            if events:
                fieldnames = events[0].to_dict().keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for event in events:
                    writer.writerow(event.to_dict())
            data = output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(data)
            return str(output_file)
        
        return data
    
    def cleanup_old_logs(self) -> int:
        """古いログファイルクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        
        for log_file in self.log_directory.glob('audit_*.log*'):
            try:
                # ファイル名から日付を抽出
                stat = log_file.stat()
                file_date = datetime.fromtimestamp(stat.st_mtime)
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed old log file: {log_file}")
                
            except Exception as e:
                logger.error(f"Error processing log file {log_file}: {e}")
        
        return removed_count
    
    def _write_to_file(self, event: AuditEvent) -> None:
        """ファイルに書き込み"""
        if not self.current_log_file or self.current_file_size >= self.max_file_size:
            self._rotate_log_file()
        
        log_line = json.dumps(event.to_dict()) + '\n'
        
        try:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
            
            self.current_file_size += len(log_line.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def _rotate_log_file(self) -> None:
        """ログファイルローテーション"""
        if self.current_log_file and self.compress_old_logs:
            self._compress_log_file(self.current_log_file)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_log_file = self.log_directory / f"audit_{timestamp}.log"
        self.current_file_size = 0
        
        logger.info(f"Rotated to new log file: {self.current_log_file}")
    
    def _compress_log_file(self, file_path: Path) -> None:
        """ログファイル圧縮"""
        try:
            compressed_path = file_path.with_suffix('.log.gz')
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            file_path.unlink()
            logger.info(f"Compressed log file: {compressed_path}")
            
        except Exception as e:
            logger.error(f"Failed to compress log file {file_path}: {e}")
    
    def _update_stats(self, event: AuditEvent) -> None:
        """統計更新"""
        self.stats['total_events'] += 1
        
        level_key = event.level.value
        self.stats['events_by_level'][level_key] = \
            self.stats['events_by_level'].get(level_key, 0) + 1
        
        category_key = event.category.value
        self.stats['events_by_category'][category_key] = \
            self.stats['events_by_category'].get(category_key, 0) + 1
        
        if event.risk_score and event.risk_score >= 70:
            self.stats['high_risk_events'] += 1
    
    def _check_alerts(self, event: AuditEvent) -> None:
        """アラートチェック"""
        # 高リスクイベント
        if event.risk_score and event.risk_score >= 80:
            self._trigger_alert('high_risk_event', event)
        
        # 認証失敗
        if event.category == AuditCategory.AUTH and event.result == 'failed':
            self._trigger_alert('auth_failure', event)
        
        # セキュリティインシデント
        if event.category == AuditCategory.SECURITY:
            self._trigger_alert('security_incident', event)
    
    def _trigger_alert(self, alert_type: str, event: AuditEvent) -> None:
        """アラート発生"""
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, event)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def _calculate_auth_risk_score(self, 
                                  action: str, 
                                  result: str, 
                                  client_ip: Optional[str]) -> int:
        """認証リスクスコア計算"""
        base_score = 10
        
        if result == 'failed':
            base_score += 40
        
        if action in ['password_auth', 'api_key_auth']:
            base_score += 10
        
        # IPアドレスベースのリスク評価（簡略化）
        if client_ip and self._is_suspicious_ip(client_ip):
            base_score += 30
        
        return min(base_score, 100)
    
    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """疑わしいIPアドレスチェック（簡略化）"""
        # 実装簡略化のため、基本的なチェックのみ
        return False
    
    def _get_log_files(self) -> List[Path]:
        """ログファイル一覧取得"""
        log_files = []
        
        # 通常のログファイル
        log_files.extend(self.log_directory.glob('audit_*.log'))
        
        # 圧縮されたログファイル
        log_files.extend(self.log_directory.glob('audit_*.log.gz'))
        
        return sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    async def _read_log_file_async(self, file_path: Path) -> AsyncGenerator[AuditEvent, None]:
        """ログファイル非同期読み込み"""
        try:
            if file_path.suffix == '.gz':
                import gzip
                open_func = gzip.open
            else:
                open_func = open
            
            with open_func(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        event = AuditEvent(**data)
                        yield event
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Invalid log line in {file_path}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {e}")
    
    async def _monitoring_loop(self) -> None:
        """監視ループ"""
        while True:
            try:
                # 定期的なクリーンアップ
                if datetime.now().hour == 2:  # 2時にクリーンアップ
                    self.cleanup_old_logs()
                
                # 統計更新
                await asyncio.sleep(60)  # 1分間隔
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)


# グローバルインスタンス（遅延初期化用）
global_audit_logger = None

def get_global_audit_logger():
    global global_audit_logger
    if global_audit_logger is None:
        global_audit_logger = SecurityAuditLogger()
    return global_audit_logger