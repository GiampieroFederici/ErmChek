"""Modulo B: crescita di L. monocytogenes nel tempo, con condizioni che cambiano per fasi.

Modello secondario: FSSP (Mejlholm & Dalgaard 2009; LAB 2013; confine Le Marc et al. 2002), da ermchek.core.fssp.
Modello primario, a scelta:
  "fssp"     logistico con effetto Jameson (Giménez & Dalgaard 2004), passi da 1 minuto come FSSP; con condizioni
             costanti dà gli stessi numeri del motore di PMN (modalità "migliorata", provata uguale a FSSP);
  "baranyi"  Baranyi & Roberts (1994) con m = 1 e lag da h0; senza batteri lattici (niente Jameson).
Condizioni dinamiche: a ogni fase si ricalcola mu_max con le condizioni di quella fase (T, pH, aw, nitrito...).
Il modello descrive solo la crescita: non prevede mai la morte di Lm (nessuna inattivazione documentata).

Tutti i calcoli sono vettoriali su n simulazioni (n = 1 per la previsione, n > 1 per il Monte Carlo).
"""
import csv
import math
from dataclasses import dataclass, field

import numpy as np

from .fssp import validita
from .fssp.calcolatrici import sale_da_aw, sale_fase_acquosa
from .fssp.modelli import ACIDI, LAB, LISTERIA, LN2_FSSP, RLT_LISTERIA, Prodotto, aw_da_sale, condizioni, secondario

# campi plausibili (sicurezza degli ingressi, non campo di validità del modello)
LIMITI = {"temperatura": (-2.0, 40.0), "ph": (3.5, 8.0), "aw": (0.85, 1.0), "sale_fase_acquosa": (0.0, 40.0),
          "nitrito": (0.0, 10000.0), "fenoli": (0.0, 1000.0), "co2": (0.0, 100.0), "acido": (0.0, 1e6),
          "ore": (1e-6, 365.0 * 24.0)}
H0_FSSP = RLT_LISTERIA * LN2_FSSP   # h0 di Baranyi equivalente al tempo di ritardo relativo di FSSP (lag = h0 / mu)


def _controlla(nome, v, chiave=None):
    lo, hi = LIMITI[chiave or nome]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(f"FUORI_LIMITE:{nome}")
    return float(v)


@dataclass(frozen=True)
class Fase:
    """Un tratto a condizioni costanti. Il sale si dà come aw OPPURE come sale nella fase acquosa (mai entrambi)."""
    ore: float
    temperatura: float
    ph: float
    aw: float | None = None
    sale_fase_acquosa: float | None = None
    nitrito: float = 0.0                     # nitrito residuo, mg/kg
    acidi: dict = field(default_factory=dict)  # ppm nella fase acquosa
    fenoli: float = 0.0
    co2: float = 0.0                         # % nello spazio di testa

    def prodotto(self):
        """Prodotto di FSSP per questa fase (aw convertita in sale con la calcolatrice di FSSP)."""
        if (self.aw is None) == (self.sale_fase_acquosa is None):
            raise ValueError("AW_OPPURE_SALE")   # niente doppio conteggio: o aw o sale nella fase acquosa
        _controlla("ore", self.ore)
        sale = (sale_da_aw(_controlla("aw", self.aw)) if self.aw is not None
                else _controlla("sale_fase_acquosa", self.sale_fase_acquosa))
        acidi = {}
        for a, v in self.acidi.items():
            if a not in ACIDI:
                raise ValueError(f"ACIDO_SCONOSCIUTO:{a}")
            acidi[a] = _controlla(a, v, "acido")
        return Prodotto(temperatura=_controlla("temperatura", self.temperatura), sale_fase_acquosa=sale,
                        ph=_controlla("ph", self.ph), fenoli=_controlla("fenoli", self.fenoli),
                        co2=_controlla("co2", self.co2), nitrito=_controlla("nitrito", self.nitrito), acidi=acidi)


def wps(nacl_prodotto, umidita):
    """Sale nella fase acquosa (%) da NaCl sul prodotto (%) e umidità (%): NaCl / (NaCl + acqua) x 100."""
    if not 0 <= nacl_prodotto <= 40 or not 0 < umidita <= 100:
        raise ValueError("FUORI_LIMITE:wps")
    return sale_fase_acquosa(nacl_prodotto, 100.0 - umidita)


