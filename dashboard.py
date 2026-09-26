"""FieldSignal: evidence for hybrid selection across environments."""
import json
import os
from pathlib import Path
import runpy

import pandas as pd
import plotly.express as px
import streamlit as st

from maize.insights import LABELS
from maize.branding import render_team_branding
from maize.yield_audit import render_yield_audit

ROOT = Path(__file__).resolve().parent
OUTPUT = Path(os.environ.get("MAIZE_OUTPUT", str(ROOT / "outputs")))
st.set_page_config(page_title="FieldSignal by Cornstellation | Across environments", page_icon="🌽", layout="wide")
view = st.sidebar.radio("Workspace", ["Decision brief", "Hybrid performance", "Scouting (secondary)"])
if view == "Decision brief":
    runpy.run_path(str(ROOT / "decision_dashboard.py"), run_name="__main__")
    st.stop()
if view == "Scouting (secondary)":
    runpy.run_path(str(ROOT / "scouting.py"), run_name="__main__")
    st.stop()

render_team_branding()
DATA = OUTPUT / "broad_performance"
if not (DATA / "claims.json").exists():
    st.info("The hybrid comparison is being prepared. Scouting remains available in the sidebar.")
    st.stop()


@st.cache_data
def load(folder, stamp):
    folder = Path(folder)
    names = ["observed_hybrids", "observed_site", "observed_environment", "forecast_hybrids", "forecast_site",
             "nitrogen_pairs", "nitrogen_sites", "nitrogen_hybrids", "ranking_metrics", "yield_metrics"]
    return json.loads((folder / "claims.json").read_text()), {name: pd.read_csv(folder / f"{name}.csv") for name in names}


claims, tables = load(str(DATA), (DATA / "claims.json").stat().st_mtime_ns)
st.caption("FIELDSIGNAL / FIVE LOCATIONS / 2022")
st.title("Hybrid performance across environments")
st.write("Satellite-informed forecasts for better hybrid selection across environments.")
st.caption("Observed harvest evidence and forecasts are separate views. No cross-season validation is claimed.")
with st.sidebar:
    st.header("Evidence view")
    evidence = st.selectbox("Evidence source", ["Observed harvest (2022)", "Forecast (held-out sites)"])
    forecast = evidence.startswith("Forecast")
    cutoff = st.select_slider("Forecast cutoff (days after planting)", [60, 75, 90], value=90, disabled=not forecast)
    chosen_model = st.selectbox("Forecast model", ["combined", "ridge_combined", "agronomy", "ridge_agronomy"], format_func=LABELS.get, disabled=not forecast)
    st.caption("Forecasts for each location come from models trained on other locations. Ridge is an exploratory 2022 comparison.")
    st.divider()
    pitch = ROOT / "deliverables" / "FieldSignal_pitch.pptx"
    brief = ROOT / "deliverables" / "FieldSignal_findings.pdf"
    if pitch.exists():
        st.download_button("Download pitch deck", pitch.read_bytes(), file_name=pitch.name)
    if brief.exists():
        st.download_button("Download findings brief", brief.read_bytes(), file_name=brief.name, mime="application/pdf")

if forecast:
    hybrids = tables["forecast_hybrids"].query("cutoff == @cutoff and model == @chosen_model").copy()
    sites = tables["forecast_site"].query("cutoff == @cutoff and model == @chosen_model").copy()
    st.info(f"FORECAST VIEW: {LABELS[chosen_model]}, day {cutoff}. Rankings below use held-out predictions, not harvest yields.")
else:
    hybrids, sites = tables["observed_hybrids"], tables["observed_site"]
    st.info("OBSERVED VIEW: completed 2022 harvest results. This shortlist describes the trial evidence, not model predictions.")

