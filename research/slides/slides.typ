#import "@preview/touying:0.8.0": *
#import themes.metropolis: *

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  footer: none,
  config-colors(
    primary: rgb("#58a6ff"),
    primary-light: rgb("#cfe3ff"),
    secondary: rgb("#0d1117"),
    neutral-darkest: rgb("#0d1117"),
  ),
  config-info(
    title: [tidemark],
    subtitle: [Not just whether a trend is real. *When.*],
    author: [
      Raiyan Bin Rashid · Jotirmoy Bhowmik · Zunaeid Siddique · Nahin Rahman \
      #text(size: 0.85em)[Team Hylith · Bangladesh]
    ],
    date: [NASA Space Apps Challenge 2026 — Be An Earth System Trend Detective],
    logo: image("favicon.png", width: 2.5em),
  ),
)

// Slide 1: Title
#title-slide()

// Slide 2: Problem
== The Gap Every Tool Leaves Open

#cols[
  Most tools stop here:

  ```
  p-value   0.112   not yet significant
  ```

  #v(0.4em)

  Farmers plan 10-year rotations. \
  Policymakers fund flood walls. \
  *They need a year. Not a p-value.*

  #v(0.4em)

  #text(size: 0.78em, style: "italic")[
    "Sometimes all a trend needs to become significant \
    is a longer period." \
    — Dr. James Aker, NASA Goddard
  ]
][
  *tidemark answers two new questions:*

  #v(0.5em)

  - If not yet significant: *when will it be?*
  - Once significant: *when does it cross a threshold?*

  #v(0.5em)

  ```
  significance trajectory:
    Monte Carlo   2037
    85% PI        2028 to 2053

  milestones (once significant):
    local +0.5C warming  2048
    local +1.0C warming  2061
  ```
]

// Slide 3: User experience — what it looks like to run it
== Using tidemark

#cols[
  *Any location. Any NASA variable. One command.*

  #v(0.3em)

  ```
  $ tidemark analyze \
      --location dhaka \
      --var lst
  ```

  #v(0.5em)

  No sign-up. No dashboard. \
  Single binary. Runs offline after first fetch. \
  *Result in seconds.*
][
  ```
  location   Dhaka, Bangladesh (23.81N, 90.41E)
  variable   land surface temp (LST, C)
  period     2001 - 2025  (25 years)
  test       Mann-Kendall, AR(1) sieve bootstrap

  trend      +0.037 C / year
  p-value    0.018   significant

  local +0.5C warming   2041
  local +1.0C warming   2054
  ```

  #v(0.3em)
  #text(size: 0.78em)[Live NASA AppEEARS MODIS data. Not synthetic.]
]

// Slide 4: How it works + NASA data
== Powered by NASA Open Data

#cols[
  #table(
    columns: (auto, auto, auto),
    stroke: none,
    inset: (x: 0.4em, y: 0.5em),
    table.hline(),
    [*NASA Source*], [*Variable*], [*Record*],
    table.hline(stroke: 0.5pt),
    [POWER / MERRA-2], [temp, wind, humidity, soil], [1981–now],
    [GES DISC GPM IMERG], [precipitation], [2001–now],
    [AppEEARS MODIS], [land surface temp, ET], [2001–now],
    [ORNL DAAC MODIS], [NDVI vegetation], [2000–now],
    [LAADS DAAC MODIS], [aerosol optical depth], [2002–now],
    table.hline(),
  )

  #v(0.4em)
  #text(size: 0.82em)[ENSO correction via NOAA MEI v2 strips \
  El Niño variability to isolate the forced trend.]
][
  *Analysis pipeline:*

  + Rust CLI resolves location → lat/lon
  + Python fetches from correct NASA API
  + *Mann-Kendall, AR(1) sieve-bootstrap null* (verdict)
  + Block bootstrap · MKC3 · Hamed-Rao shown for comparison
  + Sen's slope · sup-F trend-break test (Andrews 1993)
  + ENSO separation (partial MK, rank-based)
  + ITA: sub-population slopes (extremes divergence)
  + *Bayesian changepoint scan (NIG marginal likelihood)*
  + Monte Carlo bootstrap projects detection year
  + Milestones computed once significant

  #v(0.3em)
  Up to *45 years* of Earth observation data. \
  *Any region on Earth. 19 variables.*
]

// Slide 5: Significance trajectory — the core invention
== The Significance Trajectory

#cols[
  *Four independent estimates:*

  #v(0.3em)

  #table(
    columns: (auto, 1fr),
    stroke: none,
    inset: (x: 0.4em, y: 0.5em),
    table.hline(),
    [*Method*], [*Models*],
    table.hline(stroke: 0.5pt),
    [Analytical MK], [Gaussian IID noise],
    [Weatherhead 1998], [AR(1) autocorrelation],
    text(fill: rgb("#58a6ff"), weight: "bold")[Monte Carlo],
    text(fill: rgb("#58a6ff"))[AR(1) simulation, skewness-robust],
    [CRB lower bound], [Fisher information floor],
    table.hline(),
  )

  #v(0.3em)
  *Verdict:* AR(1) sieve-bootstrap null; block bootstrap · MKC3 · Hamed-Rao shown for comparison \
  If trajectory methods diverge: prints why and shows all estimates.
][
  *Dhaka annual rainfall — not yet significant:*

  ```
  p-value  0.385   not yet significant
  slope    -0.016  mm/day per year

  significance trajectory:
    Monte Carlo   2037  (n=1000, AR(1) sim)
    Weatherhead   2028  (OLS, AR(1))
    analytical    2042  (IID approx)
    85% PI        2028 to 2053
  ```

  *The math existed in the literature. \
  We built it into a tool.*
]

