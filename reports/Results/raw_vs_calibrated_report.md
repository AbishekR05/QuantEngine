# QuantEngine: Baseline Models - Raw vs. Calibrated Macro F1 Report

**Generated on:** 2026-07-25 12:31:35
**Walk-Forward Run ID:** fs_v1_threeclass_embargo0

This report presents the fold-by-fold classification comparison before (Raw) and after (Calibrated) probability calibration for each baseline model.

---
## Logistic Regression

| Fold | Raw Macro F1 | Calibrated Macro F1 | Difference | Status |
| :--- | :--- | :--- | :--- | :--- |
| Fold 1 | 0.3291 | 0.2834 | -0.0457 | **PASS** |
| Fold 2 | 0.3252 | 0.3080 | -0.0172 | **PASS** |
| Fold 3 | 0.3381 | 0.3871 | +0.0489 | **PASS** |
| Fold 4 | 0.2963 | 0.3079 | +0.0116 | **PASS** |
| Fold 5 | 0.3068 | 0.2474 | -0.0593 | FAIL |
| Fold 6 | 0.3852 | 0.2950 | -0.0903 | **PASS** |
| Fold 7 | 0.3900 | 0.3140 | -0.0760 | **PASS** |
| Fold 8 (Partial) | 0.3460 | 0.3384 | -0.0076 | **PASS** |
| **Average (Full Years)** | **0.3387** | **0.3061** | **-0.0326** | - |

**Viability Summary:** PASSED (Passed folds: 7/8 vs. 5 required)

**Stability Indicator:** Stable (Max deviation: 0.0810 vs. 0.1000 allowed)

---
## Decision Tree

| Fold | Raw Macro F1 | Calibrated Macro F1 | Difference | Status |
| :--- | :--- | :--- | :--- | :--- |
| Fold 1 | 0.2786 | 0.2154 | -0.0632 | FAIL |
| Fold 2 | 0.2911 | 0.1662 | -0.1249 | FAIL |
| Fold 3 | 0.2466 | 0.2009 | -0.0456 | FAIL |
| Fold 4 | 0.3932 | 0.1916 | -0.2016 | FAIL |
| Fold 5 | 0.3046 | 0.2468 | -0.0578 | FAIL |
| Fold 6 | 0.3460 | 0.2339 | -0.1120 | FAIL |
| Fold 7 | 0.4007 | 0.2453 | -0.1554 | FAIL |
| Fold 8 (Partial) | 0.4135 | 0.1932 | -0.2203 | FAIL |
| **Average (Full Years)** | **0.3230** | **0.2143** | **-0.1087** | - |

**Viability Summary:** FAILED (Passed folds: 0/8 vs. 5 required)

**Stability Indicator:** Stable (Max deviation: 0.0481 vs. 0.1000 allowed)

---
## Random Forest

| Fold | Raw Macro F1 | Calibrated Macro F1 | Difference | Status |
| :--- | :--- | :--- | :--- | :--- |
| Fold 1 | 0.2589 | 0.2154 | -0.0435 | FAIL |
| Fold 2 | 0.3166 | 0.1662 | -0.1505 | FAIL |
| Fold 3 | 0.2401 | 0.2009 | -0.0391 | FAIL |
| Fold 4 | 0.3494 | 0.2003 | -0.1492 | FAIL |
| Fold 5 | 0.3485 | 0.2468 | -0.1017 | FAIL |
| Fold 6 | 0.2425 | 0.2339 | -0.0086 | FAIL |
| Fold 7 | 0.3294 | 0.2453 | -0.0841 | FAIL |
| Fold 8 (Partial) | 0.3085 | 0.1932 | -0.1153 | FAIL |
| **Average (Full Years)** | **0.2979** | **0.2155** | **-0.0824** | - |

**Viability Summary:** FAILED (Passed folds: 0/8 vs. 5 required)

**Stability Indicator:** Stable (Max deviation: 0.0494 vs. 0.1000 allowed)

---
## XGBoost

| Fold | Raw Macro F1 | Calibrated Macro F1 | Difference | Status |
| :--- | :--- | :--- | :--- | :--- |
| Fold 1 | 0.2129 | 0.3526 | +0.1397 | **PASS** |
| Fold 2 | 0.3195 | 0.2257 | -0.0938 | **PASS** |
| Fold 3 | 0.3616 | 0.2482 | -0.1134 | FAIL |
| Fold 4 | 0.3115 | 0.2310 | -0.0805 | FAIL |
| Fold 5 | 0.2741 | 0.1919 | -0.0823 | FAIL |
| Fold 6 | 0.2893 | 0.2260 | -0.0633 | FAIL |
| Fold 7 | 0.3741 | 0.1842 | -0.1898 | FAIL |
| Fold 8 (Partial) | 0.2889 | 0.3103 | +0.0214 | **PASS** |
| **Average (Full Years)** | **0.3062** | **0.2371** | **-0.0691** | - |

**Viability Summary:** FAILED (Passed folds: 3/8 vs. 5 required)

**Stability Indicator:** Unstable (Max deviation: 0.1155 vs. 0.1000 allowed)

---
## LightGBM

| Fold | Raw Macro F1 | Calibrated Macro F1 | Difference | Status |
| :--- | :--- | :--- | :--- | :--- |
| Fold 1 | 0.2375 | 0.2154 | -0.0221 | FAIL |
| Fold 2 | 0.2975 | 0.1662 | -0.1313 | FAIL |
| Fold 3 | 0.3831 | 0.2009 | -0.1821 | FAIL |
| Fold 4 | 0.3712 | 0.1916 | -0.1797 | FAIL |
| Fold 5 | 0.3167 | 0.2498 | -0.0669 | FAIL |
| Fold 6 | 0.3104 | 0.2339 | -0.0765 | FAIL |
| Fold 7 | 0.3660 | 0.2453 | -0.1207 | FAIL |
| Fold 8 (Partial) | 0.2903 | 0.1932 | -0.0971 | FAIL |
| **Average (Full Years)** | **0.3261** | **0.2147** | **-0.1113** | - |

**Viability Summary:** FAILED (Passed folds: 0/8 vs. 5 required)

**Stability Indicator:** Stable (Max deviation: 0.0486 vs. 0.1000 allowed)
