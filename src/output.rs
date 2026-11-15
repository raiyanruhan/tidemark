use crate::cli::Config;

pub fn print_result(config: &Config, json: &serde_json::Value) {
    let start_year  = json["start_year"].as_u64().unwrap_or(1981);
    let end_year    = json["end_year"].as_u64().unwrap_or(2025);
    let n_years     = json["n_years"].as_u64().unwrap_or(0);
    let slope       = json["slope"].as_f64().unwrap_or(0.0);
    let tau         = json["tau"].as_f64().unwrap_or(0.0);
    let z_score     = json["z_score"].as_f64().unwrap_or(0.0);
    let p_value     = json["p_value"].as_f64().unwrap_or(1.0);
    let significant = json["significant"].as_bool().unwrap_or(false);
    let direction   = json["direction"].as_str().unwrap_or("unknown");
    let floor       = json["detection_floor"].as_f64().unwrap_or(0.0);
    let floor_ratio = json["floor_ratio"].as_f64().unwrap_or(0.0);

    println!();
    print_location(config, json);
    println!("{:<12}{} ({}, {})", "variable", config.var_label, config.param, config.unit);
    println!("{:<12}{} - {}  ({} years)", "period", start_year, end_year, n_years);
    let method = json["method"].as_str()
        .unwrap_or("Modified Mann-Kendall (Hamed-Rao, lag=3)");
    println!("{:<12}{}", "test", method);

    println!();
    println!("{:<12}{} {} / year", "trend", fmt_slope(slope), config.unit);
    println!("{:<12}{}", "direction", direction);
    println!("{:<12}{:.2}", "tau", tau);
    println!("{:<12}{:.2}", "z-score", z_score);
    print_pvalue_line(p_value, significant);
    print_eprocess_line(&json["e_process"]);
    print_partial_mk_line(&json["partial_mk"], direction);
    print_floor_line(floor, floor_ratio, &config.unit);
    print_efficiency_line(&json["efficiency"]);
    print_changepoint_line(&json["changepoint"]);
    print_records_line(&json["records"]);

    if let Some(s) = json.get("seasonal").filter(|v| v.is_object()) {
        if s.as_object().map(|m| !m.is_empty()).unwrap_or(false) {
            println!();
            print_seasonal_block(s, &config.unit);
        }
    }

    println!();
    if significant {
        print_milestones(json);
    } else {
        print_trajectory(json);
    }

    print_bocpd_block(&json["bocpd"], start_year, end_year, &config.unit);
    print_enso_block(&json["enso_correction"], &config.unit);
}

fn print_location(config: &Config, json: &serde_json::Value) {
    let lat = json["lat"].as_f64().unwrap_or(config.lat);
    let lon = json["lon"].as_f64().unwrap_or(config.lon);
    let coord = format!(
        "({:.2}\u{00b0}{}, {:.2}\u{00b0}{})",
        lat.abs(), if lat >= 0.0 { "N" } else { "S" },
        lon.abs(), if lon >= 0.0 { "E" } else { "W" },
    );
    if config.location_display.is_empty() {
        println!("{:<12}{}", "location", coord);
    } else {
        println!("{:<12}{}  {}", "location", config.location_display, coord);
    }
}

fn print_pvalue_line(p: f64, significant: bool) {
    let p_str = fmt_pvalue(p);
    if significant {
        println!("{:<12}{}   \u{2713} significant (p < 0.05)", "p-value", p_str);
    } else {
        println!("{:<12}{}   not yet significant (p > 0.05)", "p-value", p_str);
    }
}

fn print_efficiency_line(eff: &serde_json::Value) {
    let are_opt = match eff["are_mk_optimal"].as_f64() {
        Some(v) if v < 0.95 => v,
        _ => return, // skip when near-Gaussian (difference negligible)
    };
    let are_ols = eff["are_mk_ols"].as_f64().unwrap_or(1.0);
    // how many times more data MK needs vs optimal rank test
    let penalty = (1.0 / are_opt).powf(1.0 / 3.0);
    if are_ols > 1.0 {
        println!("{:<12}MK {:.2}x OLS   ARE {:.2} vs optimal   (gap: {:.2}x more data needed)",
            "method eff", are_ols, are_opt, penalty);
    } else {
        println!("{:<12}ARE {:.2} vs optimal   ({:.2}x more data needed than optimal rank test)",
            "method eff", are_opt, penalty);
    }
}

