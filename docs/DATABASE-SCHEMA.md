# PaperTrading Platform - Database Schema

## Data: 18 Dicembre 2025

---

## 📊 Overview

Il database PostgreSQL 16 contiene **14 tabelle** e **13 tipi ENUM** personalizzati.

### Tabelle
| Tabella | Descrizione |
|---------|-------------|
| `users` | Utenti e autenticazione |
| `portfolios` | Portfolio con cash_balance e valuta |
| `positions` | Posizioni aperte |
| `trades` | Storico operazioni |
| `watchlists` | Liste di titoli da monitorare |
| `watchlist_symbols` | Simboli nelle watchlist |
| `alerts` | Alert sui prezzi |
| `user_settings` | Impostazioni utente e API keys |
| `fx_transactions` | Transazioni forex |
| `market_universe` | Universo simboli globale |
| `bot_signals` | Segnali generati dal bot |
| `bot_reports` | Report periodici del bot |
| `price_bars` | Dati OHLCV storici |
| `exchange_rates` | Tassi di cambio FX cached |

> ⚠️ **NOTA**: La tabella `cash_balances` è stata **RIMOSSA** il 18/12/2025.
> Usare `portfolios.cash_balance` come unica fonte di verità per il cash.

---

## 🔑 ENUM Types

### `riskprofile`
| Valore | Descrizione |
|--------|-------------|
| `AGGRESSIVE` | Profilo aggressivo |
| `BALANCED` | Profilo bilanciato |
| `PRUDENT` | Profilo prudente |

### `tradetype`
| Valore | Descrizione |
|--------|-------------|
| `BUY` | Acquisto |
| `SELL` | Vendita |

### `ordertype`
| Valore | Descrizione |
|--------|-------------|
| `MARKET` | Ordine a mercato |
| `LIMIT` | Ordine limite |
| `STOP` | Ordine stop |
| `STOP_LIMIT` | Ordine stop-limit |

### `tradestatus`
| Valore | Descrizione |
|--------|-------------|
| `PENDING` | In attesa |
| `EXECUTED` | Eseguito |
| `PARTIAL` | Parzialmente eseguito |
| `CANCELLED` | Cancellato |
| `FAILED` | Fallito |

### `alerttype`
| Valore | Descrizione |
|--------|-------------|
| `PRICE_ABOVE` | Prezzo sopra target |
| `PRICE_BELOW` | Prezzo sotto target |
| `PERCENT_CHANGE_UP` | Variazione % positiva |
| `PERCENT_CHANGE_DOWN` | Variazione % negativa |

### `alertstatus`
| Valore | Descrizione |
|--------|-------------|
| `ACTIVE` | Attivo |
| `TRIGGERED` | Scattato |
| `EXPIRED` | Scaduto |
| `DISABLED` | Disabilitato |

### `assettype`
| Valore | Descrizione |
|--------|-------------|
| `STOCK` | Azione |
| `ETF` | Exchange-Traded Fund |
| `INDEX` | Indice |
| `ADR` | American Depositary Receipt |

### `marketregion`
| Valore | Descrizione |
|--------|-------------|
| `US` | Stati Uniti |
| `UK` | Regno Unito |
| `EU` | Europa |
| `ASIA` | Asia |
| `GLOBAL` | Globale |

### `timeframe`
| Valore | Descrizione |
|--------|-------------|
| `M1` | 1 minuto |
| `M5` | 5 minuti |
| `M15` | 15 minuti |
| `M30` | 30 minuti |
| `H1` | 1 ora |
| `H4` | 4 ore |
| `D1` | 1 giorno |
| `W1` | 1 settimana |

### `signaltype`
| Valore | Descrizione |
|--------|-------------|
| `TRADE_SUGGESTION` | Suggerimento trade |
| `POSITION_ALERT` | Alert posizione |
| `RISK_WARNING` | Warning rischio |
| `MARKET_ALERT` | Alert mercato |
| `PRICE_LEVEL` | Livello prezzo |
| `VOLUME_SPIKE` | Spike volume |
| `ML_PREDICTION` | Predizione ML |
| `NEWS_ALERT` | Alert news |
| `REBALANCE_SUGGESTION` | Suggerimento ribilanciamento |
| `TRAILING_STOP` | Trailing stop |

