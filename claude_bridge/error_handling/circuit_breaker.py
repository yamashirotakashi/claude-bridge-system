"""
Claude Bridge System - Circuit Breaker
サーキットブレーカーパターン実装
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """サーキットブレーカー状態"""
    CLOSED = "closed"       # 正常状態（リクエスト通過）
    OPEN = "open"          # 障害状態（リクエスト遮断）
    HALF_OPEN = "half_open" # 回復試行状態（限定的にリクエスト通過）


@dataclass
class CircuitBreakerConfig:
    """サーキットブレーカー設定"""
    failure_threshold: int = 5              # 失敗閾値
    success_threshold: int = 3              # 成功閾値（HALF_OPEN時）
    timeout_seconds: int = 60               # OPEN状態の持続時間
    monitoring_window_seconds: int = 300    # 監視ウィンドウ（秒）
    expected_exception_types: List[type] = None  # 予期される例外タイプ
    
    def __post_init__(self):
        if self.expected_exception_types is None:
            self.expected_exception_types = [Exception]


@dataclass
class CircuitBreakerMetrics:
    """サーキットブレーカーメトリクス"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    state_transitions: int = 0
    last_failure_time: Optional[str] = None
    last_success_time: Optional[str] = None
    current_consecutive_failures: int = 0
    current_consecutive_successes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)
    
    @property
    def failure_rate(self) -> float:
        """失敗率を計算"""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100
    
    @property
    def success_rate(self) -> float:
        """成功率を計算"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


class CircuitBreaker:
    """サーキットブレーカー実装"""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """
        初期化
        
        Args:
            name: サーキットブレーカー名
            config: 設定
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        
        # 状態管理
        self.last_failure_time: Optional[float] = None
        self.next_attempt_time: Optional[float] = None
        
        # リクエスト履歴（監視ウィンドウ内）
        self.request_history: List[Dict[str, Any]] = []
        
        # 状態変更時のコールバック
        self.state_change_callbacks: List[Callable[[CircuitState, CircuitState], None]] = []
        
        logger.info(f"CircuitBreaker '{name}' initialized in {self.state.value} state")
    
    def add_state_change_callback(self, callback: Callable[[CircuitState, CircuitState], None]) -> None:
        """状態変更コールバックを追加"""
        self.state_change_callbacks.append(callback)
    
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """保護された関数呼び出し"""
        # リクエスト前チェック
        if not self._can_execute():
            self.metrics.rejected_requests += 1
            raise CircuitBreakerOpenException(
                f"Circuit breaker '{self.name}' is {self.state.value}"
            )
        
        start_time = time.time()
        
        try:
            # 関数実行
            result = await func(*args, **kwargs)
            
            # 成功処理
            self._on_success(start_time)
            return result
            
        except Exception as e:
            # 失敗処理
            self._on_failure(e, start_time)
            raise
    
    def call_sync(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """同期関数の保護された呼び出し"""
        # リクエスト前チェック
        if not self._can_execute():
            self.metrics.rejected_requests += 1
            raise CircuitBreakerOpenException(
                f"Circuit breaker '{self.name}' is {self.state.value}"
            )
        
        start_time = time.time()
        
        try:
            # 関数実行
            result = func(*args, **kwargs)
            
            # 成功処理
            self._on_success(start_time)
            return result
            
        except Exception as e:
            # 失敗処理
            self._on_failure(e, start_time)
            raise
    
    def _can_execute(self) -> bool:
        """実行可能かどうかチェック"""
        current_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # タイムアウト後にHALF_OPENに移行
            if (self.next_attempt_time and 
                current_time >= self.next_attempt_time):
                self._change_state(CircuitState.HALF_OPEN)
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def _on_success(self, start_time: float) -> None:
        """成功時の処理"""
        duration_ms = (time.time() - start_time) * 1000
        
        # メトリクス更新
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.current_consecutive_successes += 1
        self.metrics.current_consecutive_failures = 0
        self.metrics.last_success_time = datetime.now().isoformat()
        
        # リクエスト履歴更新
        self._add_request_history(True, duration_ms)
        
        # 状態遷移チェック
        if self.state == CircuitState.HALF_OPEN:
            if (self.metrics.current_consecutive_successes >= 
                self.config.success_threshold):
                self._change_state(CircuitState.CLOSED)
        
        logger.debug(f"Circuit breaker '{self.name}': Success recorded ({duration_ms:.2f}ms)")
    
    def _on_failure(self, exception: Exception, start_time: float) -> None:
        """失敗時の処理"""
        duration_ms = (time.time() - start_time) * 1000
        
        # 予期される例外タイプかチェック
        if not any(isinstance(exception, exc_type) 
                   for exc_type in self.config.expected_exception_types):
            logger.debug(f"Circuit breaker '{self.name}': Ignoring unexpected exception: {type(exception)}")
            return
        
        # メトリクス更新
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.current_consecutive_failures += 1
        self.metrics.current_consecutive_successes = 0
        self.metrics.last_failure_time = datetime.now().isoformat()
        
        # リクエスト履歴更新
        self._add_request_history(False, duration_ms, exception)
        
        self.last_failure_time = time.time()
        
        # 状態遷移チェック
        if self.state == CircuitState.CLOSED:
            if (self.metrics.current_consecutive_failures >= 
                self.config.failure_threshold):
                self._change_state(CircuitState.OPEN)
        elif self.state == CircuitState.HALF_OPEN:
            # HALF_OPEN状態で失敗したらOPENに戻る
            self._change_state(CircuitState.OPEN)
        
        logger.warning(f"Circuit breaker '{self.name}': Failure recorded - {exception}")
    
    def _add_request_history(self, 
                           success: bool, 
                           duration_ms: float, 
                           exception: Optional[Exception] = None) -> None:
        """リクエスト履歴を追加"""
        current_time = time.time()
        
        # 古い履歴を削除
        cutoff_time = current_time - self.config.monitoring_window_seconds
        self.request_history = [
            req for req in self.request_history 
            if req["timestamp"] >= cutoff_time
        ]
        
        # 新しい履歴を追加
        history_entry = {
            "timestamp": current_time,
            "success": success,
            "duration_ms": duration_ms,
            "state": self.state.value
        }
        
        if exception:
            history_entry["exception_type"] = type(exception).__name__
            history_entry["exception_message"] = str(exception)
        
        self.request_history.append(history_entry)
    
    def _change_state(self, new_state: CircuitState) -> None:
        """状態を変更"""
        old_state = self.state
        
        if old_state == new_state:
            return
        
        self.state = new_state
        self.metrics.state_transitions += 1
        
        # OPEN状態になった場合、次回試行時間を設定
        if new_state == CircuitState.OPEN:
            self.next_attempt_time = time.time() + self.config.timeout_seconds
        
        # CLOSED状態に戻った場合、カウンターをリセット
        if new_state == CircuitState.CLOSED:
            self.metrics.current_consecutive_failures = 0
            self.metrics.current_consecutive_successes = 0
            self.next_attempt_time = None
        
        logger.info(f"Circuit breaker '{self.name}': State changed from {old_state.value} to {new_state.value}")
        
        # コールバック実行
        for callback in self.state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    def force_open(self) -> None:
        """強制的にOPEN状態にする"""
        self._change_state(CircuitState.OPEN)
        logger.warning(f"Circuit breaker '{self.name}': Forced to OPEN state")
    
    def force_close(self) -> None:
        """強制的にCLOSED状態にする"""
        self._change_state(CircuitState.CLOSED)
        logger.warning(f"Circuit breaker '{self.name}': Forced to CLOSED state")
    
    def force_half_open(self) -> None:
        """強制的にHALF_OPEN状態にする"""
        self._change_state(CircuitState.HALF_OPEN)
        logger.warning(f"Circuit breaker '{self.name}': Forced to HALF_OPEN state")
    
    def reset(self) -> None:
        """サーキットブレーカーをリセット"""
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self.last_failure_time = None
        self.next_attempt_time = None
        self.request_history.clear()
        
        logger.info(f"Circuit breaker '{self.name}': Reset to initial state")
    
    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        current_time = time.time()
        
        status = {
            "name": self.name,
            "state": self.state.value,
            "metrics": self.metrics.to_dict(),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_seconds": self.config.timeout_seconds,
                "monitoring_window_seconds": self.config.monitoring_window_seconds
            },
            "next_attempt_time": None,
            "time_until_next_attempt_seconds": None
        }
        
        if self.next_attempt_time:
            status["next_attempt_time"] = datetime.fromtimestamp(
                self.next_attempt_time
            ).isoformat()
            status["time_until_next_attempt_seconds"] = max(
                0, self.next_attempt_time - current_time
            )
        
        return status
    
    def get_recent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """最近のリクエスト履歴を取得"""
        return sorted(
            self.request_history[-limit:],
            key=lambda x: x["timestamp"],
            reverse=True
        )
    
    def is_healthy(self) -> bool:
        """健全性をチェック"""
        if self.state == CircuitState.OPEN:
            return False
        
        # 最近の失敗率をチェック
        if self.metrics.total_requests > 0:
            failure_rate = self.metrics.failure_rate
            if failure_rate > 50:  # 失敗率50%超
                return False
        
        return True