// Slide 6: Live results across three variables
== Live Findings from Dhaka

#cols(columns: (1fr, 1fr, 1fr))[
  *Land Surface Temp* \
  #text(size: 0.78em)[MODIS · 2001–2025]

  #v(0.3em)

  ```
  trend  +0.037 C/yr
  p      0.018  ✓

  +0.5C local  2041
  +1.0C local  2054
  ```
][
  *Annual Rainfall* \
  #text(size: 0.78em)[GPM IMERG · 2001–2025]

  #v(0.3em)

  ```
  p      0.385  not yet
  slope  -0.016 mm/day/yr

  MC     2037
  PI     2028–2053
  ```
][
  *Air Temperature* \
  #text(size: 0.78em)[POWER MERRA-2 · 1981–2025]

  #v(0.3em)

  ```
  p      0.037  ✓
  slope  -0.021 C/yr
  tau    -0.361
  Sup-F break: 1997 (p=0.006)
  Bayesian scan: no break
  ```
]

#v(0.4em)
#text(size: 0.8em, style: "italic")[All from live NASA API calls.]

// Slide 7: ITA — sub-population divergence
== When Extremes Pull Apart

#cols[
  *Mann-Kendall tests only the net trend.*

  #v(0.3em)

  When driest years get drier and wettest years
  get wetter simultaneously, the net slope is
  near zero. MK says "no trend." The finding
  that matters is invisible.

  #v(0.5em)

  *Innovative Trend Analysis (Şen 2012)*
  splits the record into two halves and compares
  sorted pairs rank by rank — revealing which
  part of the value range is driving change.
][
  ```
  extreme trend structure (ITA):
    low-value years   -0.021 mm/day/yr
    mid-value years   +0.001 mm/day/yr
    high-value years  +0.013 mm/day/yr

    intensification of extremes
    MK tau sees only the net signal
  ```

  #v(0.3em)
  #text(size: 0.8em)[Shown when low and high tercile \
  slopes have opposite signs. Scatter plot included.]
]

// Slide 8: Bayesian changepoint
== When Did the Trend Change?

#cols[
  *Mann-Kendall tests the full series.*

  #v(0.3em)

  It cannot see that a series has two regimes —
  one warming, one flat — where the two halves
  partially cancel and the net result is marginal.

  #v(0.5em)

  *Bayesian changepoint scan (NIG marginal likelihood)*
  compares the evidence for splitting the series at
  every candidate year. The year with the highest
  Bayes factor is the structural break.

  #v(0.3em)
  #text(size: 0.78em)[Detection: log BF > 3.5 and above bootstrap null 95th pct. \
  Conjugate NIG marginal likelihoods. Pure numpy — no C extensions.]
][
  ```
  sup-F trend-break test (Andrews 1993):
    structural break:  1997
    bootstrap p-value: 0.006

  Bayesian scan: no break detected

  Mann-Kendall: p = 0.037 (significant)
  slope: -0.021 C/yr over full 1981-2025
  ```

  #v(0.3em)
  #text(size: 0.78em)[Dhaka temperature, NASA POWER 1981-2025. \
  Sup-F and Bayesian scan have different sensitivities — both shown.]
]

// Slide 9: AOD — Dr. Aker callback
== Dr. Aker's Variable, Live

#cols[
  #text(size: 0.88em, style: "italic")[
    "Aerosol optical depth... I'm looking at \
    Wisconsin here..."
  ]

  #v(0.3em)
  #text(size: 0.78em)[— Dr. James Aker, NASA Goddard, \
  Space Apps 2026 challenge video]

  #v(0.5em)

  *Wisconsin, right now:*

  ```
  $ tidemark analyze \
      --location madison \
      --var aod
  ```

  MODIS MOD08_M3 · 2002–2025 · 23 years \
  Verdict: AR(1) sieve bootstrap; variants shown for comparison
][
  *Data: MODIS MOD08_M3 V6.1*

  #v(0.3em)

  - Monthly 1° × 1° gridded AOD at 550nm
  - NASA LAADS DAAC via CMR + OPeNDAP
  - Same Earthdata login as precipitation
  - No new dependencies

  #v(0.3em)

  Full pipeline: MK test + significance trajectory +
  detection floor + 4-method crossing year +
  ENSO separation + ITA extremes check.

  #text(size: 0.78em)[Live NASA satellite data. Not synthetic.]
]

// Slide 10: Closing
#focus-slide[
  A tool that gives policy *a year.*

  #v(0.5em)
  Not a dashboard. Not a report. Not a p-value.

  #v(1em)

  ```
  $ tidemark analyze --location dhaka --var lst

  local +1.0C warming   2054
  ```

  #v(0.8em)
  #text(size: 0.65em)[
    Team Hylith · Raiyan Bin Rashid · Jotirmoy Bhowmik · \
    Zunaeid Siddique · Nahin Rahman · Bangladesh
  ]
]
