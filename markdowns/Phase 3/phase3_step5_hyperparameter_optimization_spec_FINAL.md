# Phase 3 Step 5 — Hyperparameter Optimization: Implementation Specification

**Status:** Draft for review
**Depends on (frozen, not re-discussed here):** Step 1 (Architecture), Step 2 (Feature Store), Step 3 (Walk-Forward), Step 4 (Baseline Benchmarking + Viability Gate), `raw_vs_calibrated_report.md` (Run ID `fs_v1_threeclass_embargo0`)
**Consumed by:** Antigravity
**Out of scope for this document:** data leakage of any kind, feature engineering, feature selection, explainability, backtesting, new models, redesign of Feature Store/Walk-Forward/calibration methodology.

---

## 1. Scope and Objectives

Step 5 tunes the hyperparameters of the model(s) that passed Step 4's viability gate, using the same walk-forward folds, the same scaling/calibration boundaries, and the same evaluation framework already established. The objective is to **improve performance within the existing pipeline**, not to change the pipeline. No new model family, no new feature, no new fold logic, no new calibration method is introduced here.

---

## 2. Eligibility Determination (data-driven, from Step 4 results)

Per Step 4's viability gate (`min_margin_over_naive_baseline` on Macro F1, `min_passing_folds: 5` of 8):

| Model | Passed Folds | Viability Result | Stability |
|---|---|---|---|
| Logistic Regression | 7/8 | **PASSED** | Stable (max deviation 0.0810 < 0.10) |
| Decision Tree | 0/8 | FAILED | Stable, but non-viable |
| Random Forest | 0/8 | FAILED | Stable, but non-viable |
| XGBoost | 3/8 | FAILED | **Unstable** (max deviation 0.1155 > 0.10) |
| LightGBM | 0/8 | FAILED | Stable, but non-viable |

- **Eligible for Step 5 optimization: Logistic Regression and XGBoost.**
  - **Logistic Regression** is eligible because it **passed** Step 4's viability gate outright (7/8).
  - **XGBoost** is eligible as a **conditional optimization candidate**, despite having failed the gate (3/8, unstable). It is not treated as uniformly non-viable like the three models below: it consistently showed predictive signal and is the strongest non-linear model in the benchmark. One purpose of hyperparameter optimization is precisely to determine whether XGBoost's instability originates from poor default hyperparameters rather than from the model family itself — that question is left open pending Step 5's own results, not decided here.
- Decision Tree, Random Forest, and LightGBM remain **excluded from optimization** — 0/8 passing folds each, with no evidence in the Step 4 report that tuning is likely to recover competitive performance. Tuning them would blur Step 4's gate rather than respect it.
- This eligibility list is **derived from the report, not assumed** — if Step 4 is ever re-run (e.g. different feature set, different label version) and produces a different pass/fail outcome, the eligible-model list for Step 5 is re-derived from that new report, not hardcoded to today's two models as a permanent fact.

---

## 3. Important Data-Driven Note (context for Section 9, not a redesign)

The Step 4 report shows calibration **reduces** Macro F1 in the large majority of folds, across every model, including the eligible one (Logistic Regression: calibrated average 0.3061 vs. raw average 0.3387 across full-year folds; only 3 of 8 folds actually improved with calibration). This is a real, visible pattern in the data — flagged here so it is not silently ignored, but **not corrected in this document**: Step 4's calibration methodology (fit process, per-model method assignment) is frozen. The only decision this raises for Step 5 is which metric variant (raw or calibrated Macro F1) the optimization objective is computed on — addressed explicitly in Section 9 and Section 15, rather than assumed.

---

## 4. Inputs and Outputs

