"""
Position Calculator Service

Computes market values and P&L at runtime using:
- Position data from database (trade-driven, persistent)
- Current prices from Redis cache
- Current FX rates from Redis cache

This service NEVER stores computed values in the database.
All calculations are performed on-demand for data freshness.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from loguru import logger

from app.db.models.position import Position
from app.db.redis_client import redis_client
from app.services.fx_rate_service import fx_rate_service


@dataclass
class ComputedPosition:
    """
    Position with computed market values.
    
    Combines persistent DB data with real-time computed values.
    """
    # From Database (Trade-Driven)
    id: int
    portfolio_id: int
    symbol: str
    exchange: Optional[str]
    native_currency: str
    quantity: Decimal
    avg_cost: Decimal  # Native currency
    avg_cost_portfolio: Decimal  # Portfolio currency
    entry_exchange_rate: Decimal
    opened_at: Optional[str]
    
    # Computed (Market-Driven)
    current_price: Decimal  # Native currency
    current_fx_rate: Decimal  # Native -> Portfolio
    market_value: Decimal  # Portfolio currency
    unrealized_pnl: Decimal  # Portfolio currency
    unrealized_pnl_pct: Decimal  # Percentage
    
    # Metadata
    price_timestamp: Optional[str] = None
    fx_rate_timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "portfolio_id": self.portfolio_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "native_currency": self.native_currency,
            "quantity": float(self.quantity),
            "avg_cost": float(self.avg_cost),
            "avg_cost_portfolio": float(self.avg_cost_portfolio),
            "entry_exchange_rate": float(self.entry_exchange_rate),
            "current_price": float(self.current_price),
            "current_fx_rate": float(self.current_fx_rate),
            "market_value": float(self.market_value),
            "unrealized_pnl": float(self.unrealized_pnl),
            "unrealized_pnl_percent": float(self.unrealized_pnl_pct),
            "opened_at": self.opened_at,
            "price_timestamp": self.price_timestamp,
            "fx_rate_timestamp": self.fx_rate_timestamp,
        }


class PositionCalculator:
    """
    Service for computing position values at runtime.
    
    Design Principles:
    - Never store computed values in DB
    - Always use fresh prices and FX rates
    - Graceful fallback when data unavailable
    """
    
    def __init__(self, portfolio_currency: str = "EUR"):
        self.portfolio_currency = portfolio_currency
    
    async def compute_position(
        self, 
        position: Position,
        current_price: Optional[Decimal] = None,
        fx_rate: Optional[Decimal] = None
    ) -> ComputedPosition:
        """
        Compute market values for a single position.
        
        Args:
            position: Position model from database
            current_price: Override price (optional, fetched from cache if None)
            fx_rate: Override FX rate (optional, fetched from cache if None)
            
        Returns:
            ComputedPosition with calculated values
        """
        native_currency = position.native_currency or "USD"
        
        # Get current price from cache if not provided
        if current_price is None:
            current_price = await self._get_cached_price(position.symbol)
            if current_price is None:
                # Fallback to DB stored price (may be stale)
                current_price = position.current_price or position.avg_cost
        
        # Get FX rate if currencies differ
        if native_currency != self.portfolio_currency:
            if fx_rate is None:
                fx_rate = await fx_rate_service.get_rate(
                    native_currency, 
                    self.portfolio_currency
                )
        else:
            fx_rate = Decimal("1.0")
        
        # Compute market value in portfolio currency
        market_value_native = position.quantity * current_price
        market_value = (market_value_native * fx_rate).quantize(
            Decimal("0.01"), 
            rounding=ROUND_HALF_UP
        )
        
        # Compute unrealized P&L in portfolio currency
        cost_basis = position.quantity * (position.avg_cost_portfolio or position.avg_cost)
        unrealized_pnl = (market_value - cost_basis).quantize(
            Decimal("0.01"), 
            rounding=ROUND_HALF_UP
        )
        
        # Compute P&L percentage (based on native prices for accuracy)
        if position.avg_cost and position.avg_cost > 0:
            unrealized_pnl_pct = (
                (current_price - position.avg_cost) / position.avg_cost * 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            unrealized_pnl_pct = Decimal("0")
        
        # Get timestamps
        fx_timestamp = await fx_rate_service.get_rates_timestamp()
        
        return ComputedPosition(
            id=position.id,
            portfolio_id=position.portfolio_id,
            symbol=position.symbol,
            exchange=position.exchange,
            native_currency=native_currency,
            quantity=position.quantity,
            avg_cost=position.avg_cost,
            avg_cost_portfolio=position.avg_cost_portfolio or position.avg_cost,
            entry_exchange_rate=position.entry_exchange_rate or Decimal("1.0"),
            opened_at=position.opened_at.isoformat() if position.opened_at else None,
            current_price=current_price,
            current_fx_rate=fx_rate,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            fx_rate_timestamp=fx_timestamp,
        )
    
    async def compute_positions(
        self, 
        positions: List[Position],
        prices: Optional[Dict[str, Decimal]] = None,
        fx_rates: Optional[Dict[str, Decimal]] = None
    ) -> List[ComputedPosition]:
        """
        Compute market values for multiple positions efficiently.
        
        Batches price and FX rate lookups for better performance.
        
        Args:
            positions: List of Position models
            prices: Optional dict of symbol -> price
            fx_rates: Optional dict of currency_pair -> rate
            
        Returns:
            List of ComputedPosition with calculated values
        """
        if not positions:
            return []
        
        # Batch fetch prices if not provided
        if prices is None:
            symbols = list(set(p.symbol for p in positions))
            prices = await self._get_cached_prices_batch(symbols)
        
        # Batch fetch FX rates if not provided
        if fx_rates is None:
            currencies = list(set(
                p.native_currency or "USD" 
                for p in positions 
                if (p.native_currency or "USD") != self.portfolio_currency
            ))
            fx_rates = {}
            for curr in currencies:
                fx_rates[curr] = await fx_rate_service.get_rate(
                    curr, 
                    self.portfolio_currency
                )
        
        # Compute each position
        computed = []
        for position in positions:
            price = prices.get(position.symbol)
            native_curr = position.native_currency or "USD"
            fx_rate = fx_rates.get(native_curr, Decimal("1.0"))
            
            computed_pos = await self.compute_position(
                position,
                current_price=price,
                fx_rate=fx_rate if native_curr != self.portfolio_currency else None
            )
            computed.append(computed_pos)
        
        return computed
    
    async def compute_portfolio_summary(
        self, 
        positions: List[Position]
    ) -> Dict:
        """
        Compute portfolio-level summary from positions.
        
        Args:
            positions: List of Position models
            
        Returns:
            Dict with total_value, total_pnl, etc.
        """
        computed_positions = await self.compute_positions(positions)
        
        total_value = Decimal("0")
        total_pnl = Decimal("0")
        total_cost_basis = Decimal("0")
        
        for cp in computed_positions:
            total_value += cp.market_value
            total_pnl += cp.unrealized_pnl
            total_cost_basis += cp.quantity * cp.avg_cost_portfolio
        
        # Overall P&L percentage
        total_pnl_pct = Decimal("0")
        if total_cost_basis > 0:
            total_pnl_pct = (total_pnl / total_cost_basis * 100).quantize(
                Decimal("0.01"), 
                rounding=ROUND_HALF_UP
            )
        
        return {
            "total_market_value": float(total_value),
            "total_unrealized_pnl": float(total_pnl),
            "total_unrealized_pnl_pct": float(total_pnl_pct),
            "total_cost_basis": float(total_cost_basis),
            "position_count": len(computed_positions),
            "positions": [cp.to_dict() for cp in computed_positions],
        }
    
    async def _get_cached_price(self, symbol: str) -> Optional[Decimal]:
        """Get price from Redis cache."""
        try:
            quote = await redis_client.get_quote(symbol)
            if quote and "price" in quote:
                return Decimal(str(quote["price"]))
            if quote and "close" in quote:
                return Decimal(str(quote["close"]))
        except Exception as e:
            logger.debug(f"Failed to get cached price for {symbol}: {e}")
        return None
    
    async def _get_cached_prices_batch(
        self, 
        symbols: List[str]
    ) -> Dict[str, Decimal]:
        """Get multiple prices from Redis cache."""
        prices = {}
        try:
            quotes = await redis_client.get_quotes(symbols)
            for symbol, quote in quotes.items():
                if quote:
                    if "price" in quote:
                        prices[symbol] = Decimal(str(quote["price"]))
                    elif "close" in quote:
                        prices[symbol] = Decimal(str(quote["close"]))
        except Exception as e:
            logger.debug(f"Failed to get cached prices batch: {e}")
        return prices


# =============================================================================
# Factory Function
# =============================================================================

def create_calculator(portfolio_currency: str = "EUR") -> PositionCalculator:
    """
    Create a PositionCalculator for a specific portfolio currency.
    
    Args:
        portfolio_currency: The portfolio's base currency
        
    Returns:
        Configured PositionCalculator instance
    """
    return PositionCalculator(portfolio_currency)
