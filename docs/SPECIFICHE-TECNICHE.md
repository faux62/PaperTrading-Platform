# 📋 Specifiche Tecniche - PaperTrading Platform

**Versione:** 2.0  
**Data:** 18 Dicembre 2025  
**Autore:** Sistema

> **Changelog v2.0:** Aggiunta sezione 8 (Gestione Multi-Currency FX)

---

## 1. Panoramica Architetturale

### 1.1 Stack Tecnologico

#### Backend
| Componente | Tecnologia | Versione |
|------------|------------|----------|
| Framework | FastAPI | ≥0.109.0 |
| Server WSGI | Uvicorn | ≥0.27.0 |
| Database ORM | SQLAlchemy (async) | ≥2.0.25 |
| Database | PostgreSQL | 16 |
| Time-Series DB | TimescaleDB | latest-pg16 |
| Cache/Pub-Sub | Redis | 7 |
| Migrazioni | Alembic | ≥1.13.1 |

#### Frontend
| Componente | Tecnologia | Versione |
|------------|------------|----------|
| Framework | React | 18.2.0 |
| Linguaggio | TypeScript | 5.3.3 |
| Build Tool | Vite | latest |
| State Management | Zustand | 4.5.7 |
| Data Fetching | TanStack Query | 5.17.19 |
| Styling | TailwindCSS | 3.4.1 |
| Charts | Recharts + Lightweight Charts | 2.10.4 / 4.1.1 |
| Forms | React Hook Form + Zod | 7.49.3 / 3.22.4 |

#### Machine Learning
| Componente | Tecnologia | Versione |
|------------|------------|----------|
| Framework | scikit-learn | ≥1.4.0 |
| Gradient Boosting | XGBoost, LightGBM | ≥2.0.3 / ≥4.2.0 |
| Technical Analysis | ta | ≥0.11.0 |
| Data Processing | Pandas, NumPy | ≥2.1.4 / ≥1.26.3 |

---

## 2. Architettura del Sistema

### 2.1 Diagramma dei Componenti

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React/TypeScript)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │Dashboard │ │Portfolio │ │ Markets  │ │ Trading  │ │Analytics │         │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘         │
│       └────────────┴────────────┴────────────┴────────────┘                │
│                              REST API + WebSocket                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                         API GATEWAY (FastAPI)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │            JWT Authentication + Rate Limiting + CORS                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  API v1 Routes:                                                              │
│  ├── /auth        (registro, login, refresh, logout)                        │
│  ├── /portfolios  (CRUD, posizioni, performance)                            │
│  ├── /positions   (gestione posizioni)                                      │
│  ├── /trades      (ordini, esecuzione, storico)                             │
│  ├── /market      (quote, ricerca, storici)                                 │
│  ├── /watchlists  (liste personalizzate)                                    │
│  ├── /alerts      (alert prezzi)                                            │
│  ├── /analytics   (metriche, benchmark)                                     │
│  ├── /ml          (predizioni, segnali, ottimizzazione)                     │
│  ├── /currency    (tassi cambio, conversione)                               │
│  ├── /settings    (preferenze, API keys)                                    │
│  └── /providers   (stato provider dati)                                     │
│                                                                              │
│  WebSocket:                                                                  │
│  ├── /ws/market/{symbol}    (quote real-time)                               │
│  └── /ws/portfolio/{id}     (aggiornamenti portfolio)                       │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                        CORE SERVICES LAYER                                   │
│                                                                              │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │   PORTFOLIO   │  │    TRADING    │  │   ANALYTICS   │                   │
│  │   SERVICE     │  │    ENGINE     │  │    SERVICE    │                   │
│  │               │  │               │  │               │                   │
│  │ • CRUD        │  │ • Order Mgmt  │  │ • Performance │                   │
│  │ • Risk Prof.  │  │ • Execution   │  │ • Risk Metr.  │                   │
│  │ • Rebalancing │  │ • P&L Calc    │  │ • Benchmark   │                   │
│  │ • Allocation  │  │ • Slippage    │  │ • Drawdown    │                   │
│  └───────────────┘  └───────────────┘  └───────────────┘                   │
│                                                                              │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │  ML SERVICE   │  │  MARKET DATA  │  │   SCHEDULER   │                   │
│  │               │  │  AGGREGATOR   │  │    SERVICE    │                   │
│  │ • Predictions │  │               │  │               │                   │
│  │ • Signals     │  │ • Multi-Prov. │  │ • Cron Jobs   │                   │
│  │ • Optimize    │  │ • Failover    │  │ • Market Hrs  │                   │
│  │ • Backtest    │  │ • Rate Limit  │  │ • Cleanup     │                   │
│  └───────────────┘  └───────────────┘  └───────────────┘                   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                    DATA PROVIDER LAYER (14 Providers)                        │
│                                                                              │
│  Primary (Real-time):     │  Historical:        │  No API Key:             │
│  • Alpaca (WS)            │  • EODHD            │  • yfinance              │
│  • Polygon (REST)         │  • Stooq            │  • Stooq                 │
│  • Finnhub (REST+WS)      │  • FMP              │  • Investing.com         │
│  • Twelve Data (REST)     │  • Alpha Vantage    │                          │
│  • Tiingo (REST+WS)       │  • Nasdaq DataLink  │                          │
│  • MarketStack (REST)     │  • Intrinio         │                          │
│  • StockData.org (REST)   │                     │                          │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                          DATA STORAGE LAYER                                  │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  PostgreSQL  │    │    Redis     │    │ TimescaleDB  │                  │
│  │    (5432)    │    │    (6379)    │    │    (5433)    │                  │
│  │              │    │              │    │              │                  │
│  │ • Users      │    │ • Cache      │    │ • OHLCV      │                  │
│  │ • Portfolios │    │ • Sessions   │    │ • Indicators │                  │
│  │ • Trades     │    │ • Rate Lim.  │    │ • ML Features│                  │
│  │ • Positions  │    │ • Pub/Sub    │    │ • Tick Data  │                  │
│  │ • Settings   │    │ • Quotes     │    │ • Historical │                  │
│  │ • Alerts     │    │              │    │              │                  │
│  │ • Watchlists │    │              │    │              │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Schema Database

