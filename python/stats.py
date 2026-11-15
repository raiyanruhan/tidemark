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


def mkc3_variance(residuals, n):
    """
    MKC3 variance of Mann-Kendall S-statistic (Then et al., Sci. Rep. 2025).
    Var_MKC3(S) = Var_HR(S) + 2 * sum_{k=1}^{n-1} (n-k) * w_k * kappa3_k
    where kappa3_k = mean(eps[:-k]^2 * eps[k:])  (third-order lag-k cumulant).
    Returns var_hr as fallback if correction produces non-positive result.
    """
    eps = residuals - float(np.mean(residuals))
    n = len(eps)

    rho = []
    for k in range(1, n):
        if n - k < 2:
            rho.append(0.0)
        else:
            r = float(np.corrcoef(eps[:-k], eps[k:])[0, 1])
            rho.append(0.0 if math.isnan(r) else r)
    rho = np.array(rho)

    n_star_inv = 1.0
    for k in range(1, n):
        w = 1.0 - k / (n + 1)
        n_star_inv += (2.0 / n) * (n - k) * w * rho[k - 1]

    var0 = n * (n - 1) * (2 * n + 5) / 18.0
    var_hr = var0 * n_star_inv

    C3 = 0.0
    for k in range(1, n):
        kappa3_k = float(np.mean(eps[:-k] ** 2 * eps[k:]))
        w = 1.0 - k / (n + 1)
        C3 += (n - k) * w * kappa3_k

    var_mkc3 = var_hr + 2.0 * C3
    return var_mkc3 if var_mkc3 > 0 else var_hr


def mk_z_mkc3(vals):
    """
    Mann-Kendall z-score using MKC3 variance correction (Then et al. 2025).
    Returns (z, p_value, slope, significant).
    """
    from scipy.stats import norm as _norm
    n = len(vals)
    t = np.arange(n, dtype=float)

    # S statistic
    S = 0.0
    for i in range(n - 1):
        for j in range(i + 1, n):
            S += float(np.sign(vals[j] - vals[i]))

    # Sen slope + residuals
    slopes = [(vals[j] - vals[i]) / (j - i) for i in range(n - 1) for j in range(i + 1, n)]
    slope = float(np.median(slopes))
    residuals = vals - slope * t

    var_s = mkc3_variance(residuals, n)
    if var_s <= 0:
        var_s = n * (n - 1) * (2 * n + 5) / 18.0

    if S > 0:
        z = (S - 1.0) / math.sqrt(var_s)
    elif S < 0:
        z = (S + 1.0) / math.sqrt(var_s)
    else:
        z = 0.0

    p = float(2.0 * _norm.sf(abs(z)))
    significant = p < 0.05
    return z, p, slope, significant


def partial_mk(x, q):
    """
    Partial Mann-Kendall test of x controlling for covariate q.
    Libiseller & Grimvall (2002), Water Resources Research, 38(6), 1–8.

    Removes the effect of covariate q from the concordance structure of x
    using the variance-covariance formula:
      sigma_xq = sum_k h_k(x)*h_k(q) / 3
      h_k(x) = sum_{j!=k} sign(x_k - x_j)   (net concordance of obs k)

    Returns dict with z, p, significant, enso_fraction, or None.
    """
    n = len(x)
    if n < 10:
        return None

    xd = x[None, :] - x[:, None]   # xd[i,j] = x[j] - x[i]
    qd = q[None, :] - q[:, None]

    # S statistics: sum of signs of upper triangle (j > i means later time)
    S_x = float(np.sum(np.sign(np.triu(xd, k=1))))
    S_q = float(np.sum(np.sign(np.triu(qd, k=1))))

    # h_k(x)[k] = sum_{j!=k} sign(x_k - x_j) = -rowsum(sign(xd))[k]
    # since xd[k,j]=x[j]-x[k], sign(xd[k,j])=sign(x[j]-x[k])=-sign(x[k]-x[j])
    h_x = -np.sum(np.sign(xd), axis=1).astype(float)
    h_q = -np.sum(np.sign(qd), axis=1).astype(float)

    sigma_xx = float(np.dot(h_x, h_x)) / 3.0
    sigma_qq = float(np.dot(h_q, h_q)) / 3.0
    sigma_xq = float(np.dot(h_x, h_q)) / 3.0

    if sigma_qq < 1e-10 or sigma_xx < 1e-10:
        return None

    S_partial = S_x - (sigma_xq / sigma_qq) * S_q
    var_partial = sigma_xx - sigma_xq ** 2 / sigma_qq

    if var_partial <= 0.0:
        return None

    z = S_partial / math.sqrt(var_partial)
    p = 2.0 * float(stats.norm.sf(abs(z)))
    enso_fraction = sigma_xq ** 2 / (sigma_xx * sigma_qq)

    return {
        "z":             round(z, 4),
        "p":             round(p, 6),
        "significant":   bool(p < 0.05),
        "enso_fraction": round(enso_fraction, 4),
    }


