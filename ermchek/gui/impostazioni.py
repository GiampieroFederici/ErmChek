"""Impostazioni (QSettings "ErmChek"): lingua, peso del pezzo, incertezza di misura predefinita."""
from PySide6.QtWidgets import QComboBox

from ermchek import lingua
from ermchek.gui.base import Campo, CampoNonValido, Pagina, etichetta, impostazioni, incertezza_misura, leggi, pannello, \
    peso_pezzo
from ermchek.gui.condizioni import blocco
from ermchek.gui.glossario import termine
from ermchek.lingua import N_, _


class PaginaImpostazioni(Pagina):
    titolo = N_("Impostazioni")

    def __init__(self, contesto, parent=None):
        super().__init__(contesto, parent)
        c = self.corpo
        p, s = pannello(_("Lingua"))
        self.lingua = QComboBox()
        for codice, nome in lingua.LINGUE.items():
            self.lingua.addItem(nome, codice)
        self.lingua.setCurrentIndex(self.lingua.findData(lingua.attuale()))
        s.addWidget(blocco(_("Lingua dell'interfaccia e dei report"), self.lingua, "",
                           _("Si cambia anche con il pulsante in alto a destra.")))
        c.addWidget(p)
        p, s = pannello(_("Il prodotto"))
        self.peso = Campo(_("Peso di un pezzo"), "g", (1, 1e6), obbligatorio=False, esempio="400", aiuto=_(
            "Il peso di un pezzo intero (per esempio un salame).\nServe per dire quante cellule c'erano in un pezzo."))
        self.peso.imposta(peso_pezzo())
        s.addWidget(self.peso)
        s.addWidget(etichetta(_("Nessun valore predefinito: lascialo vuoto se non serve."), "nota"))
        c.addWidget(p)
        p, s = pannello(_("Il laboratorio"))
        self.u = Campo(_("Incertezza di misura predefinita"), "log10", (0, 3), esempio="0,5", aiuto=termine("incertezza"))
        self.u.imposta(incertezza_misura())
        s.addWidget(self.u)
        s.addWidget(etichetta(_("0,5 log è il valore della guida EURL per Listeria con EN ISO 11290-2."), "nota"))
        c.addWidget(p)
        self.testo_principale = _("Salva le impostazioni")

    def azione_principale(self):
        try:
            v = leggi({"peso": self.peso, "u": self.u})
        except CampoNonValido as e:
            self.avviso_barra(str(e), "errore")
            return
        q = impostazioni()
        q.setValue("peso_pezzo_g", "" if v["peso"] is None else v["peso"])
        q.setValue("incertezza_log", v["u"])
        self.avviso_barra(_("Impostazioni salvate. Valgono dal prossimo calcolo."), "")
        self.salvate.emit()
        codice = self.lingua.currentData()
        if codice != lingua.attuale():
            self.lingua_scelta.emit(codice)