### 3.1 Modello Entità-Relazioni

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│    users    │       │    portfolios   │       │  positions  │
├─────────────┤       ├─────────────────┤       ├─────────────┤
│ id (PK)     │──┐    │ id (PK)         │──┐    │ id (PK)     │
│ username    │  │    │ user_id (FK)    │  │    │ portfolio_id│
│ email       │  └───►│ name            │  └───►│ symbol      │
│ password    │       │ description     │       │ quantity    │
│ full_name   │       │ risk_profile    │       │ avg_cost    │
│ is_active   │       │ initial_capital │       │ market_value│
│ created_at  │       │ cash_balance    │       │ unrealized  │
│ updated_at  │       │ currency        │       │ created_at  │
└─────────────┘       │ is_active       │       │ updated_at  │
      │               │ created_at      │       └─────────────┘
      │               └─────────────────┘              │
      │                      │                         │
      │               ┌──────┴──────┐                  │
      │               ▼             ▼                  │
      │        ┌─────────────┐ ┌─────────────┐        │
      │        │   trades    │ │  watchlists │        │
      │        ├─────────────┤ ├─────────────┤        │
      │        │ id (PK)     │ │ id (PK)     │        │
      │        │ portfolio_id│ │ user_id (FK)│        │
      │        │ symbol      │ │ name        │        │
      │        │ trade_type  │ │ description │        │
      │        │ order_type  │ │ symbols[]   │        │
      │        │ status      │ │ created_at  │        │
      │        │ quantity    │ └─────────────┘        │
      │        │ price       │                        │
      │        │ executed_at │                        │
      │        │ commission  │                        │
      │        │ realized_pnl│                        │
      │        └─────────────┘                        │
      │                                               │
      └────────────────┐                              │
                       ▼                              │
                ┌─────────────┐       ┌──────────────┐
                │   alerts    │       │user_settings │
                ├─────────────┤       ├──────────────┤
                │ id (PK)     │       │ id (PK)      │
                │ user_id (FK)│       │ user_id (FK) │
                │ symbol      │       │ theme        │
                │ alert_type  │       │ api_keys     │
                │ target_value│       │ notifications│
                │ status      │       │ display_pref │
                │ triggered_at│       │ updated_at   │
                └─────────────┘       └──────────────┘
