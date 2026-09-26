"""UI checks use the completed local evaluation and skip before it exists."""
from pathlib import Path
import os

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from maize.modeling import scout_table

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(os.environ.get("MAIZE_OUTPUT", ROOT / "outputs"))


@pytest.mark.skipif(not (OUTPUT / "held_out_predictions.csv").exists(), reason="Run evaluation first")
def test_dashboard_filters_and_download_contents(monkeypatch):
    from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
    stores = []

    def capture_storage(*args, **kwargs):
        storage = MemoryMediaFileStorage(*args, **kwargs)
        stores.append(storage)
        return storage

    monkeypatch.setattr("streamlit.testing.v1.app_test.MemoryMediaFileStorage", capture_storage)
    app = AppTest.from_file(str(ROOT / "scouting.py"), default_timeout=30).run()
    assert not app.exception
    app.selectbox[0].select("MOValley")
    app.select_slider[0].set_value(60)
    app.number_input(key="scouting_capacity_count").set_value(20)
    app.run()
    assert not app.exception
    assert any("no usable satellite" in w.value for w in app.warning)
    actual_table = app.dataframe[0].value
    predictions = pd.read_csv(OUTPUT / "held_out_predictions.csv")
    expected = scout_table(predictions, 60, "MOValley", capacity=20)
    chosen = expected.loc[expected.selected]
    assert len(chosen) == 20
    assert actual_table["Plot"].tolist() == chosen.plot_id.tolist()
    assert actual_table["Predicted yield (bu/ac)"].tolist() == chosen.predicted_yield.tolist()
    assert "yieldPerAcre" not in actual_table
    button = app.get("download_button")[0]
    assert button.proto.url
    # Read the actual bytes registered by Streamlit's download button.
    file_id = button.proto.url.split("/")[-1].split(".")[0]
    content = stores[-1].get_file(file_id).content
    assert content == chosen.to_csv(index=False).encode("utf-8")
    app.select_slider[0].set_value(75).run()
    assert not app.exception
    assert not any("no usable satellite" in w.value for w in app.warning)
    app.selectbox[0].select("Ames").run()
    app.number_input(key="scouting_capacity_count").set_value(487).run()
    assert len(app.dataframe[0].value) == 487
    app.selectbox[0].select("MOValley").run()
    assert not app.exception
    assert app.number_input(key="scouting_capacity_count").value == 163
    assert len(app.dataframe[0].value) == 163