### `signalpriority`
| Valore | Descrizione |
|--------|-------------|
| `LOW` | Bassa |
| `MEDIUM` | Media |
| `HIGH` | Alta |
| `URGENT` | Urgente |

### `signalstatus`
| Valore | Descrizione |
|--------|-------------|
| `PENDING` | In attesa |
| `ACCEPTED` | Accettato |
| `IGNORED` | Ignorato |
| `EXPIRED` | Scaduto |
| `EXECUTED` | Eseguito |

### `signaldirection`
| Valore | Descrizione |
|--------|-------------|
| `LONG` | Long (acquisto) |
| `SHORT` | Short (vendita) |
| `CLOSE` | Chiusura posizione |
| `REDUCE` | Riduzione posizione |
| `HOLD` | Mantieni |

---

## 📋 Tracciati Record Dettagliati

---

### 👤 USERS

Gestisce utenti e autenticazione.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `email` | VARCHAR(255) | NOT NULL | - | Email utente (indexed) |
| `username` | VARCHAR(100) | NOT NULL | - | Username univoco |
| `hashed_password` | VARCHAR(255) | NOT NULL | - | Password hash bcrypt |
| `full_name` | VARCHAR(255) | NULL | - | Nome completo |
| `is_active` | BOOLEAN | NULL | - | Utente attivo |
| `is_superuser` | BOOLEAN | NULL | - | Privilegi admin |
| `base_currency` | VARCHAR(3) | NOT NULL | - | Valuta base utente |
| `created_at` | TIMESTAMP | NULL | - | Data creazione |
| `updated_at` | TIMESTAMP | NULL | - | Data ultimo aggiornamento |
| `last_login` | TIMESTAMP | NULL | - | Ultimo login |

**Indici:**
- `users_pkey` - PRIMARY KEY (id)
- `ix_users_email` - INDEX (email)
- `ix_users_username` - UNIQUE INDEX (username)

**Referenze FK:**
- `portfolios`, `watchlists`, `alerts`, `user_settings`, `bot_signals`, `bot_reports`

---

### 💼 PORTFOLIOS

Portfolio utente con cash balance e valuta. **`cash_balance` è l'UNICA fonte di verità per il cash**.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `user_id` | INTEGER | NOT NULL | - | FK → users.id |
| `name` | VARCHAR(255) | NOT NULL | - | Nome portfolio |
| `description` | VARCHAR(1000) | NULL | - | Descrizione |
| `risk_profile` | ENUM riskprofile | NULL | - | Profilo rischio |
| `strategy_period_weeks` | INTEGER | NOT NULL | - | Periodo strategia |
| `initial_capital` | NUMERIC(15,2) | NULL | - | Capitale iniziale |
| `cash_balance` | NUMERIC(15,2) | NULL | - | **💰 CASH DISPONIBILE** |
| `currency` | VARCHAR(3) | NULL | - | Valuta portfolio (EUR/USD/GBP/CHF) |
| `is_active` | BOOLEAN | NOT NULL | - | Portfolio attivo |
| `created_at` | TIMESTAMP | NULL | - | Data creazione |
| `updated_at` | TIMESTAMP | NULL | - | Data aggiornamento |

**Indici:**
- `portfolios_pkey` - PRIMARY KEY (id)
- `uq_portfolios_user_name` - UNIQUE (user_id, name)

**Constraints:**
- `ck_portfolios_initial_capital_min` - CHECK (initial_capital >= 100)
- `portfolios_user_id_fkey` - FK → users(id) ON DELETE CASCADE

**Referenze FK:**
- `positions`, `trades`, `fx_transactions`, `bot_signals`

---

### 📈 POSITIONS

