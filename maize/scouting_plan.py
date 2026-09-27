"""Forecast-only, illustrative expectation-gap screen. Not a calibrated risk model."""
import math
import pandas as pd
from .uav import UAV_FEATURES


def plan_tables(predictions, cutoff, model="combined"):
    columns = ["cutoff", "plot_id", "location", "experiment", "range", "row", "genotype", "predicted_yield", "delta_ndvi", "image_age_days", "observation_count", "missing_imagery", "prediction_date"]
    columns += [c for c in ["model", *UAV_FEATURES] if c in predictions]
    combined = predictions.loc[predictions.cutoff.eq(cutoff) & predictions.model.eq(model), columns].copy()
    agronomy = predictions.loc[predictions.cutoff.eq(cutoff) & predictions.model.eq("agronomy"), ["plot_id", "predicted_yield"]].rename(columns={"predicted_yield":"agronomy_yield"})
    frame = combined.merge(agronomy, on="plot_id", validate="one_to_one")
    if len(frame) != len(combined):
        raise ValueError("Every combined forecast needs a matching agronomy forecast")
    for source, name in [("predicted_yield", "forecast_percentile"), ("agronomy_yield", "expectation_percentile")]:
        frame[name] = frame.groupby("location")[source].rank(method="average", pct=True) * 100
    frame["expectation_gap"] = frame.expectation_percentile - frame.forecast_percentile
    frame["low_forecast"] = False
    for _, site in frame.groupby("location"):
        idx = site.sort_values(["predicted_yield", "plot_id"]).head(math.ceil(len(site)*.2)).index
        frame.loc[idx, "low_forecast"] = True
    frame["candidate_anomaly"] = frame.low_forecast & frame.expectation_gap.ge(20) & (cutoff >= 75)
    frame["large_disagreement"] = frame.expectation_gap.abs().ge(30)
    frame = frame.sort_values(["location", "candidate_anomaly", "expectation_gap", "predicted_yield", "plot_id"], ascending=[True, False, False, True, True]).reset_index(drop=True)
    frame["plan_priority"] = frame.groupby("location").cumcount() + 1
    sites = frame.groupby("location", as_index=False).agg(plots=("plot_id", "size"), anomalies=("candidate_anomaly", "sum"), disagreements=("large_disagreement", "sum"), missing_images=("missing_imagery", "sum"))
    sites["anomaly_rate"] = sites.anomalies / sites.plots
    sites = sites.sort_values(["anomaly_rate", "anomalies", "location"], ascending=[False, False, True]).reset_index(drop=True)
    sites["site_priority"] = sites.index + 1
    return frame, sites


def hybrid_watch(forecast_sites, cutoff, model="combined"):
    keys = ["genotype", "location", "year"]
    base = forecast_sites.loc[forecast_sites.cutoff.eq(cutoff) & forecast_sites.model.eq(model), keys + ["site_percentile"]]
    agronomy = forecast_sites.loc[forecast_sites.cutoff.eq(cutoff) & forecast_sites.model.eq("agronomy"), keys + ["site_percentile"]].rename(columns={"site_percentile":"expectation_percentile"})
    joined = base.merge(agronomy, on=keys, validate="one_to_one")
    joined["below_expectation"] = (joined.expectation_percentile - joined.site_percentile).ge(20)
    joined["above_median"] = joined.site_percentile.gt(50)
    watch = joined.groupby("genotype", as_index=False).agg(average_percentile=("site_percentile","mean"), worst_site=("site_percentile","min"), best_site=("site_percentile","max"), sites=("location","nunique"), above_median=("above_median","sum"), below_expectation=("below_expectation","sum"))
    watch["model"] = model
    watch["site_spread"] = watch.best_site - watch.worst_site
    return watch.sort_values(["average_percentile","genotype"], ascending=[False,True])
