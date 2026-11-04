"""Pezzi comuni dell'interfaccia (come app/pagine/base.py di profilemetananni).

Una pagina ha uno o più passi (procedura guidata: un passo per schermata). Ogni passo ha il suo corpo, che scorre.
La pagina dichiara la barra delle azioni: testo_principale, principale_attivo, aiuto (+ aiuto_livello), secondari;
dopo averli cambiati chiama self.azioni_cambiate.emit(). La finestra chiama mostrata() a ogni ingresso.
stato() e ripristina() conservano i dati scritti quando si cambia lingua (la finestra si rifà da capo).
"""
import math

from PySide6.QtCore import QPoint, QRect, QSettings, QSize, Qt, QThread, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel,
                               QLayout, QLineEdit, QProgressBar, QPushButton, QRadioButton, QScrollArea,
                               QSizePolicy,
                               QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ermchek import lingua, testi
from ermchek.lingua import N_, _

UNITA = (N_("ufc/g"), N_("giorni dal giorno 0"))   # unità tradotte dentro Campo
SUPERSCRITTI = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


# ---------------- impostazioni (QSettings "ErmChek") ----------------
def impostazioni():
    return QSettings("ErmChek", "app")


def peso_pezzo():
    """Peso del pezzo in grammi, scelto nelle Impostazioni (nessun valore predefinito: None)."""
    v = impostazioni().value("peso_pezzo_g", "")
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if 0 < v <= 1e6 else None


def incertezza_misura():
    """Incertezza di misura predefinita (log10): 0,5 se non scelta (guida EURL, EN ISO 11290-2)."""
    try:
        v = float(impostazioni().value("incertezza_log", 0.5))
    except (TypeError, ValueError):
        return 0.5
    return v if 0 <= v <= 3 else 0.5


# ---------------- numeri ----------------
def cifre2(x):
    """Due cifre significative nella lingua scelta (come nel PDF): 4,0487 -> "4"; 1.687 -> "1.700"; 6,7e-5 -> "6,7 × 10⁻⁵"."""
    if x is None or not math.isfinite(x):
        return "-"
    if x == 0:
        return "0"
    esponente = math.floor(math.log10(abs(x)))
    if -2 <= esponente < 6:
        cifre = 1 - esponente
        testo = lingua.separatori(f"{round(x, cifre):,.{max(0, cifre)}f}")
        return testo.rstrip("0").rstrip(lingua.decimale()) if lingua.decimale() in testo else testo
    mantissa = round(x / 10 ** esponente, 1)
    if mantissa >= 10:
        mantissa, esponente = mantissa / 10, esponente + 1
    m = lingua.virgola(f"{mantissa:.1f}").rstrip("0").rstrip(lingua.decimale())
    return f"{m} × 10{str(esponente).translate(SUPERSCRITTI)}"


def numero(x, cifre=2):
    """Numero con al massimo `cifre` decimali, separatori della lingua scelta (60000 -> "60.000")."""
    testo = lingua.separatori(f"{x:,.{cifre}f}")
    return testo.rstrip("0").rstrip(lingua.decimale()) if lingua.decimale() in testo else testo


def fisso(x, cifre=2):
    """Numero con sempre `cifre` decimali (colonne di tabella allineate): 9.1 -> "9,10"."""
    return lingua.separatori(f"{x:,.{cifre}f}")


def per_campo(x):
    """Un numero da scrivere in un campo modificabile: senza migliaia, decimali della lingua scelta."""
    return lingua.virgola(f"{x:.10g}") if "e" not in f"{x:.10g}" else f"{x:.6g}"


def percento(p):
    """Probabilità in %; sotto lo 0,1 % si dice "meno di 0,1 %" (mai un falso "0 %")."""
    simbolo = " %" if lingua.attuale() == "it" else "%"
    if p < 0.001:   # anche 0: un exp() troppo piccolo per il computer, non una probabilità nulla
        return _("meno di {x}", x=numero(0.1, 1)) + simbolo
    if p > 0.999:
        return _("più di {x}", x=numero(99.9, 1)) + simbolo
    return numero(100 * p, 1) + simbolo


