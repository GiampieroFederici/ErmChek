# ErmChek in brief

ErmChek is a free, offline Windows program that helps you reason about *Listeria monocytogenes* in ready-to-eat foods, especially cured meats. It answers three questions:

- **A. Is the lot compliant?** It compares results with the legal criteria (Reg. EC 2073/2005 as amended by Reg. EU 2024/2895). It also says whether the pattern points to homogeneous or localised contamination.
- **B. How much does Listeria grow over time?** A forward prediction from the product conditions.
- **C. How much Listeria was there at the start?** A backward prediction (back-calculation): from the count found today to the concentration on day 0.

For Salmonella only question A is available. No published growth model validated in meat with nitrite exists.

ErmChek is a teaching and decision-support tool. It does not replace challenge tests, durability studies or the competent authority.

## The example we follow

A fresh salami **example** (made-up values, not real data):

- 2 days at 20 °C, pH 5.9, aw 0.965, nitrite 40 mg/kg;
- then 10 days at 12 °C, pH 5.4, aw 0.95, nitrite 20 mg/kg;
- lactic acid bacteria at the start: 10⁵ CFU/g.

On day 12 the lab finds **300 CFU/g** of Listeria. How much was there on day 0?

## 1. How fast Listeria grows in each phase

$$\mu_{max} = \mu_{ref} \left(\frac{T - T_{min}}{T_{ref} - T_{min}}\right)^2 \cdot \frac{a_w - a_{w,min}}{1 - a_{w,min}} \cdot \left(1 - 10^{\,pH_{min} - pH}\right) \cdot \left(\frac{NIT_{max} - NIT}{NIT_{max}}\right)^2 \cdot \ldots \cdot \xi$$

**What it means.** The maximum growth rate (μmax, per hour) starts from the rate Listeria would have at 25 °C with no hurdles (μref). It is then multiplied by a number between 0 and 1 for each hurdle: temperature, free water (aw), acidity (pH), nitrite (NIT) and, if present, organic acids, CO₂ and smoke. A hurdle is 1 when it does not slow growth and 0 when it stops it. The last factor (ξ) handles hurdles acting together: near the growth/no-growth boundary the rate falls to zero. This is the cardinal parameter model of Mejlholm & Dalgaard (2009), with the boundary of Le Marc et al. (2002).

**With the numbers of phase 1 (20 °C).** The calculation goes hurdle by hurdle:
- Start from μref = 0.419 h⁻¹.
- Temperature: (22.83 / 27.83)² = 0.673, so 0.282.
- aw: (0.965 − 0.923) / (1 − 0.923) = 0.547, so 0.154.
- pH: 1 − 10^(4.97 − 5.9) = 0.882, so 0.136.
- Nitrite: ((350 − 40) / 350)² = 0.785, so **μmax = 0.107 h⁻¹**.

The hurdles here are far from the boundary (ψ = 0.06, where ψ = 1 means "no growth"), so ξ = 1. In phase 2, at 12 °C with lower pH and aw, μmax drops to 0.023 h⁻¹.

## 2. How it grows over time, together with lactic acid bacteria

$$\frac{dN}{dt} = \mu_{max} \cdot N \cdot \left(1 - \frac{N}{N_{max}}\right) \cdot \left(1 - \frac{N_{LAB}}{N_{max,LAB}}\right)$$

**What it means.** Listeria grows in proportion to how much there is (N), until it approaches its maximum (Nmax, about 3 × 10⁸ CFU/g). The last bracket is the Jameson effect: when lactic acid bacteria reach their maximum, the bracket becomes zero and Listeria stops. The calculation runs in one-minute steps and uses the μmax of each phase, as the FSSP program by DTU does.

**With the numbers.** Starting from 10⁵ CFU/g, the lactic acid bacteria reach their maximum around day 3.8. Up to then Listeria grows by 1.87 log, about 74-fold; afterwards it stays still. Without lactic acid bacteria it would grow by 4.65 log, about 45,000-fold.

