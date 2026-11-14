# Weatherhead (1998) detection time formula

Source: Weatherhead et al., JGR Atmospheres, 1998, DOI 10.1029/98JD00995.
Used by NASA Goddard atmospheric scientists to estimate how many years of satellite data are needed.

---

## formula

```
n* = (3.3 · σ_N / |ω|)^(2/3) · ((1+φ)/(1-φ))^(1/3)
```

| symbol | meaning |
|---|---|
| n* | years of data needed to detect the trend at ~90% probability |
| σ_N | standard deviation of noise (annual residuals from detrended series) |
| ω | trend magnitude (units/year, same as σ_N) |
| φ | lag-1 autocorrelation of noise residuals |

The 3.3 factor: z_α/2 + z_β ≈ 1.96 + 1.28 = 3.24 ≈ 3.3 (for α=0.05, power=90%).

---

## difference from the MK analytical formula

Weatherhead is derived from OLS regression (linear model with AR(1) noise).
The MK analytical formula (see z-growth-analytical.md) is derived from the MK pairwise comparison structure.

They are not the same test but they answer the same question. For Gaussian noise:
- MK asymptotic relative efficiency vs OLS = 3/π ≈ 0.955
- MK needs ~5% more data than OLS for same power at Gaussian data
- Both give crossing year estimates within 2-3 years of each other

Weatherhead adds the ACF correction `((1+φ)/(1-φ))^(1/3)`. The MK formula doesn't.

---

## autocorrelation correction worked out

For φ = 0 (no autocorrelation): correction = 1.0 (no effect)
For φ = 0.2: correction = (1.2/0.8)^(1/3) = 1.5^(1/3) = 1.145 → 14.5% more years needed
For φ = 0.3: correction = (1.3/0.7)^(1/3) = 1.857^(1/3) = 1.229 → 23% more years needed
For φ = 0.5: correction = (1.5/0.5)^(1/3) = 3^(1/3) = 1.442 → 44% more years needed

For annual temperature (φ ≈ 0.2-0.3): autocorrelation adds 14-23% to the required record length.
For annual precipitation (φ ≈ 0-0.1): negligible effect.

---

## applying Weatherhead to MK

Weatherhead is derived for OLS but the inputs (σ_N, ω, φ) are available from the MK analysis:
- σ_N = std(residuals) where residuals = x - (intercept + slope·t), using Sen's slope
- ω = Sen's slope (same as β in the Weatherhead notation)
- φ = __acf(residuals, nlags=1)[1]

This is an approximation: using OLS-derived formula with MK-estimated parameters. For annual data
the approximation is good because:
1. OLS slope ≈ Sen's slope for data without extreme outliers
2. The autocorrelation structure of residuals is the same regardless of how slope was estimated

---

## four-way comparison in output

For a not-yet-significant trend:

```
significance trajectory:
  analytical MK     2031   (n^1.5 growth formula, assumes Gaussian IID)
  Weatherhead 1998  2033   (OLS detection time with ACF correction, φ=0.24)
  Monte Carlo       2031   (n=1000, empirical bootstrap from residuals)
  CRB lower bound   2030   (Fisher information floor, any test)
  methods agree → high confidence
```

For arid precipitation (skewed noise):

```
significance trajectory:
  analytical MK     2045   (assumes Gaussian IID, invalid here)
  Weatherhead 1998  2046   (OLS detection time, also assumes Gaussian)
  Monte Carlo       2060   (n=1000, empirical bootstrap, captures real distribution)
  CRB lower bound   2041   (Fisher information floor, correct for skewed noise)
  methods diverge: 15 years
  reason: residual skewness=1.95, normality p<0.001 → non-Gaussian noise delays significance
  trust: Monte Carlo
```

The divergence is the signal. It tells the user WHY the trend is hard to confirm.

---

## Python implementation

```python
def weatherhead_detection_years(sigma_n, omega, phi):
    """
    Returns years needed to detect trend omega at ~90% power.
    sigma_n: std of detrended residuals
    omega: Sen's slope (same units/year as sigma_n)
    phi: lag-1 ACF of residuals
    """
    if abs(omega) < 1e-12:
        return float('inf')
    phi = max(-0.99, min(0.99, phi))   # clamp: formula undefined at ±1
    base = (3.3 * sigma_n / abs(omega)) ** (2/3)
    acf_correction = ((1 + phi) / (1 - phi)) ** (1/3)
    return base * acf_correction
```

---

## literature confirmation

Weatherhead (1998) is cited by:
- NASA Goddard stratospheric ozone group (Jackman et al.)  
- AMT satellite stability study (2024)  
- Ocean biogeochemistry detection times (PMC 4785610)  
- Long Island Sound environmental monitoring

It is the standard formula in atmospheric science for "how many years of satellite data do we need."  
No existing user-facing climate tool implements it directly against live API data.
