import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PIL import Image

from maize.data import load_dates
from maize.uav import (MEASUREMENTS, UAV_FEATURES, summarize_rgb, add_uav_features,
                       extract_uav, latest_image)
from maize.modeling import evaluate, predict, scout_table
from maize.scouting_plan import plan_tables, hybrid_watch
from test_pipeline import fixture_data, CONFIG
from maize.data import build_cutoff_features


def test_rgb_features_and_masks():
    a = np.array([[[0, 0, 0, 255], [10, 30, 10, 255], [100, 0, 0, 0]]], dtype=np.uint8)
    summary = summarize_rgb(a)
    assert summary["green"] == pytest.approx(.6)
    assert summary["excess_green"] == pytest.approx(.8)
    assert summary["green_fraction"] == 1
    assert summary["valid_fraction"] == pytest.approx(1/3)
    assert summary["excess_green_iqr"] == 0
    assert summarize_rgb(a[:, 1:2, :3])["red"] == pytest.approx(.2)
    with pytest.raises(ValueError, match="Empty"):
        summarize_rgb(np.zeros((2, 2, 3)))
    with pytest.raises(ValueError, match="RGB"):
        summarize_rgb(np.ones((2, 2)))


def uav_observations(plots):
    return pd.DataFrame([dict(plot_id=p.plot_id, image_date=p.plantingDate+pd.Timedelta(days=day),
                              valid_fraction=.8, path=f"{p.plot_id}-{day}.PNG",
                              **{m: (i+day)/100 for m in MEASUREMENTS})
                         for i, p in enumerate(plots.itertuples()) for day in [40, 70]])


def test_uav_cutoffs_missingness_and_thumbnail():
    plots, satellite = fixture_data()
    features = build_cutoff_features(plots, satellite, [60, 75])
    observations = uav_observations(plots)
    result = add_uav_features(features, observations)
    assert result.loc[result.cutoff.eq(60), "uav_observation_count"].eq(1).all()
    assert result.loc[result.cutoff.eq(75), "uav_image_age_days"].eq(5).all()
    future = observations.assign(image_date=pd.Timestamp("2023-01-01"), green=999).drop_duplicates("plot_id")
    pd.testing.assert_frame_equal(result, add_uav_features(features, pd.concat([observations, future])))
    plot = features.iloc[0]
    before = latest_image(observations, plot.plot_id, plot.plantingDate, plot.prediction_date)
    after = latest_image(pd.concat([observations, future]), plot.plot_id, plot.plantingDate, plot.prediction_date)
    pd.testing.assert_series_equal(before, after)
    empty = add_uav_features(features, observations.iloc[:0])
    assert len(empty) == len(features) and empty.uav_missing_imagery.eq(1).all()
    assert empty.uav_latest_green.isna().all()
    with pytest.raises(ValueError, match="Duplicate"):
        add_uav_features(features, pd.concat([observations, observations.iloc[:1]]))


def test_inventory_dates_errors_and_cache(tmp_path):
    root = tmp_path / "data"
    (root / "GroundTruth").mkdir(parents=True)
    folder = root / "UAV"
    folder.mkdir()
    dates = pd.DataFrame([dict(Location="A", Date="2022-06-01", Image="Satellite", time="TP1"),
                          dict(Location="A", Date="2022-06-10", Image="UAV", time="TP1")])
    dates.to_excel(root / "GroundTruth/DateofCollection.xlsx", index=False)
    assert load_dates(root, "UAV").iloc[0].image_date == pd.Timestamp("2022-06-10")
    plots, _ = fixture_data()
    for row, pixels in [(0, np.full((3, 3, 3), [10, 30, 10], dtype=np.uint8)),
                        (1, np.zeros((3, 3, 3), dtype=np.uint8))]:
        Image.fromarray(pixels).save(folder / f"A-TP1-trial_1_{row}.PNG")
    (folder / "A-TP1-trial_1_2.PNG").write_bytes(b"broken")
    Image.new("RGB", (2, 2), "green").save(folder / "A-TP9-trial_1_3.PNG")
    Image.new("RGB", (2, 2), "green").save(folder / "A-TP1-trial_1_99.PNG")
    output = tmp_path / "output"
    output.mkdir()
    first = extract_uav(root, output, plots, workers=1)
    assert len(first) == 1 and first.iloc[0].image_date == pd.Timestamp("2022-06-10")
    assert len(pd.read_csv(output / "uav_image_errors.csv")) == 2
    assert len(pd.read_csv(output / "uav_unmatched_images.csv")) == 2
    second = extract_uav(root, output, plots, workers=1)
    assert first.iloc[0].fingerprint == second.iloc[0].fingerprint
    Image.new("RGB", (4, 4), "red").save(folder / "A-TP1-trial_1_0.PNG")
    changed = extract_uav(root, output, plots, workers=1)
    assert changed.iloc[0].fingerprint != first.iloc[0].fingerprint
    assert changed.iloc[0].green_fraction == 0
    dates = pd.concat([dates, dates.iloc[[1]]])
    dates.to_excel(root / "GroundTruth/DateofCollection.xlsx", index=False)
    with pytest.raises(ValueError, match="unique"):
        load_dates(root, "UAV")
    dates = dates.iloc[:2]
    dates.to_excel(root / "GroundTruth/DateofCollection.xlsx", index=False)
    Image.new("RGB", (2, 2), "green").save(folder / "A-TP2-trial_1_0.PNG")
    dates = pd.concat([dates, dates.iloc[[1]].assign(time="TP2")])
    dates.to_excel(root / "GroundTruth/DateofCollection.xlsx", index=False)
    with pytest.raises(ValueError, match="Duplicate UAV"):
        extract_uav(root, output, plots, workers=1)


