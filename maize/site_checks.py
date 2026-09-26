"""Plain-language, cross-site inspection overview using the existing candidate rule."""
import streamlit as st


def choose_site(widget_key, location):
    st.session_state[widget_key] = location


def render_site_checks(sites, cutoff, location_key, key_prefix):
    st.subheader("Which sites need checks first?")
    st.write("Compare how much of each site is flagged, then open its plot list to plan your visit.")
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
        with st.container(border=True):
            detail, action = st.columns([3, 1], vertical_alignment="center")
            with detail:
                st.markdown(f"**{int(row.site_priority)}. {name}**")
                st.write(f"**{int(row.anomalies)} of {int(row.plots)} plots flagged · {row.anomaly_rate:.1%}**")
                st.progress(float(row.anomaly_rate))
                if row.missing_images:
                    st.caption(f"{int(row.missing_images)} plots have no eligible image. Missing imagery can hide problems.")
            with action:
                st.button(f"Check {name}", key=f"{key_prefix}_{row.location}_{cutoff}", on_click=choose_site, args=(location_key, row.location), width="stretch")
    st.caption("A lower position means fewer flags under this rule; it does not mean a site is free of problems. The selected site's inspection list appears below.")
    export = sites[["site_priority", "location", "anomalies", "plots", "anomaly_rate", "missing_images"]].copy()
    export["anomaly_rate"] = (export.anomaly_rate * 100).round(2)
    export = export.rename(columns={"site_priority":"Suggested order", "location":"Site", "anomalies":"Plots flagged", "plots":"Total plots", "anomaly_rate":"Plots flagged (%)", "missing_images":"Plots missing imagery"})
    export["Site"] = export.Site.replace({"MOValley":"Missouri Valley"})
    st.download_button("Download site check priorities", export.to_csv(index=False).encode(), file_name=f"site_check_priorities_day{cutoff}.csv", mime="text/csv", key=f"{key_prefix}_download")
    st.divider()
