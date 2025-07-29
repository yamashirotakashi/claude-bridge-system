"""
Claude Bridge System - Performance Profiler
パフォーマンスプロファイリングとベンチマーク機能
"""

import asyncio
import cProfile
import functools
import io
import logging
import pstats
import time
import threading
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, AsyncGenerator
from dataclasses import dataclass, asdict
import psutil

logger = logging.getLogger(__name__)


class ProfileType(Enum):
    """プロファイルタイプ"""
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    FUNCTION = "function"
    ASYNC = "async"


@dataclass
class ProfileConfig:
    """プロファイル設定"""
    profile_types: List[ProfileType] = None
    sample_interval: float = 0.1
    max_samples: int = 1000
    include_stdlib: bool = False
    sort_by: str = "cumulative"
    top_functions: int = 20
    memory_threshold_mb: float = 100.0
    
    def __post_init__(self):
        if self.profile_types is None:
            self.profile_types = [ProfileType.CPU, ProfileType.MEMORY]


@dataclass
class ProfileResult:
    """プロファイル結果"""
    profile_type: ProfileType
    start_time: str
    end_time: str
    duration_ms: float
    function_name: Optional[str] = None
    cpu_stats: Optional[Dict[str, Any]] = None
    memory_stats: Optional[Dict[str, Any]] = None
    io_stats: Optional[Dict[str, Any]] = None
    network_stats: Optional[Dict[str, Any]] = None
    function_stats: Optional[Dict[str, Any]] = None
    call_graph: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


