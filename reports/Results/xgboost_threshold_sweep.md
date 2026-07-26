# QuantEngine: XGBoost Decision Threshold Sweep Report

*Evaluated under realistic transaction costs across Folds 1–7.*

---

## 1. Threshold Sweep Results Table
| Threshold | Mean Sharpe | Mean Sortino | Mean Max DD | Mean Profit Factor | Mean Expectancy (₹) | Mean Exposure | Mean Trades Count | Mean CAGR |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.50** | -0.94 | -0.86 | -5.97% | 0.92 | -2688.47 | 35.3% | 14.4 | -3.60% |
| **0.55** | -0.77 | -0.67 | -5.58% | 1.11 | -2122.11 | 32.5% | 12.7 | -3.30% |
| **0.60** | -0.59 | -0.48 | -4.80% | 1.31 | -1562.35 | 26.4% | 10.3 | -2.41% |
| **0.65** | 0.08 | 0.04 | -3.10% | 5114.50 | 2880.40 | 20.3% | 7.9 | -0.08% |
| **0.70** | 0.22 | 0.22 | -2.08% | 8724.64 | 2185.29 | 13.0% | 5.3 | 0.37% |
| **0.75** | -0.49 | -0.33 | -1.82% | 1.24 | -1090.84 | 8.6% | 3.4 | -1.04% |
| **0.80** | -0.07 | -0.09 | -1.02% | 1.14 | 27.21 | 5.4% | 2.0 | -0.35% |
| **0.85** | -0.05 | -0.02 | -0.43% | 0.95 | -486.36 | 1.7% | 0.4 | -0.15% |
| **0.90** | 0.00 | 0.00 | 0.00% | 1.00 | 0.00 | 0.0% | 0.0 | 0.00% |

## 2. Strategic Insights
- **Optimal Decision Coordinate**: Symmetrical threshold of **`0.70`** yields the highest risk-adjusted profile with a Sharpe of **`0.22`** and CAGR of **`0.37%`**.
- **Trade Frequency Optimization**: Raising the threshold restricts marginal trades, lowering the transaction cost drag (mean trades count goes from `14.4` to `0.0`).