# 📈 Guida Operativa Giornaliera - PaperTrading Platform

> **Versione**: 2.2  
> **Ultimo aggiornamento**: 31 Dicembre 2025  
> **Autore**: Sistema PaperTrading  
> **Novità v2.2**: Trade Candidates Panel (automazione FASE 1)  
> **Novità v2.1**: Filtro regionale ML, Schedule notifiche, Limite ordini giornaliero

---

## 📧 Sistema di Notifiche Automatiche

La piattaforma invia automaticamente email per i momenti importanti della giornata di trading. 
Per attivare le notifiche, vai su **Impostazioni** → **Notifiche** e abilita le opzioni desiderate.

### 📬 Notifiche Programmate

| Orario (CET) | Notifica | Contenuto |
|--------------|----------|-----------|
| **07:00** | 🌅 Morning Briefing | Riepilogo portfolio + Top 5 segnali ML |
| **08:45** | 🔔 Alert Apertura EU | Mercati europei aprono tra 15 min |
| **15:15** | 🔔 Alert Apertura US | Mercati USA aprono tra 15 min |

### 🚨 Notifiche in Tempo Reale

| Evento | Descrizione |
|--------|-------------|
| 🛑 **Stop-Loss Triggered** | Quando uno stop-loss viene attivato |
| 🎯 **Take-Profit Reached** | Quando raggiungi il tuo obiettivo di prezzo |
| 🤖 **ML Signal Alert** | Segnali ML ad alta confidenza (>70%) |

### ⚙️ Come Configurare le Notifiche

1. Vai su **⚙️ Impostazioni** → **Notifiche**
2. Abilita "Email Notifications"
3. Seleziona quali notifiche ricevere:
   - ✅ Trade Execution
   - ✅ Price Alerts
   - ✅ Portfolio Updates
   - ✅ Market News

### 🕐 Schedule Personalizzato (Novità v2.1)

Puoi ora configurare **quando** ricevere le notifiche:

1. **Finestra Oraria**: Imposta l'orario di inizio e fine (es: 07:00 - 22:00)
2. **Giorni Attivi**: Seleziona i giorni della settimana
   - Default: Lun-Ven (giorni di mercato)
   - Puoi aggiungere Sab/Dom per notifiche di riepilogo

```
⚙️ Settings → Preferences → Notification Schedule
├── Time Range: [07:00] to [22:00]
└── Active Days: [L] [M] [M] [G] [V] [ ] [ ]
```

---

## 📚 Glossario dei Termini Finanziari

Prima di iniziare, familiarizza con questi termini che userai quotidianamente:

### Termini Base

| Termine | Spiegazione Semplice |
|---------|---------------------|
| **P&L (Profit & Loss)** | Profitto o Perdita - quanto hai guadagnato o perso |
| **Portfolio** | L'insieme di tutti i tuoi investimenti |
| **Position** | Un singolo investimento in un'azione (es: "ho una posizione in Apple") |
| **BUY** | Acquisto - compri un'azione sperando che salga |
| **SELL** | Vendita - vendi un'azione che possiedi |
| **Long** | Quando possiedi un'azione (hai comprato) |
| **Short** | Quando scommetti che un'azione scenderà (avanzato, non usarlo all'inizio) |

### Tipi di Ordini

| Termine | Spiegazione |
|---------|-------------|
| **Market Order** | Compri/vendi subito al prezzo corrente. Veloce ma potresti pagare più del previsto |
| **Limit Order** | Compri/vendi solo se il prezzo raggiunge quello che hai deciso tu. Più sicuro |
| **Stop-Loss** | Ordine automatico che vende se il prezzo scende troppo. Ti protegge dalle perdite |
| **Take-Profit** | Ordine automatico che vende quando raggiungi il guadagno desiderato |
| **Trailing Stop** | Stop-loss che si muove automaticamente quando il prezzo sale, proteggendo i guadagni |

### Indicatori e Analisi

| Termine | Spiegazione |
|---------|-------------|
| **Volatilità** | Quanto "nervoso" è un titolo - se si muove molto è volatile |
| **ATR (Average True Range)** | Misura la volatilità media - quanto si muove tipicamente il prezzo ogni giorno |
| **Trend** | La direzione generale del prezzo (sale = uptrend, scende = downtrend) |
| **Supporto** | Livello di prezzo dove tipicamente smette di scendere |
| **Resistenza** | Livello di prezzo dove tipicamente smette di salire |
| **RSI** | Indica se un'azione è "ipercomprata" (troppo cara) o "ipervenduta" (occasione) |
| **Bollinger Bands** | Bande che mostrano se il prezzo è "normale" o estremo |

