# Phase 3 Step 2 — Feature Store Schema & ML Feature Set Finalization

**Status:** Draft for review (v2 — Feature Store scoped to be model-agnostic; feature selection deferred to Step 4)
**Depends on:** Phase 3 Step 1 (roadmap/architecture, approved), EDA_REPORT.md (Phase 2 Step 10)
**Assumptions carried forward from Step 1 (unresolved open items, proceeding with defaults):**
- ATR-relative label addendum remains unscoped — not designed here, only referenced as a future Training Dataset build on top of this same Feature Store (Section 1).
- Calibration method (Platt vs. isotonic) remains a per-model choice, deferred to Step 4.

---

## 1. Feature Store: Purpose and Boundary

The Feature Store is the reusable, canonical dataset sitting between raw data and any model-specific artifact. It is **model-agnostic**: its job is to define how engineered features are stored, versioned, validated, and retrieved — not to decide which features a model should use. That decision is empirical and belongs downstream, after baseline models exist (Section 5).

**In scope (lives in the Feature Store):**
- All engineered features from the Phase 2 pipeline (`nifty_features.csv` lineage) — price-based, moving-average, momentum, volatility, and return-based features, as enumerated in the Phase 2 feature catalogue.
- A `Date` index (primary key, trading-day granularity).
- Feature-level metadata (Section 2).

**Out of scope (does NOT live in the Feature Store — lives downstream):**
- Label columns (`Label_Binary`, `Label_ThreeClass`, and any future ATR-relative label) — structurally excluded, not just conventionally excluded. This directly enforces the lookahead-leakage flag from Step 1 Section 10: a label column simply cannot be present at the point features are pulled for training.
- Any scaling/normalization — StandardScaler/RobustScaler/MinMaxScaler assignments (Step 1 Section 10) are applied per-fold, downstream, never baked into the store.
- `log1p(Volume)` transform — also applied downstream (Section 4), not stored pre-transformed, so the store retains raw values and the transform stays a visible, swappable pipeline step.
- Train/test split — the store is fold-agnostic; walk-forward slicing (Step 1 Section 4) happens after a Training Dataset is built from the store.
- **Feature selection** — the store carries the full engineered feature set, undiminished. Which subset a model actually trains on is decided empirically in Step 4 (Section 5), never here.

This boundary is what makes the ATR-relative label comparison (deferred per Step 1) cheap later: it's a new label-merge + preprocessing pass over the same store, not a feature-engineering re-run.

---

## 2. Storage Format, Versioning & Feature Metadata Schema

- **Format: Parquet**, not CSV, for the Feature Store specifically. Reasoning: dtypes are preserved natively (avoids the recurring float/int/object ambiguity CSV round-trips introduce), columnar storage is more efficient for the per-fold column subsets Step 3/4 will repeatedly read, and it supports partitioning if the store later grows (e.g. multi-instrument expansion beyond ^NSEI).
  - Config-driven fallback: if Antigravity's environment lacks parquet support, versioned CSV is the fallback — this is a config flag, not a hard dependency, consistent with existing project convention of config-driven paths/formats.
- **Versioning scheme:** `feature_store_v{N}.parquet` + a sidecar `feature_store_v{N}_manifest.yaml` containing generation timestamp, source file(s) and their hashes (e.g. `nifty_features.csv` checksum), row count, date range covered, and the full **feature metadata schema** below — one entry per feature.

### Feature Metadata Schema (per feature, in the manifest)

