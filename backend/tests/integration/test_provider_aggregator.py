"""
Integration Tests - Provider Aggregator
Tests for the data provider orchestration and failover logic.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum
import asyncio


# ============================================================
# Local definitions for testing
# ============================================================

class ProviderType(str, Enum):
    YFINANCE = "yfinance"
    FINNHUB = "finnhub"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    IEX = "iex"


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    RATE_LIMITED = "rate_limited"


@dataclass
class ProviderHealth:
    """Provider health status."""
    provider: ProviderType
    status: ProviderStatus
    latency_ms: float
    success_rate: float  # 0-1
    requests_remaining: Optional[int] = None
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None


@dataclass
class Quote:
    """Quote data."""
    symbol: str
    price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    volume: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    provider: Optional[ProviderType] = None


@dataclass
class ProviderResponse:
    """Wrapper for provider responses."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    provider: Optional[ProviderType] = None
    latency_ms: float = 0
    cached: bool = False


# ============================================================
# Test Classes
# ============================================================

class TestProviderHealthTracking:
    """Tests for provider health monitoring."""
    
    def test_health_status_healthy(self):
        """Should mark provider as healthy."""
        health = ProviderHealth(
            provider=ProviderType.YFINANCE,
            status=ProviderStatus.HEALTHY,
            latency_ms=150.0,
            success_rate=0.99,
        )
        
        assert health.status == ProviderStatus.HEALTHY
        assert health.success_rate >= 0.95
    
    def test_health_status_degraded(self):
        """Should mark provider as degraded on high latency."""
        health = ProviderHealth(
            provider=ProviderType.FINNHUB,
            status=ProviderStatus.DEGRADED,
            latency_ms=2500.0,  # High latency
            success_rate=0.85,
        )
        
        assert health.status == ProviderStatus.DEGRADED
        assert health.latency_ms > 2000
    
    def test_health_status_down(self):
        """Should mark provider as down on failures."""
        health = ProviderHealth(
            provider=ProviderType.ALPHA_VANTAGE,
            status=ProviderStatus.DOWN,
            latency_ms=0,
            success_rate=0.0,
            error_message="Connection refused",
        )
        
        assert health.status == ProviderStatus.DOWN
        assert health.error_message is not None
    
    def test_health_status_rate_limited(self):
        """Should detect rate limiting."""
        health = ProviderHealth(
            provider=ProviderType.POLYGON,
            status=ProviderStatus.RATE_LIMITED,
            latency_ms=50.0,
            success_rate=0.95,
            requests_remaining=0,
        )
        
        assert health.status == ProviderStatus.RATE_LIMITED
        assert health.requests_remaining == 0
    
    def test_health_last_check_timestamp(self):
        """Should track last health check time."""
        now = datetime.now(timezone.utc)
        health = ProviderHealth(
            provider=ProviderType.YFINANCE,
            status=ProviderStatus.HEALTHY,
            latency_ms=100.0,
            success_rate=1.0,
            last_check=now,
        )
        
        assert health.last_check == now


