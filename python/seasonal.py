"""
seasonal.py, seasonal breakdown via Hamed-Rao Mann-Kendall on quarterly means.
DJF: Dec of prior year + Jan/Feb of labelled year (standard meteorological convention).
MAM/JJA/SON: same-year grouping.
"""
import numpy as np
import pymannkendall as mk

from fetch import contiguous_run

_SAME_YEAR_SEASONS = [
    ("MAM", [3, 4, 5]),
    ("JJA", [6, 7, 8]),
    ("SON", [9, 10, 11]),
]


def monthly_to_seasonal(monthly_by_year):
    """
    {season: [(year, mean)]} for DJF/MAM/JJA/SON.
    Year dropped if any of the 3 months is missing.
    DJF year Y = Dec[Y-1] + Jan[Y] + Feb[Y].
    """
    result = {}

    # DJF: standard meteorological convention
    djf_series = []
    for year in sorted(monthly_by_year):
        prev = monthly_by_year.get(year - 1, {})
        curr = monthly_by_year[year]
        if 12 in prev and 1 in curr and 2 in curr:
            djf_series.append((year, float(np.mean([prev[12], curr[1], curr[2]]))))
    result["DJF"] = djf_series

    # MAM, JJA, SON: same-calendar-year grouping
    for name, months in _SAME_YEAR_SEASONS:
        series = []
        for year in sorted(monthly_by_year):
            m = monthly_by_year[year]
            if all(mo in m for mo in months):
                series.append((year, float(np.mean([m[mo] for mo in months]))))
        result[name] = series

    return result


def run_seasonal_mk(monthly_by_year):
    seasonal_data = monthly_to_seasonal(monthly_by_year)
    results = {}
    for name, series in seasonal_data.items():
        series, _ = contiguous_run(series)   # Sen slope is per index = per year only without gaps
        if len(series) < 10:
            continue
        sv  = np.array([v for _, v in series])
        res = mk.hamed_rao_modification_test(sv, alpha=0.05, lag=3)
        results[name] = {
            "slope":       round(float(res.slope), 6),
            "p":           round(float(res.p), 4),
            "direction":   "upward" if res.slope >= 0 else "downward",
            "significant": bool(res.h),
        }
    return results
