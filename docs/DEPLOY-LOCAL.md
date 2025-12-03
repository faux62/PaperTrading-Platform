# 🏠 Deploy Locale su Mac

Guida per eseguire PaperTrading Platform sulla rete locale domestica.

---

## Prerequisiti

- **Docker Desktop** installato e in esecuzione
- File **`.env`** configurato con le API keys

---

## Quick Start

```bash
cd /Volumes/X9\ Pro/Sviluppo/Applicazioni/Finance/PaperTrading-Platform
cd infrastructure/docker

# Avvia tutto
./deploy-local.sh start
```

Dopo ~1-2 minuti (prima volta richiede build), l'app sarà disponibile.

---

## Accesso all'Applicazione

### Da questo Mac
- **Frontend**: http://localhost
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Da altri dispositivi in rete (iPhone, iPad, altro Mac)
- **Frontend**: http://TUO_IP (es: http://192.168.1.100)
- **API**: http://TUO_IP:8000

Per trovare il tuo IP:
```bash
ipconfig getifaddr en0   # WiFi
# oppure
ipconfig getifaddr en1   # Ethernet
```

---

## Comandi Disponibili

```bash
cd infrastructure/docker

./deploy-local.sh start     # Avvia tutti i servizi
./deploy-local.sh stop      # Ferma tutti i servizi
./deploy-local.sh restart   # Riavvia tutto
./deploy-local.sh status    # Mostra stato servizi
./deploy-local.sh logs      # Mostra tutti i logs
./deploy-local.sh logs backend   # Logs solo backend
./deploy-local.sh logs frontend  # Logs solo frontend
./deploy-local.sh update    # Aggiorna e riavvia
./deploy-local.sh cleanup   # Rimuove tutto (container, volumi, immagini)
```

---

## Struttura Servizi

| Servizio | Container | Porta | Descrizione |
|----------|-----------|-------|-------------|
| Frontend | papertrading-frontend | 80 | React app (nginx) |
| Backend | papertrading-backend | 8000 | FastAPI |
| Database | papertrading-postgres | 5432 | PostgreSQL 15 |
| Cache | papertrading-redis | 6379 | Redis 7 |

---

## Prima Esecuzione

La prima volta che avvii:

1. **Docker scarica le immagini base** (~500MB)
2. **Builda le immagini** del progetto (~2-3 minuti)
3. **Avvia i container**

Le esecuzioni successive sono molto più veloci (~10 secondi).

---

## Persistenza Dati

I dati sono salvati in **Docker volumes**:
- `postgres_local_data` - Database PostgreSQL
- `redis_local_data` - Cache Redis

I dati **persistono** anche dopo `./deploy-local.sh stop`.

Per **eliminare tutti i dati** e ricominciare da zero:
```bash
./deploy-local.sh cleanup
```

---

## Configurazione Avanzata

### Cambiare porta frontend

Modifica `docker-compose.local.yml`:
```yaml
frontend:
  ports:
    - "8080:80"  # Cambia 80 con la porta desiderata
```

### Variabili d'ambiente

Il deploy locale legge le variabili da `../../.env` (root del progetto).

Variabili principali:
- `SECRET_KEY` - Chiave segreta applicazione
- `JWT_SECRET_KEY` - Chiave per token JWT
- `ALPACA_API_KEY`, `FINNHUB_API_KEY`, etc. - API keys provider

---

## Troubleshooting

### "Cannot connect to Docker daemon"
→ Avvia Docker Desktop

### "Port 80 already in use"
→ Qualcosa usa già la porta 80. Opzioni:
```bash
# Trova cosa usa la porta
lsof -i :80

# Oppure cambia porta in docker-compose.local.yml
```

### Container non parte
```bash
# Vedi logs dettagliati
./deploy-local.sh logs backend
```

### Ripartire da zero
```bash
./deploy-local.sh cleanup
./deploy-local.sh start
```

---

## Health Checks

Verifica che tutto funzioni:

```bash
# Status generale
./deploy-local.sh status

# Health backend
curl http://localhost:8000/health

# Readiness (verifica DB e Redis)
curl http://localhost:8000/ready

# Metriche
curl http://localhost:8000/metrics
```

---

## Fermare l'Applicazione

```bash
./deploy-local.sh stop
```

I dati rimangono salvati. Al prossimo `start` ritrovi tutto.