class CircuitBreakerOpenException(Exception):
    """サーキットブレーカーが開いている時の例外"""
    pass


class CircuitBreakerRegistry:
    """サーキットブレーカー管理レジストリ"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        logger.info("CircuitBreakerRegistry initialized")
    
    def create_circuit_breaker(self, 
                              name: str, 
                              config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """サーキットブレーカーを作成"""
        if name in self.circuit_breakers:
            raise ValueError(f"Circuit breaker '{name}' already exists")
        
        circuit_breaker = CircuitBreaker(name, config)
        self.circuit_breakers[name] = circuit_breaker
        
        logger.info(f"Circuit breaker '{name}' created and registered")
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """サーキットブレーカーを取得"""
        return self.circuit_breakers.get(name)
    
    def remove_circuit_breaker(self, name: str) -> bool:
        """サーキットブレーカーを削除"""
        if name in self.circuit_breakers:
            del self.circuit_breakers[name]
            logger.info(f"Circuit breaker '{name}' removed")
            return True
        return False
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """全サーキットブレーカーの状態を取得"""
        return {
            name: cb.get_status() 
            for name, cb in self.circuit_breakers.items()
        }
    
    def get_unhealthy_circuit_breakers(self) -> List[str]:
        """不健全なサーキットブレーカーを取得"""
        return [
            name for name, cb in self.circuit_breakers.items()
            if not cb.is_healthy()
        ]
    
    def reset_all(self) -> None:
        """全サーキットブレーカーをリセット"""
        for circuit_breaker in self.circuit_breakers.values():
            circuit_breaker.reset()
        logger.info("All circuit breakers reset")


# グローバルレジストリ
global_circuit_breaker_registry = CircuitBreakerRegistry()