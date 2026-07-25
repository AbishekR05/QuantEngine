# Phase 3 Step 4 — Baseline Model Benchmarking: Implementation Specification

**Status:** Draft for review
**Depends on (frozen, not re-discussed here):** Step 1 (ML Architecture), Step 2 (Feature Store Spec + Implementation), Step 3 (Walk-Forward Spec + Implementation)
**Consumed by:** Antigravity
**Out of scope for this document:** hyperparameter optimisation, explainability/SHAP, backtesting, paper trading, live inference, trading strategy logic, any change to Feature Store, Walk-Forward framework, label strategy, or leakage prevention.

---

## 1. Purpose and Scope Boundary

This module trains and benchmarks the five approved baseline models across the walk-forward folds produced by Step 3, and evaluates them using classification and probability-quality metrics. The objective is **benchmarking, not optimisation** — no model here is tuned; each is run with fixed, reasonable, config-declared defaults.

**Scope boundary relative to Step 1's original roadmap (not a redesign — a clarification of where this document sits):** Step 1 Section 6 defined promotion as a combination of classification metrics *and* backtested trading metrics (Sharpe, Profit Factor, Drawdown, cumulative return). Backtesting is out of scope for this document per instruction. Consistent with Step 1's own step sequence (Section 8), which separated "Step 4 — baseline training + evaluation" from "Step 6 — full evaluation & backtest framework," this document produces the **classification/calibration-based benchmarking result** and a **provisional viability gate** (Section 10). Final trading-metric-based promotion remains Step 6's responsibility and is not performed here.

---

## 2. Baseline Model Catalogue

Five models, each run as a fixed-configuration benchmark — no tuning loop, no search:

| Model | Role as Benchmark |
|---|---|
| Logistic Regression (multinomial) | Linear floor — establishes whether the problem has meaningful linear separability at all. |
| Decision Tree | Single-tree non-linear floor — cheap sanity check on non-linear structure before ensembling. |
| Random Forest | Bagged-ensemble benchmark — variance reduction over a single tree, native feature importance available. |
| XGBoost | Boosted-ensemble benchmark — typically the strongest tabular-data baseline; sets the bar tuning would need to clear later. |
| LightGBM | Second boosted-ensemble benchmark — included alongside XGBoost for a cross-check, since the two occasionally rank differently on the same tabular features. |

Each model uses one fixed default configuration for this benchmarking pass (e.g. `n_estimators=100` for Random Forest, default learning rate for XGBoost/LightGBM) — the exact default values are declared in the configuration schema (Section 11), not chosen ad hoc per fold or per model run.

---

## 3. Training Workflow

For each model in the catalogue, per fold (Step 3 output):

1. Receive `(train_df, test_df, fold_metadata)` from the Walk-Forward module (Step 3) — already scaled, leakage-checked, and label-merged. This module does not re-slice, re-scale, or re-validate that data; it consumes it as-is.
2. Instantiate the model with its fixed default configuration (Section 11) plus **class weighting enabled** (`class_weight='balanced'` for Logistic Regression/Decision Tree/Random Forest; `scale_pos_weight`/equivalent per-class weighting for XGBoost/LightGBM), per Step 1 Section 5's requirement — enabled by default, not conditional on observed imbalance.
3. Fit on `train_df`'s features against `Label_ThreeClass`.
4. Predict class probabilities on `test_df` (raw, pre-calibration).
5. Compute raw evaluation metrics on these raw outputs (before calibration) and save them.
6. Apply probability calibration (Section 5) to the raw output using the configured calibration fitting cross-validation strategy (`cv` parameter in model configs).
7. Compute calibrated evaluation metrics on the calibrated probability output.
8. Persist fold-level artifacts (Section 8), keeping both raw and calibrated results.

A fixed random seed is set per model per fold (Section 7) — the same seed value is reused across all folds for a given model, not re-randomized per fold, so fold-to-fold performance differences reflect data, not seed variance.

---

## 4. Fold Execution Workflow

