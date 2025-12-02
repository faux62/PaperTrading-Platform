"""
ML Features Package

Provides feature calculation and storage for ML models:
- Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Fundamental ratios (P/E, ROE, debt ratios, etc.)
- Market features (correlations, sector strength, etc.)
"""

from app.ml.features.technical_features import (
    TechnicalFeatures,
    TechnicalFeaturesCalculator,
    calculate_technical_features,
)

from app.ml.features.fundamental_features import (
    FundamentalFeatures,
    FundamentalFeaturesCalculator,
    FinancialStatements,
    calculate_fundamental_features,
)

from app.ml.features.market_features import (
    MarketFeatures,
    MarketFeaturesCalculator,
    calculate_market_features,
    SECTOR_MAPPING,
    SECTOR_ETF_MAPPING,
)

from app.ml.features.feature_store import (
    FeatureStore,
    FeatureRecord,
    CombinedFeatures,
    InMemoryFeatureCache,
    get_feature_store,
)

from app.ml.features.pipeline import (
    FeaturePipeline,
    FeatureType,
    PipelineConfig,
    PipelineResult,
    FeatureQuality,
    get_feature_pipeline,
)

__all__ = [
    # Technical
    'TechnicalFeatures',
    'TechnicalFeaturesCalculator',
    'calculate_technical_features',
    # Fundamental
    'FundamentalFeatures',
    'FundamentalFeaturesCalculator',
    'FinancialStatements',
    'calculate_fundamental_features',
    # Market
    'MarketFeatures',
    'MarketFeaturesCalculator',
    'calculate_market_features',
    'SECTOR_MAPPING',
    'SECTOR_ETF_MAPPING',
    # Store
    'FeatureStore',
    'FeatureRecord',
    'CombinedFeatures',
    'InMemoryFeatureCache',
    'get_feature_store',
    # Pipeline
    'FeaturePipeline',
    'FeatureType',
    'PipelineConfig',
    'PipelineResult',
    'FeatureQuality',
    'get_feature_pipeline',
]
