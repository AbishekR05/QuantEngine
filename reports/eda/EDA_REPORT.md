# QuantEngine: Consolidated Exploratory Data Analysis (EDA) Report
**Document Version**: v1.0.0 (Phase 2 Master Compilation)
**Consolidation Date**: 2026-07-24 22:31:34
**Target Asset**: Nifty 50 Index (Features & Target Labels)

---

## Executive Summary
| Metadata Dimension | Status / Details |
| :--- | :--- |
| **Project Status** | Phase 2 (Completed) |
| **Dataset Quality** | Excellent |
| **Missing Values** | Expected warm-up only |
| **Market Coverage** | 2007–2026 |
| **Indicators** | 22 |
| **Engineered Labels** | Binary, Three-Class |
| **ML Ready?** | **NO** |
| **Reason** | Need Feature Selection, Need Train/Test Pipeline, Need Backtesting |

---

## Phase 3 Readiness Checklist
| Status | Step / Milestone | Phase |
| :---: | :--- | :--- |
| ✔ | Data Collected | Phase 1 |
| ✔ | Features Engineered | Phase 1 |
| ✔ | Dataset Validated | Phase 2 |
| ✔ | Correlations Studied | Phase 2 |
| ✔ | Outliers Understood | Phase 2 |
| ✔ | Market Regimes Created | Phase 2 |
| ✔ | Labels Generated | Phase 2 |
| ✔ | Scaling Recommendations Ready | Phase 2 |
| ⬜ | Train/Test Pipeline | Phase 3 |
| ⬜ | Walk Forward Validation | Phase 3 |
| ⬜ | Feature Selection | Phase 3 |
| ⬜ | Model Training | Phase 3 |
| ⬜ | Hyperparameter Search | Phase 3 |
| ⬜ | Backtesting | Phase 3 |
| ⬜ | Paper Trading | Phase 3 |

---

