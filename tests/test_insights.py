import numpy as np
import pandas as pd
import pytest
from maize.insights import hybrid_tables, nitrogen_tables, compare_rankings, ridge_pipeline


def records():
    rows = []
    for site, offset in [("A", 0), ("B", 100), ("C", 40), ("D", 20), ("E", 50)]:
        for rate in [75, 150]:
            for hybrid, value in [("H1", 50), ("H2", 100), ("H3", 150)]:
                for rep in range(2):
                    rows.append({"location": site, "year": 2022, "poundsOfNitrogenPerAcre": rate, "irrigationProvided": 0,
                                 "genotype": hybrid, "plot_id": f"{site}-{rate}-{hybrid}-{rep}", "yield": value + offset + rate / 10})
    return pd.DataFrame(rows)


def test_extra_replicates_do_not_change_hybrid_weights():
    data = records()
    cells, sites, overall = hybrid_tables(data, "yield")
    extra = data.loc[data.genotype.eq("H1") & data.location.eq("A")]
    c2, s2, o2 = hybrid_tables(pd.concat([data, extra, extra]), "yield")
    np.testing.assert_allclose(cells.percentile, c2.percentile)
    np.testing.assert_allclose(cells.environment_mean, c2.environment_mean)
    np.testing.assert_allclose(overall.average_percentile, o2.average_percentile)
    assert overall.iloc[0].genotype == "H3" and overall.iloc[0].sites_above_median == 5
    assert not overall.loc[overall.genotype.eq("H2"), "qualifies"].iloc[0]


def test_sites_and_treatments_have_equal_weight():
    data = records()
    data.loc[data.location.eq("A") & data.genotype.eq("H3"), "yield"] = -100
    _, sites, overall = hybrid_tables(data, "yield")
    h3 = overall.loc[overall.genotype.eq("H3")].iloc[0]
    assert h3.average_percentile == pytest.approx(80)
    assert h3.worst_site_percentile == 0
    assert h3.sites_above_median == 4
    assert h3.between_site_sd == pytest.approx(40)


def test_constant_forecast_has_no_ranking_and_no_shortlist():
    data = records()
    _, observed, _ = hybrid_tables(data, "yield")
    data["forecast"] = 120.1
    _, predicted, hybrids = hybrid_tables(data, "forecast")
    assert predicted.site_percentile.eq(50).all()
    result = compare_rankings(observed, predicted)
    assert result.spearman.isna().all() and result.top10_overlap.isna().all()
    assert not hybrids.shortlisted.any()


def test_nitrogen_pairs_match_hybrid_site_and_replicates():
    data = records()
    data = data.loc[~(data.location.eq("E") & data.poundsOfNitrogenPerAcre.eq(150))]
    cells, _, _ = hybrid_tables(data, "yield")
    pairs, sites, hybrids = nitrogen_tables(cells)
    assert len(pairs) == 12
    assert "E" not in set(pairs.location)
    assert pairs.replicates_75.eq(2).all()
    assert np.allclose(pairs.difference_150_minus_75, 7.5)
    assert sites.matched_hybrids.eq(3).all()


def test_observed_and_forecast_rankings_are_separate():
    data = records()
    _, obs, _ = hybrid_tables(data, "yield")
    data["forecast"] = -data["yield"]
    _, pred, _ = hybrid_tables(data, "forecast")
    result = compare_rankings(obs, pred)
    assert np.allclose(result.spearman, -1)


def test_ridge_preprocessing_does_not_learn_from_test():
    from maize.data import AGRONOMY
    from maize.modeling import model_matrix
    train = pd.DataFrame({"planting_doy": [120., 140., np.nan], "poundsOfNitrogenPerAcre": [75, 150, 75],
                          "irrigationProvided": [0, 0, 0], "genotype": ["A", "B", "A"]})
    pipe = ridge_pipeline(AGRONOMY, 10)
    pipe.fit(model_matrix(train, AGRONOMY), [100, 150, 110])
    before = pipe.named_steps["prepare"].named_transformers_["numeric"].named_steps["impute"].statistics_.copy()
    test = train.iloc[:1].assign(planting_doy=9999, genotype="UNSEEN")
    assert np.isfinite(pipe.predict(model_matrix(test, AGRONOMY))).all()
    np.testing.assert_array_equal(before, pipe.named_steps["prepare"].named_transformers_["numeric"].named_steps["impute"].statistics_)


def test_primary_dashboard_separates_observed_forecasts_and_scouting():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    root = Path(__file__).resolve().parents[1]
    if not (root / "outputs/broad_performance/claims.json").exists():
        pytest.skip("Run broad-performance analysis first")
    app = AppTest.from_file(str(root / "dashboard.py"), default_timeout=30).run()
    app.radio[0].set_value("Hybrid performance").run()
    assert not app.exception
    assert any("OBSERVED VIEW" in x.value for x in app.info)
    expected = pd.read_csv(root / "outputs/broad_performance/observed_hybrids.csv")
    assert app.dataframe[0].value.Hybrid.tolist() == expected.loc[expected.shortlisted].genotype.tolist()
    next(x for x in app.selectbox if x.label == "Evidence source").select("Forecast (held-out sites)").run()
    assert not app.exception
    assert any("FORECAST VIEW" in x.value for x in app.info)
    forecast = pd.read_csv(root / "outputs/broad_performance/forecast_hybrids.csv").query("model == 'combined' and cutoff == 90 and shortlisted")
    assert app.dataframe[0].value.Hybrid.tolist() == forecast.genotype.tolist()
    app.radio[0].set_value("Scouting (secondary)").run()
    assert not app.exception
    assert any("Scouting priorities" == x.label for x in app.tabs)
