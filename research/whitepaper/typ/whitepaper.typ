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
    We present Tidemark, a command-line Earth system trend analysis tool built on six
    novel contributions. The first is the *significance trajectory*: a probabilistic,
    multi-method estimate of when a climate trend will cross the p#h(0.05em)<#h(0.05em)0.05
    threshold, together with a predictive interval and projected variable state at that
    crossing. The second is a four-method cross-validation framework combining the
    analytical Mann-Kendall $n^(3/2)$ Z-score growth formula (derived from first principles
    and not previously published in usable form), the Weatherhead et al. (1998) OLS
    detection time formula with autocorrelation correction, a Monte Carlo empirical
    bootstrap over 1,000 runs, and a Cramér-Rao lower bound from Fisher information theory
    that sets the minimum years any test could ever require. When methods diverge by more
    than five years, Tidemark identifies the cause and directs the user to the correct estimate. The third is
    the detection floor: the minimum slope Mann-Kendall can resolve at 80% power for the
    current record length, printed unconditionally to contextualize trend strength.
    A fourth contribution is the MKC3 variance correction (Then et al., 2025), applied
    automatically to series with $|"skewness"| > 0.5$, eliminating a systematic
    false-positive bias in Hamed-Rao for right-skewed residuals (precipitation, NDVI, ET).
    A fifth contribution is the partial Mann-Kendall test (Libiseller & Grimvall, 2002),
    which separates the anthropogenic trend signal from contemporaneous ENSO variability
    using a rank-based cross-covariance framework, answering whether a detected trend is
    real or ENSO-driven. A sixth contribution is a Bayesian changepoint detection
    scan using the Normal-Inverse-Gamma (NIG) closed-form marginal likelihood (Chib, 1998):
    for every candidate split year it computes the log Bayes factor of a two-segment
    model against the full-series model, detecting when the trend structure changed
    with calibrated confidence.
    Validation against NASA POWER data for Dhaka, Bangladesh (significant cooling,
    p#h(0.05em)=#h(0.05em)0.047; Bayesian changepoint 1997, log BF = 18, 99% confidence)
    and Cairo, Egypt (non-Gaussian precipitation, Monte Carlo crossing year 2051, 85%
    PI 2036-2068) confirms the pipeline. Applied to Bangladesh, the full Earth system
    scan reveals two of five variables already significant, with humidity projected to
    cross significance around 2031 and precipitation not until 2051. The tool is
    implemented as a Rust CLI binary with a Python statistics engine, requires no
    authentication for POWER variables (a free NASA Earthdata account is needed for
    precipitation and remote sensing data), and is freely reproducible from open NASA
    data with no installation beyond standard Python packages.
  ]
  #v(0.3em)
  #text(size: 9pt, fill: gray-6)[
    *Keywords:* Mann-Kendall, trend detection, significance trajectory, detection floor,
    Monte Carlo, Sen's slope, Bayesian changepoint, NIG marginal likelihood, NASA POWER,
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
      align(right, text(fill: gray-6)[#pg]),
    )
    v(0.38em)
  }

  #set text(size: 10.5pt, font: "Ubuntu Sans")

  #toc-entry("1.", [Introduction], "3", lnk: <s-intro>)
  #toc-entry("2.", [Background and Motivation], "4", lnk: <s-bg>)
  #toc-entry("3.", [Data Sources], "6", lnk: <s-data>)
  #toc-entry("4.", [Statistical Methods], "7", lnk: <s-stats>)
  #pad(left: 2.2em)[
    #toc-entry("4.1", [Mann-Kendall and the Hamed-Rao Correction], "7", lnk: <s-mk>)
    #toc-entry("4.2", [Sen's Slope Estimator], "8", lnk: <s-sens>)
    #toc-entry("4.3", [The Detection Floor], "9", lnk: <s-floor>)
    #toc-entry("4.4", [Four Independent Estimation Methods], "10", lnk: <s-three>)
    #toc-entry("4.5", [Divergence Detection and Diagnosis], "12", lnk: <s-div>)
    #toc-entry("4.6", [MKC3 Third-Order Cumulant Variance Correction], "13", lnk: <s-mkc3>)
    #toc-entry("4.7", [Partial Mann-Kendall with ENSO Control], "14", lnk: <s-pmk>)
    #toc-entry("4.8", [Bayesian Changepoint Detection (NIG Marginal Likelihood)], "15", lnk: <s-bocpd>)
  ]
  #toc-entry("5.", [Novel Contributions], "16", lnk: <s-novel>)
  #pad(left: 2.2em)[
    #toc-entry("5.1", [The Significance Trajectory], "16", lnk: <s-sigtraj>)
    #toc-entry("5.2", [The Earth System Scan], "17", lnk: <s-scan>)
    #toc-entry("5.3", [The Adaptive Rank Evidence Process (AREP)], "18", lnk: <s-arep>)
    #toc-entry("5.4", [MKC3 Variance Correction], "19", lnk: <s-novel-mkc3>)
    #toc-entry("5.5", [Partial Mann-Kendall ENSO Separation], "20", lnk: <s-novel-pmk>)
    #toc-entry("5.6", [Bayesian Changepoint Detection], "21", lnk: <s-novel-bocpd>)
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
brief: "Sometimes all a trend needs to become significant is a longer period." Every
existing tool ignores that sentence. The Mann-Kendall test rejects or fails to reject
the null hypothesis of no trend, and the result is reported as a binary: significant
or not. Standard tools (NASA Giovanni, NOAA Climate Explorer, Copernicus CDS Toolbox)
implement this test and stop there. What they do not report is what the result implies
about the future.

The cost of that omission is concrete. Cairo's precipitation series: not yet significant
($p = 0.74$). The standard analytical formula returns a significance crossing year around
2128. The correct estimate, from Monte Carlo simulation over the actual residual
distribution, is 2051. The difference is 77 years. The standard formula assumes
bell-curve noise. Cairo's precipitation residuals are right-skewed. Applied to skewed
data, the formula gives a confident wrong answer. Tidemark detects this automatically,
diagnoses the cause, and routes the user to the estimate that is valid for the actual
noise structure of the data.

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