# ---------------- pezzi grafici ----------------
def etichetta(testo, nome=None, ricco=False):
    """Testo che va a capo da solo; nome = objectName per lo stile (titolo, sottotitolo, nota)."""
    e = QLabel(testo)
    e.setWordWrap(True)
    e.setTextFormat(Qt.RichText if ricco else Qt.PlainText)
    e.setTextInteractionFlags(Qt.TextSelectableByMouse)
    if nome:
        e.setObjectName(nome)
    return e


def riquadro(titolo, testo, livello="info"):
    """Avviso, errore o informazione con la barra colorata a sinistra (livello: info, avviso, errore, neutro)."""
    r = QFrame(objectName="riquadro")
    r.setProperty("livello", livello)
    s = QVBoxLayout(r)
    s.setContentsMargins(18, 12, 18, 12)
    s.setSpacing(4)
    if titolo:
        s.addWidget(etichetta(titolo, "riquadro_titolo"))
    if testo:
        s.addWidget(etichetta(testo))
    return r


def risposta(livello, grande, righe, spiega):
    """La risposta in alto: riquadro grande colorato (verde, ambra, rosso) con il testo esplicito del livello."""
    r = QFrame(objectName="risposta")
    r.setProperty("livello", livello)
    s = QVBoxLayout(r)
    s.setContentsMargins(26, 20, 26, 20)
    s.setSpacing(8)
    s.addWidget(etichetta(grande, "risposta_grande"))
    for riga in righe:
        s.addWidget(etichetta(riga, "risposta_media"))
    if spiega:
        s.addSpacing(4)
        s.addWidget(etichetta(spiega, "risposta_livello"))
    r.setAccessibleName(" ".join([grande, *righe, spiega or ""]))
    return r


def pannello(titolo=None):
    """Riquadro bianco con il bordo grigio; titolo facoltativo in grassetto."""
    p = QFrame(objectName="pannello")
    s = QVBoxLayout(p)
    s.setContentsMargins(22, 16, 22, 18)
    s.setSpacing(10)
    if titolo:
        s.addWidget(etichetta(titolo, "pannello_titolo"))
    return p, s


def con_suggerimento(w, testo):
    w.setToolTip(testo)
    return w


def ricolora(w):
    w.style().unpolish(w)
    w.style().polish(w)


def svuota(disposizione):
    """Toglie i widget di un layout (per ridisegnare una zona), anche quelli dei layout dentro."""
    while disposizione.count():
        voce = disposizione.takeAt(0)
        w, dentro = voce.widget(), voce.layout()
        if w:
            w.hide()
            w.deleteLater()
        elif dentro is not None:
            svuota(dentro)
            dentro.deleteLater()


class Apribile(QWidget):
    """Sezione che si apre e si chiude ("Altri ingredienti", "Opzioni avanzate"): chiusa all'inizio."""
    def __init__(self, titolo, suggerimento=""):
        super().__init__()
        s = QVBoxLayout(self)
        s.setContentsMargins(0, 0, 0, 0)
        s.setSpacing(6)
        self.titolo = titolo
        self.pulsante = QPushButton(objectName="apri")
        self.pulsante.setToolTip(suggerimento)
        self.pulsante.clicked.connect(lambda: self.apri(not self.dentro.isVisible()))
        self.dentro = QWidget(objectName="trasparente")
        self.corpo = QVBoxLayout(self.dentro)
        self.corpo.setContentsMargins(0, 4, 0, 0)
        self.corpo.setSpacing(10)
        s.addWidget(self.pulsante)
        s.addWidget(self.dentro)
        self.apri(False)

    def apri(self, si):
        self.dentro.setVisible(si)
        self.pulsante.setText(("▾  " if si else "▸  ") + self.titolo)


