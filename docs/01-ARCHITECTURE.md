# 📐 PaperTrading Platform - Architettura del Sistema

## 1. Overview del Sistema

### 1.1 Vision
Piattaforma di paper trading multi-mercato con architettura multi-provider ottimizzata per l'acquisizione dati, gestione intelligente dei rate limits, supporto ML per analisi predittive, e frontend completo per gestione portafogli.

### 1.2 Caratteristiche Principali
- **800 simboli** distribuiti su mercati globali (US, EU, Asia-Pacific)
- **15 provider** di dati con failover automatico
- **3 profili portafoglio**: Aggressivo, Bilanciato, Prudente
- **Machine Learning** per predizioni e ottimizzazione
- **Real-time** ogni 5 minuti per mercati aperti
- **Budget 75%** dei rate limits giornalieri

---

## 2. Architettura High-Level

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React/TypeScript)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  Dashboard  │ │  Portfolio  │ │   Market    │ │     ML      │ │  Settings │ │
│  │   Module    │ │   Manager   │ │   Viewer    │ │  Insights   │ │   Panel   │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬─────┘ │
│         │               │               │               │               │       │
│         └───────────────┴───────────────┴───────────────┴───────────────┘       │
│                                         │                                        │
│                              WebSocket + REST API                                │
└─────────────────────────────────────────┼────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────┼────────────────────────────────────────┐
│                              API GATEWAY (FastAPI)                               │
│  ┌──────────────────────────────────────┴──────────────────────────────────────┐│
│  │                           Authentication & Rate Limiting                     ││
│  └──────────────────────────────────────────────────────────────────────────────┘│
│                                         │                                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  Portfolio  │ │   Market    │ │    Trade    │ │     ML      │ │   Admin   │ │
│  │   Routes    │ │   Routes    │ │   Routes    │ │   Routes    │ │   Routes  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────┼────────────────────────────────────────┐
│                              CORE SERVICES LAYER                                 │
│                                         │                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │  PORTFOLIO       │  │  TRADING         │  │  ANALYTICS       │              │
│  │  SERVICE         │  │  ENGINE          │  │  SERVICE         │              │
│  │                  │  │                  │  │                  │              │
│  │ • Portfolio CRUD │  │ • Order Manager  │  │ • Performance    │              │
│  │ • Risk Profiles  │  │ • Position Track │  │ • Risk Metrics   │              │
│  │ • Rebalancing    │  │ • P&L Calculator │  │ • Benchmarking   │              │
│  │ • Allocation     │  │ • Trade History  │  │ • Reporting      │              │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘              │
│           │                     │                     │                         │
│  ┌────────┴─────────────────────┴─────────────────────┴─────────┐              │
│  │                      EVENT BUS (Redis Pub/Sub)               │              │
│  └──────────────────────────────┬───────────────────────────────┘              │
│                                 │                                               │
│  ┌──────────────────┐  ┌───────┴──────────┐  ┌──────────────────┐              │
│  │  ML SERVICE      │  │  MARKET DATA     │  │  SCHEDULER       │              │
│  │                  │  │  AGGREGATOR      │  │  SERVICE         │              │
│  │ • Price Predict  │  │                  │  │                  │              │
│  │ • Risk Analysis  │  │ • Data Normalize │  │ • Cron Jobs      │              │
│  │ • Optimization   │  │ • Cache Manager  │  │ • Market Hours   │              │
│  │ • Signals Gen    │  │ • Gap Detection  │  │ • Rate Budgets   │              │
│  └──────────────────┘  └────────┬─────────┘  └──────────────────┘              │
└─────────────────────────────────┼────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────────────────────┐
│                      DATA ACQUISITION LAYER                                      │
│                                 │                                                │
│  ┌──────────────────────────────┴───────────────────────────────────────────┐   │
│  │                    PROVIDER ORCHESTRATOR                                  │   │
│  │  • Provider Health Monitor    • Failover Manager                         │   │
│  │  • Rate Limit Tracker         • Request Queue                            │   │
│  │  • Budget Allocator           • Response Validator                       │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                 │                                                │
│  ┌──────────────────────────────┼───────────────────────────────────────────┐   │
│  │                      PROVIDER ADAPTERS                                    │   │
│  │                                                                           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │   │
│  │  │ Alpaca  │ │ Polygon │ │ Finnhub │ │ Twelve  │ │yfinance │            │   │
│  │  │Adapter  │ │ Adapter │ │ Adapter │ │  Data   │ │ Adapter │            │   │
│  │  │   WS    │ │  REST   │ │REST+WS  │ │  REST   │ │ Scraper │            │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │   │
│  │                                                                           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │   │
│  │  │ EODHD   │ │  Stooq  │ │   FMP   │ │ Alpha   │ │ Nasdaq  │            │   │
│  │  │ Adapter │ │ Adapter │ │ Adapter │ │ Vantage │ │DataLink │            │   │
│  │  │Bulk+REST│ │CSV Bulk │ │  REST   │ │  REST   │ │  REST   │            │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │   │
│  │                                                                           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │   │
│  │  │ Tiingo  │ │ Market  │ │Investing│ │ Stock   │ │Intrinio │            │   │
│  │  │ Adapter │ │  Stack  │ │   .com  │ │Data.org │ │ Adapter │            │   │
│  │  │REST+WS  │ │  REST   │ │ Scraper │ │  REST   │ │  REST   │            │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘            │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────────────────────┐
│                          DATA STORAGE LAYER                                      │
│                                 │                                                │
│  ┌──────────────┐  ┌───────────┴────────────┐  ┌──────────────┐                │
│  │   PostgreSQL │  │        Redis           │  │  TimescaleDB │                │
│  │              │  │                        │  │              │                │
│  │ • Users      │  │ • Real-time Quotes     │  │ • OHLCV Data │                │
│  │ • Portfolios │  │ • Rate Limit Counters  │  │ • Indicators │                │
│  │ • Trades     │  │ • Session Cache        │  │ • ML Features│                │
│  │ • Positions  │  │ • Provider Health      │  │ • Tick Data  │                │
│  │ • Settings   │  │ • Event Pub/Sub        │  │ • Historical │                │
│  └──────────────┘  └────────────────────────┘  └──────────────┘                │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Struttura del Codice

