"""Test del Modulo A, conformità e campionamento (ermchek.core.conformita)."""
import contextlib
import io
import math

import numpy as np
import pytest
from scipy import integrate, stats

from ermchek.core import conformita as C

ESAME = [C.conta(9000), C.assente(25), C.assente(25), C.assente(25), C.assente(25)]
TABELLA = [(0.5, 1.47e-23, -0.20), (0.8, 1.11e-11, -0.55), (1.0, 1.40e-08, -0.75),
           (1.5, 3.48e-05, -1.20), (2.0, 8.04e-04, -1.65)]


def _script_originale():
    """Script di partenza, copiato senza modifiche."""
    hi = np.log10(9000)

    def p_neg(mu, s):
        f = lambda x: np.exp(-25 * 10**x) * stats.norm.pdf(x, mu, s)
        return integrate.quad(f, mu - 8*s, mu + 8*s, limit=200)[0]

    for s in [0.5, 0.8, 1.0, 1.5, 2.0]:
        best = (0, None)
        for mu in np.arange(-4, 4.01, 0.05):
            p = 5 * stats.norm.sf(hi, mu, s) * p_neg(mu, s)**4
            if p > best[0]:
                best = (p, mu)
        print(f"sigma={s}: max P={best[0]:.2e} at mu={best[1]:.2f} log CFU/g")

    print("log increase from 10 CFU/g:", round(hi - 1, 2),
          "generations:", round((hi - 1) / np.log10(2), 1))


def test_replica_esatta_dello_script():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _script_originale()
    assert C.replica_script() == buf.getvalue().splitlines()


def test_tabella_caso_esame():
    g = C.griglia_pattern(ESAME, [s for s, _, _ in TABELLA])
    assert g["coefficiente"] == 5
    for (s, p_att, mu_att), p, mu in zip(TABELLA, g["p_max"], g["mu_ottimale"]):
        assert abs(math.log10(p) - math.log10(p_att)) <= 0.05 * abs(math.log10(p_att))
        assert mu == pytest.approx(mu_att, abs=1e-9)


def test_generazioni():
    g = C.generazioni(9000, 10)
    assert round(g["aumento_log"], 2) == 2.95 and round(g["generazioni"], 1) == 9.8


def test_conta_in_massa():
    assert C.conta_in_massa(5000, 25) == C.conta(200)
    assert C.conta_in_massa(0, 25) == C.assente(25)


def test_mle_non_peggiore_della_griglia():
    mle = C.mle_lognormale(ESAME)
    griglia = max(C.log_verosimiglianza(ESAME, mu, s)
                  for s in (0.5, 1.0, 2.0, 3.0, 5.0) for mu in np.arange(-6, 4.01, 0.25))
    assert mle["log_verosimiglianza"] >= griglia - 1e-6
    assert C.log_verosimiglianza(ESAME, mle["mu"], mle["sigma"]) == pytest.approx(mle["log_verosimiglianza"])


def test_miscela_preferita_nel_caso_esame():
    i = C.interpretazione(ESAME)
    assert i["codice"] == "CONTAMINAZIONE_LOCALIZZATA"
    assert i["aic_miscela"] < i["aic_lognormale"] and i["p_valore"] < 0.05
    assert i["pi"] == pytest.approx(0.8, abs=0.01)


def test_conta_in_25_g():
    i = C.interpretazione([C.conta_in_massa(5000, 25)] + [C.assente(25)] * 4)
    assert i["codice"] == "CONTAMINAZIONE_LOCALIZZATA"


def test_lotto_omogeneo():
    i = C.interpretazione([C.conta(v) for v in (50, 80, 120, 60, 90)])
    assert i["codice"] == "LOTTO_OMOGENEO"


def test_miscela_annidata():
    c = C.confronto_modelli(ESAME)
    assert c["miscela"]["log_verosimiglianza"] >= c["lognormale"]["log_verosimiglianza"] - 1e-9
    assert c["p_valore"] == pytest.approx(0.5 * stats.chi2.sf(c["lr"], 1))


@pytest.mark.parametrize("criterio", ["presenza_assenza", "enumerazione"])
def test_curve_oc_decrescenti(criterio):
    mu = np.arange(-4, 4.01, 0.25)
    p = C.curva_oc(5, 0, 0.8, 25, mu, criterio)
    assert np.all(np.diff(p) <= 1e-12) and p[0] > 0.5 and p[-1] < 0.01


def test_clopper_pearson():
    assert C.prevalenza(0, 5)["superiore"] == pytest.approx(0.5218, abs=1e-4)
    assert C.prevalenza(5, 5)["inferiore"] == pytest.approx(0.4782, abs=1e-4)
    p = C.prevalenza(2, 10)
    assert (p["inferiore"], p["superiore"]) == pytest.approx((0.0252, 0.5561), abs=1e-4)


def test_n_necessario():
    assert C.n_necessario(0.05, 0.95) == 59
    assert C.n_necessario(0.5, 0.75) == 2


@pytest.mark.parametrize("mu, sigma, risultati", [
    (-1.65, 2.0, ESAME),
    (1.0, 1.0, [C.assente(25), C.sotto_lod(10), C.conta(50), C.conta(50)]),
])
def test_monte_carlo_concorda(mu, sigma, risultati):
    mc = C.monte_carlo_pattern(mu, sigma, risultati)
    assert abs(mc["p_mc"] - mc["p_analitica"]) <= 3 * mc["errore_standard"]
    assert mc == C.monte_carlo_pattern(mu, sigma, risultati)   # riproducibile


@pytest.mark.parametrize("chiamata, codice", [
    (lambda: C.conta(-1), "CONTA_NON_POSITIVA"),
    (lambda: C.assente(0), "MASSA_NON_POSITIVA"),
    (lambda: C.conta_in_massa(-5, 25), "CONTA_NEGATIVA"),
    (lambda: C.Risultato("boh", 1), "TIPO_RISULTATO_SCONOSCIUTO"),
    (lambda: C.griglia_pattern([], [1.0]), "RISULTATI_VUOTI"),
    (lambda: C.griglia_pattern(ESAME, [0.0]), "SIGMA_NON_VALIDA"),
    (lambda: C.curva_oc(0, 0, 1.0, 25, [0], "enumerazione"), "N_NON_VALIDO"),
    (lambda: C.curva_oc(5, 0, 1.0, 25, [0], "altro"), "CRITERIO_SCONOSCIUTO"),
    (lambda: C.prevalenza(1, 5, conf=1.0), "CONF_FUORI_RANGE"),
    (lambda: C.n_necessario(0.0), "P_FUORI_RANGE"),
    (lambda: C.log_verosimiglianza(ESAME, float("nan"), 1.0), "MU_FUORI_RANGE"),
])
def test_validazione(chiamata, codice):
    with pytest.raises(ValueError, match=codice):
        chiamata()
