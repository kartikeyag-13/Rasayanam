"""Shared feature engineering for training (ml.train) and online rollout
(backend.forecast). Keeping one implementation guarantees that serving-time
feature rows are built exactly like training rows.

All features are knowable at prediction time:
  * pollutant "now" = value at the current step, lags = previous steps,
  * weather = observed weather at the current step (persistence during rollout),
  * time / Diwali features = derived from the timestamp itself.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.aqi import aqi_from_frame

# ---------------------------------------------------------------- columns ---
POLLUTANTS = ["pm25_ugm3", "pm10_ugm3", "no2_ugm3", "so2_ugm3", "co_mgm3"]

WEATHER_FEATURES = [
    "temp_c",
    "relative_humidity_pct",
    "dew_point_c",
    "surface_pressure_hpa",
    "precipitation_mm",
    "wind_speed_kmh",
    "wind_direction_deg",
    "u_wind_10m",
    "v_wind_10m",
]

# pollutant-history features (the "_lagN" suffix counts 3-hour steps)
LAG_FEATURES: list[str] = []
for _p in ("pm25_ugm3", "pm10_ugm3"):
    LAG_FEATURES += [f"{_p}_now", f"{_p}_lag1", f"{_p}_lag8"]
for _p in ("no2_ugm3", "so2_ugm3", "co_mgm3"):
    LAG_FEATURES += [f"{_p}_now", f"{_p}_lag1"]
LAG_FEATURES += ["aqi_now", "aqi_lag1", "aqi_lag8", "pm25_roll8", "pm10_roll8"]

TIME_FEATURES = [
    "hour",
    "sin_hour",
    "cos_hour",
    "month",
    "sin_month",
    "cos_month",
    "doy_sin",
    "doy_cos",
]

DIWALI_FEATURES = ["days_to_diwali", "diwali_window", "post_diwali_15"]

FEATURE_COLUMNS = LAG_FEATURES + WEATHER_FEATURES + TIME_FEATURES + DIWALI_FEATURES

# Histories that must be maintained during recursive rollout (>= 9 values).
HISTORY_KEYS = POLLUTANTS + ["aqi"]

# Training targets: name -> column created by prepare_training_frame()
TARGETS = {
    "pm25_3h": "y_pm25_3h",
    "aqi_3h": "y_aqi_3h",
    "pm25_24h": "y_pm25_24h",
    "aqi_24h": "y_aqi_24h",
}

# ------------------------------------------------------------------ diwali ---
# Diwali (Lakshmi Puja) dates used for the Diwali-proximity features.
DIWALI_DATES = pd.DatetimeIndex(
    [
        "2020-11-14",
        "2021-11-04",
        "2022-10-24",
        "2023-11-12",
        "2024-10-31",
        "2025-10-20",
        "2026-11-08",
        "2027-10-29",
        "2028-10-17",
    ]
)


def time_feature_values(ts: pd.Timestamp) -> dict[str, float]:
    """Time features for a single timestamp (rollout path)."""
    h, m, doy = ts.hour, ts.month, ts.dayofyear
    return {
        "hour": float(h),
        "sin_hour": float(np.sin(2 * np.pi * h / 24)),
        "cos_hour": float(np.cos(2 * np.pi * h / 24)),
        "month": float(m),
        "sin_month": float(np.sin(2 * np.pi * m / 12)),
        "cos_month": float(np.cos(2 * np.pi * m / 12)),
        "doy_sin": float(np.sin(2 * np.pi * doy / 365.25)),
        "doy_cos": float(np.cos(2 * np.pi * doy / 365.25)),
    }


def diwali_feature_values(ts: pd.Timestamp) -> dict[str, float]:
    """Diwali-proximity features for a single timestamp (rollout path).

    days_to_diwali > 0 -> before Diwali, < 0 -> after Diwali.
    """
    deltas = (DIWALI_DATES - ts) / pd.Timedelta(days=1)
    k = int(np.argmin(np.abs(deltas.to_numpy())))
    days = float(deltas[k])
    return {
        "days_to_diwali": days,
        "diwali_window": float(abs(days) <= 30),
        "post_diwali_15": float(-15 <= days < 0),
    }


def _time_features_frame(ts: pd.Series) -> pd.DataFrame:
    hour = ts.dt.hour.to_numpy(dtype=float)
    month = ts.dt.month.to_numpy(dtype=float)
    doy = ts.dt.dayofyear.to_numpy(dtype=float)
    return pd.DataFrame(
        {
            "hour": hour,
            "sin_hour": np.sin(2 * np.pi * hour / 24),
            "cos_hour": np.cos(2 * np.pi * hour / 24),
            "month": month,
            "sin_month": np.sin(2 * np.pi * month / 12),
            "cos_month": np.cos(2 * np.pi * month / 12),
            "doy_sin": np.sin(2 * np.pi * doy / 365.25),
            "doy_cos": np.cos(2 * np.pi * doy / 365.25),
        },
        index=ts.index,
    )


def _diwali_features_frame(ts: pd.Series) -> pd.DataFrame:
    vals = ts.to_numpy(dtype="datetime64[ns]")
    dates = DIWALI_DATES.to_numpy(dtype="datetime64[ns]")
    diff = (dates[None, :] - vals[:, None]) / np.timedelta64(1, "D")
    k = np.argmin(np.abs(diff), axis=1)
    days = diff[np.arange(len(vals)), k]
    return pd.DataFrame(
        {
            "days_to_diwali": days,
            "diwali_window": (np.abs(days) <= 30).astype(float),
            "post_diwali_15": ((days >= -15) & (days < 0)).astype(float),
        },
        index=ts.index,
    )


# --------------------------------------------------------------- training ---
def prepare_training_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Add AQI, lag/rolling features, time & Diwali features, and targets.

    Expects raw dataset columns incl. ``timestamp`` and ``station_id``.
    """
    out = df.sort_values(["station_id", "timestamp"]).reset_index(drop=True).copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    # the raw file already carries sin_hour/cos_hour — we recompute them below
    out = out.drop(columns=[c for c in ("sin_hour", "cos_hour") if c in out.columns])

    aqi_vals, _ = aqi_from_frame(
        {
            "pm25": out["pm25_ugm3"].to_numpy(),
            "pm10": out["pm10_ugm3"].to_numpy(),
            "no2": out["no2_ugm3"].to_numpy(),
            "so2": out["so2_ugm3"].to_numpy(),
            "co": out["co_mgm3"].to_numpy(),
        }
    )
    out["aqi"] = aqi_vals

    grouped = out.groupby("station_id", sort=False)

    for p in POLLUTANTS:
        out[f"{p}_now"] = out[p]
        out[f"{p}_lag1"] = grouped[p].shift(1)
        if p in ("pm25_ugm3", "pm10_ugm3"):
            out[f"{p}_lag8"] = grouped[p].shift(8)

    out["aqi_now"] = out["aqi"]
    out["aqi_lag1"] = grouped["aqi"].shift(1)
    out["aqi_lag8"] = grouped["aqi"].shift(8)
    out["pm25_roll8"] = grouped["pm25_ugm3"].transform(
        lambda s: s.rolling(8, min_periods=1).mean()
    )
    out["pm10_roll8"] = grouped["pm10_ugm3"].transform(
        lambda s: s.rolling(8, min_periods=1).mean()
    )

    time_feats = _time_features_frame(out["timestamp"])
    diwali_feats = _diwali_features_frame(out["timestamp"])
    out = pd.concat([out, time_feats, diwali_feats], axis=1)

    # targets: next 3-hour step and next-day (24h = 8 steps) step
    out["y_pm25_3h"] = grouped["pm25_ugm3"].shift(-1)
    out["y_aqi_3h"] = grouped["aqi"].shift(-1)
    out["y_pm25_24h"] = grouped["pm25_ugm3"].shift(-8)
    out["y_aqi_24h"] = grouped["aqi"].shift(-8)

    return out


