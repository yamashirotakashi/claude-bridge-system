"""
Claude Bridge System - Async Optimizer
非同期処理最適化とコネクションプール管理
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union, AsyncGenerator
from dataclasses import dataclass, asdict
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)


class BatchStrategy(Enum):
    """バッチ処理戦略"""
    SIZE_BASED = "size_based"          # サイズベース
    TIME_BASED = "time_based"          # 時間ベース
    HYBRID = "hybrid"                  # ハイブリッド
    ADAPTIVE = "adaptive"              # 適応型


@dataclass
class BatchConfig:
    """バッチ処理設定"""
    batch_size: int = 100
    batch_timeout_ms: int = 1000
    max_concurrent_batches: int = 5
    strategy: BatchStrategy = BatchStrategy.HYBRID
    retry_attempts: int = 3
    retry_delay_ms: int = 100


@dataclass
class ConnectionPoolConfig:
    """コネクションプール設定"""
    max_connections: int = 100
    max_connections_per_host: int = 30
    keepalive_timeout: int = 30
    connection_timeout: int = 10
    read_timeout: int = 30
    enable_tcp_keepalive: bool = True
    keepalive_expiry: int = 300


class AsyncOptimizer:
    """非同期処理最適化エンジン"""
    
    def __init__(self):
        """初期化"""
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.semaphores: Dict[str, asyncio.Semaphore] = {}
        self.rate_limiters: Dict[str, Dict[str, Any]] = {}
        
        # 統計情報
        self.stats = {
            "async_tasks_executed": 0,
            "batch_operations": 0,
            "connection_pool_hits": 0,
            "rate_limit_hits": 0,
            "total_time_saved_ms": 0
        }
        
        logger.info("AsyncOptimizer initialized")
    
    async def optimize_concurrent_execution(self, 
                                          tasks: List[Callable[..., Awaitable[Any]]],
                                          max_concurrent: int = 10,
                                          timeout_seconds: Optional[float] = None) -> List[Any]:
        """並行実行を最適化"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_task(task):
            async with semaphore:
                return await task()
        
        start_time = time.time()
        
        try:
            if timeout_seconds:
                results = await asyncio.wait_for(
                    asyncio.gather(*[limited_task(task) for task in tasks], 
                                 return_exceptions=True),
                    timeout=timeout_seconds
                )
            else:
                results = await asyncio.gather(
                    *[limited_task(task) for task in tasks], 
                    return_exceptions=True
                )
            
            execution_time = (time.time() - start_time) * 1000
            self.stats["async_tasks_executed"] += len(tasks)
            self.stats["total_time_saved_ms"] += execution_time
            
            logger.info(f"Executed {len(tasks)} tasks concurrently in {execution_time:.2f}ms")
            return results
            
        except Exception as e:
            logger.error(f"Error in concurrent execution: {e}")
            raise
    
    async def optimize_with_rate_limiting(self, 
                                        task: Callable[..., Awaitable[Any]],
                                        rate_limit_key: str,
                                        calls_per_second: float,
                                        *args, **kwargs) -> Any:
        """レート制限付き実行最適化"""
        if rate_limit_key not in self.rate_limiters:
            self.rate_limiters[rate_limit_key] = {
                "last_call": 0,
                "call_interval": 1.0 / calls_per_second
            }
        
        rate_limiter = self.rate_limiters[rate_limit_key]
        current_time = time.time()
        
        # レート制限チェック
        time_since_last_call = current_time - rate_limiter["last_call"]
        if time_since_last_call < rate_limiter["call_interval"]:
            wait_time = rate_limiter["call_interval"] - time_since_last_call
            await asyncio.sleep(wait_time)
            self.stats["rate_limit_hits"] += 1
        
        rate_limiter["last_call"] = time.time()
        
        return await task(*args, **kwargs)
    
    async def optimize_cpu_bound_task(self, 
                                    func: Callable[..., Any],
                                    *args, **kwargs) -> Any:
        """CPU集約的タスクの最適化"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args, **kwargs)
    
    async def optimize_io_operations(self, 
                                   operations: List[Dict[str, Any]],
                                   max_concurrent: int = 20) -> List[Any]:
        """I/O操作の最適化"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_operation(operation):
            async with semaphore:
                op_type = operation.get("type")
                
                if op_type == "file_read":
                    return await self._optimized_file_read(operation["path"])
                elif op_type == "file_write":
                    return await self._optimized_file_write(
                        operation["path"], operation["data"]
                    )
                elif op_type == "http_request":
                    return await self._optimized_http_request(operation)
                else:
                    raise ValueError(f"Unknown operation type: {op_type}")
        
        return await asyncio.gather(
            *[execute_operation(op) for op in operations],
            return_exceptions=True
        )
    
    async def _optimized_file_read(self, file_path: str) -> str:
        """最適化されたファイル読み込み"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def _optimized_file_write(self, file_path: str, data: str) -> None:
        """最適化されたファイル書き込み"""
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(data)
    
    async def _optimized_http_request(self, request_config: Dict[str, Any]) -> Any:
        """最適化されたHTTPリクエスト"""
        # この実装は簡略化されています
        # 実際の実装では ConnectionPool を使用
        async with aiohttp.ClientSession() as session:
            method = request_config.get("method", "GET")
            url = request_config["url"]
            
            async with session.request(method, url) as response:
                return await response.json()
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """最適化統計を取得"""
        return self.stats.copy()


class BatchProcessor:
    """バッチ処理最適化システム"""
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """
        初期化
        
        Args:
            config: バッチ処理設定
        """
        self.config = config or BatchConfig()
        self.pending_items: List[Any] = []
        self.batch_handlers: Dict[str, Callable] = {}
        self.processing_semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        self.last_batch_time = time.time()
        
        # 統計情報
        self.batch_stats = {
            "total_batches_processed": 0,
            "total_items_processed": 0,
            "avg_batch_size": 0,
            "avg_processing_time_ms": 0
        }
        
        logger.info("BatchProcessor initialized")
    
    def register_batch_handler(self, 
                             batch_type: str, 
                             handler: Callable[[List[Any]], Awaitable[List[Any]]]) -> None:
        """バッチハンドラーを登録"""
        self.batch_handlers[batch_type] = handler
        logger.info(f"Batch handler registered: {batch_type}")
    
    async def add_item(self, item: Any, batch_type: str = "default") -> None:
        """アイテムをバッチに追加"""
        self.pending_items.append({"item": item, "batch_type": batch_type, "added_at": time.time()})
        
        # バッチ処理条件をチェック
        await self._check_batch_conditions()
    
    async def _check_batch_conditions(self) -> None:
        """バッチ処理条件をチェック"""
        current_time = time.time()
        
        should_process = False
        
        if self.config.strategy == BatchStrategy.SIZE_BASED:
            should_process = len(self.pending_items) >= self.config.batch_size
        
        elif self.config.strategy == BatchStrategy.TIME_BASED:
            time_since_last_batch = (current_time - self.last_batch_time) * 1000
            should_process = time_since_last_batch >= self.config.batch_timeout_ms
        
        elif self.config.strategy == BatchStrategy.HYBRID:
            size_condition = len(self.pending_items) >= self.config.batch_size
            time_condition = (current_time - self.last_batch_time) * 1000 >= self.config.batch_timeout_ms
            should_process = size_condition or (time_condition and self.pending_items)
        
        elif self.config.strategy == BatchStrategy.ADAPTIVE:
            # 適応的バッチサイズ（簡略化実装）
            adaptive_size = min(self.config.batch_size, len(self.pending_items))
            should_process = len(self.pending_items) >= adaptive_size
        
        if should_process:
            await self._process_pending_batches()
    
    async def _process_pending_batches(self) -> None:
        """保留中のバッチを処理"""
        if not self.pending_items:
            return
        
        async with self.processing_semaphore:
            # バッチタイプ別にグループ化
            batches_by_type = {}
            for item_data in self.pending_items:
                batch_type = item_data["batch_type"]
                if batch_type not in batches_by_type:
                    batches_by_type[batch_type] = []
                batches_by_type[batch_type].append(item_data["item"])
            
            self.pending_items.clear()
            self.last_batch_time = time.time()
            
            # 各バッチタイプを処理
            processing_tasks = []
            for batch_type, items in batches_by_type.items():
                if batch_type in self.batch_handlers:
                    task = self._process_batch(batch_type, items)
                    processing_tasks.append(task)
            
            if processing_tasks:
                await asyncio.gather(*processing_tasks, return_exceptions=True)
    
    async def _process_batch(self, batch_type: str, items: List[Any]) -> None:
        """バッチを処理"""
        start_time = time.time()
        
        try:
            handler = self.batch_handlers[batch_type]
            results = await handler(items)
            
            processing_time = (time.time() - start_time) * 1000
            
            # 統計更新
            self.batch_stats["total_batches_processed"] += 1
            self.batch_stats["total_items_processed"] += len(items)
            
            total_items = self.batch_stats["total_items_processed"]
            total_batches = self.batch_stats["total_batches_processed"]
            self.batch_stats["avg_batch_size"] = total_items / total_batches
            
            # 平均処理時間更新
            current_avg = self.batch_stats["avg_processing_time_ms"]
            self.batch_stats["avg_processing_time_ms"] = (
                (current_avg * (total_batches - 1) + processing_time) / total_batches
            )
            
            logger.info(f"Processed batch {batch_type}: {len(items)} items in {processing_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error processing batch {batch_type}: {e}")
    
    async def flush_pending(self) -> None:
        """保留中のアイテムを強制処理"""
        await self._process_pending_batches()
    
    def get_batch_statistics(self) -> Dict[str, Any]:
        """バッチ処理統計を取得"""
        stats = self.batch_stats.copy()
        stats["pending_items"] = len(self.pending_items)
        stats["registered_handlers"] = list(self.batch_handlers.keys())
        return stats


class ConnectionPool:
    """コネクションプール管理"""
    
    def __init__(self, config: Optional[ConnectionPoolConfig] = None):
        """
        初期化
        
        Args:
            config: コネクションプール設定
        """
        self.config = config or ConnectionPoolConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 統計情報
        self.pool_stats = {
            "total_requests": 0,
            "active_connections": 0,
            "pool_hits": 0,
            "pool_misses": 0,
            "connection_errors": 0
        }
        
        logger.info("ConnectionPool initialized")
    
    async def __aenter__(self):
        """非同期コンテキストマネージャー開始"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー終了"""
        await self.close()
    
    async def start(self) -> None:
        """コネクションプールを開始"""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.max_connections_per_host,
                keepalive_timeout=self.config.keepalive_timeout,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.config.connection_timeout + self.config.read_timeout,
                connect=self.config.connection_timeout,
                sock_read=self.config.read_timeout
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
            
            logger.info("Connection pool started")
    
    async def close(self) -> None:
        """コネクションプールを閉じる"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Connection pool closed")
    
    async def request(self, 
                     method: str, 
                     url: str, 
                     **kwargs) -> aiohttp.ClientResponse:
        """最適化されたHTTPリクエスト"""
        if not self.session:
            await self.start()
        
        try:
            self.pool_stats["total_requests"] += 1
            response = await self.session.request(method, url, **kwargs)
            self.pool_stats["pool_hits"] += 1
            return response
            
        except Exception as e:
            self.pool_stats["connection_errors"] += 1
            logger.error(f"Connection pool request error: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[aiohttp.ClientSession, None]:
        """セッションを取得"""
        if not self.session:
            await self.start()
        
        try:
            yield self.session
        finally:
            pass  # セッションは自動的に管理される
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """プール統計を取得"""
        stats = self.pool_stats.copy()
        
        if self.session and self.session.connector:
            connector = self.session.connector
            stats["active_connections"] = len(connector._conns)
            stats["acquired_connections"] = len(connector._acquired)
        
        return stats


# グローバルインスタンス
global_async_optimizer = AsyncOptimizer()
global_batch_processor = BatchProcessor()
global_connection_pool = ConnectionPool()