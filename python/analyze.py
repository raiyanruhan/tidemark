#!/usr/bin/env python3
"""
analyze.py, orchestrator: fetch, analyse, output JSON to stdout.
Spawned by tidemark (Rust) as a subprocess.

Data sources:
  NASA POWER API  : https://power.larc.nasa.gov/            (climate, no auth)
  NASA GES DISC   : https://disc.gsfc.nasa.gov/             (GPM precip, Earthdata)
  NASA AppEEARS   : https://appeears.earthdatacloud.nasa.gov/ (LST/ET, Earthdata)
  ORNL DAAC MODIS : https://modis.ornl.gov/rst/api/v1/      (NDVI, no auth)
  NOAA MEI v2     : https://psl.noaa.gov/enso/mei/          (ENSO correction)
"""
import argparse
import json
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")

# Load .env from project root (two levels up from python/) if present.
# No dependency on python-dotenv; plain key=value parser.
def _load_dotenv():
    here    = os.path.dirname(os.path.abspath(__file__))
    dotenv  = os.path.join(here, "..", ".env")
    if not os.path.isfile(dotenv):
        return
    with open(dotenv) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val

_load_dotenv()

from changepoint import pettitt_changepoint
from decompose   import enso_correct, fetch_enso
from fetch       import (APPEEARS_PARAMS, COMPOUND_PARAMS, MODIS_PARAMS,
                         compute_compound_series, fetch_monthly,
                         monthly_to_annual, monthly_to_annual_min)
from milestones  import compute_milestones
from records     import record_rate
from seasonal    import run_seasonal_mk
from stats       import (compute_efficiency_metrics, compute_residuals,
                         detection_floor, lag1_acf, run_mannkendall)
from trajectory  import compute_pvalue_series, compute_trajectory


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--lat",   type=float, required=True)
    p.add_argument("--lon",   type=float, required=True)
    p.add_argument("--var",   required=True)
    p.add_argument("--start", type=int,   required=True)
    p.add_argument("--end",   type=int,   required=True)
    p.add_argument("--plot",  default=None, metavar="PATH",
                   help="save visualization to this PNG path (not yet implemented)")
    return p.parse_args()


def analyse(vals, years, param, last_year, monthly_by_year=None, progress=None):
    """
    Run the full Mann-Kendall pipeline on vals.
    Returns a result dict. monthly_by_year is optional (needed for seasonal).
    progress is an optional callable(str) for streaming status updates.
    """
    def emit(msg):
        if progress:
            progress(msg)

    n   = len(vals)
    emit("running Mann-Kendall test...")
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

    cp_detected, cp_idx, cp_p = pettitt_changepoint(vals)
    obs_r, exp_r, rec_ratio   = record_rate(vals, direction)
    seasonal                  = run_seasonal_mk(monthly_by_year) if monthly_by_year else {}

    result = {
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
        "changepoint": {
            "detected": cp_detected,
            "year":     years[cp_idx] if cp_detected else None,
            "p":        cp_p,
        },
        "records": {
            "observed": obs_r,
            "expected": exp_r,
            "ratio":    rec_ratio,
        },
        "seasonal": seasonal,
    }

    if significant:
        result["milestones"] = compute_milestones(vals, slope, last_year, param)
    else:
        emit("running Monte Carlo simulation (1000 paths)...")
        result["trajectory"] = compute_trajectory(
            vals, slope, intercept, residuals, z_score,
            sigma_n, phi, n, last_year, eff, progress=progress,
        )

    emit("computing p-value trajectory...")
    result["pvalue_series"] = compute_pvalue_series(vals, years, last_year)

    return result


def main():
    args = parse_args()

    try:
        if args.var in COMPOUND_PARAMS:
            annual          = compute_compound_series(args.lat, args.lon, args.var, args.start, args.end)
            monthly_by_year = None
        elif args.var in MODIS_PARAMS or args.var in APPEEARS_PARAMS:
            # satellite composites: cloud cover or processing gaps may leave some months missing
            monthly_by_year = fetch_monthly(args.lat, args.lon, args.var, args.start, args.end)
            annual          = monthly_to_annual_min(monthly_by_year, min_months=6)
            if len(annual) < 10:
                annual = monthly_to_annual_min(monthly_by_year, min_months=4)
            monthly_by_year = None   # skip seasonal MK; composite gaps make months unreliable
        else:
            monthly_by_year = fetch_monthly(args.lat, args.lon, args.var, args.start, args.end)
            annual          = monthly_to_annual(monthly_by_year)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)

    if len(annual) < 10:
        print(json.dumps({"error": f"only {len(annual)} complete years of data, need at least 10"}))
        sys.exit(1)

    years     = [y for y, _ in annual]
    vals      = np.array([v for _, v in annual])
    last_year = years[-1]

    # --- raw analysis ---
    result = analyse(vals, years, args.var, last_year, monthly_by_year)
    result.update({
        "lat":        args.lat,
        "lon":        args.lon,
        "param":      args.var,
        "start_year": years[0],
        "end_year":   last_year,
        "n_years":    len(vals),
    })

    # --- ENSO correction ---
    # Regresses out ENSO (El Nino-Southern Oscillation) variability to isolate
    # the anthropogenic forced trend from natural interannual oscillations.
    # Source: NOAA MEI v2 (Wolter & Timlin 2011, doi:10.1002/joc.2336).
    enso_annual, enso_source = fetch_enso(years)
    if enso_annual:
        corrected_vals, attribution = enso_correct(vals, years, enso_annual)
        if corrected_vals is not None:
            corr_result = analyse(corrected_vals, years, args.var, last_year)
            masking = round(corr_result["slope"] - result["slope"], 6)
            result["enso_correction"] = {
                "available":          True,
                "source":             enso_source,
                "enso_fraction":      attribution["enso_fraction"],
                "masking_rate":       masking,
                "corrected_vals":     corrected_vals.tolist(),
                "enso_component":     attribution["enso_component"],
                "trend_component":    attribution["trend_component"],
                "residual_component": attribution["residual_component"],
                "component_years":    attribution["component_years"],
                "corrected": {
                    "slope":       corr_result["slope"],
                    "p_value":     corr_result["p_value"],
                    "z_score":     corr_result["z_score"],
                    "significant": corr_result["significant"],
                    "trajectory":  corr_result.get("trajectory"),
                    "milestones":  corr_result.get("milestones"),
                },
            }
        else:
            result["enso_correction"] = {"available": False, "reason": "insufficient ENSO coverage"}
    else:
        result["enso_correction"] = {"available": False, "reason": "ENSO fetch failed"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
