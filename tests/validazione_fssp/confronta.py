"""Confronta ErmChek con FSSP.Models.dll (uscita di banco_dll.ps1) e scrive tests/validation_fssp.md
e tests/dati/fssp_dll_finali.json (valori finali di FSSP, usati da test_validazione_fssp.py)."""
import json
import sys
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RADICE))
from ermchek.core.crescita import simula  # noqa: E402
from tests.test_crescita import RIF, fasi_di  # noqa: E402

QUI = Path(__file__).parent
casi = json.loads((QUI / "casi_dll.json").read_text(encoding="utf-8"))["casi"]
scalari = {json.loads(r)["id"]: json.loads(r) for r in (QUI / "uscita_dll" / "scalari.jsonl").read_text(encoding="utf-8-sig").splitlines()}
TOLL_MU, TOLL_LOG = 0.10, 0.2   # tolleranze proposte (prompt): mu_max entro 10 %, log N entro 0,2 log

righe, finali, peggiore = [], {}, 0.0
for c, rif in zip(casi, RIF):
    s = scalari[c["id"]]
    serie = np.fromfile(QUI / "uscita_dll" / f"{c['id']}.bin", dtype="<f8").reshape(3 if c["tipo"] == "lm_lab" else 2, -1)
    dll_lm = serie[1]
    sim = simula(fasi_di(rif), rif["n0"], lab0=rif.get("lab0"), lag=rif["lag"])
    erm = sim["log_lm"][0][1:]
    diff = float(np.max(np.abs(erm - dll_lm)))
    mu_dll = float(s.get("mu") or s.get("mu_listeria"))
    mu_erm = sim["fasi"][0]["mu_lm"]
    dmu = abs(mu_erm - mu_dll) / mu_dll if mu_dll else abs(mu_erm)
    peggiore = max(peggiore, diff)
    finali[c["id"]] = {"log_finale_dll": float(dll_lm[-1]), "mu_dll": mu_dll}
    esito = "OK" if diff <= TOLL_LOG and dmu <= TOLL_MU else "FUORI"
    righe.append(f"| {c['id']} | {rif['nome']}{' (lag)' if rif['lag'] else ''} | {'Lm+LAB' if c['tipo'] == 'lm_lab' else 'Lm'} | "
                 f"{mu_dll:.5f} | {mu_erm:.5f} | {dll_lm[-1]:.4f} | {erm[-1]:.4f} | {diff:.1e} | {esito} |")
(RADICE / "tests" / "dati" / "fssp_dll_finali.json").write_text(json.dumps(finali, indent=1), encoding="utf-8")
testo = f"""# Validazione di ErmChek contro FSSP

Riferimento: FSSP.Models.dll 1.1.0.21167 (FSSP 4.0, DTU Food), installata in `C:\Program Files (x86)\DTU Food\FSSP`,
chiamata con `banco_dll.ps1` (da PMN, prova F1): stessa sequenza di chiamate delle finestre di FSSP, passi da 1 minuto.
Nessun codice o file di FSSP è copiato in ErmChek: la DLL si usa solo qui, per confronto.

Tolleranze proposte: differenza di μmax ≤ 10 %, differenza di log N ≤ 0,2 log in ogni minuto della curva.
Risultato: {sum('OK |' in r for r in righe)} casi su {len(righe)} entro tolleranza; differenza massima su tutte le curve {peggiore:.1e} log.

| Caso | Scenario | Modello | μmax FSSP (h⁻¹) | μmax ErmChek | log N finale FSSP | log N finale ErmChek | max diff curva (log) | Esito |
|---|---|---|---|---|---|---|---|---|
""" + "\n".join(righe) + """

Rigenerare: `powershell -File tests/validazione_fssp/banco_dll.ps1 -Casi tests/validazione_fssp/casi_dll.json -Uscita tests/validazione_fssp/uscita_dll`,
poi `.venv/Scripts/python.exe tests/validazione_fssp/confronta.py`. Il test automatico `tests/test_validazione_fssp.py`
confronta ogni volta i valori finali con quelli salvati in `tests/dati/fssp_dll_finali.json`.
"""
(RADICE / "tests" / "validation_fssp.md").write_text(testo, encoding="utf-8")
print(testo[-2500:])
