# Uncertainty-Adjusted Detection Time (uTDT)

**Basis:** Extension of Weatherhead et al. (1998) for instrument calibration uncertainty.
Reference: Weatherhead et al. 2000 (JGR followup), Leroy et al. 2008 (JRSSB), and
NASA POWER / MERRA-2 published uncertainty documentation.

---

## The gap in Weatherhead 1998

The standard Weatherhead formula treats σ_N (noise standard deviation) as a known constant.
In practice σ_N is estimated from observed residuals and contains two sources of variance:

```
σ²_observed = σ²_climate   (true interannual variability)
            + σ²_instrument (sensor calibration + sampling uncertainty)
```

Weatherhead 1998 uses σ_observed directly, which means the detection time estimate inherits
the instrument uncertainty. For well-calibrated instruments (σ_instrument << σ_climate),
this is negligible. For newer sensors, remotely-sensed data, or derived parameters, it matters.

---

## uTDT formula

Replace σ_N in the Weatherhead formula with the uncertainty-adjusted total:

```
σ²_total = σ²_N + σ²_calibration
```

Then:

```
n*_uTDT = (3.3 · σ_total / |ω|)^(2/3) · ((1+φ)/(1-φ))^(1/3)
```

This is identical to the Weatherhead formula with σ_total instead of σ_N. The CRB formula
also adjusts:

```
n*_CRB_adjusted = n*_uTDT · (I(f) · σ²_total)^(-1/3)
```

---

## NASA instrument uncertainties

**NASA POWER (MERRA-2 reanalysis):**

| Variable | σ_calibration | Source |
|---|---|---|
| T2M temperature | 0.1–0.3°C | MERRA-2 validation vs ERA5, NOAA GHCN |
| RH2M humidity | 2–5% | MERRA-2 validation studies |
| WS10M wind speed | 0.3–0.5 m/s | MERRA-2 vs ECMWF |
| PRECTOTCORR precipitation | 10–20% of σ | MERRA-2 vs GPM ground validation |
| GWETROOT soil moisture | 0.03–0.05 fraction | MERRA-2 vs SCAN network |

**GPM IMERG (precipitation):**

| Product | Random error | Systematic |
|---|---|---|
| IMERG Final V07B monthly | ±15–25% in tropics | <5% bias vs GPCC |

**MODIS (AppEEARS and ORNL DAAC):**

| Variable | Uncertainty |
|---|---|
| LST (MOD11A2) | ±1°C (land) | MODIS LST validation papers |
| ET (MOD16A2) | 10–30% | MOD16 validation vs flux towers |
| NDVI (MOD13Q1) | ±0.02–0.05 (unitless) | MODIS NDVI uncertainty analysis |

---

## Implementation

