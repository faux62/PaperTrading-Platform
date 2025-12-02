"""
Gap Detector

Detects missing data gaps in historical market data.
Helps identify when data needs to be backfilled.
"""
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from typing import Optional
from loguru import logger

from app.data_providers.adapters.base import OHLCV, TimeFrame, MarketType


@dataclass
class DataGap:
    """Represents a gap in historical data."""
    symbol: str
    timeframe: TimeFrame
    start: datetime
    end: datetime
    expected_bars: int
    actual_bars: int
    
    @property
    def missing_bars(self) -> int:
        return self.expected_bars - self.actual_bars
    
    @property
    def gap_duration(self) -> timedelta:
        return self.end - self.start
    
    def __repr__(self) -> str:
        return (
            f"DataGap({self.symbol}, {self.start.date()} to {self.end.date()}, "
            f"missing {self.missing_bars} bars)"
        )


@dataclass
class MarketHours:
    """Market trading hours configuration."""
    open_hour: int = 9
    open_minute: int = 30
    close_hour: int = 16
    close_minute: int = 0
    timezone: str = "America/New_York"
    
    # Days when market is closed (0=Monday, 6=Sunday)
    closed_days: list[int] = field(default_factory=lambda: [5, 6])  # Sat, Sun
    
    # US market holidays (dates as MMDD strings for easy comparison)
    holidays: set[str] = field(default_factory=set)


# Default market hours configurations
US_MARKET_HOURS = MarketHours(
    open_hour=9,
    open_minute=30,
    close_hour=16,
    close_minute=0,
    timezone="America/New_York",
    closed_days=[5, 6],
)

EU_MARKET_HOURS = MarketHours(
    open_hour=8,
    open_minute=0,
    close_hour=16,
    close_minute=30,
    timezone="Europe/London",
    closed_days=[5, 6],
)

CRYPTO_MARKET_HOURS = MarketHours(
    open_hour=0,
    open_minute=0,
    close_hour=23,
    close_minute=59,
    timezone="UTC",
    closed_days=[],  # Crypto trades 24/7
)


