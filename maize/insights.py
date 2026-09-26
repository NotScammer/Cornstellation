"""Reproducible, equally weighted hybrid comparisons and nested Ridge validation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .data import CATEGORICAL
from .modeling import VARIANTS, location_folds, model_matrix, regression_metrics

ENV = ["location", "year", "poundsOfNitrogenPerAcre", "irrigationProvided"]
LABELS = {"mean": "Training mean", "agronomy": "CatBoost: agronomy", "combined": "CatBoost: combined",
          "ridge_agronomy": "Ridge: agronomy", "ridge_combined": "Ridge: combined"}


def ridge_pipeline(columns, alpha):
    numerical = [c for c in columns if c not in CATEGORICAL]
    categorical = [c for c in columns if c in CATEGORICAL]
    numeric_pipe = Pipeline([("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                             ("scale", StandardScaler())])
    prep = ColumnTransformer([("numeric", numeric_pipe, numerical),
                              ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical)])
    return Pipeline([("prepare", prep), ("regressor", Ridge(alpha=alpha, solver="lsqr"))])


def evaluate_ridge(features, output):
    """Alpha selection uses inner held-out sites only. Outer labels remain unseen."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows, audits = [], []
    for cutoff, group in features.loc[features.yieldPerAcre.notna()].groupby("cutoff"):
        for held_out, train, test in location_folds(group):
            for variant, columns in VARIANTS.items():
                candidates = []
                for alpha in [1, 10, 100]:
                    site_errors = []
                    for inner_site, inner_train, inner_test in location_folds(train):
                        pipe = ridge_pipeline(columns, alpha)
                        pipe.fit(model_matrix(inner_train, columns), inner_train.yieldPerAcre)
                        values = pipe.predict(model_matrix(inner_test, columns))
                        site_errors.append(float(np.mean(np.abs(values - inner_test.yieldPerAcre))))
                    candidates.append({"alpha": alpha, "inner_site_mean_mae": float(np.mean(site_errors))})
                chosen = min(candidates, key=lambda r: (r["inner_site_mean_mae"], r["alpha"]))["alpha"]
                pipe = ridge_pipeline(columns, chosen)
                pipe.fit(model_matrix(train, columns), train.yieldPerAcre)
                result = test[["plot_id", "location", "cutoff", "yieldPerAcre"]].copy()
                result["model"] = f"ridge_{variant}"
                result["predicted_yield"] = pipe.predict(model_matrix(test, columns))
                result["prediction_kind"] = "nested_held_out_location"
                rows.append(result)
                audits.append({"cutoff": int(cutoff), "model": f"ridge_{variant}", "held_out_site": held_out,
                               "training_sites": sorted(train.location.unique().tolist()),
                               "inner_validation_sites": sorted(train.location.unique().tolist()),
                               "chosen_alpha": chosen, "candidates": candidates})
            print(f"Ridge: day {cutoff}, held out {held_out}", flush=True)
    predictions = pd.concat(rows, ignore_index=True)
    predictions.to_csv(output / "ridge_predictions.csv", index=False)
    (output / "ridge_fold_audit.json").write_text(json.dumps(audits, indent=2), encoding="utf-8")
    return predictions


def hybrid_tables(frame, value_column):
    """Replicate means, then equal treatment weights, then equal site weights."""
    if frame[ENV + ["genotype", value_column]].isna().any().any():
        raise ValueError("Hybrid analysis requires complete environment, genotype, and yield fields.")
    cells = frame.groupby(ENV + ["genotype"], dropna=False).agg(
        yield_mean=(value_column, "mean"), replicates=("plot_id", "size")).reset_index()
    groups = cells.groupby(ENV, dropna=False)
    cells["environment_mean"] = groups.yield_mean.transform("mean")
    cells["yield_advantage"] = cells.yield_mean - cells.environment_mean
    # Avoid numerical noise turning identical training-mean predictions into ranks.
    cells["ranking_yield"] = cells.yield_mean.round(8)
    ranks = cells.groupby(ENV, dropna=False).ranking_yield.rank(method="average")
    counts = groups.genotype.transform("size")
    cells["percentile"] = np.where(counts > 1, 100 * (ranks - 1) / (counts - 1), 50)
    sites = cells.groupby(["genotype", "location", "year"]).agg(
        site_percentile=("percentile", "mean"), site_yield_advantage=("yield_advantage", "mean"),
        site_yield_mean=("yield_mean", "mean"), treatments=("yield_mean", "size"),
        replicates=("replicates", "sum"), min_cell_replicates=("replicates", "min")).reset_index()
    overall = sites.groupby("genotype").agg(
        average_percentile=("site_percentile", "mean"), worst_site_percentile=("site_percentile", "min"),
        between_site_sd=("site_percentile", lambda x: float(np.std(x, ddof=0))),
        sites_above_median=("site_percentile", lambda x: int((x > 50).sum())),
        sites=("location", "nunique"), site_years=("site_percentile", "size"),
        yield_advantage=("site_yield_advantage", "mean"), replicates=("replicates", "sum"),
        min_cell_replicates=("min_cell_replicates", "min")).reset_index()
    overall = overall.sort_values(["average_percentile", "genotype"], ascending=[False, True]).reset_index(drop=True)
    overall["rank"] = np.arange(1, len(overall) + 1)
    overall["qualifies"] = overall.sites.eq(5) & overall.sites_above_median.ge(4)
    shortlisted = set(overall.loc[overall.qualifies].head(5).genotype)
    overall["shortlisted"] = overall.genotype.isin(shortlisted)
    return cells, sites, overall