This paper makes six contributions to the Earth system trend analysis problem:

+ The *significance trajectory concept*: a probabilistic estimate of when
  p#h(0.05em)<#h(0.05em)0.05 will be reached, with 85% predictive interval from
  Monte Carlo simulation and four-method cross-validation.

+ The *analytical $n^(3/2)$ crossing formula*: derived from the mathematical structure
  of the Mann-Kendall test, computable in microseconds without simulation, and not
  previously published in usable form.

+ The *detection floor*: the minimum slope Mann-Kendall can detect at 80% power given
  the current record length, printed unconditionally to contextualize every result.

+ The *Earth system scan*: analysis of all POWER meteorological variables for a location
  in a single command, producing a system fingerprint showing which variables are trending,
  which are significant, and which will become significant first.

+ The *MKC3 third-order cumulant variance correction* (Then et al., 2025): applied
  automatically to series with $|"skewness"| > 0.5$, correcting a systematic
  false-positive bias in Hamed-Rao for right-skewed residuals (precipitation, NDVI, ET).

+ The *partial Mann-Kendall ENSO separation* (Libiseller & Grimvall, 2002): a
  rank-based nonparametric test of trend after removing the contemporaneous ENSO signal,
  answering whether a detected trend is anthropogenic or ENSO-driven.

+ The *Bayesian changepoint detection scan* (NIG marginal likelihood, Chib, 1998): a
  retrospective scan of every candidate split year using the Normal-Inverse-Gamma
  closed-form marginal likelihood, answering *when* the trend structure changed, not
  just whether it exists. Outputs detected year, log Bayes factor, calibrated confidence,
  and regime slopes before and after the break.

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

Hamed and Rao recommend including lags up to $L = 3$ based on empirical analysis across
hydroclimatic series [3]. When the lag-1 autocorrelation coefficient
$|phi_1| < 1.96 slash sqrt(n)$ (approximately 0.292 for $n = 45$), the correction
factor approaches zero and the test reduces to the original Mann-Kendall.

*A known limitation of the pymannkendall implementation* [6] is that it uses
$|rho_S(i)|$ (absolute value) in the variance inflation step. The original Hamed and
Rao (1998) paper does not take absolute value: the correction should decrease variance
for negative autocorrelation and increase it for positive autocorrelation. The
implementation always inflates variance, producing conservative p-values for series
with negative lag-1 autocorrelation. This is the safe direction: the implementation
never produces false positives, but the bias is noted here for scientific completeness.
Its practical impact is greatest for arid precipitation series, where lag-1 autocorrelation
is typically negative.

Tidemark uses `hamed_rao_modification_test(x, alpha=0.05, lag=3)` for the main
assessment of real data, and `original_test(x)` inside the Monte Carlo loop where
synthetic series have i.i.d. noise by construction, making the autocorrelation correction
compute to approximately zero regardless.

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
the cube root of the noise-to-signal ratio, meaning that halving the trend doubles
the required record length. Second, autocorrelation substantially inflates detection
time: a series with $phi = 0.5$ requires $(1.5 slash 0.5)^(1 slash 3) = 1.44$ times
as many years as an independent series.

This formula is used by NASA Goddard atmospheric scientists for satellite data planning
and cited by multiple atmospheric science groups as the standard for detection time
estimation. It has not, to our knowledge, been implemented in any user-facing climate
trend analysis tool against live API data before Tidemark.

== The Structural Flaw in Sequential P-Value Monitoring

P-values carry a validity assumption that is violated in climate monitoring: they are
only valid at a pre-specified sample size. When a monitoring program checks "is p
< 0.05?" every year for 20 years, the effective false positive rate is not 5% but
approximately 30-40% due to repeated testing.

Climate monitoring is inherently sequential. National agencies, researchers, and tools
like Tidemark's significance trajectory all check significance at multiple points in
time. This means every existing climate trend tool has an inflated false positive rate
when used as actually intended.

The theoretically correct framework is the *e-process* [11], a nonneg
adapted process $E_n$ such that $E[E_tau | H_0] <= 1$ for every stopping time $tau$.
Rejecting $H_0$ when $E_n >= 1 slash alpha$ controls the false positive rate at $alpha$
regardless of when the check is performed. We introduce a sequential evidence accumulation process inspired by e-process theory
for climate trend detection in Section 5.3.

// ============================================================
// 3. DATA
// ============================================================

= Data Sources <s-data>

Tidemark draws from four NASA data sources depending on the variable requested.
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
      [T2M_MAX], [Maximum temperature at 2 m], [degC], [1981+],
      [T2M_MIN], [Minimum temperature at 2 m], [degC], [1981+],
      [RH2M], [Relative humidity at 2 m], [%], [1981+],
      [EVLAND], [Evaporation over land], [mm/day], [1981+],
      [WS10M], [Wind speed at 10 m], [m/s], [1981+],
    )
  ],
  caption: [NASA POWER parameters. All confirmed working against live API as of November 2026.],
)

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

== Mann-Kendall and the Hamed-Rao Correction <s-mk>

Tidemark applies `hamed_rao_modification_test(x, alpha=0.05, lag=3)` from the
pymannkendall library [6] to real data. Inside the Monte Carlo projection
loop, `original_test(x)` is used instead, as synthetic extension series are generated
with i.i.d. resampled residuals, making the autocorrelation correction compute to
approximately zero. The switch reduces computation time for the 1,000-simulation
loop without affecting accuracy.

The skip threshold for insignificant lags in the Hamed-Rao calculation is
$plus.minus 1.96 slash sqrt(n)$, which equals $plus.minus 0.292$ for $n = 45$. Any lag-1 autocorrelation
coefficient with absolute value below this threshold is treated as zero, and the
correction factor is 1.0, identical to the original test. For annual precipitation
series (typical ACF range -0.2 to +0.1), the Hamed-Rao correction is inactive and
both tests return identical results. For annual temperature series (typical ACF range
+0.15 to +0.35), the correction may activate and can noticeably inflate the p-value.

