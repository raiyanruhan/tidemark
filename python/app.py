"""
app.py, Flask web interface for tidemark.
All analysis calls real NASA data. No demo data.
"""
import sys
import os

# Allow importing sibling modules (fetch, stats, etc.) regardless of CWD
sys.path.insert(0, os.path.dirname(__file__))

# Load .env from project root if present (no python-dotenv dependency).
def _load_dotenv():
    here   = os.path.dirname(os.path.abspath(__file__))
    dotenv = os.path.join(here, "..", ".env")
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

import json
import os
import threading
import time
import uuid

import numpy as np
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_file

from analyze   import analyse
from fetch     import (fetch_monthly, monthly_to_annual, monthly_to_annual_min,
                       compute_compound_series, APPEEARS_PARAMS,
                       COMPOUND_PARAMS, GESDISC_PARAMS, LAADS_PARAMS, MODIS_PARAMS)
from decompose import fetch_enso, enso_correct

app = Flask(__name__)

# In-memory result store: token -> (stored_at, result bundle).
# Expires after 10 minutes; not consumed on read so the link stays shareable.
_result_store = {}
_RESULT_TTL    = 600  # seconds

# In-flight job store: job_id -> threading.Event (cancel flag).
# Entry is removed when the worker thread finishes or the SSE stream closes.
_job_store = {}


class _Cancelled(Exception):
    pass

#, location registry --------------------------------------------------
# Same cities as src/locations.rs. lat, lon, display name.
LOCATIONS = {
    "dhaka":        (23.81,  90.41,  "Dhaka, Bangladesh"),
    "chittagong":   (22.33,  91.84,  "Chittagong, Bangladesh"),
    "sylhet":       (24.90,  91.87,  "Sylhet, Bangladesh"),
    "rajshahi":     (24.37,  88.60,  "Rajshahi, Bangladesh"),
    "bogura":       (24.85,  89.37,  "Bogura, Bangladesh"),
    "khulna":       (22.82,  89.55,  "Khulna, Bangladesh"),
    "cairo":        (30.06,  31.25,  "Cairo, Egypt"),
    "nairobi":      (-1.29,  36.82,  "Nairobi, Kenya"),
    "lagos":        (6.52,   3.38,   "Lagos, Nigeria"),
    "accra":        (5.56,   -0.20,  "Accra, Ghana"),
    "addisababa":   (9.03,   38.74,  "Addis Ababa, Ethiopia"),
    "khartoum":     (15.55,  32.53,  "Khartoum, Sudan"),
    "mogadishu":    (2.05,   45.34,  "Mogadishu, Somalia"),
    "dakar":        (14.72,  -17.47, "Dakar, Senegal"),
    "mumbai":       (19.08,  72.88,  "Mumbai, India"),
    "delhi":        (28.61,  77.21,  "New Delhi, India"),
    "karachi":      (24.86,  67.01,  "Karachi, Pakistan"),
    "colombo":      (6.93,   79.85,  "Colombo, Sri Lanka"),
    "kathmandu":    (27.72,  85.32,  "Kathmandu, Nepal"),
    "bangkok":      (13.75,  100.52, "Bangkok, Thailand"),
    "jakarta":      (-6.21,  106.85, "Jakarta, Indonesia"),
    "manila":       (14.60,  120.98, "Manila, Philippines"),
    "hanoi":        (21.03,  105.85, "Hanoi, Vietnam"),
    "yangon":       (16.87,  96.14,  "Yangon, Myanmar"),
    "beijing":      (39.91,  116.39, "Beijing, China"),
    "shanghai":     (31.23,  121.47, "Shanghai, China"),
    "tokyo":        (35.69,  139.69, "Tokyo, Japan"),
    "seoul":        (37.57,  126.98, "Seoul, South Korea"),
    "dubai":        (25.20,  55.27,  "Dubai, UAE"),
    "riyadh":       (24.69,  46.72,  "Riyadh, Saudi Arabia"),
    "tehran":       (35.69,  51.39,  "Tehran, Iran"),
    "istanbul":     (41.01,  28.95,  "Istanbul, Turkey"),
    "london":       (51.51,  -0.13,  "London, UK"),
    "paris":        (48.85,  2.35,   "Paris, France"),
    "berlin":       (52.52,  13.40,  "Berlin, Germany"),
    "moscow":       (55.75,  37.62,  "Moscow, Russia"),
    "newyork":      (40.71,  -74.01, "New York, USA"),
    "losangeles":   (34.05,  -118.24,"Los Angeles, USA"),
    "miami":        (25.77,  -80.19, "Miami, USA"),
    "mexico":       (19.43,  -99.13, "Mexico City, Mexico"),
    "bogota":       (4.71,   -74.07, "Bogota, Colombia"),
    "lima":         (-12.05, -77.04, "Lima, Peru"),
    "saopaulo":     (-23.55, -46.63, "Sao Paulo, Brazil"),
    "buenosaires":  (-34.60, -58.38, "Buenos Aires, Argentina"),
    "sydney":       (-33.87, 151.21, "Sydney, Australia"),
}

