"""
FX Rate Service

Manages exchange rate caching and real-time updates.

HYBRID ARCHITECTURE:
1. Frankfurter API (BCE) - Bulk fetch all rates, fallback, daily precision
2. Alpha Vantage - Real-time rates for ACTIVE currency pairs only

Strategy:
- Every 5 min: Fetch all rates from Frankfurter (1 API call = all currencies)
- On-demand: Fetch real-time rate from Alpha Vantage for active pairs
- Cache in Redis with 6-min TTL
- Smart rate limiting: only fetch pairs actually used in portfolios
"""
import asyncio
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Set
import httpx
from loguru import logger

from app.db.redis_client import redis_client
from app.config import settings


# Redis key prefixes
FX_RATE_KEY_PREFIX = "fx_rate:"
FX_RATES_ALL_KEY = "fx_rates:all"
FX_RATES_TIMESTAMP_KEY = "fx_rates:timestamp"
FX_ACTIVE_PAIRS_KEY = "fx_rates:active_pairs"
FX_REALTIME_PREFIX = "fx_rate:realtime:"

# Cache TTL
FX_RATE_TTL = 360  # 6 minutes for bulk rates
FX_REALTIME_TTL = 120  # 2 minutes for real-time rates

# Supported currency pairs (base -> quote)
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "HKD", "SGD", "CNY"]

# Fallback rates (USD as base) - used if API fails
FALLBACK_RATES_USD = {
    "USD": 1.0,
    "EUR": 0.95,
    "GBP": 0.79,
    "JPY": 149.50,
    "CHF": 0.88,
    "CAD": 1.36,
    "AUD": 1.53,
    "HKD": 7.78,
    "SGD": 1.34,
    "CNY": 7.25,
}

# Alpha Vantage API
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


