# Phase 3 Step 6 — Model Explainability: Implementation Specification

**Status:** Draft for review
**Depends on (frozen, not re-discussed here):** Step 1 (Architecture), Step 2 (Feature Store), Step 3 (Walk-Forward), Step 4 (Baseline Benchmarking), Step 5 (Hyperparameter Optimization)
**Consumed by:** Antigravity
**Frozen models entering this step:** Logistic Regression (Step 5 best trial), XGBoost (Step 5 best trial). Both are treated as final, trained artifacts — nothing about either model changes here.
**Roadmap note:** the original Step 1 sequence reserved "Step 6" for the backtest framework, with explainability only noted as a possible future addition. This document is being registered as Step 6 per current instruction; the backtest framework is renumbered to Step 7 as a consequence, not a redesign of its content.

---

## 1. Scope and Objectives

Step 6 explains **how** the two frozen models — Logistic Regression and XGBoost — arrive at their predictions. It is exclusively interpretability work. No model is retrained, retuned, modified, or replaced. The step exists to answer four questions, each addressed in later sections:

- Which features drive predictions, for each model.
- Whether the learned behavior is economically reasonable (i.e., feature direction/importance aligns with plausible market logic, not an artifact).
- Whether either model appears to rely on spurious correlations (e.g. a structurally near-duplicate feature dominating for no defensible reason).
- Whether feature importance is stable across walk-forward folds, or whether it drifts fold-to-fold in a way that would undermine trust in a single "the model uses X" narrative.

This step produces **data and reports**, not judgments baked into code — the economic-reasonableness question in particular is answered by a human reading the generated reports, not by a pass/fail assertion this module computes.

---

## 2. Inputs and Outputs

**Inputs:**
- Per-fold trained model artifacts from Step 5's best trial for each eligible model (`hpo_runs/{run_id}/best_trial/` per model, Step 5 Section 13) — loaded as-is, never refit.
- Per-fold `train_df`/`test_df` from Step 3 (for SHAP background data and evaluation inputs respectively — Section 5).
- Step 2's feature metadata schema (`feature_group`, `units`, `formula` per feature) — used to annotate explainability reports with human-readable context, not recomputed.

**Outputs:**
- Per-fold, per-model interpretation artifacts (Sections 6–10).
- Cross-fold stability analysis, per model (Section 11).
- A single cross-model comparison report (Section 12).
- All reports listed in Section 15, in machine-readable form.

---

## 3. Explainability Philosophy

- **No global, full-dataset model is used for convenience.** Every explanation — coefficient or SHAP value — is generated from that fold's already-trained model (Step 5's per-fold artifact), evaluated only against that fold's own data. A single "overall" explanation computed by refitting on the entire date range would violate the walk-forward discipline this project has maintained since Step 3, purely to save engineering effort, and is explicitly rejected.
- **Explanations are diagnostic, not corrective.** Nothing produced here feeds back into feature selection, feature engineering, or model configuration within this step. If a report surfaces something that looks like a spurious correlation, that is written up as a finding — acted on, if at all, in a future step or addendum, never silently patched here.
- **Method choice is matched to model structure**, not applied uniformly: Logistic Regression is explained through its own coefficients (an exact, deterministic property of the fitted model — no approximation needed); XGBoost is explained through SHAP (TreeSHAP specifically, Section 8), since a tree ensemble has no single global coefficient to read off directly.

---

## 4. Eligible Models

Both models carried forward from Step 5 are in scope — there is no additional viability filter applied at this step. Unlike Step 5's optimization eligibility (data-driven from Step 4's gate), explainability is run for **every model Step 5 actually produced a best trial for**, regardless of that model's earlier viability-gate outcome, because understanding *why* a borderline model (XGBoost) behaves the way it does is itself one of this step's stated purposes (Section 1).

| Model | Source Artifact | Explainability Method |
|---|---|---|
| Logistic Regression | Step 5 best trial, per fold | Coefficient analysis (Section 6) |
| XGBoost | Step 5 best trial, per fold | SHAP / TreeSHAP (Sections 7–10) |

---

## 5. Walk-Forward Explainability Workflow

Per model, per fold (Folds 1–8, Step 3 boundaries, unchanged):