pub fn print_comparison(
    config_a: &Config, json_a: &serde_json::Value,
    config_b: &Config, json_b: &serde_json::Value,
) {
    let name_a = if config_a.location_display.is_empty() {
        format!("{:.2}N {:.2}E", config_a.lat, config_a.lon)
    } else {
        config_a.location_display.clone()
    };
    let name_b = if config_b.location_display.is_empty() {
        format!("{:.2}N {:.2}E", config_b.lat, config_b.lon)
    } else {
        config_b.location_display.clone()
    };

    let col = 28usize;
    println!();
    println!("- comparison -");
    println!();
    println!("{:<16}{:<col$}{}", "", name_a, name_b);

    let sa = json_a["slope"].as_f64().unwrap_or(0.0);
    let sb = json_b["slope"].as_f64().unwrap_or(0.0);
    println!("{:<16}{:<col$}{}",
        "trend",
        format!("{} {} / year", fmt_slope(sa), config_a.unit),
        format!("{} {} / year", fmt_slope(sb), config_b.unit),
    );

    let pa   = json_a["p_value"].as_f64().unwrap_or(1.0);
    let pb   = json_b["p_value"].as_f64().unwrap_or(1.0);
    let siga = json_a["significant"].as_bool().unwrap_or(false);
    let sigb = json_b["significant"].as_bool().unwrap_or(false);
    println!("{:<16}{:<col$}{}",
        "p-value",
        format!("{}  {}", fmt_pvalue(pa), if siga { "\u{2713}" } else { "--" }),
        format!("{}  {}", fmt_pvalue(pb), if sigb { "\u{2713}" } else { "--" }),
    );

    let cp_str = |cp: &serde_json::Value| -> String {
        if cp["detected"].as_bool().unwrap_or(false) {
            format!("{} (p={:.3})", cp["year"].as_i64().unwrap_or(0), cp["p"].as_f64().unwrap_or(1.0))
        } else {
            "none".to_string()
        }
    };
    println!("{:<16}{:<col$}{}", "changepoint", cp_str(&json_a["changepoint"]), cp_str(&json_b["changepoint"]));

    let ra = json_a["records"]["ratio"].as_f64().unwrap_or(1.0);
    let rb = json_b["records"]["ratio"].as_f64().unwrap_or(1.0);
    let rec_note = |r: f64| -> &'static str { if r >= 1.5 { " (dice loaded)" } else { "" } };
    println!("{:<16}{:<col$}{}",
        "records",
        format!("{:.2}x{}", ra, rec_note(ra)),
        format!("{:.2}x{}", rb, rec_note(rb)),
    );

    let sig_line = |json: &serde_json::Value, sig: bool| -> String {
        if sig {
            "significant".to_string()
        } else if let Some(mc) = json["trajectory"]["mc_median"].as_i64() {
            format!("{} (MC, 85% PI {}-{})",
                mc,
                json["trajectory"]["mc_pi_low"].as_i64().unwrap_or(mc),
                json["trajectory"]["mc_pi_high"].as_i64().unwrap_or(mc),
            )
        } else {
            "not significant".to_string()
        }
    };
    println!("{:<16}{:<col$}{}", "significance", sig_line(json_a, siga), sig_line(json_b, sigb));
}

fn print_seasonal_block(seasonal: &serde_json::Value, unit: &str) {
    println!("seasonal trends:");
    for season in &["DJF", "MAM", "JJA", "SON"] {
        let s = match seasonal.get(season) {
            Some(v) => v,
            None    => continue,
        };
        let slope = s["slope"].as_f64().unwrap_or(0.0);
        let p     = s["p"].as_f64().unwrap_or(1.0);
        let sig   = s["significant"].as_bool().unwrap_or(false);
        let sign  = if slope >= 0.0 { "+" } else { "" };
        let sig_str = if sig { "significant" } else { "--" };
        println!("  {:<5}{}{:.5} {} / year   p={:.3}   {}",
            season, sign, slope, unit, p, sig_str);
    }
}

fn print_changepoint_line(cp: &serde_json::Value) {
    let p = cp["p"].as_f64().unwrap_or(1.0);
    if cp["detected"].as_bool().unwrap_or(false) {
        let year = cp["year"].as_i64().unwrap_or(0);
        println!("{:<12}{}   (Pettitt p={:.3})", "changepoint", year, p);
    } else {
        println!("{:<12}none   (Pettitt p={:.3})", "changepoint", p);
    }
}