class PerformanceProfiler:
    """パフォーマンスプロファイラー"""
    
    def __init__(self, config: Optional[ProfileConfig] = None):
        """
        初期化
        
        Args:
            config: プロファイル設定
        """
        self.config = config or ProfileConfig()
        self.active_profiles: Dict[str, Dict[str, Any]] = {}
        self.profile_results: List[ProfileResult] = []
        self.max_results = 1000
        
        # システム情報取得用
        self.process = psutil.Process()
        
        # スレッドローカルストレージ
        self.local = threading.local()
        
        logger.info("PerformanceProfiler initialized")
    
    @contextmanager
    def profile(self, 
                name: str,
                profile_types: Optional[List[ProfileType]] = None):
        """プロファイリングコンテキストマネージャー"""
        types = profile_types or self.config.profile_types
        profile_id = f"{name}_{int(time.time() * 1000000)}"
        
        # プロファイリング開始
        start_data = self._start_profiling(profile_id, name, types)
        
        try:
            yield profile_id
        finally:
            # プロファイリング終了
            self._end_profiling(profile_id, start_data)
    
    def profile_function(self, 
                        name: Optional[str] = None,
                        profile_types: Optional[List[ProfileType]] = None):
        """関数プロファイリングデコレーター"""
        def decorator(func):
            func_name = name or f"{func.__module__}.{func.__name__}"
            types = profile_types or self.config.profile_types
            
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    with self.profile(func_name, types):
                        return await func(*args, **kwargs)
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    with self.profile(func_name, types):
                        return func(*args, **kwargs)
                return sync_wrapper
        
        return decorator
    
    def _start_profiling(self, 
                        profile_id: str, 
                        name: str, 
                        profile_types: List[ProfileType]) -> Dict[str, Any]:
        """プロファイリング開始"""
        start_time = time.time()
        start_data = {
            "profile_id": profile_id,
            "name": name,
            "start_time": start_time,
            "profile_types": profile_types,
            "profilers": {}
        }
        
        # CPU プロファイリング
        if ProfileType.CPU in profile_types:
            cpu_profiler = cProfile.Profile()
            cpu_profiler.enable()
            start_data["profilers"]["cpu"] = cpu_profiler
        
        # メモリプロファイリング
        if ProfileType.MEMORY in profile_types:
            memory_info = self.process.memory_info()
            start_data["profilers"]["memory"] = {
                "start_rss": memory_info.rss,
                "start_vms": memory_info.vms
            }
        
        # I/O プロファイリング
        if ProfileType.IO in profile_types:
            io_counters = self.process.io_counters()
            start_data["profilers"]["io"] = {
                "start_read_bytes": io_counters.read_bytes,
                "start_write_bytes": io_counters.write_bytes,
                "start_read_count": io_counters.read_count,
                "start_write_count": io_counters.write_count
            }
        
        # ネットワークプロファイリング
        if ProfileType.NETWORK in profile_types:
            net_io = psutil.net_io_counters()
            if net_io:
                start_data["profilers"]["network"] = {
                    "start_bytes_sent": net_io.bytes_sent,
                    "start_bytes_recv": net_io.bytes_recv,
                    "start_packets_sent": net_io.packets_sent,
                    "start_packets_recv": net_io.packets_recv
                }
        
        self.active_profiles[profile_id] = start_data
        return start_data
    
    def _end_profiling(self, profile_id: str, start_data: Dict[str, Any]) -> None:
        """プロファイリング終了"""
        if profile_id not in self.active_profiles:
            logger.warning(f"Profile not found: {profile_id}")
            return
        
        end_time = time.time()
        duration_ms = (end_time - start_data["start_time"]) * 1000
        
        results = []
        
        # CPU プロファイリング結果
        if "cpu" in start_data["profilers"]:
            cpu_profiler = start_data["profilers"]["cpu"]
            cpu_profiler.disable()
            
            # 統計を文字列に変換
            stats_stream = io.StringIO()
            stats = pstats.Stats(cpu_profiler, stream=stats_stream)
            stats.sort_stats(self.config.sort_by)
            stats.print_stats(self.config.top_functions)
            
            cpu_stats = {
                "total_calls": stats.total_calls,
                "primitive_calls": stats.prim_calls,
                "total_time": stats.total_tt,
                "stats_output": stats_stream.getvalue()
            }
            
            results.append(ProfileResult(
                profile_type=ProfileType.CPU,
                start_time=datetime.fromtimestamp(start_data["start_time"]).isoformat(),
                end_time=datetime.fromtimestamp(end_time).isoformat(),
                duration_ms=duration_ms,
                function_name=start_data["name"],
                cpu_stats=cpu_stats
            ))
        
        # メモリプロファイリング結果
        if "memory" in start_data["profilers"]:
            start_memory = start_data["profilers"]["memory"]
            end_memory_info = self.process.memory_info()
            
            memory_stats = {
                "start_rss_mb": start_memory["start_rss"] / (1024 * 1024),
                "end_rss_mb": end_memory_info.rss / (1024 * 1024),
                "rss_diff_mb": (end_memory_info.rss - start_memory["start_rss"]) / (1024 * 1024),
                "start_vms_mb": start_memory["start_vms"] / (1024 * 1024),
                "end_vms_mb": end_memory_info.vms / (1024 * 1024),
                "vms_diff_mb": (end_memory_info.vms - start_memory["start_vms"]) / (1024 * 1024),
                "memory_percent": self.process.memory_percent()
            }
            
            results.append(ProfileResult(
                profile_type=ProfileType.MEMORY,
                start_time=datetime.fromtimestamp(start_data["start_time"]).isoformat(),
                end_time=datetime.fromtimestamp(end_time).isoformat(),
                duration_ms=duration_ms,
                function_name=start_data["name"],
                memory_stats=memory_stats
            ))
        
        # I/O プロファイリング結果
        if "io" in start_data["profilers"]:
            start_io = start_data["profilers"]["io"]
            end_io_counters = self.process.io_counters()
            
            io_stats = {
                "read_bytes": end_io_counters.read_bytes - start_io["start_read_bytes"],
                "write_bytes": end_io_counters.write_bytes - start_io["start_write_bytes"],
                "read_count": end_io_counters.read_count - start_io["start_read_count"],
                "write_count": end_io_counters.write_count - start_io["start_write_count"],
                "read_bytes_per_sec": (end_io_counters.read_bytes - start_io["start_read_bytes"]) / (duration_ms / 1000),
                "write_bytes_per_sec": (end_io_counters.write_bytes - start_io["start_write_bytes"]) / (duration_ms / 1000)
            }
            
            results.append(ProfileResult(
                profile_type=ProfileType.IO,
                start_time=datetime.fromtimestamp(start_data["start_time"]).isoformat(),
                end_time=datetime.fromtimestamp(end_time).isoformat(),
                duration_ms=duration_ms,
                function_name=start_data["name"],
                io_stats=io_stats
            ))
        
        # ネットワークプロファイリング結果
        if "network" in start_data["profilers"]:
            start_net = start_data["profilers"]["network"]
            end_net_io = psutil.net_io_counters()
            
            if end_net_io:
                network_stats = {
                    "bytes_sent": end_net_io.bytes_sent - start_net["start_bytes_sent"],
                    "bytes_recv": end_net_io.bytes_recv - start_net["start_bytes_recv"],
                    "packets_sent": end_net_io.packets_sent - start_net["start_packets_sent"],
                    "packets_recv": end_net_io.packets_recv - start_net["start_packets_recv"],
                    "send_rate_bps": (end_net_io.bytes_sent - start_net["start_bytes_sent"]) / (duration_ms / 1000),
                    "recv_rate_bps": (end_net_io.bytes_recv - start_net["start_bytes_recv"]) / (duration_ms / 1000)
                }
                
                results.append(ProfileResult(
                    profile_type=ProfileType.NETWORK,
                    start_time=datetime.fromtimestamp(start_data["start_time"]).isoformat(),
                    end_time=datetime.fromtimestamp(end_time).isoformat(),
                    duration_ms=duration_ms,
                    function_name=start_data["name"],
                    network_stats=network_stats
                ))
        
        # 結果を保存
        self.profile_results.extend(results)
        
        # 結果数を制限
        if len(self.profile_results) > self.max_results:
            self.profile_results = self.profile_results[-self.max_results:]
        
        # アクティブプロファイルから削除
        del self.active_profiles[profile_id]
        
        logger.info(f"Profiling completed: {start_data['name']} ({duration_ms:.2f}ms)")
    
    def get_profile_summary(self, 
                           function_name: Optional[str] = None,
                           profile_type: Optional[ProfileType] = None,
                           limit: int = 10) -> Dict[str, Any]:
        """プロファイル結果サマリーを取得"""
        filtered_results = self.profile_results
        
        if function_name:
            filtered_results = [r for r in filtered_results if r.function_name == function_name]
        
        if profile_type:
            filtered_results = [r for r in filtered_results if r.profile_type == profile_type]
        
        # 最新の結果を取得
        recent_results = sorted(
            filtered_results,
            key=lambda x: x.start_time,
            reverse=True
        )[:limit]
        
        if not recent_results:
            return {"message": "No profile results found"}
        
        # 統計を計算
        durations = [r.duration_ms for r in recent_results]
        
        summary = {
            "total_profiles": len(recent_results),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "recent_results": [r.to_dict() for r in recent_results[:5]]
        }
        
        # タイプ別統計
        type_stats = {}
        for result in recent_results:
            ptype = result.profile_type.value
            if ptype not in type_stats:
                type_stats[ptype] = {"count": 0, "avg_duration": 0, "total_duration": 0}
            
            type_stats[ptype]["count"] += 1
            type_stats[ptype]["total_duration"] += result.duration_ms
            type_stats[ptype]["avg_duration"] = (
                type_stats[ptype]["total_duration"] / type_stats[ptype]["count"]
            )
        
        summary["by_type"] = type_stats
        
        return summary
    
    def get_top_slow_functions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """最も遅い関数を取得"""
        function_stats = {}
        
        for result in self.profile_results:
            if result.function_name:
                fname = result.function_name
                if fname not in function_stats:
                    function_stats[fname] = {
                        "function_name": fname,
                        "call_count": 0,
                        "total_duration_ms": 0,
                        "avg_duration_ms": 0,
                        "max_duration_ms": 0,
                        "min_duration_ms": float('inf')
                    }
                
                stats = function_stats[fname]
                stats["call_count"] += 1
                stats["total_duration_ms"] += result.duration_ms
                stats["max_duration_ms"] = max(stats["max_duration_ms"], result.duration_ms)
                stats["min_duration_ms"] = min(stats["min_duration_ms"], result.duration_ms)
                stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["call_count"]
        
        # 平均実行時間でソート
        sorted_functions = sorted(
            function_stats.values(),
            key=lambda x: x["avg_duration_ms"],
            reverse=True
        )
        
        return sorted_functions[:limit]
    
    def clear_results(self) -> None:
        """プロファイル結果をクリア"""
        self.profile_results.clear()
        logger.info("Profile results cleared")
    
    def export_results(self, format: str = "json") -> str:
        """プロファイル結果をエクスポート"""
        if format == "json":
            import json
            return json.dumps(
                [r.to_dict() for r in self.profile_results],
                ensure_ascii=False,
                indent=2
            )
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if self.profile_results:
                fieldnames = list(self.profile_results[0].to_dict().keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for result in self.profile_results:
                    writer.writerow(result.to_dict())
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


class ProfiledFunction:
    """プロファイル対象関数ラッパー"""
    
    def __init__(self, 
                 func: Callable,
                 profiler: PerformanceProfiler,
                 name: Optional[str] = None,
                 profile_types: Optional[List[ProfileType]] = None):
        self.func = func
        self.profiler = profiler
        self.name = name or f"{func.__module__}.{func.__name__}"
        self.profile_types = profile_types
        
        functools.update_wrapper(self, func)
    
    def __call__(self, *args, **kwargs):
        with self.profiler.profile(self.name, self.profile_types):
            return self.func(*args, **kwargs)
    
    async def __call_async__(self, *args, **kwargs):
        with self.profiler.profile(self.name, self.profile_types):
            return await self.func(*args, **kwargs)


# グローバルプロファイラーインスタンス
global_profiler = PerformanceProfiler()


def profile(name: Optional[str] = None,
           profile_types: Optional[List[ProfileType]] = None):
    """グローバルプロファイラーを使用したデコレーター"""
    return global_profiler.profile_function(name, profile_types)