"""
PaperTrading Platform - Admin Endpoints
User management for superusers only
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from loguru import logger

from app.dependencies import get_current_active_user, get_db
from app.db.models.user import User
from app.db.models.user_settings import UserSettings
from app.db.models.portfolio import Portfolio
from app.db.models.position import Position
from app.db.models.trade import Trade
from app.db.models.watchlist import Watchlist, watchlist_symbols
from app.db.models.alert import Alert
from app.db.models.bot_signal import BotSignal, BotReport
from app.services.email_service import (
    send_account_enabled_email,
    send_account_disabled_email,
    send_account_deleted_email,
)

router = APIRouter()


# ============================================
# Schemas
# ============================================

class UserListItem(BaseModel):
    """User summary for list view."""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    base_currency: str
    created_at: datetime
    last_login: Optional[datetime]
    portfolio_count: int = 0


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserStatusUpdate(BaseModel):
    """Request to enable/disable user."""
    is_active: bool
    reason: Optional[str] = Field(None, max_length=500, description="Reason for disabling (shown in email)")


class UserActionResponse(BaseModel):
    """Response for user actions."""
    success: bool
    message: str
    user_id: int
    email_sent: bool


class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics."""
    total_users: int
    active_users: int
    disabled_users: int
    superusers: int
    total_portfolios: int
    users_today: int
    users_this_week: int


# ============================================
# Helper Functions
# ============================================

