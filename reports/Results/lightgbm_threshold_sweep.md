# QuantEngine: LIGHTGBM Decision Threshold Sweep Report

*Evaluated under realistic transaction costs across Folds 1–7.*

---

## 1. Threshold Sweep Results Table
| Threshold | Mean Sharpe | Mean Sortino | Mean Max DD | Mean Profit Factor | Mean Expectancy (₹) | Mean Exposure | Mean Trades Count | Mean CAGR |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.55** | -0.59 | -0.60 | -23.81% | 0.76 | -1503.94 | 41.4% | 16.9 | -2.75% |
| **0.57** | -0.83 | -0.79 | -27.14% | 0.66 | -2072.44 | 38.9% | 16.0 | -3.67% |
| **0.59** | -0.92 | -0.83 | -25.70% | 0.63 | -2329.94 | 36.9% | 15.4 | -3.87% |
| **0.61** | -1.04 | -0.98 | -26.96% | 0.56 | -2859.40 | 36.8% | 14.3 | -4.40% |
| **0.63** | -0.97 | -0.91 | -25.58% | 0.56 | -2879.87 | 34.1% | 13.0 | -3.92% |
| **0.65** | -0.93 | -0.81 | -22.50% | 0.55 | -2940.69 | 30.4% | 11.9 | -3.59% |
| **0.67** | -0.55 | -0.47 | -14.21% | 0.70 | -1857.46 | 28.6% | 11.1 | -2.15% |
| **0.69** | -0.40 | -0.32 | -11.90% | 0.76 | -1501.93 | 25.4% | 9.7 | -1.53% |
| **0.71** | -0.63 | -0.47 | -16.09% | 0.63 | -2433.55 | 22.2% | 8.7 | -2.22% |
| **0.73** | -0.78 | -0.53 | -16.85% | 0.53 | -3388.11 | 18.5% | 7.4 | -2.60% |
| **0.75** | -0.61 | -0.40 | -13.42% | 0.60 | -2807.70 | 16.8% | 6.7 | -1.96% |

## 2. Strategic Insights
- **Optimal Decision Coordinate**: Symmetrical threshold of **`0.69`** yields the highest risk-adjusted profile with a Sharpe of **`-0.40`** and CAGR of **`-1.53%`**.
- **Trade Frequency Optimization**: Raising the threshold restricts marginal trades, lowering the transaction cost drag (mean trades count goes from `16.9` to `6.7`).