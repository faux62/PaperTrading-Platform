"""
PaperTrading Platform - Position Endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_positions():
    """List all positions."""
    return {"message": "List positions - TODO"}


@router.get("/{position_id}")
async def get_position(position_id: int):
    """Get position by ID."""
    return {"message": f"Get position {position_id} - TODO"}


@router.get("/portfolio/{portfolio_id}")
async def get_portfolio_positions(portfolio_id: int):
    """Get all positions for a portfolio."""
    return {"message": f"Portfolio {portfolio_id} positions - TODO"}
