# Salmonella spp. in RTE meat products: growth models and EU criteria (research notes)

Date: 2026-11-03. Read-only research. Nothing below is a parameter value to implement unless marked VERIFIED.
Sources: PubMed (NCBI E-utilities), Crossref, Europe PMC, IRTA open repository, Publications Office (CELEX).

## Part 1. Candidate Salmonella growth models

### Bottom line
- No published Salmonella model found that covers T + pH + aw + **nitrite** and is validated in fermented/cured meat.
- Two models are close to salami conditions, both gamma-concept (cardinal-type), both include growth AND inactivation:
  1. Coroller et al. 2015 (T, pH, aw, lactic acid; built in dried sausages). Best fit to independent sausage data.
  2. Pin et al. 2011 (T, pH, aw; ComBase data; "validated in several pork products"). Fail-safe overprediction of growth in sausages.
- I could NOT read the full text of either (Elsevier paywall; no open accepted manuscript found on publisher, HAL, Quadram, DTU Orbit).
  Equations and parameter tables are therefore NOT transcribed here. Do not implement from memory or from secondary descriptions.
- EFSA BIOHAZ aged-meat opinion (2023) did not model Salmonella at all (Table 1 lists L. monocytogenes, non-proteolytic C. botulinum, Y. enterocolitica, LAB, pseudomonads), and states the models used were mostly not validated in fresh meat. https://doi.org/10.2903/j.efsa.2023.7745 (PMC9850206)
- No Salmonella model by Mejlholm and Dalgaard found in PubMed (only a shrimp challenge-test paper, doi 10.1016/j.ijfoodmicro.2012.04.006). FSSP website could not be reached to re-check its model list.

### Candidate table (what was verified)

| # | Citation (DOI) | Factors | Matrix of development | Independent validation in meat | Params fully reported? |
|---|---|---|---|---|---|
| A | Coroller L, Jeuge S, Couvert O, Christieans S, Ellouze M (2015) Food Microbiol 45:266-275. https://doi.org/10.1016/j.fm.2014.06.011 | T, pH, aw, lactic acid; gamma concept for growth, extended to non-thermal inactivation (Weibull, per Austrich 2023) | Pork dried sausages, several formulations (starter type, NaCl, dextrose/lactose), dynamic process | Austrich et al. 2023 (chicken dry-fermented sausages, fuet and snack type, with/without starter): predictions inside ASZ +/-1 log for all batches. Werlang et al. 2021 (Brazilian salami, MRA 19:100177, https://doi.org/10.1016/j.mran.2021.100177): ~1 log growth in 2 d at 30 C then ~-4.9 log in 36 d at 20 C predicted, matching observations | Austrich 2023 implemented it in Excel "from the equations available in the publications", so equations are published. Table numbers and values NOT verified by me. Bf/Af NOT reported in Austrich (ASZ only). No nitrite term |
| B | Pin C, Avendano-Perez G, Cosciani-Cunico E, Gomez N, Gounadakic A, Nychas G-J, Skandamis P, Barker G (2011) Int J Food Microbiol 145 Suppl 1:S96-S102. https://doi.org/10.1016/j.ijfoodmicro.2010.09.025 | T, pH, aw; probability of growth + growth rate + inactivation rate (Arrhenius-type, per Austrich 2023) | ComBase data (broth and foods, >700 records per Quadram summary) | Abstract: "validated in several pork products" (products not named in abstract). Austrich 2023: overpredicted early growth in DFS (+1 log fuet, +3.7 to 4 log snack type; observed much less) = fail-safe. No lactic acid, no nitrite | Equations published (implemented by Austrich 2023). Values NOT verified by me |
| C | Moller COA, Ilg Y, Aabo S, Christensen BB, Dalgaard P, Hansen TB (2013) Food Microbiol 34:284-295. https://doi.org/10.1016/j.fm.2012.10.010 | T only (4-38 C); lag, mu_max, Nmax; expanded Jameson-effect and Lotka-Volterra with natural microbiota | Sterile ground pork | Challenge tests in ground pork 9.4-24.1 C | Not checked (paywall). T only: unusable for pH/aw/nitrite |
| D | Velugoti PR et al. (2011) Food Microbiol 28:796-803. https://doi.org/10.1016/j.fm.2010.05.007 | T only (10-45 C), modified Ratkowsky, Baranyi primary | Sterile ground pork | Dynamic T profiles; RMSE, Af, Bf "satisfactory"; authors advise use only above 7 C | T only |
| E | Haque M, Wang B, Mvuyekure AL, Chaves BD (2024) Int J Food Microbiol 422:110808. https://doi.org/10.1016/j.ijfoodmicro.2024.110808 | T only (10-40 C), competition with APC | Raw ground pork | Dynamic profiles, 90% residuals in APZ | T only |
| F | Gwak E et al. (2016) Asian-Australas J Anim Sci 29:1013-1021. https://doi.org/10.5713/ajas.15.0713 | NaCl 0-1.75%, NaNO2 0-120 ppm, T 4-15 C, aerobic/anaerobic; logistic growth/no-growth | Nutrient broth | Compared with frankfurter data | Probability model only; no pH, no aw, broth-derived; low NaCl range (salami has 2.5-3.5%) |
| G | Oscar TP (2006, 2008, 2015) J Food Prot 69:2048; 71:1135; 78:1819 (doi 10.4315/0362-028x-69.9.2048; 10.4315/0362-028x-71.6.1135; 10.4315/0362-028X.JFP-15-093) | T only | Chicken meat, chicken frankfurters | Yes (APZ/PI) | T only, poultry |
| H | Tirloni E, Stella S, Bernardi C, Rosshaug PS (2021) LWT 143 (ricotta) | T, pH, lactic/citric/acetic acids, cardinal | Ricotta cheese | Bf 1.10-1.11 in ricotta | Dairy, not meat: excluded |

