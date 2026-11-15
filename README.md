<h1 align="center">
  <a href="https://github.com/raiyanruhan/tidemark"><img src="assets/logo.png" width="300px" alt="tidemark"></a>
</h1>

<h3 align="center">pulls NASA Earth science data for any location and runs statistical trend analysis.</h3>

---

<p align="center">
  <a href="https://www.spaceappschallenge.org/2026/challenges/">
    <img src="https://img.shields.io/badge/NASA-Space%20Apps%202026-0B3D91?style=flat-square" alt="NASA Space Apps 2026">
  </a>
  <a href="https://power.larc.nasa.gov">
    <img src="https://img.shields.io/badge/Data-NASA%20POWER-blue?style=flat-square" alt="NASA POWER">
  </a>
  <a href="https://disc.gsfc.nasa.gov">
    <img src="https://img.shields.io/badge/Data-GPM%20IMERG-blue?style=flat-square" alt="GPM IMERG">
  </a>
</p>

<p align="center">
  <a href="whitepaper.pdf">
    <img src="https://img.shields.io/badge/Read-Whitepaper-1a56db?style=flat-square" alt="Whitepaper">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square" alt="Python 3.10+">
  </a>
  <a href="https://www.rust-lang.org/">
    <img src="https://img.shields.io/badge/Rust-1.70%2B-CE422B?style=flat-square" alt="Rust 1.70+">
  </a>
</p>

---

## Table of Contents

