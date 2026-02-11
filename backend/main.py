"""FastAPI backend for FinTradeAgent with performance optimizations."""

import time
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.routers import portfolios, agents, trades, analytics, system
from backend.middleware.performance import PerformanceMiddleware
from backend.middleware.cache import CacheMiddleware
from backend.utils.database import DatabaseOptimizer
from backend.utils.memory import MemoryOptimizer

# Performance monitoring
performance_metrics = {
    "requests": 0,
    "total_time": 0,
    "avg_response_time": 0,
    "errors": 0,
    "cache_hits": 0,
    "cache_misses": 0
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with startup and shutdown optimizations."""
    # Startup
    print("Starting FinTradeAgent API with performance optimizations...")
    
    # Initialize database connection pool
    await DatabaseOptimizer.initialize_pool()
    
    # Initialize memory optimizer
    MemoryOptimizer.initialize()
    
    # Warm up critical services
    await warm_up_services()
    
    print("FinTradeAgent API started successfully")
    
    yield
    
    # Shutdown
    print("Shutting down FinTradeAgent API...")
    
    # Close database connections
    await DatabaseOptimizer.close_pool()
    
    # Clean up memory
    MemoryOptimizer.cleanup()
    
    print("FinTradeAgent API shutdown complete")

app = FastAPI(
    title="FinTradeAgent API",
    description="REST API for Agentic Trade Assistant with Performance Optimizations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if __name__ != "__main__" else None,  # Disable docs in production
    redoc_url="/redoc" if __name__ != "__main__" else None
)

# Middleware (order matters - last added runs first)
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses > 1KB
app.add_middleware(PerformanceMiddleware)  # Custom performance monitoring
app.add_middleware(CacheMiddleware)  # Response caching

# Custom middleware for request/response optimization
class OptimizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Add request ID for tracing
        request_id = f"req_{int(start_time * 1000)}"
        request.state.request_id = request_id
        
        # Performance metrics
        performance_metrics["requests"] += 1
        
        try:
            response = await call_next(request)
            
            # Add performance headers
            process_time = time.time() - start_time
            performance_metrics["total_time"] += process_time
            performance_metrics["avg_response_time"] = (
                performance_metrics["total_time"] / performance_metrics["requests"]
            )
            
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-API-Version"] = "1.0.0"
            
            return response
            
        except Exception as e:
            performance_metrics["errors"] += 1
            process_time = time.time() - start_time
            
            # Log error with performance context
            print(f"Request {request_id} failed in {process_time:.4f}s: {str(e)}")
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "request_id": request_id,
                    "timestamp": int(time.time())
                },
                headers={
                    "X-Process-Time": str(process_time),
                    "X-Request-ID": request_id
                }
            )

app.add_middleware(OptimizationMiddleware)


# Pure ASGI CORS middleware — handles preflight at the lowest level,
# bypassing any BaseHTTPMiddleware interference.
CORS_ALLOW_ORIGINS = {
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:5173", "http://127.0.0.1:5173",
}

class CORSMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        origin = headers.get(b"origin", b"").decode()

        # Handle preflight OPTIONS requests
        if scope["method"] == "OPTIONS":
            preflight_headers = {
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "3600",
            }
            if origin and (origin in CORS_ALLOW_ORIGINS or not CORS_ALLOW_ORIGINS):
                preflight_headers["Access-Control-Allow-Origin"] = origin
                preflight_headers["Access-Control-Allow-Credentials"] = "true"
            else:
                preflight_headers["Access-Control-Allow-Origin"] = "*"
            response = StarletteResponse(status_code=200, headers=preflight_headers)
            await response(scope, receive, send)
            return

        # For regular requests, add CORS headers to the response
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                if origin and origin in CORS_ALLOW_ORIGINS:
                    response_headers.append((b"access-control-allow-origin", origin.encode()))
                    response_headers.append((b"access-control-allow-credentials", b"true"))
                else:
                    response_headers.append((b"access-control-allow-origin", b"*"))
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(scope, receive, send_with_cors)

app.add_middleware(CORSMiddleware)

# Include routers with optimized configuration
app.include_router(portfolios.router, tags=["Portfolios"])
app.include_router(agents.router, tags=["Agents"])
app.include_router(trades.router, tags=["Trades"])
app.include_router(analytics.router, tags=["Analytics"])
app.include_router(system.router, tags=["System"])

@app.get("/health", tags=["Health"])
async def health_check():
    """Enhanced health check endpoint with system metrics."""
    return {
        "status": "ok",
        "service": "FinTradeAgent API",
        "version": "1.0.0",
        "timestamp": int(time.time()),
        "performance": {
            "requests_handled": performance_metrics["requests"],
            "avg_response_time_ms": round(performance_metrics["avg_response_time"] * 1000, 2),
            "error_rate": round(
                (performance_metrics["errors"] / max(performance_metrics["requests"], 1)) * 100, 2
            ),
            "cache_hit_rate": round(
                (performance_metrics["cache_hits"] / max(
                    performance_metrics["cache_hits"] + performance_metrics["cache_misses"], 1
                )) * 100, 2
            )
        },
        "memory": MemoryOptimizer.get_stats(),
        "database": await DatabaseOptimizer.get_stats()
    }

@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """Detailed performance metrics endpoint."""
    return {
        "performance": performance_metrics,
        "memory": MemoryOptimizer.get_detailed_stats(),
        "database": await DatabaseOptimizer.get_detailed_stats(),
        "timestamp": int(time.time())
    }

async def warm_up_services():
    """Warm up critical services for better initial performance."""
    try:
        # Pre-load critical data
        await asyncio.gather(
            # Add your warm-up tasks here
            # Example: preload_portfolio_cache(),
            # Example: initialize_ml_models(),
            asyncio.sleep(0.1)  # Placeholder
        )
        print("Services warmed up successfully")
    except Exception as e:
        print(f"Service warm-up failed: {e}")

if __name__ == "__main__":
    import uvicorn
    import sys

    uvicorn_kwargs = {
        "app": "backend.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,
        "workers": 1,
        "log_level": "info",
        "access_log": True,
        "server_header": False,
        "date_header": True,
    }

    # uvloop/httptools are not available on Windows
    if sys.platform != "win32":
        uvicorn_kwargs["loop"] = "uvloop"
        uvicorn_kwargs["http"] = "httptools"

    uvicorn.run(**uvicorn_kwargs)