def nitrogen_tables(observed_cells):
    keys = ["location", "year", "irrigationProvided", "genotype"]
    low = observed_cells.loc[observed_cells.poundsOfNitrogenPerAcre.eq(75), keys + ["yield_mean", "replicates"]]
    high = observed_cells.loc[observed_cells.poundsOfNitrogenPerAcre.eq(150), keys + ["yield_mean", "replicates"]]
    paired = low.merge(high, on=keys, suffixes=("_75", "_150"), validate="one_to_one")
    paired["difference_150_minus_75"] = paired.yield_mean_150 - paired.yield_mean_75
    by_site = paired.groupby(["location", "year"]).agg(
        mean_difference=("difference_150_minus_75", "mean"),
        median_difference=("difference_150_minus_75", "median"), matched_hybrids=("genotype", "size"),
        positive_hybrids=("difference_150_minus_75", lambda x: int((x > 0).sum())),
        replicates_75=("replicates_75", "sum"), replicates_150=("replicates_150", "sum")).reset_index()
    by_hybrid = paired.groupby("genotype").agg(
        mean_difference=("difference_150_minus_75", "mean"), sites=("location", "nunique"),
        positive_sites=("difference_150_minus_75", lambda x: int((x > 0).sum())),
        min_difference=("difference_150_minus_75", "min"), max_difference=("difference_150_minus_75", "max")).reset_index()
    return paired, by_site, by_hybrid


def compare_rankings(observed_sites, forecast_sites):
    rows = []
    for (site, year), obs in observed_sites.groupby(["location", "year"]):
        pred = forecast_sites.loc[forecast_sites.location.eq(site) & forecast_sites.year.eq(year)]
        both = obs[["genotype", "site_percentile"]].merge(pred[["genotype", "site_percentile"]], on="genotype", suffixes=("_observed", "_forecast"), validate="one_to_one")
        rankable = both.site_percentile_forecast.nunique() > 1 and both.site_percentile_observed.nunique() > 1
        k = min(10, len(both))
        actual = set(both.sort_values(["site_percentile_observed", "genotype"], ascending=[False, True]).head(k).genotype)
        predicted = set(both.sort_values(["site_percentile_forecast", "genotype"], ascending=[False, True]).head(k).genotype)
        rows.append({"location": site, "year": year, "hybrids": len(both), "top_k": k,
                     "spearman": both.site_percentile_observed.corr(both.site_percentile_forecast, method="spearman") if rankable else np.nan,
                     "top10_overlap": len(actual & predicted) if rankable else np.nan,
                     "rankable": rankable})
    return pd.DataFrame(rows)


