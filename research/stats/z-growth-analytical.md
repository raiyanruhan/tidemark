# Analytical MK Z-score growth rate

This is the mathematical core of what makes this tool novel.

---

## derivation

For a series x_i = α + β·i + ε_i, i=0..n−1, with ε_i ~ IID(0, σ²):

For any pair (i, j) with i < j:
```
x_j - x_i = β(j-i) + (ε_j - ε_i)   where ε_j - ε_i ~ N(0, 2σ²)
P(x_j > x_i) = Φ(β(j-i) / (σ√2))
E[sign(x_j - x_i)] = 2Φ(β(j-i)/(σ√2)) - 1
```

For small signal-to-noise (β·Δt/σ << 1), linearize Φ:
```
2Φ(δ) - 1 ≈ δ · √(2/π)
```

Sum over all pairs (carrying the 1/√2 from δ through):
```
E[sign(x_j - x_i)] = δ · √(2/π)   where δ = β(j-i)/(σ√2)
                   = β(j-i)/(σ√2) · √(2/π)
                   = β(j-i)/σ · √(1/π)      [1/√2 · √(2/π) = √(1/π)]

E[S] = (β/σ) · √(1/π) · Σ_{i<j} (j-i)
     = (β/σ) · √(1/π) · n(n-1)(n+1)/6
     ≈ (β/σ) · √(1/π) · n³/6    [large n]
```

The variance:
```
Var(S) = n(n-1)(2n+5)/18 ≈ n³/9    [large n]
√Var(S) ≈ n^(3/2) / 3
```

Expected Z-score:
```
E[Z] ≈ E[S] / √Var(S)
     = [(β/σ) · √(1/π) · n³/6] / [n^(3/2)/3]
     = (β/σ) · n^(3/2) · √(1/π) / 2
     = (β/σ) · n^(3/2) · 1/(2√π)
     = (β/σ) · n^(3/2) · 0.282
```

Note: 1/(2√π) = 0.2821. This is the same C used in the detection floor formula.
An earlier version wrote C = √(1/(2π)) = 0.399, which omitted the 1/√2 factor from δ.
The crossing-year formula and β_min = 9.93·σ/n^1.5 are unaffected (C cancels in ratios).

**E[Z] grows as n^(3/2), not n^(1/2).**

Same growth rate as OLS regression (t-statistic for slope grows as n^(3/2) because leverage increases as n³).
ARE(MK vs OLS) for Gaussian data = 3/π ≈ 0.955; MK needs ~5% more data than OLS for same power.

---

## analytical crossing formula

Given current z₀ at series length n₀, to reach z_target = 1.96:

```
z_target / z₀ = (n_target / n₀)^(3/2)
n_target = n₀ · (1.96 / |z₀|)^(2/3)
years_needed = n₀ · [(1.96 / |z₀|)^(2/3) - 1]
crossing_year = last_data_year + years_needed
```

### examples

| z₀ | n₀ | years_needed | crossing_year |
|----|----|-------------|---------------|
| 1.5 | 45 | 9 | 2034 |
| 1.2 | 45 | 17 | 2042 |
| 1.0 | 45 | 26 | 2051 |
| 0.8 | 45 | 37 | 2062 |
| 0.5 | 45 | 67 | 2092 |

At z₀ < 0.8, the trend is so weak that it would take longer than a human lifetime to confirm.

---

## rate of Z accumulation

Differentiating E[Z] = C · n^(3/2) with respect to n:
```
dZ/dn = (3/2) · z₀ / n₀
```

This is the **evidence accumulation rate**: how much the z-score grows per additional year of data.

| z₀ | n₀ | dZ/dn |
|----|----|-------|
| 1.5 | 45 | 0.050/year |
| 1.0 | 45 | 0.033/year |
| 0.5 | 45 | 0.017/year |

"Your significance score is growing at 0.033 z-units per year" is an actionable number.  
It tells a policymaker whether collecting 5 more years of data is worth it.

---

## literature status

Searched: cfholbert MK power analysis, VSP PNNL documentation, CRAN trend vignette, Yue & Wang papers,
pymannkendall JOSS paper, Weatherhead framework. Nobody publishes this formula.

VSP answers the "minimum n" question by binary search simulation (~10 seconds per query).  
This formula answers it analytically in microseconds.

The formula exists implicitly in the structure of the test, but has never been extracted and presented
in usable form. That's the gap this tool fills.

---

## assumptions and limits

1. IID Gaussian noise. Breaks for skewed precipitation residuals.  
   Consequence: analytical estimate is optimistic (earlier) than Monte Carlo by ~10-20 years for arid precip.

2. Small signal-to-noise (linearization of Φ). For β/σ > 0.5 per year-gap, the approximation
   becomes less accurate. In practice, near-significant series always have small β/σ.

3. No autocorrelation. With ACF = φ, the n^(3/2) growth still holds but the prefactor changes.
   Weatherhead gives the correction: multiply years_needed by `((1+φ)/(1-φ))^(1/3)`.

---

## verification protocol (must run before shipping)

```python
import numpy as np
import pymannkendall as mk

def verify_z_growth():
    """expected: |z| ~ n^1.5, fit slope in log-log space should be ~1.5"""
    beta, sigma = 0.02, 0.3   # small signal-to-noise
    ns = [30, 45, 60, 90, 120]
    n_trials = 500
    
    mean_z = []
    for n in ns:
        zs = []
        for _ in range(n_trials):
            x = np.array([beta*i + np.random.normal(0, sigma) for i in range(n)])
            res = mk.original_test(x)
            zs.append(abs(res.z))
        mean_z.append(np.mean(zs))
    
    log_n = np.log(ns)
    log_z = np.log(mean_z)
    slope = np.polyfit(log_n, log_z, 1)[0]
    print(f"fitted exponent: {slope:.3f}   (expected: ~1.5)")
    return slope
```

Run this once. If the exponent is within 0.1 of 1.5, the formula is confirmed.