def require_superuser(current_user: User) -> User:
    """Verify current user is a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires administrator privileges"
        )
    return current_user


# ============================================
# Endpoints
# ============================================

@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get admin statistics",
    description="Get overview statistics for the admin dashboard."
)
async def get_admin_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AdminStatsResponse:
    """Get admin dashboard statistics."""
    require_superuser(current_user)
    
    from datetime import timedelta
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    
    # Total users
    total_result = await db.execute(select(func.count(User.id)))
    total_users = total_result.scalar() or 0
    
    # Active users
    active_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_result.scalar() or 0
    
    # Superusers
    super_result = await db.execute(
        select(func.count(User.id)).where(User.is_superuser == True)
    )
    superusers = super_result.scalar() or 0
    
    # Total portfolios
    portfolio_result = await db.execute(select(func.count(Portfolio.id)))
    total_portfolios = portfolio_result.scalar() or 0
    
    # Users today
    today_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    users_today = today_result.scalar() or 0
    
    # Users this week
    week_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )
    users_this_week = week_result.scalar() or 0
    
    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        disabled_users=total_users - active_users,
        superusers=superusers,
        total_portfolios=total_portfolios,
        users_today=users_today,
        users_this_week=users_this_week,
    )


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users",
    description="Get paginated list of all users. Superuser only."
)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserListResponse:
    """Get paginated list of users."""
    require_superuser(current_user)
    
    # Base query
    query = select(User)
    count_query = select(func.count(User.id))
    
    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.username.ilike(search_filter)) |
            (User.email.ilike(search_filter)) |
            (User.full_name.ilike(search_filter))
        )
        count_query = count_query.where(
            (User.username.ilike(search_filter)) |
            (User.email.ilike(search_filter)) |
            (User.full_name.ilike(search_filter))
        )
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get portfolio counts for each user
    user_items = []
    for user in users:
        portfolio_result = await db.execute(
            select(func.count(Portfolio.id)).where(Portfolio.user_id == user.id)
        )
        portfolio_count = portfolio_result.scalar() or 0
        
        user_items.append(UserListItem(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            base_currency=user.base_currency,
            created_at=user.created_at,
            last_login=user.last_login,
            portfolio_count=portfolio_count,
        ))
    
    total_pages = (total + page_size - 1) // page_size
    
    return UserListResponse(
        users=user_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=UserActionResponse,
    summary="Enable or disable user",
    description="Enable or disable a user account. Sends notification email."
)
async def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserActionResponse:
    """Enable or disable a user account."""
    require_superuser(current_user)
    
    # Cannot modify self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own account status"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Cannot disable another superuser
    if user.is_superuser and not status_update.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable another administrator"
        )
    
    # Update status
    old_status = user.is_active
    user.is_active = status_update.is_active
    await db.commit()
    
    # Send notification email
    email_sent = False
    if old_status != status_update.is_active:
        try:
            if status_update.is_active:
                email_sent = await send_account_enabled_email(user.email, user.username)
                action = "enabled"
            else:
                email_sent = await send_account_disabled_email(
                    user.email, 
                    user.username, 
                    status_update.reason
                )
                action = "disabled"
            
            logger.info(f"Admin {current_user.username} {action} user {user.username}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    status_text = "enabled" if status_update.is_active else "disabled"
    
    return UserActionResponse(
        success=True,
        message=f"User {user.username} has been {status_text}",
        user_id=user_id,
        email_sent=email_sent,
    )


@router.delete(
    "/users/{user_id}",
    response_model=UserActionResponse,
    summary="Delete user",
    description="Permanently delete a user and all their data. Sends notification email."
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserActionResponse:
    """Permanently delete a user account."""
    require_superuser(current_user)
    
    # Cannot delete self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Cannot delete another superuser
    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete another administrator"
        )
    
    # Store info for email before deletion
    user_email = user.email
    user_name = user.username
    
    # Manually delete related data (cascade may not work with async SQLAlchemy)
    try:
        # Get all user's portfolios
        portfolios_result = await db.execute(
            select(Portfolio.id).where(Portfolio.user_id == user_id)
        )
        portfolio_ids = [p[0] for p in portfolios_result.fetchall()]
        
        # Delete bot signals FIRST (has FK to portfolios and alerts)
        await db.execute(
            delete(BotSignal).where(BotSignal.user_id == user_id)
        )
        
        # Delete bot reports
        await db.execute(
            delete(BotReport).where(BotReport.user_id == user_id)
        )
        
        # Delete positions for all portfolios
        if portfolio_ids:
            await db.execute(
                delete(Position).where(Position.portfolio_id.in_(portfolio_ids))
            )
            # Delete trades for all portfolios
            await db.execute(
                delete(Trade).where(Trade.portfolio_id.in_(portfolio_ids))
            )
        
        # Delete portfolios
        await db.execute(
            delete(Portfolio).where(Portfolio.user_id == user_id)
        )
        
        # Get all user's watchlists and delete items
        watchlists_result = await db.execute(
            select(Watchlist.id).where(Watchlist.user_id == user_id)
        )
        watchlist_ids = [w[0] for w in watchlists_result.fetchall()]
        
        if watchlist_ids:
            await db.execute(
                delete(watchlist_symbols).where(watchlist_symbols.c.watchlist_id.in_(watchlist_ids))
            )
        
        # Delete watchlists
        await db.execute(
            delete(Watchlist).where(Watchlist.user_id == user_id)
        )
        
        # Delete alerts
        await db.execute(
            delete(Alert).where(Alert.user_id == user_id)
        )
        
        # Delete user settings
        await db.execute(
            delete(UserSettings).where(UserSettings.user_id == user_id)
        )
        
        # Finally delete the user
        await db.delete(user)
        await db.commit()
        
        logger.info(f"Admin {current_user.username} deleted user {user_name} and all related data")
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete user {user_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
    
    # Send notification email
    email_sent = False
    try:
        email_sent = await send_account_deleted_email(user_email, user_name)
    except Exception as e:
        logger.error(f"Failed to send deletion email: {e}")
    
    return UserActionResponse(
        success=True,
        message=f"User {user_name} has been permanently deleted",
        user_id=user_id,
        email_sent=email_sent,
    )


@router.patch(
    "/users/{user_id}/superuser",
    response_model=UserActionResponse,
    summary="Toggle superuser status",
    description="Grant or revoke administrator privileges. Superuser only."
)
async def toggle_superuser(
    user_id: int,
    is_superuser: bool,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserActionResponse:
    """Grant or revoke superuser privileges."""
    require_superuser(current_user)
    
    # Cannot modify self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own superuser status"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Update status
    user.is_superuser = is_superuser
    await db.commit()
    
    action = "granted admin privileges to" if is_superuser else "revoked admin privileges from"
    logger.info(f"Admin {current_user.username} {action} {user.username}")
    
    return UserActionResponse(
        success=True,
        message=f"{'Granted' if is_superuser else 'Revoked'} admin privileges for {user.username}",
        user_id=user_id,
        email_sent=False,  # No email for privilege changes
    )
