"""
Claude Bridge System - Performance Logger
パフォーマンス専用ログ記録システム
"""

import time
import threading
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging

from .structured_logger import StructuredLogger, LogLevel

logger = logging.getLogger(__name__)


@dataclass
class PerformanceLogEntry:
    """パフォーマンスログエントリー"""
    timestamp: str
    operation: str
    duration_ms: float
    status: str
    component: str
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PerformanceLogger:
    """パフォーマンス専用ロガー"""
    
    def __init__(self, 
                 name: str = "performance",
                 log_file: Optional[Path] = None,
                 enable_console: bool = False):
        """
        初期化
        
        Args:
            name: ロガー名
            log_file: ログファイルパス
            enable_console: コンソール出力を有効にするか
        """
        self.name = name
        
        # 構造化ロガーを初期化
        self.logger = StructuredLogger(
            name=f"perf_{name}",
            log_file=log_file,
            console_output=enable_console,
            json_format=True
        )
        
        # パフォーマンス統計
        self.stats: Dict[str, Dict[str, Any]] = {}
        self._stats_lock = threading.Lock()
        
        logger.info(f"PerformanceLogger initialized: {name}")
    
    def log_operation(self, 
                     operation: str,
                     duration_ms: float,
                     status: str = "success",
                     component: str = "claude_bridge",
                     session_id: Optional[str] = None,
                     request_id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """操作パフォーマンスを記録"""
        
        entry = PerformanceLogEntry(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            duration_ms=duration_ms,
            status=status,
            component=component,
            session_id=session_id,
            request_id=request_id,
            metadata=metadata or {}
        )
        
        # 構造化ログに記録
        context = {
            "operation": operation,
            "duration_ms": duration_ms,
            "status": status,
            "component": component
        }
        
        if metadata:
            context.update(metadata)
        
        self.logger.info(
            f"Operation: {operation} ({duration_ms:.2f}ms) - {status}",
            context=context,
            session_id=session_id,
            request_id=request_id
        )
        
        # 統計を更新
        self._update_stats(operation, duration_ms, status)
    
    def _update_stats(self, operation: str, duration_ms: float, status: str) -> None:
        """パフォーマンス統計を更新"""
        with self._stats_lock:
            if operation not in self.stats:
                self.stats[operation] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "total_duration_ms": 0.0,
                    "min_duration_ms": float('inf'),
                    "max_duration_ms": 0.0,
                    "avg_duration_ms": 0.0
                }
            
            stats = self.stats[operation]
            stats["total_calls"] += 1
            
            if status == "success":
                stats["successful_calls"] += 1
            else:
                stats["failed_calls"] += 1
            
            stats["total_duration_ms"] += duration_ms
            stats["min_duration_ms"] = min(stats["min_duration_ms"], duration_ms)
            stats["max_duration_ms"] = max(stats["max_duration_ms"], duration_ms)
            stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_calls"]
    
    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """パフォーマンス統計を取得"""
        with self._stats_lock:
            if operation:
                return self.stats.get(operation, {})
            else:
                return dict(self.stats)
    
    def reset_stats(self, operation: Optional[str] = None) -> None:
        """パフォーマンス統計をリセット"""
        with self._stats_lock:
            if operation:
                if operation in self.stats:
                    del self.stats[operation]
            else:
                self.stats.clear()
        
        logger.info(f"Performance stats reset for: {operation or 'all operations'}")


