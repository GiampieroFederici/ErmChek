"""Modulo A, conformità e campionamento: modello statistico del lotto per Listeria monocytogenes.

Concentrazione tra unità log-normale: log10 c (UFC/g) ~ N(mu, sigma). Presenza/assenza nella porzione
analitica con Poisson: P(negativo | c) = exp(-massa_g * c). Le funzioni restituiscono codici e numeri,
mai testo tradotto (lo traduce la GUI). Errori di input: ValueError con un codice breve."""
import math
from dataclasses import dataclass

import numpy as np
from scipy import integrate, optimize, stats

TIPI = ("assente", "conta", "sotto_lod")
SIGMA_MIN, SIGMA_MAX = 0.05, 5.0      # limiti della stima MLE di sigma (log10 UFC/g)
MU_MIN, MU_MAX = -8.0, 8.0            # limiti della stima MLE di mu (log10 UFC/g)
PI_MAX = 1.0 - 1e-6                   # limite superiore della frazione di unità non contaminate
LIMITE_UFC_G = 100.0                  # criterio di enumerazione (UFC/g), righe 1.2 e 1.3
SIGMA_SCRIPT = (0.5, 0.8, 1.0, 1.5, 2.0)
N_SIM_MAX = 10_000_000


def _numero(v, codice, minimo=None, massimo=None, incluso=True):
    """Numero finito dentro [minimo, massimo] (estremi esclusi se incluso=False), altrimenti ValueError(codice)."""
    if isinstance(v, bool):
        raise ValueError(codice)
    try:
        v = float(v)
    except (TypeError, ValueError):
        raise ValueError(codice) from None
    if not math.isfinite(v):
        raise ValueError(codice)
    if minimo is not None and (v < minimo or (not incluso and v == minimo)):
        raise ValueError(codice)
    if massimo is not None and (v > massimo or (not incluso and v == massimo)):
        raise ValueError(codice)
    return v


def _intero(v, codice, minimo):
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v < minimo:
        raise ValueError(codice)
    return int(v)


@dataclass(frozen=True)
class Risultato:
    """Risultato di una unità. tipo: assente (valore = massa analizzata, g), conta (UFC/g),
    sotto_lod (valore = LOD, UFC/g)."""
    tipo: str
    valore: float

    def __post_init__(self):
        if self.tipo not in TIPI:
            raise ValueError("TIPO_RISULTATO_SCONOSCIUTO")
        codice = {"assente": "MASSA_NON_POSITIVA", "conta": "CONTA_NON_POSITIVA",
                  "sotto_lod": "LOD_NON_POSITIVO"}[self.tipo]
        object.__setattr__(self, "valore", _numero(self.valore, codice, 0.0, incluso=False))


def assente(massa_g=25.0):
    """Non rilevata in massa_g grammi (presenza/assenza, es. EN ISO 11290-1)."""
    return Risultato("assente", massa_g)


def conta(ufc_g):
    """Conta in UFC/g (es. EN ISO 11290-2); trattata come ">= ufc_g" nella griglia, come nello script."""
    return Risultato("conta", ufc_g)


def sotto_lod(lod_ufc_g=10.0):
    """Conta sotto il limite di rilevabilità: < lod_ufc_g UFC/g."""
    return Risultato("sotto_lod", lod_ufc_g)


def conta_in_massa(ufc, massa_g=25.0):
    """Conta espressa come "ufc UFC in massa_g g" -> UFC/g (es. 5000 in 25 g = 200 UFC/g).
    ufc = 0 equivale a "non rilevata in massa_g g"."""
    ufc = _numero(ufc, "CONTA_NEGATIVA", 0.0)
    massa_g = _numero(massa_g, "MASSA_NON_POSITIVA", 0.0, incluso=False)
    return assente(massa_g) if ufc == 0 else conta(ufc / massa_g)