```
papertrading-platform/
│
├── 📁 backend/                          # Backend Python/FastAPI
│   ├── 📁 app/
│   │   ├── 📄 __init__.py
│   │   ├── 📄 main.py                   # FastAPI application entry point
│   │   ├── 📄 config.py                 # Configuration management
│   │   ├── 📄 dependencies.py           # Dependency injection
│   │   │
│   │   ├── 📁 api/                      # API Routes
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📁 v1/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 router.py         # Main API router
│   │   │   │   ├── 📁 endpoints/
│   │   │   │   │   ├── 📄 auth.py
│   │   │   │   │   ├── 📄 portfolios.py
│   │   │   │   │   ├── 📄 positions.py
│   │   │   │   │   ├── 📄 trades.py
│   │   │   │   │   ├── 📄 market_data.py
│   │   │   │   │   ├── 📄 watchlists.py
│   │   │   │   │   ├── 📄 analytics.py
│   │   │   │   │   ├── 📄 ml_predictions.py
│   │   │   │   │   ├── 📄 settings.py
│   │   │   │   │   └── 📄 admin.py
│   │   │   │   └── 📁 websockets/
│   │   │   │       ├── 📄 market_stream.py
│   │   │   │       └── 📄 portfolio_updates.py
│   │   │
│   │   ├── 📁 core/                     # Core Business Logic
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📁 portfolio/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 service.py        # Portfolio CRUD operations
│   │   │   │   ├── 📄 risk_profiles.py  # Aggressive/Balanced/Prudent
│   │   │   │   ├── 📄 allocation.py     # Asset allocation logic
│   │   │   │   ├── 📄 rebalancing.py    # Auto-rebalancing engine
│   │   │   │   └── 📄 constraints.py    # Investment constraints
│   │   │   │
│   │   │   ├── 📁 trading/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 engine.py         # Paper trading engine
│   │   │   │   ├── 📄 order_manager.py  # Order processing
│   │   │   │   ├── 📄 position_tracker.py
│   │   │   │   ├── 📄 pnl_calculator.py # P&L calculations
│   │   │   │   └── 📄 execution.py      # Simulated execution
│   │   │   │
│   │   │   ├── 📁 analytics/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 performance.py    # Performance metrics
│   │   │   │   ├── 📄 risk_metrics.py   # VaR, Sharpe, etc.
│   │   │   │   ├── 📄 benchmarking.py   # Benchmark comparison
│   │   │   │   └── 📄 reporting.py      # Report generation
│   │   │   │
│   │   │   └── 📁 indicators/
│   │   │       ├── 📄 __init__.py
│   │   │       ├── 📄 technical.py      # Technical indicators
│   │   │       ├── 📄 fundamental.py    # Fundamental ratios
│   │   │       └── 📄 sentiment.py      # Sentiment indicators
│   │   │
│   │   ├── 📁 data_providers/           # Multi-Provider Data Layer
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 orchestrator.py       # Provider orchestration
│   │   │   ├── 📄 rate_limiter.py       # Rate limit management
│   │   │   ├── 📄 health_monitor.py     # Provider health checks
│   │   │   ├── 📄 failover.py           # Failover logic
│   │   │   ├── 📄 budget_tracker.py     # Daily budget tracking
│   │   │   │
│   │   │   ├── 📁 adapters/             # Provider-specific adapters
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 base.py           # Base adapter interface
│   │   │   │   ├── 📄 alpaca.py         # Alpaca Markets (WebSocket)
│   │   │   │   ├── 📄 polygon.py        # Polygon.io
│   │   │   │   ├── 📄 finnhub.py        # Finnhub
│   │   │   │   ├── 📄 twelve_data.py    # Twelve Data
│   │   │   │   ├── 📄 yfinance.py       # Yahoo Finance
│   │   │   │   ├── 📄 eodhd.py          # EOD Historical Data
│   │   │   │   ├── 📄 stooq.py          # Stooq (CSV bulk)
│   │   │   │   ├── 📄 fmp.py            # Financial Modeling Prep
│   │   │   │   ├── 📄 alpha_vantage.py  # Alpha Vantage
│   │   │   │   ├── 📄 nasdaq_datalink.py
│   │   │   │   ├── 📄 tiingo.py
│   │   │   │   ├── 📄 marketstack.py
│   │   │   │   ├── 📄 investing.py      # Investing.com (scraper)
│   │   │   │   ├── 📄 stockdata.py
│   │   │   │   └── 📄 intrinio.py
│   │   │   │
│   │   │   ├── 📁 routing/              # Market-Provider routing
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 market_router.py  # Route by market
│   │   │   │   ├── 📄 us_markets.py     # NYSE, NASDAQ routing
│   │   │   │   ├── 📄 eu_markets.py     # LSE, Xetra, etc.
│   │   │   │   └── 📄 asia_markets.py   # Tokyo, HK, etc.
│   │   │   │
│   │   │   └── 📁 aggregator/
│   │   │       ├── 📄 __init__.py
│   │   │       ├── 📄 data_normalizer.py
│   │   │       ├── 📄 cache_manager.py
│   │   │       └── 📄 gap_detector.py
│   │   │
│   │   ├── 📁 ml/                       # Machine Learning Module
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📁 models/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 price_predictor.py    # Price prediction
│   │   │   │   ├── 📄 trend_classifier.py   # Trend classification
│   │   │   │   ├── 📄 volatility_model.py   # Volatility forecasting
│   │   │   │   ├── 📄 risk_scorer.py        # Risk scoring
│   │   │   │   └── 📄 portfolio_optimizer.py # Portfolio optimization
│   │   │   │
│   │   │   ├── 📁 features/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 technical_features.py
│   │   │   │   ├── 📄 fundamental_features.py
│   │   │   │   ├── 📄 market_features.py
│   │   │   │   └── 📄 feature_store.py
│   │   │   │
│   │   │   ├── 📁 training/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 trainer.py
│   │   │   │   ├── 📄 backtester.py
│   │   │   │   └── 📄 hyperparameter.py
│   │   │   │
│   │   │   └── 📁 inference/
│   │   │       ├── 📄 __init__.py
│   │   │       ├── 📄 predictor.py
│   │   │       └── 📄 signal_generator.py
│   │   │
│   │   ├── 📁 scheduler/                # Task Scheduling
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 scheduler.py          # Main scheduler
│   │   │   ├── 📄 market_hours.py       # Market hours manager
│   │   │   ├── 📁 jobs/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 startup_job.py    # Startup data loading
│   │   │   │   ├── 📄 realtime_job.py   # Real-time updates
│   │   │   │   ├── 📄 eod_job.py        # End-of-day processing
│   │   │   │   ├── 📄 ml_job.py         # ML model updates
│   │   │   │   └── 📄 cleanup_job.py    # Data cleanup
│   │   │   └── 📄 budget_manager.py     # Rate limit budget
│   │   │
│   │   ├── 📁 db/                       # Database Layer
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 database.py           # Database connections
│   │   │   ├── 📄 redis_client.py       # Redis client
│   │   │   ├── 📁 models/               # SQLAlchemy models
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 user.py
│   │   │   │   ├── 📄 portfolio.py
│   │   │   │   ├── 📄 position.py
│   │   │   │   ├── 📄 trade.py
│   │   │   │   ├── 📄 watchlist.py
│   │   │   │   ├── 📄 market_data.py
│   │   │   │   └── 📄 ml_model.py
│   │   │   │
│   │   │   ├── 📁 repositories/         # Data access layer
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 base.py
│   │   │   │   ├── 📄 portfolio_repo.py
│   │   │   │   ├── 📄 trade_repo.py
│   │   │   │   └── 📄 market_data_repo.py
│   │   │   │
│   │   │   └── 📁 migrations/           # Alembic migrations
│   │   │       └── 📄 ...
│   │   │
│   │   ├── 📁 schemas/                  # Pydantic schemas
│   │   │   ├── 📄 __init__.py
│   │   │   ├── 📄 portfolio.py
│   │   │   ├── 📄 trade.py
│   │   │   ├── 📄 market_data.py
│   │   │   ├── 📄 analytics.py
│   │   │   └── 📄 ml.py
│   │   │
│   │   └── 📁 utils/                    # Utilities
│   │       ├── 📄 __init__.py
│   │       ├── 📄 logger.py
│   │       ├── 📄 exceptions.py
│   │       ├── 📄 validators.py
│   │       └── 📄 helpers.py
│   │
│   ├── 📁 tests/                        # Backend tests
│   │   ├── 📄 __init__.py
│   │   ├── 📄 conftest.py
│   │   ├── 📁 unit/
│   │   ├── 📁 integration/
│   │   └── 📁 e2e/
│   │
│   ├── 📄 requirements.txt
│   ├── 📄 requirements-dev.txt
│   ├── 📄 pyproject.toml
│   ├── 📄 alembic.ini
│   └── 📄 Dockerfile
│
├── 📁 frontend/                         # Frontend React/TypeScript
│   ├── 📁 src/
│   │   ├── 📄 App.tsx
│   │   ├── 📄 main.tsx
│   │   ├── 📄 vite-env.d.ts
│   │   │
│   │   ├── 📁 components/               # Reusable components
│   │   │   ├── 📁 common/
│   │   │   │   ├── 📄 Button.tsx
│   │   │   │   ├── 📄 Card.tsx
│   │   │   │   ├── 📄 Modal.tsx
│   │   │   │   ├── 📄 Table.tsx
│   │   │   │   ├── 📄 Loading.tsx
│   │   │   │   └── 📄 ErrorBoundary.tsx
│   │   │   │
│   │   │   ├── 📁 charts/
│   │   │   │   ├── 📄 CandlestickChart.tsx
│   │   │   │   ├── 📄 LineChart.tsx
│   │   │   │   ├── 📄 PieChart.tsx
│   │   │   │   ├── 📄 AreaChart.tsx
│   │   │   │   └── 📄 HeatMap.tsx
│   │   │   │
│   │   │   ├── 📁 portfolio/
│   │   │   │   ├── 📄 PortfolioCard.tsx
│   │   │   │   ├── 📄 PortfolioSummary.tsx
│   │   │   │   ├── 📄 AllocationChart.tsx
│   │   │   │   ├── 📄 PerformanceChart.tsx
│   │   │   │   └── 📄 RiskProfileSelector.tsx
│   │   │   │
│   │   │   ├── 📁 trading/
│   │   │   │   ├── 📄 OrderForm.tsx
│   │   │   │   ├── 📄 OrderBook.tsx
│   │   │   │   ├── 📄 PositionTable.tsx
│   │   │   │   ├── 📄 TradeHistory.tsx
│   │   │   │   └── 📄 QuickTrade.tsx
│   │   │   │
│   │   │   ├── 📁 market/
│   │   │   │   ├── 📄 MarketOverview.tsx
│   │   │   │   ├── 📄 StockCard.tsx
│   │   │   │   ├── 📄 Watchlist.tsx
│   │   │   │   ├── 📄 MarketHours.tsx
│   │   │   │   └── 📄 StockSearch.tsx
│   │   │   │
│   │   │   ├── 📁 analytics/
│   │   │   │   ├── 📄 PerformanceMetrics.tsx
│   │   │   │   ├── 📄 RiskAnalysis.tsx
│   │   │   │   ├── 📄 BenchmarkComparison.tsx
│   │   │   │   └── 📄 DrawdownChart.tsx
│   │   │   │
│   │   │   ├── 📁 ml/
│   │   │   │   ├── 📄 PredictionPanel.tsx
│   │   │   │   ├── 📄 SignalIndicator.tsx
│   │   │   │   ├── 📄 ModelPerformance.tsx
│   │   │   │   └── 📄 FeatureImportance.tsx
│   │   │   │
│   │   │   └── 📁 settings/
│   │   │       ├── 📄 ProviderConfig.tsx
│   │   │       ├── 📄 RateLimitMonitor.tsx
│   │   │       ├── 📄 ApiKeyManager.tsx
│   │   │       └── 📄 NotificationSettings.tsx
│   │   │
│   │   ├── 📁 pages/                    # Page components
│   │   │   ├── 📄 Dashboard.tsx
│   │   │   ├── 📄 Portfolio.tsx
│   │   │   ├── 📄 Trading.tsx
│   │   │   ├── 📄 Markets.tsx
│   │   │   ├── 📄 Analytics.tsx
│   │   │   ├── 📄 MLInsights.tsx
│   │   │   ├── 📄 Settings.tsx
│   │   │   └── 📄 Login.tsx
│   │   │
│   │   ├── 📁 hooks/                    # Custom React hooks
│   │   │   ├── 📄 usePortfolio.ts
│   │   │   ├── 📄 useMarketData.ts
│   │   │   ├── 📄 useWebSocket.ts
│   │   │   ├── 📄 useTrades.ts
│   │   │   └── 📄 useML.ts
│   │   │
│   │   ├── 📁 store/                    # State management (Zustand/Redux)
│   │   │   ├── 📄 index.ts
│   │   │   ├── 📄 portfolioStore.ts
│   │   │   ├── 📄 marketStore.ts
│   │   │   ├── 📄 tradeStore.ts
│   │   │   └── 📄 settingsStore.ts
│   │   │
│   │   ├── 📁 services/                 # API services
│   │   │   ├── 📄 api.ts                # Axios instance
│   │   │   ├── 📄 portfolioService.ts
│   │   │   ├── 📄 tradeService.ts
│   │   │   ├── 📄 marketService.ts
│   │   │   ├── 📄 analyticsService.ts
│   │   │   └── 📄 mlService.ts
│   │   │
│   │   ├── 📁 types/                    # TypeScript types
│   │   │   ├── 📄 index.ts
│   │   │   ├── 📄 portfolio.ts
│   │   │   ├── 📄 trade.ts
│   │   │   ├── 📄 market.ts
│   │   │   └── 📄 ml.ts
│   │   │
│   │   ├── 📁 utils/                    # Utilities
│   │   │   ├── 📄 formatters.ts
│   │   │   ├── 📄 validators.ts
│   │   │   ├── 📄 calculations.ts
│   │   │   └── 📄 constants.ts
│   │   │
│   │   └── 📁 styles/                   # Global styles
│   │       ├── 📄 globals.css
│   │       └── 📄 themes.ts
│   │
│   ├── 📁 public/
│   ├── 📄 package.json
│   ├── 📄 tsconfig.json
│   ├── 📄 vite.config.ts
│   ├── 📄 tailwind.config.js
│   └── 📄 Dockerfile
│
├── 📁 ml-pipeline/                      # ML Training Pipeline (separate)
│   ├── 📁 notebooks/                    # Jupyter notebooks
│   │   ├── 📄 01_data_exploration.ipynb
│   │   ├── 📄 02_feature_engineering.ipynb
│   │   ├── 📄 03_model_training.ipynb
│   │   └── 📄 04_backtesting.ipynb
│   │
│   ├── 📁 src/
│   │   ├── 📄 data_loader.py
│   │   ├── 📄 feature_pipeline.py
│   │   ├── 📄 model_trainer.py
│   │   └── 📄 model_registry.py
│   │
│   └── 📄 requirements.txt
│
├── 📁 infrastructure/                   # DevOps & Infrastructure
│   ├── 📁 docker/
│   │   ├── 📄 docker-compose.yml
│   │   ├── 📄 docker-compose.dev.yml
│   │   └── 📄 docker-compose.prod.yml
│   │
│   ├── 📁 scripts/
│   │   ├── 📄 setup.sh
│   │   ├── 📄 migrate.sh
│   │   └── 📄 seed_data.sh
│   │
│   └── 📁 config/
│       ├── 📄 nginx.conf
│       └── 📄 redis.conf
│
├── 📁 docs/                             # Documentation
│   ├── 📄 API.md
│   ├── 📄 ARCHITECTURE.md
│   ├── 📄 PROVIDERS.md
│   ├── 📄 ML_MODELS.md
│   └── 📄 DEPLOYMENT.md
│
├── 📄 .env.example
├── 📄 .gitignore
├── 📄 README.md
└── 📄 Makefile
```

