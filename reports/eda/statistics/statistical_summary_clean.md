# Statistical summary report for: `nsei_clean`
**Report Generated At**: 2026-07-08 00:39:19

*Convention Note: Excess Kurtosis is reported below. A normal distribution corresponds to a kurtosis value of 0. Kurtosis values greater than 0 indicate a fat-tailed distribution.*

## 1. Descriptive Statistics Table
| Column Name | N | Mean | Median | Mode (first) | Modes Count | Std Dev | Variance | Min | Max | 25% | 50% | 75% | Skewness | Excess Kurtosis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Open` | 4610 | 11279.6393 | 8889.9502 | 2714.7000 | 41 | 6619.4872 | 43817611.3574 | 2553.6001 | 26333.6992 | 5715.4624 | 8889.9502 | 16480.0371 | 0.8474 | -0.5315 |
| `High` | 4610 | 11338.9494 | 8932.1001 | 3147.2000 | 41 | 6640.0623 | 44090426.7869 | 2585.3000 | 26373.1992 | 5752.7125 | 8932.1001 | 16589.0503 | 0.8495 | -0.5307 |
| `Low` | 4610 | 11205.1934 | 8818.2998 | 2611.9500 | 39 | 6593.6301 | 43475958.0923 | 2252.7500 | 26210.0508 | 5676.8876 | 8818.2998 | 16376.2373 | 0.8476 | -0.5278 |
| `Close` | 4610 | 11273.4160 | 8874.0996 | 5274.8501 | 2 | 6617.3423 | 43789218.4704 | 2524.2000 | 26328.5508 | 5712.9875 | 8874.0996 | 16493.2993 | 0.8483 | -0.5304 |
| `Adj Close` | 4610 | 11273.4160 | 8874.0996 | 5274.8501 | 2 | 6617.3423 | 43789218.4704 | 2524.2000 | 26328.5508 | 5712.9875 | 8874.0996 | 16493.2993 | 0.8483 | -0.5304 |
| `Volume` | 4610 | 217042.6898 | 193800.0000 | 0.0000 | 1 | 206636.1345 | 42698492089.0966 | 0.0000 | 1811000.0000 | 0.0000 | 193800.0000 | 304250.0000 | 1.3944 | 3.6381 |

## 2. Interpretive Data Observations
### Skewness Warnings
The following columns exhibit high skewness (absolute value > 1.0):
- `Volume` (Skewness: 1.3944)

### Heavy-Tail Warnings (Excess Kurtosis)
The following columns exhibit fat-tailed distributions (excess kurtosis > 3.0):
- `Volume` (Excess Kurtosis: 3.6381)

### Zero Variance Flags
No zero-variance columns were detected. (Data values fluctuate normally).

## 3. Variable Sample Sizes (N)
All numeric columns are computed over the full sample size of **4610** records.