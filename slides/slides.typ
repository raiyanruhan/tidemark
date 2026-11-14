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
    author: [Raiyan Bin Rashid, Bangladesh, Team Hylith],
    date: [NASA Space Apps Challenge 2026],
  ),
)

#title-slide()

= Impact

== The Unanswered Question

#cols[
  Every existing tool stops here:

  ```
  p-value   0.112   not yet significant
  ```

  Farmers plan 10-year rotations. \
  Policymakers fund flood walls. \
  *They need a year. Not a p-value.*
][
  *tidemark answers the next two questions:*

  #v(0.5em)

  - If not yet significant: *when will it be?*
  - Once significant: *when does it cross a threshold?*

  #v(0.5em)

  ```
  significance trajectory:
    Monte Carlo   2037
    85% PI        2028 to 2053
  ```
]

#focus-slide[
  "Sometimes all a trend needs to become \
  significant is a longer period."

  #v(1em)
  #text(size: 0.65em)[Dr. James Aker, NASA Goddard Space Flight Center (challenge author)]
]

= Creativity

== Significance Trajectory

#cols[
  *Three independent estimates and a floor:*

  #v(0.3em)

  #table(
    columns: (auto, 1fr),
    stroke: none,
    inset: (x: 0.4em, y: 0.5em),
    table.hline(),
    [*Method*], [*Assumption*],
    table.hline(stroke: 0.5pt),
    [Analytical MK], [Gaussian IID noise],
    [Weatherhead 1998], [AR(1) corrected],
    text(fill: rgb("#58a6ff"), weight: "bold")[Monte Carlo],
    text(fill: rgb("#58a6ff"))[empirical bootstrap],
    [CRB lower bound], [Fisher information floor],
    table.hline(),
  )

  #v(0.3em)
  If methods diverge over 5 years: prints why, trusts Monte Carlo.
][
  *Dhaka rainfall, not yet significant:*

  ```
  p-value  0.385  not yet significant
  slope    -0.016 mm/day per year

  Monte Carlo   2037  (n=1000, correct)
  Weatherhead   2028  (OLS, AR(1))
  analytical    2042  (IID approx)

  85% PI        2028 to 2053
  ```

  The math has always been there. \
  *Nobody built this into a tool.*
]

= Validity

== Architecture

#cols[
  *Pipeline:*

  + *Rust CLI*: parse args, resolve location to lat/lon \
    (embedded 25-city table, zero network overhead)
  + *Python fetch*: route variable to correct NASA source
  + *Analysis*: Hamed-Rao MK, Sen's slope, ENSO \
    correction, Pettitt changepoint, detection floor
  + *Output*: milestones if significant; \
    trajectory if not

  #v(0.5em)
  Single binary. No server. No database.
][
  ```
  tidemark (Rust)
    resolve "dhaka" to 23.81N, 90.41E
    spawn python analyze.py --lat ...
    read stdout JSON
    format aligned terminal output

  python/analyze.py
    route variable to fetch module
    run Mann-Kendall pipeline
    run Monte Carlo (p > 0.05 only)
    print JSON to stdout
  ```
]

= Relevance

== Four NASA Data Sources

#cols[
  #table(
    columns: (auto, auto, auto),
    stroke: none,
    inset: (x: 0.4em, y: 0.5em),
    table.hline(),
    [*Source*], [*Variable*], [*Coverage*],
    table.hline(stroke: 0.5pt),
    [NASA POWER / MERRA-2], [temp, humidity, wind, soil], [1981 to present],
    [GES DISC GPM IMERG V07B], [precipitation], [2001 to present],
    [AppEEARS MODIS MOD11A2], [land surface temp], [2001 to present],
    [ORNL DAAC MOD13Q1], [NDVI vegetation], [2000 to present],
    table.hline(),
  )
][
  *Challenge criteria, exceeded:*

  #v(0.3em)

  - Earth science variables from NASA missions
  - Any region (name or lat/lon)
  - Time series up to 45 years
  - Mann-Kendall significance test and rate of change
  - *Projects when the trend becomes significant*
  - *Projects what threshold it crosses after that*

  #v(0.3em)
  #text(size: 0.82em)[Also: ENSO correction via NOAA MEI v2 strips \
  El Nino variability to isolate the forced trend.]
]

= Results

== Live Findings from Dhaka

#cols(columns: (1fr, 1fr, 1fr))[
  *Land Surface Temp* \
  #text(size: 0.78em)[MODIS MOD11A2, 2001 to 2025]

  #v(0.3em)

  ```
  trend  +0.037 C per year
  p      0.018  significant

  Paris +1.5C   2066
  Paris +2.0C   2079
  ```
][
  *Annual Rainfall* \
  #text(size: 0.78em)[GPM IMERG, 2001 to 2025]

  #v(0.3em)

  ```
  p      0.385  not yet
  slope  -0.016 mm/day/yr
  floor  0.23x

  MC     2037
  85% PI 2028 to 2053
  ```
][
  *Air Temperature 2m* \
  #text(size: 0.78em)[POWER MERRA-2, 1981 to 2025]

  #v(0.3em)

  ```
  p      0.047  significant
  slope  -0.021 C per year
  tau    -0.361
  chgpt  1999
  ```
]

#v(0.4em)
#text(size: 0.8em, style: "italic")[All findings from live NASA API calls. Not synthetic data.]

#focus-slide[
  A tool that gives policy *a year.*

  #v(0.5em)
  Not a dashboard. Not a report. Not a p-value.

  #v(1em)

  ```
  $ tidemark analyze --location dhaka --var lst

  Paris +1.5C   2066
  ```
]
