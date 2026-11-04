"""ErmChek da riga di comando: gli stessi calcoli dell'interfaccia, senza finestre.

  python -m ermchek.cli replicate-script
  python -m ermchek.cli grow --input caso.json [--pdf report.pdf] [--lang it|en]
  python -m ermchek.cli back --input caso.json [--pdf report.pdf] [--lang it|en]

Il file JSON (solo json.load, solo chiavi note, solo numeri dove serve un numero):
  {"titolo": "...", "fasi": [{"ore": 48, "temperatura": 20, "ph": 5.9, "aw": 0.965, "nitrito": 40}, ...],
   grow: "n0": 1.0, "lab0": 1e4 (facoltativo), "modello": "fssp"|"baranyi", "lag": false
   back: "osservato_ufc_g": 300  oppure  "osservato_ufc": 7500 con "massa_g": 25,
         "lab0", "modello", "peso_pezzo_g", "u_misura_log", "n_mc"}
Ogni fase: ore, temperatura, ph, aw OPPURE sale_fase_acquosa, e facoltativi nitrito, fenoli, co2, acidi {nome: ppm}.
Errore negli ingressi: messaggio chiaro e codice di uscita 1.
"""
import argparse
import json
import math
import sys
from pathlib import Path

from ermchek import lingua, testi
from ermchek.lingua import _

MAX_BYTE = 1_000_000
MAX_FASI = 1000
CHIAVI_FASE = {"ore", "temperatura", "ph", "aw", "sale_fase_acquosa", "nitrito", "acidi", "fenoli", "co2"}
NUMERI_FASE = CHIAVI_FASE - {"acidi", "aw", "sale_fase_acquosa"}
CHIAVI = {"grow": {"titolo", "fasi", "phases", "n0", "lab0", "modello", "lag"},
          "back": {"titolo", "fasi", "phases", "osservato_ufc_g", "osservato_ufc", "massa_g", "lab0", "modello",
                   "peso_pezzo_g", "u_misura_log", "n_mc"}}


class ErroreIngresso(ValueError):
    pass


def _numero(v, campo, facoltativo=False):
    if v is None and facoltativo:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ErroreIngresso(_("Il campo \"{c}\" deve essere un numero.", c=campo))
    return float(v)


def _rifiuta_costante(nome):
    raise ErroreIngresso(_("Il file contiene {n}: non è un numero valido.", n=nome))


def leggi_json(percorso):
    """Legge il JSON del caso (al massimo 1 MB). Solo json.load, mai eval."""
    p = Path(percorso)
    if not p.is_file():
        raise ErroreIngresso(_("File non trovato: {p}", p=percorso))
    if p.stat().st_size > MAX_BYTE:
        raise ErroreIngresso(_("Il file è troppo grande (massimo 1 MB)."))
    try:
        with open(p, encoding="utf-8-sig") as fh:
            dati = json.load(fh, parse_constant=_rifiuta_costante)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ErroreIngresso(_("Il file non è un JSON valido: {e}", e=e)) from None
    if not isinstance(dati, dict):
        raise ErroreIngresso(_("Il file deve contenere un oggetto JSON con le chiavi del caso."))
    return dati


def _fasi(dati):
    from ermchek.core.crescita import Fase
    if "fasi" in dati and "phases" in dati:
        raise ErroreIngresso(_("Usa \"fasi\" oppure \"phases\", non entrambe."))
    grezze = dati.get("fasi", dati.get("phases"))
    if not isinstance(grezze, list) or not grezze:
        raise ErroreIngresso(_("Serve \"fasi\": una lista di fasi, almeno una."))
    if len(grezze) > MAX_FASI:
        raise ErroreIngresso(_("Troppe fasi (massimo {n}).", n=MAX_FASI))
    fasi = []
    for i, f in enumerate(grezze, 1):
        if not isinstance(f, dict):
            raise ErroreIngresso(_("Fase {i}: deve essere un oggetto con ore, temperatura, ph...", i=i))
        ignote = set(f) - CHIAVI_FASE
        if ignote:
            raise ErroreIngresso(_("Fase {i}: chiave sconosciuta {k}.", i=i, k=", ".join(sorted(ignote))))
        for k in ("ore", "temperatura", "ph"):
            if k not in f:
                raise ErroreIngresso(_("Fase {i}: manca \"{k}\".", i=i, k=k))
        arg = {k: _numero(f[k], f"fasi[{i}].{k}") for k in NUMERI_FASE if k in f}
        for k in ("aw", "sale_fase_acquosa"):
            if k in f:
                arg[k] = _numero(f[k], f"fasi[{i}].{k}", facoltativo=True)
        if "acidi" in f:
            if not isinstance(f["acidi"], dict):
                raise ErroreIngresso(_("Fase {i}: \"acidi\" deve essere un oggetto {{nome: ppm}}.", i=i))
            arg["acidi"] = {str(a): _numero(v, f"fasi[{i}].acidi.{a}") for a, v in f["acidi"].items()}
        fasi.append(Fase(**arg))
    return fasi


