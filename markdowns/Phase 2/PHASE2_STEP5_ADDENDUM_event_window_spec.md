# Phase 2 — Step 5 ADDENDUM Spec
## Outlier Report v2: Event-Window Annotation

**Status:** Ready for implementation
**Scope:** This is an enhancement to the market-event annotation/labeling logic in `outlier_analysis.py` ONLY.
**Explicitly NOT in scope:** IQR calculation, Z-score calculation, overlap detection, any threshold, any dataset modification. `iqr_outliers()`, `zscore_outliers()`, `outlier_overlap()` are untouched.

This addendum also folds in one finding from the Step 5 review: the `RSI_14` = 100.0 stretch at the very start of the series (2007-09-18 through 2007-10-03) is a warm-up boundary artifact, not an unexplained anomaly, and should be captured by the new "Known Data Limitation" category rather than left in an unexplained bucket.

---

## 1. Problem Being Fixed

The current `annotate_known_events()` matches outlier dates against **single exact dates**. A multi-day event like the COVID crash only gets its anchor date (e.g. 2020-03-23) labeled correctly — adjacent days that are clearly part of the same event (2020-03-24, 03-25, 03-26...) fall through to "Unexplained." This makes the report understate how much of the "unexplained" bucket is actually just imprecise event matching.

---

## 2. Replace Single-Date Matching with Event-Window Matching

### New config structure — `config/known_events.yaml` (or `.json`, your call — must be an external, editable file, not hardcoded in `outlier_analysis.py`)

```yaml
known_events:
  - event_name: "Global Financial Crisis"
    start_date: "2008-01-01"
    end_date: "2009-03-31"
    category: "known_market_event"
    description: "Global financial crisis and extreme market volatility."

  - event_name: "2009 Election Rally"
    start_date: "2009-05-15"
    end_date: "2009-05-22"
    category: "known_market_event"
    description: "Indian general election results and upper circuit rally."

  - event_name: "COVID Crash"
    start_date: "2020-03-09"
    end_date: "2020-04-30"
    category: "known_market_event"
    description: "COVID-19 market crash and recovery volatility."

  - event_name: "2024 Election Volatility"
    start_date: "2024-06-03"
    end_date: "2024-06-07"
    category: "known_market_event"
    description: "Indian general election result volatility."

  - event_name: "RSI Warm-Up Boundary Artifact"
    start_date: "2007-09-18"
    end_date: "2007-10-05"
    category: "known_data_limitation"
    description: "Earliest RSI_14 values are mathematically pinned near 100 because the initial rolling window contains only up-days. This is a rolling-window boundary effect, not a market event or data error."
    affected_columns: ["RSI_14"]
```

