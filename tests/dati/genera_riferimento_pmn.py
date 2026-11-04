"""Genera tests/dati/riferimento_pmn.json con il motore ORIGINALE di profilemetananni (provato uguale a FSSP, prova F1).
Si lancia una volta sola, a mano (argomento: la cartella motore di PMN); i test poi usano il JSON e non hanno bisogno di PMN."""
import json
import sys
from pathlib import Path

PMN = Path(sys.argv[1])   # cartella motore/ di profilemetananni
sys.path.insert(0, str(PMN))
from fssp import crescita_listeria_lab, crescita_singola  # noqa: E402
from fssp.calcolatrici import sale_da_aw  # noqa: E402
from fssp.modelli import Prodotto  # noqa: E402

SCENARI = [
    {"nome": "cotto 5C", "prodotto": {"sale": 3.0, "ph": 6.2}, "profilo": [[5, 30 * 24]], "n0": 10.0},
    {"nome": "cotto 8C lattato", "prodotto": {"sale": 3.5, "ph": 6.3, "acidi": {"lattico": 7000}}, "profilo": [[8, 21 * 24]], "n0": 1.0},
    {"nome": "salame fresco 20/12", "prodotto": {"aw": 0.965, "ph": 5.8, "nitrito": 30}, "profilo": [[20, 48], [12, 240]], "n0": 3.0},
    {"nome": "salame 22/13", "prodotto": {"sale": 4.0, "ph": 5.6, "nitrito": 40}, "profilo": [[22, 48], [13, 312]], "n0": 100.0},
    {"nome": "affumicato", "prodotto": {"sale": 3.0, "ph": 6.1, "fenoli": 10, "co2": 20}, "profilo": [[5, 240], [10, 120]], "n0": 50.0},
    {"nome": "acetato", "prodotto": {"sale": 2.5, "ph": 6.0, "acidi": {"acetico": 2000, "lattico": 5000}}, "profilo": [[7, 400]], "n0": 5.0},
    {"nome": "ATM nitrito", "prodotto": {"sale": 2.8, "ph": 6.0, "nitrito": 60, "co2": 30}, "profilo": [[4, 200], [12, 48], [4, 300]], "n0": 2.0},
    {"nome": "sorbato", "prodotto": {"sale": 4.0, "ph": 5.8, "acidi": {"sorbico": 300, "citrico": 500}}, "profilo": [[10, 300]], "n0": 20.0},
    {"nome": "non cresce pH", "prodotto": {"sale": 3.0, "ph": 4.9}, "profilo": [[10, 200]], "n0": 100.0},
    {"nome": "vicino Nmax", "prodotto": {"sale": 0.5, "ph": 7.0}, "profilo": [[20, 200]], "n0": 1000.0},
    {"nome": "lab 1e4 22/13", "prodotto": {"sale": 4.0, "ph": 5.6, "nitrito": 40}, "profilo": [[22, 48], [13, 312]], "n0": 50.0, "lab0": 1e4},
    {"nome": "lab 1e5 20/12 aw", "prodotto": {"aw": 0.965, "ph": 5.8, "nitrito": 30}, "profilo": [[20, 48], [12, 240]], "n0": 3.0, "lab0": 1e5},
    {"nome": "lab 1e6 cotto", "prodotto": {"sale": 3.0, "ph": 6.2}, "profilo": [[8, 400]], "n0": 10.0, "lab0": 1e6},
]


def prodotto(d, t):
    sale = sale_da_aw(d["aw"]) if "aw" in d else d["sale"]
    return Prodotto(temperatura=t, sale_fase_acquosa=sale, ph=d["ph"], fenoli=d.get("fenoli", 0.0),
                    co2=d.get("co2", 0.0), nitrito=d.get("nitrito", 0.0), acidi=d.get("acidi", {}))


uscita = []
for s in SCENARI:
    prof = [tuple(x) for x in s["profilo"]]
    p = prodotto(s["prodotto"], prof[0][0])
    for lag in ((False,) if "lab0" in s else (False, True)):
        if "lab0" in s:
            o = crescita_listeria_lab(p, prof, s["n0"], s["lab0"], modalita="migliorata")
            log, lab = o["log_listeria"], o["log_lab"]
        else:
            o = crescita_singola(p, prof, s["n0"], lag=lag, modalita="migliorata")
            log, lab = o["log_ufc"], None
        idx = [59, len(log) // 3, len(log) // 2, len(log) - 1]
        uscita.append(dict(s, lag=lag, punti={str(i + 1): log[i] for i in idx},
                           lab_finale=lab[-1] if lab else None))
Path(__file__).with_name("riferimento_pmn.json").write_text(json.dumps(uscita, indent=1), encoding="utf-8")
print(len(uscita), "casi")
