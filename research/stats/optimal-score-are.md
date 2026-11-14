# Optimal rank score, ARE formula correction, Fisher information CRB

Sources:
- Hajek, Ann. Math. Statist. 33 (1962), 1124-1147
  (not 1968, that paper is the projection lemma for asymptotic normality, not optimality)
- Hajek & Sidak, Theory of Rank Tests, 2nd ed. 1999 (with Pranab K. Sen)
- Bickel (1982), "On adaptive estimation," Ann. Statist. 10, 647-671
- Hallin & Werker (2011), J. Econometrics 163(2), 200-214

---

## Hajek 1962: optimal score for linear trend

For model Y_i = beta*c_i + eps_i with eps ~ f(x):

The locally most powerful rank test uses scores:

```
a(i) = phi_opt(i/(N+1))
     = -f'(F_inv(i/(N+1))) / f(F_inv(i/(N+1)))
```

This is the negative log-derivative of f evaluated at the population quantile.
Equivalent: the Fisher score function c(x) = -f'(x)/f(x) composed with the probability
integral transform.

Mann-Kendall uses phi_MK(u) = sign(u - 1/2). Optimal only for the logistic distribution.

Van der Waerden uses phi_vdW(u) = Phi_inv(u) (inverse normal CDF of rank).
Optimal for Gaussian. ARE vs t-test >= 1 for all continuous f (Chernoff-Savage 1958).

---

## ARE formula: there is an error in common presentations

Often stated as: ARE(MK vs optimal) = 12*sigma^2 * [integral of f^2(x) dx]^2

This is wrong. That formula computes ARE(MK vs OLS/t-test), not MK vs optimal rank test.

Correct derivations:

Pitman efficacy of MK test:
```
e_MK = 12 * [integral of f^2(x) dx]^2
```

ARE of MK vs t-test/OLS:
```
ARE(MK vs OLS) = sigma^2 * e_MK = 12*sigma^2 * [integral of f^2(x) dx]^2
```

Under normality: integral of f^2 = 1/(2*sigma*sqrt(pi)), so ARE = 12*sigma^2 * 1/(4*sigma^2*pi) = 3/pi ~ 0.955.

Fisher information of f:
```
I(f) = integral of [f'(x)/f(x)]^2 * f(x) dx
```

Efficacy of optimal rank test:
```
e_opt = I(f)
```

ARE(MK vs optimal rank test), the correct formula:
```
ARE(MK vs optimal) = e_MK / e_opt = 12*sigma^2 * [integral of f^2]^2 / I(f)
```

Under normality: I(f_normal) = 1/sigma^2, so ARE(MK vs opt) = 3/pi ~ 0.955.
MK needs ~5% more data than optimal even at Gaussian noise.

For right-skewed precipitation (gamma-like): I(f_gamma) >> 1/sigma^2.
ARE(MK vs opt) < 1. MK can need 30-50% more data than optimal. No paper has computed
exact numbers for precipitation distributions specifically.

---

## van der Waerden vs MK

Chernoff-Savage 1958: ARE(van der Waerden vs t-test) >= 1 for all continuous f.
Under symmetric heavy tails, van der Waerden can be beaten by Wilcoxon-type tests
because rank magnitudes get dominated by outliers. For right-skewed distributions
(arid precipitation): van der Waerden wins over MK.

Practical recommendation: use Hamed-Rao (MK variant) for the data assessment as it
matches existing literature. Use c_hat(x) = -f_hat'/f_hat inside AREP for efficiency.

---

## Fisher information lower bound on detection time

Weatherhead 1998 formula: n* = (3.3 * sigma_N / |omega|)^(2/3) * ((1+phi)/(1-phi))^(1/3)
Derived for OLS/Gaussian. The 3.3*sigma_N/|omega| term comes from power analysis of the OLS
slope standard error: se(omega_hat) ~ sigma/n^(3/2) for equispaced data.

For non-Gaussian f via Fisher information, the Cramer-Rao minimum variance of any unbiased
slope estimator is:

```
Var(omega_hat) >= 1 / (I(f) * sum(t^2)) ~ 3 / (I(f) * n^3)   for equispaced t=1..n
```

For Gaussian: I(f) = 1/sigma^2, so Var >= 3*sigma^2/n^3 = Var(OLS slope). OLS achieves CRB.