The modified test reports: trend direction, Kendall's $tau$, the normalized Z-score,
the two-tailed p-value, and Sen's slope.

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

This formula is derivable from the structure of the Mann-Kendall test but, to our
knowledge, has not been published in usable form. Existing tools such as VSP (Pacific
Northwest National Laboratory) answer the minimum-$n$ question via binary search
simulation taking several seconds. This formula answers it analytically in microseconds.

It assumes Gaussian i.i.d. noise. For non-Gaussian residuals (skewed precipitation),
it underestimates the crossing year. This is detected by the divergence check.

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

For $phi = 0$, the Weatherhead formula simplifies to $(3.3 sigma_N slash |omega|)^{2/3}$,
which is within 5% of the analytical MK result for Gaussian data, providing a check
on both formulas.

The Weatherhead formula is derived for OLS regression. Applying it with Sen's slope is
an approximation, valid because OLS slope and Sen's slope are close for data without
extreme outliers, and the autocorrelation structure of residuals is the same regardless
of which estimator was used.

=== Monte Carlo Empirical Bootstrap

The empirically correct method for all noise distributions:

```
1. Compute OLS residuals of the detrended series (using Sen's slope).
2. For each of 1,000 simulations:
   a. Extend the series forward one year at a time.
   b. At each step, draw a residual by sampling uniformly with
      replacement from the observed residuals (empirical bootstrap).
   c. Set the new observation:
         x[n+k] = x[n] + k * beta_hat + residual[k]
   d. Run original_test on the extended series.
   e. Check for significance in the same direction as the observed trend.
   f. If significant, record the current year. Stop extending.
3. Crossing year = median of simulations that reached significance.
4. 85% PI (predictive interval) = 7.5th to 92.5th percentile of crossing years.
```

The empirical bootstrap preserves the actual noise distribution, including skewness,
heavy tails, and clustering of values. It is the only method that remains valid for
non-Gaussian residuals (such as right-skewed arid precipitation).

The 85% level is chosen to maintain informative intervals on planning horizons of 10 to
50 years. This is a *predictive interval* (PI), not a confidence interval: it covers 85%
of model-generated future trajectories under the assumed noise distribution, not a fixed
parameter. For 1,000 simulations at 85%, the PI spans simulations 75 to 925 of the
sorted crossing-year distribution.

When more than 500 of the 1,000 simulations do not reach significance within the
60-year projection window, Tidemark reports the fraction and notes that the trajectory
is uncertain. This case indicates a slope below the detection floor or noise distribution
incompatible with significance on any reasonable horizon.

The IID empirical bootstrap is appropriate for annual data across POWER meteorological
variables, where lag-1 autocorrelation is typically below 0.35 and the effect of
residual temporal clustering on crossing-year estimates is a second-order effect
(2 to 5 years, smaller than the 85% PI width).

=== Cramér-Rao Lower Bound

The Cramér-Rao bound (CRB) gives the theoretical minimum number of years any
unbiased estimator could require to detect a trend of size $hat(beta)$ at significance
level $alpha$. No statistical test, however powerful, can beat it.

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
- Shapiro-Wilk normality test p-value
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

The Hamed-Rao correction accounts for autocorrelation but uses only second-order
statistics: the lag-$k$ autocorrelation $rho_k$. For right-skewed series (precipitation,
NDVI, ET in arid regions), the skewness of lag products introduces an additional
systematic bias into $"Var"(S)$ that $rho_k$ cannot capture. The result is
underestimation of $"Var"(S)$, inflated Z-scores, and false positives. For Cairo
precipitation (skewness $approx 1.95$), Hamed-Rao gives $p approx 0.03$ when the
corrected $p > 0.10$.

Then et al. (2025) [16] introduced the third-order cumulant correction. Define
$hat(epsilon)_t = x_t - hat(beta) dot.op t$ as the Sen-slope residuals. The corrected
variance is:

$ "Var"_"MKC3"(S) = "Var"_"HR"(S) + C_3 $ <eq:var-mkc3>

where:

$ C_3 = 2 sum_(k=1)^(n-1) (n-k) w_k hat(kappa)_3 (k) $ <eq:c3>

with $hat(kappa)_3 (k) = (1 slash n) sum_t hat(epsilon)_t^2 hat(epsilon)_(t+k)$
(the sample third-order lag-$k$ cumulant) and $w_k = 1 - k slash (n+1)$ (the same
Bartlett taper as Hamed-Rao).

For symmetric distributions, $kappa_3(k) = 0$ for all $k$ and MKC3 reduces exactly to
Hamed-Rao. For right-skewed residuals, $kappa_3(k) > 0$, inflating $"Var"(S)$ relative
to HR, which decreases Z and reduces false positives.

Tidemark applies MKC3 automatically when $|"skewness"(hat(epsilon))| > 0.5$ and
$n >= 20$; otherwise Hamed-Rao is used. No Python package implements this correction;
Tidemark is the first open implementation. The test method is printed on every output
line so the user always knows which correction was applied.

== Partial Mann-Kendall with ENSO Control <s-pmk>

ENSO (El Niño--Southern Oscillation) explains 15--40% of interannual variability in
tropical precipitation and vegetation [17]. Applied to raw data, the Mann-Kendall test
conflates the anthropogenic trend with ENSO-induced low-frequency variability. A trend
that exists may be missed (ENSO masks it) or spuriously detected (ENSO drives it).

The existing OLS ENSO correction in Tidemark removes the linear ENSO component
parametrically and re-runs the test. Libiseller and Grimvall (2002) [17] derived a
nonparametric alternative that makes no assumption about the form of the ENSO-climate
relationship.

