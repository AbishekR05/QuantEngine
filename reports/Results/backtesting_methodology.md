# QuantEngine: Backtesting Statistical Methodology Document

This document outlines the rigorous mathematical definitions and statistical aggregation methods implemented in the QuantEngine backtesting framework (Phase 3.5). These methods conform to industry standards in systematic quantitative finance and machine learning research.

---

## 1. Metric Definitions

### 1.1 Profit Factor (PF)
*   **Formula**:
    $$PF = \frac{\sum_{i=1}^{M} \text{Net Winning Trades}_i}{\sum_{j=1}^{N} |\text{Net Losing Trades}_j|}$$
*   **Definition**: The ratio of the absolute sum of net profits from all winning trades to the absolute sum of net losses from all losing trades. 
*   **Methodology Refinements**:
    *   Uses **net P&L** (post-brokerage, slippage, taxes, and fees) instead of gross realized returns.
    *   If zero losing trades occur, the Profit Factor is mathematically defined as infinite ($\infty$), avoiding invalid drop-in substitutions of absolute cash profits.
    *   Fold-level Profit Factors are **never averaged** using arithmetic means (since averaging ratios or infinities is statistically invalid). A single global Profit Factor is compiled by aggregating all net wins and losses across all test windows.

### 1.2 Expectancy (E)
*   **Formula**:
    $$E = \frac{\sum_{k=1}^{T} \text{Net P\&L}_k}{T}$$
*   **Definition**: The average expected net profit/loss in absolute currency units (₹) per completed trade.
*   **Methodology Refinements**:
    *   Expectancy is computed globally by taking the arithmetic mean of every completed trade across all folds combined. This prevents the fold-size bias of taking the simple average of fold expectancies (which would treat a fold with 1 trade and a fold with 20 trades with equal weight).

### 1.3 Unified Sharpe Ratio (SR)
*   **Formula**:
    $$SR = \frac{\text{Mean}(R_{1..N})}{\text{Std}(R_{1..N})} \times \sqrt{252}$$
*   **Definition**: A measure of risk-adjusted excess return per unit of portfolio volatility.
*   **Methodology Refinements**:
    *   Daily returns of the running portfolio equity curve are concatenated chronologically across all 7 full-year folds to form a single continuous returns series $R_{1..N}$.
    *   A single unified Sharpe ratio is computed from this concatenated series. This avoids the distortion of averaging fold-level Sharpe ratios (which ignores differences in variance across years).
    *   Risk-free rate $R_f$ is assumed to be $0.0\%$.

### 1.4 Unified Sortino Ratio (SoR)
*   **Formula**:
    $$SoR = \frac{\text{Mean}(R_{1..N})}{\text{DownsideStd}(R_{1..N})} \times \sqrt{252}$$
*   **Definition**: A variation of the Sharpe ratio that penalizes only negative excess returns (downside deviation).
*   **Methodology Refinements**:
    *   Computed from the same concatenated daily returns series $R_{1..N}$ using only negative returns for the standard deviation denominator.

### 1.5 Worst-Case Maximum Drawdown (Max DD)
*   **Formula**:
    $$DD_t = \frac{\text{Equity}_t - \text{Peak}_t}{\text{Peak}_t}$$
    $$\text{Unified Max DD} = \min_{t} (DD_t)$$
    $$\text{Peak}_t = \max_{s \le t} (\text{Equity}_s)$$
*   **Definition**: The largest peak-to-trough drop in portfolio value over the entire stitched multi-year equity curve.
*   **Methodology Refinements**:
    *   Replaces the arithmetic average of fold drawdowns (which understates the actual multi-year tail risk).

### 1.6 Portfolio-Level CAGR
*   **Formula**:
    $$\text{Unified CAGR} = (1 + \text{Cumulative Return})^{\frac{252}{T_{\text{days}}}} - 1$$
*   **Definition**: The geometric compounding growth rate of the portfolio over the total active trading days.
*   **Methodology Refinements**:
    *   Replaces arithmetic average of CAGRs, which mathematically overstates returns due to volatility drag.

---

## 2. Statistical Validity & Verification

### 2.1 Sample Size Constraints
When evaluating decision confidence thresholds $\ge 0.65$, trade frequency drops to 1–6 trades per fold. At these levels:
*   Fold-level Sharpe, Sortino, and Profit Factor metrics become highly unstable (high variance).
*   By transitioning to unified daily returns and global trade statistics, the effective sample size is pooled (e.g. 11 trades globally for Logistic Regression and 89 trades globally for XGBoost), restoring statistical consistency.

### 2.2 Threshold Sweep Analysis (Exploratory Only)
*   The threshold sweep of `0.50–0.90` is classified as **Exploratory Research Analysis**.
*   Selecting `0.69` as the strategy default based on test set sweeps introduces optimization bias. 
*   **Publication-Grade Threshold Optimization Methodology**:
    For each chronological walk-forward fold:
    1.  **Training Window**: Train the ML model.
    2.  **Inner Validation Split**: Segment the end of the training window (e.g., last 20%) or use K-fold cross-validation on the training set to serve as validation data.
    3.  **Threshold Grid Search**: Run backtest iterations on the validation data for thresholds $T \in [0.50, 0.90]$ at step $0.01$.
    4.  **Freeze Optimal Threshold**: Select the threshold $T^*$ that maximizes the validation Sharpe ratio.
    5.  **Out-of-Sample Evaluation**: Execute the model on the completely unseen Test Fold using threshold $T^*$.
