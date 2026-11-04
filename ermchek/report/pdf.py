"""Report PDF (reportlab platypus): la risposta in alto, in un riquadro grande e colorato, poi sezioni brevi e ariose.

Il testo del report è nella lingua scelta (ermchek.lingua): italiano nel codice, inglese in ermchek/i18n/en_report.json.
I grafici sono sempre in inglese (ermchek.report.grafici). Si scrive solo nel percorso dato; nessuna rete.

  crea_pdf(percorso, tipo, risultato, ingressi)
    tipo       "retro" | "crescita" | "conformita"
    risultato  retro: il dict di retro(); crescita: {"sim", "riassunto", "mc" o None};
               conformita: {"esito", "interpretazione", "griglia", "mle", "miscela", "prevalenza" o None, "patogeno"}
    ingressi   {"titolo": str, "righe": [(etichetta, valore)], "contesto": [(etichetta, testo)], "fasi": [Fase] o None}
"""
import io
import math
from datetime import date
from xml.sax.saxutils import escape

import yaml
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

import ermchek
from ermchek import lingua, testi
from ermchek.core.conformita import SIGMA_MAX, SIGMA_MIN
from ermchek.core.fssp.validita import numero_it
from ermchek.lingua import N_, _
from ermchek.percorsi import risorsa
from ermchek.report import grafici

TIPI = ("retro", "crescita", "conformita")
MARGINE_X, MARGINE_ALTO, MARGINE_BASSO = 2.3 * cm, 1.8 * cm, 2.3 * cm
PAD = 6   # padding interno della cornice di platypus
LARGHEZZA = A4[0] - 2 * MARGINE_X - 2 * PAD
LIMITE_UFC_G = 100.0

INCHIOSTRO, GRIGIO_TESTO, LINEA = colors.HexColor("#1F2328"), colors.HexColor("#5A6270"), colors.HexColor("#D5D9E0")
INTESTAZIONE = colors.HexColor("#EEF1F5")
AMBRA = colors.HexColor("#C77C00")
# riquadro della risposta: (fondo tenue, barra laterale, colore dell'etichetta)
TINTE = {"verde": ("#E4F3E8", "#2E7D4F", "#1E5C38"), "ambra": ("#FFF2D3", "#C98A00", "#7A5200"),
         "rosso": ("#FBE4E1", "#B3261E", "#8C1D17"), "grigio": ("#F1F3F5", "#9AA1AB", "#4A515B")}

LIMITI = N_("ErmChek è uno strumento didattico e di supporto alle decisioni. Non sostituisce i challenge test, gli "
            "studi di durabilità (EURL Lm TGD v4, emendamento 1, 26/02/2026, DOI 10.5281/zenodo.18783767) né "
            "l'autorità competente. I modelli valgono solo dentro i loro campi di validità.")
VALIDAZIONE = N_("Il motore di crescita dà gli stessi risultati di FSSP.Models.dll 1.1.0.21167 (FSSP 4.0, DTU Food) "
                 "in 23 casi su 23 (tests/validation_fssp.md).")
FONTI_STATISTICA = [
    "Clopper CJ, Pearson ES (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. "
    "Biometrika 26(4):404-413. doi:10.1093/biomet/26.4.404",
    "Self SG, Liang KY (1987). Asymptotic properties of maximum likelihood estimators and likelihood ratio tests "
    "under nonstandard conditions. J Am Stat Assoc 82(398):605-610. doi:10.1080/01621459.1987.10478472",
]


# ---------------- caratteri ----------------
def _registra_caratteri():
    """Atkinson Hyperlegible (assets/fonts, licenza OFL) se c'è, altrimenti Helvetica. DejaVu Sans (da matplotlib)
    solo per i simboli che mancano ad Atkinson, come σ e δ."""
    simboli = None
    try:
        import matplotlib
        from pathlib import Path
        p = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
        if p.is_file():
            pdfmetrics.registerFont(TTFont("ErmSimboli", str(p)))
            simboli = "ErmSimboli"
    except Exception:   # carattere di riserva: il report resta leggibile anche senza
        simboli = None
    nomi = {"": "Regular", "-B": "Bold", "-I": "Italic", "-BI": "BoldItalic"}
    try:
        for suff, nome in nomi.items():
            pdfmetrics.registerFont(TTFont("Erm" + suff, str(risorsa("assets", "fonts", f"AtkinsonHyperlegible-{nome}.ttf"))))
        pdfmetrics.registerFontFamily("Erm", normal="Erm", bold="Erm-B", italic="Erm-I", boldItalic="Erm-BI")
        return "Erm", "Erm-B", simboli
    except Exception:
        return "Helvetica", "Helvetica-Bold", simboli


FONT, FONT_B, FONT_SIMBOLI = _registra_caratteri()


def _simboli(testo):
    if FONT_SIMBOLI:
        for c in "σδ":
            testo = testo.replace(c, f'<font name="{FONT_SIMBOLI}">{c}</font>')
    return testo


def _stile(nome, size, leading=None, font=None, colore=INCHIOSTRO, **altro):
    return ParagraphStyle(nome, fontName=font or FONT, fontSize=size, leading=leading or round(size * 1.35, 1),
                          textColor=colore, **altro)


