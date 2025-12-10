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
from app.data_providers.provider_init import initialize_providers, shutdown_providers


async def load_api_keys_from_settings() -> dict[str, str]:
    """Load API keys from user settings in database."""
    from app.db.database import async_session_maker
    from app.db.repositories.user import UserRepository
    
    api_keys = {}
    
    try:
        async with async_session_maker() as db:
            user_repo = UserRepository(db)
            # Load default/system settings from first user or admin
            users = await user_repo.get_all(skip=0, limit=1)
            
            if users:
                user = users[0]
                if user.settings and "data_providers" in user.settings:
                    providers = user.settings.get("data_providers", {})
                    for provider_config in providers.values():
                        if isinstance(provider_config, dict):
                            name = provider_config.get("provider_id", "").lower()
                            api_key = provider_config.get("api_key", "")
                            if name and api_key:
                                api_keys[name] = api_key
                                # Handle Alpaca secret
                                if name == "alpaca" and "api_secret" in provider_config:
                                    api_keys["alpaca_secret"] = provider_config["api_secret"]
    except Exception as e:
        logger.warning(f"Could not load API keys from database: {e}")
    
    # Also load from environment variables as fallback
    import os
    env_mappings = {
        "FINNHUB_API_KEY": "finnhub",
        "POLYGON_API_KEY": "polygon",
        "ALPHA_VANTAGE_API_KEY": "alpha_vantage",
        "TIINGO_API_KEY": "tiingo",
        "TWELVE_DATA_API_KEY": "twelve_data",
        "ALPACA_API_KEY": "alpaca",
        "ALPACA_SECRET_KEY": "alpaca_secret",
        "FMP_API_KEY": "fmp",
        "EODHD_API_KEY": "eodhd",
        "INTRINIO_API_KEY": "intrinio",
        "MARKETSTACK_API_KEY": "marketstack",
        "NASDAQ_DATA_LINK_API_KEY": "nasdaq_datalink",
        "STOCKDATA_API_KEY": "stockdata",
    }
    
    for env_var, provider_name in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value and provider_name not in api_keys:
            api_keys[provider_name] = env_value
    
    return api_keys


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
    
    # Initialize data providers
    try:
        api_keys = await load_api_keys_from_settings()
        logger.info(f"📊 Found API keys for {len(api_keys)} providers")
        
        results = await initialize_providers(api_keys)
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"✅ Initialized {success_count}/{len(results)} data providers")
    except Exception as e:
        logger.error(f"⚠️ Provider initialization error (non-fatal): {e}")
    
    # Initialize Trading Assistant Bot
    try:
        from app.bot import initialize_bot
        await initialize_bot()
        logger.info("✅ Trading Assistant Bot initialized")
    except Exception as e:
        logger.error(f"⚠️ Bot initialization error (non-fatal): {e}")
    
    # TODO: Load ML models
    
    logger.info("✅ PaperTrading Platform started successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down PaperTrading Platform...")
    
    # Shutdown Trading Assistant Bot
    try:
        from app.bot import shutdown_bot
        await shutdown_bot()
        logger.info("✅ Trading Assistant Bot stopped")
    except Exception as e:
        logger.warning(f"Bot shutdown error: {e}")
    
    await shutdown_providers()
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
