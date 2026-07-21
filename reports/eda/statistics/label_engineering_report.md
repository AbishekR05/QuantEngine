# QuantEngine: Label Engineering Report
**Report Generated At**: 2026-07-22 00:06:55
**Source Dataset**: `nifty_features`
**Configuration Threshold**: Three-Class Return Boundary = ±0.50%

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