Notes on this structure:
- **`category` field is required per event** — this is what drives the new report labels (Section 4), not a hardcoded if/else keyed on event name.
- **`affected_columns` is optional** — when present (as with the RSI warm-up event), the match should only apply to outliers in those specific columns, not every column on that date range. This matters because the RSI warm-up window (Sept–Oct 2007) might coincide with an unrelated outlier in a different column that has nothing to do with RSI's warm-up — those should NOT be swept into "known limitation" just because the date falls in the window.
- This file is meant to grow over time (exactly per the original Step 5 spec's "living reference" design) — adding an event should never require touching `outlier_analysis.py`.

---

## 3. Class Design Changes

### `OutlierAnalyzer` — modified/new methods

| Method | Change |
|---|---|
| `load_known_events(config_path: str) -> list[dict]` | **New.** Loads and parses the event-window config. |
| `annotate_known_events(outlier_df: pd.DataFrame) -> pd.DataFrame` | **Modified.** Instead of exact-date lookup, checks whether each outlier's date falls within `[start_date, end_date]` for any event, additionally filtering by `affected_columns` when specified. Adds `event_name`, `category`, and `description` columns rather than a single `known_event` string. |
| `classify_outlier(row) -> str` | **New.** Returns one of the four category labels from Section 4, based on whether a matching event/limitation window was found. |

No changes to `iqr_outliers()`, `zscore_outliers()`, or `outlier_overlap()` — confirmed out of scope.

---

## 4. New Classification Labels

Replace the binary "Explained" / "Unexplained" labeling everywhere in the report with:

| Label | Meaning |
|---|---|
| **Known Market Event** | Falls within a configured event window with `category: known_market_event` (e.g. COVID crash, 2009 election, GFC) |
| **Known Data Limitation** | Falls within a configured window with `category: known_data_limitation` (e.g. the RSI warm-up artifact, or — if it recurs — the zero-volume pattern) |
| **Potential Unknown Event** | Does not match any configured window, but co-occurs with other outlier columns on the same date (i.e. appears in the chronological clustering table) — suggests a real but *uncatalogued* market event worth investigating and possibly adding to `known_events.yaml` |
| **Potential Data Quality Issue** | Does not match any configured window and does NOT co-occur with other columns — an isolated single-column single-day spike is more likely to warrant a data integrity check than a market-wide event |

This distinction (cluster vs. isolated) gives a sharper prioritization than a flat "Unexplained" bucket — a lone spike in one column is a different kind of finding than eight columns moving together on the same day.

---

## 5. Report Changes

### Detail tables (per-column outlier lists)
Replace the "Explained / Expected" vs. "Unexplained (Potential Anomalies)" subsection headers with the four categories from Section 4. A column may now have up to four subsections instead of two (omit any that are empty for that column).

### Chronological Clustering — add a summary layer above the existing detail table

For each known event window that overlaps the outlier data, add a summary block **before** the existing day-by-day table (which stays, unmodified, as the detailed view):

```
### COVID Crash Window (2020-03-09 to 2020-04-30)

Trading Days in Window: {count}
Outlier Days in Window: {count}
Maximum Simultaneous Features Flagged (single day): {count}
Most Frequently Flagged Features:
- Daily_Return ({n} days)
- Log_Return ({n} days)
- ATR_14 ({n} days)
- MACD ({n} days)
- MACD_Signal ({n} days)
```

Generate one such block per known event window present in the data (Global Financial Crisis, 2009 Election Rally, COVID Crash, 2024 Election Volatility, and any future additions to the config) — computed from the same outlier data already gathered, not a new detection pass.

The existing row-by-row chronological table remains beneath these summaries, unchanged in format — this is an additional interpretive layer, not a replacement.

### RSI warm-up finding specifically
Once the `RSI Warm-Up Boundary Artifact` event is added to config, the 11 rows currently sitting under "Unclassified extreme point" for `RSI_14` (2007-09-18 to 2007-10-05) should automatically move to **Known Data Limitation** once this addendum is implemented — this is the acceptance check for whether the `affected_columns` filtering logic is working correctly, since those same calendar dates should NOT reclassify any *other* column's outliers (there likely aren't any in that exact window, but the logic must not blanket-apply).

---

## 6. Edge Cases

- **Overlapping event windows** (e.g. if a future addition to `known_events.yaml` overlaps an existing window) — match should return all applicable events for that date, not silently pick one. Report should show all matches if more than one applies.
- **Event window with no `affected_columns` key** — applies to all columns (this is the default behavior for the market-wide events like COVID/GFC; only the RSI warm-up entry needs the restriction).
- **Config file missing or malformed** — fail loudly with a clear error, don't silently fall back to unclassified-everything.
- **Adding a new event later** — must require zero code changes, only a config edit. This is the core value of this addendum; if any part of the implementation still requires touching `outlier_analysis.py` to add an event, that's a gap.

---

## 7. Acceptance Criteria

- [ ] `known_events.yaml` (or equivalent) exists as an external, human-editable config file
- [ ] Event-window (start/end date range) matching replaces exact-date matching
- [ ] `affected_columns` filtering works correctly (RSI warm-up doesn't bleed into unrelated columns)
- [ ] Four-category classification (Known Market Event / Known Data Limitation / Potential Unknown Event / Potential Data Quality Issue) replaces binary Explained/Unexplained throughout the report
- [ ] Cluster-vs-isolated logic correctly distinguishes "Potential Unknown Event" from "Potential Data Quality Issue"
- [ ] Per-event summary blocks (trading days, outlier days, max simultaneous features, most frequent features) added above the existing detailed chronological table — detailed table itself unchanged
- [ ] The 11 RSI_14 warm-up rows reclassify from unexplained to "Known Data Limitation" once the new event entry is added
- [ ] No changes to IQR/Z-score/overlap computation logic or thresholds
- [ ] No dataset modification anywhere

---

## Next Step

Once this addendum is implemented and reviewed, we proceed to **Step 6 — Market Regime Analysis** (Bull/Bear/High-Vol/Low-Vol/Sideways period identification) as originally planned.
