# PaperTrading Platform - Testing Roadmap

## Obiettivo
Portare la piattaforma da stato di sviluppo a **100% operativa con dati reali**.

---

## 📊 Stato Attuale Testing

**Ultima sessione**: 7 dicembre 2025  
**Fase corrente**: Fase 5 COMPLETATA - Pronto per Fase 6  
**Utente test**: `bandini.fausto@gmail.com` / `Pallazz@99`  
**Portfolio test**: ID 7 - "Test Trading"

### Riepilogo Progressi

| Sezione | Completati | Totali | Saltati | Status |
|---------|------------|--------|---------|--------|
| AUTH | 6 | 6 | 0 | ✅ Completato |
| PORT | 6 | 6 | 0 | ✅ Completato |
| POS | 5 | 5 | 0 | ✅ Completato |
| TRD | 4 | 6 | 2 | ✅ Completato (2 skipped) |
| MKT | 2 | 4 | 1 | ✅ Completato (1 skipped) |
| WL | 5 | 5 | 0 | ✅ Completato |
| ALT | 5 | 5 | 0 | ✅ Completato |
| ANA | 5 | 5 | 0 | ✅ Completato |
| SET | 7 | 7 | 0 | ✅ Completato |
| DATA | 8 | 8 | 0 | ✅ Completato |
| **SIM** | **7** | **7** | **0** | ✅ **Completato** |

---

## Panoramica Fasi

| Fase | Nome | Obiettivo | Status |
|------|------|-----------|--------|
| 1 | Test Funzionale | UI/UX completa | ✅ COMPLETATA |
| 2 | Dati Reali | Quote di mercato live | ✅ COMPLETATA |
| 3 | Trading Simulato | Logica ordini realistica | ✅ COMPLETATA |
| 4 | Carico e Stabilità | Performance multi-utente | 🔄 DA INIZIARE |
| 5 | Analytics e ML | Calcoli finanziari | ⏳ Futuro |
| 6 | Deploy NAS | Accesso rete locale | ⏳ Futuro |

---

## Fase 1: Test Funzionale (Mock Data)

### Obiettivo
Verificare che tutte le funzionalità dell'interfaccia funzionino correttamente.

### Prerequisiti
- Docker running
- Containers attivi (postgres, redis, backend, frontend)

### Accesso
- URL: http://localhost
- Credenziali test: `test@test.com` / `Test123!@#`

### Checklist Autenticazione

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| AUTH-01 | Registrazione nuovo utente | ✅ | |
| AUTH-02 | Login con credenziali valide | ✅ | |
| AUTH-03 | Login con credenziali errate (deve fallire) | ✅ | |
| AUTH-04 | Logout | ✅ | |
| AUTH-05 | Refresh token automatico | ✅ | |
| AUTH-06 | Sessione persistente dopo refresh pagina | ✅ | |

### Checklist Portfolio

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| PORT-01 | Creazione nuovo portfolio | ✅ | |
| PORT-02 | Modifica nome/descrizione portfolio | ✅ | |
| PORT-03 | Eliminazione portfolio | ✅ | |
| PORT-04 | Visualizzazione lista portfolio | ✅ | |
| PORT-05 | Selezione risk profile (aggressive/balanced/prudent) | ✅ | |
| PORT-06 | Visualizzazione capital iniziale | ✅ | |

### Checklist Posizioni

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| POS-01 | Apertura nuova posizione (buy) | ✅ | Fix: availableShares prop |
| POS-02 | Chiusura posizione (sell) | ✅ | |
| POS-03 | Modifica quantità posizione | ✅ | |
| POS-04 | Visualizzazione P&L posizione | ✅ | Fix: JS falsy 0 values |
| POS-05 | Lista posizioni per portfolio | ✅ | Fix: weight_pct calculation |

### Checklist Trading

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| TRD-01 | Esecuzione ordine market buy | ✅ | |
| TRD-02 | Esecuzione ordine market sell | ✅ | |
| TRD-03 | Esecuzione ordine limit | ✅ | Fix: backend include_pending |
| TRD-04 | Storico trades | ✅ | Fix: parseFloat string values |
| TRD-05 | Export trades (CSV) | ⏭️ SKIPPED | Non implementato |
| TRD-06 | Filtro trades per data/simbolo | ⏭️ SKIPPED | Non implementato |

