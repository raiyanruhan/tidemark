"""
milestones.py, project Sen's slope forward to real-world policy thresholds.

Thresholds and sources:
  Temperature:  Paris Agreement (2015), Art. 2: +1.5C and +2.0C above pre-industrial
  Precipitation/Evaporation: standard drought classification (% of baseline)
  Humidity:     semi-arid (<40%) and arid (<30%) zone definitions (Kottek et al. 2006)
  VPD:          crop stress thresholds (Lefsrud et al. 2020, doi:10.1016/j.scitotenv...)
  Soil moisture: FAO-56 (Allen et al. 1998) field capacity guidelines
  Frost days:   frost-free growing season literature
  Wind speed:   Beaufort scale; Roderick et al. (2007) terrestrial stilling
  DTR:          diurnal range literature
"""
import math

import numpy as np


def _ceil_years(numerator, rate):
    # round before ceil: exact divisions like 0.1/0.1 in IEEE 754 give
    # 1.0000000000000002, making ceil overshoot the year by 1
    return int(math.ceil(round(numerator / rate, 10)))


def compute_milestones(vals, slope, last_year, param):
    """
    Years when variable crosses real-world thresholds at current Sen's slope rate.
    Returns list of {delta, unit, year, label}. Only meaningful for significant trends.
    """
    milestones = []
    n = len(vals)

    if param in ("T2M", "T2M_MAX", "T2M_MIN") and slope > 1e-6:
        baseline_n      = min(30, n)
        baseline        = float(np.mean(vals[:baseline_n]))
        current_anomaly = float(vals[-1]) - baseline
        for delta, label in [
            (0.5,  None),
            (1.0,  None),
            (1.5,  "Paris Agreement +1.5C threshold"),
            (2.0,  "Paris Agreement +2.0C threshold"),
        ]:
            remaining = delta - current_anomaly
            if remaining <= 0:
                continue
            milestones.append({
                "delta": f"+{delta:.1f}", "unit": "C",
                "year":  last_year + _ceil_years(remaining, slope),
                "label": label,
            })

    elif param in ("PRECTOTCORR", "EVLAND") and slope < -1e-9:
        baseline = float(np.mean(vals))
        last_val = float(vals[-1])
        for pct, label in [
            (0.80, "80% of baseline mean"),
            (0.60, "moderate drought (60% of baseline)"),
            (0.40, "severe drought (40% of baseline)"),
        ]:
            target = baseline * pct
            if last_val <= target:
                continue
            milestones.append({
                "delta": f"{int(pct*100)}% mean", "unit": "",
                "year":  last_year + _ceil_years(last_val - target, abs(slope)),
                "label": label,
            })

    elif param == "RH2M" and slope < -1e-9:
        last_val = float(vals[-1])
        for target, label in [
            (40.0, "semi-arid threshold (RH < 40%)"),
            (30.0, "arid threshold (RH < 30%)"),
        ]:
            if last_val <= target:
                continue
            milestones.append({
                "delta": f"< {int(target)}%", "unit": "",
                "year":  last_year + _ceil_years(last_val - target, abs(slope)),
                "label": label,
            })

    elif param == "VPD" and slope > 1e-9:
        last_val = float(vals[-1])
        for target, label in [
            (1.5, "moderate crop stress (VPD > 1.5 kPa)"),
            (2.0, "high crop stress (VPD > 2.0 kPa)"),
            (3.0, "severe stress, most crops fail (VPD > 3.0 kPa)"),
        ]:
            if last_val >= target:
                continue
            milestones.append({
                "delta": f"> {target:.1f} kPa", "unit": "",
                "year":  last_year + _ceil_years(target - last_val, slope),
                "label": label,
            })

    elif param in ("GWETROOT", "GWETTOP", "GWETPROF") and slope < -1e-9:
        last_val = float(vals[-1])
        for target, label in [
            (0.3, "crop water stress onset (FAO-56)"),
            (0.2, "severe stress, yield impact likely"),
        ]:
            if last_val <= target:
                continue
            milestones.append({
                "delta": f"< {target:.1f}", "unit": "",
                "year":  last_year + _ceil_years(last_val - target, abs(slope)),
                "label": label,
            })

    elif param == "FROST_DAYS" and slope < -1e-9:
        last_val = float(vals[-1])
        for target, label in [
            (1.0, "near frost-free conditions (< 1 day/month)"),
            (0.5, "frost-free year-round"),
        ]:
            if last_val <= target:
                continue
            milestones.append({
                "delta": f"< {target:.1f}", "unit": "days/month",
                "year":  last_year + _ceil_years(last_val - target, abs(slope)),
                "label": label,
            })

    elif param == "FROST_DAYS" and slope > 1e-9:
        last_val = float(vals[-1])
        for target, label in [
            (1.0, "> 1 frost day/month"),
            (5.0, "significant frost risk"),
        ]:
            if last_val >= target:
                continue
            milestones.append({
                "delta": f"> {target:.0f}", "unit": "days/month",
                "year":  last_year + _ceil_years(target - last_val, slope),
                "label": label,
            })

    elif param in ("TSOIL1", "TS") and slope > 1e-6:
        baseline_n      = min(30, n)
        baseline        = float(np.mean(vals[:baseline_n]))
        current_anomaly = float(vals[-1]) - baseline
        for delta, label in [
            (0.5, None),
            (1.0, None),
            (1.5, "Paris Agreement +1.5C threshold"),
            (2.0, "Paris Agreement +2.0C threshold"),
        ]:
            remaining = delta - current_anomaly
            if remaining <= 0:
                continue
            milestones.append({
                "delta": f"+{delta:.1f}", "unit": "C",
                "year":  last_year + _ceil_years(remaining, slope),
                "label": label,
            })

    elif param == "WS10M" and slope > 1e-9:
        last_val = float(vals[-1])
        for target, label in [
            (5.5, "Beaufort 4 (light wind)"),
            (8.0, "Beaufort 5, optimal wind energy threshold"),
        ]:
            if last_val >= target:
                continue
            milestones.append({
                "delta": f"> {target:.1f}", "unit": "m/s",
                "year":  last_year + _ceil_years(target - last_val, slope),
                "label": label,
            })

    elif param == "WS10M" and slope < -1e-9:
        last_val = float(vals[-1])
        for target, label in [
            (3.0, "terrestrial stilling threshold (Roderick 2007)"),
            (2.0, "calm, reduced evapotranspiration"),
        ]:
            if last_val <= target:
                continue
            milestones.append({
                "delta": f"< {target:.1f}", "unit": "m/s",
                "year":  last_year + _ceil_years(last_val - target, abs(slope)),
                "label": label,
            })

    elif param == "DTR" and slope > 1e-9:
        last_val = float(vals[-1])
        for target, label in [
            (12.0, "large diurnal swing, crop thermal stress"),
            (15.0, "extreme diurnal range"),
        ]:
            if last_val >= target:
                continue
            milestones.append({
                "delta": f"> {target:.0f}", "unit": "C",
                "year":  last_year + _ceil_years(target - last_val, slope),
                "label": label,
            })

    elif param == "DTR" and slope < -1e-9:
        last_val = float(vals[-1])
        # compressed DTR = more cloud cover or humidity; below 8C is a documented signal
        for target, label in [
            (8.0, "compressed diurnal range, cloud/humidity increase signal"),
        ]:
            if last_val <= target:
                continue
            milestones.append({
                "delta": f"< {target:.0f}", "unit": "C",
                "year":  last_year + _ceil_years(last_val - target, abs(slope)),
                "label": label,
            })

    elif param == "NDVI" and slope < -1e-6:
        last_val = float(vals[-1])
        # NDVI thresholds: Tucker (1979) vegetation classification
        for target, label in [
            (0.5, "moderate vegetation decline"),
            (0.3, "sparse vegetation (bare soil encroachment)"),
            (0.2, "near-bare soil, desertification risk"),
        ]:
            if last_val <= target:
                continue
            milestones.append({
                "delta": f"< {target:.1f}", "unit": "",
                "year":  last_year + _ceil_years(last_val - target, abs(slope)),
                "label": label,
            })

    elif param == "NDVI" and slope > 1e-6:
        last_val = float(vals[-1])
        for target, label in [
            (0.5, "moderate vegetation health"),
            (0.6, "good vegetation cover"),
            (0.7, "dense vegetation/reforestation milestone"),
        ]:
            if last_val >= target:
                continue
            milestones.append({
                "delta": f"> {target:.1f}", "unit": "",
                "year":  last_year + _ceil_years(target - last_val, slope),
                "label": label,
            })

    return milestones[:4]
