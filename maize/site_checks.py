"""Plain-language, cross-site inspection overview using the existing candidate rule."""
import pandas as pd
import streamlit as st
from maize.scouting_trip import render_scouting_trip
from maize.uav_dashboard import render_uav


def render_plot_summaries(selected, order, output=None):
    st.markdown("**Scout first**")
    for number, (_, plot) in enumerate(selected.head(3).iterrows(), 1):
        st.markdown(f"**{number}. {plot.plot_id}** · {plot.genotype}")
        left, right = st.columns(2)
        with left:
            st.write(f"**Predicted yield:** {plot.predicted_yield:.1f} bu/ac")
            expected = "High" if plot.expectation_percentile >= 75 else "Middle" if plot.expectation_percentile >= 25 else "Low"
            st.caption(f"Agronomic expectation: {expected} · percentile {plot.expectation_percentile:.1f}")
        with right:
            if plot.observation_count < 2 or pd.isna(plot.delta_ndvi):
                trajectory = "Not enough observations"
            else:
                direction = "Declining" if plot.delta_ndvi < 0 else "Rising" if plot.delta_ndvi > 0 else "Unchanged"
                trajectory = f"{direction} · NDVI {plot.delta_ndvi:+.3f}"
            st.write(f"**Satellite trajectory:** {trajectory}")
            age = f"{plot.image_age_days:.0f} days" if pd.notna(plot.image_age_days) else "No eligible image"
            st.caption(f"Image age: {age} · Replay: {plot.prediction_date}")
        if output is not None:
            render_uav(plot, output)
        if order == "gap":
            reason = f"Forecast rank is {plot.expectation_gap:.0f} percentile points below the agronomy model." if plot.expectation_gap >= 0 else "Model disagreement; forecast rank is above the agronomy model."
        else:
            reason = "Among the lowest predicted yields at this site."
        st.write(f"**Why check:** {reason}")
        if number < min(3, len(selected)):
            st.divider()
    st.caption("Action: ground-truth crop condition and record visible stress or field differences. Confidence: Not calibrated.")


def render_site_checks(sites, cutoff, plots, capacity, key_prefix, order="gap", output=None):
    st.subheader("Which sites need checks first?")
    st.write("Expand a site to see which plots to check and download its inspection list.")
    if cutoff < 75:
        st.info("Site check priorities start at day 75. Choose day 75 or 90 to compare sites.")
        return
    leader = sites.iloc[0]
    if leader.anomalies:
        name = "Missouri Valley" if leader.location == "MOValley" else leader.location
        st.success(f"Suggested first stop: {name} — {int(leader.anomalies)} plots flagged ({leader.anomaly_rate:.1%} of the site).")
    else:
        st.info("No sites have flagged plots under this screening rule. Continue routine checks.")
    st.caption("Suggested order uses the share of plots flagged, so a larger site does not automatically come first. Flags mean low forecast performance plus a drop from the agronomy model. This is an unvalidated screening rule, not confirmed crop stress.")
    for _, row in sites.iterrows():
        name = "Missouri Valley" if row.location == "MOValley" else row.location
        label = f"{int(row.site_priority)}. {name} — {int(row.anomalies)} plots flagged · {row.anomaly_rate:.1%}"
        with st.expander(label, expanded=False):
            st.write(f"**{int(row.anomalies)} of {int(row.plots)} plots flagged · {row.anomaly_rate:.1%}**")
            st.progress(float(row.anomaly_rate))
            if row.missing_images:
                st.caption(f"{int(row.missing_images)} plots have no eligible satellite image. Missing imagery can hide problems.")
            local = plots.loc[plots.location.eq(row.location)].copy()
            if "uav_missing_imagery" in local:
                st.caption(f"UAV coverage: {int(local.uav_missing_imagery.eq(0).sum())}/{len(local)} plots by this cutoff.")
            if order == "yield":
                local = local.sort_values(["predicted_yield", "plot_id"])
                st.caption("Plot order: lowest predicted yield first. The site ranking above uses the separate, illustrative forecast-gap screen.")
            else:
                st.caption("Plot order: candidate anomalies first, then the largest gap from agronomic expectation. This order has not been validated.")
            selected = local.head(min(capacity, len(local))).copy()
            selected["cutoff"] = cutoff
            selected["inspection_order"] = range(1, len(selected) + 1)
            render_plot_summaries(selected, order, output)
            st.caption(f"Showing {min(3, len(selected))} plot summaries; download includes {len(selected)} plots. Capacity is applied separately to each site.")
            st.download_button(f"Download {name} inspection list", selected.to_csv(index=False).encode(), file_name=f"inspection_{selected.iloc[0].get('model', 'combined')}_{row.location}_day{cutoff}_{len(selected)}plots_{order}.csv", mime="text/csv", key=f"{key_prefix}_{row.location}_{cutoff}_list")
            if output is not None:
                render_scouting_trip(selected, output, f"{key_prefix}_{row.location}_trip")
    st.caption("A lower position means fewer flags under this rule; it does not mean a site is free of problems.")
    export = sites[["site_priority", "location", "anomalies", "plots", "anomaly_rate", "missing_images"]].copy()
    model = plots.iloc[0].get("model", "combined")
    export["Model"] = model
    export["anomaly_rate"] = (export.anomaly_rate * 100).round(2)
    export = export.rename(columns={"site_priority":"Suggested order", "location":"Site", "anomalies":"Plots flagged", "plots":"Total plots", "anomaly_rate":"Plots flagged (%)", "missing_images":"Plots missing imagery"})
    export["Site"] = export.Site.replace({"MOValley":"Missouri Valley"})
    st.download_button("Download site check priorities", export.to_csv(index=False).encode(), file_name=f"site_check_priorities_{model}_day{cutoff}.csv", mime="text/csv", key=f"{key_prefix}_download")
    st.divider()
