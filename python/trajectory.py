"""
trajectory.py, significance trajectory: when will the trend become detectable?

Four independent estimates:
  1. Analytical MK , n^(3/2) Z-score growth, assumes Gaussian IID
  2. Weatherhead 1998, OLS detection time with AR(1) correction (JGR, doi:10.1029/98JD00995)
  3. Monte Carlo    , empirical bootstrap, only method valid for non-Gaussian noise
  4. CRB floor      , Fisher information lower bound: no test can beat this
"""
import math

import numpy as np
import pymannkendall as mk
from scipy import stats

N_SIM       = 1000
HORIZON     = 80
N_FAN_PATHS = 200   # MC paths retained for visualization fan


def analytical_crossing_year(z0, n0, last_year):
    """
    Year when |z| reaches 1.96 under n^(3/2) Z-score growth.
    Returns None if z0 near zero.
    """
    if abs(z0) < 0.05:
        return None
    if abs(z0) >= 1.96:
        return last_year
    ratio        = (1.96 / abs(z0)) ** (2.0 / 3.0)
    years_needed = n0 * (ratio - 1.0)
    return last_year + int(math.ceil(years_needed))


def weatherhead_detection_years(sigma_n, omega, phi):
    """
    Weatherhead et al. (1998): years needed to detect omega at ~90% power.
    n* = (3.3 * sigma_N / |omega|)^(2/3) * ((1+phi)/(1-phi))^(1/3)
    """
    if abs(omega) < 1e-12:
        return float("inf")
    phi            = max(-0.99, min(0.99, phi))
    base           = (3.3 * sigma_n / abs(omega)) ** (2.0 / 3.0)
    acf_correction = ((1.0 + phi) / (1.0 - phi)) ** (1.0 / 3.0)
    return base * acf_correction


def crb_detection_year(omega, I_fisher, sigma_n, phi, n_obs, last_year):
    """
    CRB lower bound on significance year via Fisher information.
    n*_CRB = n*_Weatherhead * (I(f) * sigma^2)^(-1/3).
    No unbiased estimator can confirm the trend before this year.
    """
    if abs(omega) < 1e-12 or I_fisher < 1e-10:
        return None
    phi   = max(-0.99, min(0.99, phi))
    base  = (3.3 * sigma_n / abs(omega)) ** (2.0 / 3.0)
    acf   = ((1.0 + phi) / (1.0 - phi)) ** (1.0 / 3.0)
    n_wh  = base * acf
    n_crb = n_wh * (I_fisher * sigma_n ** 2) ** (-1.0 / 3.0)
    return last_year + max(0, int(math.ceil(n_crb - float(n_obs))))


def run_monte_carlo(vals, slope, intercept, residuals, z_score, last_year,
                    collect_paths=False, progress=None, cancel=None):
    """
    Bootstrap-extend the series N_SIM times using empirical residual resampling.
    Returns (crossing_years, never_crossed, sample_paths).
    sample_paths is a list of float-value traces; non-empty only if collect_paths=True.
    """
    n   = len(vals)
    buf = np.empty(n + HORIZON)
    buf[:n] = vals
    crossing_years = []
    never_crossed  = 0
    sample_paths   = [] if collect_paths else None

    for sim_idx in range(N_SIM):
        if cancel is not None and sim_idx % 50 == 0 and cancel.is_set():
            break
        if progress and sim_idx > 0 and sim_idx % 200 == 0:
            progress(f"Running simulation: {sim_idx} of {N_SIM}")
        noise   = np.random.choice(residuals, size=HORIZON, replace=True)
        crossed = False
        path    = [] if (collect_paths and sim_idx < N_FAN_PATHS) else None

        for step in range(1, HORIZON + 1):
            t_new             = n - 1 + step
            buf[n + step - 1] = intercept + slope * t_new + noise[step - 1]
            res               = mk.original_test(buf[:n + step])
            if path is not None:
                path.append(float(buf[n + step - 1]))
            if res.p < 0.05 and (res.z * z_score > 0):
                crossing_years.append(last_year + step)
                crossed = True
                break
        if not crossed:
            never_crossed += 1
        if path is not None:
            sample_paths.append(path)

    return crossing_years, never_crossed, sample_paths