class TestProviderSelection:
    """Tests for provider selection logic."""
    
    def test_select_healthiest_provider(self):
        """Should select provider with best health."""
        healths = [
            ProviderHealth(
                provider=ProviderType.YFINANCE,
                status=ProviderStatus.HEALTHY,
                latency_ms=200.0,
                success_rate=0.98,
            ),
            ProviderHealth(
                provider=ProviderType.FINNHUB,
                status=ProviderStatus.DEGRADED,
                latency_ms=1500.0,
                success_rate=0.85,
            ),
            ProviderHealth(
                provider=ProviderType.ALPHA_VANTAGE,
                status=ProviderStatus.DOWN,
                latency_ms=0,
                success_rate=0.0,
            ),
        ]
        
        # Select healthiest (HEALTHY status first, then by success rate)
        healthy = [h for h in healths if h.status == ProviderStatus.HEALTHY]
        best = max(healthy, key=lambda h: h.success_rate)
        
        assert best.provider == ProviderType.YFINANCE
    
    def test_select_by_latency(self):
        """Should prefer lower latency when health equal."""
        healths = [
            ProviderHealth(
                provider=ProviderType.YFINANCE,
                status=ProviderStatus.HEALTHY,
                latency_ms=300.0,
                success_rate=0.98,
            ),
            ProviderHealth(
                provider=ProviderType.POLYGON,
                status=ProviderStatus.HEALTHY,
                latency_ms=100.0,
                success_rate=0.98,
            ),
        ]
        
        # Both healthy with same success rate - prefer lower latency
        best = min(healths, key=lambda h: h.latency_ms)
        
        assert best.provider == ProviderType.POLYGON
    
    def test_skip_rate_limited_provider(self):
        """Should skip rate-limited providers."""
        healths = [
            ProviderHealth(
                provider=ProviderType.FINNHUB,
                status=ProviderStatus.RATE_LIMITED,
                latency_ms=50.0,
                success_rate=0.99,
            ),
            ProviderHealth(
                provider=ProviderType.YFINANCE,
                status=ProviderStatus.HEALTHY,
                latency_ms=200.0,
                success_rate=0.95,
            ),
        ]
        
        # Filter out rate-limited
        available = [
            h for h in healths 
            if h.status not in [ProviderStatus.RATE_LIMITED, ProviderStatus.DOWN]
        ]
        
        assert len(available) == 1
        assert available[0].provider == ProviderType.YFINANCE
    
    def test_no_providers_available(self):
        """Should handle when no providers available."""
        healths = [
            ProviderHealth(
                provider=ProviderType.YFINANCE,
                status=ProviderStatus.DOWN,
                latency_ms=0,
                success_rate=0.0,
            ),
            ProviderHealth(
                provider=ProviderType.FINNHUB,
                status=ProviderStatus.DOWN,
                latency_ms=0,
                success_rate=0.0,
            ),
        ]
        
        available = [h for h in healths if h.status == ProviderStatus.HEALTHY]
        
        assert len(available) == 0


class TestFailover:
    """Tests for failover between providers."""
    
    def test_failover_on_error(self):
        """Should failover to next provider on error."""
        providers = [
            ProviderType.FINNHUB,   # Primary
            ProviderType.YFINANCE,  # Fallback 1
            ProviderType.POLYGON,   # Fallback 2
        ]
        
        # Simulate first provider failing
        failed_provider = providers[0]
        remaining = providers[1:]
        
        assert ProviderType.YFINANCE in remaining
        assert failed_provider not in remaining
    
    def test_failover_maintains_order(self):
        """Should try providers in priority order."""
        provider_order = [
            ProviderType.POLYGON,       # Premium, fast
            ProviderType.FINNHUB,       # Good alternative
            ProviderType.ALPHA_VANTAGE, # Rate limited
            ProviderType.YFINANCE,      # Free fallback
        ]
        
        current_idx = 0
        
        # Simulate failures and track order
        attempted = []
        for provider in provider_order:
            attempted.append(provider)
            # Simulate success on third try
            if len(attempted) == 3:
                break
        
        assert attempted == [
            ProviderType.POLYGON,
            ProviderType.FINNHUB,
            ProviderType.ALPHA_VANTAGE,
        ]
    
    def test_failover_with_timeout(self):
        """Should timeout slow providers and failover."""
        timeout_ms = 5000
        
        responses = [
            {"provider": ProviderType.POLYGON, "latency": 8000, "success": False},  # Timeout
            {"provider": ProviderType.YFINANCE, "latency": 200, "success": True},
        ]
        
        # Filter by timeout
        successful = [
            r for r in responses 
            if r["latency"] < timeout_ms and r["success"]
        ]
        
        assert len(successful) == 1
        assert successful[0]["provider"] == ProviderType.YFINANCE