Posizioni aperte con supporto multi-currency.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `portfolio_id` | INTEGER | NOT NULL | - | FK → portfolios.id |
| `symbol` | VARCHAR(20) | NOT NULL | - | Simbolo titolo (indexed) |
| `exchange` | VARCHAR(20) | NULL | - | Exchange (NYSE, NASDAQ, etc.) |
| `native_currency` | VARCHAR(3) | NOT NULL | - | **Valuta NATIVA del titolo** |
| `quantity` | NUMERIC(15,4) | NULL | - | Quantità posseduta |
| `avg_cost` | NUMERIC(15,4) | NULL | - | **Costo medio in valuta NATIVA** |
| `current_price` | NUMERIC(15,4) | NULL | - | **Prezzo corrente in valuta NATIVA** |
| `market_value` | NUMERIC(15,2) | NULL | - | **Valore di mercato in valuta PORTFOLIO** |
| `unrealized_pnl` | NUMERIC(15,2) | NULL | - | **P&L non realizzato in valuta PORTFOLIO** |
| `unrealized_pnl_percent` | NUMERIC(8,4) | NULL | - | P&L % |
| `opened_at` | TIMESTAMP | NULL | - | Data apertura |
| `updated_at` | TIMESTAMP | NULL | - | Data aggiornamento |

> ⚠️ **NOTA**: I campi `avg_cost_portfolio` e `entry_exchange_rate` sono stati **RIMOSSI** il 18/12/2025.
> Con l'Approccio B (FX dinamico), questi valori vengono calcolati on-demand usando i tassi dalla tabella `exchange_rates`.

**Indici:**
- `positions_pkey` - PRIMARY KEY (id)
- `ix_positions_symbol` - INDEX (symbol)

**Constraints:**
- `positions_portfolio_id_fkey` - FK → portfolios(id) ON DELETE CASCADE

---

### 📊 TRADES

Storico di tutte le operazioni eseguite.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `portfolio_id` | INTEGER | NOT NULL | - | FK → portfolios.id |
| `symbol` | VARCHAR(20) | NOT NULL | - | Simbolo titolo (indexed) |
| `exchange` | VARCHAR(20) | NULL | - | Exchange |
| `native_currency` | VARCHAR(3) | NOT NULL | - | **Valuta NATIVA del titolo** |
| `exchange_rate` | NUMERIC(15,6) | NULL | - | **Tasso cambio usato** |
| `trade_type` | ENUM tradetype | NOT NULL | - | BUY / SELL |
| `order_type` | ENUM ordertype | NULL | - | MARKET / LIMIT / STOP / STOP_LIMIT |
| `status` | ENUM tradestatus | NULL | - | Stato ordine |
| `quantity` | NUMERIC(15,4) | NOT NULL | - | Quantità richiesta |
| `price` | NUMERIC(15,4) | NULL | - | **Prezzo limite/stop in valuta NATIVA** |
| `executed_price` | NUMERIC(15,4) | NULL | - | **Prezzo eseguito in valuta NATIVA** |
| `executed_quantity` | NUMERIC(15,4) | NULL | - | Quantità eseguita |
| `total_value` | NUMERIC(15,2) | NULL | - | **Valore totale in valuta NATIVA** |
| `commission` | NUMERIC(10,2) | NULL | - | **Commissioni in valuta NATIVA** |
| `realized_pnl` | NUMERIC(15,2) | NULL | - | **P&L realizzato in valuta NATIVA** |
| `created_at` | TIMESTAMP | NULL | - | Data creazione ordine |
| `executed_at` | TIMESTAMP | NULL | - | Data esecuzione |
| `notes` | VARCHAR(500) | NULL | - | Note |

**Indici:**
- `trades_pkey` - PRIMARY KEY (id)
- `ix_trades_symbol` - INDEX (symbol)

**Constraints:**
- `trades_portfolio_id_fkey` - FK → portfolios(id) ON DELETE CASCADE

**Referenze FK:**
- `bot_signals` (resulting_trade_id)

---

### 👁️ WATCHLISTS

Liste di titoli da monitorare.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `user_id` | INTEGER | NOT NULL | - | FK → users.id |
| `name` | VARCHAR(255) | NOT NULL | - | Nome watchlist |
| `description` | VARCHAR(500) | NULL | - | Descrizione |
| `created_at` | TIMESTAMP | NULL | - | Data creazione |
| `updated_at` | TIMESTAMP | NULL | - | Data aggiornamento |

