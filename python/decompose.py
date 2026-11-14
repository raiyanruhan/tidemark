"""
decompose.py, ENSO signal decomposition and anthropogenic trend isolation.

Fetches NOAA MEI v2 (Multivariate ENSO Index, Wolter & Timlin 2011),
regresses out ENSO variability from the climate series, and returns the
anthropogenic component. ENSO accounts for 20-40% of interannual variance
in tropical regions; removing it reveals the underlying forced trend.

Source: NOAA Physical Sciences Laboratory
        https://psl.noaa.gov/enso/mei/
"""
import numpy as np
import requests

# NOAA PSL MEI v2: year + 12 bimonthly means (DJ JF FM MA AM MJ JJ JA AS SO ON ND)
# Available from 1979-present. -999 marks incomplete trailing seasons.
NOAA_MEI_URL = "https://psl.noaa.gov/enso/mei/data/meiv2.data"

# Fallback: NOAA CPC Oceanic Nino Index (3-month running SST anomaly, Nino3.4 region)
# Same physical signal, available from 1950-present.
NOAA_ONI_URL = "https://www.cpc.noaa.gov/data/indices/oni.ascii.txt"


def _parse_mei(text, years_needed):
    """
    Parse MEI v2 fixed-width table.
    Returns {year: annual_mean_mei} for years in years_needed.
    """
    enso = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            yr   = int(parts[0])
            vals = [float(x) for x in parts[1:] if float(x) > -99.0]
            if vals:
                enso[yr] = float(np.mean(vals))
        except (ValueError, IndexError):
            continue
    return {yr: enso[yr] for yr in years_needed if yr in enso}


def _parse_oni(text, years_needed):
    """
    Parse NOAA CPC ONI ascii table (year + 12 seasonal running means).
    """
    enso = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            yr   = int(parts[0])
            vals = [float(x) for x in parts[1:] if abs(float(x)) < 50.0]
            if vals:
                enso[yr] = float(np.mean(vals))
        except (ValueError, IndexError):
            continue
    return {yr: enso[yr] for yr in years_needed if yr in enso}


def fetch_enso(years):
    """
    Fetch annual mean ENSO index for each year in `years`.
    Tries MEI v2 first, falls back to ONI. Returns {} on total failure.

    Data source: NOAA Physical Sciences Laboratory / Climate Prediction Center.
    Not affiliated with NASA but freely available government data.
    Cite as: Wolter & Timlin (2011), doi:10.1002/joc.2336 (MEI v2).
    """
    for url, parser in [
        (NOAA_MEI_URL, _parse_mei),
        (NOAA_ONI_URL, _parse_oni),
    ]:
        try:
            # verify=False: NOAA PSL uses a cert chain not in all system stores.
            # InsecureRequestWarning suppressed globally in analyze.py.
            resp = requests.get(url, timeout=15, verify=False)
            resp.raise_for_status()
            result = parser(resp.text, list(years))
            if len(result) >= len(years) * 0.7:
                return result, url
        except Exception:
            continue
    return {}, None


def enso_correct(vals, years, enso_annual):
    """
    Remove ENSO variability from the climate series via OLS regression:
        val_i = beta0 + beta1*ENSO_i + beta2*i + epsilon_i

    beta2 = anthropogenic trend rate (ENSO variance removed).
    Returns (corrected_vals, attribution) where:
      corrected_vals : ENSO component subtracted, anthropogenic trend intact.
      attribution    : dict with enso_fraction, masking_rate, beta1.

    Returns (None, None) if fewer than 80% of years have ENSO coverage.
    """
    idx = [i for i, yr in enumerate(years) if yr in enso_annual]
    if len(idx) < len(years) * 0.8:
        return None, None

    y = vals[idx]
    t = np.array(idx, dtype=float)
    e = np.array([enso_annual[years[i]] for i in idx])

    X = np.column_stack([np.ones(len(idx)), e, t])
    coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    beta0, beta1, beta2 = float(coeffs[0]), float(coeffs[1]), float(coeffs[2])

    # Variance attribution: fraction of total variance explained by ENSO component
    enso_component = beta1 * e
    total_var = float(np.var(y, ddof=1))
    enso_var  = float(np.var(enso_component, ddof=1))
    enso_fraction = enso_var / total_var if total_var > 1e-12 else 0.0

    # Corrected series: remove ENSO component for all years
    # Years without ENSO data get beta1 * 0 (neutral ENSO assumed)
    enso_full    = np.array([enso_annual.get(yr, 0.0) for yr in years])
    corrected    = vals - beta1 * enso_full

    # Additive decomposition components for the ENSO-covered years only.
    # val = enso_component + trend_component + residual_component
    enso_series   = (beta1 * e).tolist()
    trend_series  = (beta0 + beta2 * t).tolist()
    resid_series  = (y - beta1 * e - (beta0 + beta2 * t)).tolist()
    comp_years    = [years[i] for i in idx]

    attribution = {
        "enso_fraction":      round(enso_fraction, 4),
        "beta1_enso":         round(beta1, 6),
        "beta2_anthro":       round(beta2, 6),
        "enso_component":     enso_series,
        "trend_component":    trend_series,
        "residual_component": resid_series,
        "component_years":    comp_years,
    }
    return corrected, attribution
