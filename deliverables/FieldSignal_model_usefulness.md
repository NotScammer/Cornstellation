# Cornstellation presents FieldSignal

**Satellite-informed forecasts for better hybrid selection across environments.**

FieldSignal helps a maize research team decide which hybrids deserve further attention and which hybrid–management combinations need another round of testing. It combines satellite observations with planting date, nitrogen rate, recorded irrigation, and hybrid identity to forecast grain yield. Its current evidence comes from 84 hybrids and 2,131 labeled plots across five locations in 2022.

## 1. Satellite observations improve day-90 yield forecasts

Each evaluation location was excluded from model training. These are predictions at unseen locations within 2022, not predictions from models trained on the same plots.

| Model | Day-90 mean absolute error (bu/ac) |
|---|---:|
| Training-mean baseline | 55.1 |
| CatBoost, agronomy only | 72.1 |
| CatBoost, agronomy plus imagery | 44.0 |
| Ridge, agronomy only | 66.0 |
| Ridge, agronomy plus imagery | 39.4 |

The imagery-enhanced CatBoost model reduced error by 20.2% versus the training-mean baseline. The exploratory imagery-enhanced Ridge model reduced error by 28.4%. Both also improved over their corresponding agronomy-only models. This supports using imagery as additional predictive information in this evaluation; it does not establish which physiological mechanism causes the improvement. MAE is average absolute error, not a per-plot confidence interval.

**Decision value:** provide a more informative expectation of yield at a location whose harvest labels are unavailable, helping teams focus their review of trial performance. Absolute errors remain substantial, so these forecasts support prioritization rather than guaranteed yield commitments.

## 2. Forecasts recover some of the strongest hybrids

At day 90, Ridge with imagery recovered an average of **5.0 of each site's observed top 10 hybrids**. CatBoost with imagery recovered **4.6**. Randomly selecting 10 of 84 hybrids would recover about **1.19** on average. This is top-10 selection overlap, not 50% yield accuracy.

Performance varied: Ridge recovered 8 of 10 at Lincoln, 6 at Crawfordsville, 5 at Ames, and 3 each at Missouri Valley and Scottsbluff. Its whole-ranking Spearman correlation at Scottsbluff was only 0.07, showing that useful average results can conceal a weak environment.

**Decision value:** build an initial watchlist of promising hybrids before harvest, then combine it with agronomist review and field observations. Do not automatically eliminate every hybrid outside the forecast top 10; the forecasts still miss strong performers.

## 3. Historical harvest results identify candidates for the next trials

Raw site yield averages range from about 41 to 165 bu/ac after balancing hybrid and treatment contributions. Directly comparing raw yields across these sites could confuse a favorable environment with a strong hybrid.

FieldSignal first averages replicates within each hybrid–environment combination. An environment is location, year, nitrogen rate, and recorded irrigation. It then ranks hybrids within that environment, averages treatment percentiles within each site, and weights sites equally.

| Observed shortlisted hybrid | Average percentile | Worst-site percentile |
|---|---:|---:|
| HOEGEMEYER 8065RR | 93.4 | 84.3 |
| SYNGENTA NK0760-3111 | 87.5 | 74.7 |
| HOEGEMEYER 7089 AMXT | 86.5 | 67.7 |
| PIONEER P0589 AMXT | 85.0 | 67.5 |
| PHW52 X PHN82 | 81.7 | 58.9 |

All five shortlisted hybrids exceeded the median at every site. These are **observed harvest findings**, separate from the forecast rankings. Some hybrid–treatment cells have only one replicate; equal weighting does not remove sampling uncertainty.

**Decision value:** advance these candidates into the next round of replicated trials, with their weakest-site performance visible. They are promising across the observed environments, not proven broadly adapted across future seasons.

## 4. Management responses require environment-specific interpretation

Matched comparisons of 150 versus 75 lb nitrogen/acre covered 84 hybrids at each of four sites, or 336 hybrid–site pairs.

| Site | Observed yield difference, 150 minus 75 lb N/acre (bu/ac) |
|---|---:|
| Ames | -23.6 |
| Crawfordsville | +15.4 |
| Lincoln | +10.9 |
| Scottsbluff | +29.2 |

The equally weighted four-site average is +8.0 bu/ac, but this hides substantial differences between locations. Missouri Valley has a single nitrogen rate and is excluded from these contrasts. Treatment placement and other conditions may contribute to the observed differences. Irrigation is site-associated, so its independent effect is not identified.

**Decision value:** choose which hybrid–nitrogen combinations and environments warrant additional testing. These observed contrasts do not justify optimal-rate, fertilizer-saving, or causal irrigation recommendations.

## 5. Earlier forecasts have different strengths and limitations

| Forecast | Day 75 MAE (bu/ac) | Day 90 MAE (bu/ac) | Top-10 overlap, day 75 → day 90 |
|---|---:|---:|---:|
| CatBoost with imagery | 45.5 | 44.0 | 4.0 → 4.6 |
| Ridge with imagery | 71.0 | 39.4 | 4.6 → 5.0 |

CatBoost at day 75 offers a preliminary signal 15 days before day 90, with only 1.5 bu/ac higher overall MAE. Ridge's absolute yield predictions improve much more over that interval. Whole-ranking performance does not always improve with time: CatBoost's mean within-site hybrid Spearman correlation fell from 0.58 at day 75 to 0.45 at day 90 even while its top-10 overlap increased. The best cutoff depends on the decision metric.

Day 60 is supporting evidence only: Missouri Valley has no eligible satellite observations, and the combined models do not beat the training-mean baseline on overall yield MAE. Cutoffs use actual acquisition dates relative to planting, so images collected after the cutoff do not enter that forecast.

**Decision value:** use day-75 results as provisional watchlists and day-90 results as updated evidence. Neither cutoff is yet established as reliable for a future season; opportunities for field intervention also depend on crop stage and local practice.

## Proposed use and next milestone

Use the observed shortlist to prioritize the next round of replicated trials. Use forecasts as an additional, imperfect signal for reviewing promising or unexpectedly weak plots. Preserve agronomist oversight and retain weak-site results in the evaluation.

Freeze the forecasting procedure and test it on an untouched 2023 dataset before claiming cross-season reliability. The additional Ridge comparisons were developed using the already examined 2022 data; they are exploratory despite training-fold-only preprocessing and nested regularization selection. No yield gains, financial returns, or causal treatment benefits have been established.

## A short pitch

“Cornstellation's FieldSignal turns satellite observations and trial records into evidence for hybrid selection. Across five locations in 2022, our historical analysis identified five hybrids that performed above the median at every site. Separately, our day-90 imagery forecast reduced yield error by 28% against a simple baseline and recovered half of each site's top 10 hybrids on average. That gives research teams a useful starting point for deciding what to inspect and what to test next. Our next step is independent validation in 2023.”

## Traceable evidence

All numerical findings come from saved project results in `outputs/broad_performance/`: `claims.json`, `yield_metrics.csv`, `ranking_metrics.csv`, `observed_hybrids.csv`, `observed_site.csv`, `site_yields.csv`, `nitrogen_pairs.csv`, and `nitrogen_sites.csv`. Model fold details are in `ridge_fold_audit.json`. MAE combines the 2,131 held-out plot predictions; ranking overlap and mean ranking correlation weight the five sites equally.
