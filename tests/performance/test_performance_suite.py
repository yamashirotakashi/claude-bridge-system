#!/usr/bin/env python3
"""
Claude Bridge System - Performance Test Suite
Comprehensive performance testing for all system components
"""

import asyncio
import time
import threading
import statistics
import json
import psutil
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from claude_bridge.monitoring.metrics_collector import MetricsCollector
from claude_bridge.monitoring.health_checker import HealthChecker  
from claude_bridge.monitoring.performance_monitor import PerformanceMonitor
from claude_bridge.performance.profiler import Profiler
from claude_bridge.performance.cache_manager import CacheManager
from claude_bridge.core.bridge_filesystem import BridgeFileSystem
from claude_bridge.core.project_registry import ProjectRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceTestResult:
    """Performance test result data structure"""
    test_name: str
    duration_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_ops_per_sec: float
    success_rate: float
    error_count: int
    metadata: Dict[str, Any]

class PerformanceTestSuite:
    """Comprehensive performance test suite"""
    
    def __init__(self):
        self.results: List[PerformanceTestResult] = []
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker()
        self.performance_monitor = PerformanceMonitor()
        self.profiler = Profiler()
        self.cache_manager = CacheManager()
        self.bridge_fs = BridgeFileSystem("/tmp/test_bridge")
        self.project_registry = ProjectRegistry()
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests"""
        logger.info("Starting comprehensive performance test suite")
        
        # Start metrics collection
        self.metrics_collector.start_collection()
        
        try:
            # Core system performance tests
            self._test_filesystem_performance()
            self._test_project_registry_performance()
            self._test_metrics_collection_performance()
            self._test_health_check_performance()
            self._test_cache_performance()
            
            # Concurrent operation tests
            self._test_concurrent_file_operations()
            self._test_concurrent_metrics_collection()
            self._test_concurrent_health_checks()
            
            # Load testing
            self._test_high_load_scenarios()
            self._test_memory_pressure()
            self._test_cpu_intensive_operations()
            
            # Integration performance tests
            self._test_end_to_end_performance()
            
        finally:
            self.metrics_collector.stop_collection()
            
        return self._generate_performance_report()
    
    def _test_filesystem_performance(self):
        """Test filesystem operations performance"""
        logger.info("Testing filesystem performance")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        try:
            # Test file creation performance
            for i in range(1000):
                try:
                    self.bridge_fs.write_file(f"test_file_{i}.txt", f"Test content {i}")
                    operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"File write error: {e}")
            
            # Test file reading performance
            for i in range(1000):
                try:
                    content = self.bridge_fs.read_file(f"test_file_{i}.txt")
                    if content:
                        operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"File read error: {e}")
            
            # Test file listing performance
            for _ in range(100):
                try:
                    files = self.bridge_fs.list_files()
                    operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"File list error: {e}")
                    
        except Exception as e:
            logger.error(f"Filesystem test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="filesystem_performance",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "file_operations": 2000,
                "list_operations": 100
            }
        )
        
        self.results.append(result)
        logger.info(f"Filesystem performance: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_project_registry_performance(self):
        """Test project registry performance"""
        logger.info("Testing project registry performance")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        try:
            # Test project registration performance
            for i in range(500):
                try:
                    self.project_registry.register_project(
                        f"test_project_{i}",
                        f"/tmp/test_project_{i}",
                        {"type": "test", "priority": i % 5}
                    )
                    operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Project registration error: {e}")
            
            # Test project lookup performance
            for i in range(500):
                try:
                    project = self.project_registry.get_project(f"test_project_{i}")
                    if project:
                        operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Project lookup error: {e}")
            
            # Test project listing performance
            for _ in range(100):
                try:
                    projects = self.project_registry.list_projects()
                    operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Project list error: {e}")
                    
        except Exception as e:
            logger.error(f"Project registry test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="project_registry_performance",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "registration_operations": 500,
                "lookup_operations": 500,
                "list_operations": 100
            }
        )
        
        self.results.append(result)
        logger.info(f"Project registry performance: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_metrics_collection_performance(self):
        """Test metrics collection performance"""
        logger.info("Testing metrics collection performance")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        try:
            # Test metrics collection performance
            for _ in range(100):
                try:
                    metrics = self.metrics_collector.get_system_metrics()
                    if metrics:
                        operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Metrics collection error: {e}")
            
            # Test counter operations
            for i in range(1000):
                try:
                    self.metrics_collector.increment_counter(f"test_counter_{i % 10}")
                    operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Counter increment error: {e}")
            
            # Test gauge operations
            for i in range(1000):
                try:
                    self.metrics_collector.set_gauge(f"test_gauge_{i % 10}", i * 0.1)
                    operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Gauge set error: {e}")
                    
        except Exception as e:
            logger.error(f"Metrics collection test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="metrics_collection_performance",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "system_metrics_calls": 100,
                "counter_operations": 1000,
                "gauge_operations": 1000
            }
        )
        
        self.results.append(result)
        logger.info(f"Metrics collection performance: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_health_check_performance(self):
        """Test health check performance"""
        logger.info("Testing health check performance")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        try:
            # Test system health checks
            for _ in range(100):
                try:
                    health = self.health_checker.check_system_health()
                    if health:
                        operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"System health check error: {e}")
            
            # Test component health checks
            components = ["cpu", "memory", "disk", "network"]
            for _ in range(100):
                for component in components:
                    try:
                        health = self.health_checker.check_component_health(component)
                        operations += 1
                    except Exception as e:
                        errors += 1
                        logger.error(f"Component health check error: {e}")
                        
        except Exception as e:
            logger.error(f"Health check test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="health_check_performance",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "system_health_checks": 100,
                "component_health_checks": 400
            }
        )
        
        self.results.append(result)
        logger.info(f"Health check performance: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_cache_performance(self):
        """Test cache performance"""
        logger.info("Testing cache performance")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        try:
            # Test cache set operations
            for i in range(1000):
                try:
                    self.cache_manager.set(f"test_key_{i}", f"test_value_{i}")
                    operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Cache set error: {e}")
            
            # Test cache get operations
            for i in range(1000):
                try:
                    value = self.cache_manager.get(f"test_key_{i}")
                    if value is not None:
                        operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Cache get error: {e}")
            
            # Test cache delete operations
            for i in range(500):
                try:
                    self.cache_manager.delete(f"test_key_{i}")
                    operations += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Cache delete error: {e}")
                    
        except Exception as e:
            logger.error(f"Cache test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="cache_performance",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "set_operations": 1000,
                "get_operations": 1000,
                "delete_operations": 500
            }
        )
        
        self.results.append(result)
        logger.info(f"Cache performance: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_concurrent_file_operations(self):
        """Test concurrent file operations performance"""
        logger.info("Testing concurrent file operations performance")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        def file_operation_worker(worker_id: int, operation_count: int):
            nonlocal operations, errors
            worker_ops = 0
            worker_errors = 0
            
            for i in range(operation_count):
                try:
                    # Write operation
                    filename = f"concurrent_test_{worker_id}_{i}.txt"
                    self.bridge_fs.write_file(filename, f"Worker {worker_id} content {i}")
                    worker_ops += 1
                    
                    # Read operation
                    content = self.bridge_fs.read_file(filename)
                    if content:
                        worker_ops += 1
                        
                except Exception as e:
                    worker_errors += 1
                    logger.error(f"Concurrent file operation error: {e}")
            
            operations += worker_ops
            errors += worker_errors
        
        try:
            # Run concurrent file operations
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(file_operation_worker, i, 100)
                    for i in range(10)
                ]
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        errors += 1
                        logger.error(f"Concurrent operation error: {e}")
                        
        except Exception as e:
            logger.error(f"Concurrent file operations test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="concurrent_file_operations",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "concurrent_workers": 10,
                "operations_per_worker": 200
            }
        )
        
        self.results.append(result)
        logger.info(f"Concurrent file operations: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_concurrent_metrics_collection(self):
        """Test concurrent metrics collection performance"""
        logger.info("Testing concurrent metrics collection performance")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        def metrics_worker(worker_id: int, operation_count: int):
            nonlocal operations, errors
            worker_ops = 0
            worker_errors = 0
            
            for i in range(operation_count):
                try:
                    # Counter operations
                    self.metrics_collector.increment_counter(f"concurrent_counter_{worker_id}")
                    worker_ops += 1
                    
                    # Gauge operations
                    self.metrics_collector.set_gauge(f"concurrent_gauge_{worker_id}", i * 0.1)
                    worker_ops += 1
                    
                    # System metrics collection
                    if i % 10 == 0:
                        metrics = self.metrics_collector.get_system_metrics()
                        if metrics:
                            worker_ops += 1
                            
                except Exception as e:
                    worker_errors += 1
                    logger.error(f"Concurrent metrics error: {e}")
            
            operations += worker_ops
            errors += worker_errors
        
        try:
            # Run concurrent metrics operations
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(metrics_worker, i, 200)
                    for i in range(5)
                ]
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        errors += 1
                        logger.error(f"Concurrent metrics operation error: {e}")
                        
        except Exception as e:
            logger.error(f"Concurrent metrics collection test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="concurrent_metrics_collection",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "concurrent_workers": 5,
                "operations_per_worker": 200
            }
        )
        
        self.results.append(result)
        logger.info(f"Concurrent metrics collection: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_concurrent_health_checks(self):
        """Test concurrent health checks performance"""
        logger.info("Testing concurrent health checks performance")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        def health_check_worker(worker_id: int, check_count: int):
            nonlocal operations, errors
            worker_ops = 0
            worker_errors = 0
            
            components = ["cpu", "memory", "disk", "network"]
            
            for i in range(check_count):
                try:
                    # System health check
                    health = self.health_checker.check_system_health()
                    if health:
                        worker_ops += 1
                    
                    # Component health checks
                    component = components[i % len(components)]
                    comp_health = self.health_checker.check_component_health(component)
                    if comp_health:
                        worker_ops += 1
                        
                except Exception as e:
                    worker_errors += 1
                    logger.error(f"Concurrent health check error: {e}")
            
            operations += worker_ops
            errors += worker_errors
        
        try:
            # Run concurrent health checks
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(health_check_worker, i, 50)
                    for i in range(3)
                ]
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        errors += 1
                        logger.error(f"Concurrent health check operation error: {e}")
                        
        except Exception as e:
            logger.error(f"Concurrent health checks test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="concurrent_health_checks", 
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "concurrent_workers": 3,
                "checks_per_worker": 100
            }
        )
        
        self.results.append(result)
        logger.info(f"Concurrent health checks: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_high_load_scenarios(self):
        """Test high load scenarios"""
        logger.info("Testing high load scenarios")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        try:
            # Simulate high load with mixed operations
            def mixed_operations_worker(worker_id: int):
                nonlocal operations, errors
                worker_ops = 0
                worker_errors = 0
                
                for i in range(100):
                    try:
                        # File operations
                        filename = f"load_test_{worker_id}_{i}.txt"
                        self.bridge_fs.write_file(filename, f"Load test content {i}")
                        content = self.bridge_fs.read_file(filename)
                        worker_ops += 2
                        
                        # Metrics operations
                        self.metrics_collector.increment_counter(f"load_counter_{worker_id}")
                        self.metrics_collector.set_gauge(f"load_gauge_{worker_id}", i)
                        worker_ops += 2
                        
                        # Cache operations
                        self.cache_manager.set(f"load_key_{worker_id}_{i}", f"load_value_{i}")
                        cached_value = self.cache_manager.get(f"load_key_{worker_id}_{i}")
                        worker_ops += 2
                        
                        # Health check (every 10 operations)
                        if i % 10 == 0:
                            health = self.health_checker.check_system_health()
                            if health:
                                worker_ops += 1
                                
                    except Exception as e:
                        worker_errors += 1
                        logger.error(f"High load operation error: {e}")
                
                operations += worker_ops
                errors += worker_errors
            
            # Run high load test with multiple workers
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(mixed_operations_worker, i)
                    for i in range(8)
                ]
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        errors += 1
                        logger.error(f"High load worker error: {e}")
                        
        except Exception as e:
            logger.error(f"High load test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="high_load_scenarios",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "concurrent_workers": 8,
                "mixed_operations_per_worker": 700
            }
        )
        
        self.results.append(result)
        logger.info(f"High load scenarios: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_memory_pressure(self):
        """Test system behavior under memory pressure"""
        logger.info("Testing memory pressure scenarios")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        try:
            # Create memory pressure by storing large amounts of data
            large_data_cache = []
            
            for i in range(1000):
                try:
                    # Generate large data objects
                    large_data = {
                        'id': i,
                        'data': 'x' * 1024 * 10,  # 10KB per object
                        'metadata': {f'key_{j}': f'value_{j}' for j in range(100)}
                    }
                    large_data_cache.append(large_data)
                    
                    # Test system operations under memory pressure
                    if i % 50 == 0:
                        # File operations
                        self.bridge_fs.write_file(f"memory_test_{i}.txt", str(large_data))
                        operations += 1
                        
                        # Metrics collection
                        metrics = self.metrics_collector.get_system_metrics()
                        if metrics:
                            operations += 1
                        
                        # Health check
                        health = self.health_checker.check_system_health()
                        if health:
                            operations += 1
                            
                except Exception as e:
                    errors += 1
                    logger.error(f"Memory pressure operation error: {e}")
            
            # Clean up
            large_data_cache.clear()
                    
        except Exception as e:
            logger.error(f"Memory pressure test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="memory_pressure",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "memory_objects_created": 1000,
                "memory_per_object_kb": 10
            }
        )
        
        self.results.append(result)
        logger.info(f"Memory pressure: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_cpu_intensive_operations(self):
        """Test CPU intensive operations"""
        logger.info("Testing CPU intensive operations")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        def cpu_intensive_worker(worker_id: int):
            nonlocal operations, errors
            worker_ops = 0
            worker_errors = 0
            
            try:
                # CPU intensive calculations
                for i in range(1000):
                    # Complex mathematical operations
                    result = sum(j ** 2 for j in range(100))
                    
                    # String operations
                    text = f"CPU intensive test {worker_id} {i} {result}"
                    processed = text.upper().lower().replace(" ", "_")
                    
                    worker_ops += 1
                    
                    # Test system operations during CPU load
                    if i % 100 == 0:
                        try:
                            # Quick health check
                            health = self.health_checker.check_component_health("cpu")
                            if health:
                                worker_ops += 1
                                
                            # Metrics update
                            self.metrics_collector.set_gauge(f"cpu_test_gauge_{worker_id}", result)
                            worker_ops += 1
                            
                        except Exception as e:
                            worker_errors += 1
                            logger.error(f"CPU test operation error: {e}")
                            
            except Exception as e:
                worker_errors += 1
                logger.error(f"CPU intensive worker error: {e}")
                
            operations += worker_ops
            errors += worker_errors
        
        try:
            # Run CPU intensive operations with multiple workers
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(cpu_intensive_worker, i)
                    for i in range(4)
                ]
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        errors += 1
                        logger.error(f"CPU intensive test error: {e}")
                        
        except Exception as e:
            logger.error(f"CPU intensive operations test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="cpu_intensive_operations",
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "concurrent_workers": 4,
                "calculations_per_worker": 1000
            }
        )
        
        self.results.append(result)
        logger.info(f"CPU intensive operations: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _test_end_to_end_performance(self):
        """Test end-to-end system performance"""
        logger.info("Testing end-to-end system performance")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()
        
        operations = 0
        errors = 0
        
        try:
            # Simulate realistic end-to-end workflows
            for scenario in range(50):
                try:
                    # Scenario: Project setup and context loading
                    project_name = f"e2e_project_{scenario}"
                    project_path = f"/tmp/e2e_test_{scenario}"
                    
                    # Register project
                    self.project_registry.register_project(
                        project_name, project_path, {"type": "e2e_test"}
                    )
                    operations += 1
                    
                    # Create project files
                    for file_idx in range(5):
                        filename = f"project_file_{file_idx}.txt"
                        content = f"Project {project_name} file {file_idx} content"
                        self.bridge_fs.write_file(filename, content)
                        operations += 1
                    
                    # Load and process project context
                    project = self.project_registry.get_project(project_name)
                    if project:
                        operations += 1
                    
                    # Collect metrics for this scenario
                    metrics = self.metrics_collector.get_system_metrics()
                    if metrics:
                        operations += 1
                    
                    # Check system health
                    health = self.health_checker.check_system_health()
                    if health:
                        operations += 1
                    
                    # Cache scenario results
                    self.cache_manager.set(f"e2e_result_{scenario}", {
                        "project": project_name,
                        "files_created": 5,
                        "timestamp": time.time()
                    })
                    operations += 1
                    
                    # Read and verify files
                    for file_idx in range(5):
                        filename = f"project_file_{file_idx}.txt"
                        content = self.bridge_fs.read_file(filename)
                        if content:
                            operations += 1
                    
                except Exception as e:
                    errors += 1
                    logger.error(f"E2E scenario {scenario} error: {e}")
                    
        except Exception as e:
            logger.error(f"End-to-end performance test error: {e}")
            errors += 1
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()
        
        duration_ms = (end_time - start_time) * 1000
        throughput = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceTestResult(
            test_name="end_to_end_performance", 
            duration_ms=duration_ms,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "scenarios_executed": 50,
                "operations_per_scenario": 12
            }
        )
        
        self.results.append(result)
        logger.info(f"End-to-end performance: {throughput:.2f} ops/sec, {success_rate:.2f}% success rate")
    
    def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.results:
            return {"error": "No performance test results available"}
        
        # Calculate overall statistics
        total_duration = sum(r.duration_ms for r in self.results)
        total_operations = sum(r.metadata.get("total_operations", 0) for r in self.results)
        total_errors = sum(r.error_count for r in self.results)
        
        avg_throughput = statistics.mean([r.throughput_ops_per_sec for r in self.results])
        avg_success_rate = statistics.mean([r.success_rate for r in self.results])
        avg_memory_usage = statistics.mean([r.memory_usage_mb for r in self.results])
        avg_cpu_usage = statistics.mean([r.cpu_usage_percent for r in self.results])
        
        # Find best and worst performing tests
        best_throughput = max(self.results, key=lambda r: r.throughput_ops_per_sec)
        worst_throughput = min(self.results, key=lambda r: r.throughput_ops_per_sec)
        highest_memory = max(self.results, key=lambda r: r.memory_usage_mb)
        highest_cpu = max(self.results, key=lambda r: r.cpu_usage_percent)
        
        # Performance grade
        performance_grade = "A"
        if avg_success_rate < 95:
            performance_grade = "C"
        elif avg_success_rate < 98:
            performance_grade = "B"
        elif avg_throughput < 100:
            performance_grade = "B"
        
        report = {
            "performance_test_summary": {
                "total_tests": len(self.results),
                "total_duration_ms": total_duration,
                "total_operations": total_operations,
                "total_errors": total_errors,
                "overall_performance_grade": performance_grade
            },
            "average_metrics": {
                "throughput_ops_per_sec": round(avg_throughput, 2),
                "success_rate_percent": round(avg_success_rate, 2),
                "memory_usage_mb": round(avg_memory_usage, 2),
                "cpu_usage_percent": round(avg_cpu_usage, 2)
            },
            "performance_highlights": {
                "best_throughput_test": {
                    "name": best_throughput.test_name,
                    "throughput": round(best_throughput.throughput_ops_per_sec, 2)
                },
                "worst_throughput_test": {
                    "name": worst_throughput.test_name,
                    "throughput": round(worst_throughput.throughput_ops_per_sec, 2)
                },
                "highest_memory_usage": {
                    "name": highest_memory.test_name,
                    "memory_mb": round(highest_memory.memory_usage_mb, 2)
                },
                "highest_cpu_usage": {
                    "name": highest_cpu.test_name,
                    "cpu_percent": round(highest_cpu.cpu_usage_percent, 2)
                }
            },
            "detailed_results": [asdict(result) for result in self.results],
            "recommendations": self._generate_performance_recommendations()
        }
        
        return report
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Analyze results for recommendations
        avg_success_rate = statistics.mean([r.success_rate for r in self.results])
        avg_throughput = statistics.mean([r.throughput_ops_per_sec for r in self.results])
        avg_memory = statistics.mean([r.memory_usage_mb for r in self.results])
        avg_cpu = statistics.mean([r.cpu_usage_percent for r in self.results])
        
        if avg_success_rate < 95:
            recommendations.append("Investigate error handling and improve system reliability")
        
        if avg_throughput < 100:
            recommendations.append("Consider optimizing core operations for better throughput")
        
        if avg_memory > 100:
            recommendations.append("Monitor memory usage and implement memory optimization strategies")
        
        if avg_cpu > 50:
            recommendations.append("Consider CPU optimization for intensive operations")
        
        # Check for specific performance issues
        filesystem_results = [r for r in self.results if "filesystem" in r.test_name]
        if filesystem_results and statistics.mean([r.throughput_ops_per_sec for r in filesystem_results]) < 50:
            recommendations.append("Optimize filesystem operations with caching or async I/O")
        
        concurrent_results = [r for r in self.results if "concurrent" in r.test_name]
        if concurrent_results and statistics.mean([r.success_rate for r in concurrent_results]) < 90:
            recommendations.append("Review concurrent operation handling and thread safety")
        
        if not recommendations:
            recommendations.append("System performance is within acceptable ranges")
        
        return recommendations

def main():
    """Run performance test suite"""
    print("🚀 Starting Claude Bridge System Performance Test Suite")
    print("=" * 60)
    
    # Create and run performance tests
    test_suite = PerformanceTestSuite()
    
    try:
        results = test_suite.run_all_tests()
        
        # Save results to file
        output_file = "/tmp/claude_bridge_performance_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📊 Performance Test Results:")
        print(f"Total Tests: {results['performance_test_summary']['total_tests']}")
        print(f"Total Operations: {results['performance_test_summary']['total_operations']:,}")
        print(f"Total Errors: {results['performance_test_summary']['total_errors']}")
        print(f"Performance Grade: {results['performance_test_summary']['overall_performance_grade']}")
        print(f"\n📈 Average Metrics:")
        print(f"Throughput: {results['average_metrics']['throughput_ops_per_sec']:.2f} ops/sec")
        print(f"Success Rate: {results['average_metrics']['success_rate_percent']:.2f}%")
        print(f"Memory Usage: {results['average_metrics']['memory_usage_mb']:.2f} MB")
        print(f"CPU Usage: {results['average_metrics']['cpu_usage_percent']:.2f}%")
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"{i}. {rec}")
        
        print(f"\n📁 Detailed results saved to: {output_file}")
        print("✅ Performance test suite completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test suite failed: {e}")
        logger.error(f"Performance test suite error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)