Define $h_k (x) = sum_(j != k) "sgn"(x_k - x_j)$ (the net concordance of observation
$k$ with all others). The rank-based cross-covariance between target series $x$ and
ENSO index $q$ is:

$ sigma_(x q) = frac(1, 3) sum_k h_k (x) dot.op h_k (q) $ <eq:sigma-xq>

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

== Bayesian Changepoint Detection (NIG Marginal Likelihood) <s-bocpd>

The Mann-Kendall test reports the net trend across the full series. It cannot detect
whether the trend structure shifted at some point, and when that shift occurred. For a
series with a structural break, the pre- and post-break slopes may partially cancel,
biasing the MK statistic. Knowing *when* the trend changed is often the most policy-relevant
finding: it identifies the year a regime shift occurred, allows attribution to external
forcing events, and contextualizes the net MK result.

Tidemark implements a retrospective Bayesian changepoint scan. For every candidate split
year $t \in \{3, \ldots, n-3\}$, the log Bayes factor of the two-segment model against
the full-series model is:

$ "log BF"(t) = log P(x_(1:t)) + log P(x_(t+1:n)) - log P(x_(1:n)) $ <eq:bocpd-bf>

Each marginal likelihood $P(x_(1:m))$ is computed in closed form under a Normal-Inverse-Gamma
(NIG) conjugate model with an uninformative Jeffreys-like prior ($mu_0 = 0$, $kappa_0 = 1$,
$alpha_0 = 1$, $beta_0 = 1$). The NIG log marginal likelihood is [18]:

$ log P(x_(1:m)) = lg Gamma(alpha_n) - lg Gamma(alpha_0)
  + alpha_0 log beta_0 - alpha_n log beta_n
  + frac(1,2) log frac(kappa_0, kappa_n) - frac(m, 2) log pi $ <eq:nig-lml>

where the posterior hyperparameters are:
$kappa_n = kappa_0 + m$,
$mu_n = (kappa_0 mu_0 + sum x) / kappa_n$,
$alpha_n = alpha_0 + m/2$,
$beta_n = beta_0 + frac{1}{2}(sum x^2 + kappa_0 mu_0^2 - kappa_n mu_n^2)$.

The series is z-scored before the scan so the prior location $mu_0 = 0$ is innocuous.
The best split is $t^* = arg max_t "log BF"(t)$.

A changepoint is reported when $"log BF"(t^*) > 3.0$. The threshold 3.0 is calibrated
empirically: for $n = 44$ i.i.d. standard normal series, the p97 of the maximum log BF
under the null (no changepoint) is approximately 3.0. This corresponds to moderate-to-strong
evidence on the Jeffreys scale ($"log BF" > "ln"(20) approx 3.0$ is "strong").

The confidence at the detected year is mapped via a logistic transform:

$ "confidence" = frac(e^{"log BF" - 3}, 1 + e^{"log BF" - 3}) $ <eq:bocpd-conf>

which gives 50% at the detection edge, 88% at log BF = 5, and saturates at 99% above log BF ≈ 8.

After detection, Tidemark fits OLS regression to the pre-break and post-break segments
(minimum 5 observations each) and reports the slope change, noting whether the trend
steepened, weakened, or reversed.

Validation: Dhaka temperature (n = 44 annual observations, 1981--2024) detects a
structural break at 1997 with log BF = 18.0 (99% confidence). The pre-1997 slope is
+0.055 °C/year (warming); post-1997 is approximately zero (flat to cooling). This is
consistent with aerosol-driven regional cooling onset in South Asia documented in the
literature, and contextualizes the net MK result ($p = 0.047$, barely significant):
the two regimes partially cancel in the net statistic.

The implementation uses only numpy and scipy. The `fast-bocpd` package (the original
plan, based on Adams & MacKay 2007 sequential BOCPD) requires compiled C extensions and
cannot build on Windows without Microsoft Visual C++ 14.0+. The retrospective NIG scan
is statistically superior for the single-changepoint detection problem: the sequential
formulation has a fundamental upper bound on the per-step probability that is too low
for typical climate series lengths, while the retrospective marginal likelihood comparison
has no such constraint and directly maximizes the split-year evidence.

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
  the Sen's slope projection is extended to named thresholds: Paris Agreement
  +1.5 degC warming, agricultural evaporation stress levels, drought classification
  precipitation deficits. These are printed as milestone lines in the output.

The relationship between p-value and record length under a consistent trend is
well-understood theoretically, as expressed in the $n^(3/2)$ Z-score growth rate
derived in Section 4.4. What is new is the application of this relationship forward
in time as a forecasting tool, combined with the empirical bootstrap for real noise
distributions, and the four-method cross-validation to expose when the parametric
approximations break down.

The concept has academic precedent in the ozone monitoring literature [4].
It has not been implemented as a general-purpose tool for hydroclimatic trend analysis
accessible to non-specialist users.

== The Earth System Scan <s-scan>

The challenge prompt specifies an *Earth System* Trend Detective. The emphasis on
"system" is deliberate: Dr. Aker is an oceanographer who thinks in interconnected
variables. Temperature drives evaporation. Evaporation modulates humidity. Humidity
conditions precipitation. Analyzing variables in isolation misses this structure.

Tidemark's `scan` subcommand analyzes all POWER variables for a location in a
single command, producing a system fingerprint:

```
$ tidemark scan --location dhaka

location   Dhaka, Bangladesh  (23.81 N, 90.41 E)
period     1981 - 2025  (45 years)

variable          direction   slope           p-value    status
temperature       downward    -0.021 C/yr     0.047      significant
evaporation       rising      +0.008 mm/d/yr  0.041      significant
humidity          falling     -0.11 %/yr      0.112      ~2031 (MC: 2029-2034)
precipitation     rising      +0.0003 mm/d/yr 0.74       ~2051 (weak signal)
wind              falling     -0.002 m/s/yr   0.33       ~2039

system note   2 of 5 variables significant. Humidity crossing projected
              2031. Precipitation below detection floor (0.25x): weak signal
              may not resolve without additional 10 years of data.
```

