# UAV evidence: 2022 held-out-site comparison

The existing satellite forecast remains the default. UAV models are optional experimental comparisons.

Inventory: 7,281 files; 6,825 usable matched images; 456 unmatched or undated; 0 image errors.

RGB features describe appearance, not calibrated reflectance, NDVI, or a diagnosis. All models use the same eligible plots, including plots without UAV coverage at the cutoff.

| Day | Satellite MAE | Satellite + UAV MAE | MAE change | Satellite hits | Satellite + UAV hits |
|---|---|---|---|---|---|
| 60 | 75.70 | 79.53 | +3.83 | 30 | 28 |
| 75 | 45.48 | 41.90 | -3.59 | 30 | 27 |
| 90 | 43.98 | 45.27 | +1.29 | 31 | 26 |

MAE is bu/ac; negative MAE change means improvement. Hits count actual bottom-20% plots among up to 10 visits per site. The separate scouting_metrics.csv retains the 10% visit budget.

## Where UAV helps or hurts

- Day 60: lower MAE at Ames, Scottsbluff; higher MAE at Crawfordsville, Lincoln, MOValley.
- Day 75: lower MAE at Ames, Lincoln, MOValley, Scottsbluff; higher MAE at Crawfordsville.
- Day 90: lower MAE at Ames, Crawfordsville; higher MAE at Lincoln, MOValley, Scottsbluff.

See uav_incremental_value.csv for per-site errors and scouting changes, model_comparison.csv for all input combinations, and uav_coverage.csv for date-specific coverage. These exploratory results measure transfer between five sites in one season; future-season validation is pending.