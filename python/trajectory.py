"""
trajectory.py, significance trajectory: when will the trend become detectable?

Four independent estimates:
  1. Analytical MK , n^(3/2) Z-score growth, assumes Gaussian IID
  2. Weatherhead 1998, OLS detection time with AR(1) correction (JGR, doi:10.1029/98JD00995)
  3. Monte Carlo    , AR(1) simulation using the pipeline's own test; first persistent
                      significance time, right-censored at HORIZON (see run_monte_carlo)
  4. CRB floor      , Fisher information lower bound: no test can beat this
"""
import math

import numpy as np
from scipy import stats

from stats import ar1_fit, mk_variance_inflation, mk_verdict

N_SIM       = 1000
HORIZON     = 80
N_FAN_PATHS = 200   # MC paths retained for visualization fan
PERSIST     = 3     # consecutive significant years required for a MC crossing

# NASA instrument 1-sigma calibration uncertainties (native variable units).
# Sources: MERRA-2 validation (Rienecker 2011, Bosilovich 2015), MODIS product docs.
# PRECTOTCORR is dimensionless fraction of sigma_N (multiplicative).
INSTRUMENT_UNCERTAINTY = {
    "T2M":         0.20,
    "T2M_MAX":     0.25,
    "T2M_MIN":     0.25,
    "RH2M":        3.0,
    "EVLAND":      0.015,
    "WS10M":       0.35,
    "VPD":         0.05,
    "DTR":         0.30,
    "GWETROOT":    0.04,
    "GWETTOP":     0.04,
    "GWETPROF":    0.04,
    "TSOIL1":      0.25,
    "TS":          0.15,
    "FROST_DAYS":  0.5,
    "PRECTOTCORR": 0.15,
    "NDVI":        0.03,
    "LST":         1.0,
    "ET_MOD16":    0.25,
}


def uTDT_detection_year(omega, sigma_n, phi, n_obs, last_year, param_code):
    """
    Weatherhead uTDT: detection year with NASA instrument calibration uncertainty.
    sigma_total = sqrt(sigma_N^2 + sigma_cal^2).
    Returns (utdt_year, sigma_total, sigma_cal); utdt_year=None when omega~0.
    """
    sigma_cal = INSTRUMENT_UNCERTAINTY.get(param_code or "", 0.0)
    if param_code == "PRECTOTCORR":
        sigma_cal = sigma_cal * sigma_n
    sigma_total = math.sqrt(sigma_n ** 2 + sigma_cal ** 2)
    if abs(omega) < 1e-12:
        return None, sigma_total, sigma_cal
    phi_c   = max(-0.99, min(0.99, phi))
    n_star  = (3.3 * sigma_total / abs(omega)) ** (2.0 / 3.0) \
              * ((1.0 + phi_c) / (1.0 - phi_c)) ** (1.0 / 3.0)
    year    = last_year + max(0, int(math.ceil(n_star - n_obs)))
    return year, round(sigma_total, 4), round(sigma_cal, 4)


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
                    collect_paths=False, progress=None, cancel=None, seed=None, pi0=0.0):
    """
    Simulate N_SIM futures and return when each first becomes significant.

    Returns (cross_step, sample_paths). cross_step is a float array of length
    N_SIM: the step (1..HORIZON, years after last_year) at which the path
    crosses, np.inf if it never does within HORIZON (right-censored).
    sample_paths holds N_FAN_PATHS value traces (HORIZON long) when collect_paths.

    Design (each point answers a flaw in the old IID/fixed-slope version):
      * Same test as the verdict. The verdict (stats.mk_verdict, AR(1) sieve
        bootstrap) implies a variance inflation k = Var(S)/Var_IID(S) for the
        observed series (stats.mk_variance_inflation). Each step then tests
        z = (S -/+ 1) / sqrt(k * n(n-1)(2n+5)/18), S updated incrementally.
        A per-step bootstrap would be ~1e5x slower. Approximation: k is held
        fixed as n grows.
      * AR(1) noise. phi and innovations come from stats.ar1_fit (same as
        ar1_null_series); future noise continues the AR(1) process from the
        path's own last residual, innovations resampled, so autocorrelation
        and skew are kept.
      * Slope uncertainty. Each path draws its slope as b + se*t(n-2),
        b = observed Sen slope, se = OLS slope SE inflated by
        sqrt((1+phi)/(1-phi)). Lines pivot on the data mean, so a different
        slope changes the end level consistently. This is the sampling
        distribution of the slope, so the result is conditional on a trend of
        about the observed size existing: draws near zero or of the opposite
        sign never cross, but there is no extra "no trend at all" mass. (An
        earlier version added one, set from the p-value; with p > 0.15 it
        exceeded one half and the median was "never" even for series whose
        true trend becomes significant in ~20 years.) pi0 can still be passed
        explicitly to add such a mass.
      * Peeking. Testing every year and stopping at the first p<0.05 is
        optional stopping. A crossing here must PERSIST: significant in the
        trend's direction for PERSIST consecutive years; the reported year is
        the first of that run. Still a "first persistent significance time",
        not the time at which a single pre-registered test would pass.
      * Direction. Only significance in the observed trend's direction counts.
      * Censoring. Never-crossed paths stay in the sample as np.inf.
    """
    vals = np.asarray(vals, dtype=float)
    n = len(vals)
    rng = np.random.default_rng(seed)
    steps = HORIZON + PERSIST - 1          # extra steps so late runs can complete

    k = mk_variance_inflation(mk_verdict(vals), n)
    phi, innov = ar1_fit(residuals)

    tbar = (n - 1) / 2.0
    sxx = n * (n * n - 1) / 12.0
    sigma = float(np.std(residuals, ddof=1))
    se = sigma / math.sqrt(sxx) * math.sqrt((1.0 + phi) / (1.0 - phi))

    beta = slope + se * rng.standard_t(max(n - 2, 1), size=N_SIM)
    if pi0:
        beta[rng.random(N_SIM) < pi0] = 0.0
    level = float(np.mean(vals))
    e = vals[-1] - (level + beta * (n - 1 - tbar))        # per-path AR(1) state
    shocks = rng.choice(innov, size=(N_SIM, steps), replace=True)

    buf = np.empty((N_SIM, n + steps))
    buf[:, :n] = vals
    iu, ju = np.triu_indices(n, k=1)
    S = np.full(N_SIM, float(np.sum(np.sign(vals[ju] - vals[iu]))))
    direction = 1.0 if z_score >= 0 else -1.0

    sig = np.zeros((N_SIM, steps), dtype=bool)
    for step in range(1, steps + 1):
        if cancel is not None and cancel.is_set():
            break
        if progress and step % 20 == 0:
            progress(f"Running simulation: year {step} of {HORIZON}")
        m = n + step - 1
        e = phi * e + shocks[:, step - 1]
        buf[:, m] = level + beta * (m - tbar) + e
        S += np.sign(buf[:, m:m + 1] - buf[:, :m]).sum(axis=1)
        nn = m + 1
        sd = math.sqrt(k * nn * (nn - 1) * (2 * nn + 5) / 18.0)
        z = np.where(S > 0, S - 1.0, np.where(S < 0, S + 1.0, 0.0)) / sd
        sig[:, step - 1] = (np.abs(z) > 1.959964) & (z * direction > 0)

    # first step that starts a run of PERSIST consecutive significant steps
    run = sig[:, :HORIZON].copy()
    for j in range(1, PERSIST):
        run &= sig[:, j:HORIZON + j]
    crossed = run.any(axis=1)
    cross_step = np.where(crossed, run.argmax(axis=1) + 1, np.inf)

    sample_paths = None
    if collect_paths:
        sample_paths = [[float(v) for v in buf[i, n:n + HORIZON]]
                        for i in range(min(N_FAN_PATHS, N_SIM))]
    return cross_step, sample_paths


