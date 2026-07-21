# QuantEngine: Feature Usefulness Analysis Report
**Report Generated At**: 2026-07-21 23:47:57
**Source Dataset**: `nifty_features`
**Configuration**: Discretization Bins (MI Estimator) = 10

## 1. Explicit Non-Decision Statement
> [!IMPORTANT]
> **Standing Non-Decision and Non-Pruning Directive:**
> *This report ranks features along three independent dimensions. It does not recommend removing any feature. Feature selection decisions should be deferred until label-based (Step 8+) predictive relevance can be measured, since a feature's raw variance, redundancy with other features, or informational independence does not by itself determine whether it will be useful for predicting future market direction.*

## 2. Methodology Summary
This report analyzes the informational footprint of technical indicators and features across three independent lenses:
1. **Variance Ranking**: Measures the raw signal volatility. Standardized using the **Coefficient of Variation** ($CV = \sigma / |\mu|$) to make bounded oscillators (e.g. RSI_14) comparable to price-level features.
2. **Redundancy Count**: Reuses the Pearson correlation matrix ($|r| \ge 0.90$) generated in Step 4. Tracks the count of highly correlated partners each feature shares.
3. **Mutual Information (MI)**: Computes pairwise informational dependency (in bits) between features discretized into equal-frequency bins. Unlike correlation, MI captures nonlinear dependencies (e.g., U-shaped or cyclical patterns).

## 3. Known Data Limitations & Distribution Quirks
- **Volume Zero-Inflation**: Volume's variance is dominated by its zero-inflated shape (due to the 2007–2013 calculation limitation). Its raw variance is extremely large but does not represent a clean trading signal. Use caution if using Volume's raw variance directly.
- **RSI Boundary Artifact**: During warm-up (first 13 days of series), RSI_14 is mathematically pinned near 100.0. This boundary artifact creates high artificial information concentration at the start of Nifty.
- **Structural Near-Duplicates**: Features like `Close` and `Adj Close`, or `SMA_20` and `BB_Middle`, are mathematically near-identical by construction. These display maximum Mutual Information ($\approx 3.32$ bits for 10 bins) and high redundant partner counts as expected.

## 4. Feature Variance Rankings
Features ranked descending by their **Coefficient of Variation** (relative standard deviation):
| Rank | Feature | Raw Variance | Mean | Coefficient of Variation |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `MACD_Hist` | 1777.869938 | 0.0956 | 440.949535 |
| 2 | `Log_Return` | 0.000169 | 0.0004 | 35.802535 |
| 3 | `Daily_Return` | 0.000169 | 0.0004 | 29.029951 |
| 4 | `MACD` | 19767.149682 | 29.3904 | 4.783726 |
| 5 | `MACD_Signal` | 17539.866420 | 29.2948 | 4.520877 |
| 6 | `Volume` | 42694072085.106216 | 217165.5539 | 0.951465 |
| 7 | `BB_Lower` | 41780172.212040 | 10884.8621 | 0.593830 |
| 8 | `Low` | 43554574.990290 | 11213.5316 | 0.588538 |
| 9 | `Adj Close` | 43867402.234248 | 11281.7454 | 0.587076 |
| 10 | `Close` | 43867402.234248 | 11281.7454 | 0.587076 |
| 11 | `EMA_20` | 43549388.311121 | 11241.5978 | 0.587034 |
| 12 | `EMA_50` | 43052514.039004 | 11178.5547 | 0.586967 |
| 13 | `Open` | 43897954.579162 | 11288.0534 | 0.586953 |
| 14 | `SMA_20` | 43572988.930573 | 11268.4979 | 0.585791 |
| 15 | `BB_Middle` | 43572988.930573 | 11268.4979 | 0.585791 |
| 16 | `High` | 44171334.739960 | 11347.3927 | 0.585699 |
| 17 | `SMA_50` | 43160162.777372 | 11246.6817 | 0.584140 |
| 18 | `EMA_200` | 40102722.169880 | 10852.1328 | 0.583542 |
| 19 | `BB_Upper` | 45508682.915137 | 11652.1336 | 0.578951 |
| 20 | `SMA_200` | 40594407.797391 | 11117.7992 | 0.573079 |
| 21 | `ATR_14` | 6041.057366 | 146.8377 | 0.529321 |
| 22 | `RSI_14` | 163.472509 | 53.9634 | 0.236932 |

