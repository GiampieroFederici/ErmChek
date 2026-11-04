"""Modulo C: quanta Listeria c'era all'origine (back-calculation, ermchek.core.retro).

Passi: prodotto e risultato, condizioni per fasi, batteri lattici, opzioni, risultato. Il risultato comincia con
UNA risposta grande (colore + testo esplicito), poi il caso peggiore senza LAB, il grafico, gli scenari, gli avvisi.
"""
from pathlib import Path

from PySide6.QtWidgets import QLineEdit, QPushButton

from ermchek import testi
from ermchek.core.retro import PORZIONE_G, retro
from ermchek.gui.base import (Apribile, Campo, CampoNonValido, Flusso, Guidata, cifre2, etichetta, fisso, grafico, incertezza_misura,
                              numero, pannello, peso_pezzo, percento, risposta, riquadro, salva_file, tabella)
from ermchek.gui.condizioni import (MAX_UFC, TIPI, EditorFasi, PannelloLab, PannelloOpzioni, blocco, menu_esempi,
                                    menu_tipo, preset)
from ermchek.gui.glossario import termine
from ermchek.lingua import N_, _

UNITA_OSSERVATO = [("g", N_("ufc/g")), ("25g", N_("ufc in 25 g"))]


def unita_lm(chiave, nome, esempio):
    """Campo per una quantità di Listeria con il menu dell'unità: ufc/g oppure ufc in 25 g."""
    return Campo(nome, aiuto=termine("ufc"), esempio=esempio, chiave=chiave,
                 unita_scelte=[(c, _(t)) for c, t in UNITA_OSSERVATO], nota=_("più di 0") + " · " + _("obbligatorio"))


def per_grammo(campo):
    """ufc/g da un campo con l'unità scelta (None se vuoto o non valido)."""
    v = campo.prova()
    if v is None or v <= 0:
        return None
    return v / PORZIONE_G if campo.unita_scelta() == "25g" else v


def testo_conversione(campo):
    v, g = campo.prova(), per_grammo(campo)
    if g is None:
        return ""
    if campo.unita_scelta() == "25g":
        return _("{x} ufc in 25 g = {y} ufc/g", x=numero(v), y=cifre2(g))
    return _("{x} ufc/g = {y} ufc in 25 g", x=numero(v), y=cifre2(g * PORZIONE_G))


