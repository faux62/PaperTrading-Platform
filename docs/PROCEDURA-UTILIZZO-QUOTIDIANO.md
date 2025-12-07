# 📋 Procedura Standard per l'Utilizzo Quotidiano

**Versione:** 1.0  
**Data:** 7 Dicembre 2025  
**Destinatari:** Trader, Utenti della piattaforma

---

## Indice

1. [Panoramica](#1-panoramica)
2. [Routine Pre-Market](#2-routine-pre-market)
3. [Operatività Durante le Sessioni](#3-operatività-durante-le-sessioni)
4. [Gestione Portfolio](#4-gestione-portfolio)
5. [Utilizzo degli Alert](#5-utilizzo-degli-alert)
6. [Analisi e Report](#6-analisi-e-report)
7. [Routine Post-Market](#7-routine-post-market)
8. [Procedure Settimanali](#8-procedure-settimanali)
9. [Best Practices](#9-best-practices)
10. [Checklist Operative](#10-checklist-operative)

---

## 1. Panoramica

### 1.1 Scopo del Documento

Questa guida fornisce le procedure standardizzate per l'utilizzo quotidiano della piattaforma PaperTrading. L'obiettivo è massimizzare l'efficacia del paper trading come strumento di apprendimento e testing delle strategie.

### 1.2 Fasi della Giornata di Trading

```
┌─────────────────────────────────────────────────────────────────┐
│                    GIORNATA DI TRADING                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  06:00-09:30    │ PRE-MARKET PREPARATION                       │
│  ─────────────  │ • Review overnight news                       │
│                 │ • Check pre-market movers                     │
│                 │ • Review alerts triggered                     │
│                 │ • Plan today's trades                         │
│                                                                 │
│  09:30-16:00    │ MARKET HOURS (US)                             │
│  ─────────────  │ • Execute planned trades                      │
│                 │ • Monitor positions                           │
│                 │ • Adjust stop-loss/take-profit               │
│                 │ • React to market events                      │
│                                                                 │
│  16:00-18:00    │ POST-MARKET REVIEW                            │
│  ─────────────  │ • Review today's trades                       │
│                 │ • Update journal                              │
│                 │ • Analyze performance                         │
│                 │ • Prepare next day                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Orari di Mercato di Riferimento

| Mercato | Apertura (locale) | Chiusura (locale) | Orario Italia |
|---------|-------------------|-------------------|---------------|
| US (NYSE/NASDAQ) | 09:30 | 16:00 | 15:30 - 22:00 |
| Pre-Market US | 04:00 | 09:30 | 10:00 - 15:30 |
| After-Hours US | 16:00 | 20:00 | 22:00 - 02:00 |

---

## 2. Routine Pre-Market

### 2.1 Accesso alla Piattaforma (06:00-07:00)

#### Step 1: Login
1. Accedi a http://localhost:5173 (dev) o https://yourdomain.com (prod)
2. Inserisci email e password
3. Verifica che la sessione sia attiva

#### Step 2: Verifica Sistema
1. Controlla lo stato dei provider dati nel footer o in **Settings > Provider Status**
2. Assicurati che almeno 2-3 provider siano attivi
3. Verifica la connessione WebSocket (indicatore verde in alto a destra)

### 2.2 Review Alert Notturni (07:00-08:00)

#### Step 1: Accedi alla sezione Alert
1. Naviga a **Dashboard** 
2. Controlla il pannello "Active Alerts" per notifiche trigger

#### Step 2: Analizza gli Alert Scattati
Per ogni alert triggerato:
1. **Note il simbolo** e il tipo di alert
2. **Verifica il grafico** del titolo
3. **Decidi l'azione**: 
   - Aggiungere alla watchlist per monitoraggio
   - Pianificare un trade
   - Ignorare se non più rilevante

#### Step 3: Gestione Alert
```
Alert Scattato → Verifica Grafico → Decisione:
                                    ├── Trade pianificato → Aggiungi a Trade Plan
                                    ├── Watchlist → Aggiungi a watchlist attiva
                                    └── Ignora → Disattiva alert
```

### 2.3 Analisi Pre-Market (08:00-09:00)

#### Step 1: Controlla i Top Movers
1. Vai a **Markets**
2. Seleziona la tab "Gainers/Losers"
3. Identifica i titoli con movimenti significativi (>3%)

#### Step 2: Review Watchlist
1. Apri la tua watchlist principale
2. Per ogni titolo:
   - Controlla prezzo corrente vs chiusura precedente
   - Verifica volumi pre-market
   - Controlla se ci sono news

#### Step 3: Consulta ML Predictions (Opzionale)
1. Naviga a **ML Insights**
2. Genera predizioni per i titoli nella watchlist
3. Nota le predizioni > 60% confidence

### 2.4 Piano di Trading Giornaliero (09:00-09:30)

#### Step 1: Definisci i Trade del Giorno
Crea una lista di trade pianificati:

| Simbolo | Direzione | Entry | Stop-Loss | Take-Profit | Size | Rationale |
|---------|-----------|-------|-----------|-------------|------|-----------|
| AAPL | Long | $185.00 | $183.00 | $190.00 | 50 | Breakout pattern |
| NVDA | Long | $140.00 | $137.00 | $148.00 | 30 | ML signal |

#### Step 2: Calcola il Risk
Per ogni trade pianificato:
- **Risk per trade**: Non più del 2% del portfolio
- **Verifica margin**: Assicurati di avere capitale sufficiente

#### Step 3: Imposta Alert Pre-Entry
1. Per ogni trade pianificato, crea un alert al livello di entry
2. Imposta alert aggiuntivi per livelli chiave (supporto/resistenza)

---

## 3. Operatività Durante le Sessioni

### 3.1 Prima Ora di Trading (09:30-10:30)

⚠️ **ATTENZIONE**: La prima ora è la più volatile. Procedere con cautela.

#### Regole Prima Ora:
1. **Non entrare nei primi 5-15 minuti** se non hai esperienza
2. **Riduci la size** del 50% per trade nella prima ora
3. **Conferma il trend** prima di entrare

#### Checklist Apertura:
- [ ] Gap up/down significativo? → Attendere conferma
- [ ] Volumi normali o anomali?
- [ ] Direzione coerente con piano?

### 3.2 Esecuzione Trade

#### Step 1: Prepara l'Ordine
1. Vai a **Trading**
2. Seleziona il simbolo dalla watchlist o cerca
3. Verifica:
   - Prezzo attuale
   - Spread (differenza bid/ask)
   - Volume

#### Step 2: Configura l'Ordine
```
Tipo Ordine: [LIMIT raccomandato per paper trading]

┌──────────────────────────────────┐
│ Buy/Sell: [BUY]                  │
│ Quantity: [50]                   │
│ Order Type: [LIMIT]              │
│ Limit Price: [$185.00]           │
│ Time in Force: [DAY]             │
│                                  │
│ ☑ Stop-Loss: [$183.00] (-1.08%) │
│ ☑ Take-Profit: [$190.00] (+2.7%)│
└──────────────────────────────────┘
```

#### Step 3: Review Pre-Invio
Prima di cliccare "Submit":
1. **Verifica il simbolo** - È quello giusto?
2. **Verifica la direzione** - Buy/Sell corretto?
3. **Verifica la quantità** - È quella pianificata?
4. **Verifica il prezzo** - È ragionevole?
5. **Verifica stop/take-profit** - Sono impostati?

#### Step 4: Invio e Conferma
1. Clicca "Preview Order"
2. Rivedi il sommario
3. Clicca "Submit Order"
4. Verifica la notifica di conferma
5. Controlla in "Open Orders" che l'ordine sia presente

### 3.3 Monitoraggio Posizioni

#### Dashboard di Monitoraggio
Usa la vista **Portfolio** per monitorare:

```
┌─────────────────────────────────────────────────────────────┐
│ POSIZIONI APERTE                                            │
├─────────────────────────────────────────────────────────────┤
│ Simbolo │ Qty │ Avg Price │ Current │ P/L      │ P/L %     │
├─────────────────────────────────────────────────────────────┤
│ AAPL    │ 50  │ $185.00   │ $186.50 │ +$75.00  │ +0.81%    │
│ NVDA    │ 30  │ $140.00   │ $138.50 │ -$45.00  │ -1.07%    │
└─────────────────────────────────────────────────────────────┘
```

#### Azioni di Monitoraggio
Ogni 15-30 minuti:
1. Controlla P/L delle posizioni aperte
2. Verifica che stop-loss e take-profit siano ancora appropriati
3. Aggiorna se il prezzo si è mosso significativamente

### 3.4 Gestione Trade Attivi

#### Scenario: Posizione in Profitto
```
P/L > +1.5%  → Considera trailing stop
P/L > +2.5%  → Valuta presa profitto parziale (50%)
P/L = Target → Chiudi posizione
```

#### Trailing Stop Procedure:
1. Vai alla posizione in Portfolio
2. Clicca "Modify"
3. Aggiorna lo stop-loss al nuovo livello:
   - Entry: $185, Current: $188
   - Nuovo Stop: $186.50 (lock in profit)

#### Scenario: Posizione in Perdita
```
P/L < -1%    → Rivaluta la tesi
P/L < -2%    → Considera chiusura anticipata
P/L = Stop   → Lascia eseguire lo stop (disciplina!)
```

⚠️ **MAI spostare lo stop-loss più in basso per "dare più spazio"**

### 3.5 Chiusura Posizione

#### Step 1: Vai alla Posizione
1. In **Portfolio**, identifica la posizione da chiudere
2. Clicca sul pulsante "Close" o "Sell"

#### Step 2: Configura Ordine di Chiusura
```
Chiusura Completa:
- Quantity: [Tutto] o numero specifico
- Order Type: MARKET (per uscita rapida) o LIMIT

Chiusura Parziale:
- Quantity: [50%] della posizione
- Order Type: LIMIT preferito
```

#### Step 3: Conferma e Verifica
1. Submit ordine
2. Verifica esecuzione in "Trade History"
3. Controlla che la posizione sia effettivamente chiusa/ridotta

---

## 4. Gestione Portfolio

### 4.1 Review Portfolio Giornaliero

Ogni giorno alle 12:00 e 15:00:

#### Metriche da Controllare
| Metrica | Target | Azione se fuori target |
|---------|--------|------------------------|
| Cash disponibile | >20% del totale | Chiudi posizioni |
| Posizioni singole | <10% portfolio | Riduci size |
| Settore max | <25% portfolio | Diversifica |
| Correlazione | Evita >3 titoli correlati | Diversifica |

### 4.2 Gestione Risk

#### Calcolo Position Size
```
Position Size = (Portfolio * Risk%) / (Entry - Stop)

Esempio:
Portfolio: $100,000
Risk per trade: 2% = $2,000
Entry: $185
Stop: $183
Risk per share: $2

Position Size = $2,000 / $2 = 1,000 shares max
```

#### Verifica Esposizione
1. Vai a **Analytics > Risk Metrics**
2. Controlla:
   - Total exposure (long vs short)
   - Sector breakdown
   - Beta portfolio

### 4.3 Ribilanciamento

#### Quando Ribilanciare:
- Una posizione supera il 15% del portfolio
- Un settore supera il 30%
- Drawdown portfolio >5%

#### Come Ribilanciare:
1. Identifica posizioni sovrapesate
2. Calcola size target
3. Crea ordini di vendita parziale
4. Esegui durante sessione liquida (10:00-15:00)

---

## 5. Utilizzo degli Alert

### 5.1 Tipi di Alert e Uso

| Tipo Alert | Quando Usare | Esempio |
|------------|--------------|---------|
| Price Above | Breakout | AAPL > $190 |
| Price Below | Stop mentale | AAPL < $180 |
| Percent Change | Volatilità | NVDA ±5% |
| Volume Spike | Entry signal | TSLA vol > 150% avg |

### 5.2 Setup Alert Efficaci

#### Alert Breakout
```
Simbolo: AAPL
Tipo: Price Above
Valore: $192.50 (resistenza chiave)
Nota: "Breakout resistenza Q3 - considerare long"
```

#### Alert Support
```
Simbolo: MSFT
Tipo: Price Below
Valore: $370.00 (supporto)
Nota: "Breakdown supporto - chiudere long se confermato"
```

### 5.3 Gestione Alert Attivi

#### Review Giornaliero
1. Accedi agli alert attivi
2. Rimuovi alert non più rilevanti
3. Aggiorna livelli se necessario (dopo movimenti significativi)

#### Best Practice
- Max 10-15 alert attivi
- Pulisci alert scaduti settimanalmente
- Aggiungi note descrittive per ricordare il razionale

---

## 6. Analisi e Report

### 6.1 Review Trade (Post-Trade)

Dopo ogni trade chiuso, registra:

```
┌────────────────────────────────────────────┐
│ TRADE REVIEW                               │
├────────────────────────────────────────────┤
│ Data: 2025-12-07                           │
│ Simbolo: AAPL                              │
│ Direzione: Long                            │
│ Entry: $185.00 @ 10:15                     │
│ Exit: $188.50 @ 14:30                      │
│ P/L: +$175.00 (+1.89%)                     │
│                                            │
│ Cosa ha funzionato:                        │
│ - Entry su pullback a supporto             │
│ - Stop appropriato                         │
│                                            │
│ Cosa migliorare:                           │
│ - Potevo aggiungere su forza              │
│ - Take profit parziale ignorato           │
│                                            │
│ Rating: ★★★★☆                              │
└────────────────────────────────────────────┘
```

### 6.2 Analytics Giornalieri

A fine giornata, accedi a **Analytics**:

#### Metriche da Annotare
1. **P/L del giorno**: Guadagno/perdita totale
2. **Win rate giornaliero**: % trade vincenti
3. **Avg win vs Avg loss**: Ratio medio
4. **Trades eseguiti**: Numero operazioni

### 6.3 Report Settimanale

Ogni venerdì sera:

1. **Performance settimanale**
   - P/L totale settimana
   - Confronto con benchmark (SPY)
   - Migliori/peggiori trade

2. **Analisi pattern**
   - Setup più profittevoli
   - Errori ricorrenti
   - Orari migliori per trading

3. **Obiettivi settimana prossima**
   - Setup da cercare
   - Miglioramenti da implementare

---

## 7. Routine Post-Market

### 7.1 Chiusura Sessione (16:00-17:00)

#### Step 1: Review Posizioni Aperte
1. Controlla tutte le posizioni overnight
2. Valuta se mantenere o chiudere
3. Aggiusta stop-loss per il giorno dopo

#### Step 2: Verifica Ordini Pendenti
1. Controlla ordini non eseguiti
2. Decidi:
   - Cancellare (GTC non più valido)
   - Modificare prezzo
   - Lasciare attivo

#### Step 3: Update Watchlist
1. Rimuovi titoli che hanno raggiunto target
2. Aggiungi nuovi titoli da earnings/news
3. Prioritizza per domani

### 7.2 Analisi Performance Giornaliera (17:00-18:00)

#### Step 1: Review P/L
1. Vai a **Analytics**
2. Annota:
   - P/L giornaliero
   - Numero trade
   - Win rate

#### Step 2: Journal Trade
Per ogni trade eseguito:
1. Registra razionale entry
2. Registra razionale exit
3. Valuta qualità della decisione (indipendentemente dal risultato)

#### Step 3: Identifica Pattern
```
Domande da porsi:
- Quali setup hanno funzionato oggi?
- Ho rispettato il piano?
- Ci sono stati trade emotivi?
- Cosa avrei fatto diversamente?
```

### 7.3 Preparazione Domani

#### Checklist Fine Giornata
- [ ] Posizioni overnight hanno stop-loss
- [ ] Ordini pendenti verificati
- [ ] Watchlist aggiornata
- [ ] Alert importanti impostati
- [ ] Trade pianificati per domani identificati

---

## 8. Procedure Settimanali

### 8.1 Domenica: Pianificazione Settimanale

#### Step 1: Review Settimana Passata (1h)
1. Apri **Analytics** 
2. Genera report settimanale
3. Analizza:
   - Performance totale
   - Migliori/peggiori trade
   - Pattern ricorrenti

#### Step 2: Calendario Eventi (30min)
Identifica eventi market-moving:
- Earnings della settimana
- FOMC/Fed speakers
- Economic data (CPI, jobs, etc.)
- Expiration dates (opzioni)

#### Step 3: Watchlist Setup (30min)
1. Crea/aggiorna watchlist settimanale
2. Identifica 10-15 titoli focus
3. Imposta alert chiave

### 8.2 Lunedì: Fresh Start

#### Morning Routine Estesa
1. Review weekend news
2. Check gap up/down significativi
3. Valuta sentiment mercato
4. Conferma piano settimanale

### 8.3 Venerdì: Wrap-Up Settimanale

#### Chiusura Posizioni
Considera:
- Chiusura posizioni rischiose prima del weekend
- Stop più stretti per posizioni overnight
- Riduzione esposizione complessiva

#### Analisi Completa
1. Performance settimanale dettagliata
2. Confronto con obiettivi
3. Lezioni apprese
4. Obiettivi prossima settimana

### 8.4 Manutenzione Mensile

#### Prima settimana del mese:
1. **Backup dati** - Esporta trade history
2. **Review metriche** - Analisi mensile approfondita
3. **Aggiornamento strategia** - Modifica se necessario
4. **Pulizia watchlist** - Rimuovi titoli obsoleti
5. **Reset contatori** - Se usi target mensili

---

## 9. Best Practices

### 9.1 Gestione Emotiva

#### Prima di Ogni Trade
```
STOP - Respira
THINK - È nel piano?
OBSERVE - Cosa dice il mercato?
PROCEED - Solo se confermato
```

#### Dopo una Perdita
1. **Non fare revenge trading** - Aspetta almeno 30 min
2. **Rivedi il trade** - Era corretto o errore?
3. **Rispetta i limiti** - Max 3 trade perdenti consecutivi → pausa

#### Dopo un Gain
1. **Non diventare overconfident** - Ogni trade è indipendente
2. **Rispetta la size** - Non aumentare perché "sei on fire"
3. **Prendi profitti** - Un profit è un profit

### 9.2 Disciplina di Trading

#### Regole Fondamentali
1. **Sempre stop-loss** - MAI trade senza stop
2. **Rispetta il piano** - No trade improvvisati
3. **Size appropriata** - Max 2% risk per trade
4. **Journaling** - Registra ogni trade
5. **Review regolare** - Analizza performance

#### Errori Comuni da Evitare
| Errore | Conseguenza | Soluzione |
|--------|-------------|-----------|
| No stop-loss | Perdite catastrofiche | Regola ferrea: no stop = no trade |
| Overtrading | Fee + errori emotivi | Max 5-10 trade/giorno |
| FOMO | Entry sbagliate | Aspetta pullback |
| Averaging down | Perdite maggiori | Mai aggiungere a perdenti |
| Revenge trading | Perdite consecutive | Pausa dopo 3 loss |

### 9.3 Ottimizzazione Tempo

#### Sessioni Focus
```
09:30-10:30: Alta attività (entry)
10:30-14:00: Monitoraggio (pochi trade)
14:00-15:00: Valutazione (adjust/close)
15:00-16:00: Chiusure (take profit/cut loss)
```

#### Quando NON Tradare
- Durante news ad alto impatto (prima 5 min)
- Se non hai dormito abbastanza
- Se sei emotivamente disturbato
- Mercato laterale senza volume
- Venerdì pomeriggio pre-holiday

### 9.4 Utilizzo ML Predictions

#### Come Interpretare
```
Confidence > 75%: Segnale forte, considera trade
Confidence 60-75%: Segnale medio, cerca conferma
Confidence < 60%: Segnale debole, ignora
```

#### Integrazione nel Trading
1. **Mai usare ML da solo** - Solo conferma
2. **Combina con analisi tecnica**
3. **Verifica su timeframe multipli**
4. **Track ML accuracy** nel tempo

---

## 10. Checklist Operative

### 10.1 Checklist Mattutina

```
□ Login e verifica sistema
□ Controllo alert notturni
□ Review pre-market movers
□ Analisi watchlist
□ Definizione trade plan
□ Impostazione alert entry
□ Verifica capitale disponibile
□ Check calendario eventi
```

### 10.2 Checklist Pre-Trade

```
□ Il trade è nel piano?
□ Entry level identificato?
□ Stop-loss calcolato e accettabile?
□ Take-profit definito?
□ Size calcolata (max 2% risk)?
□ R:R ratio > 1.5:1?
□ Volume sufficiente?
□ No news ad alto impatto imminenti?
```

### 10.3 Checklist Post-Trade

```
□ Trade registrato nel journal
□ Stop-loss effettivamente impostato
□ Alert creato per livelli chiave
□ Screenshot grafico salvato (opzionale)
□ Revisione entry quality
```

### 10.4 Checklist Fine Giornata

```
□ Posizioni overnight verificate
□ Stop-loss aggiornati
□ Ordini pendenti revisionati
□ P/L giornaliero annotato
□ Trade journal aggiornato
□ Watchlist aggiornata
□ Alert per domani impostati
□ Piano domani definito
```

### 10.5 Checklist Settimanale

```
□ Performance review completa
□ Analisi errori/successi
□ Confronto con benchmark
□ Watchlist rinnovata
□ Calendario eventi aggiornato
□ Obiettivi settimana nuova definiti
□ Backup dati se necessario
```

---

## Appendice A: Template Trade Plan

```markdown
# TRADE PLAN - [DATA]

## Condizioni di Mercato
- Trend SPY: [Bullish/Bearish/Neutral]
- VIX Level: [XX]
- Sentiment: [Positivo/Negativo/Neutro]

## Trade Pianificati

### Trade 1
- **Simbolo**: 
- **Direzione**: Long/Short
- **Entry**: $
- **Stop-Loss**: $ (-X%)
- **Take-Profit**: $ (+X%)
- **Size**: azioni
- **R:R Ratio**: X:1
- **Razionale**: 

### Trade 2
...

## Note
- Eventi da monitorare:
- Livelli chiave mercato:
```

---

## Appendice B: Template Trade Journal

```markdown
# TRADE JOURNAL - [DATA]

## Trade #1
- **Orario**: 
- **Simbolo**: 
- **Side**: Long/Short
- **Entry**: $ @ [orario]
- **Exit**: $ @ [orario]
- **Size**: 
- **P/L**: $ (%)
- **Razionale Entry**: 
- **Razionale Exit**: 
- **Cosa ho fatto bene**: 
- **Cosa migliorare**: 
- **Rating Esecuzione**: ★★★☆☆

## Sommario Giornaliero
- Trades totali: 
- Vincenti: 
- Perdenti: 
- P/L Totale: $
- Win Rate: %
- Lesson Learned: 
```

---

## Appendice C: Glossario Rapido

| Termine | Definizione |
|---------|-------------|
| Stop-Loss | Ordine automatico di chiusura a un prezzo predefinito per limitare perdite |
| Take-Profit | Ordine automatico di chiusura a un prezzo predefinito per bloccare profitti |
| R:R Ratio | Risk/Reward - rapporto tra rischio e guadagno potenziale |
| Position Size | Numero di azioni/contratti per un singolo trade |
| Trailing Stop | Stop-loss che si muove automaticamente con il prezzo |
| Breakout | Rottura di un livello di resistenza/supporto |
| FOMO | Fear Of Missing Out - paura di perdere un'opportunità |
| Drawdown | Perdita massima dal picco del portfolio |

---

**Versione documento:** 1.0  
**Ultimo aggiornamento:** 7 Dicembre 2025
