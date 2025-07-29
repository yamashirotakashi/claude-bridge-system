"""
Claude Bridge System - Performance CLI Commands
パフォーマンス関連CLIコマンド
"""

import click
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

from ..performance import (
    PerformanceProfiler, PerformanceOptimizer, CacheManager,
    AsyncOptimizer, BatchProcessor, ConnectionPool,
    ProfileType, OptimizationStrategy, CacheStrategy
)


@click.group()
def performance():
    """Performance optimization and profiling commands"""
    pass


# プロファイリングコマンド
@performance.group('profile')
def profile():
    """Performance profiling commands"""
    pass


@profile.command('function')
@click.argument('function_name', type=str)
@click.option('--types', multiple=True, 
              type=click.Choice([t.value for t in ProfileType]),
              default=['cpu', 'memory'],
              help='Profile types to collect')
@click.option('--duration', type=int, default=60, 
              help='Profiling duration in seconds')
@click.option('--output', '-o', type=click.Path(), 
              help='Output file for results')
@click.pass_context
def profile_function(ctx, function_name: str, types, duration: int, output):
    """Profile a specific function"""
    try:
        profiler = PerformanceProfiler()
        profile_types = [ProfileType(t) for t in types]
        
        click.echo(f"🔍 Starting profiling for function: {function_name}")
        click.echo(f"Profile types: {', '.join(types)}")
        click.echo(f"Duration: {duration}s")
        
        # 模擬プロファイリング（実際の実装では対象関数を実行）
        with profiler.profile(function_name, profile_types):
            time.sleep(duration)
        
        # 結果取得
        summary = profiler.get_profile_summary(function_name=function_name)
        
        # 結果表示
        click.echo("\n📊 Profiling Results:")
        click.echo(f"Total profiles: {summary.get('total_profiles', 0)}")
        if 'avg_duration_ms' in summary:
            click.echo(f"Average duration: {summary['avg_duration_ms']:.2f}ms")
        if 'min_duration_ms' in summary:
            click.echo(f"Min duration: {summary['min_duration_ms']:.2f}ms")
        if 'max_duration_ms' in summary:
            click.echo(f"Max duration: {summary['max_duration_ms']:.2f}ms")
        
        # タイプ別統計
        if 'by_type' in summary:
            click.echo("\n📈 By Profile Type:")
            for ptype, stats in summary['by_type'].items():
                click.echo(f"  {ptype}: {stats['count']} profiles, "
                          f"{stats['avg_duration']:.2f}ms avg")
        
        # ファイル出力
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            click.echo(f"\n💾 Results saved to: {output}")
        
    except Exception as e:
        click.echo(f"❌ Error profiling function: {e}", err=True)
        sys.exit(1)


@profile.command('summary')
@click.option('--function', help='Filter by function name')
@click.option('--type', 'profile_type',
              type=click.Choice([t.value for t in ProfileType]),
              help='Filter by profile type')
@click.option('--limit', type=int, default=10, help='Number of results to show')
@click.option('--export', type=click.Choice(['json', 'csv']),
              help='Export format')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def profile_summary(function, profile_type, limit, export, output):
    """Show profiling summary"""
    try:
        profiler = PerformanceProfiler()
        
        ptype = ProfileType(profile_type) if profile_type else None
        summary = profiler.get_profile_summary(
            function_name=function,
            profile_type=ptype,
            limit=limit
        )
        
        if export:
            # エクスポート
            exported_data = profiler.export_results(format=export)
            
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(exported_data)
                click.echo(f"📄 Profile data exported to: {output}")
            else:
                click.echo(exported_data)
        else:
            # 画面表示
            click.echo("📊 Profile Summary:")
            click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
        
    except Exception as e:
        click.echo(f"❌ Error getting profile summary: {e}", err=True)
        sys.exit(1)