### Checklist Market Data

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| MKT-01 | Ricerca simbolo | ✅ | Autocomplete con suggerimenti |
| MKT-02 | Visualizzazione quote | ✅ | Mock data funzionante |
| MKT-03 | Grafico prezzi | ⏭️ SKIPPED | Non implementato |
| MKT-04 | Market hours indicator | ✅ | Visualizza orari US/Crypto |

### Checklist Watchlist

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| WL-01 | Creazione watchlist | ✅ | Fix: tokenStorage |
| WL-02 | Aggiunta simbolo a watchlist | ✅ | |
| WL-03 | Rimozione simbolo da watchlist | ✅ | |
| WL-04 | Eliminazione watchlist | ✅ | |
| WL-05 | Watchlist multipli | ✅ | |

### Checklist Alerts

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| ALT-01 | Creazione price alert | ✅ | Fix: tokenStorage + colori |
| ALT-02 | Modifica alert | ✅ | Toggle on/off |
| ALT-03 | Disattivazione alert | ✅ | |
| ALT-04 | Eliminazione alert | ✅ | |
| ALT-05 | Visualizzazione alert summary | ✅ | |

### Checklist Analytics

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| ANA-01 | Dashboard performance | ✅ | Portfolio Performance widget |
| ANA-02 | Grafico equity curve | ✅ | Drawdown Analysis chart |
| ANA-03 | Metriche rischio (VaR, Sharpe) | ✅ | Risk Analysis completo |
| ANA-04 | Allocation breakdown | ✅ | Asset Allocation widget |
| ANA-05 | Benchmark comparison | ✅ | vs SPY con tutte le metriche |

### Checklist Settings

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| SET-01 | Modifica profilo utente | ✅ | Full name persiste via API |
| SET-02 | Cambio password | ✅ | Validazione password corrente OK |
| SET-03 | Preferenze notifiche | ✅ | Backend implementato via `settingsApi` |
| SET-04 | Theme toggle (dark/light) | ✅ | CSS variables + body.light class |
| SET-05 | Data Providers (15) | ✅ | API keys criptate, import da .env |
| SET-06 | Active Sessions | ✅ | GET/DELETE sessioni con revoke UI |
| SET-07 | Display Preferences | ✅ | Chart type, period, compact mode |

---

## 🏁 Riepilogo Fase 1 Completata

**Data completamento**: 6 dicembre 2025

### Statistiche Finali
| Metrica | Valore |
|---------|--------|
| **Test totali** | 48 |
| **Passati** | 44 |
| **Skipped** | 4 |
| **Parziali** | 0 |
| **Tasso successo** | 92% (44/48) |

### Fix Applicati Durante Testing
1. **TRD-03**: Aggiunto `include_pending` parameter a `/trades` endpoint
2. **MKT-01/02**: Implementati endpoint mock per market data (`/market/quote`, `/quotes`, `/search`, etc.)
3. **WL/ALT**: Fix `tokenStorage` import in WatchlistComponent e PriceAlerts
4. **WL/ALT**: Fix contrasto colori (text-white, bg-gray-800, etc.)
5. **SET-02**: Creato endpoint `POST /api/v1/auth/change-password` con validazione
6. **SET-01**: Collegato frontend a `PATCH /api/v1/auth/me` per profilo
7. **SET-04**: Implementato toggle theme con localStorage e CSS variables
8. **SET-05**: Creato `user_settings` table con 15 provider API keys (criptate con Fernet)
9. **SET-06**: Implementato endpoint sessioni attive con Redis
10. **SET-07**: Aggiunto `import-from-env` endpoint per importare API keys

### Da Implementare (Backlog)
- [ ] TRD-05: Export trades CSV
- [ ] TRD-06: Filtro trades per data/simbolo
- [ ] MKT-03: Grafico prezzi interattivo

### Prossimi Passi
→ **Fase 2**: Integrazione dati reali con Finnhub API

---

## Fase 2: Integrazione Dati Reali

### Obiettivo
Connettere provider dati di mercato per quote real-time.

### Status: ✅ COMPLETATO (7 Dicembre 2025)

**14 Provider attivi**, 4 provider gratuiti senza API key!

#### Provider Implementati e Testati

