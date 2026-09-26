"""Simple presentation view of forecast gaps and hybrid watch."""
import os
from pathlib import Path
import pandas as pd
import streamlit as st
from maize.branding import render_team_branding
from maize.scouting_plan import plan_tables, hybrid_watch
from maize.site_checks import render_site_checks

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ.get("MAIZE_OUTPUT", str(ROOT / "outputs")))
render_team_branding()
st.title("FIELD SIGNAL — SCOUTING PLAN")
st.caption("2022 historical replay · Forecasts at held-out locations · No harvest yields used in this view")
cutoff = st.sidebar.selectbox("Plan cutoff (days after planting)", [75,90], key="plan_cutoff")
predictions = pd.read_csv(OUT / "held_out_predictions.csv")
plots, sites = plan_tables(predictions, cutoff)
location = st.sidebar.selectbox("Plan location", sites.location.tolist(), key=f"plan_location_{cutoff}")
local = plots.loc[plots.location.eq(location)]
capacity = st.sidebar.number_input("Plots in this plan", 1, len(local), 10, key=f"plan_capacity_{location}")
site = sites.loc[sites.location.eq(location)].iloc[0]
render_site_checks(sites, cutoff, f"plan_location_{cutoff}", "plan_sites")
st.subheader(f"Site priority #{int(site.site_priority)}: {location}")
a,b = st.columns(2)
a.metric("Candidate anomalies", int(site.anomalies), help="Bottom 20% forecast and at least a 20-percentile-point drop from the agronomy model.")
b.metric("Large model disagreements", int(site.disagreements), help="At least 30 percentile points between models in either direction. This is not calibrated uncertainty.")
st.write("**Primary signal:** satellite-informed forecasts below agronomic-model expectation.")
st.caption(f"{site.anomaly_rate:.1%} of {int(site.plots)} plots meet the candidate rule. Sites rank by this fraction. {int(site.missing_images)} plots have missing imagery.")
st.info("Illustrative screening view: model disagreement is not measured stress or calibrated confidence. These thresholds and this ordering are not validated; the earlier 60% scouting precision does not apply to this queue.")

st.subheader("Scout first")
selected = local.head(int(capacity))
if not site.anomalies:
    st.write("No plots meet the candidate anomaly rule. The list below shows the largest forecast gaps for review.")
for _, plot in selected.head(3).iterrows():
    with st.container(border=True):
        label = "🔴 Priority inspection" if plot.candidate_anomaly else "🟡 Review"
        st.markdown(f"**{plot.plot_id} — {label}**")
        st.caption(f"{plot.genotype} · Replay date {plot.prediction_date}")
        left,right = st.columns(2)
        with left:
            st.write(f"**Predicted yield:** {plot.predicted_yield:.1f} bu/ac")
            st.write(f"**Predicted performance:** percentile {plot.forecast_percentile:.1f} within site")
            expected = "High" if plot.expectation_percentile >= 75 else "Middle" if plot.expectation_percentile >= 25 else "Low"
            st.write(f"**Agronomic expectation:** {expected} (percentile {plot.expectation_percentile:.1f})")
        with right:
            if plot.observation_count < 2 or pd.isna(plot.delta_ndvi):
                trajectory = "Insufficient observations"
            else:
                direction = "Declining" if plot.delta_ndvi < 0 else "Rising" if plot.delta_ndvi > 0 else "Unchanged"
                trajectory = f"{direction} · NDVI change {plot.delta_ndvi:+.3f}"
            st.write(f"**Satellite trajectory:** {trajectory}")
            st.write(f"**Image age:** {plot.image_age_days:.0f} days" if pd.notna(plot.image_age_days) else "**Image age:** No eligible image")
            st.write("**Confidence:** Not calibrated")
        st.write(f"**Reason:** satellite-informed rank is {plot.expectation_gap:+.0f} percentile points below the agronomy model." if plot.expectation_gap >= 0 else "**Reason:** forecast disagreement; combined rank is above the agronomy model.")
        st.write("**Recommended action:** ground-truth crop condition and record any visible stress or field differences.")
st.caption(f"Showing the first {min(3,len(selected))} plot summaries. Download includes all {len(selected)} plots in the plan. Plot identity is site | experiment | range | row.")
st.download_button("Download scouting plan", selected.to_csv(index=False).encode(), file_name=f"scouting_plan_{location}_day{cutoff}_{capacity}plots.csv", mime="text/csv")

st.subheader("Hybrid watch")
st.caption("Forecast watch across all five sites at the selected cutoff. These labels describe model rankings, not observed outcomes or proven adaptation.")
watch = hybrid_watch(pd.read_csv(OUT / "broad_performance/forecast_site.csv"), cutoff)
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
    st.download_button("Download hybrid watch evidence", watch.to_csv(index=False).encode(),file_name=f"forecast_hybrid_watch_day{cutoff}.csv")