def build_analysis(base_output, include_ridge=True):
    base = Path(base_output)
    out = base / "broad_performance"
    out.mkdir(parents=True, exist_ok=True)
    features = pd.read_parquet(base / "features.parquet")
    features = features.loc[features.yieldPerAcre.notna()].copy()
    features["year"] = pd.to_datetime(features.plantingDate).dt.year
    if features.year.nunique() != 1:
        raise ValueError("This release is scoped to one season; season identifiers must be incorporated into plot keys before pooling years.")
    plots = features.sort_values("cutoff").drop_duplicates("plot_id").copy()
    required = plots[ENV + ["genotype"]].notna().all(axis=1)
    plots.loc[~required].to_csv(out / "comparison_exclusions.csv", index=False)
    plots = plots.loc[required]
    observed_cells, observed_sites, observed_hybrids = hybrid_tables(plots, "yieldPerAcre")
    for name, table in [("observed_environment", observed_cells), ("observed_site", observed_sites), ("observed_hybrids", observed_hybrids)]:
        table.to_csv(out / f"{name}.csv", index=False)
    paired, nitrogen_sites, nitrogen_hybrids = nitrogen_tables(observed_cells)
    for name, table in [("nitrogen_pairs", paired), ("nitrogen_sites", nitrogen_sites), ("nitrogen_hybrids", nitrogen_hybrids)]:
        table.to_csv(out / f"{name}.csv", index=False)
    predictions = pd.read_csv(base / "held_out_predictions.csv")
    if include_ridge:
        ridge = evaluate_ridge(features, out)
    else:
        ridge = pd.read_csv(out / "ridge_predictions.csv")
    predictions = pd.concat([predictions, ridge], ignore_index=True)
    if predictions.duplicated(["plot_id", "cutoff", "model"]).any():
        raise ValueError("Duplicate predictions in comparison inputs.")
    all_sites, all_hybrids, ranking_metrics, yield_metrics = [], [], [], []
    for (cutoff, model), group in predictions.groupby(["cutoff", "model"]):
        joined = plots.drop(columns="yieldPerAcre").merge(group[["plot_id", "predicted_yield"]], on="plot_id", validate="one_to_one")
        if len(joined) != len(plots):
            raise ValueError(f"Forecast cohort differs from observed cohort for {model}/{cutoff}.")
        _, sites, hybrids = hybrid_tables(joined, "predicted_yield")
        all_sites.append(sites.assign(cutoff=cutoff, model=model))
        all_hybrids.append(hybrids.assign(cutoff=cutoff, model=model))
        comparison = compare_rankings(observed_sites, sites)
        ranking_metrics.append(comparison.assign(cutoff=cutoff, model=model))
        yield_metrics.append({"cutoff": cutoff, "model": model, "location": "Overall", **regression_metrics(group)})
        for site, subset in group.groupby("location"):
            yield_metrics.append({"cutoff": cutoff, "model": model, "location": site, **regression_metrics(subset)})
    forecast_sites, forecast_hybrids = pd.concat(all_sites), pd.concat(all_hybrids)
    ranks, metrics = pd.concat(ranking_metrics), pd.DataFrame(yield_metrics)
    for name, table in [("forecast_site", forecast_sites), ("forecast_hybrids", forecast_hybrids), ("ranking_metrics", ranks), ("yield_metrics", metrics)]:
        table.to_csv(out / f"{name}.csv", index=False)
    site_yields = observed_cells.groupby(ENV).yield_mean.mean().groupby(["location", "year"]).mean().rename("balanced_yield").reset_index()
    site_yields.to_csv(out / "site_yields.csv", index=False)
    overall = metrics.loc[metrics.location.eq("Overall")]
    mae90 = overall.loc[overall.cutoff.eq(90)].set_index("model").mae
    claims = {"season": int(plots.year.iloc[0]), "locations": int(plots.location.nunique()), "hybrids": int(plots.genotype.nunique()),
              "labeled_plots": len(plots), "environments": len(observed_cells[ENV].drop_duplicates()),
              "shortlist": observed_hybrids.loc[observed_hybrids.shortlisted].to_dict("records"),
              "qualifying_hybrids": int(observed_hybrids.qualifies.sum()), "site_yields": site_yields.to_dict("records"),
              "nitrogen_sites": nitrogen_sites.to_dict("records"), "nitrogen_equal_site_difference": float(nitrogen_sites.mean_difference.mean()),
              "nitrogen_matched_pairs": len(paired), "day90_combined_mae": float(mae90["combined"]), "day90_mean_mae": float(mae90["mean"]),
              "day90_ridge_combined_mae": float(mae90["ridge_combined"]),
              "day90_ridge_improvement_vs_mean_pct": float(100 * (mae90["mean"] - mae90["ridge_combined"]) / mae90["mean"]),
              "day90_improvement_vs_mean_pct": float(100 * (mae90["mean"] - mae90["combined"]) / mae90["mean"]),
              "ranking_by_model_cutoff": ranks.groupby(["model", "cutoff"])[["spearman", "top10_overlap"]].mean().reset_index().replace({np.nan: None}).to_dict("records"),
              "sources": {"observed": "observed_environment.csv; observed_site.csv; observed_hybrids.csv",
                          "nitrogen": "nitrogen_pairs.csv; nitrogen_sites.csv",
                          "forecast": "yield_metrics.csv; ranking_metrics.csv; ridge_fold_audit.json"},
              "limitations": ["Five sites in 2022 only; no cross-season validation.", "Descriptive nitrogen contrasts, not causal irrigation or economic recommendations.",
                              "Rankings average treatment percentiles within site and weight sites equally.", "Shortlist is observed-harvest evidence; forecasts are evaluated separately.",
                              "Ridge comparisons are exploratory development using the already examined 2022 dataset."]}
    (out / "claims.json").write_text(json.dumps(claims, indent=2, allow_nan=False), encoding="utf-8")
    presentation_data = {"claims": claims, "observed_sites": observed_sites.to_dict("records"),
                         "overall_yield_metrics": overall.replace({np.nan: None}).to_dict("records"),
                         "ranking_metrics": ranks.replace({np.nan: None}).to_dict("records")}
    (out / "presentation_data.json").write_text(json.dumps(presentation_data, indent=2, allow_nan=False), encoding="utf-8")
    provenance = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [base / "features.parquet", base / "held_out_predictions.csv", Path(__file__)]}
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    make_figures(out, claims, observed_sites, forecast_sites, ranks, metrics, paired)
    print(json.dumps(claims, indent=2), flush=True)
    return claims


