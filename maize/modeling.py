from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

from .data import AGRONOMY, CATEGORICAL, IMAGE_FEATURES
from .uav import UAV_FEATURES, SETTINGS as UAV_SETTINGS

VARIANTS = {"agronomy": AGRONOMY, "combined": AGRONOMY + IMAGE_FEATURES}
UAV_VARIANTS = {"agronomy_uav": AGRONOMY + UAV_FEATURES,
                "combined_uav": AGRONOMY + IMAGE_FEATURES + UAV_FEATURES}


def model_matrix(frame, columns):
    """Explicit allowlist excludes all targets and post-cutoff measurements."""
    if not set(columns).issubset(set(AGRONOMY + IMAGE_FEATURES + UAV_FEATURES)):
        raise ValueError("Disallowed model feature.")
    result = frame[columns].copy()
    for col in columns:
        if col == "irrigationProvided":
            numeric = pd.to_numeric(result[col], errors="coerce")
            result[col] = numeric.map(lambda x: "__MISSING__" if pd.isna(x) else f"{x:g}")
        elif col in CATEGORICAL:
            result[col] = result[col].fillna("__MISSING__").astype(str)
        else:
            result[col] = pd.to_numeric(result[col], errors="coerce").replace([np.inf, -np.inf], np.nan).astype(float)
    return result


def location_folds(frame):
    sites = sorted(frame.location.unique())
    if len(sites) < 2:
        raise ValueError("At least two locations are required for held-out-location evaluation.")
    for site in sites:
        train, test = frame.loc[frame.location.ne(site)], frame.loc[frame.location.eq(site)]
        assert set(train.location).isdisjoint(test.location)
        assert set(train.plot_id).isdisjoint(test.plot_id)
        yield site, train, test


def fit_model(frame, columns, settings):
    model = CatBoostRegressor(**settings, verbose=False, allow_writing_files=False)
    model.fit(model_matrix(frame, columns), frame.yieldPerAcre,
              cat_features=[name for name in CATEGORICAL if name in columns])
    return model


def rank_correlation(group):
    if group.predicted_yield.nunique() < 2 or group.yieldPerAcre.nunique() < 2:
        return np.nan
    return float(group.predicted_yield.corr(group.yieldPerAcre, method="spearman"))


def regression_metrics(group):
    error = group.predicted_yield - group.yieldPerAcre
    correlations = [rank_correlation(site) for _, site in group.groupby("location")]
    valid = [x for x in correlations if np.isfinite(x)]
    return {"n": len(group), "mae": float(error.abs().mean()),
            "rmse": float(np.sqrt(np.mean(error ** 2))), "bias": float(error.mean()),
            "within_site_spearman": float(np.mean(valid)) if valid else np.nan}


def scouting_count(total, fraction=0.1, capacity=None):
    """Resolve an exact plot count, while retaining fractional batch-report support."""
    if capacity is not None:
        if isinstance(capacity, bool) or not isinstance(capacity, (int, np.integer)) or not 1 <= capacity <= total:
            raise ValueError("Scouting capacity must be an integer from 1 to the number of plots.")
        return int(capacity)
    if not 0 < fraction <= 1:
        raise ValueError("Scouting fraction must be between 0 and 1.")
    return max(1, math.ceil(total * fraction))


def scouting_metrics(group, fraction=0.1, underperformance=0.2, *, capacity=None):
    k = scouting_count(len(group), fraction, capacity)
    target_n = max(1, math.ceil(len(group) * underperformance))
    true_low = set(group.sort_values(["yieldPerAcre", "plot_id"]).head(target_n).plot_id)
    chosen = set(group.sort_values(["predicted_yield", "plot_id"]).head(k).plot_id)
    hits = len(true_low & chosen)
    return {"k": k, "target_n": target_n, "hits": hits, "precision_at_k": hits / k, "recall_at_k": hits / target_n}


def scout_table(predictions, cutoff, location, fraction=0.1, *, capacity=None, model="combined"):
    frame = predictions.loc[predictions.cutoff.eq(cutoff) & predictions.location.eq(location)
                            & predictions.model.eq(model)].copy()
    frame = frame.sort_values(["predicted_yield", "plot_id"]).reset_index(drop=True)
    k = scouting_count(len(frame), fraction, capacity)
    frame["scouting_rank"] = np.arange(1, len(frame) + 1)
    frame["selected"] = frame.scouting_rank.le(k)
    columns = ["scouting_rank", "selected", "plot_id", "location", "experiment", "range", "row", "genotype",
               "cutoff", "prediction_date", "predicted_yield", "delta_ndvi", "image_age_days", "observation_count", "missing_imagery"]
    columns += [c for c in ["model", *UAV_FEATURES] if c in frame]
    return frame[columns]