def test_no_uav_files_preserves_empty_schema(tmp_path):
    (tmp_path / "GroundTruth").mkdir()
    pd.DataFrame(columns=["Location", "Date", "Image", "time"]).to_excel(
        tmp_path / "GroundTruth/DateofCollection.xlsx", index=False)
    plots, _ = fixture_data()
    observations = extract_uav(tmp_path, tmp_path, plots, workers=1)
    assert observations.empty
    assert set(MEASUREMENTS).issubset(observations.columns)


def test_uav_models_inference_and_scout_selection(tmp_path):
    plots, satellite = fixture_data()
    features = add_uav_features(build_cutoff_features(plots, satellite, [60, 75]), uav_observations(plots))
    config = {**CONFIG, "include_uav": True}
    predictions, metrics = evaluate(features, tmp_path, config, smoke=True)
    assert len(predictions) == len(features)*5
    fixed = pd.read_csv(tmp_path / "model_comparison.csv")
    assert fixed.query("location != 'Overall'").k.eq(6).all()
    assert set(metrics.model) == {"mean", "agronomy", "combined", "agronomy_uav", "combined_uav"}
    cohorts = predictions.groupby(["model", "cutoff"]).plot_id.apply(set)
    assert all(ids == set(plots.plot_id) for ids in cohorts)
    for name in ["agronomy_uav", "combined_uav"]:
        manifest = json.loads((tmp_path / f"models/{name}_60.json").read_text())
        assert manifest["uav_settings"] and set(UAV_FEATURES).issubset(manifest["features"])
        predict(features.assign(yieldPerAcre=np.nan), tmp_path / "models", tmp_path / name, config, name)
        inferred = pd.read_csv(tmp_path / name / "inference_predictions.csv")
        assert inferred.model.eq(name).all() and "yieldPerAcre" not in inferred
    # Force a different ranking to prove selection propagates instead of silently using combined.
    predictions.loc[predictions.model.eq("combined_uav"), "predicted_yield"] = -predictions.loc[predictions.model.eq("combined_uav"), "predicted_yield"]
    selected = scout_table(predictions, 75, "A", capacity=2, model="combined_uav")
    assert selected.model.eq("combined_uav").all()
    expected = predictions.query("model == 'combined_uav' and cutoff == 75 and location == 'A'").sort_values(["predicted_yield", "plot_id"])
    assert selected.plot_id.tolist() == expected.plot_id.tolist()
    plan, _ = plan_tables(predictions, 75, model="combined_uav")
    assert plan.model.eq("combined_uav").all()
    assert "yieldPerAcre" not in plan
    from maize.decision_brief import warning_queue
    queue = warning_queue(expected, capacity=2)
    assert queue.model.eq("combined_uav").all()
    assert queue.loc[queue.selected, "plot_id"].tolist() == expected.head(2).plot_id.tolist()
    manifest_path = tmp_path / "models/combined_uav_60.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["uav_settings"]["version"] = -1
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="settings differ"):
        predict(features, tmp_path / "models", tmp_path / "invalid", config, "combined_uav")
