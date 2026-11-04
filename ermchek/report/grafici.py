"""Grafici del report e dell'interfaccia (matplotlib, senza pyplot: sicuri con Agg e dentro Qt).

Tutto il testo DENTRO i grafici è in inglese, anche con l'interfaccia in italiano.
Stile pulito: linee sottili, griglia chiara, niente decorazioni inutili, colori Okabe-Ito (sicuri per chi non
distingue i colori). Ogni funzione restituisce una matplotlib.figure.Figure di circa 8 x 4,2 pollici.
"""
import math

import numpy as np
from matplotlib import font_manager
from matplotlib.figure import Figure

from ermchek.percorsi import risorsa

DIMENSIONE = (8, 4.2)
# Okabe & Ito (2008): palette leggibile anche con daltonismo
BLU, VERDE, VERMIGLIO, ARANCIO, GRIGIO, NERO = "#0072B2", "#009E73", "#D55E00", "#E69F00", "#7F7F7F", "#222222"
TESTO, GRIGLIA = "#333333", "#E3E3E3"
SERIE = [BLU, VERMIGLIO, VERDE, ARANCIO, "#CC79A7", "#56B4E9", NERO]


def _famiglia():
    """Atkinson Hyperlegible se c'è (con DejaVu Sans per i simboli che le mancano, come σ e δ), altrimenti DejaVu."""
    try:
        for nome in ("Regular", "Bold"):
            percorso = risorsa("assets", "fonts", f"AtkinsonHyperlegible-{nome}.ttf")
            if percorso.is_file():
                font_manager.fontManager.addfont(str(percorso))
        font_manager.fontManager.findfont("Atkinson Hyperlegible", fallback_to_default=False)
        return ["Atkinson Hyperlegible", "DejaVu Sans"]
    except (ValueError, OSError, RuntimeError):
        return ["DejaVu Sans"]


FAMIGLIA = _famiglia()


def _figura():
    fig = Figure(figsize=DIMENSIONE, dpi=100, facecolor="white", layout="constrained")
    ax = fig.add_subplot()
    for lato in ("top", "right"):
        ax.spines[lato].set_visible(False)
    for lato in ("left", "bottom"):
        ax.spines[lato].set_color("#9A9A9A")
        ax.spines[lato].set_linewidth(0.8)
    ax.grid(True, color=GRIGLIA, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TESTO, labelsize=9.5, width=0.6, length=3, labelfontfamily=FAMIGLIA)
    return fig, ax


def _testi(ax, titolo, x, y, legenda=True):
    ax.set_title(titolo, loc="left", fontsize=12, color=TESTO, fontfamily=FAMIGLIA, fontweight="bold", pad=10)
    ax.set_xlabel(x, fontsize=10.5, color=TESTO, fontfamily=FAMIGLIA)
    ax.set_ylabel(y, fontsize=10.5, color=TESTO, fontfamily=FAMIGLIA)
    if legenda and ax.get_legend_handles_labels()[0]:
        ax.legend(frameon=False, fontsize=9.5, loc="best", prop={"family": FAMIGLIA, "size": 9.5})


def _durata(ore):
    return f"{ore:g} h" if ore < 48 else f"{ore / 24:.3g} d"


def _fasi(ax, fasi, y_testo=0.985):
    """Confini delle fasi (linee verticali chiare) ed etichetta con temperatura e durata all'inizio di ogni fase.
    Con più di 8 fasi (es. data logger) le etichette diventerebbero illeggibili: non si disegnano."""
    if not fasi or len(fasi) > 8:
        return
    totale = sum(f["ore"] for f in fasi) / 24.0
    inizio, stretta_prima = 0.0, False
    for i, f in enumerate(fasi):
        giorni = f["ore"] / 24.0
        if i:
            ax.axvline(inizio, color="#BDBDBD", linewidth=0.8, linestyle=(0, (2, 2)), zorder=1)
        y = y_testo - (0.075 if stretta_prima else 0.0)
        ax.text(inizio + totale * 0.006, y, f"{f['temperatura']:g} °C, {_durata(f['ore'])}",
                transform=ax.get_xaxis_transform(), ha="left", va="top", fontsize=8.5, color="#555555",
                fontfamily=FAMIGLIA)
        stretta_prima = (giorni / totale < 0.15) and not stretta_prima
        inizio += giorni


def _limite(ax, limite_ufc_g):
    y = math.log10(limite_ufc_g)
    ax.axhline(y, color=VERMIGLIO, linewidth=0.9, linestyle=(0, (5, 3)), zorder=2)
    ax.text(1.008, y, f"{limite_ufc_g:g}\nCFU/g", transform=ax.get_yaxis_transform(), ha="left", va="center",
            fontsize=8.5, color=VERMIGLIO, fontfamily=FAMIGLIA, linespacing=1.1)


