# Statistical summary report for: `nsei_clean`
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

## 2. Interpretive Data Observations
### Skewness Warnings
The following columns exhibit high skewness (absolute value > 1.0):
- `Volume` (Skewness: 1.3924)

### Heavy-Tail Warnings (Excess Kurtosis)
The following columns exhibit fat-tailed distributions (excess kurtosis > 3.0):
- `Volume` (Excess Kurtosis: 3.6323)

### Zero Variance Flags
No zero-variance columns were detected. (Data values fluctuate normally).

## 3. Variable Sample Sizes (N)
All numeric columns are computed over the full sample size of **4613** records.