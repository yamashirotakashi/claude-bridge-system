"""
Claude Bridge System - Recovery Manager
自動復旧機能とエラー回復メカニズム
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union
from dataclasses import dataclass, asdict

from .exception_handler import BridgeException, ErrorSeverity, ErrorCategory, ErrorContext

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """復旧戦略"""
    RETRY = "retry"                    # 再試行
    FALLBACK = "fallback"              # フォールバック
    RESTART = "restart"                # 再起動
    RESET = "reset"                    # リセット
    MANUAL = "manual"                  # 手動介入
    IGNORE = "ignore"                  # 無視


class RecoveryAction(Enum):
    """復旧アクション"""
    RECONNECT = "reconnect"            # 再接続
    RELOAD_CONFIG = "reload_config"    # 設定再読み込み
    CLEAR_CACHE = "clear_cache"        # キャッシュクリア
    RESET_STATE = "reset_state"        # 状態リセット
    RESTART_SERVICE = "restart_service"  # サービス再起動
    SWITCH_ENDPOINT = "switch_endpoint"  # エンドポイント切り替え
    CUSTOM = "custom"                  # カスタム処理


@dataclass
class RecoveryResult:
    """復旧結果"""
    success: bool
    strategy: RecoveryStrategy
    action: RecoveryAction
    attempts: int
    duration_ms: float
    message: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class RecoveryConfig:
    """復旧設定"""
    max_retries: int = 3
    retry_delay_ms: int = 1000
    backoff_multiplier: float = 2.0
    max_delay_ms: int = 30000
    timeout_ms: int = 60000
    enable_fallback: bool = True
    enable_auto_restart: bool = False
    
    def get_retry_delay(self, attempt: int) -> float:
        """再試行遅延時間を計算"""
        delay = self.retry_delay_ms * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay_ms) / 1000.0


class RecoveryManager:
    """復旧管理システム"""
    
    def __init__(self, config: Optional[RecoveryConfig] = None):
        """
        初期化
        
        Args:
            config: 復旧設定
        """
        self.config = config or RecoveryConfig()
        
        # 復旧ハンドラー
        self.recovery_handlers: Dict[ErrorCategory, Callable] = {}
        self.custom_handlers: Dict[str, Callable] = {}
        
        # 復旧履歴
        self.recovery_history: List[RecoveryResult] = []
        self.max_history = 1000
        
        # 統計情報
        self.recovery_stats = {
            "total_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "by_strategy": {},
            "by_category": {}
        }
        
        # デフォルトハンドラーを登録
        self._register_default_handlers()
        
        logger.info("RecoveryManager initialized")
    
    def register_recovery_handler(self, 
                                 category: ErrorCategory,
                                 handler: Callable[[BridgeException, RecoveryConfig], Awaitable[RecoveryResult]]) -> None:
        """復旧ハンドラーを登録"""
        self.recovery_handlers[category] = handler
        logger.info(f"Recovery handler registered for: {category.value}")
    
    def register_custom_handler(self, 
                               name: str,
                               handler: Callable[[Any, RecoveryConfig], Awaitable[RecoveryResult]]) -> None:
        """カスタム復旧ハンドラーを登録"""
        self.custom_handlers[name] = handler
        logger.info(f"Custom recovery handler registered: {name}")
    
    async def attempt_recovery(self, 
                              exception: BridgeException,
                              custom_config: Optional[RecoveryConfig] = None) -> RecoveryResult:
        """復旧を試行"""
        config = custom_config or self.config
        start_time = time.time()
        
        # 統計更新
        self.recovery_stats["total_attempts"] += 1
        category_stats = self.recovery_stats["by_category"].get(exception.category.value, 0)
        self.recovery_stats["by_category"][exception.category.value] = category_stats + 1
        
        logger.info(f"Attempting recovery for: {exception.category.value} - {exception.message}")
        
        result = None
        
        # 適切なハンドラーを選択して実行
        if exception.category in self.recovery_handlers:
            handler = self.recovery_handlers[exception.category]
            try:
                result = await handler(exception, config)
            except Exception as recovery_error:
                logger.error(f"Recovery handler failed: {recovery_error}")
                result = RecoveryResult(
                    success=False,
                    strategy=RecoveryStrategy.MANUAL,
                    action=RecoveryAction.CUSTOM,
                    attempts=1,
                    duration_ms=(time.time() - start_time) * 1000,
                    message=f"Recovery handler error: {recovery_error}",
                    timestamp=datetime.now().isoformat()
                )
        else:
            # デフォルト復旧を実行
            result = await self._default_recovery(exception, config)
        
        # 結果を記録
        self._record_recovery_result(result)
        
        return result
    
    async def execute_custom_recovery(self, 
                                    handler_name: str,
                                    context: Any,
                                    custom_config: Optional[RecoveryConfig] = None) -> RecoveryResult:
        """カスタム復旧を実行"""
        if handler_name not in self.custom_handlers:
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.MANUAL,
                action=RecoveryAction.CUSTOM,
                attempts=1,
                duration_ms=0,
                message=f"Custom handler not found: {handler_name}",
                timestamp=datetime.now().isoformat()
            )
        
        config = custom_config or self.config
        handler = self.custom_handlers[handler_name]
        
        start_time = time.time()
        
        try:
            result = await handler(context, config)
            self._record_recovery_result(result)
            return result
        except Exception as e:
            result = RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.MANUAL,
                action=RecoveryAction.CUSTOM,
                attempts=1,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"Custom recovery failed: {e}",
                timestamp=datetime.now().isoformat()
            )
            self._record_recovery_result(result)
            return result
    
    def _register_default_handlers(self) -> None:
        """デフォルト復旧ハンドラーを登録"""
        
        async def network_error_recovery(exc: BridgeException, config: RecoveryConfig) -> RecoveryResult:
            """ネットワークエラー復旧"""
            start_time = time.time()
            
            for attempt in range(1, config.max_retries + 1):
                logger.info(f"Network recovery attempt {attempt}/{config.max_retries}")
                
                # 遅延
                if attempt > 1:
                    delay = config.get_retry_delay(attempt)
                    await asyncio.sleep(delay)
                
                # ダミー復旧処理（実際の実装では具体的な復旧処理）
                try:
                    # 例: 接続テスト、DNS解決テストなど
                    await asyncio.sleep(0.1)  # 模擬処理
                    
                    # 成功と仮定
                    return RecoveryResult(
                        success=True,
                        strategy=RecoveryStrategy.RETRY,
                        action=RecoveryAction.RECONNECT,
                        attempts=attempt,
                        duration_ms=(time.time() - start_time) * 1000,
                        message=f"Network recovery successful after {attempt} attempts",
                        timestamp=datetime.now().isoformat()
                    )
                except Exception as retry_error:
                    logger.warning(f"Recovery attempt {attempt} failed: {retry_error}")
                    continue
            
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.RETRY,
                action=RecoveryAction.RECONNECT,
                attempts=config.max_retries,
                duration_ms=(time.time() - start_time) * 1000,
                message="Network recovery failed after all retry attempts",
                timestamp=datetime.now().isoformat()
            )
        
        async def sync_error_recovery(exc: BridgeException, config: RecoveryConfig) -> RecoveryResult:
            """同期エラー復旧"""
            start_time = time.time()
            
            logger.info("Attempting sync error recovery")
            
            try:
                # 状態リセット
                await asyncio.sleep(0.1)  # 模擬処理
                
                return RecoveryResult(
                    success=True,
                    strategy=RecoveryStrategy.RESET,
                    action=RecoveryAction.RESET_STATE,
                    attempts=1,
                    duration_ms=(time.time() - start_time) * 1000,
                    message="Sync state reset successful",
                    timestamp=datetime.now().isoformat()
                )
            except Exception as e:
                return RecoveryResult(
                    success=False,
                    strategy=RecoveryStrategy.RESET,
                    action=RecoveryAction.RESET_STATE,
                    attempts=1,
                    duration_ms=(time.time() - start_time) * 1000,
                    message=f"Sync recovery failed: {e}",
                    timestamp=datetime.now().isoformat()
                )
        
        async def config_error_recovery(exc: BridgeException, config: RecoveryConfig) -> RecoveryResult:
            """設定エラー復旧"""
            start_time = time.time()
            
            logger.info("Attempting config error recovery")
            
            try:
                # 設定再読み込み
                await asyncio.sleep(0.1)  # 模擬処理
                
                return RecoveryResult(
                    success=True,
                    strategy=RecoveryStrategy.FALLBACK,
                    action=RecoveryAction.RELOAD_CONFIG,
                    attempts=1,
                    duration_ms=(time.time() - start_time) * 1000,
                    message="Configuration reloaded successfully",
                    timestamp=datetime.now().isoformat()
                )
            except Exception as e:
                return RecoveryResult(
                    success=False,
                    strategy=RecoveryStrategy.FALLBACK,
                    action=RecoveryAction.RELOAD_CONFIG,
                    attempts=1,
                    duration_ms=(time.time() - start_time) * 1000,
                    message=f"Config recovery failed: {e}",
                    timestamp=datetime.now().isoformat()
                )
        
        # ハンドラーを登録
        self.register_recovery_handler(ErrorCategory.NETWORK_ERROR, network_error_recovery)
        self.register_recovery_handler(ErrorCategory.SYNC_ERROR, sync_error_recovery)
        self.register_recovery_handler(ErrorCategory.CONFIG_ERROR, config_error_recovery)
    
    async def _default_recovery(self, 
                               exception: BridgeException, 
                               config: RecoveryConfig) -> RecoveryResult:
        """デフォルト復旧処理"""
        start_time = time.time()
        
        logger.info(f"Executing default recovery for: {exception.category.value}")
        
        # 重要度に基づいた復旧戦略
        if exception.severity == ErrorSeverity.CRITICAL:
            strategy = RecoveryStrategy.RESTART
            action = RecoveryAction.RESTART_SERVICE
        elif exception.severity == ErrorSeverity.HIGH:
            strategy = RecoveryStrategy.RESET
            action = RecoveryAction.RESET_STATE
        else:
            strategy = RecoveryStrategy.RETRY
            action = RecoveryAction.CUSTOM
        
        try:
            # 模擬復旧処理
            await asyncio.sleep(0.1)
            
            return RecoveryResult(
                success=True,
                strategy=strategy,
                action=action,
                attempts=1,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"Default recovery completed for {exception.category.value}",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy=strategy,
                action=action,
                attempts=1,
                duration_ms=(time.time() - start_time) * 1000,
                message=f"Default recovery failed: {e}",
                timestamp=datetime.now().isoformat()
            )
    
    def _record_recovery_result(self, result: RecoveryResult) -> None:
        """復旧結果を記録"""
        # 履歴に追加
        self.recovery_history.append(result)
        
        # 履歴サイズを制限
        if len(self.recovery_history) > self.max_history:
            self.recovery_history = self.recovery_history[-self.max_history:]
        
        # 統計更新
        if result.success:
            self.recovery_stats["successful_recoveries"] += 1
        else:
            self.recovery_stats["failed_recoveries"] += 1
        
        strategy_stats = self.recovery_stats["by_strategy"].get(result.strategy.value, 0)
        self.recovery_stats["by_strategy"][result.strategy.value] = strategy_stats + 1
        
        logger.info(f"Recovery result recorded: {result.success} - {result.message}")
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """復旧統計を取得"""
        success_rate = 0.0
        if self.recovery_stats["total_attempts"] > 0:
            success_rate = (self.recovery_stats["successful_recoveries"] / 
                          self.recovery_stats["total_attempts"]) * 100
        
        return {
            "total_attempts": self.recovery_stats["total_attempts"],
            "successful_recoveries": self.recovery_stats["successful_recoveries"],
            "failed_recoveries": self.recovery_stats["failed_recoveries"],
            "success_rate_percent": round(success_rate, 2),
            "by_strategy": self.recovery_stats["by_strategy"],
            "by_category": self.recovery_stats["by_category"],
            "recent_recoveries": [result.to_dict() for result in self.recovery_history[-10:]]
        }
    
    def clear_recovery_history(self) -> None:
        """復旧履歴をクリア"""
        self.recovery_history.clear()
        self.recovery_stats = {
            "total_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "by_strategy": {},
            "by_category": {}
        }
        logger.info("Recovery history and statistics cleared")
    
    def get_recent_failures(self, hours: int = 24) -> List[RecoveryResult]:
        """最近の失敗を取得"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_failures = []
        for result in self.recovery_history:
            result_time = datetime.fromisoformat(result.timestamp)
            if result_time >= cutoff_time and not result.success:
                recent_failures.append(result)
        
        return recent_failures
    
    def is_healthy(self) -> bool:
        """システムの健全性を判定"""
        # 最近1時間の失敗率をチェック
        recent_failures = self.get_recent_failures(hours=1)
        
        if len(recent_failures) >= 10:  # 1時間に10回以上失敗
            return False
        
        # 全体的な成功率をチェック
        stats = self.get_recovery_statistics()
        if stats["success_rate_percent"] < 50:  # 成功率50%未満
            return False
        
        return True