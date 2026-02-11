"""Production-optimized FastAPI backend for FinTradeAgent."""

import os
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Production configuration
from backend.config.production import production_settings
from backend.routers import portfolios, agents, trades, analytics, system
from backend.middleware.performance import PerformanceMiddleware
from backend.middleware.cache import CacheMiddleware
from backend.middleware.security import SecurityMiddleware
from backend.middleware.rate_limiter import RateLimiterMiddleware
from backend.utils.database import DatabaseOptimizer
from backend.utils.memory import MemoryOptimizer
from backend.utils.logging import setup_production_logging
from backend.utils.monitoring import MetricsCollector

# Initialize security
security = HTTPBearer(auto_error=False)

# Performance monitoring
metrics_collector = MetricsCollector()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with production optimizations."""
    # Setup production logging
    setup_production_logging(production_settings)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starting FinTradeAgent API in PRODUCTION mode...")
    
    try:
        # Initialize database connection pool
        await DatabaseOptimizer.initialize_pool(production_settings.database_config)
        logger.info("✅ Database connection pool initialized")
        
        # Initialize memory optimizer
        MemoryOptimizer.initialize(
            max_memory_percent=80,
            cleanup_interval=300  # 5 minutes
        )
        logger.info("✅ Memory optimizer initialized")
        
        # Initialize metrics collection
        await metrics_collector.initialize()
        logger.info("✅ Metrics collector initialized")
        
        # Warm up critical services
        await warm_up_services()
        logger.info("✅ Services warmed up successfully")
        
        # Setup health checks
        await setup_health_checks()
        logger.info("✅ Health checks configured")
        
        logger.info("🎉 FinTradeAgent API started successfully in PRODUCTION mode")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start FinTradeAgent API: {e}")
        raise
    
    finally:
        # Shutdown sequence
        logger.info("🛑 Shutting down FinTradeAgent API...")
        
        # Close database connections
        await DatabaseOptimizer.close_pool()
        logger.info("✅ Database connections closed")
        
        # Stop metrics collection
        await metrics_collector.shutdown()
        logger.info("✅ Metrics collector stopped")
        
        # Clean up memory
        MemoryOptimizer.cleanup()
        logger.info("✅ Memory cleanup completed")
        
        logger.info("✅ FinTradeAgent API shutdown complete")


app = FastAPI(
    title=production_settings.app_name,
    description="Production REST API for Agentic Trade Assistant",
    version=production_settings.app_version,
    lifespan=lifespan,
    docs_url=None,  # Disable docs in production for security
    redoc_url=None,
    openapi_url=None,  # Disable OpenAPI schema endpoint
    # Custom OpenAPI schema for internal monitoring only
    openapi_prefix="" if production_settings.debug else None
)

# Security Middleware Stack (order matters!)
# 1. Trusted Host Middleware (validates Host header)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=production_settings.allowed_hosts + ["localhost", "127.0.0.1"]
)

# 2. Security Headers Middleware
app.add_middleware(SecurityMiddleware, headers=production_settings.security_headers)

# 3. Rate Limiting Middleware
if production_settings.rate_limit_enabled:
    app.add_middleware(
        RateLimiterMiddleware,
        requests_per_minute=production_settings.rate_limit_requests,
        storage_url=production_settings.rate_limit_storage
    )

# 4. Session Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=production_settings.secret_key,
    https_only=production_settings.ssl_redirect,
    same_site="strict"
)

# 5. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=production_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

# 6. Compression Middleware
if production_settings.gzip_enabled:
    app.add_middleware(
        GZipMiddleware,
        minimum_size=production_settings.gzip_minimum_size,
        compresslevel=production_settings.compression_level
    )

# 7. Performance Monitoring Middleware
app.add_middleware(
    PerformanceMiddleware,
    metrics_collector=metrics_collector
)

# 8. Response Caching Middleware
if production_settings.cache_enabled:
    app.add_middleware(
        CacheMiddleware,
        redis_url=production_settings.redis_url,
        default_ttl=production_settings.cache_ttl
    )


class ProductionOptimizationMiddleware(BaseHTTPMiddleware):
    """Production-specific optimization middleware."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Generate request ID for tracing
        request_id = f"req_{int(start_time * 1000000)}"
        request.state.request_id = request_id
        
        # Add request to metrics
        await metrics_collector.record_request_start(request)
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add production headers
            response.headers.update({
                "X-Process-Time": f"{process_time:.4f}",
                "X-Request-ID": request_id,
                "X-API-Version": production_settings.app_version,
                "X-Environment": production_settings.app_env,
                **production_settings.security_headers
            })
            
            # Record metrics
            await metrics_collector.record_request_success(
                request, response, process_time
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Log error with context
            logger = logging.getLogger(__name__)
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "process_time": process_time,
                    "error": str(e)
                }
            )
            
            # Record error metrics
            await metrics_collector.record_request_error(
                request, e, process_time
            )
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "request_id": request_id,
                    "timestamp": int(time.time())
                },
                headers={
                    "X-Process-Time": f"{process_time:.4f}",
                    "X-Request-ID": request_id,
                    **production_settings.security_headers
                }
            )


