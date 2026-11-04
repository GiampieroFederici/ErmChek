"""Modulo B: identico al motore di PMN (provato uguale a FSSP), casi analitici, controlli degli ingressi."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from ermchek.core.crescita import Fase, applica_temperature, leggi_csv_temperature, monte_carlo, riassunto, simula, wps
from ermchek.core.fssp.modelli import LISTERIA

RIF = json.loads((Path(__file__).parent / "dati" / "riferimento_pmn.json").read_text(encoding="utf-8"))


def fasi_di(caso):
    d = caso["prodotto"]
    sale = {"aw": d["aw"]} if "aw" in d else {"sale_fase_acquosa": d["sale"]}
    return [Fase(ore=o, temperatura=t, ph=d["ph"], nitrito=d.get("nitrito", 0.0), acidi=d.get("acidi", {}),
                 fenoli=d.get("fenoli", 0.0), co2=d.get("co2", 0.0), **sale) for t, o in caso["profilo"]]


@pytest.mark.parametrize("caso", RIF, ids=lambda c: f"{c['nome']}{' lag' if c['lag'] else ''}")
def test_uguale_al_motore_pmn(caso):
    sim = simula(fasi_di(caso), caso["n0"], lab0=caso.get("lab0"), lag=caso["lag"])
    log = sim["log_lm"][0]
    for passo, atteso in caso["punti"].items():
        assert log[int(passo)] == pytest.approx(atteso, abs=1e-9)
    if caso["lab_finale"] is not None:
        assert sim["log_lab"][0][-1] == pytest.approx(caso["lab_finale"], abs=1e-9)


def test_esponenziale_puro():
    # lontano da Nmax e senza lag: log N(t) = log N0 + mu * t / ln 10
    f = [Fase(ore=48, temperatura=10, ph=6.5, sale_fase_acquosa=1.0)]
    sim = simula(f, 1.0)
    mu = sim["fasi"][0]["mu_lm"]
    assert sim["log_lm"][0][-1] == pytest.approx(mu * 48 / math.log(10), rel=1e-6)


def test_baranyi_senza_lag_come_logistico():
    f = [Fase(ore=200, temperatura=12, ph=6.2, sale_fase_acquosa=2.0)]
    a, b = simula(f, 10.0)["log_lm"][0][-1], simula(f, 10.0, modello="baranyi")["log_lm"][0][-1]
    assert a == pytest.approx(b, abs=0.01)


def test_baranyi_lag_rallenta():
    f = [Fase(ore=100, temperatura=10, ph=6.2, sale_fase_acquosa=2.0)]
    assert simula(f, 10.0, modello="baranyi", lag=True)["log_lm"][0][-1] < simula(f, 10.0, modello="baranyi")["log_lm"][0][-1]


def test_doppio_conteggio_aw_sale_impedito():
    with pytest.raises(ValueError, match="AW_OPPURE_SALE"):
        simula([Fase(ore=10, temperatura=5, ph=6, aw=0.97, sale_fase_acquosa=3.0)], 1.0)
    with pytest.raises(ValueError, match="AW_OPPURE_SALE"):
        simula([Fase(ore=10, temperatura=5, ph=6)], 1.0)


@pytest.mark.parametrize("campo,valore", [("temperatura", 60), ("ph", 2.0), ("aw", 0.5), ("ore", -1)])
def test_ingressi_fuori_limite(campo, valore):
    d = dict(ore=10, temperatura=5, ph=6, aw=0.97)
    d[campo] = valore
    with pytest.raises(ValueError, match="FUORI_LIMITE"):
        simula([Fase(**d)], 1.0)


def test_wps_esempio_del_prompt():
    assert wps(2.5, 60) == pytest.approx(2.5 / 62.5 * 100)   # 4,0 %


def test_riassunto_e_avvisi():
    f = [Fase(ore=48, temperatura=20, ph=5.9, aw=0.965, nitrito=40), Fase(ore=240, temperatura=12, ph=5.4, aw=0.95, nitrito=20)]
    sim = simula(f, 3.0, lab0=1e5)
    r = riassunto(sim)
    assert r["log_finale"] > r["log_iniziale"] and r["giorni_al_limite"] is not None
    codici = {a["codice"] for a in sim["avvisi"]}
    assert {"FUORI_CAMPO", "JAMESON_PH_SOTTO_6", "SOLO_CRESCITA"} <= codici


def test_monte_carlo_riproducibile_e_coerente():
    f = [Fase(ore=240, temperatura=8, ph=6.2, sale_fase_acquosa=3.0)]
    a = monte_carlo(f, 10.0, log_n0_sd=0.3, sd_temperatura=1.0, n=200)
    b = monte_carlo(f, 10.0, log_n0_sd=0.3, sd_temperatura=1.0, n=200)
    assert a["log_finale_p50"] == b["log_finale_p50"]
    centrale = simula(f, 10.0)["log_lm"][0][-1]
    assert a["log_finale_p5"] < centrale < a["log_finale_p95"]
    assert 0.0 <= a["p_sopra_limite"] <= 1.0


def test_csv_data_logger(tmp_path):
    p = tmp_path / "logger.csv"
    p.write_text("ore;temperatura\n0;4\n24;15,5\n48;15\n", encoding="utf-8")
    punti = leggi_csv_temperature(p)
    assert punti == [(0.0, 4.0), (24.0, 15.5), (48.0, 15.0)]
    fasi = applica_temperature([Fase(ore=72, temperatura=10, ph=5.5, aw=0.97)], punti)
    assert [(f.ore, f.temperatura) for f in fasi] == [(24.0, 4.0), (24.0, 15.5), (24.0, 15.0)]
    p.write_text("0;4\n10;99\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CSV_RIGA"):
        leggi_csv_temperature(p)


def test_non_supera_nmax():
    sim = simula([Fase(ore=400, temperatura=20, ph=7.0, sale_fase_acquosa=0.5)], 1000.0)
    assert sim["log_lm"][0].max() <= LISTERIA.log_nmax + 1e-9
    assert np.all(np.diff(sim["log_lm"][0]) >= -1e-12)
