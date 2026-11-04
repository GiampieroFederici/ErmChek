"""La finestra di ErmChek (come quella di profilemetananni): testata con logo e lingua, percorso a passi a sinistra,
pagina al centro, barra delle azioni in basso con un solo pulsante principale. Prima di tutto l'avvio con il logo.
Tastiera: Tab segue l'ordine di Qt, Invio preme il pulsante che ha il fuoco.
"""
import sys

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from ermchek import __version__, lingua
from ermchek.gui.base import Contesto, etichetta, ricolora, svuota
from ermchek.gui.home import PaginaHome
from ermchek.gui.impostazioni import PaginaImpostazioni
from ermchek.gui.info import PaginaInfo
from ermchek.gui.modulo_a import ModuloA
from ermchek.gui.modulo_b import ModuloB
from ermchek.gui.modulo_c import ModuloC
from ermchek.lingua import _
from ermchek.percorsi import risorsa

PAGINE = {"home": PaginaHome, "C": ModuloC, "B": ModuloB, "A": ModuloA, "impostazioni": PaginaImpostazioni,
          "info": PaginaInfo}
LOGO = risorsa("assets", "logo", "ErmChek_logo.png")
ICONA = risorsa("assets", "logo", "ErmChek_icona.ico")
LARGA = 1100                          # sotto questa larghezza: percorso più stretto e margini minori
PERCORSO_LARGO, PERCORSO_STRETTO = 310, 260


def movimento_ridotto():
    """True se in Windows è spento "Mostra animazioni" (come in profilemetananni)."""
    if sys.platform != "win32":
        return False
    import ctypes
    acceso = ctypes.c_int(1)
    ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(acceso), 0)   # SPI_GETCLIENTAREAANIMATION
    return not acceso.value


def misure(libero):
    """Misura iniziale e minima, mai più grandi dello spazio libero dello schermo (40 px per la barra del titolo)."""
    w, h = libero.width(), libero.height() - 40
    return QSize(min(1366, w), min(860, h)), QSize(min(1000, w), min(640, h))


