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

# LAADS_PARAMS: fetched from NASA LAADS DAAC via CMR + OPeNDAP ASCII (Earthdata auth).
# MOD08_M3: MODIS Terra monthly 1-degree gridded aerosol optical depth.
LAADS_PARAMS = frozenset({"MOD08_M3"})

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
    "MOD08_M3":    ("aerosol optical depth",        "unitless"),
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

    if param in LAADS_PARAMS:
        from fetch_laads import fetch_aod_monthly
        return fetch_aod_monthly(lat, lon, start, end, progress)

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


def fetch_monthly_multi(lat, lon, params, start, end):
    """
    Single POWER request for multiple params.
    Returns {param: {year: {month: value}}}, fill values and month 13 dropped.
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

    out = {p: {} for p in params}
    for p in params:
        for key, val in param_data[p].items():
            year, month = int(key[:4]), int(key[4:])
            if month == 13 or val <= FILL_VALUE + 1.0:
                continue
            out[p].setdefault(year, {})[month] = val
    return out


def _complete_years(monthly, params):
    return sorted(set.intersection(*[
        {y for y, m in monthly[p].items() if len(m) == 12} for p in params
    ]))


NOAA_ONI_URL = "https://www.cpc.noaa.gov/data/indices/oni.ascii.txt"


def fetch_oni_annual(years):
    """
    Fetch NOAA CPC ONI (Oceanic Niño Index) annual means for the given years.
    Handles two file formats:
      Format A: year-first rows  (year  val1  val2  ... val12)
      Format B: season-first rows (SEAS  YR  TOTAL  ANOM)
    Returns {year: float} with annual mean ONI anomaly, or {} on failure.
    """
    try:
        resp = requests.get(NOAA_ONI_URL, timeout=15, verify=False)
        resp.raise_for_status()
    except Exception:
        return {}

    year_set = set(years)
    accumulate = {}   # {year: [anom, ...]}
    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if not parts:
            continue
        # Format A: first token is 4-digit year, rest are anomalies
        if parts[0].lstrip('-').isdigit() and len(parts[0]) == 4:
            try:
                yr = int(parts[0])
                vals = [float(x) for x in parts[1:] if abs(float(x)) < 50.0]
                if yr in year_set and vals:
                    accumulate[yr] = vals
            except (ValueError, IndexError):
                continue
        # Format B: second token is 4-digit year, fourth token is anomaly
        elif len(parts) >= 4 and parts[1].isdigit() and len(parts[1]) == 4:
            try:
                yr = int(parts[1])
                anom = float(parts[3])
                if yr in year_set and abs(anom) < 50.0:
                    accumulate.setdefault(yr, []).append(anom)
            except (ValueError, IndexError):
                continue

    return {yr: float(np.mean(vals)) for yr, vals in accumulate.items()}


def compute_compound_series(lat, lon, var, start, end):
    """
    VPD: es(T) * (1 - RH/100), Tetens formula, kPa. Computed per month, then averaged
         (es is convex, so applying it to annual-mean T biases VPD low).
    DTR: POWER T2M_RANGE (mean daily range). T2M_MAX - T2M_MIN is NOT the diurnal
         range: POWER monthly MAX/MIN are the month's extreme values.
    """
    if var == "VPD":
        mm = fetch_monthly_multi(lat, lon, ["T2M", "RH2M"], start, end)
        series = []
        for year in _complete_years(mm, ["T2M", "RH2M"]):
            vpd = []
            for m in range(1, 13):
                T  = mm["T2M"][year][m]
                RH = mm["RH2M"][year][m]
                es = 0.6108 * math.exp(17.27 * T / (T + 237.3))
                vpd.append(es * (1.0 - RH / 100.0))
            series.append((year, float(np.mean(vpd))))
        return series
    if var == "DTR":
        mm = fetch_monthly_multi(lat, lon, ["T2M_RANGE"], start, end)
        return [(y, float(np.mean(list(mm["T2M_RANGE"][y].values()))))
                for y in _complete_years(mm, ["T2M_RANGE"])]
    raise ValueError(f"unknown compound variable: {var}")
