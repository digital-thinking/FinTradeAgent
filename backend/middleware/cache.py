"""Caching middleware for FastAPI with Redis-like in-memory cache."""

import time
import json
import hashlib
from typing import Dict, Any, Optional, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

class InMemoryCache:
    """In-memory cache with TTL and LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        
        # Check TTL
        if entry['expires'] < time.time():
            self.delete(key)
            return None
            
        # Update access time for LRU
        self.access_times[key] = time.time()
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        if len(self.cache) >= self.max_size:
            self._evict_lru()
            
        expires = time.time() + (ttl or self.default_ttl)
        self.cache[key] = {
            'value': value,
            'expires': expires,
            'created': time.time()
        }
        self.access_times[key] = time.time()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.access_times.clear()
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self.access_times:
            return
            
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self.delete(lru_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        active_entries = sum(1 for entry in self.cache.values() if entry['expires'] > current_time)
        
        return {
            'total_entries': len(self.cache),
            'active_entries': active_entries,
            'expired_entries': len(self.cache) - active_entries,
            'max_size': self.max_size,
            'memory_usage_estimate': len(str(self.cache))  # Rough estimate
        }


class CacheMiddleware(BaseHTTPMiddleware):
    """HTTP response caching middleware."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.cache = InMemoryCache(max_size=1000, default_ttl=300)  # 5 minutes default
        
        # Cache configuration for different endpoints
        self.cache_config = {
            # Analytics endpoints (cache longer)
            '/api/analytics/dashboard': {'ttl': 60, 'vary_by': ['user', 'timeframe']},
            '/api/analytics/execution-logs': {'ttl': 30, 'vary_by': ['user', 'limit', 'offset']},
            
            # Portfolio endpoints (medium cache)
            '/api/portfolios': {'ttl': 120, 'vary_by': ['user']},
            '/api/portfolios/{name}': {'ttl': 60, 'vary_by': ['user']},
            
            # System endpoints (short cache)
            '/api/system/health': {'ttl': 30, 'vary_by': []},
            '/api/system/scheduler': {'ttl': 15, 'vary_by': []},
            
            # Trades endpoints (very short cache due to real-time nature)
            '/api/trades/pending': {'ttl': 10, 'vary_by': ['user']},
        }
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with caching logic."""
        # Only cache GET requests
        if request.method != 'GET':
            return await call_next(request)
        
        # Check if endpoint should be cached
        cache_config = self._get_cache_config(request.url.path)
        if not cache_config:
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request, cache_config)
        
        # Try to get from cache
        cached_response = self.cache.get(cache_key)
        if cached_response:
            self.stats['hits'] += 1
            return self._create_response_from_cache(cached_response)
        
        # Cache miss - process request
        self.stats['misses'] += 1
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            await self._cache_response(cache_key, response, cache_config['ttl'])
        
        return response
    
    def _get_cache_config(self, path: str) -> Optional[Dict[str, Any]]:
        """Get cache configuration for path."""
        # Exact match
        if path in self.cache_config:
            return self.cache_config[path]
        
        # Pattern matching for dynamic paths
        for pattern, config in self.cache_config.items():
            if '{' in pattern:
                # Simple pattern matching for paths like /api/portfolios/{name}
                pattern_parts = pattern.split('/')
                path_parts = path.split('/')
                
                if len(pattern_parts) == len(path_parts):
                    match = True
                    for i, (pattern_part, path_part) in enumerate(zip(pattern_parts, path_parts)):
                        if pattern_part != path_part and not pattern_part.startswith('{'):
                            match = False
                            break
                    
                    if match:
                        return config
        
        return None
    
    def _generate_cache_key(self, request: Request, config: Dict[str, Any]) -> str:
        """Generate cache key based on request and config."""
        key_parts = [request.url.path]
        
        # Add query parameters
        if request.query_params:
            key_parts.append(str(sorted(request.query_params.items())))
        
        # Add vary_by parameters from headers/context
        vary_by = config.get('vary_by', [])
        for param in vary_by:
            if param == 'user':
                # In a real app, extract user ID from auth token
                user_id = request.headers.get('X-User-ID', 'anonymous')
                key_parts.append(f"user:{user_id}")
            elif param in request.query_params:
                key_parts.append(f"{param}:{request.query_params[param]}")
        
        # Generate hash
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _cache_response(self, cache_key: str, response: Response, ttl: int) -> None:
        """Cache response data."""
        try:
            # Read response body
            body = b''
            async for chunk in response.body_iterator:
                body += chunk
            
            # Create cached response data
            cached_data = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': body.decode('utf-8') if body else '',
                'content_type': response.headers.get('content-type', 'application/json')
            }
            
            # Store in cache
            self.cache.set(cache_key, cached_data, ttl)
            self.stats['sets'] += 1
            
            # Recreate response with original body
            response.body_iterator = self._iterate_body(body)
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"Cache error: {e}")
    
    def _create_response_from_cache(self, cached_data: Dict[str, Any]) -> Response:
        """Create Response object from cached data."""
        headers = cached_data['headers'].copy()
        headers['X-Cache'] = 'HIT'
        headers['X-Cache-Timestamp'] = str(int(time.time()))
        
        return Response(
            content=cached_data['body'],
            status_code=cached_data['status_code'],
            headers=headers,
            media_type=cached_data['content_type']
        )
    
    async def _iterate_body(self, body: bytes):
        """Create async iterator for response body."""
        yield body
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        invalidated = 0
        keys_to_delete = []
        
        for key in self.cache.cache.keys():
            if pattern in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            if self.cache.delete(key):
                invalidated += 1
        
        return invalidated
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'requests': {
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'total': total_requests,
                'hit_rate_percent': round(hit_rate, 2)
            },
            'operations': {
                'sets': self.stats['sets'],
                'errors': self.stats['errors']
            },
            'cache': self.cache.get_stats()
        }


class CacheManager:
    """Cache management utilities."""
    
    def __init__(self, middleware: CacheMiddleware):
        self.middleware = middleware
    
    def warm_up_cache(self, endpoints: list) -> None:
        """Pre-warm cache with common requests."""
        # Implementation would make requests to common endpoints
        pass
    
    def schedule_cleanup(self) -> None:
        """Schedule periodic cache cleanup."""
        # Implementation would run periodic cleanup tasks
        pass
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        return {
            **self.middleware.get_stats(),
            'configuration': {
                'max_size': self.middleware.cache.max_size,
                'default_ttl': self.middleware.cache.default_ttl,
                'cached_endpoints': list(self.middleware.cache_config.keys())
            }
        }