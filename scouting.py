"""Read-only historical scouting dashboard. Launch with Streamlit."""
import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from maize.modeling import scout_table, scouting_metrics
from maize.branding import render_team_branding

st.set_page_config(page_title="FieldSignal by Cornstellation | Maize scouting", page_icon="🌽", layout="wide")
st.markdown("""
<style>
.stApp { background: #f5f7f2; }
h1, h2, h3 { color: #183c2b; }
[data-testid="stMetric"] { background: white; padding: 18px; border-radius: 12px; border: 1px solid #e0e7dc; }
[data-testid="stSidebar"] { background: #edf2e8; }
</style>
""", unsafe_allow_html=True)
render_team_branding()
st.caption("FIELDSIGNAL / MAIZE RESEARCH NETWORK")
st.title("A clearer view of where to scout.")
st.write("2022 historical replay—held-out-location predictions.")
st.caption("Each site's predictions come from a model trained on the other four sites. This evaluates spatial transfer in 2022, not future-season accuracy.")

output = Path(os.environ.get("MAIZE_OUTPUT", str(Path(__file__).resolve().parent / "outputs")))
required = ["held_out_predictions.csv", "metrics.csv", "data_quality.json", "run_config.json", "coverage.csv"]
if any(not (output / name).exists() for name in required):
    st.info("Evaluation results are not ready yet. Once model training finishes, refresh this page to open the scouting brief.")
    st.stop()


@st.cache_data
def load_results(folder, stamp):
    folder = Path(folder)
    return (pd.read_csv(folder / "held_out_predictions.csv"), pd.read_csv(folder / "metrics.csv"),
            json.loads((folder / "data_quality.json").read_text(encoding="utf-8")),
            json.loads((folder / "run_config.json").read_text(encoding="utf-8")),
            pd.read_csv(folder / "coverage.csv"))


predictions, metrics, quality, run_config, coverage = load_results(str(output), tuple((output / f).stat().st_mtime_ns for f in required))
if run_config.get("smoke_test"):
    st.warning("SMOKE TEST: this is a small pipeline check, not a full research result.")

with st.sidebar:
    st.header("Scouting brief")
    cutoff = st.select_slider("Days after planting", options=sorted(predictions.cutoff.unique().tolist()), value=int(predictions.cutoff.max()))
    location = st.selectbox("Trial location", sorted(predictions.location.unique()))
    capacity = st.slider("Scouting capacity (%)", min_value=1, max_value=100, value=10, step=1)
    st.caption("Capacity is applied within the selected site. Plots are ordered by lowest predicted yield.")
    st.divider()
    st.write("**Prediction inputs**")
    st.caption("Planting date · nitrogen · irrigation · hybrid · six-band satellite observations available by the cutoff.")

table = scout_table(predictions, cutoff, location, capacity / 100)
selected = table.loc[table.selected]
group = predictions.loc[predictions.cutoff.eq(cutoff) & predictions.location.eq(location) & predictions.model.eq("combined")]
missing = int(table.missing_imagery.sum())
a, b, c = st.columns(3)
a.metric("Plots in this site", f"{len(table):,}")
b.metric("Visits in this brief", f"{len(selected):,}")
c.metric("Plots with satellite coverage", f"{len(table)-missing:,} / {len(table):,}")
if missing:
    st.warning(f"{missing} plots have no usable satellite observation by day {cutoff}. Predictions remain available using the combined model's learned handling of missing imagery; these are not validated imagery-based forecasts for those plots.")

scouting_tab, evaluation_tab, quality_tab = st.tabs(["Scouting priorities", "Evaluate the forecast", "Data & limitations"])
display_names = {"scouting_rank": "Priority", "plot_id": "Plot", "genotype": "Hybrid", "predicted_yield": "Predicted yield (bu/ac)",
                 "delta_ndvi": "Recent NDVI change", "image_age_days": "Image age (days)", "observation_count": "Observations"}
display_columns = list(display_names)
with scouting_tab:
    st.subheader(f"{location}: your next {len(selected)} visits")
    st.write("Use low predicted yield as a reason to inspect. Field observations are needed to establish the cause and whether intervention can help.")
    st.dataframe(selected[display_columns].rename(columns=display_names), hide_index=True, width="stretch")
    st.download_button("Download scouting brief", selected.to_csv(index=False).encode("utf-8"),
                       file_name=f"scouting_{location}_day{cutoff}.csv", mime="text/csv")
    with st.expander("View all ranked plots"):
        st.dataframe(table[display_columns].rename(columns=display_names), hide_index=True, width="stretch")
    st.caption("Missing changes indicate fewer than two usable observations. Yield is standardized to 15.5% grain moisture.")

with evaluation_tab:
    scope = st.radio("Evaluation scope", ["All sites", "Selected site"], horizontal=True)
    site_key = "Overall" if scope == "All sites" else location
    subset = metrics.loc[metrics.location.eq(site_key)]
    current = subset.loc[subset.cutoff.eq(cutoff)].set_index("model")
    a_mae, c_mae = current.loc["agronomy", "mae"], current.loc["combined", "mae"]
    a, b, c = st.columns(3)
    a.metric("Agronomy-only MAE", f"{a_mae:.1f} bu/ac")
    b.metric("Combined MAE", f"{c_mae:.1f} bu/ac")
    c.metric("MAE reduction from imagery", f"{100*(a_mae-c_mae)/a_mae:.1f}%")
    figure = px.line(subset, x="cutoff", y="mae", color="model", markers=True,
                     labels={"cutoff": "Days after planting", "mae": "Mean absolute error (bu/ac)", "model": "Inputs"},
                     color_discrete_map={"mean": "#9a9a8a", "agronomy": "#d18b32", "combined": "#237347"})
    figure.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360)
    st.plotly_chart(figure, width="stretch")
    st.dataframe(current[["n", "mae", "rmse", "bias", "within_site_spearman"]].round(3), width="stretch")
    st.caption("Bias is predicted minus actual yield. Overall errors are plot-weighted; overall rank correlation is the mean of defined within-site correlations.")
    performance = scouting_metrics(group, capacity / 100, run_config["underperformance_fraction"])
    st.subheader(f"Did the scouting brief find low-yield plots in {location}?")
    a, b = st.columns(2)
    a.metric("Precision at selected capacity", f"{performance['precision_at_k']:.0%}")
    b.metric("Recall of underperformers", f"{performance['recall_at_k']:.0%}")
    st.caption("Retrospective target: the lowest-yielding 20% within this site. Random selection would have roughly 20% precision. Low final yield does not establish preventable stress.")
    st.scatter_chart(group, x="yieldPerAcre", y="predicted_yield")
    with st.expander("Actual versus predicted yields"):
        st.dataframe(group[["plot_id", "yieldPerAcre", "predicted_yield"]], hide_index=True, width="stretch")

with quality_tab:
    st.subheader("What this prototype can establish")
    st.write("The experiment measures how imagery changes prediction when transferring between five locations in one completed season. It does not establish reliability in a new growing season, diagnose nitrogen deficiency, or estimate causal hybrid effects.")
    st.write("No trustworthy cutoff is declared automatically. The crop team must set an acceptable error tolerance and check whether enough time remains for useful action.")
    st.write("The early cutoff has no satellite coverage in Missouri Valley. Every comparison retains the same labeled plot cohort.")
    st.dataframe(coverage, hide_index=True, width="stretch")
    st.json(quality)
    st.caption("Band order follows the supplied extraction notebook and is checked against recognized TIFF descriptions. Cloud/shadow QA masks are not supplied; valid pixels do not guarantee cloud-free observations.")
