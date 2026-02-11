"""Performance monitoring middleware for FastAPI."""

import time
import asyncio
import psutil
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring API performance and system resources."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.stats = {
            "requests": 0,
            "response_times": [],
            "slow_requests": [],
            "errors": 0,
            "endpoints": {},
            "methods": {},
            "status_codes": {}
        }
        
        # Performance thresholds
        self.slow_request_threshold = 1.0  # seconds
        self.max_response_times = 1000  # Keep last 1000 response times
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance monitoring."""
        start_time = time.time()
        start_cpu = psutil.cpu_percent()
        process = psutil.Process()
        start_memory = process.memory_info().rss
        
        # Request metadata
        method = request.method
        path = request.url.path
        endpoint_key = f"{method} {path}"
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate performance metrics
            end_time = time.time()
            response_time = end_time - start_time
            end_cpu = psutil.cpu_percent()
            end_memory = process.memory_info().rss
            
            # Update statistics
            await self._update_stats(
                endpoint_key, method, response.status_code, 
                response_time, start_cpu, end_cpu, 
                start_memory, end_memory
            )
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{response_time:.4f}"
            response.headers["X-CPU-Usage"] = f"{end_cpu:.2f}%"
            response.headers["X-Memory-Delta"] = f"{(end_memory - start_memory) / 1024:.2f}KB"
            
            # Log slow requests
            if response_time > self.slow_request_threshold:
                await self._log_slow_request(endpoint_key, response_time, request)
                
            return response
            
        except Exception as e:
            # Handle errors
            response_time = time.time() - start_time
            self.stats["errors"] += 1
            
            await self._log_error(endpoint_key, response_time, str(e))
            raise
    
    async def _update_stats(
        self, endpoint: str, method: str, status_code: int,
        response_time: float, start_cpu: float, end_cpu: float,
        start_memory: int, end_memory: int
    ):
        """Update performance statistics."""
        self.stats["requests"] += 1
        
        # Response times
        self.stats["response_times"].append(response_time)
        if len(self.stats["response_times"]) > self.max_response_times:
            self.stats["response_times"] = self.stats["response_times"][-self.max_response_times:]
        
        # Endpoint statistics
        if endpoint not in self.stats["endpoints"]:
            self.stats["endpoints"][endpoint] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
                "min_time": float('inf'),
                "max_time": 0,
                "errors": 0
            }
        
        endpoint_stats = self.stats["endpoints"][endpoint]
        endpoint_stats["count"] += 1
        endpoint_stats["total_time"] += response_time
        endpoint_stats["avg_time"] = endpoint_stats["total_time"] / endpoint_stats["count"]
        endpoint_stats["min_time"] = min(endpoint_stats["min_time"], response_time)
        endpoint_stats["max_time"] = max(endpoint_stats["max_time"], response_time)
        
        # Method statistics
        self.stats["methods"][method] = self.stats["methods"].get(method, 0) + 1
        
        # Status code statistics
        self.stats["status_codes"][status_code] = self.stats["status_codes"].get(status_code, 0) + 1
    
    async def _log_slow_request(self, endpoint: str, response_time: float, request: Request):
        """Log slow requests for optimization."""
        slow_request = {
            "endpoint": endpoint,
            "response_time": response_time,
            "timestamp": time.time(),
            "user_agent": request.headers.get("user-agent", ""),
            "query_params": str(request.query_params)
        }
        
        self.stats["slow_requests"].append(slow_request)
        
        # Keep only last 100 slow requests
        if len(self.stats["slow_requests"]) > 100:
            self.stats["slow_requests"] = self.stats["slow_requests"][-100:]
        
        print(f"Slow request: {endpoint} took {response_time:.4f}s")
    
    async def _log_error(self, endpoint: str, response_time: float, error: str):
        """Log request errors."""
        print(f"Error in {endpoint} after {response_time:.4f}s: {error}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        response_times = self.stats["response_times"]
        
        if not response_times:
            return self.stats
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        length = len(sorted_times)
        
        return {
            **self.stats,
            "summary": {
                "total_requests": self.stats["requests"],
                "error_rate": (self.stats["errors"] / max(self.stats["requests"], 1)) * 100,
                "avg_response_time": sum(response_times) / length,
                "p50_response_time": sorted_times[int(length * 0.5)] if length > 0 else 0,
                "p90_response_time": sorted_times[int(length * 0.9)] if length > 0 else 0,
                "p99_response_time": sorted_times[int(length * 0.99)] if length > 0 else 0,
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "slow_requests_count": len([t for t in response_times if t > self.slow_request_threshold])
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        }
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = {
            "requests": 0,
            "response_times": [],
            "slow_requests": [],
            "errors": 0,
            "endpoints": {},
            "methods": {},
            "status_codes": {}
        }


class AsyncPerformanceMonitor:
    """Background performance monitoring and alerting."""
    
    def __init__(self, middleware: PerformanceMiddleware):
        self.middleware = middleware
        self.monitoring_task = None
        self.alert_thresholds = {
            "cpu_percent": 80,
            "memory_percent": 85,
            "error_rate": 5.0,
            "avg_response_time": 2.0
        }
    
    async def start_monitoring(self):
        """Start background performance monitoring."""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self):
        """Stop background performance monitoring."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
    
    async def _monitor_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Monitor every minute
                stats = self.middleware.get_stats()
                await self._check_alerts(stats)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Performance monitoring error: {e}")
    
    async def _check_alerts(self, stats: Dict[str, Any]):
        """Check for performance alerts."""
        system = stats.get("system", {})
        summary = stats.get("summary", {})
        
        # CPU alert
        if system.get("cpu_percent", 0) > self.alert_thresholds["cpu_percent"]:
            await self._send_alert(f"High CPU usage: {system['cpu_percent']:.1f}%")
        
        # Memory alert
        if system.get("memory_percent", 0) > self.alert_thresholds["memory_percent"]:
            await self._send_alert(f"High memory usage: {system['memory_percent']:.1f}%")
        
        # Error rate alert
        if summary.get("error_rate", 0) > self.alert_thresholds["error_rate"]:
            await self._send_alert(f"High error rate: {summary['error_rate']:.2f}%")
        
        # Response time alert
        if summary.get("avg_response_time", 0) > self.alert_thresholds["avg_response_time"]:
            await self._send_alert(f"Slow response time: {summary['avg_response_time']:.2f}s")
    
    async def _send_alert(self, message: str):
        """Send performance alert."""
        print(f"Performance Alert: {message}")
        # In a real implementation, this would send notifications
        # to monitoring systems like Slack, email, etc.