class Finestra(QMainWindow):
    def __init__(self, avvio_ms=1800):
        super().__init__()
        self.avvio_ms = avvio_ms
        self.setWindowTitle("ErmChek")
        self.setWindowIcon(QIcon(str(ICONA)))
        grande, minima = misure(QGuiApplication.primaryScreen().availableGeometry().size())
        self.resize(grande)
        self.setMinimumSize(minima)
        self.contesto = Contesto()
        self.pagine = {}
        self.attuale = "home"
        self.fuori = QStackedWidget()
        self.setCentralWidget(self.fuori)
        self.fuori.addWidget(self._avvio())
        self.fuori.addWidget(self._area())

    # ---------------- avvio ----------------
    def _avvio(self):
        w = QWidget(objectName="avvio")
        s = QVBoxLayout(w)
        s.setAlignment(Qt.AlignCenter)
        s.setSpacing(18)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)).scaledToWidth(640, Qt.SmoothTransformation))
        logo.setAccessibleName("ErmChek")
        s.addWidget(logo, 0, Qt.AlignHCenter)
        for testo in (_("Listeria monocytogenes negli alimenti pronti"), _("Versione {v}", v=__version__)):
            e = QLabel(testo)
            e.setAlignment(Qt.AlignCenter)
            s.addWidget(e)
        return w

    def avvia(self):
        self.fuori.setCurrentIndex(0)
        QTimer.singleShot(self.avvio_ms, self._pronto)

    def _pronto(self):
        self.fuori.setCurrentIndex(1)
        self.vai(self.attuale)

    # ---------------- finestra ----------------
    def _area(self):
        w = QWidget(objectName="area")
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(0)
        g.addWidget(self._testata(), 0, 0, 1, 2)
        g.addWidget(self._percorso(), 1, 0)
        self.pila = QStackedWidget()
        for chiave, classe in PAGINE.items():
            p = classe(self.contesto)
            p.vai.connect(self.vai)
            p.azioni_cambiate.connect(self._azioni)
            p.lingua_scelta.connect(self.cambia_lingua)
            p.salvate.connect(lambda: [q.impostazioni_cambiate() for q in self.pagine.values()])
            self.pagine[chiave] = p
            self.pila.addWidget(p)
        g.addWidget(self.pila, 1, 1)
        g.addWidget(self._barra(), 2, 0, 1, 2)
        g.setColumnStretch(1, 1)
        g.setRowStretch(1, 1)
        return w

    def _testata(self):
        t = QFrame(objectName="testata")
        s = QHBoxLayout(t)
        s.setContentsMargins(20, 8, 20, 8)
        s.setSpacing(14)
        logo = QPushButton(objectName="link")
        logo.setIcon(QIcon(QPixmap(str(LOGO)).scaledToHeight(84, Qt.SmoothTransformation)))
        logo.setIconSize(QSize(126, 42))
        logo.setFocusPolicy(Qt.NoFocus)   # c'è già "Inizio" fra i collegamenti: niente bordo del fuoco all'avvio
        logo.setAccessibleName(_("ErmChek: torna all'inizio"))
        logo.setToolTip(logo.accessibleName())
        logo.clicked.connect(lambda: self.vai("home"))
        s.addWidget(logo)
        s.addWidget(QLabel(f"v{__version__}", objectName="versione"))
        s.addStretch(1)
        for chiave, testo in (("home", _("Inizio")), ("impostazioni", _("Impostazioni")), ("info", _("Info"))):
            b = QPushButton(testo, objectName="link")
            b.clicked.connect(lambda _x=False, c=chiave: self.vai(c))
            s.addWidget(b)
        altra = "en" if lingua.attuale() == "it" else "it"
        self.pulsante_lingua = QPushButton(lingua.LINGUE[altra], objectName="link")
        self.pulsante_lingua.setAccessibleName(_("Cambia lingua: {lingua}", lingua=lingua.LINGUE[altra]))
        self.pulsante_lingua.setToolTip(self.pulsante_lingua.accessibleName())
        self.pulsante_lingua.clicked.connect(lambda: self.cambia_lingua(altra))
        s.addWidget(self.pulsante_lingua)
        return t

    def _percorso(self):
        p = self.zona_percorso = QFrame(objectName="percorso")
        p.setFixedWidth(PERCORSO_LARGO)
        self.voci = QVBoxLayout(p)
        self.voci.setContentsMargins(16, 24, 16, 24)
        self.voci.setSpacing(4)
        return p

    def _disegna_percorso(self):
        svuota(self.voci)
        pagina = self.pagine[self.attuale]
        b = QPushButton("⌂   " + _("Inizio"), objectName="passo")
        b.setProperty("stato", "attivo" if self.attuale == "home" else "")
        b.clicked.connect(lambda: self.vai("home"))
        self.voci.addWidget(b)
        if pagina.nomi_passi:
            self.voci.addSpacing(14)
            self.voci.addWidget(QFrame(objectName="separatore"))
            self.voci.addSpacing(10)
            self.voci.addWidget(etichetta(pagina.titolo, "percorso_titolo"))
            self.voci.addSpacing(4)
            for i, nome in enumerate(pagina.nomi_passi):
                fatto = i in pagina.fatti and i != pagina.passo
                b = QPushButton(f"{'✓' if fatto else i + 1}   {_(nome)}", objectName="passo")
                b.setProperty("stato", "attivo" if i == pagina.passo else ("fatto" if fatto else ""))
                b.setAccessibleDescription(_("passo attuale") if i == pagina.passo else (_("fatto") if fatto else ""))
                b.setEnabled(not pagina.occupata)
                b.clicked.connect(lambda _x=False, j=i: pagina.salta(j))
                self.voci.addWidget(b)
        self.voci.addStretch(1)

    def _barra(self):
        b = QFrame(objectName="azioni")
        self.barra = QHBoxLayout(b)
        self.barra.setContentsMargins(24, 12, 24, 12)
        self.barra.setSpacing(16)
        self.aiuto = QLabel(objectName="aiuto")
        self.aiuto.setWordWrap(True)
        self.aiuto.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.barra.addWidget(self.aiuto, 1)
        self.secondari = []
        self.principale = QPushButton(objectName="principale")
        self.principale.clicked.connect(lambda: self.pagine[self.attuale].azione_principale())
        self.barra.addWidget(self.principale)
        return b

    # ---------------- navigazione ----------------
    def vai(self, chiave):
        self.attuale = chiave
        self.pila.setCurrentWidget(self.pagine[chiave])
        self.pagine[chiave].mostrata()
        self._adatta(self.width())
        self._azioni()

    def _azioni(self):
        p = self.pagine[self.attuale]
        self.principale.setText(p.testo_principale)
        self.principale.setVisible(bool(p.testo_principale))
        self.principale.setEnabled(p.principale_attivo)
        self.aiuto.setText(p.aiuto)
        self.aiuto.setProperty("livello", p.aiuto_livello)
        ricolora(self.aiuto)
        for b in self.secondari:
            b.hide()
            b.deleteLater()
        self.secondari = []
        for testo, funzione in p.secondari:
            b = QPushButton(testo, objectName="secondario")
            b.clicked.connect(funzione)
            b.setEnabled(not p.occupata)
            self.barra.insertWidget(self.barra.count() - 1, b)
            self.secondari.append(b)
        self._disegna_percorso()
        fuoco = self.focusWidget()   # i pulsanti dei passi si ridisegnano: il fuoco non deve cadere su "Inizio"
        if (fuoco is None or not fuoco.isVisible() or fuoco.objectName() in ("link", "passo"))                 and self.principale.isVisible() and self.principale.isEnabled():
            self.principale.setFocus(Qt.OtherFocusReason)

    def _adatta(self, larghezza):
        if not hasattr(self, "zona_percorso"):
            return
        stretta = larghezza < LARGA
        self.zona_percorso.setFixedWidth(PERCORSO_STRETTO if stretta else PERCORSO_LARGO)
        for p in self.pagine.values():
            p.adatta(stretta)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._adatta(evento.size().width())

    # ---------------- lingua ----------------
    def cambia_lingua(self, codice):
        """Rifà testata, percorso, pagine e barra nella nuova lingua, con i dati già scritti, e torna allo stesso
        passo. Non durante un calcolo."""
        if any(p.occupata for p in self.pagine.values()):
            self.aiuto.setText(_("Puoi cambiare lingua quando il calcolo è finito."))
            self.aiuto.setProperty("livello", "avviso")
            ricolora(self.aiuto)
            return False
        stati = {k: p.stato() for k, p in self.pagine.items()}
        lingua.imposta(codice)
        lingua.salva(codice)
        vecchia = self.fuori.widget(1)
        self.fuori.removeWidget(vecchia)
        vecchia.hide()
        vecchia.deleteLater()
        self.pagine, self.secondari = {}, []
        self.fuori.insertWidget(1, self._area())
        self.fuori.setCurrentIndex(1)
        for k in [k for k in self.pagine if k != "home"] + ["home"]:   # la pagina iniziale per ultima: il patogeno
            self.pagine[k].ripristina(stati[k])
        self.vai(self.attuale)
        self.pulsante_lingua.setFocus()
        return True

    # ---------------- tastiera e chiusura ----------------
    def keyPressEvent(self, evento):
        fuoco = self.focusWidget()
        if evento.key() in (Qt.Key_Return, Qt.Key_Enter) and isinstance(fuoco, QPushButton) and fuoco.isEnabled():
            fuoco.click()
            return
        super().keyPressEvent(evento)

    def closeEvent(self, evento):
        """Un calcolo ancora in corso finisce prima della chiusura (un filo non si interrompe a metà)."""
        for p in self.pagine.values():
            lavoro = getattr(p, "lavoro", None)
            if lavoro is not None and lavoro.isRunning():
                lavoro.wait()
        super().closeEvent(evento)