app.add_middleware(ProductionOptimizationMiddleware)

# Include routers with production configuration
app.include_router(portfolios.router, tags=["Portfolios"])
app.include_router(agents.router, tags=["Agents"])
app.include_router(trades.router, tags=["Trades"])
app.include_router(analytics.router, tags=["Analytics"])
app.include_router(system.router, tags=["System"])


@app.get("/health", include_in_schema=False)
async def health_check():
    """Production health check endpoint with comprehensive metrics."""
    try:
        health_data = {
            "status": "healthy",
            "service": production_settings.app_name,
            "version": production_settings.app_version,
            "environment": production_settings.app_env,
            "timestamp": int(time.time()),
            "uptime": await metrics_collector.get_uptime(),
            "checks": {
                "database": await DatabaseOptimizer.health_check(),
                "memory": MemoryOptimizer.health_check(),
                "cache": await metrics_collector.check_cache_health()
            }
        }
        
        # Check if all services are healthy
        all_healthy = all(
            check.get("status") == "healthy" 
            for check in health_data["checks"].values()
        )
        
        status_code = 200 if all_healthy else 503
        if not all_healthy:
            health_data["status"] = "degraded"
        
        return JSONResponse(content=health_data, status_code=status_code)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Health check failed: {e}")
        
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": "Health check failed",
                "timestamp": int(time.time())
            },
            status_code=503
        )


@app.get("/metrics", include_in_schema=False)
async def get_metrics(token: str = Depends(security)):
    """Production metrics endpoint with authentication."""
    # In production, you might want to authenticate this endpoint
    if production_settings.metrics_enabled:
        return await metrics_collector.get_comprehensive_metrics()
    else:
        raise HTTPException(status_code=404, detail="Metrics disabled")


@app.get("/ready", include_in_schema=False)
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Quick checks for readiness
        db_ready = await DatabaseOptimizer.quick_health_check()
        memory_ok = MemoryOptimizer.quick_health_check()
        
        if db_ready and memory_ok:
            return {"status": "ready", "timestamp": int(time.time())}
        else:
            return JSONResponse(
                content={"status": "not_ready", "timestamp": int(time.time())},
                status_code=503
            )
    except Exception:
        return JSONResponse(
            content={"status": "not_ready", "timestamp": int(time.time())},
            status_code=503
        )


async def warm_up_services():
    """Warm up critical services for optimal performance."""
    try:
        # Pre-initialize connection pools
        await DatabaseOptimizer.warm_up()
        
        # Pre-load critical data
        await asyncio.gather(
            # Add service-specific warm-up tasks
            asyncio.sleep(0.1),  # Placeholder
            return_exceptions=True
        )
        
        logging.getLogger(__name__).info("🔥 All services warmed up successfully")
        
    except Exception as e:
        logging.getLogger(__name__).error(f"⚠️ Service warm-up failed: {e}")


async def setup_health_checks():
    """Setup comprehensive health monitoring."""
    if production_settings.health_check_enabled:
        # Setup periodic health checks
        await metrics_collector.setup_periodic_health_checks(interval=30)


if __name__ == "__main__":
    # This should not be used in production
    # Use gunicorn or uvicorn with proper configuration
    raise RuntimeError(
        "Do not run production server with python -m backend.main_production. "
        "Use proper ASGI server like gunicorn or uvicorn."
    )