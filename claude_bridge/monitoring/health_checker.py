"""
Claude Bridge System - Health Checker
システムコンポーネントのヘルスチェック
"""

import logging
import asyncio
import time
import psutil
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """ヘルスステータス"""
    HEALTHY = "healthy"          # 正常
    DEGRADED = "degraded"        # 機能低下
    UNHEALTHY = "unhealthy"      # 異常
    UNKNOWN = "unknown"          # 不明


@dataclass
class ComponentHealth:
    """コンポーネントヘルス情報"""
    name: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    last_check: Optional[str] = None
    response_time_ms: float = 0.0
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.last_check is None:
            self.last_check = datetime.now().isoformat()


@dataclass 
class SystemHealth:
    """システム全体のヘルス情報"""
    overall_status: HealthStatus
    components: List[ComponentHealth]
    system_info: Dict[str, Any]
    timestamp: str
    uptime_seconds: float = 0.0
    alerts: Optional[List[Dict[str, Any]]] = None
    
    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []


class HealthChecker:
    """ヘルスチェックシステム"""
    
    def __init__(self):
        """初期化"""
        self.health_checks: Dict[str, Callable] = {}
        self.component_history: Dict[str, List[ComponentHealth]] = {}
        self.start_time = time.time()
        
        # デフォルトのヘルスチェックを登録
        self._register_default_checks()
        
        logger.info("HealthChecker initialized")
    
    def _register_default_checks(self) -> None:
        """デフォルトのヘルスチェックを登録"""
        self.register_health_check("system_resources", self._check_system_resources)
        self.register_health_check("disk_space", self._check_disk_space)
        self.register_health_check("memory_usage", self._check_memory_usage)
        self.register_health_check("bridge_filesystem", self._check_bridge_filesystem)
        self.register_health_check("memory_bridge", self._check_memory_bridge)
    
    def register_health_check(self, name: str, check_func: Callable[[], ComponentHealth]) -> None:
        """ヘルスチェック関数を登録"""
        self.health_checks[name] = check_func
        logger.info(f"Health check registered: {name}")
    
    def unregister_health_check(self, name: str) -> bool:
        """ヘルスチェック関数を削除"""
        if name in self.health_checks:
            del self.health_checks[name]
            logger.info(f"Health check unregistered: {name}")
            return True
        return False
    
    async def check_all_components(self) -> SystemHealth:
        """全コンポーネントのヘルスチェックを実行"""
        components = []
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                
                # 非同期チェック関数の場合
                if asyncio.iscoroutinefunction(check_func):
                    component_health = await check_func()
                else:
                    component_health = check_func()
                
                # レスポンス時間を記録
                response_time = (time.time() - start_time) * 1000
                component_health.response_time_ms = response_time
                
                components.append(component_health)
                
                # 履歴に追加
                if name not in self.component_history:
                    self.component_history[name] = []
                self.component_history[name].append(component_health)
                
                # 履歴を制限（最新100件）
                if len(self.component_history[name]) > 100:
                    self.component_history[name] = self.component_history[name][-100:]
                
                logger.debug(f"Health check completed: {name} = {component_health.status.value}")
                
            except Exception as e:
                logger.error(f"Health check failed: {name}, error: {e}")
                
                error_health = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {str(e)}",
                    details={"error": str(e), "error_type": type(e).__name__}
                )
                components.append(error_health)
        
        # 全体ステータスを決定
        overall_status = self._determine_overall_status(components)
        
        # システム情報を収集
        system_info = self._collect_system_info()
        
        # アラートを生成
        alerts = self._generate_alerts(components)
        
        return SystemHealth(
            overall_status=overall_status,
            components=components,
            system_info=system_info,
            timestamp=datetime.now().isoformat(),
            uptime_seconds=time.time() - self.start_time,
            alerts=alerts
        )
    
    def check_component(self, name: str) -> Optional[ComponentHealth]:
        """特定のコンポーネントのヘルスチェック"""
        if name not in self.health_checks:
            return None
        
        try:
            start_time = time.time()
            check_func = self.health_checks[name]
            
            if asyncio.iscoroutinefunction(check_func):
                # 非同期関数の場合は同期的に実行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    component_health = loop.run_until_complete(check_func())
                finally:
                    loop.close()
            else:
                component_health = check_func()
            
            # レスポンス時間を記録
            response_time = (time.time() - start_time) * 1000
            component_health.response_time_ms = response_time
            
            return component_health
            
        except Exception as e:
            logger.error(f"Health check failed: {name}, error: {e}")
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    def get_component_history(self, name: str, limit: int = 50) -> List[ComponentHealth]:
        """コンポーネントのヘルス履歴を取得"""
        if name not in self.component_history:
            return []
        
        return self.component_history[name][-limit:]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """ヘルスサマリーを取得"""
        summary = {
            "registered_checks": list(self.health_checks.keys()),
            "total_checks": len(self.health_checks),
            "uptime_seconds": time.time() - self.start_time,
            "history_stats": {}
        }
        
        # 各コンポーネントの統計
        for name, history in self.component_history.items():
            if history:
                recent_checks = history[-10:]  # 最新10件
                healthy_count = sum(1 for h in recent_checks if h.status == HealthStatus.HEALTHY)
                
                summary["history_stats"][name] = {
                    "total_checks": len(history),
                    "recent_health_rate": healthy_count / len(recent_checks),
                    "last_status": recent_checks[-1].status.value if recent_checks else "unknown",
                    "avg_response_time_ms": sum(h.response_time_ms for h in recent_checks) / len(recent_checks)
                }
        
        return summary
    
    def _determine_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """全体ステータスを決定"""
        if not components:
            return HealthStatus.UNKNOWN
        
        # 各ステータスの数をカウント
        status_counts = {status: 0 for status in HealthStatus}
        for component in components:
            status_counts[component.status] += 1
        
        # 決定ロジック
        if status_counts[HealthStatus.UNHEALTHY] > 0:
            return HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.DEGRADED] > 0:
            return HealthStatus.DEGRADED
        elif status_counts[HealthStatus.UNKNOWN] > len(components) / 2:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """システム情報を収集"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "memory_available_gb": psutil.virtual_memory().available / (1024**3),
                "disk_total_gb": psutil.disk_usage('/').total / (1024**3),
                "disk_free_gb": psutil.disk_usage('/').free / (1024**3),
                "boot_time": psutil.boot_time(),
                "process_count": len(psutil.pids()),
                "platform": psutil.os.name,
                "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}"
            }
        except Exception as e:
            logger.error(f"Failed to collect system info: {e}")
            return {"error": str(e)}
    
    def _generate_alerts(self, components: List[ComponentHealth]) -> List[Dict[str, Any]]:
        """アラートを生成"""
        alerts = []
        
        for component in components:
            if component.status == HealthStatus.UNHEALTHY:
                alerts.append({
                    "type": "component_unhealthy",
                    "component": component.name,
                    "message": f"Component {component.name} is unhealthy: {component.message}",
                    "severity": "critical",
                    "timestamp": component.last_check,
                    "response_time_ms": component.response_time_ms
                })
            elif component.status == HealthStatus.DEGRADED:
                alerts.append({
                    "type": "component_degraded",
                    "component": component.name,
                    "message": f"Component {component.name} is degraded: {component.message}",
                    "severity": "warning",
                    "timestamp": component.last_check,
                    "response_time_ms": component.response_time_ms
                })
            elif component.response_time_ms > 5000:  # 5秒以上
                alerts.append({
                    "type": "slow_response",
                    "component": component.name,
                    "message": f"Component {component.name} has slow response time: {component.response_time_ms:.1f}ms",
                    "severity": "warning",
                    "timestamp": component.last_check,
                    "response_time_ms": component.response_time_ms
                })
        
        return alerts
    
    # デフォルトヘルスチェック関数群
    
    def _check_system_resources(self) -> ComponentHealth:
        """システムリソースをチェック"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3)
            }
            
            # ステータス判定
            if cpu_percent > 90 or memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"High resource usage: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%"
            elif cpu_percent > 70 or memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Elevated resource usage: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Normal resource usage: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%"
            
            return ComponentHealth(
                name="system_resources",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return ComponentHealth(
                name="system_resources",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check system resources: {str(e)}",
                details={"error": str(e)}
            )
    
    def _check_disk_space(self) -> ComponentHealth:
        """ディスク容量をチェック"""
        try:
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            free_gb = disk.free / (1024**3)
            
            details = {
                "usage_percent": usage_percent,
                "free_gb": free_gb,
                "total_gb": disk.total / (1024**3)
            }
            
            # ステータス判定
            if usage_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk usage: {usage_percent:.1f}% used, {free_gb:.1f}GB free"
            elif usage_percent > 85:
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {usage_percent:.1f}% used, {free_gb:.1f}GB free"
            else:
                status = HealthStatus.HEALTHY
                message = f"Normal disk usage: {usage_percent:.1f}% used, {free_gb:.1f}GB free"
            
            return ComponentHealth(
                name="disk_space",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return ComponentHealth(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check disk space: {str(e)}",
                details={"error": str(e)}
            )
    
    def _check_memory_usage(self) -> ComponentHealth:
        """メモリ使用量をチェック"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            details = {
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_used_gb": memory.used / (1024**3),
                "swap_percent": swap.percent,
                "swap_used_gb": swap.used / (1024**3)
            }
            
            # ステータス判定
            if memory.percent > 95 or swap.percent > 80:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory usage: RAM {memory.percent:.1f}%, Swap {swap.percent:.1f}%"
            elif memory.percent > 85 or swap.percent > 50:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: RAM {memory.percent:.1f}%, Swap {swap.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Normal memory usage: RAM {memory.percent:.1f}%, Swap {swap.percent:.1f}%"
            
            return ComponentHealth(
                name="memory_usage",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return ComponentHealth(
                name="memory_usage",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check memory usage: {str(e)}",
                details={"error": str(e)}
            )
    
    def _check_bridge_filesystem(self) -> ComponentHealth:
        """ブリッジファイルシステムをチェック"""
        try:
            bridge_data_path = Path("bridge_data")
            
            details = {
                "bridge_data_exists": bridge_data_path.exists(),
                "is_directory": bridge_data_path.is_dir() if bridge_data_path.exists() else False,
                "is_writable": bridge_data_path.is_dir() and bridge_data_path.stat().st_mode & 0o200 != 0 if bridge_data_path.exists() else False
            }
            
            if bridge_data_path.exists():
                # ディレクトリ内のファイル数を確認
                file_count = len(list(bridge_data_path.iterdir())) if bridge_data_path.is_dir() else 0
                details["file_count"] = file_count
            
            # ステータス判定
            if not bridge_data_path.exists():
                status = HealthStatus.DEGRADED
                message = "Bridge data directory does not exist"
            elif not bridge_data_path.is_dir():
                status = HealthStatus.UNHEALTHY
                message = "Bridge data path exists but is not a directory"
            elif not details["is_writable"]:
                status = HealthStatus.DEGRADED
                message = "Bridge data directory is not writable"
            else:
                status = HealthStatus.HEALTHY
                message = f"Bridge filesystem is accessible with {details.get('file_count', 0)} items"
            
            return ComponentHealth(
                name="bridge_filesystem",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return ComponentHealth(
                name="bridge_filesystem",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check bridge filesystem: {str(e)}",
                details={"error": str(e)}
            )
    
    def _check_memory_bridge(self) -> ComponentHealth:
        """MISメモリブリッジをチェック"""
        try:
            memory_file = Path("bridge_data/mis_memory.json")
            
            details = {
                "memory_file_exists": memory_file.exists(),
                "file_size_mb": memory_file.stat().st_size / (1024**2) if memory_file.exists() else 0
            }
            
            if memory_file.exists():
                try:
                    import json
                    with open(memory_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    details["total_memories"] = data.get("total_memories", 0)
                    details["json_valid"] = True
                    
                except (json.JSONDecodeError, KeyError) as e:
                    details["json_valid"] = False
                    details["json_error"] = str(e)
            
            # ステータス判定
            if not memory_file.exists():
                status = HealthStatus.DEGRADED
                message = "MIS memory file does not exist"
            elif not details.get("json_valid", True):
                status = HealthStatus.UNHEALTHY
                message = f"MIS memory file is corrupted: {details.get('json_error', 'unknown error')}"
            elif details["file_size_mb"] > 100:  # 100MB以上
                status = HealthStatus.DEGRADED
                message = f"MIS memory file is large: {details['file_size_mb']:.1f}MB"
            else:
                status = HealthStatus.HEALTHY
                message = f"MIS memory bridge is healthy with {details.get('total_memories', 0)} memories"
            
            return ComponentHealth(
                name="memory_bridge",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return ComponentHealth(
                name="memory_bridge",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check memory bridge: {str(e)}",
                details={"error": str(e)}
            )