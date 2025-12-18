# PaperTrading Platform - Roadmap FX Refactoring

## Data: 18 Dicembre 2025
## Versione: 1.0

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

### FASE 1: Database - Nuova Tabella `exchange_rates`
**Tempo stimato: 1-2 ore**

#### 1.1 Creare migration Alembic

File: `backend/alembic/versions/YYYYMMDD_HHMMSS_add_exchange_rates_table.py`

```python
"""Add exchange_rates table

Revision ID: xxx
Revises: xxx
Create Date: 2025-12-18
"""

def upgrade():
    op.create_table(
        'exchange_rates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('base_currency', sa.String(3), nullable=False),
        sa.Column('quote_currency', sa.String(3), nullable=False),
        sa.Column('rate', sa.Numeric(20, 10), nullable=False),
        sa.Column('source', sa.String(50), default='frankfurter'),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
        sa.UniqueConstraint('base_currency', 'quote_currency', name='uq_exchange_rates_pair')
    )
    op.create_index('ix_exchange_rates_pair', 'exchange_rates', ['base_currency', 'quote_currency'])

def downgrade():
    op.drop_index('ix_exchange_rates_pair')
    op.drop_table('exchange_rates')
```

#### 1.2 Seed iniziale

Coppie supportate (4 valute × 3 = 12 coppie):
- EUR/USD, EUR/GBP, EUR/CHF
- USD/EUR, USD/GBP, USD/CHF
- GBP/EUR, GBP/USD, GBP/CHF
- CHF/EUR, CHF/USD, CHF/GBP

---

### FASE 2: Database - Modifica Tabella `positions`
**Tempo stimato: 1 ora**

#### 2.1 Creare migration Alembic

File: `backend/alembic/versions/YYYYMMDD_HHMMSS_remove_position_fx_fields.py`

```python
"""Remove avg_cost_portfolio and entry_exchange_rate from positions

Revision ID: xxx
Revises: xxx
Create Date: 2025-12-18
"""

def upgrade():
    op.drop_column('positions', 'avg_cost_portfolio')
    op.drop_column('positions', 'entry_exchange_rate')

def downgrade():
    op.add_column('positions', sa.Column('avg_cost_portfolio', sa.Numeric(20, 8)))
    op.add_column('positions', sa.Column('entry_exchange_rate', sa.Numeric(20, 8)))
```

#### 2.2 Aggiornare modello SQLAlchemy

File: `backend/app/db/models/position.py`

Rimuovere:
```python
avg_cost_portfolio = Column(Numeric(15, 4), default=Decimal("0"))
entry_exchange_rate = Column(Numeric(15, 6), default=Decimal("1.0"))
```

---

### FASE 3: Modelli e Repository
**Tempo stimato: 2 ore**

#### 3.1 Nuovo modello ExchangeRate

File: `backend/app/db/models/exchange_rate.py`

```python
from sqlalchemy import Column, Integer, String, Numeric, DateTime, UniqueConstraint
from app.db.base import Base

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    base_currency = Column(String(3), nullable=False)
    quote_currency = Column(String(3), nullable=False)
    rate = Column(Numeric(20, 10), nullable=False)
    source = Column(String(50), default="frankfurter")
    fetched_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    __table_args__ = (
        UniqueConstraint('base_currency', 'quote_currency', name='uq_exchange_rates_pair'),
    )
```

#### 3.2 Aggiornare `__init__.py` dei models

File: `backend/app/db/models/__init__.py`

Aggiungere:
```python
from app.db.models.exchange_rate import ExchangeRate
```

#### 3.3 Nuovo repository ExchangeRateRepository

File: `backend/app/db/repositories/exchange_rate.py`

```python
class ExchangeRateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_rate(self, base: str, quote: str) -> Optional[ExchangeRate]:
        """Get single exchange rate"""
        
    async def get_all_rates(self) -> List[ExchangeRate]:
        """Get all exchange rates"""
        
    async def upsert_rate(self, base: str, quote: str, rate: Decimal, source: str):
        """Insert or update single rate"""
        
    async def upsert_all_rates(self, rates: Dict[str, Decimal], source: str):
        """Bulk upsert all rates"""
```

---

### FASE 4: Service FX Rate Updater
**Tempo stimato: 2 ore**

#### 4.1 Nuovo service

File: `backend/app/services/fx_rate_service.py`

