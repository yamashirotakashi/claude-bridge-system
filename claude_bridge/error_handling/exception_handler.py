"""
Claude Bridge System - Exception Handler
包括的エラーハンドリングと例外管理
"""

import json
import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Type, Union
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """エラー重要度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """エラーカテゴリ"""
    BRIDGE_ERROR = "bridge_error"
    SYNC_ERROR = "sync_error"
    NETWORK_ERROR = "network_error"
    FILE_ERROR = "file_error"
    CONFIG_ERROR = "config_error"
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    TIMEOUT_ERROR = "timeout_error"
    EXTERNAL_API_ERROR = "external_api_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """エラーコンテキスト"""
    timestamp: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    component: str = "claude_bridge"
    operation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


class BridgeException(Exception):
    """Claude Bridge共通例外"""
    
    def __init__(self, 
                 message: str,
                 category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 context: Optional[ErrorContext] = None,
                 cause: Optional[Exception] = None,
                 recovery_suggestions: Optional[List[str]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            category: エラーカテゴリ
            severity: エラー重要度
            context: エラーコンテキスト
            cause: 原因例外
            recovery_suggestions: 復旧提案
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext(
            timestamp=datetime.now().isoformat()
        )
        self.cause = cause
        self.recovery_suggestions = recovery_suggestions or []
        
        # スタックトレースを取得
        self.stack_trace = traceback.format_stack()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context.to_dict(),
            "recovery_suggestions": self.recovery_suggestions,
            "stack_trace": self.stack_trace
        }
        
        if self.cause:
            result["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause)
            }
        
        return result
    
    def to_json(self) -> str:
        """JSON形式に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ExceptionHandler:
    """例外ハンドラー"""
    
    def __init__(self):
        self.handlers: Dict[Type[Exception], Callable] = {}
        self.global_handlers: List[Callable] = []
        self.error_history: List[Dict[str, Any]] = []
        self.max_history = 1000
        
        # デフォルトハンドラーを登録
        self._register_default_handlers()
        
        logger.info("ExceptionHandler initialized")
    
    def register_handler(self, 
                        exception_type: Type[Exception], 
                        handler: Callable[[Exception, ErrorContext], None]) -> None:
        """特定の例外タイプのハンドラーを登録"""
        self.handlers[exception_type] = handler
        logger.info(f"Exception handler registered for: {exception_type.__name__}")
    
    def register_global_handler(self, 
                               handler: Callable[[Exception, ErrorContext], None]) -> None:
        """グローバルハンドラーを登録"""
        self.global_handlers.append(handler)
        logger.info("Global exception handler registered")
    
    def handle_exception(self, 
                        exception: Exception, 
                        context: Optional[ErrorContext] = None) -> None:
        """例外を処理"""
        if context is None:
            context = ErrorContext(timestamp=datetime.now().isoformat())
        
        # BridgeExceptionの場合はそのコンテキストを使用
        if isinstance(exception, BridgeException):
            context = exception.context
        
        # エラー履歴に追加
        error_info = {
            "timestamp": context.timestamp,
            "exception_type": type(exception).__name__,
            "message": str(exception),
            "context": context.to_dict()
        }
        
        if isinstance(exception, BridgeException):
            error_info.update({
                "category": exception.category.value,
                "severity": exception.severity.value,
                "recovery_suggestions": exception.recovery_suggestions
            })
        
        self.error_history.append(error_info)
        
        # 履歴サイズを制限
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        # 特定のハンドラーを実行
        exception_type = type(exception)
        if exception_type in self.handlers:
            try:
                self.handlers[exception_type](exception, context)
            except Exception as handler_error:
                logger.error(f"Error in exception handler: {handler_error}")
        
        # グローバルハンドラーを実行
        for handler in self.global_handlers:
            try:
                handler(exception, context)
            except Exception as handler_error:
                logger.error(f"Error in global exception handler: {handler_error}")
        
        # ログに記録
        self._log_exception(exception, context)
    
    def _register_default_handlers(self) -> None:
        """デフォルトハンドラーを登録"""
        
        def bridge_exception_handler(exc: BridgeException, ctx: ErrorContext):
            """BridgeException専用ハンドラー"""
            logger.error(f"Bridge Exception [{exc.severity.value}]: {exc.message}")
            if exc.recovery_suggestions:
                logger.info(f"Recovery suggestions: {exc.recovery_suggestions}")
        
        def network_error_handler(exc: Exception, ctx: ErrorContext):
            """ネットワークエラーハンドラー"""
            logger.error(f"Network error: {exc}")
            # 再試行ロジックなどを実装可能
        
        def file_error_handler(exc: Exception, ctx: ErrorContext):
            """ファイルエラーハンドラー"""
            logger.error(f"File operation error: {exc}")
            # ファイル復旧ロジックなどを実装可能
        
        # ハンドラーを登録
        self.register_handler(BridgeException, bridge_exception_handler)
        self.register_handler(ConnectionError, network_error_handler)
        self.register_handler(FileNotFoundError, file_error_handler)
        self.register_handler(PermissionError, file_error_handler)
    
    def _log_exception(self, exception: Exception, context: ErrorContext) -> None:
        """例外をログに記録"""
        if isinstance(exception, BridgeException):
            log_level = self._severity_to_log_level(exception.severity)
            logger.log(
                log_level,
                f"BridgeException [{exception.category.value}]: {exception.message}",
                extra={
                    "context": context.to_dict(),
                    "exception_data": exception.to_dict()
                }
            )
        else:
            logger.error(
                f"Unhandled exception: {type(exception).__name__}: {exception}",
                extra={
                    "context": context.to_dict(),
                    "stack_trace": traceback.format_exception(
                        type(exception), exception, exception.__traceback__
                    )
                }
            )
    
    def _severity_to_log_level(self, severity: ErrorSeverity) -> int:
        """重要度をログレベルに変換"""
        mapping = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return mapping.get(severity, logging.ERROR)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計を取得"""
        if not self.error_history:
            return {
                "total_errors": 0,
                "by_type": {},
                "by_category": {},
                "by_severity": {},
                "recent_errors": []
            }
        
        # 統計を計算
        by_type = {}
        by_category = {}
        by_severity = {}
        
        for error in self.error_history:
            # タイプ別
            exc_type = error["exception_type"]
            by_type[exc_type] = by_type.get(exc_type, 0) + 1
            
            # カテゴリ別（BridgeExceptionのみ）
            if "category" in error:
                category = error["category"]
                by_category[category] = by_category.get(category, 0) + 1
            
            # 重要度別（BridgeExceptionのみ）
            if "severity" in error:
                severity = error["severity"]
                by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "by_type": by_type,
            "by_category": by_category,
            "by_severity": by_severity,
            "recent_errors": self.error_history[-10:]  # 最新10件
        }
    
    def clear_error_history(self) -> None:
        """エラー履歴をクリア"""
        self.error_history.clear()
        logger.info("Error history cleared")
    
    def get_recovery_suggestions(self, exception: Exception) -> List[str]:
        """復旧提案を取得"""
        if isinstance(exception, BridgeException):
            return exception.recovery_suggestions
        
        # 例外タイプに基づいた一般的な提案
        suggestions = []
        
        if isinstance(exception, ConnectionError):
            suggestions.extend([
                "ネットワーク接続を確認してください",
                "プロキシ設定を確認してください",
                "しばらく待ってから再試行してください"
            ])
        elif isinstance(exception, FileNotFoundError):
            suggestions.extend([
                "ファイルパスが正しいか確認してください",
                "ファイルが存在するか確認してください",
                "権限が適切に設定されているか確認してください"
            ])
        elif isinstance(exception, PermissionError):
            suggestions.extend([
                "ファイル・ディレクトリの権限を確認してください",
                "管理者権限で実行してください",
                "ファイルが他のプロセスで使用されていないか確認してください"
            ])
        elif isinstance(exception, TimeoutError):
            suggestions.extend([
                "タイムアウト値を増やしてください",
                "処理を分割して実行してください",
                "システムの負荷を確認してください"
            ])
        
        return suggestions


# よく使用される例外クラス
class BridgeSyncError(BridgeException):
    """同期エラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SYNC_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class BridgeNetworkError(BridgeException):
    """ネットワークエラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK_ERROR,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class BridgeConfigError(BridgeException):
    """設定エラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIG_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class BridgeValidationError(BridgeException):
    """バリデーションエラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class BridgeTimeoutError(BridgeException):
    """タイムアウトエラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.TIMEOUT_ERROR,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class BridgeAuthenticationError(BridgeException):
    """認証エラー"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


# グローバル例外ハンドラーインスタンス
global_exception_handler = ExceptionHandler()


def handle_exception(exception: Exception, context: Optional[ErrorContext] = None) -> None:
    """グローバル例外処理関数"""
    global_exception_handler.handle_exception(exception, context)


def create_error_context(session_id: Optional[str] = None,
                        user_id: Optional[str] = None,
                        request_id: Optional[str] = None,
                        component: str = "claude_bridge",
                        operation: Optional[str] = None,
                        **metadata) -> ErrorContext:
    """エラーコンテキストを作成"""
    return ErrorContext(
        timestamp=datetime.now().isoformat(),
        session_id=session_id,
        user_id=user_id,
        request_id=request_id,
        component=component,
        operation=operation,
        metadata=metadata
    )