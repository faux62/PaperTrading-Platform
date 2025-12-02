"""
Data Normalizer

Normalizes data from different providers into a consistent format.
Handles symbol mapping, currency conversion, and data validation.
"""
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional, Any
import re
from loguru import logger

from app.data_providers.adapters.base import Quote, OHLCV, MarketType, TimeFrame


@dataclass
class SymbolMapping:
    """Mapping between provider-specific and canonical symbols."""
    canonical: str              # Our standard symbol (e.g., "AAPL")
    provider_symbol: str        # Provider's symbol format
    provider: str               # Provider name
    exchange: Optional[str] = None
    currency: str = "USD"
    market_type: MarketType = MarketType.US_STOCK


class DataNormalizer:
    """
    Normalizes market data from various providers into a consistent format.
    
    Features:
    - Symbol standardization (handles different formats)
    - Price/volume validation
    - Timestamp normalization (UTC)
    - Currency conversion support
    - Data quality checks
    """
    
    def __init__(self):
        # Symbol mappings: canonical -> {provider: provider_symbol}
        self._symbol_mappings: dict[str, dict[str, SymbolMapping]] = {}
        
        # Reverse mappings: (provider, provider_symbol) -> canonical
        self._reverse_mappings: dict[tuple[str, str], str] = {}
        
        # Exchange suffixes by provider
        self._exchange_suffixes: dict[str, dict[str, str]] = {
            "yahoo": {
                "NYSE": "",
                "NASDAQ": "",
                "LSE": ".L",
                "XETRA": ".DE",
                "EURONEXT_PARIS": ".PA",
                "BORSA_ITALIANA": ".MI",
                "TSX": ".TO",
                "ASX": ".AX",
            },
            "polygon": {
                "NYSE": "",
                "NASDAQ": "",
                "OTC": "",
            },
            "alpaca": {
                "NYSE": "",
                "NASDAQ": "",
            },
        }
        
        # Currency symbols
        self._currency_decimals: dict[str, int] = {
            "USD": 2,
            "EUR": 2,
            "GBP": 2,
            "GBX": 2,  # British pence
            "JPY": 0,
            "CHF": 2,
        }
    
    def register_mapping(self, mapping: SymbolMapping) -> None:
        """Register a symbol mapping."""
        canonical = mapping.canonical.upper()
        
        if canonical not in self._symbol_mappings:
            self._symbol_mappings[canonical] = {}
        
        self._symbol_mappings[canonical][mapping.provider] = mapping
        self._reverse_mappings[(mapping.provider, mapping.provider_symbol)] = canonical
        
        logger.debug(
            f"Registered mapping: {canonical} -> {mapping.provider}:{mapping.provider_symbol}"
        )
    
    def get_provider_symbol(self, canonical: str, provider: str) -> str:
        """
        Get the provider-specific symbol for a canonical symbol.
        
        Args:
            canonical: Canonical symbol (e.g., "AAPL")
            provider: Provider name
            
        Returns:
            Provider-specific symbol
        """
        canonical = canonical.upper()
        
        # Check for explicit mapping
        if canonical in self._symbol_mappings:
            if provider in self._symbol_mappings[canonical]:
                return self._symbol_mappings[canonical][provider].provider_symbol
        
        # Default: return as-is (works for US stocks on most providers)
        return canonical
    
    def get_canonical_symbol(self, provider_symbol: str, provider: str) -> str:
        """
        Get the canonical symbol from a provider-specific symbol.
        
        Args:
            provider_symbol: Provider's symbol format
            provider: Provider name
            
        Returns:
            Canonical symbol
        """
        key = (provider, provider_symbol)
        
        if key in self._reverse_mappings:
            return self._reverse_mappings[key]
        
        # Default: clean up and return
        return self._clean_symbol(provider_symbol)
    
    def _clean_symbol(self, symbol: str) -> str:
        """Clean up a symbol to canonical format."""
        # Remove common suffixes
        symbol = re.sub(r'\.(L|DE|PA|MI|TO|AX|HK|SS|SZ)$', '', symbol.upper())
        # Remove spaces and special characters
        symbol = re.sub(r'[^A-Z0-9.]', '', symbol)
        return symbol
    
    def normalize_quote(
        self,
        raw_data: dict[str, Any],
        provider: str,
        market_type: MarketType = MarketType.US_STOCK,
    ) -> Quote:
        """
        Normalize raw quote data from a provider.
        
        Args:
            raw_data: Raw data dictionary from provider
            provider: Provider name
            market_type: Market type
            
        Returns:
            Normalized Quote object
        """
        # Extract and normalize symbol
        raw_symbol = self._extract_field(raw_data, ["symbol", "ticker", "s", "sym"])
        symbol = self.get_canonical_symbol(str(raw_symbol), provider)
        
        # Extract price (required)
        price = self._extract_decimal(
            raw_data, 
            ["price", "last", "lastPrice", "c", "close", "regularMarketPrice"]
        )
        
        if price is None:
            raise ValueError(f"No price found in data for {symbol}")
        
        # Extract optional fields
        bid = self._extract_decimal(raw_data, ["bid", "bidPrice", "b"])
        ask = self._extract_decimal(raw_data, ["ask", "askPrice", "a"])
        bid_size = self._extract_int(raw_data, ["bidSize", "bs", "bidQty"])
        ask_size = self._extract_int(raw_data, ["askSize", "as", "askQty"])
        volume = self._extract_int(raw_data, ["volume", "v", "vol", "totalVolume"])
        
        # Change metrics
        change = self._extract_decimal(raw_data, ["change", "ch", "netChange"])
        change_pct = self._extract_decimal(
            raw_data, 
            ["changePercent", "changePct", "cp", "percentChange", "regularMarketChangePercent"]
        )
        
        # Day range
        day_high = self._extract_decimal(raw_data, ["high", "h", "dayHigh", "regularMarketDayHigh"])
        day_low = self._extract_decimal(raw_data, ["low", "l", "dayLow", "regularMarketDayLow"])
        day_open = self._extract_decimal(raw_data, ["open", "o", "dayOpen", "regularMarketOpen"])
        prev_close = self._extract_decimal(
            raw_data, 
            ["previousClose", "prevClose", "pc", "regularMarketPreviousClose"]
        )
        
        # Timestamp
        timestamp = self._extract_timestamp(
            raw_data, 
            ["timestamp", "time", "t", "datetime", "date", "updated"]
        )
        
        # Exchange and currency
        exchange = self._extract_field(raw_data, ["exchange", "exch", "primaryExchange"])
        currency = self._extract_field(raw_data, ["currency", "curr"]) or "USD"
        
        # Calculate change if not provided
        if change is None and prev_close is not None and price is not None:
            change = price - prev_close
        
        if change_pct is None and change is not None and prev_close is not None and prev_close != 0:
            change_pct = (change / prev_close) * 100
        
        return Quote(
            symbol=symbol,
            price=price,
            bid=bid,
            ask=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            volume=volume,
            timestamp=timestamp,
            provider=provider,
            market_type=market_type,
            change=change,
            change_percent=change_pct,
            day_high=day_high,
            day_low=day_low,
            day_open=day_open,
            prev_close=prev_close,
            exchange=str(exchange) if exchange else None,
            currency=str(currency).upper(),
        )
    
    def normalize_ohlcv(
        self,
        raw_data: dict[str, Any],
        provider: str,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> OHLCV:
        """
        Normalize raw OHLCV (candlestick) data from a provider.
        
        Args:
            raw_data: Raw data dictionary from provider
            provider: Provider name
            symbol: Symbol (already canonical)
            timeframe: Data timeframe
            
        Returns:
            Normalized OHLCV object
        """
        # Extract OHLCV values (all required)
        open_price = self._extract_decimal(raw_data, ["open", "o"])
        high = self._extract_decimal(raw_data, ["high", "h"])
        low = self._extract_decimal(raw_data, ["low", "l"])
        close = self._extract_decimal(raw_data, ["close", "c"])
        volume = self._extract_int(raw_data, ["volume", "v", "vol"])
        
        if any(v is None for v in [open_price, high, low, close]):
            raise ValueError(f"Missing OHLC values in data for {symbol}")
        
        # Timestamp
        timestamp = self._extract_timestamp(
            raw_data,
            ["timestamp", "time", "t", "datetime", "date", "d"]
        )
        
        # Optional fields
        adjusted_close = self._extract_decimal(
            raw_data, 
            ["adjustedClose", "adjClose", "ac", "adjusted"]
        )
        vwap = self._extract_decimal(raw_data, ["vwap", "vw"])
        trade_count = self._extract_int(raw_data, ["trades", "n", "tradeCount", "numberOfTrades"])
        
        return OHLCV(
            symbol=symbol,
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume or 0,
            provider=provider,
            timeframe=timeframe,
            adjusted_close=adjusted_close,
            vwap=vwap,
            trade_count=trade_count,
        )
    
    def normalize_ohlcv_list(
        self,
        raw_data_list: list[dict[str, Any]],
        provider: str,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.DAY,
    ) -> list[OHLCV]:
        """Normalize a list of OHLCV data points."""
        results = []
        for raw_data in raw_data_list:
            try:
                ohlcv = self.normalize_ohlcv(raw_data, provider, symbol, timeframe)
                results.append(ohlcv)
            except ValueError as e:
                logger.warning(f"Skipping invalid OHLCV data: {e}")
        
        # Sort by timestamp
        results.sort(key=lambda x: x.timestamp)
        return results
    
    def _extract_field(
        self, 
        data: dict[str, Any], 
        keys: list[str]
    ) -> Optional[Any]:
        """Extract a field trying multiple possible keys."""
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
            # Try lowercase
            if key.lower() in data and data[key.lower()] is not None:
                return data[key.lower()]
        return None
    
    def _extract_decimal(
        self, 
        data: dict[str, Any], 
        keys: list[str]
    ) -> Optional[Decimal]:
        """Extract and convert a numeric field to Decimal."""
        value = self._extract_field(data, keys)
        if value is None:
            return None
        
        try:
            if isinstance(value, Decimal):
                return value
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            if isinstance(value, str):
                # Remove currency symbols and commas
                clean = re.sub(r'[,$€£¥%]', '', value.strip())
                return Decimal(clean)
        except (InvalidOperation, ValueError):
            return None
        
        return None
    
    def _extract_int(
        self, 
        data: dict[str, Any], 
        keys: list[str]
    ) -> Optional[int]:
        """Extract and convert a numeric field to int."""
        value = self._extract_field(data, keys)
        if value is None:
            return None
        
        try:
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                # Handle K, M, B suffixes
                value = value.strip().upper()
                multiplier = 1
                if value.endswith('K'):
                    multiplier = 1000
                    value = value[:-1]
                elif value.endswith('M'):
                    multiplier = 1000000
                    value = value[:-1]
                elif value.endswith('B'):
                    multiplier = 1000000000
                    value = value[:-1]
                return int(float(value.replace(',', '')) * multiplier)
        except (ValueError, TypeError):
            return None
        
        return None
    
    def _extract_timestamp(
        self, 
        data: dict[str, Any], 
        keys: list[str]
    ) -> datetime:
        """Extract and normalize a timestamp to UTC datetime."""
        value = self._extract_field(data, keys)
        
        if value is None:
            return datetime.now(timezone.utc)
        
        # Already a datetime
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        
        # Unix timestamp (seconds or milliseconds)
        if isinstance(value, (int, float)):
            # Detect milliseconds (> year 2100 in seconds)
            if value > 4102444800:
                value = value / 1000
            return datetime.fromtimestamp(value, tz=timezone.utc)
        
        # String parsing
        if isinstance(value, str):
            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y%m%d",
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
        
        # Fallback
        logger.warning(f"Could not parse timestamp: {value}")
        return datetime.now(timezone.utc)
    
    def validate_quote(self, quote: Quote) -> list[str]:
        """
        Validate a quote for data quality issues.
        
        Returns:
            List of warning messages (empty if valid)
        """
        warnings = []
        
        # Check for zero or negative price
        if quote.price <= 0:
            warnings.append(f"Invalid price: {quote.price}")
        
        # Check bid/ask spread
        if quote.bid and quote.ask:
            if quote.bid > quote.ask:
                warnings.append(f"Inverted spread: bid {quote.bid} > ask {quote.ask}")
            spread_pct = (quote.ask - quote.bid) / quote.price * 100
            if spread_pct > 10:
                warnings.append(f"Wide spread: {spread_pct:.1f}%")
        
        # Check day range consistency
        if quote.day_high and quote.day_low:
            if quote.day_low > quote.day_high:
                warnings.append("Invalid day range: low > high")
            if quote.price > quote.day_high or quote.price < quote.day_low:
                warnings.append("Price outside day range")
        
        # Check for stale data
        age_seconds = (datetime.now(timezone.utc) - quote.timestamp.replace(tzinfo=timezone.utc)).total_seconds()
        if age_seconds > 300:  # 5 minutes
            warnings.append(f"Stale data: {age_seconds/60:.1f} minutes old")
        
        return warnings
    
    def validate_ohlcv(self, ohlcv: OHLCV) -> list[str]:
        """
        Validate OHLCV data for quality issues.
        
        Returns:
            List of warning messages (empty if valid)
        """
        warnings = []
        
        # Check OHLC consistency
        if ohlcv.low > ohlcv.high:
            warnings.append("Invalid range: low > high")
        
        if ohlcv.open > ohlcv.high or ohlcv.open < ohlcv.low:
            warnings.append("Open outside high/low range")
        
        if ohlcv.close > ohlcv.high or ohlcv.close < ohlcv.low:
            warnings.append("Close outside high/low range")
        
        # Check for zero values
        if any(v <= 0 for v in [ohlcv.open, ohlcv.high, ohlcv.low, ohlcv.close]):
            warnings.append("Zero or negative OHLC values")
        
        # Check for extreme moves
        range_pct = (ohlcv.high - ohlcv.low) / ohlcv.low * 100
        if range_pct > 50:
            warnings.append(f"Extreme range: {range_pct:.1f}%")
        
        return warnings


# Global normalizer instance
data_normalizer = DataNormalizer()
