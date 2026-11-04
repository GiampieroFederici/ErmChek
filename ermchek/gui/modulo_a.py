"""Modulo A: conformità al criterio di legge e statistica del campionamento (ermchek.core.criteri, conformita).

Passi: criterio di legge, risultati delle unità, statistica, risultato. Il risultato comincia con l'esito normativo
e l'interpretazione del lotto; poi la tabella σ (probabilità massima su griglia, come lo script originale), le stime
di massima verosimiglianza, le curve OC, la prevalenza e lo script replicato.
"""
import numpy as np
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDateEdit, QFrame, QGridLayout, QHBoxLayout, QPlainTextEdit,
                               QPushButton, QRadioButton, QVBoxLayout)

from ermchek import testi
from ermchek.core import conformita, criteri
from ermchek.gui.base import (LIVELLI_ESITO, Campo, CampoNonValido, Flusso, Guidata, cifre2, etichetta, fisso, grafico,
                              leggi,
                              numero, pannello, percento, raccogli, rimetti, risposta, riquadro, salva_file, svuota, tabella)
from ermchek.gui.condizioni import blocco
from ermchek.gui.glossario import termine
from ermchek.lingua import N_, _

CATEGORIE = {"1.1": N_("Alimenti pronti per lattanti e a fini medici speciali"),
             "1.2": N_("Alimenti pronti che favoriscono la crescita di Listeria"),
             "1.3": N_("Alimenti pronti che non favoriscono la crescita di Listeria"),
             "1.4": N_("Carni macinate e preparazioni di carne da consumare crude"),
             "1.5": N_("Carni macinate e preparazioni di pollame da consumare cotte"),
             "1.6": N_("Carni macinate e preparazioni di altre specie da consumare cotte"),
             "1.7": N_("Carni separate meccanicamente"),
             "1.8": N_("Prodotti a base di carne da consumare crudi (salami)"),
             "1.9": N_("Prodotti a base di carne di pollame da consumare cotti"),
             "1.28": N_("Carni fresche di pollame (solo S. Typhimurium e S. Enteritidis)")}
PREDEFINITA = {"listeria": "1.2", "salmonella": "1.8"}
FASI = {"immesso_sul_mercato_shelf_life": N_("Mercato: prodotto immesso sul mercato, durante la shelf-life"),
        "prima_di_lasciare_controllo_osa": N_("Produzione: prima che lasci il controllo di chi lo ha prodotto")}
FORME = [N_("Intero"), N_("Affettato"), N_("Porzionato o a tranci"), N_("Macinato o impasto")]
INTEGRITA = [N_("Confezione integra"), N_("Confezione danneggiata"), N_("Non confezionato")]
TIPI = {"assente": N_("Non rilevata in {g} g"), "presente": N_("Rilevata in {g} g (presenza)"),
        "conta_g": N_("Conta in ufc/g"), "conta_25g": N_("Conta in ufc in 25 g"), "lod": N_("Conta sotto il LOD (< {lod} ufc/g)")}
SOLO_PRESENZA = ("assente", "presente")
SIGMA = (0.5, 0.8, 1.0, 1.5, 2.0)


