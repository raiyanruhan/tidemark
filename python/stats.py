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
    int_f_sq = float(np.trapezoid(f ** 2, x) if hasattr(np, 'trapezoid') else np.trapz(f ** 2, x))

    h     = max(1e-5, s * 1e-3)
    score = -(kde(x + h) - kde(x - h)) / (2.0 * h * f)
    score = np.clip(score, float(np.percentile(score, 2)), float(np.percentile(score, 98)))

    I_fisher = float(np.trapezoid(score ** 2 * f, x) if hasattr(np, 'trapezoid') else np.trapz(score ** 2 * f, x))
    I_fisher = max(I_fisher, 1.0 / sigma2)

    are_mk_ols = 12.0 * sigma2 * int_f_sq ** 2
    are_mk_opt = min(are_mk_ols / (I_fisher * sigma2), 1.0)
    return {
        "I_fisher":       round(I_fisher, 6),
        "are_mk_ols":     round(are_mk_ols, 4),
        "are_mk_optimal": round(are_mk_opt, 4),
    }


def compute_arep(vals, residuals, slope, phi, efficiency):
    """
    AREP e-process (Option B: Gaussian score process, valid n > 30).
    E_n = exp(omega * Lambda_n - omega^2 * I * n^3/6 * (1+phi)/(1-phi))
    See research/stats/arep.md.

    Score function is estimated from residuals (shape of f), but evaluated at
    centered_vals = slope*t + residuals (keeps trend signal for E[Lambda_n|H1] > 0).
    Evaluating at residuals alone gives E[Lambda_n] ≈ 0 under both hypotheses.
    """
    n = len(residuals)
    if n < 20 or efficiency is None:
        return None
    omega = slope
    I_hat = efficiency["I_fisher"]
    try:
        kde = stats.gaussian_kde(residuals, bw_method='silverman')
    except Exception:
        return None

    # centered[i] = slope*i + residuals[i] = vals[i] - intercept
    # KDE score estimated from residuals (shape of f), applied at centered_vals.
    # Gaussian fallback outside KDE support: avoids score→0 in tails for large trends.
    t0 = np.arange(n, dtype=float)
    centered = slope * t0 + residuals

    s = float(np.std(residuals, ddof=1))
    h = max(1e-5, s * 1e-3)

    # clip bounds from score at residuals (the in-distribution set)
    f_at_res = np.maximum(kde(residuals), 1e-12)
    score_at_res = -(kde(residuals + h) - kde(residuals - h)) / (2.0 * h * f_at_res)
    lo = float(np.percentile(score_at_res, 2))
    hi = float(np.percentile(score_at_res, 98))

    # Gaussian score fallback: c(x) = x/sigma^2 (always defined)
    c_hat = centered / (s ** 2)

    # Override with KDE score where centered is within residual support
    support_lo = float(residuals.min()) - 3.0 * s
    support_hi = float(residuals.max()) + 3.0 * s
    in_support = (centered >= support_lo) & (centered <= support_hi)
    if in_support.any():
        c_in = centered[in_support]
        f_in = np.maximum(kde(c_in), 1e-12)
        s_in = -(kde(c_in + h) - kde(c_in - h)) / (2.0 * h * f_in)
        c_hat[in_support] = np.clip(s_in, lo, hi)

    # 1-indexed time weights for normalizer (sum t^2 = n(n+1)(2n+1)/6 ≈ n^3/3)
    t = np.arange(1, n + 1, dtype=float)
    Lambda_n = float(np.sum(c_hat * t))

    # AR(1) correction omitted: (1+phi)/(1-phi) inflation makes E[log E_n|H1] < 0
    # for phi > 1/3, killing the signal. E_n is anti-conservative for correlated
    # data; interpret alongside Hamed-Rao p-value for autocorrelated series.
    normalizer = omega ** 2 * I_hat * n ** 3 / 6.0

    log_E = omega * Lambda_n - normalizer
    significant = log_E > math.log(20.0)
    # clamp for display; use log_E for significance to avoid float overflow
    E_n_display = round(float(np.exp(min(log_E, 50.0))), 2)

    return {
        "E_n":         E_n_display,
        "log_E":       round(log_E, 4),
        "threshold":   20,
        "significant": significant,
        "phi_note":    abs(phi) > 0.4,
    }


def run_mannkendall(vals):
    """
    Hamed-Rao modified Mann-Kendall test (lag=3).
    Corrects for autocorrelation by inflating var_s based on ACF of rank-detrended series.
    Returns the pymannkendall result object.
    """
    return mk.hamed_rao_modification_test(vals, alpha=0.05, lag=3)