**Constraints:**
- `watchlists_user_id_fkey` - FK → users(id) ON DELETE CASCADE

---

### 🔗 WATCHLIST_SYMBOLS

Simboli associati alle watchlist (tabella di relazione).

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `watchlist_id` | INTEGER | NULL | - | FK → watchlists.id |
| `symbol` | VARCHAR(20) | NULL | - | Simbolo titolo |
| `added_at` | TIMESTAMP | NULL | - | Data aggiunta |

**Constraints:**
- `watchlist_symbols_watchlist_id_fkey` - FK → watchlists(id) ON DELETE CASCADE

---

### 🔔 ALERTS

Alert sui prezzi dei titoli.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `user_id` | INTEGER | NOT NULL | - | FK → users.id |
| `symbol` | VARCHAR(20) | NOT NULL | - | Simbolo titolo (indexed) |
| `alert_type` | ENUM alerttype | NOT NULL | - | Tipo alert |
| `target_value` | DOUBLE PRECISION | NOT NULL | - | Valore target |
| `status` | ENUM alertstatus | NOT NULL | - | Stato alert |
| `is_recurring` | BOOLEAN | NULL | - | Alert ricorrente |
| `triggered_at` | TIMESTAMP | NULL | - | Data attivazione |
| `triggered_price` | DOUBLE PRECISION | NULL | - | Prezzo attivazione |
| `note` | VARCHAR(500) | NULL | - | Nota |
| `expires_at` | TIMESTAMP | NULL | - | Data scadenza |
| `created_at` | TIMESTAMP | NULL | - | Data creazione |
| `updated_at` | TIMESTAMP | NULL | - | Data aggiornamento |

**Constraints:**
- `alerts_user_id_fkey` - FK → users(id) ON DELETE CASCADE

---

### ⚙️ USER_SETTINGS

Impostazioni utente e chiavi API per data provider.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `user_id` | INTEGER | NOT NULL | - | FK → users.id (UNIQUE) |
| **API Keys** | | | | |
| `api_key_alpaca` | TEXT | NULL | - | Alpaca API key |
| `api_key_alpaca_secret` | TEXT | NULL | - | Alpaca secret |
| `api_key_polygon` | TEXT | NULL | - | Polygon API key |
| `api_key_finnhub` | TEXT | NULL | - | Finnhub API key |
| `api_key_twelvedata` | TEXT | NULL | - | Twelve Data API key |
| `api_key_eodhd` | TEXT | NULL | - | EODHD API key |
| `api_key_fmp` | TEXT | NULL | - | Financial Modeling Prep key |
| `api_key_alphavantage` | TEXT | NULL | - | Alpha Vantage API key |
| `api_key_nasdaq` | TEXT | NULL | - | NASDAQ API key |
| `api_key_tiingo` | TEXT | NULL | - | Tiingo API key |
| `api_key_marketstack` | TEXT | NULL | - | Marketstack API key |
| `api_key_stockdata` | TEXT | NULL | - | Stock Data API key |
| `api_key_intrinio` | TEXT | NULL | - | Intrinio API key |
| `api_key_yahoo_old` | TEXT | NULL | - | Yahoo Finance (old) |
| `api_key_yfinance` | TEXT | NULL | - | yfinance |
| `api_key_stooq` | TEXT | NULL | - | Stooq API key |
| `api_key_investingcom` | TEXT | NULL | - | Investing.com API key |
| **Preferenze UI** | | | | |
| `theme` | VARCHAR(20) | NULL | - | Tema (light/dark) |
| `display_compact_mode` | BOOLEAN | NULL | - | Modalità compatta |
| `display_show_percent_change` | BOOLEAN | NULL | - | Mostra variazioni % |
| `display_default_chart_period` | VARCHAR(10) | NULL | - | Periodo default grafici |
| `display_chart_type` | VARCHAR(20) | NULL | - | Tipo grafico |
| **Notifiche** | | | | |
| `notifications_email` | BOOLEAN | NULL | - | Notifiche email |
| `notifications_push` | BOOLEAN | NULL | - | Notifiche push |
| `notifications_trade_execution` | BOOLEAN | NULL | - | Notifiche esecuzione |
| `notifications_price_alerts` | BOOLEAN | NULL | - | Notifiche alert prezzo |
| `notifications_portfolio_updates` | BOOLEAN | NULL | - | Notifiche portfolio |
| `notifications_market_news` | BOOLEAN | NULL | - | Notifiche news |
| **Timestamps** | | | | |
| `password_changed_at` | TIMESTAMP | NULL | - | Ultimo cambio password |
| `created_at` | TIMESTAMP | NULL | - | Data creazione |
| `updated_at` | TIMESTAMP | NULL | - | Data aggiornamento |