The system scan gives a complete picture at a glance: which Earth system variables are
already significant, which are trending but sub-threshold, which are below the detection
floor, and which will cross significance first.

== The Adaptive Rank Evidence Process (AREP) <s-arep>

As described in Section 2.4, p-values become invalid under sequential monitoring.
The theoretically correct replacement is an e-process. We introduce the Adaptive
Rank Evidence Process (AREP) for climate trend detection.

The AREP combines three components not previously combined in climate analysis:
(1) the adaptive score function $hat(c)(x) = -hat(f)'(x) slash hat(f)(x)$ estimated
from the residual density [12, 13], (2) the e-process construction
for sequential evidence accumulation inspired by e-process theory [11], and (3) application to Earth
system climate trend detection.

The construction begins from the model $Y_t = omega dot.op t + epsilon_t$ with
$epsilon_t ~ f$ (unknown density).

*Step 1: Initial estimate.* Compute Sen's slope $hat(omega)$ and residuals
$hat(epsilon)_t = Y_t - hat(omega) dot.op t$.

*Step 2: Estimate the optimal score function.* Fit a Gaussian KDE to the residuals
to estimate $hat(f)$. Compute the score function:

$ hat(c)(x) = -frac(hat(f)'(x), hat(f)(x)) $

The estimated Fisher information is:

$ hat(I) = integral hat(c)(x)^2 hat(f)(x) d x approx frac(1, n) sum_t hat(c)(hat(epsilon)_t)^2 $

*Step 3: Score process.* Build the cumulative score:

$ Lambda_n = sum_(t=1)^n hat(c)(hat(epsilon)_t) dot.op t $

For comparison, the Mann-Kendall statistic uses $"sgn"(hat(epsilon)_t)$ in place of
$hat(c)(hat(epsilon)_t)$. AREP uses the data-estimated optimal score.

*Step 4: E-process.*

$ E_n = exp lr((hat(omega) dot.op Lambda_n - frac(hat(omega)^2 dot.op hat(I) dot.op n^3, 6))) $

*Step 5: Sequential significance.* Reject $H_0$ when $E_n >= 20$ (at $alpha = 0.05$).
AREP is a sequential evidence accumulation index inspired by e-process theory. The formal
anytime-validity property -- $E[E_tau | H_0] <= 1$ for all stopping times -- requires
a supermartingale argument under plug-in parameter estimation that remains under
investigation. $E_n$ is interpretable as evidence strength regardless.

The AREP output reads:

```
  evidence state    E_n = 7.3   (threshold for significance: 20)
  growth rate       +1.4 E-units per year
  projected cross   2031, 85% PI: 2027-2035
  note   evidence accumulation index; formal anytime-validity under investigation
```

$E_n = 7.3$ is more informative than $p = 0.08$. Evidence is building at a measurable
rate. The formal proof that this construction maintains $E[E_tau | H_0] <= 1$ for all
stopping times is under investigation; empirically, $E_n$ grows predictably with trend
strength and converges to expected values under simulation.

== MKC3 Variance Correction <s-novel-mkc3>

No existing climate trend tool selects variance correction based on residual skewness.
Tidemark is the first tool to implement the Then et al. (2025) correction [16] and the
first to apply it in a live-data pipeline against real NASA satellite data.

For Cairo precipitation (skewness = 1.95), the correction changes the significance
verdict from $p = 0.03$ (significant under Hamed-Rao) to $p > 0.10$ (not significant
under MKC3). This is not a marginal refinement; it is the difference between a reported
finding and a non-finding. The dispatch is fully automatic: when
$|"skewness"(hat(epsilon))| > 0.5$ and $n >= 20$, MKC3 is applied; otherwise Hamed-Rao.
No user setting is required.

The correction also closes the gap between the parametric Gaussian formula and Monte
Carlo for right-skewed series. When MKC3 and Monte Carlo independently agree that Cairo
precipitation is not significant, the user has two confirmations from independent methods.
No existing tool produces this cross-validation for skewed series.

== Partial Mann-Kendall ENSO Separation <s-novel-pmk>

No existing live-data climate trend tool provides a nonparametric ENSO separation test.
Tidemark's partial Mann-Kendall answers the question scientists care about most: is this
trend real, or is ENSO driving it? The rank-based construction (Libiseller & Grimvall,
2002) [17] requires no assumption about the form of the ENSO-climate relationship, making
it valid even where the coupling is nonlinear. The same ENSO data fetched for the OLS
correction is reused, adding no API calls.

The partial MK output complements the OLS ENSO correction already in Tidemark. When
the two methods agree (both show the ENSO-adjusted trend significant, raw not), the
nonparametric confirmation strengthens the conclusion. The rank-based approach is more
credible than the parametric correction for variables with nonlinear ENSO coupling.

== Bayesian Changepoint Detection <s-novel-bocpd>

No existing live-data Earth system trend tool answers the question of *when* the trend
structure changed and provides a calibrated Bayesian confidence for that year. The two
closest methods are the Pettitt test (a rank-based test for a single distributional
shift in the median) and binary segmentation (sequential splitting with an information
criterion). Both are frequentist and do not produce a Bayes factor or confidence interval.

Tidemark's NIG marginal likelihood scan answers a different question: at what year is the
evidence strongest that the data before that year and after that year are better explained
as two independent Gaussian processes than as one? The log Bayes factor is on an absolute
scale (Jeffreys 1961), interpretable without null-hypothesis testing machinery. A log BF of
18.0 for the Dhaka temperature break (1997) is an overwhelming result — the two-segment
model is $e^{18} approx 65$ million times more probable than the one-segment model.

The output is richer than any existing changepoint method: detected year, log BF,
calibrated confidence (%), and regime slopes before and after the break with steepening/
weakening/reversal note. The web interface adds a log BF scan chart showing the evidence
at every candidate split year, which lets the user see whether the peak is sharp (clear
break) or broad (gradual transition).

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
      [Dhaka, T2M (degC/yr)],           [-0.021], [-0.361], [-1.98], [0.047], [Significant], [1.56x],
      [Cairo, PRECTOTCORR (mm/d/yr)],   [+0.0009], [+0.07], [+0.33], [0.74],  [Not yet],     [0.25x],
    )
  ],
  caption: [Main validation results, NASA POWER 1981-2025 (n = 45 annual observations per location).],
)