class Flusso(QLayout):
    """Una fila di pulsanti che va a capo quando non ci sta, come il testo (da profilemetananni)."""
    def __init__(self, spazio=12):
        super().__init__()
        self._voci, self._spazio = [], spazio
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, voce):
        self._voci.append(voce)

    def count(self):
        return len(self._voci)

    def itemAt(self, i):
        return self._voci[i] if 0 <= i < len(self._voci) else None

    def takeAt(self, i):
        return self._voci.pop(i) if 0 <= i < len(self._voci) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, larghezza):
        return self._disponi(QRect(0, 0, larghezza, 0), False)

    def setGeometry(self, rettangolo):
        super().setGeometry(rettangolo)
        self._disponi(rettangolo, True)

    def sizeHint(self):
        visibili = [v.sizeHint() for v in self._voci if not v.isEmpty()]
        return QSize(sum(d.width() for d in visibili) + self._spazio * max(0, len(visibili) - 1),
                     max((d.height() for d in visibili), default=0))

    def minimumSize(self):
        s = QSize()
        for v in self._voci:
            if not v.isEmpty():
                s = s.expandedTo(v.minimumSize())
        return s

    def _disponi(self, r, sposta):
        x, y, alto = r.x(), r.y(), 0
        for v in self._voci:
            if v.isEmpty():
                continue
            d = v.sizeHint()
            if x > r.x() and x + d.width() > r.right() + 1:
                x, y, alto = r.x(), y + alto + self._spazio, 0
            if sposta:
                v.setGeometry(QRect(QPoint(x, y), d))
            x += d.width() + self._spazio
            alto = max(alto, d.height())
        return y + alto - r.y()


class Scelta(QFrame):
    """Scheda grande con un pulsante tondo, il titolo e una frase che dice cosa fa; si sceglie con un clic."""
    scelta = Signal()

    def __init__(self, titolo, spiega, gruppo, consigliato=False, lettera=None):
        super().__init__(objectName="scelta")
        s = QHBoxLayout(self)
        s.setContentsMargins(18, 14, 18, 14)
        s.setSpacing(14)
        if lettera:
            s.addWidget(QLabel(lettera, objectName="lettera"), 0, Qt.AlignTop)
        colonna = QVBoxLayout()
        riga = QHBoxLayout()
        self.pulsante = QRadioButton(titolo)
        self.pulsante.setStyleSheet("font-weight: bold;")
        gruppo.addButton(self.pulsante)
        riga.addWidget(self.pulsante)
        if consigliato:
            riga.addWidget(QLabel(_("consigliato"), objectName="consigliato"))
        riga.addStretch(1)
        colonna.addLayout(riga)
        self.spiega = etichetta(spiega)
        self.spiega.setContentsMargins(30, 0, 0, 0)
        colonna.addWidget(self.spiega)
        s.addLayout(colonna, 1)
        self.setToolTip(spiega)
        self.pulsante.toggled.connect(self._ridisegna)
        self._ridisegna()

    def mousePressEvent(self, evento):
        if self.pulsante.isEnabled():
            self.pulsante.setChecked(True)
        super().mousePressEvent(evento)

    def _ridisegna(self, *_x):
        self.setProperty("scelto", self.pulsante.isChecked())
        self.setProperty("spento", not self.pulsante.isEnabled())
        ricolora(self)
        if self.pulsante.isChecked():
            self.scelta.emit()

    def setEnabled(self, si):
        self.pulsante.setEnabled(si)
        self._ridisegna()


# ---------------- campi numerici ----------------
class CampoNonValido(Exception):
    pass


