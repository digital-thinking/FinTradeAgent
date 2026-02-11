"""Caching module for market data and other external API responses."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional


class CacheService:
    """Service for caching market data and API responses."""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = 3600  # 1 hour in seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value by key."""
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            if cache_data.get('expires_at', 0) < time.time():
                # Remove expired cache
                cache_file.unlink()
                return None
                
            return cache_data.get('value')
        except (json.JSONDecodeError, KeyError, IOError):
            # Remove corrupted cache file
            if cache_file.exists():
                cache_file.unlink()
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        cache_file = self.cache_dir / f"{key}.json"
        
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        
        cache_data = {
            'value': value,
            'expires_at': expires_at,
            'cached_at': time.time()
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except IOError:
            # Ignore cache write errors
            pass
    
    def delete(self, key: str) -> None:
        """Delete cached value by key."""
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            cache_file.unlink()
    
    def clear_all(self) -> None:
        """Clear all cached values."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries and return count of removed items."""
        removed_count = 0
        current_time = time.time()
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    
                if cache_data.get('expires_at', 0) < current_time:
                    cache_file.unlink()
                    removed_count += 1
            except (json.JSONDecodeError, KeyError, IOError):
                # Remove corrupted files too
                cache_file.unlink()
                removed_count += 1
                
        return removed_count


# Global cache service instance
_cache_service = None


def get_cache_service() -> CacheService:
    """Get the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def cache_market_data(ticker: str, data: Dict[str, Any], ttl: int = 300) -> None:
    """Cache market data for a ticker (5 minute default TTL)."""
    cache_key = f"market_data_{ticker}"
    get_cache_service().set(cache_key, data, ttl)


def get_cached_market_data(ticker: str) -> Optional[Dict[str, Any]]:
    """Get cached market data for a ticker."""
    cache_key = f"market_data_{ticker}"
    return get_cache_service().get(cache_key)