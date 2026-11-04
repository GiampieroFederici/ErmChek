"""Esportazione dei risultati in Excel (openpyxl) e della curva in CSV. Numeri come numeri, testi nella lingua scelta.

  esporta_excel(percorso, tipo, risultato, ingressi)   fogli: Riepilogo, Ingressi, Curva + Scenari (retro),
                                                       Curva (crescita) o Risultati (conformita), Fonti
  esporta_csv_curva(percorso, sim)                     giorni, log Lm, log LAB (tutti i punti della curva)
Stessi argomenti di ermchek.report.pdf.crea_pdf. Si scrive solo nel percorso dato.
"""
import csv
import math
from datetime import date

import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import ermchek
from ermchek import lingua, testi
from ermchek.lingua import _
from ermchek.report.pdf import FONTI_STATISTICA, LIMITI, TIPI, VALIDAZIONE, _fonti_fssp, _riga_criterio

GRASSETTO = Font(bold=True)
TITOLO = Font(bold=True, size=14)
FONDO = PatternFill("solid", fgColor="EEF1F5")


def _intestazione(ws, riga, valori):
    for j, v in enumerate(valori, 1):
        c = ws.cell(row=riga, column=j, value=v)
        c.font, c.fill = GRASSETTO, FONDO
    return riga + 1


def _righe(ws, riga, righe):
    for r in righe:
        for j, v in enumerate(r, 1):
            if isinstance(v, (float, np.floating)):
                v = float(v) if math.isfinite(v) else None
            ws.cell(row=riga, column=j, value=v)
        riga += 1
    return riga


def _larghezze(ws, larghezze):
    for j, w in enumerate(larghezze, 1):
        ws.column_dimensions[get_column_letter(j)].width = w


def _riepilogo(ws, titolo, righe):
    ws.title = _("Riepilogo")
    ws["A1"] = titolo
    ws["A1"].font = TITOLO
    ws["A2"] = _("Report del {d}", d=date.today().isoformat()) + f", ErmChek {ermchek.__version__}"
    r = _intestazione(ws, 4, [_("Grandezza"), _("Valore"), _("Unità")])
    _righe(ws, r, righe)
    _larghezze(ws, [46, 18, 16])


def _ingressi(wb, ingressi, info_fasi, fasi_obj):
    ws = wb.create_sheet(_("Ingressi"))
    r = _intestazione(ws, 1, [_("Dato"), _("Valore")])
    r = _righe(ws, r, [[str(a), str(b)] for a, b in list(ingressi.get("contesto") or []) + list(ingressi.get("righe") or [])])
    if info_fasi:
        nitrito = fasi_obj is not None and len(fasi_obj) == len(info_fasi)
        testa = [_("Fase"), _("Durata (h)"), _("Temperatura (°C)"), "pH", "aw", _("Sale nella fase acquosa (%)")]
        r = _intestazione(ws, r + 1, testa + ([_("Nitrito (mg/kg)")] if nitrito else []))
        for i, f in enumerate(info_fasi):
            riga = [i + 1, f["ore"], f["temperatura"], f["ph"], f["aw"], f["sale_fase_acquosa"]]
            r = _righe(ws, r, [riga + ([fasi_obj[i].nitrito] if nitrito else [])])
    _larghezze(ws, [34, 30, 18, 10, 10, 26, 16])


def _curva(wb, sim, mc=None):
    ws = wb.create_sheet(_("Curva"))
    t = np.asarray(sim["tempi_giorni"])
    idx = sorted(set(range(0, len(t), 60)) | {len(t) - 1}) if len(t) > 2000 else range(len(t))   # un punto all'ora
    testa = [_("Giorni"), _("log Lm (ufc/g)")]
    lab = sim.get("log_lab") is not None
    if lab:
        testa.append(_("log LAB (ufc/g)"))
    if mc is not None:
        testa += [_("log Lm, 5° percentile"), _("log Lm, mediana"), _("log Lm, 95° percentile")]
        tm = np.asarray(mc["sim"]["tempi_giorni"])
    r = _intestazione(ws, 1, testa)
    for i in idx:
        riga = [t[i], sim["log_lm"][0][i]] + ([sim["log_lab"][0][i]] if lab else [])
        if mc is not None:
            riga += [float(np.interp(t[i], tm, mc[k])) for k in ("curva_p5", "curva_p50", "curva_p95")]
        r = _righe(ws, r, [riga])
    _larghezze(ws, [12, 18, 18, 22, 18, 22])


