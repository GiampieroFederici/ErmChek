"""Pezzi comuni ai moduli B (crescita) e C (back-calculation): esempi, fasi, batteri lattici, opzioni.

Le fasi sono schede una sotto l'altra (una fase = un tratto a condizioni costanti). Il sale si dà come aw OPPURE
come sale nella fase acquosa: un menu per fase spegne l'altro campo (niente doppio conteggio, come nel core).
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
                               QGridLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QVBoxLayout, QWidget)

from ermchek import testi
from ermchek.core import crescita
from ermchek.core.crescita import LIMITI
from ermchek.core.fssp.modelli import ACIDI
from ermchek.gui.base import (Apribile, Campo, CampoNonValido, Scelta, etichetta, incertezza_misura, leggi, numero,
                              pannello, raccogli, rimetti, riquadro, svuota)
from ermchek.gui.glossario import termine
from ermchek.lingua import N_, _

MAX_UFC = 3e8   # poco sotto Nmax di Listeria e dei LAB (10^8,5 ufc/g)
TIPI = [("fermentato", N_("Salame o insaccato fermentato")), ("fresco", N_("Salsiccia o insaccato fresco")),
        ("cotto", N_("Prodotto cotto affettato")), ("altro", N_("Altro alimento pronto"))]
NOMI_ACIDI = {"lattico": N_("Acido lattico"), "acetico": N_("Acido acetico"), "diacetato": N_("Diacetato"),
              "citrico": N_("Acido citrico"), "sorbico": N_("Acido sorbico"), "benzoico": N_("Acido benzoico")}


def _fase(durata, unita, t, ph, aw=None, sale=None, nitrito=0.0):
    return {"durata": durata, "unita": unita, "temperatura": t, "ph": ph, "aw": aw, "sale": sale, "nitrito": nitrito}


# Esempi: valori plausibili, solo per provare il programma (da sostituire con dati reali).
PRESET = [
    {"chiave": "salame_fresco", "nome": N_("Salame fresco (esempio)"), "tipo": "fermentato",
     "fasi": [_fase(2, "giorni", 20, 5.9, aw=0.965, nitrito=40), _fase(10, "giorni", 12, 5.4, aw=0.95, nitrito=20)],
     "lab0": 1e5, "starter": False, "osservato": 300, "unita_oss": "g", "giorno": 12, "n0": 1, "nota": ""},
    {"chiave": "salsiccia", "nome": N_("Salsiccia fresca (esempio)"), "tipo": "fresco",
     "fasi": [_fase(10, "giorni", 4, 6.0, aw=0.97)], "lab0": 1e3, "starter": False,
     "osservato": 20, "unita_oss": "g", "giorno": 10, "n0": 1, "nota": ""},
    {"chiave": "stagionato", "nome": N_("Salame stagionato (esempio)"), "tipo": "fermentato",
     "fasi": [_fase(2, "giorni", 22, 5.8, aw=0.96, nitrito=60), _fase(5, "giorni", 15, 5.2, aw=0.94, nitrito=30),
              _fase(35, "giorni", 13, 5.3, aw=0.90, nitrito=10)],
     "lab0": 1e6, "starter": True, "osservato": 10, "unita_oss": "g", "giorno": 42, "n0": 10, "nota": ""},
    {"chiave": "cotto", "nome": N_("Prosciutto cotto affettato (esempio)"), "tipo": "cotto",
     "fasi": [_fase(7, "giorni", 4, 6.2, sale=3.0, nitrito=40), _fase(21, "giorni", 8, 6.2, sale=3.0, nitrito=40)],
     "lab0": 100, "starter": False, "osservato": 150, "unita_oss": "g", "giorno": 28, "n0": 1, "nota": ""},
]


def menu_esempi(chiave):
    """Il menu degli esempi, con la scritta chiara che sono esempi da sostituire."""
    m = QComboBox(objectName=chiave)
    m.addItem(_("Nessun esempio: scrivo i miei dati"), None)
    for p in PRESET:
        m.addItem(_(p["nome"]), p["chiave"])
    m.setAccessibleName(_("Esempio: sostituisci con i tuoi dati"))
    m.setToolTip(_("Riempie tutti i passi con un esempio. Poi sostituisci i valori con i tuoi dati."))
    return m


def preset(chiave):
    return next((p for p in PRESET if p["chiave"] == chiave), None)


def menu_tipo(chiave):
    m = QComboBox(objectName=chiave)
    for codice, nome in TIPI:
        m.addItem(_(nome), codice)
    m.setAccessibleName(_("Tipo di prodotto"))
    return m


def blocco(titolo, widget, nota="", suggerimento=""):
    """Etichetta in grassetto sopra un widget (menu, data...), con una nota sotto."""
    w = QWidget(objectName="trasparente")
    s = QVBoxLayout(w)
    s.setContentsMargins(0, 0, 0, 0)
    s.setSpacing(3)
    e = etichetta(titolo, "etichetta_campo")
    s.addWidget(e)
    s.addWidget(widget)
    if nota:
        s.addWidget(etichetta(nota, "nota_campo"))
    for x in (e, widget):
        x.setToolTip(suggerimento)
    return w


# ---------------- calcolatrice del sale nella fase acquosa ----------------
class DialogoWps(QDialog):
    """WPS dal NaCl sul prodotto e dall'umidità, con il calcolo scritto per intero (crescita.wps)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Sale nella fase acquosa (WPS)"))
        self.valore = None
        s = QVBoxLayout(self)
        s.setContentsMargins(24, 20, 24, 20)
        s.setSpacing(12)
        s.addWidget(etichetta(_("WPS = NaCl × 100 / (NaCl + umidità)"), "etichetta_campo"))
        self.nacl = Campo(_("NaCl sul prodotto"), "%", (0, 40), aiuto=_("Sale sul peso totale del prodotto."),
                          esempio="2,5")
        self.umidita = Campo(_("Umidità del prodotto"), "%", (0.1, 100), aiuto=_("Acqua sul peso totale del prodotto."),
                             esempio="60")
        self.calcolo = etichetta("", "conversione")
        for c in (self.nacl, self.umidita):
            c.cambiato.connect(self._aggiorna)
            s.addWidget(c)
        s.addWidget(self.calcolo)
        pulsanti = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        pulsanti.button(QDialogButtonBox.Ok).setText(_("Usa questo valore"))
        pulsanti.button(QDialogButtonBox.Cancel).setText(_("Annulla"))
        pulsanti.accepted.connect(self._usa)
        pulsanti.rejected.connect(self.reject)
        s.addWidget(pulsanti)

    def _aggiorna(self):
        n, u = self.nacl.prova(), self.umidita.prova()
        if n is None or u is None:
            self.calcolo.setText("")
            return
        self.valore = crescita.wps(n, u)
        self.calcolo.setText(f"WPS = {numero(n)} × 100 / ({numero(n)} + {numero(u)}) = {numero(self.valore)} %")

    def _usa(self):
        try:
            leggi({"n": self.nacl, "u": self.umidita})
        except CampoNonValido:
            return
        self._aggiorna()
        self.accept()


