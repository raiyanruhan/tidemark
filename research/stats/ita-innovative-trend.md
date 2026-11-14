# Innovative Trend Analysis (ITA)

**Source:** Şen, "Innovative Trend Analysis Methodology," *Journal of Hydrological Engineering*
17(9), 1042–1046, 2012.

Applied widely 2020–2025: Croatia (2023), Nigeria (2022), Brazil (2026), Ethiopia (2025),
Afghanistan (2024), Bangladesh (2024).

---

## Why MK misses non-monotonic trends

Mann-Kendall tests for a single monotonic trend across the entire series. It cannot detect:

1. **Trend in low-value sub-population different from trend in high-value sub-population**
   Example: rainfall low-extreme years trending down, high-extreme years trending up.
   Net MK statistic: near zero, "no significant trend."
   ITA: shows two diverging branches.

2. **Trend that changed direction mid-series**
   Example: warming 1981–2000, cooling 2001–2025.
   MK: near-zero tau, "no trend."
   ITA: visible crossing in the graphical output.

3. **Trend confined to a specific sub-range of values**
   Example: only years with NDVI > 0.4 show decline.
   ITA: visible in the high-value region of the scatter.

---

## Method

Divide the time series into two equal halves:

```
first  = x[0 : n//2]      (earlier period)
second = x[n//2 : n]      (later period)
```

Sort each half independently in ascending order:

```
x1_sorted = sort(first)
x2_sorted = sort(second)
```

Plot x1_sorted (x-axis) vs x2_sorted (y-axis):
- Points above the 1:1 diagonal (y = x): second period higher than first → increasing trend
- Points below: decreasing trend
- Scatter parallel to diagonal: no trend
- Upper points above diagonal, lower points below: high-extremes increasing, low-extremes decreasing (or vice versa)

---

## Quantitative ITA statistics

**ITA slope for each tercile:**

```python
import numpy as np

def ita_analysis(x):
    """
    Innovative Trend Analysis.
    Returns: slope_low, slope_mid, slope_high, overall_ita_slope
    """
    n = len(x)
    half = n // 2
    
    x1 = np.sort(x[:half])
    x2 = np.sort(x[half:half*2])   # equal length
    
    # Overall ITA slope (mean difference / half-length)
    ita_slope = (np.mean(x2) - np.mean(x1)) / half
    
    # Tercile breakdown
    t1 = half // 3
    t2 = 2 * t1
    
    low_slope  = (np.mean(x2[:t1])    - np.mean(x1[:t1]))    / half
    mid_slope  = (np.mean(x2[t1:t2])  - np.mean(x1[t1:t2]))  / half
    high_slope = (np.mean(x2[t2:])    - np.mean(x1[t2:]))     / half
    
    return {
        "ita_slope":   round(float(ita_slope),  6),
        "low_slope":   round(float(low_slope),  6),
        "mid_slope":   round(float(mid_slope),  6),
        "high_slope":  round(float(high_slope), 6),
        "x1_sorted":   x1.tolist(),
        "x2_sorted":   x2.tolist(),
    }
```

**Significance test for ITA slope:**

Under H0 (no trend, IID series), the expected ITA slope distribution can be approximated
via parametric bootstrap (shuffle x, compute ITA slope, repeat 1000×):

```python
def ita_pvalue(x, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    obs_slope = ita_analysis(x)["ita_slope"]
    
    null = []
    for _ in range(n_boot):
        shuffled = rng.permutation(x)
        null.append(ita_analysis(shuffled)["ita_slope"])
    
    null = np.array(null)
    p = float(np.mean(np.abs(null) >= abs(obs_slope)))
    return max(p, 1.0/n_boot)
```

---

## Interpretation rules

| Pattern | Meaning |
|---|---|
| All terciles above diagonal | Uniform increasing trend |
| All terciles below diagonal | Uniform decreasing trend |
| Low below, high above | High-extremes intensifying, low-extremes weakening |
| Low above, high below | Low-extremes rising, high-extremes declining |
| Zigzag | Non-monotonic — MK misses this entirely |
| Parallel to diagonal | No trend (consistent with high MK p-value) |

---

## Expected output format in Tidemark

```
innovative trend analysis (ITA)
  low values    -0.004 mm/day/yr   (driest years getting drier)
  mid values    +0.001 mm/day/yr   (average years stable)
  high values   +0.012 mm/day/yr   (wettest years getting wetter)
  ITA slope     +0.003 mm/day/yr   (net; agrees with Sen's slope 0.0031)

  note: trend is non-uniform — intensification of extremes both ways
        MK tests for monotonic trend only; ITA detects this divergence
```

This output is unique. No other tool shows the sub-population trend structure. For climate
science, the intensification of extremes is often more important than the mean trend.

---

## Relation to detection floor and crossing year

The ITA slope can feed directly into the detection floor and crossing-year formulas:
- Use `high_slope` for detecting trend in extreme precipitation events
- Use `low_slope` for detecting drought intensification

This extends the significance trajectory concept to sub-population trends — another first.

---

## Implementation status

- **Published:** 2012. Applied in 50+ regional papers 2020–2025.
- **Python:** no package. The ~20-line implementation above is the full core.
- **R:** no dedicated package (manual implementations in papers).
- **Tidemark:** not yet implemented.
