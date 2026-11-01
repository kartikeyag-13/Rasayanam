"""CPCB National Air Quality Index (AQI): computation, categories, health advisories.

Reference: Central Pollution Control Board, "National Air Quality Index" (2014).
The sub-index for each pollutant is a piecewise-linear interpolation over the
official breakpoint table; the overall AQI is the maximum sub-index across the
pollutants present. Verified against the dataset's own ``aqi_sub_index`` column
(PM2.5 96.7 -> 222, exactly as the dataset encodes it).
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

# pollutant -> (concentration breakpoints, corresponding AQI breakpoints)
# The final concentration breakpoint maps to AQI 500; beyond it values clamp to 500.
BREAKPOINTS: dict[str, tuple[list[float], list[float]]] = {
    "pm25": ([0, 30, 60, 90, 120, 250, 380], [0, 50, 100, 200, 300, 400, 500]),
    "pm10": ([0, 50, 100, 250, 350, 430, 510], [0, 50, 100, 200, 300, 400, 500]),
    "no2": ([0, 40, 80, 180, 280, 400, 520], [0, 50, 100, 200, 300, 400, 500]),
    "so2": ([0, 40, 80, 380, 800, 1600, 2400], [0, 50, 100, 200, 300, 400, 500]),
    "co": ([0, 1, 2, 10, 17, 34, 51], [0, 50, 100, 200, 300, 400, 500]),
}

POLLUTANT_UNITS: dict[str, str] = {
    "pm25": "µg/m³",
    "pm10": "µg/m³",
    "no2": "µg/m³",
    "so2": "µg/m³",
    "co": "mg/m³",
}

# (min, max, name, color) — CPCB categories
CATEGORIES: list[tuple[int, int, str, str]] = [
    (0, 50, "Good", "#43a047"),
    (51, 100, "Satisfactory", "#8bc34a"),
    (101, 200, "Moderate", "#f2c230"),
    (201, 300, "Poor", "#f28c28"),
    (301, 400, "Very Poor", "#e03b3b"),
    (401, 500, "Severe", "#a4133c"),
]

# Health advisories per CPCB category (extended with actionable guidance).
ADVISORIES: dict[str, dict] = {
    "Good": {
        "summary": "Air quality is satisfactory. Enjoy your normal outdoor activities.",
        "sensitive": "No health risk for anyone, including children, elderly and people with lung or heart disease.",
        "do": [
            "Open windows and ventilate your home in the morning",
            "Go for walks, runs and outdoor exercise",
            "Keep windows open while cooking to exhaust fumes",
        ],
        "avoid": [],
        "mask": False,
        "outdoor": "safe",
    },
    "Satisfactory": {
        "summary": "Air quality is acceptable. Minor breathing discomfort may occur in unusually sensitive people.",
        "sensitive": "Unusually sensitive people may feel mild irritation on prolonged outdoor exposure.",
        "do": [
            "Normal outdoor activity is fine for most people",
            "Drink plenty of water to keep airways moist",
            "Sensitive people: take breaks if you feel throat or eye irritation",
        ],
        "avoid": ["Unusually sensitive people should avoid prolonged heavy exertion outdoors"],
        "mask": False,
        "outdoor": "safe",
    },
    "Moderate": {
        "summary": "Breathing discomfort to people with lung and heart disease on prolonged exposure.",
        "sensitive": "Children, elderly, asthma/COPD patients and heart patients should limit long outdoor exertion.",
        "do": [
            "Asthma & COPD patients: carry your inhaler/rescue medication",
            "Prefer indoor exercise over outdoor runs",
            "Use purifiers in bedrooms if AQI stays above 150 through the night",
            "Wet-mop floors and dust surfaces to cut settled particulate matter",
        ],
        "avoid": [
            "Prolonged heavy outdoor exertion for sensitive groups",
            "Outdoor morning exercise near busy roads",
        ],
        "mask": False,
        "outdoor": "limit",
    },
    "Poor": {
        "summary": "Breathing discomfort to most people on prolonged exposure.",
        "sensitive": "Children, elderly and people with asthma/COPD/heart disease are at明显 increased risk — symptoms like coughing and wheeze can start within hours.",
        "do": [
            "Wear an N95/FFP2 mask whenever you step outside",
            "Keep outdoor exposure short; shift workouts indoors",
            "Run air purifiers (CADR-rated) in the room where you sleep",
            "Keep medications and inhalers within reach",
            "Avoid smoky kitchens, incense and candles indoors",
        ],
        "avoid": [
            "Morning and evening outdoor exercise",
            "Long commutes on open two-wheelers",
            "Outdoor sports for school children",
        ],
        "mask": True,
        "outdoor": "limit",
    },
    "Very Poor": {
        "summary": "Respiratory illness likely on prolonged exposure. Healthy people may feel discomfort too.",
        "sensitive": "Asthma, COPD, bronchitis and heart patients: high risk of attacks and hospital visits. Children's lungs absorb more pollutant per kg of body weight.",
        "do": [
            "N95 mask outdoors — every time, no exceptions",
            "Stay indoors as much as possible; work from home if you can",
            "Seal window gaps; use purifiers on high mode for 30 min after cooking",
            "Steam inhalation and saline gargles once a day if throat is irritated",
            "Watch for breathlessness, chest tightness — seek help early",
        ],
        "avoid": [
            "All non-essential outdoor activity",
            "Crackers, open burning, outdoor barbecues",
            "Traffic-choked routes; carpool and recirculate cabin air",
        ],
        "mask": True,
        "outdoor": "avoid",
    },
    "Severe": {
        "summary": "Healthy people are affected; serious impact on those with existing lung and heart disease.",
        "sensitive": "This is an emergency for elderly, infants, pregnant women and anyone with heart/lung disease. Effects appear quickly even in healthy adults.",
        "do": [
            "Stay indoors with windows closed; purifiers running",
            "N95/FFP2 mask even for brief outdoor trips",
            "Follow official advisories (CPCB/CAQM, district administration)",
            "Keep emergency numbers and medications ready",
            "See a doctor if you develop breathlessness at rest, chest pain or bluish lips",
        ],
        "avoid": [
            "Stepping out unless absolutely necessary",
            "Outdoor exercise of any kind",
            "Letting children play outdoors",
        ],
        "mask": True,
        "outdoor": "avoid",
    },
}


def sub_index(pollutant: str, conc: float | None) -> float | None:
    """Scalar CPCB sub-index for one pollutant concentration. None if unknown."""
    if conc is None:
        return None
    try:
        c = float(conc)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(c) or c < 0:
        return None
    xs, ys = BREAKPOINTS[pollutant]
    if c >= xs[-1]:
        return 500.0
    # piecewise-linear interpolation over breakpoints
    for i in range(len(xs) - 1):
        if c <= xs[i + 1]:
            if xs[i + 1] == xs[i]:
                return float(ys[i])
            frac = (c - xs[i]) / (xs[i + 1] - xs[i])
            return float(ys[i] + frac * (ys[i + 1] - ys[i]))
    return 500.0


def sub_index_np(pollutant: str, conc: Sequence[float] | np.ndarray) -> np.ndarray:
    """Vectorised sub-index. Invalid/negative inputs become NaN."""
    xs, ys = BREAKPOINTS[pollutant]
    c = np.asarray(conc, dtype=float)
    out = np.full(c.shape, np.nan)
    valid = np.isfinite(c) & (c >= 0)
    if valid.any():
        out[valid] = np.interp(c[valid], xs, ys)
    return out


def aqi_from_frame(cols: Mapping[str, Sequence[float]]) -> tuple[np.ndarray, np.ndarray]:
    """Overall AQI per row from pollutant columns.

    ``cols`` keys must be breakpoint keys: pm25, pm10, no2, so2, co.
    Returns (aqi_array, dominant_pollutant_index_array).
    """
    names = list(cols)
    if not names:
        raise ValueError("no pollutant columns given")
    stack = np.vstack([sub_index_np(n, cols[n]) for n in names])
    filled = np.where(np.isnan(stack), -1.0, stack)
    dom = np.argmax(filled, axis=0)
    aqi = stack[dom, np.arange(stack.shape[1])]
    aqi = np.where(aqi < 0, np.nan, aqi)
    return aqi, dom


def classify(aqi: float | int | None) -> dict:
    """Category + health advisory for an AQI value (None-safe)."""
    if aqi is None or not math.isfinite(float(aqi)):
        return {
            "aqi": None,
            "category": "Unknown",
            "color": "#8a93a6",
            "range": "-",
            "severity": 0,
            "summary": "No AQI reading available for this station yet.",
            "sensitive": "",
            "do": [],
            "avoid": [],
            "mask": False,
            "outdoor": "unknown",
        }
    v = int(round(float(aqi)))
    for i, (lo, hi, name, color) in enumerate(CATEGORIES):
        if v <= hi:
            adv = ADVISORIES[name]
            return {
                "aqi": v,
                "category": name,
                "color": color,
                "range": f"{lo}-{hi}",
                "severity": i,
                "summary": adv["summary"],
                "sensitive": adv["sensitive"],
                "do": adv["do"],
                "avoid": adv["avoid"],
                "mask": adv["mask"],
                "outdoor": adv["outdoor"],
            }
    lo, hi, name, color = CATEGORIES[-1]
    adv = ADVISORIES[name]
    return {
        "aqi": min(v, 500),
        "category": name,
        "color": color,
        "range": f"{lo}+",
        "severity": 5,
        "summary": adv["summary"],
        "sensitive": adv["sensitive"],
        "do": adv["do"],
        "avoid": adv["avoid"],
        "mask": adv["mask"],
        "outdoor": adv["outdoor"],
    }
