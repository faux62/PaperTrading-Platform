# 📋 PaperTrading Platform - Piano di Sviluppo e Roadmap

> **Ultimo aggiornamento:** 7 Dicembre 2025
> **Stato corrente:** FASE 2 COMPLETATA ✅ - Pronto per FASE 3

## 1. Overview del Progetto

### 1.1 Informazioni Generali
| Attributo | Valore |
|-----------|--------|
| **Nome Progetto** | PaperTrading Platform |
| **Durata Stimata** | 16-20 settimane |
| **Team Suggerito** | 1 sviluppatore full-stack (Fausto) |
| **Tech Stack** | Python/FastAPI, React/TypeScript, PostgreSQL, Redis, TimescaleDB |
| **Metodologia** | Agile/Iterativo con rilasci incrementali |

### 1.2 Obiettivi Chiave
1. ✅ Architettura multi-provider con 15 data sources
2. ✅ Gestione intelligente rate limits (budget 75%)
3. ✅ Frontend completo per trading e analytics
4. ✅ 3 profili portafoglio (Aggressivo, Bilanciato, Prudente)
5. ✅ Machine Learning per predizioni e ottimizzazione
6. ✅ Copertura 800 simboli su mercati globali

---

## 2. Piano di Sviluppo Macro (Fasi)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          TIMELINE COMPLESSIVA                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FASE 1          FASE 2          FASE 3          FASE 4          FASE 5        │
│  Foundation      Data Layer      Core Trading    ML & Analytics  Polish         │
│  ──────────      ──────────      ────────────    ──────────────  ──────         │
│  Settimane       Settimane       Settimane       Settimane       Settimane      │
│    1-3             4-7             8-11           12-15           16-18         │
│                                                                                  │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ Setup   │    │Providers│    │Portfolio│    │   ML    │    │  Test   │       │
│  │ Infra   │───▶│ Layer   │───▶│ Engine  │───▶│ Models  │───▶│ Deploy  │       │
│  │ DB/API  │    │ 15 APIs │    │ Trading │    │Analytics│    │ Optimize│       │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘       │
│                                                                                  │
│  Milestone:      Milestone:      Milestone:      Milestone:      Milestone:     │
│  Backend +       All providers   Paper trading   ML predictions  Production     │
│  DB running      integrated      functional      working         ready          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. FASE 1: Foundation (Settimane 1-3)

### 3.1 Obiettivi
- Setup infrastruttura di base
- Database schema e migrations
- API Gateway con autenticazione
- Frontend scaffold con routing
- CI/CD pipeline base

### 3.2 Dettaglio Settimana per Settimana

#### Settimana 1: Infrastructure Setup
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Setup progetto backend (FastAPI, Poetry/pip) | `backend/` struttura base |
| Lun | Setup progetto frontend (Vite, React, TypeScript) | `frontend/` struttura base |
| Mar | Docker Compose per sviluppo (PostgreSQL, Redis, TimescaleDB) | `docker-compose.dev.yml` |
| Mar | Configurazione environment variables | `.env.example`, `config.py` |
| Mer | Setup Alembic per migrations | Migrations infrastructure |
| Mer | Database schema design iniziale | Schema diagram |
| Gio | Implementazione modelli SQLAlchemy (User, Portfolio base) | `db/models/` |
| Gio | Prima migration | Database tables create |
| Ven | Setup logging e error handling | `utils/logger.py`, `utils/exceptions.py` |
| Ven | Health check endpoints | `/health`, `/ready` endpoints |

#### Settimana 2: Authentication & Base API
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | JWT Authentication system | `api/auth.py` |
| Lun | User registration/login endpoints | Auth endpoints working |
| Mar | Password hashing, token refresh | Security layer complete |
| Mar | API middleware (CORS, rate limiting interno) | Middleware stack |
| Mer | Base CRUD per User | User management API |
| Mer | Pydantic schemas iniziali | `schemas/` base |
| Gio | Setup Redis client | `db/redis_client.py` |
| Gio | Session management | Sessions in Redis |
| Ven | API documentation (OpenAPI/Swagger) | `/docs` endpoint |
| Ven | Postman collection iniziale | API testing ready |