def _fonti(wb, fonti, extra=()):
    ws = wb.create_sheet(_("Fonti"))
    r = _intestazione(ws, 1, [_("Fonti")])
    r = _righe(ws, r, [[f] for f in fonti])
    for testo in extra:
        r = _righe(ws, r + 1, [[testo]])
    _larghezze(ws, [140])
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")


def esporta_excel(percorso, tipo, risultato, ingressi):
    """Scrive il file .xlsx in `percorso` e lo restituisce."""
    if tipo not in TIPI:
        raise ValueError("TIPO_REPORT_SCONOSCIUTO")
    ingressi = ingressi or {}
    wb = Workbook()
    titolo = ingressi.get("titolo") or "ErmChek"
    if tipo == "retro":
        ris = risultato
        p, peg, mc = ris["principale"], ris["peggiore"], ris["monte_carlo"]
        righe = [[_("Listeria misurata"), ris["osservato_ufc_g"], _("ufc/g")],
                 [_("Giorno dell'analisi"), ris["giorni"], _("giorni")],
                 [_("Stima all'origine (N0)"), p["ufc_g"], _("ufc/g")],
                 [_("Stima all'origine in 25 g"), p["ufc_25g"], _("ufc")],
                 [_("Stima all'origine in un pezzo"), p["ufc_pezzo"], _("ufc")]]
        if mc:
            righe += [[_("Intervallo al 90 %, da"), 10 ** mc["log_n0_p5"], _("ufc/g")],
                      [_("Intervallo al 90 %, a"), 10 ** mc["log_n0_p95"], _("ufc/g")]]
        righe += [[_("Probabilità di non trovarla in 25 g al giorno 0"), ris["p_non_rilevata_25g"], ""],
                  [_("Caso peggiore senza batteri lattici"), peg["ufc_g"], _("ufc/g")],
                  [_("Caso peggiore, in un pezzo"), peg["ufc_pezzo"], _("ufc")]]
        _riepilogo(wb.active, titolo, righe)
        _ingressi(wb, ingressi, ris["curva"]["fasi"], ingressi.get("fasi") or ris.get("fasi"))
        _curva(wb, ris["curva"])
        ws = wb.create_sheet(_("Scenari"))
        r = _intestazione(ws, 1, [_("Batteri lattici"), _("Fase di latenza (lag)"), _("log N0"), _("ufc/g"),
                                  _("ufc in 25 g"), _("ufc per pezzo"), _("Crescita (log)")])
        _righe(ws, r, [[_("sì") if s["con_lab"] else _("no"), _("fisiologica") if s["lag"] else _("nessuna"),
                        s["log_n0"], s["ufc_g"], s["ufc_25g"], s["ufc_pezzo"], s["delta_log"]] for s in ris["scenari"]])
        _larghezze(ws, [16, 22, 12, 14, 14, 16, 16])
        avvisi = [testi.avviso(a) for a in ris["avvisi"]]
        _fonti(wb, _fonti_fssp(ris["curva"].get("modello", "fssp"), p["con_lab"]),
               list(dict.fromkeys(avvisi)) + [_(VALIDAZIONE), _(LIMITI)])
    elif tipo == "crescita":
        sim, rias, mc = risultato["sim"], risultato["riassunto"], risultato.get("mc")
        righe = [[_("Listeria all'inizio"), 10 ** rias["log_iniziale"], _("ufc/g")],
                 [_("Listeria alla fine"), rias["ufc_g_finale"], _("ufc/g")],
                 [_("Potenziale di crescita δ (log)"), rias["delta"], "log"],
                 [_("Giorni per arrivare a 100 ufc/g"), rias["giorni_al_limite"], _("giorni")],
                 [_("Batteri lattici alla fine"),
                  10 ** rias["log_lab_finale"] if rias["log_lab_finale"] is not None else None, _("ufc/g")]]
        if mc:
            righe += [[_("Fine, 5° percentile"), 10 ** mc["log_finale_p5"], _("ufc/g")],
                      [_("Fine, mediana"), 10 ** mc["log_finale_p50"], _("ufc/g")],
                      [_("Fine, 95° percentile"), 10 ** mc["log_finale_p95"], _("ufc/g")],
                      [_("Probabilità sopra 100 ufc/g"), mc["p_sopra_limite"], ""]]
        _riepilogo(wb.active, titolo, righe)
        _ingressi(wb, ingressi, sim["fasi"], ingressi.get("fasi"))
        _curva(wb, sim, mc)
        _fonti(wb, _fonti_fssp(sim.get("modello", "fssp"), sim.get("log_lab") is not None),
               list(dict.fromkeys(testi.avviso(a) for a in sim["avvisi"])) + [_(VALIDAZIONE), _(LIMITI)])
    else:
        es, it, g = risultato["esito"], risultato["interpretazione"], risultato["griglia"]
        mle, mix, prev = risultato["mle"], risultato["miscela"], risultato.get("prevalenza")
        righe = [[_("Esito"), _(testi.ESITI[es["esito"]]), ""],
                 [_("Motivo"), _(testi.MOTIVI.get(es["motivo"], es["motivo"])), ""],
                 [_("Riga del criterio"), es.get("riga"), ""],
                 [_("Unità oltre il limite"), es.get("unita_oltre_limite"), ""],
                 [_("Unità analizzate"), es.get("n_analizzato"), ""],
                 [_("Interpretazione"), _(testi.INTERPRETAZIONI[it["codice"]]), ""],
                 [_("p del rapporto di verosimiglianza"), it["p_valore"], ""]]
        _riepilogo(wb.active, titolo, righe)
        _ingressi(wb, ingressi, None, None)
        ws = wb.create_sheet(_("Risultati"))
        r = _intestazione(ws, 1, [_("σ fra le unità (log)"), _("Probabilità massima"), _("μ migliore (log ufc/g)")])
        r = _righe(ws, r, [[s, pm, mu] for s, pm, mu in zip(g["sigma"], g["p_max"], g["mu_ottimale"])])
        r = _intestazione(ws, r + 1, [_("Stima"), _("Valore"), ""])
        stime = [[_("Log-normale: media (log ufc/g)"), mle["mu"]], [_("Log-normale: σ (log)"), mle["sigma"]],
                 [_("Log-normale: log-verosimiglianza"), mle["log_verosimiglianza"]],
                 [_("Miscela: frazione non contaminata"), mix["pi"]], [_("Miscela: media (log ufc/g)"), mix["mu"]],
                 [_("Miscela: σ (log)"), mix["sigma"]], [_("Miscela: log-verosimiglianza"), mix["log_verosimiglianza"]],
                 ["AIC " + _("log-normale"), it["aic_lognormale"]], ["AIC " + _("miscela"), it["aic_miscela"]],
                 [_("Rapporto di verosimiglianza"), it["lr"]], [_("p del rapporto di verosimiglianza"), it["p_valore"]]]
        if prev:
            stime += [[_("Prevalenza"), prev["stima"]], [_("Prevalenza, limite inferiore"), prev["inferiore"]],
                      [_("Prevalenza, limite superiore"), prev["superiore"]], [_("Confidenza"), prev["conf"]]]
        _righe(ws, r, stime)
        _larghezze(ws, [40, 20, 22])
        riga = _riga_criterio(es["riga"]) if es.get("riga") else None
        _fonti(wb, ([riga["riferimento"]] if riga else []) + FONTI_STATISTICA, [_(LIMITI)])
    wb.save(str(percorso))
    return percorso


def esporta_csv_curva(percorso, sim):
    """CSV della curva: giorni, log Lm, log LAB (vuoto se senza LAB). Con l'italiano ';' e la virgola decimale
    (si apre bene in Excel italiano), con l'inglese ',' e il punto."""
    it = lingua.attuale() == "it"
    fmt = (lambda v: "" if v is None else repr(float(v)).replace(".", ",")) if it else \
        (lambda v: "" if v is None else repr(float(v)))
    lab = sim.get("log_lab")
    with open(percorso, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";" if it else ",")
        w.writerow([_("giorni"), _("log Lm (ufc/g)"), _("log LAB (ufc/g)")])
        for i, t in enumerate(sim["tempi_giorni"]):
            w.writerow([fmt(t), fmt(sim["log_lm"][0][i]), fmt(lab[0][i] if lab is not None else None)])
    return percorso