1. Load that fold's trained model artifact from Step 5's best-trial output — not refit, not re-instantiated with new data.
2. Load that fold's `train_df` (used only as SHAP's background reference distribution for XGBoost, Section 8 — Logistic Regression's coefficients need no background data) and `test_df` (used as the evaluation set for both models' explanations).
3. Generate the model-appropriate explanation artifacts (Sections 6–10) using only this fold's model and this fold's train/test data.
4. Persist fold-level explainability artifacts (Section 13).
5. Fold 8's partial-year status (Step 3 Section 6 metadata) is carried through into reporting exactly as in Steps 4/5 — included in per-fold output, excluded from any full-year aggregate.

No explanation computed for fold *N* uses any data or model state from fold *N+1* or later — this is the same forward-only discipline already enforced for training and calibration, applied here to interpretation instead.

---

## 6. Logistic Regression Interpretation

Computed per fold, from that fold's fitted coefficients:

- **Raw coefficients:** the fitted coefficient vector, one value per feature per class (multinomial — `BUY`, `HOLD`, `SELL` each get their own coefficient row), exactly as stored in the model artifact.
- **Standardized coefficients:** since features arrive at the model pre-scaled per Step 2/3 (with different scalers — StandardScaler, RobustScaler, MinMaxScaler — assigned per feature, per Step 2's metadata schema), raw coefficient magnitudes are not directly comparable across features scaled differently. Standardized coefficients are computed by multiplying each raw coefficient by that feature's training-fold standard deviation (computed from `train_df`, the same fold's training data — no leakage from `test_df`), producing a comparable "effect per one-standard-deviation move" value regardless of which scaler a feature originally used.
- **Coefficient ranking:** features ranked by absolute standardized coefficient, per class, per fold.
- **Sign interpretation:** for each feature, whether its coefficient sign is consistent with the class it's associated with (e.g. a positive `RSI_14` coefficient on the `BUY` class is directionally what momentum logic would predict) — the interpretation itself (is this "economically reasonable") is written into the report as a plain-language note tied to the feature's `formula`/`feature_group` metadata (Step 2), not inferred automatically.
- **Feature direction analysis:** for each feature, whether its sign is **consistent across all 8 folds** or flips — a flipping sign across folds is flagged explicitly, since that's a direct, cheap signal of an unstable rather than a genuinely predictive relationship.

---

## 7. XGBoost Interpretation

Computed per fold, from that fold's fitted XGBoost model:

- **Native gain-based importance:** XGBoost's built-in feature importance (`gain`, `weight`, `cover` — all three recorded, since they can disagree and each tells a different part of the story: `gain` reflects average improvement per split, `weight` reflects how often a feature is used, `cover` reflects how many samples a feature's splits affect).
- **SHAP-based importance:** the primary interpretation method for this model (Section 8), since native importance is known to be less reliable in the presence of correlated features — which the project's own EDA correlation report has already established exist in this feature set.

---

## 8. SHAP Analysis Strategy

- **Explainer type: TreeSHAP** (exact, not the sampling-based KernelSHAP) — XGBoost's tree structure supports exact SHAP computation efficiently, and exactness also satisfies the reproducibility/determinism requirement (Section 16) without needing a fixed sampling seed for the core value computation itself.
- **Background dataset:** that fold's `train_df` (or a fixed-size random subsample of it, seeded per Section 14, if the full training window is large enough that using it whole is computationally excessive) — never `test_df`, and never data outside the fold's own training window. This mirrors the same train-only-fitting discipline used for scalers (Step 2/3) and calibration (Step 4/5).
- **Evaluation set:** SHAP values are computed for predictions on that fold's `test_df` — this is what gets reported as "why did the model predict this" for that fold's actual test period.
- **Feature interaction values:** SHAP interaction values (pairwise) are computed only if the fold's evaluation set size is within a configured computational ceiling (Section 14) — interaction values are substantially more expensive than main-effect SHAP values. This is gated the same way Step 1 gated the Transformer/TFT advanced-tier model on dataset size: a computational affordability check, not a modeling decision. If the ceiling is exceeded, interaction analysis is skipped for that fold and the report notes it was skipped, rather than silently omitting it without explanation.

---

## 9. Global Feature Importance

Per fold, per model:

- **Logistic Regression:** ranked standardized coefficients (Section 6), taken as-is — there is no separate "global importance" computation distinct from the coefficients themselves for a linear model.
- **XGBoost:** mean absolute SHAP value per feature, across all rows in that fold's `test_df` — this is the primary global-importance figure for XGBoost, reported alongside (not instead of) the native gain/weight/cover values from Section 7, so a reader can see where the two methods agree or disagree.

A single **global feature ranking table per model** aggregates the per-fold rankings above (mean rank across Folds 1–7, full-year folds; Fold 8 shown separately) — this is a descriptive rollup, not a new computation on pooled data (no model is refit on pooled data to produce this table).

---

## 10. Local Prediction Explanations

For XGBoost, a fixed number of individual test-set predictions per fold (configurable, Section 14) are explained at the row level using that row's own SHAP values (the per-feature contribution to that specific prediction, relative to the background's expected value). Sample selection, per fold:

- A configurable number of **high-confidence correct predictions** (per class, where feasible) — illustrates what a "clean" decision looks like.
- A configurable number of **misclassified predictions** — illustrates where the model's reasoning diverges from the actual outcome, which is often more diagnostically useful than a correct-prediction example.
- Sample selection uses a fixed seed (Section 14) for reproducibility, and the exact row indices selected are recorded in the artifact so the same samples can be re-inspected later.

Logistic Regression does not require a separate local-explanation mechanism beyond Section 6: for a linear model, the local explanation for any single row is just that row's feature values multiplied by the (already-reported) coefficients — this is noted in the report rather than computed as a second, redundant artifact.

---

## 11. Feature Stability Across Folds

Per model, independently:

- **Rank correlation across folds:** Spearman rank correlation between each pair of folds' global feature-importance rankings (Section 9) — summarized as a fold × fold correlation matrix, per model.
- **Top-K stability:** what fraction of a fixed top-K feature set (K configurable, Section 14) is shared across all 8 folds, versus appearing in only some folds — a feature that's top-5 in one fold and absent from the top-15 in another is flagged explicitly.
- **Sign stability (Logistic Regression only):** carried over from Section 6's per-fold sign check, aggregated here into a single stability summary across all folds.
- Fold 8's partial-year status is excluded from the full-year stability aggregate but still computed and shown separately, consistent with the project's existing convention.

---

## 12. Model Comparison

A single comparison report, not computed per fold but built from each model's already-generated per-fold and aggregate artifacts (Sections 9–11):

- **Top-K overlap:** the overlap (e.g. Jaccard similarity) between Logistic Regression's top-K standardized-coefficient features and XGBoost's top-K mean-absolute-SHAP features, both globally (aggregate ranking) and per fold.
- **Directional agreement:** for features that appear in both models' top-K sets, whether the direction implied by Logistic Regression's coefficient sign (Section 6) agrees with the direction implied by XGBoost's SHAP dependence trend (Section 8) for that feature — a qualitative note per shared feature, not a single automated score.
- **Stability comparison:** side-by-side summary of each model's Section 11 stability results — which model shows more consistent feature usage across folds.

This report does not declare a "winner" — that judgment belongs to whoever reads it, informed by Step 4/5's separate performance results, not to this module.

---

## 13. Artifact Directory Structure

```
explainability_runs/{run_id}/
  logistic_regression/
    fold_{n}/
      coefficients_raw.yaml
      coefficients_standardized.yaml
      coefficient_ranking.yaml
      sign_analysis.yaml
    global_ranking.yaml
    stability_report.yaml
  xgboost/
    fold_{n}/
      native_importance.yaml          # gain, weight, cover
      shap_summary.yaml               # mean abs SHAP per feature
      shap_dependence_data.yaml       # raw feature-value vs SHAP-value pairs, for external plotting
      shap_interaction.yaml           # present only if fold's data size was within the computational ceiling (Section 8)
      local_explanations.yaml         # selected sample rows, per Section 10
    global_ranking.yaml
    stability_report.yaml
  model_comparison_report.yaml
  run_config_snapshot.yaml
```

