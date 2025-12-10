"""
PaperTrading Platform - Notifications API Endpoints

Test and manage email notifications.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional
from loguru import logger

from app.dependencies import get_current_active_user, get_db
from app.db.models.user import User
from app.services.email_service import email_service

router = APIRouter()


class TestEmailRequest(BaseModel):
    """Request to send a test email."""
    email_type: str = "trade"  # trade, price_alert, portfolio_summary, system_alert


class EmailStatusResponse(BaseModel):
    """Email service status response."""
    enabled: bool
    configured: bool
    smtp_host: str
    smtp_user: Optional[str] = None


@router.get("/status")
async def get_email_status(
    current_user: User = Depends(get_current_active_user)
) -> EmailStatusResponse:
    """
    Get email service status.
    Shows if email notifications are configured and enabled.
    """
    from app.services.email_service import EmailConfig
    
    return EmailStatusResponse(
        enabled=email_service.is_enabled(),
        configured=EmailConfig.is_configured(),
        smtp_host=EmailConfig.SMTP_HOST,
        smtp_user=EmailConfig.SMTP_USER[:3] + "***" if EmailConfig.SMTP_USER else None,
    )


@router.post("/test")
async def send_test_email(
    request: TestEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
):
    """
    Send a test email to verify configuration.
    
    Email types:
    - trade: Test trade execution notification
    - price_alert: Test price alert notification  
    - portfolio_summary: Test portfolio summary
    - system_alert: Test system alert
    """
    if not email_service.is_enabled():
        raise HTTPException(
            status_code=400,
            detail="Email service not configured. Set SMTP_USER and SMTP_PASSWORD environment variables."
        )
    
    user_email = current_user.email
    
    if request.email_type == "trade":
        background_tasks.add_task(
            email_service.send_trade_notification,
            to_email=user_email,
            symbol="AAPL",
            trade_type="BUY",
            quantity=10,
            price=178.50,
            total_value=1785.00,
            portfolio_name="Test Portfolio",
            executed_at=__import__("datetime").datetime.now(),
        )
        
    elif request.email_type == "price_alert":
        background_tasks.add_task(
            email_service.send_price_alert,
            to_email=user_email,
            symbol="TSLA",
            current_price=255.00,
            target_price=250.00,
            direction="above",
        )
        
    elif request.email_type == "portfolio_summary":
        background_tasks.add_task(
            email_service.send_portfolio_summary,
            to_email=user_email,
            portfolio_name="Test Portfolio",
            total_value=105000.00,
            day_change=1250.00,
            day_change_percent=1.20,
            cash_balance=25000.00,
            positions=[
                {"symbol": "AAPL", "quantity": 50, "pnl_percent": 2.5},
                {"symbol": "GOOGL", "quantity": 20, "pnl_percent": -0.8},
                {"symbol": "MSFT", "quantity": 30, "pnl_percent": 1.2},
            ],
        )
        
    elif request.email_type == "system_alert":
        background_tasks.add_task(
            email_service.send_system_alert,
            to_email=user_email,
            title="Test Alert",
            message="This is a test system alert to verify your email notification configuration is working correctly.",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown email type: {request.email_type}. Use: trade, price_alert, portfolio_summary, system_alert"
        )
    
    return {
        "message": f"Test {request.email_type} email queued for delivery to {user_email}",
        "status": "queued"
    }


@router.post("/test-direct")
async def send_test_email_direct(
    request: TestEmailRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Send a test email directly (synchronous) to verify configuration.
    Returns immediately with success/failure.
    """
    if not email_service.is_enabled():
        raise HTTPException(
            status_code=400,
            detail="Email service not configured. Set SMTP_USER and SMTP_PASSWORD environment variables."
        )
    
    user_email = current_user.email
    success = False
    
    try:
        if request.email_type == "trade":
            success = await email_service.send_trade_notification(
                to_email=user_email,
                symbol="AAPL",
                trade_type="BUY",
                quantity=10,
                price=178.50,
                total_value=1785.00,
                portfolio_name="Test Portfolio",
                executed_at=__import__("datetime").datetime.now(),
            )
            
        elif request.email_type == "price_alert":
            success = await email_service.send_price_alert(
                to_email=user_email,
                symbol="TSLA",
                current_price=255.00,
                target_price=250.00,
                direction="above",
            )
            
        elif request.email_type == "portfolio_summary":
            success = await email_service.send_portfolio_summary(
                to_email=user_email,
                portfolio_name="Test Portfolio",
                total_value=105000.00,
                day_change=1250.00,
                day_change_percent=1.20,
                cash_balance=25000.00,
                positions=[
                    {"symbol": "AAPL", "quantity": 50, "pnl_percent": 2.5},
                    {"symbol": "GOOGL", "quantity": 20, "pnl_percent": -0.8},
                    {"symbol": "MSFT", "quantity": 30, "pnl_percent": 1.2},
                ],
            )
            
        elif request.email_type == "system_alert":
            success = await email_service.send_system_alert(
                to_email=user_email,
                title="Test Alert",
                message="This is a test system alert to verify your email notification configuration is working correctly.",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown email type: {request.email_type}"
            )
        
        if success:
            return {
                "message": f"Test {request.email_type} email sent successfully to {user_email}",
                "status": "sent"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send email. Check server logs for details."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )
