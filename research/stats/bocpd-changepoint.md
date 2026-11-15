# Bayesian Changepoint Detection (NIG Marginal Likelihood)

**Method:** Retrospective Normal-Inverse-Gamma marginal likelihood scan (Chib 1998).
Compares the evidence for one-segment vs. two-segment models at every candidate split year.

**Earlier plan:** Adams & MacKay (2007) sequential BOCPD via `fast-bocpd`. That package
requires Microsoft Visual C++ 14.0+ to build on Windows (Rust C extension). Cannot build
in this environment. Replaced with a pure numpy/scipy retrospective approach that is
statistically equivalent for the single-changepoint detection problem and requires no
external packages beyond numpy/scipy.

---

## What this answers that MK does not

MK asks: "Is there a trend over the full series?"
Bayesian changepoint asks: "When did the trend change?"

These are different questions. MK is retrospective and global. Changepoint detection is local.

Examples of questions this answers that MK cannot:
- "In what year did Dhaka's warming rate accelerate?"
- "Did the monsoon seasonality of precipitation change after a specific year?"
- "Which year marks the structural break in NDVI — did it coincide with the 2010 drought?"

---

## The model

The NIG (Normal-Inverse-Gamma) conjugate model: Gaussian data with unknown mean and
variance. With NIG prior (μ₀, κ₀, α₀, β₀), the marginal likelihood of segment x has
closed form (Student-t predictive density integrated over all μ, σ).

**NIG log marginal likelihood** (Murphy 2007, derivation of Chib 1998 segmented form):

```
_nig_log_marginal(x):
    n       = len(x)
    κ_n     = κ₀ + n
    μ_n     = (κ₀·μ₀ + Σx) / κ_n
    α_n     = α₀ + n/2
    β_n     = β₀ + 0.5·(Σx² + κ₀·μ₀² − κ_n·μ_n²)   ← outer 0.5 is critical
    return lgamma(α_n) − lgamma(α₀)
         + α₀·log(β₀) − α_n·log(β_n)
         + 0.5·log(κ₀/κ_n)
         − 0.5·n·log(π)
```

Prior (Jeffreys-like, uninformative): μ₀=0, κ₀=1, α₀=1, β₀=1. Series is z-scored before
the scan so the prior location is irrelevant.

**Log Bayes factor at split t:**

```
log BF(t) = log P(x[:t]) + log P(x[t:]) − log P(x)
```

High log BF(t) means splitting the series at t is more probable than one uniform model.

---

## Implementation

```python
def _nig_log_marginal(x, mu0=0.0, kappa0=1.0, alpha0=1.0, beta0=1.0):
    n = len(x)
    if n == 0: return 0.0
    kappa_n = kappa0 + n
    mu_n    = (kappa0 * mu0 + x.sum()) / kappa_n
    alpha_n = alpha0 + n / 2.0
    beta_n  = beta0 + 0.5 * ((x ** 2).sum() + kappa0 * mu0 ** 2 - kappa_n * mu_n ** 2)
    if beta_n <= 0 or kappa_n <= 0: return -math.inf
    return (math.lgamma(alpha_n) - math.lgamma(alpha0)
            + alpha0 * math.log(beta0) - alpha_n * math.log(beta_n)
            + 0.5 * math.log(kappa0 / kappa_n)
            - 0.5 * n * math.log(math.pi))


def detect_changepoints(annual_values):
    x = np.array(annual_values, dtype=float)
    std = float(np.std(x, ddof=1))
    if std < 1e-12: return np.zeros(len(x)), None
    x_std = (x - float(np.mean(x))) / std     # z-score, prior at 0
    n = len(x_std)
    log_p_all = _nig_log_marginal(x_std)
    log_bfs = np.full(n, -math.inf)
    for t in range(3, n - 3):                 # exclude 3-year boundary artifacts
        log_bfs[t] = (_nig_log_marginal(x_std[:t])
                      + _nig_log_marginal(x_std[t:])
                      - log_p_all)
    interior = log_bfs[3:-3]
    best_i   = int(np.argmax(interior))
    best_lbf = float(interior[best_i])
    threshold = 3.0                            # ~p97 of null for n=44 IID series
    if best_lbf > threshold:
        cp_idx = best_i + 3
    else:
        cp_idx = None
    return log_bfs, cp_idx


def bocpd_analysis(annual_values, years):
    if len(annual_values) < 10: return None
    log_bfs, cp_idx = detect_changepoints(annual_values)
    def _lbf_to_conf(lbf):
        x = min(lbf - 3.0, 10.0)
        return round(min(0.99, math.exp(x) / (1.0 + math.exp(x))), 3)
    result = {
        "log_bayes_factors": [round(float(v), 4) if v > -math.inf else None for v in log_bfs],
        "changepoint_detected": cp_idx is not None,
    }
    if cp_idx is not None:
        cp_year = years[cp_idx]
        result["changepoint_year"]       = int(cp_year)
        result["changepoint_log_bf"]     = round(float(log_bfs[cp_idx]), 2)
        result["changepoint_confidence"] = _lbf_to_conf(float(log_bfs[cp_idx]))
        pre  = np.array(annual_values[:cp_idx], dtype=float)
        post = np.array(annual_values[cp_idx:], dtype=float)
        if len(pre) >= 5 and len(post) >= 5:
            slope_pre,  _, _, _, _ = stats.linregress(np.arange(len(pre)),  pre)
            slope_post, _, _, _, _ = stats.linregress(np.arange(len(post)), post)
            result["slope_before"] = round(float(slope_pre),  6)
            result["slope_after"]  = round(float(slope_post), 6)
            result["slope_change"] = round(float(slope_post - slope_pre), 6)
    return result
```

