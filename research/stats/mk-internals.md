# pymannkendall internals

source: github.com/mmhs013/pyMannKendall, v1.4.2

---

## S statistic

```python
# vectorized pairwise sign sum
S = Σ sign(x[j] - x[i])  for all i < j
```

`__mk_score` uses numpy broadcasting. For n=45: 45×44/2 = 990 pairs.

## variance with tie correction

```python
# no ties (continuous float data: almost always this branch)
var_s = n*(n-1)*(2*n+5) / 18

# with ties (tp = count per tied group)
var_s = (n*(n-1)*(2*n+5) - Σ tp*(tp-1)*(2*tp+5)) / 18
```

For POWER API reanalysis floats, ties are rare. Tie correction rarely activates.

## z-score (continuity correction)

```python
z = (S - 1) / sqrt(var_s)   # S > 0
z = 0                         # S = 0
z = (S + 1) / sqrt(var_s)   # S < 0
```

## p-value

Two-tailed: `p = 2*(1 - Φ(|z|))`.  
Trend is "increasing" if `z > 0 and p < alpha`, "decreasing" if `z < 0 and p < alpha`.

## Sen's slope

Median of all `(x[j] - x[i])/(j - i)` for i < j.  
Intercept: `median(x) - slope * median(range(n))`.

## return namedtuple fields

`trend, h, p, z, Tau, s, var_s, slope, intercept`

---

## the 13 variants: why they exist

| function | what it corrects | when to use |
|---|---|---|
| `original_test` | nothing | iid data, no autocorrelation |
| `hamed_rao_modification_test(x, lag=3)` | ACF of rank-detrended series inflates var_s | annual temperature (ACF typically 0.15-0.35) |
| `yue_wang_modification_test` | similar ACF correction, different weighting | alternative to Hamed-Rao |
| `pre_whitening_modification_test` | removes AR(1) before MK | moderate ACF, loses 1 data point |
| `trend_free_pre_whitening_modification_test` | detrend → prewhiten → retrend | stronger ACF; Yue & Wang 2002 recommendation |
| `seasonal_test` | within-season comparison only | monthly data, seasonal cycles |
| remaining 7 | multi-site, partial, correlated | multiple variables or stations |

---

## hamed_rao actual code (key lines)

```python
# detrend by Sen slope
x_detrend = x - np.arange(1, n+1) * slope

# rank the detrended series
I = rankdata(x_detrend)

# ACF of ranks
acf_1 = __acf(I, nlags=lag-1)

# confidence interval for "skip insignificant lags"
interval = norm.ppf(1 - alpha/2) / np.sqrt(n)

# sum only significant lags
sni = 0
for i in range(1, lag):
    if lower_bound <= acf_1[i] <= upper_bound:
        sni = sni  # skip: within CI
    else:
        sni += (n-i)*(n-i-1)*(n-i-2) * acf_1[i]

n_ns = 1 + (2 / (n*(n-1)*(n-2))) * abs(sni)
var_s = var_s * n_ns   # inflated variance → larger p-value
```

**Bug**: uses `abs(sni)`. Original Hamed & Rao (1998) does NOT take abs, it only inflates for positive ACF.
For negative ACF the variance should decrease (larger effective n). This implementation always inflates.
Impact: for precipitation with negative lag-1 ACF, `hamed_rao` is over-conservative (p too large). Safe direction but wrong.

## critical behavior at n=45

Confidence interval for skipping lags: `±1.96/√45 = ±0.292`.  
Any lag-1 ACF below 0.292 in absolute value is skipped → `n_ns = 1.0` → identical to `original_test`.  
Practical consequence: `hamed_rao` only diverges from `original_test` when `|ACF_lag1| > 0.292`.  
For most annual precipitation series this threshold is not crossed.  
For annual temperature it may be.

## which test to use for this project

Annual precipitation (PRECTOTCORR): ACF typically −0.2 to +0.1 → below the 0.292 skip threshold.  
`hamed_rao` reduces to `original_test`. Either works.

Annual temperature (T2M): ACF typically 0.15-0.35. May cross the 0.292 threshold.  
Use `hamed_rao(x, alpha=0.05, lag=3)`. The `lag=3` follows the original paper's recommendation.  
When ACF is below threshold, it still returns identical numbers to `original_test`.

**Decision**: use `hamed_rao(x, alpha=0.05, lag=3)` for the current data assessment.  
Use `original_test` inside the Monte Carlo loops: MC-generated series have iid noise (ACF ~ 0), so the correction computes to ~zero anyway. Faster.

## `__acf` uses biased estimator

```python
d = n * np.ones(2*n - 1)   # biased: divides by n, not n-lag
acov = (np.correlate(y, y, 'full') / d)[n-1:]
return acov[:nlags+1] / acov[0]
```

Biased estimator underestimates ACF at high lags. For lag-1 on n=45, bias is small (factor 44/45). Fine.