a, b, c, d = st.columns(4)
a.metric("Hybrids compared", claims["hybrids"])
b.metric("Sites", claims["locations"])
c.metric("Labeled plots", f"{claims['labeled_plots']:,}")
d.metric("Site × treatment environments", claims["environments"])
across, management, validation = st.tabs(["Across environments", "Management response", "Forecast evidence"])
with across:
    st.subheader("A shortlist for the next replicated trials")
    st.caption("Candidates exceed the median at four or more sites. We rank them by average within-site percentile, giving each site equal weight. Higher is better.")
    shortlist = hybrids.loc[hybrids.shortlisted]
    rename = {"genotype": "Hybrid", "average_percentile": "Average percentile", "worst_site_percentile": "Worst-site percentile",
              "sites_above_median": "Sites above median", "between_site_sd": "Variation across sites", "replicates": "Plots", "min_cell_replicates": "Fewest replicates in a treatment"}
    st.dataframe(shortlist[list(rename)].rename(columns=rename).round(1), hide_index=True, width="stretch")
    if shortlist.empty:
        st.info("No hybrid meets the shortlist rule in this forecast view.")
    else:
        matrix = sites.loc[sites.genotype.isin(shortlist.genotype)].pivot(index="genotype", columns="location", values="site_percentile").reindex(shortlist.genotype)
        figure = px.imshow(matrix, color_continuous_scale="YlGn", zmin=0, zmax=100, text_auto=".0f", aspect="auto",
                            labels={"color": "Percentile", "x": "Site", "y": "Hybrid"})
        figure.update_layout(height=340, margin=dict(l=0, r=0, t=20, b=10))
        st.plotly_chart(figure, width="stretch")
    scatter = px.scatter(hybrids, x="between_site_sd", y="average_percentile", color="shortlisted", hover_name="genotype",
                         hover_data=["worst_site_percentile", "sites_above_median", "replicates"],
                         color_discrete_map={True: "#237347", False: "#b6c4ad"},
                         labels={"between_site_sd": "Variation across sites (percentile points)", "average_percentile": "Average percentile", "shortlisted": "Shortlist"})
    scatter.update_layout(height=360)
    st.plotly_chart(scatter, width="stretch")
    st.caption("Higher and farther left means stronger relative performance with less variation. This is descriptive evidence across the observed environments.")
    suffix = f"forecast_{chosen_model}_{cutoff}" if forecast else "observed_2022"
    st.download_button("Download current hybrid comparison", hybrids.to_csv(index=False).encode(), file_name=f"hybrids_{suffix}.csv", mime="text/csv")
    with st.expander("All hybrids and comparison method"):
        st.dataframe(hybrids[list(rename)].rename(columns=rename).round(2), hide_index=True, width="stretch")
        st.write("We first average replicate plots per hybrid and treatment. Each hybrid has equal weight in its environment benchmark. We rank hybrids within each environment, average treatment percentiles within site, and finally average across sites. Replicate counts remain visible. Variation is the population standard deviation across site percentiles.")

with management:
    st.subheader("Nitrogen contrasts depend on the environment")
    st.caption("OBSERVED HARVEST COMPARISON: 150 minus 75 lb nitrogen/acre, matching the same hybrid within each site. These are descriptive treatment contrasts, not recommended rates.")
    ns = tables["nitrogen_sites"]
    figure = px.bar(ns, x="location", y="mean_difference", color="mean_difference", color_continuous_scale="BrBG",
                    color_continuous_midpoint=0, text_auto="+.1f", labels={"location": "Site", "mean_difference": "Observed difference (bu/ac)"})
    figure.update_layout(showlegend=False, coloraxis_showscale=False, height=360)
    st.plotly_chart(figure, width="stretch")
    st.write(f"The equally weighted mean across four sites is **{claims['nitrogen_equal_site_difference']:+.1f} bu/ac**, but the site results range from **{ns.mean_difference.min():+.1f}** to **{ns.mean_difference.max():+.1f} bu/ac**.")
    selected = st.selectbox("Inspect a hybrid's nitrogen response", sorted(tables["nitrogen_pairs"].genotype.unique()))
    pairs = tables["nitrogen_pairs"].loc[tables["nitrogen_pairs"].genotype.eq(selected)]
    st.dataframe(pairs[["location", "yield_mean_75", "yield_mean_150", "difference_150_minus_75", "replicates_75", "replicates_150"]].round(2), hide_index=True, width="stretch")
    st.download_button("Download all matched nitrogen comparisons", tables["nitrogen_pairs"].to_csv(index=False).encode(), file_name="matched_nitrogen_comparisons.csv", mime="text/csv")
    with st.expander("Treatment support and interpretation"):
        st.dataframe(ns.round(2), hide_index=True, width="stretch")
        st.write("Missouri Valley has one nitrogen rate and is excluded from dose contrasts. Nitrogen treatments can occupy separate experiments, so field placement and other conditions can contribute to differences. Irrigation is site-associated; its independent effect is not identified. Recorded irrigation values remain unchanged in the data.")

