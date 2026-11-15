# MKC3: Third-Order Cumulant Mann-Kendall Variance Correction

**Source:** Then et al., "Modified Mann-Kendall with higher-order statistics for trend analysis,"
*Nature Scientific Reports*, 2025. doi:10.1038/s41598-025-30034-0

---

## Verified against the paper (2026-11-15, PMC12775442)

Then & Abdul Halim, Sci. Rep. 16, 500 (2025). Open access, equations are images on PMC.
The earlier version of this note (skewness argument, kappa3(k) = E[eps_t^2 eps_{t+k}],
additive 2/n^2 * sum (n-k) w_k kappa3(k), Bartlett weights, lag cutoff 3) is NOT in the paper.

```
Eq 18  n/n*_s = 1 + 2 * sum_{i=1}^{n-1} (n-i)(n-i-1)(n-i-2) rho_s(i) / (n(n-1)(n-2))
       rho_s = lag-i autocorrelation of rank-detrended data (MKRD = Hamed-Rao 1998);
       pymannkendall default: all lags, keep only |rho| > z_.975/sqrt(n)
Eq 19  C3(t1,t2) = E[x(t) x(t+t1) x(t+t2)]            zero-mean stationary series
Eq 20  C3 estimator, detrended + standardized series, max lag M
Eq 21  Phi_3 = 1/(N-2) * sum_{k=1}^{N-2} x(t_k) x(t_k+1) x(t_k+2)     lags (1,2)
Eq 22  n/n*' = n/n*_s + Phi_3
Eq 23  Var'(S) = Var(S) * n/n*'
```

Z uses Var'(S) in place of the MKRD variance (their Eq 8). Phi_3 is dimensionless
(standardized), so it multiplies the IID variance, not an additive data-unit term.

Ambiguity: prose says "the rank-detrended data are standardized" before Eq 21, the
estimator text says "detrended and standardized". Code uses standardized ranks.
Both readings give the same null rejection rates within Monte Carlo error.

The paper does not motivate the term by skewness; it targets nonlinearity ("if
nonlinearity does not exist, the third-order cumulant is zero"). Its own Table 4 reports
Type I error of 0.09-0.37 for MKC3 (n=30..200), and states MKC3 does not do well at n=30.
Null false-positive rates for skewed (lognormal) noise are in the commit message; MKC3 as
published is anti-conservative at n<=60, more so than the previous implementation.

---

## When to use MKC3 vs Hamed-Rao

| Series type | Recommendation |
|---|---|
| Temperature (near-Gaussian residuals) | Hamed-Rao and MKC3 agree; either works |
| Precipitation (right-skewed) | MKC3; Hamed-Rao gives inflated z-scores |
| NDVI (right-skewed in dry regions) | MKC3 |
| ET (log-normal residuals) | MKC3 |
| Relative humidity (bounded, mild skew) | MKC3 marginally better |

Decision rule: if `abs(skewness of residuals) > 0.5`, use MKC3. Otherwise Hamed-Rao.
Tidemark already computes residuals and skewness; the switch is automatic.

---

## Implementation sketch

```python
def mkc3_variance(residuals, n):
    """
    MKC3 variance correction for Mann-Kendall S-statistic.
    Returns Var_MKC3(S) / Var_0(S) correction factor.
    
    residuals: array of detrended residuals (Sen slope removed)
    n: series length
    """
    import numpy as np
    eps = residuals - np.mean(residuals)
    sigma2 = np.var(eps)
    
    # Hamed-Rao lag-k autocorrelations
    rho = np.array([np.corrcoef(eps[:-k], eps[k:])[0,1] if k < n else 0.0
                    for k in range(1, n)])
    
    # Hamed-Rao correction factor (sum over lags with Bartlett taper)
    n_star_inv = 1.0
    for k in range(1, n):
        w = 1.0 - k / (n + 1)
        n_star_inv += (2.0 / n) * (n - k) * w * rho[k-1]
    
    # Third-order cumulant correction
    C3 = 0.0
    for k in range(1, n):
        kappa3_k = np.mean(eps[:-k]**2 * eps[k:])
        w = 1.0 - k / (n + 1)
        C3 += (2.0 / n**2) * (n - k) * w * kappa3_k
    
    # Var_0(S) = n(n-1)(2n+5)/18
    var0 = n * (n - 1) * (2*n + 5) / 18.0
    
    var_hr = var0 * n_star_inv
    var_mkc3 = var_hr + C3 * (n**2)   # scale C3 to S units
    
    return var_mkc3

def mk_z_mkc3(x):
    """Mann-Kendall z-score using MKC3 variance correction."""
    import numpy as np
    n = len(x)
    S = sum(np.sign(x[j] - x[i]) for i in range(n-1) for j in range(i+1, n))
    
    # Sen slope residuals
    slopes = [(x[j]-x[i])/(j-i) for i in range(n-1) for j in range(i+1,n)]
    beta = np.median(slopes)
    residuals = x - beta * np.arange(n)
    
    var_s = mkc3_variance(residuals, n)
    
    if S > 0:
        z = (S - 1) / np.sqrt(var_s)
    elif S < 0:
        z = (S + 1) / np.sqrt(var_s)
    else:
        z = 0.0
    return z, S, beta
```

---

## Implementation status

- **Published:** 2025 (Malaysia regional precipitation application only)
- **Python:** No package. Tidemark is first open implementation.
- **R:** No package.
- **Tidemark:** Implemented.

Implemented as `mkc3_variance(residuals, n)` and `mk_z_mkc3(vals)` in `python/stats.py`.
Dispatch in `python/analyze.py`: `abs(skew(residuals)) > 0.5 and n >= 20` triggers MKC3;
else Hamed-Rao. Output: `src/output.rs` reads `json["method"]` and prints on the `test`
line. Result HTML shows "Test method" row in the stats table.

---

## Effect on Tidemark outputs

For symmetric series: z-score unchanged, p-value unchanged.
For precipitation, NDVI, ET with skewness > 0.5:
- z-score decreases (more conservative)
- p-value increases (fewer false positives)
- Monte Carlo and MKC3 will agree more closely (MC already captures distribution shape)
- Divergence between analytical and MC will decrease

The MKC3 correction directly closes the gap between the analytical method and Monte Carlo
for non-Gaussian series, which strengthens the credibility of the four-way comparison.

---

## Relation to existing Tidemark research

- `detection-floor.md`: β_min uses Var(S) in denominator. MKC3 gives more accurate Var(S) → more accurate floor.
- `z-growth-analytical.md`: the n^(3/2) growth formula uses expected z under H1. Under MKC3, C = 1/(2√π) still holds for the mean; variance correction affects the denominator only.
- `optimal-score-are.md`: MKC3 is a variance correction; ARE uses the optimal score function. These are orthogonal improvements that stack.