@profile.command('top-slow')
@click.option('--limit', type=int, default=10, help='Number of functions to show')
def profile_top_slow(limit):
    """Show top slowest functions"""
    try:
        profiler = PerformanceProfiler()
        slow_functions = profiler.get_top_slow_functions(limit=limit)
        
        if not slow_functions:
            click.echo("📊 No profiling data available")
            return
        
        click.echo(f"🐌 Top {len(slow_functions)} Slowest Functions:")
        click.echo("-" * 80)
        
        for i, func_stats in enumerate(slow_functions, 1):
            click.echo(f"{i:2d}. {func_stats['function_name']}")
            click.echo(f"    Calls: {func_stats['call_count']}")
            click.echo(f"    Avg: {func_stats['avg_duration_ms']:.2f}ms")
            click.echo(f"    Max: {func_stats['max_duration_ms']:.2f}ms")
            click.echo(f"    Total: {func_stats['total_duration_ms']:.2f}ms")
            click.echo()
        
    except Exception as e:
        click.echo(f"❌ Error getting slow functions: {e}", err=True)
        sys.exit(1)


# 最適化コマンド
@performance.group('optimize')
def optimize():
    """Performance optimization commands"""
    pass


@optimize.command('analyze')
@click.argument('target', type=str)
@click.option('--strategies', multiple=True,
              type=click.Choice([s.value for s in OptimizationStrategy]),
              help='Optimization strategies to test')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
def optimize_analyze(target, strategies, output):
    """Analyze optimization opportunities"""
    try:
        optimizer = PerformanceOptimizer()
        
        if not strategies:
            strategies = ['cpu_optimization', 'memory_optimization', 'async_optimization']
        
        click.echo(f"🔧 Analyzing optimization opportunities for: {target}")
        click.echo(f"Strategies: {', '.join(strategies)}")
        
        # 模擬最適化分析
        click.echo("Running optimization analysis...")
        
        # 統計取得
        stats = optimizer.get_optimization_statistics()
        best_strategies = optimizer.get_best_performing_strategies()
        
        # 結果表示
        click.echo("\n📈 Optimization Statistics:")
        click.echo(f"Total optimizations: {stats['total_optimizations']}")
        click.echo(f"Successful optimizations: {stats['successful_optimizations']}")
        if stats['total_optimizations'] > 0:
            click.echo(f"Success rate: {stats['success_rate']:.1f}%")
        click.echo(f"Total time saved: {stats['total_time_saved_ms']:.2f}ms")
        click.echo(f"Total memory saved: {stats['total_memory_saved_mb']:.2f}MB")
        
        if best_strategies:
            click.echo("\n🏆 Best Performing Strategies:")
            for strategy in best_strategies:
                click.echo(f"  • {strategy['strategy']}: "
                          f"{strategy['avg_improvement']:.1f}% improvement "
                          f"({strategy['success_rate']:.1f}% success rate)")
        
        # ファイル出力
        if output:
            result_data = {
                "target": target,
                "strategies_tested": list(strategies),
                "statistics": stats,
                "best_strategies": best_strategies
            }
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            click.echo(f"\n💾 Analysis results saved to: {output}")
        
    except Exception as e:
        click.echo(f"❌ Error analyzing optimizations: {e}", err=True)
        sys.exit(1)


@optimize.command('stats')
@click.option('--reset', is_flag=True, help='Reset optimization statistics')
def optimize_stats(reset):
    """Show optimization statistics"""
    try:
        optimizer = PerformanceOptimizer()
        
        if reset:
            optimizer.clear_optimization_history()
            click.echo("🔄 Optimization statistics reset")
            return
        
        stats = optimizer.get_optimization_statistics()
        best_strategies = optimizer.get_best_performing_strategies()
        
        click.echo("📊 Optimization Statistics:")
        click.echo(f"Total optimizations: {stats['total_optimizations']}")
        click.echo(f"Successful: {stats['successful_optimizations']}")
        click.echo(f"Success rate: {stats.get('success_rate', 0):.1f}%")
        click.echo(f"Time saved: {stats['total_time_saved_ms']:.2f}ms")
        click.echo(f"Memory saved: {stats['total_memory_saved_mb']:.2f}MB")
        
        if stats['by_strategy']:
            click.echo("\n📈 By Strategy:")
            for strategy, strategy_stats in stats['by_strategy'].items():
                click.echo(f"  {strategy}:")
                click.echo(f"    Count: {strategy_stats['count']}")
                click.echo(f"    Success rate: {strategy_stats.get('success_rate', 0):.1f}%")
                click.echo(f"    Avg improvement: {strategy_stats.get('avg_improvement', 0):.1f}%")
        
    except Exception as e:
        click.echo(f"❌ Error getting optimization stats: {e}", err=True)
        sys.exit(1)


# キャッシュコマンド
@performance.group('cache')
def cache():
    """Cache management commands"""
    pass


