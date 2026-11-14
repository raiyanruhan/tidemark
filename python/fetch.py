"""
fetch.py, data retrieval routing and variable computation.

Sources:
  NASA POWER API  (MERRA-2 reanalysis, 1981-present)
  NASA GES DISC   (GPM IMERG satellite precipitation, 2001-present)
  NASA AppEEARS   (MODIS MOD11A2 LST + MOD16A2 ET, 2001-present)
  ORNL DAAC MODIS (MOD13Q1 NDVI, 2000-present)
"""
import math

import numpy as np
import requests

POWER_URL   = "https://power.larc.nasa.gov/api/temporal/monthly/point"
FILL_VALUE  = -999.0

COMPOUND_PARAMS = frozenset({"VPD", "DTR"})

# MODIS_PARAMS: fetched from ORNL DAAC (no auth).
MODIS_PARAMS = frozenset({"NDVI"})

# GESDISC_PARAMS: fetched from NASA GES DISC (GPM IMERG, Earthdata auth).
# PRECTOTCORR routes here instead of POWER: satellite data, 0.1-deg resolution.
GESDISC_PARAMS = frozenset({"PRECTOTCORR"})

# APPEEARS_PARAMS: fetched from NASA AppEEARS (MODIS, Earthdata auth, async).
APPEEARS_PARAMS = frozenset({"LST", "ET_MOD16"})

PARAM_META = {
    "T2M":         ("temperature",                  "degC"),
    "T2M_MAX":     ("max temperature",              "degC"),
    "T2M_MIN":     ("min temperature",              "degC"),
    "PRECTOTCORR": ("precipitation",                "mm/day"),
    "RH2M":        ("humidity",                     "%"),
    "EVLAND":      ("evaporation",                  "mm/day"),
    "WS10M":       ("wind speed",                   "m/s"),
    "VPD":         ("vapor pressure deficit",       "kPa"),
    "DTR":         ("diurnal temp range",           "degC"),
    "GWETROOT":    ("root zone soil moisture",      "fraction"),
    "GWETTOP":     ("surface soil moisture",        "fraction"),
    "GWETPROF":    ("profile soil moisture",        "fraction"),
    "FROST_DAYS":  ("frost days",                   "days"),
    "TSOIL1":      ("soil temperature",             "degC"),
    "TS":          ("skin temperature",             "degC"),
    "NDVI":        ("vegetation index",             "ratio"),
    "LST":         ("land surface temperature",     "degC"),
    "ET_MOD16":    ("evapotranspiration (MODIS)",   "mm/day"),
}


def fetch_monthly(lat, lon, param, start, end, progress=None):
    """
    {year: {month: value}} for all valid monthly values.
    Routes to the appropriate source based on param:
      MODIS_PARAMS   -> ORNL DAAC (no auth)
      GESDISC_PARAMS -> GES DISC GPM IMERG (Earthdata auth)
      APPEEARS_PARAMS-> AppEEARS MODIS (Earthdata auth, async)
      everything else -> NASA POWER MERRA-2 (no auth)
    """
    if param in MODIS_PARAMS:
        from fetch_modis import fetch_ndvi_monthly
        return fetch_ndvi_monthly(lat, lon, start, end, progress)

    if param in GESDISC_PARAMS:
        from fetch_gesdisc import fetch_precip_monthly
        return fetch_precip_monthly(lat, lon, start, end, progress)

    if param in APPEEARS_PARAMS:
        from fetch_appeears import fetch_appeears_monthly
        return fetch_appeears_monthly(lat, lon, param, start, end, progress)

    resp = requests.get(
        POWER_URL,
        params={
            "start": start, "end": end,
            "latitude": lat, "longitude": lon,
            "community": "ag", "parameters": param, "format": "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json()["properties"]["parameter"][param]
    by_year = {}
    for key, val in raw.items():
        year, month = int(key[:4]), int(key[4:])
        if month == 13 or val <= FILL_VALUE + 1.0:
            continue
        by_year.setdefault(year, {})[month] = val
    return by_year


def monthly_to_annual(monthly_by_year):
    annual = []
    for year in sorted(monthly_by_year):
        m = monthly_by_year[year]
        if len(m) == 12:
            annual.append((year, float(np.mean(list(m.values())))))
    return annual


def monthly_to_annual_min(monthly_by_year, min_months=6):
    """
    Like monthly_to_annual but accepts years with >= min_months valid months.
    Used for MODIS NDVI where monsoon cloud cover may gap some calendar months.
    """
    annual = []
    for year in sorted(monthly_by_year):
        m = monthly_by_year[year]
        if len(m) >= min_months:
            annual.append((year, float(np.mean(list(m.values())))))
    return annual


def fetch_annual_multi(lat, lon, params, start, end):
    """
    Single POWER request for multiple params.
    Returns {year: {param: annual_mean}}, only years complete in all params.
    """
    resp = requests.get(
        POWER_URL,
        params={
            "start": start, "end": end,
            "latitude": lat, "longitude": lon,
            "community": "ag", "parameters": ",".join(params), "format": "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    param_data = resp.json()["properties"]["parameter"]

    by_year = {p: {} for p in params}
    for p in params:
        for key, val in param_data[p].items():
            year, month = int(key[:4]), int(key[4:])
            if month == 13 or val <= FILL_VALUE + 1.0:
                continue
            by_year[p].setdefault(year, []).append(val)

    complete = set.intersection(*[
        {y for y, v in by_year[p].items() if len(v) == 12} for p in params
    ])
    return {
        year: {p: float(np.mean(by_year[p][year])) for p in params}
        for year in sorted(complete)
    }


def compute_compound_series(lat, lon, var, start, end):
    """
    VPD: es(T) * (1 - RH/100), Tetens/Buck (1981) formula, kPa.
    DTR: T2M_MAX - T2M_MIN, degC.
    """
    if var == "VPD":
        multi = fetch_annual_multi(lat, lon, ["T2M", "RH2M"], start, end)
        series = []
        for year in sorted(multi):
            T  = multi[year]["T2M"]
            RH = multi[year]["RH2M"]
            es = 0.6108 * math.exp(17.27 * T / (T + 237.3))
            series.append((year, es * (1.0 - RH / 100.0)))
        return series
    if var == "DTR":
        multi = fetch_annual_multi(lat, lon, ["T2M_MAX", "T2M_MIN"], start, end)
        return [(y, multi[y]["T2M_MAX"] - multi[y]["T2M_MIN"]) for y in sorted(multi)]
    raise ValueError(f"unknown compound variable: {var}")
