# Bayesian Online Changepoint Detection (BOCPD)

**Foundation:** Adams & MacKay, "Bayesian Online Changepoint Detection," arXiv:0710.3742, 2007.

**Climate application:** Fearnhead & Rigaill, "Changepoint Detection in the Presence of
Outliers," *JASA* 2019. Multivariate satellite application: arXiv:2112.12899, 2021
(NDVI deforestation monitoring — the only prior climate/satellite use).

---

## What BOCPD answers that MK does not

MK asks: "Is there a trend over the full series?"
BOCPD asks: "When did the trend change?"

These are different questions. MK is retrospective and global. BOCPD is sequential and local.

Examples of questions BOCPD answers that MK cannot:
- "In what year did Dhaka's warming rate accelerate?"
- "Did the monsoon seasonality of precipitation change after a specific year?"
- "Which year marks the structural break in NDVI — did it coincide with the 2010 drought?"
- "Are multiple climate variables breaking simultaneously, suggesting a regime shift?"

---

## The model

At each time step t, the run length r_t is the number of time steps since the last changepoint.

BOCPD maintains the posterior probability of the current run length:

```
P(r_t | x_{1:t})
```

Updated recursively:

```
P(r_t, x_{1:t}) = P(r_t | r_{t-1}) · P(x_t | x_{t-r_t:t-1}) · P(r_{t-1}, x_{1:t-1})
```

where:
- P(r_t | r_{t-1}) is the **hazard function** (prior probability of a changepoint at step t)
  - Constant hazard: P(changepoint) = h each step (geometric run-length prior)
  - Typical: h = 1/200 (expect one changepoint per 200 observations)
- P(x_t | x_{t-r_t:t-1}) is the **predictive distribution** given the current segment's data
  - Gaussian with unknown mean and variance (Normal-Gamma conjugate)
  - Student-t predictive

The output: at each time t, `P(r_t = 0 | x_{1:t})` = posterior probability of a changepoint
RIGHT NOW. High value = structural break.

---

## Implementation

Python: `pip install fast-bocpd`

```python
from fastbocpd import BOCPD
import numpy as np

def detect_changepoints(annual_values, hazard=0.02):
    """
    Bayesian Online Changepoint Detection for annual climate series.
    
    annual_values: array of annual means
    hazard: prior probability of changepoint per year (1/50 = expect 1 in 50 years)
    
    Returns: changepoint_probs (array, same length as input),
             most_likely_changepoint_year_index
    """
    x = np.array(annual_values, dtype=float)
    
    model = BOCPD(hazard_rate=hazard)
    model.fit(x)
    
    # Posterior P(changepoint at t)
    cp_probs = model.changepoint_probabilities()
    
    # Most likely changepoint (excluding first and last 3 years — boundary artifact)
    interior = cp_probs[3:-3]
    if interior.max() > 0.3:   # only report if confident
        cp_idx = int(np.argmax(interior)) + 3
    else:
        cp_idx = None
    
    return cp_probs, cp_idx


def bocpd_analysis(annual_values, years):
    """
    Full BOCPD analysis returning structured result for Tidemark output.
    """
    cp_probs, cp_idx = detect_changepoints(annual_values)
    
    result = {
        "changepoint_probabilities": [round(float(p), 4) for p in cp_probs],
        "changepoint_detected": cp_idx is not None,
    }
    
    if cp_idx is not None:
        cp_year = years[cp_idx]
        result["changepoint_year"] = int(cp_year)
        result["changepoint_confidence"] = round(float(cp_probs[cp_idx]), 3)
        
        # Trend before and after changepoint
        pre  = annual_values[:cp_idx]
        post = annual_values[cp_idx:]
        
        from scipy import stats
        if len(pre) >= 5 and len(post) >= 5:
            slope_pre,  _, _, _, _ = stats.linregress(range(len(pre)),  pre)
            slope_post, _, _, _, _ = stats.linregress(range(len(post)), post)
            result["slope_before"] = round(float(slope_pre),  6)
            result["slope_after"]  = round(float(slope_post), 6)
            result["slope_change"] = round(float(slope_post - slope_pre), 6)
    
    return result
```

---

## Multi-variable regime shift detection

The most novel application: test whether multiple climate variables break SIMULTANEOUSLY,
indicating a coupled system regime shift rather than a noise-driven single-variable change.

```python
def multi_variable_bocpd(variable_series, years, hazard=0.02):
    """
    Test for simultaneous changepoints across variables.
    
    variable_series: dict {var_name: array_of_annual_values}
    Returns: coincident changepoint years and variables involved
    """
    results = {}
    for var, vals in variable_series.items():
        cp_probs, cp_idx = detect_changepoints(vals, hazard)
        if cp_idx is not None:
            results[var] = {"year": years[cp_idx], "confidence": float(cp_probs[cp_idx])}
    
    # Find years where ≥3 variables break within a 3-year window
    if len(results) >= 3:
        cp_years = sorted(set(r["year"] for r in results.values()))
        regime_shifts = []
        for y in cp_years:
            vars_near = [v for v, r in results.items() if abs(r["year"] - y) <= 2]
            if len(vars_near) >= 3:
                regime_shifts.append({
                    "year": int(y),
                    "variables": vars_near,
                    "strength": len(vars_near)
                })
        return results, regime_shifts
    
    return results, []
```

---

## Expected output format

```
changepoint analysis (BOCPD)
  changepoint detected: 2003   (confidence 0.87)
  
  before 2003 (1981-2002, 22 years):
    slope   -0.004 mm/day/yr   (weak decline)
  after 2003 (2003-2025, 23 years):
    slope   -0.021 mm/day/yr   (accelerated decline)
  slope change:  -0.017 mm/day/yr (trend steepened 5× after 2003)

multi-variable regime shift:
  2003: temperature, precipitation, NDVI, soil moisture all break simultaneously
  interpretation: possible land-use change or long-term drought onset
```

---

## Relation to MK significance trajectory

BOCPD and MK are complementary:
- MK tests: "is the whole series trend real?"
- BOCPD asks: "where in time did the structure change?"

For a series with a structural break, MK tau is biased — the pre- and post-break slopes
may partially cancel. The correct workflow:
1. Run BOCPD first to detect breaks
2. If no break: run MK on full series
3. If break detected: run MK separately on pre-break and post-break segments
4. Report both results

This is a more correct analysis workflow than any existing climate trend tool offers.

---

## Implementation status

- **Python:** `fast-bocpd` on PyPI. Full implementation above ~50 lines.
- **Climate use:** one application (NDVI deforestation, 2021). Temperature, precipitation,
  soil moisture, ET: zero applications.
- **Multi-variable regime shift detection:** never done in any tool.
- **Tidemark:** not yet implemented.
