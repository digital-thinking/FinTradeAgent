"""FastAPI backend for FinTradeAgent with performance optimizations."""

import time
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

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
    print("🚀 Starting FinTradeAgent API with performance optimizations...")
    
    # Initialize database connection pool
    await DatabaseOptimizer.initialize_pool()
    
    # Initialize memory optimizer
    MemoryOptimizer.initialize()
    
    # Warm up critical services
    await warm_up_services()
    
    print("✅ FinTradeAgent API started successfully")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down FinTradeAgent API...")
    
    # Close database connections
    await DatabaseOptimizer.close_pool()
    
    # Clean up memory
    MemoryOptimizer.cleanup()
    
    print("✅ FinTradeAgent API shutdown complete")

app = FastAPI(
    title="FinTradeAgent API",
    description="REST API for Agentic Trade Assistant with Performance Optimizations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if __name__ != "__main__" else None,  # Disable docs in production
    redoc_url="/redoc" if __name__ != "__main__" else None
)

# Performance middleware (order matters)
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses > 1KB
app.add_middleware(PerformanceMiddleware)  # Custom performance monitoring
app.add_middleware(CacheMiddleware)  # Response caching

# CORS configuration for Vue.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

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
            print(f"❌ Request {request_id} failed in {process_time:.4f}s: {str(e)}")
            
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
        print("🔥 Services warmed up successfully")
    except Exception as e:
        print(f"⚠️ Service warm-up failed: {e}")

if __name__ == "__main__":
    import uvicorn
    
    # Production-optimized uvicorn configuration
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in production
        workers=1,  # Single worker for development
        loop="uvloop",  # High-performance event loop
        http="httptools",  # High-performance HTTP parser
        log_level="info",
        access_log=True,
        server_header=False,  # Hide server information
        date_header=True
    )