def _valida_risultati(risultati):
    if not isinstance(risultati, (list, tuple)) or not risultati:
        raise ValueError("RISULTATI_VUOTI")
    if not all(isinstance(r, Risultato) for r in risultati):
        raise ValueError("RISULTATO_NON_VALIDO")
    return tuple(risultati)


def _gruppi(risultati):
    """[(risultato, quante unità)] nell'ordine di prima comparsa."""
    g = {}
    for r in risultati:
        g[r] = g.get(r, 0) + 1
    return list(g.items())


def _coefficiente(gruppi):
    """Coefficiente multinomiale n! / prod(k!): modi di disporre il pattern fra le unità."""
    return math.factorial(sum(k for _, k in gruppi)) / math.prod(math.factorial(k) for _, k in gruppi)


def _p_neg(mu, s, massa_g, epsabs=1.49e-8):
    """P(negativo in massa_g) = integrale di exp(-massa*10^x) N(x; mu, s) dx (stessa chiamata quad dello script)."""
    f = lambda x: np.exp(-massa_g * 10**x) * stats.norm.pdf(x, mu, s)
    return integrate.quad(f, mu - 8*s, mu + 8*s, limit=200, epsabs=epsabs)[0]


def _p_unita(r, mu, s):
    """Probabilità di una unità nel pattern: assente (Poisson), conta (>= valore), sotto_lod (< LOD)."""
    if r.tipo == "assente":
        return _p_neg(mu, s, r.valore)
    if r.tipo == "conta":
        return stats.norm.sf(np.log10(r.valore), mu, s)
    return stats.norm.cdf(np.log10(r.valore), mu, s)


def griglia_pattern(risultati, sigmas=SIGMA_SCRIPT, mu_grid=None):
    """Probabilità massima del pattern osservato su una griglia di mu, per ogni sigma (come lo script).
    P = coefficiente multinomiale x prodotto delle P per unità. mu_grid default: np.arange(-4, 4.01, 0.05).
    Restituisce dict: sigma, p_max, mu_ottimale (array, log10 UFC/g; mu nan se P sempre 0), coefficiente."""
    gruppi = _gruppi(_valida_risultati(risultati))
    mu_grid = np.arange(-4, 4.01, 0.05) if mu_grid is None else mu_grid
    mu_grid = [_numero(m, "MU_FUORI_RANGE", -20.0, 20.0) for m in np.atleast_1d(mu_grid)]
    sigmas = [_numero(s, "SIGMA_NON_VALIDA", 0.0, 10.0, incluso=False) for s in np.atleast_1d(sigmas)]
    if not sigmas or not mu_grid:
        raise ValueError("GRIGLIA_VUOTA")
    coef = _coefficiente(gruppi)
    p_max, mu_ott = [], []
    for s in sigmas:
        best = (0.0, math.nan)
        for mu in mu_grid:
            p = coef
            for r, k in gruppi:
                p = p * _p_unita(r, mu, s)**k
            if p > best[0]:
                best = (p, mu)
        p_max.append(best[0])
        mu_ott.append(best[1])
    return {"sigma": np.array(sigmas), "p_max": np.array(p_max), "mu_ottimale": np.array(mu_ott),
            "coefficiente": coef}


def generazioni(a_ufc_g, da_ufc_g=10.0):
    """Aumento in log10 e numero di raddoppi (generazioni) da da_ufc_g ad a_ufc_g (UFC/g).
    Restituisce dict: aumento_log, generazioni."""
    a = _numero(a_ufc_g, "CONTA_NON_POSITIVA", 0.0, incluso=False)
    da = _numero(da_ufc_g, "CONTA_NON_POSITIVA", 0.0, incluso=False)
    aumento = np.log10(a) - np.log10(da)
    return {"aumento_log": float(aumento), "generazioni": float(aumento / np.log10(2))}


