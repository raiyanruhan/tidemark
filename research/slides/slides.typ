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
  ),
)

// Slide 1: Title
#title-slide()

// Slide 2: Problem
== The Gap Every Tool Leaves Open

#cols[
  Every existing tool stops here:

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
    Paris +1.5C   2066
    Paris +2.0C   2079
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
  test       Modified Mann-Kendall (Hamed-Rao)

  trend      +0.037 C / year
  p-value    0.018   significant

  Paris +1.5C   2066
  Paris +2.0C   2079
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
    [AppEEARS MODIS], [land surface temp], [2001–now],
    [ORNL DAAC MODIS], [NDVI vegetation], [2000–now],
    table.hline(),
  )

  #v(0.4em)
  #text(size: 0.82em)[ENSO correction via NOAA MEI v2 strips \
  El Niño variability to isolate the forced trend.]
][
  *Analysis pipeline:*

  + Rust CLI resolves location → lat/lon
  + Python fetches from correct NASA API
  + Hamed-Rao MK · Sen's slope · Pettitt changepoint
  + Monte Carlo bootstrap projects detection year
  + Milestones computed once significant

  #v(0.3em)
  Up to *45 years* of Earth observation data. \
  *Any region on Earth.*
]

// Slide 5: Significance trajectory — the core invention
== The Significance Trajectory

#cols[
  *Three independent estimates + information floor:*

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
    text(fill: rgb("#58a6ff"))[empirical bootstrap — trusted],
    [CRB lower bound], [Fisher information floor],
    table.hline(),
  )

  #v(0.3em)
  If methods diverge: prints why. Trusts Monte Carlo.
][
  *Dhaka annual rainfall — not yet significant:*

  ```
  p-value  0.385   not yet significant
  slope    -0.016  mm/day per year

  significance trajectory:
    Monte Carlo   2037  (n=1000, correct)
    Weatherhead   2028  (OLS, AR(1))
    analytical    2042  (IID approx)
    85% PI        2028 to 2053
  ```

  *The math has always existed. \
  Nobody built it into a tool.*
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

  +1.5C  2066
  +2.0C  2079
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
  p      0.047  ✓
  slope  -0.021 C/yr
  tau    -0.361
  chgpt  1999
  ```
]

#v(0.4em)
#text(size: 0.8em, style: "italic")[All from live NASA API calls.]

// Slide 7: Closing
#focus-slide[
  A tool that gives policy *a year.*

  #v(0.5em)
  Not a dashboard. Not a report. Not a p-value.

  #v(1em)

  ```
  $ tidemark analyze --location dhaka --var lst

  Paris +1.5C   2066
  ```

  #v(0.8em)
  #text(size: 0.65em)[
    Team Hylith · Raiyan Bin Rashid · Jotirmoy Bhowmik · \
    Zunaeid Siddique · Nahin Rahman · Bangladesh
  ]
]