# Tuple: (alias, code, label, unit, start_epoch)
# start_epoch is the earliest year the data source covers for that variable.
VARIABLES = [
    ("temperature",        "T2M",         "Temperature (2m)",          "degC",     1981),
    ("max-temperature",    "T2M_MAX",     "Max Temperature (2m)",      "degC",     1981),
    ("min-temperature",    "T2M_MIN",     "Min Temperature (2m)",      "degC",     1981),
    ("rainfall",           "PRECTOTCORR", "Precipitation (GPM)",       "mm/day",   2001),
    ("humidity",           "RH2M",        "Relative Humidity (2m)",    "%",        1981),
    ("evaporation",        "EVLAND",      "Evaporation",               "mm/day",   1981),
    ("wind",               "WS10M",       "Wind Speed (10m)",          "m/s",      1981),
    ("vpd",                "VPD",         "Vapor Pressure Deficit",    "kPa",      1981),
    ("dtr",                "DTR",         "Diurnal Temp Range",        "degC",     1981),
    ("soil",               "GWETROOT",    "Root Zone Soil Moisture",   "fraction", 1981),
    ("surface-soil",       "GWETTOP",     "Surface Soil Moisture",     "fraction", 1981),
    ("profile-soil",       "GWETPROF",    "Full Profile Soil Moisture","fraction", 1981),
    ("frost",              "FROST_DAYS",  "Frost Days",                "days",     1981),
    ("soil-temp",          "TSOIL1",      "Soil Temperature",          "degC",     1981),
    ("skin-temp",          "TS",          "Earth Skin Temperature",    "degC",     1981),
    ("ndvi",               "NDVI",        "Vegetation Index (NDVI)",   "ratio",    2000),
    ("lst",                "LST",         "Land Surface Temp (MODIS)", "degC",     2001),
    ("et",                 "ET_MOD16",    "Evapotranspiration (MODIS)","mm/day",   2001),
    ("aod",                "MOD08_M3",    "Aerosol Optical Depth (MODIS)", "unitless", 2002),
]

VAR_BY_ALIAS = {v[0]: v for v in VARIABLES}
VAR_BY_CODE  = {v[1]: v for v in VARIABLES}

_UNIT_PROSE = {
    "degC":     "degrees C",
    "mm/day":   "mm per day",
    "%":        "%",
    "m/s":      "m/s",
    "kPa":      "kPa",
    "fraction": "fraction",
}

_DIR_WORDS = {
    "T2M":         ("rising",        "cooling"),
    "T2M_MAX":     ("rising",        "cooling"),
    "T2M_MIN":     ("rising",        "cooling"),
    "DTR":         ("widening",      "narrowing"),
    "PRECTOTCORR": ("increasing",    "decreasing"),
    "EVLAND":      ("increasing",    "decreasing"),
    "RH2M":        ("rising",        "dropping"),
    "WS10M":       ("strengthening", "weakening"),
    "VPD":         ("rising",        "dropping"),
    "GWETROOT":    ("rising",        "dropping"),
    "LST":         ("rising",        "cooling"),
    "ET_MOD16":    ("increasing",    "decreasing"),
    "MOD08_M3":    ("rising",        "falling"),
}


