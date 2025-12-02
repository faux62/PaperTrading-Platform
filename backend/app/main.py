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
        """Health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": "1.0.0"
        }
    
    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        """Readiness check endpoint."""
        # TODO: Check DB and Redis connections
        return {
            "status": "ready",
            "database": "connected",
            "redis": "connected"
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