#### Settimana 3: Frontend Foundation
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Setup Tailwind CSS + tema dark/light | Styling infrastructure |
| Lun | Component library base (Button, Card, Modal, Table) | `components/common/` |
| Mar | React Router setup con lazy loading | Routing infrastructure |
| Mar | State management setup (Zustand) | `store/` |
| Mer | API service layer (Axios instance, interceptors) | `services/api.ts` |
| Mer | Authentication flow frontend (Login page) | Login/Logout working |
| Gio | Layout principale (Sidebar, Header, Content) | App shell |
| Gio | Dashboard page skeleton | Dashboard placeholder |
| Ven | WebSocket connection setup | Real-time infrastructure |
| Ven | Error boundaries e loading states | UX base complete |

### 3.3 Milestone Fase 1
- [x] Backend FastAPI running con auth
- [x] Frontend React con routing e auth
- [x] PostgreSQL + Redis + TimescaleDB operativi
- [x] CI/CD pipeline base
- [x] Documentazione API auto-generata

**Status: ✅ COMPLETATA**

---

## 4. FASE 2: Data Acquisition Layer (Settimane 4-7)

### 4.1 Obiettivi
- Implementazione tutti i 15 provider adapters
- Sistema di orchestrazione e routing
- Rate limiting e budget tracking
- Failover automatico
- Cache layer per dati real-time

### 4.2 Dettaglio Settimana per Settimana

#### Settimana 4: Provider Infrastructure
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Base adapter interface design | `adapters/base.py` |
| Lun | Rate limiter core implementation | `rate_limiter.py` |
| Mar | Budget tracker (daily limits) | `budget_tracker.py` |
| Mar | Provider health monitor | `health_monitor.py` |
| Mer | Failover manager | `failover.py` |
| Mer | Data normalizer (schema comune) | `data_normalizer.py` |
| Gio | Cache manager (Redis integration) | `cache_manager.py` |
| Gio | Gap detector per dati mancanti | `gap_detector.py` |
| Ven | Provider orchestrator core | `orchestrator.py` base |
| Ven | Unit tests infrastruttura | Tests passing |

#### Settimana 5: US Market Providers
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | **Alpaca adapter** (WebSocket + REST) | `adapters/alpaca.py` |
| Lun | Test Alpaca con simboli campione | Alpaca working |
| Mar | **Polygon.io adapter** (Snapshot endpoint) | `adapters/polygon.py` |
| Mar | Test Polygon batch queries | Polygon working |
| Mer | **Finnhub adapter** (REST + WebSocket) | `adapters/finnhub.py` |
| Mer | Test Finnhub multi-market | Finnhub working |
| Gio | **Tiingo adapter** | `adapters/tiingo.py` |
| Gio | **Intrinio adapter** | `adapters/intrinio.py` |
| Ven | US Market router integration | `routing/us_markets.py` |
| Ven | Integration tests US providers | US coverage complete |

#### Settimana 6: EU & Global Providers
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | **Twelve Data adapter** (batch 120 simboli) | `adapters/twelve_data.py` |
| Lun | Test Twelve Data EU markets | Twelve Data working |
| Mar | **yfinance adapter** (scraping wrapper) | `adapters/yfinance.py` |
| Mar | Rate limiting per yfinance | yfinance safe usage |
| Mer | **Investing.com adapter** (investpy/scraping) | `adapters/investing.py` |
| Mer | Test per mercati EU minori (MIB, IBEX) | Investing.com working |
| Gio | **Stooq adapter** (CSV bulk download) | `adapters/stooq.py` |
| Gio | Scheduler per Stooq bulk updates | Stooq bulk working |
| Ven | EU Market router integration | `routing/eu_markets.py` |
| Ven | Integration tests EU providers | EU coverage complete |

#### Settimana 7: Remaining Providers & Orchestration
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | **EODHD adapter** (Bulk API) | `adapters/eodhd.py` |
| Lun | **FMP adapter** | `adapters/fmp.py` |
| Mar | **Alpha Vantage adapter** | `adapters/alpha_vantage.py` |
| Mar | **Nasdaq Data Link adapter** | `adapters/nasdaq_datalink.py` |
| Mer | **Marketstack adapter** | `adapters/marketstack.py` |
| Mer | **StockData.org adapter** | `adapters/stockdata.py` |
| Gio | Asia Market router | `routing/asia_markets.py` |
| Gio | Market hours manager | `scheduler/market_hours.py` |
| Ven | Full orchestrator integration | Orchestrator complete |
| Ven | End-to-end provider tests | All 15 providers tested |

