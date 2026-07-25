# QuantEngine: Phase 3 (Machine Learning) - Feature Store & Walk-Forward Split Report

This report outlines the implementation details and outputs generated during the initial steps of **Phase 3 (Machine Learning Pipeline)**.

---

## 1. Phase 3 Objectives & Roadmap
Phase 3 transitions the QuantEngine project from descriptive data analysis to predictive modeling. The primary target is building a **decision classifier** for the Nifty 50 Index (`^NSEI`) that outputs one of three trading decisions:
- `CALL` (Directional Long)
- `PUT` (Directional Short)
- `NO_TRADE` (Sideways / Low-Volatility conditions)

---

## 2. Resolved Architectural Decisions (Step 1)
During Step 1 (ML Roadmap & Architecture Spec), the following key structural points were finalized:
1. **Target Labels**: Baseline experiments utilize the `Label_ThreeClass` column (Version B: fixed ±0.50% return threshold) computed in Step 8. An ATR-relative label option is scoped as an architectural placeholder to be integrated after baseline models establish a performance floor.
2. **Probability Calibration**: Calibration is treated as a per-model decision to be configured inside the training spec, supporting Platt scaling and isotonic regression evaluated dynamically across walk-forward folds.
3. **Walk-Forward Validation**: Model validation follows a rolling-origin walk-forward strategy anchored at the year **2014** to exclude Nifty's historical zero-volume data-feed limitations (2007–2013).

---

## 3. Feature Store Architecture & Boundaries (Step 2)
Step 2 implements a canonical, model-agnostic **Feature Store** designed to decouple raw feature engineering from downstream labeling and model-specific configurations.

### Structural Boundaries
- **In-Scope (Stays in the Store)**: The 22 price-based, moving-average, momentum, and volatility indicators computed during feature engineering, indexed by `Date`.
- **Out-of-Scope (Deferred to downstream pipeline)**:
    - **Target Labels**: Stored independently in `data/labels/` and merged downstream. This structurally enforces the prevention of time-series lookahead leakage (a label is never present in raw training arrays).
    - **Feature Scaling**: Scaler values (Standard, Robust, MinMax) are fit strictly on training splits to prevent lookahead bias.
    - **Preprocessing Transforms**: Logarithmic transforms (e.g. `log1p(Volume)`) are applied dynamically on read.

---

## 4. Walk-Forward Slicing & Validation Slices (Step 3)
Step 3 implements the calendar-based expanding-window walk-forward validation splitter to divide the Training Dataset into fold-sliced files.

### Slicing & Boundaries schedule:
- **Anchored Start**: 2014-01-01.
- **Schedule Strategy**: Expanding training window, rolling 1-year testing window.

| Fold | Training Window | Testing Window | Status |
| :--- | :--- | :--- | :--- |
| **Fold 1** | 2014-01-02 to 2018-12-31 | 2019-01-02 to 2019-12-31 | **`PASS`** |
| **Fold 2** | 2014-01-02 to 2019-12-31 | 2020-01-02 to 2020-12-31 | **`PASS`** |
| **Fold 3** | 2014-01-02 to 2020-12-31 | 2021-01-01 to 2021-12-31 | **`PASS`** |
| **Fold 4** | 2014-01-02 to 2021-12-31 | 2022-01-03 to 2022-12-30 | **`PASS`** |
| **Fold 5** | 2014-01-02 to 2022-12-30 | 2023-01-02 to 2023-12-29 | **`PASS`** |
| **Fold 6** | 2014-01-02 to 2023-12-29 | 2024-01-01 to 2024-12-31 | **`PASS`** |
| **Fold 7** | 2014-01-02 to 2024-12-31 | 2025-01-01 to 2025-12-31 | **`PASS`** |
| **Fold 8** | 2014-01-02 to 2025-12-31 | 2026-01-01 to 2026-07-09 | **`PASS`** *(Partial Year)* |

### Preprocessing & Isolation:
1. **Fit-Transform Isolation**: For each fold, scalers (StandardScaler, MinMaxScaler, RobustScaler) are fit strictly on the `Date` training boundaries, and then applied to transform both the train and test subsets. This prevents any forward leakage of distribution moments (means, standard deviations, percentiles) from the test period.
2. **Purge/Embargo**: Configured with `embargo_days: 0` (default) since target return signals represent next-day $t+1$ transitions without overlap. The framework structurally supports adding embargo windows dynamically.

---

## 5. Leakage Prevention Checks
Hard assertions are run at runtime to validate data safety. Any failure halts the pipeline:
- **No Date Overlap**: Assures `max(train_df.Date) < min(test_df.Date) - embargo_days`.
- **Set Intersection Empty**: Assures no date sessions exist in both splits.
- **Label Exclusion**: Confirms target labels are separated from the feature input matrices.
- **Fold Independence**: Assures fitted scaler models are not reused across subsequent folds.

---

## 6. Generated Outputs & Directories
All artifacts are compiled under `data/walk_forward_runs/fs_v1_threeclass_embargo0/`:

- `fold_{n}_train.parquet` & `fold_{n}_test.parquet`: Sliced, train-fit scaled datasets.
- `fold_{n}_metadata.yaml`: Tracks date ranges, row counts, and config traceability hashes.
- `walk_forward_validation_report.yaml`: Summary run verification validating all 8 folds successfully passed leakage checks.