def generate_summary(result, display, label, unit):
    """
    Plain-English interpretation of the analysis result.
    Returns a list of sentence strings (1-4 items).
    Audience: motivated student, not a statistician.
    """
    slope       = result["slope"]
    significant = result["significant"]
    p_value     = result["p_value"]
    floor_ratio = result["floor_ratio"]
    n_years     = result["n_years"]
    start_year  = result["start_year"]
    end_year    = result["end_year"]
    code        = result.get("param", "")

    unit_prose = _UNIT_PROSE.get(unit, unit)

    per_decade = abs(slope) * 10
    if per_decade >= 10:
        rate_str = f"{per_decade:.1f} {unit_prose} per decade"
    elif per_decade >= 0.1:
        rate_str = f"{per_decade:.2f} {unit_prose} per decade"
    else:
        rate_str = f"{per_decade:.3f} {unit_prose} per decade"

    up_word, down_word = _DIR_WORDS.get(code, ("increasing", "decreasing"))
    dir_word = up_word if slope > 0 else down_word

    base_label = label.split("(")[0].strip().lower()

    sentences = []

    sentences.append(
        f"{display}'s {base_label} has been {dir_word} at around {rate_str}, "
        f"based on {n_years} years of NASA satellite data ({start_year} to {end_year})."
    )

    if significant:
        if p_value < 0.001:
            conf = "very strong"
        elif p_value < 0.01:
            conf = "strong"
        else:
            conf = "sufficient"
        sentences.append(
            f"The statistical evidence is {conf}. This is a real trend, not random variation in the data."
        )
    else:
        traj     = result.get("trajectory") or {}
        mc_median = traj.get("mc_median")
        if floor_ratio < 1.0:
            sentences.append(
                f"The signal is real but faint. The current {n_years}-year record is not long enough "
                f"to confirm a trend this small. More years of data are needed before a conclusion can be drawn."
            )
        elif mc_median:
            sentences.append(
                f"The trend is consistent but not yet conclusive. "
                f"Based on Monte Carlo simulation, it is likely to reach statistical confidence around {mc_median}."
            )
        else:
            sentences.append(
                "The trend has not yet reached statistical significance. More data is needed to confirm it."
            )

    if significant:
        milestones = result.get("milestones") or []
        if milestones:
            m    = milestones[0]
            note = m.get("label") or f"a change of {m['delta']} {unit_prose}"
            sentences.append(f"At the current rate, {note} is projected around {m['year']}.")
    else:
        cp = result.get("changepoint") or {}
        if cp.get("detected") and cp.get("year"):
            sentences.append(
                f"There is evidence of a step change around {cp['year']}, "
                f"suggesting the rate may have shifted at that point."
            )

    bocpd = result.get("bocpd") or {}
    if bocpd.get("changepoint_detected") and bocpd.get("changepoint_year"):
        cp_yr   = bocpd["changepoint_year"]
        conf_pct = round(bocpd.get("changepoint_confidence", 0) * 100)
        sb = bocpd.get("slope_before")
        sa = bocpd.get("slope_after")
        if sb is not None and sa is not None and abs(sb) > 1e-9:
            ratio = abs(sa) / abs(sb)
            if sb * sa < 0:
                rate_note = f"and the trend reversed sign"
            elif ratio >= 1.5:
                rate_note = f"and the rate steepened {ratio:.1f}×"
            elif ratio <= 0.67:
                rate_note = f"and the rate weakened {1/ratio:.1f}×"
            else:
                rate_note = "with little change in rate"
            sentences.append(
                f"A Bayesian changepoint analysis detects a structural break around {cp_yr} "
                f"({conf_pct}% confidence) {rate_note} after that year."
            )
        else:
            sentences.append(
                f"A Bayesian changepoint analysis detects a structural break around {cp_yr} "
                f"({conf_pct}% confidence)."
            )

    enso = result.get("enso_correction") or {}
    if enso.get("available"):
        frac    = enso.get("enso_fraction", 0)
        masking = enso.get("masking_rate", 0)
        if frac > 0.20 and abs(masking) > abs(slope) * 0.15:
            frac_pct    = round(frac * 100)
            enso_effect = "amplifying" if (masking * slope) > 0 else "partly masking"
            sentences.append(
                f"El Nino and La Nina cycles explain about {frac_pct}% of year-to-year variability "
                f"here and are {enso_effect} the underlying trend."
            )

    if code == "MOD08_M3":
        if significant:
            sentences.append(
                "Aerosol Optical Depth measures how much sunlight is blocked by particles "
                "(pollution, dust, smoke) in the atmosphere. A rising trend means the air "
                "column above this location is becoming more opaque over time."
            )
        else:
            sentences.append(
                "Aerosol Optical Depth (MODIS MOD08_M3) captures pollution, dust, and smoke "
                "particles in the air column. The trend is not yet statistically confirmed "
                "at this location."
            )

    ita = result.get("ita")
    if ita:
        low_s  = ita["low_slope"]
        high_s = ita["high_slope"]
        low_dir  = "drying" if low_s < 0 else "rising"
        high_dir = "intensifying" if high_s > 0 else "weakening"
        sentences.append(
            f"Innovative Trend Analysis reveals the extremes are pulling apart: "
            f"the driest years are {low_dir} ({low_s:+.4f} {unit_prose}/yr) while "
            f"the wettest years are {high_dir} ({high_s:+.4f} {unit_prose}/yr). "
            f"The standard Mann-Kendall test sees only the net signal and misses this divergence."
        )

    return sentences


def _resolve_location(form):
    """Return (lat, lon, display) from form or raise ValueError."""
    name = (form.get("location") or "").strip().lower().replace(" ", "")
    if name and name in LOCATIONS:
        lat, lon, display = LOCATIONS[name]
        return lat, lon, display
    try:
        lat = float(form.get("lat", ""))
        lon = float(form.get("lon", ""))
        display = f"{abs(lat):.2f}{'N' if lat >= 0 else 'S'}, {abs(lon):.2f}{'E' if lon >= 0 else 'W'}"
        return lat, lon, display
    except (TypeError, ValueError):
        raise ValueError("Provide a known location name or valid lat/lon coordinates.")


def _resolve_variable(form):
    """Return (alias, code, label, unit, epoch) or raise ValueError."""
    alias = (form.get("var") or "temperature").strip().lower()
    if alias in VAR_BY_ALIAS:
        return VAR_BY_ALIAS[alias]
    raise ValueError(f"Unknown variable '{alias}'.")


def _run_full(lat, lon, code, start, end, progress=None, cancel=None):
    """Fetch real data and run full analysis pipeline. No caching."""
    # Clamp to actual data availability — no source has data outside 1981-2025.
    # Prevents absurd ranges from hammering NASA APIs with guaranteed-empty requests.
    start = max(int(start), 1981)
    end   = min(int(end),   2025)
    if start >= end:
        raise ValueError("Start year must be before end year.")

    def emit(msg):
        if progress:
            progress(msg)

    def check_cancel():
        if cancel is not None and cancel.is_set():
            raise _Cancelled()

    emit(f"fetching data for {lat:.2f}, {lon:.2f}...")
    if code in COMPOUND_PARAMS:
        annual          = compute_compound_series(lat, lon, code, start, end)
        monthly_by_year = None
    elif code in MODIS_PARAMS or code in APPEEARS_PARAMS or code in LAADS_PARAMS:
        monthly_by_year = fetch_monthly(lat, lon, code, start, end, progress)
        annual          = monthly_to_annual_min(monthly_by_year, min_months=6)
        if len(annual) < 10:
            annual = monthly_to_annual_min(monthly_by_year, min_months=4)
        monthly_by_year = None
    else:
        monthly_by_year = fetch_monthly(lat, lon, code, start, end, progress)
        annual          = monthly_to_annual(monthly_by_year)

    check_cancel()

    if len(annual) < 10:
        raise ValueError(f"Only {len(annual)} complete years of data (need 10+).")

    years     = [y for y, _ in annual]
    vals      = np.array([v for _, v in annual])
    last_year = years[-1]

    emit(f"{len(vals)} years of data received ({years[0]}-{last_year})")
    emit("fetching ENSO index from NOAA...")
    check_cancel()
    enso_annual, enso_source = fetch_enso(years)
    oni_for_pmk = enso_annual if len(enso_annual) >= len(years) * 0.8 else None

    result = analyse(vals, years, code, last_year, monthly_by_year,
                     progress=progress, cancel=cancel, oni=oni_for_pmk)

    check_cancel()

    result.update({
        "lat": lat, "lon": lon, "param": code,
        "start_year": years[0], "end_year": last_year,
        "n_years": len(vals),
        "annual_years": years,
        "annual_vals":  [round(float(v), 4) for v in vals],
    })
    if enso_annual:
        corrected_vals, attribution = enso_correct(vals, years, enso_annual)
        if corrected_vals is not None:
            check_cancel()
            emit("running ENSO-corrected analysis...")
            corr = analyse(corrected_vals, years, code, last_year, progress=progress, cancel=cancel)
            masking = round(corr["slope"] - result["slope"], 6)
            result["enso_correction"] = {
                "available":     True,
                "source":        enso_source,
                "enso_fraction": attribution["enso_fraction"],
                "masking_rate":  masking,
                "corrected_vals": [round(float(v), 4) for v in corrected_vals],
                "corrected": {
                    "slope":       corr["slope"],
                    "p_value":     corr["p_value"],
                    "z_score":     corr["z_score"],
                    "significant": corr["significant"],
                    "trajectory":  corr.get("trajectory"),
                    "milestones":  corr.get("milestones"),
                },
            }
        else:
            result["enso_correction"] = {"available": False}
    else:
        result["enso_correction"] = {"available": False}

    emit("analysis complete")
    return result


