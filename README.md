# 📈 PaperTrading Platform

Una piattaforma completa di paper trading multi-mercato con architettura multi-provider, gestione intelligente dei rate limits, supporto ML per analisi predittive, e frontend completo per gestione portafogli.

## 🎯 Caratteristiche Principali

- **800 simboli** distribuiti su mercati globali (US, EU, Asia-Pacific)
- **15 provider** di dati con failover automatico
- **3 profili portafoglio**: Aggressivo, Bilanciato, Prudente
- **Machine Learning** per predizioni e ottimizzazione
- **Real-time** ogni 5 minuti per mercati aperti
- **Budget 75%** dei rate limits giornalieri

## 🏗️ Architettura

```
├── backend/          # Python/FastAPI backend
├── frontend/         # React/TypeScript frontend
├── ml-pipeline/      # ML training notebooks e scripts
├── infrastructure/   # Docker, scripts, config
└── docs/            # Documentazione progetto
```

## 🚀 Quick Start

### Prerequisiti

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Git

### Setup Sviluppo

```bash
# 1. Clona il repository
git clone <repository-url>
cd papertrading-platform

# 2. Copia e configura environment
cp .env.example .env
# Modifica .env con le tue API keys

# 3. Avvia i servizi Docker (DB, Redis, etc.)
docker-compose -f infrastructure/docker/docker-compose.dev.yml up -d

# 4. Setup Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# 5. Setup Frontend (in un altro terminale)
cd frontend
npm install
npm run dev
```

### Comandi Utili

```bash
# Makefile shortcuts
make dev          # Avvia tutto per sviluppo
make test         # Esegue tutti i test
make migrate      # Applica migrations DB
make lint         # Linting codice
make build        # Build production
```

## 📊 Provider Dati

| Provider | Mercato | Tipo | Rate Limit |
|----------|---------|------|------------|
| Alpaca | US | WebSocket | 288K/day |
| Polygon.io | US | REST | 7.2K/day |
| Twelve Data | EU | REST Batch | 800/day |
| yfinance | Global | Scraper | ~48K/day |
| Finnhub | Global | REST+WS | 86K/day |
| ... | ... | ... | ... |

Vedi `docs/01-ARCHITECTURE.md` per la lista completa e la strategia multi-provider.

## 📁 Documentazione

- [Architettura Sistema](docs/01-ARCHITECTURE.md)
- [Piano di Sviluppo](docs/02-DEVELOPMENT-PLAN.md)
- [API Reference](docs/API.md) *(coming soon)*
- [ML Models](docs/ML_MODELS.md) *(coming soon)*

## 🔧 Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL + TimescaleDB
- **Cache**: Redis
- **ORM**: SQLAlchemy 2.0
- **ML**: scikit-learn, XGBoost, TensorFlow

### Frontend
- **Framework**: React 18 + TypeScript
- **State**: Zustand
- **Styling**: Tailwind CSS
- **Charts**: Recharts, Lightweight Charts
- **Build**: Vite

## 📝 License

MIT License - vedi [LICENSE](LICENSE) per dettagli.

## 👤 Autore

Fausto - Paper Trading Platform Project
