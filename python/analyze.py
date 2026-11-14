#!/usr/bin/env python3
"""
analyze.py, orchestrator: fetch, analyse, output JSON to stdout.
Spawned by tidemark (Rust) as a subprocess.
"""
import argparse
import json
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")

from fetch       import fetch_monthly, monthly_to_annual, COMPOUND_PARAMS, compute_compound_series
from milestones  import compute_milestones
from stats       import (compute_residuals, detection_floor, lag1_acf,
                         run_mannkendall, compute_efficiency_metrics)
from trajectory  import compute_pvalue_series, compute_trajectory


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--lat",   type=float, required=True)
    p.add_argument("--lon",   type=float, required=True)
    p.add_argument("--var",   required=True)
    p.add_argument("--start", type=int,   required=True)
    p.add_argument("--end",   type=int,   required=True)
    return p.parse_args()


def analyse(vals, years, param, last_year):
    n   = len(vals)
    res = run_mannkendall(vals)

    slope       = float(res.slope)
    intercept   = float(res.intercept)
    tau         = float(res.Tau)
    z_score     = float(res.z)
    p_value     = float(res.p)
    significant = bool(res.h)
    direction   = "upward" if slope >= 0 else "downward"

    residuals   = compute_residuals(vals, slope, intercept)
    sigma_n     = float(np.std(residuals, ddof=1))
    phi         = lag1_acf(residuals)
    floor       = detection_floor(sigma_n, n)
    floor_ratio = abs(slope) / floor if floor > 1e-12 else 0.0
    eff         = compute_efficiency_metrics(residuals)

    return {
        "slope":           slope,
        "intercept":       intercept,
        "direction":       direction,
        "tau":             round(tau, 4),
        "z_score":         round(z_score, 4),
        "p_value":         p_value,
        "significant":     significant,
        "sigma_n":         sigma_n,
        "phi":             round(phi, 4),
        "detection_floor": floor,
        "floor_ratio":     round(floor_ratio, 2),
        "efficiency":      eff,
    }


def main():
    args = parse_args()

    try:
        if args.var in COMPOUND_PARAMS:
            annual = compute_compound_series(args.lat, args.lon, args.var, args.start, args.end)
        else:
            monthly_by_year = fetch_monthly(args.lat, args.lon, args.var, args.start, args.end)
            annual          = monthly_to_annual(monthly_by_year)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)

    if len(annual) < 10:
        print(json.dumps({"error": f"only {len(annual)} complete years, need at least 10"}))
        sys.exit(1)

    years     = [y for y, _ in annual]
    vals      = np.array([v for _, v in annual])
    last_year = years[-1]

    result = analyse(vals, years, args.var, last_year)

    slope     = result["slope"]
    intercept = result["intercept"]
    residuals = np.array(vals) - (intercept + slope * np.arange(len(vals)))

    if result["significant"]:
        result["milestones"] = compute_milestones(vals, slope, last_year, args.var)
    else:
        result["trajectory"] = compute_trajectory(
            vals, slope, intercept, residuals, result["z_score"],
            result["sigma_n"], result["phi"], len(vals), last_year, result["efficiency"],
        )

    result["pvalue_series"] = compute_pvalue_series(vals, years, last_year)

    result.update({
        "lat":        args.lat,
        "lon":        args.lon,
        "param":      args.var,
        "start_year": years[0],
        "end_year":   last_year,
        "n_years":    len(vals),
    })

    print(json.dumps(result))


if __name__ == "__main__":
    main()
