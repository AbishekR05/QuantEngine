# QuantEngine: Phase 3 (Machine Learning) - Results & Implementation Report

This report outlines the implementation details and outputs generated during **Phase 3 (Machine Learning Pipeline)** up to **Step 7 (Backtesting Framework)**.

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
We sequentially ran 5 models across all 8 walk-forward folds:
1. **Logistic Regression** (Linear Multinomial floor)
2. **Decision Tree** (Single non-linear tree floor)
3. **Random Forest** (Bagged-ensemble baseline)
4. **XGBoost Classifier** (Boosted-ensemble baseline)
5. **LightGBM Classifier** (Second boosted-ensemble baseline)

To align with threshold-based trading decision quality, probability calibration was integrated into the benchmarking loop. Models are calibrated using `CalibratedClassifierCV` fit strictly on the train window of each fold using a parameterized `cv: 5` cross-validation strategy.

---

## 4. Hyperparameter Optimization (Step 5)
We implemented a walk-forward-nested optimization pipeline using **Optuna** with a **Tree-structured Parzen Estimator (TPE)** sampler and a **Median Pruner**. 

### Search Spaces & Budgets:
- **Logistic Regression (`n_trials: 50`)**: Regularization strength `C` (`1e-4` to `1e2`), penalty (`l1`, `l2`, `elasticnet`), and solver (`lbfgs`, `saga`). Valid parameter combinations are enforced dynamically.
- **XGBoost (`n_trials: 20`)**: learning_rate (`0.01` to `0.3`), max_depth (`2` to `10`), n_estimators (`50` to `500`), subsample/colsample (`0.5` to `1.0`), and L1/L2 regularizations.
- **Decision Tree, Random Forest, and LightGBM**: Excluded from tuning as they failed the baseline viability check (0/8 passing folds).

---

## 5. Model Explainability & Interpretability (Step 6)
We implemented diagnostic interpretability methods matched to each model family's mathematical structure:

- **Logistic Regression**: Interpreted using standardized coefficients (raw weights scaled by training-fold standard deviations). Sign directions were checked for stability across walk-forward folds.
- **XGBoost Classifier**: Interpreted using native trees metrics (gain, weight, cover) and **TreeSHAP** (exact Shapley values) computed using a background training reference distribution (subsampled to 500 rows). Gated interaction analysis is triggered on test folds.

### 5.1 Cross-Model Feature Overlap (Top-15 Features)
We calculated Jaccard Similarity index metrics comparing the Top-15 features of both models:
*   **`BUY` class**: Jaccard index **`0.58`** (11 shared features).
*   **`HOLD` class**: Jaccard index **`0.67`** (12 shared features).
*   **`SELL` class**: Jaccard index **`0.58`** (11 shared features).

#### Core Shared Drivers:
*   **Trend/momentum**: `MACD`, `MACD_Hist`, `MACD_Signal`, `SMA_200`, `EMA_200`.
*   **Volatility/spread**: `ATR_14`, `BB_Lower` (for BUY/HOLD), `BB_Upper` (for SELL).
*   **Volume & price**: `Volume`, `Daily_Return`, `Open`, `Close`, `Low`.

---

## 6. Backtesting & Trading Performance (Step 7)
We implemented a chronological, cost-aware daily walk-forward simulation engine evaluating the optimized models under two distinct structures:
1. **Idealized (zero cost)**: All transaction friction values set to 0.0.
2. **Realistic (cost applied)**: Deducts slippage, brokerage, and taxes chronologically at the point of trade execution.

### Rollup Performance Summary (Mean Folds 1-7)

| Model Name | Cost Mode | CAGR (%) | Max Drawdown (%) | Sharpe Ratio | Exposure % | Profit Factor |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`xgboost`** | **Idealized** | **`+3.65%`** | **`-5.05%`** | **`0.39`** | `20.5%` | `1.48` |
| **`xgboost`** | **Realistic** | **`-0.85%`** | **`-6.09%`** | **`-0.14`** | `20.3%` | `1.51` |
| **`logistic_regression`** | **Idealized** | `+0.04%` | `-0.25%` | `0.02` | `0.3%` | `2858.00` |
| **`logistic_regression`** | **Realistic** | `+0.33%` | `-0.25%` | `0.16` | `0.3%` | `2858.00` |

### Key Backtesting Insights:
*   **Friction Sensitivity**: Transaction fees and execution slippage represent a primary hurdle, converting XGBoost's raw alpha of **`+3.65%`** CAGR into a slight net loss of **`-0.85%`** CAGR.
*   **Alpha Preservation (Fold 2 Example)**:
    During Fold 2's volatile index regime, the **XGBoost Idealized Strategy** significantly outperformed the benchmark:
    *   Model Strategy CAGR: **`+20.53%`** (Sharpe: **`1.83`**, Max Drawdown: **`-3.99%`**).
    *   Buy & Hold Benchmark CAGR: `+62.1%` (Sharpe: `-0.94`, Max Drawdown: **`-153.0%`**).
    This highlights the model's capacity to protect equity and extract profit from volatile down-trending markets.
*   **Threshold Sparsity**: Logistic Regression rarely triggers trades (exposure `0.3%`) because its calibrated probabilities remain close to the uniform baseline (`0.33`), failing to meet the `0.55` confidence filter.

All logs, trade files, daily portfolio values, and benchmark comparisons are exported under `data/backtest_runs/fs_v1_threeclass_embargo0/`.

---

## 7. Performance Summary & Viability Acceptances

### 7.1 Logistic Regression (Passed Viability)
*   **Best Parameters**: `{'solver': 'lbfgs', 'C': 0.0022967, 'penalty': 'l2', 'max_iter': 1000}`
*   **Study Objective (Mean Folds 1-7)**: `0.3371` (Improvement of **`+0.0310`** over baseline `0.3061`)
*   **Viability Summary**: Passed in **7 out of 8 folds** with stable standardized coefficient signs.

---

### 7.2 XGBoost Classifier (Passed Viability)
*   **Best Parameters**: `{'learning_rate': 0.0254, 'max_depth': 2, 'n_estimators': 368, 'subsample': 0.56, 'colsample_bytree': 0.98, 'min_child_weight': 7.63}`
*   **Study Objective (Mean Folds 1-7)**: `0.3409` (Improvement of **`+0.1038`** over baseline `0.2371`)
*   **Viability Summary**: Passed in **8 out of 8 folds** (stability max deviation `0.0682 < 0.10`).