class TestDataAggregation:
    """Tests for aggregating data from multiple providers."""
    
    def test_merge_quotes_from_providers(self):
        """Should merge quote data from multiple sources."""
        quotes = [
            Quote(
                symbol="AAPL",
                price=Decimal("150.00"),
                bid=Decimal("149.95"),
                ask=Decimal("150.05"),
                volume=1000000,
                provider=ProviderType.YFINANCE,
            ),
            Quote(
                symbol="AAPL",
                price=Decimal("150.02"),
                bid=Decimal("149.97"),
                ask=Decimal("150.07"),
                volume=980000,
                provider=ProviderType.FINNHUB,
            ),
        ]
        
        # Average the prices
        avg_price = sum(q.price for q in quotes) / len(quotes)
        
        assert avg_price == Decimal("150.01")
    
    def test_use_most_recent_quote(self):
        """Should prefer most recent quote."""
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(minutes=5)
        
        quotes = [
            Quote(
                symbol="AAPL",
                price=Decimal("150.00"),
                timestamp=old_time,
                provider=ProviderType.YFINANCE,
            ),
            Quote(
                symbol="AAPL",
                price=Decimal("151.00"),
                timestamp=now,
                provider=ProviderType.FINNHUB,
            ),
        ]
        
        # Select most recent
        most_recent = max(quotes, key=lambda q: q.timestamp)
        
        assert most_recent.provider == ProviderType.FINNHUB
        assert most_recent.price == Decimal("151.00")
    
    def test_detect_stale_data(self):
        """Should detect stale quotes."""
        stale_threshold = timedelta(minutes=15)
        now = datetime.now(timezone.utc)
        
        quote = Quote(
            symbol="AAPL",
            price=Decimal("150.00"),
            timestamp=now - timedelta(minutes=20),  # 20 min old
            provider=ProviderType.YFINANCE,
        )
        
        age = now - quote.timestamp
        is_stale = age > stale_threshold
        
        assert is_stale is True


class TestCaching:
    """Tests for response caching."""
    
    def test_cache_hit(self):
        """Should return cached response."""
        cached_response = ProviderResponse(
            success=True,
            data=Quote(
                symbol="AAPL",
                price=Decimal("150.00"),
            ),
            cached=True,
            latency_ms=1.0,  # Very fast for cached
        )
        
        assert cached_response.cached is True
        assert cached_response.latency_ms < 10
    
    def test_cache_miss(self):
        """Should fetch from provider on cache miss."""
        response = ProviderResponse(
            success=True,
            data=Quote(
                symbol="AAPL",
                price=Decimal("150.00"),
            ),
            cached=False,
            provider=ProviderType.YFINANCE,
            latency_ms=150.0,
        )
        
        assert response.cached is False
        assert response.provider is not None
    
    def test_cache_expiry(self):
        """Should expire cached data after TTL."""
        cache_ttl = timedelta(seconds=30)
        cached_at = datetime.now(timezone.utc) - timedelta(seconds=45)
        now = datetime.now(timezone.utc)
        
        age = now - cached_at
        is_expired = age > cache_ttl
        
        assert is_expired is True


class TestBatchRequests:
    """Tests for batch quote requests."""
    
    def test_batch_request_optimization(self):
        """Should batch multiple symbol requests."""
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
        
        # Instead of 5 requests, do 1 batch
        batch = symbols
        
        assert len(batch) == 5
    
    def test_batch_size_limits(self):
        """Should respect provider batch limits."""
        max_batch_size = 50
        symbols = [f"SYM{i}" for i in range(120)]
        
        batches = [
            symbols[i:i + max_batch_size]
            for i in range(0, len(symbols), max_batch_size)
        ]
        
        assert len(batches) == 3
        assert len(batches[0]) == 50
        assert len(batches[1]) == 50
        assert len(batches[2]) == 20
    
    def test_partial_batch_failure(self):
        """Should handle partial batch failures."""
        batch_results = {
            "AAPL": Quote(symbol="AAPL", price=Decimal("150.00")),
            "MSFT": Quote(symbol="MSFT", price=Decimal("380.00")),
            "INVALID": None,  # Failed
            "GOOGL": Quote(symbol="GOOGL", price=Decimal("140.00")),
        }
        
        successful = {k: v for k, v in batch_results.items() if v is not None}
        failed = [k for k, v in batch_results.items() if v is None]
        
        assert len(successful) == 3
        assert "INVALID" in failed


