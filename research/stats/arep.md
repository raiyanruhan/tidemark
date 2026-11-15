# Trend e-process (formerly "AREP")

Status: rewritten after a validity audit. The original AREP statistic was **not** an
e-process and is removed. This note describes what `compute_eprocess` in
`python/stats.py` computes now (JSON key `e_process`).

## what was wrong with the original AREP

Original: `E_n = exp(omega*Lambda_n - omega^2*I*n^3/6)` with `omega` = Sen slope fitted on the
same series, `Lambda_n = sum c_hat(eps_t) * t`, time `t = 1..n`, intercept treated as known.

1. `omega` was fitted on the data the statistic is evaluated on. The argument
   "E[E_n | H0] = 1" holds for a constant omega, not a data-dependent one.
2. The intercept was estimated from the same data but treated as known; time was not
   centred (weights `t = 1..n`, normaliser `n^3/6` instead of `Sxx/2`), so the
   statistic carried an unmodelled nuisance parameter.
3. The AR(1) correction was documented and deliberately left out of the code.

Measured on IID Gaussian, no trend, n = 45, 2000 runs: `E >= 20` fired 12.2% of the time
against a claimed bound of 5% (Hamed-Rao on the same data: 6.0%).

## construction (option a: a real e-process)

Model: `Y_t = a + beta*t + sigma*e_t`. H0: `beta = 0`. Nuisance parameters shared by
both hypotheses: intercept `a` and scale `sigma`.

H1 is a mixture over the *standardised* slope `delta = beta/sigma` (per annual step):
`delta ~ (1/3) sum_k N(0, tau_k^2)`, `tau = (0.02, 0.05, 0.15)`. The prior is fixed
in advance; nothing about it is fitted to the series being tested.

`a` and `sigma` are integrated out with the right-Haar priors (flat on `a`, `1/sigma` on
`sigma`). With `S0 = sum (y - ybar)^2`, `Sxx = sum (t - tbar)^2` (**centred** time),
`r = Sxy / sqrt(S0*Sxx)`, and `v = sqrt(S0)/sigma`:

```
LR(delta) = exp(-delta^2 Sxx / 2) * Int v^(n-2) exp(-v^2/2 + delta*sqrt(Sxx)*r*v) dv
                                   / Int v^(n-2) exp(-v^2/2) dv
E_n       = Int LR(delta) dPrior(delta)
```

Both integrals are done numerically (24-point Gauss-Hermite per prior component; 1500-point
grid in `v`, log-sum-exp).

### why this is valid

`E_n` is the likelihood ratio of the maximal invariant of the group `y -> a + s*y`
(Wijsman 1967; Perez-Ortiz, Lardy, de Heide, Grunwald 2024, "E-statistics, group
invariance and anytime-valid testing"). The group acts on the nuisance parameters
(intercept, scale) of both hypotheses; the right-Haar prior makes the Bayes factor equal
the invariant likelihood ratio. Hence for **iid Gaussian errors**:

* `E[E_n | H0] = 1` at every n, so `P(E_n >= 20) <= 5%` (Markov).
* The invariant at n is a function of the invariant at n+1 (ratios of differences), and the
  slope prior does not depend on n, so `(E_n)` is a test martingale in the invariant
  filtration. Ville's inequality gives `P(sup_n E_n >= 20) <= 5%`, i.e. the
  "check every year" claim, for iid Gaussian noise.

### autocorrelation

Not exactly handled. `phi` is estimated from the OLS line residuals (lag-1, small-sample
correction `(1+4phi)/n`, clipped to [0, 0.9]; negative phi is not corrected) and the
series, intercept column and time column are Prais-Winsten whitened before the
formula above. This treats the estimated phi as known, so **no exact guarantee** is
claimed for autocorrelated noise; the error rate was checked by simulation (below).
Higher-order or long-memory dependence is not handled; output flags `phi_note`
when `phi > 0.4`.

### non-Gaussian errors

No exact guarantee (the likelihood is Gaussian). Skewed (centred exponential) noise was
simulated and is well below 5%, but that is an empirical statement, not a theorem.

### what was dropped

The KDE-adaptive score `c_hat` and the Fisher-information normaliser are gone from this
statistic. They require estimating `f` from the same data (the same circularity) and the
Gaussian likelihood is what makes the exact guarantee possible. `compute_efficiency_metrics`
(ARE vs optimal score, CRB detection year) is unchanged and is separate from the e-process.

## significance flag

`significant = (E_n >= 20)`, `alpha = 0.05` by Markov/Ville under the assumptions above.
The flag is **conservative**: actual null rates are ~0.1-0.2% (Markov slack), so power is
low relative to a p-value test (see below). Do not lower the threshold and still call it
an e-process; a lower, simulation-calibrated cutoff would be a different (non-guaranteed)
rule.

## simulation results (R = 1500 per cell, 2026-11-15)

False-positive rate under H0 (no trend), `E_n >= 20`. "plain" = no whitening;
"whitened" = what the code does. MK = naive Mann-Kendall z (no autocorrelation fix),
for reference only.

| noise | n | plain | whitened (shipped) | naive MK |
|---|---|---|---|---|
| IID Gaussian | 30 | 0.001 | 0.001 | 0.049 |
| IID Gaussian | 45 | 0.001 | 0.001 | 0.050 |
| IID Gaussian | 60 | 0.002 | 0.001 | 0.054 |
| skewed (exp) | 30 | 0.001 | 0.001 | 0.043 |
| skewed (exp) | 45 | 0.001 | 0.001 | 0.048 |
| skewed (exp) | 60 | 0.000 | 0.000 | 0.051 |
| AR(1) phi=0.3 | 30 | 0.018 | 0.007 | 0.130 |
| AR(1) phi=0.3 | 45 | 0.017 | 0.007 | 0.139 |
| AR(1) phi=0.3 | 60 | 0.015 | 0.005 | 0.134 |
| AR(1) phi=0.6 | 30 | 0.097 | 0.022 | 0.278 |
| AR(1) phi=0.6 | 45 | 0.113 | 0.015 | 0.307 |
| AR(1) phi=0.6 | 60 | 0.097 | 0.013 | 0.288 |

Without whitening the phi=0.6 rate is ~10%: whitening is needed, not decoration.

Anytime check (IID Gaussian, n up to 45, 600 series, E_n evaluated at every n from 8 to 45):
`P(max_n E_n >= 20) = 0.012`, below the 5% Ville bound. Sample mean of E_n under H0 is 0.4-0.98
(not exactly 1) because E_n is very heavy-tailed; this is Monte Carlo noise, not a violation.

Power on a Gaussian trend that naive MK detects ~50% of the time (slope/sigma per year
= 0.0447, 0.0239, 0.0154 for n = 30, 45, 60):

| n | MK | e-process (shipped) | e-process (plain) |
|---|---|---|---|
| 30 | 0.51 | 0.084 | 0.105 |
| 45 | 0.50 | 0.094 | 0.113 |
| 60 | 0.54 | 0.091 | 0.109 |

The e-process is valid and very conservative; it needs a clearly larger trend than MK
(about slope/sigma = 0.035 per year at n = 45 for ~45% power).
Use it as an evidence measure alongside the p-value, not as a more sensitive test.

## trajectory / future paths

The old "simulate_arep_path" multiplicative update (`exp(omega*c_new*t - omega^2*I*t^2/2)`)
relied on the invalid statistic and is withdrawn. Nothing in the pipeline uses it.
Forward first-passage simulation of `E_n >= 20` can be done by extending the series by
bootstrap and re-evaluating `log_bayes_factor_trend`, but it is not implemented.