### 4.3 Milestone Fase 2
- [x] 15 provider adapters implementati e testati
- [x] Rate limiting funzionante con budget tracking
- [x] Failover automatico provider
- [x] Market routing per US, EU, Asia
- [x] Cache Redis per quotes real-time
- [x] Bulk download per dati storici

**Status: ✅ COMPLETATA (7 Dicembre 2025)**

#### Provider Attivi (14/15):
| Provider | Tipo | Quote | OHLCV | Mercati |
|----------|------|:-----:|:-----:|---------|
| finnhub | API Key | ✅ | ✅ | US/Global |
| polygon | API Key | ✅ | ✅ | US |
| alpha_vantage | API Key | ✅ | ✅ | Global |
| tiingo | API Key | ✅ | ✅ | US |
| twelve_data | API Key | ✅ | ✅ | Global |
| alpaca | API Key | ✅ | ✅ | US |
| fmp | API Key | ✅ | ✅ | Global |
| eodhd | API Key | ✅ | ✅ | Global |
| marketstack | API Key | ✅ | ✅ | Global |
| stockdata | API Key | ✅ | ✅ | US |
| yfinance | 🆓 Free | ✅ | ✅ | Global |
| stooq | 🆓 Free | ❌ | ✅ | Global |
| nasdaq | 🆓 Free | ✅ | ✅ | US Stocks/ETF |
| frankfurter | 🆓 Free | ✅ | ✅ | Forex (ECB) |

#### Provider Disabilitati:
- intrinio - No active subscription
- nasdaq_datalink - WIKI dataset discontinued
- investing - Cloudflare blocked (403)
- investiny - Cloudflare protected

---

## 5. FASE 3: Core Trading Engine (Settimane 8-11)

### 5.1 Obiettivi
- Portfolio management completo
- Paper trading engine
- Risk profiles implementation
- Frontend per trading e portfolio
- Real-time updates via WebSocket

### 5.2 Dettaglio Settimana per Settimana

#### Settimana 8: Portfolio Core
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Portfolio model completo (DB schema) | Models aggiornati |
| Lun | Portfolio CRUD service | `core/portfolio/service.py` |
| Mar | Risk profiles configuration | `core/portfolio/risk_profiles.py` |
| Mar | Portfolio constraints validator | `core/portfolio/constraints.py` |
| Mer | Asset allocation logic | `core/portfolio/allocation.py` |
| Mer | Position model e repository | Position management |
| Gio | Portfolio API endpoints | `endpoints/portfolios.py` |
| Gio | Position API endpoints | `endpoints/positions.py` |
| Ven | Frontend: Portfolio list/create pages | Portfolio UI base |
| Ven | Frontend: Risk profile selector | Profile selection working |

#### Settimana 9: Trading Engine
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Order model e types (Market, Limit, Stop) | Order infrastructure |
| Lun | Order manager service | `core/trading/order_manager.py` |
| Mar | Simulated execution engine | `core/trading/execution.py` |
| Mar | Price slippage simulation | Realistic execution |
| Mer | Position tracker | `core/trading/position_tracker.py` |
| Mer | P&L calculator (realized/unrealized) | `core/trading/pnl_calculator.py` |
| Gio | Trade history repository | Trade logging |
| Gio | Trade API endpoints | `endpoints/trades.py` |
| Ven | Frontend: Order form component | Order submission UI |
| Ven | Frontend: Position table | Positions display |

#### Settimana 10: Real-Time & Watchlists
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | WebSocket endpoint per market data | `websockets/market_stream.py` |
| Lun | Portfolio value real-time updates | Live P&L updates |
| Mar | Frontend: WebSocket hook | `hooks/useWebSocket.ts` |
| Mar | Frontend: Real-time quote display | Live prices in UI |
| Mer | Watchlist model e service | Watchlist management |
| Mer | Watchlist API endpoints | `endpoints/watchlists.py` |
| Gio | Frontend: Watchlist component | Watchlist UI |
| Gio | Frontend: Stock search | Symbol search working |
| Ven | Frontend: Market overview page | Markets page complete |
| Ven | Alert system base | Price alerts |

