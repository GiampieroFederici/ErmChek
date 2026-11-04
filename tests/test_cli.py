"""Riga di comando: replica dello script, back-calculation di un esempio, crescita, ingressi sbagliati."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ermchek import lingua
from ermchek.cli import main
from ermchek.core.conformita import replica_script

RADICE = Path(__file__).resolve().parent.parent
FASI = [{"ore": 48, "temperatura": 20, "ph": 5.9, "aw": 0.965, "nitrito": 40},
        {"ore": 240, "temperatura": 12, "ph": 5.4, "aw": 0.95, "nitrito": 20}]
ESEMPIO = {"titolo": "Esempio", "fasi": FASI, "osservato_ufc_g": 300, "lab0": 1e5, "peso_pezzo_g": 500, "n_mc": 200}


@pytest.fixture(autouse=True)
def italiano():
    yield
    lingua.imposta("it")


def _json(tmp_path, dati, nome="caso.json"):
    p = tmp_path / nome
    p.write_text(dati if isinstance(dati, str) else json.dumps(dati), encoding="utf-8")
    return str(p)


def test_replicate_script_identico(capsys):
    assert main(["replicate-script"]) == 0
    assert capsys.readouterr().out.splitlines() == replica_script()


def test_modulo_eseguibile():
    uscita = subprocess.run([sys.executable, "-m", "ermchek.cli", "replicate-script"], cwd=RADICE,
                            capture_output=True, text=True, timeout=120)
    assert uscita.returncode == 0
    assert uscita.stdout.splitlines() == replica_script()


def test_back_esempio(tmp_path, capsys):
    pdf = tmp_path / "back.pdf"
    assert main(["back", "--input", _json(tmp_path, ESEMPIO), "--pdf", str(pdf), "--lang", "en"]) == 0
    out = capsys.readouterr().out
    assert "N0 ≈ 4.05 CFU/g" in out
    assert "100 CFU in 25 g" in out
    assert pdf.stat().st_size > 10_000


def test_back_ufc_in_25_g_italiano(tmp_path, capsys):
    dati = {k: v for k, v in ESEMPIO.items() if k != "osservato_ufc_g"} | {"osservato_ufc": 7500, "massa_g": 25,
                                                                         "n_mc": 0}
    assert main(["back", "--input", _json(tmp_path, dati)]) == 0
    assert "N0 ≈ 4,05 ufc/g" in capsys.readouterr().out


def test_grow(tmp_path, capsys):
    dati = {"fasi": FASI, "n0": 1.0, "lab0": 1e5}
    pdf = tmp_path / "grow.pdf"
    assert main(["grow", "--input", _json(tmp_path, dati), "--pdf", str(pdf)]) == 0
    out = capsys.readouterr().out
    assert "Listeria alla fine: 74,1 ufc/g" in out
    assert pdf.is_file()


@pytest.mark.parametrize("contenuto", [
    "{non è json",
    "[1, 2]",
    json.dumps({"fasi": FASI, "osservato_ufc_g": "300"}),                 # numero come testo
    json.dumps({"fasi": FASI, "osservato_ufc_g": True}),
    '{"fasi": [], "osservato_ufc_g": NaN}',
    json.dumps({"fasi": FASI, "osservato_ufc_g": 300, "sconosciuta": 1}),  # chiave non prevista
    json.dumps({"fasi": [{"ore": 24, "temperatura": 4, "ph": 5.8, "aw": 0.96, "colore": 1}], "osservato_ufc_g": 300}),
    json.dumps({"fasi": [{"ore": 24, "temperatura": 4, "ph": 5.8}], "osservato_ufc_g": 300}),   # né aw né sale
    json.dumps({"fasi": [{"ore": 24, "temperatura": 99, "ph": 5.8, "aw": 0.96}], "osservato_ufc_g": 300}),
    json.dumps({"fasi": FASI}),                                             # manca l'osservato
    json.dumps({"fasi": FASI, "osservato_ufc_g": 300, "n_mc": 2.5}),
])
def test_back_ingressi_sbagliati(tmp_path, capsys, contenuto):
    assert main(["back", "--input", _json(tmp_path, contenuto)]) == 1
    errore = capsys.readouterr().err
    assert errore.startswith("Errore: ") and len(errore) > 12


def test_file_mancante(tmp_path, capsys):
    assert main(["grow", "--input", str(tmp_path / "non_esiste.json")]) == 1
    assert "File non trovato" in capsys.readouterr().err


def test_grow_lag_non_booleano(tmp_path, capsys):
    assert main(["grow", "--input", _json(tmp_path, {"fasi": FASI, "n0": 1, "lag": "si"}), "--lang", "en"]) == 1
    assert "Error: " in capsys.readouterr().err
