"""
Claude Bridge System - Cache Manager
キャッシュ管理とパフォーマンス最適化
"""

import asyncio
import hashlib
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, asdict
import pickle

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """キャッシュ戦略"""
    LRU = "lru"                # Least Recently Used
    LFU = "lfu"                # Least Frequently Used
    FIFO = "fifo"              # First In First Out
    TTL = "ttl"                # Time To Live
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    WRITE_AROUND = "write_around"


@dataclass
class CacheConfig:
    """キャッシュ設定"""
    max_size: int = 1000
    default_ttl_seconds: int = 3600
    strategy: CacheStrategy = CacheStrategy.LRU
    enable_persistence: bool = False
    persistence_file: Optional[str] = None
    compression_enabled: bool = False
    max_memory_mb: int = 100
    cleanup_interval_seconds: int = 300
    
    def __post_init__(self):
        if self.enable_persistence and not self.persistence_file:
            self.persistence_file = "claude_bridge_cache.pkl"


@dataclass
class CacheEntry:
    """キャッシュエントリ"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl_seconds: Optional[int]
    size_bytes: int
    
    def is_expired(self) -> bool:
        """有効期限切れかチェック"""
        if self.ttl_seconds is None:
            return False
        return time.time() > (self.created_at + self.ttl_seconds)
    
    def touch(self) -> None:
        """アクセス情報を更新"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """キャッシュ統計"""
    total_entries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    expired_entries: int = 0
    total_memory_mb: float = 0
    avg_access_time_ms: float = 0
    
    @property
    def hit_rate(self) -> float:
        """ヒット率を計算"""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests == 0:
            return 0.0
        return (self.cache_hits / total_requests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = asdict(self)
        result["hit_rate"] = self.hit_rate
        return result


class CacheManager:
    """キャッシュ管理システム"""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        初期化
        
        Args:
            config: キャッシュ設定
        """
        self.config = config or CacheConfig()
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()
        
        # スレッドセーフティ
        self._lock = threading.RLock()
        
        # クリーンアップタスク
        self._cleanup_task = None
        self._running = False
        
        # 永続化設定
        if self.config.enable_persistence:
            self._load_from_persistence()
        
        logger.info(f"CacheManager initialized with strategy: {self.config.strategy.value}")
    
    def start(self) -> None:
        """キャッシュマネージャーを開始"""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("CacheManager started")
    
    async def stop(self) -> None:
        """キャッシュマネージャーを停止"""
        if self._running:
            self._running = False
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            if self.config.enable_persistence:
                self._save_to_persistence()
            
            logger.info("CacheManager stopped")
    
    def get(self, key: str, default: Any = None) -> Any:
        """キャッシュから値を取得"""
        start_time = time.time()
        
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # 有効期限チェック
                if entry.is_expired():
                    del self.cache[key]
                    self.stats.expired_entries += 1
                    self.stats.cache_misses += 1
                    logger.debug(f"Cache expired: {key}")
                    return default
                
                # アクセス情報更新
                entry.touch()
                self.stats.cache_hits += 1
                
                # アクセス時間統計更新
                access_time_ms = (time.time() - start_time) * 1000
                total_time = self.stats.avg_access_time_ms * (self.stats.cache_hits - 1)
                self.stats.avg_access_time_ms = (total_time + access_time_ms) / self.stats.cache_hits
                
                logger.debug(f"Cache hit: {key}")
                return entry.value
            else:
                self.stats.cache_misses += 1
                logger.debug(f"Cache miss: {key}")
                return default
    
    def set(self, 
            key: str, 
            value: Any, 
            ttl_seconds: Optional[int] = None) -> None:
        """キャッシュに値を設定"""
        if ttl_seconds is None:
            ttl_seconds = self.config.default_ttl_seconds
        
        with self._lock:
            # エントリサイズを計算
            try:
                size_bytes = len(pickle.dumps(value))
            except:
                size_bytes = 1024  # デフォルト値
            
            # メモリ制限チェック
            if self._would_exceed_memory_limit(size_bytes):
                self._evict_entries_for_memory(size_bytes)
            
            # サイズ制限チェック
            if len(self.cache) >= self.config.max_size:
                self._evict_entry()
            
            # エントリ作成
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                ttl_seconds=ttl_seconds,
                size_bytes=size_bytes
            )
            
            self.cache[key] = entry
            self.stats.total_entries = len(self.cache)
            self._update_memory_stats()
            
            logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
    
    def delete(self, key: str) -> bool:
        """キャッシュから値を削除"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.stats.total_entries = len(self.cache)
                self._update_memory_stats()
                logger.debug(f"Cache deleted: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        with self._lock:
            self.cache.clear()
            self.stats = CacheStats()
            logger.info("Cache cleared")
    
    def exists(self, key: str) -> bool:
        """キーが存在するかチェック"""
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry.is_expired():
                    del self.cache[key]
                    self.stats.expired_entries += 1
                    return False
                return True
            return False
    
    def keys(self) -> List[str]:
        """キー一覧を取得"""
        with self._lock:
            # 有効期限切れのエントリを除外
            valid_keys = []
            expired_keys = []
            
            for key, entry in self.cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                else:
                    valid_keys.append(key)
            
            # 有効期限切れエントリを削除
            for key in expired_keys:
                del self.cache[key]
                self.stats.expired_entries += 1
            
            self.stats.total_entries = len(self.cache)
            return valid_keys
    
    def _would_exceed_memory_limit(self, additional_size_bytes: int) -> bool:
        """メモリ制限を超過するかチェック"""
        current_memory_bytes = sum(entry.size_bytes for entry in self.cache.values())
        total_memory_mb = (current_memory_bytes + additional_size_bytes) / (1024 * 1024)
        return total_memory_mb > self.config.max_memory_mb
    
    def _evict_entries_for_memory(self, required_bytes: int) -> None:
        """メモリ制限のためにエントリを退避"""
        current_memory_bytes = sum(entry.size_bytes for entry in self.cache.values())
        target_memory_bytes = (self.config.max_memory_mb * 1024 * 1024) - required_bytes
        
        while current_memory_bytes > target_memory_bytes and self.cache:
            evicted_key = self._select_eviction_candidate()
            if evicted_key:
                evicted_entry = self.cache.pop(evicted_key)
                current_memory_bytes -= evicted_entry.size_bytes
                self.stats.evictions += 1
                logger.debug(f"Memory eviction: {evicted_key}")
            else:
                break
    
    def _evict_entry(self) -> None:
        """エントリを1つ退避"""
        evicted_key = self._select_eviction_candidate()
        if evicted_key:
            del self.cache[evicted_key]
            self.stats.evictions += 1
            logger.debug(f"Size eviction: {evicted_key}")
    
    def _select_eviction_candidate(self) -> Optional[str]:
        """退避対象エントリを選択"""
        if not self.cache:
            return None
        
        if self.config.strategy == CacheStrategy.LRU:
            # 最も古くアクセスされたエントリ
            return min(self.cache.keys(), 
                      key=lambda k: self.cache[k].last_accessed)
        
        elif self.config.strategy == CacheStrategy.LFU:
            # 最もアクセス頻度の低いエントリ
            return min(self.cache.keys(), 
                      key=lambda k: self.cache[k].access_count)
        
        elif self.config.strategy == CacheStrategy.FIFO:
            # 最も古く作成されたエントリ
            return min(self.cache.keys(), 
                      key=lambda k: self.cache[k].created_at)
        
        elif self.config.strategy == CacheStrategy.TTL:
            # 最も早く期限切れになるエントリ
            return min(self.cache.keys(), 
                      key=lambda k: self.cache[k].created_at + 
                                   (self.cache[k].ttl_seconds or float('inf')))
        
        else:
            # デフォルトはLRU
            return min(self.cache.keys(), 
                      key=lambda k: self.cache[k].last_accessed)
    
    def _update_memory_stats(self) -> None:
        """メモリ統計を更新"""
        total_bytes = sum(entry.size_bytes for entry in self.cache.values())
        self.stats.total_memory_mb = total_bytes / (1024 * 1024)
    
    async def _cleanup_loop(self) -> None:
        """定期クリーンアップループ"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                self._cleanup_expired_entries()
                
                if self.config.enable_persistence:
                    self._save_to_persistence()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")
    
    def _cleanup_expired_entries(self) -> None:
        """有効期限切れエントリをクリーンアップ"""
        with self._lock:
            expired_keys = []
            
            for key, entry in self.cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
                self.stats.expired_entries += 1
            
            if expired_keys:
                self.stats.total_entries = len(self.cache)
                self._update_memory_stats()
                logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
    
    def _save_to_persistence(self) -> None:
        """キャッシュを永続化"""
        if not self.config.persistence_file:
            return
        
        try:
            with open(self.config.persistence_file, 'wb') as f:
                pickle.dump(self.cache, f)
            logger.debug(f"Cache saved to {self.config.persistence_file}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _load_from_persistence(self) -> None:
        """永続化されたキャッシュを読み込み"""
        if not self.config.persistence_file:
            return
        
        try:
            with open(self.config.persistence_file, 'rb') as f:
                self.cache = pickle.load(f)
            
            # 有効期限切れエントリをクリーンアップ
            self._cleanup_expired_entries()
            
            self.stats.total_entries = len(self.cache)
            self._update_memory_stats()
            
            logger.info(f"Cache loaded from {self.config.persistence_file}")
        except FileNotFoundError:
            logger.debug("No persistence file found, starting with empty cache")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        with self._lock:
            stats_dict = self.stats.to_dict()
            
            # 追加統計
            if self.cache:
                access_counts = [entry.access_count for entry in self.cache.values()]
                ages = [time.time() - entry.created_at for entry in self.cache.values()]
                
                stats_dict.update({
                    "max_access_count": max(access_counts),
                    "min_access_count": min(access_counts),
                    "avg_access_count": sum(access_counts) / len(access_counts),
                    "max_age_seconds": max(ages),
                    "min_age_seconds": min(ages),
                    "avg_age_seconds": sum(ages) / len(ages),
                    "config": {
                        "max_size": self.config.max_size,
                        "default_ttl_seconds": self.config.default_ttl_seconds,
                        "strategy": self.config.strategy.value,
                        "max_memory_mb": self.config.max_memory_mb
                    }
                })
            
            return stats_dict
    
    def get_top_accessed_keys(self, limit: int = 10) -> List[Dict[str, Any]]:
        """最もアクセスされたキーを取得"""
        with self._lock:
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: x[1].access_count,
                reverse=True
            )
            
            return [
                {
                    "key": key,
                    "access_count": entry.access_count,
                    "last_accessed": datetime.fromtimestamp(entry.last_accessed).isoformat(),
                    "age_seconds": time.time() - entry.created_at,
                    "size_bytes": entry.size_bytes
                }
                for key, entry in sorted_entries[:limit]
            ]


def cached(ttl_seconds: Optional[int] = None, 
          cache_manager: Optional[CacheManager] = None):
    """キャッシュデコレーター"""
    def decorator(func):
        import functools
        
        # デフォルトキャッシュマネージャー
        nonlocal cache_manager
        if cache_manager is None:
            cache_manager = CacheManager()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # キャッシュキーを生成
            cache_key = _generate_cache_key(func.__name__, args, kwargs)
            
            # キャッシュから取得
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # 関数実行
            result = func(*args, **kwargs)
            
            # キャッシュに保存
            cache_manager.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """キャッシュキーを生成"""
    key_data = {
        "func": func_name,
        "args": str(args),
        "kwargs": str(sorted(kwargs.items()))
    }
    
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


# グローバルキャッシュマネージャー
global_cache_manager = CacheManager()