# ErmChek in breve

ErmChek è un programma per Windows, gratuito e senza internet, che aiuta a ragionare su *Listeria monocytogenes* negli alimenti pronti, soprattutto nei salumi. Risponde a tre domande:

- **A. Il lotto è conforme?** Confronta i risultati con i criteri di legge (Reg. CE 2073/2005, come modificato dal Reg. UE 2024/2895) e dice se il quadro fa pensare a una contaminazione omogenea o localizzata.
- **B. Quanto cresce Listeria nel tempo?** Previsione in avanti, dalle condizioni del prodotto.
- **C. Quanta Listeria c'era all'inizio?** Previsione all'indietro (back-calculation): dal valore trovato oggi alla concentrazione al giorno 0.

Per Salmonella c'è solo la domanda A, perché non esiste un modello di crescita pubblicato e validato su carne con nitrito.

ErmChek è uno strumento didattico e di supporto alle decisioni. Non sostituisce i challenge test, gli studi di durabilità né il giudizio dell'autorità competente.

## L'esempio che seguiamo

Un salame fresco **di esempio** (valori inventati, non dati reali):

- 2 giorni a 20 °C, pH 5,9, aw 0,965, nitrito 40 mg/kg;
- poi 10 giorni a 12 °C, pH 5,4, aw 0,95, nitrito 20 mg/kg;
- batteri lattici all'inizio: 10⁵ ufc/g.

Al giorno 12 si trovano **300 ufc/g** di Listeria. Quanta ce n'era al giorno 0?

## 1. Quanto velocemente cresce Listeria in ogni fase

$$\mu_{max} = \mu_{ref} \left(\frac{T - T_{min}}{T_{ref} - T_{min}}\right)^2 \cdot \frac{a_w - a_{w,min}}{1 - a_{w,min}} \cdot \left(1 - 10^{\,pH_{min} - pH}\right) \cdot \left(\frac{NIT_{max} - NIT}{NIT_{max}}\right)^2 \cdot \ldots \cdot \xi$$

**Che cosa significa.** La velocità massima di crescita (μmax, per ora) parte da quella che Listeria avrebbe a 25 °C senza ostacoli (μref). Poi la si moltiplica per un numero fra 0 e 1 per ogni ostacolo: temperatura, acqua libera (aw), acidità (pH), nitrito (NIT) e, se presenti, acidi organici, CO₂ e fumo. Ogni ostacolo vale 1 quando non frena e 0 quando blocca. L'ultimo fattore (ξ) tiene conto degli ostacoli che agiscono insieme: vicino al confine fra crescita e non crescita la velocità scende fino a zero. È il modello "cardinal parameter" di Mejlholm & Dalgaard (2009), con il confine di Le Marc et al. (2002).

**Con i numeri della fase 1 (20 °C).** Il calcolo procede ostacolo per ostacolo:
- Si parte da μref = 0,419 h⁻¹.
- Temperatura: (22,83 / 27,83)² = 0,673, quindi 0,282.
- aw: (0,965 − 0,923) / (1 − 0,923) = 0,547, quindi 0,154.
- pH: 1 − 10^(4,97 − 5,9) = 0,882, quindi 0,136.
- Nitrito: ((350 − 40) / 350)² = 0,785, quindi **μmax = 0,107 h⁻¹**.

Qui gli ostacoli sono lontani dal confine (ψ = 0,06, dove ψ = 1 significa "non cresce"), quindi ξ = 1. Nella fase 2, a 12 °C con pH e aw più bassi, μmax scende a 0,023 h⁻¹.

## 2. Come cresce nel tempo, insieme ai batteri lattici

$$\frac{dN}{dt} = \mu_{max} \cdot N \cdot \left(1 - \frac{N}{N_{max}}\right) \cdot \left(1 - \frac{N_{LAB}}{N_{max,LAB}}\right)$$

**Che cosa significa.** Listeria cresce in proporzione a quanta ce n'è (N), finché non si avvicina al suo massimo (Nmax, circa 3 × 10⁸ ufc/g). L'ultima parentesi è l'effetto Jameson: quando i batteri lattici arrivano al loro massimo, la parentesi diventa zero e Listeria si ferma. Il calcolo procede a passi di un minuto e a ogni fase usa la μmax di quella fase, come il programma FSSP del DTU.

**Con i numeri.** I batteri lattici, partendo da 10⁵ ufc/g, arrivano al massimo verso il giorno 3,8. Fino a quel momento Listeria cresce di 1,87 logaritmi, cioè circa 74 volte; dopo resta ferma. Senza batteri lattici crescerebbe di 4,65 logaritmi, cioè circa 45.000 volte.

