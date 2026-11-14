"""
records.py, cumulative record rate vs harmonic expected baseline.

Under IID randomness, the expected number of records in n observations
is H_n = 1 + 1/2 + 1/3 + ... + 1/n (harmonic series).
Ratio > 1.5 indicates a trend is "loading the dice" for new extremes.
"""


def record_rate(vals, direction):
    n        = len(vals)
    observed = 1
    best     = vals[0]
    for v in vals[1:]:
        if direction == "upward" and v > best:
            observed += 1
            best = v
        elif direction == "downward" and v < best:
            observed += 1
            best = v
    expected = round(sum(1.0 / k for k in range(1, n + 1)), 2)
    ratio    = round(observed / expected, 2) if expected > 0 else 1.0
    return observed, expected, ratio
