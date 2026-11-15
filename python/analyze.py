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

from changepoint import trend_break_test
from decompose   import enso_correct, fetch_enso
from fetch       import load_annual
from milestones  import compute_milestones
from records     import record_rate
from seasonal    import run_seasonal_mk
from stats       import (bocpd_analysis, compute_eprocess,
                         compute_efficiency_metrics, detection_floor,
                         ita_analysis, mk_verdict, partial_mk)
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


def analyse(vals, years, param, last_year, monthly_by_year=None, progress=None, cancel=None, oni=None):
    """
    Run the full Mann-Kendall pipeline on vals.
    Returns a result dict. monthly_by_year is optional (needed for seasonal).
    progress is an optional callable(str) for streaming status updates.
    """
    def emit(msg):
        if progress:
            progress(msg)

    n   = len(vals)
    if any(b - a != 1 for a, b in zip(years, years[1:])):
        raise ValueError("annual series has gaps; time axis would not be calendar years")
    emit("running Mann-Kendall test...")
    v           = mk_verdict(vals)
    res         = v["res"]

    slope       = v["slope"]
    intercept   = v["intercept"]
    tau         = float(res.Tau)
    z_score     = v["z"]
    p_value     = v["p"]
    significant = v["significant"]
    direction   = "upward" if slope >= 0 else "downward"

    residuals   = v["residuals"]
    sigma_n     = float(np.std(residuals, ddof=1))
    phi         = v["phi"]
    method      = v["method_label"]

    floor       = detection_floor(sigma_n, n)
    floor_ratio = abs(slope) / floor if floor > 1e-12 else 0.0
    eff         = compute_efficiency_metrics(residuals)

    eprocess   = compute_eprocess(vals)

    ita_raw = ita_analysis(vals)
    ita = ita_raw if (ita_raw["low_slope"] * ita_raw["high_slope"] < 0) else None

    pmk = None
    if oni is not None:
        oni_aligned = np.array([oni[yr] for yr in years if yr in oni])
        idx_aligned = [i for i, yr in enumerate(years) if yr in oni]
        if len(idx_aligned) >= max(15, int(n * 0.8)):
            vals_aligned = vals[idx_aligned]
            pmk_raw = partial_mk(vals_aligned, oni_aligned)
            if pmk_raw is not None:
                pmk = pmk_raw
                pmk["z_raw"]           = round(z_score, 4)
                pmk["p_raw"]           = round(p_value, 6)
                pmk["significant_raw"] = significant

    cp_detected, cp_idx, cp_p = trend_break_test(vals)
    bocpd_result              = bocpd_analysis(vals, years)
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
        "method":          method,
        "partial_mk":      pmk,
        "ita":             ita,
        "sigma_n":         sigma_n,
        "phi":             round(phi, 4),
        "detection_floor": floor,
        "floor_ratio":     round(floor_ratio, 2),
        "efficiency":      eff,
        "e_process":       eprocess,
        "changepoint": {
            "detected": cp_detected,
            "year":     years[cp_idx] if cp_detected else None,
            "p":        cp_p,
        },
        "bocpd": bocpd_result,
        "records": {
            "observed": obs_r,
            "expected": exp_r,
            "ratio":    rec_ratio,
        },
        "seasonal": seasonal,
    }

    if significant:
        result["milestones"] = compute_milestones(vals, slope, intercept, last_year, param)
    else:
        emit("running Monte Carlo simulation (1000 paths)...")
        result["trajectory"] = compute_trajectory(
            vals, slope, intercept, residuals, z_score,
            sigma_n, phi, n, last_year, eff, param_code=param,
            progress=progress, cancel=cancel,
        )

    emit("computing p-value trajectory...")
    result["pvalue_series"] = compute_pvalue_series(vals, years, last_year)

    return result


def main():
    args = parse_args()

    try:
        annual, monthly_by_year, series_info = load_annual(
            args.lat, args.lon, args.var, args.start, args.end)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)

    if len(annual) < 10:
        print(json.dumps({"error": f"only {len(annual)} complete years of data, need at least 10"}))
        sys.exit(1)

    years     = [y for y, _ in annual]
    vals      = np.array([v for _, v in annual])
    last_year = years[-1]

    # --- ENSO index (MEI v2 or ONI fallback) — shared by ENSO correction and partial MK ---
    enso_annual, enso_source = fetch_enso(years)
    oni_for_pmk = enso_annual if len(enso_annual) >= len(years) * 0.8 else None

    # --- raw analysis ---
    result = analyse(vals, years, args.var, last_year, monthly_by_year, oni=oni_for_pmk)
    result.update({
        "lat":        args.lat,
        "lon":        args.lon,
        "param":      args.var,
        "start_year": years[0],
        "end_year":   last_year,
        "n_years":    len(vals),
        "series":     series_info,
    })

    # --- ENSO correction ---
    # Regresses out ENSO (El Nino-Southern Oscillation) variability to isolate
    # the anthropogenic forced trend from natural interannual oscillations.
    # Source: NOAA MEI v2 (Wolter & Timlin 2011, doi:10.1002/joc.2336).
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