@app.route("/analyze/stream")
def analyze_stream():
    """SSE endpoint: streams progress, stores result by token, sends redirect token."""
    form = request.args
    try:
        lat, lon, display = _resolve_location(form)
        alias, code, label, unit, epoch = _resolve_variable(form)
    except ValueError as e:
        def _err():
            yield f"data: {json.dumps({'type': 'error', 'msg': str(e)})}\n\n"
        return Response(stream_with_context(_err()), mimetype="text/event-stream")

    start = int(form.get("start", epoch))
    end   = int(form.get("end",   2025))

    job_id = uuid.uuid4().hex
    cancel = threading.Event()
    _job_store[job_id] = cancel

    messages   = []
    done_flag  = [False]
    result_ref = [None]
    error_ref  = [None]

    def on_progress(msg):
        messages.append(msg)

    def worker():
        try:
            result_ref[0] = _run_full(lat, lon, code, start, end,
                                       progress=on_progress, cancel=cancel)
        except _Cancelled:
            pass  # silent — no error message shown
        except Exception as exc:
            error_ref[0] = str(exc)
        finally:
            done_flag[0] = True
            _job_store.pop(job_id, None)

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'job_id', 'job_id': job_id})}\n\n"
            sent = 0
            while not done_flag[0] or sent < len(messages):
                while sent < len(messages):
                    yield f"data: {json.dumps({'type': 'progress', 'msg': messages[sent]})}\n\n"
                    sent += 1
                if not done_flag[0]:
                    time.sleep(0.05)

            if error_ref[0]:
                yield f"data: {json.dumps({'type': 'error', 'msg': error_ref[0]})}\n\n"
            elif result_ref[0] is not None:
                token = uuid.uuid4().hex[:16]
                _result_store[token] = (time.time(), dict(
                    result=result_ref[0], display=display,
                    label=label, unit=unit, code=code,
                    start=start, end=end, lat=lat, lon=lon,
                ))
                yield f"data: {json.dumps({'type': 'done', 'token': token})}\n\n"
            # cancelled: stream closes silently, browser resetForm via onerror
        finally:
            # Client disconnect or stop button: ensure worker exits cleanly.
            cancel.set()
            _job_store.pop(job_id, None)

    resp = Response(stream_with_context(generate()), mimetype="text/event-stream")
    resp.headers["Cache-Control"]    = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


