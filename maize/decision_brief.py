"""IoT4Ag decision evidence: fixed warning rule and nitrogen-only ablation."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .modeling import fit_model, location_folds, model_matrix, regression_metrics, scouting_metrics
from .insights import hybrid_tables, compare_rankings

MODEL_LABELS = {"mean": "Training mean", "nitrogen": "Nitrogen only", "agronomy": "Agronomic records", "combined": "Agronomy + satellite"}


def warning_queue(frame, capacity=10):
    """Predictions only. A fixed bottom-20% screen starts at day 75."""
    if frame.location.nunique() != 1 or frame.cutoff.nunique() != 1:
        raise ValueError("Choose one location and cutoff")
    if not isinstance(capacity, (int, np.integer)) or isinstance(capacity, bool) or not 1 <= capacity <= len(frame):
        raise ValueError("Capacity must be an integer between 1 and the plot count")
    names = ["plot_id", "location", "experiment", "range", "row", "genotype", "cutoff", "prediction_date", "predicted_yield", "delta_ndvi", "image_age_days", "observation_count", "missing_imagery"]
    result = frame[names].sort_values(["predicted_yield", "plot_id"]).reset_index(drop=True).copy()
    result["priority"] = np.arange(1, len(result) + 1)
    result["selected"] = result.priority.le(capacity)
    active = int(result.cutoff.iloc[0]) >= 75
    result["warning_flag"] = result.priority.le(math.ceil(len(result) * .2)) & active
    result["recent_ndvi_decline"] = result.delta_ndvi.lt(0) & result.observation_count.ge(2)
    result["invalid_negative_prediction"] = result.predicted_yield.lt(0)
    result["action"] = np.where(result.warning_flag, "Inspect for possible underperformance", "Routine review / capacity beyond warning list" if active else "Supporting replay only; warning rule starts day 75")
    return result


def build(output=Path("outputs"), reuse=False):
    output = Path(output)
    dest = output / "decision_brief"
    dest.mkdir(exist_ok=True, parents=True)
    features = pd.read_parquet(output / "features.parquet")
    features = features.loc[features.yieldPerAcre.notna()].copy()
    config = json.loads((output / "run_config.json").read_text())
    existing = pd.read_csv(output / "held_out_predictions.csv")
    n_path = dest / "nitrogen_predictions.csv"
    if not reuse:
        results, folds = [], []
        for cutoff, group in features.groupby("cutoff"):
            for site, train, test in location_folds(group):
                model = fit_model(train, ["poundsOfNitrogenPerAcre"], config["model"])
                rows = existing.loc[existing.model.eq("combined") & existing.cutoff.eq(cutoff) & existing.location.eq(site)].copy()
                indexed = test.set_index("plot_id").loc[rows.plot_id]
                rows["predicted_yield"] = model.predict(model_matrix(indexed, ["poundsOfNitrogenPerAcre"]))
                rows["model"] = "nitrogen"
                results.append(rows)
                folds.append(dict(cutoff=int(cutoff), held_out_site=site, training_sites=sorted(train.location.unique()), features=["poundsOfNitrogenPerAcre"], parameters=config["model"]))
        pd.concat(results, ignore_index=True).to_csv(n_path, index=False)
        (dest / "nitrogen_fold_audit.json").write_text(json.dumps(folds, indent=2))
    predictions = pd.concat([existing, pd.read_csv(n_path)], ignore_index=True)
    assert not predictions.duplicated(["plot_id", "model", "cutoff"]).any()
    ids = set(features.plot_id)
    metrics, thresholds, queues, ranks = [], [], [], []
    plots = features.drop_duplicates("plot_id").copy()
    plots["year"] = pd.to_datetime(plots.plantingDate).dt.year
    _, observed_sites, _ = hybrid_tables(plots, "yieldPerAcre")
    for (cutoff, model), group in predictions.groupby(["cutoff", "model"]):
        assert set(group.plot_id) == ids
        assert np.isfinite(group.predicted_yield).all()
        merged = plots[["plot_id", "yieldPerAcre"]].merge(group, on="plot_id", validate="one_to_one", suffixes=("_source", ""))
        assert np.allclose(merged.yieldPerAcre_source, merged.yieldPerAcre)
        site_rows = []
        for site, g in group.groupby("location"):
            score = scouting_metrics(g, capacity=min(10, len(g)))
            row = dict(cutoff=int(cutoff), model=model, location=site, **regression_metrics(g), **score)
            metrics.append(row); site_rows.append(row)
            if model == "combined":
                queue = warning_queue(g)
                queues.append(queue)
                if cutoff >= 75:
                    warning = scouting_metrics(g, fraction=.2)
                    thresholds.append(dict(cutoff=int(cutoff), location=site, warning_yield_boundary=float(queue.loc[queue.warning_flag, "predicted_yield"].max()), **warning))
        total = pd.DataFrame(site_rows)
        metrics.append(dict(cutoff=int(cutoff), model=model, location="Overall", **regression_metrics(group), k=int(total.k.sum()), target_n=int(total.target_n.sum()), hits=int(total.hits.sum()), precision_at_k=total.hits.sum()/total.k.sum(), recall_at_k=total.hits.sum()/total.target_n.sum()))
        predicted_plots = plots.drop(columns="yieldPerAcre").merge(group[["plot_id", "predicted_yield"]], on="plot_id", validate="one_to_one")
        _, forecast_sites, _ = hybrid_tables(predicted_plots, "predicted_yield")
        ranks.append(compare_rankings(observed_sites, forecast_sites).assign(cutoff=cutoff, model=model))
    metrics = pd.DataFrame(metrics)
    thresholds = pd.DataFrame(thresholds)
    queue = pd.concat(queues, ignore_index=True)
    ranking = pd.concat(ranks, ignore_index=True)
    for name, frame in [("model_comparison", metrics), ("warning_evaluation", thresholds), ("scouting_queue", queue), ("ranking_comparison", ranking)]:
        frame.to_csv(dest / f"{name}.csv", index=False)
    # Site and date chosen in advance; examples illustrate hits and misses, not average performance.
    example_site, example_cutoff = "Ames", 75
    g = predictions.query("location == @example_site and cutoff == @example_cutoff and model == 'combined'").copy()
    q = warning_queue(g).merge(g[["plot_id", "yieldPerAcre"]], on="plot_id", validate="one_to_one")
    low = set(g.sort_values(["yieldPerAcre", "plot_id"]).head(math.ceil(len(g)*.2)).plot_id)
    q["actual_bottom_20"] = q.plot_id.isin(low)
    hit = q.loc[q.selected & q.actual_bottom_20].sort_values("priority").head(1).assign(example="Caught within 10 visits")
    miss = q.loc[~q.selected & q.actual_bottom_20].sort_values(["yieldPerAcre", "plot_id"]).head(1).assign(example="Missed within 10 visits")
    cases = pd.concat([hit, miss])
    before = predictions.query("location == @example_site and cutoff == @example_cutoff").pivot(index="plot_id", columns="model", values="predicted_yield")
    cases = cases.merge(before[["nitrogen", "agronomy"]], left_on="plot_id", right_index=True, validate="one_to_one")
    cases.to_csv(dest / "case_examples.csv", index=False)
    summary = metrics.loc[metrics.location.eq("Overall")]
    warning_summary = thresholds.groupby("cutoff")[["k", "target_n", "hits"]].sum().reset_index()
    warning_summary["precision"] = warning_summary.hits / warning_summary.k
    warning_summary["recall"] = warning_summary.hits / warning_summary.target_n
    claims = dict(scope="2022 historical replay - held-out-location predictions", plots=len(plots), locations=5, hybrids=int(plots.genotype.nunique()),
                  rule="From day 75, flag the lowest predicted 20% within each site, then inspect plots in priority order up to capacity.",
                  rule_status="Fixed candidate screening rule; not tuned here, not validated for preventable stress or future seasons.",
                  capacity=10, overall=summary.replace({np.nan:None}).to_dict("records"), warning=warning_summary.to_dict("records"),
                  ranking=ranking.groupby(["cutoff", "model"])[["spearman", "top10_overlap"]].mean().reset_index().replace({np.nan:None}).to_dict("records"),
                  cases=cases.replace({np.nan:None}).to_dict("records"),
                  tie_rule="Prediction then plot ID; nitrogen-only predictions tie for plots at the same nitrogen rate. Top-K performance therefore depends on deterministic tie-breaking.",
                  inputs_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [output/"features.parquet", output/"held_out_predictions.csv", n_path]})
    (dest / "claims.json").write_text(json.dumps(claims, indent=2, allow_nan=False))
    print(summary[["cutoff", "model", "mae", "precision_at_k", "recall_at_k"]].round(3).to_string(index=False))
    print(warning_summary.to_string(index=False))
    return claims


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--reuse-nitrogen", action="store_true")
    args=parser.parse_args()
    build(args.output, args.reuse_nitrogen)
