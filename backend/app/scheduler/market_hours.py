"""
Market Hours Manager

Manages trading hours, market sessions, and business calendars
for global stock exchanges. Used to determine when markets are
open, pre-market/after-hours sessions, and holidays.
"""
from datetime import datetime, date, time, timedelta
from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo
from functools import lru_cache
import asyncio
from loguru import logger


class MarketSession(str, Enum):
    """Trading session types."""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


class DayType(str, Enum):
    """Day classification types."""
    REGULAR = "regular"
    EARLY_CLOSE = "early_close"
    HOLIDAY = "holiday"
    WEEKEND = "weekend"


@dataclass
class MarketHours:
    """Market hours configuration for an exchange."""
    
    # Regular session
    open_time: time
    close_time: time
    timezone: str
    
    # Extended hours (optional)
    pre_market_open: Optional[time] = None
    pre_market_close: Optional[time] = None
    after_hours_open: Optional[time] = None
    after_hours_close: Optional[time] = None
    
    # Early close times
    early_close_time: Optional[time] = None
    
    # Weekend days (0=Monday, 6=Sunday)
    weekend_days: list[int] = field(default_factory=lambda: [5, 6])
    
    def get_tz(self) -> ZoneInfo:
        """Get timezone object."""
        return ZoneInfo(self.timezone)


@dataclass
class MarketStatus:
    """Current market status information."""
    exchange: str
    session: MarketSession
    is_open: bool
    local_time: datetime
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None
    day_type: DayType = DayType.REGULAR
    reason: Optional[str] = None


# ==================== Exchange Configurations ====================

EXCHANGE_HOURS: dict[str, MarketHours] = {
    # US Markets
    "NYSE": MarketHours(
        open_time=time(9, 30),
        close_time=time(16, 0),
        timezone="America/New_York",
        pre_market_open=time(4, 0),
        pre_market_close=time(9, 30),
        after_hours_open=time(16, 0),
        after_hours_close=time(20, 0),
        early_close_time=time(13, 0),
    ),
    "NASDAQ": MarketHours(
        open_time=time(9, 30),
        close_time=time(16, 0),
        timezone="America/New_York",
        pre_market_open=time(4, 0),
        pre_market_close=time(9, 30),
        after_hours_open=time(16, 0),
        after_hours_close=time(20, 0),
        early_close_time=time(13, 0),
    ),
    
    # European Markets
    "LSE": MarketHours(
        open_time=time(8, 0),
        close_time=time(16, 30),
        timezone="Europe/London",
        early_close_time=time(12, 30),
    ),
    "XETRA": MarketHours(
        open_time=time(9, 0),
        close_time=time(17, 30),
        timezone="Europe/Berlin",
        early_close_time=time(14, 0),
    ),
    "EURONEXT": MarketHours(
        open_time=time(9, 0),
        close_time=time(17, 30),
        timezone="Europe/Paris",
        early_close_time=time(14, 5),
    ),
    "BIT": MarketHours(  # Borsa Italiana
        open_time=time(9, 0),
        close_time=time(17, 30),
        timezone="Europe/Rome",
        early_close_time=time(14, 5),
    ),
    "BME": MarketHours(  # Bolsa de Madrid
        open_time=time(9, 0),
        close_time=time(17, 30),
        timezone="Europe/Madrid",
    ),
    "SIX": MarketHours(  # Swiss Exchange
        open_time=time(9, 0),
        close_time=time(17, 30),
        timezone="Europe/Zurich",
        early_close_time=time(14, 0),
    ),
    
    # Asian Markets
    "TSE": MarketHours(  # Tokyo Stock Exchange
        open_time=time(9, 0),
        close_time=time(15, 0),
        timezone="Asia/Tokyo",
        weekend_days=[5, 6],
    ),
    "HKEX": MarketHours(  # Hong Kong
        open_time=time(9, 30),
        close_time=time(16, 0),
        timezone="Asia/Hong_Kong",
    ),
    "SSE": MarketHours(  # Shanghai
        open_time=time(9, 30),
        close_time=time(15, 0),
        timezone="Asia/Shanghai",
    ),
    "SZSE": MarketHours(  # Shenzhen
        open_time=time(9, 30),
        close_time=time(15, 0),
        timezone="Asia/Shanghai",
    ),
    "NSE": MarketHours(  # National Stock Exchange India
        open_time=time(9, 15),
        close_time=time(15, 30),
        timezone="Asia/Kolkata",
        pre_market_open=time(9, 0),
        pre_market_close=time(9, 15),
    ),
    "KRX": MarketHours(  # Korea Exchange
        open_time=time(9, 0),
        close_time=time(15, 30),
        timezone="Asia/Seoul",
    ),
    "ASX": MarketHours(  # Australian Securities Exchange
        open_time=time(10, 0),
        close_time=time(16, 0),
        timezone="Australia/Sydney",
        pre_market_open=time(7, 0),
        pre_market_close=time(10, 0),
    ),
    "SGX": MarketHours(  # Singapore Exchange
        open_time=time(9, 0),
        close_time=time(17, 0),
        timezone="Asia/Singapore",
    ),
}

