"""
Rate Limiter

Implements token bucket algorithm with per-provider rate limiting.
Supports multiple rate limit windows (per second, minute, day).
"""
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: Optional[int] = None
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    burst_size: int = 10  # Maximum burst requests allowed


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: float
    tokens: float
    fill_rate: float  # tokens per second
    last_update: datetime = field(default_factory=datetime.utcnow)
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Returns:
            True if tokens were consumed, False if bucket is empty
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.utcnow()
        elapsed = (now - self.last_update).total_seconds()
        self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
        self.last_update = now
    
    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate seconds until tokens are available."""
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.fill_rate


@dataclass
class WindowCounter:
    """Sliding window counter for rate limiting."""
    limit: int
    window_seconds: int
    requests: list[datetime] = field(default_factory=list)
    
    def can_proceed(self) -> bool:
        """Check if we can make a request within the limit."""
        self._cleanup()
        return len(self.requests) < self.limit
    
    def record_request(self) -> None:
        """Record a new request."""
        self._cleanup()
        self.requests.append(datetime.utcnow())
    
    def _cleanup(self) -> None:
        """Remove expired requests from the window."""
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_seconds)
        self.requests = [r for r in self.requests if r > cutoff]
    
    def time_until_available(self) -> float:
        """Calculate seconds until a slot is available."""
        self._cleanup()
        if len(self.requests) < self.limit:
            return 0.0
        
        oldest = min(self.requests)
        wait_until = oldest + timedelta(seconds=self.window_seconds)
        wait_time = (wait_until - datetime.utcnow()).total_seconds()
        return max(0.0, wait_time)
    
    def remaining(self) -> int:
        """Get remaining requests in current window."""
        self._cleanup()
        return max(0, self.limit - len(self.requests))


class RateLimiter:
    """
    Rate limiter with support for multiple time windows.
    
    Uses a combination of token bucket (for burst control) and
    sliding window counters (for hard limits per time period).
    """
    
    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}
        self._minute_counters: dict[str, WindowCounter] = {}
        self._hour_counters: dict[str, WindowCounter] = {}
        self._day_counters: dict[str, WindowCounter] = {}
        self._configs: dict[str, RateLimitConfig] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        
    def configure(self, provider: str, config: RateLimitConfig) -> None:
        """Configure rate limits for a provider."""
        self._configs[provider] = config
        
        # Create token bucket for burst control
        # Use requests per minute as base, default to 60
        rpm = config.requests_per_minute or 60
        self._buckets[provider] = TokenBucket(
            capacity=min(config.burst_size, rpm),
            tokens=min(config.burst_size, rpm),
            fill_rate=rpm / 60.0,  # tokens per second
        )
        
        # Create window counters for each limit
        if config.requests_per_minute:
            self._minute_counters[provider] = WindowCounter(
                limit=config.requests_per_minute,
                window_seconds=60,
            )
        
        if config.requests_per_hour:
            self._hour_counters[provider] = WindowCounter(
                limit=config.requests_per_hour,
                window_seconds=3600,
            )
        
        if config.requests_per_day:
            self._day_counters[provider] = WindowCounter(
                limit=config.requests_per_day,
                window_seconds=86400,
            )
        
        logger.info(f"Rate limiter configured for {provider}: {config}")
    
    async def acquire(self, provider: str, tokens: int = 1) -> bool:
        """
        Acquire tokens for making a request.
        
        This method will wait if necessary until tokens are available.
        
        Args:
            provider: Provider name
            tokens: Number of tokens to acquire (usually 1)
            
        Returns:
            True if tokens were acquired
        """
        if provider not in self._configs:
            # No rate limit configured, allow all
            return True
        
        async with self._locks[provider]:
            # Check all limits
            wait_time = self._calculate_wait_time(provider, tokens)
            
            if wait_time > 0:
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {provider}")
                await asyncio.sleep(wait_time)
            
            # Consume from bucket and record in counters
            bucket = self._buckets.get(provider)
            if bucket:
                bucket.consume(tokens)
            
            minute_counter = self._minute_counters.get(provider)
            if minute_counter:
                minute_counter.record_request()
            
            hour_counter = self._hour_counters.get(provider)
            if hour_counter:
                hour_counter.record_request()
            
            day_counter = self._day_counters.get(provider)
            if day_counter:
                day_counter.record_request()
            
            return True
    
    def can_proceed(self, provider: str) -> bool:
        """
        Check if a request can proceed without waiting.
        
        Args:
            provider: Provider name
            
        Returns:
            True if request can proceed immediately
        """
        if provider not in self._configs:
            return True
        
        return self._calculate_wait_time(provider) == 0.0
    
    def _calculate_wait_time(self, provider: str, tokens: int = 1) -> float:
        """Calculate how long to wait before a request can proceed."""
        wait_times = []
        
        bucket = self._buckets.get(provider)
        if bucket:
            wait_times.append(bucket.time_until_available(tokens))
        
        minute_counter = self._minute_counters.get(provider)
        if minute_counter:
            wait_times.append(minute_counter.time_until_available())
        
        hour_counter = self._hour_counters.get(provider)
        if hour_counter:
            wait_times.append(hour_counter.time_until_available())
        
        day_counter = self._day_counters.get(provider)
        if day_counter:
            wait_times.append(day_counter.time_until_available())
        
        return max(wait_times) if wait_times else 0.0
    
    def get_remaining(self, provider: str) -> dict[str, int]:
        """
        Get remaining requests for each time window.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary with remaining requests per window
        """
        result = {}
        
        minute_counter = self._minute_counters.get(provider)
        if minute_counter:
            result["per_minute"] = minute_counter.remaining()
        
        hour_counter = self._hour_counters.get(provider)
        if hour_counter:
            result["per_hour"] = hour_counter.remaining()
        
        day_counter = self._day_counters.get(provider)
        if day_counter:
            result["per_day"] = day_counter.remaining()
        
        return result
    
    def get_stats(self, provider: str) -> dict:
        """Get rate limiter statistics for a provider."""
        config = self._configs.get(provider)
        if not config:
            return {"configured": False}
        
        remaining = self.get_remaining(provider)
        
        return {
            "configured": True,
            "limits": {
                "per_minute": config.requests_per_minute,
                "per_hour": config.requests_per_hour,
                "per_day": config.requests_per_day,
                "burst_size": config.burst_size,
            },
            "remaining": remaining,
            "can_proceed": self.can_proceed(provider),
            "wait_time": self._calculate_wait_time(provider),
        }
    
    def reset_daily(self, provider: str) -> None:
        """Reset daily counter for a provider."""
        if provider in self._day_counters:
            self._day_counters[provider] = WindowCounter(
                limit=self._day_counters[provider].limit,
                window_seconds=86400,
            )
            logger.info(f"Daily rate limit reset for {provider}")


# Global rate limiter instance
rate_limiter = RateLimiter()
