# ErmChek core API — read the code for details

Python: `.venv\Scripts\python.exe` (PySide6 6.12.0, numpy, scipy, matplotlib 3.11.2, PyYAML, openpyxl, reportlab 4.4.4, pytest, pytest-qt, pymupdf). Run from project root. Git: local commits only, never push.

## Shared helpers
- `ermchek/lingua.py`: `_(testo_it, **campi)` translates (Italian source string is the key), `N_()` marks constants, `imposta("it"|"en")`, `attuale()`, number helpers `separatori`, `virgola`, `leggi_numero(testo)` (IT "1.000,5" / EN "1,000.5"), `salvata()`/`salva(codice)` (QSettings "ErmChek"). English catalogs: every `ermchek/i18n/*.json` is merged ({italian: english}). Each module owner writes its OWN json file.
- `ermchek/testi.py`: `avviso(dict)` and `errore(ValueError)` turn core codes into sentences; dicts ESITI, MOTIVI, INTERPRETAZIONI, CATEGORIE.
- `ermchek/percorsi.py`: `risorsa(*parti)` -> path of a data file both from source and from the PyInstaller bundle (sys._MEIPASS). Data: `params/fssp.yaml` (parameters + `fonti` = full citations with DOI), `criteria.yaml`, `assets/logo/ErmChek_logo.png` (2172x724 RGBA, black bacillus with flagellum on the left + word "ErmChek"; never redraw or alter it, only resize).
- `ermchek/__init__.py`: `__version__ = "1.0.0"`.
- `ermchek/core/fssp/validita.py`: `numero_it(v, cifre=2)` number formatted in current language.

## Module A: ermchek/core/conformita.py, ermchek/core/criteri.py
- Results: `assente(massa_g=25.0)`, `conta(ufc_g)`, `sotto_lod(lod_ufc_g=10.0)`, `conta_in_massa(ufc, massa_g=25.0)` (5000 in 25 g -> conta(200); 0 -> assente).
- `griglia_pattern(risultati, sigmas=(0.5,0.8,1.0,1.5,2.0), mu_grid=None)` -> {sigma, p_max, mu_ottimale (arrays), coefficiente}
- `generazioni(a_ufc_g, da_ufc_g=10.0)` -> {aumento_log, generazioni}
- `replica_script()` -> list[str] (6 lines identical to the original script)
- `mle_lognormale(r)` -> {mu, sigma, log_verosimiglianza, k}; `mle_miscela(r)` -> {pi, mu, sigma, log_verosimiglianza, k}
- `confronto_modelli(r)` -> {lognormale, miscela, aic_lognormale, aic_miscela, lr, p_valore}
- `interpretazione(r, alfa=0.05)` -> {codice: LOTTO_OMOGENEO|CONTAMINAZIONE_LOCALIZZATA, p_valore, lr, aic_lognormale, aic_miscela, pi, alfa}
- `curva_oc(n, c, sigma, porzione_g, mu_values, criterio)` criterio "presenza_assenza"|"enumerazione" -> ndarray P(accept)
- `prevalenza(k, n, conf=0.95)` -> {stima, inferiore, superiore, conf}; `n_necessario(p, conf=0.95)` -> int
- `monte_carlo_pattern(mu, sigma, risultati, n_sim=1_000_000, seed=20260701)` -> {p_mc, errore_standard, p_analitica, n_sim, seed} (use n_sim 200000 in GUI)
- criteri: `carica_criteri()` -> {criteri: [rows with id, patogeno (listeria|salmonella), categoria, n, c, limite{tipo assenza massa_g | max_ufc_g valore}, metodo, fase, riferimento, valido_dal, valido_fino, fbo_dimostra_100], nota_6, potenziale_crescita}; `esito_normativo(risultati, categoria, fbo_dimostra_100: bool, data_campionamento "AAAA-MM-GG", fase_campionamento=None|"immesso_sul_mercato_shelf_life"|"prima_di_lasciare_controllo_osa")` -> {esito CONFORME|NON_CONFORME|NON_VALUTABILE, riga, motivo, unita_oltre_limite, n_richiesto, n_analizzato, fase}; `categoria_automatica(ph, aw, shelf_life_giorni, potenziale_crescita_log=None)` -> {categoria "1.2"|"1.3"|None, motivo}.
- Listeria categories 1.1/1.2/1.3; Salmonella categories 1.4,1.5,1.6,1.7,1.8 (salami),1.9,1.28 (presence/absence only).