```

### 3.2 Tabelle Principali

#### users
| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| id | SERIAL PK | ID univoco |
| username | VARCHAR(50) | Username univoco |
| email | VARCHAR(255) | Email univoca |
| hashed_password | VARCHAR | Password bcrypt |
| full_name | VARCHAR(255) | Nome completo |
| base_currency | VARCHAR(3) | Valuta preferita |
| is_active | BOOLEAN | Account attivo |
| created_at | TIMESTAMP | Data creazione |
| updated_at | TIMESTAMP | Ultimo aggiornamento |

#### portfolios
| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| id | SERIAL PK | ID univoco |
| user_id | INTEGER FK | Riferimento utente |
| name | VARCHAR(255) | Nome portfolio |
| description | TEXT | Descrizione |
| risk_profile | VARCHAR(20) | aggressive/balanced/prudent |
| initial_capital | DECIMAL(18,2) | Capitale iniziale |
| cash_balance | DECIMAL(18,2) | Saldo disponibile |
| currency | VARCHAR(3) | Valuta (USD, EUR...) |
| is_active | VARCHAR(20) | active/archived/closed |
| created_at | TIMESTAMP | Data creazione |
| updated_at | TIMESTAMP | Ultimo aggiornamento |

#### trades
| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| id | SERIAL PK | ID univoco |
| portfolio_id | INTEGER FK | Riferimento portfolio |
| symbol | VARCHAR(20) | Simbolo (es. AAPL) |
| exchange | VARCHAR(20) | Borsa |
| trade_type | ENUM | buy/sell |
| order_type | ENUM | market/limit/stop/stop_limit |
| status | ENUM | pending/executed/cancelled/rejected |
| quantity | DECIMAL(18,8) | Quantità |
| price | DECIMAL(18,8) | Prezzo ordine |
| executed_price | DECIMAL(18,8) | Prezzo eseguito |
| executed_quantity | DECIMAL(18,8) | Quantità eseguita |
| total_value | DECIMAL(18,2) | Valore totale |
| commission | DECIMAL(18,4) | Commissione |
| slippage | DECIMAL(18,4) | Slippage |
| realized_pnl | DECIMAL(18,2) | P&L realizzato |
| native_currency | VARCHAR(3) | Valuta originale |
| created_at | TIMESTAMP | Data creazione |
| executed_at | TIMESTAMP | Data esecuzione |
| notes | TEXT | Note |

#### positions
| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| id | SERIAL PK | ID univoco |
| portfolio_id | INTEGER FK | Riferimento portfolio |
| symbol | VARCHAR(20) | Simbolo |
| exchange | VARCHAR(20) | Borsa |
| quantity | DECIMAL(18,8) | Quantità |
| avg_cost | DECIMAL(18,8) | Costo medio |
| current_price | DECIMAL(18,8) | Prezzo corrente |
| market_value | DECIMAL(18,2) | Valore di mercato |
| unrealized_pnl | DECIMAL(18,2) | P&L non realizzato |
| unrealized_pnl_percent | DECIMAL(10,4) | P&L % |
| native_currency | VARCHAR(3) | Valuta originale |
| created_at | TIMESTAMP | Data apertura |
| updated_at | TIMESTAMP | Ultimo aggiornamento |

---

## 4. API REST

### 4.1 Autenticazione

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Registrazione nuovo utente |
| `/api/v1/auth/login` | POST | Login (ritorna JWT) |
| `/api/v1/auth/refresh` | POST | Rinnovo access token |
| `/api/v1/auth/logout` | POST | Logout (invalida token) |
| `/api/v1/auth/me` | GET | Profilo utente corrente |
| `/api/v1/auth/me` | PATCH | Aggiorna profilo |
| `/api/v1/auth/change-password` | POST | Cambio password |

**Autenticazione:** Bearer Token JWT
- Access Token: 30 minuti
- Refresh Token: 7 giorni
- Token blacklisting via Redis

### 4.2 Portfolio

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/v1/portfolios/` | GET | Lista portfolio utente |
| `/api/v1/portfolios/` | POST | Crea nuovo portfolio |
| `/api/v1/portfolios/{id}` | GET | Dettaglio portfolio |
| `/api/v1/portfolios/{id}` | PUT | Aggiorna portfolio |
| `/api/v1/portfolios/{id}` | DELETE | Elimina portfolio |
| `/api/v1/portfolios/{id}/positions` | GET | Posizioni portfolio |
| `/api/v1/portfolios/{id}/performance` | GET | Metriche performance |
| `/api/v1/portfolios/{id}/allocation` | GET | Allocazione asset |
| `/api/v1/portfolios/{id}/validate-trade` | POST | Valida trade vs risk profile |
| `/api/v1/portfolios/risk-profiles` | GET | Lista profili di rischio |

