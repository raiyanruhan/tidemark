"""
fetch_modis.py - NASA MODIS NDVI via ORNL DAAC MODIS Web Service.

Product: MOD13Q1, MODIS Terra 250m 16-day NDVI, 2000-present.
No authentication required. Freely available NASA satellite data.

First fetch for a location caches to disk (~/.tidemark/cache/).
Subsequent fetches use cache and are instant.

ORNL DAAC throughput: each request takes ~20s. max_workers=2 trades speed
for reliability (concurrent requests cause server-side data drops).
Default first fetch is capped at MAX_FIRST_FETCH_YEARS (10) to stay inside
the 300s CLI timeout. Use --years to extend and re-run.

Cite: Didan, K. (2015). MOD13Q1 MODIS/Terra Vegetation Indices 16-Day L3
      Global 250m SIN Grid V006. NASA EOSDIS Land Processes DAAC.
      https://doi.org/10.5067/MODIS/MOD13Q1.006
Data: https://modis.ornl.gov/rst/api/v1/
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import numpy as np
import requests

ORNL_URL       = "https://modis.ornl.gov/rst/api/v1"
NDVI_PRODUCT   = "MOD13Q1"
NDVI_BAND      = "250m_16_days_NDVI"
NDVI_SCALE     = 0.0001
NDVI_VALID_MIN = -2000  # pre-scale; fill value is -3000, outside this range
NDVI_VALID_MAX = 10000

# MOD13Q1 pixel reliability (rank): 0 good, 1 marginal, 2 snow/ice, 3 cloudy,
# -1 fill. Cloudy pixels still carry valid-range NDVI, so NDVI alone cannot
# identify them; the reliability band must be used. Keep good + marginal only.
RELIABILITY_BAND  = "250m_16_days_pixel_reliability"
RELIABILITY_KEEP  = (0, 1)

# Counts from the most recent uncached fetch (composites seen / kept / dropped).
LAST_FETCH_STATS = {}

# MODIS Terra first granule: February 2000
MODIS_EPOCH = 2000

# ORNL DAAC limits to ~10 granules per request; MOD13Q1 is 16-day composites.
# 159 days ends before day 161 (the 11th composite), so max 10 granules.
CHUNK_DAYS = 159

# Cap uncached fetches at this many years to stay inside the 300s CLI timeout.
# 10 years = 23 chunks, max_workers=2: ~252s. Use --years to extend and re-run.
MAX_FIRST_FETCH_YEARS = 10


def _cache_path(lat, lon, start_year, end_year):
    """Path for cached NDVI JSON under ~/.tidemark/cache/."""
    cache_dir = os.path.join(os.path.expanduser("~"), ".tidemark", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    fname = f"ndvi_qa_{lat:.4f}_{lon:.4f}_{start_year}_{end_year}.json"
    return os.path.join(cache_dir, fname)


def _date_chunks(start_year, end_year):
    """
    (start_str, end_str) pairs in ORNL DAAC "AYYDDDD" format,
    covering start_year-01-01 to end_year-12-31 in CHUNK_DAYS increments.
    """
    start  = date(start_year, 1, 1)
    end    = date(end_year, 12, 31)
    chunks = []
    cur    = start
    while cur <= end:
        stop = min(cur + timedelta(days=CHUNK_DAYS - 1), end)
        s    = f"A{cur.year}{cur.timetuple().tm_yday:03d}"
        e    = f"A{stop.year}{stop.timetuple().tm_yday:03d}"
        chunks.append((s, e))
        cur = stop + timedelta(days=1)
    return chunks


def _fetch_chunk(session, lat, lon, start_str, end_str):
    """
    Fetch one ORNL DAAC chunk. Returns list of subset records, [] on failure.
    Empty response is valid (no data for that period); do not retry.
    """
    try:
        resp = session.get(
            f"{ORNL_URL}/{NDVI_PRODUCT}/subset",
            params={
                "latitude":     lat,
                "longitude":    lon,
                "startDate":    start_str,
                "endDate":      end_str,
                "kmAboveBelow": 0,
                "kmLeftRight":  0,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("subset", [])
    except Exception:
        return []


def fetch_ndvi_monthly(lat, lon, start_year, end_year, progress=None):
    """
    {year: {month: ndvi}} using MODIS MOD13Q1 16-day composites.
    start_year clamped to MODIS_EPOCH (2000). Returns {} on total failure.
    Multiple 16-day composites falling in the same calendar month are averaged.
    NDVI = raw_int * 0.0001; valid range -0.2 to 1.0.
    Composites are kept only when the pixel reliability band is 0 (good) or
    1 (marginal). Cloudy (3) and snow/ice (2) composites carry valid-range NDVI
    and are excluded via that band, not via a fill value. Years with too few
    valid months are dropped downstream (fetch.satellite_annual: 9, relaxed to
    6 then 4 if fewer than 10 years qualify).

    First fetch for a (lat, lon, start, end) combination is cached to
    ~/.tidemark/cache/. All subsequent calls load from disk instantly.
    """
    effective_start = max(int(start_year), MODIS_EPOCH)
    end_year_int    = int(end_year)

    # Cap first (uncached) fetch to MAX_FIRST_FETCH_YEARS to stay inside timeout.
    capped_start = max(effective_start, end_year_int - MAX_FIRST_FETCH_YEARS + 1)
    cache = _cache_path(lat, lon, capped_start, end_year_int)

    if os.path.exists(cache):
        with open(cache) as f:
            # JSON keys are strings; convert back to int for year and month.
            raw = json.load(f)
            return {int(yr): {int(mo): v for mo, v in months.items()}
                    for yr, months in raw.items()}

    chunks = _date_chunks(capped_start, end_year_int)
    all_records = []
    total = len(chunks)
    done  = 0
    # max_workers=2: reliable at ORNL DAAC throughput; higher values cause drops.
    with requests.Session() as session, ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(_fetch_chunk, session, lat, lon, s, e): (s, e)
            for s, e in chunks
        }
        failed = []
        for future in as_completed(futures):
            records = future.result()
            done += 1
            if progress:
                progress(f"Downloading vegetation data: {done} of {total}")
            if records:
                all_records.extend(records)
            else:
                failed.append(futures[future])   # (start_str, end_str)

    # Serial retry for chunks that returned nothing -- handles transient ORNL drops.
    if failed:
        with requests.Session() as session:
            for s, e in failed:
                all_records.extend(_fetch_chunk(session, lat, lon, s, e))

    # The subset API returns every band for each date (no band filter is sent),
    # so reliability arrives in the same response. Index it by calendar date.
    reliability = {}
    for rec in all_records:
        if rec.get("band") != RELIABILITY_BAND:
            continue
        try:
            reliability[rec.get("calendar_date", "")] = int(rec["data"][0])
        except (KeyError, IndexError, ValueError, TypeError):
            continue

    # group valid composites into (year, month) buckets
    buckets = {}
    n_seen = n_dropped = 0
    for rec in all_records:
        if rec.get("band") != NDVI_BAND:
            continue
        raw_list = rec.get("data", [])
        if not raw_list:
            continue
        try:
            raw = int(raw_list[0])
        except (ValueError, TypeError):
            continue
        if raw < NDVI_VALID_MIN or raw > NDVI_VALID_MAX:
            continue

        cal = rec.get("calendar_date", "")
        n_seen += 1
        # missing reliability = unknown quality: drop
        if reliability.get(cal) not in RELIABILITY_KEEP:
            n_dropped += 1
            continue
        try:
            year, month = int(cal[:4]), int(cal[5:7])
        except (ValueError, IndexError):
            continue

        buckets.setdefault((year, month), []).append(raw * NDVI_SCALE)

    LAST_FETCH_STATS.update(seen=n_seen, dropped=n_dropped, kept=n_seen - n_dropped)

    # average composites within each month
    by_year = {}
    for (year, month), vals in buckets.items():
        by_year.setdefault(year, {})[month] = float(np.mean(vals))

    # cache to disk (key already set from capped_start above); JSON needs string keys
    try:
        str_keyed = {str(yr): {str(mo): v for mo, v in months.items()}
                     for yr, months in by_year.items()}
        with open(cache, "w") as f:
            json.dump(str_keyed, f)
    except Exception:
        pass  # cache write failure is non-fatal

    return by_year
