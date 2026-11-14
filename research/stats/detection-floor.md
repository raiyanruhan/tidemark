# Detection floor

The minimum slope Mann-Kendall can detect at a given series length and noise level.
Inverting the analytical formula from z-growth-analytical.md.

---

## formula

At 80% power:
```
β_min = z_crit / (C · n^(3/2))
where z_crit = z_0.025 + z_0.2 = 1.96 + 0.842 = 2.802  (alpha=0.05 + 80% power)
      C = 1 / (2 * sqrt(pi)) = 0.282                    (from E[Z] = C * beta/sigma * n^(3/2))

      = 2.802 / (0.282 · n^(3/2))
      = 9.93 · σ / n^(3/2)
```

For reference z_crit values:
- 90% power: 1.96 + 1.28 = 3.24 (strictly)
- 80% power: 1.96 + 0.84 = 2.80
- 50% power: 1.96 + 0 = 1.96

---

## worked examples for n=45

| variable | typical σ | β_min (80% power) | β_min (90% power) |
|---|---|---|---|
| T2M (°C/yr) | 0.30 | 0.0099 | 0.011 |
| T2M_MAX (°C/yr) | 0.40 | 0.013 | 0.015 |
| PRECTOTCORR (mm/day/yr) | 0.040 | 0.0013 | 0.0015 |
| RH2M (%/yr) | 1.5 | 0.049 | 0.057 |
| EVLAND (mm/day/yr) | 0.020 | 0.00066 | 0.00076 |
| WS10M (m/s/yr) | 0.10 | 0.0033 | 0.0038 |

(80% power: 9.93 * σ / n^1.5 at n=45. 90% power: 11.49 * σ / n^1.5.)

σ values are rough estimates from residuals of typical MERRA-2 annual series.
Actual σ is computed from the real data and used in the formula.

---

## what it tells the user

For a significant trend: "Your slope (-0.021 °C/yr) is 1.6× above the detection floor (±0.013 °C/yr). High confidence."  
For a non-significant trend: "Your slope (−0.0003 mm/day/yr) is 0.3× the detection floor (−0.001 mm/day/yr). The trend is below what 45 years can resolve."

The second case is the most valuable output the tool produces. It ends the user's confusion.
A non-significant result is not always "data not yet convincing." Sometimes it means "the signal is too weak for this instrument (45 years of annual data)."

---

## detection floor changes with n

```
β_min(n) = 9.93 · σ / n^(3/2)

n=20:  β_min = 9.93 · σ / 89   ≈  0.111σ
n=45:  β_min = 9.93 · σ / 302  ≈  0.033σ
n=60:  β_min = 9.93 · σ / 465  ≈  0.021σ
n=100: β_min = 9.93 · σ / 1000 ≈  0.010σ
```

"Adding 15 more years (n=45→60) reduces the detection floor by 35%."
This is the clearest possible argument for why longer records matter.

---

## output format (proposed addition to case 2)

```
detection floor    ±0.0099 °C / year   (80% power at n=45, σ=0.30 °C)
observed slope     +0.0031 °C / year   [0.4x floor, below instrument sensitivity]
```

When slope/floor < 1.0: the Monte Carlo projection may produce a very late crossing year or many
never-crossed simulations. Both are honest answers, not bugs.
