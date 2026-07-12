# Phase 2 — Step 4 Implementation Spec
## Module: Correlation Analysis

**Status:** Ready for implementation
**Depends on:** Step 1 (`analyzer.py`), Step 2 (`statistics.py`), Step 3 (`visualizer.py`) — reuse existing config-driven data loading; the heatmap in this step is a plot, so it should follow the same styling conventions established in `visualizer.py` (DPI, figure size, colors from config)
**Consumes:** `nifty_features.csv` (the dataset with indicators — correlation analysis is not meaningful on the 7-column clean OHLCV file alone)
**Produces:** `reports/eda/statistics/correlation_report.md` + `reports/eda/figures/correlation_heatmap_pearson.png`, `reports/eda/figures/correlation_heatmap_spearman.png`

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
    └── correlations.py          ← implement in this step

reports/
└── eda/
    ├── statistics/               (already exists)
    └── figures/                  (already exists)
```

Only `correlations.py` is implemented in this step. `label_analysis.py` remains out of scope.

---

## 2. Module Responsibility

`correlations.py` defines a `CorrelationAnalyzer` class that computes pairwise correlations across all numeric columns of `nifty_features.csv`, renders a heatmap, ranks feature pairs by correlation strength, and flags redundancy/leakage risk. This module does **not**:
- Perform outlier detection — Step 5
- Perform feature-importance ranking via variance/mutual information — Step 7 (correlation is one input to that later step, but this module's job is correlation only)
- Remove or transform any columns — analysis only, no dataset mutation

---

## 3. Class Design

### `CorrelationAnalyzer`

**Constructor inputs:**
- `data: pd.DataFrame` — `nifty_features.csv`, already loaded
- `exclude_columns: list[str]` — from config (at minimum `Date`; should also default to excluding obviously-identical-by-construction pairs like `Close`/`Adj Close` from the *heatmap clutter* — see Section 6 — though they still appear in the raw correlation matrix)
- `high_corr_threshold: float` — from config (e.g. 0.9)

**Public methods:**

| Method | Returns | Purpose |
|---|---|---|
| `pearson_matrix() -> pd.DataFrame` | DataFrame (N×N) | Full Pearson correlation matrix |
| `spearman_matrix() -> pd.DataFrame` | DataFrame (N×N) | Full Spearman correlation matrix |
| `ranked_pairs(method: str = "pearson") -> pd.DataFrame` | DataFrame | All unique column pairs ranked by absolute correlation, descending |
| `high_correlation_pairs(method: str = "pearson") -> pd.DataFrame` | DataFrame | Subset of `ranked_pairs()` above `high_corr_threshold` |
| `flag_redundant_features() -> list[dict]` | list of dicts | Groups of features that are highly correlated with each other (candidates for dropping one from a future model — flagged, not acted on) |
| `flag_potential_leakage() -> list[dict]` | list of dicts | Pairs where correlation is suspiciously close to 1.0 (e.g. > 0.99) — signals a feature that may be a near-duplicate or derived directly from another in a way that could leak information in a predictive model |
| `plot_heatmap(method: str = "pearson") -> str` | str (file path) | Renders and saves the heatmap for the given method |
| `to_markdown() -> str` | str | Full report combining all of the above |
| `save(output_path: str) -> None` | None | Writes report to disk |

### `generate_correlation_report(config: dict) -> None`

Module-level orchestrator: load `nifty_features.csv` via existing config pattern, instantiate `CorrelationAnalyzer`, generate both heatmaps, save the combined report.

---

## 4. Report Content Requirements (`to_markdown()` output)

1. **Header** — dataset name, generation timestamp, number of columns analyzed
2. **Method note** — brief explanation of when Pearson vs. Spearman diverge (Pearson assumes linear relationships; Spearman captures monotonic-but-nonlinear ones — relevant here since price/indicator relationships are often nonlinear)
3. **Top-N ranked pairs table** (both Pearson and Spearman) — N configurable, default 20
4. **High-correlation pairs section** — pairs above `high_corr_threshold`, with a plain-language note for each expected/obvious case (see Section 6) so a reader doesn't mistake known-by-construction correlations for a surprising finding
5. **Redundant feature groups** — e.g. `{SMA_20, EMA_20, BB_Middle}` if they cluster together
6. **Potential leakage flags** — pairs > 0.99, explicitly called out as needing scrutiny before use as independent model inputs
7. **Divergence notes** — any pair where Pearson and Spearman disagree meaningfully (e.g. one flags "high correlation," the other doesn't) — worth a callout since it points to a nonlinear relationship
8. **Heatmap image references** — embed/link both PNGs in the report

---

## 5. Config Integration

Extend the `eda` config block:

```yaml
eda:
  correlation:
    input_file: "data/features/nifty_features.csv"
    exclude_columns: ["Date"]
    high_corr_threshold: 0.9
    leakage_threshold: 0.99
    top_n_pairs: 20
    heatmap_output_dir: "reports/eda/figures/"
    report_output_path: "reports/eda/statistics/correlation_report.md"
