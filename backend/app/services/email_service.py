"""
PaperTrading Platform - Email Notification Service

Sends email notifications via Gmail SMTP for:
- Trade executions
- Price alerts
- Portfolio updates
- Optimizer proposals
- System alerts
"""
import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
from jinja2 import Template
import os

from app.config import settings


class EmailConfig:
    """Email configuration from environment."""
    
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")  # Gmail App Password
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "PaperTrading Platform")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER", ""))
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if email is properly configured."""
        return bool(cls.SMTP_USER and cls.SMTP_PASSWORD)


# Email Templates
TEMPLATES = {
    "trade_executed": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background-color: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #16213e; border-radius: 10px; padding: 30px; }
        .header { text-align: center; border-bottom: 2px solid #0f3460; padding-bottom: 20px; margin-bottom: 20px; }
        .header h1 { color: #00d9ff; margin: 0; }
        .trade-info { background: #0f3460; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .trade-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #1a1a2e; }
        .trade-row:last-child { border-bottom: none; }
        .label { color: #888; }
        .value { font-weight: bold; color: #fff; }
        .buy { color: #10b981; }
        .sell { color: #ef4444; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 Trade Executed</h1>
        </div>
        <div class="trade-info">
            <div class="trade-row">
                <span class="label">Symbol</span>
                <span class="value">{{ symbol }}</span>
            </div>
            <div class="trade-row">
                <span class="label">Type</span>
                <span class="value {{ 'buy' if trade_type == 'BUY' else 'sell' }}">{{ trade_type }}</span>
            </div>
            <div class="trade-row">
                <span class="label">Quantity</span>
                <span class="value">{{ quantity }}</span>
            </div>
            <div class="trade-row">
                <span class="label">Price</span>
                <span class="value">${{ "%.2f"|format(price) }}</span>
            </div>
            <div class="trade-row">
                <span class="label">Total Value</span>
                <span class="value">${{ "%.2f"|format(total_value) }}</span>
            </div>
            <div class="trade-row">
                <span class="label">Portfolio</span>
                <span class="value">{{ portfolio_name }}</span>
            </div>
            <div class="trade-row">
                <span class="label">Executed At</span>
                <span class="value">{{ executed_at }}</span>
            </div>
        </div>
        <div class="footer">
            <p>PaperTrading Platform - Paper Trading Made Simple</p>
        </div>
    </div>
</body>
</html>
""",

    "price_alert": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background-color: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #16213e; border-radius: 10px; padding: 30px; }
        .header { text-align: center; border-bottom: 2px solid #0f3460; padding-bottom: 20px; margin-bottom: 20px; }
        .header h1 { color: #f59e0b; margin: 0; }
        .alert-info { background: #0f3460; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }
        .symbol { font-size: 32px; font-weight: bold; color: #00d9ff; }
        .price { font-size: 48px; font-weight: bold; margin: 20px 0; }
        .above { color: #10b981; }
        .below { color: #ef4444; }
        .condition { color: #888; font-size: 14px; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔔 Price Alert Triggered</h1>
        </div>
        <div class="alert-info">
            <div class="symbol">{{ symbol }}</div>
            <div class="price {{ 'above' if direction == 'above' else 'below' }}">${{ "%.2f"|format(current_price) }}</div>
            <div class="condition">
                Price went {{ direction }} your target of ${{ "%.2f"|format(target_price) }}
            </div>
        </div>
        <div class="footer">
            <p>PaperTrading Platform - Paper Trading Made Simple</p>
        </div>
    </div>
</body>
</html>
""",

    "portfolio_summary": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background-color: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #16213e; border-radius: 10px; padding: 30px; }
        .header { text-align: center; border-bottom: 2px solid #0f3460; padding-bottom: 20px; margin-bottom: 20px; }
        .header h1 { color: #8b5cf6; margin: 0; }
        .summary { background: #0f3460; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .metric { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #1a1a2e; }
        .metric:last-child { border-bottom: none; }
        .label { color: #888; }
        .value { font-weight: bold; }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
        .positions { margin-top: 20px; }
        .position { background: #1a1a2e; border-radius: 6px; padding: 12px; margin: 8px 0; display: flex; justify-content: space-between; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Daily Portfolio Summary</h1>
            <p style="color: #888;">{{ date }}</p>
        </div>
        <div class="summary">
            <div class="metric">
                <span class="label">Portfolio</span>
                <span class="value">{{ portfolio_name }}</span>
            </div>
            <div class="metric">
                <span class="label">Total Value</span>
                <span class="value">${{ "%.2f"|format(total_value) }}</span>
            </div>
            <div class="metric">
                <span class="label">Day Change</span>
                <span class="value {{ 'positive' if day_change >= 0 else 'negative' }}">
                    {{ "%.2f"|format(day_change_percent) }}% (${{ "%.2f"|format(day_change) }})
                </span>
            </div>
            <div class="metric">
                <span class="label">Cash Balance</span>
                <span class="value">${{ "%.2f"|format(cash_balance) }}</span>
            </div>
        </div>
        {% if positions %}
        <div class="positions">
            <h3 style="color: #00d9ff;">Positions</h3>
            {% for pos in positions %}
            <div class="position">
                <span>{{ pos.symbol }} ({{ pos.quantity }})</span>
                <span class="{{ 'positive' if pos.pnl_percent >= 0 else 'negative' }}">
                    {{ "%.2f"|format(pos.pnl_percent) }}%
                </span>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        <div class="footer">
            <p>PaperTrading Platform - Paper Trading Made Simple</p>
        </div>
    </div>
</body>
</html>
""",

    "optimizer_proposal": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background-color: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #16213e; border-radius: 10px; padding: 30px; }
        .header { text-align: center; border-bottom: 2px solid #0f3460; padding-bottom: 20px; margin-bottom: 20px; }
        .header h1 { color: #10b981; margin: 0; }
        .proposal { background: #0f3460; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .action { background: #1a1a2e; border-radius: 6px; padding: 12px; margin: 8px 0; }
        .action-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .buy { color: #10b981; }
        .sell { color: #ef4444; }
        .hold { color: #f59e0b; }
        .rationale { color: #888; font-size: 13px; }
        .cta { text-align: center; margin: 30px 0; }
        .cta a { background: #10b981; color: #fff; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: bold; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 New Optimizer Proposal</h1>
            <p style="color: #888;">{{ portfolio_name }}</p>
        </div>
        <div class="proposal">
            <p style="margin-bottom: 15px;">The AI Optimizer has generated a new proposal for your portfolio:</p>
            {% for action in actions %}
            <div class="action">
                <div class="action-header">
                    <span class="{{ action.type.lower() }}">{{ action.type }} {{ action.symbol }}</span>
                    <span>{{ action.quantity }} shares @ ${{ "%.2f"|format(action.price) }}</span>
                </div>
                <div class="rationale">{{ action.rationale }}</div>
            </div>
            {% endfor %}
        </div>
        <div class="cta">
            <a href="{{ review_url }}">Review Proposal</a>
        </div>
        <p style="text-align: center; color: #888; font-size: 13px;">
            This proposal expires in 24 hours.
        </p>
        <div class="footer">
            <p>PaperTrading Platform - Paper Trading Made Simple</p>
        </div>
    </div>
</body>
</html>
""",

    "system_alert": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; background-color: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #16213e; border-radius: 10px; padding: 30px; }
        .header { text-align: center; border-bottom: 2px solid #ef4444; padding-bottom: 20px; margin-bottom: 20px; }
        .header h1 { color: #ef4444; margin: 0; }
        .alert { background: #0f3460; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid #ef4444; }
        .alert-title { font-weight: bold; margin-bottom: 10px; }
        .alert-message { color: #ccc; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ System Alert</h1>
        </div>
        <div class="alert">
            <div class="alert-title">{{ title }}</div>
            <div class="alert-message">{{ message }}</div>
        </div>
        <p style="text-align: center; color: #888; font-size: 13px;">
            {{ timestamp }}
        </p>
        <div class="footer">
            <p>PaperTrading Platform - Paper Trading Made Simple</p>
        </div>
    </div>
</body>
</html>
"""
}


class EmailService:
    """Async email service for sending notifications."""
    
    def __init__(self):
        self.config = EmailConfig
        self._connection = None
    
    def is_enabled(self) -> bool:
        """Check if email service is enabled and configured."""
        return self.config.is_configured()
    
    async def _get_connection(self) -> aiosmtplib.SMTP:
        """Get or create SMTP connection."""
        smtp = aiosmtplib.SMTP(
            hostname=self.config.SMTP_HOST,
            port=self.config.SMTP_PORT,
            use_tls=False,  # We'll use STARTTLS
            start_tls=self.config.SMTP_USE_TLS,
        )
        await smtp.connect()
        await smtp.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)
        return smtp
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body
            text_content: Plain text body (optional)
            attachments: List of attachments (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Email service not configured, skipping email send")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.SMTP_FROM_NAME} <{self.config.SMTP_FROM_EMAIL}>"
            msg["To"] = to_email
            
            # Add text part if provided
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))
            
            # Add HTML part
            msg.attach(MIMEText(html_content, "html"))
            
            # Add attachments if any
            if attachments:
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment["content"])
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={attachment['filename']}"
                    )
                    msg.attach(part)
            
            # Send email
            smtp = await self._get_connection()
            await smtp.send_message(msg)
            await smtp.quit()
            
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_trade_notification(
        self,
        to_email: str,
        symbol: str,
        trade_type: str,
        quantity: float,
        price: float,
        total_value: float,
        portfolio_name: str,
        executed_at: datetime,
    ) -> bool:
        """Send trade execution notification."""
        template = Template(TEMPLATES["trade_executed"])
        html = template.render(
            symbol=symbol,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            total_value=total_value,
            portfolio_name=portfolio_name,
            executed_at=executed_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
        
        subject = f"🔔 Trade Executed: {trade_type} {quantity} {symbol}"
        return await self.send_email(to_email, subject, html)
    
    async def send_price_alert(
        self,
        to_email: str,
        symbol: str,
        current_price: float,
        target_price: float,
        direction: str,  # 'above' or 'below'
    ) -> bool:
        """Send price alert notification."""
        template = Template(TEMPLATES["price_alert"])
        html = template.render(
            symbol=symbol,
            current_price=current_price,
            target_price=target_price,
            direction=direction,
        )
        
        subject = f"🔔 Price Alert: {symbol} is {direction} ${target_price:.2f}"
        return await self.send_email(to_email, subject, html)
    
    async def send_portfolio_summary(
        self,
        to_email: str,
        portfolio_name: str,
        total_value: float,
        day_change: float,
        day_change_percent: float,
        cash_balance: float,
        positions: List[Dict[str, Any]],
        date: Optional[str] = None,
    ) -> bool:
        """Send daily portfolio summary."""
        template = Template(TEMPLATES["portfolio_summary"])
        html = template.render(
            portfolio_name=portfolio_name,
            total_value=total_value,
            day_change=day_change,
            day_change_percent=day_change_percent,
            cash_balance=cash_balance,
            positions=positions,
            date=date or datetime.now().strftime("%B %d, %Y"),
        )
        
        subject = f"📊 Daily Summary: {portfolio_name} - ${total_value:,.2f}"
        return await self.send_email(to_email, subject, html)
    
    async def send_optimizer_proposal(
        self,
        to_email: str,
        portfolio_name: str,
        actions: List[Dict[str, Any]],
        review_url: str,
    ) -> bool:
        """Send optimizer proposal notification."""
        template = Template(TEMPLATES["optimizer_proposal"])
        html = template.render(
            portfolio_name=portfolio_name,
            actions=actions,
            review_url=review_url,
        )
        
        subject = f"🤖 New Optimizer Proposal for {portfolio_name}"
        return await self.send_email(to_email, subject, html)
    
    async def send_system_alert(
        self,
        to_email: str,
        title: str,
        message: str,
    ) -> bool:
        """Send system alert notification."""
        template = Template(TEMPLATES["system_alert"])
        html = template.render(
            title=title,
            message=message,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        )
        
        subject = f"⚠️ System Alert: {title}"
        return await self.send_email(to_email, subject, html)


# Global email service instance
email_service = EmailService()


# Helper function to check user notification preferences
async def should_send_notification(
    db,
    user_id: int,
    notification_type: str,
) -> tuple[bool, Optional[str]]:
    """
    Check if notification should be sent based on user settings.
    
    Returns:
        Tuple of (should_send, user_email)
    """
    from sqlalchemy import select
    from app.db.models.user import User
    from app.db.models.user_settings import UserSettings
    
    # Get user email
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False, None
    
    # Get user settings
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()
    
    if not settings:
        return True, user.email  # Default to enabled if no settings
    
    # Check specific notification type
    notification_settings = {
        "trade_execution": settings.notifications_trade_execution,
        "price_alert": settings.notifications_price_alerts,
        "portfolio_update": settings.notifications_portfolio_updates,
        "market_news": settings.notifications_market_news,
    }
    
    # Check if email notifications are enabled globally and for this type
    if not settings.notifications_email:
        return False, None
    
    should_send = notification_settings.get(notification_type, True)
    return should_send, user.email if should_send else None


# ==================== Admin Account Notifications ====================

ACCOUNT_ENABLED_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
        .button { display: inline-block; background: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 20px; font-weight: bold; }
        .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; border-radius: 0 0 8px 8px; background: #f3f4f6; }
        ul { padding-left: 20px; }
        li { margin: 8px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Account Enabled</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{{ username }}</strong>,</p>
            <p>Great news! Your PaperTrading Platform account has been <strong>enabled</strong> by an administrator.</p>
            <p>You can now log in and access all platform features:</p>
            <ul>
                <li>📈 Real-time market data</li>
                <li>💼 Paper trading portfolios</li>
                <li>📊 Analytics and insights</li>
                <li>🤖 AI-powered trading signals</li>
            </ul>
            <center>
                <a href="{{ frontend_url }}/login" class="button">Log In Now</a>
            </center>
        </div>
        <div class="footer">
            <p>PaperTrading Platform - Practice trading without risk</p>
        </div>
    </div>
</body>
</html>
"""

ACCOUNT_DISABLED_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
        .reason-box { background: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 6px; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; border-radius: 0 0 8px 8px; background: #f3f4f6; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Account Disabled</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{{ username }}</strong>,</p>
            <p>Your PaperTrading Platform account has been <strong>disabled</strong> by an administrator.</p>
            {% if reason %}
            <div class="reason-box">
                <strong>Reason:</strong> {{ reason }}
            </div>
            {% endif %}
            <p>While your account is disabled, you will not be able to log in or access the platform.</p>
            <p>If you believe this is an error, please contact the administrator.</p>
        </div>
        <div class="footer">
            <p>PaperTrading Platform - Practice trading without risk</p>
        </div>
    </div>
</body>
</html>
"""

ACCOUNT_DELETED_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #6b7280, #4b5563); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
        .data-box { background: #f3f4f6; border: 1px solid #e5e7eb; padding: 15px; border-radius: 6px; margin: 15px 0; }
        .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; border-radius: 0 0 8px 8px; background: #f3f4f6; }
        ul { padding-left: 20px; }
        li { margin: 8px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Account Deleted</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{{ username }}</strong>,</p>
            <p>Your PaperTrading Platform account and all associated data have been <strong>permanently deleted</strong>.</p>
            <p>This action was performed by an administrator.</p>
            <div class="data-box">
                <strong>Deleted data includes:</strong>
                <ul>
                    <li>Your profile and settings</li>
                    <li>All portfolios and positions</li>
                    <li>Trade history</li>
                    <li>Watchlists and alerts</li>
                </ul>
            </div>
            <p>If you wish to use the platform again, you can create a new account.</p>
        </div>
        <div class="footer">
            <p>PaperTrading Platform - Practice trading without risk</p>
        </div>
    </div>
</body>
</html>
"""


async def send_account_enabled_email(email: str, username: str) -> bool:
    """Send notification when account is enabled."""
    if not EmailConfig.is_configured():
        logger.info(f"Email not configured. Would notify {email} about account enabled")
        return True
    
    template = Template(ACCOUNT_ENABLED_TEMPLATE)
    html = template.render(
        username=username,
        frontend_url=settings.FRONTEND_URL
    )
    
    return await email_service.send_email(
        to_email=email,
        subject="✅ Your PaperTrading Account Has Been Enabled",
        html_content=html
    )


async def send_account_disabled_email(email: str, username: str, reason: Optional[str] = None) -> bool:
    """Send notification when account is disabled."""
    if not EmailConfig.is_configured():
        logger.info(f"Email not configured. Would notify {email} about account disabled")
        return True
    
    template = Template(ACCOUNT_DISABLED_TEMPLATE)
    html = template.render(
        username=username,
        reason=reason
    )
    
    return await email_service.send_email(
        to_email=email,
        subject="⚠️ Your PaperTrading Account Has Been Disabled",
        html_content=html
    )


async def send_account_deleted_email(email: str, username: str) -> bool:
    """Send notification when account is deleted."""
    if not EmailConfig.is_configured():
        logger.info(f"Email not configured. Would notify {email} about account deletion")
        return True
    
    template = Template(ACCOUNT_DELETED_TEMPLATE)
    html = template.render(username=username)
    
    return await email_service.send_email(
        to_email=email,
        subject="Your PaperTrading Account Has Been Deleted",
        html_content=html
    )
