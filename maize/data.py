from __future__ import annotations

import hashlib
import json
import re
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.errors import NotGeoreferencedWarning

KEYS = ["location", "experiment", "range", "row"]
BANDS = ["red", "green", "blue", "nir", "red_edge", "deep_blue"]
SPECTRAL = BANDS + ["ndvi", "ndre"]
AGRONOMY = ["planting_doy", "poundsOfNitrogenPerAcre", "irrigationProvided", "genotype"]
CATEGORICAL = ["irrigationProvided", "genotype"]
IMAGE_FEATURES = ([f"latest_{x}" for x in SPECTRAL]
                  + [f"delta_{x}" for x in SPECTRAL]
                  + ["observation_count", "image_age_days", "observation_gap_days",
                     "latest_valid_pixels", "latest_valid_fraction", "missing_imagery"])


def canonical_site(value):
    return {"Missouri Valley": "MOValley"}.get(str(value).strip(), str(value).strip())


def normalize_keys(frame):
    frame = frame.copy()
    if frame[KEYS].isna().any().any():
        raise ValueError("Plot identifiers cannot be missing.")
    frame["location"] = frame.location.map(canonical_site)
    for col in ["experiment", "range", "row"]:
        frame[col] = frame[col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    # Verified source typo: MOValley ground truth says Hyrbrids; TIFFs say Hybrids.
    typo = frame.location.eq("MOValley") & frame.experiment.eq("Hyrbrids")
    frame.loc[typo, "experiment"] = "Hybrids"
    frame["plot_id"] = frame[KEYS].agg("|".join, axis=1)
    return frame


def load_records(root):
    root = Path(root)
    candidates = sorted((root / "GroundTruth").glob("*.csv"))
    if len(candidates) != 1:
        raise ValueError(f"Expected exactly one plot CSV in {root / 'GroundTruth'}.")
    frame = pd.read_csv(candidates[0], dtype={k: str for k in KEYS})
    frame["invalid_plot_key"] = frame[KEYS].isna().any(axis=1)
    frame[KEYS] = frame[KEYS].fillna("__MISSING__")
    frame = normalize_keys(frame)
    for index in frame.index[frame.invalid_plot_key]:
        frame.loc[index, "plot_id"] = f"__INVALID_ROW_{index}"
    if frame.plot_id.duplicated().any():
        raise ValueError("Duplicate plot identifiers in ground truth.")
    required = ["plantingDate", "poundsOfNitrogenPerAcre", "irrigationProvided", "genotype"]
    missing = set(required) - set(frame)
    if missing:
        raise ValueError(f"Missing agronomy columns: {sorted(missing)}")
    frame["plantingDate"] = pd.to_datetime(frame.plantingDate, errors="coerce")
    frame["planting_doy"] = frame.plantingDate.dt.dayofyear
    frame["poundsOfNitrogenPerAcre"] = pd.to_numeric(frame.poundsOfNitrogenPerAcre, errors="coerce")
    if "yieldPerAcre" not in frame:
        frame["yieldPerAcre"] = np.nan
    frame["yieldPerAcre"] = pd.to_numeric(frame.yieldPerAcre, errors="coerce")
    frame.loc[~np.isfinite(frame.yieldPerAcre), "yieldPerAcre"] = np.nan
    return frame


def load_dates(root):
    dates = pd.read_excel(Path(root) / "GroundTruth" / "DateofCollection.xlsx")
    dates = dates.loc[dates.Image.astype(str).str.strip().eq("Satellite")].copy()
    dates = dates.rename(columns={"Location": "location", "Date": "image_date", "time": "timepoint"})
    dates["location"] = dates.location.map(canonical_site)
    dates["image_date"] = pd.to_datetime(dates.image_date, errors="raise")
    if dates.duplicated(["location", "timepoint"]).any() or dates.image_date.isna().any():
        raise ValueError("Satellite collection dates must be present and unique per site/timepoint.")
    return dates[["location", "timepoint", "image_date"]]


def parse_image_name(path):
    match = re.fullmatch(r"(.+)-(TP\d+)-(.+)_(\d+)_(\d+)", Path(path).stem)
    if not match:
        raise ValueError(f"Unrecognized plot image name: {Path(path).name}")
    site, timepoint, experiment, range_, row = match.groups()
    return {"location": canonical_site(site), "timepoint": timepoint,
            "experiment": experiment, "range": range_, "row": row}


def safe_index(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denom = a + b
    return np.divide(a - b, denom, out=np.full_like(denom, np.nan), where=np.abs(denom) > 1e-12)


def summarize_pixels(array, mapping, mask=None):
    array = np.asarray(array, dtype=float)
    if array.ndim != 3 or array.shape[0] != 6:
        raise ValueError(f"Expected six bands, received shape {array.shape}.")
    valid = np.isfinite(array).all(axis=0) & (array >= 0).all(axis=0) & (array != 0).any(axis=0)
    if mask is not None:
        valid &= mask
    count = int(valid.sum())
    values = {name: array[index - 1][valid] for name, index in mapping.items()}
    values["ndvi"] = safe_index(values["nir"], values["red"])
    values["ndre"] = safe_index(values["nir"], values["red_edge"])
    result = {name: float(np.nanmedian(v)) if np.isfinite(v).any() else np.nan
              for name, v in values.items()}
    return {**result, "valid_pixels": count, "valid_fraction": count / valid.size}


def metadata_conflicts(descriptions, mapping):
    aliases = {"red": "red", "green": "green", "blue": "blue", "nir": "nir",
               "nearinfrared": "nir", "rededge": "red_edge", "deepblue": "deep_blue"}
    issues = []
    for expected, index in mapping.items():
        description = descriptions[index - 1] if len(descriptions) >= index else None
        normalized = re.sub(r"[^a-z]", "", str(description).lower())
        actual = aliases.get(normalized)
        if actual is None and description:
            label = re.sub(r"\([^)]*\)", "", str(description).lower()).strip()
            label = re.sub(r"^pleiades\s+neo\s+", "", label)
            label = re.sub(r"\s+um$", "", label)
            actual = aliases.get(re.sub(r"[^a-z]", "", label))
        if actual is not None and actual != expected:
            issues.append(f"Band {index}: configured {expected}, metadata {description}")
    return issues


def extract_images(root, output, mapping, workers=8):
    root, output = Path(root).resolve(), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if set(mapping) != set(BANDS) or sorted(mapping.values()) != list(range(1, 7)):
        raise ValueError("Band mapping must assign each of the six bands exactly once.")
    paths = sorted(p for p in (root / "Satellite").rglob("*") if p.suffix.lower() in {".tif", ".tiff"})
    if not paths:
        raise ValueError(f"No satellite TIFF files found beneath {root / 'Satellite'}.")
    signature = hashlib.sha256(json.dumps({"version": 1, "root": str(root), "mapping": mapping}, sort_keys=True).encode()).hexdigest()
    cache_path = output / "image_cache.parquet"
    cache = pd.read_parquet(cache_path) if cache_path.exists() else pd.DataFrame()
    previous = {r["path"]: r for r in cache.to_dict("records")} if not cache.empty else {}

    def extract(path):
        stat = path.stat()
        relative = path.relative_to(root).as_posix()
        fingerprint = f"{signature}:{stat.st_size}:{stat.st_mtime_ns}"
        old = previous.get(relative)
        if old and old.get("fingerprint") == fingerprint and not old.get("error"):
            return old
        record = {"path": relative, "fingerprint": fingerprint, "error": "", "metadata_conflict": "", "band_descriptions": ""}
        try:
            record.update(parse_image_name(path))
            with rasterio.open(path) as src:
                record["band_descriptions"] = json.dumps(src.descriptions)
                conflicts = metadata_conflicts(src.descriptions, mapping)
                record["metadata_conflict"] = "; ".join(conflicts)
                if conflicts:
                    raise ValueError(record["metadata_conflict"])
                record.update(summarize_pixels(src.read(), mapping, src.read_masks().all(axis=0)))
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            records = []
            for index, record in enumerate(pool.map(extract, paths), 1):
                records.append(record)
                if index % 2000 == 0:
                    print(f"Summarized {index}/{len(paths)} images", flush=True)
    images = pd.DataFrame(records)
    images.to_parquet(cache_path, index=False)
    return images


def build_cutoff_features(plots, observations, cutoffs):
    """No aggregation may see observations after a plot's prediction cutoff."""
    merged = observations.merge(plots[["plot_id", "plantingDate"]], on="plot_id", validate="many_to_one")
    merged["dap"] = (merged.image_date - merged.plantingDate).dt.days
    results = []
    for cutoff in cutoffs:
        observed = merged.loc[merged.dap.between(0, cutoff)].sort_values(["plot_id", "image_date", "timepoint"])
        if observed.duplicated(["plot_id", "image_date"]).any():
            raise ValueError("Multiple observations for a plot on the same date; resolve duplicates before training.")
        usable = plots.plantingDate.notna()
        if "invalid_plot_key" in plots:
            usable &= ~plots.invalid_plot_key
        base = plots.loc[usable].copy().set_index("plot_id", drop=False)
        for name in IMAGE_FEATURES:
            base[name] = np.nan
        base["observation_count"] = 0
        base["missing_imagery"] = 1
        for plot_id, group in observed.groupby("plot_id", sort=False):
            if plot_id not in base.index:
                continue
            last = group.iloc[-1]
            base.loc[plot_id, "observation_count"] = len(group)
            base.loc[plot_id, "missing_imagery"] = 0
            base.loc[plot_id, "image_age_days"] = cutoff - last.dap
            base.loc[plot_id, "latest_valid_pixels"] = last.valid_pixels
            base.loc[plot_id, "latest_valid_fraction"] = last.valid_fraction
            for name in SPECTRAL:
                base.loc[plot_id, f"latest_{name}"] = last[name]
            if len(group) > 1:
                prev = group.iloc[-2]
                base.loc[plot_id, "observation_gap_days"] = (last.image_date - prev.image_date).days
                for name in SPECTRAL:
                    base.loc[plot_id, f"delta_{name}"] = last[name] - prev[name]
        base["cutoff"] = cutoff
        base["prediction_date"] = base.plantingDate + pd.to_timedelta(cutoff, unit="D")
        results.append(base.reset_index(drop=True))
    return pd.concat(results, ignore_index=True)


def prepare(root, output, config, cutoffs, workers=8):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    plots, dates = load_records(root), load_dates(root)
    images = extract_images(root, output, config["band_mapping"], workers)
    failures = images.loc[images.error.fillna("").ne("")].copy()
    failures.to_csv(output / "image_errors.csv", index=False)
    parsed = images.loc[images[KEYS].notna().all(axis=1)].copy()
    parsed = normalize_keys(parsed).merge(dates, on=["location", "timepoint"], how="left", validate="many_to_one")
    unmatched = parsed.loc[~parsed.plot_id.isin(plots.plot_id) | parsed.image_date.isna()]
    unmatched.to_csv(output / "unmatched_images.csv", index=False)
    eligible_images = parsed.loc[parsed.plot_id.isin(plots.plot_id) & parsed.image_date.notna()
                                 & parsed.error.fillna("").eq("") & parsed.valid_pixels.gt(0)].copy()
    if eligible_images.duplicated(["plot_id", "timepoint"]).any():
        raise ValueError("Duplicate images for a plot/timepoint.")
    features = build_cutoff_features(plots, eligible_images, cutoffs)
    features.to_parquet(output / "features.parquet", index=False)
    missing = plots.loc[~plots.plot_id.isin(eligible_images.plot_id)]
    missing.to_csv(output / "plots_without_images.csv", index=False)
    excluded = plots.loc[plots.plantingDate.isna() | plots.yieldPerAcre.isna() | plots.invalid_plot_key].copy()
    excluded["missing_planting_date"] = excluded.plantingDate.isna()
    excluded["missing_yield"] = excluded.yieldPerAcre.isna()
    excluded.to_csv(output / "training_exclusions.csv", index=False)
    coverage = features.loc[features.yieldPerAcre.notna()].groupby(["cutoff", "location"]).agg(
        plots=("plot_id", "size"), missing_imagery=("missing_imagery", "sum"),
        mean_observations=("observation_count", "mean")).reset_index()
    coverage.to_csv(output / "coverage.csv", index=False)
    quality = {"data_root": str(Path(root).resolve()), "plot_records": len(plots),
               "eligible_training_plots": int((plots.yieldPerAcre.notna() & plots.plantingDate.notna() & ~plots.invalid_plot_key).sum()),
               "invalid_plot_identifiers": int(plots.invalid_plot_key.sum()),
               "satellite_images": len(images), "image_errors": len(failures),
               "unmatched_or_undated_images": len(unmatched), "plots_without_usable_images": len(missing),
               "missing_planting_dates": int(plots.plantingDate.isna().sum()),
               "missing_yields": int(plots.yieldPerAcre.isna().sum()),
               "metadata_conflicts": int(images.metadata_conflict.fillna("").ne("").sum()),
               "band_mapping": config["band_mapping"], "band_mapping_source": config["band_mapping_source"],
               "key_normalizations": ["Missouri Valley -> MOValley", "MOValley experiment Hyrbrids -> Hybrids"],
               "cutoffs": cutoffs}
    (output / "data_quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    print(json.dumps(quality, indent=2), flush=True)
    if quality["metadata_conflicts"]:
        raise ValueError("Conflicting band metadata found; see image_errors.csv and verify config before continuing.")
    return features