# Exchange aliases
EXCHANGE_ALIASES: dict[str, str] = {
    "TYO": "TSE",
    "HKG": "HKEX",
    "SHE": "SZSE",
    "BSE": "NSE",
    "KSC": "KRX",
    "FRA": "XETRA",
    "PAR": "EURONEXT",
    "MIL": "BIT",
}


# ==================== Holiday Calendars ====================

# 2024-2025 US Market Holidays
US_HOLIDAYS_2024: set[date] = {
    date(2024, 1, 1),   # New Year's Day
    date(2024, 1, 15),  # MLK Day
    date(2024, 2, 19),  # Presidents Day
    date(2024, 3, 29),  # Good Friday
    date(2024, 5, 27),  # Memorial Day
    date(2024, 6, 19),  # Juneteenth
    date(2024, 7, 4),   # Independence Day
    date(2024, 9, 2),   # Labor Day
    date(2024, 11, 28), # Thanksgiving
    date(2024, 12, 25), # Christmas
}

US_HOLIDAYS_2025: set[date] = {
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas
}

US_EARLY_CLOSE_2024: set[date] = {
    date(2024, 7, 3),   # Day before Independence Day
    date(2024, 11, 29), # Day after Thanksgiving
    date(2024, 12, 24), # Christmas Eve
}

HOLIDAY_CALENDARS: dict[str, dict[int, set[date]]] = {
    "NYSE": {2024: US_HOLIDAYS_2024, 2025: US_HOLIDAYS_2025},
    "NASDAQ": {2024: US_HOLIDAYS_2024, 2025: US_HOLIDAYS_2025},
}

EARLY_CLOSE_CALENDARS: dict[str, dict[int, set[date]]] = {
    "NYSE": {2024: US_EARLY_CLOSE_2024},
    "NASDAQ": {2024: US_EARLY_CLOSE_2024},
}


# ==================== Market Hours Manager ====================

class MarketHoursManager:
    """
    Manager for global market hours and trading sessions.
    
    Provides:
    - Current market status (open/closed/session type)
    - Next open/close times
    - Holiday detection
    - Business day calculations
    
    Usage:
        manager = MarketHoursManager()
        
        status = manager.get_market_status("NYSE")
        print(f"NYSE is {'open' if status.is_open else 'closed'}")
        
        if manager.is_trading_day("NASDAQ", date.today()):
            print("NASDAQ is open today")
    """
    
    def __init__(self):
        self._custom_holidays: dict[str, set[date]] = {}
        self._custom_early_close: dict[str, set[date]] = {}
    
    def get_exchange_hours(self, exchange: str) -> MarketHours:
        """Get market hours for an exchange."""
        exchange = EXCHANGE_ALIASES.get(exchange.upper(), exchange.upper())
        
        if exchange not in EXCHANGE_HOURS:
            raise ValueError(f"Unknown exchange: {exchange}")
        
        return EXCHANGE_HOURS[exchange]
    
    def get_market_status(
        self,
        exchange: str,
        at_time: Optional[datetime] = None,
    ) -> MarketStatus:
        """
        Get current market status for an exchange.
        
        Args:
            exchange: Exchange code (NYSE, NASDAQ, TSE, etc.)
            at_time: Time to check (default: now)
            
        Returns:
            MarketStatus with session info
        """
        exchange = EXCHANGE_ALIASES.get(exchange.upper(), exchange.upper())
        hours = self.get_exchange_hours(exchange)
        tz = hours.get_tz()
        
        if at_time is None:
            at_time = datetime.now(tz)
        elif at_time.tzinfo is None:
            at_time = at_time.replace(tzinfo=tz)
        
        local_time = at_time.astimezone(tz)
        current_date = local_time.date()
        current_time = local_time.time()
        
        # Check weekend
        if local_time.weekday() in hours.weekend_days:
            return MarketStatus(
                exchange=exchange,
                session=MarketSession.CLOSED,
                is_open=False,
                local_time=local_time,
                next_open=self._next_trading_day_open(exchange, current_date),
                day_type=DayType.WEEKEND,
                reason="Weekend",
            )
        
        # Check holiday
        if self._is_holiday(exchange, current_date):
            return MarketStatus(
                exchange=exchange,
                session=MarketSession.CLOSED,
                is_open=False,
                local_time=local_time,
                next_open=self._next_trading_day_open(exchange, current_date),
                day_type=DayType.HOLIDAY,
                reason="Market Holiday",
            )
        
        # Check early close
        is_early_close = self._is_early_close(exchange, current_date)
        close_time = hours.early_close_time if is_early_close else hours.close_time
        day_type = DayType.EARLY_CLOSE if is_early_close else DayType.REGULAR
        
        # Determine session
        session = self._determine_session(hours, current_time, close_time)
        
        return MarketStatus(
            exchange=exchange,
            session=session,
            is_open=session == MarketSession.REGULAR,
            local_time=local_time,
            next_open=self._get_next_open(exchange, local_time, hours, close_time),
            next_close=self._get_next_close(exchange, local_time, hours, close_time),
            day_type=day_type,
        )
    
    def _determine_session(
        self,
        hours: MarketHours,
        current_time: time,
        close_time: time,
    ) -> MarketSession:
        """Determine current trading session."""
        # Check pre-market
        if hours.pre_market_open and hours.pre_market_close:
            if hours.pre_market_open <= current_time < hours.pre_market_close:
                return MarketSession.PRE_MARKET
        
        # Check regular session
        if hours.open_time <= current_time < close_time:
            return MarketSession.REGULAR
        
        # Check after-hours
        if hours.after_hours_open and hours.after_hours_close:
            if hours.after_hours_open <= current_time < hours.after_hours_close:
                return MarketSession.AFTER_HOURS
        
        return MarketSession.CLOSED
    
    def _is_holiday(self, exchange: str, check_date: date) -> bool:
        """Check if date is a holiday."""
        # Check custom holidays
        if exchange in self._custom_holidays:
            if check_date in self._custom_holidays[exchange]:
                return True
        
        # Check calendar holidays
        if exchange in HOLIDAY_CALENDARS:
            year_holidays = HOLIDAY_CALENDARS[exchange].get(check_date.year, set())
            return check_date in year_holidays
        
        return False
    
    def _is_early_close(self, exchange: str, check_date: date) -> bool:
        """Check if date is an early close day."""
        if exchange in self._custom_early_close:
            if check_date in self._custom_early_close[exchange]:
                return True
        
        if exchange in EARLY_CLOSE_CALENDARS:
            year_early = EARLY_CLOSE_CALENDARS[exchange].get(check_date.year, set())
            return check_date in year_early
        
        return False
    
    def _next_trading_day_open(
        self,
        exchange: str,
        from_date: date,
    ) -> datetime:
        """Get next trading day open time."""
        hours = self.get_exchange_hours(exchange)
        tz = hours.get_tz()
        
        next_date = from_date + timedelta(days=1)
        
        for _ in range(10):  # Max 10 days ahead
            if self.is_trading_day(exchange, next_date):
                return datetime.combine(next_date, hours.open_time, tzinfo=tz)
            next_date += timedelta(days=1)
        
        return datetime.combine(next_date, hours.open_time, tzinfo=tz)
    
    def _get_next_open(
        self,
        exchange: str,
        local_time: datetime,
        hours: MarketHours,
        close_time: time,
    ) -> Optional[datetime]:
        """Get next market open time."""
        tz = hours.get_tz()
        current_date = local_time.date()
        current_time = local_time.time()
        
        # If before today's open
        if current_time < hours.open_time:
            return datetime.combine(current_date, hours.open_time, tzinfo=tz)
        
        # Otherwise next trading day
        return self._next_trading_day_open(exchange, current_date)
    
    def _get_next_close(
        self,
        exchange: str,
        local_time: datetime,
        hours: MarketHours,
        close_time: time,
    ) -> Optional[datetime]:
        """Get next market close time."""
        tz = hours.get_tz()
        current_date = local_time.date()
        current_time = local_time.time()
        
        # If before today's close
        if current_time < close_time:
            return datetime.combine(current_date, close_time, tzinfo=tz)
        
        # Otherwise next trading day close
        next_open = self._next_trading_day_open(exchange, current_date)
        next_date = next_open.date()
        next_close_time = hours.early_close_time if self._is_early_close(exchange, next_date) else hours.close_time
        
        return datetime.combine(next_date, next_close_time, tzinfo=tz)
    
    def is_trading_day(self, exchange: str, check_date: date) -> bool:
        """Check if date is a trading day."""
        exchange = EXCHANGE_ALIASES.get(exchange.upper(), exchange.upper())
        hours = self.get_exchange_hours(exchange)
        
        # Check weekend
        if check_date.weekday() in hours.weekend_days:
            return False
        
        # Check holiday
        if self._is_holiday(exchange, check_date):
            return False
        
        return True
    
    def is_market_open(
        self,
        exchange: str,
        at_time: Optional[datetime] = None,
        include_extended: bool = False,
    ) -> bool:
        """
        Check if market is currently open.
        
        Args:
            exchange: Exchange code
            at_time: Time to check
            include_extended: Include pre-market and after-hours
            
        Returns:
            True if market is open
        """
        status = self.get_market_status(exchange, at_time)
        
        if include_extended:
            return status.session in [
                MarketSession.REGULAR,
                MarketSession.PRE_MARKET,
                MarketSession.AFTER_HOURS,
            ]
        
        return status.session == MarketSession.REGULAR
    
    def get_trading_days(
        self,
        exchange: str,
        start_date: date,
        end_date: date,
    ) -> list[date]:
        """Get list of trading days in date range."""
        trading_days = []
        current = start_date
        
        while current <= end_date:
            if self.is_trading_day(exchange, current):
                trading_days.append(current)
            current += timedelta(days=1)
        
        return trading_days
    
    def count_trading_days(
        self,
        exchange: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count trading days between two dates."""
        return len(self.get_trading_days(exchange, start_date, end_date))
    
    def add_holiday(self, exchange: str, holiday_date: date) -> None:
        """Add a custom holiday for an exchange."""
        if exchange not in self._custom_holidays:
            self._custom_holidays[exchange] = set()
        self._custom_holidays[exchange].add(holiday_date)
    
    def add_early_close(self, exchange: str, early_close_date: date) -> None:
        """Add a custom early close day for an exchange."""
        if exchange not in self._custom_early_close:
            self._custom_early_close[exchange] = set()
        self._custom_early_close[exchange].add(early_close_date)
    
    def get_all_exchange_status(
        self,
        at_time: Optional[datetime] = None,
    ) -> dict[str, MarketStatus]:
        """Get status for all configured exchanges."""
        statuses = {}
        
        for exchange in EXCHANGE_HOURS.keys():
            try:
                statuses[exchange] = self.get_market_status(exchange, at_time)
            except Exception as e:
                logger.error(f"Failed to get status for {exchange}: {e}")
        
        return statuses
    
    def get_open_markets(
        self,
        at_time: Optional[datetime] = None,
    ) -> list[str]:
        """Get list of currently open markets."""
        open_markets = []
        
        for exchange in EXCHANGE_HOURS.keys():
            if self.is_market_open(exchange, at_time):
                open_markets.append(exchange)
        
        return open_markets
    
    def next_market_event(
        self,
        exchange: str,
        at_time: Optional[datetime] = None,
    ) -> tuple[str, datetime]:
        """
        Get the next market event (open or close).
        
        Returns:
            Tuple of (event_type, event_time) where event_type is 'open' or 'close'
        """
        status = self.get_market_status(exchange, at_time)
        
        if status.is_open and status.next_close:
            return ("close", status.next_close)
        elif status.next_open:
            return ("open", status.next_open)
        
        return ("unknown", datetime.now())
    
    def time_until_market_open(
        self,
        exchange: str,
        at_time: Optional[datetime] = None,
    ) -> Optional[timedelta]:
        """Get time remaining until market opens."""
        status = self.get_market_status(exchange, at_time)
        
        if status.is_open:
            return timedelta(0)
        
        if status.next_open:
            now = at_time or datetime.now(ZoneInfo(self.get_exchange_hours(exchange).timezone))
            return status.next_open - now
        
        return None
    
    def time_until_market_close(
        self,
        exchange: str,
        at_time: Optional[datetime] = None,
    ) -> Optional[timedelta]:
        """Get time remaining until market closes."""
        status = self.get_market_status(exchange, at_time)
        
        if not status.is_open:
            return None
        
        if status.next_close:
            now = at_time or datetime.now(ZoneInfo(self.get_exchange_hours(exchange).timezone))
            return status.next_close - now
        
        return None


# ==================== Singleton Instance ====================

_manager_instance: Optional[MarketHoursManager] = None


def get_market_hours_manager() -> MarketHoursManager:
    """Get singleton MarketHoursManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MarketHoursManager()
    return _manager_instance


# ==================== Convenience Functions ====================

def is_us_market_open(at_time: Optional[datetime] = None) -> bool:
    """Check if US markets are open."""
    manager = get_market_hours_manager()
    return manager.is_market_open("NYSE", at_time)


def is_eu_market_open(at_time: Optional[datetime] = None) -> bool:
    """Check if European markets are open (any of the major ones)."""
    manager = get_market_hours_manager()
    return any([
        manager.is_market_open("LSE", at_time),
        manager.is_market_open("XETRA", at_time),
        manager.is_market_open("EURONEXT", at_time),
    ])


def is_asia_market_open(at_time: Optional[datetime] = None) -> bool:
    """Check if Asian markets are open (any of the major ones)."""
    manager = get_market_hours_manager()
    return any([
        manager.is_market_open("TSE", at_time),
        manager.is_market_open("HKEX", at_time),
        manager.is_market_open("SSE", at_time),
    ])


def get_market_session(exchange: str) -> MarketSession:
    """Get current session for an exchange."""
    manager = get_market_hours_manager()
    status = manager.get_market_status(exchange)
    return status.session
