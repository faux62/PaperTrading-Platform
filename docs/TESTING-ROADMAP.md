# PaperTrading Platform - Testing Roadmap

## Obiettivo
Portare la piattaforma da stato di sviluppo a **100% operativa con dati reali**.

---

## Panoramica Fasi

| Fase | Nome | Obiettivo | Prerequisiti |
|------|------|-----------|--------------|
| 1 | Test Funzionale | UI/UX completa | Solo Docker |
| 2 | Dati Reali | Quote di mercato live | API Key (Finnhub) |
| 3 | Trading Simulato | Logica ordini realistica | API Key (Alpaca) |
| 4 | Carico e Stabilità | Performance multi-utente | Fase 1-3 complete |
| 5 | Analytics e ML | Calcoli finanziari | Storico dati |
| 6 | Deploy NAS | Accesso rete locale | Hardware NAS |

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

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| AUTH-01 | Registrazione nuovo utente | ⬜ |
| AUTH-02 | Login con credenziali valide | ⬜ |
| AUTH-03 | Login con credenziali errate (deve fallire) | ⬜ |
| AUTH-04 | Logout | ⬜ |
| AUTH-05 | Refresh token automatico | ⬜ |
| AUTH-06 | Sessione persistente dopo refresh pagina | ⬜ |

### Checklist Portfolio

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| PORT-01 | Creazione nuovo portfolio | ⬜ |
| PORT-02 | Modifica nome/descrizione portfolio | ⬜ |
| PORT-03 | Eliminazione portfolio | ⬜ |
| PORT-04 | Visualizzazione lista portfolio | ⬜ |
| PORT-05 | Selezione risk profile (aggressive/balanced/prudent) | ⬜ |
| PORT-06 | Visualizzazione capital iniziale | ⬜ |

### Checklist Posizioni

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| POS-01 | Apertura nuova posizione (buy) | ⬜ |
| POS-02 | Chiusura posizione (sell) | ⬜ |
| POS-03 | Modifica quantità posizione | ⬜ |
| POS-04 | Visualizzazione P&L posizione | ⬜ |
| POS-05 | Lista posizioni per portfolio | ⬜ |

### Checklist Trading

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| TRD-01 | Esecuzione ordine market buy | ⬜ |
| TRD-02 | Esecuzione ordine market sell | ⬜ |
| TRD-03 | Esecuzione ordine limit | ⬜ |
| TRD-04 | Storico trades | ⬜ |
| TRD-05 | Export trades (CSV) | ⬜ |
| TRD-06 | Filtro trades per data/simbolo | ⬜ |

### Checklist Market Data

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| MKT-01 | Ricerca simbolo | ⬜ |
| MKT-02 | Visualizzazione quote | ⬜ |
| MKT-03 | Grafico prezzi | ⬜ |
| MKT-04 | Market hours indicator | ⬜ |

### Checklist Watchlist

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| WL-01 | Creazione watchlist | ⬜ |
| WL-02 | Aggiunta simbolo a watchlist | ⬜ |
| WL-03 | Rimozione simbolo da watchlist | ⬜ |
| WL-04 | Eliminazione watchlist | ⬜ |
| WL-05 | Watchlist multipli | ⬜ |

### Checklist Alerts

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| ALT-01 | Creazione price alert | ⬜ |
| ALT-02 | Modifica alert | ⬜ |
| ALT-03 | Disattivazione alert | ⬜ |
| ALT-04 | Eliminazione alert | ⬜ |
| ALT-05 | Visualizzazione alert summary | ⬜ |

### Checklist Analytics

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| ANA-01 | Dashboard performance | ⬜ |
| ANA-02 | Grafico equity curve | ⬜ |
| ANA-03 | Metriche rischio (VaR, Sharpe) | ⬜ |
| ANA-04 | Allocation breakdown | ⬜ |
| ANA-05 | Benchmark comparison | ⬜ |

### Checklist Settings

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| SET-01 | Modifica profilo utente | ⬜ |
| SET-02 | Cambio password | ⬜ |
| SET-03 | Preferenze notifiche | ⬜ |
| SET-04 | Theme toggle (dark/light) | ⬜ |