class Campo(QWidget):
    """Un campo numerico: etichetta con l'unità, campo, nota con il campo ammesso e "obbligatorio/facoltativo",
    errore in linea sotto. Il suggerimento (tooltip) spiega il termine. unita_scelte: menu dell'unità a destra."""
    cambiato = Signal()

    def __init__(self, nome, unita="", limiti=None, obbligatorio=True, aiuto="", esempio="", chiave=None,
                 unita_scelte=None, intero=False, nota=None):
        super().__init__()
        unita = _(unita) if unita else ""     # "ufc/g" -> "CFU/g" in inglese
        self.nome, self.unita, self.limiti, self.obbligatorio, self.intero = nome, unita, limiti, obbligatorio, intero
        if chiave:
            self.setObjectName(chiave)
        s = QVBoxLayout(self)
        s.setContentsMargins(0, 0, 0, 0)
        s.setSpacing(3)
        testo = f"{nome} ({unita})" if unita and not unita_scelte else nome
        self.etichetta = etichetta(testo, "etichetta_campo")
        s.addWidget(self.etichetta)
        riga = QHBoxLayout()
        riga.setSpacing(8)
        self.edit = QLineEdit()
        if lingua.attuale() != "it":   # gli esempi sono scritti all'italiana: "3,5" -> "3.5", "4.000" -> "4,000"
            esempio = esempio.translate(str.maketrans(",.", ".,"))
        self.edit.setPlaceholderText(_("per esempio {x}", x=esempio) if esempio else "")
        self.edit.setAccessibleName(testo)
        self.edit.textEdited.connect(self._modificato)
        riga.addWidget(self.edit, 1)
        self.menu_unita = None
        if unita_scelte:
            self.menu_unita = QComboBox(objectName=f"{chiave}_unita" if chiave else "")
            for codice, voce in unita_scelte:
                self.menu_unita.addItem(voce, codice)
            self.menu_unita.setAccessibleName(_("Unità di {campo}", campo=nome))
            self.menu_unita.currentIndexChanged.connect(lambda _i: self.cambiato.emit())
            riga.addWidget(self.menu_unita)
        s.addLayout(riga)
        if nota is None:
            nota = self.testo_nota()
        self.nota = etichetta(nota, "nota_campo")
        s.addWidget(self.nota)
        self.errore = etichetta("", "errore_campo")
        self.errore.hide()
        s.addWidget(self.errore)
        suggerimento = "\n".join(t for t in (aiuto, nota) if t)
        for w in (self.etichetta, self.edit, self.nota):
            w.setToolTip(suggerimento)

    def testo_nota(self):
        stato = _("obbligatorio") if self.obbligatorio else _("facoltativo")
        if not self.limiti:
            return stato
        lo, hi = self.limiti
        return _("da {lo} a {hi}", lo=numero(lo, 4), hi=numero(hi, 4)) + " · " + stato

    def _modificato(self, *_x):
        self.pulisci()
        self.cambiato.emit()

    def pulisci(self):
        self.errore.hide()
        self.edit.setProperty("errore", False)
        ricolora(self.edit)

    def segnala(self, messaggio):
        self.errore.setText(messaggio)
        self.errore.show()
        self.edit.setProperty("errore", True)
        ricolora(self.edit)
        raise CampoNonValido(messaggio)

    def setEnabled(self, si):
        super().setEnabled(si)
        if not si:
            self.pulisci()

    def testo(self):
        return self.edit.text()

    def valore(self, silenzioso=False):
        """Il numero scritto (None se vuoto e facoltativo). CampoNonValido, con il messaggio sotto il campo, se non
        è un numero, se manca ed è obbligatorio o se è fuori dal campo ammesso. silenzioso: nessun segno rosso."""
        try:
            v = lingua.leggi_numero(self.edit.text())
        except ValueError:
            v = math.nan
        try:
            if v is not None and not math.isfinite(v):
                self.segnala(_("Scrivi un numero, per esempio {x}.", x=self.edit.placeholderText().split()[-1]
                               if self.edit.placeholderText() else "1"))
            if v is None:
                if self.obbligatorio:
                    self.segnala(_("Campo obbligatorio: scrivi un valore."))
                return None
            if self.intero and v != int(v):
                self.segnala(_("Scrivi un numero intero."))
            if self.limiti and not self.limiti[0] <= v <= self.limiti[1]:
                self.segnala(_("Fuori dal campo ammesso: da {lo} a {hi}.", lo=numero(self.limiti[0], 4),
                               hi=numero(self.limiti[1], 4)))
        except CampoNonValido:
            if silenzioso:
                self.pulisci()
            raise
        self.pulisci()
        return int(v) if self.intero else v

    def prova(self):
        """Il valore senza segnalare errori: None se vuoto o non valido (per i calcoli dal vivo)."""
        try:
            return self.valore(silenzioso=True)
        except CampoNonValido:
            return None

    def imposta(self, v):
        self.edit.setText("" if v is None else per_campo(v))
        self.pulisci()
        self.cambiato.emit()

    def unita_scelta(self):
        return self.menu_unita.currentData() if self.menu_unita else self.unita

    def scegli_unita(self, codice):
        if self.menu_unita:
            self.menu_unita.setCurrentIndex(max(0, self.menu_unita.findData(codice)))