**Inputs:**
- Walk-forward fold artifacts from Step 3 (`walk_forward_runs/{run_id}/fold_{n}_*`) — consumed as-is, no re-slicing.
- Step 4's per-fold trained-model configuration and calibration assignment, per eligible model: Logistic Regression (`platt`, per Step 4 Section 11) and XGBoost (`platt`, per Step 4 Section 11) — both reused as fixed settings, not tuned.
- `raw_vs_calibrated_report.md` (this document's trigger artifact) — used only to determine eligibility (Section 2), not re-parsed as a metrics source during optimization (Step 5 generates its own trial-level metrics independently).

**Outputs (produced independently, per eligible model — see Section 8 on study isolation):**
- A best-trial hyperparameter configuration for Logistic Regression, and a separate best-trial hyperparameter configuration for XGBoost.
- Full trial history per model (Section 12).
- A comparison of optimized vs. Step 4 default-configuration performance, fold-by-fold, per model (Section 14).
- Decision Tree's, Random Forest's, and LightGBM's report entries are carried forward unchanged into Step 5's summary output as "excluded — failed viability gate," so a reader of Step 5's output isn't left wondering why only two of five baseline models were optimized.

---

## 5. Hyperparameter Optimization Philosophy

- Tune only the parameters of each eligible model itself (Logistic Regression: regularization strength, penalty type, solver; XGBoost: boosting/tree parameters, Section 7). Do not tune `class_weight`/`scale_pos_weight` (fixed at `balanced`, per Step 1 Section 5 — a frozen architectural requirement, not a hyperparameter) and do not tune either model's calibration method (fixed at `platt` for both, per Section 3/4 above).
- Optimization is **walk-forward-nested**: every trial, for either model, is evaluated across the same fold set used in Step 4, not a single hold-out split. A hyperparameter configuration is judged on its aggregate behavior across folds, exactly as Step 4 judged the default configuration.
- No trial result from a given fold's test window may influence hyperparameter choice used within that same fold — search operates purely on the aggregate objective (Section 10) computed after all folds are scored; there is no per-fold hyperparameter override.
- **Logistic Regression and XGBoost are optimized as two fully independent efforts.** Each model has its own Optuna study, its own search space, its own trial history, and its own comparison against its own Step 4 baseline. XGBoost's conditional/borderline status (Section 2) does not affect how Logistic Regression's study is run, and vice versa — there is no shared study, no shared trial pool, and no cross-model comparison performed by this module (a cross-model comparison, if wanted, is a separate downstream concern, not part of Step 5's output).

---

## 6. Search Strategy

**Chosen strategy: Bayesian optimization via Optuna, Tree-structured Parzen Estimator (TPE) sampler.**

**Justification:**
- Both eligible models' search spaces (Section 7) mix continuous and categorical parameters — Logistic Regression's `C`/`penalty`/`solver`, and XGBoost's learning rate, tree depth, and sampling ratios — which TPE handles natively without the combinatorial blow-up of grid search.
- Each trial, for either model, requires a full 8-fold walk-forward evaluation (Section 8), which is expensive relative to a single train/test fit. TPE's sample efficiency (fewer trials to reach a good region) matters more here than in a cheap single-split setting, where random search would be an adequate and simpler alternative.
- Optuna supports trial pruning (Section 12), letting a clearly poor configuration be abandoned partway through its fold loop rather than always running all 8 folds to completion — reducing wasted compute without touching the walk-forward logic itself.
- The framework is built generically (per-model search-space registry, Section 7): each eligible model gets its own independent Optuna study (Section 5), so the engine runs the same way whether one model or several are eligible — it simply iterates the registry's active entries, which now include both Logistic Regression and XGBoost, per Section 2.

---

## 7. Parameter Search Space

Both eligible models are populated, per Section 2's eligibility determination. Each has its own table and its own study (Section 5) — there is no shared or combined search space.

### 7.1 Logistic Regression

| Parameter | Type | Range / Choices | Notes |
|---|---|---|---|
| `C` | continuous (log-uniform) | `1e-4` to `1e2` | Inverse regularization strength |
| `penalty` | categorical | `l2`, `l1`, `elasticnet` | `l1`/`elasticnet` require `solver='saga'` (constraint below) |
| `solver` | categorical | `lbfgs`, `liblinear`, `saga` | Constrained jointly with `penalty` — invalid combinations (e.g. `lbfgs` + `l1`) are excluded from the search space definition itself, not caught as runtime errors |
| `l1_ratio` | continuous | `0.0` to `1.0` | Only sampled when `penalty='elasticnet'`; otherwise not applicable to the trial |
| `max_iter` | fixed | `1000` | Not tuned — set high enough to avoid convergence-related noise in the comparison, per reproducibility (Section 11) |

`class_weight='balanced'` and `random_state` (Section 11) are fixed inputs to every trial, not part of the search space.

### 7.2 XGBoost

| Parameter | Type | Range / Choices | Notes |
|---|---|---|---|
| `learning_rate` | continuous (log-uniform) | `0.01` to `0.3` | |
| `max_depth` | integer | `2` to `10` | Bounded to limit overfitting risk on a dataset this size |
| `n_estimators` | integer | `50` to `500` | |
| `subsample` | continuous | `0.5` to `1.0` | Row subsampling ratio |
| `colsample_bytree` | continuous | `0.5` to `1.0` | Column subsampling ratio |
| `min_child_weight` | continuous | `1` to `10` | |
| `reg_alpha` | continuous (log-uniform) | `1e-8` to `1.0` | L1 regularization |
| `reg_lambda` | continuous (log-uniform) | `1e-8` to `1.0` | L2 regularization |

`scale_pos_weight`/equivalent class-weighting mode (`balanced`) and `random_state` (Section 11) are fixed inputs to every trial, not part of the search space — consistent with how `class_weight` is held fixed for Logistic Regression above.

---

## 8. Walk-Forward Optimization Workflow

Run independently, once per eligible model (Logistic Regression, then XGBoost, or vice versa — order between models is not significant since each runs in its own study with no shared state):

Per trial (one sampled hyperparameter configuration, for the model that study belongs to):

1. For each of Folds 1–8 (Step 3 boundaries, unchanged):
   a. Instantiate that model (Logistic Regression or XGBoost) with the trial's sampled parameters (Section 7.1 or 7.2), fixed class-weighting, fixed seed (Section 11).
   b. Fit on that fold's `train_df` (already scaled per Step 2/3 — no re-scaling logic introduced here).
   c. Predict raw probabilities on `test_df`.
   d. Apply calibration (`platt`, fit on `train_df` only — same isolation discipline as Step 4 Section 5, and identical for both models).
   e. Compute Macro F1 (and secondary metrics, Section 10) on the calibrated output for that fold.
2. Aggregate across Folds 1–7 (full-year folds) into the trial's primary objective value (Section 10); Fold 8 is computed and recorded but excluded from the aggregate, matching Step 4's own "Average (Full Years)" convention.
3. Report the aggregate value back to that model's Optuna study as the trial's result.

This is the same per-fold sequence Step 4 used for the default configuration — Step 5 changes only which hyperparameter values are plugged in at step 1a, and which model's study is being run, not the sequence itself. **Each model's full trial loop (all trials, all folds) runs to completion within its own study before or independently of the other model's study** — the two studies never interleave trial-by-trial and never share a sampler, seed state, or trial history (Section 5).

---

## 9. Fold Isolation and Leakage Prevention

- Scaler fitting (Step 2/3) and calibration fitting (Step 4/Section 8 above) remain train-fold-only for every trial — this is re-verified per trial, not assumed to still hold just because it held in Step 4.
- No trial may use any fold's test-window data to influence that same fold's training (identical constraint to Step 3 Section 5, re-applied here across every sampled configuration, not just the default one).
- No information leaks **across trials** either — each trial's model/scaler/calibrator objects are freshly instantiated per trial per fold; nothing fitted in trial N is reused in trial N+1.
- The Optuna study itself only ever sees the aggregate objective value (Section 8, step 3) — it does not have access to per-fold test data directly, only the scored result, preventing the search process itself from indirectly overfitting to a specific fold's test set.

---

## 10. Objective Function(s)

- **Primary objective:** mean Macro F1 across Folds 1–7 (full-year folds), on **calibrated** predictions — chosen because calibrated output is what the pipeline actually produces downstream (Step 1 Section 1's confidence-output requirement), despite Section 3's observation that calibration currently often reduces this metric. Optimizing the metric the pipeline actually emits is treated as the more defensible default; see Section 15 for the corresponding acceptance-criteria implication and Section 16 for this as an open decision rather than a silent assumption.
- **Secondary objective (reported, not searched on):** cross-fold stability, computed the same way as Step 4 Section 9 (max deviation from the trial's own cross-fold mean). This is recorded for every trial and used to break ties among near-equal primary-objective results, but is not itself the value Optuna's sampler optimizes against.
- **Also recorded per trial (diagnostic, not objective):** raw (pre-calibration) Macro F1, per Section 3's note — so the raw-vs-calibrated gap can be inspected per trial, not just for the default configuration.

---

## 11. Trial Management and Reproducibility

- **Study identity:** one Optuna study per optimization run, named to include the eligible model, Feature Store version, label version, and Walk-Forward run ID (e.g. `hpo_logistic_regression_fs_v1_threeclass_embargo0`).
- **Sampler seed:** fixed seed for the TPE sampler itself, in addition to the fixed `random_state` used inside each trial's model fit (Section 7) — both are recorded, since they control different sources of randomness (search-space exploration vs. model fitting).
- **Trial budget:** number of trials and optional wall-clock timeout are configuration values (Section 12), not hardcoded.
- **Pruning:** an Optuna pruner (e.g. median pruner, evaluated after each fold within a trial) may terminate a clearly underperforming trial before all 8 folds run — pruning decisions and the partial fold results that led to them are logged (Section 13), not discarded silently.
- **Full reproducibility:** every trial's sampled parameters, per-fold metrics, aggregate objective, and pruning status are persisted (Section 12/14) such that the entire study — not just the best trial — can be reconstructed from saved artifacts and the study's config snapshot alone.

---

## 12. Configuration Schema Additions

```yaml
hyperparameter_optimization:
  eligible_models: ["logistic_regression", "xgboost"]   # derived from Step 4 viability report, not hardcoded permanently
  excluded_models:
    decision_tree: "failed viability gate (0/8)"
    random_forest: "failed viability gate (0/8)"
    lightgbm: "failed viability gate (0/8)"
  study:
    sampler: "tpe"
    sampler_seed: 123
    n_trials: 100
    timeout_seconds: null
    pruner: "median"
  objective:
    primary_metric: "macro_f1_calibrated"
    aggregate_folds: [1, 2, 3, 4, 5, 6, 7]     # Fold 8 excluded from aggregate, per Step 4 convention
    secondary_metric: "fold_stability_max_deviation"
  search_spaces:
    logistic_regression:
      active: true
      C: {type: "log_uniform", low: 0.0001, high: 100.0}
      penalty: {type: "categorical", choices: ["l2", "l1", "elasticnet"]}
      solver: {type: "categorical", choices: ["lbfgs", "liblinear", "saga"]}
      l1_ratio: {type: "uniform", low: 0.0, high: 1.0, condition: "penalty == 'elasticnet'"}
      max_iter: 1000
      class_weight: "balanced"      # fixed, not searched
      random_state: 42               # fixed per-trial model seed
      calibration_method: "platt"    # fixed, inherited from Step 4
    xgboost:
  active: true
  learning_rate: {type: "log_uniform", low: 0.01, high: 0.3}
  max_depth: {type: "int", low: 2, high: 10}
  n_estimators: {type: "int", low: 50, high: 500}
  subsample: {type: "uniform", low: 0.5, high: 1.0}
  colsample_bytree: {type: "uniform", low: 0.5, high: 1.0}
  min_child_weight: {type: "uniform", low: 1.0, high: 10.0}
  reg_alpha: {type: "log_uniform", low: 1e-8, high: 1.0}
  reg_lambda: {type: "log_uniform", low: 1e-8, high: 1.0}
  random_state: 42
  calibration_method: "platt"

  feature_store_version: "v1"
  label_version: "version_b"
  walk_forward_run_id: "fs_v1_threeclass_embargo0"
```

---

## 13. Directory / File Output Structure and Logging Requirements

```
hpo_runs/{run_id}/
  study_config_snapshot.yaml
  study.db                                  # Optuna storage (or equivalent journal)
  trial_{n}/
    sampled_params.yaml
    fold_{f}_metrics.yaml                   # per-fold raw + calibrated Macro F1, secondary metrics
    trial_summary.yaml                      # aggregate objective, pruning status if pruned
  best_trial/
    sampled_params.yaml
    fold_{f}_metrics.yaml
    comparison_vs_step4_default.yaml         # Section 14
  optimization_report.yaml                   # Section 14 top-level summary
```

- `run_id` follows the same convention as Steps 3/4: tied to Feature Store version + label version + Walk-Forward run ID, with the model name appended.
- **Logging:** every trial logs its sampled parameters, per-fold metric as it completes (not only at trial end), and — if pruned — the fold number and partial aggregate value at the point of pruning. Study-level logs record total trials run, trials pruned, trials completed, and wall-clock duration.

---

## 14. Optimization Reports and Summary Artifacts

`optimization_report.yaml` contains:
- Best trial's hyperparameters and its per-fold + aggregate metrics.
- A fold-by-fold table comparing the best trial against Step 4's default-configuration results (i.e., an extension of the format already used in `raw_vs_calibrated_report.md`) — same folds, same metric, default vs. optimized side by side.
- Trial-count summary (total run, pruned, completed).
- Convergence data: objective value per trial number, as a data table (for external plotting) — no chart is rendered or generated by this module itself.
- Separate optimization summaries for Logistic Regression and XGBoost, each comparing the optimized configuration against its own Step 4 baseline.

---

## 15. Acceptance Criteria

- Each optimized model (Logistic Regression and XGBoost) must independently meet or exceed its own Step 4 baseline on the primary objective (Section 10).
- Each optimized model must satisfy the original Step 4 viability criteria (or, for XGBoost, demonstrate a measurable improvement relative to its Step 4 baseline while being evaluated against the same unchanged benchmark).
- Fold-isolation and leakage checks (Section 9) must show zero violations across all trials, not only the best trial.
- The full study must be reproducible from its config snapshot and seeds (Section 11) — re-running the study with the same config must reproduce the same best-trial parameters (subject to the known non-determinism caveat already logged for the Step 4 pipeline, if applicable to Logistic Regression's solver — `saga` in particular has known minor run-to-run variation).

---

## 16. Explicit Exclusions

This step must NOT:
- Introduce any new model not already in Step 4's catalogue.
- Alter Feature Store contents, schema, or versioning (Step 2).
- Alter Walk-Forward fold boundaries, purge/embargo logic, or leakage-prevention assertions (Step 3).
- Perform feature engineering or feature selection of any kind.
- Perform explainability analysis (SHAP, permutation importance, etc.) — that remains out of scope until a dedicated later step, if any.
- Perform backtesting, paper trading, or live inference.
- Change the calibration *methodology* (fit-on-train-only discipline) or the calibration *method assignment* (`platt` for Logistic Regression, fixed in Step 4) — only the underlying model's own hyperparameters are searched.
- Optimize or re-evaluate the excluded models (Decision Tree, Random Forest, and LightGBM) under this step.

---

## 17. Open Decisions

1. **Raw vs. calibrated objective (Section 3/10):** this document defaults to optimizing calibrated Macro F1, since that's the pipeline's actual output — confirm, or prefer optimizing raw Macro F1 given calibration's currently-negative effect, with calibration quality tracked only as a diagnostic.
2. Trial budget (`n_trials: 100`, Section 12) is a placeholder — confirm or adjust based on acceptable compute time for a 100-trial × 7-fold Logistic Regression search.
3. Whether different trial budgets should be allocated to Logistic Regression and XGBoost based on their respective search-space complexity.
