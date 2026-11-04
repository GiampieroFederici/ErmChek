"""Modulo C: coerenza avanti/indietro, soluzione esplicita, casi limite, esempio."""
import math

import pytest

from ermchek.core.crescita import Fase, simula
from ermchek.core.retro import retro

ESEMPIO = [Fase(ore=48, temperatura=20, ph=5.9, aw=0.965, nitrito=40), Fase(ore=240, temperatura=12, ph=5.4, aw=0.95, nitrito=20)]


@pytest.fixture(scope="module")
def reale():
    # esempio: 300 ufc/g al giorno 12, batteri lattici 10^5 ufc/g; peso piccolo per provare l'avviso del pezzo
    return retro(ESEMPIO, 300.0, lab0=1e5, peso_pezzo_g=50, n_mc=300)


def test_avanti_indietro(reale):
    for s in reale["scenari"]:
        lab0 = 1e5 if s["con_lab"] else None
        nt = simula(ESEMPIO, 10 ** s["log_n0"], lab0=lab0, lag=s["lag"])["log_lm"][0][-1]
        assert nt == pytest.approx(math.log10(300), abs=1e-5)


def test_brentq_uguale_esplicita(reale):
    for s in reale["scenari"]:
        assert s["log_n0"] == pytest.approx(s["log_n0_esplicita"], abs=0.01)


def test_esempio_numeri(reale):
    p = reale["principale"]
    assert p["con_lab"] and not p["lag"]
    assert p["ufc_25g"] == pytest.approx(p["ufc_g"] * 25)
    assert 10 ** p["delta_log"] == pytest.approx(300 / p["ufc_g"], rel=0.01)
    assert reale["peggiore"]["ufc_g"] < 0.01
    mc = reale["monte_carlo"]
    assert mc["log_n0_p2_5"] < mc["log_n0_p5"] < p["log_n0"] < mc["log_n0_p95"] < mc["log_n0_p97_5"]
    codici = [a["codice"] for a in reale["avvisi"]]
    assert "MENO_DI_UNA_CELLULA_PER_PEZZO" in codici and "STIMA_MINIMA_NESSUNA_INATTIVAZIONE" in codici
    assert 0 < reale["p_non_rilevata_25g"] < 1


def test_lag_fisiologico_alza_n0(reale):
    s = {(x["con_lab"], x["lag"]): x for x in reale["scenari"]}
    assert s[(False, True)]["log_n0"] > s[(False, False)]["log_n0"]


def test_non_crescita():
    f = [Fase(ore=200, temperatura=10, ph=4.9, sale_fase_acquosa=3.0)]
    r = retro(f, 150.0, n_mc=0)
    assert r["principale"]["ufc_g"] == pytest.approx(150.0)
    assert "NON_CRESCITA" in [a["codice"] for a in r["avvisi"]]


def test_ingressi_non_validi():
    with pytest.raises(ValueError):
        retro(ESEMPIO, 0.0)
    with pytest.raises(ValueError):
        retro(ESEMPIO, 300.0, peso_pezzo_g=-1)