### Termini ML (Machine Learning)

| Termine | Spiegazione |
|---------|-------------|
| **Signal** | Suggerimento del modello ML: BUY (compra), SELL (vendi), HOLD (tieni) |
| **Confidence** | Quanto è sicuro il modello del suo suggerimento (0-100%) |
| **Accuracy** | Percentuale di previsioni corrette del modello |
| **Horizon** | Periodo di previsione (es: 5 giorni = il modello prevede cosa succederà in 5 giorni) |

---

## ⏰ Orari dei Mercati (Ora Italiana CET/CEST)

```
                    00:00                    12:00                    24:00
                      |                        |                        |
🇯🇵 Tokyo      ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
                01:00-07:00

🇭🇰 Hong Kong  ░░████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
                02:30-09:00

🇪🇺 Europa     ░░░░░░░░░░░░░░░░░░████████████████████░░░░░░░░░░░░░░░░░░
                                09:00-17:30

🇬🇧 Londra     ░░░░░░░░░░░░░░░░░░████████████████████░░░░░░░░░░░░░░░░░░
                                09:00-17:30

🇺🇸 New York   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██████████████░░░░░░░░░░░░
                                            15:30-22:00
```

### Momenti Chiave della Giornata

| Ora (CET) | Evento | Importanza |
|-----------|--------|------------|
| 07:00 | Pre-apertura EU - Analisi overnight | ⭐⭐⭐ |
| 09:00 | Apertura mercati EU | ⭐⭐⭐⭐ |
| 09:00-09:30 | Prima mezz'ora EU - Alta volatilità | ⚠️ Evita trading |
| 14:30 | Dati economici USA (spesso) | ⭐⭐⭐ |
| 15:30 | Apertura Wall Street | ⭐⭐⭐⭐⭐ |
| 15:30-16:00 | Prima mezz'ora USA - Altissima volatilità | ⚠️ Evita trading |
| 17:30 | Chiusura mercati EU | ⭐⭐⭐ |
| 22:00 | Chiusura Wall Street | ⭐⭐⭐⭐ |

---

## 📅 Routine Giornaliera Dettagliata

### 🌅 FASE 1: Pre-Apertura (07:00 - 09:00)

#### 07:00 - Caffè e Analisi Overnight ☕

**Cosa fare:**
1. **Apri la Dashboard** → vai su "Portfolio Overview"
2. **Controlla il P&L overnight**:
   - I mercati asiatici hanno chiuso da poco
   - Il mercato USA ha chiuso ieri sera
   - Cerca movimenti importanti nelle tue posizioni

**Dove guardare:**
```
Dashboard → Stats Grid (prima riga)
├── 📊 Daily Change    → Variazione % da apertura mercato oggi
├── 🌙 Overnight Change → Variazione % durante la notte (chiusura ieri → apertura oggi)
├── Total Value        → Valore totale portfolio
└── Open P&L           → Profitto/perdita posizioni aperte
```

**Come interpretare:**
- **Daily Change** negativo + **Overnight Change** positivo = mercato EU/US sta vendendo oggi
- **Daily Change** positivo + **Overnight Change** negativo = recupero intraday dopo gap down
- Entrambi negativi = giornata difficile, considera riduzione esposizione

**Domande da farti:**
- ✅ Ci sono posizioni che hanno perso più del 2% stanotte?
- ✅ Qualche stop-loss si è attivato?
- ✅ Ci sono notizie importanti su titoli che possiedo?

### 🔔 Morning Alerts Panel (Novità v2.1)

Il pannello **Morning Alerts** nella Dashboard risponde automaticamente a queste domande:

```
Dashboard → Morning Alerts
├── 🔴 URGENT: Posizioni con perdita > 5% (azione immediata)
├── 🟠 HIGH: Posizioni con perdita > 2% (monitorare)
├── 🟢 MEDIUM: Posizioni con profitto > 5% (trailing stop)
└── ✅ "All positions healthy" se tutto ok
```

**Cosa mostra:**
| Tipo Alert | Colore | Significato | Azione Suggerita |
|------------|--------|-------------|------------------|
| Critical Loss | 🔴 Rosso | Perdita > 5% | Considera chiusura immediata |
| Loss Warning | 🟠 Arancio | Perdita > 2% | Monitorare, verifica stop-loss |
| Profit Alert | 🟢 Verde | Profitto > 5% | Imposta trailing stop |