S = {
    "corpo": _stile("corpo", 11, spaceAfter=5),
    "piccolo": _stile("piccolo", 9.5, colore=GRIGIO_TESTO),
    "fonte": _stile("fonte", 9.5, leftIndent=0, spaceAfter=3, colore=colors.HexColor("#3A4048")),
    "titolo": _stile("titolo", 21, 26, FONT_B, spaceAfter=4),
    "sottotitolo": _stile("sottotitolo", 12.5, colore=GRIGIO_TESTO),
    "testata": _stile("testata", 9.5, colore=GRIGIO_TESTO, alignment=TA_RIGHT),
    "h2": _stile("h2", 14, 18, FONT_B, spaceBefore=20, spaceAfter=7, colore=colors.HexColor("#1D2B3A")),
    "cella": _stile("cella", 10, 13.5),
    "cella_b": _stile("cella_b", 10, 13.5, FONT_B),
    "cella_num": _stile("cella_num", 10, 13.5, alignment=TA_RIGHT),
    "cella_num_b": _stile("cella_num_b", 10, 13.5, FONT_B, alignment=TA_RIGHT),
    "intest": _stile("intest", 9.5, 12.5, FONT_B, colore=colors.HexColor("#33404F")),
    "intest_num": _stile("intest_num", 9.5, 12.5, FONT_B, colore=colors.HexColor("#33404F"), alignment=TA_RIGHT),
    "formula": _stile("formula", 11.5, 17, leftIndent=0.8 * cm, spaceBefore=3, spaceAfter=8),
}


def P(testo, stile="corpo"):
    return Paragraph(_simboli(testo), S[stile] if isinstance(stile, str) else stile)


def E(testo):
    """Testo che non viene da questo modulo (utente, core, testi.py): niente markup."""
    return escape(str(testo))


# ---------------- numeri ----------------
def sig(v, cifre=2, markup=True):
    """Numero con `cifre` cifre significative nella lingua scelta; molto piccoli o grandi in notazione scientifica
    (6,7 × 10^-5 come esponente vero nel PDF, come testo semplice altrove)."""
    if v is None or not math.isfinite(v):
        return "?"
    if v == 0:
        return "0"
    esp = math.floor(math.log10(abs(v)))
    if -3 <= esp < 6:
        decimali = cifre - 1 - esp   # negativo = arrotonda alle decine, centinaia...
        return numero_it(round(v, decimali), max(0, decimali))
    mantissa = round(v / 10 ** esp, cifre - 1)
    if abs(mantissa) >= 10:
        mantissa, esp = mantissa / 10, esp + 1
    m = numero_it(mantissa, cifre - 1)
    e = str(esp).replace("-", "−")
    return f"{m} × 10<super>{e}</super>" if markup else f"{m} × 10^{esp}"


def probabilita(p, markup=True):
    """Probabilità come percentuale; sotto 0,1 % in notazione scientifica, e "praticamente zero" sotto 10^-6."""
    if p >= 0.001:
        return _("{p} %", p=sig(100 * p, 2))
    if p <= 0.0:   # exp() troppo piccolo per il computer: non è una probabilità nulla
        return _("praticamente zero")
    testo = sig(p, 2, markup)
    return _("{p} (praticamente zero)", p=testo) if p < 1e-6 else testo


def valore_p(p):
    """Valore p: 3 decimali, 4 sotto 0,001, poi "< 0,0001"."""
    if p >= 0.001:
        return numero_it(p, 3)
    return numero_it(p, 4) if p >= 0.0001 else "< " + numero_it(0.0001, 4)


def _fisso(v, cifre=2):
    """Numero con decimali fissi (2,20 e non 2,2), per le formule."""
    return lingua.separatori(f"{v:.{cifre}f}").replace("-", "−")


def _giorni(g):
    return numero_it(g, 1)


def _durata(ore):
    return _("{n} h", n=numero_it(ore, 1)) if ore < 48 else _("{n} giorni", n=numero_it(ore / 24, 1))


# ---------------- blocchi ----------------
def _riquadro(tinta, righe, grande=True):
    """Riquadro a tutta larghezza: fondo tenue, barra laterale scura, testo scuro (mai solo colore)."""
    fondo, barra, _etichetta = TINTE[tinta]
    pad = 14 if grande else 10
    t = Table([["", righe]], colWidths=[0.28 * cm, LARGHEZZA - 0.28 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(barra)),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(fondo)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (1, 0), (1, 0), pad + 4), ("RIGHTPADDING", (1, 0), (1, 0), pad + 4),
        ("TOPPADDING", (1, 0), (1, 0), pad), ("BOTTOMPADDING", (1, 0), (1, 0), pad + 2),
        ("ROUNDEDCORNERS", [5, 5, 5, 5]),
    ]))
    return t


def _etichetta_box(testo, tinta):
    return P(testo.upper(), _stile("eb", 9.5, 13, FONT_B, colore=colors.HexColor(TINTE[tinta][2]), spaceAfter=6))


