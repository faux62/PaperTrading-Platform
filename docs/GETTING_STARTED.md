# 🚀 Getting Started - PaperTrading Platform

Questo documento ti guida passo-passo per iniziare a sviluppare la piattaforma.

---

## ✅ Prerequisiti Checklist

Prima di iniziare, verifica di avere tutto installato:

```bash
# Python 3.11+
python --version   # Dovrebbe mostrare Python 3.11.x o superiore

# Node.js 20+
node --version     # Dovrebbe mostrare v20.x.x o superiore
npm --version      # Dovrebbe mostrare 10.x.x

# Docker
docker --version          # Docker version 24.x.x
docker-compose --version  # Docker Compose version v2.x.x

# Git
git --version      # git version 2.x.x
```

---

## 📁 Step 1: Setup Iniziale

### 1.1 Scarica il progetto

Scarica la cartella `papertrading-platform` e posizionala dove preferisci, per esempio:

```
C:\Users\Fausto\OneDrive\Projects\papertrading-platform
```

### 1.2 Apri in VS Code

```bash
cd papertrading-platform
code .
```

### 1.3 Installa le estensioni VS Code consigliate

- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **ESLint** (Microsoft)
- **Prettier** (Prettier)
- **Tailwind CSS IntelliSense** (Tailwind Labs)
- **Thunder Client** (alternativa a Postman)
- **Docker** (Microsoft)
- **GitLens** (GitKraken)

---

## 🐳 Step 2: Avvia i Servizi Docker

### 2.1 Configura l'environment

```bash
# Copia il file di esempio
cp .env.example .env

# Modifica .env con le tue API keys
# Apri .env in VS Code e inserisci le chiavi
```

### 2.2 Avvia PostgreSQL, TimescaleDB e Redis

```bash
# Dalla root del progetto
cd infrastructure/docker
docker-compose -f docker-compose.dev.yml up -d

# Verifica che i servizi siano running
docker ps
```

Dovresti vedere 5 container running:
- `papertrading-postgres` (porta 5432)
- `papertrading-timescale` (porta 5433)
- `papertrading-redis` (porta 6379)
- `papertrading-pgadmin` (porta 5050)
- `papertrading-redis-commander` (porta 8081)

### 2.3 Verifica le connessioni

- **pgAdmin**: http://localhost:5050 (email: admin@papertrading.com, password: admin123)
- **Redis Commander**: http://localhost:8081

---

## 🐍 Step 3: Setup Backend

### 3.1 Crea e attiva il virtual environment

```bash
cd backend

# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3.2 Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 3.3 Configura Alembic per le migrations

```bash
# Crea il file alembic.ini se non esiste
alembic init alembic

# Modifica alembic/env.py per usare i nostri modelli
# (vedi sezione "Configurazione Alembic" sotto)
```

### 3.4 Esegui le migrations

```bash
# Crea la prima migration
alembic revision --autogenerate -m "Initial migration"

# Applica le migrations
alembic upgrade head
```

### 3.5 Avvia il backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verifica che funzioni:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## ⚛️ Step 4: Setup Frontend

### 4.1 Installa le dipendenze

```bash
cd frontend
npm install
```

### 4.2 Avvia il frontend

```bash
npm run dev
```

Apri il browser su: http://localhost:5173

---

## 🔧 Configurazione Alembic

Modifica `backend/alembic/env.py`:

```python
# Aggiungi all'inizio del file
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.database import Base
from app.db.models import *  # Import all models

# Sostituisci la riga config.set_main_option
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

# Imposta target_metadata
target_metadata = Base.metadata
```

Modifica `backend/alembic.ini`:

```ini
# Cambia la riga sqlalchemy.url
sqlalchemy.url = postgresql://papertrading_user:dev_password_123@localhost:5432/papertrading
```

---

## 📝 Workflow Giornaliero

Una volta completato il setup, il tuo workflow quotidiano sarà:

```bash
# 1. Avvia Docker (se non già running)
make docker-up

# 2. Attiva venv backend
cd backend && source venv/bin/activate  # o .\venv\Scripts\activate su Windows

# 3. Avvia backend (in un terminale)
uvicorn app.main:app --reload

# 4. Avvia frontend (in un altro terminale)
cd frontend && npm run dev
```

Oppure usa il Makefile:

```bash
make dev  # Avvia tutto insieme
```

---

## 🎯 Primi Task da Implementare

Seguendo il piano di sviluppo (vedi `docs/02-DEVELOPMENT-PLAN.md`), i primi task sono:

### Settimana 1 - Giorno 1-2
- [x] Setup struttura progetto ✅ (già fatto)
- [x] Docker Compose ✅ (già fatto)
- [x] Modelli DB iniziali ✅ (già fatto)
- [ ] Completare migrations Alembic
- [ ] Test connessione DB

### Settimana 1 - Giorno 3-5
- [ ] Implementare autenticazione JWT completa
- [ ] Endpoint register/login funzionanti
- [ ] Password hashing con bcrypt

### Settimana 2
- [ ] API Portfolio CRUD complete
- [ ] Pydantic schemas
- [ ] Unit tests

---

## 🆘 Troubleshooting

### Docker non parte
```bash
# Verifica che Docker Desktop sia avviato
# Riavvia i servizi
docker-compose -f infrastructure/docker/docker-compose.dev.yml down
docker-compose -f infrastructure/docker/docker-compose.dev.yml up -d
```

### Errore connessione PostgreSQL
```bash
# Verifica che il container sia running
docker ps | grep postgres

# Controlla i logs
docker logs papertrading-postgres
```

### Errore import moduli Python
```bash
# Assicurati di essere nella cartella backend con venv attivo
cd backend
source venv/bin/activate  # o .\venv\Scripts\activate
pip install -r requirements.txt
```

### Porta già in uso
```bash
# Trova e termina il processo
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8000
kill -9 <PID>
```

---

## 📚 Risorse Utili

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [React Documentation](https://react.dev/)
- [TailwindCSS](https://tailwindcss.com/docs)
- [Zustand](https://docs.pmnd.rs/zustand)

---

*Buon coding! 🚀*