---

## Fase 2: Integrazione Dati Reali

### Obiettivo
Connettere provider dati di mercato per quote real-time.

### Provider Consigliato: Finnhub (Gratuito)

#### Setup
1. Registrati su https://finnhub.io (gratuito)
2. Copia la API key dal dashboard
3. Crea file `.env` nella cartella `infrastructure/docker/`:

```bash
# infrastructure/docker/.env
FINNHUB_API_KEY=your_api_key_here
```

4. Restart backend:
```bash
cd infrastructure/docker
docker compose -f docker-compose.local.yml up -d backend --force-recreate
```

### Checklist Dati Reali

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| DATA-01 | Quote AAPL corrisponde a mercato reale | ⬜ |
| DATA-02 | Quote aggiornate ogni 15 secondi | ⬜ |
| DATA-03 | Ricerca simboli funziona | ⬜ |
| DATA-04 | Storico prezzi per grafici | ⬜ |
| DATA-05 | Gestione errori rate limit | ⬜ |
| DATA-06 | Fallback se API non disponibile | ⬜ |

### Limiti Finnhub (Piano Gratuito)
- 60 chiamate API / minuto
- Quote ritardate 15 minuti (mercato US)
- No WebSocket su piano free

---

## Fase 3: Trading Simulato Avanzato

### Obiettivo
Verificare la logica di trading con esecuzione ordini realistica.

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

### Checklist Trading Simulato

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| SIM-01 | Ordine market eseguito a prezzo realistico | ⬜ |
| SIM-02 | Ordine limit eseguito solo se prezzo raggiunto | ⬜ |
| SIM-03 | Spread bid/ask realistico | ⬜ |
| SIM-04 | Slippage simulato su ordini grandi | ⬜ |
| SIM-05 | Rifiuto ordine se capitale insufficiente | ⬜ |
| SIM-06 | Partial fill su ordini limit | ⬜ |
| SIM-07 | Calcolo commissioni | ⬜ |

---

## Fase 4: Test di Carico e Stabilità

### Obiettivo
Verificare che il sistema sia stabile sotto carico.

### Setup Test
Creare utenti e dati di test:

```bash
# Script per creare dati di test (da eseguire via API o script)
# - 5 utenti
# - 3 portfolio per utente
# - 20 posizioni per portfolio
# - 100 trades per portfolio
```

### Checklist Stabilità

| Test | Descrizione | Risultato |
|------|-------------|-----------|
| LOAD-01 | Login simultaneo 5 utenti | ⬜ |
| LOAD-02 | Portfolio con 50+ posizioni si carica < 3s | ⬜ |
| LOAD-03 | Analytics calcola in < 5s | ⬜ |
| LOAD-04 | Nessun memory leak dopo 24h uptime | ⬜ |
| LOAD-05 | Database < 1GB dopo 1000 trades | ⬜ |
| LOAD-06 | Redis cache hit rate > 80% | ⬜ |
| LOAD-07 | Backend restart senza perdita dati | ⬜ |
| LOAD-08 | Graceful degradation se Redis down | ⬜ |

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

### Obiettivo
Verificare correttezza dei calcoli finanziari.

### Prerequisiti
- Portfolio con almeno 30 giorni di storico
- Almeno 50 trades eseguiti
- Dati di mercato reali (Fase 2)

### Checklist Calcoli

| Test | Descrizione | Formula Verifica | Risultato |
|------|-------------|------------------|-----------|
| CALC-01 | Total Return | (Valore Finale - Iniziale) / Iniziale | ⬜ |
| CALC-02 | Sharpe Ratio | (Return - RiskFree) / StdDev | ⬜ |
| CALC-03 | Max Drawdown | Max peak-to-trough decline | ⬜ |
| CALC-04 | VaR 95% | Perdita massima al 95% confidence | ⬜ |
| CALC-05 | Beta vs SPY | Covariance / Variance benchmark | ⬜ |
| CALC-06 | Win Rate | Trades vincenti / Totale trades | ⬜ |
| CALC-07 | Profit Factor | Gross Profit / Gross Loss | ⬜ |

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
*Ultimo aggiornamento: 5 Dicembre 2025*
