# Phase 3 Step 3 — Walk-Forward Split Module: Implementation Specification

**Status:** Draft for review
**Depends on (frozen, not re-discussed here):** Phase 3 Step 1 (ML Architecture, Approved), Phase 3 Step 2 (Feature Store Specification, Approved)
**Consumed by:** Antigravity (code generation)
**Out of scope for this document:** model training, feature selection (Step 4), any change to Feature Store boundaries or schema (Step 2), any new ML technique.

---

## 1. Purpose of the Walk-Forward Module

This module takes a Training Dataset built from the Feature Store (per Step 2, Section 4's downstream pipeline) and produces the fold-sliced train/test datasets required for expanding-window walk-forward validation, as architecturally fixed in Step 1 Section 4. It is a data-slicing and validation module — it does not train, score, or select anything.

---

## 2. Fold Schedule and Boundaries (frozen — reproduced from Step 1, not redefined)

| Fold | Train Window | Test Window |
|------|-------------|-------------|
| 1 | 2014–2018 | 2019 |
| 2 | 2014–2019 | 2020 |
| 3 | 2014–2020 | 2021 |
| 4 | 2014–2021 | 2022 |
| 5 | 2014–2022 | 2023 |
| 6 | 2014–2023 | 2024 |
| 7 | 2014–2024 | 2025 |
| 8 | 2014–2025 | 2026 (partial year — through 2026-07-09) |

- Anchored/expanding start at 2014 is fixed (Step 1 Section 4) — this module does not re-derive or justify that boundary, only implements it.
- Fold count, anchor year, and window length are read from configuration (Section 8), not hardcoded — the table above is the default configuration values, not a literal constant in code.
- Fold 8's partial-year status is carried as an explicit boolean flag in fold metadata (Section 6), not inferred downstream.

---

## 3. Dataset Generation Pipeline

Given a Feature Store version and a chosen label version (per Step 2's Training Dataset build), the module performs, per fold:

1. **Load** the merged features+label Training Dataset (already assembled per Step 2 Section 4, steps 1–3: Feature Store load, label merge, `log1p(Volume)`). This module does not re-implement that assembly — it consumes its output.
2. **Slice** rows into `train_df` and `test_df` using the fold's `Date` boundaries (Section 2) plus any configured purge/embargo gap (Section 4).
3. **Fit scaler(s)** per Step 2's per-column scaler table, fit on `train_df` only, transform `train_df` and `test_df`.
4. **Emit** the fold's `(train_df, test_df, fold_metadata)` tuple to the caller (Step 4's training loop) and, optionally, persist them as fold artifacts (Section 9).

This module owns steps 2–4 above. Step 1 (Training Dataset assembly) is Step 2's responsibility and is only invoked, not reimplemented, here.

---

## 4. Purge/Embargo Behaviour

- Config key: `embargo_days` (integer, default `0`), as fixed architecturally in Step 1 Section 4.
- **Behaviour when `embargo_days = 0` (current default):** train window ends at the last date `<` test window start; no gap. This is the active behaviour for the current `t+1` label.
- **Behaviour when `embargo_days > 0`:** the last `embargo_days` calendar days immediately preceding the test window's start date are excluded from the training window (neither trained on nor tested on) — i.e., `train_end = test_start - embargo_days`, `train_df` is sliced up to `train_end` rather than up to `test_start - 1`.
- Embargo is applied identically to every fold; it is a single global config value for a given walk-forward run, not fold-specific.
- This module implements the mechanism only. No value other than `0` is used or justified in this document — a future addendum (not this spec) would set `embargo_days > 0` if a longer-horizon or overlapping-label version is introduced.

---

## 5. Leakage Prevention

Implemented as hard assertions, each raising an error (not a warning) on violation:

- **No date overlap:** `max(train_df.Date) < min(test_df.Date) - embargo_days` must hold for every fold; violated → raise.
- **No test-window dates in train_df, and vice versa** — explicit set-intersection check on `Date`, not just a boundary-value check, to catch any upstream indexing bug.
- **Scaler fit isolation:** the scaler object(s) used to transform `test_df` must be the same object(s) fit on `train_df` for that fold — never refit on or exposed to `test_df`. Implemented by fitting once per fold and reusing the fitted transformer, not by re-fitting on combined data.
- **Label columns never enter the feature matrix:** re-asserts the Step 2 Section 4 check (label columns absent from `X_train`/`X_test`) at this module's boundary too, since this is the last point before data reaches Step 4.
- **No cross-fold leakage:** each fold's train/test slicing and scaler fitting is independent — fold `N`'s scaler or any fitted state must not be reused in fold `N+1`.

---

## 6. Fold Metadata

Each fold emits a metadata record (dict/YAML-serializable) alongside its data:

| Field | Description |
|---|---|
| `fold_id` | Integer, 1-indexed (per Section 2 table) |
| `train_start`, `train_end` | Dates bounding the training window (post-embargo, if any) |
| `test_start`, `test_end` | Dates bounding the test window |
| `embargo_days` | Value used for this run (Section 4) |
| `is_partial_test_year` | Boolean; `true` only for Fold 8 under the current schedule |
| `train_row_count`, `test_row_count` | Actual row counts after slicing |
| `feature_store_version` | Which `feature_store_v{N}` this fold was built from (Step 2 Section 2) |
| `label_version` | Which label version was merged (e.g. `Version B, fixed ±0.50%`, per Step 1 Section 3) |
| `scaler_config_hash` | Hash of the per-column scaler assignment used, for reproducibility traceability |

---

## 7. Validation Checks

Run automatically for every fold before it is handed off or persisted:

- All checks in Section 5 (leakage prevention) pass.
- `train_row_count` and `test_row_count` are both `> 0` (an empty window fails loudly rather than silently producing a degenerate fold).
- `Date` is unique within `train_df` and within `test_df` independently (duplicate-date check, consistent with Step 2 Section 6's store-level check, re-verified at the fold level).
- No unexpected `NaN` values in the feature matrix post-scaling, other than those already documented as expected nullability in the Feature Store manifest (Step 2 Section 2) — a `NaN` outside that expectation fails the fold rather than passing through to Step 4.
- Fold boundaries in the emitted metadata (Section 6) exactly match the configured schedule (Section 8) — guards against an off-by-one or timezone-related slicing bug.

A failed fold blocks that fold from being consumed downstream; it does not silently skip to the next fold.

---

## 8. Configuration Schema

All values below are config-driven, not hardcoded, per existing project convention:

```yaml
walk_forward:
  anchor_start_year: 2014
  fold_schedule: "expanding"        # "expanding" | "rolling" (rolling reserved for future use, not active now)
  folds:
    - {train_end_year: 2018, test_year: 2019}
    - {train_end_year: 2019, test_year: 2020}
    - {train_end_year: 2020, test_year: 2021}
    - {train_end_year: 2021, test_year: 2022}
    - {train_end_year: 2022, test_year: 2023}
    - {train_end_year: 2023, test_year: 2024}
    - {train_end_year: 2024, test_year: 2025}
    - {train_end_year: 2025, test_year: 2026, partial: true}
  embargo_days: 0
  feature_store_version: "v1"        # references Step 2 versioning scheme
  label_version: "version_b"         # fixed ±0.50%, per Step 1 Section 3
  persist_fold_artifacts: true       # controls Section 9 output
```

- `fold_schedule: "rolling"` is defined in the schema for forward compatibility but is not implemented/exercised by this spec — expanding is the only active mode, per Step 1's frozen decision.

---

## 9. Generated Artifacts

Per walk-forward run:

- `fold_{n}_train.parquet`, `fold_{n}_test.parquet` — sliced, scaled datasets (only if `persist_fold_artifacts: true`; otherwise held in memory and passed directly to Step 4).
- `fold_{n}_metadata.yaml` — the record defined in Section 6.
- `walk_forward_validation_report.yaml` — aggregate pass/fail status of Section 7's checks across all folds in the run, so a caller can check one file to confirm the whole run is leakage-clean before proceeding to Step 4.

Naming and directory convention: `walk_forward_runs/{run_id}/fold_{n}_*`, where `run_id` ties back to the `feature_store_version` + `label_version` combination used.

---

## 10. Open Decisions

1. Whether `persist_fold_artifacts` defaults to `true` (disk-persisted, reproducible, more storage) or `false` (in-memory only, lighter, less traceable) for routine Step 4 runs.
2. Whether the `walk_forward_validation_report.yaml` failure mode should halt the entire run on the first failing fold, or run all folds and report all failures together.