fn print_records_line(rec: &serde_json::Value) {
    let observed = rec["observed"].as_i64().unwrap_or(0);
    let expected = rec["expected"].as_f64().unwrap_or(0.0);
    let ratio    = rec["ratio"].as_f64().unwrap_or(1.0);
    let note = if ratio >= 1.5 {
        "   (trend loading the dice)"
    } else if ratio <= 0.7 {
        "   (fewer records than expected)"
    } else {
        ""
    };
    println!("{:<12}{} observed  {:.1} expected  {:.2}x{}",
        "records", observed, expected, ratio, note);
}

fn print_eprocess_line(ep: &serde_json::Value) {
    let log_e = match ep["log_E"].as_f64() {
        Some(v) => v,
        None    => return,
    };
    let significant = ep["significant"].as_bool().unwrap_or(false);
    let phi_note    = ep["phi_note"].as_bool().unwrap_or(false);

    // compress large E_n to log form; small values show E_n = X.X
    let e_n_str = match ep["E_n"].as_f64() {
        Some(v) if v > 1000.0 => format!("E_n >> 20 (log E = {:.1})", log_e),
        Some(v)               => format!("E_n = {:.1}", v),
        None                  => return,
    };

    if significant {
        println!("{:<12}{}   \u{2713} anytime-valid   (\u{03b1}=0.05)",
            "e-process", e_n_str);
    } else {
        println!("{:<12}{}   threshold: 20   (\u{03b1}=0.05)",
            "e-process", e_n_str);
    }
    if phi_note {
        println!("{:<12}note: autocorrelation phi>0.4, e-process is approximate, interpret with p-value",
            "");
    }
}

fn print_partial_mk_line(pmk: &serde_json::Value, direction: &str) {
    let z_raw = match pmk["z_raw"].as_f64() { Some(v) => v, None => return };
    let p_raw = match pmk["p_raw"].as_f64() { Some(v) => v, None => return };
    let z_adj = match pmk["z"].as_f64()     { Some(v) => v, None => return };
    let p_adj = match pmk["p"].as_f64()     { Some(v) => v, None => return };
    let sig_raw = pmk["significant_raw"].as_bool().unwrap_or(false);
    let sig_adj = pmk["significant"].as_bool().unwrap_or(false);
    let fraction = pmk["enso_fraction"].as_f64().unwrap_or(0.0);

    println!();
    println!("{:<24}z = {:.2}   p = {}   {}",
        "trend test (raw)", z_raw, fmt_pvalue(p_raw),
        if sig_raw { "\u{2713} significant" } else { "not significant" });
    println!("{:<24}z = {:.2}   p = {}   {}",
        "trend test (ENSO-adj)", z_adj, fmt_pvalue(p_adj),
        if sig_adj { "\u{2713} significant" } else { "not significant" });
    println!();
    println!("ENSO explains {:.0}% of concordance variance", fraction * 100.0);

    let interp = match (sig_raw, sig_adj, direction) {
        (false, true, "upward")   => "anthropogenic increasing trend exists, masked by ENSO in raw test",
        (false, true, "downward") => "anthropogenic declining trend exists, masked by ENSO in raw test",
        (false, true, _)          => "anthropogenic trend exists, masked by ENSO in raw test",
        (true, false, _)          => "apparent trend may be ENSO-driven, not anthropogenic",
        (true, true, _)           => "trend robust to ENSO correction",
        _                         => "no significant trend, ENSO not explanatory",
    };
    println!("interpretation: {}", interp);
}

fn print_floor_line(floor: f64, ratio: f64, unit: &str) {
    let floor_str = fmt_sigfig(floor, 3);
    let annotation = if ratio >= 1.0 {
        format!("slope is {:.1}x above floor", ratio)
    } else {
        format!("slope is {:.1}x floor, weak signal", ratio)
    };
    println!("{:<24}\u{00b1}{} {} / year   ({})", "detection floor", floor_str, unit, annotation);
}

