import argparse
import json
from pathlib import Path

import pandas as pd

from .data import prepare


def main():
    parser = argparse.ArgumentParser(description="Mid-season maize yield pipeline")
    parser.add_argument("command", choices=["prepare", "train", "run", "predict"])
    parser.add_argument("--data-root", type=Path, default=Path("2022/DataPublication_final"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config.json")
    parser.add_argument("--cutoffs", nargs="+", type=int)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--models-dir", type=Path, default=Path("outputs/models"))
    parser.add_argument("--smoke", action="store_true", help="15 plots/site and 10 model iterations; separate output required")
    parser.add_argument("--include-uav", action="store_true", help="Include RGB UAV features and model comparisons")
    parser.add_argument("--model", default="combined", choices=["agronomy", "combined", "agronomy_uav", "combined_uav"], help="Inference model")
    args = parser.parse_args()
    include_uav = args.include_uav or (args.command == "predict" and args.model.endswith("_uav"))
    args.output = args.output or Path("outputs/uav" if include_uav else "outputs")
    if include_uav and args.output.resolve() == Path("outputs").resolve():
        parser.error("Use a separate UAV output folder to preserve the existing results")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    cutoffs = sorted(set(args.cutoffs or config["cutoffs"]))
    if not cutoffs or min(cutoffs) <= 0 or args.workers < 1:
        parser.error("Cutoffs and worker count must be positive.")
    if args.smoke and args.output.resolve() in {Path("outputs").resolve(), Path("outputs/uav").resolve()}:
        parser.error("Use --output outputs/smoke for smoke tests to preserve final results.")
    config["cutoffs"] = cutoffs
    config["include_uav"] = include_uav
    if args.command in {"prepare", "run", "predict"}:
        features = prepare(args.data_root, args.output, config, cutoffs, args.workers)
    else:
        features = pd.read_parquet(args.output / "features.parquet")
        if not set(cutoffs).issubset(set(features.cutoff.unique())):
            parser.error("Requested cutoffs are absent; rerun prepare for those cutoffs.")
        features = features.loc[features.cutoff.isin(cutoffs)]
        quality = json.loads((args.output / "data_quality.json").read_text(encoding="utf-8"))
        if quality["band_mapping"] != config["band_mapping"] or quality["metadata_conflicts"]:
            parser.error("Feature band mapping is inconsistent; resolve metadata and rerun prepare.")
        if include_uav:
            from .uav import UAV_FEATURES, SETTINGS
            uav_quality = args.output / "uav_data_quality.json"
            if not set(UAV_FEATURES).issubset(features) or not uav_quality.exists():
                parser.error("UAV features or extraction metadata are absent; rerun prepare --include-uav.")
            if json.loads(uav_quality.read_text())["settings"] != SETTINGS:
                parser.error("UAV extraction settings changed; rerun prepare --include-uav.")
    if args.command in {"train", "run"}:
        from .modeling import evaluate
        evaluate(features, args.output, config, args.smoke)
    elif args.command == "predict":
        from .modeling import predict
        predict(features, args.models_dir, args.output, config, model_name=args.model)


if __name__ == "__main__":
    main()
