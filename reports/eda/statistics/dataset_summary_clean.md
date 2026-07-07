# Dataset summary report for: `nsei_clean`
**Report Generated At**: 2026-07-08 00:11:07

## 1. Overview Statistics
| Metric | Value |
| :--- | :--- |
| **Row Count** | 4610 |
| **Column Count** | 7 |
| **Date Range** | 2007-09-17 to 2026-07-06 |
| **Memory Footprint** | 0.5057 MB |

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

## 3. Missing Value Analysis
All columns contain **0** missing values (100% complete).

## 4. Duplicate Check Results
- **Exact Duplicate Rows**: 0
- **Duplicate Date Entries**: 0

## 5. Domain & Validation Audit Notes
> [!NOTE]
> For `nsei_clean` dataset: Approximately 1,320 rows contain `Volume == 0`. For index tickers like NIFTY 50 (`^NSEI`), this is standard. Exchange feeds often do not supply volume calculations for index derivatives historically, or report 0 during earlier years. This is expected behavior and not a data corruption defect.