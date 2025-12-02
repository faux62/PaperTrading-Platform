"""
PaperTrading Platform - Watchlist Endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_watchlists():
    """List all watchlists."""
    return {"message": "List watchlists - TODO"}


@router.post("/")
async def create_watchlist():
    """Create a new watchlist."""
    return {"message": "Create watchlist - TODO"}


@router.get("/{watchlist_id}")
async def get_watchlist(watchlist_id: int):
    """Get watchlist by ID."""
    return {"message": f"Get watchlist {watchlist_id} - TODO"}


@router.post("/{watchlist_id}/symbols")
async def add_symbol(watchlist_id: int):
    """Add symbol to watchlist."""
    return {"message": f"Add symbol to watchlist {watchlist_id} - TODO"}


@router.delete("/{watchlist_id}/symbols/{symbol}")
async def remove_symbol(watchlist_id: int, symbol: str):
    """Remove symbol from watchlist."""
    return {"message": f"Remove {symbol} from watchlist {watchlist_id} - TODO"}