## 3. Quanta Listeria c'era all'inizio

$$\log N_0 = \log N_t - \Delta\log$$

**Che cosa significa.** La concentrazione iniziale è quella trovata oggi divisa per quanto Listeria è cresciuta. Il programma risolve il modello anche in modo esatto (metodo numerico di Brent) e controlla che le due strade diano lo stesso numero. Poi ripete il calcolo migliaia di volte (Monte Carlo), facendo variare il risultato di laboratorio di ±0,5 log, l'incertezza tipica della conta di Listeria secondo la guida EURL. Così ottiene un intervallo.

**Con i numeri.** log N0 = log 300 − 1,87 = 2,477 − 1,870 = 0,607, quindi **N0 ≈ 4,0 ufc/g**, cioè circa 100 ufc in 25 g. L'intervallo al 90 % va da 0,6 a 26 ufc/g. Con 100 cellule attese in 25 g, un'analisi al giorno 0 l'avrebbe quasi certamente trovata.

ErmChek mostra anche altri due scenari:
- **Senza batteri lattici (caso peggiore):** 0,0067 ufc/g. Dice quanto poca Listeria basterebbe se nulla la frenasse.
- **Con il tempo di adattamento delle cellule (lag fisiologico):** 87 ufc/g.

Il modello prevede solo crescita, mai la morte. Se durante la fermentazione Listeria è calata, all'inizio ce n'era di più: la stima è un valore minimo.

## 4. Il lotto è conforme? (statistica)

$$P(\text{negativo in } m \text{ g} \mid c) = e^{-m \cdot c}$$

**Che cosa significa.** Se un salume contiene c ufc/g, la probabilità che una porzione di m grammi non contenga nemmeno una cellula segue la legge di Poisson. ErmChek assume che le concentrazioni fra le unità di un lotto seguano una distribuzione log-normale. Con il metodo della massima verosimiglianza stima quale contaminazione spiega meglio i risultati, anche quando alcuni sono "non rilevata" o "sotto il limite". Poi confronta un lotto omogeneo con un lotto in cui solo alcune unità sono contaminate (modello a miscela).

**Con i numeri.** Una porzione di 25 g di un prodotto a 0,04 ufc/g è negativa con probabilità e^(−25 × 0,04) = e^(−1) = 0,37. Se 4 unità su 5 sono negative in 25 g e una ha 9.000 ufc/g, un lotto omogeneo non lo spiega: il programma conclude per una contaminazione localizzata.

## Quanto è affidabile

- **Uguale a FSSP.** Su 23 scenari ErmChek dà gli stessi numeri del programma FSSP 4.0 del DTU, minuto per minuto, con una differenza massima di 10⁻¹⁵ log (`tests/validation_fssp.md`).
- **Validazione pubblicata del modello per Listeria.** Su 1.014 curve in carne, pesce e latticini, fattore di bias 1,0 e fattore di accuratezza 1,5 (Mejlholm et al. 2010). In pratica la velocità è giusta in media, con un errore tipico di circa ±50 %.
- **Limiti.**
  - Il modello è validato per pH 5,6-7,7 e 2-25 °C: fuori da questi valori ErmChek avvisa.
  - Sotto pH 6 il freno dei batteri lattici è meno affidabile (Mejlholm & Dalgaard 2015).
  - Il modello non prevede la morte di Listeria.

## Fonti principali

- Mejlholm O, Dalgaard P (2009). J Food Prot 72:2132-2143. doi:10.4315/0362-028x-72.10.2132
- Mejlholm O et al. (2010). Int J Food Microbiol 141:137-150. doi:10.1016/j.ijfoodmicro.2010.04.026
- Mejlholm O, Dalgaard P (2013). Int J Food Microbiol 167:244-260. doi:10.1016/j.ijfoodmicro.2013.09.013
- Mejlholm O, Dalgaard P (2015). Food Microbiol 46:1-14. doi:10.1016/j.fm.2014.07.005
- Le Marc Y et al. (2002). Int J Food Microbiol 73:219-237. doi:10.1016/s0168-1605(01)00640-7
- Baranyi J, Roberts TA (1994). Int J Food Microbiol 23:277-294. doi:10.1016/0168-1605(94)90157-0
- Reg. (CE) 2073/2005 e Reg. (UE) 2024/2895; EURL Lm Technical Guidance Document v4, emendamento 1 (2026), doi:10.5281/zenodo.18783767
