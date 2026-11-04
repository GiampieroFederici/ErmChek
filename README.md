# ErmChek

**Italiano** | [English](#english)

Come funziona e quali modelli usa, in due pagine: [docs/DESCRIZIONE.md](docs/DESCRIZIONE.md). In English: [docs/DESCRIPTION.md](docs/DESCRIPTION.md).

ErmChek è un programma per Windows che aiuta a ragionare su *Listeria monocytogenes* negli alimenti pronti (in inglese *ready-to-eat*), con attenzione ai salumi.
Funziona senza internet.
È uno strumento didattico e di supporto alle decisioni.

## Cosa fa

- **Conformità del lotto (Modulo A).** Confronta i risultati delle analisi con i criteri del Reg. (CE) 2073/2005, come modificato dal Reg. (UE) 2024/2895. Dice anche se i risultati sono compatibili con un lotto omogeneo. Per *Salmonella* fa solo questa parte.
- **Crescita (Modulo B).** Simula quanto cresce *Listeria* nel tempo, fase per fase (temperatura, pH, aw, nitrito, batteri lattici). Il motore è quello di FSSP (Mejlholm e Dalgaard).
- **Back-calculation (Modulo C).** Parte dal valore misurato e stima quanta *Listeria* c'era all'inizio.

Ogni risultato si può salvare come report PDF, come file Excel e come CSV della curva.
Il PDF mette la risposta in alto, in un riquadro colorato con il testo esplicito.
I grafici sono sempre in inglese.

## Installazione da sorgente

Serve Python 3.11 su Windows.

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

L'interfaccia si avvia dal collegamento **ErmChek** sul Desktop o nel menu Start. Dal sorgente: `.venv\Scripts\python.exe -m ermchek`.

Costruire e installare (per questo utente, senza diritti di amministratore):

1. `.venv\Scripts\python.exe installer\costruisci.py` crea `dist\ErmChek\ErmChek.exe`.
2. `installer\installa_ermchek.cmd` copia l'app in `%LOCALAPPDATA%\ErmChek` e crea i collegamenti.
3. `ErmChek.exe --autoverifica CARTELLA` prova l'app installata: calcola un esempio e scrive PDF ed Excel.
4. `ErmChek.exe --autoverifica-gui CARTELLA` apre la finestra vera, fa la back-calculation con 5.000 ufc/g trovate oggi e salva le foto della finestra.
5. `installer\crea_zip.py` crea lo zip da dare ai colleghi (app, installatore, descrizioni).

## Riga di comando

Gli stessi calcoli, senza finestre:

```
.venv\Scripts\python.exe -m ermchek.cli replicate-script
.venv\Scripts\python.exe -m ermchek.cli back --input caso.json --pdf report.pdf
.venv\Scripts\python.exe -m ermchek.cli grow --input caso.json --pdf report.pdf --lang en
```

- `replicate-script` stampa le 6 righe dello script d'esame originale.
- `back` stima la contaminazione iniziale.
- `grow` simula la crescita.
- `--lang` sceglie la lingua del report: `it` (predefinita) oppure `en`.

Esempio di `caso.json` per `back` (salame fresco di esempio: 7.500 ufc in 25 g, cioè 300 ufc/g, al giorno 12):

```json
{
  "titolo": "Salame fresco di esempio, Listeria al giorno 12",
  "fasi": [
    {"ore": 48, "temperatura": 20, "ph": 5.9, "aw": 0.965, "nitrito": 40},
    {"ore": 240, "temperatura": 12, "ph": 5.4, "aw": 0.95, "nitrito": 20}
  ],
  "osservato_ufc": 7500,
  "massa_g": 25,
  "lab0": 100000,
  "peso_pezzo_g": 500
}
```

Risultato: circa 4,05 ufc/g all'inizio, cioè circa 101 ufc in 25 g.

Regole del file:

- ogni fase ha `ore`, `temperatura`, `ph` e **una sola** fra `aw` e `sale_fase_acquosa`;
- facoltativi per fase: `nitrito` (mg/kg), `fenoli`, `co2`, `acidi` (`{"lattico": ppm, ...}`);
- per `grow` serve `n0` (ufc/g); facoltativi `lab0`, `modello` (`fssp` o `baranyi`), `lag` (`true`/`false`);
- per `back` serve `osservato_ufc_g`, oppure `osservato_ufc` con `massa_g`; facoltativi `lab0`, `peso_pezzo_g`, `u_misura_log` (predefinito 0,5), `n_mc` (predefinito 2000);
- chiavi sconosciute, numeri scritti come testo o valori fuori campo danno un messaggio chiaro e il codice di uscita 1.

## Validazione

Il motore di crescita dà gli stessi risultati di FSSP.Models.dll 1.1.0.21167 (FSSP 4.0, DTU Food) in 23 casi su 23.
Il dettaglio è in `tests/validation_fssp.md`.
Le prove automatiche si lanciano con:

```
.venv\Scripts\python.exe -m pytest
```

## Limiti

ErmChek non sostituisce i challenge test, gli studi di durabilità (EURL Lm TGD v4, emendamento 1, 26/02/2026, DOI 10.5281/zenodo.18783767) né l'autorità competente.
I modelli valgono solo dentro i loro campi di validità.
Il modello prevede solo crescita: la stima iniziale della back-calculation è un valore minimo.
Le fonti complete dei modelli sono in `params/fssp.yaml` e in ogni report.

## Licenza

Codice: licenza MIT (`LICENSE`).
Carattere Atkinson Hyperlegible: SIL Open Font License 1.1 (`assets/fonts/OFL.txt`).

---

<a id="english"></a>

# ErmChek (English)

ErmChek is a Windows program that helps you reason about *Listeria monocytogenes* in ready-to-eat foods, with a focus on cured meats.
It works offline.
It is a teaching and decision-support tool.

## What it does

- **Lot compliance (Module A).** It compares test results with the criteria of Regulation (EC) 2073/2005, as amended by Regulation (EU) 2024/2895. It also tells you whether the results fit a homogeneous lot. For *Salmonella* it does this part only.
- **Growth (Module B).** It simulates how much *Listeria* grows over time, phase by phase (temperature, pH, aw, nitrite, lactic acid bacteria). The engine is the FSSP one (Mejlholm and Dalgaard).
- **Back-calculation (Module C).** It starts from the measured value and estimates how much *Listeria* there was at the start.

Every result can be saved as a PDF report, an Excel file and a CSV of the curve.
The PDF puts the answer at the top, in a coloured box with explicit text.
Charts are always in English.

## Install from source

You need Python 3.11 on Windows.

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

The interface starts from the **ErmChek** shortcut on the Desktop or in the Start menu. From source: `.venv\Scripts\python.exe -m ermchek`.

Build and install (for the current user, no administrator rights):

1. `.venv\Scripts\python.exe installer\costruisci.py` creates `dist\ErmChek\ErmChek.exe`.
2. `installer\installa_ermchek.cmd` copies the app to `%LOCALAPPDATA%\ErmChek` and creates the shortcuts.
3. `ErmChek.exe --autoverifica FOLDER` checks the installed app: it runs an example and writes PDF and Excel.
4. `ErmChek.exe --autoverifica-gui FOLDER` opens the real window, runs a back-calculation from 5,000 CFU/g found today and saves screenshots.
5. `installer\crea_zip.py` builds the zip to share (app, installer, descriptions).

## Command line

The same calculations, without windows:

```
.venv\Scripts\python.exe -m ermchek.cli replicate-script
.venv\Scripts\python.exe -m ermchek.cli back --input case.json --pdf report.pdf --lang en
.venv\Scripts\python.exe -m ermchek.cli grow --input case.json --pdf report.pdf --lang en
```

- `replicate-script` prints the 6 lines of the original exam script.
- `back` estimates the initial contamination.
- `grow` simulates growth.
- `--lang` chooses the report language: `it` (default) or `en`.

The JSON keys are in Italian (the same names as in the code). The example above (`caso.json`) is an example fresh salami: 7,500 CFU in 25 g, that is 300 CFU/g, on day 12.
Result: about 4.05 CFU/g at the start, that is about 101 CFU in 25 g.

File rules:

- each phase has `ore` (hours), `temperatura` (°C), `ph` and **only one** of `aw` and `sale_fase_acquosa` (water-phase salt, %);
- optional per phase: `nitrito` (nitrite, mg/kg), `fenoli` (smoke phenols), `co2`, `acidi` (`{"lattico": ppm, ...}`);
- `grow` needs `n0` (CFU/g); optional `lab0` (lactic acid bacteria, CFU/g), `modello` (`fssp` or `baranyi`), `lag` (`true`/`false`);
- `back` needs `osservato_ufc_g` (CFU/g), or `osservato_ufc` with `massa_g`; optional `lab0`, `peso_pezzo_g` (piece weight), `u_misura_log` (default 0.5), `n_mc` (default 2000);
- unknown keys, numbers written as text or out-of-range values give a clear message and exit code 1.

## Validation

The growth engine gives the same results as FSSP.Models.dll 1.1.0.21167 (FSSP 4.0, DTU Food) in 23 cases out of 23.
Details are in `tests/validation_fssp.md`.
Run the automatic tests with:

```
.venv\Scripts\python.exe -m pytest
```

## Limits

ErmChek does not replace challenge tests, durability studies (EURL Lm TGD v4, amendment 1, 26/02/2026, DOI 10.5281/zenodo.18783767) or the competent authority.
The models are valid only within their validation ranges.
The model predicts growth only: the initial estimate of the back-calculation is a minimum.
Full model sources are in `params/fssp.yaml` and in every report.

## Licence

Code: MIT licence (`LICENSE`).
Atkinson Hyperlegible font: SIL Open Font License 1.1 (`assets/fonts/OFL.txt`).
