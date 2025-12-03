# 🔄 Setup Progetto su Nuovo Mac

Guida per continuare lo sviluppo di PaperTrading Platform su un Mac diverso.

---

## Scenario A: Volume Esterno (X9 Pro)

Se il progetto è su un volume esterno che colleghi al nuovo Mac.

### Passi

1. **Collega il volume X9 Pro** al nuovo Mac

2. **Apri VS Code** sulla cartella del progetto:
   ```
   /Volumes/X9 Pro/Sviluppo/Applicazioni/Finance/PaperTrading-Platform/
   ```

3. **Ricrea il Virtual Environment Python** (i path sono legati al Mac precedente):
   ```bash
   cd "/Volumes/X9 Pro/Sviluppo/Applicazioni/Finance/PaperTrading-Platform"
   
   # Rimuovi il vecchio venv
   rm -rf venv
   
   # Crea nuovo venv
   python3 -m venv venv
   source venv/bin/activate
   
   # Installa dipendenze
   pip install -r backend/requirements.txt
   ```

4. **Installa dipendenze frontend** (opzionale, se lavori sul frontend):
   ```bash
   cd frontend
   npm install
   ```

5. **Verifica che tutto funzioni**:
   ```bash
   # Backend tests
   cd backend
   source ../venv/bin/activate
   pytest tests/ -v --tb=short | tail -20
   
   # Frontend tests
   cd ../frontend
   npm test -- --run
   ```

### Tempo stimato: ~5 minuti

---

## Scenario B: Clone da GitHub

Se vuoi una copia su un disco diverso o non hai accesso al volume esterno.

### Prerequisiti sul nuovo Mac

- **Python 3.11+**: `brew install python@3.11`
- **Node.js 20+**: `brew install node@20`
- **Docker Desktop**: [Scarica da docker.com](https://www.docker.com/products/docker-desktop/)
- **Git**: `brew install git` (o già incluso con Xcode CLI tools)

### Passi

1. **Clona il repository**:
   ```bash
   cd ~/Sviluppo  # o dove preferisci
   git clone https://github.com/faux62/PaperTrading-Platform.git
   cd PaperTrading-Platform
   ```

2. **Crea il file `.env`** (non è su GitHub per sicurezza):
   ```bash
   cp .env.example .env
   # Modifica .env con le tue API keys
   ```

3. **Setup Python environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.txt
   ```

4. **Setup Frontend**:
   ```bash
   cd frontend
   npm install
   ```

5. **Verifica**:
   ```bash
   # Backend
   cd ../backend
   pytest tests/ -q
   
   # Frontend
   cd ../frontend
   npm test -- --run
   ```

### Tempo stimato: ~10 minuti

---

## 📋 File `.env` - API Keys

Il file `.env` contiene le API keys per i data provider. Se hai clonato da GitHub, devi ricrearlo.

**Contenuto minimo necessario:**
```env
# Application
SECRET_KEY=una-chiave-segreta-lunga
JWT_SECRET_KEY=unaltra-chiave-segreta

# Database (per Docker)
POSTGRES_USER=papertrading
POSTGRES_PASSWORD=papertrading
POSTGRES_DB=papertrading

# Data Providers (inserisci le tue)
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
FINNHUB_API_KEY=...
# ... altre API keys
```

Vedi `.env.example` per la lista completa.

---

## 🆘 Troubleshooting

### Errore: "command not found: python3"
```bash
brew install python@3.11
```

### Errore: "command not found: node"
```bash
brew install node@20
```

### Errore permessi Git
```bash
git config --global user.email "tua@email.com"
git config --global user.name "Tuo Nome"
```

### Docker non parte
Assicurati che Docker Desktop sia in esecuzione (icona nella barra menu).

---

## 📝 Riprendere lo Sviluppo

Quando apri una nuova chat con Copilot, puoi dire:

> "Ho il progetto PaperTrading-Platform aperto. Siamo alla Week 17 completata (deployment configurato). I prossimi passi sono: test E2E, popolamento dati reali, e deploy su NAS UGREEN."

L'AI leggerà i file del progetto e avrà tutto il contesto necessario.
