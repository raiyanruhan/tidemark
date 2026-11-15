use clap::{Parser, Subcommand};
#[cfg(not(feature = "bundled"))]
use std::io::ErrorKind;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::time::Duration;

pub type Result<T> = std::result::Result<T, String>;

pub struct Config {
    pub lat: f64,
    pub lon: f64,
    pub location_display: String,
    pub param: String,
    pub unit: String,
    pub var_label: String,
}

#[derive(Parser)]
#[command(name = "tidemark", about = "Earth system trend analysis using NASA POWER, GPM, AppEEARS, and MODIS data")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Analyze a climate variable at a location
    Analyze(AnalyzeArgs),
    /// Compare a climate variable between two locations
    Compare(CompareArgs),
}

#[derive(clap::Args)]
struct AnalyzeArgs {
    /// Named location (e.g. "dhaka", "cairo")
    #[arg(long)]
    location: Option<String>,

    /// Latitude (requires --lon)
    #[arg(long)]
    lat: Option<f64>,

    /// Longitude (requires --lat)
    #[arg(long)]
    lon: Option<f64>,

    /// Climate variable (e.g. temperature, rainfall, humidity)
    #[arg(long)]
    var: String,

    /// Years of historical data to use, counting back from present (default: full record from 1981)
    #[arg(long)]
    years: Option<u32>,
}

#[derive(clap::Args)]
struct CompareArgs {
    /// Named locations to compare (use twice: --location dhaka --location cairo)
    #[arg(long, action = clap::ArgAction::Append)]
    location: Vec<String>,

    /// Climate variable to compare
    #[arg(long)]
    var: String,
}

pub fn run() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Analyze(args) => run_analyze(args),
        Commands::Compare(args) => run_compare(args),
    }
}

fn run_analyze(args: AnalyzeArgs) -> Result<()> {
    let (lat, lon, location_display) = resolve_location_arg(&args)?;
    let (param, unit, var_label) = resolve_variable(&args.var)?;

    let config = Config { lat, lon, location_display, param: param.to_string(), unit: unit.to_string(), var_label: var_label.to_string() };

    let analyzer = get_analyzer_path()?;
    let end      = current_year();
    let start    = args.years.map(|y| end.saturating_sub(y)).unwrap_or(1981);
    let json_str = run_analyzer(&analyzer, lat, lon, &config.param, start, end)?;

    let json: serde_json::Value = serde_json::from_str(&json_str)
        .map_err(|e| format!("could not parse Python output: {e}\nOutput was: {json_str}"))?;

    if let Some(err) = json.get("error").and_then(|v| v.as_str()) {
        return Err(err.to_string());
    }

    crate::output::print_result(&config, &json);
    Ok(())
}

fn resolve_location_name(name: &str) -> Result<(f64, f64, String)> {
    match crate::locations::resolve_location(name) {
        Some(r) => Ok(r),
        None    => Err(format!("unknown location '{}'. use --lat/--lon for coordinates.", name)),
    }
}

fn resolve_location_arg(args: &AnalyzeArgs) -> Result<(f64, f64, String)> {
    if let Some(name) = &args.location {
        if args.lat.is_some() || args.lon.is_some() {
            return Err("use either --location or --lat/--lon, not both".to_string());
        }
        resolve_location_name(name)
    } else if let (Some(lat), Some(lon)) = (args.lat, args.lon) {
        let display = format!(
            "{:.2}\u{00b0}{}, {:.2}\u{00b0}{}",
            lat.abs(), if lat >= 0.0 { "N" } else { "S" },
            lon.abs(), if lon >= 0.0 { "E" } else { "W" },
        );
        Ok((lat, lon, display))
    } else {
        Err("provide either --location NAME or both --lat LAT --lon LON".to_string())
    }
}

