"""
PaperTrading Platform - Main Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.api.v1.router import api_router
from app.api.v1.websockets import market_stream_router
from app.db.database import engine, init_db
from app.db.redis_client import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events handler."""
    # Startup
    logger.info("🚀 Starting PaperTrading Platform...")
    
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")
    
    # Initialize Redis
    await redis_client.initialize()
    logger.info("✅ Redis connected")
    
    # TODO: Initialize providers
    # TODO: Initialize scheduler
    # TODO: Load ML models
    
    logger.info("✅ PaperTrading Platform started successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down PaperTrading Platform...")
    await redis_client.close()
    await engine.dispose()
    logger.info("👋 Goodbye!")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Multi-market paper trading platform with ML predictions",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    # Include WebSocket router
    app.include_router(market_stream_router, prefix=settings.API_V1_PREFIX)
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for load balancers."""
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": "1.0.0"
        }
    
    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        """Readiness check - verifies all dependencies are available."""
        checks = {
            "database": "unknown",
            "redis": "unknown"
        }
        
        # Check database
        try:
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "connected"
        except Exception as e:
            checks["database"] = f"error: {str(e)[:50]}"
        
        # Check Redis
        try:
            if redis_client._client:
                await redis_client._client.ping()
                checks["redis"] = "connected"
            else:
                checks["redis"] = "not initialized"
        except Exception as e:
            checks["redis"] = f"error: {str(e)[:50]}"
        
        all_healthy = all(v == "connected" for v in checks.values())
        
        return {
            "status": "ready" if all_healthy else "degraded",
            "checks": checks
        }
    
    @app.get("/metrics", tags=["Health"])
    async def metrics():
        """Basic metrics endpoint."""
        import psutil
        import os
        
        return {
            "process": {
                "pid": os.getpid(),
                "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
                "cpu_percent": psutil.Process().cpu_percent(),
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
            }
        }
    
    return app


# Create the application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