| Field | Description |
|---|---|
| `name` | Column name as it appears in the store |
| `source` | Upstream origin (e.g. `nifty_features.csv`, or "derived" if computed during Phase 2 feature engineering rather than pulled directly) |
| `feature_group` | Category, reusing the Step 1/EDA correlation taxonomy: structural / indicator / derived |
| `formula` | Exact computation, e.g. `RSI_14 = 100 - (100 / (1 + RS_14))`, or "raw passthrough" for fields like `Close` |
| `dtype` | e.g. `float64`, `int64` |
| `scaler_recommendation` | StandardScaler / RobustScaler / MinMaxScaler / none, per Step 1 Section 10's table |
| `lag` | Whether the feature is computed from a lagged/shifted value (e.g. `Daily_Return` uses `Close_{t-1}`), and how many periods; `0`/none if not lagged |
| `rolling_window` | Window size if the feature is a rolling computation (e.g. `RSI_14` → 14, `ATR_14` → 14, moving averages → their window); none if not applicable |
| `units` | e.g. "INR" for price fields, "%" for return/percentage fields, "index points" for `Volume`-adjacent or unitless indicators, "dimensionless" for oscillators like RSI |
| `nullability` | Whether the feature can be null and under what condition (e.g. `RSI_14` null only for rows before the rolling window is filled — not applicable post-2014 per Step 1 Section 4; most features non-nullable within the 2014+ range) |

This schema is what makes the store self-documenting — a consumer (Step 3, Step 4, or a future addendum) can inspect the manifest and know exactly what a column means, how it was derived, and how it should be treated, without re-reading the Phase 2 spec chain.

---

## 3. Feature Set Carried Into the Store

The store carries forward the full engineered feature set from `nifty_features.csv` as validated in Phase 2 (price/OHLC-derived, moving-average family, momentum indicators including `RSI_14` and `MACD`/`MACD_Hist`, volatility via `ATR_14`, and return-based features `Daily_Return`/`Log_Return`, plus `Volume`) — no feature is dropped at this stage, consistent with the model-agnostic boundary in Section 1.

- **RSI warm-up artifact (`RSI_14` pinned at 100.0 for first 13 rows):** confirmed to fall entirely within the 2007 start of the series. Since Phase 3 training folds start at 2014 (Step 1 Section 4), this artifact does not intersect any fold's training or test window. No masking logic is needed in the store or downstream — noted here so it isn't rediscovered as a false alarm later. Captured in the metadata schema's `nullability`/warm-up note for `RSI_14`.
- **Zero-volume days:** the known 2007–2013 zero-inflation is excluded by the fold start date, but isolated zero-volume days may still occur post-2014 (e.g. exchange holidays misaligned with the calendar). These are **not** removed automatically (no-automated-removal principle) — they pass through to `log1p(Volume)` downstream, where `log1p(0) = 0` handles them numerically without a special case, and any that look anomalous get flagged through the existing `known_events.yaml` mechanism rather than silently dropped.

---

## 4. Downstream Preprocessing Pipeline (Training Dataset build, per fold)

This is the sequence that runs **after** pulling from the Feature Store, per walk-forward fold (Step 1 Section 4):