def leggi(campi):
    """I valori di un dict di Campo: li controlla tutti (segna ogni errore) e poi, se ce n'è uno, CampoNonValido."""
    valori, sbagliati = {}, 0
    for chiave, c in campi.items():
        try:
            valori[chiave] = c.valore()
        except CampoNonValido:
            sbagliati += 1
    if sbagliati:
        raise CampoNonValido(_("Controlla i campi segnati in rosso."))
    return valori


def raccogli(radice):
    """I valori dei campi con un nome (objectName), per conservarli quando la finestra si rifà in un'altra lingua.
    I numeri si conservano come numeri (non come testo): "4.000" in italiano resta 4000 anche in inglese."""
    dati = {}
    for c in radice.findChildren(Campo):
        if c.objectName():
            try:
                dati[c.objectName()] = ("n", lingua.leggi_numero(c.testo()))
            except ValueError:
                dati[c.objectName()] = ("t", c.testo())
    for w in radice.findChildren(QComboBox):
        if w.objectName():
            dati[w.objectName()] = ("i", w.currentIndex())
    for w in radice.findChildren(QCheckBox) + radice.findChildren(QRadioButton):
        if w.objectName():
            dati[w.objectName()] = ("b", w.isChecked())
    for w in radice.findChildren(QLineEdit):
        if w.objectName() and not w.objectName().startswith("qt_"):
            dati[w.objectName()] = ("t", w.text())
    return dati


def rimetti(radice, dati):
    for c in radice.findChildren(Campo):
        tipo, v = dati.get(c.objectName(), (None, None))
        if tipo == "n":
            c.imposta(v)
        elif tipo == "t":
            c.edit.setText(v)
    for w in radice.findChildren(QComboBox):
        if w.objectName() in dati:
            w.setCurrentIndex(dati[w.objectName()][1])
    for w in radice.findChildren(QCheckBox) + radice.findChildren(QRadioButton):
        if w.objectName() in dati:
            w.setChecked(dati[w.objectName()][1])
    for w in radice.findChildren(QLineEdit):
        if w.objectName() in dati:
            w.setText(dati[w.objectName()][1])