def compute_pvalue_series(vals, years, last_year):
    """
    Historical p-value curve from actual data slices, plus analytical projection forward.
    historical: the SAME test as the reported verdict (stats.mk_verdict)
    applied to every prefix vals[:i], so the last point equals the reported p.
    projected: z(n) = z0 * (n/n0)^(3/2), p from normal CDF, forward 60 years.
    Projected series only included if current p > 0.05.
    """
    vals  = np.asarray(vals, dtype=float)
    n     = len(vals)
    start = min(20, n // 2)

    full = mk_verdict(vals)
    historical_years = []
    historical_pvals = []
    for i in range(start, n):
        historical_years.append(years[i - 1])
        historical_pvals.append(float(mk_verdict(vals[:i])["p"]))
    historical_years.append(years[n - 1])
    historical_pvals.append(float(full["p"]))

    projected_years = []
    projected_pvals = []

    if full["p"] > 0.05 and abs(full["z"]) > 1e-6:
        z0 = float(full["z"])
        n0 = float(n)
        for step in range(1, 61):
            n_fut = n0 + step
            z_fut = z0 * (n_fut / n0) ** 1.5
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
                       sigma_n, phi, n, last_year, eff, param_code=None,
                       progress=None, cancel=None):
    """
    Assemble all five trajectory estimates into a single result dict.
    Call only when trend is NOT yet significant.
    """
    analytical_year = analytical_crossing_year(z_score, n, last_year)

    utdt_year, utdt_sigma_total, utdt_sigma_cal = uTDT_detection_year(
        slope, sigma_n, phi, n, last_year, param_code
    )

    w_years = weatherhead_detection_years(sigma_n, slope, phi)
    if math.isinf(w_years):
        weatherhead_year = None
    else:
        extra = max(0, int(math.ceil(w_years - n)))
        weatherhead_year = last_year + extra

    cross_step, sample_paths = run_monte_carlo(
        vals, slope, intercept, residuals, z_score, last_year,
        collect_paths=True, progress=progress, cancel=cancel,
    )

    # Never-crossed paths are right-censored (inf), not dropped. A q-quantile
    # of crossing time is only defined when more than q of ALL paths cross.
    n_paths       = len(cross_step)
    never_crossed = int(np.isinf(cross_step).sum())

    def _q(q):
        v = np.quantile(cross_step, q / 100.0, method="higher")
        return None if np.isinf(v) else int(last_year + v)

    mc_median  = _q(50.0)      # None => "not within the horizon" (>50% never cross)
    mc_pi_low  = _q(7.5)
    mc_pi_high = _q(92.5)      # None when >7.5% never cross

    never_crossed_frac = never_crossed / n_paths
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
        "utdt_year":          utdt_year,
        "utdt_sigma_total":   utdt_sigma_total,
        "utdt_sigma_cal":     utdt_sigma_cal,
        "weatherhead_phi":    round(phi, 4),
        "mc_median":          mc_median,
        "mc_pi_low":          mc_pi_low,
        "mc_pi_high":         mc_pi_high,
        "never_crossed":      never_crossed,
        "never_crossed_frac": round(never_crossed_frac, 4),
        "mc_horizon_year":    last_year + HORIZON,
        "divergence_years":   divergence,
        "methods_agree":      methods_agree,
        "skewness":           round(skewness, 4),
        "normality_p":        float(normality_p),
        "crb_year":           crb_yr,
        "fan_paths":          fan_paths,
        "fan_years":          fan_years,
    }