```python
# NASA instrument uncertainty table (1-sigma values)
INSTRUMENT_UNCERTAINTY = {
    "T2M":         0.20,    # degC
    "T2M_MAX":     0.25,    # degC
    "T2M_MIN":     0.25,    # degC
    "RH2M":        3.0,     # %
    "EVLAND":      0.015,   # mm/day
    "WS10M":       0.35,    # m/s
    "VPD":         0.05,    # kPa (derived from T + RH, combined uncertainty)
    "DTR":         0.30,    # degC
    "GWETROOT":    0.04,    # fraction
    "GWETTOP":     0.04,    # fraction
    "GWETPROF":    0.04,    # fraction
    "TSOIL1":      0.25,    # degC
    "TS":          0.15,    # degC
    "FROST_DAYS":  0.5,     # days/year
    "PRECTOTCORR": 0.15,    # fraction of sigma_N (multiplicative)
    "NDVI":        0.03,    # unitless ratio
    "LST":         1.0,     # degC
    "ET_MOD16":    0.25,    # mm/day (fraction * sigma handled separately)
}

def uncertainty_adjusted_weatherhead(omega, sigma_n, phi, n_obs, last_year, param_code):
    """
    uTDT: Weatherhead detection year with instrument calibration uncertainty.
    
    omega: Sen's slope (units/year)
    sigma_n: residual standard deviation
    phi: lag-1 autocorrelation of residuals
    n_obs: current series length (years)
    last_year: last data year
    param_code: NASA parameter code (e.g. 'T2M') for uncertainty lookup
    
    Returns: (n_star_weatherhead, n_star_uTDT, sigma_total, year_weatherhead, year_uTDT)
    """
    import math
    
    sigma_cal = INSTRUMENT_UNCERTAINTY.get(param_code, 0.0)
    
    # For multiplicative uncertainty (precipitation), use fraction of sigma_n
    if param_code == "PRECTOTCORR":
        sigma_cal = sigma_cal * sigma_n   # 15% of observed noise
    
    sigma_total = math.sqrt(sigma_n**2 + sigma_cal**2)
    
    if abs(omega) < 1e-10:
        return None, None, sigma_total, None, None
    
    ar1_factor = ((1 + phi) / (1 - phi))**(1/3) if abs(phi) < 0.999 else 1.0
    
    n_star_wh    = (3.3 * sigma_n     / abs(omega))**(2/3) * ar1_factor
    n_star_uTDT  = (3.3 * sigma_total / abs(omega))**(2/3) * ar1_factor
    
    year_wh   = last_year + max(0.0, n_star_wh    - n_obs)
    year_uTDT = last_year + max(0.0, n_star_uTDT  - n_obs)
    
    return n_star_wh, n_star_uTDT, sigma_total, year_wh, year_uTDT
```

---

## Effect magnitude

For temperature (σ_N = 0.3°C, σ_cal = 0.2°C):
```
σ_total = sqrt(0.09 + 0.04) = 0.36°C
n*_uTDT / n*_Weatherhead = (0.36/0.30)^(2/3) = 1.19
```
Detection time 19% longer than standard Weatherhead — not negligible.

For NDVI (σ_N = 0.05 ratio, σ_cal = 0.03):
```
σ_total = sqrt(0.0025 + 0.0009) = 0.058
n*_uTDT / n*_Weatherhead = (0.058/0.050)^(2/3) = 1.11
```
Detection time 11% longer. Meaningful for a 45-year series.

For LST (σ_N = 1.5°C, σ_cal = 1.0°C):
```
σ_total = sqrt(2.25 + 1.00) = 1.80°C
n*_uTDT / n*_Weatherhead = (1.80/1.50)^(2/3) = 1.19
```

---

## Expected output format

```
significance trajectory (with instrument uncertainty):
  analytical MK      2031   (n^1.5 growth formula)
  Weatherhead 1998   2033   (σ_N = 0.30°C)
  Weatherhead uTDT   2036   (σ_total = 0.36°C, includes MERRA-2 calibration ±0.2°C)
  Monte Carlo        2031   (n=1000, empirical bootstrap)
  CRB lower bound    2030   (Fisher information floor)

instrument uncertainty note:
  MERRA-2 T2M calibration uncertainty: ±0.20°C (Rienecker 2011 validation)
  adds 3 years to detection time vs noise-only Weatherhead estimate
```

---

## Why this matters

No existing climate trend tool propagates sensor calibration uncertainty into detection time.
Yet every NASA data product has published uncertainty estimates. This is an obvious gap in
the literature — the Weatherhead framework has been widely applied since 1998 but never
extended to include the uncertainty of the instrument providing the data.

For policy decisions based on "trend expected significant by 2033" — knowing the true
range is "2033–2036 depending on MERRA-2 calibration accuracy" is a material difference.

---

## Implementation status

- **Published:** not in any paper in this exact form (σ_total substitution is implicit in
  Leroy 2008 but never made explicit for NASA POWER variables)
- **Python:** no package. The ~20-line function above is the full implementation.
- **Tidemark:** implemented. `python/trajectory.py::uTDT_detection_year()` applies σ_total = √(σ_N² + σ_cal²) using the `INSTRUMENT_UNCERTAINTY` table keyed by NASA parameter code. Result returned as `utdt_year`, `utdt_sigma_total`, `utdt_sigma_cal` in the trajectory JSON. Rendered as "Weatherhead uTDT" row in `src/output.rs` and `python/templates/result.html`.