with validation:
    st.subheader("Yield accuracy and hybrid selection are different tests")
    render_yield_audit(OUTPUT, cutoff, chosen_model)
    st.write("Every location is held out once. No held-out harvest yield enters its forecast. Additional Ridge comparisons are exploratory development on 2022, with regularization selected inside each training fold.")
    metrics = tables["yield_metrics"]
    overall = metrics.loc[metrics.location.eq("Overall") & metrics.cutoff.isin([75, 90])].copy()
    overall["Inputs"] = overall.model.map(LABELS)
    figure = px.line(overall, x="cutoff", y="mae", color="Inputs", markers=True, labels={"cutoff": "Days after planting", "mae": "MAE (bu/ac)"})
    figure.update_xaxes(tickvals=[75, 90])
    st.plotly_chart(figure, width="stretch")
    ranks = tables["ranking_metrics"]
    summary = ranks.loc[ranks.cutoff.isin([75, 90]) & ranks.model.ne("mean")].groupby(["model", "cutoff"])[["spearman", "top10_overlap"]].mean().reset_index()
    summary["model"] = summary.model.map(LABELS)
    st.dataframe(summary.round(3), hide_index=True, width="stretch")
    st.caption("Hybrid scores use equal treatment weights within sites. Top-10 overlap is the average number of correctly recovered observed top-10 hybrids per site. Random selection has an expected overlap of 10 × 10 / 84 = 1.19. The constant-mean baseline cannot rank hybrids.")
    compare_site = st.selectbox("Inspect forecast performance at a site", sorted(ranks.location.unique()))
    rank_view = ranks.loc[ranks.location.eq(compare_site) & ranks.cutoff.isin([75, 90])]
    st.dataframe(rank_view[["cutoff", "model", "spearman", "top10_overlap", "hybrids"]].round(3), hide_index=True, width="stretch")
    st.dataframe(metrics.loc[metrics.location.eq(compare_site) & metrics.cutoff.isin([75, 90]), ["cutoff", "model", "mae", "bias"]].round(2), hide_index=True, width="stretch")
    obs = tables["observed_site"].query("location == @compare_site")
    pred = tables["forecast_site"].query("location == @compare_site and cutoff == @cutoff and model == @chosen_model")
    joined = obs[["genotype", "site_percentile"]].merge(pred[["genotype", "site_percentile"]], on="genotype", suffixes=("_observed", "_forecast"))
    chart = px.scatter(joined, x="site_percentile_observed", y="site_percentile_forecast", hover_name="genotype", title=f"{LABELS[chosen_model]}, day {cutoff}: {compare_site}",
                       labels={"site_percentile_observed": "Observed percentile", "site_percentile_forecast": "Forecast percentile"})
    st.plotly_chart(chart, width="stretch")
    st.download_button("Download forecast ranking evidence", ranks.to_csv(index=False).encode(), file_name="hybrid_ranking_validation.csv", mime="text/csv")
    st.warning("One season supports cross-site evidence only. Rankings remain imperfect, and weak sites remain visible. The next milestone is an untouched 2023 evaluation before claims of cross-season reliability.")
