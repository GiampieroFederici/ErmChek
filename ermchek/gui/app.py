"""Avvio dell'interfaccia di ErmChek:  .venv\\Scripts\\python.exe -m ermchek"""
import sys

from PySide6.QtCore import QDir, QEvent, QObject, Qt
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QComboBox

from ermchek import lingua
from ermchek.gui.finestra import ICONA, Finestra, movimento_ridotto
from ermchek.percorsi import risorsa

GUI = risorsa("ermchek", "gui")


class _RotellinaSicura(QObject):
    """La rotellina sopra un menu o una casella numerica che non ha il fuoco scorre la pagina: non cambia il dato
    (un valore cambiato per sbaglio passerebbe inosservato)."""

    def eventFilter(self, oggetto, evento):
        if isinstance(oggetto, (QComboBox, QAbstractSpinBox)):
            if evento.type() == QEvent.Polish:   # il fuoco solo con clic o Tab: la rotellina non lo prende
                oggetto.setFocusPolicy(Qt.StrongFocus)
            elif evento.type() == QEvent.Wheel and not oggetto.hasFocus():
                evento.ignore()
                return True
        return False


def prepara(app):
    """Carattere Atkinson Hyperlegible (OFL, ermchek/gui/risorse/carattere) e stile (url(risorse:...)).
    Con "riduci movimento" di Windows si spengono anche le animazioni di Qt (menu, suggerimenti)."""
    QDir.addSearchPath("risorse", str(GUI / "risorse"))
    for ttf in sorted((GUI / "risorse" / "carattere").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))
    app.setStyleSheet((GUI / "stile.qss").read_text(encoding="utf-8"))
    app._rotellina = _RotellinaSicura(app)   # tenuto in vita dall'applicazione
    app.installEventFilter(app._rotellina)
    app.setWindowIcon(QIcon(str(ICONA)))
    if movimento_ridotto():
        for effetto in (Qt.UI_AnimateMenu, Qt.UI_FadeMenu, Qt.UI_AnimateCombo, Qt.UI_AnimateTooltip,
                        Qt.UI_FadeTooltip, Qt.UI_AnimateToolBox):
            app.setEffectEnabled(effetto, False)


def main():
    if sys.platform == "win32":          # l'icona di ErmChek (non quella di Python) nella barra di Windows
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ermchek.app")
    app = QApplication(sys.argv)
    app.setApplicationName("ErmChek")
    app.setOrganizationName("ErmChek")
    prepara(app)
    lingua.imposta(lingua.salvata())     # la lingua scelta l'ultima volta (italiano la prima)
    f = Finestra()
    f.show()
    try:   # immagine di avvio dell'eseguibile (PyInstaller --splash): si chiude quando c'è la finestra
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass
    f.avvia()
    return app.exec()