def _unita_unite(testo):
    """Il numero non va a capo lontano dalla sua unità (spazio unificatore prima di ufc e CFU)."""
    return testo.replace(" ufc", "\u00a0ufc").replace(" CFU", "\u00a0CFU")


def _grande(testo):
    return P(_unita_unite(testo), _stile("grande", 21, 27, FONT_B, spaceAfter=4))


def _riga_box(testo, size=13.5):
    return P(testo, _stile("rb", size, round(size * 1.38, 1), spaceAfter=2))


def _nota_box(testo):
    return P(testo, _stile("nb", 11, 15, spaceBefore=8, colore=colors.HexColor("#2B3038")))


def _tabella(righe, larghezze, num_col=(), intestazione=True, evidenzia=None):
    """Tabella con griglia chiara, intestazione tinta, numeri allineati a destra. righe: liste di testi (markup ok)."""
    dati = []
    for i, r in enumerate(righe):
        riga = []
        for j, c in enumerate(r):
            if i == 0 and intestazione:
                stile = "intest_num" if j in num_col else "intest"
            elif evidenzia is not None and i == evidenzia:
                stile = "cella_num_b" if j in num_col else "cella_b"
            else:
                stile = "cella_num" if j in num_col else "cella"
            riga.append(P(c, stile))
        dati.append(riga)
    t = Table(dati, colWidths=larghezze, hAlign="LEFT", repeatRows=1 if intestazione else 0)
    stile = [("GRID", (0, 0), (-1, -1), 0.5, LINEA), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
             ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7)]
    if intestazione:
        stile.append(("BACKGROUND", (0, 0), (-1, 0), INTESTAZIONE))
    if evidenzia is not None:
        stile.append(("BACKGROUND", (0, evidenzia), (-1, evidenzia), colors.HexColor("#F7F9FB")))
    t.setStyle(TableStyle(stile))
    return t


def _sezione(titolo, *blocchi, insieme=True):
    """Titolo + blocchi. Le sezioni brevi restano intere sulla stessa pagina (insieme=True); in quelle lunghe
    il titolo resta almeno con il primo blocco, mai da solo in fondo alla pagina."""
    blocchi = [b for b in blocchi if b is not None]
    if not blocchi:
        return []
    if insieme:
        return [KeepTogether([P(titolo, "h2"), *blocchi])]
    return [KeepTogether([P(titolo, "h2"), blocchi[0]])] + list(blocchi[1:])


def _grafico(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="white")
    buf.seek(0)
    larghezza, altezza = fig.get_size_inches()
    return Image(buf, width=LARGHEZZA, height=LARGHEZZA * altezza / larghezza)


def _elenco_avvisi(frasi):
    voci = []
    for f in dict.fromkeys(frasi):   # stessa frase una volta sola
        voci.append(ListItem(P(E(f)), value="•", bulletColor=AMBRA, bulletFontSize=11, leftIndent=16))
    return ListFlowable(voci, bulletType="bullet", start="•", bulletColor=AMBRA, bulletFontName=FONT,
                        bulletFontSize=11, leftIndent=16, bulletOffsetY=0)


def _fonti_insieme(fonti):
    """Titoletto "Fonti" ed elenco numerato, sulla stessa pagina."""
    return KeepTogether([P(_("Fonti"), "cella_b")] + [P(f"{i}. {E(f)}", "fonte") for i, f in enumerate(fonti, 1)])


def _fonti_fssp(modello="fssp", con_lab=True):
    with open(risorsa("params", "fssp.yaml"), encoding="utf-8") as fh:
        fonti = yaml.safe_load(fh).get("fonti", {})
    escluse = set()
    if modello != "baranyi":
        escluse.add("baranyi_1994")
    if not con_lab:
        escluse |= {"mejlholm_2007b", "mejlholm_2013", "mejlholm_2015", "gimenez_2004"}
    return [v for k, v in fonti.items() if k not in escluse]


# ---------------- ingressi ----------------
def _sezione_ingressi(ingressi, info_fasi, fasi_obj, intro):
    blocchi = [P(intro)]
    contesto = ingressi.get("contesto") or []
    righe = list(contesto) + list(ingressi.get("righe") or [])
    if righe:
        blocchi.append(_tabella([[E(a), E(b)] for a, b in righe], [6.2 * cm, LARGHEZZA - 6.2 * cm],
                                intestazione=False))
    uscita = _sezione(_("Cosa abbiamo inserito"), *blocchi)
    if info_fasi:
        uscita += [Spacer(1, 10), KeepTogether(_tabella_fasi(info_fasi, fasi_obj))]
    return uscita


