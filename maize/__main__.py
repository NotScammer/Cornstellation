import argparse
import json
from pathlib import Path

import pandas as pd

from .data import prepare


def main():
    parser = argparse.ArgumentParser(description="Mid-season maize yield pipeline")
    parser.add_argument("command", choices=["prepare", "train", "run", "predict"])
    parser.add_argument("--data-root", type=Path, default=Path("2022/DataPublication_final"))
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config.json")
    parser.add_argument("--cutoffs", nargs="+", type=int)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--models-dir", type=Path, default=Path("outputs/models"))
    parser.add_argument("--smoke", action="store_true", help="15 plots/site and 10 model iterations; separate output required")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    cutoffs = sorted(set(args.cutoffs or config["cutoffs"]))
    if not cutoffs or min(cutoffs) <= 0 or args.workers < 1:
        parser.error("Cutoffs and worker count must be positive.")
    if args.smoke and args.output.resolve() == Path("outputs").resolve():
        parser.error("Use --output outputs/smoke for smoke tests to preserve final results.")
    config["cutoffs"] = cutoffs
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
    if args.command in {"train", "run"}:
        from .modeling import evaluate
        evaluate(features, args.output, config, args.smoke)
    elif args.command == "predict":
        from .modeling import predict
        predict(features, args.models_dir, args.output, config)


if __name__ == "__main__":
    main()
