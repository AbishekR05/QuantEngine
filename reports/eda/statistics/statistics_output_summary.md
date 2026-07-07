# QuantEngine: Statistical Analysis Summary Report (Step 2)

This report details what was created and the specific statistical outputs generated during **Phase 2 - Step 2 (Statistical Analysis)**.

---

## 1. Components Created & Modified

We implemented the following pipeline additions:

1.  **Descriptive Calculator Module**: Created [statistics.py](file:///D:/Full%20Stack/QuantEngine/src/eda/statistics.py) under the `src/eda/` package.
    *   Exposes `StatisticalAnalyzer` class to process all numeric columns, skip NaNs, handle 1-item columns without crashing, and format summaries as Markdown tables.
    *   Includes `generate_all_statistics(config)` orchestrator function to load config paths and write results to disk.
2.  **Configuration Extension**: Added validation thresholds and exclude criteria under the `statistics` config block in [config.yaml](file:///D:/Full%20Stack/QuantEngine/config/config.yaml):
    ```yaml
    statistics:
      exclude_columns:
        - Date
      skew_threshold: 1.0
      kurtosis_threshold: 3.0
    ```
3.  **Config Validation Loader**: Expanded Pydantic models in [config_loader.py](file:///D:/Full%20Stack/QuantEngine/src/utils/config_loader.py) to parse and validate these threshold settings.

---

## 2. Descriptive Statistics Outputs

The descriptive statistics were computed over **4,610 daily trading sessions** (from `2007-09-17` to `2026-07-06`). 

Key statistics computed from the clean price data and technical indicators:

### Clean Price Series Statistics
([Full Report](file:///D:/Full%20Stack/QuantEngine/reports/eda/statistics/statistical_summary_clean.md))

| Metric Column | Mean | Median | Std Dev | Min | Max | Skewness | Excess Kurtosis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Open` | 11279.6393 | 8889.9502 | 6619.4872 | 2553.6001 | 26333.6992 | 0.8474 | -0.5315 |
| `High` | 11338.9494 | 8932.1001 | 6640.0623 | 2585.3000 | 26373.1992 | 0.8495 | -0.5307 |
| `Low` | 11205.1934 | 8818.2998 | 6593.6301 | 2252.7500 | 26210.0508 | 0.8476 | -0.5278 |
| `Close` | 11273.4160 | 8874.0996 | 6617.3423 | 2524.2000 | 26328.5508 | 0.8483 | -0.5304 |
| `Volume` | 217042.6898 | 193800.0000 | 206636.1345 | 0.0000 | 1811000.0000 | 1.3944 | 3.6381 |

### Technical Indicators Statistics (Selected Sample)
([Full Report](file:///D:/Full%20Stack/QuantEngine/reports/eda/statistics/statistical_summary_features.md))

| Indicator Column | Mean | Median | Std Dev | Min | Max | Skewness | Excess Kurtosis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `RSI_14` | 53.9634 | 54.4036 | 12.7887 | 12.9418 | 100.0000 | -0.0043 | -0.1976 |
| `ATR_14` | 146.7665 | 119.0160 | 77.6989 | 49.7260 | 535.4672 | 1.3988 | 2.1961 |
| `Daily_Return` | 0.0005 | 0.0006 | 0.0130 | -0.1298 | 0.1774 | 0.0556 | 15.9179 |
| `Log_Return` | 0.0004 | 0.0006 | 0.0130 | -0.1390 | 0.1633 | -0.2812 | 15.0791 |
| `MACD` | 29.3222 | 37.0750 | 140.6150 | -1005.8375 | 451.0834 | -1.0522 | 6.1490 |

---

## 3. Key Observations & Findings

1.  **Highly Skewed Features**:
    *   `Volume` (Skewness: 1.3944) and `ATR_14` (Skewness: 1.3988) show high positive skewness, indicating a long tail of right-side extreme values (common in volatility and trading volumes).
    *   `MACD` (Skewness: -1.0522) exhibits negative skewness.
2.  **Fat-Tailed / Leptokurtic Distributions**:
    *   `Daily_Return` (Excess Kurtosis: 15.9179) and `Log_Return` (Excess Kurtosis: 15.0791) show high excess kurtosis (well above the normal threshold of 0). This is a standard characteristic of financial time-series representing "fat tails" (extreme price moves like market crashes occur much more frequently than predicted by a normal distribution).
    *   `MACD` (6.1490) and `MACD_Signal` (5.5217) also exhibit heavy tails.
3.  **Variable Effective Sample Sizes ($N$)**:
    *   Due to indicator lookback warm-up periods, the effective sample sizes vary:
        *   `SMA_20`, `BB_Middle`, `BB_Upper`, `BB_Lower`: **4,591** rows (19 NaNs)
        *   `SMA_50`: **4,561** rows (49 NaNs)
        *   `SMA_200`: **4,411** rows (199 NaNs)
        *   `RSI_14`, `Daily_Return`, `Log_Return`: **4,609** rows (1 NaN)
4.  **Zero-Variance check**:
    *   No zero-variance columns were detected across both clean and features datasets, confirming that all columns vary normally and contain no stale/constant values.