`run_id` follows the same convention as Steps 3–5: tied to Feature Store version, label version, Walk-Forward run ID, and the Step 5 run ID whose best-trial artifacts were explained.

---

## 14. Configuration Schema

```yaml
explainability:
  enabled_methods:
    logistic_regression: ["coefficients", "standardized_coefficients", "sign_stability"]
    xgboost: ["native_importance", "shap_global", "shap_local", "shap_interaction"]
  shap:
    background_sample_size: 500        # subsample of train_df if larger than this
    interaction_row_ceiling: 2000      # skip interaction values above this test-set row count, per fold
    seed: 77
  local_explanations:
    n_correct_samples_per_class: 5
    n_misclassified_samples: 10
    seed: 77
  stability:
    top_k: 15
  output:
    base_directory: "explainability_runs"
  versioning:
    feature_store_version: "v1"
    label_version: "version_b"
    walk_forward_run_id: "fs_v1_threeclass_embargo0"
    hpo_run_id_logistic_regression: "<from Step 5>"
    hpo_run_id_xgboost: "<from Step 5>"
```

---

## 15. Generated Reports

- Global feature ranking, per model (Section 9).
- Fold-wise feature importance, per model (Sections 6/7/9).
- SHAP summary statistics (mean absolute SHAP per feature per fold, Section 9).
- SHAP dependence data (raw values only — no rendered plots, per instruction; Section 8).
- Local explanation samples (Section 10).
- Coefficient tables, raw and standardized (Section 6).
- Stability analysis, per model (Section 11).
- Model comparison report (Section 12).

All reports are machine-readable (YAML, consistent with prior steps' artifact conventions) — no image or chart file is generated by this module; any downstream visualization consumes this exported data separately.

---

## 16. Acceptance Criteria

- **Reproducibility:** given the same frozen model artifacts, the same fold data, and the same config (seeds included), every report in Section 15 is byte-for-byte or value-for-value identical across repeated runs. TreeSHAP's exactness (Section 8) removes sampling variance from the core SHAP computation; the only seeded components are background subsampling (if triggered) and local-sample selection (Section 10).
- **Fold isolation:** no fold's explanation artifacts are computed using another fold's model or data — verified the same way Steps 3–5 verify fold isolation (explicit assertion, not just convention).
- **No data leakage:** SHAP background data is drawn only from that fold's `train_df`; standardized coefficients use only that fold's training-window statistics.
- **Complete artifact generation:** every fold, for both models, produces the full artifact set defined in Section 13 — a fold missing an artifact (e.g. interaction values skipped due to the size ceiling, Section 8) is explicitly marked as skipped-with-reason in that fold's output, not silently absent.
- **Deterministic report outputs:** re-running this module against the same frozen inputs produces identical rankings, coefficient values, and SHAP summaries — no non-deterministic library behavior is introduced (TreeSHAP is exact; no KernelSHAP or other sampling-based explainer is used, per Section 8).

---

## 17. Explicit Exclusions

This step must NOT:
- Retrain, refit, or in any way modify either frozen model.
- Perform hyperparameter optimization or reopen Step 5's results.
- Engineer new features or remove any existing feature.
- Change Walk-Forward fold boundaries, purge/embargo configuration, or leakage-prevention assertions (Step 3).
- Perform calibration experiments of any kind — calibration is read from Step 4/5's frozen assignment only insofar as predictions are already calibrated before SHAP/coefficient analysis is applied to them; this step does not test, compare, or adjust calibration methods.
- Perform backtesting, paper trading, or live inference (deferred to Step 7).
- Use a single full-dataset model fit for convenience, in place of the per-fold walk-forward models (Section 3).

---

## 18. Open Decisions

1. Whether `shap_interaction` should be attempted for every fold and only skipped where the row-count ceiling is actually exceeded (current default), or disabled globally by default and enabled only on explicit request, given its computational cost.
2. Local explanation sample counts (`n_correct_samples_per_class: 5`, `n_misclassified_samples: 10`) are placeholder values — confirm or adjust based on how much manual review of individual predictions is actually wanted.
3. Whether the Section 12 model-comparison report should be scoped to only the aggregate (full-year) rankings, or should also include a fold-by-fold comparison table, given that doubles the size of that report.