def fig_crescita(sim, mc=None, limite_ufc_g=100.0):
    """Lm (log ufc/g) nel tempo; LAB tratteggiati se presenti; banda 5-95 % se c'è il Monte Carlo."""
    fig, ax = _figura()
    t = np.asarray(sim["tempi_giorni"])
    if mc is not None:
        tm = np.asarray(mc["sim"]["tempi_giorni"])
        ax.fill_between(tm, mc["curva_p5"], mc["curva_p95"], color=BLU, alpha=0.15, linewidth=0,
                        label="L. monocytogenes, 5-95 % range")
    ax.plot(t, sim["log_lm"][0], color=BLU, linewidth=1.8, label="L. monocytogenes", zorder=4)
    if sim.get("log_lab") is not None:
        ax.plot(t, sim["log_lab"][0], color=VERDE, linewidth=1.4, linestyle=(0, (6, 3)),
                label="Lactic acid bacteria (LAB)", zorder=3)
    _limite(ax, limite_ufc_g)
    ax.set_xlim(0, t[-1])
    basso = min(float(np.min(sim["log_lm"][0])), math.log10(limite_ufc_g)) - 0.6
    alto = max(float(np.max(sim["log_lm"][0])), math.log10(limite_ufc_g))
    if sim.get("log_lab") is not None:
        alto = max(alto, float(np.max(sim["log_lab"][0])))
    if mc is not None:
        basso = min(basso, float(np.min(mc["curva_p5"])) - 0.3)
        alto = max(alto, float(np.max(mc["curva_p95"])))
    ax.set_ylim(basso, alto + 1.4)   # spazio in alto per le etichette delle fasi
    _fasi(ax, sim.get("fasi"))
    _testi(ax, "Growth of Listeria monocytogenes", "Time (days)", "log10 CFU/g")
    if ax.get_legend():
        ax.get_legend().set_loc("center right")
    return fig


def fig_retro(ris):
    """Back-calculation: curva in avanti dalla N0 centrale fino al punto osservato; N0 con l'intervallo al 90 %;
    caso peggiore senza LAB (grigio tratteggiato) se ris contiene le fasi."""
    from ermchek.core.crescita import simula

    fig, ax = _figura()
    curva = ris["curva"]
    t = np.asarray(curva["tempi_giorni"])
    p = ris["principale"]
    if ris.get("fasi") and ris.get("lab0") is not None:
        peg = simula(ris["fasi"], 10.0 ** ris["peggiore"]["log_n0"], lab0=None, modello=curva.get("modello", "fssp"))
        ax.plot(peg["tempi_giorni"], peg["log_lm"][0], color=GRIGIO, linewidth=1.3, linestyle=(0, (5, 3)),
                label="Worst case: no lactic acid bacteria", zorder=3)
        ax.plot([0], [ris["peggiore"]["log_n0"]], marker="o", markersize=5, color=GRIGIO, zorder=5)
    etichetta = "Central estimate, with LAB" if p["con_lab"] else "Central estimate"
    ax.plot(t, curva["log_lm"][0], color=BLU, linewidth=1.8, label=etichetta, zorder=4)
    mc = ris.get("monte_carlo")
    if mc:
        ax.errorbar([0], [p["log_n0"]], yerr=[[p["log_n0"] - mc["log_n0_p5"]], [mc["log_n0_p95"] - p["log_n0"]]],
                    fmt="o", color=BLU, markersize=6, capsize=4, elinewidth=1.2, zorder=6,
                    label="Initial level N0 (90 % interval)")
    else:
        ax.plot([0], [p["log_n0"]], marker="o", markersize=6, color=BLU, zorder=6, label="Initial level N0")
    u = ris.get("u_misura_log") or 0.0
    ax.errorbar([ris["giorni"]], [ris["log_osservato"]], yerr=[[u], [u]] if u else None, fmt="D", color=VERMIGLIO,
                markersize=6, capsize=4, elinewidth=1.2, zorder=6,
                label=f"Observed: {ris['osservato_ufc_g']:.3g} CFU/g" + (f" (±{u:g} log)" if u else ""))
    ax.axhline(0.0, color="#9A9A9A", linewidth=0.6, zorder=1)   # 1 ufc/g
    ax.set_xlim(-0.03 * t[-1], t[-1] * 1.03)
    ylo, yhi = ax.get_ylim()
    ax.set_ylim(ylo, yhi + 0.12 * (yhi - ylo) + 0.6)
    _fasi(ax, curva.get("fasi"))
    _testi(ax, "Back-calculation of the initial level", "Time (days)", "log10 CFU/g")
    if ax.get_legend():
        ax.get_legend().set_loc("lower right")
    return fig


def fig_pattern_sigma(griglia):
    """Probabilità massima del pattern osservato al variare di σ (tra le unità), asse y logaritmico."""
    fig, ax = _figura()
    s, pm, mu = (np.asarray(griglia[k], dtype=float) for k in ("sigma", "p_max", "mu_ottimale"))
    ok = pm > 0
    ax.plot(s[ok], pm[ok], color=BLU, linewidth=1.5, marker="o", markersize=5, zorder=4)
    ultimo = len(s[ok]) - 1
    for i, (x, y, m) in enumerate(zip(s[ok], pm[ok], mu[ok])):   # etichette a destra, sotto la linea che sale
        ax.annotate(f"μ = {m:.2f}".replace("-", "−"), (x, y), textcoords="offset points",
                    xytext=(-8, 6) if i == ultimo else (8, -12), ha="right" if i == ultimo else "left",
                    fontsize=8.5, color="#555555", fontfamily=FAMIGLIA)
    ax.set_yscale("log")
    if ok.any():
        ax.set_ylim(pm[ok].min() / 100, pm[ok].max() * 30)   # spazio per le etichette μ
    _testi(ax, "Maximum probability of the observed results", "σ between units (log10 CFU/g)",
           "Max P(observed pattern)", legenda=False)
    return fig


def fig_oc(mu_values, curve):
    """Curve operative (OC): P(accettazione del lotto) al variare della media log10 della concentrazione."""
    fig, ax = _figura()
    x = np.asarray(mu_values, dtype=float)
    for i, (nome, y) in enumerate(curve.items()):
        ax.plot(x, y, color=SERIE[i % len(SERIE)], linewidth=1.6, label=str(nome))
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlim(x.min(), x.max())
    _testi(ax, "Operating characteristic (OC) curves", "Mean log10 concentration (CFU/g)", "P(acceptance)")
    return fig
