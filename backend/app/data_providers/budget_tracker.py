"""
Budget Tracker

Tracks API costs and enforces daily budget limits per provider.
Supports cost estimation and alerts when approaching limits.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Callable, Awaitable
from collections import defaultdict
from loguru import logger


@dataclass
class BudgetConfig:
    """Budget configuration for a provider."""
    daily_limit: Decimal = Decimal("0")  # 0 = unlimited
    monthly_limit: Decimal = Decimal("0")  # 0 = unlimited
    cost_per_request: Decimal = Decimal("0")
    cost_per_symbol: Decimal = Decimal("0")  # For batch requests
    warning_threshold: float = 0.8  # Alert at 80% of budget
    
    # Some providers have different costs per endpoint
    endpoint_costs: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class BudgetUsage:
    """Tracks budget usage for a provider."""
    provider: str
    date: date = field(default_factory=date.today)
    daily_spent: Decimal = Decimal("0")
    monthly_spent: Decimal = Decimal("0")
    request_count: int = 0
    
    # Breakdown by endpoint
    endpoint_usage: dict[str, Decimal] = field(default_factory=dict)
    
    def reset_daily(self) -> None:
        """Reset daily counters."""
        self.daily_spent = Decimal("0")
        self.request_count = 0
        self.endpoint_usage = {}
        self.date = date.today()
    
    def reset_monthly(self) -> None:
        """Reset monthly counters."""
        self.monthly_spent = Decimal("0")
        self.reset_daily()


class BudgetExceededError(Exception):
    """Raised when budget is exceeded."""
    def __init__(self, provider: str, budget_type: str, limit: Decimal, spent: Decimal):
        self.provider = provider
        self.budget_type = budget_type
        self.limit = limit
        self.spent = spent
        super().__init__(
            f"Budget exceeded for {provider}: {budget_type} limit ${limit}, spent ${spent}"
        )


class BudgetTracker:
    """
    Tracks API costs across providers and enforces budget limits.
    
    Features:
    - Per-provider daily and monthly budgets
    - Cost tracking per request and endpoint
    - Warning alerts when approaching limits
    - Automatic daily/monthly reset
    """
    
    def __init__(self):
        self._configs: dict[str, BudgetConfig] = {}
        self._usage: dict[str, BudgetUsage] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._alert_callbacks: list[Callable[[str, str, float], Awaitable[None]]] = []
        self._last_reset_date: Optional[date] = None
        
    def configure(self, provider: str, config: BudgetConfig) -> None:
        """Configure budget for a provider."""
        self._configs[provider] = config
        if provider not in self._usage:
            self._usage[provider] = BudgetUsage(provider=provider)
        logger.info(
            f"Budget configured for {provider}: "
            f"daily=${config.daily_limit}, monthly=${config.monthly_limit}"
        )
    
    def register_alert_callback(
        self, 
        callback: Callable[[str, str, float], Awaitable[None]]
    ) -> None:
        """
        Register a callback for budget alerts.
        
        Callback receives: provider name, alert type, usage percentage
        """
        self._alert_callbacks.append(callback)
    
    async def check_and_record(
        self,
        provider: str,
        cost: Optional[Decimal] = None,
        endpoint: Optional[str] = None,
        symbol_count: int = 1,
    ) -> None:
        """
        Check budget availability and record cost.
        
        Args:
            provider: Provider name
            cost: Explicit cost (if not using config)
            endpoint: Endpoint name for per-endpoint tracking
            symbol_count: Number of symbols (for batch requests)
            
        Raises:
            BudgetExceededError: If budget would be exceeded
        """
        config = self._configs.get(provider)
        if not config:
            # No budget configured, allow all
            return
        
        # Check for day change and reset if needed
        await self._check_reset()
        
        async with self._locks[provider]:
            usage = self._usage.get(provider)
            if not usage:
                usage = BudgetUsage(provider=provider)
                self._usage[provider] = usage
            
            # Calculate cost
            if cost is None:
                cost = self._calculate_cost(config, endpoint, symbol_count)
            
            # Check daily limit
            if config.daily_limit > 0:
                if usage.daily_spent + cost > config.daily_limit:
                    raise BudgetExceededError(
                        provider, "daily", config.daily_limit, usage.daily_spent
                    )
            
            # Check monthly limit
            if config.monthly_limit > 0:
                if usage.monthly_spent + cost > config.monthly_limit:
                    raise BudgetExceededError(
                        provider, "monthly", config.monthly_limit, usage.monthly_spent
                    )
            
            # Record the cost
            usage.daily_spent += cost
            usage.monthly_spent += cost
            usage.request_count += 1
            
            if endpoint:
                usage.endpoint_usage[endpoint] = (
                    usage.endpoint_usage.get(endpoint, Decimal("0")) + cost
                )
            
            # Check for warnings
            await self._check_warnings(provider, config, usage)
    
    def _calculate_cost(
        self, 
        config: BudgetConfig, 
        endpoint: Optional[str],
        symbol_count: int
    ) -> Decimal:
        """Calculate the cost of a request."""
        # Check for endpoint-specific cost
        if endpoint and endpoint in config.endpoint_costs:
            base_cost = config.endpoint_costs[endpoint]
        else:
            base_cost = config.cost_per_request
        
        # Add per-symbol cost for batch requests
        symbol_cost = config.cost_per_symbol * symbol_count
        
        return base_cost + symbol_cost
    
    async def _check_warnings(
        self,
        provider: str,
        config: BudgetConfig,
        usage: BudgetUsage,
    ) -> None:
        """Check if we should send warning alerts."""
        # Check daily warning
        if config.daily_limit > 0:
            daily_pct = float(usage.daily_spent / config.daily_limit)
            if daily_pct >= config.warning_threshold:
                await self._send_alert(provider, "daily_warning", daily_pct)
        
        # Check monthly warning
        if config.monthly_limit > 0:
            monthly_pct = float(usage.monthly_spent / config.monthly_limit)
            if monthly_pct >= config.warning_threshold:
                await self._send_alert(provider, "monthly_warning", monthly_pct)
    
    async def _send_alert(
        self, 
        provider: str, 
        alert_type: str, 
        usage_pct: float
    ) -> None:
        """Send alert to registered callbacks."""
        logger.warning(
            f"Budget alert for {provider}: {alert_type} at {usage_pct*100:.1f}%"
        )
        for callback in self._alert_callbacks:
            try:
                await callback(provider, alert_type, usage_pct)
            except Exception as e:
                logger.error(f"Error in budget alert callback: {e}")
    
    async def _check_reset(self) -> None:
        """Check if we need to reset daily/monthly counters."""
        today = date.today()
        
        if self._last_reset_date != today:
            for provider, usage in self._usage.items():
                # Check if it's a new day
                if usage.date != today:
                    logger.info(f"Resetting daily budget for {provider}")
                    usage.reset_daily()
                    
                    # Check if it's a new month
                    if today.month != usage.date.month:
                        logger.info(f"Resetting monthly budget for {provider}")
                        usage.reset_monthly()
            
            self._last_reset_date = today
    
    def can_afford(
        self,
        provider: str,
        cost: Optional[Decimal] = None,
        endpoint: Optional[str] = None,
        symbol_count: int = 1,
    ) -> bool:
        """
        Check if we can afford a request without making it.
        
        Returns:
            True if the request is within budget
        """
        config = self._configs.get(provider)
        if not config:
            return True
        
        usage = self._usage.get(provider)
        if not usage:
            return True
        
        if cost is None:
            cost = self._calculate_cost(config, endpoint, symbol_count)
        
        if config.daily_limit > 0:
            if usage.daily_spent + cost > config.daily_limit:
                return False
        
        if config.monthly_limit > 0:
            if usage.monthly_spent + cost > config.monthly_limit:
                return False
        
        return True
    
    def get_usage(self, provider: str) -> Optional[BudgetUsage]:
        """Get current usage for a provider."""
        return self._usage.get(provider)
    
    def get_remaining(self, provider: str) -> dict[str, Decimal]:
        """
        Get remaining budget for a provider.
        
        Returns:
            Dictionary with remaining daily and monthly budget
        """
        config = self._configs.get(provider)
        usage = self._usage.get(provider)
        
        if not config:
            return {"daily": Decimal("-1"), "monthly": Decimal("-1")}  # Unlimited
        
        if not usage:
            return {
                "daily": config.daily_limit,
                "monthly": config.monthly_limit,
            }
        
        return {
            "daily": max(Decimal("0"), config.daily_limit - usage.daily_spent),
            "monthly": max(Decimal("0"), config.monthly_limit - usage.monthly_spent),
        }
    
    def get_stats(self, provider: str) -> dict:
        """Get detailed statistics for a provider."""
        config = self._configs.get(provider)
        usage = self._usage.get(provider)
        
        if not config:
            return {"configured": False}
        
        remaining = self.get_remaining(provider)
        
        return {
            "configured": True,
            "limits": {
                "daily": float(config.daily_limit),
                "monthly": float(config.monthly_limit),
                "cost_per_request": float(config.cost_per_request),
            },
            "usage": {
                "daily_spent": float(usage.daily_spent) if usage else 0,
                "monthly_spent": float(usage.monthly_spent) if usage else 0,
                "request_count": usage.request_count if usage else 0,
            },
            "remaining": {
                "daily": float(remaining["daily"]),
                "monthly": float(remaining["monthly"]),
            },
            "percentages": {
                "daily": float(usage.daily_spent / config.daily_limit * 100) 
                    if usage and config.daily_limit > 0 else 0,
                "monthly": float(usage.monthly_spent / config.monthly_limit * 100)
                    if usage and config.monthly_limit > 0 else 0,
            },
        }
    
    def get_all_stats(self) -> dict[str, dict]:
        """Get statistics for all configured providers."""
        return {
            provider: self.get_stats(provider)
            for provider in self._configs.keys()
        }


# Global budget tracker instance
budget_tracker = BudgetTracker()