def leggi_csv_temperature(percorso, max_righe=200000):
    """CSV del data logger: due colonne, tempo in ore (crescente, da 0) e temperatura in °C; intestazione facoltativa.
    Restituisce [(ore_inizio, temperatura)]. Ogni valore è controllato; niente eval."""
    punti = []
    with open(percorso, newline="", encoding="utf-8-sig") as fh:
        campione = fh.read(4096)
        fh.seek(0)
        sep = ";" if campione.count(";") > campione.count(",") else ","
        for i, riga in enumerate(csv.reader(fh, delimiter=sep)):
            if i >= max_righe:
                raise ValueError("CSV_TROPPO_LUNGO")
            if not riga or all(not c.strip() for c in riga):
                continue
            if len(riga) < 2:
                raise ValueError(f"CSV_RIGA:{i + 1}")
            try:
                ore, t = (float(c.strip().replace(",", ".")) if sep == ";" else float(c.strip()) for c in riga[:2])
            except ValueError:
                if i == 0:
                    continue   # intestazione
                raise ValueError(f"CSV_RIGA:{i + 1}") from None
            if not (math.isfinite(ore) and math.isfinite(t)) or not LIMITI["temperatura"][0] <= t <= LIMITI["temperatura"][1]:
                raise ValueError(f"CSV_RIGA:{i + 1}")
            if punti and ore <= punti[-1][0]:
                raise ValueError(f"CSV_TEMPO_NON_CRESCENTE:{i + 1}")
            punti.append((ore, t))
    if len(punti) < 2 or punti[0][0] != 0.0:
        raise ValueError("CSV_SERVONO_ALMENO_2_PUNTI_DA_ZERO")
    return punti


def applica_temperature(fasi, punti):
    """Sostituisce le temperature delle fasi con quelle del data logger: ogni intervallo fra due letture usa la
    temperatura della prima; le altre condizioni restano quelle della fase in corso. Durata = quella delle fasi."""
    from dataclasses import replace
    totale = sum(f.ore for f in fasi)
    confini = sorted({0.0, totale, *[o for o, _t in punti if 0 < o < totale],
                      *np.cumsum([f.ore for f in fasi])[:-1].tolist()})
    nuove = []
    for a, b in zip(confini[:-1], confini[1:]):
        fase = _fase_al_tempo(fasi, a)
        t = [tt for o, tt in punti if o <= a][-1]
        nuove.append(replace(fase, ore=b - a, temperatura=t))
    return nuove


def _fase_al_tempo(fasi, ore):
    inizio = 0.0
    for f in fasi:
        if ore < inizio + f.ore:
            return f
        inizio += f.ore
    return fasi[-1]


def _passi(ore, intervallo_min=1.0):
    """Durate dei passi (h) di una fase: passi da 1 minuto, l'ultimo più corto (come espandi() di FSSP/PMN)."""
    minuti = ore * 60.0
    n = int(math.floor(minuti / intervallo_min))
    if minuti - intervallo_min * n > 0.0001:
        n += 1
    out = []
    for _ in range(n):
        if minuti > intervallo_min:
            out.append(intervallo_min / 60.0)
            minuti -= intervallo_min
        else:
            out.append(minuti / 60.0)
    return out


def _mu(par, prodotto, temperature):
    """mu_max e psi per un vettore di temperature (stesso prodotto)."""
    mu, psi = np.zeros(len(temperature)), np.full(len(temperature), np.nan)
    for i, t in enumerate(temperature):
        s = secondario(par, condizioni(prodotto, temperatura=float(t)))
        mu[i] = 0.0 if s.bloccato else s.mu
        psi[i] = np.nan if s.psi is None else s.psi
    return mu, psi


