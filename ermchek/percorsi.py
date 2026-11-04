"""Percorsi dei file di dati (params, criteri, logo, traduzioni), uguali da sorgente e da pacchetto PyInstaller."""
import sys
from pathlib import Path

RADICE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def risorsa(*parti):
    return RADICE.joinpath(*parti)
