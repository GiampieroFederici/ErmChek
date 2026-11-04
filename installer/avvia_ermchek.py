"""Punto d'ingresso dell'eseguibile (PyInstaller): avvia l'interfaccia come `python -m ermchek`.

`ErmChek.exe --autoverifica CARTELLA`: senza aprire finestre, calcola un esempio del modulo C dentro l'app
impacchettata e scrive in CARTELLA il PDF (it, en), l'Excel e autoverifica.txt (OK o l'errore). Serve a
provare l'eseguibile installato, comprese le parti caricate solo quando servono (grafici, caratteri, report).
"""
import runpy
import sys
import traceback
from pathlib import Path


def autoverifica(cartella):
    cartella = Path(cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    try:
        from ermchek import lingua
        from ermchek.core.crescita import Fase
        from ermchek.core.retro import retro
        from ermchek.report.excel import esporta_excel
        from ermchek.report.pdf import crea_pdf
        fasi = [Fase(ore=48, temperatura=20, ph=5.9, aw=0.965, nitrito=40),
                Fase(ore=240, temperatura=12, ph=5.4, aw=0.95, nitrito=20)]
        ris = retro(fasi, 300.0, lab0=1e5, n_mc=500)
        ingressi = {"titolo": "Autoverifica", "righe": [("Lm", "300 ufc/g")], "contesto": [], "fasi": fasi}
        for codice in ("it", "en"):
            lingua.imposta(codice)
            crea_pdf(cartella / f"autoverifica_{codice}.pdf", "retro", ris, ingressi)
        esporta_excel(cartella / "autoverifica.xlsx", "retro", ris, ingressi)
        esito = f"OK N0={ris['principale']['ufc_g']:.4g} ufc/g"
    except Exception:
        esito = "ERRORE\n" + traceback.format_exc()
    (cartella / "autoverifica.txt").write_text(esito, encoding="utf-8")
    return 0 if esito.startswith("OK") else 1


def autoverifica_gui(cartella, osservato="5.000"):
    """La finestra vera, come la usa una persona: modulo C con l'esempio, Lm misurata oggi = `osservato` ufc/g.
    Scrive le foto della finestra (gui_*.png) e la risposta in autoverifica_gui.txt."""
    cartella = Path(cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    try:
        import time
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication, QFrame, QLabel
        from ermchek import lingua
        from ermchek.gui.app import prepara
        from ermchek.gui.finestra import Finestra
        QSettings.setDefaultFormat(QSettings.IniFormat)   # impostazioni di prova fuori dal registro
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(cartella))
        app = QApplication([])
        prepara(app)
        lingua.imposta("it")
        f = Finestra(avvio_ms=0)
        f.resize(1366, 860)
        f.show()
        f._pronto()
        app.processEvents()
        f.grab().save(str(cartella / "gui_1_inizio.png"))
        f.vai("C")
        c = f.pagine["C"]
        c.esempio.setCurrentIndex(c.esempio.findData("salame_fresco"))
        c.osservato.edit.setText(osservato)
        c.osservato.scegli_unita("g")
        app.processEvents()
        f.grab().save(str(cartella / "gui_2_dato_oggi.png"))
        for _i in range(c.ultimo):
            c.azione_principale()
            app.processEvents()
        fine = time.time() + 180
        while (c.occupata or c.risultato is None) and time.time() < fine:
            app.processEvents()
            time.sleep(0.05)
        for _i in range(5):
            app.processEvents()
        f.grab().save(str(cartella / "gui_3_risultato.png"))
        from ermchek.gui.base import Apribile
        for t_ in c.findChildren(Apribile):
            if t_.titolo in ("Intervallo", "Interval"):
                t_.apri(True)
                app.processEvents()
                t_.grab().save(str(cartella / "gui_4_intervallo.png"))
        riquadri = [w for w in c.findChildren(QFrame) if w.objectName() == "risposta" and w.isVisibleTo(c)]
        testo = " | ".join(e.text() for e in riquadri[0].findChildren(QLabel)) if riquadri else "NESSUNA RISPOSTA"
        esito = ("OK " if riquadri else "ERRORE ") + testo
    except Exception:
        esito = "ERRORE\n" + traceback.format_exc()
    (cartella / "autoverifica_gui.txt").write_text(esito, encoding="utf-8")
    return 0 if esito.startswith("OK") else 1


if len(sys.argv) == 3 and sys.argv[1].startswith("--autoverifica"):
    try:   # nelle autoverifiche l'immagine di avvio non serve
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass
if len(sys.argv) == 3 and sys.argv[1] == "--autoverifica":
    sys.exit(autoverifica(sys.argv[2]))
if len(sys.argv) == 3 and sys.argv[1] == "--autoverifica-gui":
    sys.exit(autoverifica_gui(sys.argv[2]))
runpy.run_module("ermchek", run_name="__main__", alter_sys=True)
