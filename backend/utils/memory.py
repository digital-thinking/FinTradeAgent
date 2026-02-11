"""Memory optimization utilities for FinTradeAgent."""

import gc
import psutil
import sys
import threading
import time
import weakref
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class MemoryStats:
    """Memory statistics container."""
    total_memory: int
    available_memory: int
    used_memory: int
    memory_percent: float
    process_memory: int
    gc_collections: Dict[int, int]
    large_objects: int
    
class MemoryOptimizer:
    """Memory usage optimization and monitoring."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = self.process.memory_info().rss
        self.memory_history = []
        self.large_objects: Set[weakref.ref] = set()
        self.memory_pools = defaultdict(list)
        self.gc_stats = {0: 0, 1: 0, 2: 0}
        self.monitoring_enabled = False
        self.monitoring_thread = None
        self._lock = threading.Lock()
        
    @classmethod
    def initialize(cls) -> 'MemoryOptimizer':
        """Initialize memory optimizer."""
        instance = cls()
        instance.start_monitoring()
        return instance
    
    def start_monitoring(self):
        """Start memory monitoring thread."""
        if self.monitoring_enabled:
            return
            
        self.monitoring_enabled = True
        self.monitoring_thread = threading.Thread(target=self._monitor_memory)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        print("🧠 Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring thread."""
        self.monitoring_enabled = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=1)
        print("🧠 Memory monitoring stopped")
    
    def _monitor_memory(self):
        """Background memory monitoring loop."""
        while self.monitoring_enabled:
            try:
                with self._lock:
                    stats = self._collect_stats()
                    self.memory_history.append({
                        'timestamp': time.time(),
                        'stats': stats
                    })
                    
                    # Keep only last 100 measurements
                    if len(self.memory_history) > 100:
                        self.memory_history = self.memory_history[-100:]
                    
                    # Check for memory issues
                    self._check_memory_alerts(stats)
                
                time.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                print(f"Memory monitoring error: {e}")
                time.sleep(60)  # Wait longer if error occurred
    
    def _collect_stats(self) -> MemoryStats:
        """Collect current memory statistics."""
        # System memory
        system_memory = psutil.virtual_memory()
        
        # Process memory
        process_memory = self.process.memory_info().rss
        
        # Garbage collection stats
        gc_stats = {}
        for generation in range(3):
            gc_stats[generation] = gc.get_count()[generation]
        
        # Count large objects
        large_objects = 0
        for obj in gc.get_objects():
            try:
                if hasattr(obj, '__sizeof__') and obj.__sizeof__() > 1024*1024:  # > 1MB
                    large_objects += 1
            except (TypeError, AttributeError):
                # Skip objects that can't be sized
                pass
        
        return MemoryStats(
            total_memory=system_memory.total,
            available_memory=system_memory.available,
            used_memory=system_memory.used,
            memory_percent=system_memory.percent,
            process_memory=process_memory,
            gc_collections=gc_stats,
            large_objects=large_objects
        )
    
    def _check_memory_alerts(self, stats: MemoryStats):
        """Check for memory usage alerts."""
        # High system memory usage
        if stats.memory_percent > 85:
            print(f"⚠️ High system memory usage: {stats.memory_percent:.1f}%")
            self.trigger_cleanup()
        
        # High process memory growth
        memory_growth = stats.process_memory - self.baseline_memory
        if memory_growth > 500 * 1024 * 1024:  # 500MB growth
            print(f"⚠️ Process memory grew by {memory_growth / (1024*1024):.1f}MB")
        
        # Too many large objects
        if stats.large_objects > 100:
            print(f"⚠️ High number of large objects: {stats.large_objects}")
    
    def trigger_cleanup(self, force: bool = False):
        """Trigger memory cleanup operations."""
        print("🧹 Starting memory cleanup...")
        
        initial_memory = self.process.memory_info().rss
        
        # Force garbage collection
        collected_objects = []
        for generation in range(3):
            collected = gc.collect(generation)
            collected_objects.append(collected)
        
        # Clear weak references to dead objects
        self._cleanup_weak_references()
        
        # Clear memory pools
        self._clear_memory_pools()
        
        # Compact memory (Python-specific optimizations)
        self._compact_memory()
        
        final_memory = self.process.memory_info().rss
        memory_freed = initial_memory - final_memory
        
        print(f"🧹 Memory cleanup complete: freed {memory_freed / (1024*1024):.2f}MB")
        print(f"   - GC collected: {sum(collected_objects)} objects")
        
        return memory_freed
    
    def _cleanup_weak_references(self):
        """Clean up dead weak references."""
        dead_refs = [ref for ref in self.large_objects if ref() is None]
        for ref in dead_refs:
            self.large_objects.discard(ref)
    
    def _clear_memory_pools(self):
        """Clear custom memory pools."""
        cleared_pools = 0
        for pool_name, pool in self.memory_pools.items():
            if len(pool) > 100:  # Only clear large pools
                pool.clear()
                cleared_pools += 1
        
        if cleared_pools > 0:
            print(f"🧹 Cleared {cleared_pools} memory pools")
    
    def _compact_memory(self):
        """Attempt to compact memory allocations."""
        # Force string interning cleanup
        sys.intern("dummy_string_for_cleanup")
        
        # Clear import caches
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()
    
    def register_large_object(self, obj: Any, name: str = "unknown"):
        """Register a large object for monitoring."""
        try:
            if hasattr(obj, '__sizeof__') and obj.__sizeof__() > 1024*1024:  # > 1MB
                ref = weakref.ref(obj)
                self.large_objects.add(ref)
                print(f"📊 Registered large object: {name} ({obj.__sizeof__() / (1024*1024):.2f}MB)")
        except (TypeError, AttributeError):
            # Skip objects that can't be sized
            pass
    
    def add_to_pool(self, pool_name: str, obj: Any):
        """Add object to a named memory pool."""
        self.memory_pools[pool_name].append(obj)
    
    def get_pool(self, pool_name: str) -> List[Any]:
        """Get objects from a named memory pool."""
        return self.memory_pools[pool_name]
    
    def clear_pool(self, pool_name: str) -> int:
        """Clear a specific memory pool."""
        pool = self.memory_pools[pool_name]
        count = len(pool)
        pool.clear()
        return count
    
    def _get_stats_impl(self) -> Dict[str, Any]:
        """Get basic memory statistics."""
        current_stats = self._collect_stats()
        
        return {
            'process_memory_mb': round(current_stats.process_memory / (1024*1024), 2),
            'system_memory_percent': current_stats.memory_percent,
            'memory_growth_mb': round(
                (current_stats.process_memory - self.baseline_memory) / (1024*1024), 2
            ),
            'large_objects': current_stats.large_objects,
            'gc_objects': sum(current_stats.gc_collections.values())
        }
    
    def _get_detailed_stats_impl(self) -> Dict[str, Any]:
        """Get detailed memory statistics."""
        current_stats = self._collect_stats()
        
        # Calculate memory trends
        memory_trend = self._calculate_memory_trend()
        
        return {
            'current': {
                'process_memory_mb': round(current_stats.process_memory / (1024*1024), 2),
                'system_total_gb': round(current_stats.total_memory / (1024*1024*1024), 2),
                'system_available_gb': round(current_stats.available_memory / (1024*1024*1024), 2),
                'system_used_percent': current_stats.memory_percent
            },
            'trends': memory_trend,
            'garbage_collection': {
                'generation_0': current_stats.gc_collections[0],
                'generation_1': current_stats.gc_collections[1],
                'generation_2': current_stats.gc_collections[2]
            },
            'objects': {
                'large_objects': current_stats.large_objects,
                'tracked_objects': len(self.large_objects),
                'memory_pools': {name: len(pool) for name, pool in self.memory_pools.items()}
            },
            'monitoring': {
                'baseline_memory_mb': round(self.baseline_memory / (1024*1024), 2),
                'growth_mb': round(
                    (current_stats.process_memory - self.baseline_memory) / (1024*1024), 2
                ),
                'history_points': len(self.memory_history)
            }
        }
    
    def _calculate_memory_trend(self) -> Dict[str, Any]:
        """Calculate memory usage trends."""
        if len(self.memory_history) < 2:
            return {'trend': 'insufficient_data'}
        
        recent_points = self.memory_history[-10:]  # Last 10 measurements
        memory_values = [point['stats'].process_memory for point in recent_points]
        
        if len(memory_values) >= 2:
            trend_direction = 'increasing' if memory_values[-1] > memory_values[0] else 'decreasing'
            avg_memory = sum(memory_values) / len(memory_values)
            
            return {
                'trend': trend_direction,
                'avg_memory_mb': round(avg_memory / (1024*1024), 2),
                'min_memory_mb': round(min(memory_values) / (1024*1024), 2),
                'max_memory_mb': round(max(memory_values) / (1024*1024), 2),
                'data_points': len(memory_values)
            }
        
        return {'trend': 'stable'}
    
    def get_top_memory_consumers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top memory consuming objects."""
        # This is a simplified implementation
        # In a real scenario, you'd use more sophisticated profiling
        
        consumers = []
        for obj in gc.get_objects():
            try:
                if hasattr(obj, '__sizeof__'):
                    size = obj.__sizeof__()
                    if size > 100*1024:  # Objects > 100KB
                        consumers.append({
                            'type': type(obj).__name__,
                            'size_mb': round(size / (1024*1024), 3),
                            'id': id(obj)
                        })
            except (TypeError, AttributeError):
                # Skip objects that can't be sized
                pass
        
        # Sort by size and return top consumers
        consumers.sort(key=lambda x: x['size_mb'], reverse=True)
        return consumers[:limit]
    
    @classmethod  
    def get_stats(cls) -> Dict[str, Any]:
        """Class method to get stats from global instance."""
        global memory_optimizer
        if memory_optimizer is None:
            memory_optimizer = cls.initialize()
        # Call the instance method directly without recursion
        return memory_optimizer._get_stats_impl()
    
    @classmethod
    def get_detailed_stats(cls) -> Dict[str, Any]:
        """Class method to get detailed stats from global instance."""  
        global memory_optimizer
        if memory_optimizer is None:
            memory_optimizer = cls.initialize()
        # Call the instance method directly without recursion 
        return memory_optimizer._get_detailed_stats_impl()
    
    @classmethod
    def cleanup(cls):
        """Global cleanup method."""
        # Force final garbage collection
        for generation in range(3):
            gc.collect(generation)
        
        print("🧹 Final memory cleanup completed")


# Global memory optimizer instance
memory_optimizer = None

def get_memory_optimizer() -> MemoryOptimizer:
    """Get or create memory optimizer instance."""
    global memory_optimizer
    if memory_optimizer is None:
        memory_optimizer = MemoryOptimizer.initialize()
    return memory_optimizer

# Context manager for memory monitoring
class MemoryMonitor:
    """Context manager for monitoring memory usage of code blocks."""
    
    def __init__(self, name: str = "operation", alert_threshold_mb: int = 50):
        self.name = name
        self.alert_threshold = alert_threshold_mb * 1024 * 1024  # Convert to bytes
        self.start_memory = 0
        self.optimizer = get_memory_optimizer()
    
    def __enter__(self):
        self.start_memory = self.optimizer.process.memory_info().rss
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_memory = self.optimizer.process.memory_info().rss
        memory_delta = end_memory - self.start_memory
        
        if memory_delta > self.alert_threshold:
            print(f"⚠️ High memory usage in {self.name}: {memory_delta / (1024*1024):.2f}MB")
        
        return False