1. Load `feature_store_v{N}.parquet` (full feature set, undiminished — no selection applied yet).
2. Merge the chosen label version (Version B, fixed ±0.50%, per Step 1 Section 3) on `Date`.
3. Apply `log1p(Volume)` to the `Volume` column.
4. Slice into the fold's train/test windows (walk-forward boundaries + optional purge/embargo gap, per Step 1 Section 4 — currently 0).
5. Fit the per-column scaler (StandardScaler / RobustScaler / MinMaxScaler per Step 1 Section 10's table) **on the training window only**, transform both train and test windows with it.
6. Hand off the full feature set to Step 4. Feature selection (Section 5) happens empirically inside Step 4, after baseline models are trained — it is not applied here.
7. Assert label columns are not present in the feature matrix (hard check, not a convention — raises an error if `Label_Binary`/`Label_ThreeClass` is found among model inputs).

Steps 2–7 are re-run per fold in the walk-forward loop (scaler refit each fold, since it's fit train-only); step 1 (loading the store) happens once per Training Dataset build.

---

## 5. Feature Selection Strategy (methodology only — executed in Step 4, not here)

No model is trained and no feature is removed in Step 2. This section defines *how* selection will be done once baseline models exist, so Step 4 has a pre-agreed methodology to implement rather than an open-ended choice.

- **When it happens:** after Step 4's baseline models (Logistic Regression, Decision Tree, Random Forest, XGBoost/LightGBM) are trained on Fold 1, using their outputs — not as a separate up-front modeling exercise.
- **Candidate methods** (Step 4 selects/combines as appropriate per model type, documented in Step 4's own spec):
  - **Tree-based native importance** — available directly from Random Forest / XGBoost / LightGBM, effectively free once those models are trained anyway.
  - **Permutation importance** — model-agnostic, applicable to Logistic Regression as well as tree models; more reliable than native importance when structural near-duplicates are present (per the EDA correlation report's own flag).
  - **SHAP values** — for a more granular, per-prediction view of feature contribution, useful for the tree-based models in particular, and for sanity-checking whether a feature's importance is stable across the dataset or driven by a handful of regime-specific rows.
  - **Recursive Feature Elimination (RFE)** — as an optional cross-check against the ranking produced by the methods above, particularly useful if the ranked list from importance methods is ambiguous in the middle (not obviously KEEP or REMOVE).
- **Cross-reference with the existing correlation taxonomy:** for any pair flagged `REMOVE CANDIDATE` in the Phase 2 correlation report, whichever member ranks lower empirically (by the methods above) is the one dropped — resolving the deferred "predictive correlation roadmap" item from Phase 2 with an actual label-based signal, but only once that signal exists.
- **Which fold's data is used for selection:** Fold 1's training window only (2014–2018), to avoid leaking information into later folds' test data and to keep the selected feature set fixed across all subsequent folds for a fair fold-by-fold comparison. (This constraint is fixed now; the models and importance computation are not.)
- **Output (produced in Step 4, not Step 2):** a `feature_selection_v1.yaml` artifact recording the full ranked list, which features were dropped and why, and the exact model/method/seed used for reproducibility.

---

## 6. Feature Store Validation Stage

Every Feature Store build (new version cut, per Section 2) runs an automated validation pass before the version is considered usable downstream. This is a build-time gate, not a one-off manual check:

- **Schema integrity:** every column present in the manifest (Section 2) exists in the parquet file, and no undocumented columns exist in the file that aren't in the manifest.
- **Data types:** each column's actual dtype matches its declared `dtype` in the metadata schema.
- **Duplicate dates:** `Date` is asserted unique — no duplicate trading-day rows.
- **Expected columns:** the full expected feature list (from the prior store version, or an explicit expected-columns config on first build) is present; any addition or removal versus the previous version is flagged explicitly rather than passing silently.
- **Row counts:** row count is checked against the expected trading-day count for the covered date range (via `pandas-market-calendars`, already in use for NSE holiday validation) — a mismatch indicates a gap or an unexpected extra row.
- **Missing-value summary:** a per-column null count/percentage is generated and compared against the `nullability` expectation in the metadata schema (Section 2) — e.g. `RSI_14` should show zero nulls given the 2014+ range; any column showing unexpected nulls fails validation rather than being silently passed through.
- **Schema checksum:** a hash of the manifest's schema (column names + dtypes + order) is computed and stored; this lets any downstream consumer (Step 3, Step 4) cheaply verify it's reading a store version with the schema it expects, without re-parsing the full manifest.

Validation output is a `feature_store_v{N}_validation_report.yaml`, saved alongside the manifest. A failed validation blocks the store version from being consumed downstream — consistent with the project's existing discipline of reviewing each artifact before the next step begins.

---

## 7. Open Decisions for Review

1. Parquet as the default Feature Store format, with versioned CSV as config-driven fallback — confirm, or state a hard preference either way.
2. Whether the validation stage (Section 6) should hard-fail the build on any violation, or allow a configurable warn-only mode for non-critical checks (e.g. missing-value summary) while still hard-failing on schema/duplicate-date/checksum issues.
3. Whether `feature_selection_v1.yaml` (produced in Step 4, per Section 5) is treated as final for all of Phase 3, or revisited if the ATR-relative label addendum (still unscoped) turns up different importances later.