def _tabella_fasi(info, fasi_obj, massimo=12):
    nitrito = fasi_obj is not None and len(fasi_obj) == len(info)
    testa = [_("Fase"), _("Durata"), _("Temperatura") + "<br/>(°C)", "pH", "aw",
             _("Sale nella fase acquosa") + "<br/>(%)"]
    if nitrito:
        testa.append(_("Nitrito") + "<br/>(mg/kg)")
    righe = [testa]
    for i, f in enumerate(info[:massimo]):
        r = [str(i + 1), _durata(f["ore"]), numero_it(f["temperatura"], 1), numero_it(f["ph"], 2),
             numero_it(f["aw"], 3), numero_it(f["sale_fase_acquosa"], 2)]
        if nitrito:
            r.append(numero_it(fasi_obj[i].nitrito, 1))
        righe.append(r)
    if nitrito:
        larg = [1.75 * cm, 2.45 * cm, 2.6 * cm, 1.6 * cm, 1.8 * cm, 3.6 * cm]
    else:
        larg = [1.75 * cm, 2.8 * cm, 3.0 * cm, 2.0 * cm, 2.2 * cm]
    larg.append(LARGHEZZA - sum(larg))
    blocchi = [_tabella(righe, larg, num_col=set(range(1, len(testa))))]
    if len(info) > massimo:
        blocchi.append(P(_("Più altre {n} fasi: l'elenco completo è nel file Excel.", n=len(info) - massimo), "piccolo"))
    return blocchi


