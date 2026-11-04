"""Interfaccia (pytest-qt): finestra, lingua avanti e indietro, modulo C su un esempio, modulo A sul caso d'esame,
Salmonella che spegne B e C, traduzioni complete. Le impostazioni vanno in un file .ini temporaneo (mai nel registro)."""
import ast
import json
import re
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFrame, QLabel

from ermchek import lingua, testi

RADICE = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def impostazioni_temporanee(tmp_path, qapp):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    from ermchek.gui.app import prepara
    prepara(qapp)
    lingua.imposta("it")
    yield
    lingua.imposta("it")


@pytest.fixture
def finestra(qtbot):
    from ermchek.gui.finestra import Finestra
    f = Finestra(avvio_ms=0)
    qtbot.addWidget(f)
    f.show()
    f._pronto()
    return f


def risposta_di(pagina):
    riquadri = [w for w in pagina.findChildren(QFrame) if w.objectName() == "risposta" and w.isVisibleTo(pagina)]
    assert len(riquadri) == 1
    return " ".join(e.text() for e in riquadri[0].findChildren(QLabel))


def calcola_tutto(qtbot, pagina):
    for _i in range(pagina.ultimo):
        pagina.azione_principale()
    qtbot.waitUntil(lambda: not pagina.occupata and pagina.risultato is not None, timeout=120000)
    qtbot.wait(50)   # Qt mostra i widget nuovi al giro successivo del ciclo degli eventi


def test_finestra_e_lingua(finestra):
    assert finestra.windowTitle() == "ErmChek"
    assert not finestra.windowIcon().isNull()
    assert finestra.principale.text() == "Inizia il modulo C"
    finestra.vai("C")
    c = finestra.pagine["C"]
    c.osservato.edit.setText("5.000")
    c.osservato.scegli_unita("25g")
    assert finestra.cambia_lingua("en")
    assert lingua.attuale() == "en"
    c = finestra.pagine["C"]
    assert finestra.attuale == "C" and finestra.principale.text() == "Next"
    assert c.osservato.valore() == 5000 and c.osservato.unita_scelta() == "25g"   # i dati restano
    assert c.conversione.text() == "5,000 CFU in 25 g = 200 CFU/g"
    assert finestra.cambia_lingua("it")
    assert finestra.pagine["C"].conversione.text() == "5.000 ufc in 25 g = 200 ufc/g"
    assert finestra.pulsante_lingua.text() == "English"


def test_modulo_c_esempio(finestra, qtbot):
    finestra.vai("C")
    c = finestra.pagine["C"]
    c.esempio.setCurrentIndex(c.esempio.findData("salame_fresco"))
    calcola_tutto(qtbot, c)
    testo = risposta_di(c)
    assert "All'origine c'erano circa 4 ufc/g" in testo
    assert "circa 100 ufc in 25 g" in testo
    assert "Intervallo al 90 %" not in testo and "fra" not in testo   # nel riquadro solo il valore più probabile
    from ermchek.gui.base import Apribile
    tendine = [w for w in c.findChildren(Apribile) if w.titolo == "Intervallo" and w.isVisibleTo(c)]
    assert len(tendine) == 1 and not tendine[0].dentro.isVisible()   # chiusa all'inizio
    tendine[0].apri(True)
    assert any("In 9 calcoli su 10" in e.text() for e in tendine[0].dentro.findChildren(QLabel))
    assert c.risultato["principale"]["con_lab"]
    assert abs(c.risultato["principale"]["ufc_g"] - 4.05) < 0.01


def test_modulo_c_errori_in_linea(finestra):
    finestra.vai("C")
    c = finestra.pagine["C"]
    c.osservato.edit.setText("abc")
    c.azione_principale()
    assert c.passo == 0 and c.osservato.errore.isVisibleTo(c)
    assert finestra.aiuto.property("livello") == "errore"


def test_modulo_a_caso_esame(finestra, qtbot):
    finestra.vai("A")
    a = finestra.pagine["A"]
    a.esempio.setCurrentIndex(a.esempio.findData("esame"))
    assert a.categoria.currentData() == "1.2" and a.fbo_no.isChecked()
    calcola_tutto(qtbot, a)
    assert a.risultato["interpretazione"]["codice"] == "CONTAMINAZIONE_LOCALIZZATA"
    testo = risposta_di(a)
    assert lingua._(testi.INTERPRETAZIONI["CONTAMINAZIONE_LOCALIZZATA"]) in testo
    assert "Non conforme" in testo


