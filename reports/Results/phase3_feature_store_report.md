# QuantEngine: Phase 3 (Machine Learning) - Feature Store Implementation Report

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

## 4. Technical Implementation & Formats
1. **Parquet Format**: The Feature Store is saved as a Parquet file (`feature_store_v1.parquet`) using the `pyarrow` engine. Columnar storage ensures native data type conservation and fast partial reads during fold-level training.
2. **YAML Manifest**: A sidecar manifest metadata sheet (`feature_store_v1_manifest.yaml`) details the file checksum, record counts, date ranges, and a feature catalog mapping every column's formula, rolling window, lag index, and scaling recommendation.
3. **Automated Validation Report**: Every feature store build runs a validation suite (`feature_store_v1_validation_report.yaml`) enforcing:
    - **Schema Integrity**: Validates actual columns against manifest metadata.
    - **Dtype Alignment**: Enforces strict casts for float64 and int64 values.
    - **Uniqueness Check**: Assures `Date` values contain no duplicates.
    - **Post-2014 Null Check**: Asserts that all indicators are fully warmed up (contain zero nulls) within the training/validation boundaries.

---

## 5. Generated Outputs & Metrics
The pipeline was executed and generated the following outputs under `data/feature_store/`:

| Output File Name | Format | Size / Rows | Purpose |
| :--- | :--- | :--- | :--- |
| `feature_store_v1.parquet` | Parquet | 4,613 rows | Canonical feature dataset (22 indicators + Date) |
| `feature_store_v1_manifest.yaml` | YAML | 252 lines | Sidecar manifest detailing schema checksum & column metadata |
| `feature_store_v1_validation_report.yaml` | YAML | 34 lines | Run-time validation report showing PASS status |

### Audit Summary:
- **Total Sessions**: 4,613 trading days (from `2007-09-17` to `2026-07-09`).
- **Validation Status**: **`PASS`** (overall_pass: true).
- **Post-2014 Warmup Null Count**: **`0`** (confirmed all indicators are fully computed).
- **Schema Checksum**: Evaluated unique SHA-256 schema signature to check downstream readers' compatibility.

---

## 6. Downstream Preprocessing & Leakage Checks
The Feature Store Manager exposes `build_training_dataset` which compiles model-ready matrices:
- Merges selected labels (`Label_ThreeClass` or `Label_Binary`).
- Compresses Volume skewness using `log1p(Volume)`.
- Performs a **hard validation check** asserting that no target column is present among feature inputs, raising an exception if lookahead indicators are detected.
