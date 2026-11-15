"""
Annual-series construction on synthetic monthly data with a strong seasonal
cycle and a known trend. Run: python python/tests/test_annual_series.py
(also collected by pytest).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fetch import contiguous_run, monthly_to_annual, monthly_to_annual_min  # noqa: E402
from stats import mk_verdict  # noqa: E402

TRUE_SLOPE = 0.03          # units per year
Y0, Y1 = 1981, 2025


def make_monthly(noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    out = {}
    for y in range(Y0, Y1 + 1):
        out[y] = {}
        for m in range(1, 13):
            season = 10.0 * np.sin(2 * np.pi * (m - 4) / 12) + 3.0 * np.cos(4 * np.pi * m / 12)
            out[y][m] = 15.0 + season + TRUE_SLOPE * (y - Y0 + (m - 1) / 12) + rng.normal(0, noise)
    return out


def delete_months(mon, rule):
    return {y: {m: v for m, v in ms.items() if not rule(y, m)} for y, ms in mon.items()}


def delete_years(mon, years):
    return {y: ms for y, ms in mon.items() if y not in years}


SCENARIOS = {
    "full": lambda mon: mon,
    # winter months lost in the later half, summer months lost in the earlier half
    "months_seasonal": lambda mon: delete_months(
        mon, lambda y, m: (y > 2005 and m in (12, 1, 2, 3)) or (y < 1995 and m in (6, 7, 8))),
    # different random-looking months lost in different years
    "months_scattered": lambda mon: delete_months(
        mon, lambda y, m: (y * 7 + m * 3) % 11 in (0, 1)),
    # current year partial (Jan-Aug) plus first year starting in February
    "partial_edges": lambda mon: delete_months(
        mon, lambda y, m: (y == Y1 and m > 8) or (y == Y0 and m == 1)),
    # whole years missing in the middle
    "years_missing": lambda mon: delete_years(mon, {1999, 2000, 2012}),
    "everything": lambda mon: delete_years(delete_months(
        mon, lambda y, m: (y > 2005 and m in (12, 1, 2)) or (y == Y1 and m > 6)
        or (y * 7 + m * 3) % 11 == 0), {1990, 2011}),
}


def naive_series(mon, min_months):
    """The old behaviour: plain mean of whichever months exist, gaps kept."""
    return [(y, float(np.mean(list(ms.values())))) for y, ms in sorted(mon.items())
            if len(ms) >= min_months]


def sen_per_year(annual):
    years = np.array([y for y, _ in annual], dtype=float)
    vals = np.array([v for _, v in annual], dtype=float)
    return mk_verdict(vals, method="hr")["slope"], years


def old_slope(annual):
    """Old pipeline: slope per array index, whatever the years are."""
    return sen_per_year(annual)[0]


def new_slope(mon, min_months):
    run, _ = contiguous_run(monthly_to_annual_min(mon, min_months))
    years = [y for y, _ in run]
    assert all(b - a == 1 for a, b in zip(years, years[1:])), "gap survived"
    return sen_per_year(run)[0], len(run), years


def test_gap_free_unchanged():
    mon = make_monthly(noise=0.4, seed=1)
    plain = [(y, float(np.mean(list(ms.values())))) for y, ms in sorted(mon.items())]
    assert monthly_to_annual(mon) == plain


def test_contiguous_run():
    ann = [(y, 0.0) for y in (1, 2, 3, 5, 6, 7, 8, 10)]
    run, dropped = contiguous_run(ann)
    assert [y for y, _ in run] == [5, 6, 7, 8] and dropped == [1, 2, 3, 10]


def test_recovers_known_slope_noise_free():
    for name, f in SCENARIOS.items():
        s, _, _ = new_slope(f(make_monthly()), 9)
        assert abs(s - TRUE_SLOPE) < 1e-9, (name, s)


def test_recovers_known_slope_noisy():
    for name, f in SCENARIOS.items():
        s = np.mean([new_slope(f(make_monthly(0.4, seed)), 9)[0] for seed in range(20)])
        assert abs(s - TRUE_SLOPE) < 0.004, (name, s)


if __name__ == "__main__":
    print(f"true slope {TRUE_SLOPE}/yr; Sen slope per calendar year")
    print(f"{'scenario':18} {'old(noise-free)':>16} {'new(noise-free)':>16} {'n_yr':>5} "
          f"{'old(noisy,20 seeds)':>20} {'new(noisy,20 seeds)':>20}")
    for name, f in SCENARIOS.items():
        clean = f(make_monthly())
        o = old_slope(naive_series(clean, 6))
        n, ny, _ = new_slope(clean, 9)
        o_n = np.mean([old_slope(naive_series(f(make_monthly(0.4, s)), 6)) for s in range(20)])
        n_n = np.mean([new_slope(f(make_monthly(0.4, s)), 9)[0] for s in range(20)])
        print(f"{name:18} {o:16.5f} {n:16.5f} {ny:5d} {o_n:20.5f} {n_n:20.5f}")