- Folds are executed **sequentially in fold order** (Fold 1 → Fold 8), not in parallel, so that any fold-level failure (per Step 3 Section 7's validation checks) halts before wasting compute on subsequent folds — consistent with the project's existing discipline of reviewing each artifact before proceeding.
- Each of the 5 models runs across all 8 folds independently — a full benchmarking pass is `5 models × 8 folds = 40` train/evaluate cycles.
- Models are independent of one another within a fold — Model B's training is not affected by Model A's results. Execution order across models within a fold is not significant and may run in any order (or in parallel across models, since they don't share state), but fold order must remain sequential.
- Fold 8's partial-year status (per Step 3 Section 6 metadata) is carried through into this module's metrics reporting (Section 6) — its results are reported but flagged, not silently averaged in with full-year folds.

---

## 5. Probability Calibration

Per Step 1 Section 6, calibrated probabilities — not raw model output — are what gets evaluated, persisted, and would eventually be consumed downstream.

- Each model's raw probability output is passed through `CalibratedClassifierCV` (or equivalent), fit **on the training window only**, using the same leakage-isolation discipline as the feature scalers (Step 3 Section 5).
- The cross-validation strategy for calibration is explicitly configured via the `cv` configuration parameter (Section 11) (e.g. using `cv=5` internal cross-validation or `cv="prefit"` with a validation split) to prevent training leakage or data starvation.
- Calibration method (Platt scaling vs. isotonic regression) is a **per-model config value** (Section 11), left open per Step 1's original deferral — this document does not force a single method across all five models. A reasonable starting default is declared in configuration but is not treated as final.
- Calibration quality is itself measured (Brier score, and a reliability diagram artifact) per model per fold — a model is not considered adequately calibrated just because the step ran; the check has to actually hold on that fold's test window.

---

## 6. Evaluation Methodology and Metrics

Computed per model, per fold, both on raw (pre-calibration) and calibrated test-set predictions:

- **Classification metrics:** Macro F1; per-class Precision/Recall/F1 for `BUY`, `HOLD`, `SELL` individually (`BUY`/`SELL` given particular attention, per Step 1 Section 6, since `HOLD` is the majority class); full confusion matrix. Computed and logged independently for both raw outputs and calibrated outputs.
- **Calibration metrics:** Brier score; reliability diagram data (binned predicted-probability vs. observed frequency).
- **Class balance context:** actual class distribution of that fold's test window, reported alongside the metrics above — not to score the model, but so a metric shift can be checked against a possible distribution shift before being read as a model defect.
- No trading/backtest metric (cumulative return, Sharpe, Profit Factor, Drawdown) is computed in this module — those belong to Step 6, per Section 1's scope boundary.

---

## 7. Reproducibility Requirements

- **Fixed seeds:** one seed value per model, declared in configuration (Section 11), reused identically across all 8 folds for that model.
- **Config snapshot:** the exact configuration used for a benchmarking run (model defaults, class-weighting setting, calibration method per model, seed values, Feature Store version, label version, Walk-Forward run ID) is serialized and saved alongside the run's artifacts — a run must be fully reconstructable from its saved config alone.
- **Library version pinning:** the versions of scikit-learn, XGBoost, and LightGBM used are recorded in the run's metadata. XGBoost/LightGBM determinism across versions/hardware is not guaranteed bit-for-bit even with a fixed seed — this is recorded as a known limitation, not silently assumed away.
- **No silent defaults:** any configuration value not explicitly set falls back to a documented default recorded in the run's config snapshot, not an unlogged library default.

---

## 8. Experiment Artifacts

Per model, per fold:

- Trained model (serialized)
- Calibrated prediction probabilities on the test window
- Raw (pre-calibration) prediction probabilities, retained for calibration-quality comparison
- Confusion matrix (saved for both raw and calibrated prediction thresholds)
- Metrics record (Section 6, saving both raw and calibrated metrics as structured data — not just a printed report)
- Native feature importance, where available (Random Forest, XGBoost, LightGBM natively; Logistic Regression coefficients; Decision Tree native importance) — recorded for later reference by Step 5's empirical feature-selection work. **These feature importance outputs are strictly informational/exploratory and must not influence feature selection or pruning during this phase.**
- Evaluation summary (human-readable rollup of the above)

Per model, aggregated across all 8 folds:

- Cross-fold metrics summary (mean, standard deviation, per-fold breakdown, Fold 8 flagged separately per Section 4)
- Calibration quality summary across folds

Per benchmarking run (all 5 models):

- A single cross-model comparison table (Section 9)
- The reproducibility config snapshot (Section 7)

**Naming/versioning convention:** `benchmark_runs/{run_id}/{model_name}/fold_{n}_*`, where `run_id` ties back to the Feature Store version + label version + Walk-Forward run ID combination used, consistent with Step 3 Section 9's artifact convention.

---

## 9. Cross-Model Comparison

A single comparison artifact (`benchmark_comparison.yaml` or equivalent tabular format) presents, per model:

- Cross-fold mean and standard deviation for each classification metric (Section 6)
- Cross-fold mean and standard deviation for Brier score
- A fold-stability indicator — e.g. whether performance in any single fold deviates from that model's own cross-fold mean by more than a configurable threshold (Section 11), surfacing instability without applying a pass/fail judgment at this stage
- Fold 8 (partial year) shown as a separate column, not folded into the mean

This table is descriptive — it ranks and reports, it does not itself decide which model advances. That decision is Section 10.

---

## 10. Provisional Viability Gate (not final promotion — see Section 1)

Before any model's results are handed to Step 5 (advanced tier decision) or Step 6 (backtest-based promotion), a minimal viability check is applied:

- **Naive baseline comparison:** a trivial "always predict `HOLD`" (majority class) baseline is computed against the same folds, using the same metrics (Section 6). This is not one of the five catalogue models — it exists purely as a floor.
- **Viability condition:** a benchmarked model must exceed the naive baseline's Macro F1 by a configurable margin (Section 11) on a majority of folds (e.g. at least 5 of 8) to be considered viable at all.
- Models that fail this floor are still fully reported (Section 8/9) — they are not deleted or hidden — but are flagged as **not viable** in the comparison artifact, distinguishing "this model underperforms trivial guessing" from "this model is a legitimate but weaker benchmark."
- Passing this floor does **not** constitute promotion — it only means the model's results are eligible to be carried into Step 6's backtest-based evaluation. Step 1 Section 6's actual promotion gate (trading metrics, stability) is executed there, not here.

---

## 11. Configuration Schema

```yaml
baseline_benchmarking:
  models:
    logistic_regression:
      seed: 42
      class_weight: "balanced"
      calibration_method: "platt"      # per-model, not forced project-wide
      calibration_cv: 5                # validation strategy for CalibratedClassifierCV
    decision_tree:
      seed: 42
      class_weight: "balanced"
      calibration_method: "isotonic"
      calibration_cv: 5
    random_forest:
      seed: 42
      n_estimators: 100
      class_weight: "balanced"
      calibration_method: "isotonic"
      calibration_cv: 5
    xgboost:
      seed: 42
      n_estimators: 100
      learning_rate: 0.1
      scale_pos_weight_mode: "balanced"
      calibration_method: "platt"
      calibration_cv: 5
    lightgbm:
      seed: 42
      n_estimators: 100
      learning_rate: 0.1
      class_weight: "balanced"
      calibration_method: "platt"
      calibration_cv: 5
  viability_gate:
    metric: "macro_f1"
    min_margin_over_naive_baseline: 0.05
    min_passing_folds: 5
  stability_threshold: 0.10   # max allowed per-fold deviation from a model's own cross-fold mean, before flagging instability (Section 9)
  feature_store_version: "v1"
  label_version: "version_b"
  walk_forward_run_id: "<from Step 3>"
```

- All model defaults above are illustrative starting values, declared explicitly so a run's config snapshot (Section 7) is never ambiguous — not tuned or optimised.

---

## 12. Open Decisions

1. Calibration method defaults shown per model (Section 11) are a reasonable starting assignment, not a settled choice — confirm, or leave fully open for Antigravity to set per model's actual raw-score behavior during implementation.
2. `min_margin_over_naive_baseline` (0.05) and `min_passing_folds` (5 of 8) in the viability gate are placeholder values — confirm or adjust before implementation.
3. Whether cross-model execution (Section 4) should run in parallel (independent models, no shared state) for speed, or remain strictly sequential for simplicity/log-readability during this first benchmarking pass.
