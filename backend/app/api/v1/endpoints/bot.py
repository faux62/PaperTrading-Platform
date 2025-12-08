"""
Trading Assistant Bot - API Endpoints

Endpoints for:
- Getting pending signals
- Accepting/ignoring signals
- Getting reports (morning briefing, daily summary, weekly)
- Bot status and configuration
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.db.models import (
    BotSignal,
    BotReport,
    SignalType,
    SignalPriority,
    SignalStatus,
    SignalDirection,
    User,
)
from app.api.v1.endpoints.auth import get_current_user
from app.bot import get_bot_scheduler
from app.bot.signal_engine import SignalEngine


router = APIRouter(prefix="/bot", tags=["Trading Assistant Bot"])


# ==================== Pydantic Schemas ====================

class SignalResponse(BaseModel):
    """Bot signal response schema."""
    id: int
    signal_type: str
    priority: str
    status: str
    symbol: Optional[str] = None
    direction: Optional[str] = None
    title: str
    message: str
    rationale: Optional[str] = None
    
    # Trade suggestion details
    current_price: Optional[float] = None
    suggested_entry: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    suggested_quantity: Optional[int] = None
    risk_reward_ratio: Optional[float] = None
    
    # ML metadata
    confidence_score: Optional[float] = None
    ml_model_used: Optional[str] = None
    technical_indicators: Optional[dict] = None
    
    # Timestamps
    created_at: datetime
    valid_until: Optional[datetime] = None
    is_actionable: bool
    
    class Config:
        from_attributes = True


class SignalActionRequest(BaseModel):
    """Request to accept or ignore a signal."""
    action: str = Field(..., pattern="^(accept|ignore)$")
    notes: Optional[str] = Field(None, max_length=500)
    resulting_trade_id: Optional[int] = None


class ReportResponse(BaseModel):
    """Bot report response schema."""
    id: int
    report_type: str
    report_date: datetime
    title: str
    content: dict
    total_signals: int
    trades_suggested: int
    alerts_triggered: int
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class BotStatusResponse(BaseModel):
    """Bot status response."""
    is_running: bool
    jobs: dict
    pending_signals_count: int
    unread_reports_count: int


class SignalsSummary(BaseModel):
    """Summary of signals by type and status."""
    total_pending: int
    by_type: dict
    by_priority: dict
    recent_signals: List[SignalResponse]


# ==================== Signal Endpoints ====================

@router.get("/signals", response_model=List[SignalResponse])
async def get_signals(
    status: Optional[str] = Query(None, pattern="^(pending|accepted|ignored|expired)$"),
    signal_type: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get bot signals for the current user.
    
    Filter by status, type, or symbol.
    """
    query = select(BotSignal).where(BotSignal.user_id == current_user.id)
    
    if status:
        query = query.where(BotSignal.status == status)
    
    if signal_type:
        query = query.where(BotSignal.signal_type == signal_type)
    
    if symbol:
        query = query.where(BotSignal.symbol == symbol.upper())
    
    query = query.order_by(
        desc(BotSignal.priority),
        desc(BotSignal.created_at)
    ).limit(limit)
    
    result = await db.execute(query)
    signals = result.scalars().all()
    
    return [_signal_to_response(s) for s in signals]


