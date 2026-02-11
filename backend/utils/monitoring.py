"""Production monitoring and metrics collection utilities."""

import time
import asyncio
import psutil
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from starlette.requests import Request
from starlette.responses import Response


@dataclass
class RequestMetrics:
    """Metrics for individual requests."""
    method: str
    path: str
    status_code: int
    process_time: float
    timestamp: float
    client_ip: str
    user_agent: str
    request_size: int
    response_size: int


class MetricsCollector:
    """Comprehensive metrics collection for production monitoring."""
    
    def __init__(self, retention_seconds: int = 3600):
        self.retention_seconds = retention_seconds
        self.start_time = time.time()
        
        # Request metrics storage
        self.request_metrics = deque(maxlen=10000)
        self.error_metrics = deque(maxlen=1000)
        
        # Aggregated metrics
        self.total_requests = 0
        self.total_errors = 0
        self.status_code_counts = defaultdict(int)
        self.endpoint_metrics = defaultdict(lambda: {
            'count': 0, 
            'total_time': 0, 
            'avg_time': 0,
            'errors': 0
        })
        
        # System metrics
        self.system_metrics_history = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        
        # Background tasks
        self._collection_task = None
        self._cleanup_task = None
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize background monitoring tasks."""
        self._collection_task = asyncio.create_task(self._collect_system_metrics())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_metrics())
        self.logger.info("Metrics collector initialized")
    
    async def shutdown(self):
        """Shutdown background tasks."""
        if self._collection_task:
            self._collection_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Wait for tasks to finish
        await asyncio.gather(
            self._collection_task, 
            self._cleanup_task, 
            return_exceptions=True
        )
        
        self.logger.info("Metrics collector shutdown complete")
    
    async def record_request_start(self, request: Request):
        """Record the start of a request."""
        request.state.start_time = time.time()
        request.state.request_size = len(await request.body())
    
    async def record_request_success(
        self, 
        request: Request, 
        response: Response, 
        process_time: float
    ):
        """Record successful request completion."""
        self.total_requests += 1
        self.status_code_counts[response.status_code] += 1
        
        # Extract path without query parameters
        path = request.url.path
        method = request.method
        
        # Update endpoint metrics
        endpoint_key = f"{method} {path}"
        endpoint_stats = self.endpoint_metrics[endpoint_key]
        endpoint_stats['count'] += 1
        endpoint_stats['total_time'] += process_time
        endpoint_stats['avg_time'] = endpoint_stats['total_time'] / endpoint_stats['count']
        
        # Store detailed metrics
        metrics = RequestMetrics(
            method=method,
            path=path,
            status_code=response.status_code,
            process_time=process_time,
            timestamp=time.time(),
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get('user-agent', '')[:100],
            request_size=getattr(request.state, 'request_size', 0),
            response_size=self._get_response_size(response)
        )
        
        self.request_metrics.append(metrics)
    
    async def record_request_error(
        self, 
        request: Request, 
        error: Exception, 
        process_time: float
    ):
        """Record failed request."""
        self.total_requests += 1
        self.total_errors += 1
        self.status_code_counts[500] += 1
        
        # Update endpoint error count
        endpoint_key = f"{request.method} {request.url.path}"
        self.endpoint_metrics[endpoint_key]['errors'] += 1
        
        # Store error metrics
        error_info = {
            'method': request.method,
            'path': request.url.path,
            'error': str(error),
            'error_type': type(error).__name__,
            'process_time': process_time,
            'timestamp': time.time(),
            'client_ip': self._get_client_ip(request),
            'user_agent': request.headers.get('user-agent', '')[:100]
        }
        
        self.error_metrics.append(error_info)
        
        # Log error for monitoring
        self.logger.error(
            f"Request failed: {request.method} {request.url.path}",
            extra=error_info
        )
    
    async def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time
    
    async def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        uptime = await self.get_uptime()
        
        # Calculate rates
        requests_per_second = self.total_requests / uptime if uptime > 0 else 0
        error_rate = (self.total_errors / self.total_requests * 100) if self.total_requests > 0 else 0
        
        # Get recent system metrics
        recent_system_metrics = list(self.system_metrics_history)[-1] if self.system_metrics_history else {}
        
        # Get top endpoints by request count
        top_endpoints = sorted(
            self.endpoint_metrics.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:10]
        
        # Get slowest endpoints
        slowest_endpoints = sorted(
            [(k, v) for k, v in self.endpoint_metrics.items() if v['count'] > 0],
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )[:10]
        
        return {
            'application': {
                'uptime_seconds': uptime,
                'start_time': self.start_time,
                'status': 'healthy'
            },
            'requests': {
                'total': self.total_requests,
                'errors': self.total_errors,
                'success_rate': 100 - error_rate,
                'error_rate': error_rate,
                'requests_per_second': requests_per_second,
                'status_codes': dict(self.status_code_counts)
            },
            'performance': {
                'avg_response_time': self._calculate_avg_response_time(),
                'p95_response_time': self._calculate_percentile_response_time(95),
                'p99_response_time': self._calculate_percentile_response_time(99)
            },
            'endpoints': {
                'top_by_requests': [
                    {'endpoint': k, **v} for k, v in top_endpoints
                ],
                'slowest': [
                    {'endpoint': k, **v} for k, v in slowest_endpoints
                ]
            },
            'system': recent_system_metrics,
            'timestamp': time.time()
        }
    
    async def check_cache_health(self) -> Dict[str, Any]:
        """Check cache system health."""
        # This would integrate with your cache system (Redis, etc.)
        return {
            'status': 'healthy',
            'hit_rate': 85.5,  # Placeholder
            'memory_usage': '45%',  # Placeholder
            'connections': 12  # Placeholder
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'
    
    def _get_response_size(self, response: Response) -> int:
        """Get response size from headers."""
        content_length = response.headers.get('content-length')
        if content_length:
            return int(content_length)
        return 0
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time from recent requests."""
        if not self.request_metrics:
            return 0.0
        
        total_time = sum(m.process_time for m in self.request_metrics)
        return total_time / len(self.request_metrics)
    
    def _calculate_percentile_response_time(self, percentile: int) -> float:
        """Calculate percentile response time."""
        if not self.request_metrics:
            return 0.0
        
        times = sorted([m.process_time for m in self.request_metrics])
        index = int(len(times) * percentile / 100)
        return times[min(index, len(times) - 1)]
    
    async def _collect_system_metrics(self):
        """Background task to collect system metrics."""
        while True:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Network I/O
                network = psutil.net_io_counters()
                
                # Process info
                process = psutil.Process()
                process_memory = process.memory_info()
                process_cpu = process.cpu_percent()
                
                metrics = {
                    'timestamp': time.time(),
                    'cpu': {
                        'percent': cpu_percent,
                        'count': psutil.cpu_count()
                    },
                    'memory': {
                        'total': memory.total,
                        'available': memory.available,
                        'percent': memory.percent,
                        'used': memory.used
                    },
                    'disk': {
                        'total': disk.total,
                        'used': disk.used,
                        'free': disk.free,
                        'percent': disk.percent
                    },
                    'network': {
                        'bytes_sent': network.bytes_sent,
                        'bytes_recv': network.bytes_recv,
                        'packets_sent': network.packets_sent,
                        'packets_recv': network.packets_recv
                    },
                    'process': {
                        'memory_rss': process_memory.rss,
                        'memory_vms': process_memory.vms,
                        'cpu_percent': process_cpu,
                        'num_threads': process.num_threads(),
                        'connections': len(process.connections())
                    }
                }
                
                self.system_metrics_history.append(metrics)
                
                # Sleep for 60 seconds
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_metrics(self):
        """Background task to cleanup old metrics."""
        while True:
            try:
                current_time = time.time()
                cutoff_time = current_time - self.retention_seconds
                
                # Clean up old request metrics
                while (self.request_metrics and 
                       self.request_metrics[0].timestamp < cutoff_time):
                    self.request_metrics.popleft()
                
                # Clean up old error metrics
                while (self.error_metrics and 
                       self.error_metrics[0]['timestamp'] < cutoff_time):
                    self.error_metrics.popleft()
                
                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error during metrics cleanup: {e}")
                await asyncio.sleep(300)
    
    async def setup_periodic_health_checks(self, interval: int = 30):
        """Setup periodic health monitoring."""
        async def health_check_task():
            while True:
                try:
                    # Perform health checks
                    metrics = await self.get_comprehensive_metrics()
                    
                    # Check for alerts
                    if metrics['requests']['error_rate'] > 10:
                        self.logger.warning(
                            f"High error rate detected: {metrics['requests']['error_rate']:.2f}%"
                        )
                    
                    if metrics['system']['cpu']['percent'] > 90:
                        self.logger.warning(
                            f"High CPU usage detected: {metrics['system']['cpu']['percent']:.2f}%"
                        )
                    
                    if metrics['system']['memory']['percent'] > 90:
                        self.logger.warning(
                            f"High memory usage detected: {metrics['system']['memory']['percent']:.2f}%"
                        )
                    
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Health check failed: {e}")
                    await asyncio.sleep(interval)
        
        asyncio.create_task(health_check_task())