### 🎯 Trade Candidates Panel (Novità v2.2)

Il pannello **Trade Candidates** automatizza completamente la preparazione degli ordini!

```
Dashboard → Trade Candidates
├── 🎯 3-5 candidati selezionati automaticamente dal ML
├── 📊 Entry Price, Stop-Loss, Take-Profit pre-calcolati
├── 📦 Quantità suggerita (5% del portfolio)
└── ⚖️ Risk/Reward Ratio
```

**Come funziona:**
1. Il sistema analizza tutti i simboli nel Market Universe
2. Genera previsioni ML per ciascuno
3. Seleziona i top 3-5 candidati con confidence > 60%
4. Calcola automaticamente tutti i parametri di trading

**Cosa mostra ogni candidato:**
| Campo | Descrizione |
|-------|-------------|
| Symbol | Titolo con regione (es: SAP.DE) |
| Confidence | Sicurezza ML (60-100%) |
| Entry Price | Prezzo suggerito per entrare |
| Stop-Loss | Prezzo di uscita in perdita (-3% EU, -4% US) |
| Take-Profit | Prezzo obiettivo (+6% EU, +8% US) |
| Shares | Numero azioni da comprare |
| R:R Ratio | Risk/Reward (es: 1:2 = rischi 1 per guadagnare 2) |

**Come usarlo:**
1. **Clicca sul candidato** → Vai automaticamente alla pagina Trading
2. **Verifica i parametri** → Form già compilato con tutti i valori
3. **Conferma l'ordine** → Click su "Place Buy Order"

> 💡 **Tip**: Il pannello mostra un filtro EU/US per concentrarti sul mercato che sta per aprire!

#### 07:30 - Analisi Segnali ML 🤖 (Opzionale)

**Cosa fare:**
1. Vai su **ML Insights** → Tab **"Signals"**
2. **Usa il filtro regionale** (Novità v2.1):
   - Seleziona **"EU"** dal dropdown per mercati europei
   - Seleziona **"US"** per mercati americani
   - Seleziona **"Asia"** per mercati asiatici
   - Seleziona **"All"** per vedere tutto

```
ML Insights → Signals
├── Region Filter: [All ▼] [US] [EU] [Asia]
└── Lista segnali filtrata automaticamente
```

3. **Cerca segnali interessanti**:
   - Signal = **BUY**
   - Confidence > **60%**
   - Trend = **UP** o **NEUTRAL**

**Come interpretare i segnali:**

| Confidence | Significato | Azione Suggerita |
|------------|-------------|------------------|
| > 75% | Segnale forte | Considera seriamente |
| 60-75% | Segnale moderato | Valuta con altri fattori |
| 50-60% | Segnale debole | Solo se altri indicatori confermano |
| < 50% | Incerto | Evita |

**📝 Annota i tuoi top 3-5 candidati per oggi:**
```
Esempio:
1. SAP.DE - BUY 72% - Settore Tech in ripresa
2. ENEL.MI - BUY 65% - Utilities stabili
3. LVMH.PA - BUY 68% - Lusso forte in Asia
```

> 💡 **Nota v2.2**: Il pannello Trade Candidates fa già questo lavoro automaticamente!
> Usa ML Insights solo se vuoi esplorare segnali aggiuntivi.

#### 08:30 - Preparazione Ordini 📋 (Automatizzata v2.2)

**Con Trade Candidates (consigliato):**
1. Vai su **Dashboard** → **Trade Candidates**
2. Clicca sul candidato che ti interessa
3. Verifica i parametri pre-compilati nella pagina Trading
4. Conferma l'ordine

**Manualmente (se preferisci):**
1. Per ogni candidato, definisci:
   - **Prezzo di entrata** (usa Limit Order, non Market!)
   - **Stop-Loss** (massimo -3% dal prezzo di entrata)
   - **Take-Profit** (obiettivo +5% a +10%)

**Formula semplice per Position Sizing:**
```
Capitale da investire = Portfolio Totale × 5%

Esempio:
- Portfolio: €100.000
- Max per singolo trade: €5.000
- Se azione costa €50, compra max 100 azioni
```

> 💡 **Nota v2.2**: Il Trade Candidates Panel calcola tutto questo automaticamente!

---

### 🌞 FASE 2: Apertura Europa (09:00 - 12:00)

#### 09:00-09:30 - ⚠️ ATTENZIONE: Non Tradare!