class FXRateService:
    """
    Foreign Exchange Rate Service.
    
    HYBRID STRATEGY:
    - Frankfurter (BCE): Bulk rates, 1 call = all currencies, daily precision
    - Alpha Vantage: Real-time rates for specific pairs, limited calls
    
    Provides:
    - Real-time FX rate fetching and caching
    - Smart rate limiting (only fetch active pairs)
    - Rate conversion utilities
    - WebSocket broadcast support
    """
    
    def __init__(self):
        self._last_fetch_time: Optional[datetime] = None
        self._frankfurter_url = "https://api.frankfurter.app/latest"
        self._alpha_vantage_url = ALPHA_VANTAGE_URL
        self._alpha_vantage_key: Optional[str] = None
        self._active_pairs: Set[str] = set()  # Track which pairs need real-time updates
        self._in_memory_rates: Dict[str, float] = {}  # In-memory cache fallback
    
    def _get_alpha_vantage_key(self) -> Optional[str]:
        """Get Alpha Vantage API key from settings."""
        if self._alpha_vantage_key is None:
            try:
                self._alpha_vantage_key = settings.ALPHA_VANTAGE_API_KEY
            except Exception:
                self._alpha_vantage_key = ""
        return self._alpha_vantage_key if self._alpha_vantage_key else None
    
    async def fetch_and_cache_rates(self, base_currency: str = "USD") -> Dict[str, float]:
        """
        Fetch latest rates from Frankfurter API (bulk) and cache in Redis.
        
        This is the PRIMARY rate fetch - gets ALL currencies in one call.
        Called every 5 minutes by scheduler.
        
        Args:
            base_currency: Base currency for rates (default USD)
            
        Returns:
            Dict of currency -> rate
        """
        rates = await self._fetch_from_frankfurter(base_currency)
        
        if rates:
            await self._cache_rates(rates, base_currency)
            self._in_memory_rates = rates.copy()  # Update in-memory fallback
            self._last_fetch_time = datetime.utcnow()
            logger.info(f"FX rates (Frankfurter): {len(rates)} currencies")
        
        return rates
    
    async def fetch_realtime_rate(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """
        Fetch real-time rate from Alpha Vantage for a specific pair.
        
        Used for ACTIVE pairs that need intraday precision.
        Rate-limited: only call when necessary.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Exchange rate or None if unavailable
        """
        api_key = self._get_alpha_vantage_key()
        if not api_key:
            logger.debug("Alpha Vantage API key not configured, using cached rate")
            return None
        
        pair_key = f"{from_currency}_{to_currency}"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self._alpha_vantage_url,
                    params={
                        "function": "CURRENCY_EXCHANGE_RATE",
                        "from_currency": from_currency.upper(),
                        "to_currency": to_currency.upper(),
                        "apikey": api_key
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for rate limit message
                    if "Note" in data:
                        logger.warning("Alpha Vantage rate limit reached")
                        return None
                    
                    rate_data = data.get("Realtime Currency Exchange Rate", {})
                    if rate_data:
                        rate = Decimal(str(rate_data.get("5. Exchange Rate", 0)))
                        
                        if rate > 0:
                            # Cache the real-time rate
                            await self._cache_realtime_rate(from_currency, to_currency, rate)
                            logger.debug(f"FX real-time (Alpha Vantage): {from_currency}/{to_currency} = {rate}")
                            return rate
                            
        except Exception as e:
            logger.error(f"Alpha Vantage FX fetch failed: {e}")
        
        return None
    
    async def _cache_realtime_rate(self, from_curr: str, to_curr: str, rate: Decimal) -> None:
        """Cache a real-time rate with shorter TTL."""
        try:
            client = redis_client.client
            key = f"{FX_REALTIME_PREFIX}{from_curr}_{to_curr}"
            await client.setex(key, FX_REALTIME_TTL, str(rate))
        except Exception as e:
            logger.debug(f"Failed to cache real-time rate: {e}")
    
    async def _get_realtime_rate(self, from_curr: str, to_curr: str) -> Optional[Decimal]:
        """Get cached real-time rate if available."""
        try:
            client = redis_client.client
            key = f"{FX_REALTIME_PREFIX}{from_curr}_{to_curr}"
            value = await client.get(key)
            if value:
                return Decimal(value)
        except Exception:
            pass
        return None
    
    def register_active_pair(self, from_currency: str, to_currency: str) -> None:
        """
        Register a currency pair as "active" (needs real-time updates).
        
        Called when a position uses a specific currency pair.
        """
        pair = f"{from_currency}_{to_currency}"
        if pair not in self._active_pairs and from_currency != to_currency:
            self._active_pairs.add(pair)
            logger.debug(f"Registered active FX pair: {pair}")
    
    def get_active_pairs(self) -> List[str]:
        """Get list of active currency pairs needing real-time updates."""
        return list(self._active_pairs)
    
    async def update_active_pairs_realtime(self) -> Dict[str, Decimal]:
        """
        Fetch real-time rates ONLY for active pairs.
        
        This is the SMART update - only fetches pairs actually in use.
        Called less frequently or on-demand.
        
        Returns:
            Dict of pair -> rate for successfully updated pairs
        """
        if not self._active_pairs:
            return {}
        
        api_key = self._get_alpha_vantage_key()
        if not api_key:
            return {}
        
        updated = {}
        
        for pair in list(self._active_pairs):
            from_curr, to_curr = pair.split("_")
            rate = await self.fetch_realtime_rate(from_curr, to_curr)
            if rate:
                updated[pair] = rate
            
            # Rate limiting: wait between calls
            await asyncio.sleep(12)  # Alpha Vantage: 5 calls/min = 12s between
        
        if updated:
            logger.info(f"FX real-time update: {len(updated)} pairs updated")
        
        return updated
    
    async def _fetch_from_frankfurter(self, base: str) -> Dict[str, float]:
        """Fetch bulk rates from Frankfurter API (1 call = all currencies)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self._frankfurter_url,
                    params={"from": base}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    rates = data.get("rates", {})
                    
                    # Add base currency with rate 1.0
                    rates[base] = 1.0
                    
                    # Filter to supported currencies
                    filtered_rates = {
                        curr: rates.get(curr, FALLBACK_RATES_USD.get(curr, 1.0))
                        for curr in SUPPORTED_CURRENCIES
                        if curr in rates or curr in FALLBACK_RATES_USD
                    }
                    
                    return filtered_rates
                else:
                    logger.warning(f"Frankfurter API returned status {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Failed to fetch FX rates from Frankfurter: {e}")
        
        # Return fallback rates on failure
        return FALLBACK_RATES_USD.copy()
    
    async def _cache_rates(self, rates: Dict[str, float], base: str) -> None:
        """Cache rates in Redis."""
        try:
            client = redis_client.client
            
            # Store individual rates
            pipe = client.pipeline()
            for currency, rate in rates.items():
                key = f"{FX_RATE_KEY_PREFIX}{base}_{currency}"
                pipe.setex(key, FX_RATE_TTL, str(rate))
            
            # Store all rates as JSON for bulk retrieval
            all_rates_data = {
                "base": base,
                "rates": rates,
                "timestamp": datetime.utcnow().isoformat()
            }
            pipe.setex(FX_RATES_ALL_KEY, FX_RATE_TTL, json.dumps(all_rates_data))
            pipe.setex(FX_RATES_TIMESTAMP_KEY, FX_RATE_TTL, datetime.utcnow().isoformat())
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Failed to cache FX rates: {e}")
    
    async def get_rate(self, from_currency: str, to_currency: str, prefer_realtime: bool = True) -> Decimal:
        """
        Get exchange rate between two currencies.
        
        Priority:
        1. Real-time rate from Alpha Vantage (if available and prefer_realtime=True)
        2. Cached bulk rate from Frankfurter/Redis
        3. In-memory fallback
        4. Static fallback rates
        
        Args:
            from_currency: Source currency (e.g., "USD")
            to_currency: Target currency (e.g., "EUR")
            prefer_realtime: Whether to prefer real-time rate if available
            
        Returns:
            Exchange rate as Decimal
        """
        if from_currency == to_currency:
            return Decimal("1.0")
        
        # Register this pair as active
        self.register_active_pair(from_currency, to_currency)
        
        # 1. Try real-time cached rate first (if prefer_realtime)
        if prefer_realtime:
            realtime_rate = await self._get_realtime_rate(from_currency, to_currency)
            if realtime_rate:
                return realtime_rate
        
        # 2. Try bulk cached rates from Redis
        try:
            client = redis_client.client
            
            # Try direct rate first (USD_EUR)
            direct_key = f"{FX_RATE_KEY_PREFIX}USD_{to_currency}"
            from_key = f"{FX_RATE_KEY_PREFIX}USD_{from_currency}"
            
            to_rate = await client.get(direct_key)
            from_rate = await client.get(from_key)
            
            if to_rate and from_rate:
                # Cross rate calculation: USD_EUR / USD_FROM
                to_rate_dec = Decimal(to_rate)
                from_rate_dec = Decimal(from_rate)
                
                if from_rate_dec > 0:
                    rate = (to_rate_dec / from_rate_dec).quantize(
                        Decimal("0.000001"), 
                        rounding=ROUND_HALF_UP
                    )
                    return rate
            
        except Exception as e:
            logger.error(f"Failed to get FX rate from cache: {e}")
        
        # 3. Try in-memory rates
        if self._in_memory_rates:
            to_mem = self._in_memory_rates.get(to_currency, 1.0)
            from_mem = self._in_memory_rates.get(from_currency, 1.0)
            if from_mem > 0:
                return Decimal(str(to_mem / from_mem)).quantize(Decimal("0.000001"))
        
        # 4. Static fallback calculation
        to_fallback = Decimal(str(FALLBACK_RATES_USD.get(to_currency, 1.0)))
        from_fallback = Decimal(str(FALLBACK_RATES_USD.get(from_currency, 1.0)))
        
        if from_fallback > 0:
            return (to_fallback / from_fallback).quantize(Decimal("0.000001"))
        return Decimal("1.0")
    
    async def get_all_rates(self, base: str = "USD") -> Dict[str, float]:
        """
        Get all cached rates.
        
        Args:
            base: Base currency
            
        Returns:
            Dict of currency -> rate
        """
        try:
            client = redis_client.client
            data = await client.get(FX_RATES_ALL_KEY)
            
            if data:
                parsed = json.loads(data)
                if parsed.get("base") == base:
                    return parsed.get("rates", {})
        except Exception as e:
            logger.error(f"Failed to get all FX rates: {e}")
        
        # Fetch fresh if not cached
        return await self.fetch_and_cache_rates(base)
    
    async def get_rates_timestamp(self) -> Optional[str]:
        """Get timestamp of last rate update."""
        try:
            client = redis_client.client
            return await client.get(FX_RATES_TIMESTAMP_KEY)
        except Exception:
            return None
    
    async def convert(
        self, 
        amount: Decimal, 
        from_currency: str, 
        to_currency: str
    ) -> tuple[Decimal, Decimal]:
        """
        Convert amount between currencies.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            Tuple of (converted_amount, exchange_rate)
        """
        rate = await self.get_rate(from_currency, to_currency)
        converted = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return converted, rate


# Global singleton instance
fx_rate_service = FXRateService()


# =============================================================================
# Scheduler Job Functions
# =============================================================================

async def update_fx_rates_job() -> Dict[str, any]:
    """
    Job function for scheduler to update FX rates.
    
    HYBRID STRATEGY:
    1. Fetch all rates from Frankfurter (1 call, all currencies)
    2. If active pairs exist & Alpha Vantage key configured, fetch real-time rates
    
    Called every 5 minutes by the bot scheduler.
    """
    logger.info("Running FX rate update job...")
    
    # Step 1: Bulk fetch from Frankfurter (always - 1 API call)
    rates = await fx_rate_service.fetch_and_cache_rates("USD")
    
    result = {
        "success": True,
        "frankfurter_rates": len(rates),
        "realtime_rates": 0,
        "active_pairs": fx_rate_service.get_active_pairs(),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Step 2: Real-time update for active pairs (only if Alpha Vantage configured)
    active_pairs = fx_rate_service.get_active_pairs()
    if active_pairs and fx_rate_service._get_alpha_vantage_key():
        logger.info(f"Updating {len(active_pairs)} active FX pairs with real-time rates...")
        realtime_updates = await fx_rate_service.update_active_pairs_realtime()
        result["realtime_rates"] = len(realtime_updates)
    
    # Broadcast update via Redis pub/sub
    try:
        await redis_client.publish(
            "fx_rates_updated",
            json.dumps({
                "rates": rates,
                "active_pairs": active_pairs,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
    except Exception as e:
        logger.error(f"Failed to broadcast FX rate update: {e}")
    
    logger.info(f"FX update complete: {result['frankfurter_rates']} bulk, {result['realtime_rates']} real-time")
    return result
