"""
fetch_appeears.py - NASA AppEEARS API for MODIS satellite products.

Products:
  LST      MOD11A2.061  Land Surface Temperature (8-day, 1km), 2001-present
  ET_MOD16 MOD16A2.061  Actual Evapotranspiration (8-day, 500m), 2001-present

Authentication: NASA Earthdata Login. Set environment variables:
  NASA_EARTHDATA_USERNAME
  NASA_EARTHDATA_PASSWORD

Authorize "AppEEARS" at urs.earthdata.nasa.gov before first use.

AppEEARS is an async task API: submit -> poll -> download CSV. First fetch for
a (location, product) pair takes 1-5 minutes. Result cached to disk after.
Subsequent fetches are instant from ~/.tidemark/cache/.

Cite: Wan, Z., Hook, S., Hulley, G. (2021). MODIS/Terra Land Surface Temp.
      MOD11A2 V061. NASA EOSDIS LPDAAC. doi:10.5067/MODIS/MOD11A2.061
      Running, S., Mu, Q., Zhao, M., Moreno, A. (2021). MOD16A2 V061.
      NASA EOSDIS LPDAAC. doi:10.5067/MODIS/MOD16A2.061
Data: https://appeears.earthdatacloud.nasa.gov/
"""
import csv
import datetime
import io
import json
import os
import time

import numpy as np
import requests
from requests.auth import HTTPBasicAuth

APPEEARS_BASE = "https://appeears.earthdatacloud.nasa.gov/api"
MODIS_EPOCH   = 2001

# AppEEARS applies scale factors before returning values.
# LST: returns Kelvin (raw DN * 0.02). Fill raw=0 -> 0.0 K.
# ET:  returns mm per composite (raw DN * 0.1; sum over 8 days, 5/6 for the
#      last composite of a year). Fill raw=32767 -> 3276.7.
_PRODUCTS = {
    "LST": {
        "product":     "MOD11A2.061",
        "layer":       "LST_Day_1km",
        "fill_above":  400.0,   # > 400 K = > 127 C: impossible Earth surface
        "fill_below":  100.0,   # < 100 K: impossible Earth surface
        "offset":      -273.15, # Kelvin to Celsius
        "unit_factor": 1.0,
    },
    "ET_MOD16": {
        "product":     "MOD16A2.061",
        "layer":       "ET_500m",
        "fill_above":  3000.0,  # raw 32767 * 0.1 = 3276.7; flag fill
        "fill_below":  -50.0,   # negative ET is rare but possible (condensation)
        "offset":      0.0,
        "unit_factor": 1.0,
        # ET is a SUM over the composite period (MOD16 User Guide V6.1). The
        # last composite of each year (DOY 361) spans only 5 days (6 in leap
        # years), so divide by the true composite length, not a fixed 8.
        "per_composite_day": True,
    },
}


