"""
PaperTrading Platform - Watchlist Endpoints
Full CRUD for watchlists and symbol management
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.user import User
from app.core.security import get_current_user
from app.core.watchlist.service import WatchlistService
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistResponse,
    WatchlistWithSymbols,
    WatchlistSummary,
    WatchlistSymbolResponse,
    AddSymbolRequest,
)

router = APIRouter()


@router.get("/", response_model=WatchlistSummary)
async def list_watchlists(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get all watchlists for current user with summary."""
    service = WatchlistService(db)
    watchlists = await service.get_user_watchlists(current_user.id)
    
    # Count total symbols
    total_symbols = 0
    for watchlist in watchlists:
        symbols = await service.get_watchlist_symbols(watchlist.id)
        total_symbols += len(symbols)
    
    return WatchlistSummary(
        total_watchlists=len(watchlists),
        total_symbols=total_symbols,
        watchlists=[WatchlistResponse.model_validate(w) for w in watchlists]
    )


@router.post("/", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    data: WatchlistCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new watchlist."""
    service = WatchlistService(db)
    watchlist = await service.create_watchlist(
        user_id=current_user.id,
        name=data.name,
        description=data.description
    )
    return WatchlistResponse.model_validate(watchlist)


@router.get("/{watchlist_id}", response_model=WatchlistWithSymbols)
async def get_watchlist(
    watchlist_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get watchlist by ID with all symbols."""
    service = WatchlistService(db)
    watchlist = await service.get_watchlist(watchlist_id, current_user.id)
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    
    symbols = await service.get_watchlist_symbols(watchlist_id)
    
    return WatchlistWithSymbols(
        id=watchlist.id,
        user_id=watchlist.user_id,
        name=watchlist.name,
        description=watchlist.description,
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at,
        symbols=[WatchlistSymbolResponse(**s) for s in symbols]
    )


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: int,
    data: WatchlistUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update watchlist name or description."""
    service = WatchlistService(db)
    watchlist = await service.update_watchlist(
        watchlist_id=watchlist_id,
        user_id=current_user.id,
        name=data.name,
        description=data.description
    )
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    
    return WatchlistResponse.model_validate(watchlist)


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    watchlist_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a watchlist and all its symbols."""
    service = WatchlistService(db)
    deleted = await service.delete_watchlist(watchlist_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )


@router.get("/{watchlist_id}/symbols", response_model=list[WatchlistSymbolResponse])
async def list_watchlist_symbols(
    watchlist_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get all symbols in a watchlist."""
    service = WatchlistService(db)
    
    # Verify ownership
    watchlist = await service.get_watchlist(watchlist_id, current_user.id)
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    
    symbols = await service.get_watchlist_symbols(watchlist_id)
    return [WatchlistSymbolResponse(**s) for s in symbols]


@router.post("/{watchlist_id}/symbols", status_code=status.HTTP_201_CREATED)
async def add_symbol(
    watchlist_id: int,
    data: AddSymbolRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a symbol to watchlist."""
    service = WatchlistService(db)
    success = await service.add_symbol(
        watchlist_id=watchlist_id,
        user_id=current_user.id,
        symbol=data.symbol
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    
    return {"message": f"Symbol {data.symbol.upper()} added to watchlist"}


@router.delete("/{watchlist_id}/symbols/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_symbol(
    watchlist_id: int,
    symbol: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a symbol from watchlist."""
    service = WatchlistService(db)
    removed = await service.remove_symbol(
        watchlist_id=watchlist_id,
        user_id=current_user.id,
        symbol=symbol
    )
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist or symbol not found"
        )


@router.get("/symbols/all", response_model=list[str])
async def get_all_watched_symbols(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get all unique symbols across all user's watchlists."""
    service = WatchlistService(db)
    return await service.get_all_user_symbols(current_user.id)