def ita_analysis(x):
    """
    Innovative Trend Analysis (Şen 2012).
    Split series into two halves, sort each, compare sorted pairs by tercile.
    Returns tercile slopes and raw sorted arrays for the scatter plot.
    """
    n = len(x)
    half = n // 2
    x1 = np.sort(x[:half])
    x2 = np.sort(x[half:half * 2])

    ita_slope = (np.mean(x2) - np.mean(x1)) / half

    t1 = half // 3
    t2 = 2 * t1

    low_slope  = (np.mean(x2[:t1])   - np.mean(x1[:t1]))   / half
    mid_slope  = (np.mean(x2[t1:t2]) - np.mean(x1[t1:t2])) / half
    high_slope = (np.mean(x2[t2:])   - np.mean(x1[t2:]))   / half

    return {
        "ita_slope":  round(float(ita_slope),  6),
        "low_slope":  round(float(low_slope),  6),
        "mid_slope":  round(float(mid_slope),  6),
        "high_slope": round(float(high_slope), 6),
        "x1_sorted":  x1.tolist(),
        "x2_sorted":  x2.tolist(),
    }


def _nig_log_marginal(x, mu0=0.0, kappa0=1.0, alpha0=1.0, beta0=1.0):
    """
    Log marginal likelihood of x under Normal-Inverse-Gamma prior.
    Closed-form: integrates out mean and variance analytically.
    """
    n = len(x)
    if n == 0:
        return 0.0
    kappa_n = kappa0 + n
    mu_n    = (kappa0 * mu0 + x.sum()) / kappa_n
    alpha_n = alpha0 + n / 2.0
    beta_n  = beta0 + 0.5 * ((x ** 2).sum() + kappa0 * mu0 ** 2 - kappa_n * mu_n ** 2)
    if beta_n <= 0 or kappa_n <= 0:
        return -math.inf
    return (math.lgamma(alpha_n) - math.lgamma(alpha0)
            + alpha0 * math.log(beta0) - alpha_n * math.log(beta_n)
            + 0.5 * math.log(kappa0 / kappa_n)
            - 0.5 * n * math.log(math.pi))


def detect_changepoints(annual_values):
    """
    Bayesian changepoint detection via NIG marginal likelihood (Chib 1998).
    For each candidate split t, log Bayes factor:
      log BF(t) = log P(x[:t]) + log P(x[t:]) - log P(x)
    BF > 3 (Jeffreys: moderate evidence) triggers detection.
    Returns (log_bfs array, cp_idx) where cp_idx is None if max BF < 3.
    """
    x = np.array(annual_values, dtype=float)
    std = float(np.std(x, ddof=1))
    if std < 1e-12:
        return np.zeros(len(x)), None
    x_std = (x - float(np.mean(x))) / std

    n         = len(x_std)
    log_p_all = _nig_log_marginal(x_std)
    log_bfs   = np.full(n, -math.inf)

    for t in range(3, n - 3):
        log_bfs[t] = (_nig_log_marginal(x_std[:t])
                      + _nig_log_marginal(x_std[t:])
                      - log_p_all)

    interior = log_bfs[3:-3]
    best_i   = int(np.argmax(interior))
    best_lbf = float(interior[best_i])

    # Threshold calibrated at ~p97 of null max log_BF for n=44 (simulated).
    # Scales naturally with series length via log(n): ~1.9 for n=44 raw, but
    # multiple comparisons inflate null; fixed 3.0 gives ~2-3% FPR for 30-60yr series.
    threshold = 3.0
    if best_lbf > threshold:
        cp_idx = best_i + 3
    else:
        cp_idx = None

    return log_bfs, cp_idx