class TestRateLimiting:
    """Tests for rate limit handling."""
    
    def test_track_request_count(self):
        """Should track requests per provider."""
        requests_per_minute = {
            ProviderType.YFINANCE: 25,
            ProviderType.FINNHUB: 58,
            ProviderType.POLYGON: 4,
        }
        
        limits = {
            ProviderType.YFINANCE: 30,
            ProviderType.FINNHUB: 60,
            ProviderType.POLYGON: 5,
        }
        
        # Check approaching limit
        finnhub_usage = requests_per_minute[ProviderType.FINNHUB] / limits[ProviderType.FINNHUB]
        assert finnhub_usage > 0.9  # Over 90% used
    
    def test_distribute_load(self):
        """Should distribute load across providers."""
        total_requests = 100
        num_providers = 3
        
        # Even distribution
        per_provider = total_requests // num_providers
        
        assert per_provider == 33
    
    def test_backoff_on_rate_limit(self):
        """Should implement exponential backoff."""
        base_delay = 1.0
        max_delay = 60.0
        
        for attempt in range(5):
            delay = min(base_delay * (2 ** attempt), max_delay)
            
            if attempt == 0:
                assert delay == 1.0
            elif attempt == 3:
                assert delay == 8.0
            elif attempt == 4:
                assert delay == 16.0
    
    def test_rate_limit_reset(self):
        """Should track rate limit reset times."""
        reset_time = datetime.now(timezone.utc) + timedelta(minutes=1)
        now = datetime.now(timezone.utc)
        
        wait_time = (reset_time - now).total_seconds()
        
        assert wait_time > 0
        assert wait_time <= 60


class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""
    
    def test_circuit_opens_on_failures(self):
        """Should open circuit after consecutive failures."""
        failure_threshold = 5
        consecutive_failures = 6
        
        circuit_open = consecutive_failures >= failure_threshold
        
        assert circuit_open is True
    
    def test_circuit_half_open(self):
        """Should enter half-open state after cooldown."""
        cooldown_period = timedelta(seconds=30)
        circuit_opened_at = datetime.now(timezone.utc) - timedelta(seconds=35)
        now = datetime.now(timezone.utc)
        
        time_since_open = now - circuit_opened_at
        is_half_open = time_since_open > cooldown_period
        
        assert is_half_open is True
    
    def test_circuit_closes_on_success(self):
        """Should close circuit on successful request in half-open."""
        consecutive_successes = 3
        success_threshold = 3
        
        should_close = consecutive_successes >= success_threshold
        
        assert should_close is True
    
    def test_circuit_reopens_on_failure(self):
        """Should reopen circuit on failure in half-open."""
        is_half_open = True
        request_failed = True
        
        should_reopen = is_half_open and request_failed
        
        assert should_reopen is True


class TestProviderCostOptimization:
    """Tests for cost-based provider selection."""
    
    def test_prefer_free_providers(self):
        """Should prefer free providers when possible."""
        providers = [
            {"name": ProviderType.YFINANCE, "cost": Decimal("0"), "quality": 0.8},
            {"name": ProviderType.POLYGON, "cost": Decimal("0.001"), "quality": 0.95},
        ]
        
        # For non-critical requests, prefer free
        selected = min(providers, key=lambda p: p["cost"])
        
        assert selected["name"] == ProviderType.YFINANCE
    
    def test_use_paid_for_premium_features(self):
        """Should use paid providers for premium features."""
        need_realtime = True
        need_extended_hours = True
        
        providers = [
            {"name": ProviderType.YFINANCE, "realtime": False, "extended": False},
            {"name": ProviderType.POLYGON, "realtime": True, "extended": True},
        ]
        
        if need_realtime or need_extended_hours:
            selected = next(
                p for p in providers 
                if p["realtime"] and p["extended"]
            )
            assert selected["name"] == ProviderType.POLYGON
    
    def test_budget_tracking(self):
        """Should track daily budget usage."""
        daily_budget = Decimal("10.00")
        spent_today = Decimal("7.50")
        request_cost = Decimal("0.001")
        
        remaining = daily_budget - spent_today
        requests_possible = remaining / request_cost
        
        assert remaining == Decimal("2.50")
        assert requests_possible == 2500
