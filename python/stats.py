"""
stats.py, core statistical computations for climate trend analysis.
"""
import math

import numpy as np
import pymannkendall as mk
from scipy import stats


def compute_residuals(vals, slope, intercept):
    t = np.arange(len(vals))
    return vals - (intercept + slope * t)


def lag1_acf(arr):
    if len(arr) < 3:
        return 0.0
    r = np.corrcoef(arr[:-1], arr[1:])[0, 1]
    return float(r) if not math.isnan(r) else 0.0


def detection_floor(sigma_n, n):
    """
    Minimum slope Mann-Kendall can detect at 80% power.
    beta_min = 9.93 * sigma_N / n^1.5
    Derivation: z_crit / (C * n^1.5) where z_crit = 2.802 (80% power), C = 1/(2*sqrt(pi)) = 0.282.
    """
    return 9.93 * sigma_n / (n ** 1.5)


def compute_efficiency_metrics(residuals):
    """
    Fisher information I(f), ARE(MK vs OLS), ARE(MK vs optimal rank test).
    Clamps I(f) >= 1/sigma^2: KDE over-smoothing can violate Cramer-Rao otherwise.
    Returns None if n < 20 or distribution degenerate.
    """
    n = len(residuals)
    if n < 20:
        return None
    sigma2 = float(np.var(residuals, ddof=1))
    if sigma2 < 1e-12:
        return None
    try:
        kde = stats.gaussian_kde(residuals, bw_method='silverman')
    except Exception:
        return None

    s = math.sqrt(sigma2)
    x = np.linspace(float(residuals.min()) - 2.0 * s,
                    float(residuals.max()) + 2.0 * s, 500)
    f        = np.maximum(kde(x), 1e-12)
    int_f_sq = float(np.trapz(f ** 2, x))

    h     = max(1e-5, s * 1e-3)
    score = -(kde(x + h) - kde(x - h)) / (2.0 * h * f)
    score = np.clip(score, float(np.percentile(score, 2)), float(np.percentile(score, 98)))

    I_fisher = float(np.trapz(score ** 2 * f, x))
    I_fisher = max(I_fisher, 1.0 / sigma2)

    are_mk_ols = 12.0 * sigma2 * int_f_sq ** 2
    are_mk_opt = min(are_mk_ols / (I_fisher * sigma2), 1.0)
    return {
        "I_fisher":       round(I_fisher, 6),
        "are_mk_ols":     round(are_mk_ols, 4),
        "are_mk_optimal": round(are_mk_opt, 4),
    }


def run_mannkendall(vals):
    """
    Hamed-Rao modified Mann-Kendall test (lag=3).
    Corrects for autocorrelation by inflating var_s based on ACF of rank-detrended series.
    Returns the pymannkendall result object.
    """
    return mk.hamed_rao_modification_test(vals, alpha=0.05, lag=3)