# ---------------- back-calculation ----------------
def _retro(ris, ingressi):
    p, peg, mc = ris["principale"], ris["peggiore"], ris["monte_carlo"]
    peso = p["ufc_pezzo"] / p["ufc_g"] if p["ufc_pezzo"] is not None else None
    g = _giorni(ris["giorni"])
    rosso = p["ufc_25g"] >= 1.0
    tinta = "rosso" if rosso else "ambra"
    righe = [_etichetta_box(_("Quanta Listeria c'era all'inizio"), tinta),
             _grande(_("All'origine c'erano circa {n} ufc/g", n=sig(p["ufc_g"]))),
             _riga_box(_("cioè circa {n} ufc in 25 g", n=sig(p["ufc_25g"])))]
    if peso:
        righe.append(_riga_box(_("e circa {n} ufc in un pezzo da {peso} g", n=sig(p["ufc_pezzo"]),
                                 peso=numero_it(peso, 0))))
    pnr = probabilita(ris["p_non_rilevata_25g"])
    if rosso:
        righe.append(_nota_box(_("Con questa quantità un'analisi su 25 g al giorno 0 l'avrebbe quasi certamente "
                                 "trovata. Probabilità di non trovarla: {p}.", p=pnr)))
    else:
        righe.append(_nota_box(_("Con questa quantità un'analisi su 25 g al giorno 0 poteva non trovarla. "
                                 "Probabilità di non trovarla: {p}.", p=pnr)))
    righe.append(P(_("Calcolo con i batteri lattici (LAB) presenti e senza fase di latenza (lag).") if p["con_lab"]
                   else _("Calcolo senza batteri lattici e senza fase di latenza (lag)."),
                   _stile("pb", 9.5, colore=GRIGIO_TESTO, spaceBefore=6)))
    con_lag = next((s for s in ris["scenari"] if s["con_lab"] == p["con_lab"] and s["lag"]), None)
    if con_lag is not None:
        righe.append(P(_("Perché lag 0: Listeria cresce da subito, senza fase di adattamento. È il caso più cauto ed è "
                         "il predefinito di FSSP. Con il lag fisiologico (RLT 4,5) all'origine sarebbero circa {y} ufc/g.",
                         y=sig(con_lag["ufc_g"])), _stile("pb", 9.5, colore=GRIGIO_TESTO, spaceBefore=2)))
    storia = [_riquadro(tinta, righe)]

    if ris.get("lab0") is not None:
        grigio = [_etichetta_box(_("Caso peggiore, senza batteri lattici"), "grigio"),
                  _riga_box(_("All'origine sarebbero bastate circa {n} ufc/g", n=sig(peg["ufc_g"])), 13)]
        if peg["ufc_pezzo"] is not None:
            grigio.append(_riga_box(_("cioè circa {n} ufc in un pezzo da {peso} g", n=sig(peg["ufc_pezzo"]),
                                      peso=numero_it(peso, 0)), 12))
        grigio.append(_nota_box(_("Senza batteri lattici Listeria cresce di più, quindi all'inizio ne bastava "
                                  "molto meno.")))
        if peg["ufc_pezzo"] is not None and peg["ufc_pezzo"] < 1:
            grigio.append(_nota_box(_("Vuol dire meno di una cellula per pezzo: non è possibile. Senza il freno dei "
                                      "batteri lattici il risultato non si spiega con Listeria già presente al "
                                      "giorno 0. Fa pensare a una contaminazione avvenuta dopo.")))
        elif peg["ufc_25g"] < 1:
            grigio.append(_nota_box(_("Vuol dire meno di una cellula in 25 g.")))
        storia += [Spacer(1, 12), _riquadro("grigio", grigio, grande=False)]

    if mc:   # l'intervallo fuori dal riquadro: nel riquadro solo il valore più probabile
        u = ris["u_misura_log"]
        frasi = [P(_("Il valore più probabile all'origine è {x} ufc/g.", x=sig(p["ufc_g"]))),
                 P(_("La conta di laboratorio ha un errore di circa ± {u} log: il valore vero può essere circa {f} volte "
                     "più alto o più basso di quello letto.", u=numero_it(u, 1), f=numero_it(10 ** u, 1))),
                 P(_("Per questo ErmChek ripete il calcolo {n} volte, ogni volta con una conta diversa entro "
                     "quell'errore.", n=numero_it(mc["n"], 0))),
                 P(_("In 9 calcoli su 10 all'origine c'erano fra {a} e {b} ufc/g.", a=sig(10 ** mc["log_n0_p5"]),
                     b=sig(10 ** mc["log_n0_p95"])))]
        if ris.get("monte_carlo_peggiore") and p["con_lab"]:
            mp = ris["monte_carlo_peggiore"]
            frasi.append(P(_("Senza batteri lattici (caso peggiore): fra {a} e {b} ufc/g.", a=sig(10 ** mp["log_n0_p5"]),
                             b=sig(10 ** mp["log_n0_p95"]))))
        storia += [Spacer(1, 10)] + _sezione(_("Intervallo"), *frasi)
    storia += _sezione_ingressi(ingressi, ris["curva"]["fasi"], ingressi.get("fasi") or ris.get("fasi"),
                                _("Questi sono i dati usati per il calcolo. Listeria è stata misurata al giorno {g}.",
                                  g=g))

    testo = [_("La linea blu parte dalla stima centrale al giorno 0 e arriva al valore misurato al giorno {g}.", g=g)]
    if mc:
        testo.append(_("La barra al giorno 0 è l'intervallo al 90 %."))
    if ris.get("lab0") is not None:
        testo.append(_("La linea grigia tratteggiata è il caso peggiore, senza batteri lattici."))
    storia += _sezione(_("Come cresce Listeria"), P(" ".join(testo)), Spacer(1, 4), _grafico(grafici.fig_retro(ris)))

    pezzo = peso is not None
    testa = [_("Batteri lattici"), _("Fase di latenza (lag)"), _("ufc/g"), _("ufc in 25 g")]
    if pezzo:
        testa.append(_("ufc per pezzo"))
    righe_s, evid = [testa], None
    for s in ris["scenari"]:
        r = [_("sì") if s["con_lab"] else _("no"), _("fisiologica") if s["lag"] else _("nessuna"),
             sig(s["ufc_g"]), sig(s["ufc_25g"])]
        if pezzo:
            r.append(sig(s["ufc_pezzo"]))
        if (s["con_lab"], s["lag"]) == (p["con_lab"], p["lag"]):
            evid = len(righe_s)
        righe_s.append(r)
    larg = [3.0 * cm, 4.0 * cm] + [(LARGHEZZA - 7.0 * cm) / (len(testa) - 2)] * (len(testa) - 2)
    storia += _sezione(_("Gli scenari"),
                       P(_("Lo stesso calcolo, con e senza batteri lattici, con e senza fase di latenza. La fase di "
                           "latenza (lag) è il tempo in cui Listeria si adatta prima di crescere.")),
                       P(_("Con la fase di latenza serve più Listeria all'inizio. La riga in grassetto è quella del "
                           "riquadro in alto.")),
                       Spacer(1, 4), _tabella(righe_s, larg, num_col={2, 3, 4}, evidenzia=evid))

    storia += _sezione(_("Avvisi"), _elenco_avvisi([testi.avviso(a) for a in ris["avvisi"]]))

    modello = ris["curva"].get("modello", "fssp")
    metodo = [P(_("Modello di crescita: FSSP per Listeria monocytogenes, con il freno dei batteri lattici (effetto "
                  "Jameson).") if p["con_lab"] else
                _("Modello di crescita: FSSP per Listeria monocytogenes.") if modello == "fssp" else
                _("Modello di crescita: Baranyi e Roberts, con i parametri di FSSP per Listeria monocytogenes.")),
              P(_("Il calcolo cerca la quantità iniziale che, con le stesse condizioni, porta al valore misurato. "
                  "Lontano dal massimo vale la formula:")),
              P("log N<sub>0</sub> = log N<sub>t</sub> − Δlog", "formula"),
              P(_("N<sub>t</sub> è il valore misurato al giorno {g}. Δlog è la crescita prevista dal modello. "
                  "Con i numeri di questo caso:", g=g)),
              P(_("log N<sub>0</sub> = {nt} − {d} = {n0}, quindi N<sub>0</sub> = {c} ufc/g",
                  nt=_fisso(ris["log_osservato"]), d=_fisso(p["delta_log"]),
                  n0=_fisso(ris["log_osservato"] - p["delta_log"]), c=sig(10 ** p["log_n0"], 3)), "formula")]
    if mc:
        metodo.append(P(_("L'intervallo viene da {n} simulazioni Monte Carlo con un'incertezza di misura di {u} log.",
                          n=numero_it(mc["n"], 0), u=numero_it(ris["u_misura_log"], 2))))
    metodo += [P(_(VALIDAZIONE)), Spacer(1, 4), _fonti_insieme(_fonti_fssp(modello, p["con_lab"]))]
    storia += _sezione(_("Metodo e fonti"), *metodo, insieme=False)
    return storia