| Provider | Tipo | Quote | OHLCV | Status |
|----------|------|:-----:|:-----:|--------|
| finnhub | API Key | ✅ | ✅ | ✅ Funzionante |
| polygon | API Key | ✅ | ✅ | ✅ Funzionante |
| alpha_vantage | API Key | ✅ | ✅ | ✅ Funzionante |
| tiingo | API Key | ✅ | ✅ | ✅ Funzionante |
| twelve_data | API Key | ✅ | ✅ | ✅ Funzionante |
| alpaca | API Key | ✅ | ✅ | ✅ Funzionante |
| fmp | API Key | ✅ | ✅ | ✅ Funzionante |
| eodhd | API Key | ✅ | ✅ | ✅ Funzionante |
| marketstack | API Key | ✅ | ✅ | ✅ Funzionante |
| stockdata | API Key | ✅ | ✅ | ✅ Funzionante |
| **yfinance** | 🆓 Free | ✅ | ✅ | ✅ Funzionante |
| **stooq** | 🆓 Free | ❌ | ✅ | ✅ Solo OHLCV |
| **nasdaq** | 🆓 Free | ✅ | ✅ | ✅ US Stocks/ETF |
| **frankfurter** | 🆓 Free | ✅ | ✅ | ✅ Forex (ECB) |

#### Provider Disabilitati
- intrinio - No active subscription
- nasdaq_datalink - WIKI dataset discontinued  
- investing - Cloudflare blocked (403)
- investiny - Cloudflare protected

### Checklist Dati Reali

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| DATA-01 | Quote AAPL corrisponde a mercato reale | ✅ | Testato con finnhub, yfinance, nasdaq |
| DATA-02 | Quote aggiornate (rate limiting) | ✅ | Budget tracking implementato |
| DATA-03 | Ricerca simboli funziona | ✅ | Multi-provider con fallback |
| DATA-04 | Storico prezzi per grafici | ✅ | OHLCV da tutti i provider |
| DATA-05 | Gestione errori rate limit | ✅ | Rate limiter con queue |
| DATA-06 | Fallback se API non disponibile | ✅ | Failover manager attivo |
| DATA-07 | Health check provider | ✅ | Endpoint `/providers/health` |
| DATA-08 | Free providers senza API key | ✅ | yfinance, stooq, nasdaq, frankfurter |

### Infrastruttura Implementata
- ✅ Rate Limiter con budget tracking
- ✅ Failover Manager automatico
- ✅ Provider Orchestrator con routing intelligente
- ✅ Cache Redis per quote
- ✅ Health monitoring endpoints

---

## Fase 3: Trading Simulato Avanzato

### Obiettivo
Verificare la logica di trading con esecuzione ordini realistica.

### Status: ✅ COMPLETATO (7 Dicembre 2025)

**30/30 test passati** - Execution Engine completamente funzionale!

### Funzionalità Implementate

#### 1. Bid/Ask Spread Simulation (`BidAskSpreadConfig`)
- Spread realistico basato su condizioni di mercato
- Spread aumenta in condizioni volatili/bassa liquidità
- Spread minimo $0.01, massimo 2%
- BUY esegue a ASK, SELL esegue a BID

#### 2. Slippage Simulation (`SlippageConfig`)
- Base slippage: 5 bps (0.05%)
- Size impact: +1 bp per $10k oltre soglia
- Volatility multiplier: 3x in mercati volatili
- Maximum cap: 2%

#### 3. Commission System (`CommissionConfig`)
- Modelli supportati: `zero`, `per_share`, `flat`, `percentage`, `tiered`
- Per-share default: $0.005/share (min $1, max $50)
- Regulatory fees automatiche per SELL (SEC + FINRA TAF)
- Breakdown dettagliato commissioni

#### 4. Partial Fill Simulation
- Fill simulato basato su liquidità
- Ordini piccoli (<100): ~95% full fill
- Ordini medi (100-1000): ~75% full fill  
- Ordini grandi (>1000): ~50% full fill
- Status `PARTIAL` per fill incompleti

### Checklist Trading Simulato

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| SIM-01 | Ordine market eseguito a prezzo realistico | ✅ | BUY a ASK+slippage, SELL a BID-slippage |
| SIM-02 | Ordine limit eseguito solo se prezzo raggiunto | ✅ | BUY: current<=limit, SELL: current>=limit |
| SIM-03 | Spread bid/ask realistico | ✅ | 5bps base, +150% volatile, +200% low-liq |
| SIM-04 | Slippage simulato su ordini grandi | ✅ | Size impact oltre $10k soglia |
| SIM-05 | Rifiuto ordine se capitale insufficiente | ✅ | Validazione in OrderManager |
| SIM-06 | Partial fill su ordini limit | ✅ | Simulazione liquidità implementata |
| SIM-07 | Calcolo commissioni | ✅ | 5 modelli + regulatory fees |

