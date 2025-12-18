"""
PaperTrading Platform - Services Package
"""
from app.services.email_service import email_service, EmailService
from app.services.fx_rate_updater import fx_rate_updater, FxRateUpdaterService, update_exchange_rates

__all__ = [
    "email_service",
    "EmailService",
    "fx_rate_updater",
    "FxRateUpdaterService",
    "update_exchange_rates",
]
