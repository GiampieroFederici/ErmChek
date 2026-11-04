"""Modulo B: crescita di Listeria nel tempo (ermchek.core.crescita), con le stesse fasi del modulo C.

Risultato: una risposta grande (finale contro 100 ufc/g, potenziale di crescita δ contro 0,5 log), il grafico,
i percentili del Monte Carlo e P(> 100 ufc/g), poi il salvataggio (PDF, Excel, CSV della curva).
"""
from pathlib import Path

from PySide6.QtWidgets import QLineEdit, QPushButton

from ermchek import testi
from ermchek.core import crescita
from ermchek.gui.base import (CampoNonValido, Flusso, Guidata, cifre2, etichetta, grafico, numero, pannello, percento,
                              risposta, riquadro, salva_file, tabella)
from ermchek.gui.condizioni import (MAX_UFC, TIPI, EditorFasi, PannelloLab, PannelloOpzioni, blocco, menu_esempi,
                                    menu_tipo, preset)
from ermchek.gui.glossario import termine
from ermchek.gui.modulo_c import per_grammo, testo_conversione, unita_lm
from ermchek.lingua import N_, _

LIMITE = 100.0     # ufc/g, criterio 1.2 (Reg. CE 2073/2005)
SOGLIA_DELTA = 0.5  # log, potenziale di crescita (guida EURL)
SCENARI = [(N_("1 cellula in 25 g"), 1, "25g"), (N_("1 ufc/g"), 1, "g"), (N_("10 ufc/g"), 10, "g")]


