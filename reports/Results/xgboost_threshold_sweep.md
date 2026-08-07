# QuantEngine: XGBOOST Decision Threshold Sweep Report

*Evaluated under realistic transaction costs across Folds 1–7.*

---

## 1. Threshold Sweep Results Table
| Threshold | Mean Sharpe | Mean Sortino | Mean Max DD | Mean Profit Factor | Mean Expectancy (₹) | Mean Exposure | Mean Trades Count | Mean CAGR |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.66** | -0.37 | -0.31 | -12.38% | 0.80 | -1294.12 | 22.9% | 10.0 | -1.40% |
| **0.67** | -0.24 | -0.20 | -9.20% | 0.86 | -844.85 | 23.6% | 10.0 | -0.94% |
| **0.68** | -0.11 | -0.08 | -8.04% | 0.93 | -434.87 | 21.5% | 9.0 | -0.47% |
| **0.69** | 0.02 | 0.02 | -6.26% | 1.01 | 77.01 | 20.6% | 8.6 | 0.01% |
| **0.70** | 0.27 | 0.19 | -5.36% | 1.23 | 1191.85 | 17.6% | 7.6 | 0.86% |
| **0.71** | -0.03 | -0.02 | -5.55% | 0.97 | -162.38 | 17.2% | 7.6 | -0.15% |
| **0.72** | 0.16 | 0.11 | -4.92% | 1.13 | 704.06 | 16.5% | 7.3 | 0.49% |
| **0.73** | 0.22 | 0.15 | -4.47% | 1.17 | 926.70 | 16.8% | 7.4 | 0.68% |
| **0.74** | 0.36 | 0.23 | -4.44% | 1.33 | 1736.50 | 14.7% | 6.4 | 1.12% |

## 2. Strategic Insights
- **Optimal Decision Coordinate**: Symmetrical threshold of **`0.74`** yields the highest risk-adjusted profile with a Sharpe of **`0.36`** and CAGR of **`1.12%`**.
- **Trade Frequency Optimization**: Raising the threshold restricts marginal trades, lowering the transaction cost drag (mean trades count goes from `10.0` to `6.4`).