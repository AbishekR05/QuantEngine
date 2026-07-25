# Phase 2 — Step 3 Implementation Spec
## Module: Visual Analysis

**Status:** Ready for implementation
**Depends on:** Step 1 (`analyzer.py`), Step 2 (`statistics.py`) — reuse existing config-driven data loading, don't redefine it
**Consumes:** `nsei_clean.csv`, `nifty_features.csv`
**Produces:** individual plot image files under `reports/eda/figures/`

This document is a specification, not code. Hand it to your code-generation tool as-is.

---

## 1. Package Structure to Create

```
src/
└── eda/
    ├── __init__.py            (already exists)
    ├── analyzer.py             (already exists — Step 1)
    ├── statistics.py           (already exists — Step 2)
    └── visualizer.py           ← implement in this step

reports/
└── eda/
    └── figures/                ← output directory (create if missing)
```

Only `visualizer.py` is implemented in this step. `correlations.py`, `label_analysis.py` remain out of scope.

---

## 2. Module Responsibility

`visualizer.py` defines a `Visualizer` class that generates and saves the required plots as individual image files. This module does **not**:
- Compute any new statistics beyond what plotting itself requires (e.g. rolling volatility is a plotting input, computed inline for the plot — not a new module deliverable)
- Perform correlation analysis — Step 4
- Perform outlier detection/flagging — Step 5 (plots here visualize distributions; Step 5 owns *identifying* outliers)

---

## 3. Required Plots

| # | Plot | Source column(s) | Type | Dataset |
|---|---|---|---|---|
| 1 | Closing Price over time | `Close` | Line | clean |
| 2 | Volume over time | `Volume` | Line/bar | clean |
| 3 | Daily Returns over time | `Daily_Return` | Line | features |
| 4 | Log Returns over time | `Log_Return` | Line | features |
| 5 | RSI (14) over time | `RSI_14` | Line, with 30/70 reference bands | features |
| 6 | MACD | `MACD`, `MACD_Signal`, `MACD_Hist` | Line + bar combo | features |
| 7 | EMA 20 vs. Price | `EMA_20`, `Close` | Overlaid line | features |
| 8 | EMA 50 vs. Price | `EMA_50`, `Close` | Overlaid line | features |
| 9 | EMA 200 vs. Price | *(not in current feature file — see Section 7)* | Overlaid line | features |
| 10 | ATR (14) over time | `ATR_14` | Line | features |
| 11 | Bollinger Bands | `BB_Upper`, `BB_Middle`, `BB_Lower`, `Close` | Overlaid band + price | features |
| 12 | Histogram — Daily Returns | `Daily_Return` | Histogram | features |
| 13 | Histogram — Volume | `Volume` | Histogram | clean |
| 14 | Boxplot — Daily Returns | `Daily_Return` | Boxplot | features |
| 15 | Boxplot — Volume | `Volume` | Boxplot | clean |
| 16 | Rolling Volatility | rolling std of `Daily_Return` | Line | features |

Each plot is saved as its **own individual file** (per original spec — "save every plot individually"), not combined into subplot grids.

---

## 4. Class Design

### `Visualizer`

**Constructor inputs:**
- `clean_data: pd.DataFrame`
- `features_data: pd.DataFrame`
- `output_dir: str` — from config
- `date_column: str = "Date"`

**Public methods — one per plot category, not one giant method:**

| Method | Output file |
|---|---|
| `plot_closing_price() -> str` | `closing_price.png` |
| `plot_volume() -> str` | `volume.png` |
| `plot_daily_returns() -> str` | `daily_returns.png` |
| `plot_log_returns() -> str` | `log_returns.png` |
| `plot_rsi() -> str` | `rsi_14.png` |
| `plot_macd() -> str` | `macd.png` |
| `plot_ema(period: int) -> str` | `ema_{period}.png` |
| `plot_atr() -> str` | `atr_14.png` |
| `plot_bollinger_bands() -> str` | `bollinger_bands.png` |
| `plot_histogram(column: str) -> str` | `histogram_{column}.png` |
| `plot_boxplot(column: str) -> str` | `boxplot_{column}.png` |
| `plot_rolling_volatility(window: int) -> str` | `rolling_volatility_{window}d.png` |
| `generate_all() -> list[str]` | calls all of the above, returns list of saved file paths |

Each method returns the saved file path (string) so `generate_all()` can produce a manifest/index.

