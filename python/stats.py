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


# Prior on the standardised slope delta = beta / sigma (per annual step).
# Scale mixture of three zero-mean normals; fixed in advance, never fitted to
# the series being tested. 24-point Gauss-Hermite per component.
_EP_TAUS = (0.02, 0.05, 0.15)
_EP_X, _EP_W = np.polynomial.hermite.hermgauss(24)
_EP_DELTA = np.concatenate([t * math.sqrt(2.0) * _EP_X for t in _EP_TAUS])
_EP_LOGW = np.concatenate(
    [np.log(_EP_W / math.sqrt(math.pi)) - math.log(len(_EP_TAUS)) for _ in _EP_TAUS])
EP_THRESHOLD = 20.0


def _logsumexp(a, axis=None):
    m = np.max(a, axis=axis, keepdims=True)
    out = np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True)) + m
    return out if axis is None else np.squeeze(out, axis=axis)


def _ep_ar1_phi(y):
    """Lag-1 coefficient of OLS-line residuals, small-sample corrected, in [0, 0.9]."""
    n = len(y)
    t = np.arange(n, dtype=float)
    r = y - np.polyval(np.polyfit(t, y, 1), t)
    d = float(np.dot(r[:-1], r[:-1]))
    if d <= 0.0:
        return 0.0
    p = float(np.dot(r[:-1], r[1:])) / d
    p += (1.0 + 4.0 * p) / n
    return float(np.clip(p, 0.0, 0.9))


