from pathlib import Path
import pandas as pd
from maize.scouting_plan import plan_tables, hybrid_watch

ROOT=Path(__file__).resolve().parents[1]

def test_plan_ignores_harvest_and_is_explicit_about_thresholds():
    source=pd.read_csv(ROOT/"outputs/held_out_predictions.csv")
    plots,sites=plan_tables(source,75)
    other,_=plan_tables(source.assign(yieldPerAcre=-10000),75)
    pd.testing.assert_frame_equal(plots,other)
    assert "yieldPerAcre" not in plots
    alerts=plots.loc[plots.candidate_anomaly]
    assert alerts.low_forecast.all() and alerts.expectation_gap.ge(20).all()
    assert sites.iloc[0].location=="Crawfordsville"
    assert sites.anomaly_rate.is_monotonic_decreasing
    assert not plan_tables(source,60)[0].candidate_anomaly.any()

def test_scouting_plan_dashboard_uses_real_plot_ids():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/"dashboard.py"),default_timeout=30).run()
    app.radio[0].set_value("Scouting plan").run()
    assert not app.exception
    site_panels = [x for x in app.expander if "plots flagged" in x.label]
    assert len(site_panels) == 5
    assert all(not x.proto.expanded for x in site_panels)
    plots,sites=plan_tables(pd.read_csv(ROOT/"outputs/held_out_predictions.csv"),75)
    first=plots.loc[plots.location.eq("Scottsbluff")].iloc[0]
    assert any(first.plot_id in x.value for x in app.markdown)
    scotts = next(x for x in site_panels if "Scottsbluff" in x.label)
    assert "49 plots flagged" in scotts.label
    assert any(first.plot_id in x.value for x in scotts.markdown)
    assert any(x.label=="Download Scottsbluff inspection list" for x in scotts.get("download_button"))
    assert any("Not calibrated" in x.value for x in app.caption)
    assert any("Suggested first stop: Crawfordsville" in x.value for x in app.success)
    for _, site in sites.iterrows():
        assert any(f"{int(site.anomalies)} of {int(site.plots)} plots flagged" in x.value for x in app.markdown)
    app.radio[0].set_value("Decision brief").run()
    next(x for x in app.selectbox if x.label=="Trial location").select("MOValley").run()
    assert not app.exception
    assert next(x for x in app.selectbox if x.label=="Trial location").value=="MOValley"
    assert app.dataframe[0].value.Plot.str.startswith("MOValley|").all()
    next(x for x in app.selectbox if x.label=="Decision cutoff (days after planting)").select(60).run()
    assert not app.exception
    assert any("Site check priorities start at day 75" in x.value for x in app.info)
