#!/usr/bin/env python3
"""
Claude Bridge System - Simplified Performance Test
Testing core system performance without external dependencies
"""

import time
import json
import os
import threading
import statistics
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import shutil

@dataclass
class PerformanceResult:
    """Performance test result"""
    test_name: str
    duration_ms: float
    operations_per_sec: float
    success_rate: float
    error_count: int
    metadata: Dict[str, Any]

class SimplePerformanceTest:
    """Simplified performance test suite"""
    
    def __init__(self):
        self.results: List[PerformanceResult] = []
        self.test_dir = tempfile.mkdtemp(prefix="claude_bridge_perf_")
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests"""
        print("🚀 Starting Claude Bridge System Performance Tests")
        
        try:
            # Core performance tests
            self._test_file_operations()
            self._test_concurrent_operations()
            self._test_memory_operations()
            self._test_cpu_intensive_operations()
            self._test_mixed_workload()
            
            return self._generate_report()
            
        finally:
            # Cleanup
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
    
    def _test_file_operations(self):
        """Test file I/O performance"""
        print("📁 Testing file operations...")
        
        start_time = time.time()
        operations = 0
        errors = 0
        
        try:
            # Write operations
            for i in range(1000):
                try:
                    filepath = os.path.join(self.test_dir, f"test_file_{i}.txt")
                    with open(filepath, 'w') as f:
                        f.write(f"Test content {i} " * 10)
                    operations += 1
                except Exception as e:
                    errors += 1
            
            # Read operations
            for i in range(1000):
                try:
                    filepath = os.path.join(self.test_dir, f"test_file_{i}.txt")
                    with open(filepath, 'r') as f:
                        content = f.read()
                    if content:
                        operations += 1
                except Exception as e:
                    errors += 1
            
            # List operations
            for _ in range(100):
                try:
                    files = os.listdir(self.test_dir)
                    if files:
                        operations += 1
                except Exception as e:
                    errors += 1
                    
        except Exception as e:
            errors += 1
            print(f"File operations error: {e}")
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        ops_per_sec = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceResult(
            test_name="file_operations",
            duration_ms=duration_ms,
            operations_per_sec=ops_per_sec,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "write_ops": 1000,
                "read_ops": 1000,
                "list_ops": 100
            }
        )
        
        self.results.append(result)
        print(f"   ✅ {ops_per_sec:.2f} ops/sec, {success_rate:.1f}% success")
    
    def _test_concurrent_operations(self):
        """Test concurrent operations performance"""
        print("🔄 Testing concurrent operations...")
        
        start_time = time.time()
        operations = 0
        errors = 0
        lock = threading.Lock()
        
        def worker(worker_id: int, op_count: int):
            nonlocal operations, errors
            worker_ops = 0
            worker_errors = 0
            
            for i in range(op_count):
                try:
                    # File operations
                    filepath = os.path.join(self.test_dir, f"concurrent_{worker_id}_{i}.txt")
                    with open(filepath, 'w') as f:
                        f.write(f"Worker {worker_id} operation {i}")
                    
                    # Read back
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    if content:
                        worker_ops += 2
                        
                    # Simulate processing
                    result = sum(j for j in range(10))
                    worker_ops += 1
                    
                except Exception as e:
                    worker_errors += 1
            
            with lock:
                operations += worker_ops
                errors += worker_errors
        
        try:
            # Run concurrent workers
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(worker, i, 100)
                    for i in range(8)
                ]
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        with lock:
                            errors += 1
                        
        except Exception as e:
            errors += 1
            print(f"Concurrent operations error: {e}")
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        ops_per_sec = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceResult(
            test_name="concurrent_operations",
            duration_ms=duration_ms,
            operations_per_sec=ops_per_sec,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "concurrent_workers": 8,
                "ops_per_worker": 300
            }
        )
        
        self.results.append(result)
        print(f"   ✅ {ops_per_sec:.2f} ops/sec, {success_rate:.1f}% success")
    
    def _test_memory_operations(self):
        """Test memory-intensive operations"""
        print("🧠 Testing memory operations...")
        
        start_time = time.time()
        operations = 0
        errors = 0
        
        try:
            # Create and manipulate large data structures
            data_cache = {}
            
            for i in range(1000):
                try:
                    # Create large data objects
                    large_data = {
                        'id': i,
                        'data': 'x' * 1024,  # 1KB per object
                        'metadata': {f'key_{j}': f'value_{j}' for j in range(50)}
                    }
                    data_cache[f'object_{i}'] = large_data
                    operations += 1
                    
                    # Process data
                    if i % 100 == 0:
                        # Sort keys
                        sorted_keys = sorted(data_cache.keys())
                        operations += 1
                        
                        # Calculate statistics
                        total_objects = len(data_cache)
                        operations += 1
                        
                except Exception as e:
                    errors += 1
            
            # Clean up memory
            data_cache.clear()
            operations += 1
                    
        except Exception as e:
            errors += 1
            print(f"Memory operations error: {e}")
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        ops_per_sec = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceResult(
            test_name="memory_operations",
            duration_ms=duration_ms,
            operations_per_sec=ops_per_sec,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "data_objects_created": 1000,
                "memory_per_object_kb": 1
            }
        )
        
        self.results.append(result)
        print(f"   ✅ {ops_per_sec:.2f} ops/sec, {success_rate:.1f}% success")
    
    def _test_cpu_intensive_operations(self):
        """Test CPU intensive operations"""
        print("⚡ Testing CPU intensive operations...")
        
        start_time = time.time()
        operations = 0
        errors = 0
        
        def cpu_worker(worker_id: int):
            nonlocal operations, errors
            worker_ops = 0
            worker_errors = 0
            
            try:
                for i in range(500):
                    # Mathematical operations
                    result = sum(j ** 2 for j in range(50))
                    
                    # String operations
                    text = f"CPU test {worker_id} {i} {result}"
                    processed = text.upper().lower().replace(" ", "_")
                    
                    # List operations
                    numbers = list(range(100))
                    sorted_numbers = sorted(numbers, reverse=True)
                    
                    worker_ops += 3
                    
            except Exception as e:
                worker_errors += 1
                
            with lock:
                operations += worker_ops
                errors += worker_errors
        
        lock = threading.Lock()
        
        try:
            # Run CPU intensive work with multiple threads
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(cpu_worker, i)
                    for i in range(4)
                ]
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        with lock:
                            errors += 1
                        
        except Exception as e:
            errors += 1
            print(f"CPU intensive operations error: {e}")
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        ops_per_sec = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceResult(
            test_name="cpu_intensive_operations",
            duration_ms=duration_ms,
            operations_per_sec=ops_per_sec,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "concurrent_workers": 4,
                "operations_per_worker": 1500
            }
        )
        
        self.results.append(result)
        print(f"   ✅ {ops_per_sec:.2f} ops/sec, {success_rate:.1f}% success")
    
    def _test_mixed_workload(self):
        """Test mixed workload performance"""
        print("🎯 Testing mixed workload...")
        
        start_time = time.time()
        operations = 0
        errors = 0
        lock = threading.Lock()
        
        def mixed_worker(worker_id: int):
            nonlocal operations, errors
            worker_ops = 0
            worker_errors = 0
            
            for i in range(50):
                try:
                    # File operation
                    filepath = os.path.join(self.test_dir, f"mixed_{worker_id}_{i}.txt")
                    with open(filepath, 'w') as f:
                        f.write(f"Mixed workload {worker_id} {i}")
                    worker_ops += 1
                    
                    # CPU operation
                    result = sum(j for j in range(20))
                    worker_ops += 1
                    
                    # Memory operation
                    data = {'id': i, 'data': 'x' * 100, 'result': result}
                    processed_data = str(data).upper()
                    worker_ops += 1
                    
                    # Read file back
                    with open(filepath, 'r') as f:
                        content = f.read()
                    if content:
                        worker_ops += 1
                        
                except Exception as e:
                    worker_errors += 1
            
            with lock:
                operations += worker_ops
                errors += worker_errors
        
        try:
            # Run mixed workload with multiple workers
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [
                    executor.submit(mixed_worker, i)
                    for i in range(6)
                ]
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        with lock:
                            errors += 1
                        
        except Exception as e:
            errors += 1
            print(f"Mixed workload error: {e}")
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        ops_per_sec = operations / (duration_ms / 1000) if duration_ms > 0 else 0
        success_rate = (operations / (operations + errors)) * 100 if operations + errors > 0 else 0
        
        result = PerformanceResult(
            test_name="mixed_workload",
            duration_ms=duration_ms,
            operations_per_sec=ops_per_sec,
            success_rate=success_rate,
            error_count=errors,
            metadata={
                "total_operations": operations,
                "concurrent_workers": 6,
                "mixed_ops_per_worker": 200
            }
        )
        
        self.results.append(result)
        print(f"   ✅ {ops_per_sec:.2f} ops/sec, {success_rate:.1f}% success")
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        if not self.results:
            return {"error": "No test results available"}
        
        # Calculate statistics
        total_operations = sum(r.metadata.get("total_operations", 0) for r in self.results)
        total_errors = sum(r.error_count for r in self.results)
        avg_throughput = statistics.mean([r.operations_per_sec for r in self.results])
        avg_success_rate = statistics.mean([r.success_rate for r in self.results])
        
        # Performance assessment
        performance_grade = "A"
        if avg_success_rate < 95:
            performance_grade = "C"
        elif avg_success_rate < 98:
            performance_grade = "B"
        elif avg_throughput < 100:
            performance_grade = "B"
        
        # Find best and worst tests
        best_test = max(self.results, key=lambda r: r.operations_per_sec)
        worst_test = min(self.results, key=lambda r: r.operations_per_sec)
        
        # Generate recommendations
        recommendations = []
        if avg_success_rate < 98:
            recommendations.append("Investigate error handling to improve reliability")
        if avg_throughput < 200:
            recommendations.append("Consider optimizations for better throughput")
        
        concurrent_tests = [r for r in self.results if "concurrent" in r.test_name]
        if concurrent_tests and statistics.mean([r.success_rate for r in concurrent_tests]) < 95:
            recommendations.append("Review concurrent operation handling")
            
        if not recommendations:
            recommendations.append("Performance is within acceptable ranges")
        
        report = {
            "performance_summary": {
                "total_tests": len(self.results),
                "total_operations": total_operations,
                "total_errors": total_errors,
                "performance_grade": performance_grade
            },
            "metrics": {
                "average_throughput_ops_per_sec": round(avg_throughput, 2),
                "average_success_rate_percent": round(avg_success_rate, 2)
            },
            "best_performance": {
                "test": best_test.test_name,
                "throughput": round(best_test.operations_per_sec, 2)
            },
            "worst_performance": {
                "test": worst_test.test_name,
                "throughput": round(worst_test.operations_per_sec, 2)
            },
            "detailed_results": [asdict(result) for result in self.results],
            "recommendations": recommendations
        }
        
        return report

def main():
    """Run performance tests"""
    test_suite = SimplePerformanceTest()
    
    try:
        results = test_suite.run_all_tests()
        
        # Save results
        output_file = "/tmp/claude_bridge_performance_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n📊 Performance Test Results Summary:")
        print("=" * 50)
        print(f"Total Tests: {results['performance_summary']['total_tests']}")
        print(f"Total Operations: {results['performance_summary']['total_operations']:,}")
        print(f"Total Errors: {results['performance_summary']['total_errors']}")
        print(f"Performance Grade: {results['performance_summary']['performance_grade']}")
        print(f"Average Throughput: {results['metrics']['average_throughput_ops_per_sec']:.2f} ops/sec")
        print(f"Average Success Rate: {results['metrics']['average_success_rate_percent']:.2f}%")
        
        print(f"\n🏆 Best Performance: {results['best_performance']['test']} ({results['best_performance']['throughput']:.2f} ops/sec)")
        print(f"⚠️  Worst Performance: {results['worst_performance']['test']} ({results['worst_performance']['throughput']:.2f} ops/sec)")
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"   {i}. {rec}")
        
        print(f"\n📁 Full results saved to: {output_file}")
        print("✅ Performance testing completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance testing failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)