"""
PaperTrading Platform - Settings Endpoints
User settings and preferences management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.dependencies import get_current_active_user, get_db
from app.db.models.user import User
from app.db.models.user_settings import UserSettings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()


# ============================================
# Pydantic Schemas
# ============================================

class ApiKeyRequest(BaseModel):
    """Request to save an API key."""
    provider: str = Field(..., description="Provider name: alphavantage, finnhub, polygon")
    api_key: str = Field(..., min_length=1, description="API key value")


class ApiKeyResponse(BaseModel):
    """Response showing configured providers."""
    provider: str
    configured: bool
    masked_key: Optional[str] = None


class ApiKeysListResponse(BaseModel):
    """List of configured API keys."""
    providers: list[ApiKeyResponse]


class TestConnectionRequest(BaseModel):
    """Request to test a provider connection."""
    provider: str


class TestConnectionResponse(BaseModel):
    """Response from connection test."""
    provider: str
    success: bool
    message: str


class NotificationSettings(BaseModel):
    """Notification preferences."""
    email: bool = True
    push: bool = True
    trade_execution: bool = True
    price_alerts: bool = True
    portfolio_updates: bool = True
    market_news: bool = False


class DisplaySettings(BaseModel):
    """Display preferences."""
    theme: str = "dark"
    compact_mode: bool = False
    show_percent_change: bool = True
    default_chart_period: str = "1M"
    chart_type: str = "candlestick"


class UserSettingsResponse(BaseModel):
    """Full user settings response."""
    theme: str
    display: DisplaySettings
    notifications: NotificationSettings
    api_keys: list[ApiKeyResponse]
    password_changed_at: Optional[datetime] = None


class UpdateSettingsRequest(BaseModel):
    """Request to update user settings."""
    theme: Optional[str] = None
    display: Optional[DisplaySettings] = None
    notifications: Optional[NotificationSettings] = None


# ============================================
# Helper Functions
# ============================================

async def get_or_create_settings(db: AsyncSession, user_id: int) -> UserSettings:
    """Get user settings or create if not exists."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


def mask_api_key(key: str) -> str:
    """Mask API key for display."""
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


SUPPORTED_PROVIDERS = [
    # US Market Primary
    "alpaca",
    "alpaca_secret",  # Alpaca's secret key
    "polygon",
    # Global Coverage
    "finnhub",
    "twelvedata",
    # Historical Data
    "eodhd",
    # Fundamentals
    "fmp",
    "alphavantage",
    # Additional Providers
    "nasdaq",
    "tiingo",
    "marketstack",
    "stockdata",
    "intrinio",
    # No API Key Required
    "yfinance",
    "stooq",
    "investingcom",
]


# ============================================
# Endpoints
# ============================================

@router.get(
    "/",
    response_model=UserSettingsResponse,
    summary="Get user settings",
    description="Get all user settings including preferences and configured API keys."
)
async def get_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserSettingsResponse:
    """Get current user's settings."""
    settings = await get_or_create_settings(db, current_user.id)
    
    # Get API keys status
    providers_status = []
    for provider in SUPPORTED_PROVIDERS:
        key = settings.get_provider_key(provider)
        providers_status.append(ApiKeyResponse(
            provider=provider,
            configured=bool(key),
            masked_key=mask_api_key(key) if key else None
        ))
    
    return UserSettingsResponse(
        theme=settings.theme or "dark",
        display=DisplaySettings(
            theme=settings.theme or "dark",
            compact_mode=settings.display_compact_mode or False,
            show_percent_change=settings.display_show_percent_change if settings.display_show_percent_change is not None else True,
            default_chart_period=settings.display_default_chart_period or "1M",
            chart_type=settings.display_chart_type or "candlestick"
        ),
        notifications=NotificationSettings(
            email=settings.notifications_email if settings.notifications_email is not None else True,
            push=settings.notifications_push if settings.notifications_push is not None else True,
            trade_execution=settings.notifications_trade_execution if settings.notifications_trade_execution is not None else True,
            price_alerts=settings.notifications_price_alerts if settings.notifications_price_alerts is not None else True,
            portfolio_updates=settings.notifications_portfolio_updates if settings.notifications_portfolio_updates is not None else True,
            market_news=settings.notifications_market_news or False,
        ),
        api_keys=providers_status,
        password_changed_at=settings.password_changed_at,
    )


