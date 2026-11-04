"""Dai codici del core alle frasi per l'utente (IT nel codice, EN nei cataloghi ermchek/i18n/*.json).

Il core restituisce solo codici e numeri; qui si scrivono le frasi, una volta sola, per l'interfaccia e per il report.
Frasi brevi, un concetto per frase (accessibilità).
"""
from ermchek.core.fssp.validita import NOMI, numero_it
from ermchek.lingua import N_, _

AVVISI = {
    "FUORI_CAMPO": N_("{fattore} = {valore} è fuori dal campo di validità del modello ({lo}-{hi}). "
                      "La previsione è un'estrapolazione."),
    "JAMESON_PH_SOTTO_6": N_("Con pH sotto 6 il freno dei batteri lattici è poco affidabile: nella validazione "
                             "pubblicata il modello prevedeva non crescita dove la crescita c'era (Mejlholm & Dalgaard 2015)."),
    "BARANYI_NON_VALIDATO_FSSP": N_("Modello di Baranyi: senza effetto dei batteri lattici e non confrontato con FSSP."),
    "SOLO_CRESCITA": N_("Il modello prevede solo crescita, mai la morte di Listeria."),
    "NON_CRESCITA": N_("Il modello prevede che Listeria non cresca. Quindi all'origine c'era almeno quanto hai misurato. "
                       "Se nel frattempo è morta, all'origine ce n'era di più."),
    "PESO_PEZZO_MANCANTE": N_("Peso del pezzo non impostato: inseriscilo nelle Impostazioni per sapere quante cellule "
                              "c'erano in un pezzo intero."),
    "MENO_DI_UNA_CELLULA_PER_PEZZO": N_("Meno di una cellula per pezzo: fisicamente implausibile. Fa pensare a una "
                                        "contaminazione avvenuta dopo il giorno 0 scelto."),
    "STIMA_MINIMA_NESSUNA_INATTIVAZIONE": N_("La stima è un valore minimo: il modello non prevede la morte di Listeria "
                                             "durante la fermentazione. Se è morta, all'origine ce n'era di più."),
}

ESITI = {"CONFORME": N_("Conforme"), "NON_CONFORME": N_("Non conforme"), "NON_VALUTABILE": N_("Non valutabile")}
MOTIVI = {
    "TUTTE_ENTRO_LIMITE": N_("Tutte le unità rispettano il limite."),
    "UNITA_OLTRE_LIMITE": N_("Almeno un'unità supera il limite."),
    "RISULTATO_NON_ADATTO": N_("Almeno un risultato non permette di confrontarsi con il limite (metodo o massa diversi)."),
    "N_INSUFFICIENTE": N_("Unità analizzate meno di quelle richieste dal criterio."),
    "NESSUNA_RIGA_APPLICABILE": N_("Nessun criterio di legge si applica a questa data e categoria."),
    "FASE_NON_CORRISPONDENTE": N_("Il criterio vale in un'altra fase della filiera rispetto a quella del campionamento."),
}
INTERPRETAZIONI = {
    "LOTTO_OMOGENEO": N_("Il risultato è compatibile con un lotto contaminato in modo omogeneo."),
    "CONTAMINAZIONE_LOCALIZZATA": N_("Il risultato non è compatibile con un lotto omogeneo: fa pensare a una contaminazione "
                                     "localizzata o sporadica."),
}
CATEGORIE = {
    "NOTA6_PH": N_("pH ≤ 4,4: categoria 1.3 automatica (nota 6)."),
    "NOTA6_AW": N_("aw ≤ 0,92: categoria 1.3 automatica (nota 6)."),
    "NOTA6_PH_AW": N_("pH ≤ 5,0 e aw ≤ 0,94: categoria 1.3 automatica (nota 6)."),
    "NOTA6_SHELF_LIFE": N_("Shelf-life sotto 5 giorni: categoria 1.3 automatica (nota 6)."),
    "POTENZIALE_SOPRA_SOGLIA": N_("Potenziale di crescita sopra 0,5 log: categoria 1.2."),
    "POTENZIALE_ENTRO_SOGLIA": N_("Potenziale di crescita fino a 0,5 log: categoria 1.3."),
    "GIUSTIFICAZIONE_RICHIESTA": N_("Serve una giustificazione scientifica (challenge test o studio di durabilità)."),
}
ERRORI = {
    "AW_OPPURE_SALE": N_("Indica l'aw oppure il sale nella fase acquosa, non entrambi e non nessuno dei due."),
    "NESSUNA_FASE": N_("Aggiungi almeno una fase."),
    "CSV_SERVONO_ALMENO_2_PUNTI_DA_ZERO": N_("Il file deve avere almeno due righe e partire dall'ora 0."),
    "CSV_TROPPO_LUNGO": N_("Il file ha troppe righe."),
    "CSV_RIGA": N_("Riga {n} del file non valida: servono ore e temperatura (da -2 a 40 °C)."),
    "CSV_TEMPO_NON_CRESCENTE": N_("Riga {n} del file: il tempo deve crescere."),
    "FUORI_LIMITE": N_("Valore fuori dai limiti ammessi: {campo}."),
    "BARANYI_SENZA_LAB": N_("Il modello di Baranyi non usa i batteri lattici: togli la conta dei LAB o scegli FSSP."),
}


def avviso(a):
    """Frase per un avviso del core (dict con 'codice' e, per FUORI_CAMPO, fattore/valore/campo)."""
    testo = _(AVVISI.get(a["codice"], a["codice"]))
    if a["codice"] == "FUORI_CAMPO":
        lo, hi = a["campo"]
        return testo.format(fattore=_(NOMI.get(a["fattore"], a["fattore"])), valore=numero_it(a["valore"]),
                            lo=numero_it(lo), hi=numero_it(hi))
    return testo


def errore(e):
    """Frase per un ValueError del core (codice o codice:dettaglio)."""
    codice, _sep, dettaglio = str(e).partition(":")
    testo = _(ERRORI.get(codice, codice))
    return testo.format(n=dettaglio, campo=dettaglio) if dettaglio else testo.replace(": {campo}", "")