**Constraints:**
- `ix_user_settings_user_id` - UNIQUE (user_id)
- `user_settings_user_id_fkey` - FK → users(id) ON DELETE CASCADE

---

### 💱 FX_TRANSACTIONS

Storico transazioni forex.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `portfolio_id` | INTEGER | NOT NULL | - | FK → portfolios.id |
| `from_currency` | VARCHAR(3) | NOT NULL | - | Valuta origine |
| `to_currency` | VARCHAR(3) | NOT NULL | - | Valuta destinazione |
| `from_amount` | NUMERIC(15,2) | NOT NULL | - | Importo origine |
| `to_amount` | NUMERIC(15,2) | NOT NULL | - | Importo destinazione |
| `exchange_rate` | NUMERIC(15,6) | NOT NULL | - | Tasso cambio |
| `executed_at` | TIMESTAMP | NULL | - | Data esecuzione |

**Constraints:**
- `fx_transactions_portfolio_id_fkey` - FK → portfolios(id) ON DELETE CASCADE

---

### 🌍 MARKET_UNIVERSE

Universo dei simboli tradabili (623 simboli globali).

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `symbol` | VARCHAR(20) | NOT NULL | - | Simbolo (UNIQUE) |
| `name` | VARCHAR(255) | NULL | - | Nome azienda |
| `asset_type` | ENUM assettype | NULL | - | Tipo asset |
| `region` | ENUM marketregion | NOT NULL | - | Regione mercato |
| `exchange` | VARCHAR(20) | NULL | - | Exchange |
| `currency` | VARCHAR(10) | NULL | - | Valuta |
| `indices` | JSONB | NULL | - | Indici di appartenenza |
| `sector` | VARCHAR(100) | NULL | - | Settore |
| `industry` | VARCHAR(100) | NULL | - | Industria |
| `market_cap` | DOUBLE PRECISION | NULL | - | Market cap |
| `is_active` | BOOLEAN | NULL | - | Simbolo attivo |
| `priority` | INTEGER | NULL | - | Priorità download dati |
| `last_quote_update` | TIMESTAMP | NULL | - | Ultimo aggiornamento quote |
| `last_ohlcv_update` | TIMESTAMP | NULL | - | Ultimo aggiornamento OHLCV |
| `last_fundamental_update` | TIMESTAMP | NULL | - | Ultimo aggiornamento dati fond. |
| `consecutive_failures` | INTEGER | NULL | - | Errori consecutivi |
| `last_error` | TEXT | NULL | - | Ultimo errore |
| `created_at` | TIMESTAMP | NULL | - | Data creazione |
| `updated_at` | TIMESTAMP | NULL | - | Data aggiornamento |

**Indici:**
- `ix_market_universe_symbol` - UNIQUE INDEX (symbol)
- `ix_market_universe_region_active` - INDEX (region, is_active)
- `ix_market_universe_priority` - INDEX (priority, is_active)
- `ix_market_universe_exchange` - INDEX (exchange)

---

### 🤖 BOT_SIGNALS