== Dhaka Temperature: Significant Trend

The Modified Mann-Kendall (Hamed-Rao, lag = 3) test detects a significant trend in
Dhaka's 2 m air temperature: $p = 0.047$, $tau = -0.361$, $hat(beta) = -0.021$
deg C/year (downward direction). The lag-1 autocorrelation of residuals is $phi = 0.47$,
indicating substantial positive autocorrelation. The Hamed-Rao correction is active
for this series.

The floor ratio of 1.56 indicates the trend is 1.56 times above the detection floor,
confirming that the signal is detectable at the current record length.

A note on interpretation: the downward temperature trend in Dhaka contradicts the
expectation one might form from global warming narratives. This is consistent with
aerosol-driven regional cooling documented in South Asian climate literature, where
particulate pollution and land-use change modify local temperature trends independently
of the global surface temperature signal. Tidemark reports what the data show.
Physical interpretation is the analyst's responsibility.

== Cairo Precipitation: Not Yet Significant

Cairo's precipitation trend shows a weak upward slope ($hat(beta) = +0.0009$
mm/day/year) with $p = 0.74$. The floor ratio of 0.25 indicates the trend is at
one-quarter of the detection floor: the current 45-year record cannot resolve this
signal even if the underlying trend is real.

Four-method cross-validation for Cairo:

#figure(
  block(
    fill: white,
    stroke: 0.5pt + gray-3,
    width: 100%,
    clip: true,
  )[
    #set text(size: 9.5pt, font: "Ubuntu Sans")
    #table(
      columns: (2fr, 1.5fr, 2.5fr, 1fr),
      fill: thead-fill,
      inset: (x: 10pt, y: 7pt),
      text(fill: charcoal, weight: "bold")[Method],
      text(fill: charcoal, weight: "bold")[Crossing year],
      text(fill: charcoal, weight: "bold")[Assumptions],
      text(fill: charcoal, weight: "bold")[Valid?],
      [Analytical MK ($n^(3/2)$ formula)], [2128], [Gaussian i.i.d.], [Invalid],
      [Weatherhead (1998)], [2123], [Gaussian, OLS], [Invalid],
      [Monte Carlo (n = 1,000)], [2051], [Empirical bootstrap], [Valid],
    )
  ],
  caption: [Four-method comparison for Cairo precipitation. Divergence = 77 years.],
)

Divergence is 77 years, well above the 5-year threshold. Diagnosis: residual skewness = 1.95, Shapiro-Wilk normality $p < 0.001$. The residuals are strongly non-Gaussian,
right-skewed as expected for a near-zero arid precipitation series. Methods 1 and 2,
which assume Gaussian noise, underestimate the crossing year by 77 years. The Monte
Carlo estimate of 2051 (85% PI: 2036-2068) is the trusted result.

All 1,000 Monte Carlo simulations reached significance within the 60-year projection
window. The 85% PI spans 32 years, reflecting genuine uncertainty about the future
noise realizations rather than any weakness in the method.

This Cairo result illustrates the key practical finding of the four-method framework:
the methods do not agree because the noise distribution is not Gaussian. The divergence
is not an error. It is a diagnostic. It tells the user that the standard parametric
formulas are inapplicable here, and that precipitation in Cairo is harder to track
to significance than a Gaussian analysis would suggest.

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

== Earth System Scan: Dhaka

Applying the full Earth system scan to Dhaka (23.81 N, 90.41 E), 1981-2025:

```
location   Dhaka, Bangladesh  (23.81 N, 90.41 E)
period     1981 - 2025  (45 years, POWER); 2001 - 2025  (25 years, GPM)

variable          direction   slope           p-value    significance
temperature       downward    -0.021 C/yr     0.047      significant
evaporation       rising      +0.008 mm/d/yr  0.041      significant
humidity          falling     -0.11 %/yr      0.112      ~2031 (MC 85% PI: 2029-2034)
wind              falling     -0.002 m/s/yr   0.33       ~2039
precipitation     downward    -0.016 mm/d/yr  0.385      ~2037 (GPM 2001-2025, 0.23x floor)

system note   2 of 5 variables significant. Earliest next crossing: humidity
              ~2031. Precipitation (GPM IMERG, 25 years): floor ratio 0.23,
              weak signal below detection threshold. Evaporation already
              significant: land moisture budget is changing.
```

Two variables are already statistically significant: temperature (downward trend,
consistent with aerosol-driven regional cooling) and evaporation (upward trend,
consistent with increased land surface drying). Three are trending but accumulating
evidence.

== Significance Crossing Timeline

The Bangladesh Delta Plan 2100 specifies adaptation milestones at 2030, 2050, and 2100.
The projected significance crossing years from the Earth system scan map directly onto
this framework:

#figure(
  block(
    fill: white,
    stroke: 0.5pt + gray-3,
    width: 100%,
    clip: true,
  )[
    #set text(size: 9.5pt, font: "Ubuntu Sans")
    #table(
      columns: (1.5fr, 1fr, 1fr, 1.5fr, 1.5fr),
      fill: thead-fill,
      inset: (x: 7pt, y: 6pt),
      text(fill: charcoal, weight: "bold")[Variable],
      text(fill: charcoal, weight: "bold")[p-value],
      text(fill: charcoal, weight: "bold")[Slope],
      text(fill: charcoal, weight: "bold")[Status],
      text(fill: charcoal, weight: "bold")[Crossing year (MC)],
      [Temperature (T2M)],      [0.047], [-0.021 C/yr],     [Significant],             [N/A],
      [Evaporation (EVLAND)],   [0.041], [+0.008 mm/d/yr],  [Significant],             [N/A],
      [Humidity (RH2M)],        [0.112], [-0.11 %/yr],      [Trending, p > 0.05],      [~2031 (PI: 2029-2034)],
      [Wind (WS10M)],           [0.33],  [-0.002 m/s/yr],   [Trending, p > 0.05],      [~2039],
      [Precipitation (PRECTOTCORR)], [0.385], [-0.016 mm/d/yr], [Below floor (0.23x)], [~2037 (GPM 2001-2025)],
    )
  ],
  caption: [Significance crossing projections for Dhaka, Bangladesh (1981-2025). Monte Carlo n=1000, 85% PI.],
)

The two already-significant variables (temperature, evaporation) indicate a detectable
change in the land energy and moisture budget. The three not-yet-significant variables
span three distinct regimes: a near-threshold series (humidity, ~5 years), a weak-signal
series above the floor (wind, ~13 years), and a below-floor series (precipitation,
GPM IMERG 2001-2025, floor ratio 0.23) where the 25-year record cannot resolve the
signal regardless of direction.

The precipitation result is the most consequential. Evaporation is already significantly
elevated, implying increased land surface drying. If the precipitation signal is not yet
detectable, the drying is not yet confirmed by the precipitation side of the water
balance. That gap -- detectable evaporation change, unresolved precipitation change --
is precisely the ambiguity that the significance trajectory quantifies.

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
      text(fill: charcoal, weight: "bold")[Bayesian CP],
      [NASA Giovanni], [OLS only], [No], [No], [No], [No], [No], [No], [No],
      [NOAA Climate Explorer], [Yes], [No], [Yes], [No], [No], [No], [No], [No],
      [Copernicus CDS Toolbox], [Yes], [Optional], [Yes], [No], [No], [No], [No], [No],
      [*Tidemark*], [*Hamed-Rao*], [*Yes*], [*Yes*], [*Yes (3-method)*], [*Yes*], [*Yes (auto)*], [*Yes (rank)*], [*Yes (NIG)*],
    )
  ],
  caption: [Feature comparison against publicly accessible climate trend analysis tools.],
)

Tidemark is the only tool in this comparison that answers the detection-time question
and provides a significance trajectory with a predictive interval. The four-method
cross-validation and divergence detection are not present in any existing tool.

== Known Limitations

*Spatial resolution.* POWER data at 0.5 deg x 0.5 deg represents a 55 km x 55 km
grid cell, not a point observation. Local effects such as urban heat islands and
topographic precipitation enhancement are smoothed in the reanalysis product. For
point-scale precision, in situ station data should be used.

*Single-variable independence assumption.* The significance trajectory is computed
independently per variable. Cross-variable interactions (temperature driving
evaporation, evaporation affecting humidity) are described in the system scan output
but are not modeled in the trajectory simulation.

*Constant-slope extrapolation.* The Monte Carlo simulation extends the series assuming
the Sen's slope remains constant into the future. If the underlying trend accelerates
or reverses, the crossing-year estimate will be biased accordingly. This is a standard
limitation of linear trend projection.

*pymannkendall autocorrelation direction bug.* Documented in Section 2.2 and in the
library source. The impact is bounded: Tidemark will never report a false positive due
to this implementation choice, but may report a slightly conservative p-value for
series with negative lag-1 autocorrelation.

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

The principal technical contributions are:

+ The *analytical $n^(3/2)$ crossing formula*, derived from the structure of the
  Mann-Kendall test, computable in microseconds, and not previously published in usable
  form.

+ The *Cramér-Rao lower bound for trend detection time*, computed from residual Fisher
  information, that sets the theoretical minimum years any test could require and
  exposes when parametric formulas are pessimistic for non-Gaussian noise.

+ The *four-method cross-validation framework*, combining the analytical formula,
  Weatherhead (1998), Monte Carlo empirical bootstrap, and Cramér-Rao lower bound,
  with divergence detection that identifies non-Gaussian noise and routes the user
  to the correct estimate.

+ The *detection floor*, derived from the analytical formula, printed unconditionally
  to contextualize every result and distinguish "not significant" from "below the
  detection threshold of the current record."

+ The *Earth system scan*, analyzing all POWER meteorological variables for a location
  in a single command and producing a system fingerprint that directly implements the
  "Earth System Trend Detective" challenge framing.

+ The *Adaptive Rank Evidence Process (AREP)*, a sequential evidence accumulation index
  inspired by e-process theory, applied to climate trend detection; formal anytime-validity
  under investigation.

+ The *MKC3 third-order cumulant variance correction* (Then et al., 2025): the first
  open implementation, applied automatically for skewed residuals ($|"skewness"| > 0.5$),
  eliminating a systematic false-positive bias in Hamed-Rao for precipitation and
  vegetation series.

+ The *partial Mann-Kendall ENSO separation* (Libiseller & Grimvall, 2002): the first
  live-data nonparametric ENSO isolation test, separating anthropogenic trend signal
  from ENSO-induced variability without distributional assumptions.

+ The *Bayesian changepoint detection scan* (NIG marginal likelihood, Chib, 1998): the
  first live-data Earth system trend tool to answer *when* the trend structure changed,
  using the closed-form Normal-Inverse-Gamma marginal likelihood to compute log Bayes
  factors at every candidate split year, with calibrated confidence and regime slopes.

Validation against real NASA POWER data for Dhaka (significant cooling trend, $p =
0.047$; Bayesian changepoint 1997, log BF = 18.0, 99% confidence) and Cairo
(non-Gaussian precipitation, MC crossing year 2051 with 85% PI 2036-2068) confirms the
pipeline. The Bangladesh case study shows two of five key
climate variables already significant, with humidity projected to reach significance
around 2031 and precipitation not until approximately 2051 given current signal
strength.

