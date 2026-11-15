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
    Var_MKC3(S) = Var_HR(S) + 2 * sum_{k=1}^{lag_max} (n-k) * w_k * kappa3_k
    where kappa3_k = mean(eps[:-k]^2 * eps[k:])  (third-order lag-k cumulant).

    Lag cutoff: same lag=3 convention as hamed_rao_modification_test.
    Using all n-1 lags on short series (n~45) causes noisy high-lag autocorrelation
    estimates to make n_star_inv negative → invalid variance. Lag=3 matches the
    pymannkendall HR implementation and keeps both the HR and C3 sums stable.

    Falls back to var0 (IID) if the corrected variance is non-positive.
    """
    eps = residuals - float(np.mean(residuals))
    n = len(eps)
    lag_max = min(3, n - 2)   # match hamed_rao_modification_test lag=3
    # Var(S) is unitless but kappa3 carries data-units^3; standardize so the
    # correction does not change with the units of the variable.
    sd = float(np.std(eps, ddof=1))
    if sd > 1e-12:
        eps = eps / sd

    rho = []
    for k in range(1, lag_max + 1):
        if n - k < 2:
            rho.append(0.0)
        else:
            r = float(np.corrcoef(eps[:-k], eps[k:])[0, 1])
            rho.append(0.0 if math.isnan(r) else r)

    n_star_inv = 1.0
    for k in range(1, lag_max + 1):
        w = 1.0 - k / (n + 1)
        n_star_inv += (2.0 / n) * (n - k) * w * rho[k - 1]

    var0 = n * (n - 1) * (2 * n + 5) / 18.0
    var_hr = max(var0, var0 * n_star_inv)   # floor at var0 (IID): HR never below IID

    C3 = 0.0
    for k in range(1, lag_max + 1):
        kappa3_k = float(np.mean(eps[:-k] ** 2 * eps[k:]))
        w = 1.0 - k / (n + 1)
        C3 += (n - k) * w * kappa3_k

    var_mkc3 = var_hr + 2.0 * C3
    return var_mkc3 if var_mkc3 > var0 * 0.5 else var0


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

    # Cov(S_g, S_h) = (K_gh + sum_k h_k(g) h_k(h)) / 3, K_gh = sum_{i<j} sgn(dg)*sgn(dh).
    # For g=h this reproduces n(n-1)(2n+5)/18 exactly (no ties).
    sx = np.sign(np.triu(xd, k=1))
    sq = np.sign(np.triu(qd, k=1))
    sigma_xx = (float(np.sum(sx * sx)) + float(np.dot(h_x, h_x))) / 3.0
    sigma_qq = (float(np.sum(sq * sq)) + float(np.dot(h_q, h_q))) / 3.0
    sigma_xq = (float(np.sum(sx * sq)) + float(np.dot(h_x, h_q))) / 3.0

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


CP_MIN_SEG       = 5
CP_LOG_BF_THRESH = 3.5   # ~p96 of null max log BF for n = 30-60 (simulated, IID Gaussian noise)
CP_N_BOOT        = 999


def line_residuals(Y):
    """OLS straight-line residuals for each row of Y (time = 0..n-1)."""
    Y = np.atleast_2d(np.asarray(Y, dtype=float))
    t = np.arange(Y.shape[1], dtype=float)
    tc = t - t.mean()
    slope = (Y @ tc) / float(tc @ tc)
    return Y - Y.mean(axis=1, keepdims=True) - slope[:, None] * tc


def ar1_null_series(resid, n_boot, rng):
    """
    Bootstrap series under "one straight line + AR(1) noise": estimate phi from
    the line residuals, resample the innovations, rebuild the AR(1) process.
    Keeps the autocorrelation and the innovation distribution (skew included),
    both of which otherwise pass for structural breaks. phi gets the usual
    small-sample bias correction for a fitted linear trend, (1 + 4*phi)/n.
    """
    r = np.asarray(resid, dtype=float)
    n = len(r)
    phi = lag1_acf(r)
    phi = float(np.clip(phi + (1.0 + 4.0 * phi) / n, -0.95, 0.95))
    innov = r[1:] - phi * r[:-1]
    innov = innov - innov.mean()
    burn = 20
    e = rng.choice(innov, size=(n_boot, n + burn), replace=True)
    out = np.empty_like(e)
    out[:, 0] = e[:, 0]
    for i in range(1, n + burn):
        out[:, i] = phi * out[:, i - 1] + e[:, i]
    return out[:, burn:]


def _nig_line_log_marginal(m, su, suu, sy, suy, syy, a0=1.0, b0=1.0):
    """
    Log marginal likelihood of a straight-line model y = c0 + c1*u + e from the
    sufficient statistics of m points. Conjugate Normal-Inverse-Gamma prior:
    coefficients ~ N(0, sigma^2 I), sigma^2 ~ IG(a0, b0); coefficients and
    variance integrated out in closed form (conjugate Bayesian regression).
    """
    from scipy.special import gammaln
    det  = (m + 1.0) * (suu + 1.0) - su * su          # det(X^T X + I)
    quad = ((suu + 1.0) * sy * sy - 2.0 * su * sy * suy + (m + 1.0) * suy * suy) / det
    a_n  = a0 + m / 2.0
    b_n  = np.maximum(b0 + 0.5 * (syy - quad), 1e-300)
    return (gammaln(a_n) - gammaln(a0) + a0 * math.log(b0) - a_n * np.log(b_n)
            - 0.5 * np.log(det) - 0.5 * m * math.log(2.0 * math.pi))


def _two_line_log_bfs(Y):
    """
    log BF("two lines split at k" vs "one line") for each row of Y and every
    k in [CP_MIN_SEG, n - CP_MIN_SEG]. Rows are reduced to standardized OLS
    line residuals first, so the result ignores units and trend size.
    Returns (ks, log_bf array of shape rows x len(ks)).
    """
    R = line_residuals(Y)
    n = R.shape[1]
    sd = np.sqrt((R * R).sum(axis=1, keepdims=True) / (n - 2))
    Ys = R / np.maximum(sd, 1e-300)
    t = np.arange(n, dtype=float)
    u = (t - t.mean()) / t.std()
    ks = np.arange(CP_MIN_SEG, n - CP_MIN_SEG + 1)
    i = ks - 1

    cu, cuu = np.cumsum(u), np.cumsum(u * u)
    cy, cuy, cyy = np.cumsum(Ys, axis=1), np.cumsum(Ys * u, axis=1), np.cumsum(Ys * Ys, axis=1)
    full  = _nig_line_log_marginal(float(n), cu[-1], cuu[-1], cy[:, -1], cuy[:, -1], cyy[:, -1])
    left  = _nig_line_log_marginal(ks.astype(float), cu[i], cuu[i], cy[:, i], cuy[:, i], cyy[:, i])
    right = _nig_line_log_marginal(
        (n - ks).astype(float), cu[-1] - cu[i], cuu[-1] - cuu[i],
        cy[:, -1:] - cy[:, i], cuy[:, -1:] - cuy[:, i], cyy[:, -1:] - cyy[:, i])
    return ks, left + right - full[:, None]


def detect_changepoints(annual_values, n_boot=CP_N_BOOT, seed=42):
    """
    Bayesian single-changepoint detection for a trending series.
    For each candidate split k, log Bayes factor of "two lines" over "one line":
      log BF(k) = log P(x[:k]) + log P(x[k:]) - log P(x)
    with each P the closed-form NIG marginal likelihood of a straight-line model.
    The baseline is one line, not a constant mean: a mean-shift model reads
    every monotonic trend as a changepoint.

    Detection needs max log BF above CP_LOG_BF_THRESH and above the 95th
    percentile of the same maximum under a one-line + AR(1) bootstrap null
    (ar1_null_series), since autocorrelated or skewed noise inflates the
    Bayes factor of an IID Gaussian model.
    Returns (log_bfs array, cp_idx); cp_idx is the first index of the new
    regime, or None.
    """
    x = np.array(annual_values, dtype=float)
    n = len(x)
    log_bfs = np.full(n, -math.inf)
    if n < 2 * CP_MIN_SEG + 2:
        return log_bfs, None
    resid = line_residuals(x)[0]
    if float(np.std(resid)) < 1e-12:
        return np.zeros(n), None

    ks, lbf = _two_line_log_bfs(x)
    log_bfs[ks] = lbf[0]
    best     = int(ks[np.argmax(lbf[0])])
    best_lbf = float(log_bfs[best])
    if best_lbf <= CP_LOG_BF_THRESH:
        return log_bfs, None

    null = ar1_null_series(resid, n_boot, np.random.default_rng(seed))
    null_max = _two_line_log_bfs(null)[1].max(axis=1)
    if best_lbf <= float(np.percentile(null_max, 95)):
        return log_bfs, None
    return log_bfs, best


def bocpd_analysis(annual_values, years):
    """
    Bayesian changepoint analysis: one line vs two lines, conjugate NIG
    marginal likelihoods (see detect_changepoints).
    Returns structured result for Tidemark output, or None if series too short.
    """
    if len(annual_values) < 2 * CP_MIN_SEG + 2:
        return None

    log_bfs, cp_idx = detect_changepoints(annual_values)

    # Logistic confidence centered at the threshold: 50% at detection edge,
    # capped at 0.99 to avoid false certainty.
    def _lbf_to_conf(lbf):
        x = min(lbf - CP_LOG_BF_THRESH, 10.0)
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
