# E-process: sequential evidence accumulation (anytime-validity under investigation)

Sources:
- Ramdas & Wang 2023 review (sas.uwaterloo.ca/~wang/files/e-review.pdf)
- "Anytime Validity is Free" JRSS-B 2025 (doi.org/10.1093/jrsssb/qkae104)
- Biometrika 2024 rank-based sequential independence test (doi.org/10.1093/biomet/asae023)

---

## the structural flaw in p-value based climate monitoring

P-values are only valid at a pre-specified sample size. If you check "is p < 0.05?" every year
for 20 years, your effective false positive rate is not 5%, it's roughly 30-40%.

Climate monitoring is continuous. The IPCC, national agencies, researchers all re-check
significance every few years as new data arrives. This means every existing climate trend tool
has an inflated false positive rate when used as intended. No tool addresses this.

---

## what an e-process is

An e-process E_n is a nonneg adapted process such that for every stopping time tau:

```
E[E_tau | H0] <= 1
```

Reject H0 when E_n >= 1/alpha. False positive rate stays <= alpha regardless of
how many times you check.

E_n = 20 means "20x evidence against no-trend": interpretable, not just yes/no.
Check every year with no Bonferroni correction. E-values compose multiplicatively across
independent datasets. Under H1 (real trend), E_n grows and the rate encodes evidence speed.

---

## "Anytime Validity is Free" (JRSS-B 2025)

Any fixed-sample test statistic T_n with known null CDF can be converted to anytime-valid
with no loss of asymptotic power. Construction: compute p_n at each step, build e-process
via Kelly-criterion betting. Mann-Kendall can be sequentialized at no cost in power.

---

## rank-based e-processes: closest existing work

No paper combines e-processes with linear climate trend detection.

Biometrika 2024 builds a rank-based test martingale for two-sample independence.
Not the linear trend setting, but methodologically the same structure.

arXiv 2203.03532: nonparametric change detection via e-processes for a single change point.
Not a continuous linear trend.

arXiv 2604.20612: e-values for monotonicity/unimodality on discrete distributions.
Shape constraints, not regression trend.

Hallin & Werker 2011: adaptive rank unit root tests in econometrics.
Different question (stationarity), different domain.

---

## connection to the existing Monte Carlo

Current Monte Carlo: extend 1000 times, run MK at each future year, check p < 0.05.
Problem: each simulation checks p < 0.05 at multiple future time points, inflating false alarms.
The projected crossing-year distribution mixes true significance with repeated-testing artifacts.

E-process replacement: simulate 1000 future e-process paths. First passage time of E_n >= 20
is the significance year distribution. Each path is a single monotone trajectory, no repeated
testing issue.

---

## what changes in output

Old: "p-value 0.08, not yet significant"

New:
```
evidence state    E_n = 7.3   (threshold: 20)
growth rate       +1.4 E-units/year
projected cross   2031, 85% PI: 2027-2035   (predictive interval under assumed model)
```

E_n = 7.3 is more informative than p = 0.08. Evidence is building at a measurable rate,
the result is valid even though we checked last year, and the growth rate gives a trajectory.

---

## implementation

Option A (exact, via AVIF): at each step compute MK Z, get p_t from null distribution,
run Kelly betting optimization. O(n) per update.

Option B (approximate, via Gaussian score process): build Lambda_n (see arep.md),
then E_n = exp(omega_hat * Lambda_n - omega_hat^2 * I_hat * n^3 / 6).
Valid asymptotically for n > 30.

For v1: Option B. Note in code comments that the exact version exists via AVIF.
