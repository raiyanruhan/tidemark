# Partial Mann-Kendall: ENSO Correction

**Source:** Libiseller & Grimvall, "Performance of Partial Mann-Kendall Test for Trend Detection
in the Presence of Covariates," *Environmetrics* 13(1), 71–84, 2002.

**Climate application:** Tellusjournal 2020, doi:10.1080/16000870.2020.1833584 — Baluchistan
precipitation with ENSO-MEI as covariate.

---

## The problem

Precipitation, temperature, and humidity are partially driven by ENSO (El Niño–Southern
Oscillation). A Mann-Kendall test on the raw series conflates:
1. Long-term anthropogenic trend
2. ENSO-induced low-frequency variability

If ENSO has a trend (e.g., more frequent El Niño events 1981–2025), it appears as a spurious
trend in any ENSO-correlated variable. Conversely, if ENSO masks an anthropogenic trend,
the raw MK test may miss it.

The partial MK test removes the ENSO signal analytically before testing for trend.

---

## Formulation

Let x_t = target variable (e.g., precipitation anomaly at year t).
Let y_t = ENSO index (ONI or MEI) at year t.

Compute three concordance sums over all pairs (i, j) with i < j:

```
S_x  = Σ sign(x_j - x_i)   [MK statistic for x]
S_y  = Σ sign(y_j - y_i)   [MK statistic for y]
S_xy = Σ sign(x_j - x_i) · sign(y_j - y_i)   [cross-concordance]
```

The partial MK statistic removing the effect of y:

```
S_partial = S_x - (S_xy / S_y) · S_y
           = S_x - S_xy · sign(S_y)   [simplified for unit normalization]
```

More precisely, following Libiseller & Grimvall (2002), the partial Kendall tau is:

```
τ_partial = (τ_x - τ_xy · τ_y) / sqrt((1 - τ_xy²)(1 - τ_y²))
```

where τ_x = S_x / n(n-1)/2, τ_y = S_y / n(n-1)/2, τ_xy = S_xy / n(n-1)/2.

Variance of S_partial under H0 (no trend in x after controlling for y):

```
Var(S_partial) = Var(S_x) · (1 - ρ_kendall(x,y)²)
```

Z-score:

```
z_partial = S_partial / sqrt(Var(S_partial))
```

---

## ENSO index sources

**Oceanic Niño Index (ONI):** NOAA CPC free API.
```
https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php
```
3-month running mean of ERSST v5 SST anomalies in Niño 3.4 region (5°N–5°S, 120–170°W).
Available 1950–present, monthly.

**Multivariate ENSO Index (MEI.v2):** NOAA PSL.
```
https://psl.noaa.gov/enso/mei/
```
First principal component of SSTA + SLP + surface winds + OLR. More comprehensive.

For Tidemark: download ONI at analysis time, cache to `~/.tidemark/cache/oni_{year}.json`.
Annual mean ONI per year for annual-resolution MK. Seasonal mean ONI for seasonal MK.

---

## Implementation sketch

```python
import numpy as np

def partial_mk(x_series, y_series):
    """
    Partial Mann-Kendall removing covariate y from trend test of x.
    
    x_series, y_series: arrays of same length (annual values)
    Returns: z_partial, p_partial, tau_partial, tau_xy
    """
    from scipy import stats
    n = len(x_series)
    assert len(y_series) == n
    
    pairs = [(i, j) for i in range(n-1) for j in range(i+1, n)]
    
    sx  = sum(np.sign(x_series[j] - x_series[i]) for i,j in pairs)
    sy  = sum(np.sign(y_series[j] - y_series[i]) for i,j in pairs)
    sxy = sum(np.sign(x_series[j]-x_series[i]) * np.sign(y_series[j]-y_series[i])
              for i,j in pairs)
    
    total = n * (n - 1) / 2
    tau_x  = sx  / total
    tau_y  = sy  / total
    tau_xy = sxy / total
    
    # Partial tau (Libiseller & Grimvall eq. 3)
    denom = np.sqrt((1 - tau_xy**2) * (1 - tau_y**2))
    tau_partial = (tau_x - tau_xy * tau_y) / denom if denom > 0 else tau_x
    
    # Variance of S_x under independence, corrected for covariate
    var_sx = n * (n - 1) * (2*n + 5) / 18.0
    var_partial = var_sx * (1 - tau_xy**2)
    
    if sx > 0:
        z = (sx - 1) / np.sqrt(var_partial)
    elif sx < 0:
        z = (sx + 1) / np.sqrt(var_partial)
    else:
        z = 0.0
    
    p = 2 * stats.norm.sf(abs(z))
    return z, p, tau_partial, tau_xy


def fetch_oni_annual(start_year, end_year):
    """
    Download NOAA ONI index, return dict {year: mean_oni}.
    Cached to ~/.tidemark/cache/oni.json.
    """
    import requests, json, os
    from pathlib import Path
    
    cache = Path.home() / ".tidemark" / "cache" / "oni.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    
    if cache.exists():
        with open(cache) as f:
            return json.load(f)
    
    # NOAA CPC ONI table (plain text)
    url = ("https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/"
           "ensostuff/detrend.nino34.ascii.txt")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    
    annual = {}
    for line in r.text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0].isdigit():
            year = int(parts[0])
            try:
                vals = [float(v) for v in parts[2:14] if v != '-99.9']
                if vals:
                    annual[year] = float(np.mean(vals))
            except ValueError:
                continue
    
    with open(cache, 'w') as f:
        json.dump(annual, f)
    return annual
```

---

## Expected output format

```
trend analysis   Dhaka rainfall   1981-2025
----------------------------------------------------
raw MK           tau=-0.09   z=-0.84   p=0.401   not significant
ENSO-corrected   tau=-0.14   z=-1.98   p=0.048   ✓ significant

ENSO correlation   tau_xy = 0.31   (moderate, positive coupling)
ENSO explains ~26% of concordance variance

interpretation: anthropogenic drying trend exists but is masked by ENSO
               correlation in raw test. Partial MK isolates the signal.
```

---

## Relation to other Tidemark methods

- Partial MK z feeds into the same four-way trajectory as the standard MK z.
  Report both: raw trajectory and ENSO-corrected trajectory.
- If partial z >> raw z: ENSO is masking the trend. Raw MK underestimates urgency.
- If partial z << raw z: ENSO trend is driving the apparent signal. Raw MK overstates.
- The gap between raw and partial is itself informative: quantifies ENSO's share.

---

## Implementation status

- **R:** `trend::partial.mk.test` — implemented
- **Python:** not in pymannkendall, not in scipy
- **Tidemark:** not yet implemented
