"""
PaperTrading Platform - User Settings Model
Stores user preferences and API keys for data providers
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from cryptography.fernet import Fernet
import os
import json

from app.db.database import Base

# Encryption key for API keys - generate stable key from a seed
def _get_encryption_key():
    key = os.getenv("ENCRYPTION_KEY")
    if key:
        return key.encode() if isinstance(key, str) else key
    # In development, use a stable default key
    return b'Ld7rJ3hK9mP2wQ5xZ8vB4nF6tY1cA0eI3gU7oS-DfHs='


class UserSettings(Base):
    """User settings and preferences model."""
    
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Data Provider API Keys (encrypted individually)
    # US Market Primary
    api_key_alpaca = Column(Text, nullable=True)
    api_key_alpaca_secret = Column(Text, nullable=True)  # Alpaca has two keys
    api_key_polygon = Column(Text, nullable=True)
    
    # Global Coverage
    api_key_finnhub = Column(Text, nullable=True)
    api_key_twelvedata = Column(Text, nullable=True)
    
    # Historical Data
    api_key_eodhd = Column(Text, nullable=True)
    
    # Fundamentals
    api_key_fmp = Column(Text, nullable=True)
    api_key_alphavantage = Column(Text, nullable=True)
    
    # Additional Providers
    api_key_nasdaq = Column(Text, nullable=True)
    api_key_tiingo = Column(Text, nullable=True)
    api_key_marketstack = Column(Text, nullable=True)
    api_key_stockdata = Column(Text, nullable=True)
    api_key_intrinio = Column(Text, nullable=True)
    
    # No API Key Required (stored for reference only)
    api_key_yfinance = Column(Text, nullable=True)
    api_key_stooq = Column(Text, nullable=True)
    api_key_investingcom = Column(Text, nullable=True)
    
    # Theme settings
    theme = Column(String(20), default="dark")  # dark, light, system
    
    # Notification settings
    notifications_email = Column(Boolean, default=True)
    notifications_push = Column(Boolean, default=True)
    notifications_trade_execution = Column(Boolean, default=True)
    notifications_price_alerts = Column(Boolean, default=True)
    notifications_portfolio_updates = Column(Boolean, default=True)
    notifications_market_news = Column(Boolean, default=False)
    
    # Display settings
    display_compact_mode = Column(Boolean, default=False)
    display_show_percent_change = Column(Boolean, default=True)
    display_default_chart_period = Column(String(10), default="1M")
    display_chart_type = Column(String(20), default="candlestick")
    
    # Security tracking
    password_changed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="settings")
    
    def __repr__(self):
        return f"<UserSettings user_id={self.user_id}>"
    
    @staticmethod
    def _get_cipher():
        """Get Fernet cipher for encryption/decryption."""
        key = _get_encryption_key()
        return Fernet(key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key."""
        if not api_key:
            return None
        cipher = self._get_cipher()
        return cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an API key."""
        if not encrypted_key:
            return None
        try:
            cipher = self._get_cipher()
            return cipher.decrypt(encrypted_key.encode()).decode()
        except Exception:
            return None
    
    def set_provider_key(self, provider: str, api_key: str):
        """Set an encrypted API key for a provider."""
        encrypted = self.encrypt_api_key(api_key) if api_key else None
        attr_name = f"api_key_{provider}"
        if hasattr(self, attr_name):
            setattr(self, attr_name, encrypted)
    
    def get_provider_key(self, provider: str) -> str:
        """Get a decrypted API key for a provider."""
        attr_name = f"api_key_{provider}"
        if hasattr(self, attr_name):
            encrypted = getattr(self, attr_name)
            return self.decrypt_api_key(encrypted)
        return None
    
    def has_provider_key(self, provider: str) -> bool:
        """Check if a provider has an API key configured."""
        attr_name = f"api_key_{provider}"
        if hasattr(self, attr_name):
            return bool(getattr(self, attr_name))
        return False
