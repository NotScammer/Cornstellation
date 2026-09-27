"""Simple presentation view of forecast gaps and hybrid watch."""
import os
from pathlib import Path
import pandas as pd
import streamlit as st
from maize.branding import render_team_branding
from maize.scouting_plan import plan_tables, hybrid_watch
from maize.site_checks import render_site_checks
from maize.uav_dashboard import select_forecast, render_coverage

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ.get("MAIZE_OUTPUT", str(ROOT / "outputs")))
render_team_branding()
st.title("FIELD SIGNAL — SCOUTING PLAN")
st.caption("2022 historical replay · Forecasts at held-out locations · No harvest yields used in this view")
cutoff = st.sidebar.selectbox("Plan cutoff (days after planting)", [75,90], key="plan_cutoff")
predictions = pd.read_csv(OUT / "held_out_predictions.csv")
model = select_forecast(predictions, "plan_model")
render_coverage(predictions, cutoff)
plots, sites = plan_tables(predictions, cutoff, model=model)
capacity = st.sidebar.number_input("Plots per site to include", 1, int(sites.plots.max()), min(10, int(sites.plots.max())), key="plan_capacity")
render_site_checks(sites, cutoff, plots, int(capacity), "plan_sites", order="gap", output=OUT)

st.subheader("Hybrid watch")
st.caption("Forecast watch across all five sites at the selected cutoff. These labels describe model rankings, not observed outcomes or proven adaptation.")
watch = hybrid_watch(pd.read_csv(OUT / "broad_performance/forecast_site.csv"), cutoff, model=model)
stable = watch.loc[watch.above_median.eq(5)].head(1)
used = set(stable.genotype)
sensitive = watch.loc[~watch.genotype.isin(used)].sort_values(["site_spread","genotype"],ascending=[False,True]).head(1)
used.update(sensitive.genotype)
below = watch.loc[watch.below_expectation.ge(3) & ~watch.genotype.isin(used)].sort_values(["below_expectation","average_percentile","genotype"],ascending=[False,True,True]).head(1)
if len(stable):
    h=stable.iloc[0]
    st.write(f"🟢 **{h.genotype} — Consistently on track in forecasts**")
    st.caption(f"Above the median at {int(h.above_median)}/5 sites; weakest-site percentile {h.worst_site:.0f}.")
else:
    st.write("No hybrid is forecast above the median at all five sites.")
if len(sensitive):
    h=sensitive.iloc[0]
    st.write(f"🟡 **{h.genotype} — Largest variation across forecast sites**")
    st.caption(f"Within-site percentile ranges from {h.worst_site:.0f} to {h.best_site:.0f}. Variation is descriptive, not proof of an environment interaction.")
if len(below):
    h=below.iloc[0]
    st.write(f"🔴 **{h.genotype} — Below model expectation at {int(h.below_expectation)}/5 sites**")
    st.caption("Combined hybrid percentile is at least 20 points below the agronomy-only percentile at those sites.")
else:
    st.caption("No additional hybrid meets the below-expectation rule at three or more sites.")
with st.expander("How priorities are assigned"):
    st.write("Candidate anomaly = bottom 20% combined forecast within site AND a drop of at least 20 percentile points from agronomy-only rank. Large disagreement = absolute gap of at least 30 points. Both are illustrative thresholds. Agronomy-only forecasts are an imperfect reference, not a measured yield potential. Sites rank by anomaly fraction; plots rank by anomaly flag, then largest gap, lowest forecast and plot ID. Satellite trajectory uses the last two eligible NDVI observations; a decline alone is not proof of stress.")
    st.dataframe(sites,hide_index=True,width="stretch")
    st.download_button("Download hybrid watch evidence", watch.to_csv(index=False).encode(),file_name=f"forecast_hybrid_watch_{model}_day{cutoff}.csv")