```

Thresholds must be config-driven, not hardcoded — same principle as Steps 1–3.

---

## 6. Known Findings to Anticipate (so the report reads as informed, not naive)

Based on what we already know about this dataset's structure, several high-correlation pairs are **expected by construction**, not discoveries:

- `Close` ↔ `Adj Close` — will show correlation ≈ 1.0 (confirmed identical in Step 1/2 — `^NSEI` has no dividend adjustments). The report should label this explicitly as "identical by construction, not a redundancy finding" rather than flagging it as if it were newly discovered.
- `Open`, `High`, `Low`, `Close` — all expected to correlate near-perfectly with each other (same underlying price series, different intraday snapshots).
- `SMA_20`/`EMA_20`/`BB_Middle` — `BB_Middle` is typically defined as the same rolling mean as `SMA_20`, so this cluster is expected to be near-identical, not a coincidental finding.
- `MACD`/`MACD_Signal` — by definition, `MACD_Signal` is a smoothed version of `MACD`, so high correlation here is structural, not informative.
- `Daily_Return`/`Log_Return` — mathematically near-identical for small daily moves; expected to correlate very highly.

The module should still **compute and report all of these mechanically** (don't hardcode exceptions into the logic), but `to_markdown()`'s high-correlation section should append a short "why" annotation for pairs matching these known patterns, so a reader distinguishes "expected/structural" from "worth investigating." This keeps the report honest (nothing is suppressed) while making it useful (nothing looks like a surprise when it isn't one).

---

## 7. Edge Cases to Handle

- **Constant/zero-variance columns** (none currently exist per Step 2's zero-variance check, but if one appeared later) — Pearson/Spearman correlation is undefined for a constant column; must return `NaN` gracefully, not raise.
- **NaN handling** — rolling-window columns (`SMA_200`, etc.) have leading NaNs. Correlation should be computed pairwise using only rows where *both* columns have values (pandas' default `.corr()` behavior), and the report should note that different pairs may be computed over different effective N — same principle as Step 2.
- **`Volume`'s ~1,320 zero values** — these are real values, not missing, and should be included in correlation calculations as-is (no special-casing, no exclusion).
- **Very large N×N matrix readability** — with ~22 numeric columns the heatmap is still readable; if the feature set grows substantially later, note in the report that heatmap readability should be revisited (no action needed now, just don't hardcode assumptions that only hold at the current column count).

---

## 8. Acceptance Criteria

- [ ] `src/eda/correlations.py` exists
- [ ] `CorrelationAnalyzer` implements all methods in Section 3
- [ ] Both Pearson and Spearman matrices computed and saved as heatmap images
- [ ] Ranked pairs, high-correlation pairs, redundant groups, and leakage flags all present in the report
- [ ] Known structural correlations (Section 6) are annotated with plain-language "why," not presented as novel findings
- [ ] Pearson/Spearman divergence explicitly called out where it occurs
- [ ] All thresholds sourced from config
- [ ] Type hints and docstrings on all public methods

---

## Next Step (after your approval)

Step 5 — Outlier Analysis (`label_analysis.py` is NOT this step — outlier detection is a separate module): IQR and Z-score based outlier identification, visualized but never auto-removed, consistent with the project's rule that market crashes and extreme events are documented, not cleaned.
