"""
fetch_laads.py - NASA LAADS DAAC MOD08_M3 monthly AOD via CMR + OPeNDAP ASCII.

Product: MOD08_M3 V6.1 — MODIS Terra Monthly 1-degree gridded atmosphere product.
Variable: Aerosol_Optical_Depth_Land_Ocean_Mean (550nm), scale=0.001, fill>32000.
Grid: 180 lat x 360 lon at 1-degree resolution, lat_i=0 at 90N (north-first), lon_i=0 at 180W.
Coverage: 2002-present (Terra MODIS; first granule February 2000 but V6.1 monthly
          aggregates reliably start 2002).

Authentication: same NASA Earthdata credentials as GPM IMERG.
  NASA_EARTHDATA_USERNAME
  NASA_EARTHDATA_PASSWORD
Authorize "NASA LARC ASDC" at urs.earthdata.nasa.gov before first use.

No new dependencies — CMR returns JSON, OPeNDAP returns ASCII plain text.
First fetch for a location caches to ~/.tidemark/cache/.

CMR: https://cmr.earthdata.nasa.gov/search/granules.json
OPeNDAP: https://opendap.larc.nasa.gov/opendap/MOTA/MOD08_M3.061/

Cite: Platnick, S., et al. (2015). MODIS Atmosphere L3 Monthly Product (MOD08_M3).
      NASA MODIS Adaptive Processing System, Goddard Space Flight Center.
      doi:10.5067/MODIS/MOD08_M3.061
"""
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.auth import HTTPBasicAuth

CMR_URL       = "https://cmr.earthdata.nasa.gov/search/granules.json"
OPENDAP_BASE  = "https://opendap.larc.nasa.gov/opendap/MOTA/MOD08_M3.061"
AOD_VAR       = "Aerosol_Optical_Depth_Land_Ocean_Mean"
AOD_SCALE     = 0.001
AOD_FILL_MIN  = 32000   # raw int16 fill = 32767; anything above this is fill/missing
AOD_EPOCH     = 2002


def _lat_idx(lat):
    """1-degree grid, north-first: row 0 centred 89.5N, row 179 centred 89.5S."""
    return min(179, max(0, int(math.floor(90.0 - lat))))


def _lon_idx(lon):
    """1-degree grid: col 0 centred 179.5W, col 359 centred 179.5E."""
    return min(359, max(0, int(math.floor(lon + 180.0))))


def _earthdata_token(username, password):
    """Reuse or create a short-lived Earthdata URS Bearer token."""
    headers = {"Accept": "application/json"}
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
    resp2 = requests.post(
        "https://urs.earthdata.nasa.gov/api/users/token",
        auth=HTTPBasicAuth(username, password),
        headers=headers,
        timeout=15,
    )
    resp2.raise_for_status()
    return resp2.json()["access_token"]


def _cmr_opendap_urls(start_year, end_year):
    """
    Query NASA CMR for all MOD08_M3 V6.1 granules in [start_year, end_year].
    Returns {(year, month): opendap_url_str} for every granule found.

    CMR page_size=500 covers 2002-2025 (276 months) in one request.
    Granule temporal_start is the first day of the month (e.g. 2002-01-01).
    OPeNDAP URL is in related_urls where type == "USE SERVICE API" and
    subtype contains "OPENDAP".
    """
    params = {
        "short_name":   "MOD08_M3",
        "version":      "061",
        "temporal":     f"{start_year}-01-01T00:00:00Z,{end_year}-12-31T23:59:59Z",
        "page_size":    500,
        "page_num":     1,
    }
    try:
        resp = requests.get(CMR_URL, params=params, timeout=30)
        resp.raise_for_status()
        entries = resp.json().get("feed", {}).get("entry", [])
    except Exception:
        return {}

    result = {}
    for entry in entries:
        # temporal_start: "2002-01-01T00:00:00.000Z"
        t = entry.get("time_start", "")
        try:
            year  = int(t[:4])
            month = int(t[5:7])
        except (ValueError, IndexError):
            continue

        for link in entry.get("links", []):
            href  = link.get("href", "")
            title = link.get("title", "").lower()
            rel   = link.get("rel", "")
            if ("opendap" in href.lower() or "opendap" in title) and href.endswith(".hdf"):
                result[(year, month)] = href
                break
        else:
            # fallback: use granule_ur to build OPeNDAP URL directly
            # granule_ur: MOD08_M3.A2002001.061.2015210193103.hdf
            ur = entry.get("title", "")
            if ur.endswith(".hdf") and "MOD08_M3" in ur:
                # date folder from time_start: "2002.01.01"
                folder = t[:10].replace("-", ".")
                result[(year, month)] = f"{OPENDAP_BASE}/{folder}/{ur}"

    return result