def simula(fasi, n0, lab0=None, modello="fssp", lag=False, gamma=1.0, h0=H0_FSSP, n=1, sd_temperatura=0.0,
           log_n0_sd=0.0, fattore_mu=None, seed=20261103, registra_ogni_min=None):
    """Curva di Lm (e dei LAB) lungo le fasi.

    n0, lab0: ufc/g a t0 (lab0 None = senza batteri lattici). n: numero di simulazioni (Monte Carlo se > 1):
    temperatura di ogni fase ~ N(T, sd_temperatura), log N0 ~ N(log n0, log_n0_sd), mu_max moltiplicata per
    fattore_mu (array lungo n, facoltativo: incertezza di mu_max, opzione avanzata).
    Restituisce un dict con tempi (giorni), log_lm [n x punti], log_lab, info per fase, avvisi."""
    if not fasi:
        raise ValueError("NESSUNA_FASE")
    if modello not in ("fssp", "baranyi"):
        raise ValueError("MODELLO_SCONOSCIUTO")
    if modello == "baranyi" and lab0 is not None:
        raise ValueError("BARANYI_SENZA_LAB")
    if not 0.0 <= gamma <= 2.0 or n < 1 or n > 100000:
        raise ValueError("FUORI_LIMITE:simulazioni")
    if not 0.0 < n0 <= LISTERIA.nmax or (lab0 is not None and not 0.0 < lab0 <= LAB.nmax):
        raise ValueError("FUORI_LIMITE:concentrazione_iniziale")
    prodotti = [f.prodotto() for f in fasi]
    rng = np.random.default_rng(seed)
    temp = np.array([[f.temperatura] * n for f in fasi], dtype=float)
    if n > 1 and sd_temperatura > 0:
        temp = temp + rng.normal(0.0, sd_temperatura, size=temp.shape)
        temp = np.clip(temp, LIMITI["temperatura"][0], LIMITI["temperatura"][1])
    mu_lm, psi_lm, mu_lab = [], [], []
    for p, t in zip(prodotti, temp):
        if n > 1 and sd_temperatura > 0:
            m, s = _mu(LISTERIA, p, t)
            ml = _mu(LAB, p, t)[0] if lab0 is not None else np.zeros(n)
        else:   # stessa temperatura per tutte le simulazioni: un solo calcolo
            m, s = (np.repeat(x, n) for x in _mu(LISTERIA, p, t[:1]))
            ml = np.repeat(_mu(LAB, p, t[:1])[0], n) if lab0 is not None else np.zeros(n)
        if fattore_mu is not None:
            m = m * np.asarray(fattore_mu, dtype=float)
        mu_lm.append(m), psi_lm.append(s), mu_lab.append(ml)

    log0 = np.full(n, math.log10(n0))
    if n > 1 and log_n0_sd > 0:
        log0 = log0 + rng.normal(0.0, log_n0_sd, n)
    n_lm = np.minimum(10.0 ** log0, LISTERIA.nmax)
    n_lab = np.full(n, float(lab0)) if lab0 is not None else np.zeros(n)
    nmax_lm, nmax_lab = LISTERIA.nmax, LAB.nmax
    passo_lm, passo_lab = mu_lm[0].copy(), mu_lab[0].copy()
    frazione = np.ones(n)                                    # lag di FSSP: frazione di lag ancora da consumare
    q = np.full(n, 1.0 / math.expm1(h0)) if lag else None    # stato fisiologico di Baranyi

    ogni = registra_ogni_min or (1 if n == 1 else 60)
    tempi, curve_lm, curve_lab = [0.0], [np.log10(n_lm)], [np.log10(np.maximum(n_lab, 1e-300))]
    t, k = 0.0, 0
    for i, fase in enumerate(fasi):
        m_lm, m_lab = mu_lm[i], mu_lab[i]
        for dt in _passi(fase.ore):
            if modello == "fssp":
                if lab0 is not None:
                    n_lab = n_lab * np.exp(passo_lab * dt)
                if lag:
                    ore_lag = np.where(m_lm > 0.0, RLT_LISTERIA * LN2_FSSP / np.where(m_lm > 0, m_lm, 1.0), np.inf)
                    frazione = frazione - dt / ore_lag
                    n_lm = np.where(frazione < 0.0, n_lm * np.exp(passo_lm * dt), n_lm)
                else:
                    n_lm = n_lm * np.exp(passo_lm * dt)
                passo_lab = m_lab * (1.0 - n_lab / nmax_lab) * (1.0 - n_lm / nmax_lm)
                passo_lm = m_lm * (1.0 - n_lm / nmax_lm) * (1.0 - gamma * n_lab / nmax_lab)
            else:   # Baranyi & Roberts 1994, m = 1: dlnN/dt = mu * alpha(t) * (1 - N/Nmax), alpha = q / (1 + q)
                alfa = q / (1.0 + q) if lag else 1.0
                n_lm = n_lm * np.exp(m_lm * alfa * (1.0 - n_lm / nmax_lm) * dt)
                if lag:
                    q = q * np.exp(m_lm * dt)
            t += dt
            k += 1
            if k % ogni == 0:
                tempi.append(t / 24.0), curve_lm.append(np.log10(n_lm)), curve_lab.append(np.log10(np.maximum(n_lab, 1e-300)))
    if k % ogni != 0:
        tempi.append(t / 24.0), curve_lm.append(np.log10(n_lm)), curve_lab.append(np.log10(np.maximum(n_lab, 1e-300)))

    log_lm = np.array(curve_lm).T                      # [n, punti]
    log_lab = np.array(curve_lab).T if lab0 is not None else None
    tempi = np.array(tempi)
    info = [{"ore": f.ore, "temperatura": f.temperatura, "ph": f.ph, "sale_fase_acquosa": p.sale_fase_acquosa,
             "aw": aw_da_sale(p.sale_fase_acquosa), "mu_lm": float(mu_lm[i][0]), "psi_lm": float(psi_lm[i][0]),
             "mu_lab": float(mu_lab[i][0]) if lab0 is not None else None,
             "puo_crescere": bool(mu_lm[i][0] > 0.0)} for i, (f, p) in enumerate(zip(fasi, prodotti))]
    return {"modello": modello, "lag": lag, "tempi_giorni": tempi, "log_lm": log_lm, "log_lab": log_lab,
            "fasi": info, "crescita_possibile": any(x["puo_crescere"] for x in info),
            "avvisi": avvisi(fasi, prodotti, lab0 is not None, modello)}


