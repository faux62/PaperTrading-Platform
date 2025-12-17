"""
API Key Service with Hierarchical Fallback

Provides centralized API key management with the following priority:
1. User's personal key (from user_settings)
2. System key (from superuser/admin)
3. Environment variable

This ensures all users have access to data providers while allowing
advanced users to configure their own keys.
"""
import os
from typing import Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.models.user_settings import UserSettings


# Provider name mappings for different formats
# Keys are what frontend/settings uses, values are DB column suffixes
PROVIDER_DB_NAMES = {
    "finnhub": "finnhub",
    "polygon": "polygon", 
    "alpha_vantage": "alphavantage",
    "alphavantage": "alphavantage",  # Frontend uses this
    "tiingo": "tiingo",
    "twelve_data": "twelvedata",
    "twelvedata": "twelvedata",  # Frontend uses this
    "alpaca": "alpaca",
    "alpaca_secret": "alpaca_secret",
    "fmp": "fmp",
    "eodhd": "eodhd",
    "intrinio": "intrinio",
    "marketstack": "marketstack",
    "nasdaq_datalink": "nasdaq",
    "nasdaq": "nasdaq",  # Frontend uses this
    "stockdata": "stockdata",
    "yfinance": "yfinance",
    "stooq": "stooq",
    "investing": "investingcom",
    "investingcom": "investingcom",  # Frontend uses this
}

# Environment variable mappings
ENV_VAR_MAPPINGS = {
    "finnhub": "FINNHUB_API_KEY",
    "polygon": "POLYGON_API_KEY",
    "alpha_vantage": "ALPHA_VANTAGE_API_KEY",
    "tiingo": "TIINGO_API_KEY",
    "twelve_data": "TWELVE_DATA_API_KEY",
    "alpaca": "ALPACA_API_KEY",
    "alpaca_secret": "ALPACA_SECRET_KEY",
    "fmp": "FMP_API_KEY",
    "eodhd": "EODHD_API_KEY",
    "intrinio": "INTRINIO_API_KEY",
    "marketstack": "MARKETSTACK_API_KEY",
    "nasdaq_datalink": "NASDAQ_DATA_LINK_API_KEY",
    "stockdata": "STOCKDATA_API_KEY",
}


class ApiKeySource:
    """Enum-like class for API key sources"""
    PERSONAL = "personal"
    SYSTEM = "system"
    ENVIRONMENT = "environment"
    NONE = None


class ApiKeyService:
    """
    Centralized service for API key management with hierarchical fallback.
    
    Priority order:
    1. User's personal key (user_settings)
    2. System key (superuser's settings)
    3. Environment variable
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._system_settings: Optional[UserSettings] = None
        self._system_settings_loaded = False
    
    async def _get_system_settings(self) -> Optional[UserSettings]:
        """Get the system (superuser) settings for fallback keys."""
        if self._system_settings_loaded:
            return self._system_settings
        
        try:
            from sqlalchemy import select
            from app.db.models.user import User
            
            # Find the first superuser
            stmt = (
                select(UserSettings)
                .join(User)
                .where(User.is_superuser == True)
                .limit(1)
            )
            result = await self.db.execute(stmt)
            self._system_settings = result.scalar_one_or_none()
            self._system_settings_loaded = True
            
            if not self._system_settings:
                # Fallback: get settings from user with lowest ID (usually admin)
                stmt = select(UserSettings).order_by(UserSettings.user_id).limit(1)
                result = await self.db.execute(stmt)
                self._system_settings = result.scalar_one_or_none()
                
        except Exception as e:
            logger.warning(f"Could not load system settings: {e}")
            self._system_settings_loaded = True
            
        return self._system_settings
    
    def _get_db_attr_name(self, provider: str) -> str:
        """Get the database attribute name for a provider."""
        db_name = PROVIDER_DB_NAMES.get(provider, provider)
        return f"api_key_{db_name}"
    
    def _get_key_from_settings(self, settings: UserSettings, provider: str) -> Optional[str]:
        """Extract and decrypt API key from settings object."""
        if not settings:
            return None
        
        attr_name = self._get_db_attr_name(provider)
        if not hasattr(settings, attr_name):
            return None
        
        encrypted = getattr(settings, attr_name)
        if not encrypted:
            return None
        
        return settings.decrypt_api_key(encrypted)
    
    def _get_key_from_env(self, provider: str) -> Optional[str]:
        """Get API key from environment variable."""
        env_var = ENV_VAR_MAPPINGS.get(provider)
        if env_var:
            return os.getenv(env_var)
        return None
    
    async def get_api_key(
        self, 
        provider: str, 
        user_settings: Optional[UserSettings] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get API key for a provider with hierarchical fallback.
        
        Args:
            provider: Provider name (e.g., "finnhub", "polygon")
            user_settings: User's settings object (optional)
            
        Returns:
            Tuple of (api_key, source) where source is one of:
            - "personal": User's own key
            - "system": System/admin key
            - "environment": From environment variable
            - None: No key found
        """
        # 1. Try user's personal key
        if user_settings:
            key = self._get_key_from_settings(user_settings, provider)
            if key:
                return key, ApiKeySource.PERSONAL
        
        # 2. Try system key (superuser)
        system_settings = await self._get_system_settings()
        if system_settings:
            key = self._get_key_from_settings(system_settings, provider)
            if key:
                return key, ApiKeySource.SYSTEM
        
        # 3. Try environment variable
        key = self._get_key_from_env(provider)
        if key:
            return key, ApiKeySource.ENVIRONMENT
        
        return None, ApiKeySource.NONE
    
    async def get_all_api_keys(
        self, 
        user_settings: Optional[UserSettings] = None
    ) -> Dict[str, Tuple[str, str]]:
        """
        Get all available API keys with their sources.
        
        Returns:
            Dictionary mapping provider names to (key, source) tuples
        """
        all_providers = list(PROVIDER_DB_NAMES.keys())
        result = {}
        
        for provider in all_providers:
            key, source = await self.get_api_key(provider, user_settings)
            if key:
                result[provider] = (key, source)
        
        return result
    
    async def get_provider_status(
        self, 
        user_settings: Optional[UserSettings] = None
    ) -> Dict[str, Dict]:
        """
        Get status of all providers for the settings UI.
        
        Returns:
            Dictionary with provider info including:
            - has_key: bool
            - source: "personal" | "system" | "environment" | None
            - is_personal: bool
        """
        all_providers = list(PROVIDER_DB_NAMES.keys())
        result = {}
        
        for provider in all_providers:
            key, source = await self.get_api_key(provider, user_settings)
            
            # Check if user has personal key
            has_personal = False
            if user_settings:
                personal_key = self._get_key_from_settings(user_settings, provider)
                has_personal = bool(personal_key)
            
            result[provider] = {
                "has_key": bool(key),
                "source": source,
                "is_personal": has_personal,
            }
        
        return result


async def get_api_keys_for_providers(
    db: AsyncSession,
    user_id: Optional[int] = None
) -> Dict[str, str]:
    """
    Convenience function to get all API keys for provider initialization.
    
    This is used by provider_init.py and main.py to load keys.
    
    Args:
        db: Database session
        user_id: Optional user ID (if None, uses system keys)
        
    Returns:
        Dictionary mapping provider names to API keys
    """
    from sqlalchemy import select
    
    service = ApiKeyService(db)
    user_settings = None
    
    if user_id:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await db.execute(stmt)
        user_settings = result.scalar_one_or_none()
    
    all_keys = await service.get_all_api_keys(user_settings)
    
    # Return just the keys (not sources) for backward compatibility
    return {provider: key for provider, (key, source) in all_keys.items()}
