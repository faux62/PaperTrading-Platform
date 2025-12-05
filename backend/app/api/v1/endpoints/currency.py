"""
PaperTrading Platform - Currency Endpoints

API endpoints for currency conversion and exchange rates.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.dependencies import get_current_active_user
from app.db.models.user import User
from app.utils.currency import (
    fetch_exchange_rates,
    convert_currency,
    get_supported_currencies,
    get_conversion_rate,
)


router = APIRouter()


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