### 4.3 Trading

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/v1/trades/` | GET | Lista trades con filtri |
| `/api/v1/trades/orders` | POST | Crea nuovo ordine |
| `/api/v1/trades/orders/{id}` | GET | Dettaglio ordine |
| `/api/v1/trades/orders/{id}` | DELETE | Cancella ordine pending |
| `/api/v1/trades/orders/{id}/execute` | POST | Esegui ordine |
| `/api/v1/trades/pending` | GET | Ordini pendenti |
| `/api/v1/trades/history/{portfolio_id}` | GET | Storico trades |
| `/api/v1/trades/summary/{portfolio_id}` | GET | Riepilogo trades |
| `/api/v1/trades/pnl/{portfolio_id}` | GET | Calcolo P&L |
| `/api/v1/trades/export/{portfolio_id}` | GET | Export CSV |
| `/api/v1/trades/batch` | POST | Ordini multipli |

### 4.4 Market Data

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/v1/market/quote/{symbol}` | GET | Quote singolo simbolo |
| `/api/v1/market/quotes` | GET | Quote multipli (comma-sep) |
| `/api/v1/market/history/{symbol}` | GET | Dati storici OHLCV |
| `/api/v1/market/search` | GET | Ricerca simboli |
| `/api/v1/market/market-hours` | GET | Orari mercato |

### 4.5 Watchlists

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/v1/watchlists/` | GET | Lista watchlist |
| `/api/v1/watchlists/` | POST | Crea watchlist |
| `/api/v1/watchlists/{id}` | GET | Dettaglio con simboli |
| `/api/v1/watchlists/{id}` | PUT | Aggiorna watchlist |
| `/api/v1/watchlists/{id}` | DELETE | Elimina watchlist |
| `/api/v1/watchlists/{id}/symbols` | GET | Lista simboli |
| `/api/v1/watchlists/{id}/symbols` | POST | Aggiungi simbolo |
| `/api/v1/watchlists/{id}/symbols/{sym}` | DELETE | Rimuovi simbolo |

### 4.6 Alerts

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/v1/alerts/` | GET | Lista alert |
| `/api/v1/alerts/` | POST | Crea alert |
| `/api/v1/alerts/summary` | GET | Riepilogo alert |
| `/api/v1/alerts/{id}` | GET | Dettaglio alert |
| `/api/v1/alerts/{id}` | PUT | Aggiorna alert |
| `/api/v1/alerts/{id}` | DELETE | Elimina alert |
| `/api/v1/alerts/{id}/toggle` | POST | Attiva/disattiva |

### 4.7 Analytics

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/v1/analytics/performance/{portfolio_id}` | GET | Metriche performance |
| `/api/v1/analytics/risk/{portfolio_id}` | GET | Metriche rischio (VaR, Beta) |
| `/api/v1/analytics/benchmark/{portfolio_id}` | GET | Confronto benchmark |
| `/api/v1/analytics/drawdown/{portfolio_id}` | GET | Analisi drawdown |
| `/api/v1/analytics/rolling/{portfolio_id}` | GET | Metriche rolling |

### 4.8 ML Predictions

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/v1/ml/predict` | POST | Predizione singola |
| `/api/v1/ml/predict/batch` | POST | Predizioni batch |
| `/api/v1/ml/signals/{symbol}` | GET | Segnali trading |
| `/api/v1/ml/signals/aggregate/{symbol}` | GET | Segnali aggregati |
| `/api/v1/ml/optimize` | POST | Ottimizzazione portfolio |
| `/api/v1/ml/risk-parity` | POST | Ottimizzazione risk parity |
| `/api/v1/ml/rebalance` | POST | Calcolo ribilanciamento |
| `/api/v1/ml/backtest` | POST | Backtest strategia |
| `/api/v1/ml/features/{symbol}` | GET | Feature ML |
| `/api/v1/ml/features/bulk` | POST | Feature bulk |
| `/api/v1/ml/model/{name}/health` | GET | Health modello |
| `/api/v1/ml/model/{name}/metrics` | GET | Metriche modello |

