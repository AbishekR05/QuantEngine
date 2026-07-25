# Phase 2 — Step 5 Implementation Spec
## Module: Outlier Analysis

**Status:** Ready for implementation
**Depends on:** Step 1 (`analyzer.py`), Step 2 (`statistics.py`), Step 3 (`visualizer.py`) — reuse config-driven loading and plot styling conventions
**Consumes:** `nsei_clean.csv`, `nifty_features.csv`
**Produces:** `reports/eda/statistics/outlier_report.md` + per-column outlier visualization images under `reports/eda/figures/outliers/`

This document is a specification, not code. Hand it to your code-generation tool as-is.

---

## 1. Package Structure to Create

```
src/
└── eda/
    ├── __init__.py             (already exists)
    ├── analyzer.py              (already exists — Step 1)
    ├── statistics.py            (already exists — Step 2)
    ├── visualizer.py            (already exists — Step 3)
    ├── correlations.py          (already exists — Step 4)
    └── outlier_analysis.py      ← implement in this step

reports/
└── eda/
    ├── statistics/               (already exists)
    └── figures/
        └── outliers/              ← new subdirectory for this step's plots
```

Only `outlier_analysis.py` is implemented in this step. `label_analysis.py` remains out of scope.

---

## 2. Module Responsibility

`outlier_analysis.py` defines an `OutlierAnalyzer` class that identifies statistical outliers using both IQR and Z-score methods, across all numeric columns, and reports/visualizes them. This module does **not**:
- Remove, cap, winsorize, or otherwise modify any values — detection and reporting only
- Make any judgment call about whether a flagged point is a "real" market event vs. a data error — that judgment belongs to the human reviewing the report, informed by the domain notes this module includes (see Section 6)
- Perform market regime classification — that's Step 6

**This is the project's single most consequential "do not touch" module.** Your `claude.md` is explicit that market crashes and extreme events (2009 election circuit halt, 2020 COVID crash, 2008 financial crisis) must never be auto-cleaned. This module's entire job is to surface outliers for visibility — never to act on them.

---

## 3. Class Design

### `OutlierAnalyzer`

**Constructor inputs:**
- `data: pd.DataFrame`
- `dataset_name: str`
- `exclude_columns: list[str]` — from config (at minimum `Date`)
- `iqr_multiplier: float` — from config (standard default 1.5)
- `zscore_threshold: float` — from config (standard default 3.0)

**Public methods:**

| Method | Returns | Purpose |
|---|---|---|
| `iqr_outliers(column: str) -> pd.DataFrame` | rows flagged | Rows where value < Q1 − k·IQR or > Q3 + k·IQR |
| `zscore_outliers(column: str) -> pd.DataFrame` | rows flagged | Rows where \|z-score\| > threshold |
| `outlier_summary() -> pd.DataFrame` | one row per column | Count and % of outliers by each method, per numeric column |
| `outlier_overlap(column: str) -> pd.DataFrame` | rows flagged by BOTH methods | Intersection — highest-confidence outliers |
| `annotate_known_events(outlier_df: pd.DataFrame) -> pd.DataFrame` | same df + new column | Cross-references flagged dates against the known-event list (Section 6) and adds a `known_event` label where applicable |
| `plot_outliers(column: str) -> str` | file path | Boxplot or scatter with outlier points highlighted distinctly from the main distribution |
| `to_markdown() -> str` | str | Full report |
| `save(output_path: str) -> None` | None | Writes report to disk |

### `generate_outlier_report(config: dict) -> None`

Module-level orchestrator, same pattern as Steps 1–4.

---

## 4. Report Content Requirements