class ModuloC(Guidata):
    titolo = N_("C. Quanta ce n'era all'origine")
    nomi_passi = (N_("Prodotto e risultato"), N_("Condizioni per fasi"), N_("Batteri lattici"), N_("Opzioni"),
                  N_("Risultato"))

    def __init__(self, contesto, parent=None):
        super().__init__(contesto, parent)
        self._prodotto(self.corpi[0])
        c = self.corpi[1]
        c.addWidget(etichetta(_("Dal giorno 0 al giorno dell'analisi, in ordine. Una fase = condizioni costanti.")))
        c.addWidget(etichetta(_("Porta il mouse sopra un campo per sapere che cosa significa."), "nota"))
        self.avviso_una_fase = riquadro(_("Un salume fermentato con una sola temperatura?"), _(
            "Di solito passa per più fasi (asciugatura, stagionatura). Con una fase sola la stima può essere lontana "
            "dal vero: aggiungi le fasi o importa il data logger."), "avviso")
        c.addWidget(self.avviso_una_fase)
        self.editor = EditorFasi()
        c.addWidget(self.editor)
        self.controllo_giorni = self.editor.verifica
        self.lab = PannelloLab()
        self.corpi[2].addWidget(self.lab)
        self.opzioni = PannelloOpzioni(retro=True)
        self.corpi[3].addWidget(self.opzioni)
        self.editor.cambiato.connect(self._controllo_fasi)
        self.giorno.cambiato.connect(self._controllo_fasi)
        self.tipo.currentIndexChanged.connect(self._controllo_fasi)
        self._controllo_fasi()

    def impostazioni_cambiate(self):
        self.opzioni.u.imposta(incertezza_misura())

    # ---------------- passo 1 ----------------
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
        p, s = pannello(_("Il risultato dell'analisi"))
        self.osservato = unita_lm("osservato", _("Listeria monocytogenes misurata"), "4.000")
        self.osservato.setToolTip(termine("ufc"))
        self.conversione = etichetta("", "conversione")
        self.osservato.cambiato.connect(lambda: self.conversione.setText(testo_conversione(self.osservato)))
        s.addWidget(self.osservato)
        s.addWidget(self.conversione)
        self.giorno = Campo(_("Giorno dell'analisi"), _("giorni dal giorno 0"), (0.01, 365), esempio="15",
                            aiuto=_("Quanti giorni dal giorno 0 (per esempio l'insacco) al prelievo del campione."),
                            chiave="giorno")
        s.addWidget(self.giorno)
        c.addWidget(p)
        c.addWidget(riquadro(_("Che cos'è il giorno 0?"), _(
            "È il momento in cui pensi che Listeria sia entrata nel prodotto, per esempio l'insacco. Il calcolo dice "
            "quanta ce n'era quel giorno."), "info"))

    def _carica_esempio(self, *_x):
        p = preset(self.esempio.currentData())
        if p is None:
            self.nota_esempio.setText("")
            return
        self.nota_esempio.setText(_("Esempio caricato in tutti i passi. Sostituisci i valori con i tuoi dati.")
                                  + (" " + _(p["nota"]) if p["nota"] else ""))
        self.tipo.setCurrentIndex([c for c, _t in TIPI].index(p["tipo"]))
        self.osservato.imposta(p["osservato"])
        self.osservato.scegli_unita(p["unita_oss"])
        self.giorno.imposta(p["giorno"])
        self.editor.carica(p["fasi"])
        self.lab.carica(p)
        self.nome.setText("")

    # ---------------- controlli ----------------
    def _controllo_fasi(self, *_x):
        self.avviso_una_fase.setVisible(self.tipo.currentData() == "fermentato" and len(self.editor.schede) == 1
                                        and not self.editor.punti)
        ore, giorno = self.editor.ore_totali(), self.giorno.prova()
        if ore is None or giorno is None:
            self.controllo_giorni.setText("")
        elif abs(ore / 24 - giorno) <= 0.01:
            self.controllo_giorni.setText(_("Le fasi arrivano al giorno dell'analisi ({g}): va bene.", g=numero(giorno)))
        else:
            self.controllo_giorni.setText(_("Le fasi durano {f} giorni, ma l'analisi è al giorno {g}.",
                                            f=numero(ore / 24), g=numero(giorno)))

    def controlla(self, i):
        try:
            if i == 0:
                v = self.osservato.valore()
                if v <= 0 or per_grammo(self.osservato) >= MAX_UFC:
                    self.osservato.segnala(_("Scrivi un numero più grande di 0 e sotto 300.000.000 ufc/g."))
                self.giorno.valore()
            elif i == 1:
                self.editor.fasi()
                ore, giorno = self.editor.ore_totali(), self.giorno.prova()
                if giorno is not None and abs(ore / 24 - giorno) > 0.01:
                    return self.errore_passo(_("Le fasi durano {f} giorni, ma l'analisi è al giorno {g}. Le fasi "
                                               "devono arrivare al giorno dell'analisi.", f=numero(ore / 24),
                                               g=numero(giorno)))
            elif i == 2:
                self.lab.valore()
            elif i == 3:
                self.opzioni.valori()
        except CampoNonValido:
            return self.errore_passo(_("Controlla i campi segnati in rosso."))
        self.avviso_barra("", "")
        return True

    # ---------------- calcolo ----------------
    def prepara(self):
        fasi = self.editor.fasi()
        o = self.opzioni.valori()
        lab0 = self.lab.valore()
        peso = peso_pezzo()
        osservato = per_grammo(self.osservato)
        self.dati_calcolo = {"nome": self.nome.text().strip(), "tipo": self.tipo.currentText(),
                             "osservato": self.osservato.valore(), "unita_oss": self.osservato.unita_scelta(),
                             "osservato_ufc_g": osservato, "giorno": self.giorno.valore(), "lab0": lab0,
                             "starter": self.lab.starter_si.isChecked(), "opzioni": o, "peso": peso,
                             "nitrati": self.editor.nitrati(), "file_csv": self.editor.file_csv,
                             "nota": _(preset(self.esempio.currentData())["nota"]) if self.esempio.currentData() and
                             preset(self.esempio.currentData())["nota"] else ""}
        return lambda: retro(fasi, osservato, lab0=lab0, modello=o["modello"], u_misura_log=o["u"],
                             sd_temperatura=o["sd_t"], cv_mu=o["cv_mu"], peso_pezzo_g=peso, n_mc=o["n_mc"],
                             seed=o["seme"])

    # ---------------- risultato ----------------
    def mostra(self, ris):
        u = self.uscita
        r, mc, peso = ris["principale"], ris["monte_carlo"], self.dati_calcolo["peso"]
        righe = [_("cioè circa {y} ufc in 25 g", y=cifre2(r["ufc_25g"]))]
        if r["ufc_pezzo"] is not None:
            righe.append(_("In un pezzo da {p} g: circa {z} ufc", p=numero(peso), z=cifre2(r["ufc_pezzo"])))
        if not r["cresce"]:
            livello, spiega = "ambra", _("Giallo: il modello non prevede crescita. All'origine c'era almeno quanto "
                                         "hai misurato.")
        elif r["ufc_25g"] >= 1:
            livello, spiega = "rosso", _("Rosso: all'origine c'era almeno 1 cellula attesa in 25 g. Un'analisi al "
                                         "giorno 0 l'avrebbe probabilmente trovata.")
        else:
            livello, spiega = "ambra", _("Giallo: all'origine meno di 1 cellula attesa in 25 g. Un'analisi al giorno 0 "
                                         "probabilmente non l'avrebbe trovata.")
        u.addWidget(risposta(livello, _("All'origine c'erano circa {x} ufc/g", x=cifre2(r["ufc_g"])), righe, spiega))
        if mc:
            u.addWidget(self._intervallo(ris))
        come = _("con i batteri lattici") if r["con_lab"] else _("senza batteri lattici")
        u.addWidget(etichetta(_("Stima {come}, senza fase di adattamento (lag), al giorno 0.", come=come)
                              + " " + _("Probabilità che un campione da 25 g fosse negativo al giorno 0: {p}.",
                                        p=percento(ris["p_non_rilevata_25g"])), "nota"))
        con_lag = next((s for s in ris["scenari"] if s["con_lab"] == r["con_lab"] and s["lag"]), None)
        if con_lag is not None:
            u.addWidget(etichetta(_("Perché lag 0: Listeria cresce da subito, senza fase di adattamento. È il caso più "
                                    "cauto ed è il predefinito di FSSP. Con il lag fisiologico (RLT 4,5) all'origine "
                                    "sarebbero circa {y} ufc/g.", y=cifre2(con_lag["ufc_g"])), "nota"))
        u.addWidget(self._peggiore(ris))
        u.addWidget(etichetta(_("La curva nel tempo"), "sottotitolo"))
        u.addWidget(etichetta(_("Da quanta Listeria all'origine si arriva al valore misurato."), "nota"))
        u.addWidget(grafico("fig_retro", ris))
        u.addWidget(etichetta(_("Tutti gli scenari"), "sottotitolo"))
        u.addWidget(self._scenari(ris))
        avvisi = list(dict.fromkeys(testi.avviso(a) for a in ris["avvisi"]))   # stessa frase una volta sola
        if avvisi:
            u.addWidget(etichetta(_("Da sapere"), "sottotitolo"))
            for a in avvisi:
                u.addWidget(riquadro("", a, "avviso"))
        u.addWidget(etichetta(_("Salva i risultati"), "sottotitolo"))
        u.addLayout(self._pulsanti_salva())

    def _intervallo(self, ris):
        """Tendina "Intervallo": quanto è incerto il valore più probabile, detto in parole semplici."""
        r, mc, u = ris["principale"], ris["monte_carlo"], ris["u_misura_log"]
        t = Apribile(_("Intervallo"), _("Quanto è sicuro il valore all'origine"))
        frasi = [_("Il valore più probabile all'origine è {x} ufc/g.", x=cifre2(r["ufc_g"])),
                 _("La conta di laboratorio ha un errore di circa ± {u} log: il valore vero può essere circa {f} volte "
                   "più alto o più basso di quello letto.", u=numero(u, 1), f=numero(10 ** u, 1)),
                 _("Per questo ErmChek ripete il calcolo {n} volte, ogni volta con una conta diversa entro "
                   "quell'errore.", n=numero(mc["n"], 0)),
                 _("In 9 calcoli su 10 all'origine c'erano fra {a} e {b} ufc/g.", a=cifre2(10 ** mc["log_n0_p5"]),
                   b=cifre2(10 ** mc["log_n0_p95"]))]
        peg = ris["monte_carlo_peggiore"]
        if peg and r["con_lab"]:
            frasi.append(_("Senza batteri lattici (caso peggiore): fra {a} e {b} ufc/g.",
                           a=cifre2(10 ** peg["log_n0_p5"]), b=cifre2(10 ** peg["log_n0_p95"])))
        for f in frasi:
            t.corpo.addWidget(etichetta(f))
        return t

    def _peggiore(self, ris):
        r, p = ris["principale"], ris["peggiore"]
        if not r["con_lab"]:
            return riquadro(_("Calcolo senza batteri lattici"), _("Il risultato sopra è già il caso peggiore."), "neutro")
        q = riquadro(_("Caso peggiore, senza batteri lattici"),
                     _("All'origine circa {x} ufc/g, cioè circa {y} ufc in 25 g.", x=cifre2(p["ufc_g"]),
                       y=cifre2(p["ufc_25g"])), "neutro")
        if p["ufc_pezzo"] is not None:
            q.layout().addWidget(etichetta(_("In un pezzo intero: circa {z} ufc.", z=cifre2(p["ufc_pezzo"]))))
        q.layout().addWidget(etichetta(_("Senza il freno dei batteri lattici Listeria cresce di più: per arrivare allo "
                                         "stesso valore ne basta molto meno all'inizio.")))
        q.layout().addWidget(etichetta(_("È il valore più basso compatibile con il modello: un limite, non la stima "
                                         "più probabile.")))
        return q

    def _scenari(self, ris):
        con_pezzo = ris["scenari"][0]["ufc_pezzo"] is not None
        intestazioni = [_("Scenario"), _("All'origine (ufc/g)"), _("In 25 g (ufc)")]
        suggerimenti = ["\n".join([termine("lab"), termine("lag")]), "", ""]
        if con_pezzo:
            intestazioni.append(_("In un pezzo (ufc)"))
            suggerimenti.append("")
        intestazioni.append(_("Crescita (log)"))
        suggerimenti.append(_("Di quanti log è cresciuta Listeria dal giorno 0 all'analisi."))
        righe = []
        for s in ris["scenari"]:
            nome = (_("Con LAB") if s["con_lab"] else _("Senza LAB")) + ", " + (_("con lag") if s["lag"] else _("senza lag"))
            riga = [nome, cifre2(s["ufc_g"]), cifre2(s["ufc_25g"])]
            if con_pezzo:
                riga.append(cifre2(s["ufc_pezzo"]))
            riga.append(fisso(s["delta_log"], 2))
            righe.append(riga)
        return tabella(intestazioni, righe, suggerimenti)

    def _pulsanti_salva(self):
        f = Flusso()
        for testo, funzione in [(_("Salva il PDF"), self.salva_pdf), *self.altri_salvataggi()]:
            b = QPushButton(testo, objectName="secondario")
            b.clicked.connect(funzione)
            f.addWidget(b)
        return f

    # ---------------- report ----------------
    def altri_salvataggi(self):
        return [(_("Salva Excel"), self.salva_excel)]

    def ingressi(self):
        d, o = self.dati_calcolo, self.dati_calcolo["opzioni"]
        oss = (_("{x} ufc in 25 g ({y} ufc/g)", x=numero(d["osservato"]), y=cifre2(d["osservato_ufc_g"]))
               if d["unita_oss"] == "25g" else _("{x} ufc/g", x=numero(d["osservato"])))
        righe = [(_("Listeria monocytogenes misurata"), oss), (_("Giorno dell'analisi"), numero(d["giorno"])),
                 (_("Batteri lattici al giorno 0"), _("{x} ufc/g", x=numero(d["lab0"])) if d["lab0"] else _("non indicati")),
                 (_("Modello"), "FSSP" if o["modello"] == "fssp" else "Baranyi & Roberts"),
                 (_("Incertezza di misura"), f"{numero(o['u'])} log10"),
                 (_("Variabilità della temperatura (sd)"), f"{numero(o['sd_t'])} °C"),
                 (_("Incertezza di μmax (CV)"), numero(o["cv_mu"]) if o["cv_mu"] else _("spenta")),
                 (_("Simulazioni Monte Carlo (n)"), _("{n} (seed {s})", n=numero(o["n_mc"], 0), s=o["seme"])),
                 (_("Peso del pezzo"), f"{numero(d['peso'])} g" if d["peso"] else _("non impostato"))]
        contesto = [(_("Tipo di prodotto"), d["tipo"]),
                    (_("Starter"), _("sì") if d["starter"] else _("no, fermentazione spontanea"))]
        if d["nitrati"]:
            contesto.append((_("Nitrato (solo informativo)"), "; ".join(
                _("fase {n}: {x} mg/kg", n=n, x=numero(x)) for n, x in d["nitrati"])))
        if d["file_csv"]:
            contesto.append((_("Temperature dal data logger"), Path(d["file_csv"]).name))
        if d["nota"]:
            contesto.append((_("Esempio"), d["nota"]))
        return {"titolo": d["nome"] or _("Quanta Listeria c'era all'origine"), "righe": righe, "contesto": contesto,
                "fasi": self.risultato["fasi"]}

    def _salva(self, titolo, filtro, estensione, scrivi):
        esito = salva_file(self, titolo, filtro, estensione, "ErmChek_origine" + estensione, scrivi)
        if esito:
            self.avviso_barra(*esito)

    def salva_pdf(self):
        if self.risultato is None:
            return

        def scrivi(percorso):
            from ermchek.report.pdf import crea_pdf
            crea_pdf(percorso, "retro", self.risultato, self.ingressi())
        self._salva(_("Salva il report PDF"), _("PDF (*.pdf)"), ".pdf", scrivi)

    def salva_excel(self):
        def scrivi(percorso):
            from ermchek.report.excel import esporta_excel
            esporta_excel(percorso, "retro", self.risultato, self.ingressi())
        self._salva(_("Salva il file Excel"), _("Excel (*.xlsx)"), ".xlsx", scrivi)

    def stato(self):
        return dict(super().stato(), fasi=len(self.editor.schede), punti=(self.editor.punti, self.editor.file_csv))

    def ripristina(self, stato):
        self.editor.imposta_n(stato["fasi"])
        self.esempio.blockSignals(True)
        super().ripristina(stato)
        self.esempio.blockSignals(False)
        self.editor._usa_punti(*stato["punti"])