class RigaUnita(QFrame):
    """Una unità analizzata: tipo di risultato e, per le conte, il valore."""
    togli = Signal(object)

    def __init__(self, n, togliibile):
        super().__init__(objectName="pannello")
        k = f"unita{n}_"
        r = QHBoxLayout(self)
        r.setContentsMargins(18, 10, 18, 10)
        r.setSpacing(16)
        r.addWidget(etichetta(_("Unità {n}", n=n), "pannello_titolo"), 0, Qt.AlignTop)
        self.tipo = QComboBox(objectName=k + "tipo")
        self.tipo.setAccessibleName(_("Risultato dell'unità {n}", n=n))
        r.addWidget(blocco(_("Risultato"), self.tipo, _("obbligatorio"), _("Che cosa ha detto il laboratorio per "
                                                                             "questa unità.")), 1, Qt.AlignTop)
        self.valore = Campo(_("Valore della conta"), "", (0, 1e9), aiuto=termine("ufc"), esempio="9.000",
                            chiave=k + "valore", nota=_("solo per le conte") + " · " + _("da 0 a 1.000.000.000"))
        r.addWidget(self.valore, 1, Qt.AlignTop)
        self.via = QPushButton(_("Togli"), objectName="piccolo")
        self.via.setVisible(togliibile)
        self.via.clicked.connect(lambda: self.togli.emit(self))
        r.addWidget(self.via, 0, Qt.AlignTop)
        self.tipo.currentIndexChanged.connect(self._tipo)

    def riempi(self, tipi, porzione, lod):
        scelto = self.tipo.currentData()
        self.tipo.blockSignals(True)
        self.tipo.clear()
        for t in tipi:
            self.tipo.addItem(_(TIPI[t], g=numero(porzione), lod=numero(lod)), t)
        self.tipo.setCurrentIndex(max(0, self.tipo.findData(scelto)))
        self.tipo.blockSignals(False)
        self._tipo()

    def _tipo(self, *_x):
        conta = self.tipo.currentData() in ("conta_g", "conta_25g")
        self.valore.setEnabled(conta)
        if not conta:
            self.valore.edit.clear()

    def risultato(self, porzione, lod):
        t = self.tipo.currentData()
        if t == "assente":
            return conformita.assente(porzione)
        if t == "presente":
            return conformita.conta(1.0 / porzione)   # almeno una cellula nella porzione
        if t == "lod":
            return conformita.sotto_lod(lod)
        v = self.valore.valore()
        if t == "conta_g":
            if v <= 0:
                self.valore.segnala(_("Una conta in ufc/g deve essere più grande di 0. Se è 0, scegli \"Non rilevata\"."))
            return conformita.conta(v)
        return conformita.conta_in_massa(v, 25.0)


