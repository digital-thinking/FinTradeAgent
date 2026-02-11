"""Database optimization utilities for FinTradeAgent."""

import asyncio
import time
import sqlite3
import threading
from typing import Dict, Any, Optional, List, Tuple
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

class DatabaseOptimizer:
    """Database connection and query optimization."""
    
    def __init__(self):
        self.connection_pool = None
        self.pool_size = 5
        self.query_cache = {}
        self.query_stats = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._lock = threading.Lock()
        
    @classmethod
    async def initialize_pool(cls):
        """Initialize database connection pool."""
        instance = cls()
        await instance._create_pool()
        return instance
    
    async def _create_pool(self):
        """Create database connection pool."""
        self.connection_pool = []
        
        for i in range(self.pool_size):
            # In a real implementation, this would create actual DB connections
            # For now, we'll simulate with a basic structure
            connection = {
                'id': i,
                'in_use': False,
                'created_at': time.time(),
                'last_used': time.time(),
                'queries_executed': 0
            }
            self.connection_pool.append(connection)
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool."""
        connection = None
        
        # Find available connection
        with self._lock:
            for conn in self.connection_pool:
                if not conn['in_use']:
                    conn['in_use'] = True
                    conn['last_used'] = time.time()
                    connection = conn
                    break
        
        if not connection:
            # All connections busy, wait and retry
            await asyncio.sleep(0.01)
            async with self.get_connection() as conn:
                yield conn
                return
        
        try:
            yield connection
        finally:
            with self._lock:
                connection['in_use'] = False
    
    async def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute optimized database query."""
        query_hash = hash(f"{query}:{params}")
        
        # Check query cache for read queries
        if query.strip().upper().startswith('SELECT'):
            cached_result = self.query_cache.get(query_hash)
            if cached_result and time.time() - cached_result['timestamp'] < 300:  # 5 min cache
                return cached_result['data']
        
        # Execute query
        start_time = time.time()
        
        async with self.get_connection() as conn:
            # Simulate query execution (in real implementation, use actual DB)
            result = await self._simulate_query_execution(query, params)
            
            conn['queries_executed'] += 1
            execution_time = time.time() - start_time
            
            # Update query statistics
            self._update_query_stats(query, execution_time)
            
            # Cache read queries
            if query.strip().upper().startswith('SELECT'):
                self.query_cache[query_hash] = {
                    'data': result,
                    'timestamp': time.time()
                }
            
            return result
    
    async def _simulate_query_execution(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Simulate query execution (replace with real DB logic)."""
        # Simulate processing time
        await asyncio.sleep(0.001)  # 1ms simulation
        
        # Return mock data based on query type
        if 'portfolios' in query.lower():
            return [
                {'id': 1, 'name': 'Tech Portfolio', 'value': 50000},
                {'id': 2, 'name': 'Growth Portfolio', 'value': 75000}
            ]
        elif 'trades' in query.lower():
            return [
                {'id': 1, 'symbol': 'AAPL', 'quantity': 10, 'price': 150.00},
                {'id': 2, 'symbol': 'GOOGL', 'quantity': 5, 'price': 2800.00}
            ]
        else:
            return []
    
    def _update_query_stats(self, query: str, execution_time: float):
        """Update query performance statistics."""
        query_type = query.strip().split()[0].upper()
        
        if query_type not in self.query_stats:
            self.query_stats[query_type] = {
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'slow_queries': 0
            }
        
        stats = self.query_stats[query_type]
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['min_time'] = min(stats['min_time'], execution_time)
        stats['max_time'] = max(stats['max_time'], execution_time)
        
        if execution_time > 0.1:  # Queries slower than 100ms
            stats['slow_queries'] += 1
    
    async def optimize_queries(self):
        """Analyze and optimize slow queries."""
        slow_queries = []
        
        for query_type, stats in self.query_stats.items():
            if stats['avg_time'] > 0.05:  # Average time > 50ms
                slow_queries.append({
                    'type': query_type,
                    'avg_time': stats['avg_time'],
                    'count': stats['count'],
                    'slow_count': stats['slow_queries']
                })
        
        if slow_queries:
            print("Slow queries detected:")
            for sq in slow_queries:
                print(f"  {sq['type']}: {sq['avg_time']:.4f}s avg ({sq['slow_count']}/{sq['count']} slow)")
        
        return slow_queries
    
    def clear_cache(self):
        """Clear query cache."""
        self.query_cache.clear()
        print("Database query cache cleared")
    
    async def _get_stats_impl(self) -> Dict[str, Any]:
        """Get database performance statistics."""
        if not self.connection_pool:
            return {'status': 'not_initialized'}
        
        active_connections = sum(1 for conn in self.connection_pool if conn['in_use'])
        total_queries = sum(conn['queries_executed'] for conn in self.connection_pool)
        
        return {
            'connections': {
                'pool_size': self.pool_size,
                'active': active_connections,
                'available': self.pool_size - active_connections
            },
            'queries': {
                'total_executed': total_queries,
                'cached_queries': len(self.query_cache)
            },
            'performance': {
                'avg_query_time': self._calculate_avg_query_time(),
                'cache_hit_rate': self._calculate_cache_hit_rate()
            }
        }
    
    async def _get_detailed_stats_impl(self) -> Dict[str, Any]:
        """Get detailed database statistics."""
        basic_stats = await self._get_stats_impl()
        
        return {
            **basic_stats,
            'query_stats': self.query_stats,
            'connection_details': [
                {
                    'id': conn['id'],
                    'in_use': conn['in_use'],
                    'queries_executed': conn['queries_executed'],
                    'age_seconds': time.time() - conn['created_at'],
                    'idle_seconds': time.time() - conn['last_used']
                }
                for conn in self.connection_pool
            ] if self.connection_pool else []
        }
    
    def _calculate_avg_query_time(self) -> float:
        """Calculate average query execution time."""
        if not self.query_stats:
            return 0.0
        
        total_time = sum(stats['total_time'] for stats in self.query_stats.values())
        total_queries = sum(stats['count'] for stats in self.query_stats.values())
        
        return total_time / total_queries if total_queries > 0 else 0.0
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        # Simplified calculation - in real implementation, track hits/misses
        return 85.0  # Mock value
    
    @classmethod
    async def get_stats(cls) -> Dict[str, Any]:
        """Class method to get stats from global instance."""
        global db_optimizer
        if db_optimizer is None:
            db_optimizer = await cls.initialize_pool()
        return await db_optimizer._get_stats_impl()
    
    @classmethod
    async def get_detailed_stats(cls) -> Dict[str, Any]:
        """Class method to get detailed stats from global instance."""
        global db_optimizer
        if db_optimizer is None:
            db_optimizer = await cls.initialize_pool()
        return await db_optimizer._get_detailed_stats_impl()
    
    @classmethod
    async def close_pool(cls):
        """Close database connection pool."""
        # In real implementation, properly close all connections
        print("Database connection pool closed")


class QueryBuilder:
    """SQL query builder with optimization hints."""
    
    def __init__(self):
        self.query_parts = []
        self.params = []
        self.optimization_hints = []
    
    def select(self, columns: str = "*") -> 'QueryBuilder':
        """Add SELECT clause."""
        self.query_parts.append(f"SELECT {columns}")
        return self
    
    def from_table(self, table: str) -> 'QueryBuilder':
        """Add FROM clause."""
        self.query_parts.append(f"FROM {table}")
        return self
    
    def where(self, condition: str, *params) -> 'QueryBuilder':
        """Add WHERE clause."""
        self.query_parts.append(f"WHERE {condition}")
        self.params.extend(params)
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """Add LIMIT clause."""
        self.query_parts.append(f"LIMIT {count}")
        self.optimization_hints.append("limited_result_set")
        return self
    
    def order_by(self, column: str, direction: str = "ASC") -> 'QueryBuilder':
        """Add ORDER BY clause."""
        self.query_parts.append(f"ORDER BY {column} {direction}")
        return self
    
    def join(self, table: str, condition: str) -> 'QueryBuilder':
        """Add JOIN clause."""
        self.query_parts.append(f"JOIN {table} ON {condition}")
        self.optimization_hints.append("requires_index")
        return self
    
    def build(self) -> Tuple[str, List]:
        """Build final query."""
        query = " ".join(self.query_parts)
        return query, self.params
    
    def explain(self) -> Dict[str, Any]:
        """Get query execution plan (mock)."""
        query, params = self.build()
        
        return {
            'query': query,
            'params': params,
            'estimated_cost': len(self.query_parts) * 10,  # Mock cost
            'optimization_hints': self.optimization_hints,
            'recommended_indexes': self._suggest_indexes()
        }
    
    def _suggest_indexes(self) -> List[str]:
        """Suggest database indexes for optimization."""
        suggestions = []
        query_lower = " ".join(self.query_parts).lower()
        
        if 'where' in query_lower:
            suggestions.append("Consider indexes on WHERE clause columns")
        
        if 'join' in query_lower:
            suggestions.append("Consider indexes on JOIN columns")
        
        if 'order by' in query_lower:
            suggestions.append("Consider indexes on ORDER BY columns")
        
        return suggestions


# Global database optimizer instance
db_optimizer = None

async def get_db_optimizer() -> DatabaseOptimizer:
    """Get or create database optimizer instance."""
    global db_optimizer
    if db_optimizer is None:
        db_optimizer = await DatabaseOptimizer.initialize_pool()
    return db_optimizer