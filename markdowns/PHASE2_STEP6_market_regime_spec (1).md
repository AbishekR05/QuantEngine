# Phase 2 — Step 6 Implementation Spec
## Module: Market Regime Analysis

**Status:** Ready for implementation
**Depends on:** Step 1 (`analyzer.py`), Step 2 (`statistics.py`), Step 3 (`visualizer.py`), Step 5 (`outlier_analysis.py` + `known_events.yaml`) — regime periods should cross-reference known events where they overlap, for consistency with the outlier report's event catalog
**Consumes:** `nifty_features.csv`
**Produces:** `reports/eda/statistics/regime_report.md` + `reports/eda/figures/regime_timeline.png`

This document is a specification, not code. Hand it to your code-generation tool as-is.

---

## 1. Package Structure to Create

```
src/
└── eda/
    ├── __init__.py               (already exists)
    ├── analyzer.py                (already exists — Step 1)
    ├── statistics.py              (already exists — Step 2)
    ├── visualizer.py              (already exists — Step 3)
    ├── correlations.py            (already exists — Step 4)
    ├── outlier_analysis.py        (already exists — Step 5)
    └── regime_analysis.py         ← implement in this step

reports/
└── eda/
    ├── statistics/                 (already exists)
    └── figures/                    (already exists)
```

Only `regime_analysis.py` is implemented in this step. `label_analysis.py` remains out of scope (Step 8).

---

## 2. Module Responsibility

`regime_analysis.py` defines a `RegimeAnalyzer` class that classifies each trading day (or rolling window) into a market regime and produces per-regime statistics. This is descriptive labeling for later model evaluation — **not** a predictive model, and not something the eventual ML phase should treat as a feature unless deliberately decided later (regime labels computed with hindsight, e.g. using a full-history trend, would leak future information if fed into a model naively — see Section 7).

This module does **not**:
- Predict future regimes
- Generate trading signals
- Modify any input data

---

## 3. Regime Definitions

Since "bull/bear/high-vol/low-vol/sideways" aren't single universally-agreed definitions, this spec pins down concrete, config-driven rules rather than leaving them ambiguous:

| Regime | Definition (rule-based, using only same-day-or-earlier data — no lookahead) |
|---|---|
| **Bull Market** | Price is above its rolling `SMA_200` AND rolling N-day return is positive beyond a config threshold |
| **Bear Market** | Price is below its rolling `SMA_200` AND rolling N-day return is negative beyond a config threshold |
| **Sideways Market** | Rolling N-day return magnitude stays within a config-defined "flat" band (e.g. ±5% over ~63 trading days) — regardless of position relative to SMA_200 |
| **High Volatility** | Rolling volatility (reuse the `21-day rolling std of Daily_Return` already computed in Step 3's `plot_rolling_volatility`) exceeds a config percentile threshold (e.g. above 75th percentile of its own historical distribution) |
| **Low Volatility** | Rolling volatility below a config percentile threshold (e.g. below 25th percentile) |

**Important structural note:** Bull/Bear/Sideways describe *trend*, while High/Low Volatility describe a separate *dispersion* dimension. A day can be simultaneously "Bull" and "High Volatility" (e.g. a sharp V-shaped recovery). This module should produce **two independent labels per day** — a trend regime and a volatility regime — not force them into one mutually-exclusive category. Forcing a single label would hide genuinely useful information (e.g. distinguishing a calm bull market from a volatile one matters a lot for position sizing later).

All thresholds (rolling window lengths, return thresholds, percentile cutoffs) must be config-driven, not hardcoded — this is exactly the kind of rule where reasonable practitioners disagree, and you'll likely want to tune it after seeing the first output.

---

## 4. Class Design

### `RegimeAnalyzer`

**Constructor inputs:**
- `data: pd.DataFrame` — `nifty_features.csv`
- `trend_window: int` — from config (e.g. 63 trading days ≈ 1 quarter)
- `trend_threshold: float` — from config (e.g. 0.05 for ±5%)
- `vol_window: int` — from config (reuse Step 3's rolling volatility window, e.g. 21)
- `vol_high_percentile: float` / `vol_low_percentile: float` — from config

**Public methods:**

| Method | Returns | Purpose |
|---|---|---|
| `classify_trend_regime() -> pd.Series` | Series aligned to `Date` | One of `Bull` / `Bear` / `Sideways` per day |
| `classify_volatility_regime() -> pd.Series` | Series aligned to `Date` | One of `High` / `Low` / `Normal` per day |
| `regime_periods(regime_type: str = "trend") -> pd.DataFrame` | DataFrame with `start_date`, `end_date`, `regime`, `duration_days` | Collapses the daily labels into contiguous date ranges (e.g. "Bull: 2020-04-01 to 2021-10-15, 380 days") rather than reporting a label for every single day |
| `regime_statistics(regime_type: str = "trend") -> pd.DataFrame` | DataFrame, one row per regime label | Mean/median return, volatility, and duration statistics computed *within* each regime — reuses `StatisticalAnalyzer` patterns from Step 2 where sensible rather than reinventing stat computation |
| `plot_regime_timeline() -> str` | file path | Price chart with regime periods shown as background color bands (reuse styling conventions from `visualizer.py`) |
| `to_markdown() -> str` | str | Full report |
| `save(output_path: str) -> None` | None | Writes report to disk |

### `generate_regime_report(config: dict) -> None`

Module-level orchestrator, same pattern as prior steps.

---

## 5. Report Content Requirements

1. **Header** — dataset name, generation timestamp, definitions used (state the actual configured thresholds, not just regime names — a reader needs to know what "Bull" means numerically in this report)
2. **Trend regime periods table** — contiguous date ranges per `regime_periods("trend")`, with duration and the price level at start/end of each period
3. **Volatility regime periods table** — same structure for `regime_periods("volatility")`
4. **Per-regime statistics table** — mean return, return std, average duration, count of periods, for each of Bull/Bear/Sideways and High/Low/Normal volatility
5. **Cross-tabulation** — how often each trend regime co-occurs with each volatility regime (e.g. "Bull + High Vol: X days, Bull + Low Vol: Y days...") — this is where the two-dimensional design from Section 3 pays off
6. **Cross-reference to known events (Step 5)** — where a regime period overlaps a `known_events.yaml` entry (e.g. the Bear/High-Vol period overlapping "COVID Crash"), note it explicitly. This connects the regime analysis to the same event catalog the outlier report uses, rather than treating them as disconnected findings.
7. **Regime timeline chart** — price series with shaded background bands per trend regime (reference image)

---

## 6. Config Integration

```yaml
eda:
  regime:
    input_file: "data/features/nifty_features.csv"
    trend_window: 63
    trend_threshold: 0.05
    vol_window: 21
    vol_high_percentile: 0.75
    vol_low_percentile: 0.25
    known_events_path: "config/known_events.yaml"
    output_report_path: "reports/eda/statistics/regime_report.md"
    output_chart_path: "reports/eda/figures/regime_timeline.png"
```

---

## 7. Important Caveat to Document in the Report Itself

Regime labels as defined here are computed using **rolling windows that only look backward** (no future data), so they are safe from lookahead bias in that specific sense. However, a Sideways/Bull/Bear label assigned to *today* using a 63-day trailing window is still, by construction, a description of **recent past behavior**, not a real-time-available "regime call" at the time — e.g. the start of a bear market won't be labeled "Bear" until enough trailing days have accumulated to cross the threshold, meaning regime labels lag actual regime changes. This is fine for *retrospective* analysis (which is this module's whole purpose — understanding how the model would need to have evaluated across different historical conditions) but should **not** be fed into a predictive model as a same-day feature without careful thought about this lag, since doing so naively could still introduce a form of leakage. Include a short paragraph in the report making this explicit, so it isn't silently forgotten by the time Phase 3 (ML) starts.

---

## 8. Edge Cases

- **Start of series (first `trend_window`/`vol_window` days)** — insufficient data for a regime call; label as `Insufficient Data` rather than guessing or defaulting to one regime silently.
- **Regime periods overlapping the known zero-volume era (2007–2013)** — volatility regime classification doesn't depend on `Volume`, so this shouldn't be affected, but worth a one-line confirmation in the report that volatility regimes in this window are computed from `Daily_Return`, not `Volume`, so the zero-volume years don't distort them.
- **Very short regime periods** (e.g. a 2-day "Sideways" blip between Bull and Bear) — these are valid outputs, not bugs; don't filter them out, but consider (config-driven, optional) a minimum-duration flag purely for report readability (e.g. "regimes shorter than 5 days" collapsed into an "unstable transition" note) — this is a nice-to-have, not required for Step 6 sign-off.

---

## 9. Acceptance Criteria

- [ ] `src/eda/regime_analysis.py` exists
- [ ] `RegimeAnalyzer` implements all methods in Section 4
- [ ] Trend and volatility regimes computed as two independent label sets, not forced into one category
- [ ] Regime periods collapsed into contiguous date ranges, not daily repetition
- [ ] Per-regime statistics computed
- [ ] Cross-tabulation of trend × volatility regimes present
- [ ] Known-event cross-reference (from Step 5's config) present where overlaps exist
- [ ] Regime timeline chart generated with shaded background bands
- [ ] Lookahead-bias caveat (Section 7) included in the report text itself, not just this spec
- [ ] All thresholds config-driven
- [ ] Type hints and docstrings on all public methods

---

## Next Step (after your approval)

Step 7 — Feature Usefulness Analysis: rank features by variance, correlation (reusing Step 4's output), and mutual information — without building any predictive model. Remove nothing automatically.