#### Settimana 11: Rebalancing & Advanced Trading
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Rebalancing engine | `core/portfolio/rebalancing.py` |
| Lun | Rebalancing recommendations | Auto-rebalance suggestions |
| Mar | Batch order execution | Multiple orders at once |
| Mar | Frontend: Rebalancing wizard | Rebalance UI |
| Mer | Trade history page | Complete trade log |
| Mer | Export trades (CSV) | Data export |
| Gio | Frontend: Trading page complete | Full trading UI |
| Gio | Frontend: Portfolio detail page | Portfolio analytics UI |
| Ven | Integration testing trading flow | E2E tests |
| Ven | Bug fixes e polish | Trading stable |

### 5.3 Milestone Fase 3
- [ ] Paper trading engine completo
- [ ] 3 risk profiles funzionanti
- [ ] Real-time portfolio updates
- [ ] Order execution simulato
- [ ] Watchlists e alerts
- [ ] Frontend trading completo

**Status: 🔄 DA INIZIARE**

---

## 6. FASE 4: ML & Analytics (Settimane 12-15)

### 6.1 Obiettivi
- Feature engineering pipeline
- ML models training e deployment
- Analytics dashboard
- Performance metrics
- Signal generation

### 6.2 Dettaglio Settimana per Settimana

#### Settimana 12: Feature Engineering
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Technical features calculator | `ml/features/technical_features.py` |
| Lun | RSI, MACD, Bollinger, ATR, ADX | 20+ indicators |
| Mar | Fundamental features (via FMP/Alpha Vantage) | `ml/features/fundamental_features.py` |
| Mar | P/E, P/B, ROE, Debt ratios | Key ratios |
| Mer | Market features (correlations, sector) | `ml/features/market_features.py` |
| Mer | Feature store (TimescaleDB) | `ml/features/feature_store.py` |
| Gio | Feature pipeline orchestration | Automated feature calc |
| Gio | Historical feature backfill | 1+ year features |
| Ven | Feature validation e quality checks | Data quality |
| Ven | Feature importance analysis | Notebook analysis |

#### Settimana 13: ML Models Training
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Price direction predictor (LSTM) | `ml/models/price_predictor.py` |
| Lun | Training pipeline setup | Model training infra |
| Mar | Trend classifier (Random Forest) | `ml/models/trend_classifier.py` |
| Mar | Cross-validation framework | Robust evaluation |
| Mer | Volatility model (GARCH/Prophet) | `ml/models/volatility_model.py` |
| Mer | Risk scorer (Gradient Boosting) | `ml/models/risk_scorer.py` |
| Gio | Ensemble methods | Combined predictions |
| Gio | Model registry (MLflow o custom) | Model versioning |
| Ven | Backtesting framework | `ml/training/backtester.py` |
| Ven | Model performance evaluation | Metrics dashboard |

#### Settimana 14: ML Integration & Analytics
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Inference service | `ml/inference/predictor.py` |
| Lun | Signal generator | `ml/inference/signal_generator.py` |
| Mar | Portfolio optimizer (Mean-Variance) | `ml/models/portfolio_optimizer.py` |
| Mar | ML API endpoints | `endpoints/ml_predictions.py` |
| Mer | Performance analytics service | `core/analytics/performance.py` |
| Mer | Sharpe, Sortino, Max Drawdown | Key metrics |
| Gio | Risk metrics (VaR, Beta) | `core/analytics/risk_metrics.py` |
| Gio | Benchmark comparison | `core/analytics/benchmarking.py` |
| Ven | Analytics API endpoints | `endpoints/analytics.py` |
| Ven | Automated reports | `core/analytics/reporting.py` |

#### Settimana 15: Frontend Analytics & ML
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Frontend: Chart library setup (Recharts/TradingView) | Charts infra |
| Lun | Candlestick chart component | Price charts |
| Mar | Performance charts (line, area) | Portfolio performance viz |
| Mar | Allocation pie chart | Asset allocation viz |
| Mer | Frontend: Analytics dashboard page | Analytics UI |
| Mer | Risk analysis components | Risk viz |
| Gio | Frontend: ML Insights page | Predictions UI |
| Gio | Signal indicators component | Buy/Sell signals |
| Ven | Model performance display | ML metrics viz |
| Ven | Feature importance charts | Explainable AI |

