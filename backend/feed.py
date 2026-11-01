"""In-memory access to the historical weather / AQI dataset.

Loads the CSV once at startup, computes the CPCB AQI for every row, and
exposes slices the REST API and WebSocket broadcaster need. Swap this module
for a database-backed implementation to go live — callers don't change.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from ml.features import DIWALI_DATES
from .aqi import aqi_from_frame, classify

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = "ncr_punjab_haryana_weather_aqi_2020_2025.csv"

_AQI_INPUTS = ["pm25", "pm10", "no2", "so2", "co"]
_COL_OF = {
    "pm25": "pm25_ugm3",
    "pm10": "pm10_ugm3",
    "no2": "no2_ugm3",
    "so2": "so2_ugm3",
    "co": "co_mgm3",
}

# Friendly neighbourhood labels per monitoring station
AREA_META: dict[str, dict[str, str]] = {
    "DL_SAFDARJUNG": {"area": "Safdarjung", "label": "New Delhi – Safdarjung"},
    "DL_ANAND_VIHAR": {"area": "Anand Vihar", "label": "Delhi – Anand Vihar"},
    "HR_GURUGRAM_SEC51": {"area": "Sector 51", "label": "Gurugram – Sector 51"},
    "UP_NOIDA_SEC62": {"area": "Sector 62", "label": "Noida – Sector 62"},
    "HR_AMBALA_AFS": {"area": "Air Force Station", "label": "Ambala – AFS"},
    "HR_HISAR_HAU": {"area": "HAU Campus", "label": "Hisar – HAU"},
    "PB_AMRITSAR_GT": {"area": "GT Road", "label": "Amritsar – GT Road"},
    "PB_LUDHIANA_PAU": {"area": "PAU Campus", "label": "Ludhiana – PAU"},
}


def _load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # raw timestamps look like "2020-09-01 00:%00:%00" — keep date + hour
    df["timestamp"] = pd.to_datetime(
        df["timestamp"].astype(str).str.slice(0, 13) + ":00:00",
        format="%Y-%m-%d %H:%M:%S",
    )
    df = df.sort_values(["station_id", "timestamp"]).reset_index(drop=True)
    aqi, dom = aqi_from_frame({k: df[c].to_numpy() for k, c in _COL_OF.items()})
    df["aqi"] = aqi
    df["dominant"] = [_AQI_INPUTS[i] for i in dom]
    return df


def _clean(v):
    """Convert numpy scalars to plain Python for JSON safety."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        v = float(v)
    if isinstance(v, float) and not np.isfinite(v):
        return None
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


