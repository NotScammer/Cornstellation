"""Build the standalone UAV dashboard evidence and a paired comparison report."""
import argparse
import json
from pathlib import Path

import pandas as pd


def write_comparison(output):
    output = Path(output)
    metrics = pd.read_csv(output / "model_comparison.csv")
    baseline = metrics.loc[metrics.model.eq("combined")].set_index(["cutoff", "location"])
    augmented = metrics.loc[metrics.model.eq("combined_uav")].set_index(["cutoff", "location"])
    comparison = augmented[["mae", "precision_at_k", "hits"]].join(
        baseline[["mae", "precision_at_k", "hits"]], lsuffix="_uav", rsuffix="_satellite")
    comparison["mae_change"] = comparison.mae_uav-comparison.mae_satellite
    comparison["additional_hits"] = comparison.hits_uav-comparison.hits_satellite
    comparison.reset_index().to_csv(output / "uav_incremental_value.csv", index=False)
    quality = json.loads((output / "uav_data_quality.json").read_text())
    config = json.loads((output / "run_config.json").read_text())
    lines = ["# UAV evidence: 2022 held-out-site comparison", "",
             "The existing satellite forecast remains the default. UAV models are optional experimental comparisons.", "",
             f"Inventory: {quality['files']:,} files; {quality['usable_images']:,} usable matched images; "
             f"{quality['unmatched_or_undated']:,} unmatched or undated; {quality['errors']} image errors.", "",
             "RGB features describe appearance, not calibrated reflectance, NDVI, or a diagnosis. "
             "All models use the same eligible plots, including plots without UAV coverage at the cutoff.", "",
             "| Day | Satellite MAE | Satellite + UAV MAE | MAE change | Satellite hits | Satellite + UAV hits |",
             "|---|---|---|---|---|---|"]
    for (cutoff, site), row in comparison.iterrows():
        if site == "Overall":
            lines.append(f"| {cutoff} | {row.mae_satellite:.2f} | {row.mae_uav:.2f} | {row.mae_change:+.2f} | {row.hits_satellite:.0f} | {row.hits_uav:.0f} |")
    lines += ["", "MAE is bu/ac; negative MAE change means improvement. Hits count actual bottom-20% plots "
              "among up to 10 visits per site. The separate scouting_metrics.csv retains the 10% visit budget.", "",
              "## Where UAV helps or hurts", ""]
    for cutoff in sorted(metrics.cutoff.unique()):
        local = comparison.loc[cutoff].drop(index="Overall")
        better = local.index[local.mae_change < 0].tolist()
        worse = local.index[local.mae_change > 0].tolist()
        lines.append(f"- Day {cutoff}: lower MAE at {', '.join(better) or 'no sites'}; higher MAE at {', '.join(worse) or 'no sites'}.")
    lines += ["", "See uav_incremental_value.csv for per-site errors and scouting changes, model_comparison.csv "
              "for all input combinations, and uav_coverage.csv for date-specific coverage. "
              "These exploratory results measure transfer between five sites in one season; future-season validation is pending."]
    if config.get("smoke_test"):
        lines.insert(2, "**SMOKE TEST ONLY: reduced cohort and training iterations; not research evidence.**")
    (output / "uav_evidence.md").write_text("\n".join(lines), encoding="utf-8")


def build(output, data_root, reuse_ridge=False, reuse_nitrogen=False):
    from .decision_brief import build as build_decision
    from .insights import build_analysis
    from .scouting_trip import build_coordinates
    from .yield_audit import audit
    output = Path(output)
    config = json.loads((output / "run_config.json").read_text())
    if config.get("smoke_test"):
        raise ValueError("Standalone dashboard reports require the full evaluation, not a smoke run")
    build_analysis(output, include_ridge=not reuse_ridge)
    build_decision(output, reuse=reuse_nitrogen)
    build_coordinates(data_root, output / "plot_coordinates.csv")
    audit(data_root, output)
    write_comparison(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/uav"))
    parser.add_argument("--data-root", type=Path, default=Path("2022/DataPublication_final"))
    parser.add_argument("--reuse-ridge", action="store_true")
    parser.add_argument("--reuse-nitrogen", action="store_true")
    args = parser.parse_args()
    build(args.output, args.data_root, args.reuse_ridge, args.reuse_nitrogen)
