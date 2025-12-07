# 📘 Specifiche Funzionali - PaperTrading Platform

**Versione:** 1.0  
**Data:** 7 Dicembre 2025  
**Autore:** Sistema

---

## Indice

1. [Panoramica Sistema](#1-panoramica-sistema)
2. [Modulo Autenticazione](#2-modulo-autenticazione)
3. [Modulo Portfolio](#3-modulo-portfolio)
4. [Modulo Trading](#4-modulo-trading)
5. [Modulo Market Data](#5-modulo-market-data)
6. [Modulo Watchlist](#6-modulo-watchlist)
7. [Modulo Alerts](#7-modulo-alerts)
8. [Modulo Analytics](#8-modulo-analytics)
9. [Modulo ML/AI](#9-modulo-mlai)
10. [Modulo Settings](#10-modulo-settings)
11. [Dashboard](#11-dashboard)

---

## 1. Panoramica Sistema

### 1.1 Descrizione
PaperTrading Platform è una piattaforma completa di paper trading (trading simulato) che permette di:
- Simulare operazioni di trading senza rischio di perdita reale
- Gestire portafogli virtuali con capitale simulato
- Analizzare performance e metriche di rischio
- Utilizzare predizioni ML per supporto decisionale
- Monitorare mercati globali in tempo reale

### 1.2 Utenti Target
- Trader principianti che vogliono imparare
- Trader esperti che testano nuove strategie
- Studenti di finanza
- Appassionati di investimenti

### 1.3 Mercati Supportati
- **US Markets:** NYSE, NASDAQ (azioni USA)
- **EU Markets:** Principali borse europee
- **Asia-Pacific:** Tokyo, Hong Kong, etc.
- **Crypto:** Bitcoin e principali criptovalute

---

## 2. Modulo Autenticazione

### 2.1 Registrazione Utente
**Descrizione:** Creazione nuovo account utente

**Campi richiesti:**
| Campo | Validazione |
|-------|-------------|
| Email | Formato email valido, univoco |
| Username | 3-50 caratteri, univoco |
| Password | Minimo 8 caratteri |
| Nome completo | Opzionale |

**Processo:**
1. Utente compila form di registrazione
2. Sistema valida unicità email/username
3. Password viene hashata con bcrypt
4. Account creato con stato "attivo"
5. Sistema genera JWT access + refresh token
6. Utente reindirizzato a Dashboard

### 2.2 Login
**Descrizione:** Accesso utente esistente

**Campi richiesti:**
- Email o Username
- Password

**Processo:**
1. Utente inserisce credenziali
2. Sistema verifica credenziali
3. Se valide: genera JWT tokens
4. Sessione registrata in Redis (IP, User-Agent)
5. Redirect a Dashboard

**Sicurezza:**
- Rate limiting su tentativi falliti
- Token blacklisting per logout

### 2.3 Logout
**Descrizione:** Disconnessione sicura

**Processo:**
1. Token corrente aggiunto a blacklist Redis
2. Sessione invalidata
3. Redirect a pagina login

### 2.4 Refresh Token
**Descrizione:** Rinnovo sessione senza re-login

- Access token: 30 minuti
- Refresh token: 7 giorni
- Refresh automatico prima scadenza

### 2.5 Cambio Password
**Requisiti:**
- Password corrente
- Nuova password (min 8 caratteri)
- Conferma nuova password

### 2.6 Gestione Profilo
**Dati modificabili:**
- Nome completo
- Valuta base preferita (USD, EUR, GBP, etc.)

---

## 3. Modulo Portfolio

### 3.1 Creazione Portfolio
**Descrizione:** Creazione nuovo portafoglio virtuale

**Parametri:**
| Campo | Descrizione | Default |
|-------|-------------|---------|
| Nome | Nome identificativo | Richiesto |
| Descrizione | Descrizione opzionale | - |
| Risk Profile | Profilo di rischio | balanced |
| Capitale Iniziale | $1,000 - $100,000,000 | $100,000 |
| Valuta | USD, EUR, GBP, etc. | USD |

### 3.2 Profili di Rischio
Il sistema offre 3 profili predefiniti:

#### Aggressive (Aggressivo)
- **Target:** Crescita massima, alta volatilità tollerata
- **Allocazione:**
  - Equity US: 40-70% (target 55%)
  - Equity EU: 10-25% (target 15%)
  - Equity Asia: 10-25% (target 15%)
  - Emerging Markets: 5-15% (target 10%)
  - Cash: 0-10%
- **Limiti posizione:**
  - Max singola posizione: 15%
  - Max settore: 40%
  - Min posizioni: 8
  - Max posizioni: 60
- **Metriche rischio:**
  - Max volatilità: 30%
  - Max drawdown: 35%
  - Target beta: 1.2

#### Balanced (Bilanciato)
- **Target:** Crescita moderata con controllo rischio
- **Allocazione:**
  - Equity US: 30-50% (target 40%)
  - Equity EU: 10-20% (target 15%)
  - Equity Asia: 5-15% (target 10%)
  - Fixed Income: 10-30% (target 20%)
  - Cash: 5-15% (target 10%)
- **Limiti posizione:**
  - Max singola posizione: 10%
  - Max settore: 30%
  - Min posizioni: 10
  - Max posizioni: 50
- **Metriche rischio:**
  - Max volatilità: 20%
  - Max drawdown: 20%
  - Target beta: 1.0

#### Prudent (Prudente)
- **Target:** Preservazione capitale, bassa volatilità
- **Allocazione:**
  - Equity US: 15-35% (target 25%)
  - Equity EU: 5-15% (target 10%)
  - Fixed Income: 30-50% (target 40%)
  - Cash: 10-30% (target 20%)
- **Limiti posizione:**
  - Max singola posizione: 5%
  - Max settore: 20%
  - Min posizioni: 15
  - Max posizioni: 40
- **Metriche rischio:**
  - Max volatilità: 10%
  - Max drawdown: 10%
  - Target beta: 0.5

### 3.3 Dashboard Portfolio
**Metriche visualizzate:**
- Valore totale portfolio
- Variazione giornaliera ($ e %)
- P&L non realizzato
- P&L realizzato
- Cash disponibile
- Buying power

### 3.4 Posizioni
**Per ogni posizione:**
| Dato | Descrizione |
|------|-------------|
| Simbolo | Ticker azione |
| Quantità | Numero azioni |
| Costo medio | Prezzo medio acquisto |
| Prezzo corrente | Quotazione real-time |
| Valore di mercato | Quantità × Prezzo |
| P&L non realizzato | Valore - Costo |
| P&L % | Percentuale guadagno/perdita |
| Peso % | Percentuale sul portfolio |

### 3.5 Allocazione Asset
**Vista grafico a torta:**
- Breakdown per settore
- Breakdown per asset class
- Breakdown per paese
- Confronto con target allocazione del risk profile

### 3.6 Performance Portfolio
**Metriche calcolate:**
- Total Return (%)
- Rendimento annualizzato
- Volatilità annualizzata
- Sharpe Ratio
- Sortino Ratio
- Max Drawdown
- Win Rate
- Profit Factor

### 3.7 Validazione Trade
Prima di ogni operazione, il sistema valida:
- Cash sufficiente per acquisti
- Quantità disponibile per vendite
- Rispetto limiti concentrazione (singola posizione, settore)
- Conformità al risk profile selezionato

### 3.8 Gestione Portfolio
**Operazioni disponibili:**
- Modifica nome/descrizione
- Cambio risk profile
- Archiviazione portfolio
- Eliminazione portfolio (irreversibile)

---

## 4. Modulo Trading

### 4.1 Tipi di Ordine Supportati

#### Market Order
- **Descrizione:** Esecuzione immediata al miglior prezzo disponibile
- **Uso:** Quando velocità è prioritaria rispetto al prezzo

#### Limit Order
- **Descrizione:** Esecuzione solo al prezzo specificato o migliore
- **Parametri:** Prezzo limite
- **Stato:** Pending fino a esecuzione o cancellazione

#### Stop Order
- **Descrizione:** Diventa market quando prezzo raggiunge stop
- **Parametri:** Prezzo stop trigger
- **Uso:** Protezione da perdite (stop-loss)

#### Stop-Limit Order
- **Descrizione:** Diventa limit quando prezzo raggiunge stop
- **Parametri:** Prezzo stop + Prezzo limite

### 4.2 Simulazione Esecuzione

Il sistema simula condizioni di mercato realistiche:

#### Spread Bid/Ask
- **Base spread:** 0.05% (5 bps)
- **Volatilità:** spread × 2.5
- **Bassa liquidità:** spread × 3.0
- **Alto volume:** spread × 0.5 (più stretto)
- **Max spread:** 2%

#### Slippage
- **Base:** 0.05% (5 bps)
- **Volatilità:** slippage × 3.0
- **Bassa liquidità:** slippage × 2.0
- **Impact ordini grandi:** +1 bp per ogni $10k oltre $10k
- **Max slippage:** 2%

#### Commissioni
**Modello per-share (default):**
- $0.005 per azione
- Minimo: $1.00 per ordine
- Massimo: $50.00 per ordine
- SEC Fee: $22.10 per milione
- FINRA TAF: $0.000119 per azione (max $5.95)

### 4.3 Flusso Creazione Ordine

```
┌─────────────────┐
│ Utente inserisce│
│ dettagli ordine │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Validazione:    │
│ - Cash/quantità │
│ - Risk limits   │
│ - Symbol valido │
└────────┬────────┘
         ▼
    ┌────┴────┐
    │ Valido? │
    └────┬────┘
    No   │   Sì
    │    ▼
    │  ┌─────────────────┐
    │  │ Tipo = MARKET?  │
    │  └────────┬────────┘
    │      Sì   │   No
    │      │    ▼
    │      │  ┌─────────────────┐
    │      │  │ Ordine PENDING  │
    │      │  │ (Limit/Stop)    │
    │      │  └─────────────────┘
    │      ▼
    │  ┌─────────────────┐
    │  │ Esecuzione:     │
    │  │ - Calcola spread│
    │  │ - Applica slip. │
    │  │ - Calcola comm. │
    │  └────────┬────────┘
    │           ▼
    │  ┌─────────────────┐
    │  │ Aggiorna:       │
    │  │ - Posizione     │
    │  │ - Cash balance  │
    │  │ - Trade history │
    │  └─────────────────┘
    ▼
┌─────────────────┐
│ Errore mostrato │
│ all'utente      │
└─────────────────┘
```

### 4.4 Storico Trade
**Filtri disponibili:**
- Periodo (data inizio/fine)
- Simbolo
- Tipo (Buy/Sell)
- Stato (Executed/Pending/Cancelled)

**Export CSV:**
- Colonne: ID, Data, Simbolo, Tipo, Ordine, Stato, Quantità, Prezzo, Prezzo Eseguito, Valore Totale, Commissione, P&L Realizzato, Note
- Filtri applicati all'export

### 4.5 Riepilogo Trading
**Statistiche periodo:**
- Totale trade
- Trade buy / sell
- Volume totale
- P&L realizzato
- Dimensione media trade
- Simboli più tradati

### 4.6 Calcolo P&L
**P&L Realizzato:**
- Calcolato su posizioni chiuse
- Metodo FIFO per costo

**P&L Non Realizzato:**
- Calcolato su posizioni aperte
- (Prezzo corrente - Costo medio) × Quantità

---

## 5. Modulo Market Data

### 5.1 Quote Real-time
**Dati forniti per ogni simbolo:**
| Campo | Descrizione |
|-------|-------------|
| Symbol | Ticker |
| Name | Nome azienda |
| Price | Ultimo prezzo |
| Change | Variazione assoluta |
| Change % | Variazione percentuale |
| Volume | Volume giornaliero |
| Bid | Prezzo bid |
| Ask | Prezzo ask |
| High | Massimo giornaliero |
| Low | Minimo giornaliero |
| Open | Prezzo apertura |
| Prev Close | Chiusura precedente |

### 5.2 Provider Dati
**14 provider integrati con failover automatico:**

| Provider | Tipo | API Key |
|----------|------|---------|
| Alpaca | Real-time (WS) | Sì |
| Polygon | Real-time | Sì |
| Finnhub | Real-time + WS | Sì |
| Twelve Data | Real-time | Sì |
| yfinance | Fallback | No |
| EODHD | Historical | Sì |
| Stooq | Historical | No |
| FMP | Fundamentals | Sì |
| Alpha Vantage | Historical | Sì |
| Tiingo | Real-time | Sì |
| MarketStack | Real-time | Sì |
| Nasdaq DataLink | Historical | Sì |
| StockData.org | Real-time | Sì |
| Intrinio | Real-time | Sì |

### 5.3 Dati Storici (OHLCV)
**Periodi supportati:**
- 1D (1 giorno)
- 1W (1 settimana)
- 1M (1 mese)
- 3M (3 mesi)
- 1Y (1 anno)

**Timeframe:**
- 1m, 5m, 15m, 1h, 1d

### 5.4 Ricerca Simboli
**Funzionalità:**
- Ricerca per simbolo (es. "AAPL")
- Ricerca per nome (es. "Apple")
- Risultati con: Symbol, Nome, Exchange, Settore

### 5.5 Grafico Prezzi Interattivo
**Caratteristiche:**
- Candlestick chart (TradingView Lightweight Charts)
- Volume bars
- Media mobile 20 giorni
- Crosshair con dati
- Selezione periodo (1D, 1W, 1M, 3M, 1Y)
- Supporto tema dark/light

### 5.6 Orari di Mercato
**Informazioni visualizzate:**
- US Markets: 9:30 AM - 4:00 PM ET
- Pre-market: 4:00 AM
- After-hours: fino 8:00 PM
- Crypto: 24/7

---

## 6. Modulo Watchlist

### 6.1 Gestione Watchlist
**Operazioni:**
- Creazione watchlist (nome + descrizione)
- Modifica watchlist
- Eliminazione watchlist
- Visualizzazione lista watchlist

### 6.2 Gestione Simboli
**Per ogni watchlist:**
- Aggiunta simboli
- Rimozione simboli
- Visualizzazione quote real-time per simboli

### 6.3 Vista Watchlist
**Per ogni simbolo nella lista:**
- Prezzo corrente
- Variazione giornaliera
- Variazione %
- Click per dettagli/trading

---

## 7. Modulo Alerts

### 7.1 Tipi di Alert
| Tipo | Trigger |
|------|---------|
| price_above | Prezzo supera soglia |
| price_below | Prezzo scende sotto soglia |
| percent_change | Variazione % supera soglia |
| volume_spike | Volume anomalo |

### 7.2 Creazione Alert
**Parametri:**
- Simbolo
- Tipo alert
- Valore target
- Nota (opzionale)
- Ricorrente (sì/no)
- Scadenza (opzionale)

### 7.3 Stati Alert
| Stato | Descrizione |
|-------|-------------|
| active | In monitoraggio |
| triggered | Condizione verificata |
| disabled | Disattivato manualmente |
| expired | Scaduto |

### 7.4 Gestione Alert
- Lista alert con filtri (stato, simbolo)
- Attivazione/disattivazione
- Modifica parametri
- Eliminazione
- Riepilogo per stato

---

## 8. Modulo Analytics

### 8.1 Performance Analytics

#### Metriche Base
| Metrica | Descrizione | Formula |
|---------|-------------|---------|
| Total Return | Rendimento totale | (Valore finale - Iniziale) / Iniziale |
| Annualized Return | Rendimento annualizzato | (1 + Total)^(365/giorni) - 1 |
| Volatility | Volatilità annualizzata | StdDev(rendimenti) × √252 |

#### Metriche Risk-Adjusted
| Metrica | Descrizione | Formula |
|---------|-------------|---------|
| Sharpe Ratio | Rendimento per unità di rischio | (Return - Rf) / Volatility |
| Sortino Ratio | Sharpe con solo downside risk | (Return - Rf) / Downside Dev |
| Calmar Ratio | Return / Max Drawdown | Ann. Return / Max DD |

#### Win Rate & Profit Factor
| Metrica | Descrizione |
|---------|-------------|
| Win Rate | % trade in profitto |
| Profit Factor | Gross Profit / Gross Loss |

### 8.2 Risk Metrics

#### Value at Risk (VaR)
| Metrica | Descrizione |
|---------|-------------|
| VaR 95% | Perdita max con 95% confidenza |
| VaR 99% | Perdita max con 99% confidenza |
| CVaR (Expected Shortfall) | Media perdite oltre VaR |

**Metodi calcolo:** Historical, Parametric

#### Metriche vs Benchmark
| Metrica | Descrizione |
|---------|-------------|
| Beta | Sensibilità al mercato |
| Alpha | Rendimento in eccesso risk-adjusted |
| R-squared | Correlazione con benchmark |
| Tracking Error | Deviazione dal benchmark |
| Information Ratio | Alpha / Tracking Error |

#### Altre Metriche
| Metrica | Descrizione |
|---------|-------------|
| Skewness | Asimmetria distribuzione |
| Kurtosis | "Code" distribuzione |
| Up Capture | Performance in mercati rialzisti |
| Down Capture | Performance in mercati ribassisti |

### 8.3 Drawdown Analysis
**Metriche:**
- Drawdown corrente
- Max Drawdown storico
- Data inizio/fine max drawdown
- Data recovery
- Durata max drawdown (giorni)

### 8.4 Benchmark Comparison
**Benchmark disponibili:**
- SPY (S&P 500)
- QQQ (NASDAQ 100)
- Altri ETF configurabili

**Confronti:**
- Grafico performance sovrapposto
- Tabella metriche comparative
- Excess return
- Tracking error

### 8.5 Rolling Metrics
**Metriche su finestra mobile:**
- Rendimenti rolling (30, 60, 90 giorni)
- Volatilità rolling
- Sharpe rolling

### 8.6 Grafici Disponibili
| Grafico | Descrizione |
|---------|-------------|
| Performance Chart | Equity curve vs benchmark |
| Allocation Chart | Torta allocazione asset |
| Drawdown Chart | Storico drawdown |
| Risk Chart | VaR/CVaR nel tempo |

### 8.7 Periodi Analisi
- 1 settimana
- 1 mese
- 3 mesi
- 6 mesi
- 1 anno
- YTD (da inizio anno)
- All (tutto lo storico)

---

## 9. Modulo ML/AI

### 9.1 Predizioni

#### Tipi di Predizione
| Tipo | Output | Descrizione |
|------|--------|-------------|
| price_direction | up/down | Direzione prezzo |
| trend | bullish/bearish/neutral | Trend corrente |
| volatility | low/medium/high | Previsione volatilità |
| risk | 1-10 | Livello rischio |

#### Input Features
Il sistema utilizza indicatori tecnici calcolati automaticamente:
- RSI (14 periodi)
- MACD (12, 26, 9)
- Bollinger Bands
- Volume ratio
- Momentum
- Moving averages (SMA, EMA)

### 9.2 Segnali Trading

#### Tipi Segnale
| Segnale | Descrizione |
|---------|-------------|
| STRONG_BUY | Forte raccomandazione acquisto |
| BUY | Raccomandazione acquisto |
| HOLD | Mantenere posizione |
| SELL | Raccomandazione vendita |
| STRONG_SELL | Forte raccomandazione vendita |

#### Attributi Segnale
- **Strength:** 0-1 (forza del segnale)
- **Confidence:** 0-1 (affidabilità)
- **Price Target:** Target prezzo (se disponibile)
- **Stop Loss:** Livello stop loss suggerito
- **Take Profit:** Livello take profit suggerito

### 9.3 Aggregazione Segnali
Combina segnali da fonti multiple:
- Consensus signal
- Agreement ratio (% modelli concordi)
- Forza aggregata
- Azione raccomandata
- Suggerimento dimensione posizione

### 9.4 Portfolio Optimization

#### Obiettivi Ottimizzazione
| Obiettivo | Descrizione |
|-----------|-------------|
| max_sharpe | Massimizza Sharpe Ratio |
| min_volatility | Minimizza volatilità |
| max_return | Massimizza rendimento |
| risk_parity | Equalizza contributo rischio |

#### Vincoli
- Peso minimo/massimo per asset
- Long only (opzionale)
- Target return
- Target volatility

#### Output
- Pesi ottimali per asset
- Expected return
- Volatility attesa
- Sharpe Ratio risultante
- Contributo rischio per asset

### 9.5 Risk Parity Optimization
Allocazione basata su contributo rischio uguale:
- Risk contribution per asset
- Pesi calcolati iterativamente
- Diversificazione automatica

### 9.6 Rebalancing Calculator
**Input:**
- Pesi correnti
- Pesi target
- Prezzi correnti
- Valore portfolio
- Valore minimo trade

**Output:**
- Trade da eseguire
- Quantità per simbolo
- Stima commissioni

### 9.7 Backtesting
**Parametri:**
- Simbolo/i
- Strategia (trend following, mean reversion, etc.)
- Periodo storico
- Capitale iniziale
- Costi transazione

**Output:**
- Equity curve
- Statistiche performance
- Trade log
- Confronto buy & hold

### 9.8 Model Health Monitoring
Per ogni modello ML:
- Stato (healthy/degraded/failed)
- Accuracy corrente
- Data ultimo training
- Drift detection
- Latenza predizioni

---

## 10. Modulo Settings

### 10.1 Impostazioni Profilo
| Campo | Descrizione |
|-------|-------------|
| Username | Non modificabile |
| Email | Non modificabile |
| Nome | Nome completo |
| Valuta base | Per aggregazione portfolio |

### 10.2 Impostazioni Display
| Opzione | Valori | Default |
|---------|--------|---------|
| Tema | dark / light | dark |
| Modalità compatta | on / off | off |
| Mostra % change | on / off | on |
| Periodo grafico default | 1D/1W/1M/3M/1Y | 1M |
| Tipo grafico | candlestick / line | candlestick |

### 10.3 Impostazioni Notifiche
| Notifica | Descrizione | Default |
|----------|-------------|---------|
| Email | Notifiche via email | On |
| Push | Notifiche push browser | On |
| Trade execution | Alert esecuzione ordini | On |
| Price alerts | Alert prezzi | On |
| Portfolio updates | Aggiornamenti portfolio | On |
| Market news | News di mercato | Off |

### 10.4 API Keys Data Provider
**Provider configurabili:**
- Alpaca (key + secret)
- Polygon
- Finnhub
- Twelve Data
- EODHD
- FMP
- Alpha Vantage
- Nasdaq DataLink
- Tiingo
- MarketStack
- StockData.org
- Intrinio

**Funzionalità:**
- Inserimento/modifica API key
- Test connessione
- Visualizzazione stato (configurato/non configurato)
- Mascheramento key (****xxxx)
- Rimozione key

### 10.5 Sicurezza
- Cambio password
- Data ultimo cambio password
- (Futuro: 2FA)

---

## 11. Dashboard

### 11.1 Overview
La dashboard principale mostra:

#### KPI Cards
| Card | Descrizione |
|------|-------------|
| Total Value | Valore totale tutti i portfolio |
| Daily Change | Variazione giornaliera |
| Unrealized P&L | Profitto/perdita non realizzato |
| Cash Available | Liquidità disponibile |

#### Top Positions
Lista delle 5 posizioni principali con:
- Simbolo e nome
- Valore
- Variazione %
- Quantità

#### Recent Trades
Ultimi 4 trade eseguiti con:
- Simbolo
- Tipo (Buy/Sell)
- Quantità
- Prezzo
- Tempo

#### Market Overview
Indici principali:
- S&P 500
- NASDAQ
- DOW
- BTC/USD

---

## 12. Navigazione Applicazione

### 12.1 Menu Principale
```
📊 Dashboard     - Panoramica generale
💼 Portfolio     - Gestione portafogli
📈 Trading       - Esecuzione ordini
🌍 Markets       - Dati di mercato
📉 Analytics     - Analisi performance
🤖 ML Insights   - Predizioni AI
⚙️ Settings      - Impostazioni
```

### 12.2 Flussi Utente Principali

#### Flusso Trading
```
Markets → Cerca simbolo → Visualizza grafico → 
Trading → Inserisci ordine → Conferma → 
Portfolio → Verifica posizione
```

#### Flusso Analisi
```
Portfolio → Seleziona portfolio → 
Analytics → Scegli periodo → 
Visualizza metriche/grafici → 
Export report
```

#### Flusso ML
```
ML Insights → Seleziona simbolo →
Visualizza predizioni → Genera segnali →
Trading → Esegui raccomandazione
```

---

## 13. Limitazioni Note

### 13.1 Funzionalità Non Disponibili
- Trading reale (solo paper trading)
- Margin trading
- Short selling
- Options/Futures
- Trading automatico (solo segnali manuali)

### 13.2 Limiti Tecnici
- Rate limits provider dati
- Delay quote (dipende da provider)
- Predizioni ML indicative (non garanzia)

---

## 14. Glossario

| Termine | Definizione |
|---------|-------------|
| Paper Trading | Trading simulato senza denaro reale |
| P&L | Profit & Loss (profitto e perdita) |
| Drawdown | Calo dal picco massimo |
| Sharpe Ratio | Rendimento risk-adjusted |
| VaR | Value at Risk |
| Slippage | Differenza tra prezzo atteso ed eseguito |
| Spread | Differenza bid-ask |
| OHLCV | Open, High, Low, Close, Volume |