## 3. How much Listeria was there at the start

$$\log N_0 = \log N_t - \Delta\log$$

**What it means.** The starting concentration is today's count divided by how much Listeria grew. The program also solves the model exactly (Brent's numerical method) and checks that both routes give the same number. It then repeats the calculation thousands of times (Monte Carlo), letting the lab result vary by ±0.5 log, the typical uncertainty of Listeria counts according to the EURL guide. This gives an interval.

**With the numbers.** log N0 = log 300 − 1.87 = 2.477 − 1.870 = 0.607, so **N0 ≈ 4.0 CFU/g**, about 100 CFU in 25 g. The 90 % interval runs from 0.6 to 26 CFU/g. With 100 cells expected in 25 g, a test on day 0 would almost certainly have found it.

ErmChek also shows two other scenarios:
- **Without lactic acid bacteria (worst case):** 0.0067 CFU/g. It shows how little Listeria would be enough if nothing slowed it down.
- **With the cells' adaptation time (physiological lag):** 87 CFU/g.

The model predicts growth only, never death. If Listeria declined during fermentation, there was more at the start: the estimate is a minimum.

## 4. Is the lot compliant? (statistics)

$$P(\text{negative in } m \text{ g} \mid c) = e^{-m \cdot c}$$

**What it means.** If a product contains c CFU/g, the probability that an m-gram portion holds not even one cell follows the Poisson law. ErmChek assumes that concentrations among the units of a lot follow a log-normal distribution. With maximum likelihood it estimates which contamination best explains the results, including "not detected" and "below the limit" results. It then compares a homogeneous lot with a lot where only some units are contaminated (mixture model).

**With the numbers.** A 25 g portion of a product at 0.04 CFU/g is negative with probability e^(−25 × 0.04) = e^(−1) = 0.37. If 4 units out of 5 are negative in 25 g and one has 9,000 CFU/g, a homogeneous lot cannot explain it: the program concludes localised contamination.

## How reliable it is

- **Same as FSSP.** In 23 scenarios ErmChek gives the same numbers as the FSSP 4.0 program by DTU, minute by minute, with a maximum difference of 10⁻¹⁵ log (`tests/validation_fssp.md`).
- **Published validation of the Listeria model.** On 1,014 growth curves in meat, seafood and dairy, bias factor 1.0 and accuracy factor 1.5 (Mejlholm et al. 2010). In practice the rate is right on average, with a typical error of about ±50 %.
- **Limits.**
  - The model is validated for pH 5.6-7.7 and 2-25 °C: outside these values ErmChek warns you.
  - Below pH 6 the brake from lactic acid bacteria is less reliable (Mejlholm & Dalgaard 2015).
  - The model does not predict the death of Listeria.

## Main sources

- Mejlholm O, Dalgaard P (2009). J Food Prot 72:2132-2143. doi:10.4315/0362-028x-72.10.2132
- Mejlholm O et al. (2010). Int J Food Microbiol 141:137-150. doi:10.1016/j.ijfoodmicro.2010.04.026
- Mejlholm O, Dalgaard P (2013). Int J Food Microbiol 167:244-260. doi:10.1016/j.ijfoodmicro.2013.09.013
- Mejlholm O, Dalgaard P (2015). Food Microbiol 46:1-14. doi:10.1016/j.fm.2014.07.005
- Le Marc Y et al. (2002). Int J Food Microbiol 73:219-237. doi:10.1016/s0168-1605(01)00640-7
- Baranyi J, Roberts TA (1994). Int J Food Microbiol 23:277-294. doi:10.1016/0168-1605(94)90157-0
- Reg. (EC) 2073/2005 and Reg. (EU) 2024/2895; EURL Lm Technical Guidance Document v4, amendment 1 (2026), doi:10.5281/zenodo.18783767