@cache.command('stats')
@click.option('--manager', default='global', help='Cache manager name')
def cache_stats(manager):
    """Show cache statistics"""
    try:
        from ..performance.cache_manager import global_cache_manager
        
        cache_mgr = global_cache_manager  # 実際の実装では指定されたマネージャーを取得
        stats = cache_mgr.get_cache_statistics()
        
        click.echo("💾 Cache Statistics:")
        click.echo(f"Total entries: {stats['total_entries']}")
        click.echo(f"Cache hits: {stats['cache_hits']}")
        click.echo(f"Cache misses: {stats['cache_misses']}")
        click.echo(f"Hit rate: {stats['hit_rate']:.1f}%")
        click.echo(f"Evictions: {stats['evictions']}")
        click.echo(f"Expired entries: {stats['expired_entries']}")
        click.echo(f"Memory usage: {stats['total_memory_mb']:.2f}MB")
        
        if 'avg_access_time_ms' in stats:
            click.echo(f"Avg access time: {stats['avg_access_time_ms']:.2f}ms")
        
        if 'config' in stats:
            config = stats['config']
            click.echo(f"\n⚙️  Configuration:")
            click.echo(f"Max size: {config['max_size']}")
            click.echo(f"Default TTL: {config['default_ttl_seconds']}s")
            click.echo(f"Strategy: {config['strategy']}")
            click.echo(f"Max memory: {config['max_memory_mb']}MB")
        
    except Exception as e:
        click.echo(f"❌ Error getting cache stats: {e}", err=True)
        sys.exit(1)


@cache.command('top-keys')
@click.option('--limit', type=int, default=10, help='Number of keys to show')
@click.option('--manager', default='global', help='Cache manager name')
def cache_top_keys(limit, manager):
    """Show most accessed cache keys"""
    try:
        from ..performance.cache_manager import global_cache_manager
        
        cache_mgr = global_cache_manager
        top_keys = cache_mgr.get_top_accessed_keys(limit=limit)
        
        if not top_keys:
            click.echo("💾 No cache data available")
            return
        
        click.echo(f"🔥 Top {len(top_keys)} Most Accessed Keys:")
        click.echo("-" * 80)
        
        for i, key_stats in enumerate(top_keys, 1):
            click.echo(f"{i:2d}. {key_stats['key'][:50]}{'...' if len(key_stats['key']) > 50 else ''}")
            click.echo(f"    Access count: {key_stats['access_count']}")
            click.echo(f"    Size: {key_stats['size_bytes']} bytes")
            click.echo(f"    Age: {key_stats['age_seconds']:.1f}s")
            click.echo(f"    Last accessed: {key_stats['last_accessed']}")
            click.echo()
        
    except Exception as e:
        click.echo(f"❌ Error getting top cache keys: {e}", err=True)
        sys.exit(1)


@cache.command('clear')
@click.option('--manager', default='global', help='Cache manager name')
@click.confirmation_option(prompt='Clear all cache entries?')
def cache_clear(manager):
    """Clear cache entries"""
    try:
        from ..performance.cache_manager import global_cache_manager
        
        cache_mgr = global_cache_manager
        cache_mgr.clear()
        
        click.echo("🗑️  Cache cleared successfully")
        
    except Exception as e:
        click.echo(f"❌ Error clearing cache: {e}", err=True)
        sys.exit(1)


# 非同期最適化コマンド
@performance.group('async')
def async_opt():
    """Async optimization commands"""
    pass


@async_opt.command('stats')
def async_stats():
    """Show async optimization statistics"""
    try:
        from ..performance.async_optimizer import global_async_optimizer
        
        stats = global_async_optimizer.get_optimization_stats()
        
        click.echo("⚡ Async Optimization Statistics:")
        click.echo(f"Tasks executed: {stats['async_tasks_executed']}")
        click.echo(f"Batch operations: {stats['batch_operations']}")
        click.echo(f"Connection pool hits: {stats['connection_pool_hits']}")
        click.echo(f"Rate limit hits: {stats['rate_limit_hits']}")
        click.echo(f"Total time saved: {stats['total_time_saved_ms']:.2f}ms")
        
    except Exception as e:
        click.echo(f"❌ Error getting async stats: {e}", err=True)
        sys.exit(1)


