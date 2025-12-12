"""
PaperTrading Platform - Market Universe Model

Stores the universe of tracked symbols across all markets.
Supports ~800-1000 curated symbols from major indices.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Index, Enum as SQLEnum, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
import enum

from app.db.database import Base


class MarketRegion(str, enum.Enum):
    """Market regions"""
    US = "US"
    UK = "UK"
    EU = "EU"
    ASIA = "ASIA"
    GLOBAL = "GLOBAL"


class AssetType(str, enum.Enum):
    """Asset types"""
    STOCK = "STOCK"
    ETF = "ETF"
    INDEX = "INDEX"
    ADR = "ADR"


class MarketUniverse(Base):
    """
    Market Universe - tracked symbols for data collection and analysis.
    
    Contains ~800-1000 curated symbols from major global indices:
    - S&P 500 (US)
    - FTSE 100 (UK)
    - DAX 40 (Germany)
    - CAC 40 (France)
    - FTSE MIB (Italy)
    - IBEX 35 (Spain)
    - SMI 20 (Switzerland)
    - Nikkei 225 top 50 (Japan)
    - Hang Seng top 30 (Hong Kong)
    - Major ETFs
    """
    
    __tablename__ = "market_universe"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Symbol identification
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    
    # Classification
    asset_type = Column(SQLEnum(AssetType), default=AssetType.STOCK)
    region = Column(SQLEnum(MarketRegion), nullable=False)
    exchange = Column(String(20), nullable=True)  # NYSE, NASDAQ, LSE, XETRA, etc.
    currency = Column(String(10), default="USD")
    
    # Index membership (can belong to multiple)
    indices = Column(JSONB, default=list)  # ["SP500", "NASDAQ100", etc.]
    
    # Fundamental data (updated periodically)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)  # Can disable without deleting
    priority = Column(Integer, default=1)  # 1=high priority, 2=medium, 3=low
    
    # Data collection tracking
    last_quote_update = Column(DateTime, nullable=True)
    last_ohlcv_update = Column(DateTime, nullable=True)
    last_fundamental_update = Column(DateTime, nullable=True)
    
    # Error tracking
    consecutive_failures = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('ix_market_universe_region_active', 'region', 'is_active'),
        Index('ix_market_universe_exchange', 'exchange'),
        Index('ix_market_universe_priority', 'priority', 'is_active'),
    )
    
    def __repr__(self):
        return f"<MarketUniverse {self.symbol} ({self.region.value})>"
    
    @property
    def needs_quote_update(self) -> bool:
        """Check if quote needs updating (older than 5 minutes)"""
        if not self.last_quote_update:
            return True
        from datetime import timedelta
        return datetime.utcnow() - self.last_quote_update > timedelta(minutes=5)
    
    @property  
    def needs_ohlcv_update(self) -> bool:
        """Check if OHLCV needs updating (older than 1 day)"""
        if not self.last_ohlcv_update:
            return True
        from datetime import timedelta
        return datetime.utcnow() - self.last_ohlcv_update > timedelta(days=1)
