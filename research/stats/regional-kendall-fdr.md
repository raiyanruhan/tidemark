# Regional Mann-Kendall and Field Significance via FDR

**Source (regional MK):** Helsel & Frans, "Regional Mann-Kendall Test for Trend Detection,"
*Environmental Science & Technology* 40(13), 4066–4073, 2006.

**Source (field significance):** Huth, Pokorná, Kyselý, "Testing for Trends on a Regional
Scale: Beyond Local Significance," *Journal of Climate* 34(13), 5389–5404, 2021.
doi:10.1175/JCLI-D-19-0960.1

---

## The multiple testing problem

When running Mann-Kendall independently on 10 cities, with α=0.05 per test:
- Expected number of false positives under H0: 0.05 × 10 = 0.5
- P(at least one false positive) = 1 − 0.95^10 = 40%

If 3 out of 10 cities show significant trends, is that signal or noise?

This is the **multiple testing problem** (also called "field significance" in climate science).
No existing live-data climate tool addresses it.

---

## Benjamini-Hochberg FDR correction

**False Discovery Rate (FDR)** controls the expected proportion of false positives among
all rejected hypotheses. For climate science where some trends ARE real, FDR is preferred
over Bonferroni (which is too conservative).

Procedure for k tests with p-values p₁ ≤ p₂ ≤ ... ≤ p_k:

```
Reject all H_i where p_i ≤ (i/k) · α
```

```python
import numpy as np

def fdr_correction(pvalues, alpha=0.05):
    """
    Benjamini-Hochberg FDR correction.
    Returns: reject_array (bool), adjusted_pvalues
    """
    k = len(pvalues)
    order = np.argsort(pvalues)
    sorted_p = np.array(pvalues)[order]
    
    threshold = (np.arange(1, k+1) / k) * alpha
    reject_sorted = sorted_p <= threshold
    
    # Find the largest i where p_i <= threshold, reject all below
    if reject_sorted.any():
        last = np.where(reject_sorted)[0][-1]
        reject_sorted[:last+1] = True
    
    # Adjusted p-values (BH)
    adjusted = np.minimum.accumulate((sorted_p * k / np.arange(1, k+1))[::-1])[::-1]
    adjusted = np.minimum(adjusted, 1.0)
    
    reject = np.empty(k, dtype=bool)
    reject[order] = reject_sorted
    adj_p = np.empty(k)
    adj_p[order] = adjusted
    
    return reject, adj_p
```

---

## Regional Mann-Kendall test

The regional MK test pools concordance information across all stations and tests whether
the MAJORITY DIRECTION is consistent, not whether each site is independently significant.

For stations s=1..m, each with n_s observations:

```
S_total = Σ_s S_s   [sum of all site-level MK statistics]
Var(S_total) = Σ_s Var(S_s) + 2·Σ_{s<t} Cov(S_s, S_t)
```

The spatial covariance term Cov(S_s, S_t) is estimated from the data:

```
Cov(S_s, S_t) = (n_s·n_t/4) · (τ_{st})
```

where τ_{st} is the Kendall correlation between site s and site t (measuring spatial
dependence, not trend correlation).

Z-score:

```
z_regional = S_total / sqrt(Var(S_total))
p_regional = 2 · Φ(-|z_regional|)
```

---

## Implementation

```python
def regional_mk(site_series):
    """
    Regional Mann-Kendall test for trend detection across multiple sites.
    
    site_series: list of arrays, each being a time series for one location.
                 All must have the same length n.
    
    Returns: z_regional, p_regional, fraction_positive_sites
    """
    import numpy as np
    from scipy import stats
    
    m = len(site_series)
    n = len(site_series[0])
    
    # Individual S statistics
    S_vals = []
    var_vals = []
    for x in site_series:
        pairs = [(i,j) for i in range(n-1) for j in range(i+1,n)]
        s = float(sum(np.sign(x[j]-x[i]) for i,j in pairs))
        v = n*(n-1)*(2*n+5)/18.0
        S_vals.append(s)
        var_vals.append(v)
    
    S_total = sum(S_vals)
    
    # Spatial covariance via Kendall cross-correlations
    cov_total = sum(var_vals)   # diagonal
    for s in range(m):
        for t in range(s+1, m):
            xs, xt = site_series[s], site_series[t]
            # Kendall tau between sites (spatial correlation)
            tau_st, _ = stats.kendalltau(xs, xt)
            pairs_s = n*(n-1)/2
            pairs_t = n*(n-1)/2
            cov_st = tau_st * np.sqrt(var_vals[s] * var_vals[t])
            cov_total += 2 * cov_st
    
    var_total = max(cov_total, 1.0)   # floor to prevent division by 0
    
    if S_total > 0:
        z = (S_total - 1) / np.sqrt(var_total)
    elif S_total < 0:
        z = (S_total + 1) / np.sqrt(var_total)
    else:
        z = 0.0
    
    p = float(2 * stats.norm.sf(abs(z)))
    frac_pos = sum(1 for s in S_vals if s > 0) / m
    
    return z, p, frac_pos
```

---

## Combined workflow for Tidemark multi-site scan

```python
def multi_site_significance(results_by_city, alpha=0.05):
    """
    Given individual MK results across cities, compute:
    1. Per-site FDR-corrected significance
    2. Regional MK field significance
    """
    cities = list(results_by_city.keys())
    pvalues = [results_by_city[c]['p'] for c in cities]
    series  = [results_by_city[c]['series'] for c in cities]
    
    # FDR correction
    reject, adj_p = fdr_correction(pvalues, alpha)
    
    # Regional MK
    z_reg, p_reg, frac_pos = regional_mk(series)
    
    return {
        "field_significance_p": p_reg,
        "field_significant": p_reg < alpha,
        "fraction_sites_positive": frac_pos,
        "per_site": {
            c: {"p_raw": pvalues[i], "p_fdr": float(adj_p[i]),
                "significant_fdr": bool(reject[i])}
            for i, c in enumerate(cities)
        }
    }
```

---

## Expected output format

```
regional scan: temperature   10 South Asian cities   1981-2025
------------------------------------------------------------
individual results (FDR-corrected, α=0.05):
  dhaka       significant   p=0.012  (adj p=0.040) ✓
  mumbai      significant   p=0.008  (adj p=0.040) ✓
  delhi       significant   p=0.021  (adj p=0.052) —
  karachi     borderline    p=0.071  (adj p=0.118) —
  ...

regional field significance:
  7/10 sites show warming direction
  regional MK z=4.21   p=0.00003   ✓ field significant
  
  spatial dependence corrected: yes (Kendall cross-correlations applied)
  interpretation: warming trend is real and spatially coherent
```

---

## Implementation status

- **R:** `trend::regional.mk.test`, `trend::mk.test` with FDR via `p.adjust`
- **Python:** no package. The functions above are the full implementation.
- **Tidemark:** not yet implemented. Add to `scan` subcommand.
