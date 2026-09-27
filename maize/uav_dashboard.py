"""Optional UAV controls and dated evidence, compatible with older result folders."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from .decision_brief import MODEL_LABELS
from .uav import latest_image


def select_forecast(predictions, key):
    choices = [m for m in ["combined", "combined_uav"] if m in set(predictions.model)]
    if len(choices) < 2:
        return "combined"
    selected = st.sidebar.selectbox("Scouting forecast", choices, format_func=MODEL_LABELS.get, key=key)
    if selected == "combined_uav":
        st.sidebar.caption("Experimental UAV comparison; check held-out evaluation before interpreting changed priorities.")
    else:
        st.sidebar.caption("UAV thumbnails provide supporting context; this forecast uses agronomy and satellite inputs.")
    return selected


@st.cache_data
def load_index(folder, stamp):
    return pd.read_csv(Path(folder) / "uav_image_index.csv", parse_dates=["image_date"])


def render_uav(plot, output):
    output = Path(output)
    index_path = output / "uav_image_index.csv"
    if not index_path.exists():
        return
    index = load_index(str(output), index_path.stat().st_mtime_ns)
    prediction_date = pd.Timestamp(plot.prediction_date)
    planting_date = prediction_date-pd.Timedelta(days=int(plot.cutoff))
    record = latest_image(index, plot.plot_id, planting_date, prediction_date)
    if record is None:
        st.caption("UAV: no eligible image by this forecast date.")
        return
    age = (prediction_date-record.image_date).days
    st.caption(f"UAV flight: {record.image_date:%Y-%m-%d} · Image age: {age} days")
    fraction = plot.get("uav_latest_green_fraction")
    if pd.notna(fraction):
        st.caption(f"Green-pixel fraction: {fraction:.1%} · RGB appearance indicator, not calibrated canopy cover or a diagnosis.")
    quality = json.loads((output / "uav_data_quality.json").read_text())
    path = Path(quality["data_root"]) / record.path
    if path.is_file():
        st.image(str(path), caption=f"{plot.plot_id} · UAV", width=240)
    else:
        st.caption("UAV image file unavailable locally; dated measurements remain available.")


def render_coverage(predictions, cutoff):
    rows = predictions.loc[predictions.cutoff.eq(cutoff)].drop_duplicates("plot_id")
    text = f"Day {cutoff}: satellite coverage {int(rows.missing_imagery.eq(0).sum())}/{len(rows)} plots"
    if "uav_missing_imagery" in rows:
        text += f" · UAV coverage {int(rows.uav_missing_imagery.eq(0).sum())}/{len(rows)} plots"
    st.caption(text + ". Only observations available by the forecast date are used.")
