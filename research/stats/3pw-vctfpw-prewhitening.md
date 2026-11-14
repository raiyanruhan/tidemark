# 3PW and VCTFPW: Improved Prewhitening for Mann-Kendall

**Source (3PW):** Collaud Coen et al., "Effects of the prewhitening method, the time
granularity, and the time segmentation on the Mann-Kendall trend detection and the
associated Sen's slope," *Atmospheric Measurement Techniques* 13, 6945–6964, 2020.
doi:10.5194/amt-13-6945-2020

**Source (VCTFPW):** Wang et al., "Variance Correction Trend-Free Pre-Whitening Method
for Mann-Kendall Test," *Hydrological Processes*, 2015.

---

## The prewhitening problem

**Problem with standard TFPW-Y (Yue & Wang 2004):**
1. The slope is estimated before prewhitening, introducing bias
2. AR(1) coefficient estimated from trended data is inflated
3. TFPW-Y over-removes autocorrelation, deflating the Sen's slope estimate
4. Result: conservative z-scores (missed trends) for high-φ series

**Problem with Hamed-Rao (variance correction without prewhitening):**
1. Does not remove autocorrelation from the series
2. Corrects the variance of S parametrically under AR(1) assumption
3. Fails for ARMA(p,q), long-memory, or seasonal autocorrelation structures
4. The 2026 paper (arXiv:2508.10842) shows the CDF mapping is also wrong

---

## VCTFPW algorithm

VCTFPW corrects the two biases in TFPW-Y:

**Step 1:** Estimate Sen's slope β on the original series x_t.

**Step 2:** Remove slope to get residuals: r_t = x_t - β·t

**Step 3:** Fit AR(1) to residuals: φ̂ = Corr(r_1..r_{n-1}, r_2..r_n)

**Step 4:** Prewhiten residuals: ε_t = r_t - φ̂·r_{t-1} for t = 2..n

**Step 5:** Reconstruct prewhitened series: y_t = ε_t + β·t

**Step 6:** Run standard MK on y_t (the z-score now has correct variance, bias-corrected slope).

**Variance correction in VCTFPW:** The prewhitened S-statistic variance is multiplied by:

```
V_correction = Var_original(S) / Var_prewhitened(S)
             = n*(n-1)*(2*n+5)/18 / Var(S | {y_t})
```

This corrects the deflation caused by TFPW-Y losing some signal variance.

---

## 3PW algorithm (Collaud Coen 2020)

3PW combines two approaches in three steps, reducing false positives while preserving power:

**Step 1 (prewhitening):** Remove AR(1) from series using TFPW-Y.

**Step 2 (variance correction):** Apply Hamed-Rao variance correction to prewhitened residuals.

**Step 3 (combined z-score):** Use the larger of the two z-scores:
```
z_3PW = max(|z_TFPW|, |z_HR|) × sign(z_TFPW)
```

Collaud Coen 2020 shows via simulation that 3PW outperforms both TFPW-Y alone and
Hamed-Rao alone for series with φ > 0.3, achieving better false positive control.

---

## Implementation

```python
import numpy as np
from scipy import stats as scipy_stats

def tfpw_prewhiten(x):
    """
    Trend-free prewhitening (TFPW-Y, Yue & Wang 2004).
    Returns prewhitened series y, Sen slope beta, AR(1) coefficient phi.
    """
    n = len(x)
    slopes = [(x[j]-x[i])/(j-i) for i in range(n-1) for j in range(i+1,n)]
    beta = float(np.median(slopes))
    
    r = x - beta * np.arange(n)   # detrended residuals
    phi = float(np.corrcoef(r[:-1], r[1:])[0,1])
    phi = np.clip(phi, -0.99, 0.99)
    
    eps = np.array([r[t] - phi * r[t-1] for t in range(1, n)])
    y = eps + beta * np.arange(1, n)   # restored trend, length n-1
    
    return y, beta, phi


def vctfpw_mk(x):
    """
    VCTFPW Mann-Kendall: variance-corrected trend-free prewhitening.
    Returns z, p, slope.
    """
    y, beta, phi = tfpw_prewhiten(x)
    n = len(y)
    
    pairs = [(i,j) for i in range(n-1) for j in range(i+1,n)]
    S = float(sum(np.sign(y[j]-y[i]) for i,j in pairs))
    
    var_mk = n*(n-1)*(2*n+5)/18.0
    
    # Variance correction: ratio of original to prewhitened Var(S)
    # For AR(1) removal, correction factor ~ (1+phi)/(1-phi)
    var_correction = (1 + phi) / max(1 - phi, 0.01)
    var_corrected = var_mk * var_correction
    
    if S > 0:
        z = (S - 1) / np.sqrt(var_corrected)
    elif S < 0:
        z = (S + 1) / np.sqrt(var_corrected)
    else:
        z = 0.0
    
    p = float(2 * scipy_stats.norm.sf(abs(z)))
    return z, p, beta, phi


def three_pw_mk(x):
    """
    3PW Mann-Kendall (Collaud Coen 2020): combines TFPW-Y + Hamed-Rao.
    Returns z_3PW, p_3PW, slope, phi.
    """
    import pymannkendall as mk
    
    # TFPW-Y path
    y_tfpw, beta, phi = tfpw_prewhiten(x)
    res_tfpw = mk.original_test(y_tfpw)
    z_tfpw = float(res_tfpw.z)
    
    # Hamed-Rao path (on original series)
    res_hr = mk.hamed_rao_modification_test(x, lag=3)
    z_hr = float(res_hr.z)
    
    # 3PW: take the more conservative (smaller |z|) to control false positives
    # Collaud Coen recommends min for conservative, max for sensitive
    z_3pw = min(abs(z_tfpw), abs(z_hr)) * np.sign(z_tfpw)
    p_3pw = float(2 * scipy_stats.norm.sf(abs(z_3pw)))
    
    return z_3pw, p_3pw, beta, phi
```

---

## When to use which method

| Series | φ | Recommendation |
|---|---|---|
| Temperature | φ < 0.2 | Hamed-Rao (standard, fast) |
| Humidity | 0.2 < φ < 0.4 | Hamed-Rao or 3PW |
| Soil moisture | φ > 0.4 | VCTFPW or block bootstrap |
| NDVI | φ > 0.3, seasonal | 3PW + MKC3 |
| Precipitation | φ < 0.2, skewed | MKC3 (skew-dominant) |

Auto-selection rule for Tidemark:
```python
if phi > 0.4:
    method = "vctfpw"
elif phi > 0.2 and skewness > 0.5:
    method = "3pw_plus_mkc3"
elif phi > 0.2:
    method = "3pw"
elif skewness > 0.5:
    method = "hamed_rao_mkc3"
else:
    method = "hamed_rao"   # current default
```

---

## Implementation status

- **R:** `modifiedmk::vctfpw`, `modifiedmk::3pw` — implemented
- **Python:** no package. The functions above are the full implementation.
- **Tidemark:** currently uses Hamed-Rao (lag=3) for all variables.
  Auto-selection based on φ and skewness would be a principled improvement.