class GapDetector:
    """
    Detects gaps in historical market data.
    
    Features:
    - Identifies missing bars in time series
    - Accounts for market hours and holidays
    - Supports different timeframes
    - Returns actionable gap information
    """
    
    def __init__(self):
        self._market_hours: dict[MarketType, MarketHours] = {
            MarketType.US_STOCK: US_MARKET_HOURS,
            MarketType.EU_STOCK: EU_MARKET_HOURS,
            MarketType.CRYPTO: CRYPTO_MARKET_HOURS,
            MarketType.FOREX: CRYPTO_MARKET_HOURS,  # Forex ~24/5
        }
        
        # Known holidays (format: "YYYY-MM-DD")
        self._holidays: dict[MarketType, set[str]] = {
            MarketType.US_STOCK: {
                # 2024 US Market Holidays
                "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29",
                "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02",
                "2024-11-28", "2024-12-25",
                # 2025 US Market Holidays
                "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18",
                "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01",
                "2025-11-27", "2025-12-25",
            },
        }
    
    def set_market_hours(self, market_type: MarketType, hours: MarketHours) -> None:
        """Set custom market hours for a market type."""
        self._market_hours[market_type] = hours
    
    def add_holiday(self, market_type: MarketType, holiday: str) -> None:
        """Add a holiday date (format: YYYY-MM-DD)."""
        if market_type not in self._holidays:
            self._holidays[market_type] = set()
        self._holidays[market_type].add(holiday)
    
    def detect_gaps(
        self,
        data: list[OHLCV],
        start_date: date,
        end_date: date,
        market_type: MarketType = MarketType.US_STOCK,
    ) -> list[DataGap]:
        """
        Detect gaps in historical OHLCV data.
        
        Args:
            data: List of OHLCV bars (should be sorted by timestamp)
            start_date: Expected start date
            end_date: Expected end date
            market_type: Market type for trading hours
            
        Returns:
            List of detected gaps
        """
        if not data:
            # All data is missing
            expected = self._count_expected_bars(
                start_date, end_date, data[0].timeframe if data else TimeFrame.DAY, market_type
            )
            return [DataGap(
                symbol="UNKNOWN",
                timeframe=TimeFrame.DAY,
                start=datetime.combine(start_date, datetime.min.time()),
                end=datetime.combine(end_date, datetime.max.time()),
                expected_bars=expected,
                actual_bars=0,
            )]
        
        gaps: list[DataGap] = []
        symbol = data[0].symbol
        timeframe = data[0].timeframe
        
        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        
        # Check for gap at the beginning
        first_bar = sorted_data[0]
        if first_bar.timestamp.date() > start_date:
            expected = self._count_expected_bars(
                start_date, first_bar.timestamp.date() - timedelta(days=1), timeframe, market_type
            )
            if expected > 0:
                gaps.append(DataGap(
                    symbol=symbol,
                    timeframe=timeframe,
                    start=datetime.combine(start_date, datetime.min.time()),
                    end=first_bar.timestamp - self._get_bar_duration(timeframe),
                    expected_bars=expected,
                    actual_bars=0,
                ))
        
        # Check for gaps between bars
        for i in range(len(sorted_data) - 1):
            current = sorted_data[i]
            next_bar = sorted_data[i + 1]
            
            expected_next = self._get_next_expected_timestamp(
                current.timestamp, timeframe, market_type
            )
            
            if next_bar.timestamp > expected_next:
                # There's a gap
                gap_start = expected_next
                gap_end = next_bar.timestamp - self._get_bar_duration(timeframe)
                
                expected = self._count_expected_bars(
                    gap_start.date(), gap_end.date(), timeframe, market_type
                )
                
                if expected > 0:
                    gaps.append(DataGap(
                        symbol=symbol,
                        timeframe=timeframe,
                        start=gap_start,
                        end=gap_end,
                        expected_bars=expected,
                        actual_bars=0,
                    ))
        
        # Check for gap at the end
        last_bar = sorted_data[-1]
        if last_bar.timestamp.date() < end_date:
            expected = self._count_expected_bars(
                last_bar.timestamp.date() + timedelta(days=1), end_date, timeframe, market_type
            )
            if expected > 0:
                gaps.append(DataGap(
                    symbol=symbol,
                    timeframe=timeframe,
                    start=last_bar.timestamp + self._get_bar_duration(timeframe),
                    end=datetime.combine(end_date, datetime.max.time()),
                    expected_bars=expected,
                    actual_bars=0,
                ))
        
        return gaps
    
    def _get_bar_duration(self, timeframe: TimeFrame) -> timedelta:
        """Get the duration of a single bar."""
        durations = {
            TimeFrame.MINUTE_1: timedelta(minutes=1),
            TimeFrame.MINUTE_5: timedelta(minutes=5),
            TimeFrame.MINUTE_15: timedelta(minutes=15),
            TimeFrame.MINUTE_30: timedelta(minutes=30),
            TimeFrame.HOUR_1: timedelta(hours=1),
            TimeFrame.HOUR_4: timedelta(hours=4),
            TimeFrame.DAY: timedelta(days=1),
            TimeFrame.WEEK: timedelta(weeks=1),
            TimeFrame.MONTH: timedelta(days=30),  # Approximate
        }
        return durations.get(timeframe, timedelta(days=1))
    
    def _get_next_expected_timestamp(
        self,
        current: datetime,
        timeframe: TimeFrame,
        market_type: MarketType,
    ) -> datetime:
        """Calculate the next expected bar timestamp."""
        duration = self._get_bar_duration(timeframe)
        next_ts = current + duration
        
        # For daily and longer timeframes, skip non-trading days
        if timeframe in [TimeFrame.DAY, TimeFrame.WEEK, TimeFrame.MONTH]:
            while not self._is_trading_day(next_ts.date(), market_type):
                next_ts += timedelta(days=1)
        
        return next_ts
    
    def _is_trading_day(self, d: date, market_type: MarketType) -> bool:
        """Check if a date is a trading day."""
        hours = self._market_hours.get(market_type, US_MARKET_HOURS)
        
        # Check day of week
        if d.weekday() in hours.closed_days:
            return False
        
        # Check holidays
        holidays = self._holidays.get(market_type, set())
        if d.isoformat() in holidays:
            return False
        
        return True
    
    def _count_expected_bars(
        self,
        start_date: date,
        end_date: date,
        timeframe: TimeFrame,
        market_type: MarketType,
    ) -> int:
        """Count expected bars between two dates."""
        if start_date > end_date:
            return 0
        
        if timeframe == TimeFrame.DAY:
            # Count trading days
            count = 0
            current = start_date
            while current <= end_date:
                if self._is_trading_day(current, market_type):
                    count += 1
                current += timedelta(days=1)
            return count
        
        elif timeframe == TimeFrame.WEEK:
            # Count weeks
            delta = end_date - start_date
            return max(1, delta.days // 7)
        
        elif timeframe == TimeFrame.MONTH:
            # Count months
            months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            return max(1, months)
        
        else:
            # For intraday, estimate based on trading hours
            hours = self._market_hours.get(market_type, US_MARKET_HOURS)
            trading_minutes_per_day = (
                (hours.close_hour * 60 + hours.close_minute) -
                (hours.open_hour * 60 + hours.open_minute)
            )
            
            trading_days = self._count_expected_bars(
                start_date, end_date, TimeFrame.DAY, market_type
            )
            
            bars_per_day = {
                TimeFrame.MINUTE_1: trading_minutes_per_day,
                TimeFrame.MINUTE_5: trading_minutes_per_day // 5,
                TimeFrame.MINUTE_15: trading_minutes_per_day // 15,
                TimeFrame.MINUTE_30: trading_minutes_per_day // 30,
                TimeFrame.HOUR_1: trading_minutes_per_day // 60,
                TimeFrame.HOUR_4: trading_minutes_per_day // 240,
            }
            
            return trading_days * bars_per_day.get(timeframe, 1)
    
    def get_missing_date_ranges(
        self,
        gaps: list[DataGap],
    ) -> list[tuple[date, date]]:
        """
        Convert gaps to date ranges for backfill requests.
        
        Returns:
            List of (start_date, end_date) tuples
        """
        if not gaps:
            return []
        
        # Merge overlapping gaps
        sorted_gaps = sorted(gaps, key=lambda g: g.start)
        merged: list[tuple[date, date]] = []
        
        current_start = sorted_gaps[0].start.date()
        current_end = sorted_gaps[0].end.date()
        
        for gap in sorted_gaps[1:]:
            gap_start = gap.start.date()
            gap_end = gap.end.date()
            
            if gap_start <= current_end + timedelta(days=1):
                # Overlapping or adjacent, extend
                current_end = max(current_end, gap_end)
            else:
                # New range
                merged.append((current_start, current_end))
                current_start = gap_start
                current_end = gap_end
        
        merged.append((current_start, current_end))
        return merged
    
    def summarize_gaps(self, gaps: list[DataGap]) -> dict:
        """Get a summary of detected gaps."""
        if not gaps:
            return {
                "total_gaps": 0,
                "total_missing_bars": 0,
                "affected_symbols": [],
            }
        
        symbols = set(g.symbol for g in gaps)
        total_missing = sum(g.missing_bars for g in gaps)
        
        return {
            "total_gaps": len(gaps),
            "total_missing_bars": total_missing,
            "affected_symbols": list(symbols),
            "date_ranges": self.get_missing_date_ranges(gaps),
            "gaps_by_symbol": {
                symbol: [g for g in gaps if g.symbol == symbol]
                for symbol in symbols
            },
        }


# Global gap detector instance
gap_detector = GapDetector()