**Perché evitare i primi 30 minuti:**
- Altissima volatilità
- Spread (differenza buy/sell) molto ampi
- Movimenti "falsi" che poi rientrano
- I professionisti stanno "testando" il mercato

**Cosa fare invece:**
- Osserva come si muovono i tuoi candidati
- Nota se aprono sopra o sotto la chiusura di ieri
- Prepara gli ordini ma NON inviarli ancora

#### 09:30 - Finestra Operativa EU 🎯

**Adesso puoi operare!**

1. **Controlla il sentiment generale**:
   - Gli indici (DAX, FTSE MIB, CAC40) sono in rialzo?
   - Se mercato generale è negativo, riduci l'esposizione

2. **Inserisci i tuoi ordini Limit**:
   - Vai su **Trading** → **New Order**
   - Seleziona il simbolo
   - Tipo: **LIMIT** (mai Market in apertura!)
   - Prezzo: leggermente sotto il prezzo attuale per BUY
   - Quantità: rispetta il position sizing (max 5% portfolio)

3. **Imposta Stop-Loss automatico**:
   - Subito dopo l'acquisto
   - -3% dal prezzo di entrata
   - Esempio: comprato a €100 → stop-loss a €97

### ⚠️ Limite Ordini Giornaliero (Novità v2.1)

La piattaforma implementa un **limite di 10 ordini al giorno** per promuovere trading disciplinato:

```
Trading Page
├── Counter: "Orders Today: 3/10"
├── Warning (7-9 ordini): Banner giallo "Approaching daily limit"
└── Blocked (10 ordini): Banner rosso "Daily limit reached"
```

**Perché questo limite:**
- Evita l'overtrading impulsivo
- Forza una selezione più accurata dei trade
- Riduce i costi di commissione
- Migliora la qualità decisionale

**Suggerimento:** Se raggiungi spesso il limite, potresti star facendo troppi trade. 
I trader professionisti raramente fanno più di 3-5 trade al giorno.

#### 11:00 - Check di Metà Mattina 📊

**Cosa controllare:**
1. **Portfolio** → Le posizioni aperte stamattina
2. **Orders** → Gli ordini limit sono stati eseguiti?
3. **Signals** → Ci sono nuovi segnali ML?

---

### 🍽️ FASE 3: Pausa Pranzo (12:00 - 14:30)

#### 12:00 - Review e Pranzo 🥗

**Quick check (5 minuti):**
1. Come stanno le posizioni EU?
2. Ci sono stop-loss vicini all'attivazione?
3. Qualche posizione è già in profitto > 2%?

**Se posizione in profitto > 2%:**
- Considera di alzare lo stop-loss a break-even (prezzo di entrata)
- Questo ti garantisce di non perdere soldi su quel trade

**Esempio Trailing Stop:**
```
Comprato a: €100
Attuale: €103 (+3%)
Nuovo Stop-Loss: €100 (break-even)

Se sale a €105 (+5%):
Nuovo Stop-Loss: €102 (+2% garantito)
```

---

### 🇺🇸 FASE 4: Apertura USA (14:30 - 18:00)

#### 14:30 - Pre-Apertura Wall Street 📰

**Cosa fare:**
1. **Controlla i futures USA** (indicano come aprirà il mercato):
   - S&P 500 futures
   - Nasdaq futures
   - Se negativi, mercato aprirà in ribasso

2. **Vai su ML Insights → Segnali USA**:
   - Simboli SENZA suffisso (AAPL, MSFT, GOOGL, etc.)
   - Filtra: BUY, Confidence > 60%

3. **Attenzione ai dati economici**:
   - Alle 14:30 spesso escono dati USA importanti
   - Possono causare forti movimenti

#### 15:30 - Apertura Wall Street 🔔

**⚠️ STESSA REGOLA: Evita i primi 15-30 minuti!**

La volatilità all'apertura USA è ancora più alta che in EU.

#### 16:00 - Finestra Operativa USA 🎯

**Adesso puoi operare sui titoli USA!**

1. **Verifica che i segnali ML siano ancora validi**
2. **Inserisci ordini Limit**
3. **Imposta Stop-Loss**

**Regola importante per USA:**
- I titoli USA si muovono PIÙ VELOCEMENTE di quelli EU
- Usa stop-loss leggermente più ampi (-4% invece di -3%)
- Oppure riduci la dimensione della posizione

#### 17:30 - Chiusura Europa 🇪🇺