def replica_script():
    """Righe stampate dallo script di partenza (caso d'esame: 4 non rilevate in 25 g + 1 a >= 9000 UFC/g)."""
    g = griglia_pattern([conta(9000), assente(25), assente(25), assente(25), assente(25)])
    righe = [f"sigma={s}: max P={p:.2e} at mu={mu:.2f} log CFU/g"
             for s, p, mu in zip(SIGMA_SCRIPT, g["p_max"], g["mu_ottimale"])]
    gen = generazioni(9000, 10)
    righe.append(f"log increase from 10 CFU/g: {round(gen['aumento_log'], 2)} "
                 f"generations: {round(gen['generazioni'], 1)}")
    return righe


def _log_l(gruppi, mu, s, pi):
    """Log-verosimiglianza: conta = densità log10-normale, assente = integrale di Poisson, sotto_lod = CDF.
    pi = frazione di unità non contaminate (0 = log-normale semplice)."""
    tot = 0.0
    for r, k in gruppi:
        z = math.log10(r.valore)
        if r.tipo == "conta":
            tot += k * (math.log1p(-pi) + stats.norm.logpdf(z, mu, s))
            continue
        p = _p_neg(mu, s, r.valore, epsabs=0.0) if r.tipo == "assente" else stats.norm.cdf(z, mu, s)
        tot += k * math.log(max(pi + (1 - pi) * p, 1e-300))
    return tot


def log_verosimiglianza(risultati, mu, sigma, pi=0.0):
    """Log-verosimiglianza dei risultati dato mu, sigma (log10 UFC/g) e pi (frazione non contaminata)."""
    gruppi = _gruppi(_valida_risultati(risultati))
    mu = _numero(mu, "MU_FUORI_RANGE", -20.0, 20.0)
    sigma = _numero(sigma, "SIGMA_NON_VALIDA", 0.0, 10.0, incluso=False)
    pi = _numero(pi, "PI_FUORI_RANGE", 0.0, 1.0)
    if pi == 1.0:
        raise ValueError("PI_FUORI_RANGE")
    return _log_l(gruppi, mu, sigma, pi)


def _migliore(f, partenze, limiti, n_migliori=3):
    """Minimizza f (L-BFGS-B) partendo dai n_migliori punti di partenza; restituisce il risultato migliore."""
    partenze = sorted(partenze, key=f)[:n_migliori]
    esiti = [optimize.minimize(f, x0, method="L-BFGS-B", bounds=limiti) for x0 in partenze]
    return min(esiti, key=lambda e: e.fun)


_MU0 = np.arange(-6.0, 6.1, 1.5)
_SIGMA0 = (0.3, 1.0, 2.5)


def mle_lognormale(risultati):
    """Stima di massima verosimiglianza (continua) di mu, sigma su dati censurati; sigma in [0.05, 5].
    Restituisce dict: mu, sigma (log10 UFC/g), log_verosimiglianza, k (parametri = 2)."""
    gruppi = _gruppi(_valida_risultati(risultati))
    f = lambda x: -_log_l(gruppi, x[0], x[1], 0.0)
    partenze = [(m, s) for m in _MU0 for s in _SIGMA0]
    e = _migliore(f, partenze, [(MU_MIN, MU_MAX), (SIGMA_MIN, SIGMA_MAX)])
    return {"mu": float(e.x[0]), "sigma": float(e.x[1]), "log_verosimiglianza": float(-e.fun), "k": 2}


