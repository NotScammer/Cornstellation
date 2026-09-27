"""Exercise the optional model throughout the completed UAV dashboard run."""
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from maize.modeling import scout_table
from maize.scouting_plan import plan_tables, hybrid_watch

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/uav"
pytestmark = pytest.mark.skipif(not (OUTPUT / "decision_brief/claims.json").exists(), reason="Full UAV reports required")


def test_uav_model_switch_and_downloads(monkeypatch):
    from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
    stores = []
    def capture(*args, **kwargs):
        storage = MemoryMediaFileStorage(*args, **kwargs)
        stores.append(storage)
        return storage
    monkeypatch.setattr("streamlit.testing.v1.app_test.MemoryMediaFileStorage", capture)
    monkeypatch.setenv("MAIZE_OUTPUT", str(OUTPUT))
    app = AppTest.from_file(str(ROOT / "dashboard.py"), default_timeout=60).run()
    assert not app.exception
    selector = app.selectbox(key="decision_model")
    assert selector.value == "combined"
    selector.select("combined_uav").run()
    assert not app.exception
    source = pd.read_csv(OUTPUT / "held_out_predictions.csv")
    expected = scout_table(source, 75, "Ames", capacity=10, model="combined_uav").head(10)
    assert app.dataframe[0].value.Plot.tolist() == expected.plot_id.tolist()
    button = next(x for x in app.get("download_button") if x.label == "Download inspection list")
    file_id = button.proto.url.split("/")[-1].split(".")[0]
    import io
    exported = pd.read_csv(io.BytesIO(stores[-1].get_file(file_id).content))
    assert exported.model.eq("combined_uav").all()
    assert exported.plot_id.tolist() == expected.plot_id.tolist()
    assert "yieldPerAcre" not in exported
    trip_button = [x for x in app.get("download_button") if x.label == "Download trip estimate and visit order"][-1]
    trip_id = trip_button.proto.url.split("/")[-1].split(".")[0]
    trip = pd.read_csv(io.BytesIO(stores[-1].get_file(trip_id).content))
    assert trip.model.eq("combined_uav").all()
    assert set(trip.plot_id) == set(expected.plot_id)
    warning_table = next(x.value for x in app.dataframe if {"precision", "recall", "hits"}.issubset(x.value.columns))
    warning_source = pd.read_csv(OUTPUT / "decision_brief/warning_evaluation.csv")
    warning_expected = warning_source.query("model == 'combined_uav'").groupby("cutoff")[["hits", "k", "target_n"]].sum()
    assert warning_table.hits.tolist() == warning_expected.hits.tolist()
    assert any("UAV flight:" in c.value for c in app.caption)
    app.radio[0].set_value("Scouting plan").run()
    app.selectbox(key="plan_model").select("combined_uav").run()
    assert not app.exception
    plots, sites = plan_tables(source, 75, model="combined_uav")
    for _, row in sites.iterrows():
        name = "Missouri Valley" if row.location == "MOValley" else row.location
        assert any(name in panel.label and f"{int(row.anomalies)} plots flagged" in panel.label for panel in app.expander)
    watch = hybrid_watch(pd.read_csv(OUTPUT / "broad_performance/forecast_site.csv"), 75, "combined_uav")
    assert watch.model.eq("combined_uav").all()
    watch_button = next(x for x in app.get("download_button") if x.label == "Download hybrid watch evidence")
    watch_id = watch_button.proto.url.split("/")[-1].split(".")[0]
    assert stores[-1].get_file(watch_id).content == watch.to_csv(index=False).encode()
    app.radio[0].set_value("Scouting (secondary)").run()
    app.selectbox(key="secondary_model").select("combined_uav").run()
    assert not app.exception
    app.select_slider[0].set_value(60)
    next(x for x in app.selectbox if x.label == "Trial location").select("Crawfordsville").run()
    assert not app.exception
    assert any("UAV: no eligible image" in c.value for c in app.caption)
    app.select_slider[0].set_value(90).run()
    assert not app.exception
    assert any("UAV flight:" in c.value and "Image age:" in c.value for c in app.caption)