# ---------------------------------------------------------------- rollout ---
def _at(hist: list[float], back: int) -> float:
    """Value `back` steps before the end of history (clamped to oldest known)."""
    idx = max(0, len(hist) - 1 - back)
    return float(hist[idx])


def make_rollout_row(
    ts: pd.Timestamp,
    hist: dict[str, list[float]],
    weather: dict[str, float],
) -> pd.DataFrame:
    """Build one feature row for timestamp ``ts`` during recursive forecasting.

    ``hist`` maps HISTORY_KEYS to chronological value lists whose LAST element
    is the value at time ``ts`` (observed or predicted). ``weather`` holds the
    persisted weather at ``ts`` (WEATHER_FEATURES keys).
    """
    row: dict[str, float] = {}
    for p in POLLUTANTS:
        h = hist[p]
        row[f"{p}_now"] = float(h[-1])
        row[f"{p}_lag1"] = _at(h, 1)
        if p in ("pm25_ugm3", "pm10_ugm3"):
            row[f"{p}_lag8"] = _at(h, 8)
    a = hist["aqi"]
    row["aqi_now"] = float(a[-1])
    row["aqi_lag1"] = _at(a, 1)
    row["aqi_lag8"] = _at(a, 8)
    row["pm25_roll8"] = float(np.mean(hist["pm25_ugm3"][-8:]))
    row["pm10_roll8"] = float(np.mean(hist["pm10_ugm3"][-8:]))

    for w in WEATHER_FEATURES:
        row[w] = float(weather[w])
    row.update(time_feature_values(ts))
    row.update(diwali_feature_values(ts))

    return pd.DataFrame([[row[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
