from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from maize.scouting_trip import build_coordinates, scouting_route, trip_totals

ROOT = Path(__file__).resolve().parents[1]


def test_loop_distance_order_and_timing():
    points = pd.DataFrame({"plot_id": ["a", "b", "c"], "location": ["site"] * 3,
                           "latitude": [0., 0., 0.], "longitude": [0., .02, .01]})
    route, miles, back = scouting_route(points, points)
    assert route.plot_id.tolist() == ["a", "c", "b"]
    assert miles == pytest.approx(2.7637, rel=.001)
    assert back == pytest.approx(miles / 2)
    assert route.leg_miles.sum() + back == pytest.approx(miles)
    totals = trip_totals(3, 2., walking_mph=2., minutes_per_plot=10.,
                         one_way_drive_miles=30., driving_mph=60.)
    assert totals["driving_miles"] == 60
    assert totals["total_hours"] == 2.5
    _, single_miles, back = scouting_route(points.head(1), points)
    assert single_miles == back == 0
    assert trip_totals(1, single_miles)["total_hours"] == pytest.approx(5 / 60)


def test_missing_coordinates_and_invalid_assumptions_are_not_silent():
    selected = pd.DataFrame({"plot_id": ["a", "b"], "location": ["site", "site"]})
    coords = pd.DataFrame({"plot_id": ["a"], "latitude": [40.], "longitude": [-90.]})
    with pytest.raises(ValueError, match="1 of 2"):
        scouting_route(selected, coords)
    with pytest.raises(ValueError, match="finite"):
        trip_totals(10, float("nan"))
    with pytest.raises(ValueError, match="positive"):
        trip_totals(10, 1., walking_mph=0.)


def test_saved_coordinates_cover_every_forecast_plot():
    predictions = pd.read_csv(ROOT / "outputs/held_out_predictions.csv")
    coords = pd.read_csv(ROOT / "outputs/plot_coordinates.csv")
    assert not coords.plot_id.duplicated().any()
    assert set(predictions.plot_id) <= set(coords.plot_id)
    for _, site in predictions.query("cutoff == 75 and model == 'combined'").groupby("location"):
        selected = site.sort_values(["predicted_yield", "plot_id"]).head(10)
        route, miles, _ = scouting_route(selected, coords)
        assert set(route.plot_id) == set(selected.plot_id)
        assert 0 < miles < 10


def test_coordinate_extraction_uses_georeferencing_and_canonical_ids(tmp_path):
    import rasterio
    from rasterio.transform import from_origin
    folder = tmp_path / "Satellite"
    folder.mkdir()
    for tp in [1, 2]:
        with rasterio.open(folder / f"Missouri Valley-TP{tp}-Hyrbrids_1_2.TIF", "w",
                           driver="GTiff", height=2, width=2, count=1, dtype="uint8",
                           crs="EPSG:4326", transform=from_origin(-90., 40., .001, .001)):
            pass
    result = build_coordinates(tmp_path, tmp_path / "coordinates.csv")
    assert len(result) == 1
    assert result.iloc[0].plot_id == "MOValley|Hybrids|1|2"
    assert result.iloc[0].latitude == pytest.approx(39.999)
    assert result.iloc[0].longitude == pytest.approx(-89.999)


def test_ui_updates_capacity_assumptions_and_driving():
    app = AppTest.from_file(str(ROOT / "scouting.py"), default_timeout=30).run()
    assert not app.exception
    def metric(label):
        return next(x.value for x in app.metric if x.label == label)
    assert metric("Inspection time") == "0.83 hr"
    next(x for x in app.number_input if x.label == "Number of trial plots to scout").set_value(20).run()
    assert not app.exception
    assert metric("Inspection time") == "1.67 hr"
    next(x for x in app.number_input if x.label == "Inspection minutes per plot").set_value(3.).run()
    assert metric("Inspection time") == "1.00 hr"
    field_time = float(metric("Walking + inspection").split()[0])
    next(x for x in app.checkbox if x.label == "Include round-trip driving to this site").check().run()
    next(x for x in app.number_input if x.label == "One-way road distance to site (miles)").set_value(20.).run()
    assert not app.exception
    assert float(metric("Total trip time").split()[0]) == pytest.approx(field_time + 1., abs=.011)
    assert any(x.label == "Download trip estimate and visit order" for x in app.get("download_button"))