Segnali generati dal bot di trading.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `user_id` | INTEGER | NOT NULL | - | FK → users.id |
| `portfolio_id` | INTEGER | NULL | - | FK → portfolios.id |
| `signal_type` | ENUM signaltype | NOT NULL | - | Tipo segnale |
| `priority` | ENUM signalpriority | NOT NULL | - | Priorità |
| `status` | ENUM signalstatus | NOT NULL | - | Stato |
| `symbol` | VARCHAR(20) | NULL | - | Simbolo (indexed) |
| `direction` | ENUM signaldirection | NULL | - | Direzione |
| `suggested_entry` | DOUBLE PRECISION | NULL | - | Entry price suggerito |
| `suggested_stop_loss` | DOUBLE PRECISION | NULL | - | Stop loss suggerito |
| `suggested_take_profit` | DOUBLE PRECISION | NULL | - | Take profit suggerito |
| `suggested_quantity` | INTEGER | NULL | - | Quantità suggerita |
| `risk_reward_ratio` | DOUBLE PRECISION | NULL | - | Risk/Reward |
| `risk_percent` | DOUBLE PRECISION | NULL | - | Rischio % |
| `current_price` | DOUBLE PRECISION | NULL | - | Prezzo corrente |
| `current_volume` | DOUBLE PRECISION | NULL | - | Volume corrente |
| `title` | VARCHAR(200) | NOT NULL | - | Titolo segnale |
| `message` | TEXT | NOT NULL | - | Messaggio |
| `rationale` | TEXT | NULL | - | Motivazione |
| `confidence_score` | DOUBLE PRECISION | NULL | - | Score confidenza (0-1) |
| `ml_model_used` | VARCHAR(50) | NULL | - | Modello ML usato |
| `technical_indicators` | JSON | NULL | - | Indicatori tecnici |
| `source` | VARCHAR(50) | NOT NULL | - | Sorgente segnale |
| `source_alert_id` | INTEGER | NULL | - | FK → alerts.id |
| `user_action_at` | TIMESTAMP | NULL | - | Data azione utente |
| `user_notes` | TEXT | NULL | - | Note utente |
| `resulting_trade_id` | INTEGER | NULL | - | FK → trades.id |
| `valid_until` | TIMESTAMP | NULL | - | Validità |
| `created_at` | TIMESTAMP | NULL | - | Data creazione |
| `updated_at` | TIMESTAMP | NULL | - | Data aggiornamento |

**Indici:**
- `ix_bot_signals_symbol` - INDEX (symbol)
- `ix_bot_signals_signal_type` - INDEX (signal_type)
- `ix_bot_signals_status` - INDEX (status)
- `ix_bot_signals_created_at` - INDEX (created_at)

---

### 📄 BOT_REPORTS

Report periodici generati dal bot.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | INTEGER | NOT NULL | SERIAL | Chiave primaria |
| `user_id` | INTEGER | NOT NULL | - | FK → users.id |
| `report_type` | VARCHAR(50) | NOT NULL | - | Tipo report (indexed) |
| `report_date` | TIMESTAMP | NOT NULL | - | Data report (indexed) |
| `title` | VARCHAR(200) | NOT NULL | - | Titolo report |
| `content` | JSON | NOT NULL | - | Contenuto strutturato |
| `total_signals` | INTEGER | NULL | - | Totale segnali |
| `trades_suggested` | INTEGER | NULL | - | Trade suggeriti |
| `alerts_triggered` | INTEGER | NULL | - | Alert scattati |
| `is_read` | BOOLEAN | NULL | - | Letto dall'utente |
| `read_at` | TIMESTAMP | NULL | - | Data lettura |
| `created_at` | TIMESTAMP | NULL | - | Data creazione |

**Constraints:**
- `bot_reports_user_id_fkey` - FK → users(id) ON DELETE CASCADE

---

### 📊 PRICE_BARS

Dati OHLCV storici per analisi e grafici.