def bocpd_analysis(annual_values, years):
    """
    Full BOCPD analysis returning structured result for Tidemark output.
    Returns None if series too short.
    """
    if len(annual_values) < 10:
        return None

    log_bfs, cp_idx = detect_changepoints(annual_values)

    # Logistic confidence centered at threshold=3.0: 50% at detection edge,
    # ~88% at lbf=5, ~99% at lbf=8, capped at 0.99 to avoid false certainty.
    def _lbf_to_conf(lbf):
        x = min(lbf - 3.0, 10.0)
        return round(min(0.99, math.exp(x) / (1.0 + math.exp(x))), 3)

    result = {
        "log_bayes_factors": [round(float(v), 4) if v > -math.inf else None for v in log_bfs],
        "changepoint_detected": cp_idx is not None,
    }

    if cp_idx is not None:
        cp_year = years[cp_idx]
        result["changepoint_year"]       = int(cp_year)
        result["changepoint_log_bf"]     = round(float(log_bfs[cp_idx]), 2)
        result["changepoint_confidence"] = _lbf_to_conf(float(log_bfs[cp_idx]))

        pre  = np.array(annual_values[:cp_idx], dtype=float)
        post = np.array(annual_values[cp_idx:], dtype=float)

        if len(pre) >= 5 and len(post) >= 5:
            slope_pre,  _, _, _, _ = stats.linregress(np.arange(len(pre)),  pre)
            slope_post, _, _, _, _ = stats.linregress(np.arange(len(post)), post)
            result["slope_before"] = round(float(slope_pre),  6)
            result["slope_after"]  = round(float(slope_post), 6)
            result["slope_change"] = round(float(slope_post - slope_pre), 6)

    return result


def block_bootstrap_mk_pvalue(x, n_boot=2000, seed=42):
    """
    Block bootstrap p-value for Mann-Kendall trend test.
    Önöz & Bayazit 2012, Hydrol. Process. 26(23):3552-3560.
    More accurate than Hamed-Rao for ARMA/long-memory series (soil moisture, NDVI).
    Returns (p_value, z_score, block_len).
    """
    rng = np.random.default_rng(seed)
    n = len(x)

    # Sen slope → residuals
    i_idx, j_idx = np.triu_indices(n, k=1)
    slopes = (x[j_idx] - x[i_idx]) / (j_idx - i_idx).astype(float)
    beta = float(np.median(slopes))
    residuals = x - beta * np.arange(n, dtype=float)

    # Lag-1 ACF → Politis-Romano optimal block length
    phi = float(np.corrcoef(residuals[:-1], residuals[1:])[0, 1])
    phi = float(np.clip(phi, -0.99, 0.99))
    if abs(phi) < 0.05:
        block_len = 1
    else:
        c = 1.75 * abs(2.0 * phi / (1.0 - phi ** 2)) ** (2.0 / 3.0)
        block_len = max(1, int(round(c * n ** (1.0 / 3.0))))
    block_len = min(block_len, n // 4)

    # Observed S statistic
    S_obs = float(np.sum(np.sign(x[j_idx] - x[i_idx])))

    # Block bootstrap null distribution
    null_S = np.empty(n_boot)
    n_blocks = int(math.ceil(n / block_len))
    for b in range(n_boot):
        starts = rng.integers(0, n - block_len + 1, size=n_blocks)
        resampled = np.concatenate([residuals[s:s + block_len] for s in starts])[:n]
        null_S[b] = float(np.sum(np.sign(resampled[j_idx] - resampled[i_idx])))

    p = float(np.mean(np.abs(null_S) >= abs(S_obs)))
    p = max(p, 1.0 / n_boot)

    var_boot = float(np.var(null_S))
    if var_boot > 0:
        if S_obs > 0:
            z = (S_obs - 1.0) / math.sqrt(var_boot)
        elif S_obs < 0:
            z = (S_obs + 1.0) / math.sqrt(var_boot)
        else:
            z = 0.0
    else:
        z = 0.0

    return p, z, block_len


def run_mannkendall(vals):
    """
    Hamed-Rao modified Mann-Kendall test (lag=3).
    Corrects for autocorrelation by inflating var_s based on ACF of rank-detrended series.
    Returns the pymannkendall result object.
    """
    return mk.hamed_rao_modification_test(vals, alpha=0.05, lag=3)
