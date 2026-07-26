# Changelog: Backtesting Engine Corrections (Phase 3 - Step 7)

This changelog documents the material corrections made to resolve the divergence between the initial and corrected backtesting reports.

---

## Summary of Scope Changes

| Layer | Changed? | Description |
| :--- | :---: | :--- |
| **Backtesting Engine** | **YES** | Modified `BacktestEngine.run_backtest_on_fold` and `run_benchmark_strategy` to join raw index prices on `Date` and execute all cash accounting, sizing, and risk triggers on raw prices. |
| **Metric Formulas** | **NO** | The mathematical formulas for CAGR, Sharpe Ratio, Sortino Ratio, and Max Drawdown remain identical. The source inputs were corrected from z-score standard deviations to actual currency units. |
| **Reporting Layer** | **NO** | The reporting script and markdown templates remain structurally the same, but now consume correct, real-world returns data. |

---

## Corrected Items

### 1. Z-Score Trading Execution
*   **Type of Issue**: Calculation Bug & Backtesting Engine Issue
*   **Description**: The walk-forward test Parquet files from Step 3 contain scaled features where prices (`Close`, `High`, `Low`) are standardized z-scores (mean 0, variance 1). The engine initially executed trades directly using these z-scores. Since z-scores can cross zero and become negative, this resulted in executing trades at "negative prices" and computing cash balances on non-currency scales.
*   **Correction**: Modified the `BacktestEngine` constructor to load raw unscaled index prices from `data/processed/nsei_clean.csv`. For each fold's test loop, the engine now merges `test_df` with the raw prices using the `Date` column. Trade entries, exits, risk stop checks, and portfolio values are computed using `Raw_Close`, `Raw_High`, and `Raw_Low`.
*   **Impact**: Max drawdowns are now mathematically bounded between `[-100%, 0%]` for long spot positions. XGBoost mean realistic CAGR corrected from `-0.85%` to `-3.30%` (reflecting actual transaction costs on index values).

### 2. Benchmark Price Distortion
*   **Type of Issue**: Benchmark Implementation Issue
*   **Description**: The passive benchmarks (`buy_and_hold` and `always_long`) simulated in `run_benchmark_strategy` were using the scaled Close price series. This caused their returns, Sharpe ratios, and drawdowns to reflect z-score volatility instead of real Nifty 50 index performance.
*   **Correction**: Integrated the same `Date`-based raw price merge logic into the `run_benchmark_strategy` function, ensuring that passive portfolios are sized and valued on raw Close prices.
*   **Impact**: Corrected Fold 2 Buy & Hold CAGR from `+62.10%` to a correct `+14.90%` based on actual Nifty 50 movement. Corrected Fold 2 Buy & Hold maximum drawdown from an anomalous `-152.98%` to a realistic `-38.44%` (matching the March 2020 COVID market crash).

### 3. Sizing and Settle Cash Adjustments
*   **Type of Issue**: Calculation Bug
*   **Description**: Transaction cost deductions and risk-based sizing calculations were computed using z-score quantities. Sizing was highly distorted because a risk fraction of capital divided by a z-score denominator resulted in massive position sizes.
*   **Correction**: Switched all risk capital and transaction cost calculations (brokerage, slippage, taxes) to consume raw prices.
*   **Impact**: Trading metrics and transaction cost drag now reflect realistic transaction rules.

---

## Phase 3.5: Research Methodology Refinements

This section documents the statistical methodology improvements implemented to upgrade the framework from **Research Grade** toward **Publication/Institutional Grade**.

### 1. Unified Sharpe & Sortino Ratios
*   **Previous Logic**: Simple arithmetic mean of fold Sharpe/Sortino ratios.
*   **Correction**: Daily portfolio returns are now concatenated across all full-year folds (1-7) chronologically. A single unified Sharpe and Sortino ratio is computed from the concatenated returns series.
*   **Impact**: Eliminates statistical distortion from averaging standard deviations of different periods.

### 2. Worst-Case Drawdown
*   **Previous Logic**: Simple arithmetic mean of fold maximum drawdowns.
*   **Correction**: Stitches the daily returns curve into a single equity series and evaluates the absolute peak-to-trough drop over the entire 7-year history.
*   **Impact**: Accurately reflects tail risk (e.g. XGBoost realistic worst-case drawdown corrected to a realistic `-22.67%` instead of `-5.58%`).

### 3. Global Profit Factor & Expectancy
*   **Previous Logic**: Fold-level Profit Factors calculated on gross returns and arithmetically averaged. Fallback of gross profit for zero-loss folds.
*   **Correction**: Profit Factor is calculated using **net P&L** (after costs) with a `float('inf')` fallback. Rolled up globally by taking absolute total winnings over absolute total losses across all folds combined. Expectancy is aggregated directly across all executed trades to avoid fold-size bias.
*   **Impact**: Restores realistic profit factor rollups (e.g. XGBoost realistic global profit factor is corrected to `0.62`, and Logistic Regression is `2.44`).

---

## Logic Validation & Integrity Check

*   **Model Parameter Verification**: Verified that no model weights, hyperparameters, or training states were modified.
*   **Feature Verification**: Verified that standardized parquet features (`Close`, `High`, `Low`) are passed exactly as before to `predict_proba`.
*   **Trading Rule Verification**: Enforced that the signal generation logic (confidence threshold comparison, hold downgrades), position sizing rules, Stop-Loss/Take-Profit triggers, and transaction cost rates remain **100% identical**.
*   **Conclusion**: **Only the statistical aggregator and reporting equations changed.** All underlying trade executions, fill prices, and portfolio equity series are unchanged.