```python
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.repositories.exchange_rate import ExchangeRateRepository
from app.data_providers.adapters.frankfurter import FrankfurterAdapter


class FXRateService:
    """Service for managing exchange rates"""
    
    SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP', 'CHF']
    STALE_THRESHOLD_HOURS = 2
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExchangeRateRepository(db)
        self.frankfurter = FrankfurterAdapter()
    
    async def update_all_rates(self) -> Dict[str, Any]:
        """
        Fetch all rates from Frankfurter and update DB.
        Called by scheduler every hour.
        """
        stats = {"updated": 0, "failed": 0}
        
        for base in self.SUPPORTED_CURRENCIES:
            try:
                # Fetch rates for this base currency
                rates = await self.frankfurter.get_rates(base, self.SUPPORTED_CURRENCIES)
                
                for quote, rate in rates.items():
                    if quote != base:
                        await self.repo.upsert_rate(base, quote, rate, "frankfurter")
                        stats["updated"] += 1
                        
            except Exception as e:
                logger.error(f"Failed to fetch rates for {base}: {e}")
                stats["failed"] += 1
        
        return stats
    
    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """
        Get exchange rate from DB.
        Falls back to API if rate is stale or missing.
        """
        if from_currency == to_currency:
            return Decimal("1.0")
        
        rate_record = await self.repo.get_rate(from_currency, to_currency)
        
        # Check if rate exists and is fresh
        if rate_record:
            age = datetime.utcnow() - rate_record.fetched_at
            if age < timedelta(hours=self.STALE_THRESHOLD_HOURS):
                return rate_record.rate
            else:
                logger.warning(f"Stale rate for {from_currency}/{to_currency}, fetching fresh")
        
        # Fallback to API
        try:
            fresh_rate = await self.frankfurter.get_rate(from_currency, to_currency)
            await self.repo.upsert_rate(from_currency, to_currency, fresh_rate, "frankfurter")
            return fresh_rate
        except Exception as e:
            logger.error(f"API fallback failed: {e}")
            # Use stale rate if available
            if rate_record:
                return rate_record.rate
            raise
    
    async def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """Convert amount using current rate from DB"""
        rate = await self.get_rate(from_currency, to_currency)
        return amount * rate
```

---

### FASE 5: Scheduler Job Orario
**Tempo stimato: 1 ora**

#### 5.1 Nuovo job in bot/__init__.py

File: `backend/app/bot/__init__.py`

```python
from app.services.fx_rate_service import FXRateService

# ==========================================================
# FX RATE UPDATE JOB - Updates exchange rates every hour
# ==========================================================
async def fx_rate_update_job():
    """Update all exchange rates from Frankfurter API"""
    async for db in get_db():
        fx_service = FXRateService(db)
        stats = await fx_service.update_all_rates()
        logger.info(f"FX rates updated: {stats['updated']} rates, {stats['failed']} failed")

# Run every hour
scheduler.add_interval_job(
    job_id="fx_rate_update",
    func=fx_rate_update_job,
    hours=1
)

# Also run at startup
scheduler.add_startup_job(
    job_id="fx_rate_update_startup",
    func=fx_rate_update_job
)
```

---

### FASE 6: Refactoring Funzione `convert()`
**Tempo stimato: 2 ore**

#### 6.1 Identificare utilizzi attuali

Cercare in tutto il codebase:
```bash
grep -r "from app.data_providers.adapters.frankfurter import" backend/
grep -r "convert(" backend/app/
```

#### 6.2 Creare nuova funzione centralizzata

File: `backend/app/core/currency.py`

```python
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.fx_rate_service import FXRateService


async def convert(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    db: AsyncSession
) -> tuple[Decimal, Decimal]:
    """
    Convert amount from one currency to another.
    
    Returns:
        Tuple of (converted_amount, exchange_rate)
    """
    if from_currency == to_currency:
        return amount, Decimal("1.0")
    
    fx_service = FXRateService(db)
    rate = await fx_service.get_rate(from_currency, to_currency)
    return amount * rate, rate
```

#### 6.3 Aggiornare tutti i file che usano convert

Files da modificare:
- `backend/app/core/trading/execution.py`
- `backend/app/bot/services/global_price_updater.py`
- Altri file identificati nella ricerca

---

### FASE 7: Refactoring `_add_to_position()`
**Tempo stimato: 2 ore**

#### 7.1 File: `backend/app/core/trading/execution.py`

**Codice da RIMUOVERE (circa linee 775-790):**

```python
# RIMUOVERE TUTTO QUESTO:
# Calculate price in portfolio currency
executed_price_portfolio, _ = await convert(...)

# Calculate old value in portfolio currency  
old_value_portfolio = position.quantity * (position.avg_cost_portfolio or position.avg_cost)
new_value_portfolio = trade.executed_quantity * executed_price_portfolio

# Weighted average in portfolio currency
position.avg_cost_portfolio = (old_value_portfolio + new_value_portfolio) / total_quantity

# Weighted average exchange rate
old_rate = position.entry_exchange_rate or Decimal("1.0")
position.entry_exchange_rate = (
    (position.quantity * old_rate + trade.executed_quantity * exchange_rate) / total_quantity
)
```