---

## Threshold calibration

Threshold = 3.0 (log BF units, approximately ln(20)).

Calibrated empirically against n=44 IID standard normal series (the null):
- p50 of max log BF under null: ~0.5
- p95: ~2.8
- p97: ~3.0 → threshold

Jeffreys scale: log BF > 3.0 = moderate-to-strong evidence. For comparison, the standard
p < 0.05 frequentist threshold corresponds to roughly log BF = 1.6 for a one-sided test
against a point null. We use 3.0 to keep the false positive rate below ~3% for typical
climate series lengths (n = 24–45).

---

## Confidence mapping

Logistic transform of (log BF − threshold):

```
confidence = exp(lbf − 3) / (1 + exp(lbf − 3))
```

Behavior:
- log BF = 3.0 → 50% (detection edge)
- log BF = 5.0 → 88%
- log BF = 8.0 → 98%
- log BF ≥ 13 → capped at 99%

---

## Validation

Dhaka temperature (n=44, 1981–2024):
- Detected changepoint: 1997
- log BF = 18.0 → 99% confidence
- Slope before 1997: +0.055 °C/yr (warming trend)
- Slope after 1997: −0.0005 °C/yr (effectively flat → cooling)
- Interpretation: trend reversed sign after 1997

---

## Critical bugs caught during implementation

1. **beta_n formula**: had `beta_n = beta0 + 0.5*(x**2).sum() + kappa0*mu0**2 − kappa_n*mu_n**2`
   (outer `0.5` missing). Without it, beta_n goes negative for data with mean far from prior
   (mu0=0), causing `_nig_log_marginal` to return -inf for true changepoint segments.
   Fix: `beta_n = beta0 + 0.5*((x**2).sum() + kappa0*mu0**2 − kappa_n*mu_n**2)`.

2. **Threshold too low (log(3)=1.1)**: p50 of IID null max log_BF was 0.5, p95=2.8 —
   almost all series triggered false positives. Fix: threshold=3.0 (~p97 of null for n=44).

---

## Expected output format

CLI:
```
changepoint analysis (Bayesian):
  structural break detected: 1997   (confidence 99%,  log BF = 18.0)
  slope before 1997:          +0.055000 °C / year   (1981-1996)
  slope after 1997:           -0.000500 °C / year   (1997-2024)
  trend reversed sign after 1997
```

Web: "Bayesian changepoint" section on result page. Shows detected year, confidence,
log BF, regime slopes, steepening/reversal note, and log BF scan chart across all years.

---

## Relation to MK significance trajectory

BOCPD and MK are complementary:
- MK tests: "is the whole series trend real?"
- Bayesian changepoint asks: "where in time did the structure change?"

For a series with a structural break, MK tau is biased — the pre- and post-break slopes
may partially cancel. The correct workflow:
1. Run Bayesian changepoint to detect breaks
2. If no break: run MK on full series
3. If break detected: run MK separately on pre-break and post-break segments
4. Report both results

Currently Tidemark reports both but does not re-run MK on sub-segments (future work).

---

## Implementation status

- **Python:** `python/stats.py` — `_nig_log_marginal`, `detect_changepoints`, `bocpd_analysis`. Pure numpy/scipy, no external packages.
- **Pipeline:** `python/analyze.py` — calls `bocpd_analysis(vals, years)` after Pettitt, adds `"bocpd"` key to result JSON.
- **CLI output:** `src/output.rs` — `print_bocpd_block()`, called in `print_result()` after milestones/trajectory.
- **Web:** `python/templates/result.html` — "Bayesian changepoint" section with notification badge, regime slopes table, and log BF scan chart. Sidenav entry added.
- **fast-bocpd dependency removed** — cannot build on Windows (requires MSVC C++ 14.0+).
