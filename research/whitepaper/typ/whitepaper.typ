// Tidemark Whitepaper
// Compile: typst compile --font-path fonts/ubuntu-font-family-0.83 --font-path fonts/ubuntu-sans whitepaper.typ whitepaper.pdf

#set document(
  title: "Tidemark: A Statistical Detection-Time Framework for Earth System Trend Analysis",
  author: "Raiyan Bin Rashid, Jotirmoy Bhowmik, Zunaeid Siddique, Nahin Rahman",
  keywords: ("Mann-Kendall", "MKC3", "partial Mann-Kendall", "ENSO isolation", "trend detection", "significance trajectory", "Monte Carlo", "NASA POWER", "GPM IMERG", "AppEEARS MODIS", "Bayesian changepoint", "NIG marginal likelihood"),
)

// ---- Color palette (matches app) ----
#let blue       = rgb("#1a56db")
#let blue-dark  = rgb("#1142b8")
#let navy       = rgb("#0f172a")
#let charcoal   = rgb("#1a1a1a")
#let gray-6     = rgb("#6b7280")
#let gray-3     = rgb("#d1d5db")
#let bg-light   = rgb("#f1f5f9")
#let bg-blue    = rgb("#eff6ff")
#let white      = rgb("#ffffff")

// ---- Page ----
#set page(
  paper: "a4",
  margin: (top: 2.2cm, bottom: 2.6cm, left: 2.4cm, right: 2.4cm),
  numbering: "1",
  number-align: center,
)

// ---- Typography ----
#set text(
  font: "Ubuntu Sans",
  size: 10.5pt,
  fill: charcoal,
  hyphenate: false,
)

#set par(
  justify: true,
  leading: 0.72em,
  spacing: 1.0em,
)

#set heading(numbering: "1.1")

// H1
#show heading.where(level: 1): it => {
  v(1.8em)
  text(size: 15pt, weight: "bold", fill: navy, font: "Ubuntu Sans")[#it]
  v(0.1em)
  line(length: 100%, stroke: 1pt + blue)
  v(0.5em)
}

// H2
#show heading.where(level: 2): it => {
  v(1.1em)
  text(size: 12pt, weight: "bold", fill: navy, font: "Ubuntu Sans")[#it]
  v(0.25em)
}

// H3
#show heading.where(level: 3): it => {
  v(0.8em)
  text(size: 10.5pt, weight: "bold", fill: blue-dark, font: "Ubuntu Sans")[#it]
  v(0.1em)
}

// Code blocks -- light gray bg, rounded, teal text (matches reference PDF style)
#let code-bg   = rgb("#f5f5f2")
#let code-teal = rgb("#2a7a69")

#show raw.where(block: true): it => {
  block(
    fill: code-bg,
    radius: 6pt,
    inset: (x: 1.2em, y: 1.0em),
    width: 100%,
    text(font: "Ubuntu Mono", size: 9pt, fill: code-teal)[#it],
  )
}

// Inline code -- teal, no box
#show raw.where(block: false): it => {
  text(font: "Ubuntu Mono", size: 9pt, fill: code-teal)[#it]
}

// Math equations
#set math.equation(numbering: "(1)")

// Figures
#set figure(gap: 0.6em)
#show figure.caption: it => {
  v(0.2em)
  text(size: 9pt, fill: gray-6, style: "italic")[#it]
}

// Callout helper
#let callout(body) = block(
  stroke: (left: 3pt + blue),
  inset: (left: 1.4em, top: 1.0em, bottom: 1.0em, right: 0em),
  width: 100%,
  body,
)

// Table helper -- header row light gray, data rows plain
#let thead-fill(x, y) = if y == 0 { rgb("#ebebeb") } else { none }

// Table stroke: horizontal lines only (matches reference PDF style)
#set table(stroke: (x, y) => (
  top: if y == 0 { 1pt + charcoal } else if y == 1 { 0.5pt + gray-3 } else { 0.3pt + gray-3 },
  bottom: 0.3pt + gray-3,
  left: none,
  right: none,
))

// Ref entry helper
#let refentry(body) = {
  block(below: 0.55em)[
    #set text(size: 9.5pt)
    #body
  ]
}

// ============================================================
// COVER PAGE  --  academic title page
// ============================================================

#page(numbering: none, header: none)[
  #v(2.0cm)
  #align(center)[
    #text(size: 19pt, weight: "bold", fill: navy, font: "Ubuntu Sans")[
      Earth system trend detection
    ]
    #v(0.6em)
    #text(size: 12pt, weight: "light", fill: charcoal, font: "Ubuntu Sans")[
      How to determine when a climate variable will reach statistical significance, \
      from Mann-Kendall analysis to Monte Carlo projection
    ]
    #v(1.0em)
    #text(size: 10pt, font: "Ubuntu Sans")[Raiyan Bin Rashid, Jotirmoy Bhowmik, Zunaeid Siddique, Nahin Rahman]
    #v(0.3em)
    #text(size: 9.5pt, fill: gray-6, font: "Ubuntu Sans")[November 2026]
  ]

  #v(1.0cm)
  #line(length: 100%, stroke: 0.5pt + charcoal)
  #v(0.7cm)

  #text(size: 10pt, weight: "bold", font: "Ubuntu Sans")[Abstract]
  #v(0.4em)
  #text(size: 10pt)[
    We present Tidemark, an Earth system trend analysis tool (command line and web)
    that answers the question standard trend tests leave open: if a trend is not yet
    statistically significant, when is it likely to become so? Its central output is
    the *significance trajectory*: an estimate of the year a trend will cross
    p#h(0.05em)<#h(0.05em)0.05, from four methods: an analytical formula based on the
    $n^(3/2)$ growth of the Mann-Kendall Z-score, the Weatherhead et al. (1998)
    detection-time formula, a 1,000-path Monte Carlo simulation that keeps the
    autocorrelation of the data and allows for uncertainty in the slope, and a
    Cramér-Rao bound from Fisher information. Around it Tidemark reports a
    *detection floor* (the smallest slope Mann-Kendall can resolve at 80% power for
    the current record length), a test for a break in the trend line, a partial
    Mann-Kendall test controlling for ENSO (Libiseller & Grimvall, 2002), and an
    e-process for trend.
    The significance verdict comes from a Mann-Kendall test whose null distribution
    is bootstrapped from each series (AR(1) sieve bootstrap). We chose it by
    measurement: on simulated trend-free data ($n = 45$) our original automatic
    selection among Hamed-Rao, MKC3 (Then & Abdul Halim, 2025) and block bootstrap
    rejected 7 to 16% of the time at a nominal 5%; the bootstrap test rejects 6 to 8%.
    Those three corrections are still reported for comparison.
    On NASA POWER data (1981-2025), Dhaka, Bangladesh shows a significant cooling
    trend in 2 m air temperature ($p = 0.037$) with a break in the trend line in 1997
    ($p = 0.006$); Cairo, Egypt precipitation is not significant ($p = 0.75$), lies at
    0.18 of the detection floor, and the four methods disagree by decades, which the
    tool reports rather than hides. The tool is a Rust CLI with a Python statistics
    engine, needs no authentication for POWER variables (a free NASA Earthdata account
    is needed for GPM and MODIS products), and is reproducible from open NASA data.
  ]
  #v(0.3em)
  #text(size: 9pt, fill: gray-6)[
    *Keywords:* Mann-Kendall, trend detection, significance trajectory, detection floor,
    Monte Carlo, Sen's slope, sieve bootstrap, structural break, NASA POWER,
    Bangladesh, Earth systems, climate analysis
  ]
]

// ============================================================
// TABLE OF CONTENTS
// ============================================================

