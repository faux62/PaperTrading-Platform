"""
PaperTrading Platform - Currency Service

SINGLE CURRENCY MODEL:
- Portfolios have ONE base currency (portfolio.currency)
- For currency conversions, use: from app.utils.currency import convert
- This module provides helper functions like get_symbol_currency()

DEPRECATED (to be removed):
- CurrencyService class (was IBKR-style multi-currency)
- Methods that interact with cash_balances table
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger
import warnings

from app.db.models import Portfolio, CashBalance, FxTransaction, Position


class CurrencyService:
    """
    DEPRECATED: Use app.utils.currency.convert() for conversions.
    
    This class is kept for backward compatibility but will be removed.
    The Single Currency Model uses only portfolio.cash_balance.
    """
    
    # Supported currencies
    SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD', 'HKD', 'SGD', 'CNY']
    
    # Currency symbols for display
    CURRENCY_SYMBOLS = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'CHF': 'CHF',
        'JPY': '¥',
        'CAD': 'C$',
        'AUD': 'A$',
        'HKD': 'HK$',
        'SGD': 'S$',
        'CNY': '¥',
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """
        Get current exchange rate between two currencies.
        Uses external API or cached rates.
        """
        if from_currency == to_currency:
            return Decimal("1.0")
        
        # Try to get rate from yfinance
        try:
            import yfinance as yf
            
            # Yahoo Finance format: EURUSD=X
            pair = f"{from_currency}{to_currency}=X"
            ticker = yf.Ticker(pair)
            data = ticker.history(period="1d")
            
            if not data.empty:
                rate = Decimal(str(data['Close'].iloc[-1]))
                logger.debug(f"FX rate {from_currency}/{to_currency}: {rate}")
                return rate
        except Exception as e:
            logger.warning(f"Failed to get FX rate from yfinance: {e}")
        
        # Fallback: use hardcoded approximate rates (for demo/paper trading)
        fallback_rates = {
            ('USD', 'EUR'): Decimal("0.92"),
            ('USD', 'GBP'): Decimal("0.79"),
            ('USD', 'JPY'): Decimal("149.50"),
            ('USD', 'CHF'): Decimal("0.88"),
            ('USD', 'CAD'): Decimal("1.36"),
            ('USD', 'AUD'): Decimal("1.54"),
            ('USD', 'HKD'): Decimal("7.80"),
            ('USD', 'SGD'): Decimal("1.34"),
            ('USD', 'CNY'): Decimal("7.24"),
            ('EUR', 'USD'): Decimal("1.08"),
            ('EUR', 'GBP'): Decimal("0.86"),
            ('GBP', 'USD'): Decimal("1.27"),
            ('GBP', 'EUR'): Decimal("1.16"),
        }
        
        # Check direct rate
        if (from_currency, to_currency) in fallback_rates:
            return fallback_rates[(from_currency, to_currency)]
        
        # Check inverse rate
        if (to_currency, from_currency) in fallback_rates:
            return Decimal("1.0") / fallback_rates[(to_currency, from_currency)]
        
        # Cross rate via USD
        if from_currency != 'USD' and to_currency != 'USD':
            from_to_usd = await self.get_exchange_rate(from_currency, 'USD')
            usd_to_target = await self.get_exchange_rate('USD', to_currency)
            return from_to_usd * usd_to_target
        
        logger.warning(f"No FX rate found for {from_currency}/{to_currency}, using 1.0")
        return Decimal("1.0")
    
    async def convert_amount(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str
    ) -> Tuple[Decimal, Decimal]:
        """
        Convert amount between currencies.
        Returns (converted_amount, exchange_rate).
        """
        if from_currency == to_currency:
            return amount, Decimal("1.0")
        
        rate = await self.get_exchange_rate(from_currency, to_currency)
        converted = amount * rate
        return converted.quantize(Decimal("0.01")), rate
    
    async def get_cash_balances(self, portfolio_id: int) -> Dict[str, Decimal]:
        """Get all cash balances for a portfolio."""
        result = await self.db.execute(
            select(CashBalance).where(CashBalance.portfolio_id == portfolio_id)
        )
        balances = result.scalars().all()
        return {b.currency: b.balance for b in balances}
    
    async def get_or_create_cash_balance(
        self,
        portfolio_id: int,
        currency: str
    ) -> CashBalance:
        """Get or create a cash balance for a specific currency."""
        result = await self.db.execute(
            select(CashBalance).where(
                and_(
                    CashBalance.portfolio_id == portfolio_id,
                    CashBalance.currency == currency
                )
            )
        )
        balance = result.scalar_one_or_none()
        
        if not balance:
            balance = CashBalance(
                portfolio_id=portfolio_id,
                currency=currency,
                balance=Decimal("0.00")
            )
            self.db.add(balance)
            await self.db.flush()
        
        return balance
    
    async def update_cash_balance(
        self,
        portfolio_id: int,
        currency: str,
        amount: Decimal,
        operation: str = "add"  # "add" or "subtract"
    ) -> CashBalance:
        """Update cash balance for a currency."""
        balance = await self.get_or_create_cash_balance(portfolio_id, currency)
        
        if operation == "add":
            balance.balance += amount
        elif operation == "subtract":
            balance.balance -= amount
        else:
            raise ValueError(f"Invalid operation: {operation}")
        
        balance.updated_at = datetime.utcnow()
        await self.db.flush()
        
        return balance
    
    async def convert_currency(
        self,
        portfolio_id: int,
        from_currency: str,
        to_currency: str,
        amount: Decimal
    ) -> FxTransaction:
        """
        Convert currency within a portfolio (IBKR-style FX trade).
        Deducts from one balance, adds to another.
        """
        if from_currency == to_currency:
            raise ValueError("Cannot convert to same currency")
        
        # Get source balance
        from_balance = await self.get_or_create_cash_balance(portfolio_id, from_currency)
        
        if from_balance.balance < amount:
            raise ValueError(f"Insufficient {from_currency} balance: have {from_balance.balance}, need {amount}")
        
        # Get exchange rate and convert
        converted_amount, rate = await self.convert_amount(amount, from_currency, to_currency)
        
        # Update balances
        from_balance.balance -= amount
        to_balance = await self.get_or_create_cash_balance(portfolio_id, to_currency)
        to_balance.balance += converted_amount
        
        # Record transaction
        fx_tx = FxTransaction(
            portfolio_id=portfolio_id,
            from_currency=from_currency,
            to_currency=to_currency,
            from_amount=amount,
            to_amount=converted_amount,
            exchange_rate=rate,
            executed_at=datetime.utcnow()
        )
        self.db.add(fx_tx)
        await self.db.flush()
        
        logger.info(f"FX conversion: {amount} {from_currency} -> {converted_amount} {to_currency} @ {rate}")
        
        return fx_tx
    
    async def get_total_equity_in_currency(
        self,
        portfolio_id: int,
        target_currency: str
    ) -> Dict:
        """
        Calculate total portfolio equity converted to target currency.
        Returns breakdown by component.
        """
        # Get portfolio
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Get all cash balances
        cash_balances = await self.get_cash_balances(portfolio_id)
        
        # Get all positions
        result = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        positions = result.scalars().all()
        
        # Convert cash balances
        total_cash = Decimal("0.00")
        cash_breakdown = []
        for currency, balance in cash_balances.items():
            converted, rate = await self.convert_amount(balance, currency, target_currency)
            total_cash += converted
            cash_breakdown.append({
                "currency": currency,
                "balance": float(balance),
                "converted": float(converted),
                "rate": float(rate)
            })
        
        # Convert positions
        total_positions = Decimal("0.00")
        position_breakdown = []
        for pos in positions:
            # Position value in native currency
            native_value = pos.quantity * pos.current_price
            converted, rate = await self.convert_amount(native_value, pos.native_currency, target_currency)
            total_positions += converted
            position_breakdown.append({
                "symbol": pos.symbol,
                "native_currency": pos.native_currency,
                "native_value": float(native_value),
                "converted": float(converted),
                "rate": float(rate)
            })
        
        return {
            "portfolio_id": portfolio_id,
            "target_currency": target_currency,
            "total_equity": float(total_cash + total_positions),
            "total_cash": float(total_cash),
            "total_positions": float(total_positions),
            "cash_breakdown": cash_breakdown,
            "position_breakdown": position_breakdown
        }
    
    async def get_fx_exposure(self, portfolio_id: int, base_currency: str) -> List[Dict]:
        """
        Calculate FX exposure for a portfolio.
        Shows how much exposure the portfolio has to each currency.
        """
        equity = await self.get_total_equity_in_currency(portfolio_id, base_currency)
        total = Decimal(str(equity["total_equity"]))
        
        if total == 0:
            return []
        
        # Aggregate by currency
        exposure = {}
        
        for cash in equity["cash_breakdown"]:
            currency = cash["currency"]
            if currency not in exposure:
                exposure[currency] = Decimal("0.00")
            exposure[currency] += Decimal(str(cash["converted"]))
        
        for pos in equity["position_breakdown"]:
            currency = pos["native_currency"]
            if currency not in exposure:
                exposure[currency] = Decimal("0.00")
            exposure[currency] += Decimal(str(pos["converted"]))
        
        # Calculate percentages
        result = []
        for currency, value in sorted(exposure.items(), key=lambda x: x[1], reverse=True):
            pct = (value / total * 100) if total > 0 else Decimal("0.00")
            result.append({
                "currency": currency,
                "value": float(value),
                "percentage": float(pct.quantize(Decimal("0.01"))),
                "symbol": self.CURRENCY_SYMBOLS.get(currency, currency)
            })
        
        return result


# Helper function for quick currency detection from symbol
def get_symbol_currency(symbol: str, exchange: Optional[str] = None) -> str:
    """
    Determine the native currency of a symbol based on exchange or symbol suffix.
    """
    # Common exchange mappings
    exchange_currencies = {
        'NYSE': 'USD',
        'NASDAQ': 'USD',
        'AMEX': 'USD',
        'LSE': 'GBP',
        'XETRA': 'EUR',
        'FRA': 'EUR',
        'PAR': 'EUR',
        'AMS': 'EUR',
        'MIL': 'EUR',
        'TSE': 'JPY',
        'HKEX': 'HKD',
        'SGX': 'SGD',
        'ASX': 'AUD',
        'TSX': 'CAD',
        'SIX': 'CHF',
    }
    
    if exchange and exchange.upper() in exchange_currencies:
        return exchange_currencies[exchange.upper()]
    
    # Check symbol suffix (Yahoo Finance style)
    if '.' in symbol:
        suffix = symbol.split('.')[-1].upper()
        suffix_currencies = {
            'L': 'GBP',     # London
            'DE': 'EUR',    # Germany
            'F': 'EUR',     # Frankfurt
            'PA': 'EUR',    # Paris
            'AS': 'EUR',    # Amsterdam
            'MI': 'EUR',    # Milan
            'T': 'JPY',     # Tokyo
            'HK': 'HKD',    # Hong Kong
            'SI': 'SGD',    # Singapore
            'AX': 'AUD',    # Australia
            'TO': 'CAD',    # Toronto
            'SW': 'CHF',    # Swiss
        }
        if suffix in suffix_currencies:
            return suffix_currencies[suffix]
    
    # Default to USD
    return 'USD'
