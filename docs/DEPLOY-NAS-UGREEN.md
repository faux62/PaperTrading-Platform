# 🗄️ Deploy su NAS UGREEN

Guida per eseguire PaperTrading Platform su NAS UGREEN (UGOS).

---

## Prerequisiti

- **UGREEN NAS** con UGOS installato
- **Docker Manager** abilitato su UGOS
- Accesso al NAS via **SMB** o **SSH**

---

## Panoramica

UGREEN utilizza **UGOS** come sistema operativo, che include Docker Manager integrato.

| Caratteristica | Valore |
|----------------|--------|
| Web UI UGOS | https://IP_NAS:9443 |
| Porta 80 | ✅ Disponibile per l'app |
| Docker | Integrato in Docker Manager |
| Path dati | `/volume1/docker/` |

---

## Step 1: Copia il Progetto sul NAS

### Opzione A: Via SMB (Finder)

1. Apri **Finder** → **Vai** → **Connetti al server**
2. Inserisci: `smb://IP_NAS`
3. Accedi con le credenziali NAS
4. Crea cartella: `docker/papertrading/`
5. Copia l'intero progetto dentro

### Opzione B: Via SSH/SCP

```bash
# Dal Mac
scp -r /Volumes/X9\ Pro/Sviluppo/Applicazioni/Finance/PaperTrading-Platform/* \
    utente@IP_NAS:/volume1/docker/papertrading/
```

---

## Step 2: Configura l'Environment

1. Accedi al NAS via SSH o File Manager

2. Vai nella cartella del progetto:
   ```
   /volume1/docker/papertrading/
   ```

3. Copia il template environment:
   ```bash
   cp infrastructure/docker/.env.nas.example .env
   ```

4. Modifica `.env` con i tuoi valori:
   ```bash
   nano .env
   ```

### Configurazione `.env` minima:

```env
# IP del NAS
NAS_IP=192.168.1.50

# Porta (80 è libera su UGREEN)
FRONTEND_PORT=80

# Path dati
DATA_PATH=/volume1/docker/papertrading/data

# Sicurezza - CAMBIA QUESTE!
SECRET_KEY=genera-una-chiave-casuale-lunga
JWT_SECRET_KEY=genera-unaltra-chiave-casuale
POSTGRES_PASSWORD=password-sicura-db

# API Keys (inserisci le tue)
ALPACA_API_KEY=pk_xxx
ALPACA_SECRET_KEY=sk_xxx
FINNHUB_API_KEY=xxx
# ... altre keys
```

---

## Step 3: Crea la Cartella Dati

```bash
mkdir -p /volume1/docker/papertrading/data/postgres
mkdir -p /volume1/docker/papertrading/data/redis
```

---

## Step 4: Avvia con Docker Manager

### Via UGOS Web UI

1. Apri **https://IP_NAS:9443**
2. Vai in **Docker Manager**
3. Sezione **Compose** o **Project**
4. Clicca **Aggiungi** / **Create**
5. Seleziona la cartella `/volume1/docker/papertrading/`
6. Seleziona il file `infrastructure/docker/docker-compose.nas.yml`
7. Clicca **Avvia**

### Via SSH (alternativa)

```bash
cd /volume1/docker/papertrading
docker compose -f infrastructure/docker/docker-compose.nas.yml up -d
```

---

## Step 5: Verifica

Attendi ~2-3 minuti per il primo avvio, poi:

- **Frontend**: http://IP_NAS (porta 80)
- **API**: http://IP_NAS:8000
- **Health check**: http://IP_NAS:8000/health

---

## Accesso dall'Esterno (Opzionale)

### Da rete locale
Tutti i dispositivi sulla stessa rete possono accedere a `http://IP_NAS`

### Da fuori casa
Opzioni:
1. **Port forwarding** sul router (porta 80 → IP_NAS:80)
2. **VPN** verso la rete domestica
3. **Reverse proxy** con dominio (più complesso)

⚠️ Se esponi all'esterno, assicurati di usare HTTPS!

---

## Gestione Container

### Via UGOS Docker Manager
- Usa l'interfaccia web per start/stop/logs

### Via SSH

```bash
cd /volume1/docker/papertrading

# Stato
docker compose -f infrastructure/docker/docker-compose.nas.yml ps

# Logs
docker compose -f infrastructure/docker/docker-compose.nas.yml logs -f

# Stop
docker compose -f infrastructure/docker/docker-compose.nas.yml down

# Restart
docker compose -f infrastructure/docker/docker-compose.nas.yml restart
```

---

## Risorse e Limiti

La configurazione NAS ha limiti di risorse per non sovraccaricare il NAS:

| Servizio | CPU | RAM |
|----------|-----|-----|
| Backend | 1 core | 1 GB |
| Frontend | 0.5 core | 256 MB |
| PostgreSQL | 0.5 core | 512 MB |
| Redis | 0.25 core | 128 MB |

**Totale**: ~2.25 core, ~2 GB RAM

Se il tuo NAS ha più risorse, puoi aumentare i limiti in `docker-compose.nas.yml`.

---

## Persistenza Dati

I dati sono salvati in:
```
/volume1/docker/papertrading/data/
├── postgres/    # Database
└── redis/       # Cache
```

Questi dati **persistono** anche dopo riavvio del NAS o dei container.

### Backup

```bash
# Backup database
docker exec papertrading-postgres pg_dump -U papertrading papertrading > backup.sql

# Backup completo cartella dati
tar -czf papertrading-backup.tar.gz /volume1/docker/papertrading/data/
```

---

## Aggiornamenti

Quando aggiorni il codice:

```bash
cd /volume1/docker/papertrading

# Aggiorna codice (se usi git sul NAS)
git pull

# Ricostruisci e riavvia
docker compose -f infrastructure/docker/docker-compose.nas.yml up -d --build
```

---

## Troubleshooting

### Container non parte
```bash
# Vedi logs
docker compose -f infrastructure/docker/docker-compose.nas.yml logs backend
```

### "Permission denied" sui volumi
```bash
# Assicurati che le cartelle dati esistano con permessi corretti
chmod -R 755 /volume1/docker/papertrading/data
```

### Porta già in uso
Modifica `FRONTEND_PORT` nel file `.env` (es: 8080)

### Database non si connette
Verifica che `POSTGRES_PASSWORD` in `.env` sia corretto e che il volume postgres esista.

### Performance lente
- Riduci `--workers` in backend Dockerfile (da 4 a 2)
- Verifica risorse disponibili sul NAS

---

## Struttura File sul NAS

```
/volume1/docker/papertrading/
├── backend/                 # Codice backend
├── frontend/                # Codice frontend
├── infrastructure/
│   └── docker/
│       ├── docker-compose.nas.yml
│       └── .env.nas.example
├── data/                    # Dati persistenti
│   ├── postgres/
│   └── redis/
├── .env                     # TUE configurazioni
└── ...
```

---

## Prossimi Passi dopo il Deploy

1. **Accedi** a http://IP_NAS
2. **Registra** un utente
3. **Configura** watchlist e portafogli
4. I **dati di mercato** inizieranno ad arrivare automaticamente (se hai configurato le API keys)