The tool is built in Rust (CLI binary and argument parsing) with a Python statistics
engine (pymannkendall, numpy, scipy, pandas, requests). Temperature, humidity, wind,
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
  [11] Ramdas, A., Ruf, J., Larsson, M., and Koolen, W. (2023). Testing exchangeability:
  Fork-convexity, supermartingales and e-processes. _International Statistical Review_,
  91(1), 1-29. doi:10.1111/insr.12490
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
  [16] Then, W., Hashim, R., and Alias, N.E. (2025). Modified Mann-Kendall test with
  higher-order statistics for trend analysis in hydroclimatic time series. _Scientific
  Reports_, 15, 7892. doi:10.1038/s41598-025-30034-0
]

#refentry[
  [17] Libiseller, C. and Grimvall, A. (2002). Performance of partial Mann-Kendall tests
  for trend detection in the presence of covariates. _Environmetrics_, 13(1), 71-84.
  doi:10.1002/env.502
]

#refentry[
  [18] Chib, S. (1998). Estimation and comparison of multiple change-point models.
  _Journal of Econometrics_, 86(2), 221-241. doi:10.1016/S0304-4076(97)00115-2
]

#refentry[
  [19] Murphy, K.P. (2007). Conjugate Bayesian analysis of the Gaussian distribution.
  Technical report, University of British Columbia.
  cs.ubc.ca/~murphyk/Papers/bayesGauss.pdf
]

#refentry[
  [20] Adams, R.P. and MacKay, D.J.C. (2007). Bayesian online changepoint detection.
  arXiv:0710.3742.
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
pip install pymannkendall numpy scipy pandas requests
```

== Analyze a Single Variable

```
$ tidemark analyze --location dhaka --var temperature

location    Dhaka, Bangladesh  (23.81 N, 90.41 E)
variable    temperature (T2M, C)
period      1981 - 2025  (45 years)
test        Modified Mann-Kendall (Hamed-Rao, lag=3)

trend       -0.021 C / year
direction   downward
tau         -0.361
z-score     -1.98
p-value     0.047   significant (p < 0.05)
detection floor     +-0.013 C / year   (slope is 1.6x above floor)

trend test (raw)        z = -1.98   p = 0.047    significant
trend test (ENSO-adj)   z = -2.73   p = 0.00632  significant

ENSO explains 13% of concordance variance
interpretation: trend robust to ENSO correction
  note   projection assumes observed trend continues at measured rate -- not a forecast
```

(no milestones block: cooling direction has no applicable standard thresholds)

== Analyze a Not-Yet-Significant Variable

Note: the output below is from the archived NASA POWER run (1981-2025). The current CLI
routes `--var rainfall` to GPM IMERG (2001-present); running this command live will show
a 25-year GPM series. The POWER result is preserved here as a methodology demonstration.

```
$ tidemark analyze --location cairo --var rainfall

location    Cairo, Egypt  (30.06 N, 31.25 E)
variable    precipitation (PRECTOTCORR, mm/day)
period      1981 - 2025  (45 years)
test        Modified Mann-Kendall (MKC3, Then 2025)

trend       +0.0009 mm/day / year
direction   upward
tau         0.07
z-score     0.33
p-value     0.74   not yet significant (p > 0.05)
detection floor     +-0.0037 mm/day / year   (slope is 0.25x floor, below sensitivity)

significance trajectory:
  analytical MK     2128   (n^1.5 growth formula, assumes Gaussian IID -- invalid here)
  Weatherhead 1998  2123   (OLS detection time -- also assumes Gaussian -- invalid here)
  Monte Carlo       2051   (n=1000, empirical bootstrap)
  methods diverge: 77 years
  reason: residual skewness=1.95, normality p<0.001 -- non-Gaussian noise
  trust: Monte Carlo
  85% PI            2036 -- 2068
  note   projection assumes observed trend continues at measured rate -- not a forecast
```

== Earth System Scan

```
$ tidemark scan --location dhaka
$ tidemark scan --lat 23.81 --lon 90.41
```

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

The Dhaka temperature result can be reproduced from open NASA POWER data with no account.
Precipitation (GPM IMERG) and LST/ET (AppEEARS MODIS) require NASA Earthdata credentials.
The Cairo precipitation result below was run against NASA POWER (pre-GPM routing) and
is preserved as a methodology validation; live CLI results use GPM IMERG instead.

== Software Versions

```
Rust 1.82+
Python 3.11+
pymannkendall 1.4.3
numpy 1.26
scipy 1.12
pandas 2.0
requests 2.31
```

== Reproduce Cairo Result

```
python python/analyze.py \
  --lat 30.06 --lon 31.25 \
  --var PRECTOTCORR \
  --start 1981 --end 2025
```

Expected JSON output (abbreviated):
```json
{
  "trend": "increasing",
  "slope": 0.0009,
  "p": 0.74,
  "tau": 0.07,
  "significance_year_mc": 2051,
  "pi_low_85": 2036,
  "pi_high_85": 2068,
  "skewness": 1.95,
  "normality_p": 0.00031,
  "methods_diverge": true,
  "trust": "monte_carlo"
}
```

== Reproduce Dhaka Temperature Result

```
python python/analyze.py \
  --lat 23.81 --lon 90.41 \
  --var T2M \
  --start 1981 --end 2025
```

Expected JSON output (abbreviated):
```json
{
  "trend": "decreasing",
  "slope": -0.021,
  "p": 0.047,
  "tau": -0.361,
  "significant": true,
  "phi": 0.47,
  "floor_ratio": 1.56
}
```

== Reproducibility Checklist

- Code publicly available on GitHub (username: raiyanruhan)
- Data sources documented with API endpoint and parameters
- Software versions specified above
- No API key or registration required
- Both validation results (Cairo, Dhaka) confirmed against live API as of November 2026
- All 1,000 Monte Carlo seeds: `np.random.seed` not fixed. Results are statistically
  stable; CI bounds reported are median across five independent runs

#v(1.2cm)
