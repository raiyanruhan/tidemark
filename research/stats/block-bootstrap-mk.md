> **Historical design note. Superseded; see research/whitepaper for the current methods.**

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
import math
import numpy as np

def block_bootstrap_mk_pvalue(x, n_boot=2000, seed=42):
    """
    Block bootstrap p-value for Mann-Kendall trend test.
    Önöz & Bayazit 2012, Hydrol. Process. 26(23):3552-3560.
    More accurate than Hamed-Rao for ARMA/long-memory series.
    Returns (p_value, z_score, block_len).
    """
    rng = np.random.default_rng(seed)
    n = len(x)

    # Sen slope → residuals (vectorized via triu_indices)
    i_idx, j_idx = np.triu_indices(n, k=1)
    slopes = (x[j_idx] - x[i_idx]) / (j_idx - i_idx).astype(float)
    beta = float(np.median(slopes))
    residuals = x - beta * np.arange(n, dtype=float)

    # Lag-1 ACF → Politis-Romano optimal block length
    # abs() on base: negative phi raises complex without it
    phi = float(np.clip(np.corrcoef(residuals[:-1], residuals[1:])[0, 1], -0.99, 0.99))
    if abs(phi) < 0.05:
        block_len = 1
    else:
        c = 1.75 * abs(2.0 * phi / (1.0 - phi ** 2)) ** (2.0 / 3.0)
        block_len = max(1, int(round(c * n ** (1.0 / 3.0))))
    block_len = min(block_len, n // 4)

    # Observed S statistic (vectorized)
    S_obs = float(np.sum(np.sign(x[j_idx] - x[i_idx])))

    # Block bootstrap null distribution
    null_S = np.empty(n_boot)
    n_blocks = int(math.ceil(n / block_len))
    for b in range(n_boot):
        starts = rng.integers(0, n - block_len + 1, size=n_blocks)
        resampled = np.concatenate([residuals[s:s + block_len] for s in starts])[:n]
        null_S[b] = float(np.sum(np.sign(resampled[j_idx] - resampled[i_idx])))

    # Two-sided p-value from empirical null; floor at 1/n_boot
    p = max(float(np.mean(np.abs(null_S) >= abs(S_obs))), 1.0 / n_boot)

    # Z with MK continuity correction from bootstrap variance
    var_boot = float(np.var(null_S))
    if var_boot > 0:
        z = (S_obs - (1.0 if S_obs > 0 else -1.0 if S_obs < 0 else 0.0)) / math.sqrt(var_boot)
    else:
        z = 0.0

    return p, z, block_len
```

---

## When to use block bootstrap vs Hamed-Rao

| Condition | Method |
|---|---|
| φ < 0.1, Gaussian residuals | Hamed-Rao (faster, accurate) |
| φ > 0.3, any residuals | Block bootstrap (more reliable) |
| Long-memory suspected | Block bootstrap |
| Skewed residuals, φ > 0.1 | MKC3 + block bootstrap (both apply) |

Auto-selection rule (implemented in `python/analyze.py`):
```python
if abs(phi) > 0.3:
    use block bootstrap  # → "Block Bootstrap MK (Önöz & Bayazit 2012, block length=N)"
elif abs(skewness) > 0.5 and n >= 20:
    use mkc3             # → "Modified Mann-Kendall (MKC3, Then 2025)"
else:
    use hamed-rao        # → "Modified Mann-Kendall (Hamed-Rao, lag=3)"
```

Block bootstrap takes priority over MKC3 when |φ| > 0.3: it is model-free and handles
both autocorrelation structure and non-Gaussian residuals simultaneously. For moderate φ
with high skewness (the "both apply" case in the table above), block bootstrap is the
correct single choice.

---

## Relation to current Tidemark bootstrap

Current Monte Carlo trajectory resamples residuals IID — correct for the trajectory
simulation but does not give the correct p-value under autocorrelation. Block bootstrap
fixes the p-value path; the trajectory simulation is a separate concern.

Block bootstrap could also improve trajectory accuracy by block-resampling in the Monte
Carlo loop instead of IID resampling — not yet implemented for trajectories.

---

## Implementation status

- **R:** `modifiedmk::bbsmk` (2000 replicates, automatic block length)
- **Python:** no package. `block_bootstrap_mk_pvalue()` in `python/stats.py` is the first open Python implementation.
- **Tidemark:** ✓ implemented — `python/stats.py:block_bootstrap_mk_pvalue()`, dispatched from `python/analyze.py` when |φ| > 0.3
