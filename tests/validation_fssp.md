# Validazione di ErmChek contro FSSP

Riferimento: FSSP.Models.dll 1.1.0.21167 (FSSP 4.0, DTU Food), installata in `C:\Program Files (x86)\DTU Food\FSSP`,
chiamata con `banco_dll.ps1` (da PMN, prova F1): stessa sequenza di chiamate delle finestre di FSSP, passi da 1 minuto.
Nessun codice o file di FSSP è copiato in ErmChek: la DLL si usa solo qui, per confronto.

Tolleranze proposte: differenza di μmax ≤ 10 %, differenza di log N ≤ 0,2 log in ogni minuto della curva.
Risultato: 23 casi su 23 entro tolleranza; differenza massima su tutte le curve 8.9e-16 log.

| Caso | Scenario | Modello | μmax FSSP (h⁻¹) | μmax ErmChek | log N finale FSSP | log N finale ErmChek | max diff curva (log) | Esito |
|---|---|---|---|---|---|---|---|---|
| E00 | cotto 5C | Lm | 0.02424 | 0.02424 | 8.2377 | 8.2377 | 0.0e+00 | OK |
| E01 | cotto 5C (lag) | Lm | 0.02424 | 0.02424 | 7.2040 | 7.2040 | 0.0e+00 | OK |
| E02 | cotto 8C lattato | Lm | 0.04131 | 0.04131 | 8.3905 | 8.3905 | 0.0e+00 | OK |
| E03 | cotto 8C lattato (lag) | Lm | 0.04131 | 0.04131 | 7.6255 | 7.6255 | 0.0e+00 | OK |
| E04 | salame fresco 20/12 | Lm | 0.10984 | 0.10984 | 7.5471 | 7.5471 | 0.0e+00 | OK |
| E05 | salame fresco 20/12 (lag) | Lm | 0.10984 | 0.10984 | 6.2420 | 6.2420 | 0.0e+00 | OK |
| E06 | salame 22/13 | Lm | 0.13980 | 0.13980 | 8.5000 | 8.5000 | 0.0e+00 | OK |
| E07 | salame 22/13 (lag) | Lm | 0.13980 | 0.13980 | 8.4992 | 8.4992 | 0.0e+00 | OK |
| E08 | affumicato | Lm | 0.01348 | 0.01348 | 5.0525 | 5.0525 | 4.4e-16 | OK |
| E09 | affumicato (lag) | Lm | 0.01348 | 0.01348 | 3.6980 | 3.6980 | 8.9e-16 | OK |
| E10 | acetato | Lm | 0.01311 | 0.01311 | 2.9769 | 2.9769 | 1.1e-16 | OK |
| E11 | acetato (lag) | Lm | 0.01311 | 0.01311 | 1.6223 | 1.6223 | 2.2e-16 | OK |
| E12 | ATM nitrito | Lm | 0.00901 | 0.00901 | 3.2201 | 3.2201 | 0.0e+00 | OK |
| E13 | ATM nitrito (lag) | Lm | 0.00901 | 0.00901 | 1.8658 | 1.8658 | 0.0e+00 | OK |
| E14 | sorbato | Lm | 0.04659 | 0.04659 | 7.3396 | 7.3396 | 8.9e-16 | OK |
| E15 | sorbato (lag) | Lm | 0.04659 | 0.04659 | 6.0147 | 6.0147 | 4.4e-16 | OK |
| E16 | non cresce pH | Lm | 0.00000 | 0.00000 | 2.0000 | 2.0000 | 0.0e+00 | OK |
| E17 | non cresce pH (lag) | Lm | 0.00000 | 0.00000 | 2.0000 | 2.0000 | 0.0e+00 | OK |
| E18 | vicino Nmax | Lm | 0.26797 | 0.26797 | 8.5000 | 8.5000 | 0.0e+00 | OK |
| E19 | vicino Nmax (lag) | Lm | 0.26797 | 0.26797 | 8.5000 | 8.5000 | 0.0e+00 | OK |
| E20 | lab 1e4 22/13 | Lm+LAB | 0.13980 | 0.13980 | 3.8132 | 3.8132 | 4.4e-16 | OK |
| E21 | lab 1e5 20/12 aw | Lm+LAB | 0.10984 | 0.10984 | 2.4022 | 2.4022 | 0.0e+00 | OK |
| E22 | lab 1e6 cotto | Lm+LAB | 0.04638 | 0.04638 | 2.3774 | 2.3774 | 0.0e+00 | OK |

Rigenerare: `powershell -File tests/validazione_fssp/banco_dll.ps1 -Casi tests/validazione_fssp/casi_dll.json -Uscita tests/validazione_fssp/uscita_dll`,
poi `.venv/Scripts/python.exe tests/validazione_fssp/confronta.py`. Il test automatico `tests/test_validazione_fssp.py`
confronta ogni volta i valori finali con quelli salvati in `tests/dati/fssp_dll_finali.json`.