class ModuloA(Guidata):
    titolo = N_("A. Conformità e campionamento")
    nomi_passi = (N_("Criterio di legge"), N_("Risultati delle unità"), N_("Statistica"), N_("Risultato"))

    def __init__(self, contesto, parent=None):
        super().__init__(contesto, parent)
        self.patogeno = None
        self.righe = []
        self._criterio(self.corpi[0])
        self._unita(self.corpi[1])
        self._statistica(self.corpi[2])
        self.mostrata()

    # ---------------- passo 1 ----------------
    def _criterio(self, c):
        p, s = pannello(_("Vuoi partire da un esempio?"))
        self.esempio = QComboBox(objectName="esempio")
        self.esempio.addItem(_("Nessun esempio: scrivo i miei dati"), None)
        self.esempio.addItem(_("Caso d'esame: 4 unità non rilevate in 25 g + 1 unità a 9.000 ufc/g"), "esame")
        self.esempio.currentIndexChanged.connect(self._carica_esempio)
        s.addWidget(blocco(_("Esempio: sostituisci con i tuoi dati"), self.esempio, _("facoltativo"),
                           _("Riempie tutti i passi con un esempio. Poi sostituisci i valori con i tuoi dati.")))
        c.addWidget(p)
        p, s = pannello(_("Il criterio"))
        self.categoria = QComboBox(objectName="categoria")
        self.patogeno_testo = etichetta("", "nota")
        s.addWidget(self.patogeno_testo)
        s.addWidget(blocco(_("Categoria di alimento (Reg. CE 2073/2005)"), self.categoria, _("obbligatorio"),
                           _("La riga del regolamento che vale per il tuo alimento.")))
        s.addWidget(etichetta(_("L'operatore ha dimostrato che Listeria resta sotto 100 ufc/g per tutta la shelf-life?"),
                              "etichetta_campo"))
        r = QHBoxLayout()
        self.fbo_si = QRadioButton(_("Sì"), objectName="fbo_si")
        self.fbo_no = QRadioButton(_("No"), objectName="fbo_no")
        self.fbo_no.setChecked(True)
        g = QButtonGroup(self)
        for b in (self.fbo_si, self.fbo_no):
            b.setToolTip(termine("fbo"))
            g.addButton(b)
            r.addWidget(b)
        r.addStretch(1)
        s.addLayout(r)
        self.nota_fbo = etichetta(_("Vale solo per Listeria, categoria 1.2."), "nota_campo")
        s.addWidget(self.nota_fbo)
        self.data = QDateEdit(QDate.currentDate(), objectName="")
        self.data.setCalendarPopup(True)
        self.data.setDisplayFormat("dd/MM/yyyy")
        s.addWidget(blocco(_("Data del campionamento"), self.data, _("obbligatorio"),
                           _("Il criterio dipende dalla data: dal 1° luglio 2026 vale il Reg. UE 2024/2895.")))
        self.fase = QComboBox(objectName="fase_campionamento")
        for codice, nome in FASI.items():
            self.fase.addItem(_(nome), codice)
        s.addWidget(blocco(_("Dove è stato prelevato il campione?"), self.fase, _("obbligatorio"),
                           _("Ogni criterio vale in una fase della filiera.")))
        self.riassunto = QVBoxLayout()
        s.addLayout(self.riassunto)
        c.addWidget(p)
        p, s = pannello(_("Il prodotto (solo contesto, va nel report)"))
        self.forma = QComboBox(objectName="forma")
        self.integrita = QComboBox(objectName="integrita")
        for menu, voci in ((self.forma, FORME), (self.integrita, INTEGRITA)):
            for v in voci:
                menu.addItem(_(v), v)
        s.addWidget(blocco(_("Forma del prodotto"), self.forma, _("facoltativo")))
        s.addWidget(blocco(_("Confezione"), self.integrita, _("facoltativo")))
        c.addWidget(p)
        for w in (self.categoria, self.fase):
            w.currentIndexChanged.connect(self._aggiorna_criterio)
        self.fbo_si.toggled.connect(self._aggiorna_criterio)
        self.data.dateChanged.connect(self._aggiorna_criterio)

    def _riga_criterio(self):
        cat = self.categoria.currentData()
        return criteri.seleziona_riga(cat, self._fbo(), self.data.date().toString("yyyy-MM-dd")) if cat else None

    def _fbo(self):
        return self.patogeno == "listeria" and self.categoria.currentData() == "1.2" and self.fbo_si.isChecked()

    def _aggiorna_criterio(self, *_x):
        ok = self.patogeno == "listeria" and self.categoria.currentData() == "1.2"
        for b in (self.fbo_si, self.fbo_no):
            b.setEnabled(ok)
        svuota(self.riassunto)
        riga = self._riga_criterio()
        if riga is None:
            self.riassunto.addWidget(riquadro(_("Nessun criterio vale per questa categoria a questa data."), "", "avviso"))
            return
        lim = riga["limite"]
        limite = (_("assente in {m} g", m=numero(lim["massa_g"])) if lim["tipo"] == "assenza"
                  else _("al massimo {v} ufc/g", v=numero(lim["valore"])))
        q = riquadro(_("Il criterio che si applica: riga {r}", r=riga["id"]), "", "info")
        for t in (_("Piano: n = {n}, c = {c}.", n=riga["n"], c=riga["c"]), _("Limite: {l}.", l=limite),
                  _("Metodo: {m}.", m=riga["metodo"]), _("Fase: {f}.", f=_(FASI[riga["fase"]])), riga["riferimento"]):
            q.layout().addWidget(etichetta(t))
        q.setToolTip(termine("n_c"))
        self.riassunto.addWidget(q)
        if not self.n.testo():
            self.n.imposta(riga["n"])
            self.c.imposta(riga["c"])

    def _carica_esempio(self, *_x):
        if self.esempio.currentData() != "esame":
            return
        self.contesto.patogeno = "listeria"
        self.mostrata()
        self.categoria.setCurrentIndex(self.categoria.findData("1.2"))
        self.fbo_no.setChecked(True)
        self.data.setDate(QDate.currentDate())
        self.fase.setCurrentIndex(0)
        self.porzione.imposta(25)
        self.lod.imposta(10)
        self.imposta_righe(5)
        for i, riga in enumerate(self.righe):
            riga.tipo.setCurrentIndex(riga.tipo.findData("conta_g" if i == 0 else "assente"))
            if i == 0:
                riga.valore.imposta(9000)
        self.n.imposta(5)
        self.c.imposta(0)

    # ---------------- passo 2 ----------------
    def _unita(self, c):
        c.addWidget(etichetta(_("Un riquadro per ogni unità analizzata del lotto.")))
        p, s = pannello()
        g = QGridLayout()
        g.setHorizontalSpacing(20)
        self.porzione = Campo(_("Porzione analitica"), "g", (0.1, 1000), aiuto=termine("porzione"), esempio="25",
                              chiave="porzione")
        self.lod = Campo("LOD", "ufc/g", (0.01, 1e6), aiuto=termine("lod"), esempio="10", chiave="lod")
        self.porzione.imposta(25)
        self.lod.imposta(10)
        g.addWidget(self.porzione, 0, 0, Qt.AlignTop)
        g.addWidget(self.lod, 0, 1, Qt.AlignTop)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        s.addLayout(g)
        c.addWidget(p)
        self.zona_righe = QVBoxLayout()
        self.zona_righe.setSpacing(10)
        c.addLayout(self.zona_righe)
        r = QHBoxLayout()
        b = QPushButton(_("+ Aggiungi un'unità"), objectName="secondario")
        b.clicked.connect(lambda: self.imposta_righe(len(self.righe) + 1, tieni=True))
        r.addWidget(b)
        r.addStretch(1)
        c.addLayout(r)
        self.conteggio = etichetta("", "nota")
        c.addWidget(self.conteggio)
        for campo in (self.porzione, self.lod):
            campo.cambiato.connect(self._riempi_tipi)

    def _tipi(self):
        return SOLO_PRESENZA if self.patogeno == "salmonella" else tuple(TIPI)

    def _riempi_tipi(self):
        porzione, lod = self.porzione.prova() or 25.0, self.lod.prova() or 10.0
        for r in self.righe:
            r.riempi(self._tipi(), porzione, lod)

    def imposta_righe(self, n, tieni=False):
        vecchi = [self._valori(r, i + 1) for i, r in enumerate(self.righe)] if tieni else []
        for r in self.righe:
            r.hide()
            r.deleteLater()
        self.righe = []
        for i in range(max(1, n)):
            riga = RigaUnita(i + 1, togliibile=n > 1)
            riga.togli.connect(self._togli)
            self.righe.append(riga)
            self.zona_righe.addWidget(riga)
        self._riempi_tipi()
        for i, v in enumerate(vecchi[:n]):
            rimetti(self.righe[i], {f"unita{i + 1}_{k}": x for k, x in v.items()})
        self.conteggio.setText(_("Unità: {n}.", n=len(self.righe)))

    @staticmethod
    def _valori(riga, n):
        prefisso = f"unita{n}_"
        return {k[len(prefisso):]: v for k, v in raccogli(riga).items() if k.startswith(prefisso)}

    def _togli(self, riga):
        i = self.righe.index(riga)
        valori = [self._valori(r, j + 1) for j, r in enumerate(self.righe) if j != i]
        self.imposta_righe(len(valori))
        for j, v in enumerate(valori):
            rimetti(self.righe[j], {f"unita{j + 1}_{k}": x for k, x in v.items()})

    # ---------------- passo 3 ----------------
    def _statistica(self, c):
        c.addWidget(etichetta(_("Le scelte per la curva OC e per la prevalenza. I valori proposti vanno bene quasi sempre.")))
        p, s = pannello(_("Curva OC (probabilità di accettare il lotto)"))
        g = QGridLayout()
        g.setHorizontalSpacing(20)
        g.setVerticalSpacing(12)
        self.sigma = QComboBox(objectName="sigma_oc")
        for v in SIGMA:
            self.sigma.addItem(numero(v, 1), v)
        self.sigma.setCurrentIndex(SIGMA.index(1.0))
        g.addWidget(blocco(_("σ fra le unità (log10)"), self.sigma, _("obbligatorio"), termine("sigma")), 0, 0, Qt.AlignTop)
        self.n = Campo("n", "", (1, 100), aiuto=termine("n_c"), esempio="5", chiave="n_oc", intero=True)
        self.c = Campo("c", "", (0, 100), aiuto=termine("n_c"), esempio="0", chiave="c_oc", intero=True)
        g.addWidget(self.n, 0, 1, Qt.AlignTop)
        g.addWidget(self.c, 0, 2, Qt.AlignTop)
        for j in range(3):
            g.setColumnStretch(j, 1)
        s.addLayout(g)
        s.addWidget(etichetta(_("n e c sono quelli del criterio: cambiali per confrontare altri piani."), "nota"))
        p.setToolTip(termine("oc"))
        c.addWidget(p)
        p, s = pannello(_("Prevalenza"))
        self.p_obiettivo = Campo(_("Prevalenza da trovare"), "%", (0.1, 99.9), aiuto=termine("clopper"), esempio="10",
                                 chiave="p_obiettivo")
        self.p_obiettivo.imposta(10)
        s.addWidget(self.p_obiettivo)
        s.addWidget(etichetta(_("Quante unità servono per trovare almeno una positiva, con confidenza 95 %."), "nota"))
        c.addWidget(p)

    # ---------------- percorso ----------------
    def mostrata(self):
        """Il patogeno si sceglie nella pagina iniziale: con un patogeno nuovo si rifanno categorie e tipi."""
        if self.patogeno != self.contesto.patogeno:
            self.patogeno = self.contesto.patogeno
            nome = "Listeria monocytogenes" if self.patogeno == "listeria" else "Salmonella spp."
            self.patogeno_testo.setText(_("Patogeno: {p} (si cambia nella pagina iniziale).", p=nome))
            self.categoria.blockSignals(True)
            self.categoria.clear()
            for r in criteri.carica_criteri()["criteri"]:
                if r["patogeno"] == self.patogeno and self.categoria.findData(r["categoria"]) < 0:
                    self.categoria.addItem(f"{r['categoria']} · {_(CATEGORIE.get(r['categoria'], ''))}", r["categoria"])
            self.categoria.setCurrentIndex(self.categoria.findData(PREDEFINITA[self.patogeno]))
            self.categoria.blockSignals(False)
            self.n.edit.clear()
            if not self.righe:
                self.imposta_righe(5)
            self._riempi_tipi()
            self.risultato = None
            svuota(self.uscita)
            self._aggiorna_criterio()
        super().mostrata()

    def controlla(self, i):
        try:
            if i == 0:
                if self._riga_criterio() is None:
                    return self.errore_passo(_("Nessun criterio vale per questa categoria a questa data."))
            elif i == 1:
                self._risultati()
            elif i == 2:
                v = leggi({"n": self.n, "c": self.c, "p": self.p_obiettivo})
                if v["c"] > v["n"]:
                    self.c.segnala(_("c non può essere più grande di n."))
        except CampoNonValido:
            return self.errore_passo(_("Controlla i campi segnati in rosso."))
        self.avviso_barra("", "")
        return True

    def _risultati(self):
        v = leggi({"porzione": self.porzione, "lod": self.lod})
        uscita, errore = [], False
        for r in self.righe:
            try:
                uscita.append(r.risultato(v["porzione"], v["lod"]))
            except CampoNonValido:
                errore = True
        if errore:
            raise CampoNonValido(_("Controlla i campi segnati in rosso."))
        return uscita

    # ---------------- calcolo ----------------
    def prepara(self):
        risultati = self._risultati()
        cat, fbo, data = self.categoria.currentData(), self._fbo(), self.data.date().toString("yyyy-MM-dd")
        fase = self.fase.currentData()
        riga = self._riga_criterio()
        v = leggi({"n": self.n, "c": self.c, "p": self.p_obiettivo, "porzione": self.porzione})
        sigma = self.sigma.currentData()
        criterio = "presenza_assenza" if riga["limite"]["tipo"] == "assenza" else "enumerazione"
        positive = sum(r.tipo == "conta" for r in risultati)
        self.dati_calcolo = {"categoria": self.categoria.currentText(), "fbo": fbo, "data": data, "fase": fase,
                             "forma": self.forma.currentText(), "integrita": self.integrita.currentText(),
                             "porzione": v["porzione"], "lod": self.lod.prova(), "n_oc": v["n"], "c_oc": v["c"],
                             "sigma": sigma, "criterio": criterio, "unita": [r.tipo.currentText() + (
                                 f": {r.valore.testo()}" if r.valore.isEnabled() else "") for r in self.righe]}
        patogeno = self.patogeno

        def calcolo():
            mu = np.linspace(-4.0, 3.0, 141)
            nome = (f"n = {v['n']}, c = {v['c']}, σ = {sigma:g}, " +
                    (f"{v['porzione']:g} g (presence/absence)" if criterio == "presenza_assenza" else "> 100 CFU/g"))
            confronto = conformita.confronto_modelli(risultati)
            prev = conformita.prevalenza(positive, len(risultati))
            prev.update(k=positive, n=len(risultati), p_obiettivo=v["p"] / 100,
                        n_necessario=conformita.n_necessario(v["p"] / 100))
            return {"esito": criteri.esito_normativo(risultati, cat, fbo, data, fase_campionamento=fase),
                    "interpretazione": conformita.interpretazione(risultati),
                    "griglia": conformita.griglia_pattern(risultati),
                    "mle": confronto["lognormale"], "miscela": confronto["miscela"], "confronto": confronto,
                    "oc": {"mu": mu, "curve": {nome: conformita.curva_oc(v["n"], v["c"], sigma, v["porzione"], mu,
                                                                         criterio)}},
                    "prevalenza": prev, "patogeno": patogeno}
        return calcolo

    # ---------------- risultato ----------------
    def mostra(self, ris):
        u, e, it = self.uscita, ris["esito"], ris["interpretazione"]
        righe = [_(testi.MOTIVI[e["motivo"]])]
        if e["riga"]:
            righe.append(_("Riga del regolamento: {r}.", r=e["riga"]))
        if e["unita_oltre_limite"] is not None:
            righe.append(_("Unità oltre il limite: {k} su {n}.", k=e["unita_oltre_limite"], n=e["n_analizzato"]))
        righe.append(_(testi.INTERPRETAZIONI[it["codice"]]))
        spiega = {"CONFORME": _("Verde: il lotto rispetta il criterio."),
                  "NON_CONFORME": _("Rosso: il lotto non rispetta il criterio."),
                  "NON_VALUTABILE": _("Giallo: con questi dati il criterio non si può valutare.")}[e["esito"]]
        u.addWidget(risposta(LIVELLI_ESITO[e["esito"]], _(testi.ESITI[e["esito"]]), righe, spiega))
        u.addWidget(etichetta(_("Interpretazione: confronto fra lotto omogeneo e contaminazione localizzata, "
                                "p = {p} (soglia 0,05).", p=numero(it["p_valore"], 4)), "nota"))

        u.addWidget(etichetta(_("Quanto varia la contaminazione fra le unità (σ)"), "sottotitolo"))
        u.addWidget(etichetta(_("Per ogni σ fissata si cerca la μ che rende più probabile il risultato osservato, su una "
                                "griglia di valori (come lo script originale).")))
        g = ris["griglia"]
        u.addWidget(tabella([_("σ (log10)"), _("Probabilità massima del risultato"), _("μ migliore (log10 ufc/g)")],
                            [[fisso(s, 1), cifre2(p) if p > 0 else "0", fisso(m, 2) if np.isfinite(m) else "-"]
                             for s, p, m in zip(g["sigma"], g["p_max"], g["mu_ottimale"])],
                            [termine("sigma"), "", termine("mu")]))
        u.addWidget(grafico("fig_pattern_sigma", g, altezza=400))

        u.addWidget(etichetta(_("Stime di massima verosimiglianza (MLE)"), "sottotitolo"))
        ln, mi, c = ris["mle"], ris["miscela"], ris["confronto"]
        bordo = any(x["sigma"] <= 0.051 or x["sigma"] >= 4.99 for x in (ln, mi))
        for t in (_("Log-normale: μ = {mu} e σ = {s} log10 ufc/g. Sono i valori che rendono più probabili tutti i "
                    "risultati insieme.", mu=numero(ln["mu"], 2), s=numero(ln["sigma"], 2)),
                  _("Miscela: circa {pi} delle unità senza Listeria; le altre con μ = {mu} e σ = {s}.",
                    pi=percento(mi["pi"]), mu=numero(mi["mu"], 2), s=numero(mi["sigma"], 2)),
                  _("σ e la miscela sono al bordo della ricerca (da 0,05 a 5 log): con poche unità la stima è "
                    "poco precisa.") if bordo else "",
                  _("Differenza con la tabella sopra: lì σ è fissata e μ si cerca su una griglia; la MLE cerca μ e σ "
                    "insieme, senza griglia. Per questo i numeri non coincidono."),
                  _("Confronto fra i due modelli (rapporto di verosimiglianza): p = {p}. Sotto 0,05 si preferisce la "
                    "miscela.", p=numero(c["p_valore"], 4))):
            if not t:
                continue
            q = etichetta(t)
            q.setToolTip("\n".join([termine("mle"), termine("miscela")]))
            u.addWidget(q)
        if ris["patogeno"] == "salmonella":
            u.addWidget(etichetta(_("Con Salmonella le stime valgono per la presenza nelle porzioni, non per conte."),
                                  "nota"))

        u.addWidget(etichetta(_("Curva OC: probabilità di accettare il lotto"), "sottotitolo"))
        u.addWidget(etichetta(_("Per ogni concentrazione media μ del lotto, la probabilità che il piano n, c lo accetti."),
                              ""))
        u.addWidget(grafico("fig_oc", ris["oc"]["mu"], ris["oc"]["curve"], altezza=400))

        u.addWidget(etichetta(_("Prevalenza"), "sottotitolo"))
        pr = ris["prevalenza"]
        q = etichetta(_("Unità positive: {k} su {n}. Prevalenza stimata: {p} (intervallo di Clopper-Pearson al 95 %: "
                        "da {a} a {b}).", k=pr["k"], n=pr["n"], p=percento(pr["stima"]), a=percento(pr["inferiore"]),
                        b=percento(pr["superiore"])))
        q.setToolTip(termine("clopper"))
        u.addWidget(q)
        u.addWidget(etichetta(_("Per trovare almeno un'unità positiva con prevalenza {p} e confidenza 95 % servono "
                                "{n} unità.", p=percento(pr["p_obiettivo"]), n=pr["n_necessario"])))

        u.addWidget(etichetta(_("Lo script di partenza"), "sottotitolo"))
        u.addWidget(etichetta(_("Le righe stampate dallo script originale sul caso d'esame, rifatte da ErmChek."), "nota"))
        self.script = QPlainTextEdit(objectName="codice")
        self.script.setReadOnly(True)
        self.script.setPlainText("\n".join(conformita.replica_script()))
        carattere = QFont("Consolas")      # come QPlainTextEdit#codice in stile.qss
        carattere.setPixelSize(16)
        self.script.setFixedHeight(QFontMetrics(carattere).lineSpacing() * len(conformita.replica_script()) + 44)
        self.script.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.script.hide()
        b = QPushButton(_("Replica lo script"), objectName="secondario")
        b.clicked.connect(lambda: self.script.setVisible(not self.script.isVisible()))
        f = Flusso()
        f.addWidget(b)
        u.addLayout(f)
        u.addWidget(self.script)

        u.addWidget(etichetta(_("Salva i risultati"), "sottotitolo"))
        f = Flusso()
        for testo, funzione in [(_("Salva il PDF"), self.salva_pdf), *self.altri_salvataggi()]:
            b = QPushButton(testo, objectName="secondario")
            b.clicked.connect(funzione)
            f.addWidget(b)
        u.addLayout(f)

    # ---------------- report ----------------
    def altri_salvataggi(self):
        return [(_("Salva Excel"), self.salva_excel)]

    def ingressi(self):
        d = self.dati_calcolo
        righe = [(_("Categoria"), d["categoria"]), (_("Data del campionamento"), d["data"]),
                 (_("Dove è stato prelevato il campione?"), _(FASI[d["fase"]])),
                 (_("Porzione analitica"), f"{numero(d['porzione'])} g"), ("LOD", f"{numero(d['lod'] or 10)} ufc/g"),
                 (_("Curva OC"), f"n = {d['n_oc']}, c = {d['c_oc']}, σ = {numero(d['sigma'], 1)}")]
        righe += [(_("Unità {n}", n=i + 1), t) for i, t in enumerate(d["unita"])]
        if d["categoria"].startswith("1.2"):
            righe.insert(1, (_("Dimostrazione dell'operatore (100 ufc/g)"), _("sì") if d["fbo"] else _("no")))
        contesto = [(_("Forma del prodotto"), d["forma"]), (_("Confezione"), d["integrita"])]
        return {"titolo": _("Conformità e campionamento"), "righe": righe, "contesto": contesto, "fasi": None}

    def _per_report(self):
        return {k: self.risultato[k] for k in ("esito", "interpretazione", "griglia", "mle", "miscela", "prevalenza",
                                               "patogeno")}

    def _salva(self, titolo, filtro, estensione, scrivi):
        esito = salva_file(self, titolo, filtro, estensione, "ErmChek_conformita" + estensione, scrivi)
        if esito:
            self.avviso_barra(*esito)

    def salva_pdf(self):
        if self.risultato is None:
            return

        def scrivi(percorso):
            from ermchek.report.pdf import crea_pdf
            crea_pdf(percorso, "conformita", self._per_report(), self.ingressi())
        self._salva(_("Salva il report PDF"), _("PDF (*.pdf)"), ".pdf", scrivi)

    def salva_excel(self):
        def scrivi(percorso):
            from ermchek.report.excel import esporta_excel
            esporta_excel(percorso, "conformita", self._per_report(), self.ingressi())
        self._salva(_("Salva il file Excel"), _("Excel (*.xlsx)"), ".xlsx", scrivi)

    def stato(self):
        return dict(super().stato(), righe=len(self.righe), patogeno=self.patogeno, data=self.data.date())

    def ripristina(self, stato):
        self.contesto.patogeno = stato["patogeno"]
        self.mostrata()
        self.imposta_righe(stato["righe"])
        self.esempio.blockSignals(True)
        super().ripristina(stato)
        self.esempio.blockSignals(False)
        self.data.setDate(stato["data"])
        self._riempi_tipi()
