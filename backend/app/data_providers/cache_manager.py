"""
Cache Manager

Redis-based caching layer for market data.
Supports different TTLs for quotes, historical data, and metadata.
"""
import json
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, TypeVar, Generic, Any, Callable
from loguru import logger

from app.db.redis_client import redis_client
from app.data_providers.adapters.base import Quote, OHLCV, MarketType, TimeFrame


T = TypeVar('T')


@dataclass
class CacheConfig:
    """Cache configuration."""
    # TTL in seconds for different data types
    quote_ttl: int = 5              # Real-time quotes: 5 seconds
    historical_ttl: int = 3600      # Historical data: 1 hour
    metadata_ttl: int = 86400       # Metadata: 24 hours
    
    # Key prefixes
    prefix: str = "market"
    
    # Compression threshold (bytes)
    compress_threshold: int = 1024
    
    # Max items in list caches
    max_list_size: int = 1000


class CacheSerializer:
    """Handles serialization/deserialization of cached data."""
    
    @staticmethod
    def serialize_quote(quote: Quote) -> str:
        """Serialize a Quote to JSON string."""
        return json.dumps(quote.to_dict())
    
    @staticmethod
    def deserialize_quote(data: str) -> Quote:
        """Deserialize a Quote from JSON string."""
        d = json.loads(data)
        return Quote(
            symbol=d["symbol"],
            price=Decimal(str(d["price"])),
            bid=Decimal(str(d["bid"])) if d.get("bid") else None,
            ask=Decimal(str(d["ask"])) if d.get("ask") else None,
            bid_size=d.get("bid_size"),
            ask_size=d.get("ask_size"),
            volume=d.get("volume"),
            timestamp=datetime.fromisoformat(d["timestamp"]),
            provider=d.get("provider", ""),
            market_type=MarketType(d.get("market_type", "us_stock")),
            change=Decimal(str(d["change"])) if d.get("change") else None,
            change_percent=Decimal(str(d["change_percent"])) if d.get("change_percent") else None,
            day_high=Decimal(str(d["day_high"])) if d.get("day_high") else None,
            day_low=Decimal(str(d["day_low"])) if d.get("day_low") else None,
            day_open=Decimal(str(d["day_open"])) if d.get("day_open") else None,
            prev_close=Decimal(str(d["prev_close"])) if d.get("prev_close") else None,
            exchange=d.get("exchange"),
            currency=d.get("currency", "USD"),
        )
    
    @staticmethod
    def serialize_ohlcv(ohlcv: OHLCV) -> str:
        """Serialize an OHLCV to JSON string."""
        return json.dumps(ohlcv.to_dict())
    
    @staticmethod
    def deserialize_ohlcv(data: str) -> OHLCV:
        """Deserialize an OHLCV from JSON string."""
        d = json.loads(data)
        return OHLCV(
            symbol=d["symbol"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            open=Decimal(str(d["open"])),
            high=Decimal(str(d["high"])),
            low=Decimal(str(d["low"])),
            close=Decimal(str(d["close"])),
            volume=d["volume"],
            provider=d.get("provider", ""),
            timeframe=TimeFrame(d.get("timeframe", "1day")),
            adjusted_close=Decimal(str(d["adjusted_close"])) if d.get("adjusted_close") else None,
            vwap=Decimal(str(d["vwap"])) if d.get("vwap") else None,
            trade_count=d.get("trade_count"),
        )
    
    @staticmethod
    def serialize_ohlcv_list(ohlcv_list: list[OHLCV]) -> str:
        """Serialize a list of OHLCV to JSON string."""
        return json.dumps([o.to_dict() for o in ohlcv_list])
    
    @staticmethod
    def deserialize_ohlcv_list(data: str) -> list[OHLCV]:
        """Deserialize a list of OHLCV from JSON string."""
        items = json.loads(data)
        return [CacheSerializer.deserialize_ohlcv(json.dumps(d)) for d in items]


class CacheManager:
    """
    Redis-based cache manager for market data.
    
    Features:
    - Separate TTLs for quotes, historical, and metadata
    - Automatic serialization/deserialization
    - Batch operations for efficiency
    - Cache invalidation patterns
    - Statistics tracking
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }
    
    def _key(self, *parts: str) -> str:
        """Build a cache key from parts."""
        return f"{self.config.prefix}:{':'.join(parts)}"
    
    # ==================== Quote Caching ====================
    
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get a cached quote for a symbol."""
        key = self._key("quote", symbol.upper())
        
        try:
            data = await redis_client.client.get(key)
            if data:
                self._stats["hits"] += 1
                return CacheSerializer.deserialize_quote(data)
            self._stats["misses"] += 1
            return None
        except Exception as e:
            logger.error(f"Cache get error for {symbol}: {e}")
            return None
    
    async def set_quote(self, quote: Quote) -> None:
        """Cache a quote."""
        key = self._key("quote", quote.symbol.upper())
        
        try:
            data = CacheSerializer.serialize_quote(quote)
            await redis_client.client.setex(key, self.config.quote_ttl, data)
            self._stats["sets"] += 1
        except Exception as e:
            logger.error(f"Cache set error for {quote.symbol}: {e}")
    
    async def get_quotes(self, symbols: list[str]) -> dict[str, Optional[Quote]]:
        """Get cached quotes for multiple symbols."""
        result: dict[str, Optional[Quote]] = {}
        
        # Build keys
        keys = [self._key("quote", s.upper()) for s in symbols]
        
        try:
            # Use pipeline for batch get
            values = await redis_client.client.mget(keys)
            
            for symbol, value in zip(symbols, values):
                if value:
                    result[symbol.upper()] = CacheSerializer.deserialize_quote(value)
                    self._stats["hits"] += 1
                else:
                    result[symbol.upper()] = None
                    self._stats["misses"] += 1
            
            return result
        except Exception as e:
            logger.error(f"Cache mget error: {e}")
            return {s.upper(): None for s in symbols}
    
    async def set_quotes(self, quotes: list[Quote]) -> None:
        """Cache multiple quotes."""
        if not quotes:
            return
        
        try:
            # Use pipeline for batch set
            pipe = redis_client.client.pipeline()
            
            for quote in quotes:
                key = self._key("quote", quote.symbol.upper())
                data = CacheSerializer.serialize_quote(quote)
                pipe.setex(key, self.config.quote_ttl, data)
            
            await pipe.execute()
            self._stats["sets"] += len(quotes)
        except Exception as e:
            logger.error(f"Cache mset error: {e}")
    
    # ==================== Historical Data Caching ====================
    
    async def get_historical(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start_date: str,
        end_date: str,
    ) -> Optional[list[OHLCV]]:
        """Get cached historical data."""
        key = self._key(
            "historical", 
            symbol.upper(), 
            timeframe.value,
            start_date,
            end_date
        )
        
        try:
            data = await redis_client.client.get(key)
            if data:
                self._stats["hits"] += 1
                return CacheSerializer.deserialize_ohlcv_list(data)
            self._stats["misses"] += 1
            return None
        except Exception as e:
            logger.error(f"Cache get historical error for {symbol}: {e}")
            return None
    
    async def set_historical(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start_date: str,
        end_date: str,
        data: list[OHLCV],
    ) -> None:
        """Cache historical data."""
        key = self._key(
            "historical",
            symbol.upper(),
            timeframe.value,
            start_date,
            end_date
        )
        
        try:
            serialized = CacheSerializer.serialize_ohlcv_list(data)
            await redis_client.client.setex(key, self.config.historical_ttl, serialized)
            self._stats["sets"] += 1
        except Exception as e:
            logger.error(f"Cache set historical error for {symbol}: {e}")
    
    # ==================== Latest Bar Caching ====================
    
    async def get_latest_bar(
        self, 
        symbol: str, 
        timeframe: TimeFrame = TimeFrame.DAY
    ) -> Optional[OHLCV]:
        """Get the latest cached OHLCV bar for a symbol."""
        key = self._key("bar", symbol.upper(), timeframe.value, "latest")
        
        try:
            data = await redis_client.client.get(key)
            if data:
                self._stats["hits"] += 1
                return CacheSerializer.deserialize_ohlcv(data)
            self._stats["misses"] += 1
            return None
        except Exception as e:
            logger.error(f"Cache get bar error for {symbol}: {e}")
            return None
    
    async def set_latest_bar(self, bar: OHLCV) -> None:
        """Cache the latest OHLCV bar."""
        key = self._key("bar", bar.symbol.upper(), bar.timeframe.value, "latest")
        
        try:
            data = CacheSerializer.serialize_ohlcv(bar)
            # Use historical TTL for bars
            await redis_client.client.setex(key, self.config.historical_ttl, data)
            self._stats["sets"] += 1
        except Exception as e:
            logger.error(f"Cache set bar error for {bar.symbol}: {e}")
    
    # ==================== Metadata Caching ====================
    
    async def get_metadata(self, key: str) -> Optional[dict[str, Any]]:
        """Get cached metadata."""
        cache_key = self._key("meta", key)
        
        try:
            data = await redis_client.client.get(cache_key)
            if data:
                self._stats["hits"] += 1
                return json.loads(data)
            self._stats["misses"] += 1
            return None
        except Exception as e:
            logger.error(f"Cache get metadata error for {key}: {e}")
            return None
    
    async def set_metadata(self, key: str, value: dict[str, Any]) -> None:
        """Cache metadata."""
        cache_key = self._key("meta", key)
        
        try:
            data = json.dumps(value)
            await redis_client.client.setex(cache_key, self.config.metadata_ttl, data)
            self._stats["sets"] += 1
        except Exception as e:
            logger.error(f"Cache set metadata error for {key}: {e}")
    
    # ==================== Cache Invalidation ====================
    
    async def invalidate_quote(self, symbol: str) -> None:
        """Invalidate cached quote for a symbol."""
        key = self._key("quote", symbol.upper())
        
        try:
            await redis_client.client.delete(key)
            self._stats["deletes"] += 1
        except Exception as e:
            logger.error(f"Cache invalidate error for {symbol}: {e}")
    
    async def invalidate_historical(
        self,
        symbol: str,
        timeframe: Optional[TimeFrame] = None,
    ) -> None:
        """Invalidate cached historical data for a symbol."""
        pattern = self._key("historical", symbol.upper(), "*")
        if timeframe:
            pattern = self._key("historical", symbol.upper(), timeframe.value, "*")
        
        try:
            keys = await redis_client.client.keys(pattern)
            if keys:
                await redis_client.client.delete(*keys)
                self._stats["deletes"] += len(keys)
        except Exception as e:
            logger.error(f"Cache invalidate historical error for {symbol}: {e}")
    
    async def invalidate_all(self, symbol: str) -> None:
        """Invalidate all cached data for a symbol."""
        patterns = [
            self._key("quote", symbol.upper()),
            self._key("historical", symbol.upper(), "*"),
            self._key("bar", symbol.upper(), "*"),
        ]
        
        try:
            for pattern in patterns:
                keys = await redis_client.client.keys(pattern)
                if keys:
                    await redis_client.client.delete(*keys)
                    self._stats["deletes"] += len(keys)
        except Exception as e:
            logger.error(f"Cache invalidate all error for {symbol}: {e}")
    
    async def clear_all(self) -> None:
        """Clear all market data cache."""
        pattern = f"{self.config.prefix}:*"
        
        try:
            keys = await redis_client.client.keys(pattern)
            if keys:
                await redis_client.client.delete(*keys)
                self._stats["deletes"] += len(keys)
            logger.info(f"Cleared {len(keys)} cache entries")
        except Exception as e:
            logger.error(f"Cache clear all error: {e}")
    
    # ==================== Cache Stats ====================
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        
        return {
            **self._stats,
            "total_requests": total,
            "hit_rate": round(hit_rate * 100, 2),
        }
    
    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }


# Global cache manager instance
cache_manager = CacheManager()


# ==================== Cache Decorator ====================

def cached_quote(ttl: Optional[int] = None):
    """
    Decorator for caching quote results.
    
    Usage:
        @cached_quote(ttl=10)
        async def get_quote(symbol: str) -> Quote:
            ...
    """
    def decorator(func: Callable):
        async def wrapper(symbol: str, *args, **kwargs) -> Quote:
            # Try cache first
            cached = await cache_manager.get_quote(symbol)
            if cached:
                return cached
            
            # Call original function
            result = await func(symbol, *args, **kwargs)
            
            # Cache result
            if result:
                await cache_manager.set_quote(result)
            
            return result
        return wrapper
    return decorator


def cached_historical(ttl: Optional[int] = None):
    """
    Decorator for caching historical data results.
    
    Usage:
        @cached_historical()
        async def get_historical(symbol: str, timeframe: TimeFrame, start: str, end: str) -> list[OHLCV]:
            ...
    """
    def decorator(func: Callable):
        async def wrapper(
            symbol: str, 
            timeframe: TimeFrame,
            start_date: str,
            end_date: str,
            *args, 
            **kwargs
        ) -> list[OHLCV]:
            # Try cache first
            cached = await cache_manager.get_historical(symbol, timeframe, start_date, end_date)
            if cached:
                return cached
            
            # Call original function
            result = await func(symbol, timeframe, start_date, end_date, *args, **kwargs)
            
            # Cache result
            if result:
                await cache_manager.set_historical(symbol, timeframe, start_date, end_date, result)
            
            return result
        return wrapper
    return decorator
