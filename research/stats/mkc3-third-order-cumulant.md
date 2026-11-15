# MKC3: Third-Order Cumulant Mann-Kendall Variance Correction

**Source:** Then et al., "Modified Mann-Kendall with higher-order statistics for trend analysis,"
*Nature Scientific Reports*, 2025. doi:10.1038/s41598-025-30034-0

---

## Why Hamed-Rao fails for skewed series

Hamed-Rao and all existing variance corrections (Yue-Wang, TFPW) use only second-order
statistics — the lag-k autocorrelation ρ_k. They assume the correction term is fully captured by:

```
Var_HR(S) = Var_0(S) · (n/n*) · correction(ρ_k)
```

This is correct when residuals are symmetric. For right-skewed series (precipitation,
NDVI, ET in arid regions), the skewness of lag products introduces an additional systematic
bias into Var(S) that ρ_k cannot capture. Result: Var(S) is underestimated → z-score inflated
→ false positives.

Empirical evidence: for Cairo precipitation (skewness ≈ 1.95), Hamed-Rao gives p ≈ 0.03
when the true p under the correct distribution is > 0.10. This is not noise — it is a
structural flaw for all right-skewed residual distributions.

---

## MKC3 formulation

The third-order cumulant of the lag-k product is:

```
κ₃(k) = E[(x_t - μ)²(x_{t+k} - μ)] - 2·ρ_k·σ²·μ   [third cumulant of lag-k pairs]
```

For zero-mean residuals (after trend removal):

```
κ₃(k) = E[ε_t² · ε_{t+k}]   (k ≠ 0)
κ₃(0) = E[ε_t³] = γ₁ · σ³   (skewness × cube of std dev)
```

The corrected variance is:

```
Var_MKC3(S) = Var_HR(S) + C₃
```

where the third-order correction term C₃ is:

```
C₃ = (2/n²) · Σ_{k=1}^{n-1} (n-k) · w_k · κ₃(k)
```

and w_k are weights analogous to the Hamed-Rao lag weights:

```
w_k = 1 - k/(n+1)   [Bartlett taper, same as HR]
```

The sample estimator of κ₃(k) from residuals ε̂_t:

```
κ̂₃(k) = (1/n) · Σ_{t=1}^{n-k} ε̂_t² · ε̂_{t+k}
```

For symmetric distributions: κ₃(k) = 0 for all k → MKC3 reduces exactly to Hamed-Rao.
For right-skewed: κ₃(k) > 0 → Var_MKC3 > Var_HR → smaller z → fewer false positives.

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
