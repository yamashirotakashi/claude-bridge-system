"""
Claude Bridge System - Metrics Collector
システムメトリクスの収集と管理
"""

import json
import logging
import time
import psutil
import threading
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """メトリクスタイプ"""
    COUNTER = "counter"          # カウンター（累積値）
    GAUGE = "gauge"             # ゲージ（瞬間値）
    HISTOGRAM = "histogram"     # ヒストグラム（分布）
    TIMER = "timer"             # タイマー（実行時間）
    SYSTEM = "system"           # システムメトリクス


@dataclass
class MetricEntry:
    """メトリクスエントリー"""
    name: str
    value: Union[float, int, Dict[str, Any]]
    metric_type: MetricType
    timestamp: str
    labels: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SystemMetrics:
    """システムメトリクス"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    timestamp: str


class MetricsCollector:
    """メトリクス収集システム"""
    
    def __init__(self, 
                 storage_path: Optional[Path] = None,
                 retention_hours: int = 24,
                 collection_interval: int = 60):
        """
        初期化
        
        Args:
            storage_path: メトリクス保存パス
            retention_hours: メトリクス保持時間（時間）
            collection_interval: 収集間隔（秒）
        """
        self.storage_path = storage_path or Path("bridge_data/metrics")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.retention_hours = retention_hours
        self.collection_interval = collection_interval
        
        # メトリクスストレージ
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # システムメトリクス履歴
        self.system_metrics_history: deque = deque(maxlen=1440)  # 24時間分（1分間隔）
        
        # 収集制御
        self.collection_active = False
        self.collection_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        logger.info(f"MetricsCollector initialized: {self.storage_path}")
    
    def start_collection(self) -> None:
        """メトリクス収集を開始"""
        if self.collection_active:
            logger.warning("Metrics collection already running")
            return
        
        self.collection_active = True
        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()
        
        logger.info("Metrics collection started")
    
    def stop_collection(self) -> None:
        """メトリクス収集を停止"""
        self.collection_active = False
        if self.collection_thread and self.collection_thread.is_alive():
            self.collection_thread.join(timeout=5.0)
        
        logger.info("Metrics collection stopped")
    
    def _collection_loop(self) -> None:
        """メトリクス収集ループ"""
        while self.collection_active:
            try:
                # システムメトリクスを収集
                system_metrics = self._collect_system_metrics()
                self.system_metrics_history.append(system_metrics)
                
                # メトリクスを保存
                self._save_metrics()
                
                # 古いメトリクスをクリーンアップ
                self._cleanup_old_metrics()
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """システムメトリクス収集"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用量
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # ディスク使用量
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            
            # ネットワーク統計
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            # プロセス数
            process_count = len(psutil.pids())
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                process_count=process_count,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                process_count=0,
                timestamp=datetime.now().isoformat()
            )
    
    def record_counter(self, name: str, increment: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """カウンター値を記録"""
        with self._lock:
            self.counters[name] += increment
            
            entry = MetricEntry(
                name=name,
                value=self.counters[name],
                metric_type=MetricType.COUNTER,
                timestamp=datetime.now().isoformat(),
                labels=labels or {}
            )
            
            self.metrics[name].append(entry)
            logger.debug(f"Counter recorded: {name} = {self.counters[name]}")
    
    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """ゲージ値を記録"""
        with self._lock:
            self.gauges[name] = value
            
            entry = MetricEntry(
                name=name,
                value=value,
                metric_type=MetricType.GAUGE,
                timestamp=datetime.now().isoformat(),
                labels=labels or {}
            )
            
            self.metrics[name].append(entry)
            logger.debug(f"Gauge recorded: {name} = {value}")
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """ヒストグラム値を記録"""
        with self._lock:
            self.histograms[name].append(value)
            
            # 統計値を計算
            values = self.histograms[name]
            stats = {
                "count": len(values),
                "sum": sum(values),
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "avg": sum(values) / len(values) if values else 0
            }
            
            entry = MetricEntry(
                name=name,
                value=stats,
                metric_type=MetricType.HISTOGRAM,
                timestamp=datetime.now().isoformat(),
                labels=labels or {},
                metadata={"raw_values": values[-100:]}  # 最新100個のみ保持
            )
            
            self.metrics[name].append(entry)
            logger.debug(f"Histogram recorded: {name} = {stats}")
    
    def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
        """タイマー値を記録"""
        with self._lock:
            self.timers[name].append(duration)
            
            # 統計値を計算
            values = self.timers[name]
            stats = {
                "count": len(values),
                "total_time": sum(values),
                "min_time": min(values) if values else 0,
                "max_time": max(values) if values else 0,
                "avg_time": sum(values) / len(values) if values else 0
            }
            
            entry = MetricEntry(
                name=name,
                value=stats,
                metric_type=MetricType.TIMER,
                timestamp=datetime.now().isoformat(),
                labels=labels or {},
                metadata={"raw_durations": values[-100:]}  # 最新100個のみ保持
            )
            
            self.metrics[name].append(entry)
            logger.debug(f"Timer recorded: {name} = {stats}")
    
    def get_metric(self, name: str, limit: int = 100) -> List[MetricEntry]:
        """メトリクス履歴を取得"""
        with self._lock:
            if name not in self.metrics:
                return []
            
            return list(self.metrics[name])[-limit:]
    
    def get_current_values(self) -> Dict[str, Any]:
        """現在のメトリクス値を取得"""
        with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    name: {
                        "count": len(values),
                        "avg": sum(values) / len(values) if values else 0
                    }
                    for name, values in self.histograms.items()
                },
                "timers": {
                    name: {
                        "count": len(values),
                        "avg_time": sum(values) / len(values) if values else 0
                    }
                    for name, values in self.timers.items()
                },
                "timestamp": datetime.now().isoformat()
            }
    
    def get_system_metrics(self, limit: int = 100) -> List[SystemMetrics]:
        """システムメトリクス履歴を取得"""
        return list(self.system_metrics_history)[-limit:]
    
    def get_metric_summary(self) -> Dict[str, Any]:
        """メトリクスサマリーを取得"""
        with self._lock:
            current_system = self.system_metrics_history[-1] if self.system_metrics_history else None
            
            return {
                "summary": {
                    "total_metrics": len(self.metrics),
                    "counters_count": len(self.counters),
                    "gauges_count": len(self.gauges),
                    "histograms_count": len(self.histograms),
                    "timers_count": len(self.timers),
                    "system_metrics_count": len(self.system_metrics_history)
                },
                "current_system": asdict(current_system) if current_system else None,
                "alerts": self._check_alerts(),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_alerts(self) -> List[Dict[str, Any]]:
        """アラート条件をチェック"""
        alerts = []
        
        # 最新のシステムメトリクスをチェック
        if self.system_metrics_history:
            latest = self.system_metrics_history[-1]
            
            # CPU使用率アラート
            if latest.cpu_percent > 80:
                alerts.append({
                    "type": "high_cpu",
                    "message": f"High CPU usage: {latest.cpu_percent:.1f}%",
                    "severity": "critical" if latest.cpu_percent > 90 else "warning",
                    "value": latest.cpu_percent,
                    "threshold": 80
                })
            
            # メモリ使用率アラート
            if latest.memory_percent > 80:
                alerts.append({
                    "type": "high_memory",
                    "message": f"High memory usage: {latest.memory_percent:.1f}%",
                    "severity": "critical" if latest.memory_percent > 90 else "warning",
                    "value": latest.memory_percent,
                    "threshold": 80
                })
            
            # ディスク使用率アラート
            if latest.disk_usage_percent > 85:
                alerts.append({
                    "type": "high_disk",
                    "message": f"High disk usage: {latest.disk_usage_percent:.1f}%",
                    "severity": "critical" if latest.disk_usage_percent > 95 else "warning",
                    "value": latest.disk_usage_percent,
                    "threshold": 85
                })
        
        return alerts
    
    def _save_metrics(self) -> None:
        """メトリクスをファイルに保存"""
        try:
            metrics_file = self.storage_path / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
            
            # 保存データを準備
            save_data = {
                "timestamp": datetime.now().isoformat(),
                "current_values": self.get_current_values(),
                "system_metrics": [asdict(m) for m in list(self.system_metrics_history)[-10:]],  # 最新10件
                "alerts": self._check_alerts()
            }
            
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Metrics saved to {metrics_file}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _cleanup_old_metrics(self) -> None:
        """古いメトリクスファイルをクリーンアップ"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
            
            for metrics_file in self.storage_path.glob("metrics_*.json"):
                try:
                    # ファイル名から日付を抽出
                    date_str = metrics_file.stem.split('_')[1]
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff_time:
                        metrics_file.unlink()
                        logger.info(f"Cleaned up old metrics file: {metrics_file}")
                        
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse metrics file date: {metrics_file}, {e}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
    
    def export_metrics(self, output_path: Path, format: str = "json", 
                      start_time: Optional[str] = None, 
                      end_time: Optional[str] = None) -> bool:
        """メトリクスをエクスポート"""
        try:
            with self._lock:
                export_data = {
                    "export_info": {
                        "start_time": start_time,
                        "end_time": end_time,
                        "format": format,
                        "exported_at": datetime.now().isoformat()
                    },
                    "metrics": {},
                    "system_metrics": [asdict(m) for m in self.system_metrics_history],
                    "current_values": self.get_current_values(),
                    "summary": self.get_metric_summary()
                }
                
                # 各メトリクスをエクスポート
                for name, entries in self.metrics.items():
                    export_data["metrics"][name] = [asdict(entry) for entry in entries]
                
                if format == "json":
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                elif format == "csv":
                    # CSV形式でのエクスポート実装
                    import csv
                    with open(output_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Name', 'Type', 'Value', 'Timestamp', 'Labels'])
                        
                        for name, entries in self.metrics.items():
                            for entry in entries:
                                writer.writerow([
                                    entry.name,
                                    entry.metric_type.value,
                                    str(entry.value),
                                    entry.timestamp,
                                    json.dumps(entry.labels)
                                ])
                else:
                    logger.error(f"Unsupported export format: {format}")
                    return False
                
                logger.info(f"Metrics exported to {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False
    
    def timer_context(self, name: str, labels: Optional[Dict[str, str]] = None):
        """タイマーコンテキストマネージャー"""
        return TimerContext(self, name, labels)


class TimerContext:
    """タイマーコンテキストマネージャー"""
    
    def __init__(self, collector: MetricsCollector, name: str, labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.collector.record_timer(self.name, duration, self.labels)