* [Introduction](#introduction)
* [Build](#build)
* [Usage](#usage)
* [Variables](#variables)
* [Data Sources](#data-sources)
* [Team](#team)

## Introduction

> [!NOTE]
> Tidemark was built for NASA Space Apps Challenge 2026 - "Be An Earth System Trend Detective".
> It is not an open source library. The repository contains the full implementation and whitepaper.

Every existing climate trend tool reports the same thing: significant or not. That binary omits three things - how much more data is needed before a not-yet-significant trend becomes detectable, whether the current record is long enough to resolve the signal at all, and when a significant trend will cross real-world thresholds.

Tidemark answers all three. It runs the Modified Mann-Kendall test with Hamed-Rao autocorrelation correction (or MKC3 for skewed series), computes the detection floor unconditionally, runs four independent crossing-year estimates with divergence detection, and separates anthropogenic trend signal from ENSO variability using a rank-based partial Mann-Kendall test.

```
$ tidemark analyze --location cairo --var rainfall

location    Cairo, Egypt  (30.06N, 31.25E)
variable    precipitation (PRECTOTCORR, mm/day)
period      1981 - 2025  (45 years)

trend       +0.0009 mm/day / year
p-value     0.74   not yet significant
detection floor     +-0.0037 mm/day / year   (slope is 0.25x floor)

significance trajectory:
  analytical MK     2128   (Gaussian IID - invalid here)
  Weatherhead 1998  2123   (Gaussian - invalid here)
  Monte Carlo       2051   (n=1000, empirical bootstrap)
  CRB lower bound   2047   (Fisher information floor, any test)
  methods diverge: 77 years
  reason: residual skewness=1.95, normality p<0.001
  trust: Monte Carlo
  85% PI            2036 - 2068
```

The 77-year divergence between methods is a diagnostic. Cairo residuals are right-skewed. The standard formulas assume bell-curve noise and return a confident wrong answer. Tidemark detects this automatically and routes to the correct estimate. For precipitation and other skewed variables, Tidemark applies the MKC3 variance correction (Then et al. 2025) instead of Hamed-Rao, eliminating the false-positive bias that inflated that p-value in the first place.

### Earth System Scan

The `scan` subcommand runs all variables for a location in one command and produces a system fingerprint.

```
$ tidemark scan --location dhaka

variable          direction   slope           p-value    significance
temperature       downward    -0.021 C/yr     0.047      significant
evaporation       rising      +0.008 mm/d/yr  0.041      significant
humidity          falling     -0.11 %/yr      0.112      ~2031 (MC: 2029-2034)
wind              falling     -0.002 m/s/yr   0.33       ~2039
precipitation     downward    -0.016 mm/d/yr  0.385      ~2037 (GPM 2001-2025, 0.23x floor)
```

## Build

```
cargo build --release
pip install pymannkendall numpy scipy requests pandas
```

Requires Python 3.10+ and Rust 1.70+. Temperature, humidity, wind, and soil variables use the open NASA POWER API with no credentials. Precipitation (GPM IMERG) and remote sensing variables (AppEEARS MODIS) require a free NASA Earthdata account.

## Usage

```
tidemark analyze --location <name> --var <variable>
tidemark analyze --lat <lat> --lon <lon> --var <variable>
tidemark analyze --location <name> --var <variable> --years <n>
tidemark scan --location <name>
tidemark compare --location <name> --location <name> --var <variable>
```

`--years N` restricts to the last N years. Default is the full record from 1981. Named locations include dhaka, chittagong, sylhet, rajshahi, bogura, khulna, cairo, nairobi, lagos, mumbai, delhi, karachi, jakarta, manila, bangkok, addis ababa, dakar, lima, bogota, new york, london, tokyo, sydney, beijing, riyadh, islamabad. Use `--lat`/`--lon` for anything else.

## Variables

| Alias | Parameter | Unit | Source | From |
|---|---|---|---|---|
| `temperature` | T2M | C | NASA POWER | 1981 |
| `max-temperature` | T2M_MAX | C | NASA POWER | 1981 |
| `min-temperature` | T2M_MIN | C | NASA POWER | 1981 |
| `humidity` | RH2M | % | NASA POWER | 1981 |
| `evaporation` | EVLAND | mm/day | NASA POWER | 1981 |
| `wind` | WS10M | m/s | NASA POWER | 1981 |
| `vpd` | derived | kPa | NASA POWER | 1981 |
| `dtr` | derived | C | NASA POWER | 1981 |
| `soil` | GWETROOT | fraction | NASA POWER | 1981 |
| `surface-soil` | GWETTOP | fraction | NASA POWER | 1981 |
| `profile-soil` | GWETPROF | fraction | NASA POWER | 1981 |
| `frost` | FROST_DAYS | days | NASA POWER | 1981 |
| `soil-temp` | TSOIL1 | C | NASA POWER | 1981 |
| `skin-temp` | TS | C | NASA POWER | 1981 |
| `rainfall` | PRECTOTCORR | mm/day | GPM IMERG | 2001 |
| `ndvi` | MOD13Q1 | ratio | ORNL DAAC MODIS | 2000 |
| `aod` | MOD08_M3 | unitless | NASA LAADS DAAC MODIS | 2002 |
| `lst` | MOD11A2.061 | C | AppEEARS MODIS | 2001 |
| `et` | MOD16A2.061 | mm/day | AppEEARS MODIS | 2001 |

## Statistical Methods

Tidemark applies the following statistical methods automatically:

| Method | When applied | Reference |
|---|---|---|
| Modified Mann-Kendall (Hamed-Rao, lag=3) | Symmetric residuals (&#124;skewness&#124; ≤ 0.5) | Hamed & Rao 1998 |
| MKC3 third-order cumulant correction | Skewed residuals (&#124;skewness&#124; > 0.5, n ≥ 20) | Then et al. 2025 |
| Partial Mann-Kendall with ENSO control | When ENSO coverage ≥ 80% of period | Libiseller & Grimvall 2002 |
| AREP e-process | Sequential evidence accumulation | Ramdas et al. 2023 |
| Innovative Trend Analysis (ITA) | When extremes diverge (low and high tercile slopes have opposite signs) | Şen 2012 |

**MKC3** (Then, W., Hashim, R., and Alias, N.E., *Scientific Reports* 2025) corrects a systematic false-positive bias in Hamed-Rao for right-skewed series. For Cairo precipitation (skewness≈1.95), Hamed-Rao gives p≈0.03 (significant); MKC3 gives p>0.10 (not significant, correct). No Python package implements this; Tidemark is the first open implementation.

**Innovative Trend Analysis** (Şen, Z., *Journal of Hydrological Engineering* 2012) detects non-monotonic sub-population trends that Mann-Kendall cannot see. The series is split into two halves, each sorted in ascending order, and compared rank by rank. When the driest years are drying while the wettest years are intensifying, the net MK statistic is near zero (no trend) but ITA reveals the divergence. Output includes tercile slopes (low / mid / high value years) and a scatter plot showing both halves against the 1:1 diagonal. Shown only when low and high tercile slopes have opposite signs.

**Partial Mann-Kendall** (Libiseller, C. and Grimvall, A., *Environmetrics* 2002) separates the anthropogenic trend from ENSO variability using a rank-based cross-covariance framework. No parametric assumption required. Output: "trend robust to ENSO correction" / "anthropogenic trend exists, masked by ENSO" / "apparent trend may be ENSO-driven."

## Data Sources

**[NASA POWER](https://power.larc.nasa.gov)** - MERRA-2 reanalysis, 0.5 x 0.5 deg. Free REST API, no authentication. 1981-present.

**[NASA GES DISC GPM IMERG](https://disc.gsfc.nasa.gov)** - GPM IMERG Final Run V07B monthly precipitation. NASA Earthdata auth required. 2001-present. First fetch ~170s; cached after.

**[NASA AppEEARS](https://appeears.earthdatacloud.nasa.gov)** - MODIS LST (MOD11A2.061) and ET (MOD16A2.061). NASA Earthdata auth required. Authorize "AppEEARS" at urs.earthdata.nasa.gov before first use. First task 2-10 min; subsequent runs instant from cache.

**[ORNL DAAC MODIS](https://modis.ornl.gov/rst/api/v1/)** - MOD13Q1 250m NDVI. No authentication. 2000-present. Cached to `~/.tidemark/cache/`.

**[NASA LAADS DAAC](https://ladsweb.modaps.eosdis.nasa.gov)** - MOD08_M3 V6.1 monthly 1×1° gridded Aerosol Optical Depth (AOD at 550nm). NASA Earthdata auth required. Authorize "NASA LARC ASDC" at urs.earthdata.nasa.gov before first use. Granule catalog fetched via NASA CMR; individual pixels extracted via OPeNDAP ASCII (no HDF4 library required). 2002-present. Cached to `~/.tidemark/cache/`.

## Team

Raiyan Bin Rashid, Jotirmoy Bhowmik, Zunaeid Siddique, Nahin Rahman

NASA Space Apps Challenge 2026.
