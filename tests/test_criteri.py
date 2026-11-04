"""Test dei criteri per L. monocytogenes (ermchek.core.criteri, criteria.yaml)."""
from datetime import date

import pytest

from ermchek.core import conformita as C
from ermchek.core import criteri as K

DOPO = "2026-07-01"
NEG5 = [C.assente(25)] * 5


@pytest.fixture(scope="module")
def criteri():
    return K.carica_criteri()


def test_righe(criteri):
    r = {x["id"]: x for x in criteri["criteri"]}
    assert (r["1.1"]["n"], r["1.1"]["c"], r["1.1"]["limite"]) == (10, 0, {"tipo": "assenza", "massa_g": 25.0})
    assert (r["1.2a"]["n"], r["1.2a"]["limite"]["valore"], r["1.2a"]["metodo"]) == (5, 100.0, "EN/ISO 11290-2")
    assert r["1.2b"]["fase"] == "immesso_sul_mercato_shelf_life" and r["1.2b"]["valido_dal"] == date(2026, 7, 1)
    assert r["1.2b_ante_2026"]["fase"] == "prima_di_lasciare_controllo_osa"
    assert r["1.2b_ante_2026"]["valido_fino"] == date(2026, 6, 30)
    assert (r["1.3"]["n"], r["1.3"]["c"], r["1.3"]["limite"]["valore"]) == (5, 0, 100.0)
    assert all(x["riferimento"] for x in criteri["criteri"])


def test_cambio_data_2026(criteri):
    assert K.seleziona_riga("1.2", False, "2026-06-30", criteri)["id"] == "1.2b_ante_2026"
    assert K.seleziona_riga("1.2", False, date(2026, 7, 1), criteri)["id"] == "1.2b"
    assert K.seleziona_riga("1.2", True, "2025-01-01", criteri)["id"] == "1.2a"
    assert K.seleziona_riga("1.2", True, DOPO, criteri)["id"] == "1.2a"


@pytest.mark.parametrize("risultati, cat, fbo, esito, riga, motivo", [
    (NEG5, "1.2", False, "CONFORME", "1.2b", "TUTTE_ENTRO_LIMITE"),
    ([C.conta(9000)] + [C.assente(25)] * 4, "1.2", False, "NON_CONFORME", "1.2b", "UNITA_OLTRE_LIMITE"),
    ([C.conta(50)] + [C.assente(25)] * 4, "1.2", True, "CONFORME", "1.2a", "TUTTE_ENTRO_LIMITE"),
    ([C.conta_in_massa(5000, 25)] + [C.assente(25)] * 4, "1.2", True, "NON_CONFORME", "1.2a", "UNITA_OLTRE_LIMITE"),
    ([C.sotto_lod(10)] * 5, "1.2", False, "NON_VALUTABILE", "1.2b", "RISULTATO_NON_ADATTO"),
    ([C.sotto_lod(10)] * 5, "1.3", False, "CONFORME", "1.3", "TUTTE_ENTRO_LIMITE"),
    (NEG5, "1.1", False, "NON_VALUTABILE", "1.1", "N_INSUFFICIENTE"),
    ([C.assente(25)] * 10, "1.1", False, "CONFORME", "1.1", "TUTTE_ENTRO_LIMITE"),
])
def test_esito_normativo(criteri, risultati, cat, fbo, esito, riga, motivo):
    e = K.esito_normativo(risultati, cat, fbo, DOPO, criteri)
    assert (e["esito"], e["riga"], e["motivo"]) == (esito, riga, motivo)


@pytest.mark.parametrize("ph, aw, giorni, delta, cat, motivo", [
    (4.4, 0.98, 30, None, "1.3", "NOTA6_PH"),
    (6.0, 0.92, 30, None, "1.3", "NOTA6_AW"),
    (5.0, 0.94, 30, None, "1.3", "NOTA6_PH_AW"),
    (6.0, 0.98, 4, None, "1.3", "NOTA6_SHELF_LIFE"),
    (5.0, 0.95, 30, None, None, "GIUSTIFICAZIONE_RICHIESTA"),
    (6.0, 0.98, 5, None, None, "GIUSTIFICAZIONE_RICHIESTA"),
    (6.0, 0.98, 30, 0.6, "1.2", "POTENZIALE_SOPRA_SOGLIA"),
    (6.0, 0.98, 30, 0.5, "1.3", "POTENZIALE_ENTRO_SOGLIA"),
])
def test_categoria_automatica(criteri, ph, aw, giorni, delta, cat, motivo):
    assert K.categoria_automatica(ph, aw, giorni, delta, criteri) == {"categoria": cat, "motivo": motivo}


def test_validazione_input(criteri):
    with pytest.raises(ValueError, match="CATEGORIA_SCONOSCIUTA"):
        K.esito_normativo(NEG5, "9.9", False, DOPO, criteri)
    with pytest.raises(ValueError, match="DATA_NON_VALIDA"):
        K.esito_normativo(NEG5, "1.2", False, "31/12/2026", criteri)
    with pytest.raises(ValueError, match="FBO_NON_BOOLEANO"):
        K.esito_normativo(NEG5, "1.2", "no", DOPO, criteri)
    with pytest.raises(ValueError, match="AW_FUORI_RANGE"):
        K.categoria_automatica(6.0, 1.5, 30, criteri=criteri)


@pytest.mark.parametrize("testo, codice", [
    ("!!python/object/apply:os.system ['echo x']", "CRITERI_YAML_NON_VALIDO"),
    ("criteri: []", "CRITERI_STRUTTURA_NON_VALIDA"),
    ("criteri:\n  - {id: x, categoria: '1.3', n: 0, c: 0}", "CRITERI_RIGA_NON_VALIDA"),
])
def test_yaml_non_valido(tmp_path, testo, codice):
    f = tmp_path / "criteria.yaml"
    f.write_text(testo, encoding="utf-8")
    with pytest.raises(ValueError, match=codice):
        K.carica_criteri(f)


def test_fase_di_campionamento_diversa_dalla_riga():
    from ermchek.core.conformita import assente
    from ermchek.core.criteri import esito_normativo
    r = esito_normativo([assente(25.0)] * 5, "1.2", False, "2026-03-01", fase_campionamento="immesso_sul_mercato_shelf_life")
    assert r["esito"] == "NON_VALUTABILE" and r["motivo"] == "FASE_NON_CORRISPONDENTE"
    r = esito_normativo([assente(25.0)] * 5, "1.2", False, "2026-08-01", fase_campionamento="immesso_sul_mercato_shelf_life")
    assert r["esito"] == "CONFORME"


def test_salmonella_riga_1_8_salami():
    from ermchek.core.conformita import assente, conta_in_massa
    from ermchek.core.criteri import carica_criteri, esito_normativo
    righe = {r["categoria"]: r for r in carica_criteri()["criteri"] if r["patogeno"] == "salmonella"}
    assert set(righe) == {"1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.28"}
    assert righe["1.6"]["limite"]["massa_g"] == 10 and righe["1.8"]["metodo"] == "EN ISO 6579-1"
    assert esito_normativo([assente(25.0)] * 5, "1.8", False, "2026-11-03")["esito"] == "CONFORME"
    assert esito_normativo([assente(25.0)] * 4 + [conta_in_massa(1, 25.0)], "1.8", False, "2026-11-03")["esito"] == "NON_CONFORME"
