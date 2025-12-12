"""
PaperTrading Platform - Price Bar Model (TimescaleDB)

Stores historical OHLCV data for all tracked symbols.
Uses TimescaleDB hypertable for efficient time-series queries.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    Index, BigInteger, Enum as SQLEnum
)
import enum

from app.db.database import Base


class TimeFrame(str, enum.Enum):
    """Supported timeframes for price bars"""
    M1 = "1m"      # 1 minute
    M5 = "5m"      # 5 minutes
    M15 = "15m"    # 15 minutes
    M30 = "30m"    # 30 minutes
    H1 = "1h"      # 1 hour
    H4 = "4h"      # 4 hours
    D1 = "1d"      # 1 day
    W1 = "1w"      # 1 week


class PriceBar(Base):
    """
    OHLCV Price Bar - historical market data.
    
    Designed for TimescaleDB hypertable with:
    - Automatic partitioning by time
    - Efficient compression for older data
    - Fast time-range queries
    
    Primary use cases:
    - Technical indicator calculation
    - ML model training
    - Backtesting strategies
    - Chart rendering
    """
    
    __tablename__ = "price_bars"
    
    # Composite primary key: symbol + timeframe + timestamp
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Identification
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(SQLEnum(TimeFrame), nullable=False, default=TimeFrame.D1)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=True)
    
    # Additional data
    adjusted_close = Column(Float, nullable=True)  # For dividends/splits
    vwap = Column(Float, nullable=True)  # Volume weighted average price
    trade_count = Column(Integer, nullable=True)  # Number of trades
    
    # Data source tracking
    source = Column(String(50), nullable=True)  # Provider name
    
    # Indexes for efficient queries
    __table_args__ = (
        # Main query pattern: symbol + timeframe + time range
        Index('ix_price_bars_symbol_tf_ts', 'symbol', 'timeframe', 'timestamp'),
        # Unique constraint to prevent duplicates
        Index('ix_price_bars_unique', 'symbol', 'timeframe', 'timestamp', unique=True),
    )
    
    def __repr__(self):
        return f"<PriceBar {self.symbol} {self.timeframe.value} {self.timestamp}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe.value,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "adjusted_close": self.adjusted_close,
        }


# =============================================================================
# TimescaleDB Setup SQL (run manually or via migration)
# =============================================================================
"""
-- Convert to hypertable (run after table creation)
SELECT create_hypertable('price_bars', 'timestamp', 
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Add compression policy (compress data older than 7 days)
ALTER TABLE price_bars SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,timeframe'
);

SELECT add_compression_policy('price_bars', INTERVAL '7 days');

-- Add retention policy (keep 2 years of data)
SELECT add_retention_policy('price_bars', INTERVAL '2 years');

-- Create continuous aggregate for daily OHLCV from minute data
CREATE MATERIALIZED VIEW price_bars_daily
WITH (timescaledb.continuous) AS
SELECT 
    symbol,
    time_bucket('1 day', timestamp) AS bucket,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM price_bars
WHERE timeframe = '1m'
GROUP BY symbol, bucket;
"""