---

## 4. Componenti Chiave Dettagliati

### 4.1 Provider Orchestrator

```python
# Responsabilità principali:
# - Routing intelligente delle richieste ai provider corretti
# - Gestione failover automatico
# - Tracking budget rate limits in tempo reale
# - Health monitoring di tutti i provider

class ProviderOrchestrator:
    def __init__(self):
        self.providers: Dict[str, BaseAdapter]
        self.market_routes: Dict[str, List[ProviderRoute]]
        self.rate_limiter: RateLimiter
        self.health_monitor: HealthMonitor
        self.budget_tracker: BudgetTracker
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Route symbols to appropriate providers based on market"""
        
    async def get_historical(self, symbol: str, period: str) -> DataFrame:
        """Get historical data with automatic failover"""
```

### 4.2 Risk Profiles

```python
# Configurazione dei tre profili di portafoglio

RISK_PROFILES = {
    "aggressive": {
        "equity_allocation": 0.90,
        "max_single_position": 0.15,
        "max_sector_exposure": 0.40,
        "stop_loss": 0.15,
        "take_profit": 0.30,
        "rebalance_threshold": 0.10,
        "volatility_tolerance": "high",
        "ml_signal_weight": 0.7
    },
    "balanced": {
        "equity_allocation": 0.70,
        "max_single_position": 0.10,
        "max_sector_exposure": 0.30,
        "stop_loss": 0.10,
        "take_profit": 0.20,
        "rebalance_threshold": 0.07,
        "volatility_tolerance": "medium",
        "ml_signal_weight": 0.5
    },
    "prudent": {
        "equity_allocation": 0.50,
        "max_single_position": 0.05,
        "max_sector_exposure": 0.20,
        "stop_loss": 0.05,
        "take_profit": 0.10,
        "rebalance_threshold": 0.05,
        "volatility_tolerance": "low",
        "ml_signal_weight": 0.3
    }
}
```