# ---------------- tabelle ----------------
def tabella(intestazioni, righe, suggerimenti=None):
    """Tabella compatta di sola lettura, alta quanto le sue righe (niente barra di scorrimento interna)."""
    t = QTableWidget(len(righe), len(intestazioni))
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionMode(QAbstractItemView.NoSelection)
    t.setFocusPolicy(Qt.NoFocus)
    t.verticalHeader().hide()
    t.setWordWrap(True)
    for j, testo in enumerate(intestazioni):
        voce = QTableWidgetItem(testo)
        if suggerimenti and suggerimenti[j]:
            voce.setToolTip(suggerimenti[j])
        t.setHorizontalHeaderItem(j, voce)
    for i, riga in enumerate(righe):
        for j, testo in enumerate(riga):
            voce = QTableWidgetItem(str(testo))
            voce.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if j == 0 else Qt.AlignRight))
            t.setItem(i, j, voce)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    t.horizontalHeader().setDefaultAlignment(Qt.AlignCenter | Qt.TextWordWrap)
    t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.resizeRowsToContents()
    t.horizontalHeader().setMinimumHeight(58)
    alto = t.horizontalHeader().minimumHeight() + sum(t.rowHeight(i) for i in range(t.rowCount())) + 6
    t.setFixedHeight(alto)
    t.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return t


# ---------------- grafici (dal pacchetto dei report, etichette in inglese) ----------------
def grafico(nome, *argomenti, altezza=440):
    """Un grafico di ermchek.report.grafici dentro la pagina. Si importa qui (non in cima) perché il pacchetto dei
    report è separato: se manca o fallisce, al posto del grafico c'è un avviso e l'app non si ferma."""
    try:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from ermchek.report import grafici
        figura = getattr(grafici, nome)(*argomenti)
    except Exception as e:   # noqa: BLE001 (il grafico è facoltativo: l'app non deve fermarsi)
        return riquadro(_("Grafico non disponibile."), str(e), "neutro")
    tela = FigureCanvasQTAgg(figura)
    tela.setFixedHeight(altezza)
    tela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    tela.setAccessibleName(_("Grafico (testi in inglese)"))
    return tela


# ---------------- calcolo in un altro filo ----------------
class Lavoro(QThread):
    """Un calcolo del core fuori dal filo dell'interfaccia: la finestra non si blocca mai.
    fatto(risultato) o fallito(frase per l'utente); ValueError del core -> testi.errore."""
    fatto = Signal(object)
    fallito = Signal(str)

    def __init__(self, funzione, parent=None):
        super().__init__(parent)
        self.funzione = funzione

    def run(self):
        try:
            self.fatto.emit(self.funzione())
        except ValueError as e:
            self.fallito.emit(testi.errore(e))
        except Exception as e:   # noqa: BLE001 (mai un arresto: si spiega l'errore)
            self.fallito.emit(_("Errore inatteso nel calcolo: {e}", e=str(e)))


# ---------------- pagine ----------------
class Corpo(QVBoxLayout):
    """Il corpo di un passo: tutto in alto, alto quanto serve con i testi che vanno a capo (da profilemetananni)."""
    def setGeometry(self, r):
        alto = self.heightForWidth(r.width()) if self.hasHeightForWidth() else self.sizeHint().height()
        super().setGeometry(QRect(r.x(), r.y(), r.width(), min(r.height(), max(alto, self.minimumSize().height()))))


class Contesto:
    """Ciò che le pagine condividono: il patogeno scelto nella pagina iniziale."""
    def __init__(self):
        self.patogeno = "listeria"


