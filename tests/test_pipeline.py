import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from maize.data import (AGRONOMY, IMAGE_FEATURES, SPECTRAL, build_cutoff_features, load_records,
                        metadata_conflicts, normalize_keys, parse_image_name, safe_index, summarize_pixels)
from maize.modeling import (evaluate, location_folds, model_matrix, predict, scout_table, scouting_metrics)

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config.json").read_text())


def fixture_data():
    plots = []
    for site in ["A", "B", "C"]:
        for i in range(6):
            plots.append({"location": site, "experiment": "trial", "range": "1", "row": str(i),
                          "plantingDate": pd.Timestamp("2022-05-01"), "planting_doy": 121,
                          "poundsOfNitrogenPerAcre": 50 + i * 10, "irrigationProvided": i % 2,
                          "genotype": f"hybrid{i%3}", "yieldPerAcre": 120 + 8*i + ord(site)-65})
    plots = normalize_keys(pd.DataFrame(plots))
    records = []
    for p in plots.itertuples():
        for day, tp in [(40, "TP1"), (65, "TP2")]:
            records.append({"plot_id": p.plot_id, "image_date": p.plantingDate + pd.Timedelta(days=day),
                            "timepoint": tp, "valid_pixels": 20, "valid_fraction": 0.8,
                            **{name: float(day + int(p.row)) / 100 for name in SPECTRAL}})
    return plots, pd.DataFrame(records)


def test_plot_alias_and_filename_join():
    image = parse_image_name("Missouri Valley-TP1-trial_1_2.TIF")
    frame = normalize_keys(pd.DataFrame([image]))
    assert frame.iloc[0].plot_id == "MOValley|trial|1|2"
    frame = normalize_keys(pd.DataFrame([{"location": "MOValley", "experiment": "Hyrbrids", "range": 1, "row": 2}]))
    assert frame.iloc[0].plot_id == "MOValley|Hybrids|1|2"


def test_band_mapping_border_mask_and_safe_index():
    array = np.zeros((6, 1, 3))
    array[:, 0, 1] = [2, 3, 1, 6, 4, 1]
    array[:, 0, 2] = np.nan
    result = summarize_pixels(array, CONFIG["band_mapping"])
    assert result["valid_pixels"] == 1
    assert result["red"] == 2
    assert result["ndvi"] == pytest.approx(0.5)
    assert result["ndre"] == pytest.approx(0.2)
    assert np.isnan(safe_index([0], [0])[0])
    assert metadata_conflicts(["Pleiades NEO NIR (0.7 - 0.8) um"] + [None]*5, CONFIG["band_mapping"])
    assert not metadata_conflicts(["Red", "Green", "Blue", "NIR", "Red Edge", "Deep Blue"], CONFIG["band_mapping"])


def test_cutoff_invariant_to_future_images_and_missing_observations():
    plots, images = fixture_data()
    early = build_cutoff_features(plots, images, [60])
    future = images.iloc[[0]].copy()
    future["image_date"] = pd.Timestamp("2022-10-01")
    future["timepoint"] = "TP9"
    future["ndvi"] = 999
    same = build_cutoff_features(plots, pd.concat([images, future]), [60])
    pd.testing.assert_frame_equal(early, same)
    missing_id = plots.iloc[0].plot_id
    missing = build_cutoff_features(plots, images.loc[images.plot_id.ne(missing_id)], [60])
    row = missing.loc[missing.plot_id.eq(missing_id)].iloc[0]
    assert row.missing_imagery == 1 and row.observation_count == 0
    assert np.isnan(row.latest_ndvi)
    late = build_cutoff_features(plots, images, [75])
    assert (late.observation_count == 2).all()
    assert np.allclose(late.delta_ndvi, 0.25)
    assert (late.image_age_days == 10).all()


def test_empty_observation_table_retains_plots():
    plots, images = fixture_data()
    result = build_cutoff_features(plots, images.iloc[:0], [60])
    assert len(result) == len(plots)
    assert result.missing_imagery.eq(1).all()


def test_fold_isolation_and_feature_allowlist():
    plots, images = fixture_data()
    data = build_cutoff_features(plots, images, [75])
    for _, train, test in location_folds(data):
        assert set(train.location).isdisjoint(test.location)
        assert set(train.plot_id).isdisjoint(test.plot_id)
    matrix = model_matrix(data, AGRONOMY + IMAGE_FEATURES)
    assert not {"yieldPerAcre", "daysToAnthesis", "GDDToAnthesis", "totalStandCount", "plot_id", "location"}.intersection(matrix)
    with pytest.raises(ValueError):
        model_matrix(data, ["yieldPerAcre"])
    integer_irrigation = model_matrix(data.assign(irrigationProvided=1), AGRONOMY)
    float_irrigation = model_matrix(data.assign(irrigationProvided=1.0), AGRONOMY)
    pd.testing.assert_frame_equal(integer_irrigation, float_irrigation)


def test_scouting_metrics_known_ranking():
    frame = pd.DataFrame({"plot_id": [str(x) for x in range(10)], "yieldPerAcre": range(10), "predicted_yield": range(10)})
    result = scouting_metrics(frame)
    assert result["k"] == 1 and result["hits"] == 1
    assert result["precision_at_k"] == 1 and result["recall_at_k"] == 0.5


def test_training_and_unlabeled_inference(tmp_path):
    plots, images = fixture_data()
    features = build_cutoff_features(plots, images, [60, 75])
    predictions, metrics = evaluate(features, tmp_path, CONFIG, smoke=True)
    assert len(predictions) == len(features) * 3
    assert predictions.predicted_yield.notna().all()
    assert set(metrics.model) == {"mean", "agronomy", "combined"}
    table = scout_table(predictions, 60, "A")
    assert "yieldPerAcre" not in table and table.selected.sum() == 1
    pd.testing.assert_frame_equal(table.reset_index(drop=True),
        pd.read_csv(tmp_path / "scouting_priorities.csv", dtype={"range": str, "row": str}, parse_dates=["prediction_date"])
        .query("cutoff == 60 and location == 'A'").reset_index(drop=True), check_dtype=False)
    unlabeled = features.copy()
    unlabeled["yieldPerAcre"] = np.nan
    predict(unlabeled, tmp_path / "models", tmp_path / "new", CONFIG)
    inference = pd.read_csv(tmp_path / "new" / "inference_predictions.csv")
    assert len(inference) == len(features)
    assert "yieldPerAcre" not in inference


def test_records_without_yield_column(tmp_path):
    plots, _ = fixture_data()
    (tmp_path / "GroundTruth").mkdir()
    plots.drop(columns="yieldPerAcre").to_csv(tmp_path / "GroundTruth" / "plots.csv", index=False)
    records = load_records(tmp_path)
    assert records.yieldPerAcre.isna().all()
