"""
PaperTrading Platform - Currency Endpoints

API endpoints for currency conversion and exchange rates.

SINGLE CURRENCY MODEL:
- Portfolios use a SINGLE base currency (portfolio.currency)
- Trading converts costs on-demand to portfolio currency
- Exchange rates and the convert() function are the key utilities

DEPRECATED ENDPOINTS (will be removed):
- /portfolio/{id}/balances - Multi-currency cash balances
- /portfolio/{id}/fx-convert - Manual FX conversions
- /portfolio/{id}/deposit - Currency deposits
- /portfolio/{id}/withdraw - Currency withdrawals
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_current_active_user, get_db
from app.db.models.user import User
from app.db.models import Portfolio, CashBalance, FxTransaction
from app.utils.currency import (
    fetch_exchange_rates,
    convert_currency,
    get_supported_currencies,
    get_conversion_rate,
    convert,  # NEW: Unified conversion function
)


router = APIRouter()


# ============================================
# Basic Schemas
# ============================================

class ConvertRequest(BaseModel):
    """Request schema for currency conversion."""
    amount: float
    from_currency: str
    to_currency: str


class ConvertResponse(BaseModel):
    """Response schema for currency conversion."""
    original_amount: float
    converted_amount: float
    from_currency: str
    to_currency: str
    rate: float


# ============================================
# IBKR-style Schemas
# ============================================

class CashBalanceResponse(BaseModel):
    currency: str
    balance: float
    symbol: str

class PortfolioCashResponse(BaseModel):
    portfolio_id: int
    portfolio_name: str
    base_currency: str
    balances: List[CashBalanceResponse]
    total_in_base: float

class FxConvertRequest(BaseModel):
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)
    amount: float = Field(..., gt=0)

class FxConvertResponse(BaseModel):
    from_currency: str
    to_currency: str
    from_amount: float
    to_amount: float
    exchange_rate: float
    transaction_id: int

class DepositWithdrawRequest(BaseModel):
    currency: str = Field(..., min_length=3, max_length=3)
    amount: float = Field(..., gt=0)


@router.get("/supported")
async def list_supported_currencies():
    """
    Get list of supported currencies.
    
    Returns currency codes, names, and symbols.
    """
    return {
        "currencies": get_supported_currencies()
    }


@router.get("/rates")
async def get_exchange_rates(
    base: str = "USD",
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current exchange rates.
    
    Returns rates relative to the specified base currency.
    Rates are cached for 1 hour to minimize API calls.
    """
    rates = await fetch_exchange_rates(base)
    return {
        "base": base,
        "rates": rates,
    }