class RequestLogger:
    """リクエスト専用ロガー"""
    
    def __init__(self, performance_logger: PerformanceLogger):
        """
        初期化
        
        Args:
            performance_logger: パフォーマンスロガー
        """
        self.perf_logger = performance_logger
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        self._requests_lock = threading.Lock()
    
    def start_request(self, 
                     request_id: str,
                     method: str,
                     path: str,
                     session_id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """リクエスト開始を記録"""
        
        with self._requests_lock:
            self.active_requests[request_id] = {
                "method": method,
                "path": path,
                "session_id": session_id,
                "start_time": time.time(),
                "metadata": metadata or {}
            }
        
        self.perf_logger.logger.info(
            f"Request started: {method} {path}",
            context={
                "http_method": method,
                "path": path,
                "request_type": "start"
            },
            session_id=session_id,
            request_id=request_id
        )
    
    def end_request(self, 
                   request_id: str,
                   status_code: int,
                   response_size: Optional[int] = None,
                   error_message: Optional[str] = None) -> float:
        """リクエスト終了を記録"""
        
        with self._requests_lock:
            if request_id not in self.active_requests:
                logger.warning(f"Request not found for end_request: {request_id}")
                return 0.0
            
            request_info = self.active_requests.pop(request_id)
        
        # 実行時間を計算
        duration_ms = (time.time() - request_info["start_time"]) * 1000
        
        # ステータス判定
        status = "success" if 200 <= status_code < 400 else "error"
        
        # メタデータを準備
        metadata = request_info["metadata"].copy()
        metadata.update({
            "http_method": request_info["method"],
            "path": request_info["path"],
            "status_code": status_code
        })
        
        if response_size is not None:
            metadata["response_size"] = response_size
        
        if error_message:
            metadata["error_message"] = error_message
        
        # パフォーマンスログに記録
        operation = f"{request_info['method']} {request_info['path']}"
        
        self.perf_logger.log_operation(
            operation=operation,
            duration_ms=duration_ms,
            status=status,
            component="request_handler",
            session_id=request_info["session_id"],
            request_id=request_id,
            metadata=metadata
        )
        
        return duration_ms
    
    def get_active_requests(self) -> List[Dict[str, Any]]:
        """アクティブなリクエスト一覧を取得"""
        with self._requests_lock:
            current_time = time.time()
            active_list = []
            
            for request_id, request_info in self.active_requests.items():
                duration_ms = (current_time - request_info["start_time"]) * 1000
                
                active_list.append({
                    "request_id": request_id,
                    "method": request_info["method"],
                    "path": request_info["path"],
                    "session_id": request_info["session_id"],
                    "duration_ms": duration_ms,
                    "metadata": request_info["metadata"]
                })
            
            return active_list


class OperationLogger:
    """操作専用ロガー"""
    
    def __init__(self, performance_logger: PerformanceLogger):
        """
        初期化
        
        Args:
            performance_logger: パフォーマンスロガー
        """
        self.perf_logger = performance_logger
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self._operations_lock = threading.Lock()
    
    def start_operation(self, 
                       operation_id: str,
                       operation_name: str,
                       component: str = "claude_bridge",
                       session_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """操作開始を記録"""
        
        with self._operations_lock:
            self.active_operations[operation_id] = {
                "name": operation_name,
                "component": component,
                "session_id": session_id,
                "start_time": time.time(),
                "metadata": metadata or {}
            }
        
        self.perf_logger.logger.debug(
            f"Operation started: {operation_name}",
            context={
                "operation": operation_name,
                "component": component,
                "operation_type": "start"
            },
            session_id=session_id
        )
    
    def end_operation(self, 
                     operation_id: str,
                     status: str = "success",
                     result_metadata: Optional[Dict[str, Any]] = None,
                     error_message: Optional[str] = None) -> float:
        """操作終了を記録"""
        
        with self._operations_lock:
            if operation_id not in self.active_operations:
                logger.warning(f"Operation not found for end_operation: {operation_id}")
                return 0.0
            
            operation_info = self.active_operations.pop(operation_id)
        
        # 実行時間を計算
        duration_ms = (time.time() - operation_info["start_time"]) * 1000
        
        # メタデータを準備
        metadata = operation_info["metadata"].copy()
        if result_metadata:
            metadata.update(result_metadata)
        
        if error_message:
            metadata["error_message"] = error_message
        
        # パフォーマンスログに記録
        self.perf_logger.log_operation(
            operation=operation_info["name"],
            duration_ms=duration_ms,
            status=status,
            component=operation_info["component"],
            session_id=operation_info["session_id"],
            metadata=metadata
        )
        
        return duration_ms
    
    def operation_context(self, 
                         operation_name: str,
                         component: str = "claude_bridge",
                         session_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None):
        """操作コンテキストマネージャー"""
        return OperationContext(self, operation_name, component, session_id, metadata)
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """アクティブな操作一覧を取得"""
        with self._operations_lock:
            current_time = time.time()
            active_list = []
            
            for operation_id, operation_info in self.active_operations.items():
                duration_ms = (current_time - operation_info["start_time"]) * 1000
                
                active_list.append({
                    "operation_id": operation_id,
                    "name": operation_info["name"],
                    "component": operation_info["component"],
                    "session_id": operation_info["session_id"],
                    "duration_ms": duration_ms,
                    "metadata": operation_info["metadata"]
                })
            
            return active_list


class OperationContext:
    """操作コンテキストマネージャー"""
    
    def __init__(self, 
                 operation_logger: OperationLogger,
                 operation_name: str,
                 component: str = "claude_bridge",
                 session_id: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.operation_logger = operation_logger
        self.operation_name = operation_name
        self.component = component
        self.session_id = session_id
        self.metadata = metadata
        self.operation_id = f"{operation_name}_{int(time.time() * 1000000)}"
        self.status = "success"
        self.result_metadata: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None
    
    def __enter__(self):
        self.operation_logger.start_operation(
            self.operation_id,
            self.operation_name,
            self.component,
            self.session_id,
            self.metadata
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.status = "error"
            self.error_message = str(exc_val)
        
        self.operation_logger.end_operation(
            self.operation_id,
            self.status,
            self.result_metadata,
            self.error_message
        )
    
    def set_success_metadata(self, metadata: Dict[str, Any]) -> None:
        """成功時のメタデータを設定"""
        self.result_metadata = metadata
    
    def set_error(self, error_message: str) -> None:
        """エラー状態を設定"""
        self.status = "error"
        self.error_message = error_message