# Revisione scientifica del motore di crescita (da PMN)

Data: 3 novembre 2026. Domanda: il motore di PMN è giusto scientificamente e affidabile per la microbiologia predittiva?

## Risposta breve

Sì, come implementazione del modello di FSSP 4.0: è identico al programma originale e il modello è pubblicato e validato su carne e pesce. Sui salumi fermentati, però, si lavora in parte fuori dal campo di validità. I numeri vanno letti come ordini di grandezza, non come prova: per una prova servono i challenge test.

## Prove

- **Identico a FSSP.**
  - ErmChek contro FSSP.Models.dll 1.1.0.21167: 23 casi su 23, differenza massima 8,9 × 10⁻¹⁶ log, minuto per minuto, con lag e con batteri lattici. I dettagli sono in `tests/validation_fssp.md`.
  - PMN: 382 casi su 382 (prova F1).
- **Equazioni.** Modello "cardinal parameter" per μmax, con termini per:
  - temperatura, aw, pH;
  - sei acidi organici in forma non dissociata;
  - CO₂, fenoli del fumo, nitrito.

  A questo si aggiungono:
  - le interazioni fra i fattori e il confine crescita/non crescita (ψ, ξ) di Le Marc et al. 2002;
  - un modello primario logistico con il tempo di ritardo relativo di 4,5;
  - l'effetto Jameson per i batteri lattici.

  La struttura corrisponde a quella pubblicata (Mejlholm & Dalgaard 2009; LAB 2013; Jameson 2007b e 2015).
- **Parametri.** μref 0,419 h⁻¹, Tmin −2,83 °C, pHmin 4,97, awmin 0,923, CO₂max 3.140 ppm, fenoli max 32 ppm, nitrito max 350 ppm e le MIC degli acidi sono quelli del modello pubblicato e di FSSP. Sono in `params/fssp.yaml`; tabella e pagina sono ancora da completare.
- **Prestazioni pubblicate.**
  - Validazione internazionale su 1.014 risposte di crescita in carne, pesce, pollame e latticini: fattore di bias 1,0 e fattore di accuratezza 1,5 (Mejlholm et al. 2010, doi:10.1016/j.ijfoodmicro.2010.04.026).
  - Confine crescita/non crescita giusto nell'89 % dei casi.

## Limiti per i salumi (dove fare attenzione)

1. **Campo di validità per Lm:** 2-25 °C, pH 5,6-7,7, sale nella fase acquosa 0,7-9 %. Un salame fresco a pH 5,3-5,5 è un'estrapolazione, e ErmChek lo segnala.
2. **Listeria più batteri lattici sotto pH 6.** In insalate di mare con pH < 6 il modello combinato ha previsto non crescita dove Lm cresceva (Mejlholm & Dalgaard 2015, doi:10.1016/j.fm.2014.07.005). Nei salumi fermentati il freno dei batteri lattici può quindi essere sovrastimato. Avviso `JAMESON_PH_SOTTO_6`.
3. **Nessuna inattivazione.** Durante fermentazione e asciugatura Lm spesso cala, ma il modello non lo prevede. La back-calculation dà quindi un valore minimo. Per decisione del responsabile del progetto non si aggiunge un modello di inattivazione non documentato.
4. **Condizioni per fasi.** Il modello ricalcola μmax a ogni fase (approccio dinamico standard, Baranyi & Roberts 1994). Il pH che cambia nel tempo, però, non è validato da FSSP.
5. **I batteri lattici del modello sono Lactobacillus spp. psicrotolleranti** (L. sakei, L. curvatus). Su Leuconostoc, Weissella e Carnobacterium le prestazioni sono inaccettabili (Mejlholm & Dalgaard 2013).

## Salmonella

Nessun modello pubblicato è validato su carne e include anche il nitrito (ricerca in `params/salmonella_ricerca.md`). Il candidato più vicino è Coroller et al. 2015 (salsicce di maiale essiccate, senza nitrito), ma non ho potuto verificarne i parametri. Per la regola del responsabile del progetto, ErmChek offre per Salmonella solo il Modulo A (criteri e statistica).