@router.post("/convert", response_model=ConvertResponse)
async def convert(
    request: ConvertRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Convert an amount between two currencies.
    
    Uses real-time exchange rates (cached for 1 hour).
    """
    if request.amount < 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    converted = await convert_currency(
        request.amount,
        request.from_currency.upper(),
        request.to_currency.upper()
    )
    
    rate = await get_conversion_rate(
        request.from_currency.upper(),
        request.to_currency.upper()
    )
    
    return ConvertResponse(
        original_amount=request.amount,
        converted_amount=converted,
        from_currency=request.from_currency.upper(),
        to_currency=request.to_currency.upper(),
        rate=round(rate, 6),
    )


# ============================================
# NEW: Single Currency Model Endpoint
# ============================================

class SingleCurrencyConvertRequest(BaseModel):
    """Request for unified currency conversion (Decimal precision)."""
    amount: float
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)


class SingleCurrencyConvertResponse(BaseModel):
    """Response with converted amount and exchange rate used."""
    original_amount: float
    converted_amount: float
    from_currency: str
    to_currency: str
    exchange_rate: float


@router.post("/convert/precise", response_model=SingleCurrencyConvertResponse)
async def convert_precise(
    request: SingleCurrencyConvertRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Convert currency using the unified convert() function.
    
    This is the recommended endpoint for the Single Currency Model.
    Returns both the converted amount and the exchange rate used.
    """
    converted_amount, exchange_rate = await convert(
        Decimal(str(request.amount)),
        request.from_currency.upper(),
        request.to_currency.upper()
    )
    
    return SingleCurrencyConvertResponse(
        original_amount=request.amount,
        converted_amount=float(converted_amount),
        from_currency=request.from_currency.upper(),
        to_currency=request.to_currency.upper(),
        exchange_rate=float(exchange_rate),
    )


# ============================================
# DEPRECATED: IBKR-style Multi-Currency Endpoints
# These endpoints will be removed in a future version.
# Use portfolio.cash_balance instead of cash_balances table.
# ============================================

CURRENCY_SYMBOLS = {
    'USD': '$', 'EUR': '€', 'GBP': '£', 'CHF': 'CHF', 'JPY': '¥',
    'CAD': 'C$', 'AUD': 'A$', 'HKD': 'HK$', 'SGD': 'S$', 'CNY': '¥',
}


async def get_or_create_cash_balance(db: AsyncSession, portfolio_id: int, currency: str) -> CashBalance:
    """DEPRECATED: Get or create a cash balance for a specific currency."""
    result = await db.execute(
        select(CashBalance).where(
            CashBalance.portfolio_id == portfolio_id,
            CashBalance.currency == currency
        )
    )
    balance = result.scalar_one_or_none()
    
    if not balance:
        balance = CashBalance(
            portfolio_id=portfolio_id,
            currency=currency,
            balance=Decimal("0.00")
        )
        db.add(balance)
        await db.flush()
    
    return balance


@router.get("/portfolio/{portfolio_id}/balances", response_model=PortfolioCashResponse, deprecated=True)
async def get_portfolio_cash_balances(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    DEPRECATED: Get all cash balances for a portfolio (IBKR-style multi-currency).
    
    Use portfolio.cash_balance instead for the Single Currency Model.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Get all cash balances
    result = await db.execute(
        select(CashBalance).where(CashBalance.portfolio_id == portfolio_id)
    )
    cash_balances = result.scalars().all()
    
    # Convert to response format
    balances = []
    total_in_base = Decimal("0.00")
    
    for cb in cash_balances:
        if cb.currency == portfolio.currency:
            converted = cb.balance
        else:
            rate = await get_conversion_rate(cb.currency, portfolio.currency)
            converted = cb.balance * Decimal(str(rate))
        total_in_base += converted
        
        balances.append({
            "currency": cb.currency,
            "balance": float(cb.balance),
            "symbol": CURRENCY_SYMBOLS.get(cb.currency, cb.currency)
        })
    
    balances.sort(key=lambda x: x["balance"], reverse=True)
    
    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio.name,
        "base_currency": portfolio.currency,
        "balances": balances,
        "total_in_base": float(total_in_base)
    }


@router.post("/portfolio/{portfolio_id}/fx-convert", response_model=FxConvertResponse)
async def portfolio_convert_currency(
    portfolio_id: int,
    request: FxConvertRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Convert currency within a portfolio (IBKR-style FX trade).
    Deducts from one currency balance and adds to another.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    from_currency = request.from_currency.upper()
    to_currency = request.to_currency.upper()
    amount = Decimal(str(request.amount))
    
    if from_currency == to_currency:
        raise HTTPException(status_code=400, detail="Cannot convert to same currency")
    
    # Get source balance
    from_balance = await get_or_create_cash_balance(db, portfolio_id, from_currency)
    
    if from_balance.balance < amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient {from_currency} balance: have {from_balance.balance}, need {amount}"
        )
    
    # Get exchange rate and convert
    rate = await get_conversion_rate(from_currency, to_currency)
    converted_amount = (amount * Decimal(str(rate))).quantize(Decimal("0.01"))
    
    # Update balances
    from_balance.balance -= amount
    to_balance = await get_or_create_cash_balance(db, portfolio_id, to_currency)
    to_balance.balance += converted_amount
    
    # Record transaction
    fx_tx = FxTransaction(
        portfolio_id=portfolio_id,
        from_currency=from_currency,
        to_currency=to_currency,
        from_amount=amount,
        to_amount=converted_amount,
        exchange_rate=Decimal(str(rate))
    )
    db.add(fx_tx)
    await db.commit()
    
    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "from_amount": float(amount),
        "to_amount": float(converted_amount),
        "exchange_rate": rate,
        "transaction_id": fx_tx.id
    }