fn resolve_variable(input: &str) -> Result<(&'static str, &'static str, &'static str)> {
    let normalized = input.to_lowercase().replace('_', "-");
    match normalized.as_str() {
        "rainfall" | "rain" | "precip" | "precipitation" => Ok(("PRECTOTCORR", "mm/day", "precipitation")),
        "temperature" | "temp"                           => Ok(("T2M",         "\u{00b0}C",   "temperature")),
        "max-temperature" | "max-temp" | "tmax"          => Ok(("T2M_MAX",     "\u{00b0}C",   "max temperature")),
        "min-temperature" | "min-temp" | "tmin"          => Ok(("T2M_MIN",     "\u{00b0}C",   "min temperature")),
        "humidity" | "rh"                                => Ok(("RH2M",        "%",     "humidity")),
        "evaporation" | "evap"                           => Ok(("EVLAND",      "mm/day", "evaporation")),
        "wind" | "wind-speed"                            => Ok(("WS10M",       "m/s",   "wind speed")),
        "vpd" | "vapor-pressure-deficit"                 => Ok(("VPD",         "kPa",          "vapor pressure deficit")),
        "dtr" | "diurnal-temperature-range"              => Ok(("DTR",         "\u{00b0}C",    "diurnal temperature range")),
        // "soil" routes to root zone, the layer that matters for crops
        "soil" | "soil-moisture" | "root-moisture" | "gwetroot" => Ok(("GWETROOT",    "fraction",    "root zone soil moisture")),
        "surface-soil" | "top-soil" | "gwettop"                 => Ok(("GWETTOP",     "fraction",    "surface soil moisture")),
        "profile-soil" | "gwetprof"                             => Ok(("GWETPROF",    "fraction",    "profile soil moisture")),
        "frost" | "frost-days"                                  => Ok(("FROST_DAYS",  "days",        "frost days")),
        "soil-temp" | "soil-temperature" | "tsoil" | "tsoil1"  => Ok(("TSOIL1",      "\u{00b0}C",   "soil temperature")),
        "skin-temp" | "skin-temperature" | "surface-temp" | "ts" => Ok(("TS",         "\u{00b0}C",   "earth skin temperature")),
        "ndvi" | "vegetation" | "vegetation-index"              => Ok(("NDVI",       "ratio",       "vegetation index")),
        "lst"  | "land-surface-temperature" | "land-surface-temp" => Ok(("LST",      "\u{00b0}C",   "land surface temperature")),
        "et"   | "evapotranspiration-modis" | "et-modis"          => Ok(("ET_MOD16", "mm/day",      "evapotranspiration (MODIS)")),
        "aod"  | "aerosol" | "aerosol-optical-depth" | "mod08"   => Ok(("MOD08_M3", "unitless",    "aerosol optical depth (MODIS)")),
        _ => Err(format!(
            "unknown variable '{}'. valid: rainfall, temperature, max-temperature, min-temperature, humidity, evaporation, wind, vpd, dtr, soil, surface-soil, profile-soil, frost, soil-temp, skin-temp, ndvi, lst, et, aod",
            input
        )),
    }
}

#[cfg(not(feature = "bundled"))]
fn find_analyze_script() -> Result<PathBuf> {
    // adjacent to binary (installed), then two levels up (cargo dev)
    if let Ok(exe) = std::env::current_exe() {
        let sibling = exe.parent().map(|d| d.join("python").join("analyze.py"));
        let cargo_root = exe
            .parent()
            .and_then(|d| d.parent())
            .and_then(|d| d.parent())
            .map(|d| d.join("python").join("analyze.py"));
        for candidate in [sibling, cargo_root].into_iter().flatten() {
            if candidate.exists() {
                return Ok(candidate);
            }
        }
    }
    // Fall back to CWD
    let cwd = PathBuf::from("python").join("analyze.py");
    if cwd.exists() {
        return Ok(cwd);
    }
    Err("cannot find python/analyze.py. run from the project root or place the script next to the binary.".to_string())
}