def evaluate(features, output, config, smoke=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    models_dir = output / "models"
    models_dir.mkdir(exist_ok=True)
    labeled = features.loc[features.yieldPerAcre.notna()].copy()
    if labeled.empty:
        raise ValueError("No labeled plots available for evaluation.")
    variants = {**VARIANTS, **(UAV_VARIANTS if config.get("include_uav") else {})}
    settings = dict(config["model"])
    if smoke:
        settings["iterations"] = 10
        ids = labeled.drop_duplicates("plot_id").groupby("location").head(15).plot_id
        labeled = labeled.loc[labeled.plot_id.isin(ids)]
    predictions, fold_audit = [], []
    for cutoff, data in labeled.groupby("cutoff", sort=True):
        print(f"Evaluating cutoff {cutoff}: {len(data)} plots", flush=True)
        for site, train, test in location_folds(data):
            fold_audit.append({"cutoff": int(cutoff), "held_out_site": site,
                               "training_sites": sorted(train.location.unique()),
                               "training_plots": len(train), "test_plots": len(test)})
            for variant in ["mean", *variants]:
                if variant == "mean":
                    values = np.full(len(test), train.yieldPerAcre.mean())
                else:
                    model = fit_model(train, variants[variant], settings)
                    values = model.predict(model_matrix(test, variants[variant]))
                columns = ["plot_id", "location", "experiment", "range", "row", "genotype", "cutoff", "prediction_date",
                           "yieldPerAcre", "delta_ndvi", "image_age_days", "observation_count", "missing_imagery"]
                columns += [c for c in UAV_FEATURES if c in test]
                result = test[columns].copy()
                result["predicted_yield"] = values
                result["model"] = variant
                result["prediction_kind"] = "held_out_location"
                predictions.append(result)
            print(f"  Held out {site}", flush=True)
        for variant, columns in variants.items():
            model = fit_model(data, columns, settings)
            name = f"{variant}_{int(cutoff)}"
            model.save_model(str(models_dir / f"{name}.cbm"))
            (models_dir / f"{name}.json").write_text(json.dumps({
                "features": columns, "cutoff": int(cutoff), "variant": variant,
                "training_years": sorted(pd.to_datetime(data.prediction_date).dt.year.unique().tolist()),
                "training_locations": sorted(data.location.unique()), "training_plots": len(data),
                "band_mapping": config["band_mapping"], "parameters": settings,
                "uav_settings": UAV_SETTINGS if variant in UAV_VARIANTS else None,
                "warning": "Full-data fit for inference only; never use for reported validation metrics."
            }, indent=2), encoding="utf-8")
    predicted = pd.concat(predictions, ignore_index=True)
    if predicted.duplicated(["plot_id", "cutoff", "model"]).any():
        raise AssertionError("Duplicate held-out predictions.")
    predicted.to_csv(output / "held_out_predictions.csv", index=False)
    metrics, scouting = [], []
    for (cutoff, variant), group in predicted.groupby(["cutoff", "model"]):
        metrics.append({"cutoff": cutoff, "model": variant, "location": "Overall", **regression_metrics(group)})
        for site, subset in group.groupby("location"):
            metrics.append({"cutoff": cutoff, "model": variant, "location": site, **regression_metrics(subset)})
            scouting.append({"cutoff": cutoff, "model": variant, "location": site,
                             **scouting_metrics(subset, config["scouting_fraction"], config["underperformance_fraction"])})
    metrics, scouting = pd.DataFrame(metrics), pd.DataFrame(scouting)
    metrics.to_csv(output / "metrics.csv", index=False)
    totals = scouting.groupby(["cutoff", "model"])[["k", "target_n", "hits"]].sum().reset_index()
    totals["location"] = "Overall"
    totals["precision_at_k"] = totals.hits / totals.k
    totals["recall_at_k"] = totals.hits / totals.target_n
    scouting = pd.concat([scouting, totals], ignore_index=True)
    scouting.to_csv(output / "scouting_metrics.csv", index=False)
    fixed_rows = []
    for (cutoff, variant), group in predicted.groupby(["cutoff", "model"]):
        local = []
        for site, subset in group.groupby("location"):
            row = dict(cutoff=cutoff, model=variant, location=site,
                       **regression_metrics(subset), **scouting_metrics(subset, capacity=min(10, len(subset))))
            fixed_rows.append(row)
            local.append(row)
        totals = pd.DataFrame(local)
        fixed_rows.append(dict(cutoff=cutoff, model=variant, location="Overall",
                               **regression_metrics(group), k=int(totals.k.sum()), hits=int(totals.hits.sum()),
                               target_n=int(totals.target_n.sum()), precision_at_k=totals.hits.sum()/totals.k.sum(),
                               recall_at_k=totals.hits.sum()/totals.target_n.sum()))
    pd.DataFrame(fixed_rows).to_csv(output / "model_comparison.csv", index=False)
    all_lists = [scout_table(predicted, cutoff, site, capacity=min(10, len(group)), model=variant)
                 for (cutoff, site, variant), group in predicted.groupby(["cutoff", "location", "model"])]
    pd.concat(all_lists, ignore_index=True).to_csv(output / "scouting_priorities_10.csv", index=False)
    lists = [scout_table(predicted, cutoff, site, config["scouting_fraction"])
             for cutoff in sorted(predicted.cutoff.unique()) for site in sorted(predicted.location.unique())]
    pd.concat(lists, ignore_index=True).to_csv(output / "scouting_priorities.csv", index=False)
    (output / "fold_audit.json").write_text(json.dumps(fold_audit, indent=2), encoding="utf-8")
    (output / "run_config.json").write_text(json.dumps({**config, "smoke_test": smoke}, indent=2), encoding="utf-8")
    make_report(metrics, scouting, predicted, output, smoke)
    return predicted, metrics


def make_report(metrics, scouting, predicted, output, smoke):
    import os
    os.environ.setdefault("MPLCONFIGDIR", str((output / ".matplotlib").resolve()))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    overall = metrics.loc[metrics.location.eq("Overall")]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for variant, group in overall.groupby("model"):
        ax.plot(group.cutoff, group.mae, marker="o", label=variant)
    ax.set(xlabel="Days after planting", ylabel="Held-out MAE (bushels/acre)", title="2022: transfer to an unseen location")
    ax.legend(); ax.grid(alpha=0.2); fig.tight_layout()
    fig.savefig(output / "accuracy_vs_time.png", dpi=160); plt.close(fig)
    last = predicted.loc[predicted.model.eq("combined") & predicted.cutoff.eq(predicted.cutoff.max())]
    fig, ax = plt.subplots(figsize=(6, 5))
    for site, group in last.groupby("location"):
        ax.scatter(group.yieldPerAcre, group.predicted_yield, s=10, alpha=0.5, label=site)
    low = min(last.yieldPerAcre.min(), last.predicted_yield.min())
    high = max(last.yieldPerAcre.max(), last.predicted_yield.max())
    ax.plot([low, high], [low, high], "k--", linewidth=1)
    ax.set(xlabel="Actual yield (bu/ac)", ylabel="Held-out predicted yield (bu/ac)", title=f"Combined model at {int(last.cutoff.max())} days")
    ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(output / "predicted_vs_actual.png", dpi=160); plt.close(fig)
    lines = ["# Maize yield evaluation", "", "SMOKE TEST ONLY" if smoke else "2022 historical replay: five held-out-location folds.", "",
             "Units: bushels/acre at 15.5% moisture. Results test spatial transfer in 2022, not future-season accuracy.", "",
             "| Cutoff | Agronomy MAE | Combined MAE | Improvement (%) | Combined precision@K |", "|---|---|---|---|---|"]
    for cutoff in sorted(overall.cutoff.unique()):
        rows = overall.loc[overall.cutoff.eq(cutoff)].set_index("model")
        a, c = rows.loc["agronomy", "mae"], rows.loc["combined", "mae"]
        precision = scouting.loc[scouting.location.eq("Overall") & scouting.model.eq("combined") & scouting.cutoff.eq(cutoff), "precision_at_k"].iloc[0]
        lines.append(f"| {cutoff} | {a:.2f} | {c:.2f} | {100*(a-c)/a:.1f} | {precision:.1%} |")
    lines += ["", "![Accuracy versus time](accuracy_vs_time.png)", "", "![Predicted versus actual](predicted_vs_actual.png)", "",
              "Scouting precision uses a 10% per-site budget by default and the lowest-yielding 20% as retrospective targets. Ties use plot ID for reproducibility.",
              "Overall errors are plot-weighted; within-site Spearman is the unweighted mean of defined site correlations.",
              "No automatic trustworthy cutoff is declared: operational error tolerance and future-season validation remain necessary.",
              "At 60 days Missouri Valley lacks satellite coverage. Missing imagery is retained, not silently dropped.",
              "Scouting identifies predicted low yield, not confirmed remediable stress. Hybrid rankings are conditional predictions, not causal genetic comparisons."]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def predict(features, models_dir, output, config, model_name="combined"):
    models_dir, output = Path(models_dir), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for cutoff, group in features.groupby("cutoff"):
        name = f"{model_name}_{int(cutoff)}"
        metadata = json.loads((models_dir / f"{name}.json").read_text(encoding="utf-8"))
        if metadata["band_mapping"] != config["band_mapping"]:
            raise ValueError("Inference band mapping differs from training.")
        if metadata.get("uav_settings") and metadata["uav_settings"] != UAV_SETTINGS:
            raise ValueError("UAV extraction settings differ from training")
        missing = set(metadata["features"]) - set(group.columns)
        if missing:
            raise ValueError(f"Missing inference features: {sorted(missing)}")
        model = CatBoostRegressor()
        model.load_model(str(models_dir / f"{name}.cbm"))
        result = group.drop(columns=["yieldPerAcre", "daysToAnthesis", "GDDToAnthesis", "totalStandCount"], errors="ignore").copy()
        result["predicted_yield"] = model.predict(model_matrix(group, metadata["features"]))
        result["model"] = model_name
        result["prediction_kind"] = "full_data_model_inference_not_validation"
        results.append(result)
    pd.concat(results, ignore_index=True).to_csv(output / "inference_predictions.csv", index=False)