#page(numbering: none, header: none)[
  #v(0.4cm)
  #text(size: 15pt, weight: "bold", fill: navy, font: "Ubuntu Sans")[Contents]
  #v(0.5cm)

  #let toc-entry(num, title, pg, lnk: none) = {
    grid(
      columns: (2.2em, 1fr, 2.2em),
      text(fill: gray-6)[#num],
      if lnk != none { link(lnk)[#text(fill: charcoal)[#title]] } else { text(fill: charcoal)[#title] },
      align(right, text(fill: gray-6)[#if lnk != none { context counter(page).at(lnk).first() } else { pg }]),
    )
    v(0.38em)
  }

  #set text(size: 10.5pt, font: "Ubuntu Sans")

  #toc-entry("1.", [Introduction], "3", lnk: <s-intro>)
  #toc-entry("2.", [Background and Motivation], "4", lnk: <s-bg>)
  #toc-entry("3.", [Data Sources], "6", lnk: <s-data>)
  #toc-entry("4.", [Statistical Methods], "7", lnk: <s-stats>)
  #pad(left: 2.2em)[
    #toc-entry("4.1", [The Significance Test], "7", lnk: <s-mk>)
    #toc-entry("4.2", [Sen's Slope Estimator], "8", lnk: <s-sens>)
    #toc-entry("4.3", [The Detection Floor], "9", lnk: <s-floor>)
    #toc-entry("4.4", [Four Independent Estimation Methods], "10", lnk: <s-three>)
    #toc-entry("4.5", [Divergence Detection and Diagnosis], "12", lnk: <s-div>)
    #toc-entry("4.6", [MKC3 Third-Order Cumulant Variance Correction], "13", lnk: <s-mkc3>)
    #toc-entry("4.7", [Partial Mann-Kendall with ENSO Control], "14", lnk: <s-pmk>)
    #toc-entry("4.8", [Trend-Break Detection], "15", lnk: <s-bocpd>)
  ]
  #toc-entry("5.", [Novel Contributions], "16", lnk: <s-novel>)
  #pad(left: 2.2em)[
    #toc-entry("5.1", [The Significance Trajectory], "16", lnk: <s-sigtraj>)
    #toc-entry("5.2", [A System View], "17", lnk: <s-scan>)
    #toc-entry("5.3", [The Trend E-process], "18", lnk: <s-arep>)
    #toc-entry("5.4", [MKC3 and Block Bootstrap Implementations], "19", lnk: <s-novel-mkc3>)
    #toc-entry("5.5", [Partial Mann-Kendall ENSO Separation], "20", lnk: <s-novel-pmk>)
    #toc-entry("5.6", [Trend-Break Detection], "21", lnk: <s-novel-bocpd>)
  ]
  #toc-entry("6.", [Validation Results], "16", lnk: <s-valid>)
  #toc-entry("7.", [Case Study: Bangladesh], "18", lnk: <s-bd>)
  #toc-entry("8.", [Discussion], "20", lnk: <s-discuss>)
  #toc-entry("9.", [Conclusions], "21", lnk: <s-conclude>)
  #toc-entry("", [References], "22", lnk: <s-refs>)
  #toc-entry("A.", [Appendix: CLI Usage and Output Format], "23", lnk: <appendix-a>)
  #toc-entry("B.", [Appendix: Reproducibility Checklist], "24", lnk: <appendix-b>)
]

#counter(page).update(1)

// ============================================================
// 1. INTRODUCTION
// ============================================================

= Introduction <s-intro>

Dr. James Aker of NASA Goddard Space Flight Center framed the gap in the challenge
brief: "Sometimes all a trend needs to become significant is a longer period." The
tools we surveyed do not act on that sentence. The Mann-Kendall test rejects or fails to reject
the null hypothesis of no trend, and the result is reported as a binary: significant
or not. Standard tools (NASA Giovanni, NOAA Climate Explorer, Copernicus CDS Toolbox)
implement this test and stop there. What they do not report is what the result implies
about the future.

The cost of that omission is concrete. Cairo's precipitation series (NASA POWER,
1981-2025) is not significant ($p = 0.75$). Asked when it will be, the analytical
formula says about 2125, the Weatherhead formula 2078, the Cramér-Rao bound 2063, and
in the Monte Carlo simulation just over half of the 1,000 paths never reach
significance within 80 years. The residuals are strongly right-skewed (skewness 1.95)
and the slope is at 0.18 of the detection floor. A single number would be false
precision here. Tidemark reports all four estimates, flags the disagreement, and
states the reason.

The binary outcome carries three pieces of information not shown:

+ For a not-yet-significant series, how much additional data is required before
  the same trend, if real, will be detectable? The answer depends on the signal-to-noise
  ratio, the autocorrelation structure of residuals, and the shape of the noise
  distribution. It is not derivable from the p-value alone.

+ For a significant series, at what rate is the variable approaching critical physical
  thresholds? Sen's slope provides the rate; projecting it forward to named thresholds
  (warming targets, drought classification levels, agricultural stress limits) gives
  the implied timeline.

+ Is the current record long enough to resolve the signal at all? A trend below the
  detection floor of the Mann-Kendall test cannot become significant regardless of
  direction, until the record grows enough to lower the floor.

This paper introduces the *significance trajectory*: given a time series with a
consistent direction and Sen's slope $hat(beta)$, the significance trajectory is the
distribution over future years $Y^*$ at which the Mann-Kendall p-value will cross
$alpha = 0.05$, estimated via four independent methods with divergence detection and
an 85% Monte Carlo predictive interval. The trajectory is computed forward from the
empirical noise distribution, requiring no Gaussian assumption.

This paper makes the following contributions to the Earth system trend analysis problem:

+ The *significance trajectory*: an estimate of when p#h(0.05em)<#h(0.05em)0.05 will be
  reached, with an 85% predictive interval from Monte Carlo simulation and a four-method
  cross-check.

+ The *analytical $n^(3/2)$ crossing formula*: derived from the structure of the
  Mann-Kendall test and computable without simulation.

+ The *detection floor*: the minimum slope Mann-Kendall can detect at 80% power given
  the current record length, printed with every result.

+ A *measured significance test*: the false-alarm rate of every test in the pipeline
  was measured on simulated trend-free data, and the verdict was moved to the test
  that came closest to its nominal rate (Section 4.1).

+ A *trend-break test* that asks whether two straight lines fit better than one,
  so that a steady trend is not mistaken for a changepoint (Section 4.8).

+ *ENSO separation* by regression and by the partial Mann-Kendall test
  (Libiseller & Grimvall, 2002).

+ Open implementations of the *MKC3* (Then & Abdul Halim, 2025) and *block bootstrap*
  (Önöz & Bayazit, 2012) Mann-Kendall variants, reported for comparison.

// ============================================================
// 2. BACKGROUND
// ============================================================

= Background and Motivation <s-bg>

== The Mann-Kendall Test and Its Limitations

The Mann-Kendall test [1, 2] has become the standard nonparametric
method for detecting monotonic trends in environmental time series. It is robust to
outliers, makes no distributional assumption on the data, and handles missing values
gracefully. For a time series $x_1, x_2, dots, x_n$, the test statistic $S$ is:

$ S = sum_(k=1)^(n-1) sum_(j=k+1)^(n) "sgn"(x_j - x_k) $ <eq:mk-s>

where $"sgn"(theta) = +1$ if $theta > 0$, $0$ if $theta = 0$, and $-1$ if $theta < 0$.

The variance of $S$ under the null hypothesis of no trend is:

$ "Var"(S) = frac(n(n-1)(2n+5) - sum_p t_p (t_p - 1)(2 t_p + 5), 18) $ <eq:var-s>

where $t_p$ are the sizes of tied groups. The normalized test statistic is
$Z = (S - 1) slash sqrt("Var"(S))$, and significance is assessed against the
standard normal distribution.

The test's primary limitation is sensitivity to autocorrelation. Environmental time
series, particularly temperature records, commonly exhibit positive lag-1
autocorrelation that inflates $S$ and produces artificially low p-values. Applied
naively, the original Mann-Kendall test overrejects the null hypothesis for
autocorrelated series.

== The Hamed-Rao Autocorrelation Correction

Hamed and Rao (1998) [3] proposed a correction to the variance of $S$ that
accounts for serial correlation. The corrected variance is:

$ "Var"^*(S) = "Var"(S) dot frac(n, n_S) $ <eq:var-corrected>

where the inflation factor $n slash n_S$ is computed from the autocorrelation function
of the rank-detrended series:

$ frac(n, n_S) = 1 + frac(2, n(n-1)(n-2)) sum_(i=1)^(n-1) (n-i)(n-i-1)(n-i-2) rho_S (i) $ <eq:inflation>

Only lags whose rank autocorrelation is significant are included; Tidemark's
Hamed-Rao variant uses the first three lags via the pymannkendall library [6].

*A measured limitation.* On simulated trend-free series ($n = 45$) this test rejected
about 7% of the time at a nominal 5% for independent noise. Tidemark's original
automatic selection among Hamed-Rao, MKC3 and block bootstrap rejected 9 to 16% for
skewed and autocorrelated noise. For that reason these corrections are now reported
for comparison only, and the significance verdict comes from the bootstrap test
described in Section 4.1.

== The Detection Time Problem

The question of how long a monitoring record must be to detect a trend of a given
magnitude was formalized by Weatherhead et al. (1998) [4] in the context
of detecting trends in stratospheric ozone from satellite data. They derived:

$ n^* = lr((frac(3.3 sigma_N, |omega|))^(2 slash 3)) dot lr((frac(1 + phi, 1 - phi))^(1 slash 3)) $ <eq:weatherhead>

where $n^*$ is the number of years needed to detect the trend at 90% power,
$sigma_N$ is the standard deviation of noise (annual residuals from the detrended
series), $omega$ is the trend magnitude, and $phi$ is the lag-1 autocorrelation
coefficient of the residuals. The factor 3.3 comes from $z_(alpha slash 2) + z_beta
approx 1.96 + 1.28 = 3.24 approx 3.3$ for a two-tailed test at $alpha = 0.05$
with 90% power.

The Weatherhead formula has two critical properties. First, detection time grows as
the two-thirds power of the noise-to-signal ratio, meaning that halving the trend lengthens
the required record by about 59%. Second, autocorrelation substantially inflates detection
time: a series with $phi = 0.5$ requires $(1.5 slash 0.5)^(1 slash 3) = 1.44$ times
as many years as an independent series.

The formula is widely used in atmospheric science to plan how long a record must be
to detect a trend. We are not aware of a public trend tool that applies it to live
NASA API data.

== The Structural Flaw in Sequential P-Value Monitoring

A p-value is valid at a sample size fixed in advance. When a monitoring programme
asks "is p < 0.05?" again every year, the chance of at least one false alarm over the
whole period is well above 5%.

