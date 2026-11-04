"""Costruisce l'app Windows (PyInstaller, cartella unica) in dist/ErmChek. Uso: .venv\Scripts\python.exe installer\costruisci.py"""
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
DATI = [("params", "params"), ("criteria.yaml", "."), ("assets", "assets"), ("ermchek/i18n", "ermchek/i18n"),
        ("ermchek/gui/risorse", "ermchek/gui/risorse"), ("ermchek/gui/stile.qss", "ermchek/gui")]
comando = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed", "--name", "ErmChek",
           "--icon", str(RADICE / "assets" / "logo" / "ErmChek_icona.ico"),
           "--distpath", str(RADICE / "dist"), "--workpath", str(RADICE / "build" / "pyinstaller"),
           "--specpath", str(RADICE / "build"), "--collect-submodules", "ermchek",
           "--splash", str(RADICE / "assets" / "logo" / "ErmChek_avvio.png"),   # compare subito al doppio clic
           "--exclude-module", "pytest", "--exclude-module", "pytestqt", "--exclude-module", "pymupdf"]
for sorgente, destinazione in DATI:
    if (RADICE / sorgente).exists():
        comando += ["--add-data", f"{RADICE / sorgente};{destinazione}"]
comando.append(str(RADICE / "installer" / "avvia_ermchek.py"))
subprocess.run(comando, check=True, cwd=RADICE)
print("Pronto:", RADICE / "dist" / "ErmChek" / "ErmChek.exe")