## 5. Linear Redundancy Rankings (Reused from Step 4)
Features ranked descending by the number of highly correlated partners ($|r| \ge 0.90$):
| Rank | Feature | Highly Correlated Partners | Redundancy Status |
| :--- | :--- | :--- | :--- |
| 1 | `Open` | 13 | Highly Redundant |
| 2 | `High` | 13 | Highly Redundant |
| 3 | `Low` | 13 | Highly Redundant |
| 4 | `Close` | 13 | Highly Redundant |
| 5 | `Adj Close` | 13 | Highly Redundant |
| 6 | `SMA_20` | 13 | Highly Redundant |
| 7 | `BB_Lower` | 13 | Highly Redundant |
| 8 | `SMA_50` | 13 | Highly Redundant |
| 9 | `SMA_200` | 13 | Highly Redundant |
| 10 | `EMA_20` | 13 | Highly Redundant |
| 11 | `EMA_50` | 13 | Highly Redundant |
| 12 | `EMA_200` | 13 | Highly Redundant |
| 13 | `BB_Middle` | 13 | Highly Redundant |
| 14 | `BB_Upper` | 13 | Highly Redundant |
| 15 | `Daily_Return` | 1 | Highly Redundant |
| 16 | `MACD` | 1 | Highly Redundant |
| 17 | `Log_Return` | 1 | Highly Redundant |
| 18 | `MACD_Signal` | 1 | Highly Redundant |
| 19 | `Volume` | 0 | Independent Profile |
| 20 | `RSI_14` | 0 | Independent Profile |
| 21 | `MACD_Hist` | 0 | Independent Profile |
| 22 | `ATR_14` | 0 | Independent Profile |

## 6. Pairwise Mutual Information Rankings
Average and maximum Mutual Information (in bits) between each feature and all other features:
| Rank | Feature | Average MI (bits) | Max MI (bits) | Informational Profile |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `EMA_20` | 1.8184 | 3.0618 | Highly Entangled |
| 2 | `SMA_20` | 1.8057 | 3.3219 | Highly Entangled |
| 3 | `BB_Middle` | 1.8057 | 3.3219 | Highly Entangled |
| 4 | `High` | 1.7973 | 3.1160 | Highly Entangled |
| 5 | `Adj Close` | 1.7905 | 3.3219 | Highly Entangled |
| 6 | `Close` | 1.7905 | 3.3219 | Highly Entangled |
| 7 | `Open` | 1.7856 | 3.1160 | Highly Entangled |
| 8 | `Low` | 1.7823 | 3.1137 | Highly Entangled |
| 9 | `EMA_50` | 1.7577 | 2.9225 | Highly Entangled |
| 10 | `BB_Upper` | 1.7323 | 2.8310 | Highly Entangled |
| 11 | `BB_Lower` | 1.7235 | 2.7876 | Highly Entangled |
| 12 | `SMA_50` | 1.7075 | 2.9225 | Highly Entangled |
| 13 | `EMA_200` | 1.5922 | 2.5786 | Highly Entangled |
| 14 | `SMA_200` | 1.5287 | 2.5786 | Highly Entangled |
| 15 | `Volume` | 0.7420 | 1.1568 | Moderately Coupled |
| 16 | `ATR_14` | 0.6403 | 0.9132 | Moderately Coupled |
| 17 | `MACD` | 0.3124 | 1.4946 | Independent Source |
| 18 | `MACD_Signal` | 0.3033 | 1.4946 | Independent Source |
| 19 | `Log_Return` | 0.2249 | 3.3219 | Independent Source |
| 20 | `Daily_Return` | 0.2249 | 3.3219 | Independent Source |
| 21 | `MACD_Hist` | 0.1510 | 0.3705 | Independent Source |
| 22 | `RSI_14` | 0.1260 | 0.7585 | Independent Source |

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