class DataFeed:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.environ.get("DATA_PATH") or (ROOT / DEFAULT_DATA))
        self.reload()

    # ------------------------------------------------------------ lifecycle --
    def reload(self) -> None:
        self.df = _load(self.path)
        self._by_station = {
            sid: grp for sid, grp in self.df.groupby("station_id", sort=False)
        }
        self.latest_ts = self.df["timestamp"].max()
        self.earliest_ts = self.df["timestamp"].min()

    # ------------------------------------------------------------ metadata ---
    @property
    def station_ids(self) -> list[str]:
        return sorted(self._by_station.keys())

    def metadata(self) -> list[dict]:
        out = []
        for sid in self.station_ids:
            g = self._by_station[sid]
            first = g.iloc[0]
            meta = AREA_META.get(sid, {"area": sid, "label": sid})
            out.append(
                {
                    "station_id": sid,
                    "city": _clean(first["city"]),
                    "state": _clean(first["state"]),
                    "area": meta["area"],
                    "label": meta["label"],
                    "spatial_level": _clean(first["spatial_level"]),
                    "latitude": _clean(first["latitude"]),
                    "longitude": _clean(first["longitude"]),
                    "records": int(len(g)),
                    "from": g["timestamp"].min().isoformat(),
                    "to": g["timestamp"].max().isoformat(),
                }
            )
        return out

    def station_df(self, station_id: str) -> pd.DataFrame:
        if station_id not in self._by_station:
            raise KeyError(f"unknown station: {station_id}")
        return self._by_station[station_id]

    # ------------------------------------------------------------- records ---
    @staticmethod
    def _record(row: pd.Series) -> dict:
        cls = classify(row["aqi"])
        return {
            "timestamp": row["timestamp"].isoformat(),
            "aqi": cls["aqi"],
            "category": cls["category"],
            "color": cls["color"],
            "severity": cls["severity"],
            "dominant": _clean(row["dominant"]),
            "pm25": _clean(round(float(row["pm25_ugm3"]), 1)),
            "pm10": _clean(round(float(row["pm10_ugm3"]), 1)),
            "no2": _clean(round(float(row["no2_ugm3"]), 1)),
            "so2": _clean(round(float(row["so2_ugm3"]), 1)),
            "co": _clean(round(float(row["co_mgm3"]), 2)),
            "temp_c": _clean(round(float(row["temp_c"]), 1)),
            "relative_humidity_pct": _clean(round(float(row["relative_humidity_pct"]), 1)),
            "dew_point_c": _clean(round(float(row["dew_point_c"]), 1)),
            "precipitation_mm": _clean(round(float(row["precipitation_mm"]), 1)),
            "wind_speed_kmh": _clean(round(float(row["wind_speed_kmh"]), 1)),
            "wind_direction_deg": _clean(round(float(row["wind_direction_deg"]), 1)),
        }

    def latest_per_station(self) -> list[dict]:
        out = []
        for sid in self.station_ids:
            g = self._by_station[sid]
            rec = self._record(g.iloc[-1])
            rec["station_id"] = sid
            out.append(rec)
        return out

    def latest(self, station_id: str) -> dict:
        g = self.station_df(station_id)
        rec = self._record(g.iloc[-1])
        rec["station_id"] = station_id
        return rec

    def history(
        self,
        station_id: str,
        hours: float | None = None,
        max_points: int = 500,
    ) -> list[dict]:
        g = self.station_df(station_id)
        if hours is not None:
            start = g["timestamp"].max() - pd.Timedelta(hours=float(hours))
            g = g[g["timestamp"] >= start]
        if len(g) > max_points:
            step = int(np.ceil(len(g) / max_points))
            keep = g.iloc[::step]
            if keep.index[-1] != g.index[-1]:
                keep = pd.concat([keep, g.tail(1)])
            g = keep
        return [
            {
                "ts": r["timestamp"].isoformat(),
                "aqi": (None if pd.isna(r["aqi"]) else int(round(r["aqi"]))),
                "pm25": _clean(round(float(r["pm25_ugm3"]), 1)),
                "pm10": _clean(round(float(r["pm10_ugm3"]), 1)),
                "no2": _clean(round(float(r["no2_ugm3"]), 1)),
                "so2": _clean(round(float(r["so2_ugm3"]), 1)),
                "co": _clean(round(float(r["co_mgm3"]), 2)),
                "temp_c": _clean(round(float(r["temp_c"]), 1)),
                "humidity": _clean(round(float(r["relative_humidity_pct"]), 1)),
                "wind": _clean(round(float(r["wind_speed_kmh"]), 1)),
            }
            for _, r in g.iterrows()
        ]

    # ------------------------------------------------------ diwali climatology --
    @staticmethod
    def _window_stats(g: pd.DataFrame) -> dict | None:
        if g.empty:
            return None
        return {
            "aqi_mean": int(round(float(g["aqi"].mean()))),
            "pm25_mean": round(float(g["pm25_ugm3"].mean()), 1),
            "aqi_max": int(round(float(g["aqi"].max()))),
            "n": int(len(g)),
        }

    def diwali_climatology(self) -> dict:
        """Before / during / after Diwali statistics from the historical data."""
        df = self.df
        data_years = set(int(y) for y in df["timestamp"].dt.year.unique())

        per_year = []
        for d in DIWALI_DATES:
            if d.year not in data_years:
                continue
            before = df[(df["timestamp"] >= d - pd.Timedelta(days=15)) & (df["timestamp"] < d - pd.Timedelta(days=1))]
            during = df[(df["timestamp"] >= d - pd.Timedelta(days=1)) & (df["timestamp"] <= d + pd.Timedelta(days=1))]
            after = df[(df["timestamp"] > d + pd.Timedelta(days=1)) & (df["timestamp"] <= d + pd.Timedelta(days=15))]
            if during.empty:
                continue
            per_year.append(
                {
                    "year": d.year,
                    "diwali_date": d.strftime("%Y-%m-%d"),
                    "before": self._window_stats(before),
                    "during": self._window_stats(during),
                    "after": self._window_stats(after),
                }
            )

        month = df["timestamp"].dt.month
        oct_nov = df[month.isin([10, 11])]
        rest = df[~month.isin([10, 11])]
        monthly = df.groupby(month)["aqi"].mean()
        peak_month = int(monthly.idxmax())

        oct_nov_mean = float(oct_nov["aqi"].mean())
        rest_mean = float(rest["aqi"].mean())
        uplift = round(100 * (oct_nov_mean - rest_mean) / max(rest_mean, 1e-9), 1)

        today = pd.Timestamp.today().normalize()
        upcoming = DIWALI_DATES[DIWALI_DATES >= today]
        nxt = upcoming[0] if len(upcoming) else DIWALI_DATES[-1]

        season_means = {
            "diwali_months_aqi_mean": int(round(oct_nov_mean)),
            "other_months_aqi_mean": int(round(rest_mean)),
            "uplift_pct": uplift,
            "peak_month": peak_month,
            "peak_month_aqi_mean": int(round(float(monthly.loc[peak_month]))),
        }

        during_means = [y["during"]["aqi_mean"] for y in per_year if y["during"]]
        diwali_avg = int(round(float(np.mean(during_means)))) if during_means else None

        insight = (
            f"Across 2020–2025 the region's AQI in October–November averages "
            f"{season_means['diwali_months_aqi_mean']} vs {season_means['other_months_aqi_mean']} "
            f"in the rest of the year ({uplift:+.0f}%). On Diwali day itself (±1 day) the 6-year "
            f"average is {diwali_avg}, and pollution typically peaks in the 24–48 hours AFTER "
            f"Diwali night as cracker smoke settles under calm, cold, humid air — often on top of "
            f"stubble-burning smoke from Punjab/Haryana."
        )

        return {
            "per_year": per_year,
            "seasonal": season_means,
            "next_diwali": {
                "date": nxt.strftime("%Y-%m-%d"),
                "days_remaining": int((nxt - today).days),
            },
            "insight": insight,
        }