@app.route("/analyze/cancel/<job_id>", methods=["POST"])
def analyze_cancel(job_id):
    """Cancel an in-flight analysis. Called by stop button or beforeunload beacon."""
    cancel = _job_store.get(job_id)
    if cancel:
        cancel.set()
    return "", 204


@app.route("/result/<token>")
def result_page(token):
    """Render result from token stored by /analyze/stream."""
    # Purge expired entries on each visit to prevent unbounded memory growth.
    now = time.time()
    expired = [k for k, (ts, _) in _result_store.items() if now - ts > _RESULT_TTL]
    for k in expired:
        del _result_store[k]

    entry = _result_store.get(token)
    if not entry or now - entry[0] > _RESULT_TTL:
        return render_template("index.html",
                               error="Result not found or expired (links last 10 minutes).",
                               locations=sorted(LOCATIONS.items()),
                               variables=VARIABLES)
    _, d = entry
    summary = generate_summary(d["result"], d["display"], d["label"], d["unit"])
    return render_template("result.html",
                           result=d["result"], display=d["display"],
                           label=d["label"], unit=d["unit"], code=d["code"],
                           start=d["start"], end=d["end"],
                           lat=d["lat"], lon=d["lon"],
                           summary=summary)


@app.route("/")
def index():
    return render_template("index.html",
                           locations=sorted(LOCATIONS.items()),
                           variables=VARIABLES)


@app.route("/analyze", methods=["GET", "POST"])
def analyze_page():
    if request.method == "GET" and not request.args.get("lat") and not request.args.get("location"):
        return render_template("index.html",
                               locations=sorted(LOCATIONS.items()),
                               variables=VARIABLES)

    form = request.form if request.method == "POST" else request.args

    try:
        lat, lon, display = _resolve_location(form)
        alias, code, label, unit, epoch = _resolve_variable(form)
    except ValueError as e:
        return render_template("index.html",
                               error=str(e),
                               locations=sorted(LOCATIONS.items()),
                               variables=VARIABLES)

    start = int(form.get("start", epoch))
    end   = int(form.get("end",   2025))

    try:
        result = _run_full(lat, lon, code, start, end)
    except Exception as e:
        return render_template("index.html",
                               error=f"Analysis failed: {e}",
                               locations=sorted(LOCATIONS.items()),
                               variables=VARIABLES)

    summary = generate_summary(result, display, label, unit)
    return render_template("result.html",
                           result=result,
                           display=display,
                           label=label,
                           unit=unit,
                           code=code,
                           start=start,
                           end=end,
                           lat=lat,
                           lon=lon,
                           summary=summary)


@app.route("/api/analyze")
def api_analyze():
    """JSON endpoint for map or programmatic use."""
    try:
        lat, lon, display = _resolve_location(request.args)
        alias, code, label, unit, epoch = _resolve_variable(request.args)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    start = int(request.args.get("start", epoch))
    end   = int(request.args.get("end",   2025))

    try:
        result = _run_full(lat, lon, code, start, end)
        result["location_display"] = display
        result["var_label"] = label
        result["var_unit"]  = unit
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/how-it-works")
def explainer():
    return render_template("explainer.html")


@app.route("/whitepaper.pdf")
def serve_whitepaper():
    pdf = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', 'research', 'whitepaper', 'whitepaper.pdf'
    ))
    return send_file(pdf, mimetype='application/pdf', download_name='tidemark-whitepaper.pdf', as_attachment=False)


@app.route("/slides.pdf")
def serve_slides():
    pdf = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', 'research', 'slides', 'slides.pdf'
    ))
    return send_file(pdf, mimetype='application/pdf', download_name='tidemark-slides.pdf', as_attachment=False)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