### 4.3 ML Models Stack

| Modello | Scopo | Algoritmo | Features Input |
|---------|-------|-----------|----------------|
| **Price Predictor** | Previsione direzione prezzo (5 giorni) | LSTM / XGBoost Ensemble | Technical indicators, Volume, Sentiment |
| **Trend Classifier** | Classificazione trend (Bull/Bear/Neutral) | Random Forest | Moving averages, Momentum, ADX |
| **Volatility Model** | Previsione volatilità | GARCH / Prophet | Historical volatility, VIX correlation |
| **Risk Scorer** | Score di rischio per simbolo | Gradient Boosting | Beta, Correlation, Drawdown history |
| **Portfolio Optimizer** | Ottimizzazione allocazione | Mean-Variance / Black-Litterman | Expected returns, Covariance matrix |

---

## 5. Flussi di Dati Principali

### 5.1 Startup Flow
```
App Start → Load Config → Initialize Providers → Health Check All
    → Download Bulk Historical (Stooq, EODHD)
    → Populate Cache (Redis)
    → Initialize ML Models
    → Start Scheduler
    → Ready
```

### 5.2 Real-Time Update Flow (ogni 5 min)
```
Scheduler Trigger → Check Market Hours → Get Active Markets
    → For each market:
        → Select Primary Provider
        → Execute Batch Request
        → If Fail: Failover to Backup
        → Normalize Data
        → Update Cache
        → Broadcast via WebSocket
        → Update Positions P&L
        → Check Alerts/Signals
```

### 5.3 Trade Execution Flow
```
User Order → Validate Order → Check Portfolio Constraints
    → Get Latest Price → Calculate Simulated Execution
    → Update Position → Update Portfolio Balance
    → Record Trade History → Emit Event
    → Update Analytics → Return Confirmation
```

---

## 6. Database Schema Overview

### PostgreSQL (Relational Data)
- `users` - User accounts
- `portfolios` - Portfolio definitions with risk profile
- `positions` - Current holdings
- `trades` - Trade history
- `watchlists` - User watchlists
- `alerts` - Price/signal alerts
- `settings` - User/system settings

### TimescaleDB (Time-Series Data)
- `ohlcv_1d` - Daily OHLCV (hypertable)
- `ohlcv_5m` - 5-minute OHLCV (hypertable)
- `indicators` - Calculated indicators
- `ml_features` - ML feature store
- `ml_predictions` - Model predictions

### Redis (Cache & Real-Time)
- `quotes:{symbol}` - Latest quotes (TTL: 5min)
- `ratelimit:{provider}:{date}` - Rate limit counters
- `health:{provider}` - Provider health status
- `session:{user_id}` - User sessions
- Channel: `market_updates` - Real-time pub/sub
