"""Report: PDF dei tre tipi in italiano e in inglese, Excel, CSV, grafici, catalogo inglese completo."""
import ast
import csv
import json
import re
from pathlib import Path
from string import Formatter

import fitz
import pytest
from matplotlib.figure import Figure
from openpyxl import load_workbook

from ermchek import lingua
from ermchek.core import conformita as C
from ermchek.core.criteri import esito_normativo
from ermchek.core.crescita import Fase, monte_carlo, riassunto, simula
from ermchek.core.retro import retro
from ermchek.report import grafici
from ermchek.report.excel import esporta_csv_curva, esporta_excel
from ermchek.report.pdf import crea_pdf, probabilita, sig

RADICE = Path(__file__).resolve().parent.parent
FASI = [Fase(ore=48, temperatura=20, ph=5.9, aw=0.965, nitrito=40), Fase(ore=240, temperatura=12, ph=5.4, aw=0.95, nitrito=20)]
ESAME = [C.assente(25)] * 4 + [C.conta(9000)]


@pytest.fixture(autouse=True)
def italiano():
    lingua.imposta("it")
    yield
    lingua.imposta("it")


@pytest.fixture(scope="module")
def casi():
    sim = simula(FASI, 1.0, lab0=1e5)
    mc = monte_carlo(FASI, 1.0, log_n0_sd=0.3, lab0=1e5, n=50)
    return {
        "retro": retro(FASI, 300.0, lab0=1e5, peso_pezzo_g=500, n_mc=300),
        "crescita": {"sim": sim, "riassunto": riassunto(sim), "mc": mc},
        "conformita": {"esito": esito_normativo(ESAME, "1.2", False, "2026-11-03"),
                       "interpretazione": C.interpretazione(ESAME), "griglia": C.griglia_pattern(ESAME),
                       "mle": C.mle_lognormale(ESAME), "miscela": C.mle_miscela(ESAME),
                       "prevalenza": C.prevalenza(1, 5), "patogeno": "listeria"},
    }


def _ingressi(tipo):
    return {"titolo": "Prova <&> " + tipo, "righe": [("Dato", "1.000 ufc/g")], "contesto": [("Prodotto", "salame")],
            "fasi": None if tipo == "conformita" else FASI}


RISPOSTE = {("retro", "it"): "All'origine c'erano circa 4 ufc/g", ("retro", "en"): "At the start there were about 4 CFU/g",
            ("crescita", "it"): "Alla fine Listeria arriva a circa", ("crescita", "en"): "At the end Listeria reaches about",
            ("conformita", "it"): "Non conforme", ("conformita", "en"): "Non-compliant"}


@pytest.mark.parametrize("lg", ["it", "en"])
@pytest.mark.parametrize("tipo", ["retro", "crescita", "conformita"])
def test_pdf_creato_con_la_risposta_in_alto(tmp_path, casi, tipo, lg):
    lingua.imposta(lg)
    percorso = tmp_path / f"{tipo}_{lg}.pdf"
    crea_pdf(percorso, tipo, casi[tipo], _ingressi(tipo))
    assert percorso.stat().st_size > 10_000
    assert percorso.read_bytes()[:5] == b"%PDF-"
    with fitz.open(percorso) as doc:
        prima = doc[0].get_text()
        tutto = "".join(p.get_text() for p in doc)
    assert RISPOSTE[(tipo, lg)] in prima          # la risposta sta nella prima pagina
    assert "Prova <&> " + tipo in prima           # testo dell'utente non interpretato come markup
    assert "—" not in tutto                   # niente trattino lungo


def test_pdf_retro_colore_e_numeri(tmp_path, casi):
    crea_pdf(tmp_path / "r.pdf", "retro", casi["retro"], _ingressi("retro"))
    with fitz.open(tmp_path / "r.pdf") as doc:
        prima = doc[0].get_text()
        rossi = [d for d in doc[0].get_drawings() if d.get("fill") and abs(d["fill"][0] - 0xB3 / 255) < 0.01
                 and abs(d["fill"][1] - 0x26 / 255) < 0.01]
    assert "cioè circa 100 ufc in 25 g" in prima
    assert "Intervallo al 90 %" not in prima
    with fitz.open(tmp_path / "r.pdf") as doc:
        tutto = "".join(pg.get_text() for pg in doc)
    assert re.search(r"In 9 calcoli su 10 all'origine c'erano fra \S+ e \S+ ufc/g", tutto.replace(chr(10), " "))
    assert rossi, "100 ufc in 25 g >= 1: il riquadro deve essere rosso"


def test_tipo_sconosciuto(tmp_path, casi):
    with pytest.raises(ValueError):
        crea_pdf(tmp_path / "x.pdf", "altro", casi["retro"], {})


