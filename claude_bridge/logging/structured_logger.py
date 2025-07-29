"""
Claude Bridge System - Structured Logger
構造化ログ記録とフィルタリング機能
"""

import json
import logging
import traceback
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """ログレベル"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    def to_logging_level(self) -> int:
        """標準ライブラリのログレベルに変換"""
        mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }
        return mapping[self]


@dataclass
class LogEntry:
    """構造化ログエントリー"""
    timestamp: str
    level: LogLevel
    message: str
    module: str
    function: str
    line_number: int
    component: str = "claude_bridge"
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)
    
    def to_json(self) -> str:
        """JSON形式に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=None)


class LogFilter:
    """ログフィルター"""
    
    def __init__(self):
        self.level_filters: List[LogLevel] = []
        self.component_filters: List[str] = []
        self.keyword_filters: List[str] = []
        self.custom_filters: List[Callable[[LogEntry], bool]] = []
    
    def add_level_filter(self, level: LogLevel) -> None:
        """レベルフィルターを追加"""
        if level not in self.level_filters:
            self.level_filters.append(level)
    
    def add_component_filter(self, component: str) -> None:
        """コンポーネントフィルターを追加"""
        if component not in self.component_filters:
            self.component_filters.append(component)
    
    def add_keyword_filter(self, keyword: str) -> None:
        """キーワードフィルターを追加"""
        if keyword not in self.keyword_filters:
            self.keyword_filters.append(keyword)
    
    def add_custom_filter(self, filter_func: Callable[[LogEntry], bool]) -> None:
        """カスタムフィルターを追加"""
        self.custom_filters.append(filter_func)
    
    def should_log(self, entry: LogEntry) -> bool:
        """ログエントリーがフィルター条件を満たすかチェック"""
        # レベルフィルター
        if self.level_filters and entry.level not in self.level_filters:
            return False
        
        # コンポーネントフィルター
        if self.component_filters and entry.component not in self.component_filters:
            return False
        
        # キーワードフィルター
        if self.keyword_filters:
            message_lower = entry.message.lower()
            if not any(keyword.lower() in message_lower for keyword in self.keyword_filters):
                return False
        
        # カスタムフィルター
        for custom_filter in self.custom_filters:
            if not custom_filter(entry):
                return False
        
        return True


