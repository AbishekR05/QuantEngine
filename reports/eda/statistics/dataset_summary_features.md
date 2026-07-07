# Dataset summary report for: `nifty_features`
**Report Generated At**: 2026-07-08 00:11:07

## 1. Overview Statistics
| Metric | Value |
| :--- | :--- |
| **Row Count** | 4610 |
| **Column Count** | 22 |
| **Date Range** | 2007-09-17 to 2026-07-06 |
| **Memory Footprint** | 1.0333 MB |

## 2. Column Data Types
| Column Name | Pandas Data Type |
| :--- | :--- |
| `Date` | object |
| `Open` | float64 |
| `High` | float64 |
| `Low` | float64 |
| `Close` | float64 |
| `Adj Close` | float64 |
| `Volume` | int64 |
| `SMA_20` | float64 |
| `SMA_50` | float64 |
| `SMA_200` | float64 |
| `EMA_20` | float64 |
| `EMA_50` | float64 |
| `RSI_14` | float64 |
| `MACD` | float64 |
| `MACD_Signal` | float64 |
| `MACD_Hist` | float64 |
| `BB_Middle` | float64 |
| `BB_Upper` | float64 |
| `BB_Lower` | float64 |
| `ATR_14` | float64 |
| `Daily_Return` | float64 |
| `Log_Return` | float64 |

## 3. Missing Value Analysis
| Column Name | Missing Count | Percentage |
| :--- | :--- | :--- |
| `SMA_20` | 19 | 0.41% |
| `SMA_50` | 49 | 1.06% |
| `SMA_200` | 199 | 4.32% |
| `RSI_14` | 1 | 0.02% |
| `BB_Middle` | 19 | 0.41% |
| `BB_Upper` | 19 | 0.41% |
| `BB_Lower` | 19 | 0.41% |
| `Daily_Return` | 1 | 0.02% |
| `Log_Return` | 1 | 0.02% |

*Note: The other 13 columns contain no missing values.*

## 4. Duplicate Check Results
- **Exact Duplicate Rows**: 0
- **Duplicate Date Entries**: 0

## 5. Domain & Validation Audit Notes
> [!NOTE]
> For `nifty_features` dataset: Leading missing values (`NaNs`) in indicators like `SMA_20`, `SMA_50`, `SMA_200`, `BB_Upper`, `BB_Lower`, and `ATR_14` are standard. These are lookback warm-up periods necessary for rolling mathematical calculations. They are directly proportional to each indicator's window setting and do not represent data pipeline failures.