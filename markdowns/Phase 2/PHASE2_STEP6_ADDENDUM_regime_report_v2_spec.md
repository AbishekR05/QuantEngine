# Phase 2 — Step 6 ADDENDUM Spec
## Regime Report v2: Analytical Depth Enhancements

**Status:** Ready for implementation
**Scope:** Report content and computation of a few additional descriptive statistics from data `RegimeAnalyzer` already produces. No changes to regime classification logic, thresholds, config keys, or acceptance criteria from the base Step 6 spec.
**Explicitly NOT in scope:** Changing how Bull/Bear/Sideways/High/Low/Normal are determined; changing `trend_window`, `trend_threshold`, `vol_window`, or percentile cutoffs; any predictive modeling (item 3 below is explicitly descriptive-only, consistent with the project's phase discipline).

---

## 1. Regime Distribution Summary (new table)

Add to Section 2 (Per-Regime Statistics) of the report, one table each for trend and volatility:

| Regime | Trading Days | Percentage of Dataset |
|---|---|---|
| Bull | {n} | {pct}% |
| Bear | {n} | {pct}% |
| Sideways | {n} | {pct}% |
| Insufficient Data | {n} | {pct}% |
| **Total** | {n} | 100.0% |

(Same structure for the volatility regime: High / Normal / Low / Insufficient Data.)

**This also resolves the gap flagged in the Step 6 review** — the existing per-regime statistics tables omit an "Insufficient Data" row, so the dataset doesn't fully partition. This new table should explicitly include it, so trading days across all rows sum to the full dataset row count (4,613 for `nifty_features`).

Computed directly from `classify_trend_regime()` / `classify_volatility_regime()` value counts — no new detection logic required.

---

## 2. Explicit Mathematical Definitions (new methodology subsection)

Add a short subsection near the top of the report (after the header/config block, before Section 1's caveat) titled **"Methodology: Formal Definitions."** State the exact formulas already implemented, in notation, not just prose:

**Rolling Return** (used for trend classification):
```
RollingReturn_t = (Close_t - Close_(t - trend_window)) / Close_(t - trend_window)
```

**Rolling Volatility** (used for volatility classification, reusing Step 3's definition):
```
RollingVolatility_t = StdDev(DailyReturn_(t-vol_window+1), ..., DailyReturn_t)
```

**Trend regime assignment:**
```
Bull:      Close_t > SMA_200_t   AND   RollingReturn_t > +trend_threshold
Bear:      Close_t < SMA_200_t   AND   RollingReturn_t < -trend_threshold
Sideways:  |RollingReturn_t| <= trend_threshold  (regardless of SMA_200 position)
```

**Volatility regime assignment:**
```
High:    RollingVolatility_t > P75(RollingVolatility, full history)
Low:     RollingVolatility_t < P25(RollingVolatility, full history)
Normal:  otherwise
```

This is documentation of what the code already does (per the base Step 6 spec's Section 3 rules) — not a change to the rules themselves. The point is removing any ambiguity for a future reader who wants to reproduce or audit the classification without reading the source.

---

## 3. Regime Transition Summary (new table, descriptive only)

Add a small transition count matrix for the **trend** regime (volatility transitions are optional/lower priority — trend transitions are the more interpretable of the two):

| From \ To | Bull | Bear | Sideways |
|---|---|---|---|
| **Bull** | — | {n} | {n} |
| **Bear** | {n} | — | {n} |
| **Sideways** | {n} | {n} | — |

Computed by comparing each contiguous regime period (from `regime_periods("trend")`, already computed in the base implementation) to the period immediately following it, and counting how often each (from → to) pair occurs. This is a count of **period-to-period transitions**, not day-to-day — i.e. a 380-day Bull period followed by a 12-day Sideways period counts as exactly one Bull→Sideways transition, not 380 individual transition events. This keeps the table meaningful (otherwise long stable regimes would swamp the counts with same-regime "transitions").

**Explicit framing required in the report text:** state plainly that this table is descriptive/historical only — it characterizes how regimes have transitioned in the past, and is *not* a Markov transition probability model or a forecast of future regime changes. This guards against the table being misread as more predictive than it is, consistent with "descriptive only, not predictive."

---

## 4. Regime Persistence Metrics (extend existing per-regime statistics table)

Add four columns to the existing Section 2 per-regime statistics tables (both trend and volatility):

| ...existing columns... | Min Duration (days) | Max Duration (days) | Median Duration (days) | 
|---|---|---|---|

(Average duration already exists in the base report as "Avg Trading Days per Period" — these are the complementary min/max/median, computed from the same `regime_periods()` duration values already gathered, no new data collection needed.)

This directly helps answer a practical question the current report doesn't: e.g. knowing Bull markets average 14 trading days doesn't tell you whether that's driven by a few very long bull runs and many short ones, or fairly uniform durations — min/max/median resolves that.

---

## 5. Implementation Documentation: Why Two Independent Dimensions

Add a short (3-5 sentence) explanatory note, either in the report's methodology section or as a code-level docstring on `RegimeAnalyzer` (both is fine, report placement is the priority since that's what a future human reader will actually see) — the design comes directly from the base Step 6 spec (Section 3):

> "Trend and volatility are modeled as two independent labels rather than one combined regime because they describe different dimensions of market behavior: trend describes *direction* (is price rising, falling, or flat), while volatility describes *dispersion* (how much day-to-day movement is occurring, independent of direction). A market can be simultaneously trending upward and highly volatile (e.g. a sharp V-shaped recovery) or trending upward calmly. Collapsing these into a single mutually-exclusive category would discard information relevant to later use cases such as position sizing, where a calm bull market and a volatile bull market warrant different risk treatment even though both are 'Bull' by trend."

---

## 6. What Does NOT Change

- Regime classification logic (`classify_trend_regime()`, `classify_volatility_regime()`) — untouched
- `trend_window`, `trend_threshold`, `vol_window`, percentile thresholds — untouched, not retuned
- `regime_periods()`, cross-tabulation logic — untouched (items above consume their output, don't recompute it differently)
- No predictive/forecasting logic introduced anywhere (item 3 is explicitly historical counting)
- No dataset modification

---

## 7. Acceptance Criteria

- [ ] Regime distribution summary table added for both trend and volatility, including "Insufficient Data" row, summing to full dataset row count
- [ ] Explicit formulas for Rolling Return, Rolling Volatility, and regime assignment rules stated in a methodology subsection
- [ ] Trend regime transition count matrix added, with explicit "descriptive only, not predictive" framing in the surrounding text
- [ ] Min/Max/Median duration columns added to both per-regime statistics tables, alongside existing average
- [ ] Short explanatory note on the two-independent-dimensions design decision present in the report
- [ ] No changes to classification logic, thresholds, or config keys
- [ ] No new predictive/forecasting computation introduced

---

## Next Step

Once this addendum is implemented and reviewed, we proceed to **Step 7 — Feature Usefulness Analysis** (variance, correlation reuse from Step 4, mutual information ranking — no automated feature removal) as originally planned.
