# FieldSignal yield audit

Scouting uses held-out CatBoost combined predictions; the revised capacity is an exact number of research plots, not farm fields.

## Source-label and unit checks

Checked 44,751 saved predictions across models and cutoffs against 2,131 original eligible records. Plot joins, site identities, feature labels and prediction labels match. Maximum label difference: 0 bu/ac.

yieldPerAcre used directly; no log transform or acre/moisture conversion in model pipeline. Raw grain mass, moisture and full area inputs are not provided here; author calculations cannot be independently reconstructed.

## Day-90 CatBoost combined: site means

All values below are bu/ac. These are plot-weighted means, not the treatment-balanced means used in hybrid selection.

| Site | Plots | Actual source yield | Predicted yield | Bias (predicted - actual) | USDA state mean |
|---|---:|---:|---:|---:|---:|
| Ames | 487 | 130.3 | 124.1 | -6.2 | 200.0 |
| Crawfordsville | 488 | 165.1 | 125.0 | -40.1 | 200.0 |
| Lincoln | 504 | 41.2 | 111.7 | +70.5 | 165.0 |
| MOValley | 163 | 152.5 | 152.1 | -0.3 | 200.0 |
| Scottsbluff | 489 | 143.4 | 101.7 | -41.7 | 165.0 |

## Interpretation

1. The supplied research-plot harvest yields are themselves below USDA state means at every included site. The training targets already contain this difference.
2. Scouting deliberately selects the lowest predicted-yield plots. Its selected rows are not a representative site average.
3. There are real model errors as well: day-90 CatBoost underpredicts Crawfordsville and Scottsbluff by about 40 bu/ac, but overpredicts Lincoln by about 70 bu/ac. A universal upward adjustment would worsen Lincoln.
4. USDA state yields summarize corn-for-grain production per harvested acre across a much broader population. These trials cover selected hybrids, nitrogen treatments and site-associated irrigation; neither their raw plot means nor equal-site hybrid scores estimate state yield. The exact causes of the source-data gap cannot be established from this audit.
5. We did not rescale predictions or use 2022 USDA harvest statistics as mid-season inputs. Any future calibration must be trained without held-out site labels and tested on a new season.

## Other models and dates

site_comparison.csv includes every available model and cutoff, yield ranges, negative-prediction counts, MAE, RMSE, bias and the mean of the lowest 10 predictions.

day 60, combined, Ames: 1 negative predictions; day 60, ridge_combined, Ames: 487 negative predictions; day 60, ridge_combined, Scottsbluff: 466 negative predictions; day 75, ridge_combined, Scottsbluff: 38 negative predictions. These are physically invalid estimates and model failures, retained and flagged rather than silently clipped.

## Sources

- Original target definition and trial layout: 2022/README.md and 2022/DataPublication_final/GroundTruth/HYBRID_HIPS_V3.5_ALLPLOTS.csv.
- [USDA NASS Crop Production 2024 Summary](https://www.nass.usda.gov/Publications/Todays_Reports/reports/cropan25.pdf), January 10, 2025, printed page 10: 2022 corn-for-grain yields of 200.0 bu/ac in Iowa and 165.0 in Nebraska. These are retrospective context, not local trial targets.
- Saved evaluation predictions and exact input hashes: checks.json.
