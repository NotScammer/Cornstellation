"""RGB appearance measurements; no reflectance or stress diagnosis is inferred."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

SETTINGS = {"version": 1, "normalization": "rgb / (r + g + b)",
            "mask": "alpha > 0 and RGB sum > 0", "green": "g > r and g > b"}
MEASUREMENTS = ["red", "green", "blue", "excess_green", "excess_green_iqr", "green_fraction"]
UAV_FEATURES = ([f"uav_latest_{x}" for x in MEASUREMENTS]
                + [f"uav_delta_{x}" for x in MEASUREMENTS]
                + ["uav_observation_count", "uav_image_age_days", "uav_observation_gap_days",
                   "uav_valid_fraction", "uav_missing_imagery"])


def summarize_rgb(array):
    a = np.asarray(array)
    if a.ndim != 3 or a.shape[2] not in (3, 4):
        raise ValueError("Expected RGB or RGBA PNG")
    rgb = a[..., :3].astype(float)
    total = rgb.sum(axis=2)
    valid = np.isfinite(rgb).all(axis=2) & (rgb >= 0).all(axis=2) & (total > 0)
    if a.shape[2] == 4:
        valid &= a[..., 3] > 0
    result = dict(valid_pixels=int(valid.sum()), valid_fraction=float(valid.mean()))
    if not valid.any():
        raise ValueError("Empty valid-pixel mask")
    r, g, b = (rgb[valid] / total[valid, None]).T
    exg = 2*g-r-b
    result.update(red=float(np.median(r)), green=float(np.median(g)), blue=float(np.median(b)),
                  excess_green=float(np.median(exg)),
                  excess_green_iqr=float(np.percentile(exg, 75)-np.percentile(exg, 25)),
                  green_fraction=float(((g > r) & (g > b)).mean()))
    return result


def extract_uav(root, output, plots, workers=8):
    from .data import KEYS, load_dates, normalize_keys, parse_image_name
    root, output = Path(root).resolve(), Path(output)
    dates = load_dates(root, source="UAV")
    inventory = []
    for path in sorted((root / "UAV").rglob("*")):
        if not path.is_file():
            continue
        row = dict(path=path.relative_to(root).as_posix(), error="", mode="", **{k: None for k in KEYS})
        try:
            row.update(parse_image_name(path))
            if path.suffix.lower() != ".png":
                raise ValueError("Unsupported UAV format; expected PNG")
            with Image.open(path) as im:
                row.update(mode=im.mode, width=im.width, height=im.height)
                if im.mode not in ("RGB", "RGBA"):
                    raise ValueError(f"Unsupported UAV mode: {im.mode}")
        except Exception as exc:
            row["error"] = str(exc)
        inventory.append(row)
    columns = ["path", "error", "mode", *KEYS, "timepoint"]
    inventory = pd.DataFrame(inventory) if inventory else pd.DataFrame(columns=columns)
    for column in columns:
        if column not in inventory:
            inventory[column] = None
    inventory.to_csv(output / "uav_file_inventory.csv", index=False)
    parsed = inventory.loc[inventory[KEYS].notna().all(axis=1)].copy()
    parsed = normalize_keys(parsed).merge(dates, on=["location", "timepoint"], how="left", validate="many_to_one")
    parsed["matched_plot"] = parsed.plot_id.isin(plots.plot_id)
    parsed.to_csv(output / "uav_inventory.csv", index=False)
    unmatched = parsed.loc[~parsed.matched_plot | parsed.image_date.isna()]
    unmatched.to_csv(output / "uav_unmatched_images.csv", index=False)
    eligible = parsed.loc[parsed.matched_plot & parsed.image_date.notna() & parsed.error.eq("")].copy()
    if eligible.duplicated(["plot_id", "image_date"]).any():
        raise ValueError("Duplicate UAV observations for a plot/date; see uav_inventory.csv")
    cache_path = output / "uav_image_cache.parquet"
    cache = pd.read_parquet(cache_path) if cache_path.exists() else pd.DataFrame()
    previous = {r["path"]: r for r in cache.to_dict("records")}

    def extract(row):
        path = root / row["path"]
        stat = path.stat()
        fingerprint = json.dumps([str(root), row["path"], stat.st_size, stat.st_mtime_ns, SETTINGS], sort_keys=True)
        old = previous.get(row["path"])
        if old and old.get("fingerprint") == fingerprint and not old.get("error"):
            row.update({k: old[k] for k in [*MEASUREMENTS, "valid_pixels", "valid_fraction"]})
        else:
            try:
                with Image.open(path) as im:
                    row.update(summarize_rgb(np.asarray(im)))
            except Exception as exc:
                row["error"] = str(exc)
        row["fingerprint"] = fingerprint
        return row

    records = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, row in enumerate(pool.map(extract, eligible.to_dict("records")), 1):
            records.append(row)
            if i % 1000 == 0:
                print(f"Summarized {i}/{len(eligible)} UAV images", flush=True)
    extracted = pd.DataFrame(records) if records else eligible.copy()
    for col in [*MEASUREMENTS, "valid_pixels", "valid_fraction"]:
        if col not in extracted:
            extracted[col] = np.nan
    extracted.to_parquet(cache_path, index=False)
    errors = pd.concat([inventory.loc[inventory.error.ne("")], extracted.loc[extracted.error.ne("")]], ignore_index=True)
    errors.to_csv(output / "uav_image_errors.csv", index=False)
    good = extracted.loc[extracted.error.eq("") & extracted.valid_pixels.gt(0)].copy()
    good[["plot_id", "path", "image_date", "timepoint"]].to_csv(output / "uav_image_index.csv", index=False)
    quality = dict(files=len(inventory), usable_images=len(good), errors=len(errors),
                   unmatched_or_undated=len(unmatched), modes=inventory["mode"].value_counts().to_dict(),
                   data_root=str(root), settings=SETTINGS)
    (output / "uav_data_quality.json").write_text(json.dumps(quality, indent=2))
    return good


def add_uav_features(features, observations):
    result = features.copy()
    for col in UAV_FEATURES:
        result[col] = np.nan
    result["uav_observation_count"] = 0
    result["uav_missing_imagery"] = 1
    if observations.duplicated(["plot_id", "image_date"]).any():
        raise ValueError("Duplicate UAV observations for a plot/date")
    groups = {pid: g.sort_values("image_date") for pid, g in observations.groupby("plot_id")}
    for index, row in result.iterrows():
        group = groups.get(row.plot_id)
        if group is None:
            continue
        eligible = group.loc[group.image_date.between(row.plantingDate, row.prediction_date)]
        if eligible.empty:
            continue
        last = eligible.iloc[-1]
        result.loc[index, "uav_observation_count"] = len(eligible)
        result.loc[index, "uav_missing_imagery"] = 0
        result.loc[index, "uav_image_age_days"] = (row.prediction_date-last.image_date).days
        result.loc[index, "uav_valid_fraction"] = last.valid_fraction
        for name in MEASUREMENTS:
            result.loc[index, f"uav_latest_{name}"] = last[name]
        if len(eligible) > 1:
            previous = eligible.iloc[-2]
            result.loc[index, "uav_observation_gap_days"] = (last.image_date-previous.image_date).days
            for name in MEASUREMENTS:
                result.loc[index, f"uav_delta_{name}"] = last[name]-previous[name]
    return result


def latest_image(index, plot_id, planting_date, prediction_date):
    eligible = index.loc[index.plot_id.eq(plot_id) & index.image_date.between(pd.Timestamp(planting_date), pd.Timestamp(prediction_date))]
    return None if eligible.empty else eligible.sort_values("image_date").iloc[-1]
