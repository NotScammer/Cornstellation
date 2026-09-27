"""Presentation companion: action this season, evidence for the next trials."""
import json
import os
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from maize.branding import render_team_branding
from maize.decision_brief import warning_queue, MODEL_LABELS
from maize.modeling import scouting_metrics
from maize.scouting_plan import plan_tables
from maize.site_checks import render_site_checks
from maize.scouting_trip import render_scouting_trip
from maize.uav_dashboard import select_forecast, render_uav, render_coverage

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ.get("MAIZE_OUTPUT", str(ROOT / "outputs")))
DATA = OUT / "decision_brief"
render_team_branding()
st.title("FieldSignal decision brief")
st.write("Imagery-informed forecasts for scouting and hybrid comparisons across environments.")
st.info("2022 historical replay—held-out-location predictions. Future-season validation is pending.")
if not (DATA / "claims.json").exists():
    st.warning("Prepare the decision evidence with python -m maize.decision_brief")
    st.stop()
predictions = pd.read_csv(OUT / "held_out_predictions.csv")
comparison = pd.read_csv(DATA / "model_comparison.csv")
warnings = pd.read_csv(DATA / "warning_evaluation.csv")
cutoff = st.sidebar.selectbox("Decision cutoff (days after planting)", [75, 90, 60])
site = st.sidebar.selectbox("Trial location", sorted(predictions.location.unique()), key="decision_location")
model = select_forecast(predictions, "decision_model")
render_coverage(predictions, cutoff)
group = predictions.query("model == @model and cutoff == @cutoff and location == @site")
capacity = st.sidebar.number_input("Trial plots to inspect", 1, len(group), min(10, len(group)), key=f"decision_capacity_{site}")
queue = warning_queue(group, int(capacity))
now, evidence, trials = st.tabs(["Scouting & warning", "What imagery adds · evaluation", "Next replicated trials · observed"])
with now:
    site_plots, site_priorities = plan_tables(predictions, cutoff, model=model)
    render_site_checks(site_priorities, cutoff, site_plots, int(capacity), "decision_sites", order="yield", output=OUT)
    with st.expander(f"Detailed inspection table · {site}", expanded=False):
        st.caption("Site comparison uses the illustrative forecast-gap rule. The inspection list below keeps the evaluated lowest-yield-first order.")
        st.subheader("Inspect the lowest predicted yields first")
        st.write("Candidate rule: from day 75, flag the lowest predicted 20% within each location. Inspect in predicted-yield order up to your capacity. A flag prompts a human check; it does not diagnose a cause or prescribe a treatment.")
        if cutoff == 60:
            st.warning("Day 60 is supporting evidence only. The warning rule starts at day 75. Check source-specific coverage above.")
        flagged = queue.loc[queue.warning_flag]
        a, b, c = st.columns(3)
        a.metric("Inspection capacity", int(capacity))
        b.metric("Plots flagged", len(flagged))
        c.metric("Flag boundary · bu/ac", f"{flagged.predicted_yield.max():.1f}" if len(flagged) else "Inactive")
        st.caption("The yield boundary changes with site and date; it is not a universal agronomic threshold. Ties use plot ID. Recent NDVI decline is supporting context, not a trigger.")
        selected = queue.loc[queue.selected]
        fields = {"priority":"Priority", "plot_id":"Plot", "genotype":"Hybrid", "predicted_yield":"Predicted yield (bu/ac)", "warning_flag":"Flagged", "delta_ndvi":"Recent NDVI change", "image_age_days":"Image age (days)", "prediction_date":"Replay date"}
        st.dataframe(selected[list(fields)].rename(columns=fields).round(3), hide_index=True, width="stretch")
        st.download_button("Download inspection list", selected.to_csv(index=False).encode(), file_name=f"inspection_{model}_{site}_day{cutoff}_{capacity}plots.csv", mime="text/csv")
        render_scouting_trip(selected, OUT, f"decision_detail_{site}_trip")
        if (OUT / "uav_image_index.csv").exists():
            with st.expander("UAV evidence for the first three visits"):
                for _, plot in selected.head(3).iterrows():
                    render_uav(plot, OUT)
        st.caption(f"Missing satellite imagery: {int(queue.missing_imagery.sum())} of {len(queue)} plots. Image age and observation count should inform inspection planning.")
        if queue.invalid_negative_prediction.any():
            st.warning("Some forecasts are negative and physically implausible. They indicate model failure, not a literal yield estimate.")