| Campo | Tipo | Null | Default | Descrizione |
|-------|------|------|---------|-------------|
| `id` | BIGINT | NOT NULL | SERIAL | Chiave primaria |
| `symbol` | VARCHAR(20) | NOT NULL | - | Simbolo titolo (indexed) |
| `timeframe` | ENUM timeframe | NOT NULL | - | Timeframe (M1-W1) |
| `timestamp` | TIMESTAMP | NOT NULL | - | Data/ora barra (indexed) |
| `open` | DOUBLE PRECISION | NOT NULL | - | Prezzo apertura |
| `high` | DOUBLE PRECISION | NOT NULL | - | Prezzo massimo |
| `low` | DOUBLE PRECISION | NOT NULL | - | Prezzo minimo |
| `close` | DOUBLE PRECISION | NOT NULL | - | Prezzo chiusura |
| `volume` | BIGINT | NULL | - | Volume |
| `adjusted_close` | DOUBLE PRECISION | NULL | - | Prezzo adjusted |
| `vwap` | DOUBLE PRECISION | NULL | - | VWAP |
| `trade_count` | INTEGER | NULL | - | Numero trade |
| `source` | VARCHAR(50) | NULL | - | Data provider source |

**Indici:**
- `ix_price_bars_symbol` - INDEX (symbol)
- `ix_price_bars_timestamp` - INDEX (timestamp)
- `ix_price_bars_symbol_tf_ts` - INDEX (symbol, timeframe, timestamp)
- `ix_price_bars_unique` - UNIQUE (symbol, timeframe, timestamp)

---

### 💱 EXCHANGE_RATES

> **Descrizione**: Tassi di cambio FX cached, aggiornati ogni ora dal job `fx_rate_updater`.
> 
> **Valute supportate**: EUR, USD, GBP, CHF (12 coppie totali)
>
> **Fonte dati**: Frankfurter API (ECB - European Central Bank)

| Campo | Tipo | Nullable | Default | Descrizione |
|-------|------|----------|---------|-------------|
| `id` | INTEGER | NOT NULL | auto | PK |
| `base_currency` | VARCHAR(3) | NOT NULL | - | Valuta base (es. EUR) |
| `quote_currency` | VARCHAR(3) | NOT NULL | - | Valuta quota (es. USD) |
| `rate` | NUMERIC(20,10) | NOT NULL | - | Tasso (1 base = rate quote) |
| `source` | VARCHAR(50) | NOT NULL | 'frankfurter' | Fonte dati |
| `fetched_at` | TIMESTAMP | NOT NULL | - | Quando il tasso è stato recuperato |
| `created_at` | TIMESTAMP | NULL | now() | Data creazione |
| `updated_at` | TIMESTAMP | NULL | now() | Ultimo aggiornamento |

**Vincoli:**
- `uq_exchange_rates_pair` - UNIQUE (base_currency, quote_currency)

**Indici:**
- `ix_exchange_rates_pair` - INDEX (base_currency, quote_currency)

**Esempio dati:**
```
| base | quote | rate       | source      |
|------|-------|------------|-------------|
| EUR  | USD   | 1.05000000 | frankfurter |
| EUR  | GBP   | 0.86000000 | frankfurter |
| USD  | EUR   | 0.95238095 | frankfurter |
```

---

## 🔄 Diagramma Relazioni

```
                    ┌──────────────┐
                    │    USERS     │
                    └──────┬───────┘
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌───────────┐   ┌───────────┐
    │PORTFOLIOS│    │WATCHLISTS │   │USER_SETTGS│
    └────┬─────┘    └─────┬─────┘   └───────────┘
         │                │
    ┌────┼────┐           ▼
    │    │    │    ┌────────────────┐
    ▼    ▼    ▼    │WATCHLIST_SYMBS │
┌────┐┌────┐┌────┐ └────────────────┘
│POS ││TRAD││ FX │
│ITNS││ES  ││TXN │
└────┘└────┘└────┘
                    ┌──────────────┐
                    │    ALERTS    │
                    └──────────────┘
                    
                    ┌──────────────┐
                    │MARKET_UNIVERS│
                    └──────────────┘
                    
                    ┌──────────────┐
                    │  PRICE_BARS  │
                    └──────────────┘
                    
                    ┌──────────────┐
                    │EXCHANGE_RATES│ (standalone)
                    └──────────────┘
```

---

*Generato automaticamente il 18 Dicembre 2025*