@router.patch(
    "/",
    response_model=UserSettingsResponse,
    summary="Update user settings",
    description="Update user preferences (theme, display, notifications)."
)
async def update_settings(
    updates: UpdateSettingsRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserSettingsResponse:
    """Update user settings."""
    settings = await get_or_create_settings(db, current_user.id)
    
    # Update theme
    if updates.theme is not None:
        if updates.theme not in ["dark", "light", "system"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid theme. Must be: dark, light, or system"
            )
        settings.theme = updates.theme
    
    # Update display settings
    if updates.display is not None:
        if updates.display.theme:
            settings.theme = updates.display.theme
        settings.display_compact_mode = updates.display.compact_mode
        settings.display_show_percent_change = updates.display.show_percent_change
        settings.display_default_chart_period = updates.display.default_chart_period
        settings.display_chart_type = updates.display.chart_type
    
    # Update notifications
    if updates.notifications is not None:
        settings.notifications_email = updates.notifications.email
        settings.notifications_push = updates.notifications.push
        settings.notifications_trade_execution = updates.notifications.trade_execution
        settings.notifications_price_alerts = updates.notifications.price_alerts
        settings.notifications_portfolio_updates = updates.notifications.portfolio_updates
        settings.notifications_market_news = updates.notifications.market_news
    
    await db.commit()
    await db.refresh(settings)
    
    # Return updated settings
    return await get_settings(current_user, db)


@router.post(
    "/api-keys",
    response_model=ApiKeyResponse,
    summary="Save API key",
    description="Save an API key for a data provider."
)
async def save_api_key(
    request: ApiKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ApiKeyResponse:
    """Save an API key for a provider."""
    if request.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    
    settings = await get_or_create_settings(db, current_user.id)
    settings.set_provider_key(request.provider, request.api_key)
    
    await db.commit()
    
    return ApiKeyResponse(
        provider=request.provider,
        configured=True,
        masked_key=mask_api_key(request.api_key)
    )


@router.delete(
    "/api-keys/{provider}",
    summary="Delete API key",
    description="Remove an API key for a data provider."
)
async def delete_api_key(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    
    settings = await get_or_create_settings(db, current_user.id)
    settings.set_provider_key(provider, None)  # Set to None to remove
    
    await db.commit()
    
    return {"message": f"API key for {provider} removed"}


@router.post(
    "/api-keys/test",
    response_model=TestConnectionResponse,
    summary="Test API connection",
    description="Test connection to a data provider using saved API key."
)
async def test_connection(
    request: TestConnectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> TestConnectionResponse:
    """Test connection to a data provider."""
    import httpx
    
    if request.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    
    settings = await get_or_create_settings(db, current_user.id)
    api_key = settings.get_provider_key(request.provider)
    
    if not api_key:
        return TestConnectionResponse(
            provider=request.provider,
            success=False,
            message="No API key configured for this provider"
        )
    
    # Test endpoints for each provider
    test_urls = {
        "alpaca": None,  # Special handling below
        "alpaca_secret": None,  # Tested together with alpaca
        "polygon": f"https://api.polygon.io/v2/aggs/ticker/AAPL/prev?apiKey={api_key}",
        "finnhub": f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={api_key}",
        "twelvedata": f"https://api.twelvedata.com/quote?symbol=AAPL&apikey={api_key}",
        "eodhd": f"https://eodhd.com/api/real-time/AAPL.US?api_token={api_key}&fmt=json",
        "fmp": f"https://financialmodelingprep.com/api/v3/quote/AAPL?apikey={api_key}",
        "alphavantage": f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={api_key}",
        "nasdaq": None,  # Complex auth
        "tiingo": None,  # Special header-based auth
        "marketstack": f"http://api.marketstack.com/v1/tickers/AAPL?access_key={api_key}",
        "stockdata": f"https://api.stockdata.org/v1/data/quote?symbols=AAPL&api_token={api_key}",
        "intrinio": None,  # Complex auth
        "yfinance": None,  # No API key needed
        "stooq": None,  # No API key needed
        "investingcom": None,  # No API key needed
    }
    
    # Providers that don't need testing
    no_key_providers = ["yfinance", "stooq", "investingcom"]
    if request.provider in no_key_providers:
        return TestConnectionResponse(
            provider=request.provider,
            success=True,
            message="This provider does not require an API key"
        )
    
    # Providers with complex auth or no test URL
    if test_urls.get(request.provider) is None:
        return TestConnectionResponse(
            provider=request.provider,
            success=True,
            message="API key saved. Manual verification may be needed."
        )
        return TestConnectionResponse(
            provider=request.provider,
            success=True,
            message="Yahoo Finance does not require an API key"
        )
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(test_urls[request.provider])
            
            if response.status_code == 200:
                data = response.json()
                # Check for API-specific error messages
                if request.provider == "alphavantage" and "Error Message" in data:
                    return TestConnectionResponse(
                        provider=request.provider,
                        success=False,
                        message="Invalid API key"
                    )
                if request.provider == "finnhub" and data.get("error"):
                    return TestConnectionResponse(
                        provider=request.provider,
                        success=False,
                        message=data.get("error", "Invalid API key")
                    )
                return TestConnectionResponse(
                    provider=request.provider,
                    success=True,
                    message="Connection successful!"
                )
            elif response.status_code == 401 or response.status_code == 403:
                return TestConnectionResponse(
                    provider=request.provider,
                    success=False,
                    message="Invalid API key"
                )
            else:
                return TestConnectionResponse(
                    provider=request.provider,
                    success=False,
                    message=f"Connection failed: HTTP {response.status_code}"
                )
    except httpx.TimeoutException:
        return TestConnectionResponse(
            provider=request.provider,
            success=False,
            message="Connection timeout"
        )
    except Exception as e:
        return TestConnectionResponse(
            provider=request.provider,
            success=False,
            message=f"Connection error: {str(e)}"
        )


# ============================================
# Import API Keys from Environment
# ============================================

class ImportFromEnvResponse(BaseModel):
    """Response from importing API keys from environment."""
    imported: list[str]
    skipped: list[str]
    message: str


# Mapping from env variable names to provider keys
ENV_TO_PROVIDER = {
    "ALPACA_API_KEY": "alpaca",
    "ALPACA_SECRET_KEY": "alpaca_secret",
    "POLYGON_API_KEY": "polygon",
    "FINNHUB_API_KEY": "finnhub",
    "TWELVE_DATA_API_KEY": "twelvedata",
    "EODHD_API_KEY": "eodhd",
    "FMP_API_KEY": "fmp",
    "ALPHA_VANTAGE_API_KEY": "alphavantage",
    "NASDAQ_DATA_LINK_API_KEY": "nasdaq",
    "TIINGO_API_KEY": "tiingo",
    "MARKETSTACK_API_KEY": "marketstack",
    "STOCKDATA_API_KEY": "stockdata",
    "INTRINIO_API_KEY": "intrinio",
}


@router.post(
    "/api-keys/import-from-env",
    response_model=ImportFromEnvResponse,
    summary="Import API keys from environment",
    description="Import all configured API keys from environment variables into user settings."
)
async def import_api_keys_from_env(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ImportFromEnvResponse:
    """Import API keys from environment variables."""
    import os
    
    settings = await get_or_create_settings(db, current_user.id)
    
    imported = []
    skipped = []
    
    for env_var, provider in ENV_TO_PROVIDER.items():
        api_key = os.getenv(env_var)
        if api_key and api_key.strip():
            # Check if already configured
            existing = settings.get_provider_key(provider)
            if existing:
                skipped.append(f"{provider} (already configured)")
            else:
                settings.set_provider_key(provider, api_key.strip())
                imported.append(provider)
        else:
            skipped.append(f"{provider} (no env var)")
    
    if imported:
        await db.commit()
        await db.refresh(settings)
    
    return ImportFromEnvResponse(
        imported=imported,
        skipped=skipped,
        message=f"Imported {len(imported)} API keys from environment"
    )