def log_bayes_factor_trend(y, phi=0.0):
    """
    log E_n for H0: no linear trend vs H1: slope beta = delta*sigma, delta ~ prior above.

    Intercept and noise scale are nuisance parameters shared by both
    hypotheses and are integrated out with the right-Haar priors
    (flat on intercept, 1/sigma on scale). The result is the likelihood ratio of
    the maximal invariant under y -> a + s*y, so E[E_n | H0] = 1 exactly for
    iid Gaussian errors, and E_n is a martingale in the invariant filtration
    (Wijsman 1967; Perez-Ortiz et al. 2024). With phi != 0 the series, the
    intercept column and the time column are Prais-Winsten whitened first; that
    step treats the estimated phi as known and is approximate.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    t = np.arange(n, dtype=float)
    one = np.ones(n)
    if phi != 0.0:
        def white(x):
            z = np.empty(n)
            z[0] = math.sqrt(1.0 - phi * phi) * x[0]
            z[1:] = x[1:] - phi * x[:-1]
            return z
        y, t, one = white(y), white(t), white(one)
    o = one / np.linalg.norm(one)
    y0 = y - o * (o @ y)          # intercept projected out
    x0 = t - o * (o @ t)          # centred (whitened) time
    S0 = float(y0 @ y0)
    Sxx = float(x0 @ x0)
    if S0 <= 0.0 or Sxx <= 0.0:
        return 0.0
    r = float(x0 @ y0) / math.sqrt(S0 * Sxx)
    c = _EP_DELTA * math.sqrt(Sxx) * r
    v = np.linspace(1e-6, math.sqrt(n) + 12.0 + float(np.abs(c).max()), 1500)
    lv = (n - 2) * np.log(v) - v * v / 2.0
    l_alt = (_logsumexp(lv[None, :] + c[:, None] * v[None, :], axis=1)
             - _logsumexp(lv) - _EP_DELTA ** 2 * Sxx / 2.0)
    return float(_logsumexp(_EP_LOGW + l_alt))


def compute_eprocess(vals):
    """
    Mixture e-variable for "no linear trend" (research/stats/arep.md).

    E_n = integral over the slope prior of the likelihood ratio, with intercept
    and noise scale integrated out (log_bayes_factor_trend). Nothing is fitted
    to the series being tested apart from phi, so the omega-fitted-on-the-same-data
    flaw of the old statistic is gone.

    Guarantees: for iid Gaussian errors, E[E_n | H0] = 1, so P(E_n >= 20) <= 5%
    at any fixed n, and by Ville's inequality on the invariant filtration the
    same bound holds uniformly over n. Autocorrelation: phi is estimated and the
    series Prais-Winsten whitened; this is approximate (no exact guarantee) and
    was checked only by simulation. Non-Gaussian errors: no guarantee, simulated.
    """
    y = np.asarray(vals, dtype=float)
    n = len(y)
    if n < 15 or not np.all(np.isfinite(y)):
        return None
    phi_used = _ep_ar1_phi(y)
    log_E = log_bayes_factor_trend(y, phi_used)
    return {
        "E_n":         round(float(np.exp(min(log_E, 50.0))), 2),
        "log_E":       round(log_E, 4),
        "threshold":   int(EP_THRESHOLD),
        "significant": bool(log_E >= math.log(EP_THRESHOLD)),
        "phi_used":    round(phi_used, 3),
        "phi_note":    phi_used > 0.4,
    }


def mkc3_variance(residuals, n):
    """
    MKC3 variance of the Mann-Kendall S-statistic, Then & Abdul Halim,
    Sci. Rep. 16, 500 (2025), doi:10.1038/s41598-025-30034-0 (PMC12775442).

    Eq. 18 (MKRD, Hamed-Rao on rank-detrended data):
        n/n*_s = 1 + 2 * sum_{i=1}^{n-1} (n-i)(n-i-1)(n-i-2) rho_s(i) / (n(n-1)(n-2))
      rho_s = lag-i autocorrelation of the ranks of the Sen-detrended series,
      only lags with |rho_s(i)| > z_{0.975}/sqrt(n) (pymannkendall default, lag=None).
    Eq. 21 (third-order cumulant, lags 1 and 2, standardized series):
        Phi_3 = 1/(n-2) * sum_{k=1}^{n-2} x_k x_{k+1} x_{k+2}
    Eq. 22-23:  n/n*' = n/n*_s + Phi_3 ;  Var'(S) = Var(S) * n/n*'

    The paper says "the rank-detrended data are standardized" before Eq. 21
    but also "detrended and standardized"; the ranks reading is used here.
    `residuals` are the Sen-detrended values. Phi_3 is dimensionless, so the
    result is unit invariant. Falls back to var0 (IID) if non-positive.
    """
    from scipy.stats import rankdata
    x = np.asarray(residuals, dtype=float)
    n = len(x)
    var0 = n * (n - 1) * (2 * n + 5) / 18.0
    if n < 4:
        return var0

    r = rankdata(x)
    rc = r - r.mean()
    ss = float(rc @ rc)
    if ss <= 1e-12:
        return var0
    interval = 1.959963984540054 / math.sqrt(n)
    sni = 0.0
    for i in range(1, n):
        rho = float(rc[:-i] @ rc[i:]) / ss
        if abs(rho) > interval:
            sni += (n - i) * (n - i - 1) * (n - i - 2) * rho
    n_ns = 1.0 + 2.0 * sni / (n * (n - 1) * (n - 2))

    z = rc / float(np.std(rc, ddof=1))
    phi3 = float(np.mean(z[:-2] * z[1:-1] * z[2:]))

    var = var0 * (n_ns + phi3)
    return var if var > 0 else var0


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


def ar1_fit(resid):
    """
    AR(1) fit to line residuals: returns (phi, centred innovations).
    phi gets the usual small-sample bias correction for a fitted linear
    trend, (1 + 4*phi)/n, and is clipped to [-0.95, 0.95].
    """
    r = np.asarray(resid, dtype=float)
    n = len(r)
    phi = lag1_acf(r)
    phi = float(np.clip(phi + (1.0 + 4.0 * phi) / n, -0.95, 0.95))
    innov = r[1:] - phi * r[:-1]
    return phi, innov - innov.mean()


def ar1_null_series(resid, n_boot, rng):
    """
    Bootstrap series under "one straight line + AR(1) noise": estimate phi from
    the line residuals, resample the innovations, rebuild the AR(1) process.
    Keeps the autocorrelation and the innovation distribution (skew included),
    both of which otherwise pass for structural breaks. See ar1_fit for phi.
    """
    r = np.asarray(resid, dtype=float)
    n = len(r)
    phi, innov = ar1_fit(r)
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


def _block_bootstrap_null(x, n_boot, seed):
    """Observed MK S, block-bootstrap null draws of S, block length."""
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

    return S_obs, null_S, block_len


def block_bootstrap_mk_variance(x, n_boot=2000, seed=42):
    """Variance of S under the block-bootstrap null (what the bootstrap z uses)."""
    _, null_S, _ = _block_bootstrap_null(x, n_boot, seed)
    return float(np.var(null_S))


def block_bootstrap_mk_pvalue(x, n_boot=2000, seed=42):
    """
    Block bootstrap p-value for Mann-Kendall trend test.
    Önöz & Bayazit 2012, Hydrol. Process. 26(23):3552-3560.
    More accurate than Hamed-Rao for ARMA/long-memory series (soil moisture, NDVI).
    Returns (p_value, z_score, block_len).
    """
    S_obs, null_S, block_len = _block_bootstrap_null(x, n_boot, seed)

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


METHOD_LABELS = {
    "sieve": "Mann-Kendall, AR(1) sieve bootstrap",
    "hr":    "Modified Mann-Kendall (Hamed-Rao, lag=3)",
    "mkc3":  "Modified Mann-Kendall (MKC3, Then 2025)",
}
SIEVE_N_BOOT = 1999


def select_mk_method(phi, skewness, n):
    """
    Variance-correction variant reported for comparison next to the verdict:
    'bb' (autocorrelated), 'mkc3' (skewed) or 'hr'. Not used for the verdict:
    on trend-free data these reject 7-17% of the time at a nominal 5%.
    """
    if abs(phi) > 0.3:
        return "bb"
    if abs(skewness) > 0.5 and n >= 20:
        return "mkc3"
    return "hr"


def mk_s_rows(Y):
    """Mann-Kendall S statistic for each row of Y."""
    Y = np.atleast_2d(np.asarray(Y, dtype=float))
    i, j = np.triu_indices(Y.shape[1], k=1)
    return np.sign(Y[:, j] - Y[:, i]).sum(axis=1)


def sieve_bootstrap_mk(x, n_boot=SIEVE_N_BOOT, seed=42):
    """
    Mann-Kendall test with the null distribution of S bootstrapped from the
    series itself: remove the Sen-slope line, fit AR(1) to the residuals
    (ar1_fit, bias-corrected phi), resample the innovations and rebuild
    trend-free AR(1) series (ar1_null_series). The null therefore carries the
    data's own autocorrelation and innovation shape (skew included) rather
    than a formula for either.

    Simulated rejection rate on trend-free data at a nominal 5% (n = 45):
    iid 5%, skewed 5%, AR(1) 0.3 6%, AR(1) 0.6 5%, AR(1) 0.8 11%.
    Shorter or more persistent series are less well calibrated (n = 20,
    phi = 0.6: 11%), because phi itself is poorly estimated there.
    Returns (p, z, var_boot, phi): z uses the bootstrap variance of S with the
    usual continuity correction.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    i, j = np.triu_indices(n, k=1)
    beta = float(np.median((x[j] - x[i]) / (j - i)))
    r = x - beta * np.arange(n, dtype=float)
    r = r - r.mean()
    s_obs = float(np.sum(np.sign(x[j] - x[i])))
    var0 = n * (n - 1) * (2 * n + 5) / 18.0
    if float(np.std(r)) < 1e-12:
        return (1.0 if s_obs == 0 else 1.0 / (n_boot + 1.0)), 0.0, var0, 0.0

    phi, _ = ar1_fit(r)
    null = ar1_null_series(r, n_boot, np.random.default_rng(seed))
    s_null = mk_s_rows(null)
    p = (1.0 + float(np.sum(np.abs(s_null) >= abs(s_obs)))) / (n_boot + 1.0)
    var_boot = float(np.var(s_null))
    if var_boot <= 0:
        var_boot = var0
    z = (s_obs - np.sign(s_obs)) / math.sqrt(var_boot)
    return float(p), float(z), var_boot, phi


