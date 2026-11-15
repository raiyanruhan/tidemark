"""
changepoint.py, structural-break test for trending series.

Pettitt (1979) tests "no change in location" and therefore rejects on any
monotonic trend, which is the normal case here. The test below asks the
question the output needs: is one straight line enough, or do two lines
(a shift in level and/or slope at some year) fit significantly better?
"""
import numpy as np

from stats import CP_MIN_SEG as MIN_SEG, ar1_null_series, line_residuals


def _line_rss(ct, ctt, cy, cyy, cty, m):
    """RSS of an OLS line from running sums over m points (broadcasts)."""
    sxx = ctt - ct * ct / m
    sxy = cty - ct * cy / m
    syy = cyy - cy * cy / m
    return np.maximum(syy - sxy * sxy / sxx, 0.0)


def _sup_f(Y):
    """
    sup-F statistic (one line vs two lines) for each row of Y.
    Returns (supF, argmax split k), k = first index of the second segment.
    """
    Y = np.atleast_2d(np.asarray(Y, dtype=float))
    n = Y.shape[1]
    t = np.arange(n, dtype=float)
    ks = np.arange(MIN_SEG, n - MIN_SEG + 1)

    ct, ctt = np.cumsum(t), np.cumsum(t * t)
    cy, cyy, cty = np.cumsum(Y, axis=1), np.cumsum(Y * Y, axis=1), np.cumsum(Y * t, axis=1)

    rss0 = _line_rss(ct[-1], ctt[-1], cy[:, -1], cyy[:, -1], cty[:, -1], n)

    i = ks - 1   # last index of the first segment
    left = _line_rss(ct[i], ctt[i], cy[:, i], cyy[:, i], cty[:, i], ks)
    right = _line_rss(
        ct[-1] - ct[i], ctt[-1] - ctt[i],
        cy[:, -1:] - cy[:, i], cyy[:, -1:] - cyy[:, i], cty[:, -1:] - cty[:, i], n - ks,
    )
    rss1 = np.maximum(left + right, 1e-300)
    f = ((rss0[:, None] - rss1) / 2.0) / (rss1 / (n - 4))
    j = np.argmax(f, axis=1)
    return f[np.arange(len(j)), j], ks[j]


def trend_break_test(vals, n_boot=1999, seed=42):
    """
    sup-F test of a single linear trend against a two-segment linear trend
    (Andrews 1993 statistic). The null distribution is bootstrapped from
    "one line + AR(1) noise" fitted to the data (stats.ar1_null_series), so
    the p-value is unaffected by the size of the trend and allows for
    year-to-year persistence, which otherwise looks like a break.
    Returns (detected, change_point_index, p_value); the index is the first
    observation of the new regime.
    """
    y = np.asarray(vals, dtype=float)
    n = len(y)
    if n < 2 * MIN_SEG + 2:
        return False, 0, 1.0
    resid = line_residuals(y)[0]
    if float(np.std(resid)) < 1e-12:
        return False, 0, 1.0

    f_obs, k_obs = _sup_f(resid)
    null = ar1_null_series(resid, n_boot, np.random.default_rng(seed))
    f_null, _ = _sup_f(null)
    p = (1.0 + float(np.sum(f_null >= f_obs[0]))) / (n_boot + 1.0)
    return bool(p < 0.05), int(k_obs[0]), round(p, 4)