# ---------------- crescita ----------------
def _crescita(ris, ingressi):
    sim, rias, mc = ris["sim"], ris["riassunto"], ris.get("mc")
    giorni = float(sim["tempi_giorni"][-1])
    finale = rias["ufc_g_finale"]
    tinta = "rosso" if finale > LIMITE_UFC_G else "ambra" if rias["delta"] > 0.5 else "verde"
    righe = [_etichetta_box(_("Quanta Listeria c'è alla fine"), tinta),
             _grande(_("Alla fine Listeria arriva a circa {n} ufc/g", n=sig(finale))),
             _riga_box(_("Parte da {a} ufc/g e cresce di {d} log in {g} giorni.", a=sig(10 ** rias["log_iniziale"]),
                         d=numero_it(rias["delta"], 2), g=_giorni(giorni)))]
    if rias["log_iniziale"] >= math.log10(LIMITE_UFC_G):
        righe.append(_riga_box(_("È già sopra 100 ufc/g all'inizio.")))
    elif rias["giorni_al_limite"] is not None:
        righe.append(_riga_box(_("Supera 100 ufc/g dopo circa {g} giorni.", g=_giorni(rias["giorni_al_limite"]))))
    else:
        righe.append(_riga_box(_("Non supera 100 ufc/g in questo periodo.")))
    if mc:
        righe.append(_riga_box(_("Probabilità di superare 100 ufc/g alla fine: {p}", p=probabilita(mc["p_sopra_limite"]))))
    righe.append(_nota_box({"rosso": _("Supera il limite di 100 ufc/g."),
                            "ambra": _("La crescita supera 0,5 log: secondo il modello il prodotto favorisce la "
                                       "crescita di Listeria."),
                            "verde": _("La crescita resta entro 0,5 log: secondo il modello il prodotto non favorisce "
                                       "la crescita di Listeria.")}[tinta]))
    storia = [_riquadro(tinta, righe)]

    fasi = ingressi.get("fasi")
    con_lab = sim.get("log_lab") is not None
    if con_lab and fasi:
        from ermchek.core.crescita import simula
        senza = simula(fasi, 10 ** rias["log_iniziale"], lab0=None, modello=sim.get("modello", "fssp"), lag=sim.get("lag", False))
        f_senza = float(10 ** senza["log_lm"][0][-1])
        storia += [Spacer(1, 12), _riquadro("grigio", [
            _etichetta_box(_("Caso peggiore, senza batteri lattici"), "grigio"),
            _riga_box(_("Alla fine Listeria arriverebbe a circa {n} ufc/g", n=sig(f_senza)), 13),
            _nota_box(_("I batteri lattici frenano Listeria. Senza di loro la crescita è più alta."))], grande=False)]

    if mc:
        storia += [Spacer(1, 10)] + _sezione(_("Intervallo"), P(_(
            "Il calcolo è stato ripetuto {n} volte facendo variare i dati incerti. In 9 calcoli su 10 alla fine Listeria "
            "sta fra {a} e {b} ufc/g.", n=numero_it(mc["n"], 0), a=sig(10 ** mc["log_finale_p5"]),
            b=sig(10 ** mc["log_finale_p95"]))))
    storia += _sezione_ingressi(ingressi, sim["fasi"], fasi, _("Questi sono i dati usati per il calcolo."))

    testo = [_("La linea blu è Listeria.")]
    if con_lab:
        testo.append(_("La linea verde tratteggiata sono i batteri lattici."))
    if mc:
        testo.append(_("La fascia azzurra contiene il 90 % delle simulazioni Monte Carlo."))
    testo.append(_("La linea rossa tratteggiata è il limite di 100 ufc/g."))
    storia += _sezione(_("Come cresce Listeria"), P(" ".join(testo)), Spacer(1, 4),
                       _grafico(grafici.fig_crescita(sim, mc, LIMITE_UFC_G)))

    tab = [[_("Grandezza"), _("Valore")],
           [_("Listeria all'inizio"), _("{n} ufc/g", n=sig(10 ** rias["log_iniziale"]))],
           [_("Listeria alla fine"), _("{n} ufc/g", n=sig(finale))],
           [_("Potenziale di crescita δ (log)"), numero_it(rias["delta"], 2)],
           [_("Giorni per arrivare a 100 ufc/g"),
            _giorni(rias["giorni_al_limite"]) if rias["giorni_al_limite"] is not None else _("non arriva")]]
    if rias["log_lab_finale"] is not None:
        tab.append([_("Batteri lattici alla fine"), _("{n} ufc/g", n=sig(10 ** rias["log_lab_finale"]))])
    if mc:
        tab += [[_("Fine, 5° percentile"), _("{n} ufc/g", n=sig(10 ** mc["log_finale_p5"]))],
                [_("Fine, mediana"), _("{n} ufc/g", n=sig(10 ** mc["log_finale_p50"]))],
                [_("Fine, 95° percentile"), _("{n} ufc/g", n=sig(10 ** mc["log_finale_p95"]))],
                [_("Probabilità sopra 100 ufc/g"), probabilita(mc["p_sopra_limite"])]]
    storia += _sezione(_("I numeri"),
                       P(_("Il potenziale di crescita (δ) è l'aumento massimo in log rispetto all'inizio.")),
                       Spacer(1, 4), _tabella(tab, [9.0 * cm, LARGHEZZA - 9.0 * cm], num_col={1}))

    storia += _sezione(_("Avvisi"), _elenco_avvisi([testi.avviso(a) for a in sim["avvisi"]]))

    modello = sim.get("modello", "fssp")
    metodo = [P(_("Modello di crescita: FSSP per Listeria monocytogenes, con il freno dei batteri lattici (effetto "
                  "Jameson).") if con_lab else
                _("Modello di crescita: FSSP per Listeria monocytogenes.") if modello == "fssp" else
                _("Modello di crescita: Baranyi e Roberts, con i parametri di FSSP per Listeria monocytogenes.")),
              P(_("A ogni fase la velocità di crescita si ricalcola con le condizioni di quella fase. Il potenziale "
                  "di crescita è:")),
              P("δ = log N<sub>max</sub> − log N<sub>0</sub> = {a} − {b} = {d}".format(
                  a=_fisso(rias["log_iniziale"] + rias["delta"]), b=_fisso(rias["log_iniziale"]),
                  d=_fisso(rias["delta"])), "formula")]
    if mc:
        metodo.append(P(_("L'intervallo viene da {n} simulazioni Monte Carlo.", n=numero_it(mc["n"], 0))))
    metodo += [P(_(VALIDAZIONE)), Spacer(1, 4), _fonti_insieme(_fonti_fssp(modello, con_lab))]
    storia += _sezione(_("Metodo e fonti"), *metodo, insieme=False)
    return storia


