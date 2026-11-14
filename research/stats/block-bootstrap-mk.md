# Block Bootstrap Mann-Kendall

**Source:** Önöz & Bayazit, "Block bootstrap for Mann-Kendall trend test of serially dependent
data," *Hydrological Processes* 26(23), 3552–3560, 2012. doi:10.1002/hyp.8358

---

## Why Hamed-Rao is not enough

Hamed-Rao assumes the autocorrelation structure is AR(1): a single lag-1 coefficient captures
all dependence. This holds for temperature. It fails for:

- **Soil moisture:** long-memory process, significant lags out to 6–12 months
- **NDVI:** seasonal periodicity introduces autocorrelation at lag 12
- **Precipitation in monsoon regions:** burst structure, non-AR(1) dependence
- **ET:** driven by both temperature and precipitation, inherits complex dependence

For these series, Hamed-Rao underestimates Var(S) even after the correction, yielding
inflated z-scores and false positives. MKC3 improves on the skewness dimension; block
bootstrap improves on the dependence structure dimension. They are complementary.

---

## Block bootstrap concept

The bootstrap principle: resample data to construct an empirical null distribution without
assuming the parametric form of the dependence structure.

**Simple bootstrap (IID):** resample individual residuals with replacement. Valid only under
independence. Used in Tidemark's current Monte Carlo trajectory.

**Block bootstrap:** resample contiguous blocks of residuals. Preserves the within-block
dependence structure. As block length → 1, reduces to IID bootstrap. As block length → n,
no resampling.

For the MK S-statistic under the null:
```
S_b = Σ_{i<j} sign(ε_π(i) - ε_π(j))
```
where π is a block-bootstrap permutation of residuals. Under the true H0, the distribution
of S_b approximates the true null distribution of S.

---

## Optimal block length

**Automatic selection (Önöz & Bayazit 2012):**

```
l_opt = max(1, round(c · n^(1/3)))
```

where c is estimated from the lag-1 autocorrelation φ:

```
c = 1.75 · (2φ / (1 - φ²))^(2/3)   [Politis & Romano bandwidth estimator]
```

For φ = 0: l_opt = 1 (reduces to IID bootstrap).
For φ = 0.5, n=45: l_opt ≈ 4.
For φ = 0.8, n=45: l_opt ≈ 8.

---

## Algorithm

```python
import numpy as np
from scipy import stats

def block_bootstrap_mk_pvalue(x, n_boot=2000, seed=42):
    """
    Block bootstrap p-value for Mann-Kendall trend test.
    More accurate than Hamed-Rao for ARMA/long-memory series.
    
    Returns: p_value, z_score (using block bootstrap variance)
    """
    rng = np.random.default_rng(seed)
    n = len(x)
    
    # Sen slope and residuals
    slopes = [(x[j]-x[i])/(j-i) for i in range(n-1) for j in range(i+1,n)]
    beta = float(np.median(slopes))
    residuals = x - beta * np.arange(n)
    
    # Lag-1 autocorrelation of residuals
    phi = float(np.corrcoef(residuals[:-1], residuals[1:])[0,1])
    phi = np.clip(phi, -0.99, 0.99)
    
    # Optimal block length (Politis-Romano)
    if abs(phi) < 0.05:
        l = 1
    else:
        c = 1.75 * (2*phi / (1 - phi**2))**(2/3)
        l = max(1, int(round(c * n**(1/3))))
    l = min(l, n // 4)   # cap at n/4 to ensure enough blocks
    
    # Observed S statistic
    pairs = [(i, j) for i in range(n-1) for j in range(i+1, n)]
    S_obs = float(sum(np.sign(x[j] - x[i]) for i,j in pairs))
    
    # Block bootstrap null distribution
    null_S = []
    for _ in range(n_boot):
        # Sample blocks with replacement
        n_blocks = int(np.ceil(n / l))
        starts = rng.integers(0, n - l + 1, size=n_blocks)
        resampled = np.concatenate([residuals[s:s+l] for s in starts])[:n]
        
        # Reconstruct series under H0 (no trend, preserve dependence)
        s_b = float(sum(np.sign(resampled[j] - resampled[i]) for i,j in pairs))
        null_S.append(s_b)
    
    null_S = np.array(null_S)
    
    # Two-sided p-value from empirical null
    p = float(np.mean(np.abs(null_S) >= abs(S_obs)))
    p = max(p, 1.0 / n_boot)   # floor at 1/n_boot
    
    # Bootstrap variance for z-score
    var_boot = float(np.var(null_S))
    if S_obs > 0:
        z = (S_obs - 1) / np.sqrt(var_boot)
    elif S_obs < 0:
        z = (S_obs + 1) / np.sqrt(var_boot)
    else:
        z = 0.0
    
    return p, z, l   # also return block length used
```

---

## When to use block bootstrap vs Hamed-Rao

| Condition | Method |
|---|---|
| φ < 0.1, Gaussian residuals | Hamed-Rao (faster, accurate) |
| φ > 0.3, any residuals | Block bootstrap (more reliable) |
| Long-memory suspected | Block bootstrap |
| Skewed residuals, φ > 0.1 | MKC3 + block bootstrap (both apply) |

Auto-selection rule for Tidemark:
```python
if abs(phi) > 0.3 or ljung_box_p < 0.05:
    use block bootstrap
else:
    use hamed-rao (possibly + mkc3 if skewness > 0.5)
```

---

## Relation to current Tidemark bootstrap

Current Monte Carlo trajectory (bootstrap.py) resamples residuals IID — correct for
the trajectory simulation but does not give the correct p-value under autocorrelation.

Block bootstrap gives:
1. A correct p-value (what this doc covers)
2. Can also be used for the trajectory simulation by block-resampling in the Monte Carlo
   loop instead of IID resampling — improves trajectory accuracy for autocorrelated series

---

## Implementation status

- **R:** `modifiedmk::bbsmk` (2000 replicates, automatic block length)
- **Python:** no package. The function above is the full implementation.
- **Tidemark:** not yet implemented
