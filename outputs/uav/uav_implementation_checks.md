# UAV implementation checks

- Original prepared features, harvest labels, plot identifiers and cutoffs were compared column-for-column with the UAV run and were identical.
- UAV preparation adds 17 numeric features; file paths, dates and plot identifiers are not model predictors.
- Source inventory contains 7,281 images: 5,685 RGBA and 1,596 RGB.
- All 456 excluded UAV images have collection dates but no matching ground-truth plot. They are retained in the exclusion report rather than matched by guesswork.
- The image extractor processed 6,825 matched images without read errors and completed a second cached preparation run.
- The saved full-data day-60 UAV model was reloaded and produced finite predictions for all 2,157 records with yield labels removed. These inference results are not used for validation metrics.
- Unit tests exercise missing imagery, future-observation invariance, transparent and zero borders, corrupt files, source-specific dates, duplicate observations, cache invalidation, model round trips and model-specific scouting selection.

See `uav_evidence.md` for the full evaluation results, `fold_audit.json` for held-out-site splits, and `models/*.json` for saved model inputs and settings.

## Completed validation

- Full 2022 evaluation completed: five held-out sites at days 60, 75 and 90, with 400 CatBoost iterations and the original model settings.
- All original held-out predictions reproduced exactly, including the mean, agronomy and satellite models at all cutoffs.
- 31 tests passed; none skipped. Three pre-existing rasterio transform deprecation warnings remain.
- End-to-end dashboard tests verified optional UAV model selection, inspection CSVs, route plot membership, warning totals and hybrid-watch exports, plus missing and dated UAV imagery.
- The original results-folder dashboard passed compatibility tests.
- The local UAV dashboard was opened and its default satellite selection and source-specific coverage were verified in the browser.
- Source audit confirmed identical plot cohorts, unchanged harvest labels and finite predictions for all evaluated models.