# ---------------- conformità ----------------
def _riga_criterio(id_riga):
    from ermchek.core.criteri import carica_criteri
    return next((r for r in carica_criteri()["criteri"] if r["id"] == id_riga), None)


def _conformita(ris, ingressi):
    es, interp, griglia = ris["esito"], ris["interpretazione"], ris["griglia"]
    tinta = {"CONFORME": "verde", "NON_CONFORME": "rosso"}.get(es["esito"], "ambra")
    riga = _riga_criterio(es["riga"]) if es.get("riga") else None
    righe = [_etichetta_box(_("Esito secondo il criterio di legge"), tinta),
             _grande(E(_(testi.ESITI[es["esito"]]))),
             _riga_box(E(_(testi.MOTIVI.get(es["motivo"], es["motivo"]))))]
    if riga:
        lim = riga["limite"]
        limite = (_("assenza in {m} g", m=numero_it(lim["massa_g"], 0)) if lim["tipo"] == "assenza"
                  else _("al massimo {v} ufc/g", v=numero_it(lim["valore"], 0)))
        righe.append(_riga_box(_("Criterio: riga {r}, {n} unità, c = {c}, {lim}.", r=E(riga["categoria"]),
                                 n=riga["n"], c=riga["c"], lim=limite), 12.5))
    if es.get("unita_oltre_limite") is not None:
        righe.append(_riga_box(_("Unità oltre il limite: {k} su {n}.", k=es["unita_oltre_limite"],
                                 n=es["n_analizzato"]), 12.5))
    righe.append(_nota_box(E(_(testi.INTERPRETAZIONI[interp["codice"]])) + " " +
                           _("Confronto fra i modelli con il rapporto di verosimiglianza: p = {p}.",
                             p=valore_p(interp["p_valore"]))))
    storia = [_riquadro(tinta, righe)]

    patogeno = "Salmonella" if ris.get("patogeno") == "salmonella" else "Listeria monocytogenes"
    storia += _sezione_ingressi(ingressi, None, None,
                                _("Questi sono i risultati delle unità analizzate per {pat}.", pat=patogeno))

    mle, mix = ris["mle"], ris["miscela"]
    stat = [P(_("Il modello log-normale descrive un lotto omogeneo. La concentrazione cambia da un'unità all'altra "
                "con una deviazione standard σ.")),
            P(_("Stima: media {mu} log ufc/g, σ = {s} log.", mu=_fisso(mle["mu"]), s=_fisso(mle["sigma"]))),
            P(_("Il modello a miscela ammette anche unità non contaminate. Stima: {pi} % delle unità non "
                "contaminate.", pi=numero_it(100 * mix["pi"], 0)))]
    if mle["sigma"] >= SIGMA_MAX - 1e-3 or mle["sigma"] <= SIGMA_MIN + 1e-3:
        stat.append(P(_("σ è al limite della stima ({s} log): con questi risultati non si può stimare bene.",
                        s=_fisso(mle["sigma"], 1))))
    prev = ris.get("prevalenza")
    if prev:
        stat.append(P(_("Prevalenza (quota di unità positive): {p} %, intervallo di confidenza al {c} % da {a} a "
                        "{b} %.", p=numero_it(100 * prev["stima"], 1), c=numero_it(100 * prev["conf"], 0),
                        a=numero_it(100 * prev["inferiore"], 1), b=numero_it(100 * prev["superiore"], 1))))
    storia += _sezione(_("Cosa dicono i risultati sul lotto"), *stat, insieme=False)

    tab = [[_("σ fra le unità (log)"), _("Probabilità massima"), _("μ migliore (log ufc/g)")]]
    for s_, pm, mu in zip(griglia["sigma"], griglia["p_max"], griglia["mu_ottimale"]):
        tab.append([numero_it(s_, 1), sig(pm, 2), numero_it(mu, 2).replace("-", "−") if math.isfinite(mu) else "?"])
    storia += _sezione(_("Quanto è probabile questo risultato"),
                       P(_("Per ogni σ il grafico mostra la probabilità più alta di ottenere proprio questi risultati. "
                           "Una probabilità molto bassa con σ piccola vuol dire che un lotto omogeneo li spiega male.")),
                       Spacer(1, 4), _grafico(grafici.fig_pattern_sigma(griglia)), Spacer(1, 8),
                       _tabella(tab, [LARGHEZZA / 3] * 3, num_col={0, 1, 2}))

    storia += _sezione(_("Avvisi"), _elenco_avvisi([
        _("Con poche unità il confronto fra i due modelli è solo indicativo (approssimazione asintotica)."),
        _("L'esito vale per i risultati inseriti e per il criterio scelto.")]))

    fonti = ([riga["riferimento"]] if riga else []) + FONTI_STATISTICA
    storia += _sezione(_("Metodo e fonti"),
                       P(_("Concentrazione fra le unità log-normale. Presenza o assenza nella porzione con il modello "
                           "di Poisson:")),
                       P("P(" + _("negativo") + ") = e<super>−m·c</super>", "formula"),
                       P(_("m è la massa analizzata (g), c la concentrazione (ufc/g). Il confronto fra modello "
                           "log-normale e miscela usa il rapporto di verosimiglianza con la distribuzione "
                           "chi-bar-quadro. La prevalenza usa l'intervallo esatto di Clopper-Pearson.")),
                       Spacer(1, 4), _fonti_insieme(fonti), insieme=False)
    return storia


