# PaperTrading Platform - Handoff Notes

## Data: 18 Dicembre 2025

---

## 🎯 Overview del Progetto

**PaperTrading-Platform** è una piattaforma completa di paper trading che permette di simulare operazioni di trading su mercati globali con dati reali, senza rischiare denaro vero.

### Stack Tecnologico
- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS
- **Backend**: FastAPI + SQLAlchemy (async) + Pydantic
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Container**: Docker Compose con profiles

---

## ✅ Funzionalità Completate

### Core Trading
- ✅ **Autenticazione**: JWT con refresh tokens, sessione persistente
- ✅ **Portfolio Management**: CRUD completo con currency base (EUR/USD/GBP/CHF)
- ✅ **Order Execution**: Market orders con esecuzione automatica
- ✅ **Positions**: Apertura, chiusura, visualizzazione P&L real-time
- ✅ **Trade History**: Storico completo di tutte le operazioni

### Single Currency Model (CRITICO!)
Il sistema usa un modello **Single Currency** - ogni portfolio ha UNA SOLA valuta base:
- `portfolio.cash_balance` è l'UNICA fonte di verità per il cash
- Quando compri un titolo in valuta diversa (es. AAPL in USD con portfolio EUR), il sistema:
  1. Ottiene il prezzo in USD
  2. Converte il costo totale da USD → EUR usando `convert()`
  3. Scala `portfolio.cash_balance` in EUR
  4. Salva `exchange_rate` nel trade per audit trail
- **File chiave**: `backend/app/utils/currency.py` con funzione `convert(amount, from_ccy, to_ccy)`

### Global Market Universe
- ✅ **623 simboli** da mercati globali (US, EU, UK, ASIA)
- File: `backend/app/data_providers/symbol_universe.py`
- Simboli con suffissi: `.MI` (Milano), `.L` (Londra), `.PA` (Parigi), `.DE` (Francoforte)

### Data Providers (Orchestrator Pattern)
- **Priorità provider**: Polygon → Finnhub → Alpha Vantage → Twelve Data → Yahoo Finance
- **Fallback automatico** se un provider fallisce
- **Cache Redis** per ridurre chiamate API
- ⚠️ **MAI usare dati MOCK** - sempre dati reali

### Email Notifications
- ✅ Sistema SMTP via Gmail configurato
- Notifiche per: conferma ordini, alert prezzi, report periodici

---

## 🏗️ Architettura Database

### Tabelle Principali
```
users           → Utenti con autenticazione
portfolios      → Portfolio con cash_balance e currency
positions       → Posizioni aperte (symbol, quantity, avg_cost, etc.)
trades          → Storico operazioni (buy/sell con exchange_rate)
watchlists      → Liste titoli da monitorare
```

### Campi Position (Approccio B - FX Dinamico, Dicembre 2025)
```sql
positions.avg_cost       -- Costo medio in valuta NATIVA del titolo (USD per US stocks)
positions.current_price  -- Prezzo corrente in valuta NATIVA
positions.market_value   -- Valore in valuta PORTFOLIO (convertito con FX corrente)
positions.unrealized_pnl -- P&L in valuta PORTFOLIO (riflette solo performance stock)
-- NOTA: Non esistono più avg_cost_portfolio e entry_exchange_rate!
-- Il P&L è calcolato con tasso FX corrente per isolare performance stock da forex.
```

### Campi Trade
```sql
trades.exchange_rate            -- Tasso usato per la conversione
trades.native_currency          -- Valuta nativa del titolo
```

---

## 🐳 Docker Setup (IMPORTANTE!)

### File Unificato con Profiles
Da Dicembre 2025, esiste UN SOLO file `docker-compose.yml` con profiles:

```bash
cd "/Volumes/X9 Pro/Sviluppo/Applicazioni/Finance/PaperTrading-Platform/infrastructure/docker"

# Solo infrastruttura (sviluppo locale con backend/frontend fuori Docker)
docker-compose --profile infra up -d

# Deploy completo (tutto in Docker)
docker-compose --profile full up -d

# Aggiungere strumenti di sviluppo (pgAdmin, Redis Commander)
docker-compose --profile full --profile tools up -d

# Rebuild backend/frontend
docker-compose --profile full up -d --build backend frontend

# Stop tutto
docker-compose down
```

### ⚠️ File DEPRECATI (NON USARE!)
- `docker-compose.dev.yml.DEPRECATED`
- `docker-compose.local.yml.DEPRECATED`

Usare file diversi causa conflitti di namespace nei volumi Docker e **PERDITA DATI**!

### Volumi Docker
```
docker_postgres_data   → Dati PostgreSQL
docker_redis_data      → Dati Redis
docker_timescale_data  → Dati TimescaleDB (tools)
docker_pgadmin_data    → Config pgAdmin (tools)
```

---

## 🔐 Credenziali

### Accesso Applicazione
- **URL**: http://localhost (frontend) / http://localhost:8000 (API)
- **Admin**: `administrator` / `admin123`

