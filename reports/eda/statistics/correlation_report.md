# QuantEngine: Feature Correlation Analysis Report
**Report Generated At**: 2026-07-13 00:32:55
**Number of Analyzed Features**: 22

## 1. Methodology Summary
This report evaluates pairwise linear (**Pearson**) and rank-based (**Spearman**) correlations between all technical indicators.
- **Pearson correlation** captures linear relationships. It assumes normal distributions.
- **Spearman correlation** evaluates monotonic relationships and is less sensitive to extreme outliers or nonlinear mappings. Disagreements between Pearson and Spearman reveal non-linear patterns.
Constant columns yield `NaN` values. Pairwise correlations skip missing data (warm-up periods) dynamically.

## 2. Highest Correlation Pairs (Top Ranked)
### Top 20 Pairs: PEARSON
| Rank | Feature A | Feature B | Coefficient | Category | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `Close` | `Adj Close` | 1.0000 | Structural Correlations | These columns are functionally identical. Retain 'Close' and remove 'Adj Close' to eliminate exact duplication. |
| 2 | `SMA_20` | `BB_Middle` | 1.0000 | Structural Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. |
| 3 | `Open` | `High` | 1.0000 | Structural Correlations | Near-identical representation ($|r| = 1.0000$). Drop one column during model input selection. |
| 4 | `SMA_20` | `EMA_20` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 5 | `EMA_20` | `BB_Middle` | 0.9999 | Structural Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. |
| 6 | `High` | `Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 7 | `High` | `Adj Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 8 | `Low` | `Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 9 | `Low` | `Adj Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 10 | `Open` | `Low` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 11 | `High` | `Low` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 12 | `Open` | `Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 13 | `Open` | `Adj Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 14 | `SMA_50` | `EMA_50` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. |
| 15 | `Daily_Return` | `Log_Return` | 0.9996 | Derived Feature Correlations | Daily and log returns represent near-identical information. Retain one (typically Log_Return) and drop the other. |
| 16 | `SMA_200` | `EMA_200` | 0.9995 | Structural Correlations | Near-identical representation ($|r| = 0.9995$). Drop one column during model input selection. |
| 17 | `EMA_20` | `EMA_50` | 0.9995 | Structural Correlations | Near-identical representation ($|r| = 0.9995$). Drop one column during model input selection. |
| 18 | `SMA_20` | `BB_Upper` | 0.9994 | Indicator Correlations | Near-identical representation ($|r| = 0.9994$). Drop one column during model input selection. |
| 19 | `BB_Middle` | `BB_Upper` | 0.9994 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. |
| 20 | `EMA_20` | `BB_Upper` | 0.9994 | Indicator Correlations | Near-identical representation ($|r| = 0.9994$). Drop one column during model input selection. |

### Top 20 Pairs: SPEARMAN
| Rank | Feature A | Feature B | Coefficient | Category | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `Close` | `Adj Close` | 1.0000 | Structural Correlations | These columns are functionally identical. Retain 'Close' and remove 'Adj Close' to eliminate exact duplication. |
| 2 | `Daily_Return` | `Log_Return` | 1.0000 | Derived Feature Correlations | Daily and log returns represent near-identical information. Retain one (typically Log_Return) and drop the other. |
| 3 | `SMA_20` | `BB_Middle` | 1.0000 | Structural Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. |
| 4 | `Open` | `High` | 0.9998 | Structural Correlations | Near-identical representation ($|r| = 0.9998$). Drop one column during model input selection. |
| 5 | `High` | `Adj Close` | 0.9998 | Structural Correlations | Near-identical representation ($|r| = 0.9998$). Drop one column during model input selection. |
| 6 | `High` | `Close` | 0.9998 | Structural Correlations | Near-identical representation ($|r| = 0.9998$). Drop one column during model input selection. |
| 7 | `EMA_20` | `BB_Middle` | 0.9998 | Structural Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. |
| 8 | `SMA_20` | `EMA_20` | 0.9998 | Structural Correlations | Near-identical representation ($|r| = 0.9998$). Drop one column during model input selection. |
| 9 | `Low` | `Adj Close` | 0.9998 | Structural Correlations | Near-identical representation ($|r| = 0.9998$). Drop one column during model input selection. |
| 10 | `Low` | `Close` | 0.9998 | Structural Correlations | Near-identical representation ($|r| = 0.9998$). Drop one column during model input selection. |
| 11 | `Open` | `Low` | 0.9997 | Structural Correlations | Near-identical representation ($|r| = 0.9997$). Drop one column during model input selection. |
| 12 | `High` | `Low` | 0.9997 | Structural Correlations | Near-identical representation ($|r| = 0.9997$). Drop one column during model input selection. |
| 13 | `Open` | `Adj Close` | 0.9996 | Structural Correlations | Near-identical representation ($|r| = 0.9996$). Drop one column during model input selection. |
| 14 | `Open` | `Close` | 0.9996 | Structural Correlations | Near-identical representation ($|r| = 0.9996$). Drop one column during model input selection. |
| 15 | `SMA_50` | `EMA_50` | 0.9995 | Structural Correlations | Near-identical representation ($|r| = 0.9995$). Drop one column during model input selection. |
| 16 | `EMA_20` | `EMA_50` | 0.9986 | Structural Correlations | Near-identical representation ($|r| = 0.9986$). Drop one column during model input selection. |
| 17 | `EMA_50` | `BB_Middle` | 0.9985 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. |
| 18 | `SMA_20` | `EMA_50` | 0.9985 | Structural Correlations | Near-identical representation ($|r| = 0.9985$). Drop one column during model input selection. |
| 19 | `SMA_20` | `BB_Upper` | 0.9985 | Indicator Correlations | Near-identical representation ($|r| = 0.9985$). Drop one column during model input selection. |
| 20 | `BB_Middle` | `BB_Upper` | 0.9985 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. |