@router.get("/signals/pending", response_model=List[SignalResponse])
async def get_pending_signals(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending (actionable) signals."""
    engine = SignalEngine(db)
    signals = await engine.get_pending_signals(current_user.id, limit=limit)
    return [_signal_to_response(s) for s in signals]


@router.get("/signals/summary", response_model=SignalsSummary)
async def get_signals_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a summary of signals."""
    # Get pending signals
    result = await db.execute(
        select(BotSignal).where(
            and_(
                BotSignal.user_id == current_user.id,
                BotSignal.status == SignalStatus.PENDING
            )
        ).order_by(desc(BotSignal.created_at))
    )
    pending_signals = result.scalars().all()
    
    # Count by type
    by_type = {}
    by_priority = {}
    
    for signal in pending_signals:
        type_key = signal.signal_type.value if signal.signal_type else 'unknown'
        priority_key = signal.priority.value if signal.priority else 'unknown'
        
        by_type[type_key] = by_type.get(type_key, 0) + 1
        by_priority[priority_key] = by_priority.get(priority_key, 0) + 1
    
    return SignalsSummary(
        total_pending=len(pending_signals),
        by_type=by_type,
        by_priority=by_priority,
        recent_signals=[_signal_to_response(s) for s in pending_signals[:10]]
    )


@router.get("/signals/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific signal by ID."""
    signal = await db.get(BotSignal, signal_id)
    
    if not signal or signal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    return _signal_to_response(signal)


@router.post("/signals/{signal_id}/action", response_model=SignalResponse)
async def signal_action(
    signal_id: int,
    action_request: SignalActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept or ignore a signal.
    
    - **accept**: User agrees with the signal and may act on it
    - **ignore**: User dismisses the signal
    """
    engine = SignalEngine(db)
    
    try:
        if action_request.action == "accept":
            signal = await engine.accept_signal(
                signal_id=signal_id,
                user_id=current_user.id,
                notes=action_request.notes,
                resulting_trade_id=action_request.resulting_trade_id
            )
        else:
            signal = await engine.ignore_signal(
                signal_id=signal_id,
                user_id=current_user.id,
                notes=action_request.notes
            )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return _signal_to_response(signal)


# ==================== Report Endpoints ====================

@router.get("/reports", response_model=List[ReportResponse])
async def get_reports(
    report_type: Optional[str] = None,
    unread_only: bool = False,
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get bot reports for the current user."""
    query = select(BotReport).where(BotReport.user_id == current_user.id)
    
    if report_type:
        query = query.where(BotReport.report_type == report_type)
    
    if unread_only:
        query = query.where(BotReport.is_read == False)
    
    query = query.order_by(desc(BotReport.report_date)).limit(limit)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return reports


@router.get("/reports/latest/{report_type}", response_model=ReportResponse)
async def get_latest_report(
    report_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the latest report of a specific type."""
    result = await db.execute(
        select(BotReport).where(
            and_(
                BotReport.user_id == current_user.id,
                BotReport.report_type == report_type
            )
        ).order_by(desc(BotReport.report_date)).limit(1)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail=f"No {report_type} report found")
    
    return report


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific report by ID."""
    report = await db.get(BotReport, report_id)
    
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report


@router.post("/reports/{report_id}/read")
async def mark_report_read(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a report as read."""
    report = await db.get(BotReport, report_id)
    
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report.is_read = True
    report.read_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Report marked as read"}


# ==================== Bot Status Endpoints ====================

@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current status of the Trading Assistant Bot."""
    scheduler = get_bot_scheduler()
    
    # Count pending signals
    result = await db.execute(
        select(BotSignal).where(
            and_(
                BotSignal.user_id == current_user.id,
                BotSignal.status == SignalStatus.PENDING
            )
        )
    )
    pending_count = len(result.scalars().all())
    
    # Count unread reports
    result = await db.execute(
        select(BotReport).where(
            and_(
                BotReport.user_id == current_user.id,
                BotReport.is_read == False
            )
        )
    )
    unread_count = len(result.scalars().all())
    
    return BotStatusResponse(
        is_running=scheduler.is_running,
        jobs=scheduler.get_jobs_status().get('jobs', {}),
        pending_signals_count=pending_count,
        unread_reports_count=unread_count
    )


# ==================== Helper Functions ====================

def _signal_to_response(signal: BotSignal) -> SignalResponse:
    """Convert BotSignal model to response schema."""
    return SignalResponse(
        id=signal.id,
        signal_type=signal.signal_type.value if signal.signal_type else 'unknown',
        priority=signal.priority.value if signal.priority else 'medium',
        status=signal.status.value if signal.status else 'pending',
        symbol=signal.symbol,
        direction=signal.direction.value if signal.direction else None,
        title=signal.title,
        message=signal.message,
        rationale=signal.rationale,
        current_price=signal.current_price,
        suggested_entry=signal.suggested_entry,
        suggested_stop_loss=signal.suggested_stop_loss,
        suggested_take_profit=signal.suggested_take_profit,
        suggested_quantity=signal.suggested_quantity,
        risk_reward_ratio=signal.risk_reward_ratio,
        confidence_score=signal.confidence_score,
        ml_model_used=signal.ml_model_used,
        technical_indicators=signal.technical_indicators,
        created_at=signal.created_at,
        valid_until=signal.valid_until,
        is_actionable=signal.is_actionable
    )
