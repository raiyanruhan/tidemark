"""
changepoint.py, Pettitt (1979) non-parametric change-point test.
"""
import math

import numpy as np


def pettitt_changepoint(vals):
    """
    U[t] = sum_{i<=t, j>t} sign(x_j - x_i), K = max|U[t]|.
    p approx: 2*exp(-6*K^2 / (n^3+n^2)).
    Returns (detected, change_point_index, p_value).
    """
    n = len(vals)
    S = np.sign(vals[np.newaxis, :] - vals[:, np.newaxis])
    U = np.array([float(np.sum(S[:t + 1, t + 1:])) for t in range(n - 1)])
    K      = float(np.max(np.abs(U)))
    cp_idx = int(np.argmax(np.abs(U)))
    p      = min(1.0, 2.0 * math.exp(-6.0 * K ** 2 / (n ** 3 + n ** 2)))
    return p < 0.05, cp_idx, round(p, 4)