def mk_verdict(vals, method="sieve"):
    """
    The pipeline's significance verdict for one series. Single source of truth:
    analyse() and the trajectory module both go through here.
    method="sieve" (default) is the AR(1) sieve-bootstrap Mann-Kendall test.
    "hr", "mkc3", "bb" force one of the variance-correction variants and
    "legacy" picks among those three by autocorrelation and skew
    (select_mk_method); these are kept for comparison only.
    Returns dict: method, method_label, res (Hamed-Rao result: slope, intercept,
    Tau), slope, intercept, residuals, phi, skewness, z, p, significant, var_s.
    """
    vals = np.asarray(vals, dtype=float)
    n = len(vals)
    res = run_mannkendall(vals)
    slope, intercept = float(res.slope), float(res.intercept)
    residuals = compute_residuals(vals, slope, intercept)
    phi = lag1_acf(residuals)
    skewness = float(stats.skew(residuals))
    if method == "legacy":
        method = select_mk_method(phi, skewness, n)

    var0 = n * (n - 1) * (2 * n + 5) / 18.0
    if method == "sieve":
        p, z, var_s, _ = sieve_bootstrap_mk(vals)
        sig = bool(p < 0.05)
        label = METHOD_LABELS["sieve"]
    elif method == "bb":
        p, z, bb_len = block_bootstrap_mk_pvalue(vals)
        sig = bool(p < 0.05)
        var_s = block_bootstrap_mk_variance(vals)
        label = f"Block Bootstrap MK (Önöz & Bayazit 2012, block length={bb_len})"
    elif method == "mkc3":
        z, p, _, sig = mk_z_mkc3(vals)
        var_s = mkc3_variance(vals - slope * np.arange(n, dtype=float), n)
        label = METHOD_LABELS["mkc3"]
    else:
        z, p, sig, var_s = float(res.z), float(res.p), bool(res.h), float(res.var_s)
        label = METHOD_LABELS["hr"]
    return {"method": method, "method_label": label, "res": res,
            "slope": slope, "intercept": intercept, "residuals": residuals,
            "phi": phi, "skewness": skewness, "z": round(float(z), 4), "p": float(p),
            "significant": bool(sig), "var_s": float(var_s if var_s > 0 else var0)}


def mk_variance_inflation(verdict, n):
    """
    Var(S) used by the verdict divided by the IID variance n(n-1)(2n+5)/18.
    This is the autocorrelation/skew correction the verdict applied, so a
    simulation can reuse it at every n without a bootstrap per step.
    """
    var0 = n * (n - 1) * (2 * n + 5) / 18.0
    return float(np.clip(verdict["var_s"] / var0, 0.5, 20.0))
