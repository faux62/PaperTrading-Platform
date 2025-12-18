# PaperTrading Platform - Roadmap FX Refactoring

## Data: 18 Dicembre 2025
## Versione: 2.0 (COMPLETATO ✅)

---

## 📋 Sommario

- [Obiettivo](#-obiettivo)
- [Approccio Scelto](#-approccio-scelto)
- [Impatto sulle Tabelle](#-impatto-sulle-tabelle)
- [Fasi di Implementazione](#-fasi-di-implementazione)
- [Riepilogo Tempi](#-riepilogo-tempi)
- [Rischi e Mitigazioni](#️-rischi-e-mitigazioni)
- [Checklist Pre-Implementazione](#-checklist-pre-implementazione)

---

## 🎯 Obiettivo

Creare una tabella dedicata `exchange_rates` per i tassi di cambio, aggiornata ogni ora, eliminando la necessità di chiamate API on-demand per le conversioni valutarie.

**Benefici:**
- ✅ Performance: conversioni istantanee (query DB vs chiamata API)
- ✅ Affidabilità: nessuna dipendenza da provider esterni durante le operazioni
- ✅ Consistenza: stesso tasso per tutte le operazioni nella stessa ora
- ✅ Costo: riduzione chiamate API (1/ora invece di on-demand)
- ✅ Semplificazione: P&L riflette SOLO la performance del titolo

---

## 🔄 Approccio Scelto

### Approccio B - Tasso Corrente (Dinamico)

```
avg_cost_portfolio = avg_cost × tasso_corrente (calcolato on-demand)
unrealized_pnl = quantity × (current_price - avg_cost) × tasso_corrente
```

**Caratteristiche:**
- P&L riflette SOLO la performance del titolo (non mescola con forex)
- Conversioni sempre con tasso aggiornato dalla tabella `exchange_rates`
- Audit trail completo mantenuto nella tabella `TRADES.exchange_rate`
- Schema POSITIONS semplificato (rimozione campi ridondanti)

---

## 📊 Impatto sulle Tabelle

### Nuova Tabella: `exchange_rates`

```sql
CREATE TABLE exchange_rates (
    id SERIAL PRIMARY KEY,
    base_currency VARCHAR(3) NOT NULL,      -- EUR, USD, GBP, CHF
    quote_currency VARCHAR(3) NOT NULL,     -- EUR, USD, GBP, CHF
    rate NUMERIC(20,10) NOT NULL,           -- Tasso di cambio
    source VARCHAR(50) DEFAULT 'frankfurter',
    fetched_at TIMESTAMP NOT NULL,          -- Quando è stato recuperato
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(base_currency, quote_currency)
);

CREATE INDEX ix_exchange_rates_pair ON exchange_rates(base_currency, quote_currency);
```

### Modifica Tabella: `positions`

| Campo | Azione | Note |
|-------|--------|------|
| `avg_cost` | ✅ MANTIENI | Cache per performance |
| `avg_cost_portfolio` | ❌ RIMUOVI | Calcolato on-demand |
| `entry_exchange_rate` | ❌ RIMUOVI | Info disponibile in TRADES |

### Tabella Invariata: `trades`

Nessuna modifica - `exchange_rate` già presente per audit trail.

---

## 📋 Fasi di Implementazione

---

### FASE 1: Database - Nuova Tabella `exchange_rates` ✅ COMPLETATA
**Tempo stimato: 1-2 ore**
**Data completamento: 18 Dicembre 2025**

#### 1.1 Creare migration Alembic ✅

File: `backend/alembic/versions/20251218_163000_add_exchange_rates_table.py`

#### 1.2 Creare modello SQLAlchemy ✅

File: `backend/app/db/models/exchange_rate.py`

#### 1.3 Creare repository ✅

File: `backend/app/db/repositories/exchange_rate.py`

#### 1.4 Seed iniziale ✅

Incluso nella migration con valori approssimati (source='seed').

#### 1.5 Aggiornare documentazione ✅

File: `docs/DATABASE-SCHEMA.md` - aggiunta sezione EXCHANGE_RATES

---

### FASE 2: Database - Modifica Tabella `positions` ✅ COMPLETATA
**Tempo stimato: 1 ora**
**Data completamento: 18 Dicembre 2025**

#### 2.1 Creare migration Alembic ✅

File: `backend/alembic/versions/20251218_170000_remove_position_fx_fields.py`

#### 2.2 Aggiornare modello Position ✅

File: `backend/app/db/models/position.py` - rimossi campi `avg_cost_portfolio` e `entry_exchange_rate`

---

### FASE 3: Modelli e Repository ✅ COMPLETATA (in Fase 1)
**Tempo stimato: 2 ore**
**Nota: Completata insieme alla Fase 1**

#### 3.1 Nuovo modello ExchangeRate ✅

File: `backend/app/db/models/exchange_rate.py`

#### 3.2 Aggiornare `__init__.py` dei models ✅

File: `backend/app/db/models/__init__.py` - aggiunto export ExchangeRate

#### 3.3 Nuovo repository ExchangeRateRepository ✅

File: `backend/app/db/repositories/exchange_rate.py`

Metodi implementati:
- `get_rate()` - Get singolo tasso
- `get_rate_value()` - Get valore tasso (ritorna 1.0 se non trovato)
- `get_all_rates()` - Get tutti i tassi
- `upsert_rate()` - Insert o update singolo tasso
- `bulk_upsert_rates()` - Bulk upsert
- `convert_amount()` - Converti importo tra valute

---

### FASE 4: Service FX Rate Updater ✅ COMPLETATA
**Tempo stimato: 2 ore**
**Data completamento: 18 Dicembre 2025**

#### 4.1 Nuovo service ✅

File: `backend/app/services/fx_rate_updater.py`

Funzionalità implementate:
- `FxRateUpdaterService` class con metodi:
  - `fetch_rates_from_api()` - Fetch da Frankfurter API
  - `fetch_all_rates()` - Fetch tutte le 12 coppie
  - `update_all_rates()` - Aggiorna DB
  - `get_rate()` - Get rate con fallback API
- Singleton `fx_rate_updater`
- Funzione `update_exchange_rates()` per scheduler

---

### FASE 5: Scheduler Job Orario ✅ COMPLETATA
**Tempo stimato: 1 ora**
**Data completamento: 18 Dicembre 2025**

#### 5.1 Job in bot/__init__.py ✅

Aggiunto job `fx_rate_update` che:
- Esegue ogni ora
- Chiama `update_exchange_rates()` 
- Aggiorna tutte le 12 coppie valutarie

---

### FASE 6: Refactoring Funzione `convert()` ✅ COMPLETATA
**Tempo stimato: 2 ore**
**Data completamento: 18 Dicembre 2025**

#### 6.1 Refactoring utils/currency.py ✅

File: `backend/app/utils/currency.py`

Modifiche:
- Rimossa dipendenza da `exchangerate-api.com`
- Rimossa cache in memoria (ora usa DB)
- `get_exchange_rate_from_db()` - Fetch diretto da DB
- `convert()` - Usa tassi da tabella `exchange_rates`
- `get_exchange_rate()` - Ritorna Decimal con fallback
- Ridotte valute supportate a EUR, USD, GBP, CHF
- Aggiunti fallback rates per emergenza

---

### FASE 7: Refactoring `_add_to_position()` ✅ COMPLETATA
**Tempo stimato: 2 ore**
**Data completamento: 18 Dicembre 2025**

#### 7.1 File: `backend/app/core/trading/execution.py` ✅

Modifiche:
- Rimosso calcolo `executed_price_portfolio`
- Rimosso aggiornamento `avg_cost_portfolio`
- Rimosso aggiornamento `entry_exchange_rate`
- `avg_cost` ora calcolato solo in valuta NATIVA
- Aggiornato docstring del metodo e del file

---

### FASE 8: Refactoring GlobalPriceUpdater ✅ COMPLETATA
**Tempo stimato: 2 ore**
**Data completamento: 18 Dicembre 2025**

#### 8.1 File: `backend/app/bot/services/global_price_updater.py` ✅

Modifiche:
- `update_position_price()`: Aggiunto parametro `portfolio_currency`
- Calcolo `market_value` usa FX rate corrente da DB
- Calcolo `unrealized_pnl` in valuta PORTFOLIO
- `unrealized_pnl_percent` resta currency-agnostic
- `update_portfolio_prices()`: Passa `portfolio.currency` alla funzione
- Aggiornato docstring del file

---

### FASE 9: Refactoring PositionRepository ✅ COMPLETATA
**Tempo stimato: 1 ora**
**Data completamento: 18 Dicembre 2025**

#### 9.1 File: `backend/app/db/repositories/position.py` ✅

Verificato - il repository NON conteneva riferimenti ai campi eliminati.
I metodi `create()`, `add_to_position()`, `update()` usano solo:
- `avg_cost` (valuta nativa)
- `current_price` (valuta nativa)
- `market_value`, `unrealized_pnl` (calcolati)

---

### FASE 10: Refactoring API Endpoints ✅ COMPLETATA
**Tempo stimato: 1 ora**
**Data completamento: 18 Dicembre 2025**

#### 10.1 File: `backend/app/api/v1/endpoints/positions.py` ✅

Rimossi campi deprecati da `PositionResponse`:
- `native_currency` (rimosso)
- `avg_cost_portfolio` (rimosso)
- `entry_exchange_rate` (rimosso)

Aggiornato docstring per chiarire semantica valori:
- `avg_cost`, `current_price`: valuta NATIVA
- `market_value`, `unrealized_pnl`: valuta PORTFOLIO (convertiti)

#### 10.2 File: `backend/app/schemas/position.py`

Non esiste - gli schema sono definiti inline nell'endpoint.

---

### FASE 11: Helper Funzione per Audit ✅ COMPLETATA
**Tempo stimato: 1 ora**
**Data completamento: 18 Dicembre 2025**

#### 11.1 Nuovo service per analytics ✅

File: `backend/app/services/position_analytics.py`

Funzioni implementate:
- `get_historical_cost_in_portfolio_currency()` - Calcola costo medio storico usando FX rates da TRADES
- `get_avg_entry_exchange_rate()` - Calcola tasso FX medio ponderato di ingresso
- `get_position_cost_breakdown()` - Breakdown dettagliato dei costi (native e portfolio currency)
- `calculate_forex_impact()` - Calcola impatto forex sulla posizione

Casi d'uso:
- Audit trail: cosa è stato effettivamente pagato
- Tax reporting: cost basis con tassi storici
- Analisi: isolare performance stock da forex

---

### FASE 12: Test ✅ COMPLETATA
**Tempo stimato: 3 ore**
**Data completamento: 18 Dicembre 2025**

#### 12.1 Unit test nuovi componenti ✅

File: `backend/tests/unit/test_exchange_rate_repository.py`
- TestExchangeRateRepository: 10 test cases
- TestExchangeRateModel: 2 test cases

File: `backend/tests/unit/test_fx_rate_service.py`
- TestFxRateUpdaterService: 10 test cases
- TestCurrencyConversion: 4 test cases
- TestRateFreshness: 2 test cases

File: `backend/tests/unit/test_position_analytics.py`
- TestGetHistoricalCostInPortfolioCurrency: 3 test cases
- TestGetAvgEntryExchangeRate: 3 test cases
- TestGetPositionCostBreakdown: 3 test cases
- TestCalculateForexImpact: 3 test cases
- TestEdgeCases: 3 test cases

#### 12.2 Integration tests ✅

File: `backend/tests/integration/test_fx_system.py`
- TestFxRateUpdateJob: Job e scheduler configuration
- TestExchangeRateRepository: Repository methods existence
- TestCurrencyConversionIntegration: convert() function tests
- TestPositionWithFx: Position model structure
- TestTradingWithFx: Trade FX fields
- TestGlobalPriceUpdaterWithFx: Price updater integration
- TestApiSchemasNoDeprecatedFields: API cleanup verification
- TestFrankfurterApiIntegration: Live API tests (skipped by default)

---

### FASE 13: Documentazione ✅ COMPLETATA
**Tempo stimato: 1 ora**
**Data completamento: 18 Dicembre 2025**

#### 13.1 Aggiornato DATABASE-SCHEMA.md ✅

- Tabella `exchange_rates` già documentata
- Sezione POSITIONS aggiornata (campi deprecati rimossi)
- Note su sistema FX già presenti

#### 13.2 Aggiornato SPECIFICHE-TECNICHE.md ✅

- Aggiunta nuova **Sezione 8: Gestione Multi-Currency (FX)**
- Documentato Approccio B (FX dinamico)
- Schema architetturale FX
- Valute supportate e coppie FX
- Servizi e scheduler job
- Funzioni audit per analisi storica
- Versione documento aggiornata a 2.0

---

## 🎉 REFACTORING COMPLETATO

**Tutte le 13 fasi sono state completate con successo!**

| Componente | File | Stato |
|------------|------|-------|
| Migration exchange_rates | `alembic/versions/20251218_163000_*.py` | ✅ |
| Migration remove FX fields | `alembic/versions/20251218_170000_*.py` | ✅ |
| Model ExchangeRate | `db/models/exchange_rate.py` | ✅ |
| Repository | `db/repositories/exchange_rate.py` | ✅ |
| FX Rate Service | `services/fx_rate_updater.py` | ✅ |
| Currency Utils | `utils/currency.py` | ✅ |
| Position Analytics | `services/position_analytics.py` | ✅ |
| Scheduler Job | `bot/__init__.py` | ✅ |
| Trading Execution | `core/trading/execution.py` | ✅ |
| Price Updater | `bot/services/global_price_updater.py` | ✅ |
| API Schemas | `api/v1/endpoints/positions.py` | ✅ |
| Unit Tests | `tests/unit/test_*.py` | ✅ |
| Integration Tests | `tests/integration/test_fx_system.py` | ✅ |
| Documentation | `docs/*.md` | ✅ |

---

## 📊 Riepilogo Tempi

| Fase | Descrizione | Tempo Stimato | Stato |
|------|-------------|---------------|-------|
| 1 | Nuova tabella `exchange_rates` | 1-2 ore | ✅ |
| 2 | Modifica tabella `positions` | 1 ora | ✅ |
| 3 | Modelli e Repository | 2 ore | ✅ |
| 4 | FX Rate Service | 2 ore | ✅ |
| 5 | Scheduler Job | 1 ora | ✅ |
| 6 | Refactoring `convert()` | 2 ore | ✅ |
| 7 | Refactoring `_add_to_position()` | 2 ore | ✅ |
| 8 | Refactoring GlobalPriceUpdater | 2 ore | ✅ |
| 9 | Refactoring PositionRepository | 1 ora | ✅ |
| 10 | Refactoring API Endpoints | 1 ora | ✅ |
| 11 | Helper funzione audit | 1 ora | ✅ |
| 12 | Test | 3 ore | ✅ |
| 13 | Documentazione | 1 ora | ✅ |
| **TOTALE** | | **~20 ore** | **13/13 ✅** |

---

## ⚠️ Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Dati esistenti con vecchi campi | Media | Basso | Migration gestisce backward compatibility |
| API Frankfurter down | Bassa | Medio | Fallback a ultimo tasso disponibile + alert |
| Performance query DB | Bassa | Basso | Indice su (base_currency, quote_currency) |
| Posizioni aperte durante migration | Media | Alto | Eseguire durante finestra manutenzione |
| Test insufficienti | Media | Alto | Coverage minimo 80% su nuovi componenti |

---

## ✅ Checklist Pre-Implementazione

- [x] Backup completo database
- [x] Verificare che non ci siano ordini PENDING
- [ ] Notificare utenti di finestra manutenzione
- [ ] Preparare script di rollback
- [x] Verificare accesso a Frankfurter API
- [ ] Review codice con altro sviluppatore

---

## 📝 Note di Implementazione

### Ordine eseguito (aggiornato 18/12/2025)

Le fasi 1-6 sono state completate con il seguente ordine:

1. **Fase 1**: Creata tabella `exchange_rates` + migration + seed iniziale
2. **Fase 3**: Creato modello `ExchangeRate` e `ExchangeRateRepository` (insieme a Fase 1)
3. **Fase 2**: Rimossi campi `avg_cost_portfolio` e `entry_exchange_rate` da POSITIONS
4. **Fase 4**: Creato `FxRateUpdaterService` in services/
5. **Fase 5**: Aggiunto job `fx_rate_update` ogni ora in bot/__init__.py
6. **Fase 6**: Refactorizzato `utils/currency.py` per usare DB invece di API esterna

### Prossimi passi

7. **Fase 7-8**: Refactoring execution.py e global_price_updater.py
8. **Fase 9-10**: Cleanup repository e API endpoints
9. **Fase 11-13**: Helper audit, test, documentazione

### Rollback

In caso di problemi:
1. Disabilitare il nuovo job FX
2. Ripristinare le colonne `avg_cost_portfolio` e `entry_exchange_rate`
3. Fare rollback del codice
4. La tabella `exchange_rates` può rimanere (non crea conflitti)

---

*Documento creato il 18 Dicembre 2025*