### 4.9 Altri Endpoint

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/api/v1/currency/supported` | GET | Valute supportate |
| `/api/v1/currency/rates` | GET | Tassi di cambio |
| `/api/v1/currency/convert` | POST | Conversione valuta |
| `/api/v1/settings/` | GET | Impostazioni utente |
| `/api/v1/settings/` | PATCH | Aggiorna impostazioni |
| `/api/v1/settings/api-keys` | POST | Salva API key |
| `/api/v1/settings/api-keys/{provider}` | DELETE | Rimuovi API key |
| `/api/v1/providers/status` | GET | Stato tutti provider |
| `/api/v1/providers/rate-limits` | GET | Rate limits |
| `/api/v1/providers/health` | GET | Health provider |
| `/api/v1/providers/budget` | GET | Budget usage |

---

## 5. WebSocket API

### 5.1 Market Stream
```
ws://localhost:8000/api/v1/ws/market/{symbol}
```

**Messaggi ricevuti:**
```json
{
  "type": "quote",
  "symbol": "AAPL",
  "price": 178.50,
  "change": 2.30,
  "change_percent": 1.30,
  "volume": 45000000,
  "timestamp": "2025-12-07T10:30:00Z"
}
```

### 5.2 Portfolio Stream
```
ws://localhost:8000/api/v1/ws/portfolio/{portfolio_id}
```

**Messaggi ricevuti:**
```json
{
  "type": "position_update",
  "portfolio_id": 1,
  "symbol": "AAPL",
  "current_price": 178.50,
  "market_value": 17850.00,
  "unrealized_pnl": 350.00
}
```

---

## 6. Infrastruttura Docker

### 6.1 Servizi

| Servizio | Immagine | Porta | Descrizione |
|----------|----------|-------|-------------|
| postgres | postgres:16-alpine | 5432 | Database principale |
| timescaledb | timescale/timescaledb:latest-pg16 | 5433 | Time-series data |
| redis | redis:7-alpine | 6379 | Cache e pub/sub |
| pgadmin | dpage/pgadmin4 | 5050 | GUI PostgreSQL |
| redis-commander | rediscommander/redis-commander | 8081 | GUI Redis |

### 6.2 Configurazione

**File:** `infrastructure/docker/docker-compose.dev.yml`

```yaml
# Variabili ambiente richieste (.env):
POSTGRES_DB=papertrading
POSTGRES_USER=papertrading_user
POSTGRES_PASSWORD=<password>
TIMESCALE_DB=papertrading_ts
REDIS_URL=redis://localhost:6379
```

### 6.3 Comandi

```bash
# Avvio sviluppo
docker-compose --env-file .env -f infrastructure/docker/docker-compose.dev.yml up -d

# Stop
docker-compose --env-file .env -f infrastructure/docker/docker-compose.dev.yml down

# Logs
docker-compose logs -f postgres
```

---

## 7. Sicurezza

### 7.1 Autenticazione
- **JWT Token** con algoritmo HS256
- **Access Token:** 30 min, **Refresh Token:** 7 giorni
- **Token Blacklisting** via Redis per logout
- **Session tracking** con IP e User-Agent

### 7.2 Password
- **Hashing:** bcrypt con salt
- **Requisiti:** min 8 caratteri
- **Rate limiting:** su tentativi login

### 7.3 API Keys
- Crittografia AES per storage API keys provider
- Mascheramento in output (primi 4 + ultimi 4 caratteri)

### 7.4 CORS
```python
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

---

## 8. Gestione Multi-Currency (FX)

### 8.1 Approccio Architetturale

Il sistema utilizza l'**Approccio B - Tasso FX Dinamico** per la gestione multi-valuta:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FX ARCHITECTURE (Approach B)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    Ogni ora    ┌──────────────────┐               │
│  │ Frankfurter  │───────────────►│  exchange_rates  │               │
│  │  API (ECB)   │                │     table        │               │
│  └──────────────┘                └────────┬─────────┘               │
│                                           │                          │
│                                           ▼                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    CONVERSION FLOW                              │ │
│  │                                                                  │ │
│  │  avg_cost (native)  ×  current_fx_rate  =  market_value (port.) │ │
│  │  unrealized_pnl = qty × (price - avg_cost) × current_fx_rate    │ │
│  │                                                                  │ │
│  │  P&L riflette SOLO performance titolo (non forex)               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.2 Valute Supportate