## Module B: ermchek/core/crescita.py
- `Fase(ore, temperatura, ph, aw=None, sale_fase_acquosa=None, nitrito=0.0, acidi={}, fenoli=0.0, co2=0.0)` — give aw OR sale_fase_acquosa (else ValueError "AW_OPPURE_SALE"). acidi keys: lattico, acetico, diacetato, citrico, sorbico, benzoico (ppm in water phase).
- `wps(nacl_prodotto, umidita)` -> water-phase salt %.
- `leggi_csv_temperature(path)` -> [(ore, T)]; `applica_temperature(fasi, punti)` -> new phases.
- `simula(fasi, n0, lab0=None, modello="fssp"|"baranyi", lag=False, gamma=1.0, ...)` -> {tempi_giorni (ndarray), log_lm (ndarray [n, points]; use [0]), log_lab (same or None), fasi: [ {ore, temperatura, ph, sale_fase_acquosa, aw, mu_lm, psi_lm, mu_lab, puo_crescere} ], crescita_possibile, avvisi: [ {codice,...} ]}
- `riassunto(sim, indice=0, limite_ufc_g=100)` -> {log_iniziale, log_finale, ufc_g_finale, delta (growth potential, log), giorni_al_limite (or None), log_lab_finale}
- `monte_carlo(fasi, n0, log_n0_sd=0, lab0=None, sd_temperatura=0, cv_mu=None, n=1000, seed=..., limite_ufc_g=100, modello=..., lag=...)` -> {sim, log_finale_p5, log_finale_p50, log_finale_p95, p_sopra_limite, n, seed, curva_p5, curva_p50, curva_p95}
- Nitrate is NOT a model input (informative field only: "il nitrato agisce solo dopo la riduzione a nitrito; inserisci il nitrito residuo misurato").

## Module C: ermchek/core/retro.py
- `retro(fasi, osservato_ufc_g, lab0=None, modello="fssp", gamma=1.0, u_misura_log=0.5, sd_temperatura=0.0, cv_mu=None, peso_pezzo_g=None, n_mc=2000, seed=...)` -> 
  {fasi, lab0, osservato_ufc_g, log_osservato, giorni, principale, peggiore, scenari (list), monte_carlo {log_n0_p2_5, log_n0_p5, log_n0_p50, log_n0_p95, log_n0_p97_5, n, seed, p_non_rilevata_25g_media}, monte_carlo_peggiore (same or None), u_misura_log, avvisi [ {codice} ], curva (simula output from the central N0), p_non_rilevata_25g}
  each scenario: {log_n0, log_n0_esplicita, delta_log, cresce, con_lab, lag, ufc_g, ufc_25g, ufc_pezzo (None if no weight)}.
  principale = with LAB, lag 0 (if lab0 given) else without LAB, lag 0. peggiore = without LAB, lag 0.
- Example preset (neutral values, not real data): fresh salami 48 h at 20 °C (pH 5.9, aw 0.965, nitrite 40) then 10 days at 12 °C (pH 5.4, aw 0.95, nitrite 20); LAB 10^5 cfu/g; Lm 300 cfu/g on day 12 -> N0 ≈ 4.05 cfu/g (≈101 cfu in 25 g).

## Owner decisions (must be respected)
- Every result starts with ONE big answer box (green/yellow/red + explicit text, never colour alone), e.g. "All'origine c'erano circa X ufc/g, cioè circa Y ufc in 25 g". Then short, airy sections. The previous one-page report was rejected as: answer not clear at the top, too dense, ugly.
- Charts: ALL text inside charts in English (titles, axes, legends), also when the UI is Italian.
- Accessibility (owner is dyslexic): large font, short sentences, one idea per line, tooltip for every term (aw, δ, LOD, σ, WPS, LAB...).
- Measurement uncertainty default 0.5 log (EURL guide on measurement uncertainty, Lm EN ISO 11290-2 ~0.5 log10). μmax uncertainty = advanced option, OFF and empty. Piece weight: set by the user in Settings, no default.
- No inactivation model (not documented): only the warning that N0 is a minimum.
- Light theme only, same look as PMN. Offline, no network.
- Salmonella: criteria + statistics only (no growth/back-calculation: no verified meat model with nitrite found; see params/salmonella_ricerca.md).
- Limits shown in Info and report: didactic and decision-support tool; does not replace challenge tests, durability studies (EURL Lm TGD v4 amendment 1, 26/02/2026, DOI 10.5281/zenodo.18783767) or the competent authority; models valid only within their validation ranges.