def _controlla_chiavi(dati, comando):
    ignote = set(dati) - CHIAVI[comando]
    if ignote:
        raise ErroreIngresso(_("Chiave sconosciuta: {k}. Chiavi ammesse: {a}.", k=", ".join(sorted(ignote)),
                               a=", ".join(sorted(CHIAVI[comando]))))
    if "titolo" in dati and not isinstance(dati["titolo"], str):
        raise ErroreIngresso(_("Il campo \"titolo\" deve essere un testo."))
    if dati.get("modello", "fssp") not in ("fssp", "baranyi"):
        raise ErroreIngresso(_("Il campo \"modello\" deve essere \"fssp\" oppure \"baranyi\"."))


def _righe_fasi_testo(fasi):
    from ermchek.core.fssp.validita import numero_it
    return [(_("Fasi"), _("{n} fasi, {g} giorni in tutto", n=len(fasi), g=numero_it(sum(f.ore for f in fasi) / 24, 1)))]


def _grow(dati, pdf):
    from ermchek.core.crescita import riassunto, simula
    from ermchek.core.fssp.validita import numero_it
    from ermchek.report.pdf import crea_pdf, sig
    _controlla_chiavi(dati, "grow")
    fasi = _fasi(dati)
    if "n0" not in dati:
        raise ErroreIngresso(_("Serve \"n0\": Listeria all'inizio, in ufc/g."))
    n0 = _numero(dati["n0"], "n0")
    lab0 = _numero(dati.get("lab0"), "lab0", facoltativo=True)
    lag = dati.get("lag", False)
    if not isinstance(lag, bool):
        raise ErroreIngresso(_("Il campo \"lag\" deve essere true oppure false."))
    modello = dati.get("modello", "fssp")
    sim = simula(fasi, n0, lab0=lab0, modello=modello, lag=lag)
    r = riassunto(sim)
    print(_("Listeria all'inizio: {n} ufc/g", n=sig(n0, 3, False)))
    print(_("Listeria alla fine: {n} ufc/g", n=sig(r["ufc_g_finale"], 3, False)))
    print(_("Potenziale di crescita δ: {d} log", d=numero_it(r["delta"], 2)))
    print(_("Giorni per arrivare a 100 ufc/g: {g}", g=numero_it(r["giorni_al_limite"], 1)
            if r["giorni_al_limite"] is not None else _("non arriva")))
    for a in dict.fromkeys(testi.avviso(a) for a in sim["avvisi"]):
        print(_("Avviso: {a}", a=a))
    if pdf:
        righe = [(_("Listeria all'inizio"), _("{n} ufc/g", n=sig(n0, 3, False)))]
        if lab0 is not None:
            righe.append((_("Batteri lattici all'insacco"), _("{n} ufc/g", n=sig(lab0, 3, False))))
        righe += [(_("Modello"), modello.upper() if modello == "fssp" else "Baranyi"),
                  (_("Fase di latenza (lag)"), _("sì") if lag else _("no"))]
        ingressi = {"titolo": dati.get("titolo", ""), "righe": righe, "contesto": [], "fasi": fasi}
        crea_pdf(pdf, "crescita", {"sim": sim, "riassunto": r, "mc": None}, ingressi)
        print(_("PDF scritto: {p}", p=pdf))