#[cfg(not(feature = "bundled"))]
fn spawn_python(script: &Path, lat: f64, lon: f64, param: &str, start: u32, end: u32) -> Result<String> {
    let script_s = script.to_str().ok_or("non-UTF-8 script path")?;
    let args: Vec<String> = vec![
        script_s.to_string(),
        "--lat".to_string(),   format!("{}", lat),
        "--lon".to_string(),   format!("{}", lon),
        "--var".to_string(),   param.to_string(),
        "--start".to_string(), format!("{}", start),
        "--end".to_string(),   format!("{}", end),
    ];

    // python3 first (Linux/Mac default), then python (Windows), then py (Windows launcher)
    for exe in &["python3", "python", "py"] {
        let child = match Command::new(exe)
            .arg("-W").arg("ignore")
            .args(&args)
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
        {
            Ok(c) => c,
            Err(e) if e.kind() == ErrorKind::NotFound => continue,
            Err(e) => return Err(format!("failed to spawn Python: {e}")),
        };

        let (tx, rx) = mpsc::channel();
        std::thread::spawn(move || { tx.send(child.wait_with_output()).ok(); });

        let out = match rx.recv_timeout(Duration::from_secs(600)) {
            Ok(Ok(o))  => o,
            Ok(Err(e)) => return Err(format!("failed to wait on Python: {e}")),
            Err(_)     => return Err("timed out after 600s. First fetch for ndvi/lst/et is slow (AppEEARS async task); aod (MOD08_M3) first fetch ~2min; see ~/.tidemark/cache/. Other variables complete in <60s.".to_string()),
        };

        // MS Store Python alias exits 9009, not ENOENT
        if out.status.code() == Some(9009) { continue; }

        if !out.status.success() {
            let stderr = String::from_utf8_lossy(&out.stderr);
            return Err(format!("Python error:\n{}", stderr.trim()));
        }
        return String::from_utf8(out.stdout)
            .map_err(|e| format!("Python output not valid UTF-8: {e}"));
    }
    Err("Python not found. Install Python 3 and: pip install pymannkendall requests numpy scipy".to_string())
}

// --- bundle embedding (release builds only) -----------------------------------

#[cfg(all(feature = "bundled", target_os = "windows"))]
static ANALYZE_BUNDLE: &[u8] = include_bytes!("../dist/analyze.exe");
#[cfg(all(feature = "bundled", not(target_os = "windows")))]
static ANALYZE_BUNDLE: &[u8] = include_bytes!("../dist/analyze");

#[cfg(feature = "bundled")]
fn extract_bundle() -> Result<PathBuf> {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_else(|_| ".".to_string());
    let dir = PathBuf::from(&home).join(".tidemark");
    std::fs::create_dir_all(&dir)
        .map_err(|e| format!("cannot create ~/.tidemark: {e}"))?;

    #[cfg(target_os = "windows")]
    let path = dir.join("analyze.exe");
    #[cfg(not(target_os = "windows"))]
    let path = dir.join("analyze");

    let needs_extract = path.metadata()
        .map(|m| m.len() as usize != ANALYZE_BUNDLE.len())
        .unwrap_or(true);

    if needs_extract {
        std::fs::write(&path, ANALYZE_BUNDLE)
            .map_err(|e| format!("cannot extract analyzer to ~/.tidemark: {e}"))?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755))
                .map_err(|e| format!("cannot chmod analyzer: {e}"))?;
        }
    }
    Ok(path)
}