Climate monitoring is inherently sequential, and a significance trajectory is itself a
statement about repeated future tests. Tidemark handles this in two ways. In the
Monte Carlo simulation a crossing only counts when significance persists for three
consecutive years (Section 4.4). Separately, it reports an *e-process* [11], a
nonnegative process $E_n$ with $E[E_tau | H_0] <= 1$ at every stopping time $tau$:
rejecting when $E_n >= 1 slash alpha$ controls the false positive rate at $alpha$
whenever the check is made. Section 5.3 describes the e-process used (exact for
independent Gaussian noise; checked by simulation otherwise).

// ============================================================
// 3. DATA
// ============================================================

= Data Sources <s-data>

Tidemark draws from five NASA data sources depending on the variable requested.
The validation results in Section 6 (Dhaka temperature, Cairo precipitation) used
NASA POWER (1981-2025). The Cairo POWER result is preserved as a methodology
demonstration; the CLI now routes precipitation to GPM IMERG (2001-present).

== NASA POWER API

The NASA Prediction of Worldwide Energy Resources (POWER) dataset [9] provides
meteorological variables via a free REST API requiring no authentication.

```
GET https://power.larc.nasa.gov/api/temporal/monthly/point
    ?start=1981&end=2025
    &latitude={lat}&longitude={lon}
    &community=ag
    &parameters=T2M,T2M_MAX,T2M_MIN,RH2M,EVLAND,WS10M
    &format=json
```

The API returns monthly averages keyed by `YYYYMM` with a month-13 annual average
stripped before analysis. POWER has 0.5 deg x 0.5 deg spatial resolution derived
from the MERRA-2 reanalysis, assimilating satellite and ground-based observations globally.

#figure(
  block(
    fill: white,
    stroke: 0.5pt + gray-3,
    width: 100%,
    clip: true,
  )[
    #set text(size: 9.5pt, font: "Ubuntu Sans")
    #table(
      columns: (2fr, 2.5fr, 1fr, 1.5fr),
      fill: thead-fill,
      inset: (x: 10pt, y: 7pt),
      text(fill: charcoal, weight: "bold")[Code],
      text(fill: charcoal, weight: "bold")[Description],
      text(fill: charcoal, weight: "bold")[Unit],
      text(fill: charcoal, weight: "bold")[Coverage],
      [T2M], [Air temperature at 2 m], [degC], [1981+],
      [T2M_MAX], [Monthly maximum of hourly 2 m temperature], [degC], [1981+],
      [T2M_MIN], [Monthly minimum of hourly 2 m temperature], [degC], [1981+],
      [RH2M], [Relative humidity at 2 m], [%], [1981+],
      [EVLAND], [Evaporation over land], [mm/day], [1981+],
      [WS10M], [Wind speed at 10 m], [m/s], [1981+],
    )
  ],
  caption: [NASA POWER parameters. All confirmed working against live API as of November 2026.],
)

Annual values are means of the twelve calendar months; a year is used only if complete,
and the series is trimmed to consecutive years so that one step is always one year.
For satellite products with missing months, each year is estimated from an additive
year-plus-calendar-month model so that a missing month does not shift the annual value.
Diurnal temperature range uses POWER's `T2M_RANGE`, because monthly `T2M_MAX` and
`T2M_MIN` are the extreme hourly values of the month, not means of daily extremes.

== NASA GES DISC GPM IMERG

Precipitation is sourced from the Global Precipitation Measurement (GPM) IMERG
Final Run V07B, Level 3 monthly product, accessed via NASA GES DISC OPeNDAP.
Coverage begins June 2000 (operationally from 2001 for complete years). Requires
NASA Earthdata URS authentication. First fetch for a location takes approximately
170 seconds for 24 years; results are cached to disk.

== NASA AppEEARS (MODIS LST and ET)

Land surface temperature (LST) and evapotranspiration (ET) are extracted from MODIS
satellite composites via NASA AppEEARS (Application for Extracting and Exploring
Analysis Ready Samples). Products used:

- MOD11A2.061: LST\_Day\_1km, 8-day composites at 1 km, 2001-present (Wan et al., 2021)
- MOD16A2.061: ET\_500m, 8-day composites at 500 m, 2001-present (Running et al., 2021)

AppEEARS is an asynchronous task API (submit, poll, download CSV). First task
submission takes 2-10 minutes; Tidemark caches the task ID across process restarts
and the final result to disk. Requires NASA Earthdata URS authentication.

// ============================================================
// 4. STATISTICAL METHODS
// ============================================================

= Statistical Methods <s-stats>

== The Significance Test <s-mk>

Tidemark's verdict comes from a Mann-Kendall test whose null distribution is built
from the series itself (an AR(1) sieve bootstrap [18]):

+ Remove the Sen-slope line from the series.
+ Fit a first-order autoregression to the residuals. The lag-1 coefficient $phi$
  is corrected for its small-sample bias by adding $(1 + 4 phi) slash n$.
+ Resample the innovations with replacement and rebuild 1,999 trend-free series
  with the same persistence and the same innovation distribution, skew included.
+ Compute $S$ for each. The two-sided p-value is the share of bootstrap $|S|$ values
  at least as large as the observed $|S|$.

The reported Z-score uses the bootstrap variance of $S$ with the usual continuity
correction.

We adopted this test after measuring the alternatives. Each test was run on simulated
series with no trend, where a correct test rejects 5% of the time:

#figure(
  block(
    fill: white,
    stroke: 0.5pt + gray-3,
    width: 100%,
    clip: true,
  )[
    #set text(size: 9.5pt, font: "Ubuntu Sans")
    #table(
      columns: (2fr, 1.3fr, 1.7fr),
      fill: thead-fill,
      inset: (x: 10pt, y: 7pt),
      text(fill: charcoal, weight: "bold")[Noise],
      text(fill: charcoal, weight: "bold")[Bootstrap test],
      text(fill: charcoal, weight: "bold")[Earlier automatic selection],
      [Independent Gaussian], [6.4%], [6.8%],
      [Skewed (gamma)], [6.6%], [8.8%],
      [AR(1), phi = 0.3], [6.8%], [11.8%],
      [AR(1), phi = 0.6], [6.2%], [16.2%],
      [Skewed AR(1), phi = 0.2], [7.6%], [14.4%],
    )
  ],
  caption: [Rejection rate at a nominal 5% on simulated trend-free series, n = 45, 500 series per row.],
)

The bootstrap test is not exact. In a separate run its rejection rate was about 11%
for $n = 20$ with $phi = 0.6$, and for $phi = 0.8$ at $n = 45$, because $phi$ itself is
poorly estimated for short or very persistent series. Its power is close to the
earlier selection for independent and skewed noise (45% against 46%, and 71% against
73%, in our tests) and lower for autocorrelated noise (37% against 57% at
$phi = 0.5$), where the earlier figure was inflated by the higher false-alarm rate.

The Hamed-Rao test (pymannkendall [6], lag = 3), MKC3 (Section 4.6) and the block
bootstrap of Önöz and Bayazit [21] are still computed, and the one the earlier rule
would have selected is reported next to the verdict as a comparison.

The output reports: trend direction, Kendall's $tau$, the Z-score, the two-tailed
p-value, and Sen's slope.

== Sen's Slope Estimator <s-sens>

Sen's slope [5] is the nonparametric estimator of the linear trend rate:

$ hat(beta) = "median"_(k < j) frac(x_j - x_k, j - k) $ <eq:sens>

For $n$ annual observations, this requires $binom(n, 2) = n(n-1) slash 2$ pairwise
slope computations. For $n = 45$, this is 990 pairwise comparisons. Sen's slope is
resistant to outliers and makes no distributional assumption, making it preferable to
the OLS slope for hydroclimatic series [3].

Tidemark displays $hat(beta)$ on the *trend* output line in units of
(variable unit) per year.

== The Detection Floor <s-floor>

The detection floor $beta_"min"$ is the minimum trend magnitude that Mann-Kendall can
detect at 80% power given the current record length $n$ and noise standard deviation
$sigma_N$. Derived from the analytical $n^(3/2)$ Z-score growth formula (see Section 4.4):

$ beta_"min" = frac(9.93 dot.op sigma_N, n^(3 slash 2)) $ <eq:floor>

The constant 9.93 comes from $z_"crit" slash C$ where $z_"crit" = z_(alpha slash 2) +
z_(1-beta) = 1.96 + 0.84 = 2.80$ and $C = 1 slash (2 sqrt(pi)) approx 0.282$ is the
coefficient in $E[Z] = C dot.op (beta slash sigma) dot.op n^(3 slash 2)$ (derived below),
giving $2.80 slash 0.282 = 9.93$.

The detection floor decreases as $n^{-3/2}$. Extending the record from $n = 45$ to
$n = 60$ years reduces the floor by a factor of $(60 slash 45)^(3 slash 2) approx 1.54$,
a 39% reduction in the minimum detectable slope. This is the most direct quantitative
argument for why longer monitoring records matter.

Tidemark always prints the floor alongside the floor ratio $|hat(beta)| slash beta_"min"$:

- Ratio $< 1.0$: the observed trend is weaker than the detection floor. The current
  record cannot resolve this signal even if the underlying trend is real.