def mle_miscela(risultati):
    """MLE del modello a miscela (zero-inflated): frazione pi di unità non contaminate + log-normale
    (mu, sigma) per le contaminate. Restituisce dict: pi, mu, sigma, log_verosimiglianza, k (= 3)."""
    risultati = _valida_risultati(risultati)
    gruppi = _gruppi(risultati)
    ln = mle_lognormale(risultati)
    f = lambda x: -_log_l(gruppi, x[1], x[2], x[0])
    partenze = [(p, m, s) for p in (0.2, 0.5, 0.8) for m in _MU0 for s in _SIGMA0]
    limiti = [(0.0, PI_MAX), (MU_MIN, MU_MAX), (SIGMA_MIN, SIGMA_MAX)]
    e = _migliore(f, partenze, limiti)
    e0 = optimize.minimize(f, (0.0, ln["mu"], ln["sigma"]), method="L-BFGS-B", bounds=limiti)
    e = min((e, e0), key=lambda r: r.fun)   # modello annidato: mai peggio della log-normale
    return {"pi": float(e.x[0]), "mu": float(e.x[1]), "sigma": float(e.x[2]),
            "log_verosimiglianza": float(-e.fun), "k": 3}


def confronto_modelli(risultati):
    """Log-normale semplice contro miscela: AIC = 2k - 2 logL e statistica LR = 2 (logL_miscela - logL_lognormale).
    pi = 0 sta sul bordo dello spazio dei parametri, quindi sotto H0 il LR non segue chi2(1) ma la miscela
    50:50 di chi2(0) e chi2(1) (chi-bar-quadro, Self & Liang 1987, JASA 82:605-610): p = 0,5 x P(chi2_1 >= LR)
    per LR > 0, p = 1 per LR = 0. Approssimazione asintotica: con n piccolo è indicativa.
    Restituisce dict: lognormale, miscela (dict delle stime), aic_lognormale, aic_miscela, lr, p_valore."""
    risultati = _valida_risultati(risultati)
    ln, mi = mle_lognormale(risultati), mle_miscela(risultati)
    lr = max(0.0, 2 * (mi["log_verosimiglianza"] - ln["log_verosimiglianza"]))
    lr = 0.0 if lr < 1e-8 else lr
    p = 1.0 if lr == 0 else 0.5 * float(stats.chi2.sf(lr, 1))
    aic = lambda m: 2 * m["k"] - 2 * m["log_verosimiglianza"]
    return {"lognormale": ln, "miscela": mi, "aic_lognormale": aic(ln), "aic_miscela": aic(mi),
            "lr": lr, "p_valore": p}


def interpretazione(risultati, alfa=0.05):
    """Codice di interpretazione del lotto: CONTAMINAZIONE_LOCALIZZATA se la miscela è preferita (p del LR < alfa),
    altrimenti LOTTO_OMOGENEO. Restituisce dict: codice, p_valore, lr, aic_lognormale, aic_miscela, pi, alfa."""
    alfa = _numero(alfa, "ALFA_FUORI_RANGE", 0.0, 1.0, incluso=False)
    c = confronto_modelli(risultati)
    codice = "CONTAMINAZIONE_LOCALIZZATA" if c["p_valore"] < alfa else "LOTTO_OMOGENEO"
    return {"codice": codice, "p_valore": c["p_valore"], "lr": c["lr"], "aic_lognormale": c["aic_lognormale"],
            "aic_miscela": c["aic_miscela"], "pi": c["miscela"]["pi"], "alfa": alfa}


def curva_oc(n, c, sigma, porzione_g, mu_values, criterio):
    """Curva operativa: P(accettazione del lotto) per ogni mu (log10 UFC/g), piano n, c.
    criterio: presenza_assenza (unità difettosa = rilevata in porzione_g) | enumerazione (> 100 UFC/g;
    porzione_g non usata). Restituisce array di P(accettazione)."""
    n = _intero(n, "N_NON_VALIDO", 1)
    c = _intero(c, "C_NON_VALIDO", 0)
    if c > n:
        raise ValueError("C_NON_VALIDO")
    sigma = _numero(sigma, "SIGMA_NON_VALIDA", 0.0, 10.0, incluso=False)
    porzione_g = _numero(porzione_g, "MASSA_NON_POSITIVA", 0.0, incluso=False)
    mu_values = [_numero(m, "MU_FUORI_RANGE", -20.0, 20.0) for m in np.atleast_1d(mu_values)]
    if criterio == "presenza_assenza":
        p_dif = [1.0 - _p_neg(m, sigma, porzione_g, epsabs=0.0) for m in mu_values]
    elif criterio == "enumerazione":
        p_dif = [stats.norm.sf(math.log10(LIMITE_UFC_G), m, sigma) for m in mu_values]
    else:
        raise ValueError("CRITERIO_SCONOSCIUTO")
    return stats.binom.cdf(c, n, np.clip(p_dif, 0.0, 1.0))