def compute_pvalue_series(vals, years, last_year):
    """
    Historical p-value curve from actual data slices, plus analytical projection forward.
    historical: original_test on vals[:n] for n from start to len(vals).
    projected: z(n) = z0 * (n/n0)^(2/3), p from normal CDF, forward 60 years.
    Projected series only included if current p > 0.05.
    """
    n     = len(vals)
    start = min(20, n // 2)

    historical_years = []
    historical_pvals = []
    for i in range(start, n + 1):
        res = mk.original_test(vals[:i])
        historical_years.append(years[i - 1])
        historical_pvals.append(float(res.p))

    full_res = mk.original_test(vals)
    projected_years = []
    projected_pvals = []

    if full_res.p > 0.05 and abs(full_res.z) > 1e-6:
        z0 = float(full_res.z)
        n0 = float(n)
        for step in range(1, 61):
            n_fut = n0 + step
            z_fut = z0 * (n_fut / n0) ** (2.0 / 3.0)
            p_fut = float(2.0 * stats.norm.sf(abs(z_fut)))
            projected_years.append(last_year + step)
            projected_pvals.append(p_fut)

    return {
        "historical_years": historical_years,
        "historical_pvals": historical_pvals,
        "projected_years":  projected_years,
        "projected_pvals":  projected_pvals,
    }


def compute_trajectory(vals, slope, intercept, residuals, z_score,
                       sigma_n, phi, n, last_year, eff, progress=None, cancel=None):
    """
    Assemble all four trajectory estimates into a single result dict.
    Call only when trend is NOT yet significant.
    """
    analytical_year = analytical_crossing_year(z_score, n, last_year)

    w_years = weatherhead_detection_years(sigma_n, slope, phi)
    if math.isinf(w_years):
        weatherhead_year = None
    else:
        extra = max(0, int(math.ceil(w_years - n)))
        weatherhead_year = last_year + extra

    crossing_years, never_crossed, sample_paths = run_monte_carlo(
        vals, slope, intercept, residuals, z_score, last_year,
        collect_paths=True, progress=progress, cancel=cancel,
    )

    if crossing_years:
        cy         = np.array(sorted(crossing_years))
        mc_median  = int(np.median(cy))
        mc_pi_low  = int(np.percentile(cy, 7.5))
        mc_pi_high = int(np.percentile(cy, 92.5))
    else:
        mc_median = mc_pi_low = mc_pi_high = None

    never_crossed_frac = never_crossed / N_SIM
    skewness           = float(stats.skew(residuals))
    _, normality_p     = stats.normaltest(residuals)

    estimates = [x for x in [analytical_year, weatherhead_year, mc_median] if x is not None]
    if len(estimates) >= 2:
        spread        = max(estimates) - min(estimates)
        methods_agree = spread <= 5
        divergence    = spread
    else:
        methods_agree = True
        divergence    = None

    crb_yr = None
    if eff is not None:
        crb_yr = crb_detection_year(slope, eff["I_fisher"], sigma_n, phi, n, last_year)

    FAN_HORIZON = 60
    fan_years = list(range(last_year + 1, last_year + FAN_HORIZON + 1))
    fan_paths = []
    if sample_paths:
        for path in sample_paths:
            fan_paths.append([float(v) for v in path[:FAN_HORIZON]])

    return {
        "analytical_year":    analytical_year,
        "weatherhead_year":   weatherhead_year,
        "weatherhead_phi":    round(phi, 4),
        "mc_median":          mc_median,
        "mc_pi_low":          mc_pi_low,
        "mc_pi_high":         mc_pi_high,
        "never_crossed":      never_crossed,
        "never_crossed_frac": round(never_crossed_frac, 4),
        "divergence_years":   divergence,
        "methods_agree":      methods_agree,
        "skewness":           round(skewness, 4),
        "normality_p":        float(normality_p),
        "crb_year":           crb_yr,
        "fan_paths":          fan_paths,
        "fan_years":          fan_years,
    }