class ModuloB(Guidata):
    titolo = N_("B. Crescita nel tempo")
    nomi_passi = (N_("Prodotto e Listeria iniziale"), N_("Condizioni per fasi"), N_("Batteri lattici"), N_("Opzioni"),
                  N_("Risultato"))

    def __init__(self, contesto, parent=None):
        super().__init__(contesto, parent)
        self._prodotto(self.corpi[0])
        c = self.corpi[1]
        c.addWidget(etichetta(_("Dal giorno 0 alla fine della shelf-life, in ordine. Una fase = condizioni costanti.")))
        c.addWidget(etichetta(_("Porta il mouse sopra un campo per sapere che cosa significa."), "nota"))
        self.avviso_una_fase = riquadro(_("Un salume fermentato con una sola temperatura?"), _(
            "Di solito passa per più fasi (asciugatura, stagionatura). Con una fase sola la previsione può essere "
            "lontana dal vero: aggiungi le fasi o importa il data logger."), "avviso")
        c.addWidget(self.avviso_una_fase)
        self.editor = EditorFasi()
        c.addWidget(self.editor)
        self.lab = PannelloLab()
        self.corpi[2].addWidget(self.lab)
        self.opzioni = PannelloOpzioni(retro=False)
        self.corpi[3].addWidget(self.opzioni)
        self.corpi[3].addWidget(etichetta(_("Con Baranyi i batteri lattici non si usano."), "nota"))
        self.editor.cambiato.connect(self._controllo_fasi)
        self.tipo.currentIndexChanged.connect(self._controllo_fasi)
        self._controllo_fasi()

    def _prodotto(self, c):
        p, s = pannello(_("Vuoi partire da un esempio?"))
        self.esempio = menu_esempi("esempio")
        s.addWidget(blocco(_("Esempio: sostituisci con i tuoi dati"), self.esempio, _("facoltativo"),
                           self.esempio.toolTip()))
        self.nota_esempio = etichetta("", "nota")
        s.addWidget(self.nota_esempio)
        self.esempio.currentIndexChanged.connect(self._carica_esempio)
        c.addWidget(p)
        p, s = pannello(_("Il prodotto"))
        self.nome = QLineEdit(objectName="nome_prodotto")
        self.nome.setPlaceholderText(_("per esempio Salame, lotto 123"))
        s.addWidget(blocco(_("Nome del prodotto o del lotto"), self.nome, _("facoltativo, va nel report"),
                           _("Il nome che compare in alto nel report.")))
        self.tipo = menu_tipo("tipo_prodotto")
        s.addWidget(blocco(_("Tipo di prodotto"), self.tipo, _("obbligatorio"),
                           _("Serve per gli avvisi (per esempio: salume fermentato con una sola fase).")))
        c.addWidget(p)
        p, s = pannello(_("Listeria al giorno 0"))
        s.addWidget(etichetta(_("Una conta misurata oppure uno scenario: quanta Listeria c'è all'inizio?")))
        self.n0 = unita_lm("n0", _("Listeria monocytogenes al giorno 0"), "1")
        self.conversione = etichetta("", "conversione")
        self.n0.cambiato.connect(lambda: self.conversione.setText(testo_conversione(self.n0)))
        s.addWidget(self.n0)
        s.addWidget(self.conversione)
        f = Flusso()
        for nome, valore, unita in SCENARI:
            b = QPushButton(_("Scenario: {s}", s=_(nome)), objectName="piccolo")
            b.clicked.connect(lambda _x=False, v=valore, u=unita: (self.n0.imposta(v), self.n0.scegli_unita(u)))
            f.addWidget(b)
        s.addLayout(f)
        c.addWidget(p)

    def _carica_esempio(self, *_x):
        p = preset(self.esempio.currentData())
        if p is None:
            self.nota_esempio.setText("")
            return
        self.nota_esempio.setText(_("Esempio caricato in tutti i passi. Sostituisci i valori con i tuoi dati.")
                                  + (" " + _(p["nota"]) if p["nota"] else ""))
        self.tipo.setCurrentIndex([c for c, _t in TIPI].index(p["tipo"]))
        self.n0.imposta(p["n0"])
        self.n0.scegli_unita("g")
        self.editor.carica(p["fasi"])
        self.lab.carica(p)
        self.nome.setText("")

    def _controllo_fasi(self, *_x):
        self.avviso_una_fase.setVisible(self.tipo.currentData() == "fermentato" and len(self.editor.schede) == 1
                                        and not self.editor.punti)

    def controlla(self, i):
        try:
            if i == 0:
                self.n0.valore()
                g = per_grammo(self.n0)
                if g is None or g >= MAX_UFC:
                    self.n0.segnala(_("Scrivi un numero più grande di 0 e sotto 300.000.000 ufc/g."))
            elif i == 1:
                self.editor.fasi()
            elif i == 2:
                self.lab.valore()
            elif i == 3:
                self.opzioni.valori()
        except CampoNonValido:
            return self.errore_passo(_("Controlla i campi segnati in rosso."))
        self.avviso_barra("", "")
        return True

    def prepara(self):
        fasi = self.editor.fasi()
        o = self.opzioni.valori()
        lab0 = self.lab.valore() if o["modello"] == "fssp" else None
        n0 = per_grammo(self.n0)
        es = preset(self.esempio.currentData())
        self.dati_calcolo = {"nome": self.nome.text().strip(), "tipo": self.tipo.currentText(), "n0": n0,
                             "lab0": lab0, "starter": self.lab.starter_si.isChecked(), "opzioni": o,
                             "nitrati": self.editor.nitrati(), "file_csv": self.editor.file_csv,
                             "nota": _(es["nota"]) if es and es["nota"] else ""}

        def calcolo():
            opz = {"modello": o["modello"], "lag": o["lag"]}
            sim = crescita.simula(fasi, n0, lab0=lab0, **opz)
            mc = crescita.monte_carlo(fasi, n0, log_n0_sd=o["sd_n0"], lab0=lab0, sd_temperatura=o["sd_t"],
                                      cv_mu=o["cv_mu"], n=o["n_mc"], seed=o["seme"], limite_ufc_g=LIMITE, **opz)
            return {"sim": sim, "riassunto": crescita.riassunto(sim, limite_ufc_g=LIMITE), "mc": mc, "fasi": fasi}
        return calcolo

    def mostra(self, ris):
        u, r, sim, mc = self.uscita, ris["riassunto"], ris["sim"], ris["mc"]
        giorni = float(sim["tempi_giorni"][-1])
        sopra = r["ufc_g_finale"] > LIMITE
        cresce = r["delta"] > SOGLIA_DELTA
        righe = [_("Limite di legge: 100 ufc/g. {esito}", esito=_("Lo supera.") if sopra else _("Non lo supera.")),
                 _("Crescita potenziale (δ): {d} log (soglia 0,5 log).", d=numero(r["delta"], 2))]
        if r["giorni_al_limite"] is not None:
            righe.append(_("Arriva a 100 ufc/g dopo circa {g} giorni.", g=numero(r["giorni_al_limite"], 1)))
        elif not sopra:
            righe.append(_("Non arriva a 100 ufc/g in questo periodo."))
        if sopra:
            livello, spiega = "rosso", _("Rosso: alla fine Listeria supera 100 ufc/g.")
        elif cresce:
            livello, spiega = "ambra", _("Giallo: resta sotto 100 ufc/g, ma cresce più di 0,5 log: il prodotto "
                                         "favorisce la crescita.")
        else:
            livello, spiega = "verde", _("Verde: resta sotto 100 ufc/g e cresce al massimo 0,5 log.")
        u.addWidget(risposta(livello, _("Al giorno {g}: circa {x} ufc/g", g=numero(giorni, 1),
                                        x=cifre2(r["ufc_g_finale"])), righe, spiega))
        u.addWidget(etichetta((_("Listeria può crescere in almeno una fase.") if sim["crescita_possibile"]
                               else _("Listeria non può crescere in nessuna fase.")) + " "
                              + _("Partenza: {x} ufc/g.", x=cifre2(10 ** r["log_iniziale"])), "nota"))
        u.addWidget(etichetta(_("La curva nel tempo"), "sottotitolo"))
        u.addWidget(grafico("fig_crescita", sim, mc, LIMITE))
        u.addWidget(etichetta(_("Variabilità (Monte Carlo, {n} simulazioni)", n=numero(mc["n"], 0)), "sottotitolo"))
        u.addWidget(etichetta(_("Su 100 pezzi simili, quanta Listeria alla fine:"), ""))
        u.addWidget(tabella([_("Percentile"), _("Listeria alla fine (ufc/g)")],
                            [[_("5° (pochi pezzi sotto)"), cifre2(10 ** mc["log_finale_p5"])],
                             [_("50° (il valore di mezzo)"), cifre2(10 ** mc["log_finale_p50"])],
                             [_("95° (pochi pezzi sopra)"), cifre2(10 ** mc["log_finale_p95"])]],
                            [termine("mc"), ""]))
        if mc["log_finale_p95"] - mc["log_finale_p5"] < 1e-9:
            u.addWidget(etichetta(_("Le variabilità sono 0 (passo Opzioni): i tre percentili coincidono."), "nota"))
        u.addWidget(etichetta(_("Probabilità di superare 100 ufc/g alla fine: {p}.", p=percento(mc["p_sopra_limite"])),
                              "etichetta_campo"))
        avvisi = list(dict.fromkeys(testi.avviso(a) for a in sim["avvisi"]))   # stessa frase una volta sola
        if avvisi:
            u.addWidget(etichetta(_("Da sapere"), "sottotitolo"))
            for a in avvisi:
                u.addWidget(riquadro("", a, "avviso"))
        u.addWidget(etichetta(_("Salva i risultati"), "sottotitolo"))
        f = Flusso()
        for testo, funzione in [(_("Salva il PDF"), self.salva_pdf), *self.altri_salvataggi()]:
            b = QPushButton(testo, objectName="secondario")
            b.clicked.connect(funzione)
            f.addWidget(b)
        u.addLayout(f)

    # ---------------- report ----------------
    def altri_salvataggi(self):
        return [(_("Salva Excel"), self.salva_excel), (_("Salva la curva (CSV)"), self.salva_csv)]

    def ingressi(self):
        d, o = self.dati_calcolo, self.dati_calcolo["opzioni"]
        righe = [(_("Listeria monocytogenes al giorno 0"), _("{x} ufc/g", x=cifre2(d["n0"]))),
                 (_("Batteri lattici al giorno 0"), _("{x} ufc/g", x=numero(d["lab0"])) if d["lab0"] else _("non usati")),
                 (_("Modello"), "FSSP" if o["modello"] == "fssp" else "Baranyi & Roberts"),
                 (_("Fase di adattamento (lag)"), _("sì") if o["lag"] else _("no")),
                 (_("Variabilità di Listeria all'inizio (sd)"), f"{numero(o['sd_n0'])} log10"),
                 (_("Variabilità della temperatura (sd)"), f"{numero(o['sd_t'])} °C"),
                 (_("Incertezza di μmax (CV)"), numero(o["cv_mu"]) if o["cv_mu"] else _("spenta")),
                 (_("Simulazioni Monte Carlo (n)"), _("{n} (seed {s})", n=numero(o["n_mc"], 0), s=o["seme"]))]
        contesto = [(_("Tipo di prodotto"), d["tipo"]),
                    (_("Starter"), _("sì") if d["starter"] else _("no, fermentazione spontanea"))]
        if d["nitrati"]:
            contesto.append((_("Nitrato (solo informativo)"), "; ".join(
                _("fase {n}: {x} mg/kg", n=n, x=numero(x)) for n, x in d["nitrati"])))
        if d["file_csv"]:
            contesto.append((_("Temperature dal data logger"), Path(d["file_csv"]).name))
        if d["nota"]:
            contesto.append((_("Esempio"), d["nota"]))
        return {"titolo": d["nome"] or _("Crescita di Listeria nel tempo"), "righe": righe, "contesto": contesto,
                "fasi": self.risultato["fasi"]}

    def _per_report(self):
        return {k: self.risultato[k] for k in ("sim", "riassunto", "mc")}

    def _salva(self, titolo, filtro, estensione, scrivi):
        esito = salva_file(self, titolo, filtro, estensione, "ErmChek_crescita" + estensione, scrivi)
        if esito:
            self.avviso_barra(*esito)

    def salva_pdf(self):
        if self.risultato is None:
            return

        def scrivi(percorso):
            from ermchek.report.pdf import crea_pdf
            crea_pdf(percorso, "crescita", self._per_report(), self.ingressi())
        self._salva(_("Salva il report PDF"), _("PDF (*.pdf)"), ".pdf", scrivi)

    def salva_excel(self):
        def scrivi(percorso):
            from ermchek.report.excel import esporta_excel
            esporta_excel(percorso, "crescita", self._per_report(), self.ingressi())
        self._salva(_("Salva il file Excel"), _("Excel (*.xlsx)"), ".xlsx", scrivi)

    def salva_csv(self):
        def scrivi(percorso):
            from ermchek.report.excel import esporta_csv_curva
            esporta_csv_curva(percorso, self.risultato["sim"])
        self._salva(_("Salva la curva"), _("CSV (*.csv)"), ".csv", scrivi)

    def stato(self):
        return dict(super().stato(), fasi=len(self.editor.schede), punti=(self.editor.punti, self.editor.file_csv))

    def ripristina(self, stato):
        self.editor.imposta_n(stato["fasi"])
        self.esempio.blockSignals(True)
        super().ripristina(stato)
        self.esempio.blockSignals(False)
        self.editor._usa_punti(*stato["punti"])