# ---------------- pagina ----------------
class _Tela(rl_canvas.Canvas):
    """Canvas che conosce il numero totale di pagine (per "Pagina 1 di 3") e disegna il piè di pagina."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._pagine = []

    def showPage(self):
        self._pagine.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        totale = len(self._pagine)
        for stato in self._pagine:
            self.__dict__.update(stato)
            self._piede(totale)
            super().showPage()
        super().save()

    def _piede(self, totale):
        y = MARGINE_BASSO - 1.0 * cm
        self.setStrokeColor(LINEA)
        self.setLineWidth(0.5)
        self.line(MARGINE_X + PAD, y + 12, A4[0] - MARGINE_X - PAD, y + 12)
        self.setFont(FONT, 9)
        self.setFillColor(GRIGIO_TESTO)
        self.drawString(MARGINE_X + PAD, y, f"ErmChek {ermchek.__version__}")
        self.drawRightString(A4[0] - MARGINE_X - PAD, y, _("Pagina {n} di {tot}", n=self._pageNumber, tot=totale))


def _testata(titolo, sottotitolo):
    logo = risorsa("assets", "logo", "ErmChek_logo.png")
    oggi = date.today()
    data = oggi.strftime("%d/%m/%Y") if lingua.attuale() == "it" else oggi.isoformat()
    destra = [P(_("Report del {d}", d=data), "testata"), P(f"ErmChek {ermchek.__version__}", "testata")]
    sinistra = Image(str(logo), width=4.5 * cm, height=4.5 * cm * 724 / 2172) if logo.is_file() else P("ErmChek", "titolo")
    t = Table([[sinistra, destra]], colWidths=[LARGHEZZA * 0.5, LARGHEZZA * 0.5])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return [t, Spacer(1, 22), P(E(titolo), "titolo"), P(sottotitolo, "sottotitolo"), Spacer(1, 16)]


SOTTOTITOLI = {"retro": N_("Back-calculation di Listeria monocytogenes"),
               "crescita": N_("Crescita di Listeria monocytogenes nel tempo"),
               "conformita": N_("Conformità del lotto ai criteri microbiologici")}


def crea_pdf(percorso, tipo, risultato, ingressi):
    """Scrive il report PDF in `percorso` (A4, nella lingua scelta) e restituisce il percorso."""
    if tipo not in TIPI:
        raise ValueError("TIPO_REPORT_SCONOSCIUTO")
    ingressi = ingressi or {}
    titolo = ingressi.get("titolo") or _(SOTTOTITOLI[tipo])
    storia = _testata(titolo, _(SOTTOTITOLI[tipo]))
    storia += {"retro": _retro, "crescita": _crescita, "conformita": _conformita}[tipo](risultato, ingressi)
    storia += _sezione(_("Limiti"), P(_(LIMITI)))
    doc = SimpleDocTemplate(str(percorso), pagesize=A4, leftMargin=MARGINE_X, rightMargin=MARGINE_X,
                            topMargin=MARGINE_ALTO, bottomMargin=MARGINE_BASSO, title=titolo,
                            author=f"ErmChek {ermchek.__version__}", creator=f"ErmChek {ermchek.__version__}",
                            subject=_(SOTTOTITOLI[tipo]), lang=lingua.attuale())
    doc.build(storia, canvasmaker=_Tela)
    return percorso
