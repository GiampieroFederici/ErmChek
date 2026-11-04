# ErmChek: piano di implementazione e stato

File unico di lavoro: si aggiorna a ogni sotto-compito completato.
Stato: `[ ]` da fare, `[~]` in corso, `[x]` fatto e verificato (con la prova).

Specifica: `Downloads\Prompt_ErmChek_ClaudeCode.md`. Cartella: `Documents\ErmChek` (git locale, nessun push: GitHub lo decide il responsabile).

**Vincolo di macchina:** PMN sta girando un'analisi in WSL, che occupa circa 12 GB.
- Non toccare WSL né i processi di PMN.
- Calcoli pesanti (Monte Carlo, test, PyInstaller) uno alla volta e leggeri.

## Decisioni del responsabile (03/11/2026)

- **Motore di crescita:** copia del motore FSSP di PMN (`motore/fssp`). In PMN è stato provato identico a FSSP.Models.dll 1.1.0.21167 in 382 casi su 382 (prova F1). Va rivisto per correttezza scientifica (sezione R).
- **Modello primario:** predefinito FSSP (logistico con effetto Jameson). Baranyi e Roberts come opzione, senza Jameson.
- **Parametri senza tabella o pagina della fonte:** si usa il valore di PMN, segnato "citazione da completare".
- **Incertezza di misura predefinita:** 0,5 log (guida EURL sull'incertezza, Lm con EN ISO 11290-2).
- **Incertezza di μmax:** opzione avanzata, spenta, campo vuoto per chi ha la fonte.
- **Back-calculation:** il riquadro grande mostra lo scenario con i batteri lattici; sotto, il caso peggiore senza.
- **Inattivazione:** non documentata, quindi NON si mette. Al suo posto un avviso: la stima di N0 è un minimo.
- **Interfaccia:** solo tema chiaro, come PMN.
- **Peso del pezzo:** lo mette l'utente nelle impostazioni, senza valore predefinito.
- **Preset:** solo esempi neutri con valori plausibili; nessun dato reale nel programma, nei test o nei documenti.
- **Report:**
  - in alto, un riquadro grande con la risposta, per esempio "All'origine c'erano X ufc/g, cioè Y ufc in 25 g";
  - poi sezioni brevi e ariose, con il logo;
  - grafici con le etichette in inglese.
- **Installazione:** sul Desktop come PMN, con collegamenti nel Desktop e nel menu Start.
- **Salmonella:** stessa analisi solo con modelli pubblicati (DOI, tabella dei parametri) e validati su prodotti carnei. Se non ce ne sono, per Salmonella c'è solo il Modulo A (criteri e statistica).

## Architettura

```
ErmChek/
  ermchek/core/          scienza pura, nessuna dipendenza dalla GUI
    fssp/                motore FSSP copiato da PMN (modelli, crescita, validita, calcolatrici, confine)
    conformita.py        Modulo A: statistica del lotto, curve OC, prevalenza, Monte Carlo
    criteri.py           lettura e valutazione di criteria.yaml
    crescita.py          Modulo B: profili dinamici (T, pH, aw, nitrito...), FSSP+Jameson o Baranyi, Monte Carlo
    retro.py             Modulo C: back-calculation (brentq + soluzione esplicita), intervalli, avvisi
  ermchek/gui/           PySide6, procedura guidata, stile di PMN (stile.qss, carattere Atkinson Hyperlegible)
  ermchek/report/        PDF (reportlab) e Excel (openpyxl); grafici matplotlib in inglese
  ermchek/i18n/          catalogo inglese (chiave = testo italiano, come PMN)
  ermchek/cli.py         stessi calcoli da riga di comando (replicate-script, grow, back)
  params/*.yaml          parametri con citazione
  criteria.yaml          criteri di legge con riferimento per riga
  tests/                 pytest (+ pytest-qt)
  assets/logo/           ErmChek_logo.png (file fornito dal responsabile), icona .ico solo bacillo
  installer/             PyInstaller onedir + script di installazione sul Desktop
```

- **Tutto su Windows**, senza WSL: il motore è Python puro.
- **Offline:** nessuna chiamata di rete.

## Sotto-compiti

### F0. Ricognizione
- [x] PMN letto: struttura, GUI PySide6 6.12.0, lingua JSON, stile.qss, PyInstaller 6.22.3, licenza MIT.
- [x] FSSP 4.0 trovato in `C:\Program Files (x86)\DTU Food\FSSP` (FSSP.Models.dll 1.1.0.21167), con aiuto e riferimenti.
- [x] Normativa letta:
  - testo consolidato 2073/2005 al 01/07/2026;
  - Reg. 2024/2895 (si applica dal 01/07/2026);
  - TGD EURL v4 emendamento 1 (26/02/2026), δ > 0,5 log;
  - guida EURL sull'incertezza: circa 0,5 log.
- [x] Cartella, git, ambiente `.venv` con le versioni fissate (requirements.txt, requirements-dev.txt).
- [x] Logo copiato in `assets/logo/ErmChek_logo.png`.
- [x] Letteratura Salmonella (`params/salmonella_ricerca.md`): nessun modello validato su carne e con nitrito. Quindi per Salmonella solo il Modulo A (righe 1.4-1.9 e 1.28 in `criteria.yaml`; salami = 1.8).

### F1. Modulo A: conformità e campionamento (G001)
- [x] `conformita.py` e `criteri.py` + `criteria.yaml` (commit 34921bc). Aggiunti la fase di campionamento e Salmonella.
- [x] Test: replica esatta dello script, regressione della tabella σ, MLE, miscela, curve OC, Clopper-Pearson, Monte Carlo.

### F2. Modulo B: crescita (G002)
- [x] R: revisione scientifica in `docs/REVISIONE_SCIENTIFICA.md`. È affidabile come FSSP; per i salumi ci sono i limiti di pH e Jameson sotto pH 6, e non c'è inattivazione.
- [x] `crescita.py`:
  - profilo a fasi (T, pH, aw o sale nella fase acquosa, nitrito, acidi, CO₂, fenoli);
  - CSV del data logger;
  - lag;
  - Jameson;
  - Baranyi.
- [x] Test: identico al motore di PMN (23 casi, differenza ≤ 1e-9); crescita esponenziale analitica; doppio conteggio aw/sale impedito.
- [x] `tests/validation_fssp.md`: 23 casi su 23 identici alla DLL vera di FSSP (differenza massima 8,9e-16 log).
- [x] Monte Carlo (N0, temperatura, μmax facoltativo): percentili e P(> 100 ufc/g).

### F3. Modulo C: back-calculation (G003)
- [x] `retro.py`:
  - brentq e soluzione esplicita, che devono coincidere;
  - intervalli 90 e 95 %;
  - risultato per grammo, per 25 g e per pezzo;
  - avvisi: non crescita, meno di 1 cellula per pezzo, fuori campo, nessuna inattivazione;
  - legame con il Modulo A: P(non rilevata in 25 g a t0).
- [x] Test: N0 → Nt → N0; esempio neutro (300 ufc/g al giorno 12).

### F4. Interfaccia (G004)
- [x] Finestra stile PMN: splash con logo, percorso a passi, un solo pulsante principale, selettore IT/EN, Info con i limiti (commit 55d9901).
- [x] Pagine A, B e C con campi, unità, tooltip, obbligatorio o facoltativo; preset di esempio etichettati (solo valori neutri).
- [x] Impostazioni: lingua, peso del pezzo (vuoto), incertezza di misura.
- [x] Test pytest-qt (9) e 124 schermate guardate in `build/anteprime_gui/`.

### F5. Report, CLI, pacchetto, installazione (G005)
- [x] Report PDF (risposta in alto, sezioni brevi, grafici in inglese, citazioni, limiti) ed Excel/CSV (commit 9fe6f04). Pagine guardate in `build/anteprime/`.
- [x] `cli.py` (`replicate-script`, `grow`, `back`).
- [x] README IT + EN.
- [x] Icona .ico (solo bacillo), PyInstaller, installazione in `%LOCALAPPDATA%\ErmChek` con collegamenti nel Desktop e nel menu Start.
- [x] Prova dell'app installata:
  - avvio dal collegamento sul Desktop: finestra "ErmChek", il programma risponde;
  - `--autoverifica`: esempio neutro calcolato, PDF IT/EN ed Excel scritti dal pacchetto;
  - PDF guardato.
  - **Non fatto:** la prova cliccando nell'app installata. L'accesso con il controllo dello schermo è stato negato, quindi l'interfaccia è provata dai test pytest-qt sul sorgente e l'eseguibile dall'autoverifica.
- [x] pip-audit: nessuna vulnerabilità nota nelle dipendenze fissate.
- [x] 161 test passano.

## Scelte prese in autonomia, riviste e confermate il 03/11/2026

1. **Colori della risposta nel modulo C.**
   - Rosso: all'origine era attesa almeno 1 cellula in 25 g, quindi un'analisi al giorno 0 l'avrebbe trovata.
   - Giallo: meno di 1 cellula attesa in 25 g, oppure il modello non prevede crescita.
   - Verde: nel modulo C non c'è.
2. **Risposta principale con lag 0** (confermata, con trafiletto che spiega la scelta e dà il valore con lag fisiologico). Lo scenario con lag fisiologico (RLT 4,5) è nella tabella degli scenari.
3. **Incertezza di misura 0,5 log trattata come deviazione standard.** La guida EURL non dice se è standard o estesa (k = 2): se fosse estesa, gli intervalli sarebbero più larghi del dovuto.
4. **Baranyi: h0 = 4,5 × ln 2 = 3,12.** È ricavato dal tempo di ritardo relativo di FSSP, così il lag è uguale nei due modelli.
5. **Modulo A, caso d'esame.** Le stime MLE finiscono ai bordi della ricerca (σ da 0,05 a 5). Il verdetto "contaminazione localizzata" è solido, il valore esatto di p no. L'app lo dice.
6. **Preset "Salsiccia fresca", "Salame stagionato", "Prosciutto cotto".** Valori plausibili etichettati come esempi. Nessun dato reale nel programma.
7. **Fase di campionamento nei criteri.** Prima del 01/07/2026 la riga 1.2 "assenza in 25 g" vale solo prima che il prodotto lasci il controllo dell'OSA: un campione preso sul mercato dà "non valutabile".

## Da completare (servono fonti o te)

- **Tabella e pagina dei parametri in `params/fssp.yaml`:** "da completare". I valori sono quelli validati contro FSSP.
- **Salmonella:** per crescita e back-calculation servono i PDF di Coroller et al. 2015 (doi:10.1016/j.fm.2014.06.011) e Pin et al. 2011. Il motivo è in `params/salmonella_ricerca.md`.
- **Icona a 16 px:** la linea del bacillo è sottile e sulla barra scura si vede poco. Non l'ho modificata, come da regola sul logo.

## Rischi residui (sicurezza)

- ✅ Offline, nessuna credenziale, niente eval/pickle; YAML con safe_load; CSV e JSON validati campo per campo.
- ⚠️ `ErmChek.exe` non è firmato digitalmente: su altri PC Windows SmartScreen può mostrare un avviso.
- ⚠️ La CLI scrive il PDF nel percorso che le dai, senza limitarlo a una cartella. È uno strumento locale.

## Registro

- 03/11/2026 notte, revisione con il responsabile:
  - 7 scelte confermate; trafiletto sul lag 0 nell'app e nel PDF;
  - tolto ogni dato reale (solo esempi neutri, anche negli scenari di validazione: 23/23 identici a FSSP);
  - icona su piastrella bianca, visibile su Desktop scuro;
  - descrizione IT/EN in `docs/`;
  - "0 %" sostituito da "meno di 0,1 %";
  - zip `dist/ErmChek_1.0.0.zip`;
  - `--autoverifica-gui`: con 5.000 ufc/g oggi l'app installata dà circa 67 ufc/g a t0.
- 03/11/2026 sera, prova nella VM `pmn_win` (Windows pulito, istantanea windows_pulito) con i clic, come un collega:
  - **Percorso provato:** zip, "Estrai tutto", doppio clic su "Installa ErmChek", icona sul Desktop, modulo C con 5.000 ufc/g oggi (circa 67 ufc/g a t0, uguale al PC), PDF salvato e aperto in Edge.
  - **Difetti trovati e corretti:**
    - la rotellina cambiava i menu (ora prendono il fuoco solo con clic o Tab, con test);
    - la prima apertura durava circa 35 s senza segnali (ora c'è un'immagine di avvio immediata);
    - cartella doppia dopo l'estrazione;
    - arrotondamenti diversi fra app e PDF (ora 2 cifre significative ovunque);
    - l'installatore non apriva il programma (ora lo apre, chiude la finestra nera e si ferma solo in caso di errore);
    - "Inizio" restava evidenziato dopo il calcolo.
  - **Riprova nella VM con lo zip corretto:** tutto a posto. 161 test passano.

- 03/11/2026 sera: interfaccia e report completati, pacchetto installato sul Desktop e nel menu Start, autoverifica OK. 161 test passano.

- 03/11/2026, Moduli A, B e C completati: 117 test passano.
  - Avviati in parallelo gli agenti per l'interfaccia (`ermchek/gui`) e per il report (`ermchek/report`, CLI, README).
  - Scritti gli script di pacchetto in `installer/`.

- 03/11/2026: F0 completata. Avviati il Modulo A (agente) e la ricerca su Salmonella.
