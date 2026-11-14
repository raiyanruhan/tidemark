# Bootstrap decision: iid vs block vs Gaussian

---

## the question

When extending the time series in Monte Carlo simulation, how should we generate synthetic noise?

Options:
1. Gaussian: `np.random.normal(0, sigma)`
2. IID empirical: `np.random.choice(residuals, replace=True)`
3. Moving block bootstrap: resample blocks of length L to preserve autocorrelation

---

## the validation result (from CLAUDE.md)

Cairo PRECTOTCORR residuals: skewness=1.95, normality p<0.0001 (heavily right-skewed)
Riyadh PRECTOTCORR residuals: skewness=1.88, normality p<0.0001

Gaussian underestimates extreme wet years. IID empirical bootstrap preserves the actual distribution.

**CLAUDE.md decision: use IID empirical bootstrap. This is correct.**

---

## does autocorrelation change this?

Annual precipitation ACF is typically −0.2 to +0.1. Near zero. IID bootstrap is appropriate.

Annual temperature ACF is typically +0.15 to +0.35. Not zero. Does block bootstrap matter here?

For the Monte Carlo PROJECTION specifically:
- We are extending the series by 5-60 years
- Each simulated path's crossing year depends on whether noise is clustered or not
- Positive ACF → runs of high values can temporarily reverse a weak downward trend
- IID bootstrap destroys this clustering → slightly optimistic (earlier) crossing year estimates
- Effect magnitude: for φ=0.25, block bootstrap (L=3) would add ~2-5 years to the median crossing year

**This is a second-order effect.** The detection floor and analytical estimate already tell users
what the main story is. The 2-5 year shift from autocorrelation is smaller than the 85% PI width.

---

## moving block bootstrap for reference

If implementing later, for annual data with n=45:

```python
def block_bootstrap_residuals(residuals, n_out, block_length=3):
    """
    Returns n_out residuals resampled in blocks of block_length.
    Preserves temporal dependence structure.
    """
    n = len(residuals)
    blocks = [residuals[i:i+block_length] for i in range(n - block_length + 1)]
    n_blocks = int(np.ceil(n_out / block_length))
    chosen = np.random.choice(len(blocks), size=n_blocks, replace=True)
    resampled = np.concatenate([blocks[i] for i in chosen])
    return resampled[:n_out]
```

Block length L=3 for n=45: rule of thumb is n^(1/3) ≈ 3.6, round to 3.
For L=1, this reduces to IID empirical bootstrap.

---

## recommendation

| variable | ACF | bootstrap method |
|---|---|---|
| PRECTOTCORR | ≈0 | IID empirical |
| T2M | 0.15-0.35 | IID empirical (small effect, 2nd order) |
| T2M_MAX, T2M_MIN | similar to T2M | IID empirical |
| RH2M | low | IID empirical |
| EVLAND, WS10M | low | IID empirical |

IID empirical bootstrap is correct for all variables in v1.
If v2 adds monthly data, revisit: monthly ACF is high (0.7+) and block bootstrap becomes important.

---

## output note (when ACF is notable)

When lag-1 ACF of residuals > 0.20 and series is not yet significant:
```
  note   residual autocorrelation phi=0.27, crossing year estimate is slightly optimistic
         (Monte Carlo assumes independent noise; actual persistence may delay by 2-4 years)
```

This note is honest, not alarmist. It's printed only once and doesn't change the main numbers.