def prevalenza(k, n, conf=0.95):
    """Prevalenza k/n con intervallo esatto di Clopper-Pearson al livello conf.
    Restituisce dict: stima, inferiore, superiore, conf."""
    n = _intero(n, "N_NON_VALIDO", 1)
    k = _intero(k, "K_NON_VALIDO", 0)
    if k > n:
        raise ValueError("K_NON_VALIDO")
    conf = _numero(conf, "CONF_FUORI_RANGE", 0.0, 1.0, incluso=False)
    a = 1 - conf
    inf = 0.0 if k == 0 else float(stats.beta.ppf(a / 2, k, n - k + 1))
    sup = 1.0 if k == n else float(stats.beta.ppf(1 - a / 2, k + 1, n - k))
    return {"stima": k / n, "inferiore": inf, "superiore": sup, "conf": conf}


def n_necessario(p, conf=0.95):
    """Numero di unità per rilevare almeno una positiva con prevalenza p e confidenza conf:
    ceil(ln(1 - conf) / ln(1 - p))."""
    p = _numero(p, "P_FUORI_RANGE", 0.0, 1.0, incluso=False)
    conf = _numero(conf, "CONF_FUORI_RANGE", 0.0, 1.0, incluso=False)
    return math.ceil(round(math.log(1 - conf) / math.log(1 - p), 9))   # round: evita 2.0000000000000004 -> 3


def monte_carlo_pattern(mu, sigma, risultati, n_sim=1_000_000, seed=20260701):
    """Verifica per simulazione (seed fisso) della probabilità analitica del pattern di griglia_pattern.
    Simula le unità nell'ordine dato (conta: >= valore; assente: Poisson zero in massa; sotto_lod: < LOD)
    e moltiplica per il coefficiente multinomiale. Restituisce dict: p_mc, errore_standard, p_analitica, n_sim, seed."""
    risultati = _valida_risultati(risultati)
    mu = _numero(mu, "MU_FUORI_RANGE", -20.0, 20.0)
    sigma = _numero(sigma, "SIGMA_NON_VALIDA", 0.0, 10.0, incluso=False)
    n_sim = _intero(n_sim, "N_SIM_NON_VALIDO", 1)
    if n_sim > N_SIM_MAX:
        raise ValueError("N_SIM_NON_VALIDO")
    seed = _intero(seed, "SEED_NON_VALIDO", 0)
    rng = np.random.default_rng(seed)
    x = rng.normal(mu, sigma, size=(n_sim, len(risultati)))
    ok = np.ones(n_sim, dtype=bool)
    for j, r in enumerate(risultati):
        z = math.log10(r.valore)
        if r.tipo == "conta":
            ok &= x[:, j] >= z
        elif r.tipo == "sotto_lod":
            ok &= x[:, j] < z
        else:
            ok &= rng.random(n_sim) < np.exp(-r.valore * 10.0**x[:, j])
    gruppi = _gruppi(risultati)
    coef = _coefficiente(gruppi)
    p_ord = float(ok.mean())
    p_an = coef * math.prod(_p_unita(r, mu, sigma)**k for r, k in gruppi)
    return {"p_mc": coef * p_ord, "errore_standard": coef * math.sqrt(p_ord * (1 - p_ord) / n_sim),
            "p_analitica": float(p_an), "n_sim": n_sim, "seed": seed}
