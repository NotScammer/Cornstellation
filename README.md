# FieldSignal: maize yield and scouting

## Hackathon presentation package

The current presentation package is **`deliverables/IoT4Ag/`**. Start with `FieldSignal_scope_and_demo.md`; present `FieldSignal_IoT4Ag_pitch.pptx` and share `FieldSignal_IoT4Ag_brief.pdf`. The five-slide deck includes editable charts, an editable shortlist table and a three-minute talk track in speaker notes. Three PNG/SVG figures, CSV evidence and a rehearsal guide accompany it. Earlier presentation files are retained as background.

The default **Decision brief** connects a day-75 inspection list, a fixed bottom-20% warning screen, a nitrogen-only/agronomy/imagery comparison, and the observed hybrid shortlist for future trials. The warning is a candidate screening rule, not a diagnosis. All evidence concerns five sites in 2022; cross-season validation remains pending.

**Workspace > Scouting plan** adds a simple presentation view: site priority, candidate anomaly counts, three scout-first plot summaries, a full capacity-based CSV and forecast hybrid watch. Its illustrative anomaly rule combines a bottom-20% yield forecast with a drop of at least 20 within-site percentile points versus the agronomy-only model. Site priorities use anomaly fraction; plot priorities use anomaly status and descending rank gap. Absolute gaps of 30 or more points are labeled model disagreement, not calibrated uncertainty. This new ordering has not been evaluated, so the original scouting precision does not apply. No harvest labels enter the view; hybrid watch uses treatment-balanced held-out forecast percentiles.

**Which sites need checks first?** appears in both Decision brief and Scouting plan. Each site is a compact expandable row with its priority, flagged count and percentage. Open a row to reveal its first three plot summaries, image context and a download of its capacity-limited inspection list, directly underneath. Capacity applies separately to each site. Sites rank by flagged share, not total size. The site-level screening order remains illustrative; Decision brief plot lists retain the evaluated lowest-yield-first order. The full selected-site table is also available in a separate collapsed panel.

Reproduce the nitrogen-only comparison and decision evidence with `.venv\Scripts\python.exe -m maize.decision_brief`. Add `--reuse-nitrogen` to reuse saved predictions. Outputs are in `outputs/decision_brief/`; no harvest label enters the warning queue. Capacity is an integer number of trial plots, default 10 per site. Evaluation separates precision for limited visits from recall of all actual bottom-20% plots. Nitrogen-only ties use plot ID and should not be marketed as a robust fold-improvement.

The dashboard separates observed harvest evidence from held-out forecasts. The original scouting interface remains available through **Workspace > Scouting (secondary)**, or directly by running Streamlit with `scouting.py`.

Reproduce the hybrid comparisons and nested Ridge evaluation:

```powershell
.\.venv\Scripts\python.exe -m maize.insights
```

To regenerate the comparisons and figures without retraining Ridge, use `--reuse-ridge`. All new analysis outputs go into `outputs/broad_performance`; the original CatBoost results remain unchanged. This analysis is scoped to one season per data root. Future multi-season pooling requires season-aware plot identifiers.

The hybrid analysis averages replicate plots within hybrid/environment, calculates relative performance within location-year-nitrogen-irrigation environments, averages treatment percentiles within site, and weights sites equally. Ranking yields are rounded to eight decimals only to prevent floating-point noise from turning identical predictions into artificial ranks. The shortlist requires above-median results at four or more of five sites and selects up to five by average percentile. Sample standard errors and confidence intervals are not inferred from five locations.

Ridge uses numeric median imputation and scaling plus categorical one-hot encoding. Each outer held-out-site fold selects alpha from 1, 10, and 100 using only inner held-out-site folds, minimizing equal-site mean absolute error. Fold choices and inner validation scores are saved in `ridge_fold_audit.json`. These additional comparisons are exploratory 2022 development, not an untouched new-season test.

Nitrogen contrasts match each hybrid at 75 and 150 lb N/acre within the same site, year, and irrigation treatment. Site summaries weight matched hybrids equally and the cross-site summary weights sites equally. Separate experiments and field placement can contribute to observed differences. Irrigation values remain as recorded, and no isolated irrigation or optimal nitrogen-rate effect is claimed.

A local Python pipeline and Streamlit demo in `C:\Users\sonpo\Desktop\Hackathon`.
Original research data under `2022/` is read-only to the application.

## Start the dashboard

Run in PowerShell from this folder:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard.py --server.address 127.0.0.1
```

Open http://localhost:8501. The dashboard reads completed results; it does not retrain on each interaction.

Scouting capacity is an exact **number of trial plots**, defaulting to 10. Each selected row represents a research plot, not a whole farm field. The control is capped at the selected site's plot count, and the table, CSV download, precision and recall use that same count. The original batch scouting exports retain their configured 10% budget.

## Audit yields against the source and USDA context

```powershell
.\.venv\Scripts\python.exe -m maize.yield_audit
```

This checks saved prediction labels and feature labels against the original plot CSV, verifies identical evaluation cohorts, and exports `outputs/yield_audit/yield_audit.md`, `site_comparison.csv`, treatment summaries, source details and input hashes. The audit is read-only with respect to forecasts and fitted models. It accepts `--data-root` and `--output`.

Both dashboard evaluation views include an expandable comparison of actual research-plot yield, predicted yield, model bias and USDA 2022 state yield. USDA numbers are retrospective context only, never training inputs or rescaling targets. Scouting deliberately selects low predictions, and the source trial means are themselves below the state averages. There are also substantial site-specific model errors. Negative forecasts at early cutoffs are flagged as invalid estimates. The audit uses ordinary plot means; the hybrid-selection analysis uses treatment-balanced site summaries.

## Reproduce the pipeline

The project-local `.venv` has the dependencies installed. For a new machine, create a Python 3.12 environment and install `requirements-lock.txt` (exact tested versions) or `requirements.txt` (compatible ranges).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m maize run
.\.venv\Scripts\python.exe -m pytest -q
```