- Ratio $> 1.0$: the trend exceeds the detection threshold. The value reports how many
  times above detection sensitivity the trend sits.

The second case, slope below the floor, is the most valuable output the tool produces.
It converts "not yet significant" from an ambiguous result into a precise statement:
the signal is too weak for the current instrument (45 years of annual data).

== Four Independent Estimation Methods <s-three>

For series with $p > 0.05$, Tidemark computes four independent estimates of the year
the p-value will cross 0.05. Running four independent methods serves as cross-validation:
agreement between methods validates the estimate, while divergence reveals invalid
distributional assumptions.

=== Analytical MK Formula

For a time series $Y_t = omega dot.op t + epsilon_t$ with $epsilon_t$ i.i.d. Gaussian
noise with variance $sigma^2$, the expected value of the Mann-Kendall Z-score grows
as $n^(3 slash 2)$. The derivation proceeds from the pairwise comparison structure of
the test statistic:

For any pair $(i, j)$ with $i < j$:
$ P(x_j > x_i) = Phi lr((frac(beta(j-i), sigma sqrt(2)))) $

For small signal-to-noise ratio $beta / sigma$, linearizing $Phi$ around zero with
$delta = beta(j-i) slash (sigma sqrt(2))$ then substituting:
$ E["sgn"(x_j - x_i)] approx beta(j-i) / (sigma sqrt(pi)) $

Summing over all $binom(n, 2)$ pairs:
$ E[S] approx (beta / sigma) dot.op n^3 / (6 sqrt(pi)) $

Combined with $sqrt{"Var"(S)} approx n^(3/2) / 3$ for large $n$:

$ E[Z] approx frac(beta, sigma) dot.op frac(n^(3/2), 2 sqrt(pi)) approx 0.282 dot.op frac(beta, sigma) dot.op n^(3/2) $ <eq:z-growth>

Note: an earlier version of this derivation used $C = 1 slash sqrt(2 pi) approx 0.399$
(the sign error propagated from skipping the $delta = beta(j-i) slash (sigma sqrt(2))$
substitution). This does *not* affect the crossing formula: $Z_0$ is the observed
z-score from real data, and $C$ cancels in the ratio $z_"target" slash Z_0$.

This $n^(3/2)$ growth rate matches the asymptotic relative efficiency of Mann-Kendall
versus OLS ($3 slash pi approx 0.955$ for Gaussian data). Setting the expected Z-score
equal to $z_"crit" = 1.96$ and solving for the target series length:

$ n_"target" = n_0 dot.op lr((frac(1.96, |Z_0|)))^(2 slash 3) $ <eq:crossing>

Additional years needed: $Delta n = n_0 dot.op [(1.96 slash |Z_0|)^(2/3) - 1]$

Crossing year $= y_"last" + ceil(Delta n)$.

This follows directly from the structure of the Mann-Kendall test; we have not found
it stated in this form elsewhere. It needs no simulation.

It assumes Gaussian i.i.d. noise. For non-Gaussian residuals (skewed precipitation),
it can be badly off in either direction. The divergence check flags this.

=== Weatherhead (1998) Detection Time

Applying the Weatherhead et al. (1998) formula [4] directly with
Sen's slope as the trend estimate:

$ n^* = lr((frac(3.3 sigma_N, |hat(beta)|))^(2 slash 3)) dot.op lr((frac(1 + phi, 1 - phi))^(1 slash 3)) $ <eq:weatherhead2>

The first factor is the base detection time under independent noise. The second factor
is the autocorrelation correction. Worked examples of the correction:

#figure(
  block(
    fill: white,
    stroke: 0.5pt + gray-3,
    width: 85%,
    clip: true,
  )[
    #set text(size: 9.5pt, font: "Ubuntu Sans")
    #table(
      columns: (1fr, 1fr, 1fr),
      fill: thead-fill,
      inset: (x: 10pt, y: 7pt),
      text(fill: charcoal, weight: "bold")[phi (lag-1 ACF)],
      text(fill: charcoal, weight: "bold")[Correction factor],
      text(fill: charcoal, weight: "bold")[Additional years (%)],
      [0.0], [1.000], [0%],
      [0.2], [1.145], [+14.5%],
      [0.3], [1.229], [+23.0%],
      [0.5], [1.442], [+44.2%],
    )
  ],
  caption: [Weatherhead autocorrelation correction factors for representative lag-1 ACF values.],
)

For $phi = 0$ the formula simplifies to $(3.3 sigma_N slash |omega|)^(2 slash 3)$.

The Weatherhead formula is derived for OLS regression. Applying it with Sen's slope is
an approximation, valid because OLS slope and Sen's slope are close for data without
extreme outliers, and the autocorrelation structure of residuals is the same regardless
of which estimator was used.

=== Monte Carlo Simulation

The simulation extends the observed series 80 years into the future, 1,000 times:

```
1. Fit AR(1) to the residuals about the Sen-slope line (the same fit as
   the significance test).
2. For each of 1,000 paths:
   a. Draw a slope from its sampling distribution: the observed Sen slope
      plus its standard error (inflated for autocorrelation) times a
      Student-t draw.
   b. Extend the series year by year: trend line plus AR(1) noise that
      continues from the last observed residual, with innovations
      resampled from the data.
   c. Each year, test the extended series with the Mann-Kendall statistic
      and the variance correction that the verdict applied to the
      observed series.
   d. A crossing is the first year that starts three consecutive
      significant years in the direction of the observed trend.
3. Paths that never cross within 80 years are kept as "never".
4. Crossing year = median over all 1,000 paths; 85% predictive interval =
   7.5th to 92.5th percentile. Either is reported as "beyond the horizon"
   when it falls among the paths that never cross.
```

Four design points matter. The test inside the simulation is the same one that gave
the verdict, so a series cannot "cross" merely because the simulation uses a more
permissive test. The noise keeps the autocorrelation and skew of the data. The slope
is drawn rather than fixed, so the interval reflects how uncertain the slope is. And
paths that never cross are counted, so the median is not taken over the successful
paths only.

The interval is a *predictive interval*, not a confidence interval, and it is
conditional on a trend of roughly the observed size existing. If there is in truth no
trend, the simulation still reports that many paths cross: in our tests on trend-free
series about 65% of paths crossed within 80 years. The projection is therefore a
statement of the form "if the trend is what the data suggest", which the tool prints
with every trajectory.

We checked the calibration on simulated series with a known slope. The 85% interval
contained the year at which fresh data actually became significant for 88% of series
(24 series each, for independent and for AR(1) noise). The median was "never" for
21 to 25% of them.

=== Cramér-Rao Lower Bound

The Cramér-Rao bound (CRB) gives the theoretical minimum number of years any
unbiased estimator could require to detect a trend of size $hat(beta)$ at significance
level $alpha$, if the noise density were known. Tidemark estimates that density from
the residuals, so the printed value is an estimate of the bound, not a guarantee.