with evidence:
    st.subheader("The same held-out plots, with and without imagery")
    overall = comparison.query("location == 'Overall' and cutoff in [75, 90]").copy()
    overall["Inputs"] = overall.model.map(MODEL_LABELS)
    st.plotly_chart(px.bar(overall, x="Inputs", y="mae", color="cutoff", barmode="group", labels={"mae":"MAE (bu/ac) · lower is better", "cutoff":"Days after planting"}), width="stretch")
    st.dataframe(overall[["cutoff","Inputs","mae","hits","k","precision_at_k","recall_at_k"]].round(3), hide_index=True, width="stretch")
    st.caption("Scouting comparison fixes capacity at up to 10 plots per site. The target is the actual lowest-yielding 20% per site. Nitrogen-only and mean predictions contain ties; their inspection results depend on plot-ID tie-breaking.")
    local = scouting_metrics(group, capacity=int(capacity))
    st.write(f"Selected location/capacity retrospective check: {local['hits']} low-yield plots found in {local['k']} visits; precision {local['precision_at_k']:.0%}, recall {local['recall_at_k']:.0%}.")
    st.subheader("Warning coverage and limited visits are different decisions")
    if "model" in warnings:
        warnings = warnings.loc[warnings.model.eq(model)]
    w = warnings.groupby("cutoff")[["hits","k","target_n"]].sum()
    w["precision"] = w.hits / w.k
    w["recall"] = w.hits / w.target_n
    st.dataframe(w.round(3), width="stretch")
    st.caption("The fixed bottom-20% screen is a candidate rule. Yield error and scouting success measure different outcomes; compare both by model and date. Low final yield is not proof of preventable stress.")
    with st.expander("Satellite model: two Ames day-75 examples · harvest outcomes shown only here"):
        cases = pd.read_csv(DATA / "case_examples.csv")
        st.dataframe(cases[["example","plot_id","priority","nitrogen","agronomy","predicted_yield","yieldPerAcre","warning_flag"]].round(2), hide_index=True, width="stretch")
        st.write("Examples describe the satellite model only; they illustrate the decision, not average model accuracy.")
    st.download_button("Download comparison evidence", comparison.to_csv(index=False).encode(), file_name="model_comparison.csv")
with trials:
    st.subheader("Use the shortlist to prioritize the next replicated trials")
    hybrids = pd.read_csv(OUT / "broad_performance/observed_hybrids.csv")
    shortlist = hybrids.loc[hybrids.shortlisted]
    st.warning("OBSERVED HARVEST FINDINGS: these candidates come from completed 2022 trials, not forecast rankings.")
    st.dataframe(shortlist[["genotype","average_percentile","worst_site_percentile","sites_above_median","replicates"]].round(1), hide_index=True, width="stretch")
    st.write("Average replicates within hybrid–treatment combinations, treatment percentiles within each site, then weight sites equally. Shortlist candidates must exceed the median at four or more sites. Some treatment cells have one replicate.")
    st.download_button("Download observed hybrid shortlist", shortlist.to_csv(index=False).encode(), file_name="observed_hybrid_shortlist.csv")
    nitrogen = pd.read_csv(OUT / "broad_performance/nitrogen_sites.csv")
    st.subheader("Nitrogen response depends on the environment")
    st.dataframe(nitrogen.round(2), hide_index=True, width="stretch")
    st.caption("Observed 150-minus-75 lb N/acre contrasts for matched hybrids; equal site weighting. Missouri Valley is excluded because it has one rate. Field placement may contribute. No isolated irrigation effect or optimal-rate recommendation is established.")
    st.write("Open Hybrid performance in the sidebar for separate observed/forecast rankings, Ridge comparisons, site-specific failures and full replicate counts. Freeze the pipeline, then evaluate untouched 2023 data before claiming performance across seasons.")