### Database (PostgreSQL)
```
Host: localhost:5432
Database: papertrading
User: papertrading_user
Password: dev_password_123
```

### pgAdmin (tools profile)
- URL: http://localhost:5050
- Email: admin@papertrading.com
- Password: admin123

### Redis Commander (tools profile)
- URL: http://localhost:8081

---

## 📁 File Chiave Modificati (Dicembre 2025)

### Backend - Sistema FX (Approccio B)
| File | Scopo |
|------|-------|
| `backend/app/utils/currency.py` | Conversione `convert()` usando tassi da DB |
| `backend/app/services/fx/fx_rate_updater.py` | Aggiorna tassi FX da ECB (Frankfurter API) |
| `backend/app/db/repositories/exchange_rate.py` | Repository per tabella `exchange_rates` |
| `backend/app/bot/services/global_price_updater.py` | Aggiorna prezzi con conversione FX dinamica |
| `backend/app/core/trading/execution.py` | Esecuzione trade (solo valuta nativa) |
| `backend/app/core/currency_service.py` | DEPRECATED - non usare |

### Backend - API Endpoints
| File | Scopo |
|------|-------|
| `backend/app/api/v1/endpoints/positions.py` | Schema position (valori convertiti in portfolio currency) |
| `backend/app/api/v1/endpoints/trades.py` | Schema trade con `exchange_rate` storico |
| `backend/app/api/v1/endpoints/currency.py` | Endpoint `/convert/precise` |

### Frontend
| File | Scopo |
|------|-------|
| `frontend/src/pages/Dashboard.tsx` | `formatNativeCurrency()` per simboli valuta corretti |
| `frontend/src/types/index.ts` | Interfacce Position/Trade con campi currency |

### Docker
| File | Scopo |
|------|-------|
| `infrastructure/docker/docker-compose.yml` | File UNIFICATO con profiles |

---

## 🐛 Problemi Noti e Soluzioni

### 1. Simboli Valuta Errati (€ invece di $)
**Problema**: Dashboard mostrava € per titoli USD
**Soluzione**: Usare `position.native_currency` per "Avg Price", `portfolioCurrency` per totali

### 2. Sistema Doppio Cash (BUG CRITICO - Risolto)
**Problema**: Esistevano due sistemi paralleli (`cash_balances` table vs `portfolio.cash_balance`)
**Soluzione**: Eliminato uso di `cash_balances`, usare SOLO `portfolio.cash_balance`

### 3. Perdita Dati Docker
**Problema**: Usare `docker-compose.local.yml` dopo `docker-compose.dev.yml` creava volumi diversi
**Soluzione**: File unificato `docker-compose.yml` con profiles

### 4. TimescaleDB Warning
**Warning**: `platform (linux/amd64) does not match host (linux/arm64/v8)`
**Status**: Funziona comunque, è solo un warning per Mac M1/M2

---

## 🚀 Comandi Utili

### Logs
```bash
# Backend logs
docker-compose --profile full logs -f backend

# Solo errori
docker-compose --profile full logs backend 2>&1 | grep -i error
```

### Database Queries
```bash
# Accesso psql
docker exec -it papertrading-postgres psql -U papertrading_user -d papertrading

# Query utili
SELECT id, username, email FROM users;
SELECT id, name, cash_balance, currency FROM portfolios;
SELECT symbol, quantity, avg_cost, native_currency FROM positions;
SELECT * FROM trades ORDER BY executed_at DESC LIMIT 10;
```

### Migrazioni Alembic
```bash
cd backend

# Nuova migrazione
alembic revision --autogenerate -m "description"

# Applica migrazioni
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## ⚠️ REGOLE IMPORTANTI

1. **MAI dati MOCK** - Usare sempre dati reali dai provider
2. **INFORMARE prima di toccare il DB** - Specialmente DELETE/UPDATE
3. **SOLO docker-compose.yml** - Mai usare i file .DEPRECATED
4. **Single Currency Model** - `portfolio.cash_balance` è l'unica fonte di verità
5. **Conversione on-demand** - `convert()` per ogni operazione cross-currency

---

## 📋 TODO / Prossimi Passi

### Alta Priorità
- [ ] Implementare Limit Orders
- [ ] Stop Loss / Take Profit
- [ ] Portfolio Analytics avanzati
- [ ] ML Predictions integration

### Media Priorità
- [ ] WebSocket per prezzi real-time
- [ ] Alert sistema notifiche push
- [ ] Mobile responsive improvements

### Bassa Priorità
- [ ] Multi-user permissions
- [ ] API rate limiting dashboard
- [ ] Export dati CSV/PDF

---

## 🔄 Come Continuare lo Sviluppo

1. **Leggi questo file** per avere il contesto completo
2. **Avvia Docker** con `docker-compose --profile full --profile tools up -d`
3. **Verifica stato** con `docker ps`
4. **Accedi** a http://localhost con `administrator/admin123`
5. **Consulta** la documentazione in `docs/` per dettagli specifici

---

*Ultimo aggiornamento: 18 Dicembre 2025*
