"""Near-real-time gridded air-quality and weather provider.

Uses Open-Meteo's public Air Quality API (CAMS) and Weather API.
These are model-grid estimates, NOT CPCB reference-monitor observations.
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .aqi import classify, sub_index

log = logging.getLogger("rasaynam.live")

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = max(60, int(os.environ.get('LIVE_DATA_CACHE_SECONDS', '900')))

class LiveDataUnavailable(RuntimeError):
    pass

class LiveDataProvider:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict]] = {}

    @staticmethod
    def _get_json(url: str, params: dict) -> dict:
        request = Request(url + "?" + urlencode(params), headers={"User-Agent": "Rasaynam/1.0"})
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("error"):
            raise LiveDataUnavailable(payload.get("reason", "upstream API error"))
        return payload

    def get_station(self, station: dict) -> dict:
        sid = station["station_id"]
        cached = self._cache.get(sid)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            return cached[1]

        lat, lon = float(station["latitude"]), float(station["longitude"])
        air_params = {
            "latitude": lat, "longitude": lon,
            "current": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide",
            "hourly": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide",
            "forecast_days": 7, "past_days": 2, "timezone": "Asia/Kolkata",
        }
        weather_params = {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,dew_point_2m,surface_pressure,precipitation,wind_speed_10m,wind_direction_10m",
            "hourly": "temperature_2m,relative_humidity_2m,dew_point_2m,surface_pressure,precipitation,wind_speed_10m,wind_direction_10m",
            "past_days": 2, "forecast_days": 7, "timezone": "Asia/Kolkata",
        }
        air = self._get_json(AIR_URL, air_params)
        weather = self._get_json(WEATHER_URL, weather_params)
        cur = air.get("current") or {}
        wcur = weather.get("current") or {}

        def number(source: dict, key: str, divisor: float = 1.0):
            value = source.get(key)
            return None if value is None else float(value) / divisor

        pollutants = {
            "pm25": number(cur, "pm2_5"),
            "pm10": number(cur, "pm10"),
            "no2": number(cur, "nitrogen_dioxide"),
            "so2": number(cur, "sulphur_dioxide"),
            # Open-Meteo reports CO in µg/m³; Rasaynam's CPCB table expects mg/m³.
            "co": number(cur, "carbon_monoxide", 1000.0),
        }
        sub_indices = {}
        for key, value in pollutants.items():
            index = sub_index(key, value)
            if index is not None:
                sub_indices[key] = index
        valid = list(sub_indices.values())
        if not valid:
            raise LiveDataUnavailable("upstream current pollutant values are empty")
        aqi = int(round(max(valid)))
        cls = classify(aqi)
        timestamp = cur.get("time") or air.get("current", {}).get("time")
        if not timestamp:
            raise LiveDataUnavailable("upstream response did not include a current timestamp")

        record = {
            "station_id": sid,
            "timestamp": timestamp,
            "aqi": aqi,
            "category": cls["category"],
            "color": cls["color"],
            "severity": cls["severity"],
            "dominant": max(sub_indices, key=sub_indices.get),
            **pollutants,
            "temp_c": number(wcur, "temperature_2m"),
            "relative_humidity_pct": number(wcur, "relative_humidity_2m"),
            "dew_point_c": number(wcur, "dew_point_2m"),
            "surface_pressure_hpa": number(wcur, "surface_pressure"),
            "precipitation_mm": number(wcur, "precipitation"),
            "wind_speed_kmh": number(wcur, "wind_speed_10m"),
            "wind_direction_deg": number(wcur, "wind_direction_10m"),
             "u_wind_10m": (
                -number(wcur, "wind_speed_10m") * math.sin(math.radians(number(wcur, "wind_direction_10m")))
                if number(wcur, "wind_speed_10m") is not None and number(wcur, "wind_direction_10m") is not None else 0.0
            ),
            "v_wind_10m": (
                -number(wcur, "wind_speed_10m") * math.cos(math.radians(number(wcur, "wind_direction_10m")))
                if number(wcur, "wind_speed_10m") is not None and number(wcur, "wind_direction_10m") is not None else 0.0
            ),
            "source": "Open-Meteo CAMS gridded estimate",
            "source_resolution_km": "approximately 11–45",
            "source_note": "Model-grid estimate; not a CPCB ground-monitor measurement.",
        }
        # Build a recent 3-hourly lag window from the upstream hourly archive.
        # Keep 23 past samples and append the current 15-minute model estimate.
        ah = air.get("hourly") or {}
        wh = weather.get("hourly") or {}
        times = ah.get("time") or []
        wt = wh.get("time") or []
        try:
            current_dt = datetime.fromisoformat(timestamp)
            eligible = [i for i, value in enumerate(times)
                        if datetime.fromisoformat(value) <= current_dt]
            end_idx = eligible[-1] if eligible else len(times) - 1
            chosen = list(range(max(0, end_idx - 69), end_idx + 1, 3))[-23:]
        except Exception:
            chosen = []
        history = []
        weather_lookup = {value: i for i, value in enumerate(wt)}
        for i in chosen:
            ts = times[i]
            wi = weather_lookup.get(ts)
            if wi is None:
                continue
            def at(source, key):
                values = source.get(key) or []
                return float(values[i]) if i < len(values) and values[i] is not None else None
            p = {
                "pm25": at(ah, "pm2_5"), "pm10": at(ah, "pm10"),
                "no2": at(ah, "nitrogen_dioxide"), "so2": at(ah, "sulphur_dioxide"),
                "co": (at(ah, "carbon_monoxide") / 1000.0) if at(ah, "carbon_monoxide") is not None else None,
            }
            indices = [sub_index(k, v) for k, v in p.items() if v is not None]
            if not indices:
                continue
            history.append({"timestamp": ts, **p, "aqi": max(indices)})
        history.append({"timestamp": timestamp, **pollutants, "aqi": aqi})
        record["_history"] = history[-24:]
        result = {"current": record, "air_hourly": ah,
                  "weather_current": wcur, "fetched_at": datetime.now(timezone.utc).isoformat()}
        self._cache[sid] = (time.monotonic(), result)
        return result