For a linear trend model $Y_t = omega dot.op t + epsilon_t$ with noise density
$f(epsilon)$ having Fisher information $I(f) = integral [f'(x)]^2 / f(x) d x$:

$ n^*_"CRB" = n^*_"Weatherhead" dot.op (I(f) dot.op sigma^2)^(-1/3) $ <eq:crb>

For Gaussian noise, $I(f) = 1/sigma^2$ and the CRB equals the Weatherhead formula
exactly. For skewed noise (precipitation, arid NDVI), Fisher information exceeds
$1/sigma^2$, so the CRB is shorter than Weatherhead --- meaning the theoretical
limit is earlier than the parametric formula suggests.

Tidemark estimates $I(hat(f))$ from the residuals using a Gaussian KDE, then
computes $n^*_"CRB"$ analytically. The estimate is printed alongside the other
three methods in every trajectory table. When the CRB agrees with Monte Carlo but
both are shorter than Weatherhead, the noise distribution is non-Gaussian in a way
that actually helps detection (as often happens with bounded, leptokurtic soil
moisture series).

== Divergence Detection and Diagnosis <s-div>

After computing all four estimates, Tidemark evaluates:

$ "divergence" = max("est"_1, "est"_2, "est"_3, "est"_4) - min("est"_1, "est"_2, "est"_3, "est"_4) $ <eq:divergence>

If divergence exceeds five years, the methods are flagged as diverging. Tidemark
then diagnoses the cause by computing:

- Residual skewness (Pearson's third standardized moment)
- D'Agostino-Pearson normality test p-value
- Lag-1 ACF of residuals

If skewness exceeds 1.0 or the normality test fails at p#h(0.05em)<#h(0.05em)0.05,
the residuals are non-Gaussian. Methods 1 and 2 (Gaussian assumption) are labeled
invalid for the current data. The Monte Carlo estimate is flagged as the trusted result.

This divergence as a diagnostic signal is the key methodological contribution of the
four-method framework. When methods agree, the user has three independent confirmations
from different derivations. When they disagree, the user learns *why* the trend is
hard to confirm: not just that it takes longer, but that the shape of the noise
distribution is the culprit.

== MKC3 Third-Order Cumulant Variance Correction <s-mkc3>

The Hamed-Rao correction uses only second-order statistics, the lag-$k$
autocorrelations. Then and Abdul Halim (2025) [16] add a third-order term intended for
skewed series. With $n slash n_S$ the Hamed-Rao factor of Section 2.2 computed on the
ranks of the Sen-detrended series, and $z_t$ those ranks standardized:

$ Phi_3 = frac(1, n-2) sum_(t=1)^(n-2) z_t z_(t+1) z_(t+2) $ <eq:c3>

$ "Var"_"MKC3"(S) = "Var"(S) dot.op lr((frac(n, n_S) + Phi_3)) $ <eq:var-mkc3>

Because $Phi_3$ is computed on standardized ranks it has no units, so the result does
not depend on the units of the data. (An earlier version of Tidemark used a cumulant
of the raw residuals, which did; this was a defect and has been corrected.) The paper
is ambiguous on whether the cumulant uses ranks or detrended values; Tidemark uses
ranks.

On simulated trend-free data MKC3 rejected about 8% of skewed independent series and
14 to 15% of skewed series with AR(1) $phi = 0.2$ ($n = 30$ to $60$) at a nominal 5%.
Tidemark therefore reports MKC3 as a comparison when $|"skewness"| > 0.5$ and the
residual autocorrelation is low, and does not use it for the verdict. We are not aware
of another open Python implementation.

== Partial Mann-Kendall with ENSO Control <s-pmk>

ENSO (El Niño--Southern Oscillation) explains a substantial share of interannual variability in
tropical precipitation and vegetation. Applied to raw data, the Mann-Kendall test
conflates the anthropogenic trend with ENSO-induced low-frequency variability. A trend
that exists may be missed (ENSO masks it) or spuriously detected (ENSO drives it).

The existing OLS ENSO correction in Tidemark removes the linear ENSO component
parametrically and re-runs the test. Libiseller and Grimvall (2002) [17] derived a
nonparametric alternative that makes no assumption about the form of the ENSO-climate
relationship.

Define $h_k (x) = sum_(j != k) "sgn"(x_k - x_j)$ (the net concordance of observation
$k$ with all others). The rank-based cross-covariance between target series $x$ and
ENSO index $q$ is:

$ sigma_(x q) = frac(1, 3) lr((K_(x q) + sum_k h_k (x) dot.op h_k (q))), quad K_(x q) = sum_(i < j) "sgn"(x_j - x_i) "sgn"(q_j - q_i) $ <eq:sigma-xq>

The partial MK statistic removing the ENSO effect and its variance are:

$ S_"partial" = S_x - frac(sigma_(x q), sigma_(q q)) S_q $ <eq:s-partial>

$ "Var"(S_"partial") = sigma_(x x) - frac(sigma_(x q)^2, sigma_(q q)) $ <eq:var-partial>

$ Z_"partial" = S_"partial" slash sqrt("Var"(S_"partial")) $ <eq:z-partial>

The fraction $sigma_(x q)^2 / (sigma_(x x) dot.op sigma_(q q))$ is printed as "ENSO
explains X% of concordance variance."

Tidemark uses NOAA MEI v2 as the ENSO index $q$, the same data already fetched for
the OLS correction; no additional API calls are made. The partial MK test runs when
ENSO coverage exceeds 80% of the analysis period. The result is interpreted automatically:
if the raw test is not significant but the ENSO-adjusted test is, Tidemark reports
"anthropogenic trend exists, masked by ENSO"; the reverse reads "apparent trend may be
ENSO-driven"; agreement reads "trend robust to ENSO correction."

The regression-based ENSO correction also reports ENSO's share of interannual variance,
defined as the partial $R^2$ of the ENSO index given the linear trend.

== Trend-Break Detection <s-bocpd>

The Mann-Kendall test reports the net trend across the full series. It cannot say
whether the trend changed at some point. Two classical changepoint tools are unsuitable
for trending data: the Pettitt test and mean-shift Bayesian models both take "no change
in level" as their null hypothesis, and a steady trend violates it. An earlier version
of Tidemark used both, and on simulated series with a plain linear trend and no break
they reported a changepoint in more than 99% of cases. Both were replaced.

Tidemark now asks a different question: do two straight lines, split at some year,
fit significantly better than one?

*sup-F test.* For every split year $k$ leaving at least five observations on each
side, with $"RSS"_0$ the residual sum of squares of one line and $"RSS"_1(k)$ that of
two separate lines:

$ F(k) = frac(("RSS"_0 - "RSS"_1(k)) slash 2, "RSS"_1(k) slash (n - 4)), quad "sup" F = max_k F(k) $ <eq:supf>

This is the statistic of Andrews (1993) [19]. Its p-value is obtained by bootstrap:
series are regenerated under "one line plus AR(1) noise" fitted to the data, and the
statistic is recomputed for each. Persistent noise, which resembles a break, is thus
part of the null.

*Bayesian scan.* For each split year the log Bayes factor of two lines against one is

$ "log BF"(k) = log P(x_(1:k)) + log P(x_(k+1:n)) - log P(x_(1:n)) $ <eq:bocpd-bf>

where each $P$ is the closed-form marginal likelihood of a straight-line regression
under a conjugate Normal-Inverse-Gamma prior [20], computed on standardized residuals
of the one-line fit so that units and trend size do not matter. A break is reported
when the maximum exceeds 3.5 and also exceeds the 95th percentile of the same maximum
under the bootstrap null above. A logistic transform of the excess over 3.5 is printed
as a confidence figure, capped at 99%; it is a display scale, not a posterior
probability.

On simulated series ($n = 45$, 400 per case) both detectors reported a break in 1 to
4% of series with a steady trend, including skewed noise and AR(1) noise up to
$phi = 0.6$. Power is moderate for an abrupt step (33 to 44% for a step of 2.5 noise
standard deviations) and higher for a change of slope (56 to 86%), because a step
looks like persistence to the AR(1) null.

After detection, Tidemark fits a line to each segment and reports the slopes before
and after.

Example: Dhaka 2 m air temperature (1981-2025). The sup-F test reports a break in 1997
($p = 0.006$). The Bayesian scan does not flag it. We report both and do not claim a
physical cause.

// ============================================================
// 5. NOVEL CONTRIBUTIONS
// ============================================================

= Novel Contributions <s-novel>

== The Significance Trajectory <s-sigtraj>

The significance trajectory is the central concept of this paper.

#callout[
  *Definition.* Given a time series $X = {x_1, dots, x_n}$ with observed Sen's slope
  $hat(beta) != 0$ and current p-value $p > 0.05$, the *significance trajectory* of
  $X$ is the distribution over future crossing years
  $Y^* = min{y : p("MK on" X ++ [x_(n+1), dots, x_y]) < 0.05}$,
  estimated via Monte Carlo simulation over the empirical residual distribution,
  together with the projected variable state at $Y^*$ and at specified thresholds
  beyond it.
]

#v(0.4em)

The significance trajectory answers three linked questions in a single output block:

+ *When will the trend become statistically undeniable?* The crossing year
  $hat(Y)^* = "median"(Y^*)$ with 85% PI from the Monte Carlo distribution.

+ *What will the variable look like when it crosses?* The projected value at
  $hat(Y)^*$: $hat(x)_(hat(Y)^*) = x_n + (hat(Y)^* - y_"last") dot.op hat(beta)$.

+ *When will the trend cross real-world critical thresholds?* After significance,
  the Sen's slope projection is extended to named thresholds: local warming of
  +1.5 degC relative to the start of the local record, evaporation stress levels, drought
  precipitation deficits. These are printed as milestone lines in the output. Projections
  start from the fitted trend line, not from the last observed year, and the local
  warming figures are not the Paris Agreement targets, which refer to global mean
  temperature.

The relationship between p-value and record length under a consistent trend is
well-understood theoretically, as expressed in the $n^(3/2)$ Z-score growth rate
derived in Section 4.4. What is new is the application of this relationship forward
in time as a forecasting tool, combined with the empirical bootstrap for real noise
distributions, and the four-method cross-validation to expose when the parametric
approximations break down.

The concept has academic precedent in the ozone monitoring literature [4].
We are not aware of a general-purpose tool for hydroclimatic trend analysis that is
accessible to non-specialist users.

== A System View <s-scan>

The challenge asks for an *Earth System* trend detective. Variables are linked:
temperature drives evaporation, evaporation modulates humidity, humidity conditions
precipitation. Tidemark analyses one variable per run; running it across variables
for one location gives a system view. For Dhaka (NASA POWER, 1981-2025):

```
variable        slope               p-value   floor ratio
temperature     -0.021 C/yr         0.037     1.6x
evaporation     +0.028 mm/d/yr      0.004     2.6x
humidity        +0.35 %/yr          0.002     3.2x
wind            -0.013 m/s/yr       < 0.001   2.6x
precipitation   +0.10 mm/d/yr       < 0.001   2.3x
```

All five are significant. An earlier version of Tidemark had a `scan` subcommand
that produced such a table in one command; it has been removed from the CLI, and the
table above was assembled from single-variable runs.

== The Trend E-process <s-arep>

As described in Section 2.4, p-values become invalid under sequential monitoring. An
e-process is the replacement. An earlier version of this section described an "Adaptive
Rank Evidence Process" that plugged the Sen slope, fitted on the tested series, into an
exponential score statistic. That statistic is not an e-process (the plug-in is fitted on the
same data, the intercept was treated as known, and its false-positive rate at the
nominal 5% threshold was 12.2% on IID Gaussian data at $n = 45$). It has been removed.

The current statistic tests $Y_t = a + beta t + sigma e_t$ against $H_0: beta = 0$. The
standardised slope $delta = beta slash sigma$ gets a fixed scale-mixture normal prior,
and the intercept $a$ and scale $sigma$ are integrated out with right-Haar priors. The
result $E_n$ is the likelihood ratio of the maximal invariant under $y -> a + s y$. For
IID Gaussian errors $E[E_n | H_0] = 1$ at every $n$ and $(E_n)$ is a test martingale in
the invariant filtration, so rejecting at $E_n >= 20$ has false-positive rate at most 5%,
also when checked every year. Details and derivation are in `research/stats/arep.md`.

For autocorrelated noise the series is Prais-Winsten whitened with an estimated lag-1
coefficient; this carries no exact guarantee. Simulated false-positive rates at
$E_n >= 20$ ($n = 30, 45, 60$): IID Gaussian $<= 0.2%$, skewed $<= 0.1%$, AR(1)
$phi = 0.3$: $<= 0.9%$, $phi = 0.6$: $<= 2.2%$. The rule is conservative: for a trend that
Mann-Kendall detects about half the time, the e-process fires about 10% of the time.
It is an evidence measure to read next to the p-value, not a more sensitive test.

== MKC3 and Block Bootstrap Implementations <s-novel-mkc3>

Tidemark includes open Python implementations of the MKC3 correction [16] and of the
block bootstrap Mann-Kendall test [21]; we are not aware of earlier ones (R's
`modifiedmk` package provides the block bootstrap). Both are reported as comparisons
next to the verdict. Sections 4.1 and 4.6 give their measured false-alarm rates, which
is why neither decides significance.

For Cairo precipitation (skewness 1.95, residual lag-1 autocorrelation 0.50) the
verdict is $p = 0.75$ and the comparison (block bootstrap) gives $p = 0.74$: the
methods agree that there is no detectable trend.

== Partial Mann-Kendall ENSO Separation <s-novel-pmk>

We are not aware of a live-data climate trend tool that provides a nonparametric ENSO separation test.
Tidemark's partial Mann-Kendall addresses a common question: is this
trend real, or is ENSO driving it? The rank-based construction (Libiseller & Grimvall,
2002) [17] requires no assumption about the form of the ENSO-climate relationship, making
it usable where the coupling is monotonic but not linear. The same ENSO data fetched for the OLS
correction is reused, adding no API calls.

The partial MK output complements the OLS ENSO correction already in Tidemark. When
the two methods agree (both show the ENSO-adjusted trend significant, raw not), the
nonparametric confirmation strengthens the conclusion. The rank-based approach is more
credible than the parametric correction for variables with nonlinear ENSO coupling.

== Trend-Break Detection <s-novel-bocpd>

Most accessible changepoint tools test for a shift in level, which a steady trend
triggers. Tidemark's two detectors (Section 4.8) take a single straight line as the
null, calibrate against autocorrelated noise, and were checked on simulated steady
trends, where they stay at or below the nominal false-alarm rate. The output gives the
detected year, the p-value of the sup-F test, the log Bayes factor, and the slope
before and after. The web interface plots the log Bayes factor for every candidate
year, which shows whether the evidence is concentrated on one year or spread over
several.

// ============================================================
// 6. VALIDATION RESULTS
// ============================================================

= Validation Results <s-valid>

We validate the pipeline against real NASA POWER data for two geographically distinct
locations: Dhaka, Bangladesh (tropical monsoon climate) and Cairo, Egypt (hyper-arid
desert). These two locations stress-test the pipeline at opposite ends of the
hydroclimatic spectrum.

#figure(
  block(
    fill: white,
    stroke: 0.5pt + gray-3,
    width: 100%,
    clip: true,
  )[
    #set text(size: 9.5pt, font: "Ubuntu Sans")
    #table(
      columns: (2fr, 1fr, 1fr, 1fr, 1.2fr, 1.2fr, 1fr),
      fill: thead-fill,
      inset: (x: 7pt, y: 6pt),
      text(fill: charcoal, weight: "bold")[Location / Variable],
      text(fill: charcoal, weight: "bold")[Slope],
      text(fill: charcoal, weight: "bold")[tau],
      text(fill: charcoal, weight: "bold")[Z],
      text(fill: charcoal, weight: "bold")[p-value],
      text(fill: charcoal, weight: "bold")[Status],
      text(fill: charcoal, weight: "bold")[Floor ratio],
      [Dhaka, T2M (degC/yr)],           [-0.021], [-0.361], [-2.06], [0.037], [Significant], [1.57x],
      [Cairo, PRECTOTCORR (mm/d/yr)],   [+0.0009], [+0.07], [+0.34], [0.75],  [Not significant], [0.18x],
    )
  ],
  caption: [Main validation results, NASA POWER 1981-2025 (n = 45 annual observations per location).],
)