def test_salmonella_spegne_b_e_c(finestra):
    home = finestra.pagine["home"]
    home.salmonella.pulsante.setChecked(True)
    assert not home.schede["B"].pulsante.isEnabled() and not home.schede["C"].pulsante.isEnabled()
    assert home.schede["A"].pulsante.isChecked() and home.solo_a.isVisibleTo(home)
    home.azione_principale()
    a = finestra.pagine["A"]
    assert finestra.attuale == "A"
    assert all(a.categoria.itemData(i) not in ("1.1", "1.2", "1.3") for i in range(a.categoria.count()))
    home.listeria.pulsante.setChecked(True)
    assert home.schede["C"].pulsante.isEnabled()


def test_numeri_due_cifre():
    from ermchek.gui.base import cifre2, percento
    assert cifre2(4.0487) == "4" and cifre2(101.2) == "100" and cifre2(1687.2) == "1.700" and cifre2(6.96) == "7"
    assert cifre2(6.745e-5) == "6,7 × 10⁻⁵"
    assert percento(2e-12) == "meno di 0,1 %" and percento(0.0) == "meno di 0,1 %" and percento(1.0) == "più di 99,9 %"


def test_report_dal_risultato(finestra, qtbot, tmp_path):
    """I file del report si scrivono con l'API del pacchetto report (se c'è), dal risultato del modulo B."""
    pdf = pytest.importorskip("ermchek.report.pdf")
    excel = pytest.importorskip("ermchek.report.excel")
    finestra.vai("B")
    b = finestra.pagine["B"]
    b.esempio.setCurrentIndex(b.esempio.findData("salame_fresco"))
    b.opzioni.n_mc.imposta(200)
    calcola_tutto(qtbot, b)
    pdf.crea_pdf(str(tmp_path / "b.pdf"), "crescita", b._per_report(), b.ingressi())
    excel.esporta_excel(str(tmp_path / "b.xlsx"), "crescita", b._per_report(), b.ingressi())
    excel.esporta_csv_curva(str(tmp_path / "b.csv"), b.risultato["sim"])
    assert all((tmp_path / n).stat().st_size > 0 for n in ("b.pdf", "b.xlsx", "b.csv"))


def test_ogni_testo_ha_la_traduzione():
    """Ogni stringa passata a _() o N_() in ermchek/gui ha la sua voce in ermchek/i18n/en_gui.json."""
    gui = json.loads((RADICE / "ermchek" / "i18n" / "en_gui.json").read_text(encoding="utf-8"))
    mancanti = []
    for f in sorted((RADICE / "ermchek" / "gui").glob("*.py")):
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(n, ast.Call) and getattr(n.func, "id", None) in ("_", "N_") and n.args
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)
                    and n.args[0].value not in gui):
                mancanti.append(f"{f.name}: {n.args[0].value}")
    assert not mancanti, "\n".join(mancanti)
    campi = lambda testo: set(re.findall(r"\{(\w*)\}", testo))   # noqa: E731
    for it, en in gui.items():   # stessi {campi} nelle due lingue
        assert campi(it) == campi(en), it


def test_data_logger_e_calcolatrice_wps(finestra, tmp_path):
    from ermchek.core import crescita
    from ermchek.gui.condizioni import DialogoWps
    finestra.vai("C")
    c = finestra.pagine["C"]
    c.esempio.setCurrentIndex(c.esempio.findData("salame_fresco"))
    csv = tmp_path / "logger.csv"
    csv.write_text("ore;temperatura\n0;4,0\n48;15,5\n", encoding="utf-8")
    c.editor._usa_punti(crescita.leggi_csv_temperature(csv), str(csv))
    fasi = c.editor.fasi()
    assert [f.temperatura for f in fasi] == [4.0, 15.5]
    d = DialogoWps()
    d.nacl.imposta(2.5)
    d.umidita.imposta(60)
    assert abs(d.valore - 2.5 * 100 / 62.5) < 1e-9 and "= 4 %" in d.calcolo.text()


def test_rotellina_non_cambia_i_menu(qapp, qtbot):
    """La rotellina sopra un menu senza fuoco non cambia il valore (difetto trovato nella prova sulla VM)."""
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QComboBox
    m = QComboBox()
    m.addItems(["salame", "salsiccia", "cotto"])
    qtbot.addWidget(m)
    m.show()
    m.clearFocus()
    evento = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120), Qt.NoButton, Qt.NoModifier,
                         Qt.NoScrollPhase, False)
    qapp.sendEvent(m, evento)
    assert m.currentIndex() == 0
    assert m.focusPolicy() == Qt.StrongFocus   # con WheelFocus la rotellina darebbe il fuoco e poi cambierebbe il valore
