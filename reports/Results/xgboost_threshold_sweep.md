# QuantEngine: XGBoost Decision Threshold Sweep Report

*Evaluated under realistic transaction costs across Folds 1–7.*

---

## 1. Threshold Sweep Results Table
| Threshold | Mean Sharpe | Mean Sortino | Mean Max DD | Mean Profit Factor | Mean Expectancy (₹) | Mean Exposure | Mean Trades Count | Mean CAGR |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.66** | -0.07 | -0.11 | -2.97% | 2303.31 | 251.16 | 19.1% | 7.1 | -0.49% |
| **0.67** | 0.04 | 0.03 | -2.56% | 1.99 | -317.25 | 17.3% | 6.4 | 0.14% |
| **0.68** | 0.07 | 0.07 | -2.24% | 1.81 | -202.14 | 16.5% | 6.3 | 0.42% |
| **0.69** | 0.32 | 0.17 | -1.98% | 2.04 | 1887.38 | 15.9% | 6.0 | 0.84% |
| **0.70** | 0.22 | 0.22 | -2.08% | 8724.64 | 2185.29 | 13.0% | 5.3 | 0.37% |
| **0.71** | 0.24 | 0.23 | -1.71% | 8724.88 | 2506.83 | 11.6% | 4.9 | 0.55% |
| **0.72** | 0.23 | -0.08 | -1.51% | 5766.00 | 2772.74 | 11.2% | 4.6 | 0.37% |
| **0.73** | -0.32 | -0.16 | -1.48% | 1.32 | -734.57 | 9.5% | 3.9 | -0.36% |
| **0.74** | -0.23 | -0.22 | -1.43% | 2858.30 | 1659.11 | 8.8% | 3.6 | -0.36% |

## 2. Strategic Insights
- **Optimal Decision Coordinate**: Symmetrical threshold of **`0.69`** yields the highest risk-adjusted profile with a Sharpe of **`0.32`** and CAGR of **`0.84%`**.
- **Trade Frequency Optimization**: Raising the threshold restricts marginal trades, lowering the transaction cost drag (mean trades count goes from `7.1` to `3.6`).