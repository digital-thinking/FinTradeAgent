"""Rate limiting middleware for production API protection."""

import time
import json
import hashlib
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import redis.asyncio as aioredis


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiting middleware with Redis backend."""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 100,
        burst_limit: Optional[int] = None,
        storage_url: str = "redis://localhost:6379/1",
        key_prefix: str = "rate_limit:",
        whitelist_ips: Optional[list] = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit or requests_per_minute * 2
        self.storage_url = storage_url
        self.key_prefix = key_prefix
        self.whitelist_ips = whitelist_ips or []
        self._redis_pool = None
    
    async def get_redis(self):
        """Get Redis connection pool."""
        if self._redis_pool is None:
            self._redis_pool = aioredis.from_url(
                self.storage_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis_pool
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting logic."""
        
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Check if IP is whitelisted
        if client_id in self.whitelist_ips:
            return await call_next(request)
        
        # Check rate limit
        allowed, remaining, reset_time = await self._check_rate_limit(client_id)
        
        if not allowed:
            return self._create_rate_limit_response(remaining, reset_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Try to get real IP from proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Include user agent for more granular limiting
        user_agent = request.headers.get("user-agent", "")
        
        # Create hash of IP + user agent for privacy
        identifier = f"{client_ip}:{user_agent}"
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]
    
    async def _check_rate_limit(self, client_id: str) -> tuple[bool, int, int]:
        """Check if request is within rate limit using sliding window."""
        redis = await self.get_redis()
        key = f"{self.key_prefix}{client_id}"
        now = int(time.time())
        window = 60  # 1 minute window
        
        try:
            async with redis.pipeline() as pipe:
                # Remove entries older than the window
                pipe.zremrangebyscore(key, 0, now - window)
                
                # Count current requests in window
                pipe.zcard(key)
                
                # Add current request
                pipe.zadd(key, {str(now): now})
                
                # Set expiry
                pipe.expire(key, window)
                
                results = await pipe.execute()
                
                current_count = results[1]
                
                # Check if limit is exceeded
                allowed = current_count < self.requests_per_minute
                remaining = max(0, self.requests_per_minute - current_count - 1)
                reset_time = now + window
                
                return allowed, remaining, reset_time
                
        except Exception as e:
            # If Redis fails, allow the request but log the error
            print(f"Rate limiter error: {e}")
            return True, self.requests_per_minute, now + 60
    
    def _create_rate_limit_response(self, remaining: int, reset_time: int) -> JSONResponse:
        """Create rate limit exceeded response."""
        return JSONResponse(
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {self.requests_per_minute}/minute",
                "retry_after": reset_time - int(time.time()),
                "remaining": remaining
            },
            status_code=429,
            headers={
                "Retry-After": str(reset_time - int(time.time())),
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time)
            }
        )
    
    async def cleanup(self):
        """Cleanup Redis connections."""
        if self._redis_pool:
            await self._redis_pool.close()


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware to whitelist specific IP addresses for unlimited access."""
    
    def __init__(self, app, whitelist_ips: list):
        super().__init__(app)
        self.whitelist_ips = set(whitelist_ips)
    
    async def dispatch(self, request: Request, call_next):
        """Check if IP is whitelisted."""
        client_ip = self._get_client_ip(request)
        
        # Add to request state for other middleware to use
        request.state.is_whitelisted = client_ip in self.whitelist_ips
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"