class StructuredLogger:
    """構造化ログシステム"""
    
    def __init__(self, 
                 name: str = "claude_bridge",
                 log_file: Optional[Path] = None,
                 console_output: bool = True,
                 json_format: bool = True):
        """
        初期化
        
        Args:
            name: ロガー名
            log_file: ログファイルパス
            console_output: コンソール出力するかどうか
            json_format: JSON形式で出力するかどうか
        """
        self.name = name
        self.log_file = log_file
        self.console_output = console_output
        self.json_format = json_format
        
        # フィルター
        self.filters: List[LogFilter] = []
        
        # 標準ライブラリロガーを設定
        self.std_logger = logging.getLogger(name)
        self.std_logger.setLevel(logging.DEBUG)
        
        # ハンドラーをクリア
        self.std_logger.handlers.clear()
        
        # ハンドラーを設定
        self._setup_handlers()
        
        logger.info(f"StructuredLogger initialized: {name}")
    
    def _setup_handlers(self) -> None:
        """ログハンドラーを設定"""
        formatter = self._create_formatter()
        
        # ファイルハンドラー
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.std_logger.addHandler(file_handler)
        
        # コンソールハンドラー
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.std_logger.addHandler(console_handler)
    
    def _create_formatter(self) -> logging.Formatter:
        """ログフォーマッターを作成"""
        if self.json_format:
            return logging.Formatter('%(message)s')
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def _create_log_entry(self, 
                         level: LogLevel, 
                         message: str,
                         context: Optional[Dict[str, Any]] = None,
                         metadata: Optional[Dict[str, Any]] = None,
                         session_id: Optional[str] = None,
                         request_id: Optional[str] = None,
                         stack_trace: Optional[str] = None) -> LogEntry:
        """ログエントリーを作成"""
        import inspect
        
        # 呼び出し元の情報を取得
        frame = inspect.currentframe()
        try:
            # 2つ上のフレーム（この関数 → ログメソッド → 実際の呼び出し元）
            caller_frame = frame.f_back.f_back
            module_name = caller_frame.f_globals.get('__name__', 'unknown')
            function_name = caller_frame.f_code.co_name
            line_number = caller_frame.f_lineno
        finally:
            del frame
        
        return LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message,
            module=module_name,
            function=function_name,
            line_number=line_number,
            component=self.name,
            session_id=session_id,
            request_id=request_id,
            context=context,
            metadata=metadata,
            stack_trace=stack_trace
        )
    
    def _should_log(self, entry: LogEntry) -> bool:
        """ログエントリーを記録するかどうか判定"""
        for log_filter in self.filters:
            if not log_filter.should_log(entry):
                return False
        return True
    
    def _log_entry(self, entry: LogEntry) -> None:
        """ログエントリーを記録"""
        if not self._should_log(entry):
            return
        
        if self.json_format:
            log_message = entry.to_json()
        else:
            log_message = f"[{entry.component}] {entry.message}"
            if entry.context:
                log_message += f" | Context: {entry.context}"
        
        # 標準ライブラリロガーに記録
        std_level = entry.level.to_logging_level()
        self.std_logger.log(std_level, log_message)
    
    def add_filter(self, log_filter: LogFilter) -> None:
        """ログフィルターを追加"""
        self.filters.append(log_filter)
    
    def debug(self, message: str, **kwargs) -> None:
        """デバッグログを記録"""
        entry = self._create_log_entry(LogLevel.DEBUG, message, **kwargs)
        self._log_entry(entry)
    
    def info(self, message: str, **kwargs) -> None:
        """情報ログを記録"""
        entry = self._create_log_entry(LogLevel.INFO, message, **kwargs)
        self._log_entry(entry)
    
    def warning(self, message: str, **kwargs) -> None:
        """警告ログを記録"""
        entry = self._create_log_entry(LogLevel.WARNING, message, **kwargs)
        self._log_entry(entry)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """エラーログを記録"""
        stack_trace = None
        if exception:
            stack_trace = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
            stack_trace = ''.join(stack_trace)
        
        entry = self._create_log_entry(
            LogLevel.ERROR, message, stack_trace=stack_trace, **kwargs
        )
        self._log_entry(entry)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """致命的エラーログを記録"""
        stack_trace = None
        if exception:
            stack_trace = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
            stack_trace = ''.join(stack_trace)
        
        entry = self._create_log_entry(
            LogLevel.CRITICAL, message, stack_trace=stack_trace, **kwargs
        )
        self._log_entry(entry)
    
    def log_operation(self, 
                     operation: str, 
                     status: str, 
                     duration_ms: Optional[float] = None,
                     **kwargs) -> None:
        """操作ログを記録"""
        context = {
            "operation": operation,
            "status": status
        }
        if duration_ms is not None:
            context["duration_ms"] = duration_ms
        
        context.update(kwargs.get('context', {}))
        kwargs['context'] = context
        
        if status == "success":
            self.info(f"Operation completed: {operation}", **kwargs)
        elif status == "error":
            self.error(f"Operation failed: {operation}", **kwargs)
        else:
            self.info(f"Operation {status}: {operation}", **kwargs)
    
    def log_request(self, 
                   method: str, 
                   path: str, 
                   status_code: int,
                   duration_ms: float,
                   **kwargs) -> None:
        """リクエストログを記録"""
        context = {
            "http_method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms
        }
        
        context.update(kwargs.get('context', {}))
        kwargs['context'] = context
        
        level = LogLevel.INFO
        if status_code >= 500:
            level = LogLevel.ERROR
        elif status_code >= 400:
            level = LogLevel.WARNING
        
        message = f"{method} {path} - {status_code} ({duration_ms:.2f}ms)"
        
        if level == LogLevel.ERROR:
            self.error(message, **kwargs)
        elif level == LogLevel.WARNING:
            self.warning(message, **kwargs)
        else:
            self.info(message, **kwargs)