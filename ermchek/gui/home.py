"""Pagina iniziale: quale patogeno e quale domanda (moduli A, B, C)."""
from PySide6.QtWidgets import QButtonGroup

from ermchek.gui.base import Pagina, Scelta, etichetta, riga_di_scelte, riquadro
from ermchek.lingua import N_, _

MODULI = [("C", N_("C. Quanta ce n'era all'origine (back-calculation)"),
           N_("Hai trovato Listeria nel prodotto: quanta ce n'era all'inizio, per esempio all'insacco?")),
          ("B", N_("B. Crescita nel tempo"),
           N_("Quanto cresce Listeria durante la produzione e la shelf-life? Supera 100 ufc/g?")),
          ("A", N_("A. Conformità e campionamento"),
           N_("Il lotto rispetta il criterio di legge? Che cosa dicono i risultati delle unità?"))]


class PaginaHome(Pagina):
    titolo = N_("Che cosa vuoi sapere?")

    def __init__(self, contesto, parent=None):
        super().__init__(contesto, parent)
        c = self.corpo
        c.addWidget(etichetta(_("ErmChek aiuta a ragionare su Listeria monocytogenes negli alimenti pronti, "
                                "soprattutto nei salumi.")))
        c.addWidget(etichetta(_("1. Il patogeno"), "sottotitolo"))
        gruppo = QButtonGroup(self)
        self.listeria = Scelta("Listeria monocytogenes", _("Criteri di legge, crescita e back-calculation."), gruppo)
        self.salmonella = Scelta("Salmonella spp.", _("Solo criteri di legge e statistica (modulo A)."), gruppo)
        self.listeria.pulsante.setObjectName("patogeno_listeria")
        self.salmonella.pulsante.setObjectName("patogeno_salmonella")
        c.addLayout(riga_di_scelte(self.listeria, self.salmonella))
        c.addWidget(etichetta(_("2. La domanda"), "sottotitolo"))
        self.solo_a = riquadro(_("Con Salmonella c'è solo il modulo A."), _(
            "Non abbiamo trovato un modello di crescita di Salmonella validato su carne con nitrito "
            "(params/salmonella_ricerca.md). Per questo B e C sono spenti."), "avviso")
        c.addWidget(self.solo_a)
        self.schede = {}
        gruppo = QButtonGroup(self)
        for chiave, titolo, spiega in MODULI:
            s = Scelta(_(titolo), _(spiega), gruppo, consigliato=False, lettera=chiave)
            s.pulsante.setObjectName(f"modulo_{chiave}")
            s.pulsante.toggled.connect(lambda _x: self.aggiorna_azioni())
            self.schede[chiave] = s
            c.addWidget(s)
        self.listeria.pulsante.toggled.connect(self._patogeno)
        self.schede["C"].pulsante.setChecked(True)
        self.listeria.pulsante.setChecked(True)
        self._patogeno()

    def _patogeno(self, *_x):
        listeria = self.listeria.pulsante.isChecked()
        self.contesto.patogeno = "listeria" if listeria else "salmonella"
        for k in ("B", "C"):
            self.schede[k].setEnabled(listeria)
        if not listeria and not self.schede["A"].pulsante.isChecked():
            self.schede["A"].pulsante.setChecked(True)
        self.solo_a.setVisible(not listeria)
        self.aggiorna_azioni()

    def scelto(self):
        return next(k for k, s in self.schede.items() if s.pulsante.isChecked())

    def aggiorna_azioni(self):
        if not hasattr(self, "schede"):
            return
        self.testo_principale = _("Inizia il modulo {m}", m=self.scelto())
        self.azioni_cambiate.emit()

    def azione_principale(self):
        self.vai.emit(self.scelto())

    def mostrata(self):
        (self.listeria if self.contesto.patogeno == "listeria" else self.salmonella).pulsante.setChecked(True)
        super().mostrata()
