# PaperTrading Platform - Handoff Notes

## Data: 5 Dicembre 2025

---

## Stato Attuale

### ✅ Completato
- **Docker deployment** funzionante su localhost
- **Autenticazione**: login/logout/sessione persistente
- **Portfolio**: CRUD completo con currency preference
- **Positions**: creazione ordini market, visualizzazione P&L
- **Currency**: sistema conversione valute EUR/USD/GBP/CHF

### 🔄 In Progress
- **POS-02**: Chiusura posizione (sell) - da testare
- **POS-03**: Modifica quantità posizione - da testare

### ⬜ Da Fare
- TRD-01 to TRD-06: Test trading avanzati
- MKT, WL, ALT, ANA, SET: Altri moduli

---

## Setup su Nuovo Mac

### 1. Clone Repository
```bash
git clone https://github.com/faux62/PaperTrading-Platform.git
cd PaperTrading-Platform
```

### 2. Avvia Docker
```bash
cd infrastructure/docker
docker compose -f docker-compose.local.yml up -d
```

### 3. Verifica Containers
```bash
docker compose -f docker-compose.local.yml ps
# Tutti devono essere "healthy" o "running"
```

### 4. Accesso
- URL: http://localhost
- User test: `test@test.com` / `Test123!@#`
- User faux62: `bandini.fausto@gmail.com` / `Pallazz@99`

---

## Dati nel Database

### Utenti
| ID | Email | Note |
|----|-------|------|
| 1 | test@test.com | Utente di test |
| 2 | bandini.fausto@gmail.com | Utente principale |

### Portfolios (user 2)
| ID | Nome | Note |
|----|------|------|
| 7 | Prova 3 | Ha 1 posizione AAPL |

### Posizioni Attive
| Portfolio | Symbol | Qty | Avg Cost |
|-----------|--------|-----|----------|
| 7 | AAPL | 10 | $150.06 |

---

## File Importanti Modificati

### Backend
- `backend/app/core/portfolio/service.py` - Aggiunto `get_portfolio_value()`
- `backend/app/core/trading/order_manager.py` - Fix `position_limits.max_position_size_percent`
- `backend/app/core/trading/execution.py` - Fix `avg_cost` field names
- `backend/app/api/v1/endpoints/trades.py` - Auto-execute market orders

### Frontend
- `frontend/src/pages/Trading.tsx` - Field mapping fix (avg_cost, market_value)
- `frontend/src/components/trading/OrderForm.tsx` - Manual price input for Phase 1
- `frontend/src/services/api.ts` - Portfolio positions endpoint fix

---

## Comandi Utili

### Logs
```bash
# Backend logs
docker compose -f docker-compose.local.yml logs -f backend

# Solo errori
docker compose -f docker-compose.local.yml logs backend | grep -i error
```

### Database
```bash
# Accesso diretto PostgreSQL
docker compose -f docker-compose.local.yml exec postgres psql -U papertrading -d papertrading

# Query posizioni
docker compose -f docker-compose.local.yml exec postgres psql -U papertrading -d papertrading -c "SELECT * FROM positions;"
```

### Rebuild dopo modifiche
```bash
docker compose -f docker-compose.local.yml build backend --no-cache
docker compose -f docker-compose.local.yml up -d backend
```

---

## Note Tecniche

### Slippage
Gli ordini market hanno slippage simulato (~0.04%). Questo è intenzionale per realismo.

### Phase 1 Testing
In Phase 1 (senza API dati reali), l'utente deve inserire manualmente il prezzo nel form ordini.

### Currency API
Usa open.er-api.com (gratuito, cache 1 ora). Funziona offline con fallback rates.

---

## Prossimi Passi Consigliati

1. **Testare POS-02**: Prova a vendere 5 shares AAPL dal portfolio 7
2. **Testare POS-03**: Compra altre 5 shares AAPL (dovrebbe aggiornare la posizione esistente)
3. **Continuare con TESTING-ROADMAP.md**

---

*Generato automaticamente - 5 Dicembre 2025*