**Cosa fare:**
1. **Review posizioni EU**:
   - Chiudi i day-trade (posizioni aperte oggi)
   - Mantieni gli swing-trade (posizioni per 2-5 giorni)

2. **Decisione per ogni posizione EU:**

| Situazione | Azione |
|------------|--------|
| In profitto > 3% | Considera di chiudere o alzare stop |
| In profitto 0-3% | Mantieni con stop a break-even |
| In perdita < 2% | Mantieni, stop già impostato |
| In perdita > 2% | Lo stop dovrebbe già aver chiuso |

---

### 🌙 FASE 5: Sera (18:00 - 22:00)

#### 18:00 - Monitoraggio USA 📱

**Check ogni ora:**
- Come vanno le posizioni USA?
- Ci sono notizie importanti?
- Stop-loss attivati?

**Non serve stare incollato allo schermo!**
Gli stop-loss lavorano per te automaticamente.

#### 21:30 - Pre-Chiusura USA ⏰

**Cosa fare:**
1. **Decidi cosa tenere overnight**:
   - Posizioni USA in profitto: considera di chiudere
   - Posizioni USA con segnale forte: puoi tenere

2. **Prepara la watchlist per domani**:
   - ML Insights → segnali con horizon 5 giorni
   - Annota i simboli più promettenti

#### 22:00 - Chiusura Wall Street 🔔

**Routine di fine giornata:**

1. **Screenshot del Portfolio** (opzionale ma utile per tracking)
2. **Annota:**
   - P&L del giorno
   - Trade migliore
   - Trade peggiore
   - Lezioni apprese

3. **Controlla il Daily Summary** (email automatica)

---

## 📊 Dashboard ML Insights - Come Usarla

### Tab "Signals" - I Suggerimenti del Modello

**Cosa mostra:**
- Lista di azioni con previsione BUY/SELL/HOLD
- Confidence (sicurezza) del modello
- Trend attuale del prezzo

**Come filtrare:**
1. **Per mercato**: Usa il suffisso del simbolo
2. **Per confidence**: Solo > 60%
3. **Per segnale**: Focus su BUY quando mercato positivo

**Esempio di lettura:**
```
AAPL | BUY | 72% | Trend: UP | Horizon: 5d

Significato:
- Il modello prevede che AAPL salirà nei prossimi 5 giorni
- È sicuro al 72% (buono)
- Il trend attuale è già in salita (conferma)
```

### Tab "Models" - Salute del Modello

**Cosa controllare:**
- **Accuracy**: Dovrebbe essere > 55%
- **Last Training**: Data ultimo addestramento
- **Samples**: Quanti dati ha usato

**Se accuracy < 50%:**
Il modello non sta funzionando bene. Evita di seguire i segnali finché non migliora.

### Tab "Features" - Cosa Guida le Previsioni

**Le top features ti dicono:**
- Quali indicatori sono più importanti ora
- Come "ragiona" il modello

**Esempio:**
```
1. ATR (15%) - Il modello guarda molto la volatilità
2. RSI (10%) - Considera se azioni sono ipercomprate/vendute
3. SMA_50 (8%) - Guarda il trend di medio periodo
```

---

## 📋 Checklist Giornaliere

### ✅ Checklist Mattina (07:00)
- [ ] Controllato P&L overnight
- [ ] Verificato Morning Alerts
- [ ] Verificato stop-loss ancora attivi
- [ ] Controllato Trade Candidates Panel
- [ ] (Opzionale) Analizzato segnali ML aggiuntivi

> 💡 **v2.2**: Il Trade Candidates Panel prepara automaticamente candidati con position sizing e prezzi!

### ✅ Checklist Apertura EU (09:30)
- [ ] Aspettato 30 minuti dopo apertura
- [ ] Controllato sentiment mercato generale
- [ ] Inserito ordini Limit (non Market!)
- [ ] Impostato Stop-Loss per ogni ordine

### ✅ Checklist Apertura USA (16:00)
- [ ] Controllato futures prima dell'apertura
- [ ] Analizzato segnali ML per USA
- [ ] Aspettato 15-30 minuti dopo apertura
- [ ] Inserito ordini con stop-loss

### ✅ Checklist Sera (22:00)
- [ ] Chiuso day-trade EU
- [ ] Deciso cosa tenere overnight USA
- [ ] Annotato P&L giornaliero
- [ ] Preparato watchlist per domani
- [ ] Letto Daily Summary email

---

## 📅 Routine Settimanale

### Venerdì Sera - Review Settimanale

