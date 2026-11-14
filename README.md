<p align="center"><img src="assets/logo.png" alt="tidemark" width="420"></p>

# tidemark

pulls NASA Earth science data for any location and runs statistical trend analysis.
tells you not just whether a variable is trending, but when it becomes significant
and what it crosses after that.

```
$ tidemark analyze --location dhaka --var temperature

location    Dhaka, Bangladesh  (23.81N, 90.41E)
variable    temperature (T2M, C)
period      1981 - 2025  (45 years)
test        Modified Mann-Kendall (Hamed-Rao, lag=3)

trend       -0.0211 C / year
direction   downward
tau         -0.36
z-score     -1.98
p-value     0.047   ✓ significant (p < 0.05)
detection floor         +-0.013 C / year   (slope is 1.6x above floor)
method eff  ARE 0.73 vs optimal   (1.11x more data needed than optimal rank test)
changepoint 1999   (Pettitt p=0.000)
records     6 observed  4.4 expected  1.37x

seasonal trends:
  DJF  -0.04017 C / year   p=0.000   significant
  MAM  -0.02359 C / year   p=0.012   significant
  JJA  -0.01241 C / year   p=0.007   significant
  SON  -0.01107 C / year   p=0.236   --
```

when a trend is not yet significant, it projects when it will be:

```
significance trajectory:
  analytical MK     2128   (assumes Gaussian IID, invalid here)
  Weatherhead 1998  2123   (assumes Gaussian, also invalid)
  Monte Carlo       2051   (n=1000, empirical bootstrap, correct)
  CRB lower bound   2063   (Fisher information floor, any test)
  methods diverge: 77 years
  reason: residual skewness=1.95, normality p<0.001, non-Gaussian noise
  trust: Monte Carlo
  85% PI            2036 - 2068
```

---

## build

```
cargo build --release
pip install pymannkendall numpy scipy requests pandas
```

requires Python 3.10+. Rust 1.70+.

---

## usage

```
tidemark analyze --location <name> --var <variable>
tidemark analyze --lat <lat> --lon <lon> --var <variable>
tidemark analyze --location <name> --var <variable> --years <n>
tidemark compare --location <name> --location <name> --var <variable>
```

`--years N` uses only the last N years of data (default: full record from 1981).

named locations: dhaka, chittagong, sylhet, cairo, nairobi, lagos, mumbai,
delhi, karachi, jakarta, manila, bangkok, dakar, lima, london, tokyo, and others.
unknown location: use `--lat`/`--lon` directly.

variables:

```
rainfall        PRECTOTCORR   mm/day
temperature     T2M           C
max-temperature T2M_MAX       C
min-temperature T2M_MIN       C
humidity        RH2M          %
evaporation     EVLAND        mm/day
wind            WS10M         m/s
vpd             derived       kPa           (vapor pressure deficit: T2M + RH2M)
dtr             derived       C             (diurnal temperature range: T2M_MAX - T2M_MIN)
soil            GWETROOT      fraction      (root zone soil moisture)
surface-soil    GWETTOP       fraction      (surface soil moisture)
profile-soil    GWETPROF      fraction      (full profile soil moisture)
frost           FROST_DAYS    days          (monthly frost days)
soil-temp       TSOIL1        C             (soil temperature layer 1)
skin-temp       TS            C             (earth skin temperature)
ndvi            MOD13Q1       ratio         (MODIS Terra 250m NDVI, 2000-present)
lst             MOD11A2.061   C             (MODIS land surface temperature, 2001-present, Earthdata auth)
et              MOD16A2.061   mm/day        (MODIS evapotranspiration, 2001-present, Earthdata auth)
```

---

## data

NASA POWER API — https://power.larc.nasa.gov  
no API key. MERRA-2 reanalysis. 1981-present.  
variables: T2M, T2M_MAX, T2M_MIN, RH2M, EVLAND, WS10M, soil/derived.

NASA GES DISC GPM IMERG — https://disc.gsfc.nasa.gov  
Earthdata auth required. GPM IMERG V07B monthly precipitation. 2001-present.  
set NASA_EARTHDATA_USERNAME and NASA_EARTHDATA_PASSWORD. first fetch ~170s, cached after.

NASA AppEEARS — https://appeears.earthdatacloud.nasa.gov  
Earthdata auth required. MODIS LST (MOD11A2.061) and ET (MOD16A2.061). 2001-present.  
authorize "AppEEARS" at urs.earthdata.nasa.gov before first use.  
first task 2-10 min depending on server queue; subsequent runs instant from cache.

ORNL DAAC MODIS Web Service — https://modis.ornl.gov/rst/api/v1/  
no API key. MOD13Q1 (MODIS Terra 250m 16-day NDVI). 2000-present.  
first fetch cached to ~/.tidemark/cache/; subsequent runs instant.

---

built for NASA Space Apps Challenge 2026 — "Be An Earth System Trend Detective"
