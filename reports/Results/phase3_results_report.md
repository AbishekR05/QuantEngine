# QuantEngine: Phase 3 (Machine Learning) - Results & Implementation Report

This report outlines the implementation details and outputs generated during **Phase 3 (Machine Learning Pipeline)** up to **Step 4 (Baseline Model Benchmarking)**.

---

## 1. Phase 3 Objectives & Roadmap
Phase 3 transitions the QuantEngine project from descriptive data analysis to predictive modeling. The primary target is building a **decision classifier** for the Nifty 50 Index (`^NSEI`) that outputs one of three trading decisions:
- `BUY` / `CALL` (Directional Long)
- `SELL` / `PUT` (Directional Short)
- `HOLD` / `NO_TRADE` (Sideways / Low-Volatility conditions)

---

## 2. Feature Store Architecture & Slicing (Steps 2 & 3)
- **Feature Store**: Model-agnostic variables are saved as a Parquet file (`feature_store_v1.parquet`) containing 4,613 records (Date range: `2007-09-17` to `2026-07-09`).
- **Walk-Forward Splits**: Created 8 folds expanding from `2014-01-01` to exclude historical zero-volume data artifacts. Features are scaled per-fold using train-only moments to prevent time-series lookahead leakage.
- **Label Distribution Metadata**: Walk-forward fold metadata YAML files record class-specific label counts to enable downstream imbalance tracking.

---

## 3. Baseline Model Benchmarking (Step 4)
We implemented the benchmarking pipeline sequentially running 5 models across all 8 walk-forward folds:
1. **Logistic Regression** (Linear Multinomial floor)
2. **Decision Tree** (Single non-linear tree floor)
3. **Random Forest** (Bagged-ensemble baseline)
4. **XGBoost Classifier** (Boosted-ensemble baseline)
5. **LightGBM Classifier** (Second boosted-ensemble baseline)

---

## 4. Probability Calibration & Dual Metrics Strategy
To align with threshold-based trading decision quality, probability calibration was integrated into the benchmarking loop:
- Models are calibrated using `CalibratedClassifierCV` fit strictly on the train window of each fold using a parameterized `cv: 5` cross-validation strategy.
- Classification metrics (Macro F1, Accuracy, Precision, Recall) are recorded **both before and after calibration** to monitor raw discriminative power vs. post-calibration confidence.
- Multiclass **Brier Score** and class-specific reliability curve lists are generated for each fold to audit probability accuracy.

---

## 5. Benchmarking & Viability Gate Results
We compared each model's calibrated Macro F1 against a naive majority-class (`HOLD`) baseline. To pass the viability check, a model must exceed the naive floor by a margin of `0.05` on at least `5 out of 8` folds.

### Summary Comparison Table:
| Model Name | Full-Year Calibrated F1 (Mean) | Viability Folds Passed | Stability Pass? | Viability Gate Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **`logistic_regression`** | **`0.3061`** | **`7 / 8`** | **`PASS`** (Max dev: 0.08) | **`PASSED`** |
| **`xgboost`** | `0.2371` | `3 / 8` | `FAIL` (Max dev: 0.115) | `FAILED` |
| **`decision_tree`** | `0.2143` | `0 / 8` | `PASS` (Max dev: 0.048) | `FAILED` |
| **`random_forest`** | `0.2155` | `0 / 8` | `PASS` (Max dev: 0.049) | `FAILED` |
| **`lightgbm`** | `0.2147` | `0 / 8` | `PASS` (Max dev: 0.048) | `FAILED` |

### Key Findings & Insights:
1. **Logistic Regression Dominates**: Regularized Logistic Regression is the only model that successfully cleared the viability gate. It exhibits stable performance across folds, beating the naive floor by up to **+0.18** Macro F1.
2. **Probability Collapse on Tree Models**: Under unoptimized default parameters (e.g. `n_estimators=100`, default depth), tree-based ensembles (Decision Tree, Random Forest, LightGBM) overfit the noisy training targets. Once passed to `CalibratedClassifierCV`, their calibrated probabilities collapsed to the majority `HOLD` class, resulting in post-calibration Macro F1 scores matching the naive floor exactly.
3. **XGBoost Instability**: XGBoost shows high raw predictive ability but suffers from high cross-fold variance, causing it to fail both the fold viability count (3/8 folds passed) and the stability check (0.115 deviation exceeding the 0.10 limit).

All model runs, predictions, and serialized weights are recorded under `data/benchmark_runs/fs_v1_threeclass_embargo0/`.
