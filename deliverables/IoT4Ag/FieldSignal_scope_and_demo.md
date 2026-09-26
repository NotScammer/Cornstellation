# FieldSignal by Cornstellation — IoT4Ag presentation package

**Satellite-informed forecasts for better hybrid selection across environments.**

The decision: inspect likely underperforming plots now, and prioritize promising hybrids for the next round of replicated trials. Our evidence covers five locations in Nebraska and Iowa in **2022**, with 84 hybrids and 2,131 labeled plots. Cross-season validation is the next milestone, not a completed result.

## The five-slide story

1. **A research decision at two time horizons.** Limited inspections this season; better trial selection next season.
2. **What imagery adds.** Hold plots, location folds, cutoffs and CatBoost settings constant. Compare nitrogen only, all agronomic records, and agronomy plus satellite observations. Include the training-mean baseline.
3. **A rule that leads to an inspection list.** At day 75, flag the lowest predicted 20% within each site. Rank by predicted yield and visit as many trial plots as capacity allows. Show a caught plot and a capacity miss.
4. **The next trials.** Present the observed five-hybrid shortlist with average and weakest-site percentiles. Show matched nitrogen contrasts by site; do not turn them into fertilizer prescriptions.
5. **What is established, and the next test.** Demonstrated spatial transfer within 2022; freeze the pipeline and evaluate untouched 2023 data. Close by proposing replicated trials of the shortlist.

## Three-minute demo

Use the deck as the main presentation; it works offline. The speaker notes provide the talk track.

If showing the dashboard, open http://127.0.0.1:8501 and keep the **Decision brief** workspace selected. Choose **day 75, Ames, 10 trial plots**. Explain that the replay date is August 2022, not a live warning this week. Show the ranked inspection list and CSV download. Increase capacity to 13 to include the retrospective example that ranked 13th. Open **What imagery adds · evaluation** to reveal harvest labels and the controlled comparison. Open **Next replicated trials · observed** for the observed shortlist. The original hybrid analysis, Ridge comparisons and scouting view remain in the sidebar.

## Evidence for the claims

| Input set | Day-75 MAE (bu/ac) | Low-yield plots found / 50 visits | Precision | Recall of 428 low-yield plots |
|---|---:|---:|---:|---:|
| Training mean | 55.1 | 7 | 14% | 1.6% |
| Nitrogen only | 59.7 | 6 | 12% | 1.4% |
| Agronomic records | 72.1 | 24 | 48% | 5.6% |
| Agronomy + satellite | 45.5 | 30 | 60% | 7.0% |

Source: `tables/model_comparison.csv`, cutoff 75, location Overall. Five independent held-out locations; 10 visits per site. Low yield means the actual bottom 20% within each site, using ceil(20% × site count). Nitrogen-only and training-mean predictions have many ties: their top-K performance depends on deterministic plot-ID ordering. Do not market the nitrogen result as a robust fivefold improvement. The stronger comparison is **six additional low-yield plots found in 50 visits versus agronomic records**.

At day 90, combined MAE is **44.0 bu/ac**, versus **55.1** for the training mean (20.2% lower). It finds **31/50** low-yield plots (62% precision; 7.2% recall). Waiting improves MAE slightly but costs 15 days; not every decision metric improves.

## Early-warning rule and action

**When:** day 75 after planting, with day 90 as a later comparison. Day 60 remains supporting evidence; Missouri Valley has no eligible imagery then.

**Signal:** a plot lies in the lowest predicted 20% of its site. The implied yield boundary is site- and date-specific. There is no validated universal NDVI or bu/ac threshold. NDVI change, image age and missing observations are supporting context only.

**Action:** send a scout to inspect stand condition, weeds, visible stress and local field conditions; record findings. The model does not identify the cause or prescribe nitrogen, irrigation or pesticide treatment.

**Capacity:** visit the lowest predictions first, up to an integer number of trial plots. These are plots within research sites, not independent commercial fields. Flagged plots beyond capacity remain in the queue. Predictions and plot ID alone determine selection; final yields are used only afterwards for evaluation.

**Evidence:** the fixed 20% screen flags 428 plots. At day 75 it captures 163 of 428 eventual low-yield plots (38.1% precision and recall); at day 90 it captures 141 (32.9%). This is a candidate screening rule evaluated retrospectively, not a threshold validated for preventable crop stress. Do not confuse 60% precision for 50 visits with 60% coverage of all low-yield plots.

## Before/after examples — retrospective Ames, day 75

| Plot | N-only forecast | Agronomy forecast | Combined forecast | Harvest | Priority |
|---|---:|---:|---:|---:|---:|
| Ames / 4233 / 19 / 5 | 106.55 | 26.34 | 73.99 | 66.18 | 1 |
| Ames / 4232 / 24 / 20 | 125.13 | 33.13 | 89.72 | 27.30 | 13 |

