"""Modulo C: back-calculation. Dato Lm osservato alla fine delle fasi, quanta Lm c'era a t0.

Metodo: si risolve il modello di crescita (Modulo B) rispetto a log N0 con brentq; lontano da Nmax vale anche la
soluzione esplicita log N0 = log Nt - Δlog, che deve coincidere (test). Incertezze con Monte Carlo: misura
(u in log, normale), temperatura per fase, mu_max (opzione avanzata). Il modello prevede solo crescita: se Lm
è morta durante la fermentazione la contaminazione iniziale era più alta (la stima è un minimo).
"""
import math

import numpy as np
from scipy.optimize import brentq

from .crescita import H0_FSSP, simula
from .fssp.modelli import LISTERIA

PORZIONE_G = 25.0
LOG_N_RIF = -12.0   # N0 di riferimento per Δlog: così piccolo che Lm resta lontana da Nmax (crescita indipendente da N0)


def _log_finale(fasi, n0, **opz):
    return float(simula(fasi, n0, **opz)["log_lm"][0][-1])


def _stima(fasi, log_nt, opz):
    """log N0 centrale per uno scenario: brentq e soluzione esplicita."""
    delta = _log_finale(fasi, 10.0 ** LOG_N_RIF, **opz) - LOG_N_RIF   # Δlog lontano da Nmax
    if delta <= 1e-12:
        return {"log_n0": log_nt, "log_n0_esplicita": log_nt, "delta_log": 0.0, "cresce": False}
    lo = max(log_nt - delta - 2.0, -300.0)
    log_n0 = brentq(lambda x: _log_finale(fasi, 10.0 ** x, **opz) - log_nt, lo, log_nt, xtol=1e-7)
    return {"log_n0": float(log_n0), "log_n0_esplicita": log_nt - delta, "delta_log": delta, "cresce": True}


def _monte_carlo(fasi, log_nt, opz, u_misura_log, sd_temperatura, cv_mu, n, seed):
    rng = np.random.default_rng(seed)
    fattore = None if not cv_mu else np.exp(rng.normal(0.0, math.log1p(cv_mu), n))
    sim = simula(fasi, 10.0 ** LOG_N_RIF, n=n, sd_temperatura=sd_temperatura, fattore_mu=fattore, seed=seed, **opz)
    delta = sim["log_lm"][:, -1] - LOG_N_RIF   # soluzione esplicita: vale finché Lm osservata è lontana da Nmax
    log_n0 = log_nt + rng.normal(0.0, u_misura_log, n) - delta
    q = np.percentile(log_n0, [2.5, 5, 50, 95, 97.5])
    return {"log_n0_p2_5": float(q[0]), "log_n0_p5": float(q[1]), "log_n0_p50": float(q[2]),
            "log_n0_p95": float(q[3]), "log_n0_p97_5": float(q[4]), "n": n, "seed": seed,
            "p_non_rilevata_25g_media": float(np.mean(np.exp(-PORZIONE_G * 10.0 ** log_n0)))}


def retro(fasi, osservato_ufc_g, lab0=None, modello="fssp", gamma=1.0, h0=H0_FSSP, u_misura_log=0.5,
          sd_temperatura=0.0, cv_mu=None, peso_pezzo_g=None, n_mc=2000, seed=20261103):
    """Concentrazione iniziale stimata. fasi: da t0 al giorno dell'analisi; osservato_ufc_g: Lm misurata (ufc/g).

    Scenari: con batteri lattici (se lab0) e senza (caso peggiore), ciascuno con lag 0 e con lag fisiologico.
    Il risultato principale è "con LAB, lag 0" se lab0 è dato, altrimenti "senza LAB, lag 0".
    Restituisce dict: principale, scenari, monte_carlo, avvisi (codici), curva (simulazione in avanti da N0)."""
    if isinstance(osservato_ufc_g, bool) or not isinstance(osservato_ufc_g, (int, float)) \
            or not math.isfinite(osservato_ufc_g) or not 0.0 < osservato_ufc_g < LISTERIA.nmax:
        raise ValueError("FUORI_LIMITE:osservato")
    if not 0.0 <= u_misura_log <= 3.0 or not 0.0 <= sd_temperatura <= 10.0:
        raise ValueError("FUORI_LIMITE:incertezze")
    if peso_pezzo_g is not None and not 0.0 < peso_pezzo_g <= 1e6:
        raise ValueError("FUORI_LIMITE:peso_pezzo")
    log_nt = math.log10(osservato_ufc_g)
    con_lab = [True, False] if lab0 is not None else [False]
    scenari = []
    for usa_lab in con_lab:
        for lag in (False, True):
            opz = {"lab0": lab0 if usa_lab else None, "modello": modello, "lag": lag, "gamma": gamma, "h0": h0}
            if modello == "baranyi" and usa_lab:
                continue
            s = _stima(fasi, log_nt, opz)
            scenari.append(dict(s, con_lab=usa_lab, lag=lag, **_unita(s["log_n0"], peso_pezzo_g)))
    principale = scenari[0]
    opz0 = {"lab0": lab0 if principale["con_lab"] else None, "modello": modello, "lag": False, "gamma": gamma, "h0": h0}
    mc = _monte_carlo(fasi, log_nt, opz0, u_misura_log, sd_temperatura, cv_mu, n_mc, seed) if n_mc else None
    peggiore = next(s for s in scenari if not s["con_lab"] and not s["lag"])
    mc_peggiore = None
    if lab0 is not None and n_mc:
        opz_p = dict(opz0, lab0=None)
        mc_peggiore = _monte_carlo(fasi, log_nt, opz_p, u_misura_log, sd_temperatura, cv_mu, n_mc, seed)

    curva = simula(fasi, 10.0 ** principale["log_n0"], lab0=opz0["lab0"], modello=modello, gamma=gamma, h0=h0)
    avvisi = [a for a in curva["avvisi"] if a["codice"] != "SOLO_CRESCITA"]
    if not principale["cresce"]:
        avvisi.append({"codice": "NON_CRESCITA"})   # N0 >= Nt; con inattivazione N0 > Nt
    if peso_pezzo_g is None:
        avvisi.append({"codice": "PESO_PEZZO_MANCANTE"})
    for s in scenari:
        if s["ufc_pezzo"] is not None and s["ufc_pezzo"] < 1.0:
            avvisi.append({"codice": "MENO_DI_UNA_CELLULA_PER_PEZZO", "con_lab": s["con_lab"], "lag": s["lag"],
                           "ufc_pezzo": s["ufc_pezzo"]})
    avvisi.append({"codice": "STIMA_MINIMA_NESSUNA_INATTIVAZIONE"})
    return {"fasi": list(fasi), "lab0": lab0, "osservato_ufc_g": float(osservato_ufc_g), "log_osservato": log_nt, "giorni": float(curva["tempi_giorni"][-1]),
            "principale": principale, "peggiore": peggiore, "scenari": scenari, "monte_carlo": mc,
            "monte_carlo_peggiore": mc_peggiore, "u_misura_log": u_misura_log, "avvisi": avvisi, "curva": curva,
            "p_non_rilevata_25g": float(math.exp(-PORZIONE_G * 10.0 ** principale["log_n0"]))}


def _unita(log_n0, peso_pezzo_g):
    """Stessa concentrazione detta in tre modi: ufc/g, ufc attese in 25 g, ufc attese nel pezzo."""
    c = 10.0 ** log_n0
    return {"ufc_g": c, "ufc_25g": c * PORZIONE_G, "ufc_pezzo": c * peso_pezzo_g if peso_pezzo_g else None}