fn print_milestones(json: &serde_json::Value) {
    let milestones = match json["milestones"].as_array() {
        Some(m) if !m.is_empty() => m,
        _ => return,
    };
    println!("projected milestones at current rate:");
    for m in milestones {
        let delta = m["delta"].as_str().unwrap_or("");
        let unit  = m["unit"].as_str().unwrap_or("");
        let year  = m["year"].as_u64().unwrap_or(0);
        let label = m["label"].as_str().unwrap_or("");
        let delta_unit = if unit.is_empty() {
            delta.to_string()
        } else {
            format!("{} {}", delta, unit)
        };
        if label.is_empty() {
            println!("  {:<11}~{}", delta_unit, year);
        } else {
            println!("  {:<11}~{}   \u{2190} {}", delta_unit, year, label);
        }
    }
    println!("  note   projection assumes observed trend continues at measured rate -- not a forecast");
}

fn print_trajectory(json: &serde_json::Value) {
    let traj = &json["trajectory"];

    let analytical   = traj["analytical_year"].as_i64();
    let weatherhead  = traj["weatherhead_year"].as_i64();
    let mc_median    = traj["mc_median"].as_i64();
    let mc_pi_low    = traj["mc_pi_low"].as_i64();
    let mc_pi_high   = traj["mc_pi_high"].as_i64();
    let crb_year     = traj["crb_year"].as_i64();
    let never_crossed = traj["never_crossed"].as_u64().unwrap_or(0);
    let never_frac   = traj["never_crossed_frac"].as_f64().unwrap_or(0.0);
    let methods_agree = traj["methods_agree"].as_bool().unwrap_or(true);
    let divergence   = traj["divergence_years"].as_i64().unwrap_or(0);
    let skewness     = traj["skewness"].as_f64().unwrap_or(0.0);
    let normality_p  = traj["normality_p"].as_f64().unwrap_or(1.0);
    let phi          = traj["weatherhead_phi"].as_f64().unwrap_or(0.0);

    println!("significance trajectory:");

    if methods_agree {
        print_traj_row("analytical MK", analytical, "MK n^1.5 growth formula");
        print_traj_row("Weatherhead 1998", weatherhead,
            &format!("OLS formula with MK parameters, ~90% detection probability, phi={:.2}", phi));
        print_traj_row("Monte Carlo", mc_median, "n=1000, empirical bootstrap");
        print_traj_row("CRB lower bound", crb_year, "Fisher information floor, any test");
        println!("  methods agree, consistent estimate");
    } else {
        print_traj_row("analytical MK", analytical, "assumes Gaussian IID, invalid here");
        print_traj_row("Weatherhead 1998", weatherhead,
            "OLS formula with MK parameters, assumes Gaussian, also invalid");
        print_traj_row("Monte Carlo", mc_median, "n=1000, empirical bootstrap, correct");
        print_traj_row("CRB lower bound", crb_year, "Fisher information floor, any test");
        println!("  methods diverge: {} years", divergence);
        let norm_display = fmt_normality_p(normality_p);
        println!("  reason: residual skewness={:.2}, normality {}, non-Gaussian noise",
            skewness, norm_display);
        println!("  trust: Monte Carlo");
    }

    // MC before CRB floor, repeated-testing inflation
    if let (Some(mc), Some(crb)) = (mc_median, crb_year) {
        if mc < crb {
            println!("  note: MC ({}) precedes CRB floor ({}), p-value trajectory inflated by repeated testing",
                mc, crb);
        }
    }

    match (mc_pi_low, mc_pi_high) {
        (Some(lo), Some(hi)) => {
            println!("  {:<18}{} - {}", "85% PI", lo, hi);
        }
        _ => {
            println!("  85% PI            (insufficient crossings)");
        }
    }

    if never_frac > 0.5 {
        let crossed = 1000u64.saturating_sub(never_crossed);
        println!("  note   {}/1000 simulations become significant within 80 years", crossed);
    }

    if phi > 0.2 {
        println!("  note   residual autocorrelation phi={:.2}, MC crossing year may be 2-5 years optimistic", phi);
    }

    println!("  note   projection assumes observed trend continues at measured rate -- not a forecast");
}