The CRB-based minimum detection time (theoretical floor, no test can beat this):

```
n*_CRB = (3.3 / (|omega| * sqrt(I(f)/sigma^2)))^(2/3) * ((1+phi)/(1-phi))^(1/3)
       = n*_Weatherhead * (I(f) * sigma^2)^(-1/3)
```

Under Gaussian: I(f)*sigma^2 = 1, so n*_CRB = n*_Weatherhead.
Under right-skewed f: I(f)*sigma^2 > 1, so n*_CRB < n*_Weatherhead.
Weatherhead is pessimistic for non-Gaussian noise.

This generalization is not in any existing paper or tool.

---

## adjusting Weatherhead for non-Gaussian noise

Weatherhead uses OLS assumptions. For non-Gaussian f, the correct scaling is:

```
n*_MK = n*_Weatherhead * (1/ARE(MK vs OLS))^(1/3)
```

The exponent is 1/3, not 1. The Weatherhead formula scales as (sigma/omega)^(2/3), so
replacing sigma_eff changes n* by the (2/3) power of the variance ratio, which gives (1/3)
in terms of ARE.

If ARE(MK vs OLS) = 0.9: n*_MK = n*_Weatherhead * (1/0.9)^(1/3) = x1.034, so 3.4% more years.
If ARE(MK vs OLS) = 1.3 (MK better than OLS under heavy tails): n*_MK = x0.906, so 9.4% fewer.

For right-skewed arid precipitation, ARE(MK vs OLS) can exceed 1, so MK needs slightly
fewer years than Weatherhead predicts. But ARE(MK vs optimal) < 1, so the optimal rank
test is still better.

---

## Python implementation

```python
from scipy.stats import gaussian_kde
import numpy as np

def compute_efficiency_metrics(residuals):
    """
    Returns ARE(MK vs OLS), ARE(MK vs optimal), I_fisher.
    residuals: numpy array of detrended residuals
    """
    sigma2 = np.var(residuals)
    kde = gaussian_kde(residuals, bw_method='silverman')

    x = np.linspace(residuals.min() - 2*residuals.std(),
                    residuals.max() + 2*residuals.std(), 1000)
    dx = x[1] - x[0]
    f = kde(x)

    int_f_sq = np.trapz(f**2, x)

    h = 1e-4
    score = -(kde(x + h) - kde(x - h)) / (2 * h * np.maximum(f, 1e-10))
    score = np.clip(score, np.percentile(score, 2), np.percentile(score, 98))

    I_fisher = np.trapz(score**2 * f, x)

    e_MK = 12 * sigma2 * int_f_sq**2
    ARE_MK_vs_OLS = e_MK
    ARE_MK_vs_opt = e_MK / (I_fisher * sigma2)

    return {
        'I_fisher': I_fisher,
        'ARE_MK_vs_OLS': ARE_MK_vs_OLS,
        'ARE_MK_vs_optimal': ARE_MK_vs_opt,
        'int_f_squared': int_f_sq,
        'sigma2': sigma2,
    }
```

---

## what to add to output

Print the efficiency block when |skewness| > 0.5 or normality test p < 0.05.
Otherwise the difference is negligible and clutters output for well-behaved Gaussian data.

```
method efficiency   ARE = 0.71 vs optimal rank test
                    MK needs 1.12x more data than theoretically required for this noise shape
                    information gap: ~4 years at current rate
```

---

## connection to Le Cam one-step (Bickel 1982)

The Bickel adaptive estimator says: given a consistent initial estimator and a kernel estimate
of the score function c_hat(x) from residuals, one Newton-Raphson step achieves full Fisher
efficiency. Applied here:

1. omega_hat_0 = Sen's slope (consistent, not efficient)
2. c_hat(x) = -f_hat'/f_hat from KDE of residuals at omega_hat_0
3. omega_hat_1 = omega_hat_0 + sum(c_hat(eps_hat_t)*t) / (I_hat * sum(t^2))

This one-step estimator achieves CRB efficiency. Hallin & Werker 2011 applied this to unit
root tests in econometrics. Never applied to Mann-Kendall or climate trend detection.

For v1: use Sen's slope throughout. The one-step correction is a v2 extension.