#[cfg(feature = "bundled")]
fn run_bundle(analyzer: &Path, lat: f64, lon: f64, param: &str, start: u32, end: u32) -> Result<String> {
    let child = Command::new(analyzer)
        .args([
            "--lat",   &format!("{lat}"),
            "--lon",   &format!("{lon}"),
            "--var",   param,
            "--start", &format!("{start}"),
            "--end",   &format!("{end}"),
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("failed to launch analyzer: {e}"))?;

    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || { tx.send(child.wait_with_output()).ok(); });

    let out = match rx.recv_timeout(Duration::from_secs(600)) {
        Ok(Ok(o))  => o,
        Ok(Err(e)) => return Err(format!("failed to wait on analyzer: {e}")),
        Err(_)     => return Err("timed out after 600s. First fetch for ndvi/lst/et is slow (AppEEARS async task); aod (MOD08_M3) first fetch ~2min; see ~/.tidemark/cache/. Other variables complete in <60s.".to_string()),
    };

    if !out.status.success() {
        return Err(format!("analyzer error:\n{}", String::from_utf8_lossy(&out.stderr).trim()));
    }
    String::from_utf8(out.stdout)
        .map_err(|e| format!("analyzer output not valid UTF-8: {e}"))
}

// --- dispatchers (always compiled) --------------------------------------------

fn get_analyzer_path() -> Result<PathBuf> {
    #[cfg(feature = "bundled")]
    { return extract_bundle(); }
    #[cfg(not(feature = "bundled"))]
    { return find_analyze_script(); }
}

fn run_analyzer(path: &Path, lat: f64, lon: f64, param: &str, start: u32, end: u32) -> Result<String> {
    #[cfg(feature = "bundled")]
    { return run_bundle(path, lat, lon, param, start, end); }
    #[cfg(not(feature = "bundled"))]
    { return spawn_python(path, lat, lon, param, start, end); }
}

// ------------------------------------------------------------------------------

fn run_compare(args: CompareArgs) -> Result<()> {
    if args.location.len() != 2 {
        return Err("compare requires exactly two --location arguments".to_string());
    }

    let (lat_a, lon_a, disp_a) = resolve_location_name(&args.location[0])?;
    let (lat_b, lon_b, disp_b) = resolve_location_name(&args.location[1])?;
    let (param, unit, var_label) = resolve_variable(&args.var)?;

    let config_a = Config { lat: lat_a, lon: lon_a, location_display: disp_a,
        param: param.to_string(), unit: unit.to_string(), var_label: var_label.to_string() };
    let config_b = Config { lat: lat_b, lon: lon_b, location_display: disp_b,
        param: param.to_string(), unit: unit.to_string(), var_label: var_label.to_string() };

    let analyzer = get_analyzer_path()?;
    let end      = current_year();

    // Run both analyses in parallel; no shared state.
    let analyzer_a = analyzer.clone();
    let analyzer_b = analyzer;
    let param_a    = param.to_string();
    let param_b    = param.to_string();

    let handle_a = std::thread::spawn(move || {
        run_analyzer(&analyzer_a, lat_a, lon_a, &param_a, 1981, end)
    });
    let handle_b = std::thread::spawn(move || {
        run_analyzer(&analyzer_b, lat_b, lon_b, &param_b, 1981, end)
    });

    let json_str_a = handle_a.join().map_err(|_| "analysis thread A panicked".to_string())??;
    let json_str_b = handle_b.join().map_err(|_| "analysis thread B panicked".to_string())??;

    let json_a: serde_json::Value = serde_json::from_str(&json_str_a)
        .map_err(|e| format!("could not parse output for {}: {e}", args.location[0]))?;
    let json_b: serde_json::Value = serde_json::from_str(&json_str_b)
        .map_err(|e| format!("could not parse output for {}: {e}", args.location[1]))?;

    if let Some(err) = json_a.get("error").and_then(|v| v.as_str()) {
        return Err(format!("{}: {}", args.location[0], err));
    }
    if let Some(err) = json_b.get("error").and_then(|v| v.as_str()) {
        return Err(format!("{}: {}", args.location[1], err));
    }

    println!("\n=== {} ===", config_a.location_display);
    crate::output::print_result(&config_a, &json_a);

    println!("\n=== {} ===", config_b.location_display);
    crate::output::print_result(&config_b, &json_b);

    crate::output::print_comparison(&config_a, &json_a, &config_b, &json_b);
    Ok(())
}

fn current_year() -> u32 {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    (1970 + secs / 31_557_600) as u32
}
