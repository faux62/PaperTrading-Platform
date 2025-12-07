# 🔧 Manuale Operatore - PaperTrading Platform

**Versione:** 1.0  
**Data:** 7 Dicembre 2025  
**Destinatari:** Amministratori di sistema, DevOps

---

## Indice

1. [Requisiti di Sistema](#1-requisiti-di-sistema)
2. [Installazione](#2-installazione)
3. [Configurazione](#3-configurazione)
4. [Avvio del Sistema](#4-avvio-del-sistema)
5. [Gestione Database](#5-gestione-database)
6. [Monitoraggio](#6-monitoraggio)
7. [Backup e Recovery](#7-backup-e-recovery)
8. [Troubleshooting](#8-troubleshooting)
9. [Manutenzione](#9-manutenzione)
10. [Sicurezza](#10-sicurezza)

---

## 1. Requisiti di Sistema

### 1.1 Requisiti Hardware

#### Ambiente Sviluppo
| Componente | Minimo | Raccomandato |
|------------|--------|--------------|
| CPU | 2 core | 4 core |
| RAM | 8 GB | 16 GB |
| Storage | 20 GB SSD | 50 GB SSD |
| Network | 10 Mbps | 100 Mbps |

#### Ambiente Produzione
| Componente | Minimo | Raccomandato |
|------------|--------|--------------|
| CPU | 4 vCPU | 8 vCPU |
| RAM | 16 GB | 32 GB |
| Storage | 100 GB SSD | 500 GB SSD |
| Network | 100 Mbps | 1 Gbps |

### 1.2 Requisiti Software

#### Sistema Operativo
- Linux (Ubuntu 22.04+ / Debian 12+) - raccomandato
- macOS 13+ (sviluppo)
- Windows 11 con WSL2 (sviluppo)

#### Software Richiesto
| Software | Versione | Uso |
|----------|----------|-----|
| Docker | 24+ | Container runtime |
| Docker Compose | 2.20+ | Orchestrazione |
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend |
| Git | 2.40+ | Version control |

### 1.3 Porte di Rete

| Porta | Servizio | Descrizione |
|-------|----------|-------------|
| 8000 | Backend API | FastAPI server |
| 5173 | Frontend Dev | Vite dev server |
| 3000 | Frontend Prod | Build statica |
| 5432 | PostgreSQL | Database principale |
| 5433 | TimescaleDB | Database time-series |
| 6379 | Redis | Cache/Pub-Sub |
| 5050 | pgAdmin | GUI PostgreSQL |
| 8081 | Redis Commander | GUI Redis |

---

## 2. Installazione

### 2.1 Clone Repository

```bash
# Clone del repository
git clone https://github.com/faux62/PaperTrading-Platform.git
cd PaperTrading-Platform
```

### 2.2 Setup Ambiente Sviluppo

#### Backend (Python)

```bash
# Crea virtual environment
cd backend
python3.11 -m venv venv

# Attiva virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Installa dipendenze
pip install --upgrade pip
pip install -r requirements.txt
```

#### Frontend (Node.js)

```bash
# Installa dipendenze
cd frontend
npm install
```

### 2.3 Setup Docker

```bash
# Verifica installazione Docker
docker --version
docker-compose --version

# Pull immagini richieste
docker pull postgres:16-alpine
docker pull timescale/timescaledb:latest-pg16
docker pull redis:7-alpine
docker pull dpage/pgadmin4:latest
docker pull rediscommander/redis-commander:latest
```

---

## 3. Configurazione

### 3.1 File Ambiente

Crea il file `.env` nella root del progetto:

```bash
cp .env.example .env
```

### 3.2 Variabili Ambiente

#### Database PostgreSQL
```env
# PostgreSQL principale
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=papertrading
POSTGRES_USER=papertrading_user
POSTGRES_PASSWORD=<password_sicura>

# Connection string
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
```

#### TimescaleDB
```env
TIMESCALE_HOST=localhost
TIMESCALE_PORT=5433
TIMESCALE_DB=papertrading_ts
TIMESCALE_USER=papertrading_user
TIMESCALE_PASSWORD=<password_sicura>
```

#### Redis
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}/0
```

#### Sicurezza JWT
```env
# Genera con: openssl rand -hex 32
SECRET_KEY=<chiave_segreta_256bit>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### Provider API Keys (Opzionali)
```env
# Alpaca
ALPACA_API_KEY=<key>
ALPACA_SECRET_KEY=<secret>
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Polygon
POLYGON_API_KEY=<key>

# Finnhub
FINNHUB_API_KEY=<key>

# Twelve Data
TWELVEDATA_API_KEY=<key>

# Alpha Vantage
ALPHA_VANTAGE_API_KEY=<key>

# Altri provider...
```

#### Frontend
```env
# Frontend
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

#### pgAdmin (Sviluppo)
```env
PGADMIN_EMAIL=admin@papertrading.local
PGADMIN_PASSWORD=<password>
```

### 3.3 Configurazione Backend

File: `backend/app/config.py`

```python
class Settings:
    # Modifica per produzione
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # CORS origins per produzione
    CORS_ORIGINS: list = [
        "https://yourdomain.com",
    ]
```

### 3.4 Configurazione CORS

Per produzione, modifica `backend/app/main.py`:

```python
origins = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

---

## 4. Avvio del Sistema

### 4.1 Avvio Servizi Docker

```bash
# Avvia tutti i servizi
docker-compose --env-file .env -f infrastructure/docker/docker-compose.dev.yml up -d

# Verifica stato
docker-compose --env-file .env -f infrastructure/docker/docker-compose.dev.yml ps

# Output atteso:
# papertrading-postgres      running   0.0.0.0:5432->5432/tcp
# papertrading-timescale     running   0.0.0.0:5433->5432/tcp
# papertrading-redis         running   0.0.0.0:6379->6379/tcp
# papertrading-pgadmin       running   0.0.0.0:5050->80/tcp
# papertrading-redis-commander running  0.0.0.0:8081->8081/tcp
```

### 4.2 Inizializzazione Database

```bash
cd backend

# Attiva virtual environment
source venv/bin/activate

# Esegui migrazioni
alembic upgrade head

# Verifica tabelle create
# Connettiti a pgAdmin http://localhost:5050 e verifica
```

### 4.3 Avvio Backend

#### Sviluppo (con hot reload)
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Produzione (con Gunicorn)
```bash
cd backend
source venv/bin/activate
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### 4.4 Avvio Frontend

#### Sviluppo
```bash
cd frontend
npm run dev
# Disponibile su http://localhost:5173
```

#### Produzione (Build)
```bash
cd frontend
npm run build
# Output in frontend/dist/

# Servi con nginx o serve
npx serve -s dist -l 3000
```

### 4.5 Verifica Sistema

```bash
# Test API
curl http://localhost:8000/api/v1/

# Risposta attesa:
# {"api":"PaperTrading Platform","version":"v1","status":"operational"}

# Test Health
curl http://localhost:8000/health

# Test Frontend
curl http://localhost:5173  # Dev
curl http://localhost:3000  # Prod
```

### 4.6 Ordine di Avvio Raccomandato

```
1. Docker services (postgres, redis, timescale)
2. Wait 10-15 sec per startup
3. Database migrations (alembic)
4. Backend API
5. Frontend
```

### 4.7 Script di Avvio Completo

Usa il Makefile fornito:

```bash
# Avvia tutto
make up

# Solo backend
make backend

# Solo frontend
make frontend

# Stop tutto
make down

# Logs
make logs
```

---

## 5. Gestione Database

### 5.1 Accesso PostgreSQL

#### Via CLI
```bash
# Connessione diretta
docker exec -it papertrading-postgres psql -U papertrading_user -d papertrading

# Query esempio
\dt  # Lista tabelle
\d users  # Schema tabella users
SELECT COUNT(*) FROM users;
```

#### Via pgAdmin
1. Accedi a http://localhost:5050
2. Login con credenziali .env
3. Add Server:
   - Host: postgres (o host.docker.internal)
   - Port: 5432
   - Database: papertrading
   - Username/Password da .env

### 5.2 Migrazioni Alembic

```bash
cd backend
source venv/bin/activate

# Stato corrente
alembic current

# Storico migrazioni
alembic history

# Crea nuova migrazione
alembic revision --autogenerate -m "descrizione_modifica"

# Applica migrazioni
alembic upgrade head

# Rollback ultima migrazione
alembic downgrade -1

# Rollback a versione specifica
alembic downgrade <revision_id>
```

### 5.3 Accesso Redis

#### Via CLI
```bash
# Connessione
docker exec -it papertrading-redis redis-cli

# Comandi utili
KEYS *           # Lista tutte le chiavi
GET key_name     # Leggi valore
TTL key_name     # Time to live
INFO             # Statistiche
DBSIZE           # Numero chiavi
FLUSHALL         # ATTENZIONE: cancella tutto
```

#### Via Redis Commander
1. Accedi a http://localhost:8081
2. Naviga le chiavi graficamente

### 5.4 Backup Database

#### Backup PostgreSQL
```bash
# Backup completo
docker exec papertrading-postgres pg_dump -U papertrading_user papertrading > backup_$(date +%Y%m%d).sql

# Backup compresso
docker exec papertrading-postgres pg_dump -U papertrading_user papertrading | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup solo schema
docker exec papertrading-postgres pg_dump -U papertrading_user --schema-only papertrading > schema_backup.sql

# Backup solo dati
docker exec papertrading-postgres pg_dump -U papertrading_user --data-only papertrading > data_backup.sql
```

#### Restore PostgreSQL
```bash
# Restore
cat backup.sql | docker exec -i papertrading-postgres psql -U papertrading_user -d papertrading

# Restore da gzip
gunzip -c backup.sql.gz | docker exec -i papertrading-postgres psql -U papertrading_user -d papertrading
```

#### Backup Redis
```bash
# Trigger RDB snapshot
docker exec papertrading-redis redis-cli BGSAVE

# Copia file dump.rdb
docker cp papertrading-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

---

## 6. Monitoraggio

### 6.1 Log Applicazione

#### Backend Logs
```bash
# Se running con uvicorn diretto
# Output va a stdout

# Con Docker
docker logs -f papertrading-backend

# Con Gunicorn
tail -f /var/log/papertrading/access.log
tail -f /var/log/papertrading/error.log
```

#### Livelli Log
```
DEBUG   - Dettagli debugging
INFO    - Operazioni normali
WARNING - Situazioni anomale
ERROR   - Errori gestiti
```

### 6.2 Metriche Provider Dati

Accedi a: `GET /api/v1/providers/status`

```json
{
  "providers": {
    "alpaca": {
      "rate_limit": {"remaining": 180, "limit": 200},
      "health": {"is_healthy": true, "avg_latency_ms": 45.2},
      "budget": {"daily_limit": 1000, "daily_spent": 234}
    }
  },
  "total_providers": 14,
  "timestamp": "2025-12-07T10:30:00Z"
}
```

### 6.3 Health Check

```bash
# Endpoint health
curl http://localhost:8000/health

# Response
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2025-12-07T10:30:00Z"
}
```

### 6.4 Monitoraggio Docker

```bash
# Stato containers
docker ps

# Risorse utilizzate
docker stats

# Inspect container
docker inspect papertrading-postgres

# Eventi Docker
docker events --filter container=papertrading-postgres
```

### 6.5 Monitoraggio PostgreSQL

```sql
-- Connessioni attive
SELECT count(*) FROM pg_stat_activity;

-- Query lente (>1s)
SELECT query, calls, mean_time
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC;

-- Dimensione database
SELECT pg_size_pretty(pg_database_size('papertrading'));

-- Dimensione tabelle
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### 6.6 Monitoraggio Redis

```bash
# Info memoria
docker exec papertrading-redis redis-cli INFO memory

# Statistiche
docker exec papertrading-redis redis-cli INFO stats

# Client connessi
docker exec papertrading-redis redis-cli CLIENT LIST
```

---

## 7. Backup e Recovery

### 7.1 Strategia Backup

| Componente | Frequenza | Retention | Metodo |
|------------|-----------|-----------|--------|
| PostgreSQL | Giornaliero | 30 giorni | pg_dump |
| Redis | Giornaliero | 7 giorni | RDB snapshot |
| Configurazione | Ad ogni modifica | Illimitato | Git |
| Logs | Settimanale | 90 giorni | Rotazione |

### 7.2 Script Backup Automatico

Crea `/opt/papertrading/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/papertrading/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
docker exec papertrading-postgres pg_dump -U papertrading_user papertrading | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Backup Redis
docker exec papertrading-redis redis-cli BGSAVE
sleep 5
docker cp papertrading-redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Cleanup vecchi backup (>30 giorni)
find $BACKUP_DIR -name "postgres_*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "redis_*.rdb" -mtime +7 -delete

echo "Backup completato: $DATE"
```

### 7.3 Cron Job

```bash
# Edita crontab
crontab -e

# Aggiungi (backup alle 2:00 AM)
0 2 * * * /opt/papertrading/backup.sh >> /var/log/papertrading_backup.log 2>&1
```

### 7.4 Disaster Recovery

#### Scenario: Database Corrotto

```bash
# 1. Stop backend
pkill -f "uvicorn app.main"

# 2. Drop database
docker exec papertrading-postgres psql -U papertrading_user -c "DROP DATABASE papertrading;"
docker exec papertrading-postgres psql -U papertrading_user -c "CREATE DATABASE papertrading;"

# 3. Restore da backup
gunzip -c /opt/papertrading/backups/postgres_LATEST.sql.gz | docker exec -i papertrading-postgres psql -U papertrading_user -d papertrading

# 4. Restart backend
cd backend && source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 8. Troubleshooting

### 8.1 Problemi Comuni

#### Container non si avvia

```bash
# Verifica logs
docker logs papertrading-postgres

# Cause comuni:
# - Porta già in uso
# - Spazio disco insufficiente
# - Permessi file

# Soluzione porta in uso:
lsof -i :5432  # Trova processo
kill <PID>     # Termina processo
```

#### Database connection refused

```bash
# Verifica container running
docker ps | grep postgres

# Verifica network
docker network ls
docker network inspect papertrading_default

# Test connessione
docker exec papertrading-postgres pg_isready
```

#### Redis connection error

```bash
# Verifica container
docker ps | grep redis

# Test connessione
docker exec papertrading-redis redis-cli ping
# Deve rispondere: PONG

# Verifica memoria
docker exec papertrading-redis redis-cli INFO memory
```

#### Backend 500 Internal Server Error

```bash
# Verifica logs backend
# Se uvicorn:
# Guarda output terminale

# Se con Docker:
docker logs papertrading-backend

# Cause comuni:
# - DATABASE_URL errato
# - Migrazioni non applicate
# - Redis non raggiungibile
```

#### Frontend non si connette al backend

```bash
# Verifica CORS
# In backend/app/main.py assicurati che origine frontend sia in lista

# Verifica VITE_API_URL
# Deve puntare a http://localhost:8000 (non 127.0.0.1)

# Verifica network
curl http://localhost:8000/api/v1/
```

### 8.2 Comandi Diagnostici

```bash
# Stato sistema
docker-compose ps
docker stats

# Logs ultimi errori
docker logs --tail 100 papertrading-postgres 2>&1 | grep -i error
docker logs --tail 100 papertrading-redis 2>&1 | grep -i error

# Spazio disco
df -h
docker system df

# Connessioni database
docker exec papertrading-postgres psql -U papertrading_user -c "SELECT * FROM pg_stat_activity;"

# Test API
curl -v http://localhost:8000/health
```

### 8.3 Reset Completo

⚠️ **ATTENZIONE: Cancella tutti i dati**

```bash
# Stop tutto
docker-compose --env-file .env -f infrastructure/docker/docker-compose.dev.yml down -v

# Rimuovi volumi
docker volume prune -f

# Riavvia
docker-compose --env-file .env -f infrastructure/docker/docker-compose.dev.yml up -d

# Rerun migrations
cd backend && source venv/bin/activate
alembic upgrade head
```

---

## 9. Manutenzione

### 9.1 Aggiornamento Sistema

#### Aggiornamento Codice

```bash
# Pull ultime modifiche
git pull origin main

# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Frontend
cd frontend
npm install
npm run build

# Restart services
# ...
```

#### Aggiornamento Docker Images

```bash
# Pull nuove immagini
docker-compose pull

# Recreate containers
docker-compose up -d --force-recreate
```

### 9.2 Pulizia Periodica

```bash
# Pulizia Docker
docker system prune -f
docker volume prune -f

# Pulizia log vecchi
find /var/log/papertrading -name "*.log" -mtime +90 -delete

# Vacuum PostgreSQL
docker exec papertrading-postgres psql -U papertrading_user -d papertrading -c "VACUUM ANALYZE;"
```

### 9.3 Rotazione Log

File: `/etc/logrotate.d/papertrading`

```
/var/log/papertrading/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 root root
    sharedscripts
    postrotate
        systemctl reload papertrading 2>/dev/null || true
    endscript
}
```

### 9.4 Manutenzione Database

```sql
-- Vacuum e analyze (settimanale)
VACUUM ANALYZE;

-- Reindex (mensile)
REINDEX DATABASE papertrading;

-- Statistiche tabelle
SELECT schemaname, relname, n_live_tup, n_dead_tup, last_vacuum, last_analyze
FROM pg_stat_user_tables;
```

---

## 10. Sicurezza

### 10.1 Checklist Produzione

- [ ] Cambiare tutte le password di default
- [ ] Generare SECRET_KEY sicuro (256 bit)
- [ ] Disabilitare DEBUG mode
- [ ] Configurare HTTPS (certificato SSL)
- [ ] Configurare firewall (solo porte necessarie)
- [ ] Disabilitare pgAdmin/Redis Commander in produzione
- [ ] Backup automatici configurati
- [ ] Log rotation configurato
- [ ] Monitoraggio attivo

### 10.2 Firewall Rules (iptables)

```bash
# Permetti SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Permetti HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Blocca porte interne dall'esterno
iptables -A INPUT -p tcp --dport 5432 -j DROP  # PostgreSQL
iptables -A INPUT -p tcp --dport 6379 -j DROP  # Redis
iptables -A INPUT -p tcp --dport 8000 -j DROP  # Backend (dietro reverse proxy)
```

### 10.3 Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    
    # Frontend
    location / {
        root /var/www/papertrading/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 10.4 Hardening PostgreSQL

File: `postgresql.conf`

```
# Connessioni
listen_addresses = 'localhost'
max_connections = 100

# SSL
ssl = on
ssl_cert_file = '/etc/ssl/certs/server.crt'
ssl_key_file = '/etc/ssl/private/server.key'

# Logging
log_connections = on
log_disconnections = on
log_statement = 'ddl'
```

File: `pg_hba.conf`

```
# Solo connessioni locali
local   all   all                   md5
host    all   all   127.0.0.1/32    md5
host    all   all   ::1/128         md5
```

### 10.5 Audit Security

```bash
# Backend security scan
cd backend
pip install pip-audit bandit safety

# Audit dipendenze
pip-audit

# Static analysis
bandit -r app/

# Check vulnerabilità note
safety check
```

---

## 11. Contatti e Supporto

### 11.1 Repository
- GitHub: https://github.com/faux62/PaperTrading-Platform

### 11.2 Documentazione
- `/docs/01-ARCHITECTURE.md` - Architettura dettagliata
- `/docs/02-DEVELOPMENT-PLAN.md` - Piano sviluppo
- `/docs/GETTING_STARTED.md` - Quick start
- `/docs/SPECIFICHE-TECNICHE.md` - Specifiche tecniche
- `/docs/SPECIFICHE-FUNZIONALI.md` - Specifiche funzionali

---

**Versione documento:** 1.0  
**Ultimo aggiornamento:** 7 Dicembre 2025
