"""
seasonal.py, seasonal breakdown via Hamed-Rao Mann-Kendall on quarterly means.
DJF/MAM/JJA/SON use calendar-year grouping (DJF = Dec/Jan/Feb of same year).
"""
import numpy as np
import pymannkendall as mk

SEASONS = [
    ("DJF", [12, 1, 2]),
    ("MAM", [3, 4, 5]),
    ("JJA", [6, 7, 8]),
    ("SON", [9, 10, 11]),
]


def monthly_to_seasonal(monthly_by_year):
    """
    {season: [(year, mean)]} for DJF/MAM/JJA/SON.
    Year dropped if any of the 3 months is missing.
    """
    result = {}
    for name, months in SEASONS:
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
