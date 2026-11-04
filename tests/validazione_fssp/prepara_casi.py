"""Scrive casi_dll.json (formato di banco_dll.ps1, da PMN) con gli scenari di tests/dati/riferimento_pmn.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ermchek.core.fssp.calcolatrici import sale_da_aw  # noqa: E402

QUI = Path(__file__).parent
rif = json.loads((QUI.parent / "dati" / "riferimento_pmn.json").read_text(encoding="utf-8"))
casi = []
for i, c in enumerate(rif):
    d = c["prodotto"]
    sale = sale_da_aw(d["aw"]) if "aw" in d else d["sale"]
    acidi = d.get("acidi", {})
    prod = {"temperatura": repr(float(c["profilo"][0][0])), "sale_fase_acquosa": repr(float(sale)), "ph": repr(float(d["ph"])),
            "fenoli": repr(float(d.get("fenoli", 0))), "co2": repr(float(d.get("co2", 0))), "nitrito": repr(float(d.get("nitrito", 0))),
            **{a: repr(float(acidi.get(a, 0))) for a in ("lattico", "acetico", "diacetato", "citrico", "sorbico", "benzoico")}}
    prof = [[repr(float(t)), repr(float(o))] for t, o in c["profilo"]]
    if c.get("lab0"):
        casi.append({"id": f"E{i:02d}", "tipo": "lm_lab", "prodotto": prod, "profilo": prof, "n0_listeria": repr(c["n0"]),
                     "n0_lab": repr(float(c["lab0"])), "gamma": "1.0", "lag": False})
    else:
        casi.append({"id": f"E{i:02d}", "tipo": "singola", "organismo": "listeria", "prodotto": prod, "profilo": prof,
                     "n0": repr(float(c["n0"])), "lag": c["lag"]})
(QUI / "casi_dll.json").write_text(json.dumps({"seme": 0, "casi": casi}, indent=1), encoding="utf-8")
print(len(casi))