**Codice SEMPLIFICATO:**

```python
async def _add_to_position(self, trade: Trade, native_currency: str, portfolio_currency: str):
    """Add bought shares to position - SIMPLIFIED"""
    
    result = await self.db.execute(
        select(Position).where(
            Position.portfolio_id == trade.portfolio_id,
            Position.symbol == trade.symbol
        )
    )
    position = result.scalar_one_or_none()
    
    if position:
        # Update existing position (weighted average cost basis)
        old_value = position.quantity * position.avg_cost
        new_value = trade.executed_quantity * trade.executed_price
        total_quantity = position.quantity + trade.executed_quantity
        
        # Weighted average in native currency ONLY
        position.avg_cost = (old_value + new_value) / total_quantity
        position.quantity = total_quantity
        position.updated_at = datetime.utcnow()
    else:
        # Create new position
        position = Position(
            portfolio_id=trade.portfolio_id,
            symbol=trade.symbol,
            exchange=trade.exchange,
            quantity=trade.executed_quantity,
            avg_cost=trade.executed_price,  # Native currency
            current_price=trade.executed_price,
            native_currency=native_currency,
            opened_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(position)
```

---

### FASE 8: Refactoring GlobalPriceUpdater
**Tempo stimato: 2 ore**

#### 8.1 File: `backend/app/bot/services/global_price_updater.py`

**Modificare `update_position_price()`:**

```python
async def update_position_price(self, position: Position, portfolio: Portfolio):
    """Update position price and calculate P&L using current FX rate"""
    
    # Get current price in native currency
    current_price = await self._get_price(position.symbol)
    if not current_price:
        return
    
    position.current_price = current_price
    
    # Get current exchange rate from DB
    fx_service = FXRateService(self.db)
    rate = await fx_service.get_rate(position.native_currency, portfolio.currency)
    
    # Calculate market value in portfolio currency
    market_value_native = position.quantity * current_price
    position.market_value = market_value_native * rate
    
    # Calculate unrealized P&L in portfolio currency
    # P&L = (current_price - avg_cost) × quantity × rate
    pnl_native = (current_price - position.avg_cost) * position.quantity
    position.unrealized_pnl = pnl_native * rate
    
    # Calculate P&L percent (currency-agnostic)
    if position.avg_cost > 0:
        position.unrealized_pnl_percent = (
            (current_price - position.avg_cost) / position.avg_cost * 100
        )
    
    position.updated_at = datetime.utcnow()
```

---

### FASE 9: Refactoring PositionRepository
**Tempo stimato: 1 ora**

#### 9.1 File: `backend/app/db/repositories/position.py`

Rimuovere riferimenti ai campi eliminati in tutti i metodi:
- `add_to_position()`
- `create_position()`
- Altri metodi che accedono a `avg_cost_portfolio` o `entry_exchange_rate`

---

### FASE 10: Refactoring API Endpoints
**Tempo stimato: 1 ora**

#### 10.1 File: `backend/app/api/v1/endpoints/positions.py`

Rimuovere campi da schema response:
```python
# RIMUOVERE:
avg_cost_portfolio: Optional[float] = None
entry_exchange_rate: Optional[float] = None
```

#### 10.2 File: `backend/app/schemas/position.py` (se esiste)

Stessa modifica agli schema Pydantic.

---

### FASE 11: Helper Funzione per Audit
**Tempo stimato: 1 ora**

#### 11.1 Nuova funzione per calcolare costo storico

File: `backend/app/services/position_analytics.py`