def _appeears_token(username, password):
    """
    Get AppEEARS Bearer token via Basic auth.
    Token is valid for 48 hours.
    """
    resp = requests.post(
        f"{APPEEARS_BASE}/login",
        auth=HTTPBasicAuth(username, password),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def _submit_task(token, lat, lon, product, layer, start_year, end_year):
    """
    Submit an AppEEARS point extraction task for a single coordinate.
    Returns task_id string.
    """
    task_name = f"tidemark_{product.replace('.', '_')}_{abs(lat):.2f}_{abs(lon):.2f}"
    payload = {
        "task_type": "point",
        "task_name": task_name,
        "params": {
            "dates": [{
                "startDate": f"01-01-{start_year}",
                "endDate":   f"12-31-{end_year}",
            }],
            "layers": [{"product": product, "layer": layer}],
            "coordinates": [{
                "id":        "0",
                "latitude":  lat,
                "longitude": lon,
                "category":  "",
            }],
        },
    }
    resp = requests.post(
        f"{APPEEARS_BASE}/task",
        headers={
            "Authorization":  f"Bearer {token}",
            "Content-Type":   "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["task_id"]


def _poll_task(token, task_id, timeout=600, progress=None):
    """
    Poll until task status is 'done' or timeout expires.
    Returns True on success, False on error or timeout.
    AppEEARS single-point tasks typically complete in 1-3 minutes.
    """
    headers  = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + timeout
    delay    = 10
    start    = time.time()
    while time.time() < deadline:
        time.sleep(delay)
        resp = requests.get(
            f"{APPEEARS_BASE}/task/{task_id}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        status = resp.json().get("status", "")
        if progress:
            elapsed = int(time.time() - start)
            progress(f"NASA satellite data: processing... ({elapsed}s)")
        if status == "done":
            return True
        if status in ("error", "deleted"):
            return False
        # exponential backoff capped at 30s between polls
        delay = min(delay * 1.5, 30)
    return False


def _download_csv(token, task_id):
    """
    Download the main data CSV from an AppEEARS task bundle.
    Returns CSV text or None if no data file is found.
    Skips QC files and statistics summaries.
    """
    headers     = {"Authorization": f"Bearer {token}"}
    bundle_resp = requests.get(
        f"{APPEEARS_BASE}/bundle/{task_id}",
        headers=headers,
        timeout=15,
    )
    bundle_resp.raise_for_status()
    files = bundle_resp.json().get("files", [])

    data_file = None
    for f in files:
        name = f.get("file_name", "")
        if name.endswith(".csv") and "-QC" not in name and "Statistics" not in name:
            data_file = f
            break
    if not data_file:
        return None

    file_id = data_file["file_id"]
    dl_resp = requests.get(
        f"{APPEEARS_BASE}/bundle/{task_id}/{file_id}",
        headers=headers,
        timeout=60,
    )
    dl_resp.raise_for_status()
    return dl_resp.text


def _composite_days(year, doy):
    """Length in days of the 8-day composite starting at day-of-year doy.
    The last composite of a year is truncated at Dec 31 (5 days, 6 in leap years)."""
    days_in_year = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
    return min(8, days_in_year - doy + 1)


def _parse_csv_to_monthly(csv_text, product, layer, fill_above, fill_below,
                           offset, unit_factor, per_composite_day=False):
    """
    Parse AppEEARS point CSV into {year: {month: physical_value}}.

    AppEEARS column name is '{product_no_dots}_{layer}' (no _0 suffix).
    Multiple 8-day composites per calendar month are averaged.
    Scale factor already applied by AppEEARS; values are physical units.
    per_composite_day: value is a sum over the composite; convert to per-day by
    dividing by the actual composite length (5/6 days for the year's last one).
    """
    prod_safe = product.replace(".", "_")
    # try variants: with and without _0 suffix, with and without dot replacement
    candidates = [
        f"{prod_safe}_{layer}",
        f"{prod_safe}_{layer}_0",
        f"{product}_{layer}",
        f"{product}_{layer}_0",
    ]

    buckets = {}
    reader  = csv.DictReader(io.StringIO(csv_text))
    # pick the first candidate that exists as a header
    fieldnames = reader.fieldnames or []
    val_col = None
    for c in candidates:
        if c in fieldnames:
            val_col = c
            break
    if val_col is None:
        return {}

    for row in reader:
        date_str = row.get("Date", "").strip()
        raw_str  = row.get(val_col, "").strip()
        if not date_str or not raw_str:
            continue

        try:
            # AppEEARS uses YYYY-MM-DD
            if len(date_str) == 10 and date_str[4] == "-":
                dt    = datetime.date(int(date_str[:4]), int(date_str[5:7]),
                                      int(date_str[8:10]))
                year, month = dt.year, dt.month
                doy   = dt.timetuple().tm_yday
            # fallback: YYYYDDD Julian
            elif len(date_str) == 7:
                dt    = datetime.datetime.strptime(date_str, "%Y%j")
                year  = dt.year
                month = dt.month
                doy   = dt.timetuple().tm_yday
            else:
                continue
        except (ValueError, IndexError):
            continue

        try:
            val = float(raw_str)
        except ValueError:
            continue

        if val >= fill_above or val <= fill_below:
            continue

        if per_composite_day:
            physical = val / _composite_days(year, doy) * unit_factor + offset
        else:
            physical = val * unit_factor + offset
        buckets.setdefault((year, month), []).append(physical)

    by_year = {}
    for (year, month), vals in buckets.items():
        by_year.setdefault(year, {})[month] = float(np.mean(vals))

    return by_year


def _cache_dir():
    d = os.path.join(os.path.expanduser("~"), ".tidemark", "cache")
    os.makedirs(d, exist_ok=True)
    return d


def _cache_path(lat, lon, product, start_year, end_year):
    safe = product.replace(".", "_")
    return os.path.join(
        _cache_dir(),
        f"appeears_{safe}_{lat:.4f}_{lon:.4f}_{start_year}_{end_year}.json",
    )


def _task_id_cache_path(lat, lon, product, start_year, end_year):
    # stores the submitted task_id so a restarted process can resume polling
    safe = product.replace(".", "_")
    return os.path.join(
        _cache_dir(),
        f"appeears_task_{safe}_{lat:.4f}_{lon:.4f}_{start_year}_{end_year}.txt",
    )


def _task_status(token, task_id):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{APPEEARS_BASE}/task/{task_id}", headers=headers, timeout=15)
    if resp.status_code == 404:
        return "not_found"
    resp.raise_for_status()
    return resp.json().get("status", "unknown")


def fetch_appeears_monthly(lat, lon, var_key, start_year, end_year, progress=None):
    """
    {year: {month: physical_value}} for an AppEEARS MODIS product.
    var_key: 'LST' (land surface temperature, deg C) or 'ET_MOD16' (mm/day).
    start_year clamped to MODIS_EPOCH (2001). Returns {} on total failure.

    First call submits an async task (can take 2-10+ min depending on queue).
    Persistent task-id cache: if polled out in one run, re-run picks up same
    task instead of submitting a duplicate. Result cached after download.

    Requires NASA_EARTHDATA_USERNAME and NASA_EARTHDATA_PASSWORD env vars.
    """
    if var_key not in _PRODUCTS:
        raise ValueError(f"unknown AppEEARS variable: {var_key}")

    cfg             = _PRODUCTS[var_key]
    effective_start = max(int(start_year), MODIS_EPOCH)
    end_year_int    = int(end_year)

    # check finished result cache first
    result_cache = _cache_path(lat, lon, cfg["product"], effective_start, end_year_int)
    if os.path.exists(result_cache):
        with open(result_cache) as f:
            raw = json.load(f)
            return {int(yr): {int(mo): v for mo, v in months.items()}
                    for yr, months in raw.items()}

    username = os.environ.get("NASA_EARTHDATA_USERNAME", "")
    password = os.environ.get("NASA_EARTHDATA_PASSWORD", "")
    if not username or not password:
        raise RuntimeError(
            "NASA_EARTHDATA_USERNAME and NASA_EARTHDATA_PASSWORD must be set for AppEEARS data"
        )

    token = _appeears_token(username, password)

    # resume a previously submitted task if one exists
    task_cache = _task_id_cache_path(lat, lon, cfg["product"], effective_start, end_year_int)
    task_id    = None
    if os.path.exists(task_cache):
        with open(task_cache) as f:
            task_id = f.read().strip()
        status = _task_status(token, task_id)
        if status in ("error", "not_found", "deleted"):
            # stale task; submit fresh
            os.remove(task_cache)
            task_id = None
        elif status == "done":
            pass  # fall through to download
        # else: pending or processing; fall through to poll

    if task_id is None:
        task_id = _submit_task(
            token, lat, lon,
            cfg["product"], cfg["layer"],
            effective_start, end_year_int,
        )
        try:
            with open(task_cache, "w") as f:
                f.write(task_id)
        except Exception:
            pass

    if progress:
        progress("NASA satellite data: queued, waiting for processing...")
    if not _poll_task(token, task_id, timeout=600, progress=progress):
        # still not done: tell caller to retry
        raise RuntimeError(
            f"AppEEARS task {task_id} not done after 600s (status=pending/processing). "
            "Run the command again in a few minutes to resume."
        )

    csv_text = _download_csv(token, task_id)
    if not csv_text:
        return {}

    by_year = _parse_csv_to_monthly(
        csv_text,
        product=cfg["product"],
        layer=cfg["layer"],
        fill_above=cfg["fill_above"],
        fill_below=cfg["fill_below"],
        offset=cfg["offset"],
        unit_factor=cfg["unit_factor"],
        per_composite_day=cfg.get("per_composite_day", False),
    )

    # save result cache and clean up task-id cache
    try:
        str_keyed = {str(yr): {str(mo): v for mo, v in months.items()}
                     for yr, months in by_year.items()}
        with open(result_cache, "w") as f:
            json.dump(str_keyed, f)
        if os.path.exists(task_cache):
            os.remove(task_cache)
    except Exception:
        pass

    return by_year
