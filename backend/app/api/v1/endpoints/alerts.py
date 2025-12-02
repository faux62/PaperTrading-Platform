"""
PaperTrading Platform - Alert Endpoints
API for managing price alerts
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.user import User
from app.db.models.alert import AlertStatus
from app.core.security import get_current_user
from app.core.alerts import AlertService
from app.schemas.alert import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertSummary,
)

router = APIRouter()


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[AlertStatus] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
):
    """Get all alerts for current user with optional filters."""
    service = AlertService(db)
    alerts = await service.get_user_alerts(
        user_id=current_user.id,
        status=status,
        symbol=symbol
    )
    return [AlertResponse.model_validate(a) for a in alerts]


@router.get("/summary", response_model=AlertSummary)
async def get_alerts_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get summary of user's alerts by status."""
    service = AlertService(db)
    return await service.get_alerts_summary(current_user.id)


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: AlertCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new price alert."""
    service = AlertService(db)
    alert = await service.create_alert(
        user_id=current_user.id,
        symbol=data.symbol,
        alert_type=data.alert_type,
        target_value=data.target_value,
        note=data.note,
        is_recurring=data.is_recurring,
        expires_at=data.expires_at
    )
    return AlertResponse.model_validate(alert)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get alert by ID."""
    service = AlertService(db)
    alert = await service.get_alert(alert_id, current_user.id)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return AlertResponse.model_validate(alert)


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    data: AlertUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update alert settings."""
    service = AlertService(db)
    alert = await service.update_alert(
        alert_id=alert_id,
        user_id=current_user.id,
        target_value=data.target_value,
        note=data.note,
        is_recurring=data.is_recurring,
        expires_at=data.expires_at
    )
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return AlertResponse.model_validate(alert)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an alert."""
    service = AlertService(db)
    deleted = await service.delete_alert(alert_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )


@router.post("/{alert_id}/toggle", response_model=AlertResponse)
async def toggle_alert(
    alert_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Enable or disable an alert."""
    service = AlertService(db)
    alert = await service.toggle_alert(alert_id, current_user.id)
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return AlertResponse.model_validate(alert)