@pytest.mark.parametrize("tipo, fogli_it, fogli_en", [
    ("retro", ["Riepilogo", "Ingressi", "Curva", "Scenari", "Fonti"], ["Summary", "Inputs", "Curve", "Scenarios", "Sources"]),
    ("crescita", ["Riepilogo", "Ingressi", "Curva", "Fonti"], ["Summary", "Inputs", "Curve", "Sources"]),
    ("conformita", ["Riepilogo", "Ingressi", "Risultati", "Fonti"], ["Summary", "Inputs", "Results", "Sources"]),
])
def test_excel_si_apre_con_i_fogli(tmp_path, casi, tipo, fogli_it, fogli_en):
    for lg, fogli in (("it", fogli_it), ("en", fogli_en)):
        lingua.imposta(lg)
        percorso = tmp_path / f"{tipo}_{lg}.xlsx"
        esporta_excel(percorso, tipo, casi[tipo], _ingressi(tipo))
        wb = load_workbook(percorso)
        assert wb.sheetnames == fogli
        assert wb[fogli[0]].max_row > 4


def test_excel_retro_numeri(tmp_path, casi):
    esporta_excel(tmp_path / "r.xlsx", "retro", casi["retro"], _ingressi("retro"))
    ws = load_workbook(tmp_path / "r.xlsx")["Riepilogo"]
    valori = {r[0]: r[1] for r in ws.iter_rows(min_row=5, values_only=True)}
    assert valori["Stima all'origine (N0)"] == pytest.approx(4.05, abs=0.01)


@pytest.mark.parametrize("lg, sep", [("it", ";"), ("en", ",")])
def test_csv_curva(tmp_path, casi, lg, sep):
    lingua.imposta(lg)
    sim = casi["crescita"]["sim"]
    esporta_csv_curva(tmp_path / "c.csv", sim)
    with open(tmp_path / "c.csv", encoding="utf-8-sig", newline="") as fh:
        righe = list(csv.reader(fh, delimiter=sep))
    assert len(righe) == len(sim["tempi_giorni"]) + 1
    assert len(righe[1]) == 3
    assert float(righe[-1][1].replace(",", ".")) == pytest.approx(sim["log_lm"][0][-1])


def test_grafici_restituiscono_figure(casi):
    import numpy as np
    r = casi["retro"]
    figure = [grafici.fig_crescita(casi["crescita"]["sim"], casi["crescita"]["mc"]), grafici.fig_retro(r),
              grafici.fig_retro({k: v for k, v in r.items() if k != "fasi"}),
              grafici.fig_pattern_sigma(casi["conformita"]["griglia"]),
              grafici.fig_oc(np.linspace(-4, 2, 20), {"n=5, c=0": C.curva_oc(5, 0, 0.8, 25, np.linspace(-4, 2, 20),
                                                                                "presenza_assenza")})]
    for f in figure:
        assert isinstance(f, Figure)
        testi = [t.get_text() for t in f.findobj(lambda o: hasattr(o, "get_text"))]
        assert not any("ufc" in t or "Crescita" in t for t in testi)   # grafici sempre in inglese


def test_numeri():
    assert sig(4.0486841) == "4"
    assert sig(101.2171) == "100"
    assert sig(428.83) == "430"
    assert sig(0.153) == "0,15"
    assert sig(6.745e-5, markup=False) == "6,7 × 10^-5"
    assert probabilita(2.29e-12, markup=False) == "2,3 × 10^-12 (praticamente zero)"
    assert probabilita(0.71) == "71 %"
    lingua.imposta("en")
    assert sig(9590.19) == "9,600"


def _chiavi_tradotte():
    chiavi = set()
    for f in ("ermchek/report/pdf.py", "ermchek/report/excel.py", "ermchek/cli.py"):
        for n in ast.walk(ast.parse((RADICE / f).read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("_", "N_") and n.args \
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                chiavi.add(n.args[0].value)
    return chiavi


def test_catalogo_inglese_completo():
    catalogo = {}
    for f in (RADICE / "ermchek" / "i18n" / "en_core.json", RADICE / "ermchek" / "i18n" / "en_report.json"):
        catalogo.update(json.loads(f.read_text(encoding="utf-8")))
    mancanti = _chiavi_tradotte() - set(catalogo)
    assert not mancanti, mancanti
    report = json.loads((RADICE / "ermchek" / "i18n" / "en_report.json").read_text(encoding="utf-8"))
    campi = lambda t: {c for _testo, c, _f, _conv in Formatter().parse(t) if c}
    for it, en in report.items():   # stessi {campi} nelle due lingue
        assert campi(it) == campi(en), it


def test_niente_trattino_lungo():
    for f in ("ermchek/report/pdf.py", "ermchek/report/excel.py", "ermchek/report/grafici.py", "ermchek/cli.py",
              "ermchek/i18n/en_report.json", "README.md"):
        assert "—" not in (RADICE / f).read_text(encoding="utf-8"), f
