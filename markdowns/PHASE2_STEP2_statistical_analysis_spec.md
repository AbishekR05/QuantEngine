# Phase 2 — Step 2 Implementation Spec
## Module: Statistical Analysis

**Status:** Ready for implementation
**Depends on:** Step 1 (`src/eda/analyzer.py`) — reuses the same data-loading/config pattern, does not duplicate it
**Consumes:** `nsei_clean.csv`, `nifty_features.csv`
**Produces:** `reports/eda/statistics/statistical_summary_clean.md`, `reports/eda/statistics/statistical_summary_features.md`

This document is a specification, not code. Hand it to your code-generation tool as-is.

---

## 1. Package Structure to Create

```
src/
└── eda/
    ├── __init__.py            (already exists)
    ├── analyzer.py             (already exists — Step 1)
    └── statistics.py           ← implement in this step

reports/
└── eda/
    └── statistics/             (already exists — Step 1)
```

Only `statistics.py` is implemented in this step. `visualizer.py`, `correlations.py`, `label_analysis.py` are still out of scope.

---

## 2. Module Responsibility

`statistics.py` defines a `StatisticalAnalyzer` class that computes descriptive statistics for every **numerical** column in a given dataset and renders them to a Markdown report.

This module does **not**:
- Generate plots — Step 3.
- Compute correlations between columns — Step 4.
- Modify, impute, or drop any values (read-only, including NaNs — see Section 6).

---

## 3. Class Design

### `StatisticalAnalyzer`

**Constructor inputs:**
- `data: pd.DataFrame` — the loaded dataset
- `dataset_name: str` — human-readable label for the report
- `exclude_columns: list[str] = ["Date"]` — columns to skip even if numeric-typed (configurable, not hardcoded inside the class — sourced from config)

**Public methods:**

| Method | Returns | Purpose |
|---|---|---|
| `numeric_columns() -> list[str]` | list | Columns considered for analysis (numeric dtype, minus `exclude_columns`) |
| `compute_stats(column: str) -> dict` | dict | All statistics (see Section 4) for a single column |
| `compute_all() -> pd.DataFrame` | DataFrame (rows = columns analyzed, columns = statistics) | Full statistics table across all numeric columns |
| `to_markdown() -> str` | str | Renders `compute_all()` as a Markdown table plus interpretive notes |
| `save(output_path: str) -> None` | None | Writes `to_markdown()` output to disk |

### `generate_all_statistics(config: dict) -> None`

Module-level function that:
1. Loads both datasets (same config-driven paths as Step 1 — reuse, don't redefine)
2. Instantiates `StatisticalAnalyzer` for each
3. Saves each to `reports/eda/statistics/statistical_summary_<name>.md`

---

## 4. Statistics to Compute (per numeric column)

| Statistic | Notes |
|---|---|
| Mean | |
| Median | |
| Mode | If multiple modes exist, report the first and note the count of distinct modes |
| Standard Deviation | Sample std (ddof=1) |
| Variance | Sample variance (ddof=1) |
| Minimum | |
| Maximum | |
| 25th Percentile | |
| 50th Percentile | (redundant with median — include anyway for completeness, per spec) |
| 75th Percentile | |
| Skewness | |
| Kurtosis | Report as **excess kurtosis** (i.e. normal distribution = 0), and state explicitly in the report which convention is used — this detail changes interpretation and must not be ambiguous |

All statistics must be computed with **NaNs excluded** (pandas default `skipna=True`), not with NaNs coerced to 0 — coercing to 0 would corrupt indicator columns that have legitimate leading NaNs (per Step 1 findings on `SMA_200` etc.).

---

## 5. Report Content Requirements (`to_markdown()` output)

1. **Header** — dataset name, generation timestamp
2. **Full statistics table** — one row per numeric column, one column per statistic from Section 4
3. **Interpretive flags section** — auto-generated observations, not just raw numbers:
   - Columns with `|skewness| > 1` → flagged as "highly skewed"
   - Columns with `excess kurtosis > 3` → flagged as "heavy-tailed / fat-tailed" (relevant for `Daily_Return`, `Log_Return` — expected in financial return series, so the note should say this is expected for return columns specifically, not an anomaly)
   - Columns where `min == max` (zero variance) → flagged explicitly as a potential data quality issue (this would NOT be expected for any column in this dataset — if it fires, it should stand out)
4. **Sample size note** — for columns with fewer non-null values than the dataset's total row count (i.e. the indicator warm-up columns), explicitly state the effective N used for that column's statistics, so a reader doesn't assume all columns were computed over the same sample size.

---

## 6. Config Integration

Extend the existing `eda` config block from Step 1:

```yaml
eda:
  input_files:
    clean: "data/processed/nsei_clean.csv"
    features: "data/features/nifty_features.csv"
  output_dir: "reports/eda/statistics/"
  date_column: "Date"
  statistics:
    exclude_columns: ["Date"]
    skew_threshold: 1.0
    kurtosis_threshold: 3.0
```

Thresholds used for the interpretive flags in Section 5 must come from config, not be hardcoded, so they can be tuned later without touching code.

---

## 7. Edge Cases to Handle

- **Column with all-NaN values** — `compute_stats()` should not crash; report `N/A` for every statistic and flag the column explicitly rather than silently omitting it.
- **Column with only one non-null value** — std/variance/skew/kurtosis are undefined (or zero) in this case; report `N/A` rather than a misleading `0.0`.
- **Non-numeric columns accidentally typed as object but containing numbers** (not expected here, but the module should not silently misclassify — `numeric_columns()` should use pandas dtype, not attempt type coercion).
- **`Volume` column for `nsei_clean`** — contains ~1,320 zero values (per validation and Step 1 findings). These are real values, not missing — statistics should include them as-is (mean/std will reflect the zeros). Do not exclude zero-volume rows from this column's statistics; that would be silent, undocumented filtering.

---

## 8. Acceptance Criteria

- [ ] `src/eda/statistics.py` exists
- [ ] `StatisticalAnalyzer` implements all methods in Section 3
- [ ] All 12 statistics from Section 4 present for every numeric column
- [ ] Kurtosis convention (excess vs. raw) explicitly labeled in report output
- [ ] Interpretive flags (skew/kurtosis/zero-variance) generated using config-driven thresholds
- [ ] Effective sample size (N) shown for any column with nulls
- [ ] No hardcoded paths, column exclusions, or thresholds — all from `config.yaml`
- [ ] Type hints on all public methods
- [ ] Docstrings on the class and all public methods

---

## Next Step (after your approval)

Step 3 — Visual Analysis (`visualizer.py`): generate and save individual plots for closing price, volume, daily/log returns, RSI, MACD, EMAs, ATR, Bollinger Bands, histograms, boxplots, and rolling volatility.
