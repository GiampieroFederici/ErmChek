"""Info: logo, versione, limiti, validazione FSSP, fonti, licenza, nessuna rete."""
import yaml
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

from ermchek import __version__
from ermchek.gui.base import Pagina, etichetta, pannello, riquadro
from ermchek.lingua import N_, _
from ermchek.percorsi import risorsa

LIMITI = [N_("ErmChek è uno strumento didattico e di supporto alle decisioni."),
          N_("Non sostituisce i challenge test né gli studi di durabilità (guida tecnica EURL Lm v4, emendamento 1, "
             "26/02/2026, DOI 10.5281/zenodo.18783767)."),
          N_("Non sostituisce l'autorità competente."),
          N_("I modelli valgono solo dentro i loro campi di validità: fuori, ErmChek lo dice con un avviso."),
          N_("Il modello prevede solo crescita, mai la morte di Listeria: la stima all'origine è un valore minimo."),
          N_("Salmonella: solo criteri di legge e statistica. Nessun modello di crescita validato su carne con nitrito.")]


def fonti():
    """Le citazioni complete dei modelli (params/fssp.yaml, campo `fonti`), lette con yaml.safe_load."""
    try:
        with open(risorsa("params", "fssp.yaml"), encoding="utf-8") as f:
            return list((yaml.safe_load(f) or {}).get("fonti", {}).values())
    except (OSError, yaml.YAMLError):
        return []


class PaginaInfo(Pagina):
    titolo = N_("Informazioni")

    def __init__(self, contesto, parent=None):
        super().__init__(contesto, parent)
        c = self.corpo
        logo = QLabel()
        logo.setPixmap(QPixmap(str(risorsa("assets", "logo", "ErmChek_logo.png"))).scaledToHeight(
            120, Qt.SmoothTransformation))
        logo.setAccessibleName("ErmChek")
        c.addWidget(logo)
        c.addWidget(etichetta(_("Versione {v}", v=__version__), "sottotitolo"))
        c.addWidget(etichetta(_("Listeria monocytogenes (e Salmonella, solo criteri) negli alimenti pronti, soprattutto "
                                "nei salumi.")))
        q = riquadro(_("Limiti"), "", "avviso")
        for t in LIMITI:
            q.layout().addWidget(etichetta(_(t)))
        c.addWidget(q)
        p, s = pannello(_("Validazione"))
        s.addWidget(etichetta(_("Il motore di crescita dà gli stessi numeri di FSSP.Models.dll 1.1.0.21167 (FSSP 4.0, "
                                "DTU Food): 23 casi su 23 identici (tests/validation_fssp.md).")))
        c.addWidget(p)
        p, s = pannello(_("Fonti dei modelli"))
        for f in fonti():
            s.addWidget(etichetta(f, "nota"))
        s.addWidget(etichetta(_("Criteri di legge: Reg. (CE) 2073/2005, All. I, cap. 1, testo consolidato al "
                                "01/07/2026 (CELEX 02005R2073-20260701), con il Reg. (UE) 2024/2895."), "nota"))
        c.addWidget(p)
        p, s = pannello(_("Licenza e privacy"))
        s.addWidget(etichetta(_("Licenza MIT. Carattere Atkinson Hyperlegible (SIL Open Font License).")))
        s.addWidget(etichetta(_("Funziona offline: nessuna connessione di rete. I file si scrivono solo dove scegli tu.")))
        c.addWidget(p)