class Pagina(QWidget):
    vai = Signal(str)               # chiave della pagina dove andare
    azioni_cambiate = Signal()      # la barra delle azioni (e il percorso) vanno ridisegnati
    lingua_scelta = Signal(str)     # Impostazioni: cambia lingua
    salvate = Signal()              # Impostazioni salvate: le pagine riprendono i valori predefiniti

    titolo = ""                     # titolo della pagina (e del percorso)
    nomi_passi = ()                 # procedura guidata: titoli dei passi; vuoto = una sola schermata

    def __init__(self, contesto, parent=None):
        super().__init__(parent)
        self.contesto = contesto
        self.titolo = _(self.titolo)
        self.testo_principale, self.principale_attivo = "", True
        self.aiuto, self.aiuto_livello = "", ""
        self.secondari = []
        self.occupata = False
        self.passo = 0
        self.fatti = set()
        s = QVBoxLayout(self)
        s.setContentsMargins(0, 0, 0, 0)
        self.pila = QStackedWidget()
        s.addWidget(self.pila)
        self.corpi, self.aree = [], []
        for i in range(max(1, len(self.nomi_passi))):
            dentro = QWidget()
            corpo = Corpo(dentro)
            corpo.setContentsMargins(40, 28, 40, 28)
            corpo.setSpacing(14)
            if self.nomi_passi:
                corpo.addWidget(etichetta(_("Passo {n} di {tot}", n=i + 1, tot=len(self.nomi_passi)), "nota"))
                corpo.addWidget(etichetta(_(self.nomi_passi[i]), "titolo"))
            elif self.titolo:
                corpo.addWidget(etichetta(self.titolo, "titolo"))
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setWidget(dentro)
            self.pila.addWidget(area)
            self.corpi.append(corpo)
            self.aree.append(area)

    @property
    def corpo(self):
        return self.corpi[0]

    def vai_passo(self, i):
        if self.nomi_passi and i > self.passo:
            self.fatti.update(range(self.passo, i))
        self.passo = i
        self.pila.setCurrentIndex(i)
        self.aree[i].verticalScrollBar().setValue(0)
        self.aggiorna_azioni()

    def aggiorna_azioni(self):
        self.azioni_cambiate.emit()

    def avviso_barra(self, testo, livello=""):
        self.aiuto, self.aiuto_livello = testo, livello
        self.azioni_cambiate.emit()

    def azione_principale(self):
        pass

    def mostrata(self):
        self.aggiorna_azioni()

    def impostazioni_cambiate(self):
        pass

    def adatta(self, stretta):
        for c in self.corpi:
            c.setContentsMargins(*((20, 20, 20, 20) if stretta else (40, 28, 40, 28)))

    def stato(self):
        return {"campi": raccogli(self), "passo": self.passo, "fatti": set(self.fatti)}

    def ripristina(self, stato):
        rimetti(self, stato["campi"])
        self.fatti = stato["fatti"]
        self.vai_passo(stato["passo"])


LIVELLI_ESITO = {"CONFORME": "verde", "NON_CONFORME": "rosso", "NON_VALUTABILE": "ambra"}


# ---------------- salvataggio dei report (solo dove sceglie l'utente) ----------------
def salva_file(parent, titolo, filtro, estensione, nome, scrivi):
    """Chiede dove salvare (QFileDialog) e chiama scrivi(percorso). Restituisce (messaggio, livello) o None se
    l'utente annulla. Il pacchetto dei report si importa dentro scrivi: se manca, un messaggio, non un arresto."""
    from pathlib import Path
    from PySide6.QtWidgets import QFileDialog
    proposto = str(Path.home() / "Documents" / nome)
    percorso, _f = QFileDialog.getSaveFileName(parent, titolo, proposto, filtro)
    if not percorso:
        return None
    if not percorso.lower().endswith(estensione):
        percorso += estensione
    try:
        scrivi(percorso)
    except ImportError:
        return _("Il modulo dei report non è disponibile in questa versione."), "errore"
    except Exception as e:   # noqa: BLE001 (file aperto in un altro programma, disco pieno...)
        return _("Non sono riuscito a salvare il file: {e}", e=str(e)), "errore"
    return _("Salvato in {p}", p=percorso), ""