def _back(dati, pdf):
    from ermchek.core.fssp.validita import numero_it
    from ermchek.core.retro import retro
    from ermchek.report.pdf import crea_pdf, sig
    _controlla_chiavi(dati, "back")
    fasi = _fasi(dati)
    if "osservato_ufc_g" in dati:
        if "osservato_ufc" in dati or "massa_g" in dati:
            raise ErroreIngresso(_("Usa \"osservato_ufc_g\" oppure \"osservato_ufc\" con \"massa_g\", non entrambi."))
        osservato = _numero(dati["osservato_ufc_g"], "osservato_ufc_g")
        testo_oss = _("{n} ufc/g", n=sig(osservato, 3, False))
    elif "osservato_ufc" in dati:
        ufc = _numero(dati["osservato_ufc"], "osservato_ufc")
        massa = _numero(dati.get("massa_g", 25.0), "massa_g")
        if massa <= 0:
            raise ErroreIngresso(_("Il campo \"massa_g\" deve essere maggiore di zero."))
        osservato = ufc / massa
        testo_oss = _("{u} ufc in {m} g ({n} ufc/g)", u=sig(ufc, 4, False), m=numero_it(massa, 1),
                      n=sig(osservato, 3, False))
    else:
        raise ErroreIngresso(_("Serve \"osservato_ufc_g\" (ufc/g) oppure \"osservato_ufc\" con \"massa_g\"."))
    lab0 = _numero(dati.get("lab0"), "lab0", facoltativo=True)
    peso = _numero(dati.get("peso_pezzo_g"), "peso_pezzo_g", facoltativo=True)
    u = _numero(dati.get("u_misura_log", 0.5), "u_misura_log")
    n_mc = dati.get("n_mc", 2000)
    if isinstance(n_mc, bool) or not isinstance(n_mc, int) or not 0 <= n_mc <= 100000:
        raise ErroreIngresso(_("Il campo \"n_mc\" deve essere un numero intero da 0 a 100000."))
    modello = dati.get("modello", "fssp")
    ris = retro(fasi, osservato, lab0=lab0, modello=modello, u_misura_log=u, peso_pezzo_g=peso, n_mc=n_mc)
    p, mc = ris["principale"], ris["monte_carlo"]
    print(_("N0 ≈ {n} ufc/g, cioè {m} ufc in 25 g", n=sig(p["ufc_g"], 3, False), m=sig(p["ufc_25g"], 2, False)))
    if mc:
        print(_("Intervallo al 90 %: da {a} a {b} ufc/g", a=sig(10 ** mc["log_n0_p5"], 2, False),
                b=sig(10 ** mc["log_n0_p95"], 2, False)))
    if lab0 is not None:
        print(_("Caso peggiore senza batteri lattici: {n} ufc/g", n=sig(ris["peggiore"]["ufc_g"], 2, False)))
    for a in dict.fromkeys(testi.avviso(a) for a in ris["avvisi"]):
        print(_("Avviso: {a}", a=a))
    if pdf:
        righe = [(_("Listeria misurata"), testo_oss),
                 (_("Giorno dell'analisi"), numero_it(ris["giorni"], 1))]
        if lab0 is not None:
            righe.append((_("Batteri lattici all'insacco"), _("{n} ufc/g", n=sig(lab0, 3, False))))
        if peso is not None:
            righe.append((_("Peso del pezzo"), _("{n} g", n=numero_it(peso, 1))))
        righe.append((_("Incertezza di misura"), _("{n} log", n=numero_it(u, 2))))
        ingressi = {"titolo": dati.get("titolo", ""), "righe": righe, "contesto": [], "fasi": fasi}
        crea_pdf(pdf, "retro", ris, ingressi)
        print(_("PDF scritto: {p}", p=pdf))


def main(argv=None):
    for flusso in (sys.stdout, sys.stderr):   # console o pipe con codifica limitata: mai un errore per un simbolo
        try:
            flusso.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog="python -m ermchek.cli",
                                     description="ErmChek: Listeria monocytogenes in ready-to-eat foods.")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("replicate-script", help="print the 6 lines of the original exam script")
    for nome, aiuto in (("grow", "growth from the initial level"), ("back", "back-calculation of the initial level")):
        s = sub.add_parser(nome, help=aiuto)
        s.add_argument("--input", required=True, help="case file (JSON)")
        s.add_argument("--pdf", help="write the PDF report here")
        s.add_argument("--lang", choices=sorted(lingua.LINGUE), default="it", help="report language (default it)")
    args = parser.parse_args(argv)

    if args.comando == "replicate-script":
        from ermchek.core.conformita import replica_script
        for riga in replica_script():
            print(riga)
        return 0
    lingua.imposta(args.lang)
    try:
        dati = leggi_json(args.input)
        (_grow if args.comando == "grow" else _back)(dati, args.pdf)
    except ErroreIngresso as e:
        print(_("Errore: {e}", e=e), file=sys.stderr)
        return 1
    except ValueError as e:   # codici del core (FUORI_LIMITE, AW_OPPURE_SALE...) in frasi
        print(_("Errore: {e}", e=testi.errore(e)), file=sys.stderr)
        return 1
    except OSError as e:
        print(_("Errore: impossibile scrivere il file ({e}).", e=e.strerror or e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