Inactivation-only models specific to salami (useful for the "process lethality" question, not for growth):
- Bonilauri P et al. (2019) Meat Sci 157:107869, Italian salami, Salmonella reduction vs end pH, aw, seasoning time, calibre. https://doi.org/10.1016/j.meatsci.2019.06.005 ; update Meat Sci 2021 177:108506 https://doi.org/10.1016/j.meatsci.2021.108506 (with corrigenda 108528/108529).
- Serra-Castello C et al. (2021) Int J Food Microbiol 346:109160, Weibull delta/p vs aw and storage T in DFS, up to 80% in ASZ. https://doi.org/10.1016/j.ijfoodmicro.2021.109160
- Hwang C-A et al. (2009) Int J Food Microbiol 129:244-252, soudjouk, polynomial survival. https://doi.org/10.1016/j.ijfoodmicro.2008.12.003 (fail-dangerous in Austrich 2023).
- Austrich et al. (2023) Microorganisms 11:432 (open access, evaluation of A, B and Hwang). https://doi.org/10.3390/microorganisms11020432 , PDF: https://repositori.irta.cat/bitstream/handle/20.500.12327/2115/Austrich_Assessing_2023.pdf

### Recommendation
- Strict criteria (a)+(b) for salami-like conditions (pH 5-6, aw 0.93-0.98, nitrite, 4-25 C): **not met by any model found.** No validated Salmonella model includes nitrite.
- Without nitrite, Coroller et al. 2015 is the only candidate developed and independently checked in fermented sausages (pork origin, plus chicken DFS and Brazilian salami evaluations). It is a reasonable basis IF the full text is obtained and the equations and parameter table are transcribed from it, then re-checked on the Austrich 2023 open data (Tables 1-2 give pH, aw, lactic acid, T and counts).
- Pin et al. 2011 could serve as a conservative (fail-safe) cross-check, again only after reading the paper.
- Action needed from the owner: obtain the PDFs of Coroller 2015 and Pin 2011 (institutional access). Until then ErmChek should not offer a Salmonella growth prediction; it can state that the EU criterion is absence in 25 g (row 1.8) and that salami safety for Salmonella rests on process lethality (see inactivation models above).

## Part 2. Reg. (EC) 2073/2005, Annex I, Chapter 1 (consolidated 01.07.2026)

Source: CELEX 02005R2073-20260701, retrieved via content negotiation (Accept: application/xhtml+xml) from
http://publications.europa.eu/resource/celex/02005R2073-20260701 (cellar 98103e97-69be-11f1-ae88-01aa75ed71a1). Header: "02005R2073 - EN - 01.07.2026 - 010.001". Last amendment listed: M11 = Reg. (EU) 2024/2895 of 20 Nov 2024.
For all rows below: n = 5, c = 0, m = M (footnote 2: "For points 1.1-1.24, 1.27a, 1.28-1.30 m = M").
Stage for all rows: "Products placed on the market during their shelf-life".

| Row | Food category | Organism | n | c | Limit | Method |
|---|---|---|---|---|---|---|
| 1.4 | Minced meat and meat preparations intended to be eaten raw | Salmonella | 5 | 0 | Not detected in 25 g | EN ISO 6579-1 |
| 1.5 | Minced meat and meat preparations made from poultry meat intended to be eaten cooked | Salmonella | 5 | 0 | Not detected in 25 g | EN ISO 6579-1 |
| 1.6 | Minced meat and meat preparations from species other than poultry intended to be eaten cooked | Salmonella | 5 | 0 | Not detected in 10 g | EN ISO 6579-1 |
| 1.7 | Mechanically separated meat (MSM) (footnote 7) | Salmonella | 5 | 0 | Not detected in 10 g | EN ISO 6579-1 |
| 1.8 | Meat products intended to be eaten raw, excluding products where process or composition eliminate the salmonella risk | Salmonella | 5 | 0 | Not detected in 25 g | EN ISO 6579-1 |
| 1.9 | Meat products made from poultry meat intended to be eaten cooked | Salmonella | 5 | 0 | Not detected in 25 g | EN ISO 6579-1 |
| 1.28 | Fresh poultry meat (footnote 18) | S. Typhimurium (fn 19, not read), S. Enteritidis | 5 | 0 | Not detected in 25 g | EN ISO 6579-1 (detection) + White-Kauffmann-Le Minor (serotyping) |

Key wording (short quotes):
- Row 1.8: "excluding products where the manufacturing process or the composition of the product will eliminate the salmonella risk".
- Footnote 7 (MSM): applies to MSM "produced with the techniques referred to in paragraph 3" of Reg. 853/2004 Annex III Sec. V Ch. III.
- Interpretation: "satisfactory, if all the values observed indicate the absence of the bacterium".
- Art. 6(1): cooked-meat batches must be labelled on "the need for thorough cooking prior to consumption".
- Row 1.30 (reptile meat, not detected in 25 g) exists but is not relevant to salumi.
- Note: there is no Salmonella row for meat products "intended to be eaten cooked" of non-poultry species in Chapter 1 (only 1.9 for poultry).

Relevance for ErmChek: Fresh and dry salami fall under row 1.8 (meat products intended to be eaten raw) unless the operator shows the process eliminates the risk.
