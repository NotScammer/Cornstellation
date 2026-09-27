"""Approximate scouting loops using plot-image centers, independent of forecasts."""
from pathlib import Path
import math

import numpy as np
import pandas as pd


def build_coordinates(data_root, output):
    """Read georeferencing only; save one WGS84 center per plot with provenance."""
    import rasterio
    from rasterio.warp import transform
    from maize.data import normalize_keys, parse_image_name

    root = Path(data_root)
    records, seen, candidates = [], set(), []
    for path in sorted((root / "Satellite").rglob("*")):
        if path.suffix.lower() != ".tif":
            continue
        candidates.append(dict(**parse_image_name(path), path=path))
    normalized = normalize_keys(pd.DataFrame(candidates)) if candidates else pd.DataFrame()
    for keys in normalized.itertuples(index=False):
        path = keys.path
        if keys.plot_id in seen:
            continue
        with rasterio.open(path) as source:
            if source.crs is None:
                continue
            x, y = source.transform * (source.width / 2, source.height / 2)
            lon, lat = transform(source.crs, "EPSG:4326", [x], [y])
        if not (math.isfinite(lat[0]) and math.isfinite(lon[0])):
            continue
        records.append(dict(plot_id=keys.plot_id, location=keys.location,
                            latitude=lat[0], longitude=lon[0],
                            source_image=path.relative_to(root).as_posix()))
        seen.add(keys.plot_id)
    frame = pd.DataFrame(records, columns=["plot_id", "location", "latitude", "longitude", "source_image"])
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return frame


def scouting_route(selected, coordinates):
    """Visit exactly the selected set, starting/ending at its first priority plot.

    Nearest-next-plot is a heuristic, not an optimal route or a navigable path.
    Missing locations fail closed instead of understating the complete trip.
    """
    if selected.empty or selected.plot_id.duplicated().any():
        raise ValueError("Select at least one plot, with no duplicate plot IDs.")
    if selected.location.nunique() != 1:
        raise ValueError("Estimate each site's field trip separately.")
    points = selected[["plot_id", "location"]].merge(
        coordinates[["plot_id", "latitude", "longitude"]], on="plot_id", how="left", validate="one_to_one")
    lat = pd.to_numeric(points.latitude, errors="coerce")
    lon = pd.to_numeric(points.longitude, errors="coerce")
    valid = lat.between(-90, 90) & lon.between(-180, 180)
    if not valid.all():
        raise ValueError(f"Coordinates unavailable for {int((~valid).sum())} of {len(points)} selected plots.")
    radians = np.radians(np.column_stack([lat, lon]))
    dlat = radians[:, None, 0] - radians[None, :, 0]
    dlon = radians[:, None, 1] - radians[None, :, 1]
    a = np.sin(dlat / 2)**2 + np.cos(radians[:, None, 0]) * np.cos(radians[None, :, 0]) * np.sin(dlon / 2)**2
    distances = 3958.7613 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    plot_ids = points.plot_id.to_numpy()
    order, remaining = [0], set(range(1, len(points)))
    while remaining:
        following = min(remaining, key=lambda i: (distances[order[-1], i], plot_ids[i]))
        order.append(following)
        remaining.remove(following)
    route = points.iloc[order].copy().reset_index(drop=True)
    route.insert(0, "visit_order", np.arange(1, len(route) + 1))
    route["leg_miles"] = [0.] + [float(distances[p, q]) for p, q in zip(order, order[1:])]
    route["cumulative_miles"] = route.leg_miles.cumsum()
    return_miles = float(distances[order[-1], order[0]])
    return route, float(route.leg_miles.sum() + return_miles), return_miles


def trip_totals(plot_count, field_miles, walking_mph=2., minutes_per_plot=5.,
                one_way_drive_miles=0., driving_mph=40.):
    values = [field_miles, walking_mph, minutes_per_plot, one_way_drive_miles, driving_mph]
    if not all(math.isfinite(v) for v in values) or min(field_miles, minutes_per_plot, one_way_drive_miles) < 0:
        raise ValueError("Trip assumptions must be finite and nonnegative.")
    if walking_mph <= 0 or driving_mph <= 0 or plot_count < 1:
        raise ValueError("Speeds and plot count must be positive.")
    walking_hours = field_miles / walking_mph
    inspection_hours = plot_count * minutes_per_plot / 60
    driving_hours = 2 * one_way_drive_miles / driving_mph
    return dict(field_miles=field_miles, driving_miles=2 * one_way_drive_miles,
                walking_hours=walking_hours, inspection_hours=inspection_hours,
                driving_hours=driving_hours,
                total_hours=walking_hours + inspection_hours + driving_hours)


