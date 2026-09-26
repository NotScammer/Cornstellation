import pandas as pd
from maize.decision_brief import warning_queue

def test_warning_rule_cannot_see_harvest_labels():
    data = pd.read_csv("outputs/held_out_predictions.csv").query("model == 'combined' and cutoff == 75 and location == 'Ames'")
    first = warning_queue(data)
    changed = warning_queue(data.assign(yieldPerAcre=-99999))
    pd.testing.assert_frame_equal(first, changed)
    assert "yieldPerAcre" not in first.columns
    assert first.selected.sum() == 10 and first.warning_flag.sum() == 98
    assert not warning_queue(data.assign(cutoff=60)).warning_flag.any()

def test_decision_dashboard_matches_exported_queue(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
    stores = []
    def capture_storage(*args, **kwargs):
        storage = MemoryMediaFileStorage(*args, **kwargs)
        stores.append(storage)
        return storage
    monkeypatch.setattr("streamlit.testing.v1.app_test.MemoryMediaFileStorage", capture_storage)
    from pathlib import Path
    app = AppTest.from_file(str(Path("dashboard.py").resolve()), default_timeout=30).run()
    assert not app.exception
    expected = pd.read_csv("outputs/decision_brief/scouting_queue.csv").query("cutoff == 75 and location == 'Ames' and selected")
    assert app.dataframe[0].value.Plot.tolist() == expected.plot_id.tolist()
    next(x for x in app.number_input if x.label == "Trial plots to inspect").set_value(13).run()
    assert not app.exception and len(app.dataframe[0].value) == 13
    button = next(x for x in app.get("download_button") if x.label == "Download inspection list")
    file_id = button.proto.url.split("/")[-1].split(".")[0]
    source = pd.read_csv("outputs/held_out_predictions.csv").query("cutoff == 75 and location == 'Ames' and model == 'combined'")
    queue = warning_queue(source, 13)
    assert stores[-1].get_file(file_id).content == queue.loc[queue.selected].to_csv(index=False).encode()