def avvisi(fasi, prodotti, con_lab, modello):
    """Codici di avviso: fuori dal campo di validità, pH < 6 con Jameson, sola crescita."""
    uscita, visti = [], set()
    nome = "listeria_lab" if con_lab else "listeria"
    for f, p in zip(fasi, prodotti):
        for a in validita.avvisi(nome, p, [(f.temperatura, f.ore)]):
            chiave = (a["fattore"], a["valore"])
            if chiave not in visti:
                visti.add(chiave)
                uscita.append({"codice": "FUORI_CAMPO", "fattore": a["fattore"], "valore": a["valore"], "campo": a["campo"]})
    if con_lab and any(f.ph < 6.0 for f in fasi):
        uscita.append({"codice": "JAMESON_PH_SOTTO_6"})
    if modello == "baranyi":
        uscita.append({"codice": "BARANYI_NON_VALIDATO_FSSP"})
    uscita.append({"codice": "SOLO_CRESCITA"})
    return uscita


def riassunto(sim, indice=0, limite_ufc_g=100.0):
    """Numeri chiave di una curva: finale, delta (crescita potenziale), tempo per arrivare al limite."""
    tempi, log = sim["tempi_giorni"], sim["log_lm"][indice]
    soglia = math.log10(limite_ufc_g)
    giorni_limite = None
    if log[0] < soglia:
        sopra = np.nonzero(log >= soglia)[0]
        if sopra.size:
            j = int(sopra[0])
            giorni_limite = float(tempi[j - 1] + (soglia - log[j - 1]) / (log[j] - log[j - 1]) * (tempi[j] - tempi[j - 1]))
    return {"log_iniziale": float(log[0]), "log_finale": float(log[-1]), "ufc_g_finale": float(10 ** log[-1]),
            "delta": float(log.max() - log[0]), "giorni_al_limite": giorni_limite,
            "log_lab_finale": float(sim["log_lab"][indice][-1]) if sim["log_lab"] is not None else None}


def monte_carlo(fasi, n0, log_n0_sd=0.0, lab0=None, sd_temperatura=0.0, cv_mu=None, n=1000, seed=20261103,
                limite_ufc_g=100.0, **opzioni):
    """Variabilità e incertezza: percentili 5/50/95 del log finale e P(> limite a fine periodo).
    cv_mu: incertezza di mu_max (opzione avanzata, spenta = None): fattore lognormale con sd ln(1 + cv_mu)."""
    rng = np.random.default_rng(seed + 1)
    fattore = None if not cv_mu else np.exp(rng.normal(0.0, math.log1p(cv_mu), n))
    sim = simula(fasi, n0, lab0=lab0, n=n, sd_temperatura=sd_temperatura, log_n0_sd=log_n0_sd, fattore_mu=fattore,
                 seed=seed, **opzioni)
    finali = sim["log_lm"][:, -1]
    p5, p50, p95 = np.percentile(finali, [5, 50, 95])
    return {"sim": sim, "log_finale_p5": float(p5), "log_finale_p50": float(p50), "log_finale_p95": float(p95),
            "p_sopra_limite": float(np.mean(finali > math.log10(limite_ufc_g))), "n": n, "seed": seed,
            "curva_p5": np.percentile(sim["log_lm"], 5, axis=0), "curva_p50": np.percentile(sim["log_lm"], 50, axis=0),
            "curva_p95": np.percentile(sim["log_lm"], 95, axis=0)}