def render_scouting_trip(selected, output, key_prefix):
    import streamlit as st

    st.markdown(f"**Trip estimate · {len(selected)} selected plots**")
    coordinate_file = Path(output) / "plot_coordinates.csv"
    if not coordinate_file.exists():
        st.info("Trip distance is unavailable: this result folder has no plot coordinates.")
        return
    try:
        coordinates = pd.read_csv(coordinate_file)
        route, miles, return_miles = scouting_route(selected, coordinates)
    except (ValueError, KeyError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        st.info(f"Trip distance is unavailable. {error}")
        return
    with st.expander("Adjust trip assumptions", expanded=False):
        left, right = st.columns(2)
        minutes = left.number_input("Inspection minutes per plot", min_value=0., max_value=120., value=5., step=1., key=f"{key_prefix}_minutes")
        speed = right.number_input("Walking speed (mph)", min_value=0.1, max_value=10., value=2., step=0.1, key=f"{key_prefix}_walk")
        include_drive = st.checkbox("Include round-trip driving to this site", key=f"{key_prefix}_include_drive")
        drive_miles, drive_speed = 0., 40.
        if include_drive:
            drive_miles = left.number_input("One-way road distance to site (miles)", min_value=0., value=0., step=1., key=f"{key_prefix}_drive_miles")
            drive_speed = right.number_input("Average driving speed (mph)", min_value=1., max_value=100., value=40., step=5., key=f"{key_prefix}_drive_speed")
            st.caption("Enter road miles from your starting point. Driving time uses your average speed; live routing and traffic are unavailable.")
    totals = trip_totals(len(selected), miles, speed, minutes, drive_miles, drive_speed)
    left, middle, right = st.columns(3)
    left.metric("Estimated field loop", f"{miles:.2f} miles")
    middle.metric("Walking + inspection", f"{totals['walking_hours'] + totals['inspection_hours']:.2f} hr")
    right.metric("Total trip time" if include_drive else "Inspection time", f"{totals['total_hours'] if include_drive else totals['inspection_hours']:.2f} hr")
    st.caption(f"{len(selected)} plots × {minutes:g} min inspection; walking at {speed:g} mph. "
               + (f"Driving: {2 * drive_miles:g} round-trip miles at {drive_speed:g} mph. " if include_drive else "Driving to the site is excluded. ")
               + "Each estimate covers this site only.")
    if include_drive and drive_miles == 0:
        st.info("Enter your one-way road distance to add driving time.")
    st.caption("Approximate straight-line loop between plot-image centers, beginning and ending at the highest-priority selected plot. "
               "Visits the nearest remaining selected plot next. Field paths, obstacles, entrance travel and walking within plots are not mapped; actual distance may be longer. Inspection time should cover work within each plot.")
    # Export route order separately from the unchanged scouting priority list.
    export = route.copy()
    export["model"] = selected.iloc[0].get("model", "combined")
    export["return_to_start_miles"] = return_miles
    for name, value in totals.items():
        export[name] = value
    export["walking_mph"] = speed
    export["inspection_minutes_per_plot"] = minutes
    export["driving_included"] = include_drive
    export["driving_mph"] = drive_speed if include_drive else np.nan
    export["distance_basis"] = "straight-line plot-center loop; no field paths or entrance"
    st.download_button("Download trip estimate and visit order", export.to_csv(index=False).encode(),
                       file_name=f"scouting_trip_{selected.iloc[0].get('model', 'combined')}_{selected.iloc[0].location}_{len(selected)}plots.csv",
                       mime="text/csv", key=f"{key_prefix}_download")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default="2022/DataPublication_final")
    parser.add_argument("--output", default="outputs/plot_coordinates.csv")
    args = parser.parse_args()
    frame = build_coordinates(args.data_root, args.output)
    print(f"Saved coordinates for {len(frame)} plots to {args.output}")
