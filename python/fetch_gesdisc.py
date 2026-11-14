"""
fetch_gesdisc.py - NASA GPM IMERG monthly precipitation via GES DISC OPeNDAP.

Product: GPM_3IMERGM V07B, 0.1-degree monthly precipitation, 2001-present.
Actual satellite precipitation measurement; 5x finer resolution than MERRA-2.

Authentication: NASA Earthdata Login. Set environment variables:
  NASA_EARTHDATA_USERNAME
  NASA_EARTHDATA_PASSWORD

Authorize "NASA GESDISC DATA ARCHIVE" at urs.earthdata.nasa.gov before first use.

First fetch for a location caches to ~/.tidemark/cache/.
Subsequent fetches load from cache and are instant.

Cite: Huffman, G.J., et al. (2019). GPM IMERG Final Precipitation L3 1 month
      0.1 degree x 0.1 degree V07. NASA/GSFC/EPS. Accessed via NASA GES DISC.
      doi:10.5067/GPM/IMERG/3B-MONTHLY/07
Data: https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGM_07/summary
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.auth import HTTPBasicAuth

GPM_BASE      = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGM.07"
GPM_EPOCH     = 2001
GPM_FILL      = -9999.9
# GPM IMERG monthly unit is mm/hr; convert to mm/day for consistency with POWER
GPM_HR_TO_DAY = 24.0

# 0.1-degree grid: lat -89.95 to 89.95, lon -179.95 to 179.95
_LAT_ORIGIN = -89.95
_LON_ORIGIN = -179.95
_GRID_RES   = 0.1


def _lat_idx(lat):
    return round((lat - _LAT_ORIGIN) / _GRID_RES)


def _lon_idx(lon):
    return round((lon - _LON_ORIGIN) / _GRID_RES)


def _earthdata_token(username, password):
    """
    Get a short-lived Earthdata Bearer token from URS.
    Reuses an existing token if one is available; creates one if not.
    """
    headers = {"Accept": "application/json"}
    # list existing tokens first
    resp = requests.get(
        "https://urs.earthdata.nasa.gov/api/users/tokens",
        auth=HTTPBasicAuth(username, password),
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    tokens = resp.json()
    if tokens:
        return tokens[0]["access_token"]
    # no existing token: create one
    resp2 = requests.post(
        "https://urs.earthdata.nasa.gov/api/users/token",
        auth=HTTPBasicAuth(username, password),
        headers=headers,
        timeout=15,
    )
    resp2.raise_for_status()
    return resp2.json()["access_token"]


def _gpm_ascii_url(year, month, lat_i, lon_i):
    """
    OPeNDAP DAP2 ASCII URL for a single GPM IMERG monthly file, constrained
    to one lat/lon cell.

    DDS dimension order is time x lon x lat (lon first, lat second).
    Variable name in DAP2 DDS is "precipitation" (no group prefix).
    Endpoint is .ascii, not .nc4.ascii (this is an HDF5 file, not netCDF4).
    """
    mm         = f"{month:02d}"
    fname      = f"3B-MO.MS.MRG.3IMERG.{year}{mm}01-S000000-E235959.{mm}.V07B.HDF5"
    constraint = f"precipitation[0:0][{lon_i}:{lon_i}][{lat_i}:{lat_i}]"
    return f"{GPM_BASE}/{year}/{fname}.ascii?{constraint}"


def _parse_ascii_float(text):
    """
    Extract the precipitation value from a GES DISC OPeNDAP DAP2 ASCII response.

    Hyrax returns a compact format for scalar subsets:
      Dataset: <filename>
      precipitation[0][0], <value>

    The value follows the last comma on the data line.
    Returns float or None on parse failure or fill value.
    """
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("precipitation[") and "," in line:
            try:
                val = float(line.rsplit(",", 1)[-1].strip())
                return None if val <= GPM_FILL + 1.0 else val
            except ValueError:
                pass
    return None


def _fetch_one_month(token, lat_i, lon_i, year, month):
    """
    Fetch precipitation (mm/hr) for one calendar month via OPeNDAP ASCII.
    Returns float in mm/day, or None on missing file or error.
    404 is expected for recent months not yet processed by NASA (3-month lag).

    Each call creates its own Session to avoid thread-safety issues when called
    concurrently. Brackets in OPeNDAP constraint expressions must NOT be
    URL-encoded; PreparedRequest.url is set directly to bypass requests encoding.
    """
    raw_url = _gpm_ascii_url(year, month, lat_i, lon_i)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        req  = requests.Request("GET", "http://placeholder", headers=headers)
        prep = req.prepare()
        prep.url = raw_url
        with requests.Session() as s:
            resp = s.send(prep, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        val = _parse_ascii_float(resp.text)
        if val is None:
            return None
        return val * GPM_HR_TO_DAY
    except Exception:
        return None


def _cache_path(lat, lon, start_year, end_year):
    cache_dir = os.path.join(os.path.expanduser("~"), ".tidemark", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(
        cache_dir, f"gpm_{lat:.4f}_{lon:.4f}_{start_year}_{end_year}.json"
    )


def fetch_precip_monthly(lat, lon, start_year, end_year):
    """
    {year: {month: mm/day}} using GPM IMERG satellite precipitation.
    start_year clamped to GPM_EPOCH (2001). Returns {} on total failure.

    Requires NASA_EARTHDATA_USERNAME and NASA_EARTHDATA_PASSWORD env vars.
    GPM data resolution is 0.1 degrees; MERRA-2 (POWER) is 0.5 degrees.
    First fetch cached to ~/.tidemark/cache/; subsequent calls are instant.
    """
    effective_start = max(int(start_year), GPM_EPOCH)
    end_year_int    = int(end_year)

    cache = _cache_path(lat, lon, effective_start, end_year_int)
    if os.path.exists(cache):
        with open(cache) as f:
            raw = json.load(f)
            return {int(yr): {int(mo): v for mo, v in months.items()}
                    for yr, months in raw.items()}

    username = os.environ.get("NASA_EARTHDATA_USERNAME", "")
    password = os.environ.get("NASA_EARTHDATA_PASSWORD", "")
    if not username or not password:
        raise RuntimeError(
            "NASA_EARTHDATA_USERNAME and NASA_EARTHDATA_PASSWORD must be set for GPM data"
        )

    token = _earthdata_token(username, password)
    lat_i = _lat_idx(lat)
    lon_i = _lon_idx(lon)

    pairs = [
        (y, m)
        for y in range(effective_start, end_year_int + 1)
        for m in range(1, 13)
    ]

    by_year = {}
    # max_workers=4: GES DISC rate-limits aggressive concurrency; 4 is reliable.
    with ThreadPoolExecutor(max_workers=4) as pool:
        future_to_ym = {
            pool.submit(_fetch_one_month, token, lat_i, lon_i, y, m): (y, m)
            for y, m in pairs
        }
        failed = []
        for future in as_completed(future_to_ym):
            year, month = future_to_ym[future]
            val = future.result()
            if val is not None:
                by_year.setdefault(year, {})[month] = val
            else:
                failed.append((year, month))

    # Serial retry for months that returned None -- handles transient rate-limit drops.
    for year, month in failed:
        val = _fetch_one_month(token, lat_i, lon_i, year, month)
        if val is not None:
            by_year.setdefault(year, {})[month] = val

    try:
        str_keyed = {str(yr): {str(mo): v for mo, v in months.items()}
                     for yr, months in by_year.items()}
        with open(cache, "w") as f:
            json.dump(str_keyed, f)
    except Exception:
        pass

    return by_year