```python
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import Trade, TradeType, TradeStatus


async def get_historical_cost_in_portfolio_currency(
    db: AsyncSession,
    portfolio_id: int, 
    symbol: str
) -> Decimal:
    """
    Calcola il costo effettivo pagato in valuta portfolio
    usando i tassi storici salvati in TRADES.
    
    Utile per audit e analisi storica.
    """
    result = await db.execute(
        select(Trade).where(
            and_(
                Trade.portfolio_id == portfolio_id,
                Trade.symbol == symbol,
                Trade.trade_type == TradeType.BUY,
                Trade.status == TradeStatus.EXECUTED
            )
        )
    )
    trades = result.scalars().all()
    
    if not trades:
        return Decimal("0")
    
    total_cost_portfolio = sum(
        t.executed_price * t.executed_quantity * (t.exchange_rate or Decimal("1"))
        for t in trades
    )
    total_qty = sum(t.executed_quantity for t in trades)
    
    return total_cost_portfolio / total_qty if total_qty > 0 else Decimal("0")


async def get_avg_entry_exchange_rate(
    db: AsyncSession,
    portfolio_id: int,
    symbol: str
) -> Decimal:
    """
    Calcola il tasso di cambio medio ponderato di ingresso.
    """
    result = await db.execute(
        select(Trade).where(
            and_(
                Trade.portfolio_id == portfolio_id,
                Trade.symbol == symbol,
                Trade.trade_type == TradeType.BUY,
                Trade.status == TradeStatus.EXECUTED
            )
        )
    )
    trades = result.scalars().all()
    
    if not trades:
        return Decimal("1.0")
    
    weighted_rate = sum(
        t.executed_quantity * (t.exchange_rate or Decimal("1"))
        for t in trades
    )
    total_qty = sum(t.executed_quantity for t in trades)
    
    return weighted_rate / total_qty if total_qty > 0 else Decimal("1.0")
```

---

### FASE 12: Test
**Tempo stimato: 3 ore**

#### 12.1 Unit test nuovi componenti

File: `backend/tests/unit/test_exchange_rate_repository.py`
```python
- test_get_rate_existing
- test_get_rate_not_found
- test_upsert_rate_insert
- test_upsert_rate_update
- test_get_all_rates
```

File: `backend/tests/unit/test_fx_rate_service.py`
```python
- test_convert_same_currency
- test_convert_different_currency
- test_get_rate_fresh
- test_get_rate_stale_fallback_api
- test_get_rate_api_failure_use_stale
- test_update_all_rates
```

#### 12.2 Integration test

File: `backend/tests/integration/test_fx_rate_job.py`
```python
- test_scheduler_job_updates_rates
- test_startup_populates_rates
```

#### 12.3 Test di regressione

File: `backend/tests/integration/test_trading_with_new_fx.py`
```python
- test_buy_creates_position_without_fx_fields
- test_sell_calculates_pnl_correctly
- test_price_update_uses_current_rate
- test_portfolio_value_calculation
```

---

### FASE 13: Documentazione
**Tempo stimato: 1 ora**

#### 13.1 Aggiornare DATABASE-SCHEMA.md

- Aggiungere sezione per tabella `exchange_rates`
- Aggiornare sezione POSITIONS (rimuovere campi deprecati)
- Aggiornare note su sistema FX

#### 13.2 Aggiornare SPECIFICHE-TECNICHE.md

- Documentare nuovo approccio alla gestione valute
- Spiegare che P&L ora riflette solo performance titolo
- Documentare funzioni helper per audit storico

---

## 📊 Riepilogo Tempi

| Fase | Descrizione | Tempo Stimato |
|------|-------------|---------------|
| 1 | Nuova tabella `exchange_rates` | 1-2 ore |
| 2 | Modifica tabella `positions` | 1 ora |
| 3 | Modelli e Repository | 2 ore |
| 4 | FX Rate Service | 2 ore |
| 5 | Scheduler Job | 1 ora |
| 6 | Refactoring `convert()` | 2 ore |
| 7 | Refactoring `_add_to_position()` | 2 ore |
| 8 | Refactoring GlobalPriceUpdater | 2 ore |
| 9 | Refactoring PositionRepository | 1 ora |
| 10 | Refactoring API Endpoints | 1 ora |
| 11 | Helper funzione audit | 1 ora |
| 12 | Test | 3 ore |
| 13 | Documentazione | 1 ora |
| **TOTALE** | | **~20 ore** |

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

- [ ] Backup completo database
- [ ] Verificare che non ci siano ordini PENDING
- [ ] Notificare utenti di finestra manutenzione
- [ ] Preparare script di rollback
- [ ] Verificare accesso a Frankfurter API
- [ ] Review codice con altro sviluppatore

---

## 📝 Note di Implementazione

### Ordine consigliato

1. **Prima** creare la nuova tabella (Fase 1) senza toccare nulla di esistente
2. **Poi** creare service e job (Fasi 3-5) e verificare che funzionino
3. **Infine** fare il refactoring del codice esistente (Fasi 6-11)
4. **Ultimo** rimuovere le colonne deprecate (Fase 2)

### Rollback

In caso di problemi:
1. Disabilitare il nuovo job FX
2. Ripristinare le colonne `avg_cost_portfolio` e `entry_exchange_rate`
3. Fare rollback del codice
4. La tabella `exchange_rates` può rimanere (non crea conflitti)

---

*Documento creato il 18 Dicembre 2025*
