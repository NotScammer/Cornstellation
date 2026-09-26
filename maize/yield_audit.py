"""Check saved forecasts against source labels; USDA values are context only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import load_records

USDA_SOURCE = "https://www.nass.usda.gov/Publications/Todays_Reports/reports/cropan25.pdf"
STATES = {"Ames": "Iowa", "Crawfordsville": "Iowa", "MOValley": "Iowa", "Lincoln": "Nebraska", "Scottsbluff": "Nebraska"}
USDA_2022 = {"Iowa": 200.0, "Nebraska": 165.0}


def audit(data_root, output):
    output = Path(output)
    folder = output / "yield_audit"
    folder.mkdir(parents=True, exist_ok=True)
    records = load_records(data_root)
    eligible = records.loc[records.yieldPerAcre.notna() & records.plantingDate.notna() & ~records.invalid_plot_key].copy()
    eligible_ids = set(eligible.plot_id)
    features = pd.read_parquet(output / "features.parquet")
    feature_labels = features.loc[features.yieldPerAcre.notna()].merge(
        eligible[["plot_id", "yieldPerAcre"]], on="plot_id", how="left", validate="many_to_one", suffixes=("", "_source"))
    assert feature_labels.yieldPerAcre_source.notna().all(), "Unknown labeled feature plots"
    assert np.allclose(feature_labels.yieldPerAcre, feature_labels.yieldPerAcre_source, rtol=0, atol=1e-9), "Feature labels changed"
    sources = [output / "held_out_predictions.csv"]
    ridge = output / "broad_performance/ridge_predictions.csv"
    if ridge.exists():
        sources.append(ridge)
    predictions = pd.concat([pd.read_csv(p) for p in sources], ignore_index=True)
    assert not predictions.duplicated(["plot_id", "cutoff", "model"]).any(), "Duplicate predictions"
    joined = predictions.merge(eligible[["plot_id", "location", "yieldPerAcre"]], on="plot_id", how="left",
                               validate="many_to_one", suffixes=("", "_source"))
    assert joined.yieldPerAcre_source.notna().all(), "Predictions do not match eligible source plots"
    assert joined.location.eq(joined.location_source).all(), "Location mismatch"
    assert np.allclose(joined.yieldPerAcre, joined.yieldPerAcre_source, rtol=0, atol=1e-9), "Prediction labels changed"
    assert np.isfinite(joined.predicted_yield).all(), "Nonfinite predictions"
    rows = []
    for (cutoff, model), group in joined.groupby(["cutoff", "model"]):
        assert set(group.plot_id) == eligible_ids, f"Cohort mismatch: {model}/{cutoff}"
        for site, g in group.groupby("location"):
            error = g.predicted_yield - g.yieldPerAcre_source
            lowest = g.sort_values(["predicted_yield", "plot_id"]).head(min(10, len(g)))
            state = STATES[site]
            rows.append(dict(cutoff=int(cutoff), model=model, location=site, state=state, plots=len(g),
                             actual_mean=g.yieldPerAcre_source.mean(), predicted_mean=g.predicted_yield.mean(),
                             bias=error.mean(), mae=error.abs().mean(), rmse=np.sqrt(np.mean(error ** 2)),
                             actual_min=g.yieldPerAcre_source.min(), actual_max=g.yieldPerAcre_source.max(),
                             predicted_min=g.predicted_yield.min(), predicted_max=g.predicted_yield.max(),
                             negative_predictions=int(g.predicted_yield.lt(0).sum()),
                             lowest_10_predicted_mean=lowest.predicted_yield.mean(),
                             usda_state_yield_2022=USDA_2022[state]))
    comparisons = pd.DataFrame(rows)
    comparisons.to_csv(folder / "site_comparison.csv", index=False)
    treatments = eligible.groupby(["location", "experiment", "poundsOfNitrogenPerAcre", "irrigationProvided"]).yieldPerAcre.agg(
        plots="size", actual_mean="mean", actual_min="min", actual_max="max").reset_index()
    treatments.to_csv(folder / "source_treatment_yields.csv", index=False)
    pd.DataFrame([{"state": state, "year": 2022, "yield_bu_ac": value, "source_url": USDA_SOURCE,
                   "publication": "Crop Production 2024 Summary, January 10 2025, printed page 10",
                   "role": "retrospective context only; not model input or calibration target"}
                  for state, value in USDA_2022.items()]).to_csv(folder / "usda_context.csv", index=False)
    checks = {"eligible_plots": len(eligible), "prediction_rows_checked": len(joined),
              "source_label_max_absolute_difference": float((joined.yieldPerAcre - joined.yieldPerAcre_source).abs().max()),
              "feature_labels_match_source": True, "same_plot_cohort_every_model_cutoff": True,
              "all_predictions_finite": True, "units": "bu/ac at 15.5% moisture, as documented by dataset authors",
              "unit_processing": "yieldPerAcre used directly; no log transform or acre/moisture conversion in model pipeline",
              "original_harvest_calculation": "Raw grain mass, moisture and full area inputs are not provided here; author calculations cannot be independently reconstructed.",
              "usda_source": USDA_SOURCE, "source_report_page": 10,
              "input_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources + [output / "features.parquet"]}}
    (folder / "checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    last = comparisons.query("cutoff == 90 and model == 'combined'")
    lines = ["# FieldSignal yield audit", "", "Scouting uses held-out CatBoost combined predictions; the revised capacity is an exact number of research plots, not farm fields.", "",
             "## Source-label and unit checks", "", f"Checked {len(joined):,} saved predictions across models and cutoffs against {len(eligible):,} original eligible records. Plot joins, site identities, feature labels and prediction labels match. Maximum label difference: {checks['source_label_max_absolute_difference']:.12g} bu/ac.",
             "", checks["unit_processing"] + ". " + checks["original_harvest_calculation"], "",
             "## Day-90 CatBoost combined: site means", "", "All values below are bu/ac. These are plot-weighted means, not the treatment-balanced means used in hybrid selection.", "",
             "| Site | Plots | Actual source yield | Predicted yield | Bias (predicted - actual) | USDA state mean |",
             "|---|---:|---:|---:|---:|---:|"]
    for r in last.itertuples():
        lines.append(f"| {r.location} | {r.plots} | {r.actual_mean:.1f} | {r.predicted_mean:.1f} | {r.bias:+.1f} | {r.usda_state_yield_2022:.1f} |")
    negative_rows = comparisons.loc[comparisons.negative_predictions.gt(0)]
    negative_details = "; ".join(f"day {r.cutoff}, {r.model}, {r.location}: {r.negative_predictions} negative predictions" for r in negative_rows.itertuples())
    negative_note = (negative_details + ". These are physically invalid estimates and model failures, retained and flagged rather than silently clipped.") if len(negative_rows) else "No negative predictions were found."
    lines += ["", "## Interpretation", "",
              "1. The supplied research-plot harvest yields are themselves below USDA state means at every included site. The training targets already contain this difference.",
              "2. Scouting deliberately selects the lowest predicted-yield plots. Its selected rows are not a representative site average.",
              "3. There are real model errors as well: day-90 CatBoost underpredicts Crawfordsville and Scottsbluff by about 40 bu/ac, but overpredicts Lincoln by about 70 bu/ac. A universal upward adjustment would worsen Lincoln.",
              "4. USDA state yields summarize corn-for-grain production per harvested acre across a much broader population. These trials cover selected hybrids, nitrogen treatments and site-associated irrigation; neither their raw plot means nor equal-site hybrid scores estimate state yield. The exact causes of the source-data gap cannot be established from this audit.",
              "5. We did not rescale predictions or use 2022 USDA harvest statistics as mid-season inputs. Any future calibration must be trained without held-out site labels and tested on a new season.", "",
              "## Other models and dates", "", "site_comparison.csv includes every available model and cutoff, yield ranges, negative-prediction counts, MAE, RMSE, bias and the mean of the lowest 10 predictions.", "", negative_note, "",
              "## Sources", "", "- Original target definition and trial layout: 2022/README.md and 2022/DataPublication_final/GroundTruth/HYBRID_HIPS_V3.5_ALLPLOTS.csv.",
              f"- [USDA NASS Crop Production 2024 Summary]({USDA_SOURCE}), January 10, 2025, printed page 10: 2022 corn-for-grain yields of 200.0 bu/ac in Iowa and 165.0 in Nebraska. These are retrospective context, not local trial targets.",
              "- Saved evaluation predictions and exact input hashes: checks.json."]
    (folder / "yield_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=2))
    print(last[["location", "actual_mean", "predicted_mean", "bias", "mae"]].round(2).to_string(index=False))
    return comparisons


def render_yield_audit(output, cutoff, model="combined", location=None):
    """Only call inside a historical evaluation view because this exposes actuals."""
    import streamlit as st
    path = Path(output) / "yield_audit/site_comparison.csv"
    if not path.exists():
        return
    with st.expander("Why are these yields lower than USDA averages?", expanded=False):
        frame = pd.read_csv(path)
        subset = frame.loc[frame.cutoff.eq(cutoff) & frame.model.eq(model)]
        if location is not None:
            subset = subset.loc[subset.location.eq(location)]
        st.write("Compare forecasts with the same research plots' harvest yields first. The scouting list deliberately selects the lowest predictions. USDA state averages describe a different population and are context, not validation targets.")
        columns = {"location": "Trial site", "state": "State", "plots": "Plots", "actual_mean": "Actual mean (bu/ac)",
                   "predicted_mean": "Predicted mean (bu/ac)", "bias": "Bias (bu/ac)", "usda_state_yield_2022": "USDA 2022 state mean (bu/ac)"}
        st.caption(f"Selected forecast: {model}, day {cutoff}. Means include all evaluated plots at each displayed site.")
        st.dataframe(subset[list(columns)].rename(columns=columns).round(1), hide_index=True, width="stretch")
        st.caption("Bias = predicted minus actual. Negative bias means underprediction. These are plot-weighted means, distinct from treatment-balanced hybrid comparisons.")
        negatives = int(subset.negative_predictions.sum())
        if negatives:
            st.warning(f"This model/cutoff has {negatives} negative yield predictions in the displayed sites. They are model failures, not physically valid yields; they have not been clipped or hidden.")
        st.write("The audit matched saved evaluation labels to original plot yields. The source already reports bu/ac at 15.5% moisture; the pipeline applies no additional yield-unit conversion. Low source yields and genuine site-specific model bias both contribute to the gap.")
        st.markdown(f"[USDA NASS source: 2022 corn-for-grain yields, page 10]({USDA_SOURCE}). Iowa: 200.0; Nebraska: 165.0 bu/ac. No USDA yield is used to train or rescale these forecasts.")
        st.download_button("Download yield audit for all models and dates", path.read_bytes(), file_name="yield_audit.csv", mime="text/csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("2022/DataPublication_final"))
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    audit(args.data_root, args.output)