### `generate_all_plots(config: dict) -> list[str]`

Module-level function, same orchestration pattern as Steps 1–2: load config, load both datasets, instantiate `Visualizer`, call `generate_all()`.

---

## 5. Plot Requirements (apply to all plots)

- **Every axis labeled** (units where applicable — e.g. price in ₹/points, returns as %).
- **Every plot titled** with dataset name + date range covered.
- **X-axis is always the date column**, formatted readably (not raw datetime ticks jammed together — thin out tick density for a ~19-year series).
- **Volume-related plots** (`plot_volume`, `plot_histogram("Volume")`, `plot_boxplot("Volume")`) must **annotate the 2007–2013 zero-volume period** directly on the chart (e.g. a shaded region or text annotation), since otherwise the zero-volume years will visually read as a data outage rather than the known, expected limitation established in Step 1.
- **RSI plot** must include horizontal reference lines at 30 and 70 (standard overbought/oversold thresholds) — these are visual aids, not new computed statistics.
- **Bollinger Bands plot** should shade the area between upper/lower bands so the "band" reads visually as a band, not three overlapping lines.
- **Consistent color scheme and figure size** across all plots (define once, e.g. in a small `_apply_style()` helper or shared config, not per-method magic numbers).
- **File format:** PNG, saved at a resolution suitable for inclusion in the final report (e.g. 150 DPI minimum) — exact DPI/size sourced from config, not hardcoded.

---

## 6. Config Integration

Extend the `eda` config block:

```yaml
eda:
  figures:
    output_dir: "reports/eda/figures/"
    dpi: 150
    figure_size: [12, 6]
    rolling_volatility_window: 21   # ~1 trading month
    ema_periods: [20, 50, 200]
    rsi_overbought: 70
    rsi_oversold: 30
```

---

## 7. Open Issue to Resolve Before/During Implementation

**`EMA_200` does not currently exist in `nifty_features.csv`** — the file only contains `EMA_20` and `EMA_50` (confirmed from the Step 1 dataset summary column list). The original Phase 2 spec calls for an EMA200 plot.

Two options:
- **(a)** Compute `EMA_200` inline within `visualizer.py` just for plotting purposes (read-only derived value, not written back to the features file), or
- **(b)** Treat this as a gap in the Phase 1 feature-engineering output and add `EMA_200` to the actual features dataset upstream, then re-run Step 1/2 reports so they reflect it too.

**(b) is the more correct fix** — it keeps `nifty_features.csv` as the single source of truth rather than having plotting code silently compute values that don't exist anywhere else in the pipeline (a future consumer of the CSV, e.g. the ML phase, would want `EMA_200` as an actual feature column, not just a plot). Recommend confirming this before implementation rather than having Antigravity guess.

---

## 8. Edge Cases to Handle

- **Plotting a column that is entirely/partially NaN at the start** (e.g. `SMA_200`, `EMA_200` if added) — the line should simply not render for the NaN region, not throw, and not be interpolated/filled to hide the warm-up gap.
- **Very long date range (19 years) on a single line chart** — must remain readable; consider whether a resampled/lighter rendering is needed for the full-history closing-price plot specifically (still full daily resolution in the data, just be deliberate about tick/gridline density so the chart isn't unreadable).
- **Output directory does not yet exist** — create it, don't fail.
- **Re-running the module** — plot files should be overwritten cleanly (idempotent), not accumulate duplicate/timestamped files that pile up in `reports/eda/figures/`.

---

## 9. Acceptance Criteria

- [ ] `src/eda/visualizer.py` exists
- [ ] All 16 plots from Section 3 generated as individual PNG files
- [ ] Zero-volume period (2007–2013) visually annotated on volume-related plots
- [ ] RSI plot includes 30/70 reference lines
- [ ] Bollinger Bands rendered as a shaded band
- [ ] `EMA_200` gap (Section 7) explicitly resolved one way or the other — not silently skipped
- [ ] All chart styling (DPI, figure size, colors) sourced from config
- [ ] `generate_all()` returns a list of all saved file paths (useful for the final report step to reference)
- [ ] Type hints and docstrings on all public methods

---

## Next Step (after your approval)

Step 4 — Correlation Analysis (`correlations.py`): Pearson + Spearman correlation matrices, heatmap, feature ranking, and identification of redundant/highly-correlated indicators.
