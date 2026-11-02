"""Batched, cached access to Open-Meteo's CAMS air-quality and weather APIs.

All values are gridded model estimates, not regulatory monitor observations.
The provider cache is process-local: it reduces duplicate calls within one
Render instance, but is not shared across multiple instances or restarts.
"""
from __future__ import annotations

import json
import logging
import math
import os
import random
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .aqi import classify, overall_aqi

log = logging.getLogger("rasayanam.live")

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = max(300, int(os.environ.get("LIVE_DATA_CACHE_SECONDS", "3600")))
MAX_STALE_SECONDS = max(CACHE_SECONDS, int(os.environ.get("LIVE_DATA_MAX_STALE_SECONDS", "21600")))
REQUEST_TIMEOUT = max(2.0, float(os.environ.get("LIVE_DATA_TIMEOUT_SECONDS", "8")))
MAX_RETRIES = max(0, min(3, int(os.environ.get("LIVE_DATA_MAX_RETRIES", "2"))))
BACKOFF_BASE_SECONDS = 5.0
BACKOFF_MAX_SECONDS = 900.0


class LiveDataUnavailable(RuntimeError):
    """Raised when no usable upstream payload or recent cache is available."""


def average_cams_concentrations(hourly: dict, target: str | datetime) -> dict[str, float | None]:
    """Apply CPCB-style averaging windows to hourly CAMS model concentrations.

    Non-CO species use the preceding 24 hours and require at least 16 valid
    hourly values. CO uses the preceding 8 hours and requires at least 6. This
    addresses averaging periods and minimum temporal coverage, but model inputs
    still are not validated CPCB monitor observations.
    """
    if isinstance(target, datetime):
        target_dt = target
    else:
        try:
            target_dt = datetime.fromisoformat(str(target).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return {"pm25": None, "pm10": None, "no2": None, "so2": None, "co": None}
    times = hourly.get("time") or []
    specs = {
        "pm25": ("pm2_5", 24, 16, 1.0),
        "pm10": ("pm10", 24, 16, 1.0),
        "no2": ("nitrogen_dioxide", 24, 16, 1.0),
        "so2": ("sulphur_dioxide", 24, 16, 1.0),
        "co": ("carbon_monoxide", 8, 6, 1000.0),
    }
    result: dict[str, float | None] = {}
    for output_key, (field, window_hours, minimum_count, divisor) in specs.items():
        values = hourly.get(field) or []
        cutoff = target_dt.timestamp() - window_hours * 3600
        upper = target_dt.timestamp()
        valid = []
        for idx, value in enumerate(values):
            if idx >= len(times) or value is None:
                continue
            try:
                sample_time = datetime.fromisoformat(str(times[idx]).replace("Z", "+00:00"))
                if sample_time.tzinfo is None and target_dt.tzinfo is not None:
                    sample_time = sample_time.replace(tzinfo=target_dt.tzinfo)
                elif sample_time.tzinfo is not None and target_dt.tzinfo is None:
                    sample_time = sample_time.replace(tzinfo=None)
                stamp = sample_time.timestamp()
                concentration = float(value) / divisor
                if cutoff < stamp <= upper and math.isfinite(concentration) and concentration >= 0:
                    valid.append(concentration)
            except (TypeError, ValueError, OverflowError, OSError):
                continue
        result[output_key] = sum(valid) / len(valid) if len(valid) >= minimum_count else None
    return result


class LiveDataProvider:
    """Thread-safe per-process cache with batched location requests.

    A single lock protects cache refreshes. This intentionally serializes a
    cold batch so concurrent REST and WebSocket requests wait for and reuse the
    same result rather than stampeding the upstream provider.
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict]] = {}
        self._raw_cache: dict[str, dict[str, tuple[float, dict]]] = {}
        self._lock = threading.RLock()
        self._blocked_until: dict[str, float] = {}
        self._failures: dict[str, int] = {}

    @staticmethod
    def _retry_after(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            try:
                target = parsedate_to_datetime(value)
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                return max(0.0, (target - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    def _backoff(self, url: str, retry_after: str | None = None) -> float:
        attempt = self._failures.get(url, 0)
        delay = self._retry_after(retry_after)
        server_delay = delay is not None
        if delay is None:
            delay = min(BACKOFF_BASE_SECONDS * (2 ** min(attempt, 8)), BACKOFF_MAX_SECONDS)
            delay *= random.uniform(0.8, 1.2)
        delay = max(1.0, delay) if server_delay else min(max(1.0, delay), BACKOFF_MAX_SECONDS)
        self._failures[url] = attempt + 1
        self._blocked_until[url] = time.monotonic() + delay
        return delay

    def _get_json(self, url: str, params: dict) -> dict | list:
        blocked = self._blocked_until.get(url, 0.0) - time.monotonic()
        if blocked > 0:
            raise LiveDataUnavailable(f"provider temporarily rate-limited; retry in about {int(blocked)} seconds")

        request = Request(
            url + "?" + urlencode(params),
            headers={"User-Agent": "Rasayanam/1.0", "Accept": "application/json"},
        )
        for attempt in range(MAX_RETRIES + 1):
            try:
                with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                    raw = response.read().decode("utf-8")
                payload = json.loads(raw)
                if not isinstance(payload, (dict, list)):
                    raise LiveDataUnavailable("provider returned an unexpected response shape")
                if isinstance(payload, dict) and payload.get("error"):
                    raise LiveDataUnavailable(str(payload.get("reason") or "provider returned an error"))
                self._failures.pop(url, None)
                self._blocked_until.pop(url, None)
                return payload
            except HTTPError as exc:
                if exc.code == 429:
                    delay = self._backoff(url, exc.headers.get("Retry-After"))
                    log.warning("Open-Meteo rate limited %s; suppressing requests for %.0fs", url, delay)
                    raise LiveDataUnavailable("provider rate limit is active") from exc
                if exc.code < 500 or attempt >= MAX_RETRIES:
                    if exc.code >= 500:
                        self._backoff(url)
                    raise LiveDataUnavailable(f"provider HTTP {exc.code}") from exc
                delay = min(BACKOFF_BASE_SECONDS * (2 ** attempt), 30.0) * random.uniform(0.8, 1.2)
                time.sleep(delay)
            except (TimeoutError, URLError, ConnectionError, json.JSONDecodeError) as exc:
                if attempt >= MAX_RETRIES:
                    self._backoff(url)
                    raise LiveDataUnavailable("provider request failed or timed out") from exc
                delay = min(BACKOFF_BASE_SECONDS * (2 ** attempt), 30.0) * random.uniform(0.8, 1.2)
                time.sleep(delay)
            except LiveDataUnavailable:
                raise
        raise LiveDataUnavailable("provider request failed")

    @staticmethod
    def _locations(payload: dict | list, count: int) -> list[dict]:
        if count == 1 and isinstance(payload, dict):
            rows = [payload]
        elif isinstance(payload, list):
            rows = payload
        else:
            raise LiveDataUnavailable("provider returned a malformed multi-location response")
        if len(rows) != count or any(not isinstance(row, dict) for row in rows):
            raise LiveDataUnavailable("provider returned an incomplete multi-location response")
        return rows

    @staticmethod
    def _number(source: dict, key: str, divisor: float = 1.0):
        value = source.get(key)
        if value is None:
            return None
        try:
            result = float(value) / divisor
            return result if math.isfinite(result) else None
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    @classmethod
    def _build_bundle(cls, station: dict, air: dict, weather: dict) -> dict:
        sid = station["station_id"]
        cur = air.get("current") or {}
        wcur = weather.get("current") or {}
        air_hourly = air.get("hourly") or {}
        times = air_hourly.get("time") or []
        timestamp = cur.get("time")
        if not timestamp and times:
            from zoneinfo import ZoneInfo
            now_local = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
            past = [value for value in times if str(value) <= now_local.isoformat(timespec="minutes")]
            timestamp = past[-1] if past else times[0]
        if not timestamp:
            raise LiveDataUnavailable(f"provider did not return a timestamp for {sid}")
        pollutants = average_cams_concentrations(air_hourly, timestamp)
        aqi_value, dominant = overall_aqi(pollutants)

        cls_info = classify(aqi_value)
        speed = cls._number(wcur, "wind_speed_10m")
        direction = cls._number(wcur, "wind_direction_10m")
        record = {
            "station_id": sid,
            "timestamp": timestamp,
            "aqi": cls_info["aqi"],
            "category": cls_info["category"],
            "color": cls_info["color"],
            "severity": cls_info["severity"],
            "dominant": dominant,
            **pollutants,
            "temp_c": cls._number(wcur, "temperature_2m"),
            "relative_humidity_pct": cls._number(wcur, "relative_humidity_2m"),
            "dew_point_c": cls._number(wcur, "dew_point_2m"),
            "surface_pressure_hpa": cls._number(wcur, "surface_pressure"),
            "precipitation_mm": cls._number(wcur, "precipitation"),
            "wind_speed_kmh": speed,
            "wind_direction_deg": direction,
            "u_wind_10m": -speed * math.sin(math.radians(direction)) if speed is not None and direction is not None else None,
            "v_wind_10m": -speed * math.cos(math.radians(direction)) if speed is not None and direction is not None else None,
            "source": "Open-Meteo CAMS gridded estimate",
            "source_resolution_km": "approximately 11–45",
            "source_note": "CAMS concentrations averaged over 24 hours (8 hours for CO) and converted with CPCB breakpoints. Model estimate, not a validated CPCB monitor reading.",
            "aqi_method": "CPCB breakpoints over CAMS rolling concentration averages (24h; CO 8h)",
            "current_available": aqi_value is not None,
        }

        weather_hourly = weather.get("hourly") or {}
        weather_times = weather_hourly.get("time") or []
        try:
            current_dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            selected = []
            for idx, value in enumerate(times):
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if parsed.tzinfo != current_dt.tzinfo:
                    parsed = parsed.replace(tzinfo=current_dt.tzinfo)
                if parsed <= current_dt:
                    selected.append(idx)
            end_idx = selected[-1] if selected else max(0, len(times) - 1)
            chosen = list(range(max(0, end_idx - 69), end_idx + 1, 3))[-23:]
        except (TypeError, ValueError):
            chosen = []
        history = []
        weather_lookup = {value: idx for idx, value in enumerate(weather_times)}
        for idx in chosen:
            if idx >= len(times):
                continue
            ts = times[idx]
            if ts not in weather_lookup:
                continue

            values = average_cams_concentrations(air_hourly, ts)
            history_aqi, _ = overall_aqi(values)
            if history_aqi is not None:
                history.append({"timestamp": ts, **values, "aqi": history_aqi})
        if record["current_available"]:
            history.append({"timestamp": timestamp, **pollutants, "aqi": record["aqi"]})
        record["_history"] = history[-24:]
        return {
            "current": record,
            "air_hourly": air_hourly,
            "weather_current": wcur,
            "weather_hourly": weather_hourly,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _params(stations: list[dict], air: bool) -> dict:
        params = {
            "latitude": ",".join(str(float(s["latitude"])) for s in stations),
            "longitude": ",".join(str(float(s["longitude"])) for s in stations),
            "timezone": "Asia/Kolkata",
        }
        if air:
            params.update({
                "current": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide",
                "hourly": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide",
                "forecast_days": 7,
                "past_days": 2,
            })
        else:
            params.update({
                "current": "temperature_2m,relative_humidity_2m,dew_point_2m,surface_pressure,precipitation,wind_speed_10m,wind_direction_10m",
                "hourly": "temperature_2m,relative_humidity_2m,dew_point_2m,surface_pressure,precipitation,wind_speed_10m,wind_direction_10m",
                "past_days": 2,
                "forecast_days": 7,
            })
        return params

    def get_stations(self, stations: list[dict]) -> dict[str, dict]:
        """Return bundles for several locations using at most two upstream calls."""
        if not stations:
            return {}
        with self._lock:
            now = time.monotonic()
            ready = {}
            stale = {}
            missing = []
            for station in stations:
                sid = station["station_id"]
                item = self._cache.get(sid)
                if item:
                    age = max(0.0, now - item[0])
                    if age < CACHE_SECONDS:
                        ready[sid] = {**item[1], "cache_age_seconds": age, "cache_status": "fresh"}
                        continue
                    if age <= MAX_STALE_SECONDS:
                        stale[sid] = (age, item[1])
                missing.append(station)
            if not missing:
                return ready

            air_payloads = {}
            weather_payloads = {}
            need_air = []
            need_weather = []
            for station in missing:
                sid = station["station_id"]
                raw = self._raw_cache.get(sid, {})
                air_item = raw.get("air")
                weather_item = raw.get("weather")
                if air_item and now - air_item[0] < CACHE_SECONDS:
                    air_payloads[sid] = air_item[1]
                else:
                    need_air.append(station)
                if weather_item and now - weather_item[0] < CACHE_SECONDS:
                    weather_payloads[sid] = weather_item[1]
                else:
                    need_weather.append(station)

            for endpoint, targets, destination, is_air in (
                (AIR_URL, need_air, air_payloads, True),
                (WEATHER_URL, need_weather, weather_payloads, False),
            ):
                if not targets:
                    continue
                try:
                    rows = self._locations(self._get_json(endpoint, self._params(targets, is_air)), len(targets))
                    fetched = time.monotonic()
                    for station, row in zip(targets, rows):
                        sid = station["station_id"]
                        destination[sid] = row
                        self._raw_cache.setdefault(sid, {})["air" if is_air else "weather"] = (fetched, row)
                except LiveDataUnavailable as exc:
                    log.warning("Open-Meteo %s batch unavailable: %s", "air-quality" if is_air else "weather", exc)

            for station in missing:
                sid = station["station_id"]
                air = air_payloads.get(sid)
                if air is None:
                    continue
                weather = weather_payloads.get(sid) or {}
                try:
                    bundle = self._build_bundle(station, air, weather)
                except (LiveDataUnavailable, TypeError, ValueError, KeyError, IndexError) as exc:
                    log.warning("invalid Open-Meteo response for %s: %s", sid, exc)
                    continue
                fetched = time.monotonic()
                self._cache[sid] = (fetched, bundle)
                ready[sid] = {**bundle, "cache_age_seconds": 0.0, "cache_status": "fresh"}

            for sid, (age, bundle) in stale.items():
                ready.setdefault(sid, {**bundle, "cache_age_seconds": age, "cache_status": "stale_cache"})
            return ready

    def get_station(self, station: dict) -> dict:
        """Return one station, using the same cache and locking as batch calls."""
        result = self.get_stations([station]).get(station["station_id"])
        if result is None:
            raise LiveDataUnavailable("no current provider data or recent cache is available")
        return result