## 3. Redundancy & Domain Observations ($|r| \ge 0.9$)
The following feature pairs exhibit strong correlations (above threshold 0.9):
| Feature A | Feature B | Pearson $r$ | Category | Recommendation | Context / Domain Caveat |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Close` | `Adj Close` | 1.0000 | Structural Correlations | These columns are functionally identical. Retain 'Close' and remove 'Adj Close' to eliminate exact duplication. | Identical by construction; representing index close values without dividend distributions. |
| `SMA_20` | `BB_Middle` | 1.0000 | Structural Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | BB Middle Band is mathematically equivalent to SMA_20 by configuration design. |
| `Open` | `High` | 1.0000 | Structural Correlations | Near-identical representation ($|r| = 1.0000$). Drop one column during model input selection. | Structural intraday price metrics representing snapshots of the same daily session. |
| `SMA_20` | `EMA_20` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | BB Middle Band is mathematically equivalent to SMA_20 by configuration design. |
| `EMA_20` | `BB_Middle` | 0.9999 | Structural Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | BB Middle Band is mathematically equivalent to SMA_20 by configuration design. |
| `High` | `Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | Structural intraday price metrics representing snapshots of the same daily session. |
| `High` | `Adj Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | Structural intraday price metrics representing snapshots of the same daily session. |
| `Low` | `Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | Structural intraday price metrics representing snapshots of the same daily session. |
| `Low` | `Adj Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | Structural intraday price metrics representing snapshots of the same daily session. |
| `Open` | `Low` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | Structural intraday price metrics representing snapshots of the same daily session. |
| `High` | `Low` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | Structural intraday price metrics representing snapshots of the same daily session. |
| `Open` | `Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | Structural intraday price metrics representing snapshots of the same daily session. |
| `Open` | `Adj Close` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | Structural intraday price metrics representing snapshots of the same daily session. |
| `SMA_50` | `EMA_50` | 0.9999 | Structural Correlations | Near-identical representation ($|r| = 0.9999$). Drop one column during model input selection. | Moving averages of the same window length (50) tracking the same smoothed price wave. |
| `Daily_Return` | `Log_Return` | 0.9996 | Derived Feature Correlations | Daily and log returns represent near-identical information. Retain one (typically Log_Return) and drop the other. | Daily return and log return are mathematically near-identical for typical daily percentage shifts. |
| `SMA_200` | `EMA_200` | 0.9995 | Structural Correlations | Near-identical representation ($|r| = 0.9995$). Drop one column during model input selection. | Moving averages of the same window length (200) tracking the same smoothed price wave. |
| `EMA_20` | `EMA_50` | 0.9995 | Structural Correlations | Near-identical representation ($|r| = 0.9995$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_20` | `BB_Upper` | 0.9994 | Indicator Correlations | Near-identical representation ($|r| = 0.9994$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `BB_Middle` | `BB_Upper` | 0.9994 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `EMA_20` | `BB_Upper` | 0.9994 | Indicator Correlations | Near-identical representation ($|r| = 0.9994$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `EMA_50` | `BB_Middle` | 0.9994 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `SMA_20` | `EMA_50` | 0.9994 | Structural Correlations | Near-identical representation ($|r| = 0.9994$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `BB_Middle` | `BB_Lower` | 0.9994 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `SMA_20` | `BB_Lower` | 0.9994 | Indicator Correlations | Near-identical representation ($|r| = 0.9994$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `High` | `EMA_20` | 0.9994 | Structural Correlations | Near-identical representation ($|r| = 0.9994$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `EMA_20` | `BB_Lower` | 0.9993 | Indicator Correlations | Near-identical representation ($|r| = 0.9993$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Open` | `EMA_20` | 0.9993 | Structural Correlations | Near-identical representation ($|r| = 0.9993$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `EMA_50` | `BB_Upper` | 0.9992 | Indicator Correlations | Near-identical representation ($|r| = 0.9992$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Close` | `EMA_20` | 0.9992 | Structural Correlations | Near-identical representation ($|r| = 0.9992$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Adj Close` | `EMA_20` | 0.9992 | Structural Correlations | Near-identical representation ($|r| = 0.9992$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Low` | `EMA_20` | 0.9992 | Structural Correlations | Near-identical representation ($|r| = 0.9992$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `High` | `BB_Middle` | 0.9991 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `High` | `SMA_20` | 0.9991 | Structural Correlations | Near-identical representation ($|r| = 0.9991$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_50` | `EMA_20` | 0.9990 | Structural Correlations | Near-identical representation ($|r| = 0.9990$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Open` | `SMA_20` | 0.9990 | Structural Correlations | Near-identical representation ($|r| = 0.9990$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Open` | `BB_Middle` | 0.9990 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `SMA_50` | `BB_Middle` | 0.9990 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `SMA_20` | `SMA_50` | 0.9990 | Structural Correlations | Near-identical representation ($|r| = 0.9990$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Close` | `SMA_20` | 0.9989 | Structural Correlations | Near-identical representation ($|r| = 0.9989$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Adj Close` | `SMA_20` | 0.9989 | Structural Correlations | Near-identical representation ($|r| = 0.9989$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Close` | `BB_Middle` | 0.9989 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `Adj Close` | `BB_Middle` | 0.9989 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `SMA_50` | `BB_Upper` | 0.9989 | Indicator Correlations | Near-identical representation ($|r| = 0.9989$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Low` | `SMA_20` | 0.9989 | Structural Correlations | Near-identical representation ($|r| = 0.9989$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Low` | `BB_Middle` | 0.9989 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `Open` | `BB_Lower` | 0.9986 | Indicator Correlations | Near-identical representation ($|r| = 0.9986$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `High` | `BB_Lower` | 0.9986 | Indicator Correlations | Near-identical representation ($|r| = 0.9986$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Low` | `BB_Lower` | 0.9985 | Indicator Correlations | Near-identical representation ($|r| = 0.9985$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Adj Close` | `BB_Lower` | 0.9985 | Indicator Correlations | Near-identical representation ($|r| = 0.9985$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Close` | `BB_Lower` | 0.9985 | Indicator Correlations | Near-identical representation ($|r| = 0.9985$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `High` | `BB_Upper` | 0.9984 | Indicator Correlations | Near-identical representation ($|r| = 0.9984$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `EMA_50` | `BB_Lower` | 0.9983 | Indicator Correlations | Near-identical representation ($|r| = 0.9983$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Open` | `BB_Upper` | 0.9982 | Indicator Correlations | Near-identical representation ($|r| = 0.9982$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `High` | `EMA_50` | 0.9982 | Structural Correlations | Near-identical representation ($|r| = 0.9982$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Close` | `BB_Upper` | 0.9982 | Indicator Correlations | Near-identical representation ($|r| = 0.9982$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Adj Close` | `BB_Upper` | 0.9982 | Indicator Correlations | Near-identical representation ($|r| = 0.9982$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Open` | `EMA_50` | 0.9980 | Structural Correlations | Near-identical representation ($|r| = 0.9980$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Low` | `BB_Upper` | 0.9980 | Indicator Correlations | Near-identical representation ($|r| = 0.9980$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Adj Close` | `EMA_50` | 0.9980 | Structural Correlations | Near-identical representation ($|r| = 0.9980$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Close` | `EMA_50` | 0.9980 | Structural Correlations | Near-identical representation ($|r| = 0.9980$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Low` | `EMA_50` | 0.9978 | Structural Correlations | Near-identical representation ($|r| = 0.9978$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_50` | `BB_Lower` | 0.9978 | Indicator Correlations | Near-identical representation ($|r| = 0.9978$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `BB_Upper` | `BB_Lower` | 0.9976 | Indicator Correlations | Near-identical representation ($|r| = 0.9976$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `High` | `SMA_50` | 0.9974 | Structural Correlations | Near-identical representation ($|r| = 0.9974$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Open` | `SMA_50` | 0.9973 | Structural Correlations | Near-identical representation ($|r| = 0.9973$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Adj Close` | `SMA_50` | 0.9972 | Structural Correlations | Near-identical representation ($|r| = 0.9972$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Close` | `SMA_50` | 0.9972 | Structural Correlations | Near-identical representation ($|r| = 0.9972$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `EMA_50` | `EMA_200` | 0.9972 | Structural Correlations | Near-identical representation ($|r| = 0.9972$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Low` | `SMA_50` | 0.9971 | Structural Correlations | Near-identical representation ($|r| = 0.9971$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_50` | `EMA_200` | 0.9969 | Structural Correlations | Near-identical representation ($|r| = 0.9969$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `EMA_200` | `BB_Upper` | 0.9954 | Indicator Correlations | Near-identical representation ($|r| = 0.9954$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `EMA_20` | `EMA_200` | 0.9951 | Structural Correlations | Near-identical representation ($|r| = 0.9951$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_20` | `EMA_200` | 0.9949 | Structural Correlations | Near-identical representation ($|r| = 0.9949$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `EMA_200` | `BB_Middle` | 0.9949 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `SMA_200` | `EMA_50` | 0.9948 | Structural Correlations | Near-identical representation ($|r| = 0.9948$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_50` | `SMA_200` | 0.9945 | Structural Correlations | Near-identical representation ($|r| = 0.9945$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `High` | `EMA_200` | 0.9934 | Structural Correlations | Near-identical representation ($|r| = 0.9934$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Open` | `EMA_200` | 0.9932 | Structural Correlations | Near-identical representation ($|r| = 0.9932$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `EMA_200` | `BB_Lower` | 0.9931 | Indicator Correlations | Near-identical representation ($|r| = 0.9931$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Close` | `EMA_200` | 0.9931 | Structural Correlations | Near-identical representation ($|r| = 0.9931$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Adj Close` | `EMA_200` | 0.9931 | Structural Correlations | Near-identical representation ($|r| = 0.9931$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Low` | `EMA_200` | 0.9930 | Structural Correlations | Near-identical representation ($|r| = 0.9930$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_200` | `BB_Upper` | 0.9928 | Indicator Correlations | Near-identical representation ($|r| = 0.9928$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_200` | `EMA_20` | 0.9922 | Structural Correlations | Near-identical representation ($|r| = 0.9922$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_20` | `SMA_200` | 0.9919 | Structural Correlations | Near-identical representation ($|r| = 0.9919$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `SMA_200` | `BB_Middle` | 0.9919 | Indicator Correlations | BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity. | Standard correlation expected between lagging price indicators. |
| `High` | `SMA_200` | 0.9904 | Structural Correlations | Near-identical representation ($|r| = 0.9904$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Open` | `SMA_200` | 0.9901 | Structural Correlations | Near-identical representation ($|r| = 0.9901$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Close` | `SMA_200` | 0.9901 | Structural Correlations | Near-identical representation ($|r| = 0.9901$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Adj Close` | `SMA_200` | 0.9901 | Structural Correlations | Near-identical representation ($|r| = 0.9901$). Drop one column during model input selection. | Standard correlation expected between lagging price indicators. |
| `Low` | `SMA_200` | 0.9899 | Structural Correlations | These indicators share strong correlation. Evaluate model performance with and without to reduce collinearity. | Standard correlation expected between lagging price indicators. |
| `SMA_200` | `BB_Lower` | 0.9899 | Indicator Correlations | These indicators share strong correlation. Evaluate model performance with and without to reduce collinearity. | Standard correlation expected between lagging price indicators. |
| `MACD` | `MACD_Signal` | 0.9540 | Structural Correlations | MACD and its signal line are highly correlated trend followers. Review if MACD_Hist alone is sufficient. | MACD Signal is computed as a smoothed exponential moving average of MACD. |

## 4. Redundant Feature Groupings
Below are groups of features clustered together via connected components where every connection has an absolute Pearson correlation $\ge 0.9$. Sparing one variable per group is advised during model feature selection:

**Group 1**: [`Adj Close`, `BB_Lower`, `BB_Middle`, `BB_Upper`, `Close`, `EMA_20`, `EMA_200`, `EMA_50`, `High`, `Low`, `Open`, `SMA_20`, `SMA_200`, `SMA_50`]
**Group 2**: [`MACD`, `MACD_Signal`]
**Group 3**: [`Daily_Return`, `Log_Return`]

### Feature Action Recommendations (KEEP / REVIEW / REMOVE CANDIDATE)
#### KEEP
- **`Volume`**: Low correlation with price trend cluster ($|r|_{max} = 0.5405$). Offers a distinct, independent signal.
- **`RSI_14`**: Oscillator capturing overbought/oversold momentum ($|r|_{max} = 0.7437$), distinct from trend.
- **`MACD_Hist`**: Measures divergence between MACD and Signal ($|r|_{max} = 0.5572$), capturing momentum shifts.
- **`ATR_14`**: Volatility measure capturing range fluctuations ($|r|_{max} = 0.7648$), distinct from trend direction.

#### REVIEW
- **`MACD`**: MACD trend line closely tracks `MACD_Signal` ($|r| = 0.9540$). Evaluate collinearity impact.
- **`MACD_Signal`**: MACD trend line closely tracks `MACD` ($|r| = 0.9540$). Evaluate collinearity impact.

#### REMOVE CANDIDATE
- **`Open`**: Extremely high correlation ($|r| = 0.999952$) with `High`. Redundant input.
- **`High`**: Extremely high correlation ($|r| = 0.999952$) with `Open`. Redundant input.
- **`Low`**: Extremely high correlation ($|r| = 0.999944$) with `Close`. Redundant input.
- **`Close`**: Extremely high correlation ($|r| = 1.000000$) with `Adj Close`. Redundant input.
- **`Adj Close`**: Identical to `Close` by construction (no dividend adjustments for this index).
- **`SMA_20`**: Extremely high correlation ($|r| = 1.000000$) with `BB_Middle`. Redundant input.
- **`SMA_50`**: Extremely high correlation ($|r| = 0.999858$) with `EMA_50`. Redundant input.
- **`SMA_200`**: Extremely high correlation ($|r| = 0.999466$) with `EMA_200`. Redundant input.
- **`EMA_20`**: Extremely high correlation ($|r| = 0.999945$) with `SMA_20`. Redundant input.
- **`EMA_50`**: Extremely high correlation ($|r| = 0.999858$) with `SMA_50`. Redundant input.
- **`EMA_200`**: Extremely high correlation ($|r| = 0.999466$) with `SMA_200`. Redundant input.
- **`BB_Middle`**: Identical to `SMA_20` by configuration design.
- **`BB_Upper`**: Extremely high correlation ($|r| = 0.999434$) with `SMA_20`. Redundant input.
- **`BB_Lower`**: Extremely high correlation ($|r| = 0.999384$) with `SMA_20`. Redundant input.
- **`Daily_Return`**: Extremely high correlation ($|r| = 0.999638$) with `Log_Return`. Redundant input.
- **`Log_Return`**: Nearly identical to `Daily_Return` for small daily price movements. Retain only one return metric.

### Feature Groups with Internal Redundancy Summary
| Group Name | Members | Redundancy Summary |
| :--- | :--- | :--- |
| **Price Features** | `Open`, `High`, `Low`, `Close`, `Adj Close` | Internal absolute correlation range is extremely high (0.9999 to 1.0000). Price snapshots from the same trading session are structurally near-identical. |
| **Trend Indicators** | `SMA_20`, `SMA_50`, `SMA_200`, `EMA_20`, `EMA_50`, `EMA_200`, `BB_Middle` | Internal absolute correlation range is high (0.9919 to 1.0000). Trend trackers closely follow the underlying price series and show massive redundancy. |
| **Momentum** | `RSI_14`, `MACD`, `MACD_Signal`, `MACD_Hist` | Internal absolute correlation range is low-to-moderate (0.0402 to 0.9540). RSI and MACD_Hist exhibit independence, indicating lower internal redundancy. |
| **Volatility** | `ATR_14`, `BB_Upper`, `BB_Lower` | Bollinger Bands correlate heavily with price levels ($r \approx 0.99$), but ATR_14 is distinct ($r \approx 0.35$). Internal correlation range: 0.6925 to 0.9976. |
| **Returns** | `Daily_Return`, `Log_Return` | Internal absolute correlation is near-perfect (0.9996 to 0.9996). Daily return and log return are mathematically redundant. |
| **Volume** | `Volume` | Contains 1 feature (`Volume`). Volume is independent of price/trend clusters ($r \approx 0.50$ under Spearman, $r \approx 0.08$ under Pearson), acting as an independent source of information. |

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

## 6. Pearson vs. Spearman Disagreement (Non-linear Monotonic Patterns)
The following indicator pairs show significant difference between Pearson and Spearman coefficients. This indicates that while the relationship is monotonic, it is highly non-linear:

| Feature A | Feature B | Pearson | Spearman | Difference |
| :--- | :--- | :--- | :--- | :--- |
| `Volume` | `SMA_200` | 0.4965 | 0.8012 | -0.3047 |
| `Volume` | `EMA_200` | 0.5203 | 0.8199 | -0.2995 |
| `Volume` | `SMA_50` | 0.5104 | 0.8021 | -0.2917 |
| `Volume` | `EMA_50` | 0.5162 | 0.8075 | -0.2913 |
| `Volume` | `SMA_20` | 0.5135 | 0.8025 | -0.2890 |
| `Volume` | `BB_Middle` | 0.5135 | 0.8025 | -0.2890 |
| `Volume` | `BB_Lower` | 0.5056 | 0.7946 | -0.2890 |
| `Volume` | `EMA_20` | 0.5156 | 0.8045 | -0.2889 |
| `Low` | `Volume` | 0.5128 | 0.7998 | -0.2869 |
| `Close` | `Volume` | 0.5144 | 0.8011 | -0.2868 |
| `Adj Close` | `Volume` | 0.5144 | 0.8011 | -0.2868 |
| `High` | `Volume` | 0.5159 | 0.8024 | -0.2865 |
| `Open` | `Volume` | 0.5149 | 0.8013 | -0.2863 |
| `Volume` | `BB_Upper` | 0.5205 | 0.8058 | -0.2853 |

## 7. Correlation Matrix Heatmaps
Heatmaps are plotted individually for inspection:
### Pearson Linear Correlation
![Pearson Heatmap](../figures/correlation_heatmap_pearson.png)

> [!NOTE]
> **Pearson Heatmap Narrative Summary:**
> The Pearson heatmap reveals a massive block of near-perfect linear correlation ($r \ge 0.99$) among raw price features and trend-following moving averages (SMAs, EMAs, BB_Middle). This price-level cluster dominates the linear variance. In contrast, returns and momentum indicators (RSI_14, MACD_Hist) show extremely weak linear correlation with price levels, suggesting they provide orthogonal, non-redundant feature dimensions. Volatility (ATR_14) shows moderate linear correlation with the price trend cluster, indicating volatility levels scale slowly with absolute index price heights.

### Spearman Monotonic Correlation
![Spearman Heatmap](../figures/correlation_heatmap_spearman.png)

> [!NOTE]
> **Spearman Heatmap Narrative Summary:**
> The Spearman rank-based heatmap shows similar high correlation within the trend-following moving average and price cluster. However, the correlation between Volume and price indicators increases significantly under Spearman ($r \approx 0.80$) compared to Pearson ($r \approx 0.50$). This indicates that while volume has a strong, monotonic relationship with the long-term price trend (volume expands as the index grows), this expansion is highly non-linear. Momentum oscillators (RSI_14, MACD_Hist) remain largely independent of the trend indicators, confirming their value as distinct features.

## 8. Future Predictive Correlation Roadmap (Documentation Only)
This section outlines the deferred analysis roadmap for future pipeline stages:

1. **Feature-to-Feature vs. Feature-to-Label**: The analysis in this report focuses on feature-to-feature correlation to identify redundancy and multicollinearity. Predictive correlation measures the relationship between a feature *today* and the target label *in the future* (e.g., forecasting next-day returns or direction).
2. **Planned Predictive Metrics**: Once labels are engineered, we will measure predictive mappings:
   - Today's `RSI_14` $\to$ Tomorrow's `Daily_Return`
   - Today's `ATR_14` $\to$ Next-day rolling volatility
   - Today's `MACD_Hist` $\to$ Future price crossover outcomes
   - Engineered feature vectors $\to$ BUY / HOLD / SELL targets
3. **Phase Discipline deferral**: This analysis is explicitly deferred until after **Step 8 (Label Engineering)**. Performing predictive correlation now would violate the project's separation between exploratory data analysis (EDA) and supervised label modeling, leading to premature assumptions about feature predictive power before labels are formally defined.