# ---------------- una fase ----------------
class SchedaFase(QFrame):
    togli = Signal(object)
    cambiato = Signal()

    def __init__(self, numero_fase, togliibile):
        super().__init__(objectName="pannello")
        k = f"fase{numero_fase}_"
        s = QVBoxLayout(self)
        s.setContentsMargins(22, 14, 22, 16)
        s.setSpacing(10)
        testa = QHBoxLayout()
        testa.addWidget(etichetta(_("Fase {n}", n=numero_fase), "pannello_titolo"), 1)
        if togliibile:
            b = QPushButton(_("Togli questa fase"), objectName="piccolo")
            b.clicked.connect(lambda: self.togli.emit(self))
            testa.addWidget(b)
        s.addLayout(testa)
        g = QGridLayout()
        g.setHorizontalSpacing(20)
        g.setVerticalSpacing(12)
        for j in range(3):
            g.setColumnStretch(j, 1)
        ob = " · " + _("obbligatorio")
        self.durata = Campo(_("Durata"), aiuto=termine("durata"), esempio="24", chiave=k + "durata",
                            unita_scelte=[("ore", _("ore")), ("giorni", _("giorni"))],
                            nota=_("più di 0, fino a 365 giorni") + ob)
        self.temperatura = Campo(_("Temperatura"), "°C", LIMITI["temperatura"], aiuto=termine("temperatura"),
                                 esempio="4", chiave=k + "temperatura")
        self.ph = Campo("pH", "", LIMITI["ph"], aiuto=termine("ph"), esempio="5,5", chiave=k + "ph")
        self.usa = QComboBox(objectName=k + "usa")
        self.usa.addItem(_("aw (attività dell'acqua)"), "aw")
        self.usa.addItem(_("sale nella fase acquosa"), "sale")
        self.aw = Campo("aw", "", LIMITI["aw"], aiuto=termine("aw"), esempio="0,97", chiave=k + "aw")
        self.sale = Campo(_("Sale nella fase acquosa"), "%", LIMITI["sale_fase_acquosa"], aiuto=termine("wps"),
                          esempio="3,5", chiave=k + "sale")
        self.calcola = QPushButton(_("Calcola da NaCl e umidità"), objectName="piccolo")
        self.calcola.setToolTip(termine("wps"))
        self.calcola.clicked.connect(self._calcolatrice)
        colonna_sale = QVBoxLayout()
        colonna_sale.setSpacing(4)
        colonna_sale.addWidget(self.sale)
        colonna_sale.addWidget(self.calcola, 0, Qt.AlignLeft)
        self.nitrito = Campo(_("Nitrito residuo"), "mg/kg", LIMITI["nitrito"], obbligatorio=False,
                             aiuto=termine("nitrito"), esempio="8", chiave=k + "nitrito")
        self.nitrato = Campo(_("Nitrato, solo informativo"), "mg/kg", (0, 10000), obbligatorio=False,
                             aiuto=termine("nitrato"), esempio="100", chiave=k + "nitrato")
        g.addWidget(self.durata, 0, 0)
        g.addWidget(self.temperatura, 0, 1)
        g.addWidget(self.ph, 0, 2)
        g.addWidget(blocco(_("Il sale: che cosa conosci?"), self.usa, _("scegli uno dei due") + ob,
                           _("aw OPPURE sale nella fase acquosa, mai entrambi: sono la stessa informazione.")), 1, 0,
                    Qt.AlignTop)
        g.addWidget(self.aw, 1, 1, Qt.AlignTop)
        g.addLayout(colonna_sale, 1, 2)
        g.addWidget(self.nitrito, 2, 0, Qt.AlignTop)
        g.addWidget(self.nitrato, 2, 1, Qt.AlignTop)
        s.addLayout(g)
        self.altri = Apribile(_("Altri ingredienti (facoltativi): acidi, CO2, fenoli"), termine("acidi"))
        ga = QGridLayout()
        ga.setHorizontalSpacing(20)
        ga.setVerticalSpacing(10)
        self.acidi = {}
        for i, a in enumerate(ACIDI):
            self.acidi[a] = Campo(_(NOMI_ACIDI[a]), "ppm", (0, LIMITI["acido"][1]), obbligatorio=False,
                                  aiuto=termine("acidi"), chiave=k + a)
            ga.addWidget(self.acidi[a], i // 3, i % 3, Qt.AlignTop)
        self.co2 = Campo("CO2", "%", LIMITI["co2"], obbligatorio=False, aiuto=termine("co2"), chiave=k + "co2")
        self.fenoli = Campo(_("Fenoli del fumo"), "ppm", LIMITI["fenoli"], obbligatorio=False, aiuto=termine("fenoli"),
                            chiave=k + "fenoli")
        ga.addWidget(self.co2, 2, 0, Qt.AlignTop)
        ga.addWidget(self.fenoli, 2, 1, Qt.AlignTop)
        for j in range(3):
            ga.setColumnStretch(j, 1)
        self.altri.corpo.addLayout(ga)
        s.addWidget(self.altri)
        self.usa.currentIndexChanged.connect(self._sale_o_aw)
        for c in self.findChildren(Campo):
            c.cambiato.connect(self.cambiato)
        self._sale_o_aw()

    def _sale_o_aw(self, *_x):
        con_aw = self.usa.currentData() == "aw"
        self.aw.setEnabled(con_aw)
        self.sale.setEnabled(not con_aw)
        self.calcola.setEnabled(not con_aw)
        for campo, acceso in ((self.aw, con_aw), (self.sale, not con_aw)):
            campo.nota.setText(campo.testo_nota() if acceso else _("non usato: hai scelto l'altro valore"))

    def _calcolatrice(self):
        d = DialogoWps(self)
        if d.exec() and d.valore is not None:
            self.sale.imposta(round(d.valore, 2))

    def ore(self):
        """Durata in ore (None se non valida): per il totale scritto dal vivo."""
        v = self.durata.prova()
        return None if v is None else v * (24.0 if self.durata.unita_scelta() == "giorni" else 1.0)

    def fase(self):
        """La fase per il core (crescita.Fase). CampoNonValido se un campo è sbagliato (tutti segnati)."""
        con_aw = self.usa.currentData() == "aw"
        campi = {"durata": self.durata, "temperatura": self.temperatura, "ph": self.ph,
                 "nitrito": self.nitrito, "nitrato": self.nitrato, "co2": self.co2, "fenoli": self.fenoli}
        campi.update({"aw": self.aw} if con_aw else {"sale": self.sale})
        campi.update(self.acidi)
        v = leggi(campi)
        ore = v["durata"] * (24.0 if self.durata.unita_scelta() == "giorni" else 1.0)
        if not 0 < ore <= LIMITI["ore"][1]:
            self.durata.segnala(_("Fuori dal campo ammesso: più di 0, fino a 365 giorni."))
        return crescita.Fase(ore=ore, temperatura=v["temperatura"], ph=v["ph"], aw=v.get("aw"),
                             sale_fase_acquosa=v.get("sale"), nitrito=v["nitrito"] or 0.0,
                             acidi={a: v[a] for a in ACIDI if v[a]}, fenoli=v["fenoli"] or 0.0, co2=v["co2"] or 0.0)

    def carica(self, f):
        self.durata.imposta(f["durata"])
        self.durata.scegli_unita(f["unita"])
        self.temperatura.imposta(f["temperatura"])
        self.ph.imposta(f["ph"])
        self.usa.setCurrentIndex(0 if f.get("aw") is not None else 1)
        self.aw.imposta(f.get("aw"))
        self.sale.imposta(f.get("sale"))
        self.nitrito.imposta(f.get("nitrito") or None)
        for c in [self.nitrato, self.co2, self.fenoli, *self.acidi.values()]:
            c.imposta(None)


# ---------------- tutte le fasi ----------------
class EditorFasi(QWidget):
    """Le fasi una sotto l'altra, "Aggiungi una fase", il totale e il file del data logger."""
    cambiato = Signal()

    def __init__(self):
        super().__init__()
        s = QVBoxLayout(self)
        s.setContentsMargins(0, 0, 0, 0)
        s.setSpacing(14)
        self.zona = QVBoxLayout()
        self.zona.setSpacing(14)
        s.addLayout(self.zona)
        riga = QHBoxLayout()
        self.aggiungi = QPushButton(_("+ Aggiungi una fase"), objectName="secondario")
        self.aggiungi.clicked.connect(lambda: self._nuova())
        riga.addWidget(self.aggiungi)
        riga.addStretch(1)
        s.addLayout(riga)
        self.totale = etichetta("", "conversione")
        s.addWidget(self.totale)
        self.verifica = etichetta("", "nota")      # il modulo C ci scrive se le fasi arrivano al giorno dell'analisi
        s.addWidget(self.verifica)
        p, ps = pannello(_("Temperature dal data logger (facoltativo)"))
        ps.addWidget(etichetta(_("Un file CSV con due colonne: ore dall'inizio (da 0) e temperatura in °C.")))
        ps.addWidget(etichetta(_("Le temperature del file sostituiscono quelle delle fasi. pH, aw e il resto restano "
                                 "quelli delle fasi.")))
        r = QHBoxLayout()
        self.importa = QPushButton(_("Importa il file CSV"), objectName="secondario")
        self.importa.clicked.connect(self._importa)
        self.togli_csv = QPushButton(_("Togli il data logger"), objectName="secondario")
        self.togli_csv.clicked.connect(lambda: self._usa_punti(None, ""))
        r.addWidget(self.importa)
        r.addWidget(self.togli_csv)
        r.addStretch(1)
        ps.addLayout(r)
        self.stato_csv = QVBoxLayout()
        ps.addLayout(self.stato_csv)
        s.addWidget(p)
        self.schede, self.punti, self.file_csv = [], None, ""
        self._nuova()
        self._usa_punti(None, "")

    def _nuova(self, n=None):
        scheda = SchedaFase(len(self.schede) + 1, togliibile=len(self.schede) > 0)
        scheda.cambiato.connect(self._cambiato)
        scheda.togli.connect(self._togli)
        self.schede.append(scheda)
        self.zona.addWidget(scheda)
        self._cambiato()
        return scheda

    def _togli(self, scheda):
        """Toglie una fase e rinumera le altre (si rifanno, con gli stessi valori)."""
        i = self.schede.index(scheda)
        valori = [self._valori(s, j + 1) for j, s in enumerate(self.schede) if j != i]
        self.imposta_n(len(valori))
        for j, v in enumerate(valori):
            rimetti(self.schede[j], {f"fase{j + 1}_{k}": x for k, x in v.items()})
        self._cambiato()

    @staticmethod
    def _valori(scheda, n):
        prefisso = f"fase{n}_"
        return {k[len(prefisso):]: v for k, v in raccogli(scheda).items() if k.startswith(prefisso)}

    def imposta_n(self, n):
        for s in self.schede:
            s.hide()
            s.deleteLater()
        self.schede = []
        for _i in range(max(1, n)):
            self._nuova()

    def carica(self, fasi):
        self.imposta_n(len(fasi))
        for s, f in zip(self.schede, fasi):
            s.carica(f)
        self._usa_punti(None, "")

    def _cambiato(self, *_x):
        ore = [s.ore() for s in self.schede]
        if None in ore:
            self.totale.setText("")
        else:
            self.totale.setText(_("Totale delle fasi: {g} giorni ({h} ore).", g=numero(sum(ore) / 24, 2),
                                  h=numero(sum(ore), 1)))
        self.cambiato.emit()

    def ore_totali(self):
        ore = [s.ore() for s in self.schede]
        return None if None in ore else sum(ore)

    def fasi(self, con_logger=True):
        """Le fasi per il core; con il data logger, le temperature del file. CampoNonValido se c'è un errore."""
        fasi, errore = [], False
        for s in self.schede:
            try:
                fasi.append(s.fase())
            except CampoNonValido:
                errore = True
        if errore:
            raise CampoNonValido(_("Controlla i campi segnati in rosso."))
        if con_logger and self.punti:
            fasi = crescita.applica_temperature(fasi, self.punti)
        return fasi

    def nitrati(self):
        """Il nitrato scritto (solo informativo) per fase: [(n, mg/kg)]."""
        return [(i + 1, s.nitrato.prova()) for i, s in enumerate(self.schede) if s.nitrato.prova() is not None]

    # ---------------- data logger ----------------
    def _importa(self):
        percorso, _f = QFileDialog.getOpenFileName(self, _("Scegli il file CSV del data logger"), "",
                                                   _("File CSV (*.csv *.txt)"))
        if not percorso:
            return
        try:
            punti = crescita.leggi_csv_temperature(percorso)
        except ValueError as e:
            self._usa_punti(None, "", errore=testi.errore(e))
            return
        except (OSError, UnicodeDecodeError) as e:
            self._usa_punti(None, "", errore=_("Non riesco a leggere il file: {e}", e=str(e)))
            return
        self._usa_punti(punti, percorso)

    def _usa_punti(self, punti, percorso, errore=""):
        self.punti, self.file_csv = punti, percorso
        svuota(self.stato_csv)
        if errore:
            self.stato_csv.addWidget(riquadro(_("File non usato."), errore, "errore"))
        elif punti:
            t = [x for _o, x in punti]
            self.stato_csv.addWidget(riquadro(
                _("Data logger in uso: {n} letture.", n=len(punti)),
                _("Da {a} a {b} °C, per {g} giorni. Le temperature delle fasi non si usano.",
                  a=numero(min(t), 1), b=numero(max(t), 1), g=numero(punti[-1][0] / 24, 1)), "info"))
        self.togli_csv.setEnabled(bool(punti))
        self.cambiato.emit()


# ---------------- batteri lattici ----------------
class PannelloLab(QWidget):
    def __init__(self):
        super().__init__()
        s = QVBoxLayout(self)
        s.setContentsMargins(0, 0, 0, 0)
        s.setSpacing(14)
        s.addWidget(etichetta(_("I batteri lattici (LAB) fanno la fermentazione.")))
        s.addWidget(etichetta(_("Quando arrivano al loro massimo, Listeria smette di crescere (effetto Jameson).")))
        s.addWidget(etichetta(_("Se li conosci, la stima è più realistica. Se lasci vuoto, il calcolo è senza LAB.")))
        p, ps = pannello()
        self.lab0 = Campo(_("Batteri lattici al giorno 0"), "ufc/g", (1, MAX_UFC), obbligatorio=False,
                          aiuto=termine("lab"), esempio="10.000", chiave="lab0")
        ps.addWidget(self.lab0)
        ps.addWidget(etichetta(_("C'è uno starter (batteri lattici aggiunti)?"), "etichetta_campo"))
        r = QHBoxLayout()
        self.starter_si = QRadioButton(_("Sì, con starter"), objectName="starter_si")
        self.starter_no = QRadioButton(_("No, fermentazione spontanea"), objectName="starter_no")
        self.starter_no.setChecked(True)
        gruppo = QButtonGroup(self)
        for b in (self.starter_si, self.starter_no):
            b.setToolTip(termine("starter"))
            gruppo.addButton(b)
            r.addWidget(b)
        r.addStretch(1)
        ps.addLayout(r)
        s.addWidget(p)
        aiuto = riquadro(_("Valori tipici all'insacco (solo come orientamento)"), "", "info")
        for riga in (_("Con uno starter: di solito da 1.000.000 a 10.000.000 ufc/g."),
                     _("Fermentazione spontanea: di solito da 1.000 a 100.000 ufc/g."),
                     _("Meglio una conta in piastra del tuo prodotto (per esempio MRS).")):
            aiuto.layout().addWidget(etichetta(riga))
        s.addWidget(aiuto)
        for w in self.findChildren(QLabel):
            if not w.toolTip():
                w.setToolTip(termine("jameson"))

    def carica(self, p):
        self.lab0.imposta(p.get("lab0"))
        (self.starter_si if p.get("starter") else self.starter_no).setChecked(True)

    def valore(self):
        return self.lab0.valore()


# ---------------- opzioni del calcolo ----------------
class PannelloOpzioni(QWidget):
    """Modello, incertezze e Monte Carlo. retro=True per il modulo C (incertezza di misura), False per il B."""
    def __init__(self, retro):
        super().__init__()
        self.retro = retro
        s = QVBoxLayout(self)
        s.setContentsMargins(0, 0, 0, 0)
        s.setSpacing(14)
        s.addWidget(etichetta(_("Modello di crescita"), "sottotitolo"))
        gruppo = QButtonGroup(self)
        self.fssp = Scelta(_("FSSP (Mejlholm e Dalgaard)"), _("Con i batteri lattici (effetto Jameson). Provato uguale "
                                                              "a FSSP 4.0 in 23 casi su 23."), gruppo, consigliato=True)
        self.baranyi = Scelta(_("Baranyi e Roberts"), _("Modello classico, senza batteri lattici."), gruppo)
        self.fssp.pulsante.setObjectName("modello_fssp")
        self.baranyi.pulsante.setObjectName("modello_baranyi")
        self.fssp.setToolTip(termine("fssp"))
        self.baranyi.setToolTip(termine("baranyi"))
        self.fssp.pulsante.setChecked(True)
        s.addWidget(self.fssp)
        s.addWidget(self.baranyi)
        s.addWidget(etichetta(_("Incertezze"), "sottotitolo"))
        p, ps = pannello()
        g = QGridLayout()
        g.setHorizontalSpacing(20)
        g.setVerticalSpacing(12)
        if retro:
            self.u = Campo(_("Incertezza di misura"), "log10", (0, 3), aiuto=termine("incertezza"), esempio="0,5",
                           chiave="u_misura")
            self.u.imposta(incertezza_misura())
            g.addWidget(self.u, 0, 0, Qt.AlignTop)
        else:
            self.sd_n0 = Campo(_("Variabilità di Listeria all'inizio, sd"), "log10", (0, 3), aiuto=_(
                "Quanto varia la Listeria iniziale da un pezzo all'altro (deviazione standard, in log10).\n0 = tutti uguali."),
                esempio="0,5", chiave="sd_n0")
            self.sd_n0.imposta(0.0)
            g.addWidget(self.sd_n0, 0, 0, Qt.AlignTop)
        self.sd_t = Campo(_("Variabilità della temperatura, sd"), "°C", (0, 10), aiuto=termine("sd_t"), esempio="1",
                          chiave="sd_t")
        self.sd_t.imposta(0.0)
        g.addWidget(self.sd_t, 0, 1, Qt.AlignTop)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        ps.addLayout(g)
        if not retro:
            self.lag = QCheckBox(_("Includi la fase di adattamento (lag)"), objectName="lag")
            self.lag.setToolTip(termine("lag"))
            ps.addWidget(self.lag)
        s.addWidget(p)
        self.avanzate = Apribile(_("Opzioni avanzate"), termine("mc"))
        pa, pas = pannello()
        ga = QGridLayout()
        ga.setHorizontalSpacing(20)
        ga.setVerticalSpacing(12)
        self.cv_mu = Campo(_("Incertezza di μmax (CV)"), "", (0, 2), obbligatorio=False, aiuto=termine("cv_mu"),
                           esempio="0,2", chiave="cv_mu")
        self.n_mc = Campo(_("Simulazioni Monte Carlo (n)"), "", (100, 20000), aiuto=termine("mc"), esempio="2000",
                          chiave="n_mc", intero=True)
        self.n_mc.imposta(2000 if retro else 1000)
        self.seme = Campo(_("Seme (seed)"), "", (0, 2 ** 31 - 1), aiuto=termine("seme"), esempio="20261103",
                          chiave="seme", intero=True)
        self.seme.imposta(20261103)
        ga.addWidget(self.cv_mu, 0, 0, Qt.AlignTop)
        ga.addWidget(self.n_mc, 0, 1, Qt.AlignTop)
        ga.addWidget(self.seme, 0, 2, Qt.AlignTop)
        for j in range(3):
            ga.setColumnStretch(j, 1)
        pas.addLayout(ga)
        pas.addWidget(etichetta(_("L'incertezza di μmax è spenta se il campo è vuoto. Mettila solo se hai una fonte."),
                                "nota"))
        self.avanzate.corpo.addWidget(pa)
        s.addWidget(self.avanzate)

    def modello(self):
        return "baranyi" if self.baranyi.pulsante.isChecked() else "fssp"

    def valori(self):
        campi = {"sd_t": self.sd_t, "cv_mu": self.cv_mu, "n_mc": self.n_mc, "seme": self.seme}
        campi.update({"u": self.u} if self.retro else {"sd_n0": self.sd_n0})
        v = leggi(campi)
        v["modello"] = self.modello()
        v["lag"] = (not self.retro) and self.lag.isChecked()
        return v
