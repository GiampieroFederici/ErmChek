"""Criteri per Listeria monocytogenes da criteria.yaml (Reg. CE 2073/2005, All. I, cap. 1, righe 1.1-1.3,
con il Reg. UE 2024/2895 dal 2026-07-01). Sceglie la riga per categoria, dimostrazione dell'OSA e data di
campionamento e restituisce codici (CONFORME / NON_CONFORME / NON_VALUTABILE), mai testo tradotto."""
from datetime import date, datetime
from pathlib import Path

import yaml

from ermchek.core.conformita import Risultato, _numero, _valida_risultati
from ermchek.percorsi import risorsa

PERCORSO_CRITERI = risorsa("criteria.yaml")
_TIPI_LIMITE = ("assenza", "max_ufc_g")
_FASI = ("immesso_sul_mercato_shelf_life", "prima_di_lasciare_controllo_osa")
PATOGENI = ("listeria", "salmonella")
_NOTA_6 = ("ph_max", "aw_max", "ph_max_combinato", "aw_max_combinato", "shelf_life_giorni_minima")


def _data(v, codice):
    """date da date/datetime o da stringa "AAAA-MM-GG"."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(v)
    except (TypeError, ValueError):
        raise ValueError(codice) from None


def _valida_riga(r):
    if not isinstance(r, dict):
        raise ValueError("CRITERI_RIGA_NON_VALIDA")
    r.setdefault("patogeno", "listeria")
    if r["patogeno"] not in PATOGENI:
        raise ValueError("CRITERI_RIGA_NON_VALIDA")
    for campo in ("id", "categoria", "metodo", "riferimento"):
        if not isinstance(r.get(campo), str) or not r[campo]:
            raise ValueError("CRITERI_RIGA_NON_VALIDA")
    n, c = r.get("n"), r.get("c")
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (n, c)) or n < 1 or not 0 <= c <= n:
        raise ValueError("CRITERI_PIANO_NON_VALIDO")
    if r.get("fbo_dimostra_100") not in (True, False, None) or r.get("fase") not in _FASI:
        raise ValueError("CRITERI_RIGA_NON_VALIDA")
    lim = r.get("limite")
    if not isinstance(lim, dict) or lim.get("tipo") not in _TIPI_LIMITE:
        raise ValueError("CRITERI_LIMITE_NON_VALIDO")
    chiave = "massa_g" if lim["tipo"] == "assenza" else "valore"
    lim[chiave] = _numero(lim.get(chiave), "CRITERI_LIMITE_NON_VALIDO", 0.0, incluso=False)
    for campo in ("valido_dal", "valido_fino"):
        if r.get(campo) is not None:
            r[campo] = _data(r[campo], "CRITERI_DATA_NON_VALIDA")
        else:
            r[campo] = None


def carica_criteri(percorso=None):
    """Legge e valida criteria.yaml (solo yaml.safe_load). Restituisce il dict: criteri, nota_6, potenziale_crescita."""
    percorso = Path(percorso) if percorso is not None else PERCORSO_CRITERI
    try:
        with open(percorso, encoding="utf-8") as f:
            dati = yaml.safe_load(f)
    except yaml.YAMLError:
        raise ValueError("CRITERI_YAML_NON_VALIDO") from None
    if not isinstance(dati, dict) or not isinstance(dati.get("criteri"), list) or not dati["criteri"]:
        raise ValueError("CRITERI_STRUTTURA_NON_VALIDA")
    for r in dati["criteri"]:
        _valida_riga(r)
    if len({r["id"] for r in dati["criteri"]}) != len(dati["criteri"]):
        raise ValueError("CRITERI_ID_DUPLICATO")
    nota = dati.get("nota_6")
    if not isinstance(nota, dict):
        raise ValueError("CRITERI_STRUTTURA_NON_VALIDA")
    for k in _NOTA_6:
        nota[k] = _numero(nota.get(k), "CRITERI_NOTA6_NON_VALIDA", 0.0)
    pot = dati.get("potenziale_crescita")
    if not isinstance(pot, dict):
        raise ValueError("CRITERI_STRUTTURA_NON_VALIDA")
    pot["soglia_log"] = _numero(pot.get("soglia_log"), "CRITERI_SOGLIA_NON_VALIDA")
    return dati


def seleziona_riga(categoria, fbo_dimostra_100, data_campionamento, criteri=None):
    """Riga di criteria.yaml applicabile (dict) oppure None se nessuna riga vale per quella data."""
    criteri = carica_criteri() if criteri is None else criteri
    if categoria not in {r["categoria"] for r in criteri["criteri"]}:
        raise ValueError("CATEGORIA_SCONOSCIUTA")
    if not isinstance(fbo_dimostra_100, bool):
        raise ValueError("FBO_NON_BOOLEANO")
    giorno = _data(data_campionamento, "DATA_NON_VALIDA")
    righe = [r for r in criteri["criteri"] if r["categoria"] == categoria
             and r["fbo_dimostra_100"] in (None, fbo_dimostra_100)
             and (r["valido_dal"] is None or r["valido_dal"] <= giorno)
             and (r["valido_fino"] is None or giorno <= r["valido_fino"])]
    if len(righe) > 1:
        raise ValueError("CRITERI_AMBIGUI")
    return righe[0] if righe else None


def _valuta_unita(r: Risultato, limite):
    """OK | OLTRE (unità difettosa) | NON_ADATTO (il risultato non dimostra il rispetto del limite)."""
    if limite["tipo"] == "assenza":
        if r.tipo == "conta":
            return "OLTRE"
        if r.tipo == "assente" and r.valore >= limite["massa_g"]:
            return "OK"
        return "NON_ADATTO"   # < LOD in enumerazione, o assenza in una massa minore di quella prevista
    if r.tipo == "conta":
        return "OLTRE" if r.valore > limite["valore"] else "OK"
    if r.tipo == "sotto_lod":
        return "OK" if r.valore <= limite["valore"] else "NON_ADATTO"
    return "OK" if r.valore * limite["valore"] >= 1 else "NON_ADATTO"   # assente in m g: c < 1/m UFC/g


def esito_normativo(risultati, categoria, fbo_dimostra_100, data_campionamento, criteri=None, fase_campionamento=None):
    """Esito secondo criteria.yaml. Restituisce dict: esito (CONFORME | NON_CONFORME | NON_VALUTABILE),
    riga (id o None), motivo, unita_oltre_limite, n_richiesto, n_analizzato, fase (della riga).
    fase_campionamento (facoltativa): immesso_sul_mercato_shelf_life | prima_di_lasciare_controllo_osa; se non è la
    fase della riga il criterio non si applica a quel campione.
    motivo: TUTTE_ENTRO_LIMITE | UNITA_OLTRE_LIMITE | RISULTATO_NON_ADATTO | N_INSUFFICIENTE | NESSUNA_RIGA_APPLICABILE
    | FASE_NON_CORRISPONDENTE."""
    risultati = _valida_risultati(risultati)
    riga = seleziona_riga(categoria, fbo_dimostra_100, data_campionamento, criteri)
    base = {"riga": None, "unita_oltre_limite": None, "n_richiesto": None,
            "n_analizzato": len(risultati), "fase": None}
    if riga is None:
        return dict(base, esito="NON_VALUTABILE", motivo="NESSUNA_RIGA_APPLICABILE")
    if fase_campionamento is not None:
        if fase_campionamento not in ("immesso_sul_mercato_shelf_life", "prima_di_lasciare_controllo_osa"):
            raise ValueError("FASE_SCONOSCIUTA")
        if fase_campionamento != riga["fase"]:
            return dict(base, riga=riga["id"], fase=riga["fase"], esito="NON_VALUTABILE", motivo="FASE_NON_CORRISPONDENTE")
    stati = [_valuta_unita(r, riga["limite"]) for r in risultati]
    oltre = stati.count("OLTRE")
    base.update(riga=riga["id"], unita_oltre_limite=oltre, n_richiesto=riga["n"], fase=riga["fase"])
    if oltre > riga["c"]:
        return dict(base, esito="NON_CONFORME", motivo="UNITA_OLTRE_LIMITE")
    if "NON_ADATTO" in stati:
        return dict(base, esito="NON_VALUTABILE", motivo="RISULTATO_NON_ADATTO")
    if len(risultati) < riga["n"]:
        return dict(base, esito="NON_VALUTABILE", motivo="N_INSUFFICIENTE")
    return dict(base, esito="CONFORME", motivo="TUTTE_ENTRO_LIMITE")


def categoria_automatica(ph, aw, shelf_life_giorni, potenziale_crescita_log=None, criteri=None):
    """Categoria 1.2/1.3 (alimenti diversi dalla 1.1). Prima la nota 6 (automaticamente 1.3), poi, se dato,
    il potenziale di crescita (log10): > soglia -> 1.2, altrimenti 1.3. Restituisce dict: categoria
    ("1.3" | "1.2" | None), motivo (NOTA6_PH | NOTA6_AW | NOTA6_PH_AW | NOTA6_SHELF_LIFE |
    POTENZIALE_SOPRA_SOGLIA | POTENZIALE_ENTRO_SOGLIA | GIUSTIFICAZIONE_RICHIESTA)."""
    criteri = carica_criteri() if criteri is None else criteri
    ph = _numero(ph, "PH_FUORI_RANGE", 0.0, 14.0)
    aw = _numero(aw, "AW_FUORI_RANGE", 0.0, 1.0)
    if aw == 0:
        raise ValueError("AW_FUORI_RANGE")
    shelf = _numero(shelf_life_giorni, "SHELF_LIFE_NON_VALIDA", 0.0, incluso=False)
    n6 = criteri["nota_6"]
    if ph <= n6["ph_max"]:
        return {"categoria": "1.3", "motivo": "NOTA6_PH"}
    if aw <= n6["aw_max"]:
        return {"categoria": "1.3", "motivo": "NOTA6_AW"}
    if ph <= n6["ph_max_combinato"] and aw <= n6["aw_max_combinato"]:
        return {"categoria": "1.3", "motivo": "NOTA6_PH_AW"}
    if shelf < n6["shelf_life_giorni_minima"]:
        return {"categoria": "1.3", "motivo": "NOTA6_SHELF_LIFE"}
    if potenziale_crescita_log is None:
        return {"categoria": None, "motivo": "GIUSTIFICAZIONE_RICHIESTA"}
    delta = _numero(potenziale_crescita_log, "POTENZIALE_NON_VALIDO")
    if delta > criteri["potenziale_crescita"]["soglia_log"]:
        return {"categoria": "1.2", "motivo": "POTENZIALE_SOPRA_SOGLIA"}
    return {"categoria": "1.3", "motivo": "POTENZIALE_ENTRO_SOGLIA"}
