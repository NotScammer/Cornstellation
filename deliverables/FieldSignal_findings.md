# FieldSignal: findings brief

Satellite-informed forecasts for better hybrid selection across environments.

2022 only: 84 hybrids, five locations, 2,131 labeled plots.

## Observed shortlist

| Hybrid | Average percentile | Worst-site percentile | Plots |
|---|---:|---:|---:|
| HOEGEMEYER 8065RR | 93.4 | 84.3 | 25 |
| SYNGENTA NK0760-3111 | 87.5 | 74.7 | 64 |
| HOEGEMEYER 7089 AMXT | 86.5 | 67.7 | 26 |
| PIONEER P0589 AMXT | 85.0 | 67.5 | 26 |
| PHW52 X PHN82 | 81.7 | 58.9 | 26 |

All five exceed the median at every site. Some treatment cells have one replicate. These are observed harvest findings, not forecasts.

## Matched nitrogen contrasts

- Ames: -23.6 bu/ac (150 minus 75 lb N/acre; 84 matched hybrids).
- Crawfordsville: +15.4 bu/ac (150 minus 75 lb N/acre; 84 matched hybrids).
- Lincoln: +10.9 bu/ac (150 minus 75 lb N/acre; 84 matched hybrids).
- Scottsbluff: +29.2 bu/ac (150 minus 75 lb N/acre; 84 matched hybrids).

Descriptive contrasts, not causal fertilizer or irrigation recommendations.

## Forecast evidence

Day-90 held-out MAE: training mean 55.1, CatBoost with imagery 44.0, Ridge with imagery 39.4 bu/ac.
Ridge recovered 5.0 of the observed top 10 hybrids per site on average; CatBoost recovered 4.6. Random expectation is 1.19.
Ridge comparisons are exploratory development on 2022. No cross-season validation is claimed.

Next: advance the observed shortlist to replicated trials and evaluate the frozen forecasting pipeline on 2023.