def make_figures(out, claims, observed_sites, forecast_sites, ranks, metrics, paired):
    os.environ.setdefault("MPLCONFIGDIR", str((out / ".matplotlib").resolve()))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    figures = out / "figures"
    figures.mkdir(exist_ok=True)
    shortlist = [r["genotype"] for r in claims["shortlist"]]
    sites = sorted(observed_sites.location.unique())
    matrix = observed_sites.pivot(index="genotype", columns="location", values="site_percentile").reindex(index=shortlist, columns=sites)
    fig, ax = plt.subplots(figsize=(11, 4.6), layout="constrained")
    heat = ax.imshow(matrix.to_numpy(), vmin=0, vmax=100, cmap="YlGn", aspect="auto")
    ax.set_xticks(range(len(sites)), sites); ax.set_yticks(range(len(shortlist)), shortlist)
    for y in range(len(shortlist)):
        for x in range(len(sites)):
            v = matrix.iloc[y, x]
            ax.text(x, y, f"{v:.0f}", ha="center", va="center", color="white" if v > 65 else "#163b2c")
    ax.set_title("Observed shortlist: performance across five sites", loc="left", pad=18)
    fig.colorbar(heat, ax=ax, label="Treatment-balanced within-site percentile")
    fig.savefig(figures / "01_hybrid_shortlist.png", dpi=200); fig.savefig(figures / "01_hybrid_shortlist.svg"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    ns = pd.DataFrame(claims["nitrogen_sites"]).sort_values("mean_difference")
    ax.barh(ns.location, ns.mean_difference, color=["#a87134" if x < 0 else "#287348" for x in ns.mean_difference])
    ax.axvline(0, color="#999999", linewidth=1)
    for index, row in enumerate(ns.itertuples()):
        ax.text(row.mean_difference + (1 if row.mean_difference >= 0 else -1), index, f"{row.mean_difference:+.1f}", ha="left" if row.mean_difference >= 0 else "right", va="center")
    ax.set_xlim(min(0, ns.mean_difference.min()) - 8, max(0, ns.mean_difference.max()) + 8)
    ax.set(xlabel="Observed yield difference: 150 minus 75 lb N/acre (bu/ac)", title="Nitrogen contrasts depend on the site")
    fig.savefig(figures / "02_nitrogen_contrasts.png", dpi=200); fig.savefig(figures / "02_nitrogen_contrasts.svg"); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), layout="constrained")
    overall = metrics.loc[metrics.location.eq("Overall") & metrics.cutoff.isin([75, 90])]
    colors = {"mean": "#888888", "agronomy": "#b07a43", "combined": "#237347", "ridge_agronomy": "#baa184", "ridge_combined": "#4b8293"}
    for model, frame in overall.groupby("model"):
        axes[0].plot(frame.cutoff, frame.mae, marker="o", label=LABELS[model], color=colors[model])
    axes[0].set(xlabel="Days after planting", ylabel="Held-out MAE (bu/ac)", title="Yield forecast error", xticks=[75, 90])
    axes[0].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    for model in ["combined", "ridge_combined"]:
        data = ranks.loc[ranks.model.eq(model) & ranks.cutoff.isin([75, 90])].groupby("cutoff").top10_overlap.mean()
        axes[1].plot(data.index, data.values, marker="o", color=colors[model], label=LABELS[model])
    axes[1].axhline(100 / 84, color="#888888", linestyle="--", label="Random expectation")
    axes[1].set(xlabel="Days after planting", ylabel="Mean overlap with observed top 10 (of 10)", title="Hybrid selection agreement", xticks=[75, 90], ylim=(0, 10)); axes[1].legend(fontsize=8)
    fig.savefig(figures / "03_forecast_evidence.png", dpi=200); fig.savefig(figures / "03_forecast_evidence.svg"); plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--reuse-ridge", action="store_true")
    args = parser.parse_args()
    build_analysis(args.output, include_ridge=not args.reuse_ridge)