## Table of Contents
1. [Dataset Overview & Quality Summary](#1-dataset-overview--quality-summary)
2. [Descriptive Statistical Distributions](#2-descriptive-statistical-distributions)
3. [Core Feature Visualizations Summary](#3-core-feature-visualizations-summary)
4. [Correlation Taxonomy & Redundant Pairs](#4-correlation-taxonomy--redundant-pairs)
5. [Outlier Analysis & Market Shocks Chronology](#5-outlier-analysis--market-shocks-chronology)
6. [Market Regimes Profile (Trend & Volatility)](#6-market-regimes-profile-trend--volatility)
7. [Feature Usefulness & Information Entanglement](#7-feature-usefulness--information-entanglement)
8. [Label Engineering & Supervised Targets](#8-label-engineering--supervised-targets)
9. [Feature Scaling Recommendations](#9-feature-scaling-recommendations)
10. [Final Conclusions](#10-final-conclusions)


---

## 1. Dataset Overview & Quality Summary
The consolidated dataset `nifty_features.csv` represents the primary output of Phase 1 (Feature Engineering). It spans historical sessions from 2007 to 2026. The table below outlines the metadata characteristics of this dataset:

# Dataset summary report for: `nifty_features`
**Report Generated At**: 2026-07-10 23:56:23

## 1. Overview Statistics
| Metric | Value |
| :--- | :--- |
| **Row Count** | 4613 |
| **Column Count** | 23 |
| **Date Range** | 2007-09-17 to 2026-07-09 |
| **Memory Footprint** | 1.0692 MB |

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
| `EMA_200` | float64 |
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
| `SMA_200` | 199 | 4.31% |
| `RSI_14` | 1 | 0.02% |
| `BB_Middle` | 19 | 0.41% |
| `BB_Upper` | 19 | 0.41% |
| `BB_Lower` | 19 | 0.41% |
| `Daily_Return` | 1 | 0.02% |
| `Log_Return` | 1 | 0.02% |

*Note: The other 14 columns contain no missing values.*

## 4. Duplicate Check Results
- **Exact Duplicate Rows**: 0
- **Duplicate Date Entries**: 0

## 5. Domain & Validation Audit Notes
> [!NOTE]
> For `nifty_features` dataset: Leading missing values (`NaNs`) in indicators like `SMA_20`, `SMA_50`, `SMA_200`, `BB_Upper`, `BB_Lower`, and `ATR_14` are standard. These are lookback warm-up periods necessary for rolling mathematical calculations. They are directly proportional to each indicator's window setting and do not represent data pipeline failures.

---

## 2. Descriptive Statistical Distributions
Standard statistical moments (mean, std, skewness, excess kurtosis, and quartiles) were computed for all numerical features. High skewness ($|S| \ge 1.0$) and heavy tails ($K \ge 3.0$) are flagged for robust preprocessing:

# Statistical summary report for: `nifty_features`
**Report Generated At**: 2026-07-10 23:56:25

*Convention Note: Excess Kurtosis is reported below. A normal distribution corresponds to a kurtosis value of 0. Kurtosis values greater than 0 indicate a fat-tailed distribution.*

## 1. Descriptive Statistics Table
| Column Name | N | Mean | Median | Mode (first) | Modes Count | Std Dev | Variance | Min | Max | 25% | 50% | 75% | Skewness | Excess Kurtosis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Open` | 4613 | 11288.0534 | 8891.1504 | 2714.7000 | 41 | 6625.5532 | 43897954.5792 | 2553.6001 | 26333.6992 | 5715.6499 | 8891.1504 | 16515.6504 | 0.8455 | -0.5370 |
| `High` | 4613 | 11347.3927 | 8945.7998 | 3147.2000 | 41 | 6646.1519 | 44171334.7400 | 2585.3000 | 26373.1992 | 5754.5498 | 8945.7998 | 16610.9492 | 0.8477 | -0.5361 |
| `Low` | 4613 | 11213.5316 | 8821.9004 | 2611.9500 | 39 | 6599.5890 | 43554574.9903 | 2252.7500 | 26210.0508 | 5677.0000 | 8821.9004 | 16410.1992 | 0.8457 | -0.5334 |
| `Close` | 4613 | 11281.7454 | 8879.2002 | 5274.8501 | 2 | 6623.2471 | 43867402.2342 | 2524.2000 | 26328.5508 | 5717.1499 | 8879.2002 | 16520.8496 | 0.8464 | -0.5360 |
| `Adj Close` | 4613 | 11281.7454 | 8879.2002 | 5274.8501 | 2 | 6623.2471 | 43867402.2342 | 2524.2000 | 26328.5508 | 5717.1499 | 8879.2002 | 16520.8496 | 0.8464 | -0.5360 |
| `Volume` | 4613 | 217165.5539 | 193900.0000 | 0.0000 | 1 | 206625.4391 | 42694072085.1062 | 0.0000 | 1811000.0000 | 0.0000 | 193900.0000 | 304400.0000 | 1.3924 | 3.6323 |
| `SMA_20` | 4594 | 11268.4979 | 8804.6837 | 2715.1800 | 4594 | 6600.9839 | 43572988.9306 | 2715.1800 | 26044.9802 | 5738.8632 | 8804.6837 | 16458.5675 | 0.8490 | -0.5277 |
| `SMA_50` | 4564 | 11246.6817 | 8902.0540 | 25059.8200 | 1 | 6569.6395 | 43160162.7774 | 2784.1760 | 25971.7401 | 5732.2107 | 8902.0540 | 16503.7730 | 0.8537 | -0.5119 |
| `SMA_200` | 4414 | 11117.7992 | 8915.0314 | 3369.8087 | 4414 | 6371.3741 | 40594407.7974 | 3369.8087 | 25348.9131 | 5704.6616 | 8915.0314 | 16524.3205 | 0.8656 | -0.4530 |
| `EMA_20` | 4613 | 11241.5978 | 8804.3648 | 2710.0607 | 4613 | 6599.1960 | 43549388.3111 | 2710.0607 | 26081.5641 | 5697.7036 | 8804.3648 | 16438.0568 | 0.8537 | -0.5215 |
| `EMA_50` | 4613 | 11178.5547 | 8663.9296 | 2801.1556 | 4613 | 6561.4415 | 43052514.0390 | 2801.1556 | 25913.0351 | 5675.0207 | 8663.9296 | 16491.5922 | 0.8657 | -0.4961 |
| `EMA_200` | 4613 | 10852.1328 | 8375.4885 | 3411.4232 | 4613 | 6332.6710 | 40102722.1699 | 3411.4232 | 25251.0377 | 5573.4802 | 8375.4885 | 15883.9953 | 0.9121 | -0.3852 |
| `RSI_14` | 4612 | 53.9634 | 54.4034 | 100.0000 | 1 | 12.7856 | 163.4725 | 12.9418 | 100.0000 | 44.8739 | 54.4034 | 63.1166 | -0.0042 | -0.1966 |
| `MACD` | 4613 | 29.3904 | 37.2045 | -1005.8375 | 4613 | 140.5957 | 19767.1497 | -1005.8375 | 451.0834 | -43.7259 | 37.2045 | 102.3527 | -1.0531 | 6.1504 |
| `MACD_Signal` | 4613 | 29.2948 | 37.3528 | -848.3328 | 4613 | 132.4382 | 17539.8664 | -848.3328 | 413.9853 | -39.9011 | 37.3528 | 95.3251 | -0.9645 | 5.5249 |
| `MACD_Hist` | 4613 | 0.0956 | -0.4299 | -278.2977 | 4613 | 42.1648 | 1777.8699 | -278.2977 | 230.5792 | -22.0143 | -0.4299 | 21.8294 | 0.0680 | 4.7126 |
| `BB_Middle` | 4594 | 11268.4979 | 8804.6837 | 2715.1800 | 4594 | 6600.9839 | 43572988.9306 | 2715.1800 | 26044.9802 | 5738.8632 | 8804.6837 | 16458.5675 | 0.8490 | -0.5277 |
| `BB_Upper` | 4594 | 11652.1336 | 9124.8092 | 2871.5583 | 4594 | 6746.0124 | 45508682.9151 | 2871.5583 | 26550.3541 | 6009.5696 | 9124.8092 | 17226.4475 | 0.8490 | -0.5417 |
| `BB_Lower` | 4594 | 10884.8621 | 8558.7871 | 2432.8663 | 4594 | 6463.7584 | 41780172.2120 | 2432.8663 | 25772.2147 | 5477.8805 | 8558.7871 | 15675.2241 | 0.8487 | -0.5077 |
| `ATR_14` | 4613 | 146.8377 | 119.0251 | 49.7260 | 4613 | 77.7242 | 6041.0574 | 49.7260 | 535.4672 | 88.3105 | 119.0251 | 187.3349 | 1.3956 | 2.1836 |
| `Daily_Return` | 4612 | 0.0004 | 0.0006 | 0.0000 | 1 | 0.0130 | 0.0002 | -0.1298 | 0.1774 | -0.0052 | 0.0006 | 0.0065 | 0.0556 | 15.9086 |
| `Log_Return` | 4612 | 0.0004 | 0.0006 | 0.0000 | 1 | 0.0130 | 0.0002 | -0.1390 | 0.1633 | -0.0053 | 0.0006 | 0.0065 | -0.2810 | 15.0696 |

## 2. Interpretive Data Observations
### Skewness Warnings
The following columns exhibit high skewness (absolute value > 1.0):
- `Volume` (Skewness: 1.3924)
- `MACD` (Skewness: -1.0531)
- `ATR_14` (Skewness: 1.3956)

### Heavy-Tail Warnings (Excess Kurtosis)
The following columns exhibit fat-tailed distributions (excess kurtosis > 3.0):
- `Volume` (Excess Kurtosis: 3.6323)
- `MACD` (Excess Kurtosis: 6.1504)
- `MACD_Signal` (Excess Kurtosis: 5.5249)
- `MACD_Hist` (Excess Kurtosis: 4.7126)
- `Daily_Return` (Excess Kurtosis: 15.9086) (Expected for financial return series)
- `Log_Return` (Excess Kurtosis: 15.0696) (Expected for financial return series)

### Zero Variance Flags
No zero-variance columns were detected. (Data values fluctuate normally).

## 3. Variable Sample Sizes (N)
The following indicators were computed over subset sample sizes due to rolling warm-ups:
| Column Name | Effective N | Warm-up NaNs |
| :--- | :--- | :--- |
| `SMA_20` | 4594 | 19 |
| `SMA_50` | 4564 | 49 |
| `SMA_200` | 4414 | 199 |
| `RSI_14` | 4612 | 1 |
| `BB_Middle` | 4594 | 19 |
| `BB_Upper` | 4594 | 19 |
| `BB_Lower` | 4594 | 19 |
| `Daily_Return` | 4612 | 1 |
| `Log_Return` | 4612 | 1 |

---

## 3. Core Feature Visualizations Summary
A suite of 16 diagnostic charts was generated under `reports/eda/figures/` to confirm signal shape and uncover structure:
1. **Line Plots (Nifty Close & Moving Averages)**: Displays price trajectory over 19 years relative to SMA_200, EMA_20, and EMA_50.
2. **Bollinger Bands Shaded Region**: Visualizes price boundaries cleanly as a light blue band rather than intersecting lines.
3. **RSI_14 with Bands**: Plots RSI with 30/70 reference lines and light green shading in the normal region.
4. **Volume zero-volume annotations**: Shaded pink area ("Expected Outliers Zero-Volume Era 2007–2013") and arrow pointing at the zero-bar on the histogram.
5. **EMA_200 Line Chart**: Confirms long-term trend alignment.
6. **Boxplot for Volume**: Displays outlier dispersion alongside zero-volume text annotations.


---

## 4. Correlation Taxonomy & Redundant Pairs
## 5. Near-Duplicate / Highly Redundant Features
No look-ahead leakage was identified in this feature set — all flagged pairs below represent redundancy/multicollinearity, not validation leakage.

> [!WARNING]
> **High multicollinearity risk identified (Pearson $|r| \ge 0.99$):**
> These features are nearly identical. Using both in regression or neural network models causes extreme multicollinearity. Review if they represent identical inputs:

> - `Close` ↔ `Adj Close` (Correlation: 1.000000)
> - `SMA_20` ↔ `BB_Middle` (Correlation: 1.000000)
> - `Open` ↔ `High` (Correlation: 0.999952)
> - `SMA_20` ↔ `EMA_20` (Correlation: 0.999945)
> - `EMA_20` ↔ `BB_Middle` (Correlation: 0.999945)
> - `High` ↔ `Close` (Correlation: 0.999944)
> - `High` ↔ `Adj Close` (Correlation: 0.999944)
> - `Low` ↔ `Close` (Correlation: 0.999944)
> - `Low` ↔ `Adj Close` (Correlation: 0.999944)
> - `Open` ↔ `Low` (Correlation: 0.999927)
> - `High` ↔ `Low` (Correlation: 0.999912)
> - `Open` ↔ `Close` (Correlation: 0.999880)
> - `Open` ↔ `Adj Close` (Correlation: 0.999880)
> - `SMA_50` ↔ `EMA_50` (Correlation: 0.999858)
> - `Daily_Return` ↔ `Log_Return` (Correlation: 0.999638)
> - `SMA_200` ↔ `EMA_200` (Correlation: 0.999466)
> - `EMA_20` ↔ `EMA_50` (Correlation: 0.999462)
> - `SMA_20` ↔ `BB_Upper` (Correlation: 0.999434)
> - `BB_Middle` ↔ `BB_Upper` (Correlation: 0.999434)
> - `EMA_20` ↔ `BB_Upper` (Correlation: 0.999401)
> - `EMA_50` ↔ `BB_Middle` (Correlation: 0.999395)
> - `SMA_20` ↔ `EMA_50` (Correlation: 0.999395)
> - `BB_Middle` ↔ `BB_Lower` (Correlation: 0.999384)
> - `SMA_20` ↔ `BB_Lower` (Correlation: 0.999384)
> - `High` ↔ `EMA_20` (Correlation: 0.999354)
> - `EMA_20` ↔ `BB_Lower` (Correlation: 0.999305)
> - `Open` ↔ `EMA_20` (Correlation: 0.999281)
> - `EMA_50` ↔ `BB_Upper` (Correlation: 0.999241)
> - `Close` ↔ `EMA_20` (Correlation: 0.999211)
> - `Adj Close` ↔ `EMA_20` (Correlation: 0.999211)
> - `Low` ↔ `EMA_20` (Correlation: 0.999151)
> - `High` ↔ `BB_Middle` (Correlation: 0.999081)
> - `High` ↔ `SMA_20` (Correlation: 0.999081)
> - `SMA_50` ↔ `EMA_20` (Correlation: 0.999025)
> - `Open` ↔ `SMA_20` (Correlation: 0.998998)
> - `Open` ↔ `BB_Middle` (Correlation: 0.998998)
> - `SMA_50` ↔ `BB_Middle` (Correlation: 0.998958)
> - `SMA_20` ↔ `SMA_50` (Correlation: 0.998958)
> - `Close` ↔ `SMA_20` (Correlation: 0.998921)
> - `Adj Close` ↔ `SMA_20` (Correlation: 0.998921)
> - `Close` ↔ `BB_Middle` (Correlation: 0.998921)
> - `Adj Close` ↔ `BB_Middle` (Correlation: 0.998921)
> - `SMA_50` ↔ `BB_Upper` (Correlation: 0.998904)
> - `Low` ↔ `SMA_20` (Correlation: 0.998851)
> - `Low` ↔ `BB_Middle` (Correlation: 0.998851)
> - `Open` ↔ `BB_Lower` (Correlation: 0.998593)
> - `High` ↔ `BB_Lower` (Correlation: 0.998579)
> - `Low` ↔ `BB_Lower` (Correlation: 0.998550)
> - `Adj Close` ↔ `BB_Lower` (Correlation: 0.998515)
> - `Close` ↔ `BB_Lower` (Correlation: 0.998515)
> - `High` ↔ `BB_Upper` (Correlation: 0.998406)
> - `EMA_50` ↔ `BB_Lower` (Correlation: 0.998349)
> - `Open` ↔ `BB_Upper` (Correlation: 0.998230)
> - `High` ↔ `EMA_50` (Correlation: 0.998156)
> - `Close` ↔ `BB_Upper` (Correlation: 0.998155)
> - `Adj Close` ↔ `BB_Upper` (Correlation: 0.998155)
> - `Open` ↔ `EMA_50` (Correlation: 0.998027)
> - `Low` ↔ `BB_Upper` (Correlation: 0.997985)
> - `Adj Close` ↔ `EMA_50` (Correlation: 0.997957)
> - `Close` ↔ `EMA_50` (Correlation: 0.997957)
> - `Low` ↔ `EMA_50` (Correlation: 0.997848)
> - `SMA_50` ↔ `BB_Lower` (Correlation: 0.997809)
> - `BB_Upper` ↔ `BB_Lower` (Correlation: 0.997637)
> - `High` ↔ `SMA_50` (Correlation: 0.997445)
> - `Open` ↔ `SMA_50` (Correlation: 0.997296)
> - `Adj Close` ↔ `SMA_50` (Correlation: 0.997221)
> - `Close` ↔ `SMA_50` (Correlation: 0.997221)
> - `EMA_50` ↔ `EMA_200` (Correlation: 0.997200)
> - `Low` ↔ `SMA_50` (Correlation: 0.997088)
> - `SMA_50` ↔ `EMA_200` (Correlation: 0.996927)
> - `EMA_200` ↔ `BB_Upper` (Correlation: 0.995359)
> - `EMA_20` ↔ `EMA_200` (Correlation: 0.995077)
> - `SMA_20` ↔ `EMA_200` (Correlation: 0.994854)
> - `EMA_200` ↔ `BB_Middle` (Correlation: 0.994854)
> - `SMA_200` ↔ `EMA_50` (Correlation: 0.994835)
> - `SMA_50` ↔ `SMA_200` (Correlation: 0.994506)
> - `High` ↔ `EMA_200` (Correlation: 0.993371)
> - `Open` ↔ `EMA_200` (Correlation: 0.993155)
> - `EMA_200` ↔ `BB_Lower` (Correlation: 0.993127)
> - `Close` ↔ `EMA_200` (Correlation: 0.993125)
> - `Adj Close` ↔ `EMA_200` (Correlation: 0.993125)
> - `Low` ↔ `EMA_200` (Correlation: 0.992962)
> - `SMA_200` ↔ `BB_Upper` (Correlation: 0.992755)
> - `SMA_200` ↔ `EMA_20` (Correlation: 0.992185)
> - `SMA_20` ↔ `SMA_200` (Correlation: 0.991941)
> - `SMA_200` ↔ `BB_Middle` (Correlation: 0.991941)
> - `High` ↔ `SMA_200` (Correlation: 0.990369)
> - `Open` ↔ `SMA_200` (Correlation: 0.990105)
> - `Close` ↔ `SMA_200` (Correlation: 0.990096)
> - `Adj Close` ↔ `SMA_200` (Correlation: 0.990096)


---

## 5. Outlier Analysis & Market Shocks Chronology

---

## 6. Market Regimes Profile (Trend & Volatility)
## Methodology: Formal Definitions
This module evaluates market behavior across two independent dimensions: direction (Trend) and dispersion (Volatility).

**1. Rolling Return Formula** (used for trend classification):
```
RollingReturn_t = (Close_t - Close_(t - trend_window)) / Close_(t - trend_window)
```
**2. Rolling Volatility Formula** (used for volatility classification):
```
RollingVolatility_t = StdDev(DailyReturn_(t-vol_window+1), ..., DailyReturn_t)
```
**3. Trend Regime Assignment Rules**:
```
Bull:      Close_t > SMA_200_t   AND   RollingReturn_t > +trend_threshold
Bear:      Close_t < SMA_200_t   AND   RollingReturn_t < -trend_threshold
Sideways:  |RollingReturn_t| <= trend_threshold  (regardless of SMA_200 position)
```
*Note: Conflicts where Close price relative to SMA_200 contradicts the trailing return direction are classified under the Sideways category to maintain high rigor for Bull and Bear definitions.*

**4. Volatility Regime Assignment Rules**:
```
High:    RollingVolatility_t > P75(RollingVolatility, full history)
Low:     RollingVolatility_t < P25(RollingVolatility, full history)
Normal:  otherwise
```

## 1. Important Caveat & Structural Warning
> [!WARNING]
> **Lookahead-Bias and Time Lag Warning:**
> Regime labels defined in this report are strictly computed using **backward-looking rolling windows** (no future data is referenced), making them technically free of lookahead-bias. However, a trend label (Bull/Bear/Sideways) assigned to *today* using a 63-day trailing window is, by definition, a description of **recent past behavior** rather than a real-time signal.
>
> As a result, there is a structural **lag** between actual regime shifts and the window crossing the configured threshold (e.g., a new Bear market won't be labeled 'Bear' until index returns drop below the threshold). This lag is perfectly acceptable for retrospective model evaluation (which is the purpose of this analysis), but these regime labels should **never** be fed directly into a predictive model as same-day features, as this lag would inject severe classification errors and feedback loops.

> [!NOTE]
> **Zero-Volume Limitation Validation:**
> The Nifty zero-volume limitation period (2007–2013) identified in Step 5 does **not** distort the volatility regimes. Volatility regimes are computed entirely using standard deviation of returns (`Daily_Return`) derived from price Close series, not `Volume`. Hence, historical zero-volume years have zero distortion effect on the volatility classifications below.

## 2. Regime Distribution Summaries
### Trend Regime Distribution
| Regime | Trading Days | Percentage of Dataset |
| :--- | :--- | :--- |
| Bull | 1716 | 37.20% |
| Bear | 719 | 15.59% |
| Sideways | 1978 | 42.88% |
| Insufficient Data | 200 | 4.34% |
| **Total** | 4613 | 100.00% |

### Volatility Regime Distribution
| Regime | Trading Days | Percentage of Dataset |
| :--- | :--- | :--- |
| High | 1148 | 24.89% |
| Normal | 2296 | 49.77% |
| Low | 1148 | 24.89% |
| Insufficient Data | 21 | 0.46% |
| **Total** | 4613 | 100.00% |

## 3. Per-Regime Performance & Persistence Statistics
### Trend Regime Performance & Persistence Metrics
| Regime | Period Count | Total Trading Days | Mean Daily Return | Median Daily Return | Volatility (Std Dev) | Avg Trading Days per Period | Min Duration | Max Duration | Median Duration | Avg Calendar Days |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Bear** | 71 | 719 | -0.1838% | -0.1426% | 2.0149% | 10.1 | 1 | 76 | 3 | 13.7 |
| **Sideways** | 194 | 1978 | +0.0275% | +0.0209% | 1.0045% | 10.2 | 1 | 84 | 5 | 13.7 |
| **Bull** | 123 | 1716 | +0.1688% | +0.1519% | 1.0164% | 14.0 | 1 | 122 | 3 | 19.2 |

### Volatility Regime Performance & Persistence Metrics
| Regime | Period Count | Total Trading Days | Mean Daily Return | Median Daily Return | Volatility (Std Dev) | Avg Trading Days per Period | Min Duration | Max Duration | Median Duration | Avg Calendar Days |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **High** | 48 | 1148 | +0.0687% | +0.1130% | 2.1461% | 23.9 | 1 | 314 | 8 | 34.5 |
| **Normal** | 119 | 2296 | +0.0195% | +0.0436% | 0.9335% | 19.3 | 1 | 96 | 11 | 27.2 |
| **Low** | 71 | 1148 | +0.0514% | +0.0596% | 0.5893% | 16.2 | 1 | 159 | 4 | 22.4 |

## 5. Trend Regime Transitions Matrix
> [!IMPORTANT]
> **Descriptive-Only Framing Disclaimer:**
> The table below shows the absolute count of historical transitions between contiguous periods of different trend regimes in the dataset. This analysis is strictly **descriptive and historical**; it is not a predictive Markov transition model and cannot be used to forecast the probability of future regime changes.

| From \ To | Bull | Bear | Sideways |
| :--- | :--- | :--- | :--- |
| **Bull** | — | 0 | 123 |
| **Bear** | 0 | — | 71 |
| **Sideways** | 123 | 70 | — |


---

## 7. Feature Usefulness & Information Entanglement
## 1. Explicit Non-Decision Statement
> [!IMPORTANT]
> **Standing Non-Decision and Non-Pruning Directive:**
> *This report ranks features along three independent dimensions. It does not recommend removing any feature. Feature selection decisions should be deferred until label-based (Step 8+) predictive relevance can be measured, since a feature's raw variance, redundancy with other features, or informational independence does not by itself determine whether it will be useful for predicting future market direction.*

## 3. Known Data Limitations & Distribution Quirks
- **Volume Zero-Inflation**: Volume's variance is dominated by its zero-inflated shape (due to the 2007–2013 calculation limitation). Its raw variance is extremely large but does not represent a clean trading signal. Use caution if using Volume's raw variance directly.
- **RSI Boundary Artifact**: During warm-up (first 13 days of series), RSI_14 is mathematically pinned near 100.0. This boundary artifact creates high artificial information concentration at the start of Nifty.
- **Structural Near-Duplicates**: Features like `Close` and `Adj Close`, or `SMA_20` and `BB_Middle`, are mathematically near-identical by construction. These display maximum Mutual Information ($\approx 3.32$ bits for 10 bins) and high redundant partner counts as expected.

## 7. Combined Side-by-Side Ranking Matrix
> [!NOTE]
> **Interpretation Guidance:**
> The table below brings all three perspectives together. Do not interpret this as a single sorted list. For example, `RSI_14` has low raw variance (by design) but shows moderate Mutual Information and low redundant partners, suggesting a distinct and useful signal type compared to price trend MAs.

| Feature | Raw Variance | Coefficient of Variation | Redundant Partners | Average MI (bits) | Max MI (bits) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `MACD_Hist` | 1777.8699 | 440.949535 | 0 | 0.1510 | 0.3705 |
| `Log_Return` | 0.0002 | 35.802535 | 1 | 0.2249 | 3.3219 |
| `Daily_Return` | 0.0002 | 29.029951 | 1 | 0.2249 | 3.3219 |
| `MACD` | 19767.1497 | 4.783726 | 1 | 0.3124 | 1.4946 |
| `MACD_Signal` | 17539.8664 | 4.520877 | 1 | 0.3033 | 1.4946 |
| `Volume` | 42694072085.1062 | 0.951465 | 0 | 0.7420 | 1.1568 |
| `BB_Lower` | 41780172.2120 | 0.593830 | 13 | 1.7235 | 2.7876 |
| `Low` | 43554574.9903 | 0.588538 | 13 | 1.7823 | 3.1137 |
| `Adj Close` | 43867402.2342 | 0.587076 | 13 | 1.7905 | 3.3219 |
| `Close` | 43867402.2342 | 0.587076 | 13 | 1.7905 | 3.3219 |
| `EMA_20` | 43549388.3111 | 0.587034 | 13 | 1.8184 | 3.0618 |
| `EMA_50` | 43052514.0390 | 0.586967 | 13 | 1.7577 | 2.9225 |
| `Open` | 43897954.5792 | 0.586953 | 13 | 1.7856 | 3.1160 |
| `SMA_20` | 43572988.9306 | 0.585791 | 13 | 1.8057 | 3.3219 |
| `BB_Middle` | 43572988.9306 | 0.585791 | 13 | 1.8057 | 3.3219 |
| `High` | 44171334.7400 | 0.585699 | 13 | 1.7973 | 3.1160 |
| `SMA_50` | 43160162.7774 | 0.584140 | 13 | 1.7075 | 2.9225 |
| `EMA_200` | 40102722.1699 | 0.583542 | 13 | 1.5922 | 2.5786 |
| `BB_Upper` | 45508682.9151 | 0.578951 | 13 | 1.7323 | 2.8310 |
| `SMA_200` | 40594407.7974 | 0.573079 | 13 | 1.5287 | 2.5786 |
| `ATR_14` | 6041.0574 | 0.529321 | 0 | 0.6403 | 0.9132 |
| `RSI_14` | 163.4725 | 0.236932 | 0 | 0.1260 | 0.7585 |

## 8. Mutual Information vs. Linear Correlation Divergences
This section highlights feature pairs where Mutual Information is relatively high ($\ge 0.35$ bits) but absolute linear Pearson correlation is low ($|r| \le 0.20$). These indicate strong **nonlinear or cyclical dependencies** that standard correlation models miss:

No significant nonlinear MI-vs-Correlation divergences detected.


---

## 8. Label Engineering & Supervised Targets
## 1. Important Lookahead Warning
> [!WARNING]
> **Supervised Target Leakage Caution:**
> These label columns are intentionally forward-looking (each label at row $t$ depends on closing price Close at row $t+1$). This is expected and correct for label data, but these versioned files must **never** be used as a feature-only input set during ML model training. **Always exclude label columns** (specifically `Label_Binary` and `Label_ThreeClass`) when using this data for feature extraction. Failing to do so will leak the future closing price into the inputs, resulting in 100% training accuracy but catastrophic failure in real-time execution.

## 2. Version A: Binary Classification Summary
- **Rule**: `Label_Binary = 1` if $Close_{t+1} > Close_t$, else `0`.
- **Flat Day Policy**: Exact-tie returns ($Close_{t+1} == Close_t$) are grouped into Class 0. This is a deliberate modeling choice for daily index series where ties are extremely rare but categorized conservatively as non-up days.
- **Last Row Policy**: The final row has no future period ($t+1$) to compare against and is strictly populated with `NaN` (null) to prevent lookahead extrapolation.

### Class Distribution (Binary)
| Class | Count | Percentage |
| :--- | :--- | :--- |
| 1.0 | 2446 | 53.04% |
| 0.0 | 2166 | 46.96% |
| NaN (Last Row) | 1 | 0.02% |

## 3. Version B: Three-Class Classification Summary
- **Rule**: Return $R_{t+1} = (Close_{t+1} - Close_t) / Close_t$
  - **BUY**: $R_{t+1} > +0.0050$ (+0.50%)
  - **SELL**: $R_{t+1} < -0.0050$ (-0.50%)
  - **HOLD**: otherwise (including exact-tie zero returns)
- **Last Row Policy**: strictly populated with `NaN` (null).
- **Imbalance / Sensitivity**: The threshold is config-driven. A tight threshold (e.g. 0.50% daily) means class distributions are naturally sensitive; larger thresholds will compress BUY/SELL counts and inflate HOLD counts. Observe the resulting imbalance below to configure classification loss weights in Phase 3.

### Class Distribution (Three-Class)
| Class | Count | Percentage |
| :--- | :--- | :--- |
| HOLD | 2018 | 43.76% |
| BUY | 1398 | 30.31% |
| SELL | 1196 | 25.93% |
| NaN (Last Row) | 1 | 0.02% |

## 4. Regime vs. Class Label Cross-Reference Table
Descriptive cross-tabulation checking label behavior across Step 6 trend regimes. Expected market behavior dictates BUY frequencies should be higher in Bull regimes, while SELL frequencies should expand in Bear regimes:

| Trend Regime \ Class | BUY | HOLD | SELL | All |
| :--- | :--- | :--- | :--- | :--- |
| **Bear** | 283 | 205 | 231 | 719 |
| **Bull** | 455 | 871 | 390 | 1716 |
| **Insufficient Data** | 74 | 53 | 73 | 200 |
| **Sideways** | 586 | 889 | 502 | 1977 |
| **All** | 1398 | 2018 | 1196 | 4612 |

## 5. Version C: Future Option-Chain Labels Design note
> [!NOTE]
> **Option-Chain Label Design Sketch (Design Only — No Data Output):**
>
> **1. Pipeline Requirements & Data Gaps:**
> Option-chain modeling requires historical end-of-day (or tick-level) derivative chains from the exchange: Option Strike Prices, Call/Put Premium Prices (Bid/Ask/Last Close), Expiry Dates, and Implied Volatility (IV) surface charts. This project currently does not possess derivative data pipelines, making Version C unimplemented in the current database.
>
> **2. Proposed ATM Option Profitability Sketch:**
> - Let $C_t$ be the premium of an At-The-Money (ATM) Call Option expiring in $D$ days, and $P_t$ be the premium of an ATM Put Option.
> - **BUY ATM CALL (Class 2)**: If next-day price expansion exceeds premium decay: $Close_{t+1} - Close_t > C_t \cdot (\text{decay factor})$.
> - **BUY ATM PUT (Class 0)**: If next-day price drop exceeds premium decay: $Close_t - Close_{t+1} > P_t \cdot (\text{decay factor})$.
> - **HOLD (Class 1)**: If premium decay (theta) exceeds directional expansion, representing horizontal range-bound days.
>
> **3. Next Steps**: To execute this version, a separate derivative loader (Phase 1 extension) must be designed to fetch, strike-align, and map options tables before appending them to feature datasets.


---

## 9. Feature Scaling Recommendations
## 1. Explicit Non-Action Statement
> [!IMPORTANT]
> **Descriptive Recommendation Framework Directive:**
> *This report provides scaling recommendations only. No column in nifty_features.csv has been scaled, transformed, or modified. Scaler selection and fitting should occur later, during model-specific pipeline construction in Phase 3, using only training-fold statistics to avoid leakage.*

## 2. Forward-Looking Time-Series Leakage warning
> [!WARNING]
> **Supervised Data-Leakage Caveat:**
> In time-series machine learning pipelines, scalers must **never** be fitted on the entire dataset. Fitting a `StandardScaler`, `MinMaxScaler`, or `RobustScaler` on the entire series prior to splitting will inject future distribution statistics (mean, variance, bounds) into earlier periods, causing severe lookahead bias. Instead, the scaler must be initialized and **fitted strictly on the training folds**, and then applied (transform only) to the validation and testing splits.

## 3. Per-Column Scaling Recommendations
Below is the recommendation matrix generated based on skewness, tails, and outlier statistics:
| Rank | Feature | Recommended Scaler | Justification |
| :--- | :--- | :--- | :--- |
| 1 | `Open` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.54) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 2 | `High` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.54) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 3 | `Low` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.53) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 4 | `Close` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.54) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 5 | `Adj Close` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.54) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 6 | `Volume` | **RobustScaler** | Heavy-tailed distribution (skew=+1.39, excess kurtosis=+3.63) with 54 confirmed real-event outliers. RobustScaler uses median/IQR to resist outliers. |
| 7 | `SMA_20` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.53) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 8 | `SMA_50` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.51) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 9 | `SMA_200` | **StandardScaler** | Symmetric distribution (skew=+0.87, excess kurtosis=-0.45) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 10 | `EMA_20` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.52) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 11 | `EMA_50` | **StandardScaler** | Symmetric distribution (skew=+0.87, excess kurtosis=-0.50) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 12 | `EMA_200` | **StandardScaler** | Symmetric distribution (skew=+0.91, excess kurtosis=-0.39) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 13 | `RSI_14` | **MinMaxScaler** | Naturally bounded indicator (conceptual range 0-100 for RSI_14). MinMaxScaler preserves the bounded range interpretation. |
| 14 | `MACD` | **RobustScaler** | Heavy-tailed distribution (skew=-1.05, excess kurtosis=+6.15) with 40 confirmed real-event outliers. RobustScaler uses median/IQR to resist outliers. |
| 15 | `MACD_Signal` | **RobustScaler** | Heavy-tailed distribution (skew=-0.96, excess kurtosis=+5.52) with 42 confirmed real-event outliers. RobustScaler uses median/IQR to resist outliers. |
| 16 | `MACD_Hist` | **RobustScaler** | Heavy-tailed distribution (skew=+0.07, excess kurtosis=+4.71) with 72 confirmed real-event outliers. RobustScaler uses median/IQR to resist outliers. |
| 17 | `BB_Middle` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.53) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 18 | `BB_Upper` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.54) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 19 | `BB_Lower` | **StandardScaler** | Symmetric distribution (skew=+0.85, excess kurtosis=-0.51) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance. |
| 20 | `ATR_14` | **RobustScaler** | Heavy-tailed distribution (skew=+1.40, excess kurtosis=+2.18) with 57 confirmed real-event outliers. RobustScaler uses median/IQR to resist outliers. |
| 21 | `Daily_Return` | **RobustScaler** | Heavy-tailed distribution (skew=+0.06, excess kurtosis=+15.91) with 69 confirmed real-event outliers. RobustScaler uses median/IQR to resist outliers. |
| 22 | `Log_Return` | **RobustScaler** | Heavy-tailed distribution (skew=-0.28, excess kurtosis=+15.07) with 70 confirmed real-event outliers. RobustScaler uses median/IQR to resist outliers. |

## 4. Special Case Analysis: Trading Volume
Volume warrants specialized treatment compared to regular numerical oscillators or moving averages due to three compounding statistical characteristics established in prior steps:

1. **Zero-Inflation**: Volume displays ~29% zero values because of the 2007–2013 calculation feed limitation documented in Step 5.
2. **Massive Skewness & Variance**: Volume possesses a high variance profile (Coefficient of Variation $\approx 0.95$).
3. **Extreme Outliers**: Confirming Step 5's chronology, Volume contains numerous high-side outliers matching high-volatility events.

**Modeling Guidance for Phase 3:**
- A plain `RobustScaler` is recommended if Volume is used directly. However, standard practice for volume-like indicators is to apply a **log-transform** (e.g. `log1p(Volume)` to handle zeros gracefully) prior to scaler fitting. This compresses the high-end right-side tail, making subsequent scaling significantly more effective.
- *Note: Consistent with the project's 'no automated modifications' rules, no log-transform has been applied to nifty_features.csv. This transform should be evaluated as an active preprocessing node in the training pipeline.*

## 5. Bounded Indicator Analysis: RSI
**RSI_14 Natural Boundaries:**
- Relative Strength Index (`RSI_14`) is mathematically bounded between `0.0` and `100.0` by construction. A `MinMaxScaler` is formally recommended here to preserve this bounded range. However, because RSI already exists within a known, small-scale bounded distribution (unlike raw price levels which have no theoretical ceiling), scaling RSI is largely a formality and can be omitted in models resistant to scale differences (e.g., decision tree ensembles).

## 6. Return Indicators Analysis: Daily Return vs. Log Return
**Scale Magnitude on Returns:**
- Both `Daily_Return` and `Log_Return` display outlier overlap and high excess kurtosis, resulting in a `RobustScaler` recommendation. However, returns are already centered near zero and occupy small-magnitude scales (values ranging roughly between $\pm 0.01$ and $\pm 0.05$). The practical impact of scaling returns is significantly smaller than scaling raw price indicators (which lie in the thousands). Scaling returns is primarily useful for distance-based ML classifiers (e.g. K-Nearest Neighbors or Support Vector Machines).

## 7. Structural Near-Duplicate Features
Features that are structural duplicates (such as `Close` and `Adj Close`, or `SMA_20` and `BB_Middle`) display identical statistical distributions. Consequently, they naturally receive identical scaler recommendations. This is expected and mathematically correct, rather than a redundant computation error.


---

## 10. Final Conclusions
### Key Findings
- **Dataset quality is excellent**: High completeness across price history, missing values restricted strictly to standard indicators' warm-up boundaries.
- **No pipeline failures detected**: Clean date formatting, zero duplicates, and complete numerical alignments.
- **Feature engineering successful**: 22 functional features generated across price trend, momentum, and statistical dispersion categories.
- **Market regimes identified**: Historical Trend (direction) and Volatility (dispersion) regimes successfully created and validated descriptive-only transition matrices.
- **Heavy multicollinearity exists among trend indicators**: Multicollinearity flags confirmed in Step 4 Pearson matrices demand model pruning.
- **Feature selection required**: High mutual information and redundancy counts necessitate feature subset selection prior to model training.
- **Dataset suitable for supervised learning**: Both Version A and Version B label files correctly appended and structured.
- **Options labels require derivative data**: ATM options v3 modeling requires a distinct option-chain loader to support strike-based theta decay math.

### Next Phase
**Machine Learning Pipeline**: Developing the Phase 3 training framework, feature selector nodes, walk-forward CV, hyperparameter searches, and backtests.