== Dhaka Temperature: Significant Trend

The bootstrap Mann-Kendall test finds a significant trend in Dhaka's 2 m air
temperature: $p = 0.037$, $tau = -0.361$, $hat(beta) = -0.021$ deg C/year (downward).
The lag-1 autocorrelation of residuals is $phi = 0.47$. The comparison test (block
bootstrap) gives $p = 0.040$. The floor ratio is 1.57: the slope is 1.57 times the
detection floor. The trend-break test finds a break in 1997 ($p = 0.006$); the
Bayesian scan does not flag one. The partial Mann-Kendall test controlling for ENSO
remains significant ($p = 0.004$), while the regression-corrected series gives
$p = 0.06$, so the result is close to the threshold and should be read that way.

A note on interpretation: a downward temperature trend in Dhaka is not what global
warming narratives would suggest. These are MERRA-2 reanalysis values for a 0.5 degree
grid cell, not station measurements, and regional aerosol effects on South Asian
temperature have been discussed in the literature. Tidemark reports what the data
show; physical interpretation is the analyst's responsibility.

== Cairo Precipitation: Not Significant

Cairo's precipitation shows a weak upward slope ($hat(beta) = +0.0009$ mm/day/year)
with $p = 0.75$. The floor ratio of 0.18 means the slope is less than a fifth of what
a 45-year record can resolve.

#figure(
  block(
    fill: white,
    stroke: 0.5pt + gray-3,
    width: 100%,
    clip: true,
  )[
    #set text(size: 9.5pt, font: "Ubuntu Sans")
    #table(
      columns: (2fr, 2.2fr, 2.5fr),
      fill: thead-fill,
      inset: (x: 10pt, y: 7pt),
      text(fill: charcoal, weight: "bold")[Method],
      text(fill: charcoal, weight: "bold")[Crossing year],
      text(fill: charcoal, weight: "bold")[Assumptions],
      [Analytical MK ($n^(3/2)$ formula)], [2125], [Gaussian, independent noise],
      [Weatherhead (1998)], [2078], [Gaussian, AR(1)],
      [Cramér-Rao bound], [2063], [Estimated noise density],
      [Monte Carlo (1,000 paths)], [Median beyond 2105; 85% interval starts 2042], [AR(1), resampled innovations, slope uncertainty],
    )
  ],
  caption: [Four-method comparison for Cairo precipitation (NASA POWER, 1981-2025).],
)

The estimates span more than sixty years, and in the Monte Carlo simulation 51.5% of
paths never become significant within the 80-year horizon. The residuals are strongly
non-Gaussian (skewness 1.95, normality test $p < 0.001$), as expected for a series
that is near zero in most years. The honest summary is that this record cannot say
when, or whether, a trend will be confirmed. Both break detectors report a change
around 2016 (sup-F $p = 0.011$, log BF = 24), driven by a few wet years late in the
record.

The disagreement between methods is not an error. It is the diagnostic: the standard
formulas assume noise that this series does not have.

// ============================================================
// 7. CASE STUDY: BANGLADESH
// ============================================================

= Case Study: Bangladesh <s-bd>

Bangladesh is a low-elevation deltaic nation formed by the Brahmaputra, Ganges, and
Meghna river systems at the head of the Bay of Bengal. Approximately 10% of its land
area lies below 1 m above sea level. It is classified by the IPCC AR6 as a high-exposure
region for sea level rise, tropical cyclone intensification, and monsoon system change [8].
Its long-term planning framework, the Bangladesh Delta Plan 2100, defines adaptation
milestones at 2030, 2050, and 2100, milestones whose validity depends on how quickly
key climate variables cross statistical detectability thresholds.

Bangladesh is therefore an appropriate test case for the significance trajectory: the
planning horizon is long, the exposure is high, and the question of *when* each variable
becomes statistically confirmed matters for resource allocation across different
time windows.

== Five Variables for Dhaka

Applying Tidemark to five NASA POWER variables for Dhaka (23.81 N, 90.41 E), 1981-2025:

#figure(
  block(
    fill: white,
    stroke: 0.5pt + gray-3,
    width: 100%,
    clip: true,
  )[
    #set text(size: 9.5pt, font: "Ubuntu Sans")
    #table(
      columns: (2fr, 1.4fr, 1fr, 1fr, 1.5fr),
      fill: thead-fill,
      inset: (x: 7pt, y: 6pt),
      text(fill: charcoal, weight: "bold")[Variable],
      text(fill: charcoal, weight: "bold")[Slope],
      text(fill: charcoal, weight: "bold")[p-value],
      text(fill: charcoal, weight: "bold")[Floor ratio],
      text(fill: charcoal, weight: "bold")[Trend break],
      [Temperature (T2M)],           [-0.021 C/yr],     [0.037],   [1.6x], [1997 (p = 0.006)],
      [Evaporation (EVLAND)],        [+0.028 mm/d/yr],  [0.004],   [2.6x], [None],
      [Humidity (RH2M)],             [+0.35 %/yr],      [0.002],   [3.2x], [1997 (p = 0.036)],
      [Wind (WS10M)],                [-0.013 m/s/yr],   [< 0.001], [2.6x], [None],
      [Precipitation (PRECTOTCORR)], [+0.10 mm/d/yr],   [< 0.001], [2.3x], [None],
    )
  ],
  caption: [Trend results for Dhaka, NASA POWER (MERRA-2), 1981-2025, n = 45.],
)

All five variables show a significant trend, each above its detection floor: cooling,
with rising evaporation, humidity and precipitation and falling wind speed. For a
planner this is the first useful statement the tool makes: for these variables at
this location the question is no longer whether a change is detectable but how fast it
is proceeding. Temperature and humidity both show a break in the trend line in 1997.

Three cautions apply. These are reanalysis values for one grid cell of about 55 km,
not station data. Five tests were run, so the chance that at least one is a false
alarm is higher than for a single test, although four of the five p-values are far
below 0.05. And precipitation here is the MERRA-2 corrected product; the CLI routes
precipitation to GPM IMERG, whose record starts in 2001 and is too short to compare
directly.

For locations and variables where the trend is not yet significant, the significance
trajectory supplies the missing piece. Cairo humidity is an example (Appendix A):
$p = 0.22$, with a Monte Carlo median crossing year of 2039 and an 85% interval from
2030 to beyond 2105.

// ============================================================
// 8. DISCUSSION
// ============================================================

= Discussion <s-discuss>

== Comparison to Existing Tools

#figure(
  block(
    fill: white,
    stroke: 0.5pt + gray-3,
    width: 100%,
    clip: true,
  )[
    #set text(size: 9.5pt, font: "Ubuntu Sans")
    #table(
      columns: (1.5fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
      fill: thead-fill,
      inset: (x: 6pt, y: 7pt),
      text(fill: charcoal, weight: "bold")[Tool],
      text(fill: charcoal, weight: "bold")[MK test],
      text(fill: charcoal, weight: "bold")[ACF correction],
      text(fill: charcoal, weight: "bold")[Sen's slope],
      text(fill: charcoal, weight: "bold")[Detection time],
      text(fill: charcoal, weight: "bold")[Trajectory / CI],
      text(fill: charcoal, weight: "bold")[MKC3],
      text(fill: charcoal, weight: "bold")[Partial MK],
      text(fill: charcoal, weight: "bold")[Trend break],
      [NASA Giovanni], [OLS only], [No], [No], [No], [No], [No], [No], [No],
      [NOAA Climate Explorer], [Yes], [No], [Yes], [No], [No], [No], [No], [No],
      [Copernicus CDS Toolbox], [Yes], [Optional], [Yes], [No], [No], [No], [No], [No],
      [*Tidemark*], [*Bootstrap MK*], [*Yes*], [*Yes*], [*Yes (4-method)*], [*Yes*], [*Yes (comparison)*], [*Yes*], [*Yes (two-line)*],
    )
  ],
  caption: [Feature comparison against publicly accessible climate trend analysis tools, based on our reading of each tool's public documentation.],
)

Tidemark is the only tool in this comparison that answers the detection-time question
and provides a significance trajectory with a predictive interval. The four-method
cross-validation and divergence detection are, as far as we know, not offered elsewhere.

== Known Limitations

*Spatial resolution.* POWER data at 0.5 deg x 0.5 deg represents a 55 km x 55 km
grid cell, not a point observation. Local effects such as urban heat islands and
topographic precipitation enhancement are smoothed in the reanalysis product. For
point-scale precision, in situ station data should be used.

*Single-variable independence assumption.* The significance trajectory is computed
independently per variable. Cross-variable interactions (temperature driving
evaporation, evaporation affecting humidity) are not modeled, neither in the tests
nor in the trajectory simulation.

*Constant-slope extrapolation.* The Monte Carlo simulation extends the series assuming
a linear trend continues, with the slope drawn from its sampling uncertainty. If the underlying trend accelerates
or reverses, the crossing-year estimate will be biased accordingly. This is a standard
limitation of linear trend projection.

*Calibration of the tests.* No test here is exact. The bootstrap significance test
rejects 6 to 8% of trend-free series at a nominal 5% for 45-year records and about 11%
for very short or very persistent ones. The Monte Carlo trajectory is conditional on a
trend of about the observed size. The e-process is exact only for independent Gaussian
noise and has low power. All rates quoted in this paper come from simulation with a
few hundred to a few thousand series per case and carry sampling error of one to two
percentage points.

*Multiple testing.* Each variable is tested on its own. When several variables or
locations are examined, some significant results are expected by chance.

*NDVI via ORNL DAAC MODIS.* Vegetation index (NDVI) is now available using the ORNL
DAAC MODIS Web Service (MOD13Q1, 250m, 16-day composites, 2000-present, no authentication).
Coverage begins in 2000 versus 1981 for POWER variables, reducing the available record
to 25 years for NDVI analyses. Groundwater storage anomalies from GRACE remain a planned
future addition and require NASA Earthdata authentication.

// ============================================================
// 9. CONCLUSIONS
// ============================================================

= Conclusions <s-conclude>

We have presented Tidemark, a command-line Earth system trend analysis tool that
introduces the significance trajectory: a principled, probabilistic estimate of when
a climate trend will cross the statistical significance threshold, together with what
the variable will look like when it does and when it will cross critical real-world
thresholds beyond that.

The principal contributions are:

+ The *significance trajectory* with four estimates of the crossing year: the
  analytical $n^(3/2)$ formula, Weatherhead (1998), a Monte Carlo simulation that keeps
  autocorrelation, slope uncertainty and never-crossing paths, and a Cramér-Rao bound
  estimated from the residuals; with a report of when and why they disagree.

+ The *detection floor*, which separates "not significant" from "below what this
  record length can resolve".

+ A *significance test chosen by measurement*: a bootstrap Mann-Kendall test that
  rejects 6 to 8% of trend-free series where our earlier method selection rejected
  7 to 16%.

+ A *trend-break test* with a straight line as its null, replacing changepoint
  detectors that reported a break in over 99% of steady trends.

+ *ENSO separation* by regression and by the partial Mann-Kendall test, and a
  *mixture e-process* for trend that is exact for independent Gaussian noise.

+ Open implementations of the *MKC3* and *block bootstrap* Mann-Kendall variants,
  reported for comparison.

On NASA POWER data, Dhaka shows significant trends in all five variables examined
(temperature $p = 0.037$, with a trend break in 1997), and Cairo precipitation shows
none ($p = 0.75$, 0.18 of the detection floor), with the four trajectory methods
disagreeing by decades. The most important result of the project is methodological:
several of our original statistics did not survive testing against simulated data, and
the ones reported here are those that did, with their measured error rates stated.

The tool is built in Rust (CLI binary and argument parsing) with a Python statistics
engine (pymannkendall, numpy, scipy, requests). Temperature, humidity, wind,
and soil results are reproducible from open NASA POWER data with no authentication.
Precipitation (GPM IMERG) and satellite thermal variables (AppEEARS MODIS) require
a NASA Earthdata account, which is free to create.

#v(1em)
#line(length: 100%, stroke: 0.5pt + gray-3)
#v(0.5em)
#text(size: 9.5pt, fill: gray-6)[
  Developed for the NASA Space Apps Challenge 2026. Data: NASA POWER / GPM IMERG / AppEEARS MODIS / ORNL DAAC NDVI.
]

// ============================================================
// REFERENCES
// ============================================================

= References <s-refs>

#set par(hanging-indent: 1.5em)

#refentry[
  [1] Mann, H.B. (1945). Nonparametric tests against trend. _Econometrica_, 13(3), 245-259.
  doi:10.2307/1907187
]

#refentry[
  [2] Kendall, M.G. (1975). _Rank Correlation Methods_, 4th ed. Charles Griffin, London.
]

#refentry[
  [3] Hamed, K.H. and Rao, A.R. (1998). A modified Mann-Kendall trend test for autocorrelated
  data. _Journal of Hydrology_, 204(1-4), 182-196. doi:10.1016/S0022-1694(97)00125-X
]

#refentry[
  [4] Weatherhead, E.C., Reinsel, G.C., Tiao, G.C., Meng, X.-L., Choi, D., Cheang, W.-K.,
  Keller, T., DeLuisi, J., Wuebbles, D.J., Kerr, J.B., Miller, A.J., Oltmans, S.J., and
  Frederick, J.E. (1998). Factors affecting the detection of trends: Statistical considerations
  and applications to environmental data. _Journal of Geophysical Research: Atmospheres_,
  103(D14), 17149-17161. doi:10.1029/98JD00995
]