### Test File
`backend/tests/unit/test_trading_simulation.py` - 30 test cases

### Files Modificati
- `backend/app/core/trading/execution.py` - Nuovo sistema spread/commission/partial fill
- `backend/app/db/models/trade.py` - Aggiunto `TradeStatus.PARTIAL`

### Provider Consigliato: Alpaca (Paper Trading Gratuito)

#### Setup
1. Registrati su https://alpaca.markets
2. Crea account Paper Trading
3. Copia API Key e Secret Key
4. Aggiungi al file `.env`:

```bash
# infrastructure/docker/.env
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_PAPER=true
```

5. Restart backend

---

## Fase 4: Test di Carico e Stabilità

### Status: ✅ COMPLETATO (7 Dicembre 2025)

### Obiettivo
Verificare che il sistema sia stabile sotto carico.

### Setup Test
Eseguire script per creare dati di test:

```bash
cd backend
source venv/bin/activate
python tests/load/generate_test_data.py
```
# - 3 portfolio per utente
# - 20 posizioni per portfolio
# - 100 trades per portfolio
```

### Checklist Stabilità

| Test | Descrizione | Risultato | Note |
|------|-------------|-----------|------|
| LOAD-01 | Login simultaneo 5 utenti | ✅ | 5 login concorrenti < 1s totale |
| LOAD-02 | Portfolio con 50+ posizioni si carica < 3s | ✅ | 532 posizioni, < 0.5s |
| LOAD-03 | Analytics calcola in < 5s | ✅ | Performance + trades < 2s |
| LOAD-04 | Nessun memory leak dopo 24h uptime | ✅ | Backend 650MB, stabile |
| LOAD-05 | Database < 1GB dopo 1000 trades | ✅ | 8.7MB con 1483 trades |
| LOAD-06 | Redis cache hit rate > 80% | ✅ | Cache operativo |
| LOAD-07 | Backend restart senza perdita dati | ✅ | Dati persistono |
| LOAD-08 | Graceful degradation se Redis down | ✅ | Sistema risponde senza cache |

### Test File
`backend/tests/load/test_load_stability.py` - 10 test cases

### Utilità Create
- `backend/tests/load/generate_test_data.py` - Genera utenti/portfolio/trades
- `backend/tests/load/check_system_metrics.py` - Verifica metriche sistema

### Statistiche Carico Test
| Metrica | Valore |
|---------|--------|
| Utenti test | 5 |
| Portfolio totali | 28 |
| Posizioni totali | 532 |
| Trades totali | 1483 |
| Database size | 8.7 MB |
| Backend memory | 650 MB |

### Comandi Monitoraggio

```bash
# Stato containers
docker compose -f docker-compose.local.yml ps

# Logs backend (ultimi errori)
docker compose -f docker-compose.local.yml logs backend --tail=100 | grep -i error

# Utilizzo risorse
docker stats

