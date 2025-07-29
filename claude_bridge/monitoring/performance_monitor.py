"""
Claude Bridge System - Performance Monitor
パフォーマンス監視とベンチマーク機能
"""

import time
import logging
import asyncio
import statistics
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""
    operation: str
    duration_ms: float
    success: bool
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BenchmarkResult:
    """ベンチマーク結果"""
    name: str
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_duration_ms: float
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    median_duration_ms: float
    percentile_95_ms: float
    percentile_99_ms: float
    operations_per_second: float
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PerformanceMonitor:
    """パフォーマンス監視システム"""
    
    def __init__(self, max_history: int = 10000):
        """
        初期化
        
        Args:
            max_history: 保持する履歴の最大数
        """
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.operation_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.benchmark_results: Dict[str, BenchmarkResult] = {}
        
        logger.info("PerformanceMonitor initialized")
    
    def record_operation(self, 
                        operation: str, 
                        duration_ms: float, 
                        success: bool = True,
                        metadata: Optional[Dict[str, Any]] = None,
                        memory_usage_mb: float = 0.0,
                        cpu_usage_percent: float = 0.0) -> None:
        """操作のパフォーマンスを記録"""
        
        metrics = PerformanceMetrics(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {},
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent
        )
        
        # 全体履歴に追加
        self.metrics_history.append(metrics)
        
        # 操作別履歴に追加
        self.operation_metrics[operation].append(metrics)
        
        logger.debug(f"Performance recorded: {operation} = {duration_ms:.2f}ms (success: {success})")
    
    def get_operation_stats(self, operation: str, limit: int = 100) -> Dict[str, Any]:
        """特定操作の統計情報を取得"""
        if operation not in self.operation_metrics:
            return {"error": f"No metrics found for operation: {operation}"}
        
        metrics = list(self.operation_metrics[operation])[-limit:]
        if not metrics:
            return {"error": f"No metrics data for operation: {operation}"}
        
        # 成功した操作のみを対象に統計計算
        successful_metrics = [m for m in metrics if m.success]
        all_durations = [m.duration_ms for m in metrics]
        successful_durations = [m.duration_ms for m in successful_metrics]
        
        if not successful_durations:
            return {
                "operation": operation,
                "total_operations": len(metrics),
                "successful_operations": 0,
                "failed_operations": len(metrics),
                "success_rate": 0.0,
                "error": "No successful operations found"
            }
        
        # 統計計算
        stats = {
            "operation": operation,
            "total_operations": len(metrics),
            "successful_operations": len(successful_metrics),
            "failed_operations": len(metrics) - len(successful_metrics),
            "success_rate": len(successful_metrics) / len(metrics),
            "avg_duration_ms": statistics.mean(successful_durations),
            "min_duration_ms": min(successful_durations),
            "max_duration_ms": max(successful_durations),
            "median_duration_ms": statistics.median(successful_durations),
            "std_dev_ms": statistics.stdev(successful_durations) if len(successful_durations) > 1 else 0.0,
            "total_duration_ms": sum(all_durations),
            "last_updated": datetime.now().isoformat()
        }
        
        # パーセンタイル計算
        if len(successful_durations) >= 2:
            sorted_durations = sorted(successful_durations)
            stats["percentile_95_ms"] = self._percentile(sorted_durations, 95)
            stats["percentile_99_ms"] = self._percentile(sorted_durations, 99)
        else:
            stats["percentile_95_ms"] = stats["max_duration_ms"]
            stats["percentile_99_ms"] = stats["max_duration_ms"]
        
        # 操作毎秒数（最近の操作から計算）
        if len(successful_metrics) >= 2:
            time_range_seconds = self._calculate_time_range_seconds(successful_metrics)
            if time_range_seconds > 0:
                stats["operations_per_second"] = len(successful_metrics) / time_range_seconds
            else:
                stats["operations_per_second"] = 0.0
        else:
            stats["operations_per_second"] = 0.0
        
        return stats
    
    def get_all_operations_summary(self) -> Dict[str, Any]:
        """全操作のサマリーを取得"""
        summary = {
            "total_operations": len(self.metrics_history),
            "unique_operations": len(self.operation_metrics),
            "operations": {},
            "overall_stats": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # 各操作の簡易統計
        for operation in self.operation_metrics.keys():
            stats = self.get_operation_stats(operation, limit=50)  # 最新50件で統計
            summary["operations"][operation] = {
                "total_ops": stats.get("total_operations", 0),
                "success_rate": stats.get("success_rate", 0.0),
                "avg_duration_ms": stats.get("avg_duration_ms", 0.0),
                "ops_per_second": stats.get("operations_per_second", 0.0)
            }
        
        # 全体統計
        if self.metrics_history:
            all_metrics = list(self.metrics_history)
            successful_metrics = [m for m in all_metrics if m.success]
            
            summary["overall_stats"] = {
                "total_operations": len(all_metrics),
                "successful_operations": len(successful_metrics),
                "overall_success_rate": len(successful_metrics) / len(all_metrics),
                "avg_duration_ms": statistics.mean([m.duration_ms for m in successful_metrics]) if successful_metrics else 0.0,
                "slowest_operation": max(all_metrics, key=lambda x: x.duration_ms, default=None),
                "fastest_operation": min([m for m in all_metrics if m.success], key=lambda x: x.duration_ms, default=None)
            }
            
            # 最も遅い・速い操作の情報を整理
            if summary["overall_stats"]["slowest_operation"]:
                slowest = summary["overall_stats"]["slowest_operation"]
                summary["overall_stats"]["slowest_operation"] = {
                    "operation": slowest.operation,
                    "duration_ms": slowest.duration_ms,
                    "timestamp": slowest.timestamp
                }
            
            if summary["overall_stats"]["fastest_operation"]:
                fastest = summary["overall_stats"]["fastest_operation"]
                summary["overall_stats"]["fastest_operation"] = {
                    "operation": fastest.operation,
                    "duration_ms": fastest.duration_ms,
                    "timestamp": fastest.timestamp
                }
        
        return summary
    
    async def run_benchmark(self, 
                           name: str, 
                           operation_func: Callable,
                           iterations: int = 100,
                           concurrent: bool = False,
                           concurrency_level: int = 10,
                           warm_up_iterations: int = 10) -> BenchmarkResult:
        """ベンチマークを実行"""
        logger.info(f"Starting benchmark: {name} ({iterations} iterations)")
        
        # ウォームアップ
        if warm_up_iterations > 0:
            logger.info(f"Running {warm_up_iterations} warm-up iterations")
            for _ in range(warm_up_iterations):
                try:
                    if asyncio.iscoroutinefunction(operation_func):
                        await operation_func()
                    else:
                        operation_func()
                except Exception as e:
                    logger.warning(f"Warm-up iteration failed: {e}")
        
        # ベンチマーク実行
        start_time = time.time()
        durations = []
        successful_operations = 0
        failed_operations = 0
        
        if concurrent and asyncio.iscoroutinefunction(operation_func):
            # 並行実行（非同期）
            durations, successful_operations, failed_operations = await self._run_concurrent_benchmark(
                operation_func, iterations, concurrency_level
            )
        else:
            # 順次実行
            for i in range(iterations):
                op_start = time.time()
                success = True
                
                try:
                    if asyncio.iscoroutinefunction(operation_func):
                        await operation_func()
                    else:
                        operation_func()
                    successful_operations += 1
                except Exception as e:
                    logger.warning(f"Benchmark iteration {i+1} failed: {e}")
                    failed_operations += 1
                    success = False
                
                duration_ms = (time.time() - op_start) * 1000
                durations.append(duration_ms)
                
                # パフォーマンス記録
                self.record_operation(
                    operation=f"benchmark_{name}",
                    duration_ms=duration_ms,
                    success=success,
                    metadata={"iteration": i+1, "benchmark": True}
                )
        
        total_duration_ms = (time.time() - start_time) * 1000
        
        # 結果を計算
        result = self._calculate_benchmark_result(
            name, durations, successful_operations, failed_operations, total_duration_ms
        )
        
        self.benchmark_results[name] = result
        logger.info(f"Benchmark completed: {name}")
        
        return result
    
    async def _run_concurrent_benchmark(self, 
                                       operation_func: Callable,
                                       iterations: int,
                                       concurrency_level: int) -> tuple:
        """並行ベンチマークを実行"""
        semaphore = asyncio.Semaphore(concurrency_level)
        durations = []
        successful_operations = 0
        failed_operations = 0
        
        async def bounded_operation(iteration: int):
            nonlocal successful_operations, failed_operations
            async with semaphore:
                start_time = time.time()
                success = True
                
                try:
                    await operation_func()
                    successful_operations += 1
                except Exception as e:
                    logger.warning(f"Concurrent benchmark iteration {iteration} failed: {e}")
                    failed_operations += 1
                    success = False
                
                duration_ms = (time.time() - start_time) * 1000
                durations.append(duration_ms)
                
                return duration_ms, success
        
        # 並行実行
        tasks = [bounded_operation(i) for i in range(iterations)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return durations, successful_operations, failed_operations
    
    def _calculate_benchmark_result(self, 
                                   name: str,
                                   durations: List[float],
                                   successful_ops: int,
                                   failed_ops: int,
                                   total_duration_ms: float) -> BenchmarkResult:
        """ベンチマーク結果を計算"""
        total_ops = successful_ops + failed_ops
        
        if not durations:
            return BenchmarkResult(
                name=name,
                total_operations=total_ops,
                successful_operations=successful_ops,
                failed_operations=failed_ops,
                total_duration_ms=total_duration_ms,
                avg_duration_ms=0.0,
                min_duration_ms=0.0,
                max_duration_ms=0.0,
                median_duration_ms=0.0,
                percentile_95_ms=0.0,
                percentile_99_ms=0.0,
                operations_per_second=0.0,
                timestamp=datetime.now().isoformat(),
                metadata={"error": "No duration data available"}
            )
        
        # 成功した操作のみで統計計算
        successful_durations = durations[:successful_ops] if successful_ops > 0 else []
        
        if not successful_durations:
            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            median_duration = statistics.median(durations)
            p95 = self._percentile(sorted(durations), 95)
            p99 = self._percentile(sorted(durations), 99)
        else:
            avg_duration = statistics.mean(successful_durations)
            min_duration = min(successful_durations)
            max_duration = max(successful_durations)
            median_duration = statistics.median(successful_durations)
            p95 = self._percentile(sorted(successful_durations), 95)
            p99 = self._percentile(sorted(successful_durations), 99)
        
        # 操作毎秒数
        ops_per_second = (successful_ops / (total_duration_ms / 1000)) if total_duration_ms > 0 else 0.0
        
        return BenchmarkResult(
            name=name,
            total_operations=total_ops,
            successful_operations=successful_ops,
            failed_operations=failed_ops,
            total_duration_ms=total_duration_ms,
            avg_duration_ms=avg_duration,
            min_duration_ms=min_duration,
            max_duration_ms=max_duration,
            median_duration_ms=median_duration,
            percentile_95_ms=p95,
            percentile_99_ms=p99,
            operations_per_second=ops_per_second,
            timestamp=datetime.now().isoformat(),
            metadata={
                "success_rate": successful_ops / total_ops if total_ops > 0 else 0.0,
                "std_dev_ms": statistics.stdev(successful_durations) if len(successful_durations) > 1 else 0.0
            }
        )
    
    def get_benchmark_results(self, name: Optional[str] = None) -> Dict[str, Any]:
        """ベンチマーク結果を取得"""
        if name:
            if name in self.benchmark_results:
                return asdict(self.benchmark_results[name])
            else:
                return {"error": f"Benchmark '{name}' not found"}
        else:
            return {
                "benchmarks": {name: asdict(result) for name, result in self.benchmark_results.items()},
                "total_benchmarks": len(self.benchmark_results),
                "timestamp": datetime.now().isoformat()
            }
    
    def performance_context(self, operation: str, metadata: Optional[Dict[str, Any]] = None):
        """パフォーマンス測定コンテキストマネージャー"""
        return PerformanceContext(self, operation, metadata)
    
    def _percentile(self, sorted_data: List[float], percentile: float) -> float:
        """パーセンタイル値を計算"""
        if not sorted_data:
            return 0.0
        
        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = int(k)
        c = k - f
        
        if f + 1 < len(sorted_data):
            return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
        else:
            return sorted_data[f]
    
    def _calculate_time_range_seconds(self, metrics: List[PerformanceMetrics]) -> float:
        """メトリクスの時間範囲を秒で計算"""
        if len(metrics) < 2:
            return 0.0
        
        try:
            timestamps = [datetime.fromisoformat(m.timestamp) for m in metrics]
            time_range = max(timestamps) - min(timestamps)
            return time_range.total_seconds()
        except Exception as e:
            logger.warning(f"Failed to calculate time range: {e}")
            return 0.0
    
    def export_performance_data(self, output_path: Path, format: str = "json") -> bool:
        """パフォーマンスデータをエクスポート"""
        try:
            export_data = {
                "export_info": {
                    "timestamp": datetime.now().isoformat(),
                    "format": format,
                    "total_metrics": len(self.metrics_history),
                    "operations_count": len(self.operation_metrics)
                },
                "metrics_history": [asdict(m) for m in self.metrics_history],
                "operation_stats": {
                    name: self.get_operation_stats(name, limit=1000)
                    for name in self.operation_metrics.keys()
                },
                "benchmark_results": {
                    name: asdict(result) for name, result in self.benchmark_results.items()
                },
                "summary": self.get_all_operations_summary()
            }
            
            if format == "json":
                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            elif format == "csv":
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Operation', 'Duration_ms', 'Success', 'Timestamp', 'Memory_MB', 'CPU_Percent'])
                    
                    for metric in self.metrics_history:
                        writer.writerow([
                            metric.operation,
                            metric.duration_ms,
                            metric.success,
                            metric.timestamp,
                            metric.memory_usage_mb,
                            metric.cpu_usage_percent
                        ])
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
            
            logger.info(f"Performance data exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export performance data: {e}")
            return False


class PerformanceContext:
    """パフォーマンス測定コンテキストマネージャー"""
    
    def __init__(self, monitor: PerformanceMonitor, operation: str, metadata: Optional[Dict[str, Any]] = None):
        self.monitor = monitor
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = (time.time() - self.start_time) * 1000  # ms
            success = exc_type is None
            
            self.monitor.record_operation(
                operation=self.operation,
                duration_ms=duration,
                success=success,
                metadata=self.metadata
            )