Separate data preparation from training, or choose cutoffs:

```powershell
.\.venv\Scripts\python.exe -m maize prepare --cutoffs 60 75 90
.\.venv\Scripts\python.exe -m maize train --cutoffs 60 75 90
.\.venv\Scripts\python.exe -m maize run --output outputs/smoke --smoke
```

`--data-root`, `--output`, `--config`, and `--workers` are configurable. The data root must contain `GroundTruth/` and `Satellite/`. Use a different output directory for each season or experiment. A smoke run is deliberately small and cannot replace research results.

## Predict another season without yield labels

Keep the same folder layout and agronomy column names. The plot CSV may omit `yieldPerAcre` or leave it blank. Collection dates must describe that season. Plot keys are location, experiment, range, and row; each data root represents one season.

```powershell
.\.venv\Scripts\python.exe -m maize predict --data-root 2023/DataPublication_final --output outputs/2023 --models-dir outputs/models
```

This command uses the final models fitted on all eligible 2022 plots. Its predictions are **inference, not validation**. To establish future-season accuracy, freeze the 2022 pipeline before examining 2023 labels and evaluate those predictions separately. Inference currently produces a CSV; the dashboard intentionally displays only historical held-out-location results.

## Outputs

- `outputs/report.md`: results and presentation-ready figures.
- `outputs/metrics.csv`: MAE, RMSE, bias, and within-site Spearman correlation.
- `outputs/held_out_predictions.csv`: one independent prediction per plot, model, and cutoff.
- `outputs/scouting_priorities.csv`: all plots ranked within site; the first 10% are flagged.
- `outputs/scouting_metrics.csv`: precision and recall at the per-site scouting budget.
- `outputs/models/`: full-data models and their feature/configuration manifests, for inference only.
- `outputs/data_quality.json`, `coverage.csv`, `image_errors.csv`, `unmatched_images.csv`, `training_exclusions.csv`, `plots_without_images.csv`: explicit quality and exclusion records.
- `outputs/image_cache.parquet`: per-image summaries keyed by source path, file size, modification time, band configuration, and extraction version. Changed inputs are re-read.
- `outputs/fold_audit.json`: training sites and test counts for each held-out fold.

Set `MAIZE_OUTPUT` to an absolute result-folder path before launching Streamlit to inspect another historical run.

## Scientific interpretation

The first experiment uses 2022, five leave-one-location-out folds, and cutoffs at 60, 75, and 90 days after planting. Site identifiers are used for splitting and reporting, not as model predictors. Both models use exactly the same eligible plots. CatBoost handles numeric missing values and categorical encoding within each training fold; missing categorical values use a fixed sentinel.

Agronomy inputs are planting day-of-year, nitrogen rate, irrigation, and genotype. Combined models add latest six-band medians, NDVI/NDRE, changes since the previous observation, observation counts/gap/age, valid-pixel statistics, and a missing-image flag. Differences are raw changes; the observation gap is provided separately. No full-season peak, future interpolation, flowering measurement, or stand count is used.

Band mapping is explicit in `config.json`: red=1, green=2, blue=3, NIR=4, red-edge=5, deep-blue=6, matching the supplied notebook and sampled Pleiades NEO TIFF descriptions. Recognized conflicting descriptions stop preparation. No per-image min/max scaling is applied. Border/no-data/nonfinite/negative pixels are excluded. Cloud/shadow QA is unavailable, so valid-pixel counts are not cloud-quality estimates.

Verified join corrections: `Missouri Valley` becomes `MOValley`; within MOValley, the ground-truth experiment typo `Hyrbrids` becomes `Hybrids` to match the image filenames. Records with incomplete plot keys are preserved in the exclusion report rather than matched by guesswork.

At 60 days Missouri Valley has no satellite image. Those plots remain in all comparisons. Unknown hybrids are supported as unseen categories, but no unseen-hybrid generalization claim is made.

Yield is bushels/acre at 15.5% moisture, as documented by the dataset authors. Scouting targets the lowest-yielding 20% in each held-out site; exact-size selections round up and break ties by plot ID. Overall precision/recall pool the counts from separate site budgets. Rankings are a retrospective decision proxy, not proof of remediable stress. Raw hybrid averages are not causal genetic effects.

One season supports spatial-transfer evidence only. No calibrated prediction intervals or automatic trustworthy cutoff are claimed. Agree on tolerable error with agronomists and validate on 2023 before claiming future-season reliability.

## Version control

This workspace is a local Git repository on `main`. It tracks the application, tests, configuration, dependency specifications, team logo, ground-truth records and dataset documentation, saved models, extracted features, evaluation results, and presentation deliverables. Reusable presentation/PDF builders under `.build/` are also tracked.

Raw imagery in `2022/DataPublication_final/Satellite/` and `UAV/`, the local `.venv/`, credentials, smoke-test outputs, and temporary caches/previews are excluded. They remain on disk. A clone can use the committed results for the dashboard, but re-extracting image features requires restoring the raw imagery to those folders. Git history is local until a remote repository is explicitly configured and pushed.

To review and save future work:

```powershell
git status
git diff
git add .
git commit -m "Describe the change"
git log --oneline
```