| Valuta | Descrizione | Uso |
|--------|-------------|-----|
| EUR | Euro | Portfolio base, Euronext |
| USD | US Dollar | NYSE, NASDAQ |
| GBP | British Pound | LSE |
| CHF | Swiss Franc | SIX |

**Coppie FX gestite:** 12 (tutte le combinazioni)

### 8.3 Tabella `exchange_rates`

```sql
CREATE TABLE exchange_rates (
    id SERIAL PRIMARY KEY,
    base_currency VARCHAR(3) NOT NULL,    -- EUR, USD, GBP, CHF
    quote_currency VARCHAR(3) NOT NULL,   -- EUR, USD, GBP, CHF
    rate NUMERIC(20,10) NOT NULL,         -- 1 base = rate quote
    source VARCHAR(50) DEFAULT 'frankfurter',
    fetched_at TIMESTAMP NOT NULL,
    UNIQUE(base_currency, quote_currency)
);
```

### 8.4 Servizi FX

| Servizio | File | Descrizione |
|----------|------|-------------|
| `FxRateUpdaterService` | `services/fx_rate_updater.py` | Fetch da Frankfurter API |
| `ExchangeRateRepository` | `db/repositories/exchange_rate.py` | CRUD tassi FX |
| `convert()` | `utils/currency.py` | Conversione importi |
| `position_analytics` | `services/position_analytics.py` | Audit FX storico |

### 8.5 Scheduler Job

```python
# Job FX Rate Update - eseguito ogni ora
scheduler.add_job(
    update_exchange_rates,
    'cron',
    minute=5,  # :05 di ogni ora
    id='fx_rate_update'
)
```

### 8.6 Calcolo P&L

```
unrealized_pnl = quantity × (current_price - avg_cost) × current_fx_rate
```

**Caratteristiche:**
- P&L riflette **SOLO** la performance del titolo
- Non include variazioni forex
- Audit trail completo in `TRADES.exchange_rate`
- Funzioni helper per analisi storica con FX al momento dell'acquisto

### 8.7 Funzioni Audit

| Funzione | Descrizione |
|----------|-------------|
| `get_historical_cost_in_portfolio_currency()` | Costo medio con FX storico |
| `get_avg_entry_exchange_rate()` | Tasso FX medio di ingresso |
| `get_position_cost_breakdown()` | Breakdown completo costi |
| `calculate_forex_impact()` | Impatto forex sulla posizione |

---

## 9. Performance

### 9.1 Caching (Redis)
- Quote real-time: TTL 60 secondi
- Exchange rates: TTL 1 ora
- Session data: TTL = token expiry
- Rate limit counters: sliding window

### 9.2 Database
- Connection pooling: 5-20 connessioni
- Async queries via asyncpg
- Indici su: user_id, portfolio_id, symbol, created_at

### 9.3 Rate Limiting Provider
- Budget 75% dei rate limits giornalieri
- Failover automatico tra provider
- Circuit breaker per provider non disponibili

---

## 10. Logging e Monitoring

### 10.1 Logging
- **Library:** Loguru
- **Livelli:** DEBUG, INFO, WARNING, ERROR
- **Output:** Console + file rotativo

### 10.2 Metriche Provider
- Latenza media e P95
- Error rate
- Requests totali/successo/fallite
- Circuit breaker state

---

## 11. Testing

### 11.1 Framework
- **Backend:** pytest, pytest-asyncio
- **Frontend:** Vitest, Playwright (E2E)
- **Load:** Locust

### 11.2 Coverage Target
- Unit tests: 80%+
- Integration tests: API endpoints
- E2E tests: User flows critici

---

## 12. Requisiti di Sistema

### 12.1 Sviluppo
- Python 3.11+
- Node.js 18+
- Docker Desktop
- 8GB RAM minimo

### 12.2 Produzione
- 4 vCPU
- 16GB RAM
- 100GB SSD
- PostgreSQL 16
- Redis 7
