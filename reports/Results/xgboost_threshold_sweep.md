# QuantEngine: XGBoost Decision Threshold Sweep Report

*Evaluated under realistic transaction costs across Folds 1–7.*

---

## 1. Threshold Sweep Results Table
| Threshold | Mean Sharpe | Mean Sortino | Mean Max DD | Mean Profit Factor | Mean Expectancy (₹) | Mean Exposure | Mean Trades Count | Mean CAGR |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.66** | -0.13 | -0.08 | -8.71% | 0.88 | -648.13 | 19.1% | 7.1 | -0.51% |
| **0.67** | 0.05 | 0.03 | -7.79% | 1.05 | 263.94 | 17.3% | 6.4 | 0.12% |
| **0.68** | 0.14 | 0.09 | -5.62% | 1.13 | 679.71 | 16.5% | 6.3 | 0.41% |
| **0.69** | 0.28 | 0.16 | -5.62% | 1.26 | 1392.99 | 15.9% | 6.0 | 0.84% |
| **0.70** | 0.13 | 0.07 | -5.22% | 1.12 | 707.93 | 13.0% | 5.3 | 0.35% |
| **0.71** | 0.21 | 0.11 | -4.80% | 1.21 | 1142.43 | 11.6% | 4.9 | 0.52% |
| **0.72** | 0.15 | 0.08 | -4.96% | 1.16 | 829.33 | 11.2% | 4.6 | 0.35% |
| **0.73** | -0.15 | -0.07 | -4.13% | 0.84 | -888.16 | 9.5% | 3.9 | -0.37% |
| **0.74** | -0.16 | -0.07 | -5.40% | 0.83 | -947.76 | 8.8% | 3.6 | -0.37% |

## 2. Strategic Insights
- **Optimal Decision Coordinate**: Symmetrical threshold of **`0.69`** yields the highest risk-adjusted profile with a Sharpe of **`0.28`** and CAGR of **`0.84%`**.
- **Trade Frequency Optimization**: Raising the threshold restricts marginal trades, lowering the transaction cost drag (mean trades count goes from `7.1` to `3.6`).