class Guidata(Pagina):
    """Procedura guidata: passi di ingresso, poi "Calcola" (in un altro filo, con l'indicatore di lavoro) e
    l'ultimo passo con il risultato. Le sottoclassi scrivono controlla(i), prepara() e mostra(risultato)."""
    def __init__(self, contesto, parent=None):
        super().__init__(contesto, parent)
        self.risultato, self.dati_calcolo, self.lavoro = None, None, None
        ultimo = self.corpi[-1]
        self.attesa = QWidget()
        a = QVBoxLayout(self.attesa)
        a.setContentsMargins(0, 8, 0, 8)
        a.addWidget(etichetta(_("Sto calcolando. Ci vuole qualche secondo..."), "sottotitolo"))
        barra = QProgressBar()
        barra.setRange(0, 0)
        barra.setTextVisible(False)
        barra.setAccessibleName(_("Calcolo in corso"))
        a.addWidget(barra)
        self.attesa.hide()
        ultimo.addWidget(self.attesa)
        self.uscita = QVBoxLayout()
        self.uscita.setSpacing(16)
        ultimo.addLayout(self.uscita)

    @property
    def ultimo(self):
        return len(self.nomi_passi) - 1

    def aggiorna_azioni(self):
        self.secondari = [(_("Indietro"), lambda: self.vai_passo(self.passo - 1))] if self.passo > 0 else []
        if self.passo < self.ultimo - 1:
            self.testo_principale = _("Avanti")
        elif self.passo == self.ultimo - 1:
            self.testo_principale = _("Calcola")
        else:
            self.testo_principale = _("Salva il PDF")
            if self.risultato is not None:
                self.secondari += self.altri_salvataggi()
        self.principale_attivo = not self.occupata and (self.passo < self.ultimo or self.risultato is not None)
        self.azioni_cambiate.emit()

    def altri_salvataggi(self):
        return []

    def vai_passo(self, i):
        if self.passo != i and not self.occupata:
            self.aiuto, self.aiuto_livello = "", ""
        super().vai_passo(i)

    def salta(self, i):
        """Dal percorso: indietro sempre; avanti solo se i passi in mezzo sono a posto."""
        if self.occupata:
            return
        for j in range(self.passo, min(i, self.ultimo)):
            if not self.controlla(j):
                self.vai_passo(j)
                return
        if i == self.ultimo and self.risultato is None:
            self.calcola()
        else:
            self.vai_passo(i)

    def azione_principale(self):
        if self.passo < self.ultimo - 1:
            if self.controlla(self.passo):
                self.vai_passo(self.passo + 1)
        elif self.passo == self.ultimo - 1:
            self.calcola()
        else:
            self.salva_pdf()

    def errore_passo(self, messaggio):
        self.avviso_barra(messaggio, "errore")
        return False

    def controlla(self, i):
        return True

    def calcola(self):
        for i in range(self.ultimo):
            if not self.controlla(i):
                self.vai_passo(i)
                return
        funzione = self.prepara()
        if funzione is None:
            return
        self.risultato = None
        self.occupata = True
        svuota(self.uscita)
        self.attesa.show()
        self.avviso_barra("", "")
        self.vai_passo(self.ultimo)
        self.lavoro = Lavoro(funzione, self)
        self.lavoro.fatto.connect(self._fatto)
        self.lavoro.fallito.connect(self._fallito)
        self.lavoro.start()

    def _fine(self):
        self.occupata = False
        self.attesa.hide()

    def _fatto(self, risultato):
        self._fine()
        self.risultato = risultato
        self.ridisegna()

    def _fallito(self, messaggio):
        self._fine()
        svuota(self.uscita)
        self.uscita.addWidget(riquadro(_("Il calcolo non è riuscito."), messaggio, "errore"))
        self.aggiorna_azioni()

    def ridisegna(self):
        svuota(self.uscita)
        if self.risultato is not None:
            self.mostra(self.risultato)
        self.aggiorna_azioni()

    def salva_pdf(self):
        pass

    def stato(self):
        return dict(super().stato(), risultato=self.risultato, dati_calcolo=self.dati_calcolo)

    def ripristina(self, stato):
        self.risultato, self.dati_calcolo = stato["risultato"], stato["dati_calcolo"]
        super().ripristina(stato)
        self.ridisegna()


def riga_di_scelte(*schede):
    """Schede affiancate (con spazio uguale)."""
    r = QHBoxLayout()
    r.setSpacing(16)
    for s in schede:
        r.addWidget(s, 1)
    return r