All yields are bu/ac. Both plots fall in the warning screen. The first is included in 10 visits; the second is a **capacity miss**, not a warning-screen miss. The second example also shows a large yield overestimate. Examples are chosen retrospectively to illustrate success and failure, not to establish average model accuracy. Source: `tables/case_examples.csv`.

## Hybrid selection and management evidence

Average replicate plots within each hybrid–environment combination. Environment means location, year, nitrogen rate and recorded irrigation. Calculate yield advantage against an equally weighted hybrid benchmark and within-environment percentiles. Average treatment percentiles within each site, then weight sites equally. Require coverage of all five sites and above-median performance in at least four; rank by average percentile and display weakest-site performance. The five selected hybrids happen to exceed the median at all five sites.

| Observed hybrid | Average percentile | Weakest site | Plots |
|---|---:|---:|---:|
| HOEGEMEYER 8065RR | 93.4 | 84.3 | 25 |
| SYNGENTA NK0760-3111 | 87.5 | 74.7 | 64 |
| HOEGEMEYER 7089 AMXT | 86.5 | 67.7 | 26 |
| PIONEER P0589 AMXT | 85.0 | 67.5 | 26 |
| PHW52 X PHN82 | 81.7 | 58.9 | 26 |

These are **observed harvest findings**, separate from forecast rankings. Some hybrid–treatment cells have only one replicate. Candidates are promising across the observed environments; they are not proven broadly adapted varieties.

For 150 minus 75 lb nitrogen/acre, matched-hybrid contrasts are Ames **−23.6**, Crawfordsville **+15.4**, Lincoln **+10.9**, and Scottsbluff **+29.2 bu/ac**. Each site has 84 matched hybrids; there are 336 hybrid-site pairs. The equal-site mean is **+8.0 bu/ac**. Differences in field placement may contribute. Missouri Valley has one nitrogen rate and is excluded. Irrigation is site-associated; no isolated irrigation effect is estimated.

At day 90, combined CatBoost recovers **4.6 of the observed top 10 hybrids per site**, with mean within-site hybrid Spearman correlation **0.451**. Exploratory combined Ridge reaches **39.4 bu/ac MAE**, **5.0/10 overlap**, and **0.477 correlation**. Ridge agronomy alone has higher rank correlation (0.527), so imagery does not improve every ranking metric. Ridge tuning uses only inner training-location folds, choosing alpha from 1, 10, 100. These additional model comparisons are development on 2022, not independent confirmation.

## Training, validation and leakage checks

CatBoost uses 400 iterations, depth 5, learning rate 0.05, RMSE loss and seed 42. Agronomic predictors are planting day-of-year, nitrogen, irrigation and hybrid. Satellite predictors summarize red, green, blue, near-infrared, red-edge and deep-blue bands, NDVI and NDRE: latest observation, change, counts, image age and missingness. Actual acquisition dates enforce the 60/75/90-day cutoffs. No yield-derived variables, harvest observations or unknown-date stand counts enter predictors. UAV imagery is outside this implemented pipeline.

Each of five evaluation folds trains on four locations and predicts the fifth. Preprocessing is fitted in training data, never in the held-out site. Identical plot cohorts support input comparisons. Final models trained on all eligible 2022 plots are stored separately; the historical dashboard uses held-out predictions. The nitrogen-only ablation follows the same folds and model settings.

Known limits: spatial transfer in one year, large site-specific bias, imperfect rankings, sparse treatment replication, no calibrated uncertainty and no causal diagnosis. The audit verifies raw-source yield labels and units; USDA state averages describe different populations and must not be used to shift predictions. See `yield_audit.md`.

## Run and reproduce

```powershell
.venv\Scripts\python.exe -m maize.decision_brief
.venv\Scripts\python.exe -m maize.decision_brief --reuse-nitrogen
.venv\Scripts\python.exe -m streamlit run dashboard.py
.venv\Scripts\python.exe -m pytest -q
```

The first command fits the nitrogen-only comparison; the second rebuilds evidence from the saved nitrogen predictions. Existing data preparation, training and unlabeled prediction commands remain in the project README. Every headline has an exported table in `tables/`; `claims.json` also records input hashes.

## Judge questions and concise answers

- **Is it across seasons?** Not yet. Five held-out locations in 2022 establish spatial-transfer evidence. Untouched 2023 validation is next.
- **Why day 75?** It offers a 15-day lead over day 90 with similar yield error and 30 versus 31 low-yield plots found in 50 visits. It is a tested decision checkpoint, not an optimized or guaranteed earliest date.
- **Why not use just nitrogen?** Nitrogen describes management intent; imagery measures crop condition. Controlled same-cohort comparisons show the gain and failures.
- **Does a flag mean nitrogen deficiency?** No. It means predicted underperformance relative to peers, requiring human inspection.
- **Will this improve yield or profit?** We have not tested intervention outcomes. The demonstrated outcome is prioritization and trial evidence.
- **What should the team do next?** Prioritize the shortlist for replicated trials, log scouting findings, freeze the forecast pipeline, and validate on 2023.