**Cosa fare:**
1. **Leggi il Weekly Report** (email automatica)
2. **Calcola le statistiche**:
   - Win rate (% trade vincenti)
   - Profitto medio per trade
   - Perdita media per trade
   - P&L totale settimana

3. **Analizza gli errori**:
   - Quali trade sono andati male?
   - Perché?
   - Come evitarlo in futuro?

4. **Pianifica la settimana prossima**:
   - Ci sono earnings importanti? (report trimestrali aziende)
   - Dati economici in uscita?
   - Festività che chiudono mercati?

### Weekend - NO TRADING

**Cosa fare nel weekend:**
- 📚 Studia (libri, corsi, articoli)
- 📊 Analizza i grafici senza fretta
- 📝 Aggiorna il tuo diario di trading
- 🧘 Riposa la mente

**Cosa NON fare:**
- ❌ Preoccuparti delle posizioni aperte
- ❌ Cercare "il trade perfetto" per lunedì
- ❌ Fare overanalysis

---

## ⚠️ Regole d'Oro (Da Stampare!)

### 1. Gestione del Rischio

```
┌─────────────────────────────────────────────────────────┐
│  REGOLA DEL 2% - MAI RISCHIARE PIÙ DEL 2% PER TRADE   │
│                                                         │
│  Portfolio: €100.000                                    │
│  Max rischio per trade: €2.000                          │
│  Se stop-loss è -4%, max posizione = €50.000            │
└─────────────────────────────────────────────────────────┘
```

### 2. Position Sizing
- **Max 5%** del portfolio per singola posizione
- **Max 10 posizioni** aperte contemporaneamente
- **Max 25%** in un singolo settore

### 3. Stop-Loss SEMPRE
- Imposta PRIMA di entrare
- NON spostarlo mai verso il basso
- Se scatta, accetta la perdita

### 4. Orari da Evitare
- ❌ Primi 30 min apertura EU (09:00-09:30)
- ❌ Primi 15-30 min apertura USA (15:30-16:00)
- ❌ Ultimi 15 min di mercato
- ❌ Durante annunci importanti

### 5. Psicologia
- 😤 Arrabbiato? NON tradare
- 😰 Ansioso? Riduci le posizioni
- 🎉 Euforico dopo un gain? Fermati
- 😢 Dopo una perdita? Pausa di 1 giorno

---

## 📧 Sistema di Notifiche

La piattaforma ti invierà automaticamente:

| Notifica | Quando | Cosa Contiene |
|----------|--------|---------------|
| 🌅 **Morning Briefing** | 07:00 | Riepilogo overnight, segnali top |
| 📈 **Trade Executed** | Subito | Conferma esecuzione ordine |
| 🔔 **Price Alert** | Al trigger | Prezzo raggiunto target |
| ⚠️ **Stop-Loss Alert** | Al trigger | Posizione chiusa automaticamente |
| 📊 **Daily Summary** | 22:30 | P&L giorno, performance |
| 📅 **Weekly Report** | Venerdì 18:00 | Riepilogo settimana |

**Per configurare le notifiche:**
Settings → Notifications → Abilita quelle desiderate

---

## 🆘 Troubleshooting Comune

### "Il segnale ML era BUY ma il prezzo è sceso"
- Il modello ha accuracy ~57%, quindi sbaglia ~43% delle volte
- È normale! Per questo usi sempre lo stop-loss
- Non seguire MAI un segnale senza stop-loss

### "Ho perso su 3 trade di fila"
- È statiscamente normale (succede anche ai professionisti)
- NON aumentare le dimensioni per "recuperare"
- Rivedi la strategia ma non in panico

### "Non so se vendere una posizione in profitto"
- Usa il trailing stop: proteggi i guadagni automaticamente
- Oppure vendi metà posizione e lascia correre il resto

### "Il mercato si muove troppo velocemente"
- Usa SOLO ordini Limit, mai Market
- Definisci i prezzi PRIMA dell'apertura
- Se non riesci a stare dietro, riduci il numero di trade

---

## 📞 Supporto

Per problemi tecnici con la piattaforma:
- Controlla i log: `docker logs papertrading-backend`
- Riavvia i servizi: `docker compose --profile full restart`
- Verifica connessione API: Dashboard → Settings → API Status

---

*Buon Trading! 📈*

*Ricorda: Il paper trading è per imparare. Non rischiare mai soldi veri finché non sei consistentemente profittevole per almeno 3-6 mesi.*