def _aod_ascii_url(opendap_url, lat_i, lon_i):
    """
    OPeNDAP DAP2 ASCII constraint for a single 1-degree pixel.
    MOD08_M3 HDF4 DDS: Aerosol_Optical_Depth_Land_Ocean_Mean[lat][lon]
    Dimension order: lat (0=90N) x lon (0=180W).
    """
    constraint = f"{AOD_VAR}[{lat_i}:{lat_i}][{lon_i}:{lon_i}]"
    return f"{opendap_url}.ascii?{constraint}"


def _parse_aod_ascii(text):
    """
    Extract AOD raw int from OPeNDAP ASCII response and apply scale.

    Hyrax response format:
      Dataset { ... } filename;
      ----------------------------------------
      Aerosol_Optical_Depth_Land_Ocean_Mean
      [0][0], <int_value>

    Returns float (AOD unitless) or None for fill/cloud/parse failure.
    """
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[0][0],"):
            try:
                raw = float(line.split(",", 1)[1].strip())
                if raw > AOD_FILL_MIN or raw < -100:
                    return None
                return raw * AOD_SCALE
            except ValueError:
                pass
        # alternate: "Aerosol_Optical_Depth_Land_Ocean_Mean\n[0][0], val"
        # handled by next iteration
    # broader fallback: any line with [0][0]
    for line in text.splitlines():
        line = line.strip()
        if "[0][0]" in line and "," in line:
            try:
                raw = float(line.rsplit(",", 1)[-1].strip())
                if raw > AOD_FILL_MIN or raw < -100:
                    return None
                return raw * AOD_SCALE
            except ValueError:
                pass
    return None


def _fetch_one_month(token, opendap_url, lat_i, lon_i):
    """
    Fetch AOD for one month via OPeNDAP ASCII. Returns float or None.
    Brackets in OPeNDAP constraint must NOT be URL-encoded; set prep.url directly.
    """
    raw_url = _aod_ascii_url(opendap_url, lat_i, lon_i)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        req  = requests.Request("GET", "http://placeholder", headers=headers)
        prep = req.prepare()
        prep.url = raw_url
        with requests.Session() as s:
            resp = s.send(prep, timeout=30)
        if resp.status_code in (404, 403):
            return None
        resp.raise_for_status()
        return _parse_aod_ascii(resp.text)
    except Exception:
        return None


def _cache_path(lat, lon, start_year, end_year):
    cache_dir = os.path.join(os.path.expanduser("~"), ".tidemark", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(
        cache_dir, f"aod2_{lat:.4f}_{lon:.4f}_{start_year}_{end_year}.json"
    )


def fetch_aod_monthly(lat, lon, start_year, end_year, progress=None):
    """
    {year: {month: aod_unitless}} using MODIS MOD08_M3 V6.1 monthly AOD.
    start_year clamped to AOD_EPOCH (2002). Returns {} on total failure.

    Requires NASA_EARTHDATA_USERNAME and NASA_EARTHDATA_PASSWORD env vars.
    Authorize "NASA LARC ASDC" at urs.earthdata.nasa.gov before first use.
    First fetch cached to ~/.tidemark/cache/; subsequent calls are instant.

    Cloud-contaminated months return None (AOD fill); years with <6 valid months
    are dropped downstream by monthly_to_annual_min.
    """
    effective_start = max(int(start_year), AOD_EPOCH)
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
            "NASA_EARTHDATA_USERNAME and NASA_EARTHDATA_PASSWORD must be set "
            "for MODIS AOD data. Authorize 'NASA LARC ASDC' at urs.earthdata.nasa.gov."
        )

    if progress:
        progress("querying CMR for MOD08_M3 granule catalog...")

    granule_urls = _cmr_opendap_urls(effective_start, end_year_int)
    if not granule_urls:
        raise RuntimeError("CMR returned no MOD08_M3 granules for the requested period")

    token = _earthdata_token(username, password)
    lat_i = _lat_idx(lat)
    lon_i = _lon_idx(lon)

    total = len(granule_urls)
    done  = [0]
    by_year = {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        future_to_key = {
            pool.submit(_fetch_one_month, token, url, lat_i, lon_i): (yr, mo)
            for (yr, mo), url in sorted(granule_urls.items())
        }
        for future in as_completed(future_to_key):
            yr, mo = future_to_key[future]
            done[0] += 1
            if progress:
                progress(f"downloading aerosol data: {done[0]} of {total}")
            val = future.result()
            if val is not None:
                by_year.setdefault(yr, {})[mo] = val

    try:
        str_keyed = {str(yr): {str(mo): v for mo, v in months.items()}
                     for yr, months in by_year.items()}
        with open(cache, "w") as f:
            json.dump(str_keyed, f)
    except Exception:
        pass

    return by_year