### 6.3 Milestone Fase 4
- [ ] 5 ML models trained e deployed
- [ ] Feature store con 50+ features
- [ ] Real-time predictions
- [ ] Analytics dashboard completo
- [ ] Performance e risk metrics
- [ ] Signal generation working

**Status: ⏳ FUTURO**

---

## 7. FASE 5: Polish & Production (Settimane 16-18)

### 7.1 Obiettivi
- Testing completo
- Performance optimization
- Security hardening
- Documentation
- Deployment

### 7.2 Dettaglio Settimana per Settimana

#### Settimana 16: Testing & Quality
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Unit tests coverage >80% backend | Pytest suite |
| Lun | Unit tests coverage >80% frontend | Jest/Vitest suite |
| Mar | Integration tests data providers | Provider tests |
| Mar | Integration tests trading flow | Trading tests |
| Mer | E2E tests con Playwright | E2E suite |
| Mer | Load testing (Locust) | Performance baseline |
| Gio | Security audit (OWASP) | Security fixes |
| Gio | Dependency vulnerability check | Dependencies updated |
| Ven | Bug fixes da testing | Critical bugs fixed |
| Ven | Code review e refactoring | Code quality |

#### Settimana 17: Optimization & Settings
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | Database query optimization | Indexes, query tuning |
| Lun | Redis caching optimization | Cache efficiency |
| Mar | API response time optimization | <100ms responses |
| Mar | Frontend bundle optimization | Code splitting |
| Mer | Frontend: Settings page | User settings UI |
| Mer | Provider configuration UI | API keys management |
| Gio | Rate limit monitor UI | Budget visualization |
| Gio | Notification settings | Email/Push config |
| Ven | System settings (admin) | Admin panel |
| Ven | Dark/Light theme polish | Theme complete |

#### Settimana 18: Documentation & Deployment
| Giorno | Task | Deliverable |
|--------|------|-------------|
| Lun | API documentation completa | OpenAPI spec |
| Lun | User guide | User documentation |
| Mar | Developer documentation | Technical docs |
| Mar | Architecture decision records | ADRs |
| Mer | Docker production config | `docker-compose.prod.yml` |
| Mer | Environment setup guide | Deployment docs |
| Gio | CI/CD pipeline completa | GitHub Actions |
| Gio | Monitoring setup (logs, metrics) | Observability |
| Ven | Final deployment | Production ready |
| Ven | Handover e knowledge transfer | Project complete |

### 7.3 Milestone Fase 5
- [ ] Test coverage >80%
- [ ] Performance ottimizzata
- [ ] Security audit passed
- [ ] Documentation completa
- [ ] Production deployment ready

**Status: ⏳ FUTURO**

---

## 8. Roadmap Visuale

```
2024/2025 Timeline
══════════════════════════════════════════════════════════════════════════════

        GENNAIO               FEBBRAIO              MARZO                APRILE
    ┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
W1  │ █ Setup Infra   │                 │                 │                 │
W2  │ █ Auth & API    │                 │                 │                 │
W3  │ █ Frontend Base │                 │                 │                 │
    │    FASE 1 ✓     │                 │                 │                 │
W4  │                 │ █ Provider Infra│                 │                 │
W5  │                 │ █ US Providers  │                 │                 │
W6  │                 │ █ EU Providers  │                 │                 │
W7  │                 │ █ All Providers │                 │                 │
    │                 │    FASE 2 ✓     │                 │                 │
W8  │                 │                 │ █ Portfolio     │                 │
W9  │                 │                 │ █ Trading Eng   │                 │
W10 │                 │                 │ █ Real-Time     │                 │
W11 │                 │                 │ █ Advanced      │                 │
    │                 │                 │    FASE 3 ✓     │                 │
W12 │                 │                 │                 │ █ Features      │
W13 │                 │                 │                 │ █ ML Models     │
W14 │                 │                 │                 │ █ Analytics     │
W15 │                 │                 │                 │ █ Frontend ML   │
    │                 │                 │                 │    FASE 4 ✓     │
W16 │                 │                 │                 │                 │
W17 │                 │                 │                 │                 │
W18 │                 │                 │                 │                 │
    └─────────────────┴─────────────────┴─────────────────┴─────────────────┘

        MAGGIO
    ┌─────────────────┐
W16 │ █ Testing       │
W17 │ █ Optimization  │
W18 │ █ Deploy        │
    │    FASE 5 ✓     │
    │                 │
    │  🎉 COMPLETE    │
    └─────────────────┘

Legenda:
█ = Sprint attivo
✓ = Milestone raggiunta
```

