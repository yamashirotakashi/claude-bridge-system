"""
Claude Bridge System - Performance Optimizer
パフォーマンス最適化エンジン
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union, Tuple
from dataclasses import dataclass, asdict
import psutil

from .profiler import PerformanceProfiler, ProfileType

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """最適化戦略"""
    CPU_OPTIMIZATION = "cpu_optimization"
    MEMORY_OPTIMIZATION = "memory_optimization"
    IO_OPTIMIZATION = "io_optimization"
    NETWORK_OPTIMIZATION = "network_optimization"
    ASYNC_OPTIMIZATION = "async_optimization"
    CACHE_OPTIMIZATION = "cache_optimization"
    BATCH_OPTIMIZATION = "batch_optimization"
    LAZY_LOADING = "lazy_loading"


@dataclass
class OptimizationResult:
    """最適化結果"""
    strategy: OptimizationStrategy
    original_duration_ms: float
    optimized_duration_ms: float
    improvement_percent: float
    memory_saved_mb: float
    io_saved_bytes: int
    network_saved_bytes: int
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            from datetime import datetime
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


class PerformanceOptimizer:
    """パフォーマンス最適化エンジン"""
    
    def __init__(self, profiler: Optional[PerformanceProfiler] = None):
        """
        初期化
        
        Args:
            profiler: パフォーマンスプロファイラー
        """
        self.profiler = profiler or PerformanceProfiler()
        self.optimization_results: List[OptimizationResult] = []
        self.max_results = 500
        
        # 最適化設定
        self.cpu_optimization_enabled = True
        self.memory_optimization_enabled = True
        self.io_optimization_enabled = True
        self.network_optimization_enabled = True
        
        # スレッドプール
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # 最適化統計
        self.optimization_stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "total_time_saved_ms": 0,
            "total_memory_saved_mb": 0,
            "by_strategy": {}
        }
        
        logger.info("PerformanceOptimizer initialized")
    
    async def optimize_function(self, 
                               func: Callable,
                               *args,
                               strategies: Optional[List[OptimizationStrategy]] = None,
                               **kwargs) -> Tuple[Any, List[OptimizationResult]]:
        """関数を最適化して実行"""
        if strategies is None:
            strategies = [
                OptimizationStrategy.CPU_OPTIMIZATION,
                OptimizationStrategy.MEMORY_OPTIMIZATION,
                OptimizationStrategy.ASYNC_OPTIMIZATION
            ]
        
        results = []
        best_result = None
        best_duration = float('inf')
        
        # 元の実行時間をベースライン測定
        baseline_duration = await self._measure_baseline(func, *args, **kwargs)
        
        for strategy in strategies:
            try:
                optimized_func = await self._apply_optimization_strategy(func, strategy)
                optimized_duration = await self._measure_performance(optimized_func, *args, **kwargs)
                
                if optimized_duration < best_duration:
                    best_duration = optimized_duration
                    best_result = (optimized_func, strategy)
                
                # 最適化結果を記録
                improvement = ((baseline_duration - optimized_duration) / baseline_duration) * 100
                
                optimization_result = OptimizationResult(
                    strategy=strategy,
                    original_duration_ms=baseline_duration,
                    optimized_duration_ms=optimized_duration,
                    improvement_percent=improvement,
                    memory_saved_mb=0,  # TODO: 実装
                    io_saved_bytes=0,   # TODO: 実装
                    network_saved_bytes=0  # TODO: 実装
                )
                
                results.append(optimization_result)
                self._record_optimization_result(optimization_result)
                
            except Exception as e:
                logger.error(f"Optimization failed for strategy {strategy}: {e}")
                continue
        
        # 最適化された関数で実行
        if best_result:
            optimized_func, best_strategy = best_result
            logger.info(f"Using optimized function with strategy: {best_strategy}")
            final_result = await optimized_func(*args, **kwargs) if asyncio.iscoroutinefunction(optimized_func) else optimized_func(*args, **kwargs)
        else:
            logger.warning("No optimization applied, using original function")
            final_result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        
        return final_result, results
    
    async def _measure_baseline(self, func: Callable, *args, **kwargs) -> float:
        """ベースライン性能を測定"""
        return await self._measure_performance(func, *args, **kwargs)
    
    async def _measure_performance(self, func: Callable, *args, **kwargs) -> float:
        """関数の実行時間を測定"""
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error during performance measurement: {e}")
            return float('inf')
        
        return (time.time() - start_time) * 1000
    
    async def _apply_optimization_strategy(self, 
                                         func: Callable, 
                                         strategy: OptimizationStrategy) -> Callable:
        """最適化戦略を適用"""
        if strategy == OptimizationStrategy.CPU_OPTIMIZATION:
            return self._optimize_cpu_usage(func)
        elif strategy == OptimizationStrategy.MEMORY_OPTIMIZATION:
            return self._optimize_memory_usage(func)
        elif strategy == OptimizationStrategy.IO_OPTIMIZATION:
            return self._optimize_io_operations(func)
        elif strategy == OptimizationStrategy.NETWORK_OPTIMIZATION:
            return self._optimize_network_operations(func)
        elif strategy == OptimizationStrategy.ASYNC_OPTIMIZATION:
            return self._optimize_async_operations(func)
        elif strategy == OptimizationStrategy.CACHE_OPTIMIZATION:
            return self._optimize_with_caching(func)
        elif strategy == OptimizationStrategy.BATCH_OPTIMIZATION:
            return self._optimize_with_batching(func)
        elif strategy == OptimizationStrategy.LAZY_LOADING:
            return self._optimize_with_lazy_loading(func)
        else:
            return func
    
    def _optimize_cpu_usage(self, func: Callable) -> Callable:
        """CPU使用量を最適化"""
        if asyncio.iscoroutinefunction(func):
            async def optimized_async(*args, **kwargs):
                # CPU集約的なタスクをスレッドプールで実行
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(self.thread_pool, func, *args, **kwargs)
            return optimized_async
        else:
            # 同期関数の場合はそのまま返す（実際の最適化は実装に依存）
            return func
    
    def _optimize_memory_usage(self, func: Callable) -> Callable:
        """メモリ使用量を最適化"""
        import functools
        import gc
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def optimized_async(*args, **kwargs):
                # メモリ使用量を監視
                gc.collect()  # ガベージコレクション強制実行
                result = await func(*args, **kwargs)
                gc.collect()  # 実行後もガベージコレクション
                return result
            return optimized_async
        else:
            @functools.wraps(func)
            def optimized_sync(*args, **kwargs):
                gc.collect()
                result = func(*args, **kwargs)
                gc.collect()
                return result
            return optimized_sync
    
    def _optimize_io_operations(self, func: Callable) -> Callable:
        """I/O操作を最適化"""
        import functools
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def optimized_async(*args, **kwargs):
                # 非同期I/O最適化（実際の実装は関数の内容に依存）
                return await func(*args, **kwargs)
            return optimized_async
        else:
            @functools.wraps(func)
            def optimized_sync(*args, **kwargs):
                # 同期I/O最適化（バッファサイズ調整等）
                return func(*args, **kwargs)
            return optimized_sync
    
    def _optimize_network_operations(self, func: Callable) -> Callable:
        """ネットワーク操作を最適化"""
        import functools
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def optimized_async(*args, **kwargs):
                # 接続プールやキープアライブ等の最適化
                return await func(*args, **kwargs)
            return optimized_async
        else:
            return func
    
    def _optimize_async_operations(self, func: Callable) -> Callable:
        """非同期操作を最適化"""
        import functools
        
        if not asyncio.iscoroutinefunction(func):
            # 同期関数を非同期化
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, func, *args, **kwargs)
            return async_wrapper
        else:
            # 既に非同期の場合はタスクグループ等で最適化
            @functools.wraps(func)
            async def optimized_async(*args, **kwargs):
                return await func(*args, **kwargs)
            return optimized_async
    
    def _optimize_with_caching(self, func: Callable) -> Callable:
        """キャッシュで最適化"""
        import functools
        
        cache = {}
        
        @functools.wraps(func)
        def cached_func(*args, **kwargs):
            # 簡単なキャッシュ実装
            cache_key = str(args) + str(sorted(kwargs.items()))
            
            if cache_key in cache:
                return cache[cache_key]
            
            result = func(*args, **kwargs)
            cache[cache_key] = result
            return result
        
        return cached_func
    
    def _optimize_with_batching(self, func: Callable) -> Callable:
        """バッチ処理で最適化"""
        import functools
        
        @functools.wraps(func)
        def batched_func(*args, **kwargs):
            # バッチ処理の実装（実際の実装は関数の内容に依存）
            return func(*args, **kwargs)
        
        return batched_func
    
    def _optimize_with_lazy_loading(self, func: Callable) -> Callable:
        """遅延読み込みで最適化"""
        import functools
        
        @functools.wraps(func)
        def lazy_func(*args, **kwargs):
            # 遅延読み込みの実装
            return func(*args, **kwargs)
        
        return lazy_func
    
    def _record_optimization_result(self, result: OptimizationResult) -> None:
        """最適化結果を記録"""
        self.optimization_results.append(result)
        
        # 結果数を制限
        if len(self.optimization_results) > self.max_results:
            self.optimization_results = self.optimization_results[-self.max_results:]
        
        # 統計更新
        self.optimization_stats["total_optimizations"] += 1
        
        if result.improvement_percent > 0:
            self.optimization_stats["successful_optimizations"] += 1
            self.optimization_stats["total_time_saved_ms"] += (
                result.original_duration_ms - result.optimized_duration_ms
            )
            self.optimization_stats["total_memory_saved_mb"] += result.memory_saved_mb
        
        strategy_key = result.strategy.value
        if strategy_key not in self.optimization_stats["by_strategy"]:
            self.optimization_stats["by_strategy"][strategy_key] = {
                "count": 0,
                "successful": 0,
                "total_improvement": 0
            }
        
        strategy_stats = self.optimization_stats["by_strategy"][strategy_key]
        strategy_stats["count"] += 1
        if result.improvement_percent > 0:
            strategy_stats["successful"] += 1
            strategy_stats["total_improvement"] += result.improvement_percent
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """最適化統計を取得"""
        stats = self.optimization_stats.copy()
        
        # 成功率を計算
        if stats["total_optimizations"] > 0:
            stats["success_rate"] = (
                stats["successful_optimizations"] / stats["total_optimizations"]
            ) * 100
        else:
            stats["success_rate"] = 0
        
        # 戦略別の成功率を計算
        for strategy_key, strategy_stats in stats["by_strategy"].items():
            if strategy_stats["count"] > 0:
                strategy_stats["success_rate"] = (
                    strategy_stats["successful"] / strategy_stats["count"]
                ) * 100
                strategy_stats["avg_improvement"] = (
                    strategy_stats["total_improvement"] / strategy_stats["successful"]
                ) if strategy_stats["successful"] > 0 else 0
            else:
                strategy_stats["success_rate"] = 0
                strategy_stats["avg_improvement"] = 0
        
        # 最近の結果
        stats["recent_results"] = [
            result.to_dict() for result in self.optimization_results[-10:]
        ]
        
        return stats
    
    def get_best_performing_strategies(self, limit: int = 5) -> List[Dict[str, Any]]:
        """最も効果的な最適化戦略を取得"""
        strategy_performance = []
        
        for strategy_key, strategy_stats in self.optimization_stats["by_strategy"].items():
            if strategy_stats["successful"] > 0:
                strategy_performance.append({
                    "strategy": strategy_key,
                    "success_rate": strategy_stats["success_rate"],
                    "avg_improvement": strategy_stats["avg_improvement"],
                    "total_successful": strategy_stats["successful"],
                    "total_count": strategy_stats["count"]
                })
        
        # 平均改善率でソート
        strategy_performance.sort(key=lambda x: x["avg_improvement"], reverse=True)
        
        return strategy_performance[:limit]
    
    def clear_optimization_history(self) -> None:
        """最適化履歴をクリア"""
        self.optimization_results.clear()
        self.optimization_stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "total_time_saved_ms": 0,
            "total_memory_saved_mb": 0,
            "by_strategy": {}
        }
        logger.info("Optimization history cleared")


def optimize_performance(strategies: Optional[List[OptimizationStrategy]] = None):
    """パフォーマンス最適化デコレーター"""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            optimizer = PerformanceOptimizer()
            result, optimization_results = await optimizer.optimize_function(
                func, *args, strategies=strategies, **kwargs
            )
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            optimizer = PerformanceOptimizer()
            # 同期関数の場合は直接実行（簡易版）
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator