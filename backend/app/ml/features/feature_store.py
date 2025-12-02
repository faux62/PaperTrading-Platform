"""
Feature Store

Manages storage and retrieval of ML features:
- In-memory caching for real-time access
- Database persistence for historical features
- Feature versioning and metadata
"""
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json
from loguru import logger

from app.ml.features.technical_features import TechnicalFeatures, TechnicalFeaturesCalculator
from app.ml.features.fundamental_features import FundamentalFeatures, FundamentalFeaturesCalculator
from app.ml.features.market_features import MarketFeatures, MarketFeaturesCalculator


@dataclass
class FeatureRecord:
    """Single feature record with metadata."""
    symbol: str
    timestamp: str
    feature_type: str  # 'technical', 'fundamental', 'market'
    features: Dict[str, Any]
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp,
            'feature_type': self.feature_type,
            'features': self.features,
            'version': self.version,
            'created_at': self.created_at,
        }


@dataclass
class CombinedFeatures:
    """Combined features from all sources for a single symbol."""
    symbol: str
    timestamp: str
    
    technical: Optional[TechnicalFeatures] = None
    fundamental: Optional[FundamentalFeatures] = None
    market: Optional[MarketFeatures] = None
    
    def to_dict(self) -> dict:
        result = {
            'symbol': self.symbol,
            'timestamp': self.timestamp,
        }
        if self.technical:
            result['technical'] = self.technical.to_dict()
        if self.fundamental:
            result['fundamental'] = self.fundamental.to_dict()
        if self.market:
            result['market'] = self.market.to_dict()
        return result
    
    def to_feature_vector(self) -> list[float]:
        """Combine all features into single vector for ML."""
        vector = []
        if self.technical:
            vector.extend(self.technical.to_feature_vector())
        if self.fundamental:
            vector.extend(self.fundamental.to_feature_vector())
        if self.market:
            vector.extend(self.market.to_feature_vector())
        return vector
    
    @staticmethod
    def get_feature_names() -> list[str]:
        """Get all feature names in order."""
        names = []
        names.extend([f"tech_{n}" for n in TechnicalFeaturesCalculator.get_feature_names()])
        names.extend([f"fund_{n}" for n in FundamentalFeaturesCalculator.get_feature_names()])
        names.extend([f"mkt_{n}" for n in MarketFeaturesCalculator.get_feature_names()])
        return names


class InMemoryFeatureCache:
    """
    In-memory cache for real-time feature access.
    
    Provides fast access to recent features with TTL-based expiration.
    """
    
    def __init__(self, ttl_minutes: int = 60, max_symbols: int = 1000):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_symbols = max_symbols
        
        # Cache structure: {symbol: {feature_type: FeatureRecord}}
        self._cache: Dict[str, Dict[str, FeatureRecord]] = defaultdict(dict)
        self._timestamps: Dict[str, datetime] = {}
    
    def get(
        self, 
        symbol: str, 
        feature_type: Optional[str] = None
    ) -> Optional[Union[FeatureRecord, Dict[str, FeatureRecord]]]:
        """
        Get cached features for a symbol.
        
        Args:
            symbol: Stock symbol
            feature_type: Specific type ('technical', 'fundamental', 'market')
                         or None for all types
        
        Returns:
            FeatureRecord or dict of records, None if not cached/expired
        """
        if symbol not in self._cache:
            return None
        
        # Check expiration
        if symbol in self._timestamps:
            if datetime.utcnow() - self._timestamps[symbol] > self.ttl:
                self._evict(symbol)
                return None
        
        if feature_type:
            return self._cache[symbol].get(feature_type)
        
        return dict(self._cache[symbol])
    
    def set(
        self,
        symbol: str,
        feature_type: str,
        record: FeatureRecord
    ) -> None:
        """
        Cache features for a symbol.
        
        Args:
            symbol: Stock symbol
            feature_type: Type of features
            record: Feature record to cache
        """
        # Evict if at capacity
        if len(self._cache) >= self.max_symbols and symbol not in self._cache:
            self._evict_oldest()
        
        self._cache[symbol][feature_type] = record
        self._timestamps[symbol] = datetime.utcnow()
    
    def invalidate(self, symbol: str, feature_type: Optional[str] = None) -> None:
        """Invalidate cache for a symbol."""
        if symbol in self._cache:
            if feature_type:
                self._cache[symbol].pop(feature_type, None)
            else:
                self._evict(symbol)
    
    def _evict(self, symbol: str) -> None:
        """Evict symbol from cache."""
        self._cache.pop(symbol, None)
        self._timestamps.pop(symbol, None)
    
    def _evict_oldest(self) -> None:
        """Evict oldest symbol from cache."""
        if not self._timestamps:
            return
        
        oldest = min(self._timestamps, key=self._timestamps.get)
        self._evict(oldest)
    
    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._timestamps.clear()
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            'symbols_cached': len(self._cache),
            'max_symbols': self.max_symbols,
            'ttl_minutes': self.ttl.total_seconds() / 60,
        }


class FeatureStore:
    """
    Central feature store for ML pipeline.
    
    Manages:
    - Feature calculation and caching
    - Historical feature storage
    - Feature retrieval for training and inference
    
    Usage:
        store = FeatureStore()
        
        # Store calculated features
        store.store_features(
            symbol="AAPL",
            technical=technical_features,
            fundamental=fundamental_features,
            market=market_features,
        )
        
        # Retrieve features
        features = store.get_features("AAPL")
        vector = features.to_feature_vector()
    """
    
    def __init__(
        self,
        cache_ttl_minutes: int = 60,
        max_cached_symbols: int = 1000,
    ):
        self.cache = InMemoryFeatureCache(
            ttl_minutes=cache_ttl_minutes,
            max_symbols=max_cached_symbols,
        )
        
        # Historical storage (in-memory for now, can be replaced with DB)
        self._history: Dict[str, List[FeatureRecord]] = defaultdict(list)
        self._max_history_per_symbol = 252  # ~1 year of daily features
    
    def store_features(
        self,
        symbol: str,
        timestamp: Optional[str] = None,
        technical: Optional[TechnicalFeatures] = None,
        fundamental: Optional[FundamentalFeatures] = None,
        market: Optional[MarketFeatures] = None,
    ) -> CombinedFeatures:
        """
        Store features for a symbol.
        
        Args:
            symbol: Stock symbol
            timestamp: Feature timestamp (defaults to now)
            technical: Technical indicators
            fundamental: Fundamental ratios
            market: Market/sector features
        
        Returns:
            CombinedFeatures with all stored features
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        # Store each feature type
        if technical:
            record = FeatureRecord(
                symbol=symbol,
                timestamp=timestamp,
                feature_type='technical',
                features=technical.to_dict(),
            )
            self.cache.set(symbol, 'technical', record)
            self._add_to_history(symbol, record)
        
        if fundamental:
            record = FeatureRecord(
                symbol=symbol,
                timestamp=timestamp,
                feature_type='fundamental',
                features=fundamental.to_dict(),
            )
            self.cache.set(symbol, 'fundamental', record)
            self._add_to_history(symbol, record)
        
        if market:
            record = FeatureRecord(
                symbol=symbol,
                timestamp=timestamp,
                feature_type='market',
                features=market.to_dict(),
            )
            self.cache.set(symbol, 'market', record)
            self._add_to_history(symbol, record)
        
        return CombinedFeatures(
            symbol=symbol,
            timestamp=timestamp,
            technical=technical,
            fundamental=fundamental,
            market=market,
        )
    
    def get_features(
        self,
        symbol: str,
        include: Optional[List[str]] = None,
    ) -> Optional[CombinedFeatures]:
        """
        Get latest features for a symbol.
        
        Args:
            symbol: Stock symbol
            include: List of feature types to include
                    ('technical', 'fundamental', 'market')
                    None includes all available
        
        Returns:
            CombinedFeatures or None if not found
        """
        cached = self.cache.get(symbol)
        if not cached:
            return None
        
        include = include or ['technical', 'fundamental', 'market']
        
        combined = CombinedFeatures(
            symbol=symbol,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        if 'technical' in include and 'technical' in cached:
            record = cached['technical']
            combined.technical = self._record_to_technical(record)
            combined.timestamp = record.timestamp
        
        if 'fundamental' in include and 'fundamental' in cached:
            record = cached['fundamental']
            combined.fundamental = self._record_to_fundamental(record)
        
        if 'market' in include and 'market' in cached:
            record = cached['market']
            combined.market = self._record_to_market(record)
        
        return combined
    
    def get_features_batch(
        self,
        symbols: List[str],
        include: Optional[List[str]] = None,
    ) -> Dict[str, CombinedFeatures]:
        """
        Get features for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            include: Feature types to include
        
        Returns:
            Dict mapping symbols to CombinedFeatures
        """
        result = {}
        for symbol in symbols:
            features = self.get_features(symbol, include)
            if features:
                result[symbol] = features
        return result
    
    def get_feature_history(
        self,
        symbol: str,
        feature_type: str,
        days: int = 30,
    ) -> List[FeatureRecord]:
        """
        Get historical features for a symbol.
        
        Args:
            symbol: Stock symbol
            feature_type: Type of features to retrieve
            days: Number of days of history
        
        Returns:
            List of FeatureRecord sorted by timestamp
        """
        if symbol not in self._history:
            return []
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        records = [
            r for r in self._history[symbol]
            if r.feature_type == feature_type
            and datetime.fromisoformat(r.timestamp) > cutoff
        ]
        
        return sorted(records, key=lambda r: r.timestamp)
    
    def get_training_data(
        self,
        symbols: List[str],
        include: Optional[List[str]] = None,
    ) -> tuple[list[list[float]], list[str]]:
        """
        Get feature vectors for model training.
        
        Args:
            symbols: List of stock symbols
            include: Feature types to include
        
        Returns:
            Tuple of (feature_vectors, symbol_list)
        """
        vectors = []
        valid_symbols = []
        
        for symbol in symbols:
            features = self.get_features(symbol, include)
            if features:
                vector = features.to_feature_vector()
                if vector:  # Not empty
                    vectors.append(vector)
                    valid_symbols.append(symbol)
        
        return vectors, valid_symbols
    
    def _add_to_history(self, symbol: str, record: FeatureRecord) -> None:
        """Add record to history, maintaining max size."""
        self._history[symbol].append(record)
        
        # Trim if needed
        if len(self._history[symbol]) > self._max_history_per_symbol:
            # Sort by timestamp and keep recent
            self._history[symbol] = sorted(
                self._history[symbol],
                key=lambda r: r.timestamp
            )[-self._max_history_per_symbol:]
    
    def _record_to_technical(self, record: FeatureRecord) -> TechnicalFeatures:
        """Convert record back to TechnicalFeatures."""
        features = record.features
        return TechnicalFeatures(
            symbol=features.get('symbol', record.symbol),
            timestamp=features.get('timestamp', record.timestamp),
            **{k: v for k, v in features.items() 
               if k not in ('symbol', 'timestamp')}
        )
    
    def _record_to_fundamental(self, record: FeatureRecord) -> FundamentalFeatures:
        """Convert record back to FundamentalFeatures."""
        features = record.features
        return FundamentalFeatures(
            symbol=features.get('symbol', record.symbol),
            timestamp=features.get('timestamp', record.timestamp),
            **{k: v for k, v in features.items() 
               if k not in ('symbol', 'timestamp')}
        )
    
    def _record_to_market(self, record: FeatureRecord) -> MarketFeatures:
        """Convert record back to MarketFeatures."""
        features = record.features
        return MarketFeatures(
            symbol=features.get('symbol', record.symbol),
            timestamp=features.get('timestamp', record.timestamp),
            **{k: v for k, v in features.items() 
               if k not in ('symbol', 'timestamp')}
        )
    
    def invalidate(self, symbol: str) -> None:
        """Invalidate all cached features for a symbol."""
        self.cache.invalidate(symbol)
    
    def clear_cache(self) -> None:
        """Clear the feature cache."""
        self.cache.clear()
    
    def clear_history(self, symbol: Optional[str] = None) -> None:
        """Clear historical features."""
        if symbol:
            self._history.pop(symbol, None)
        else:
            self._history.clear()
    
    def stats(self) -> dict:
        """Get store statistics."""
        return {
            'cache': self.cache.stats(),
            'history': {
                'symbols': len(self._history),
                'total_records': sum(len(v) for v in self._history.values()),
            },
        }
    
    @staticmethod
    def get_all_feature_names() -> list[str]:
        """Get all available feature names."""
        return CombinedFeatures.get_feature_names()


# Global feature store instance
feature_store = FeatureStore()


def get_feature_store() -> FeatureStore:
    """Get the global feature store instance."""
    return feature_store