---

## 9. Risk Management

### 9.1 Rischi Identificati

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Provider API changes | Media | Alto | Adapter abstraction, monitoring, quick fix process |
| Rate limit più restrittivi | Media | Medio | Budget conservativo (75%), fallback providers |
| yfinance blocking | Alta | Medio | Multiple backup providers, conservative rate |
| ML model accuracy insufficiente | Media | Medio | Ensemble methods, continuous retraining |
| Performance issues con 800 simboli | Bassa | Alto | Batch processing, caching, async |
| Stooq/Investing.com scraping failures | Media | Basso | Structured fallback, manual intervention |

### 9.2 Piano di Contingenza
- **Weekly provider health review** - Verifica settimanale stato providers
- **Automated alerts** - Notifiche su failures o degradation
- **Fallback procedures** - Documentazione per switch manuale providers
- **Data backup** - Daily backup dati storici

---

## 10. Definition of Done

### Per ogni Feature:
- [ ] Codice implementato e funzionante
- [ ] Unit tests scritti (coverage >80%)
- [ ] Integration tests se applicabile
- [ ] Code review completata
- [ ] Documentazione aggiornata
- [ ] No critical/high bugs
- [ ] Performance accettabile

### Per ogni Milestone:
- [ ] Tutte le features della fase complete
- [ ] Demo funzionante
- [ ] Documentazione fase aggiornata
- [ ] Retrospettiva completata
- [ ] Piano fase successiva confermato

---

## 11. Dipendenze Tecniche

### Backend (Python 3.11+)
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
alembic>=1.13.0
asyncpg>=0.29.0
redis>=5.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
httpx>=0.26.0
websockets>=12.0
aiohttp>=3.9.0

# Data Providers
yfinance>=0.2.36
pandas>=2.1.0
numpy>=1.26.0
requests>=2.31.0

# ML
scikit-learn>=1.4.0
xgboost>=2.0.0
lightgbm>=4.2.0
tensorflow>=2.15.0  # o pytorch
prophet>=1.1.0

# Utils
python-dateutil>=2.8.0
pytz>=2024.1
APScheduler>=3.10.0
```

### Frontend (Node 20+)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "zustand": "^4.4.0",
    "axios": "^1.6.0",
    "@tanstack/react-query": "^5.17.0",
    "recharts": "^2.10.0",
    "lightweight-charts": "^4.1.0",
    "date-fns": "^3.2.0",
    "tailwindcss": "^3.4.0",
    "@headlessui/react": "^1.7.0",
    "@heroicons/react": "^2.1.0",
    "react-hook-form": "^7.49.0",
    "zod": "^3.22.0"
  }
}
```

---

## 12. Prossimi Passi Immediati

### Week 1 - Primo Sprint
1. **Giorno 1**: Setup repository Git, struttura cartelle
2. **Giorno 1**: Creazione `docker-compose.dev.yml`
3. **Giorno 2**: Setup backend FastAPI base
4. **Giorno 2**: Setup frontend Vite + React
5. **Giorno 3**: Database schema iniziale
6. **Giorno 3-5**: Implementazione auth flow

### Prerequisiti da Verificare
- [ ] Python 3.11+ installato
- [ ] Node.js 20+ installato
- [ ] Docker e Docker Compose installati
- [ ] PostgreSQL client tools
- [ ] Redis CLI
- [ ] Git configurato
- [ ] IDE/Editor configurato (VS Code + extensions)
- [ ] API Keys raccolte per tutti i providers

---

*Documento generato il: $(date)*
*Versione: 1.0*