fn print_bocpd_block(bocpd: &serde_json::Value, start_year: u64, end_year: u64, unit: &str) {
    if bocpd["changepoint_detected"].as_bool() != Some(true) {
        return;
    }
    let cp_year   = match bocpd["changepoint_year"].as_i64() { Some(y) => y, None => return };
    let conf      = bocpd["changepoint_confidence"].as_f64().unwrap_or(0.0);
    let slope_pre = match bocpd["slope_before"].as_f64() { Some(v) => v, None => return };
    let slope_pst = match bocpd["slope_after"].as_f64()  { Some(v) => v, None => return };

    let log_bf = bocpd["changepoint_log_bf"].as_f64().unwrap_or(0.0);
    println!();
    println!("changepoint analysis (Bayesian):");
    println!("  structural break detected: {}   (confidence {:.0}%,  log BF = {:.1})",
        cp_year, conf * 100.0, log_bf);
    println!("  {:<20}{} {} / year   ({}-{})",
        format!("slope before {}:", cp_year),
        fmt_slope(slope_pre), unit,
        start_year, cp_year - 1,
    );
    println!("  {:<20}{} {} / year   ({}-{})",
        format!("slope after {}:", cp_year),
        fmt_slope(slope_pst), unit,
        cp_year, end_year,
    );

    let abs_pre = slope_pre.abs();
    let abs_pst = slope_pst.abs();
    let same_sign = slope_pre * slope_pst >= 0.0;

    if !same_sign {
        println!("  trend reversed sign after {}", cp_year);
    } else if abs_pre > 1e-12 {
        let ratio = abs_pst / abs_pre;
        if ratio >= 1.5 {
            println!("  trend steepened {:.1}x after {}", ratio, cp_year);
        } else if ratio <= 0.67 {
            println!("  trend weakened {:.1}x after {}", 1.0 / ratio, cp_year);
        }
    }
}

fn print_enso_block(enso: &serde_json::Value, unit: &str) {
    if enso["available"].as_bool() != Some(true) {
        return;
    }
    let fraction   = enso["enso_fraction"].as_f64().unwrap_or(0.0);
    let masking    = enso["masking_rate"].as_f64().unwrap_or(0.0);
    let corr       = &enso["corrected"];
    let corr_slope = corr["slope"].as_f64().unwrap_or(0.0);
    let corr_p     = corr["p_value"].as_f64().unwrap_or(1.0);
    let corr_sig   = corr["significant"].as_bool().unwrap_or(false);

    println!();
    println!("ENSO correction (NOAA MEI v2):");
    println!("  {:<20}{:.1}% of variance explained by El Nino/La Nina cycles",
        "ENSO fraction", fraction * 100.0);
    if masking.abs() > 1e-9 {
        let sign = if masking >= 0.0 { "+" } else { "" };
        println!("  {:<20}{}{:.5} {} / year  (ENSO was masking this from raw signal)",
            "masking rate", sign, masking, unit);
    }
    println!("  {:<20}{} {} / year   p={}   {}",
        "corrected trend",
        fmt_slope(corr_slope),
        unit,
        fmt_pvalue(corr_p),
        if corr_sig { "significant" } else { "not yet significant" },
    );
}

fn print_traj_row(label: &str, year: Option<i64>, paren: &str) {
    match year {
        Some(y) => println!("  {:<18}{}   ({})", label, y, paren),
        None    => println!("  {:<18}N/A   ({})", label, paren),
    }
}

fn fmt_sigfig(x: f64, sig: usize) -> String {
    if x == 0.0 { return "0".to_string(); }
    let abs = x.abs();
    let exp = abs.log10().floor() as i32;
    let dp = ((sig as i32 - 1 - exp).max(0)) as usize;
    let s = format!("{:.prec$}", x, prec = dp);
    strip_trailing_zeros(s)
}

fn fmt_slope(slope: f64) -> String {
    let abs = slope.abs();
    // enough dp for 3 sig figs
    let s = if abs == 0.0 {
        "0".to_string()
    } else {
        let exp = abs.log10().floor() as i32;
        let dp = ((3i32 - 1 - exp).max(0)) as usize;
        let formatted = format!("{:.prec$}", abs, prec = dp);
        strip_trailing_zeros(formatted)
    };
    if slope >= 0.0 { format!("+{}", s) } else { format!("-{}", s) }
}

fn fmt_pvalue(p: f64) -> String {
    fmt_sigfig(p, 3)
}

fn fmt_normality_p(p: f64) -> String {
    if p < 0.001 {
        "p<0.001".to_string()
    } else if p < 0.01 {
        "p<0.01".to_string()
    } else {
        format!("p={:.3}", p)
    }
}

fn strip_trailing_zeros(s: String) -> String {
    if s.contains('.') {
        s.trim_end_matches('0').trim_end_matches('.').to_string()
    } else {
        s
    }
}
