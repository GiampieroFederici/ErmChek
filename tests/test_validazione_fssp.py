"""ErmChek contro i valori finali di FSSP.Models.dll salvati (tests/validation_fssp.md per la tabella completa)."""
import json
from pathlib import Path

import pytest

from ermchek.core.crescita import simula
from tests.test_crescita import RIF, fasi_di

DLL = json.loads((Path(__file__).parent / "dati" / "fssp_dll_finali.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("i", range(len(RIF)))
def test_finale_come_fssp(i):
    rif, dll = RIF[i], DLL[f"E{i:02d}"]
    sim = simula(fasi_di(rif), rif["n0"], lab0=rif.get("lab0"), lag=rif["lag"])
    assert sim["log_lm"][0][-1] == pytest.approx(dll["log_finale_dll"], abs=1e-9)
    assert sim["fasi"][0]["mu_lm"] == pytest.approx(dll["mu_dll"], rel=1e-9, abs=1e-12)
