# Phase 2 — Step 1 Implementation Spec
## Module: Dataset Summary

**Status:** Ready for implementation
**Consumes:** `nsei_clean.csv`, `nifty_features.csv` (already validated — see `MANUAL_VALIDATION_REPORT.md`)
**Produces:** `reports/eda/statistics/dataset_summary.md`

This document is a specification, not code. Hand it to your code-generation tool as-is.

---

## 1. Package Structure to Create

```
src/
└── eda/
    ├── __init__.py
    └── analyzer.py          ← implement in this step

reports/
└── eda/
    └── statistics/          ← output directory (create if missing)
```

Only `analyzer.py` is implemented in this step. `visualizer.py`, `statistics.py`, `correlations.py`, `label_analysis.py` are **not** created yet — they belong to later steps.

---

## 2. Module Responsibility

`analyzer.py` defines a `DatasetSummary` class responsible for producing a single structured summary of a given dataset (either `nsei_clean.csv` or `nifty_features.csv`) and rendering it to a Markdown report.

This module does **not**:
- Compute statistical measures (mean, std, skew, etc.) — that's Step 2.
- Generate plots — that's Step 3.
- Modify or clean the input data in any way (read-only).

---

## 3. Class Design

### `DatasetSummary`

**Constructor inputs:**
- `data: pd.DataFrame` — the loaded dataset
- `dataset_name: str` — human-readable label for the report (e.g. `"nsei_clean"`, `"nifty_features"`)
- `date_column: str = "Date"` — name of the date column

**Public methods (signatures only, no implementation logic specified beyond intent):**

| Method | Returns | Purpose |
|---|---|---|
| `row_count() -> int` | int | Total number of rows |
| `column_count() -> int` | int | Total number of columns |
| `memory_usage_mb() -> float` | float | DataFrame memory footprint in MB |
| `date_range() -> tuple[pd.Timestamp, pd.Timestamp]` | (min_date, max_date) | Earliest and latest date in dataset |
| `missing_value_counts() -> pd.Series` | Series indexed by column | Count of NaNs per column |
| `missing_value_percentages() -> pd.Series` | Series indexed by column | % of NaNs per column (relative to row count) |
| `duplicate_row_count() -> int` | int | Full-row duplicates |
| `duplicate_date_count() -> int` | int | Duplicate values in `date_column` |
| `dtype_summary() -> pd.DataFrame` | DataFrame (`column`, `dtype`) | Data type per column |
| `to_dict() -> dict` | dict | All of the above, bundled, for programmatic use |
| `to_markdown() -> str` | str | Renders the full summary as a Markdown string |
| `save(output_path: str) -> None` | None | Writes `to_markdown()` output to disk |

### `generate_all_summaries(config: dict) -> None`

Module-level function that:
1. Loads both `nsei_clean.csv` and `nifty_features.csv` (paths from config, not hardcoded)
2. Instantiates `DatasetSummary` for each
3. Saves each to its own report file:
   - `reports/eda/statistics/dataset_summary_clean.md`
   - `reports/eda/statistics/dataset_summary_features.md`
4. Also produces a combined `reports/eda/statistics/dataset_summary.md` that presents both side by side for comparison (row count, date range, missing-value profile)

---

## 4. Report Content Requirements (`to_markdown()` output)

The generated Markdown report must include, in this order:

1. **Header** — dataset name, report generation timestamp
2. **Overview table** — row count, column count, date range (start/end), memory usage (MB)
3. **Data types table** — one row per column: name, dtype
4. **Missing values table** — one row per column with any missing values: count, percentage. Columns with zero missing values should be omitted from this table (not padded with zero rows) to keep the report readable, but a one-line note should state how many columns had zero missing values.
5. **Duplicates section** — duplicate row count, duplicate date count (state explicitly "0" if none, do not omit)
6. **Known data notes** — a fixed, hand-written section (not computed) that carries forward the findings from `MANUAL_VALIDATION_REPORT.md` relevant to this dataset, specifically:
   - For `nsei_clean`: note that ~1,320 rows have `Volume == 0` and this is expected (index ticker, not a data quality defect) — not something this report should flag as an anomaly.
   - For `nifty_features`: note that leading NaNs in rolling-window columns (`SMA_20`, `SMA_50`, `SMA_200`, `BB_*`) are expected and proportional to window size, not missing-data defects.

---

## 5. Config Integration

Following the project's config-driven principle, this module must read from `config.yaml` rather than hardcode paths:

```yaml
eda:
  input_files:
    clean: "data/processed/nsei_clean.csv"
    features: "data/features/nifty_features.csv"
  output_dir: "reports/eda/statistics/"
  date_column: "Date"
```

No file paths, dataset names, or the date column name should be hardcoded inside `analyzer.py`.

---

## 6. Edge Cases to Handle

- **Empty DataFrame** — should not crash; report should state "0 rows" explicitly rather than dividing by zero when computing percentages.
- **Missing `date_column`** — raise a clear, named exception rather than a raw `KeyError`.
- **Non-numeric columns mixed with numeric** — `dtype_summary()` must handle both without special-casing failures.
- **The two input files having different max dates** (as found in validation — `nifty_features.csv` currently lags `nsei_clean.csv` by one day) — the combined summary report must surface this discrepancy explicitly as a visible line item, not hide it.

---

## 7. Acceptance Criteria (what "done" looks like for this step)

- [ ] `src/eda/__init__.py` and `src/eda/analyzer.py` exist
- [ ] `DatasetSummary` implements all methods listed in Section 3
- [ ] `generate_all_summaries()` produces all three output files listed in Section 3
- [ ] Reports are readable Markdown (verified by opening the rendered file, not just checking it doesn't crash)
- [ ] No hardcoded file paths — everything sourced from `config.yaml`
- [ ] Date-mismatch between the two source files is visible in the combined report
- [ ] Type hints on all public methods
- [ ] Docstrings on the class and all public methods

---

## Next Step (after your approval)

Step 2 — Statistical Analysis (`statistics.py`): mean, median, mode, std, variance, min/max, quartiles, skewness, kurtosis for every numerical column.