1. **Header** — dataset name(s), generation timestamp, methods used (IQR multiplier, Z-score threshold — state the actual configured values, not just method names)
2. **Summary table** — per numeric column: IQR outlier count/%, Z-score outlier count/%, overlap count (flagged by both)
3. **Per-column detail** — for columns with outliers, list the flagged dates/values (or top-N by magnitude if the list is long — configurable N)
4. **Known-event cross-reference** — every flagged outlier date checked against the known-event list (Section 6); dates matching a known event are labeled as such inline, not just implied
5. **Unexplained outliers section** — outlier points that do NOT match any known event. These deserve the most attention in the report, since they're the ones that might actually indicate a data quality issue rather than a real market event. Explicitly distinguish this from the known-event list rather than mixing them together.
6. **Explicit non-action statement** — a standing note, verbatim or close to it: *"No outliers identified in this report have been removed, capped, or modified. This report is for visibility only. Any decision to treat a specific point as erroneous vs. a genuine market event is a human judgment call, not an automated one."*

---

## 5. Config Integration

```yaml
eda:
  outliers:
    exclude_columns: ["Date"]
    iqr_multiplier: 1.5
    zscore_threshold: 3.0
    top_n_per_column: 20
    output_dir: "reports/eda/figures/outliers/"
    report_output_path: "reports/eda/statistics/outlier_report.md"
```

---

## 6. Known Market Events (for cross-referencing — do not treat these as exhaustive)

Carry forward from prior validation and Step 2/3 findings, this list should be included in the module (as config or a small constants list, not hardcoded deep in logic) so `annotate_known_events()` has something concrete to check against:

| Date | Event | Expected effect |
|---|---|---|
| 2009-05-18 | General election result — upper circuit halt | `Daily_Return` ≈ +17.7% |
| 2020-03-23 | COVID-19 crash | `Daily_Return` ≈ −13.0% |
| 2020-03-12, 2020-03-16, 2020-04-07 | COVID-19 volatility window | Multiple >6% moves |
| 2008 (Jan, Oct) | Global financial crisis | Multiple >6% moves |

This list will legitimately grow as the outlier report surfaces more dates — treat it as a living reference (e.g. a small YAML/CSV lookup file under `config/`), not something hardcoded once and forgotten. If the report surfaces an unexplained outlier that you subsequently confirm is a real event (e.g. a specific RBI policy shock), it should be addable to this list without touching `outlier_analysis.py`'s code.

---

## 7. Edge Cases to Handle

- **`Volume` column** — the ~1,320 zero values will likely register as IQR/Z-score outliers on the low end (since they're far from the distribution's center). This is **expected given Steps 1–4's findings** and should be labeled as such in the report (cross-referenced against the "known limitation" note, similar to how known market events are cross-referenced) — not presented as if newly discovered.
- **Rolling-indicator columns with leading NaNs** (`SMA_200`, etc.) — outlier detection should operate on non-null values only; don't let the warm-up NaNs distort quartile/mean/std calculations.
- **Return columns (`Daily_Return`, `Log_Return`)** — will have the most outliers by design (fat-tailed distributions per Step 2 findings). This is expected; the report should note that a high outlier count in return columns is normal for financial time series, not a red flag in itself — the *unexplained* subset is what matters.
- **A date appearing as an outlier in multiple columns simultaneously** (e.g. 2020-03-23 likely flagged in `Daily_Return`, `Log_Return`, `ATR_14`, and rolling volatility) — worth surfacing as a cluster rather than repeating the same date across disconnected per-column lists. Not a strict requirement, but improves report usefulness.

---

## 8. Acceptance Criteria

- [ ] `src/eda/outlier_analysis.py` exists
- [ ] `OutlierAnalyzer` implements all methods in Section 3
- [ ] Both IQR and Z-score methods computed independently, plus their overlap
- [ ] Known-event cross-referencing implemented and visibly separates "explained" from "unexplained" outliers
- [ ] `Volume`'s zero-value outliers correctly labeled as expected/known, not flagged as new findings
- [ ] Explicit non-action statement present in the report
- [ ] No data modification anywhere in this module — verify by confirming `iqr_outliers()`/`zscore_outliers()` are read-only and return copies/views, never mutate `self.data`
- [ ] All thresholds config-driven
- [ ] Type hints and docstrings on all public methods

---

## Next Step (after your approval)

Step 6 — Market Regime Analysis: automatically identify Bull/Bear/High-Volatility/Low-Volatility/Sideways periods and generate per-regime statistics, useful for later model evaluation.