#refentry[
  [5] Sen, P.K. (1968). Estimates of the regression coefficient based on Kendall's tau.
  _Journal of the American Statistical Association_, 63(324), 1379-1389.
  doi:10.1080/01621459.1968.10480934
]

#refentry[
  [6] Hussain, M. and Mahmud, I. (2019). pymannkendall: a python package for non parametric
  Mann Kendall family of trend tests. _Journal of Open Source Software_, 4(39), 1556.
  doi:10.21105/joss.01556
]

#refentry[
  [7] Efron, B. (1979). Bootstrap methods: Another look at the jackknife.
  _The Annals of Statistics_, 7(1), 1-26. doi:10.1214/aos/1176344552
]

#refentry[
  [8] IPCC (2021). _Climate Change 2021: The Physical Science Basis_. Contribution of
  Working Group I to the Sixth Assessment Report of the Intergovernmental Panel on
  Climate Change. Cambridge University Press. doi:10.1017/9781009157896
]

#refentry[
  [9] NASA POWER Project (2024). The POWER Data Access Viewer.
  NASA Langley Research Center Atmospheric Science Data Center.
  powerlarc.nasa.gov. Accessed November 2026.
]

#refentry[
  [10] Aker, J. (2026). Be an Earth System Trend Detective. NASA Space Apps
  Challenge 2026. NASA Goddard Space Flight Center.
  spaceappschallenge.org/2026/challenges/be-an-earth-system-trend-detective
]

#refentry[
  [11] Ramdas, A., Grünwald, P., Vovk, V., and Shafer, G. (2023). Game-theoretic statistics
  and safe anytime-valid inference. _Statistical Science_, 38(4), 576-601.
  doi:10.1214/23-STS894
]

#refentry[
  [12] Hajek, J. (1962). Asymptotically most powerful rank-order tests.
  _The Annals of Mathematical Statistics_, 33(3), 1124-1147.
]

#refentry[
  [13] Bickel, P.J. (1982). On adaptive estimation. _The Annals of Statistics_,
  10(3), 647-671. doi:10.1214/aos/1176345863
]

#refentry[
  [14] Didan, K. (2015). MOD13Q1 MODIS/Terra Vegetation Indices 16-Day L3 Global
  250m SIN Grid V006. NASA EOSDIS Land Processes DAAC.
  doi:10.5067/MODIS/MOD13Q1.006. Accessed via ORNL DAAC MODIS Web Service,
  modis.ornl.gov/rst/api/v1/
]

#refentry[
  [15] Yue, S. and Wang, C. (2004). The Mann-Kendall test modified by effective sample
  size to detect trend in serially correlated hydrological series. _Water Resources
  Management_, 18(3), 201-218. doi:10.1023/B:WARM.0000043140.61082.60
]

#refentry[
  [16] Then, Y.J. and Abdul Halim, S. (2025). Modified Mann-Kendall with
  higher-order statistics for trend analysis. _Scientific
  Reports_, 16, 500. doi:10.1038/s41598-025-30034-0
]

#refentry[
  [17] Libiseller, C. and Grimvall, A. (2002). Performance of partial Mann-Kendall tests
  for trend detection in the presence of covariates. _Environmetrics_, 13(1), 71-84.
  doi:10.1002/env.502
]

#refentry[
  [18] Bühlmann, P. (1997). Sieve bootstrap for time series. _Bernoulli_, 3(2), 123-148.
]

#refentry[
  [19] Andrews, D.W.K. (1993). Tests for parameter instability and structural change with
  unknown change point. _Econometrica_, 61(4), 821-856.
]

#refentry[
  [20] Murphy, K.P. (2007). Conjugate Bayesian analysis of the Gaussian distribution.
  Technical report, University of British Columbia.
  cs.ubc.ca/~murphyk/Papers/bayesGauss.pdf
]

#refentry[
  [21] Önöz, B. and Bayazit, M. (2012). Block bootstrap for Mann-Kendall trend test of
  serially dependent data. _Hydrological Processes_, 26(23), 3552-3560.
  doi:10.1002/hyp.8358
]

// ============================================================
// APPENDIX A
// ============================================================

= Appendix: CLI Usage and Output Format <appendix-a>

== Installation

```
# From source (requires Rust and Python 3.11+)
cargo install --path .

# Python statistics engine dependencies
pip install pymannkendall numpy scipy requests flask
```

== Analyze a Single Variable

Output of the current version (abbreviated; seasonal and ENSO blocks omitted):

```
$ tidemark analyze --location dhaka --var temperature

location    Dhaka, Bangladesh  (23.81 N, 90.41 E)
variable    temperature (T2M, C)
period      1981 - 2025  (45 years)
test        Mann-Kendall, AR(1) sieve bootstrap

trend       -0.0211 C / year
direction   downward
tau         -0.36
z-score     -2.06
p-value     0.0365   significant (p < 0.05)
e-process   E_n = 4.8   threshold: 20   (iid-Gaussian null, level 0.05)

trend test (raw)        z = -2.06   p = 0.0365    significant
trend test (ENSO-adj)   z = -2.87   p = 0.00417   significant

ENSO explains 12% of concordance variance
interpretation: trend robust to ENSO correction
detection floor         +-0.0134 C / year   (slope is 1.6x above floor)
changepoint 1997   (sup-F break test p=0.005)
```

== Analyze a Not-Yet-Significant Variable

```
$ tidemark analyze --location cairo --var humidity

location    Cairo, Egypt  (30.06 N, 31.25 E)
variable    humidity (RH2M, %)
period      1981 - 2025  (45 years)
test        Mann-Kendall, AR(1) sieve bootstrap

trend       +0.0388 % / year
direction   upward
tau         0.19
z-score     1.27
p-value     0.215   not yet significant (p > 0.05)
detection floor         +-0.0532 % / year   (slope is 0.7x floor, weak signal)

significance trajectory:
  analytical MK     2041
  Weatherhead 1998  2025
  Monte Carlo       2039
  CRB lower bound   2025
  methods diverge: 16 years
  reason: residual skewness=-0.58, normality p=0.037, non-Gaussian noise
  85% PI            2030 - beyond 2105
  note   862/1000 simulations become significant within 80 years
  note   projection assumes observed trend continues at measured rate -- not a forecast
```

The Monte Carlo figures change by a year or two between runs because the simulation
is not seeded.

== Variable Aliases

```
rainfall, rain, precip, precipitation  -> PRECTOTCORR   (mm/day)   GES DISC GPM, 2001+
temperature, temp                      -> T2M           (C)        POWER, 1981+
max-temperature, max-temp, tmax        -> T2M_MAX       (C)        POWER, 1981+
min-temperature, min-temp, tmin        -> T2M_MIN       (C)        POWER, 1981+
humidity, rh                           -> RH2M          (%)        POWER, 1981+
evaporation, evap                      -> EVLAND        (mm/day)   POWER, 1981+
wind, wind-speed                       -> WS10M         (m/s)      POWER, 1981+
lst, land-surface-temperature          -> LST           (C)        AppEEARS MODIS, 2001+
et, evapotranspiration-modis           -> ET_MOD16      (mm/day)   AppEEARS MODIS, 2001+
```

Precipitation, LST, and ET require NASA Earthdata credentials
(`NASA_EARTHDATA_USERNAME` and `NASA_EARTHDATA_PASSWORD` environment variables).

// ============================================================
// APPENDIX B
// ============================================================

= Appendix: Reproducibility Checklist <appendix-b>

The results in Sections 6 and 7 use NASA POWER data and need no account. Products from
GPM IMERG, AppEEARS and LAADS require NASA Earthdata credentials. The CLI routes
`--var rainfall` to GPM IMERG; the POWER precipitation results in this paper were
obtained by running the same analysis on the POWER `PRECTOTCORR` series.

== Software Versions

```
Rust 1.82+
Python 3.11+
pymannkendall 1.4.3
numpy 2.2
scipy 1.15
```

== Reproduce Dhaka Temperature Result

```
python python/analyze.py --lat 23.81 --lon 90.41 --var T2M --start 1981 --end 2025
```

Expected JSON output (abbreviated):
```json
{
  "slope": -0.0211,
  "tau": -0.361,
  "z_score": -2.06,
  "p_value": 0.0365,
  "significant": true,
  "method": "Mann-Kendall, AR(1) sieve bootstrap",
  "phi": 0.47,
  "floor_ratio": 1.57,
  "changepoint": {"detected": true, "year": 1997, "p": 0.0055}
}
```

== Reproducibility Checklist

- Code publicly available on GitHub (github.com/raiyanruhan/tidemark)
- Data sources documented with API endpoint and parameters
- Software versions specified above
- POWER variables need no API key or registration
- Bootstrap tests use a fixed random seed, so p-values are repeatable. The Monte Carlo
  trajectory is not seeded; its median and interval vary by a year or two between runs
- Results confirmed against the live POWER API in November 2026; later reprocessing of
  MERRA-2 may change the values slightly
- Simulation figures (false-alarm rates, power, interval coverage) were produced with
  ad hoc scripts during development and are not yet part of the repository

#v(1.2cm)