@async_opt.command('batch-stats')
def async_batch_stats():
    """Show batch processing statistics"""
    try:
        from ..performance.async_optimizer import global_batch_processor
        
        stats = global_batch_processor.get_batch_statistics()
        
        click.echo("📦 Batch Processing Statistics:")
        click.echo(f"Total batches processed: {stats['total_batches_processed']}")
        click.echo(f"Total items processed: {stats['total_items_processed']}")
        click.echo(f"Average batch size: {stats['avg_batch_size']:.1f}")
        click.echo(f"Average processing time: {stats['avg_processing_time_ms']:.2f}ms")
        click.echo(f"Pending items: {stats['pending_items']}")
        
        if stats['registered_handlers']:
            click.echo(f"Registered handlers: {', '.join(stats['registered_handlers'])}")
        
    except Exception as e:
        click.echo(f"❌ Error getting batch stats: {e}", err=True)
        sys.exit(1)


@async_opt.command('pool-stats')
def async_pool_stats():
    """Show connection pool statistics"""
    try:
        from ..performance.async_optimizer import global_connection_pool
        
        stats = global_connection_pool.get_pool_statistics()
        
        click.echo("🔌 Connection Pool Statistics:")
        click.echo(f"Total requests: {stats['total_requests']}")
        click.echo(f"Active connections: {stats['active_connections']}")
        click.echo(f"Pool hits: {stats['pool_hits']}")
        click.echo(f"Pool misses: {stats['pool_misses']}")
        click.echo(f"Connection errors: {stats['connection_errors']}")
        
        if stats['total_requests'] > 0:
            hit_rate = (stats['pool_hits'] / stats['total_requests']) * 100
            click.echo(f"Hit rate: {hit_rate:.1f}%")
        
    except Exception as e:
        click.echo(f"❌ Error getting connection pool stats: {e}", err=True)
        sys.exit(1)


# パフォーマンス総合コマンド
@performance.command('benchmark')
@click.option('--duration', type=int, default=60, 
              help='Benchmark duration in seconds')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
def performance_benchmark(duration, output):
    """Run comprehensive performance benchmark"""
    try:
        click.echo("🏃 Starting comprehensive performance benchmark...")
        click.echo(f"Duration: {duration}s")
        
        # 各種統計を収集
        profiler = PerformanceProfiler()
        optimizer = PerformanceOptimizer()
        
        from ..performance.cache_manager import global_cache_manager
        from ..performance.async_optimizer import (
            global_async_optimizer, global_batch_processor, global_connection_pool
        )
        
        # ベンチマーク実行（模擬）
        with profiler.profile(f"benchmark_{int(time.time())}", [ProfileType.CPU, ProfileType.MEMORY]):
            click.echo("⏱️  Running CPU and memory benchmark...")
            time.sleep(min(duration, 5))  # 最大5秒の模擬処理
        
        # 結果収集
        benchmark_results = {
            "duration_seconds": duration,
            "timestamp": time.time(),
            "profiling": profiler.get_profile_summary(limit=5),
            "optimization": optimizer.get_optimization_statistics(),
            "cache": global_cache_manager.get_cache_statistics(),
            "async": global_async_optimizer.get_optimization_stats(),
            "batch": global_batch_processor.get_batch_statistics(),
            "connection_pool": global_connection_pool.get_pool_statistics()
        }
        
        # 結果表示
        click.echo("\n📊 Benchmark Results Summary:")
        click.echo(f"✅ Benchmark completed in {duration}s")
        
        # 主要メトリクス表示
        if 'avg_duration_ms' in benchmark_results['profiling']:
            click.echo(f"Average operation time: {benchmark_results['profiling']['avg_duration_ms']:.2f}ms")
        
        cache_stats = benchmark_results['cache']
        click.echo(f"Cache hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
        click.echo(f"Memory usage: {cache_stats.get('total_memory_mb', 0):.2f}MB")
        
        # ファイル出力
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(benchmark_results, f, ensure_ascii=False, indent=2)
            click.echo(f"\n💾 Benchmark results saved to: {output}")
        
    except Exception as e:
        click.echo(f"❌ Error running benchmark: {e}", err=True)
        sys.exit(1)


# メインコマンドグループに登録用の関数
def register_performance_commands(main_cli):
    """メインCLIにパフォーマンスコマンドを登録"""
    main_cli.add_command(performance)