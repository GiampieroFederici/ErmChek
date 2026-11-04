"""Le spiegazioni dei termini (suggerimenti al passaggio del mouse): frasi brevi, una idea per riga."""
from ermchek.lingua import N_, _

TERMINI = {
    "aw": N_("aw (attività dell'acqua): quanta acqua è libera per i batteri.\nDa 0 a 1. Più è bassa, meno Listeria cresce.\n"
             "Un salame fresco ha circa 0,97; uno stagionato sotto 0,92."),
    "wps": N_("Sale nella fase acquosa (WPS, water-phase salt): il sale sciolto nell'acqua del prodotto, in %.\n"
              "WPS = NaCl / (NaCl + acqua) × 100.\nConta questo, non il sale sul peso totale."),
    "ph": N_("pH: quanto è acido il prodotto.\nPiù è basso, meno Listeria cresce."),
    "temperatura": N_("Temperatura del prodotto in quella fase, in gradi Celsius."),
    "durata": N_("Quanto dura la fase, in ore o in giorni.\nLe fasi, una dopo l'altra, vanno dal giorno 0 al giorno dell'analisi."),
    "nitrito": N_("Nitrito residuo: il nitrito misurato nel prodotto, in mg/kg (uguale a ppm).\nFrena la crescita di Listeria."),
    "nitrato": N_("Il nitrato agisce solo dopo la riduzione a nitrito da parte degli stafilococchi; inserisci il nitrito "
                  "residuo misurato.\nQuesto campo è solo informativo: va nel report, non nel calcolo."),
    "acidi": N_("Acidi organici sciolti nella fase acquosa, in ppm (mg per litro di acqua del prodotto).\n"
                "Lasciali vuoti se non li conosci."),
    "co2": N_("CO2 nello spazio di testa della confezione, in %.\nSolo per prodotti in atmosfera modificata."),
    "fenoli": N_("Fenoli del fumo, in ppm.\nSolo per prodotti affumicati."),
    "lab": N_("LAB (lactic acid bacteria): i batteri lattici.\nFanno la fermentazione e, quando sono tanti, frenano Listeria."),
    "jameson": N_("Effetto Jameson: quando i batteri lattici arrivano al loro massimo, Listeria smette di crescere.\n"
                  "Il modello FSSP lo usa per descrivere la competizione."),
    "lag": N_("Lag (fase di adattamento): il tempo in cui Listeria si abitua al prodotto prima di crescere.\n"
              "Senza lag la stima è più prudente."),
    "mumax": N_("μmax: la velocità massima di crescita (per ora) nelle condizioni della fase."),
    "fssp": N_("FSSP (Food Spoilage and Safety Predictor, DTU Food): modelli di crescita di Listeria e dei batteri lattici\n"
               "di Mejlholm e Dalgaard, con l'effetto Jameson."),
    "baranyi": N_("Baranyi e Roberts (1994): un modello di crescita classico, con la fase di adattamento.\n"
                  "Qui non usa i batteri lattici."),
    "incertezza": N_("Incertezza di misura: quanto può sbagliare la conta di laboratorio, in log10.\n"
                     "Circa 0,5 log per Listeria con EN ISO 11290-2 (guida EURL)."),
    "sd_t": N_("Variabilità della temperatura: deviazione standard (sd) della temperatura di ogni fase, in °C.\n"
               "0 = temperature esatte."),
    "cv_mu": N_("Incertezza di μmax (CV, coefficiente di variazione): opzione avanzata.\n"
                "Lasciala vuota se non hai una fonte per questo valore."),
    "mc": N_("Monte Carlo: si ripete il calcolo molte volte con valori un po' diversi.\nDa qui vengono gli intervalli."),
    "seme": N_("Seme (seed): il numero che fa partire i valori casuali.\nStesso seme = stessi risultati."),
    "n_c": N_("n: quante unità si analizzano.\nc: quante unità possono superare il limite senza bocciare il lotto."),
    "lod": N_("LOD (limite di rilevabilità): la conta più bassa che il metodo riesce a misurare, in ufc/g."),
    "sigma": N_("σ (sigma): quanto cambia la concentrazione da un'unità all'altra del lotto, in log10.\n"
                "σ piccola = lotto omogeneo; σ grande = contaminazione a macchie."),
    "mu": N_("μ (mu): la concentrazione media del lotto, in log10 ufc/g."),
    "delta": N_("δ (potenziale di crescita): di quanti log cresce Listeria nel periodo.\n"
                "Sopra 0,5 log il prodotto favorisce la crescita (guida EURL)."),
    "ufc": N_("ufc (unità formanti colonia, CFU in inglese): le cellule vive contate in piastra."),
    "porzione": N_("Porzione analitica: i grammi analizzati per ogni unità (di solito 25 g)."),
    "fbo": N_("L'operatore (OSA) ha dimostrato all'autorità che Listeria resta sotto 100 ufc/g per tutta la shelf-life?\n"
              "Se sì vale il limite 100 ufc/g; se no vale l'assenza in 25 g."),
    "mle": N_("MLE (stima di massima verosimiglianza): i valori di μ e σ che rendono più probabili i risultati."),
    "miscela": N_("Modello a miscela: una parte delle unità senza Listeria, le altre contaminate."),
    "oc": N_("Curva OC (operating characteristic): la probabilità di accettare il lotto per ogni concentrazione media."),
    "clopper": N_("Intervallo di Clopper-Pearson: l'intervallo esatto per una proporzione (qui, le unità positive)."),
    "starter": N_("Starter: batteri lattici aggiunti all'impasto.\nCon lo starter partono tanti; senza (fermentazione spontanea) pochi."),
}


def termine(chiave):
    return _(TERMINI[chiave])
