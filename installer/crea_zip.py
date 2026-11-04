"""Zip da dare agli utenti: dist/ErmChek_<versione>.zip con l'app, l'installatore e le descrizioni. Dopo costruisci.py."""
import sys
import zipfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
from ermchek import __version__  # noqa: E402

app = RADICE / "dist" / "ErmChek"
zip_path = RADICE / "dist" / f"ErmChek_{__version__}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for f in app.rglob("*"):
        if f.is_file():
            z.write(f, Path("ErmChek") / f.relative_to(app))
    for nome, origine in [("Installa ErmChek.cmd", "installer/installa_ermchek.cmd"),
                          ("installa_ermchek.ps1", "installer/installa_ermchek.ps1"),
                          ("DESCRIZIONE.md", "docs/DESCRIZIONE.md"), ("DESCRIPTION.md", "docs/DESCRIPTION.md"),
                          ("LICENSE.txt", "LICENSE")]:
        z.write(RADICE / origine, nome)
print(zip_path, round(zip_path.stat().st_size / 1e6, 1), "MB")