@router.post("/portfolio/{portfolio_id}/deposit")
async def deposit_cash(
    portfolio_id: int,
    request: DepositWithdrawRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deposit cash in a specific currency (paper trading)."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    currency = request.currency.upper()
    amount = Decimal(str(request.amount))
    
    balance = await get_or_create_cash_balance(db, portfolio_id, currency)
    balance.balance += amount
    await db.commit()
    
    return {
        "message": f"Deposited {request.amount} {currency}",
        "new_balance": float(balance.balance),
        "currency": currency
    }


@router.post("/portfolio/{portfolio_id}/withdraw")
async def withdraw_cash(
    portfolio_id: int,
    request: DepositWithdrawRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Withdraw cash in a specific currency (paper trading)."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    currency = request.currency.upper()
    amount = Decimal(str(request.amount))
    
    balance = await get_or_create_cash_balance(db, portfolio_id, currency)
    
    if balance.balance < amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient balance: have {balance.balance} {currency}"
        )
    
    balance.balance -= amount
    await db.commit()
    
    return {
        "message": f"Withdrew {request.amount} {currency}",
        "new_balance": float(balance.balance),
        "currency": currency
    }


@router.get("/portfolio/{portfolio_id}/fx-history")
async def get_fx_history(
    portfolio_id: int,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get FX transaction history for a portfolio."""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    result = await db.execute(
        select(FxTransaction)
        .where(FxTransaction.portfolio_id == portfolio_id)
        .order_by(FxTransaction.executed_at.desc())
        .limit(limit)
    )
    transactions = result.scalars().all()
    
    return {
        "portfolio_id": portfolio_id,
        "transactions": [
            {
                "id": tx.id,
                "from_currency": tx.from_currency,
                "to_currency": tx.to_currency,
                "from_amount": float(tx.from_amount),
                "to_amount": float(tx.to_amount),
                "exchange_rate": float(tx.exchange_rate),
                "executed_at": tx.executed_at.isoformat() if tx.executed_at else None
            }
            for tx in transactions
        ]
    }


def get_symbol_currency(symbol: str, exchange: Optional[str] = None) -> str:
    """Determine the native currency of a symbol based on exchange."""
    exchange_currencies = {
        'NYSE': 'USD', 'NASDAQ': 'USD', 'AMEX': 'USD',
        'LSE': 'GBP', 'XETRA': 'EUR', 'FRA': 'EUR',
        'PAR': 'EUR', 'AMS': 'EUR', 'MIL': 'EUR',
        'TSE': 'JPY', 'HKEX': 'HKD', 'SGX': 'SGD',
        'ASX': 'AUD', 'TSX': 'CAD', 'SIX': 'CHF',
    }
    
    if exchange and exchange.upper() in exchange_currencies:
        return exchange_currencies[exchange.upper()]
    
    # Check symbol suffix (Yahoo Finance style)
    if '.' in symbol:
        suffix = symbol.split('.')[-1].upper()
        suffix_currencies = {
            'L': 'GBP', 'DE': 'EUR', 'F': 'EUR', 'PA': 'EUR',
            'AS': 'EUR', 'MI': 'EUR', 'T': 'JPY', 'HK': 'HKD',
            'SI': 'SGD', 'AX': 'AUD', 'TO': 'CAD', 'SW': 'CHF',
        }
        if suffix in suffix_currencies:
            return suffix_currencies[suffix]
    
    return 'USD'


@router.get("/symbol/{symbol}/currency")
async def get_symbol_native_currency(symbol: str, exchange: Optional[str] = None):
    """Determine the native currency of a symbol based on exchange."""
    currency = get_symbol_currency(symbol, exchange)
    return {
        "symbol": symbol,
        "exchange": exchange,
        "native_currency": currency,
        "symbol_display": CURRENCY_SYMBOLS.get(currency, currency)
    }
