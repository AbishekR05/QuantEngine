# QuantEngine: Feature Scaling Recommendation Report
**Report Generated At**: 2026-07-23 23:03:20
**Source Dataset**: `nifty_features`
**Configuration Bounded Columns**: ['RSI_14']

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
