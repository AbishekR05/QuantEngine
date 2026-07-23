Module: Feature Scaling Recommendation

Status: Ready for implementation
Depends on: Step 2 (statistics.py — distribution shape/skew data), Step 7 (feature_usefulness.py — variance/CV data)
Consumes: nifty_features.csv
Produces: reports/eda/statistics/scaling_recommendation_report.md

This document is a specification, not code. Hand it to your code-generation tool as-is.

Reminder from the original Phase 2 spec: "Do NOT actually scale features. Instead generate recommendations." This step recommends; it does not transform any data.

1. Package Structure to Create
   src/
   └── eda/
   └── scaling_recommendation.py ← implement in this step (only new file)

No new data directories — this is a report-only step.

2. Module Responsibility

scaling_recommendation.py defines a ScalingAdvisor class that examines each numeric column's distribution characteristics (already computed in Steps 2 and 7) and recommends a scaling approach — or explicitly recommends no scaling — per column. This module does not:

Apply any transformation, scaling, or normalization to any column
Modify nifty_features.csv or produce any new dataset file
Make a final, binding decision — recommendations only, same discipline as Steps 4, 5, and 7 3. Recommendation Logic (config-driven thresholds, not hardcoded rules)
Scaler When typically recommended
StandardScaler (zero mean, unit variance) Roughly symmetric, moderate-tailed distributions — reasonable default for price/trend features once skew isn't extreme
MinMaxScaler (bounded 0-1) Features that are already naturally bounded (e.g. RSI_14's 0-100 range) — preserves the bounded interpretation
RobustScaler (median/IQR-based) Features with known heavy tails or outliers already documented in Step 5 (e.g. Daily_Return, Log_Return, Volume) — resistant to the extreme values we've already confirmed are real market events, not errors
No scaling recommended Columns that are already labels, dates, or where scaling would harm interpretability without a clear benefit (e.g. Volume might warrant a log-transform discussion rather than a scaler — see Section 5)

Recommendation logic should reference, not recompute:

Skewness/kurtosis from Step 2
Known outlier status from Step 5 (a column with confirmed real-event outliers points toward RobustScaler rather than StandardScaler, since StandardScaler's mean/std are outlier-sensitive)
Natural bounds (RSI 0-100) — this can be a small config-driven list of known-bounded columns rather than inferred purely from data, since "is this conceptually bounded" is domain knowledge, not a statistical property 4. Class Design
ScalingAdvisor

Constructor inputs:

data: pd.DataFrame
statistics_source — reused Step 2 output (skew/kurtosis per column)
outlier_source — reused Step 5 output (which columns have confirmed real-event outliers vs. none)
bounded_columns: list[str] — from config (e.g. ["RSI_14"])

Public methods:

Method Returns Purpose
recommend_scaler(column: str) -> dict {scaler, reason} Single-column recommendation with plain-language justification
recommend_all() -> pd.DataFrame one row per column Full table
to_markdown() -> str str Full report
save(output_path: str) -> None None Writes report to disk
generate_scaling_report(config: dict) -> None

Module-level orchestrator, same pattern as prior steps.

5. Special Case: Volume

Volume deserves its own discussion paragraph in the report rather than a single-line table entry, because it has multiple compounding characteristics already established:

~29% zero-inflation (2007–2013 known limitation)
High skew/kurtosis (per Step 7's variance ranking, CV ≈ 0.95, among the highest in the dataset)
Confirmed outliers at the high end (per Step 5)

The report should note that a log-transform is commonly used for volume-like data before scaling (e.g. log1p(Volume) to handle the zeros), but that this project has explicitly decided (Steps 1–7) never to transform Volume's zero values as if they were errors — so any log-transform recommendation must be framed as "a modeling technique to consider in Phase 3 if Volume is used as a model input," not as something this EDA phase should do now. This keeps the recommendation consistent with the project's standing "no automated modification" discipline while still giving Phase 3 useful guidance.

6. Report Content Requirements
   Header — dataset name, timestamp
   Per-column recommendation table — feature, recommended scaler, one-line reason
   Volume special discussion (Section 5)
   RSI_14 special note — already bounded 0-100 by construction; MinMaxScaler recommendation should state this is really just a formality here since RSI already lives in a known range, unlike, say, price levels which have no natural ceiling
   Explicit non-action statement: "This report provides scaling recommendations only. No column in nifty_features.csv has been scaled, transformed, or modified. Scaler selection and fitting should occur later, during model-specific pipeline construction in Phase 3, using only training-fold statistics to avoid leakage."
   Leakage note specific to scaling — worth stating plainly since it's a common real-world mistake: whatever scaler is eventually applied in Phase 3 must be fit only on training data (not the full dataset) to avoid leaking test-set distribution information into training — this is a forward-looking caution for Phase 3, not something this module does.
7. Config Integration
   yaml
   eda:
   scaling:
   bounded_columns: ["RSI_14"]
   output_report_path: "reports/eda/statistics/scaling_recommendation_report.md"
8. Edge Cases
   Structural near-duplicate columns (Close/Adj Close, etc.) — will naturally receive identical scaling recommendations since they have identical distributions; note this is expected, not a redundant computation error.
   Return columns (Daily_Return, Log_Return) — already centered near zero with heavy tails (per Step 2/7); RobustScaler is the natural fit, but note in the report that these are already "small-scale" (values near ±0.01–0.05) so the practical impact of scaling is smaller than for raw price columns in the thousands.
9. Acceptance Criteria
   src/eda/scaling_recommendation.py exists
   ScalingAdvisor implements all methods in Section 4
   Recommendations reuse Step 2/5/7 outputs rather than recomputing statistics
   Volume given its own discussion paragraph per Section 5
   RSI_14's natural-bounds context explicitly noted
   Explicit non-action statement present
   Train/test-fit leakage caution present as forward guidance for Phase 3
   No data scaling, transformation, or modification anywhere in this module
   Type hints and docstrings on all public methods