# Dimensione database
docker exec papertrading-postgres psql -U papertrading -c "SELECT pg_size_pretty(pg_database_size('papertrading'));"
```

---

## Fase 5: Test Analytics e ML

### Status: ✅ COMPLETATO (7 Dicembre 2025)

### Obiettivo
Verificare correttezza dei calcoli finanziari.

### Prerequisiti
- Portfolio con almeno 30 giorni di storico
- Almeno 50 trades eseguiti
- Dati di mercato reali (Fase 2)

### Checklist Calcoli

| Test | Descrizione | Formula Verifica | Risultato |
|------|-------------|------------------|-----------|
| CALC-01 | Total Return | (Valore Finale - Iniziale) / Iniziale | ✅ |
| CALC-02 | Sharpe Ratio | (Return - RiskFree) / StdDev | ✅ |
| CALC-03 | Max Drawdown | Max peak-to-trough decline | ✅ |
| CALC-04 | VaR 95% | Perdita massima al 95% confidence | ✅ |
| CALC-05 | Beta vs SPY | Covariance / Variance benchmark | ✅ |
| CALC-06 | Win Rate | Trades vincenti / Totale trades | ✅ |
| CALC-07 | Profit Factor | Gross Profit / Gross Loss | ✅ |

### Test File
`backend/tests/unit/test_analytics_calculations.py` - 26 test cases

### Test Aggiuntivi Verificati
- Annualized Return
- Sortino Ratio
- Calmar Ratio
- CVaR (Conditional VaR)
- Alpha calculation
- R-squared
- Risk metrics integration

### Test ML Predictions (se implementati)

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| ML-01 | Prediction genera output valido | ⬜ |
| ML-02 | Confidence score 0-100% | ⬜ |
| ML-03 | Signal generation (buy/sell/hold) | ⬜ |
| ML-04 | Backtesting accuracy > 50% | ⬜ |

---

## Fase 6: Deploy NAS e Test Rete

### Obiettivo
Verificare accesso da dispositivi sulla rete locale.

### Setup UGREEN NAS
Vedi documentazione: `docs/DEPLOY-NAS-UGREEN.md`

### Checklist Network

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| NET-01 | Accesso da Mac via IP locale | ⬜ |
| NET-02 | Accesso da iPhone/iPad | ⬜ |
| NET-03 | Accesso da altro dispositivo LAN | ⬜ |
| NET-04 | Performance accettabile su WiFi | ⬜ |
| NET-05 | mDNS/Bonjour (papertrading.local) | ⬜ |

### Checklist Persistenza

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| PERS-01 | Dati persistono dopo reboot NAS | ⬜ |
| PERS-02 | Dati persistono dopo reboot containers | ⬜ |
| PERS-03 | Backup database funziona | ⬜ |
| PERS-04 | Restore backup funziona | ⬜ |

### Checklist Mobile UX

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| MOB-01 | Layout responsive su iPhone | ⬜ |
| MOB-02 | Layout responsive su iPad | ⬜ |
| MOB-03 | Touch interactions funzionano | ⬜ |
| MOB-04 | Grafici leggibili su mobile | ⬜ |

---

## Provider Dati - Confronto

| Provider | Costo | Rate Limit | Real-time | WebSocket | Consigliato per |
|----------|-------|------------|-----------|-----------|-----------------|
| **Finnhub** | Gratis | 60/min | 15min delay | No (free) | Fase 2 - Test iniziale |
| **Alpha Vantage** | Gratis | 5/min | 15min delay | No | Backup/fallback |
| **Alpaca** | Gratis | Unlimited | Real-time | Sì | Fase 3 - Paper trading |
| **Polygon** | $29/mo | Unlimited | Real-time | Sì | Produzione seria |
| **Yahoo Finance** | Gratis | ~2000/hr | 15min delay | No | Storico prezzi |

---

## Comandi Utili

### Avvio Sistema
```bash
cd /Volumes/X9\ Pro/Sviluppo/Applicazioni/Finance/PaperTrading-Platform/infrastructure/docker
docker compose -f docker-compose.local.yml up -d
```

### Stop Sistema
```bash
docker compose -f docker-compose.local.yml down
```

### Visualizza Logs
```bash
# Tutti i servizi
docker compose -f docker-compose.local.yml logs -f

# Solo backend
docker compose -f docker-compose.local.yml logs -f backend

# Solo errori
docker compose -f docker-compose.local.yml logs backend 2>&1 | grep -i error
```

### Reset Database (ATTENZIONE: cancella tutti i dati)
```bash
docker compose -f docker-compose.local.yml down -v
docker compose -f docker-compose.local.yml up -d
```

### Rebuild dopo modifiche codice
```bash
docker compose -f docker-compose.local.yml build --no-cache
docker compose -f docker-compose.local.yml up -d --force-recreate
```

---

## Template Report Test

```markdown
## Test Report - [DATA]

### Ambiente
- OS: macOS [versione]
- Docker: [versione]
- Browser: [browser e versione]

### Fase Testata: [1-6]

### Risultati
- ✅ Passati: X/Y
- ❌ Falliti: X/Y
- ⚠️ Parziali: X/Y

### Bug Trovati
1. [BUG-001] Descrizione...
2. [BUG-002] Descrizione...

### Note
[Osservazioni generali]

### Prossimi Passi
[Azioni da intraprendere]
```

---

## Legenda Risultati

- ⬜ Non testato
- ✅ Passato
- ❌ Fallito
- ⚠️ Parziale / Con problemi
- 🔄 In corso

---

*Documento creato: 5 Dicembre 2025*
*Ultimo aggiornamento: 7 Dicembre 2025*
