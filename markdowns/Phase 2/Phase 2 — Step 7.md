Module: Feature Usefulness Analysis

Status: Ready for implementation
Depends on: Step 2 (statistics.py — variance data), Step 4 (correlations.py — reuse existing correlation output, do not recompute), Step 6 (regime_analysis.py — optional cross-reference, not required)
Consumes: nifty_features.csv
Produces: reports/eda/statistics/feature_usefulness_report.md

This document is a specification, not code. Hand it to your code-generation tool as-is.

Reminder from the original Phase 2 spec: "Without building any predictive model yet, estimate feature usefulness using methods such as Variance, Correlation, Mutual Information. Remove nothing automatically. Simply rank features." This step ranks; it does not decide.

1. Package Structure to Create
   src/
   └── eda/
   ├── **init**.py (already exists)
   ├── analyzer.py (already exists — Step 1)
   ├── statistics.py (already exists — Step 2)
   ├── visualizer.py (already exists — Step 3)
   ├── correlations.py (already exists — Step 4)
   ├── outlier_analysis.py (already exists — Step 5)
   ├── regime_analysis.py (already exists — Step 6)
   └── feature_usefulness.py ← implement in this step

reports/
└── eda/
└── statistics/ (already exists)

Only feature_usefulness.py is implemented in this step. label_analysis.py remains out of scope (Step 8 — and per the original spec, mutual information here is computed against nothing but the features themselves, NOT against future labels, since labels don't exist until Step 8).

2. Module Responsibility

feature_usefulness.py defines a FeatureUsefulnessAnalyzer class that ranks features using three independent lenses — variance, correlation-based redundancy, and mutual information — and produces a combined ranking report. This module does not:

Remove, transform, or select any features — ranking and reporting only
Compute any label-based / predictive relevance (that requires labels, which don't exist until Step 8 — this is explicitly deferred, consistent with the "Future Predictive Correlation Roadmap" already documented in the Step 4 addendum)
Recompute the correlation matrix — it reuses Step 4's CorrelationAnalyzer output directly 3. What "Mutual Information" Means Here — Important Scoping Note

Since there is no target label yet (Step 8 hasn't happened), mutual information in this step is computed between features themselves (e.g. MI(RSI_14, MACD)), not between features and a future outcome. This serves a different purpose than Step 4's correlation analysis: correlation only captures linear (Pearson) or monotonic (Spearman) relationships, while mutual information can catch nonlinear dependencies that correlation misses entirely (e.g. two features related by a U-shaped or cyclical pattern would show near-zero correlation but nonzero mutual information).

This distinction should be stated explicitly in the report — the value of adding MI here isn't redundant with Step 4, it's specifically catching what Step 4's linear/monotonic methods structurally cannot.

4. Class Design
   FeatureUsefulnessAnalyzer

Constructor inputs:

data: pd.DataFrame — nifty_features.csv
exclude_columns: list[str] — from config (at minimum Date)
correlation_report_path: str — path to Step 4's already-generated correlation data (reuse, don't recompute the matrix — see Section 6)
mi_bins: int — from config, for discretizing continuous features before MI computation (standard approach for continuous-variable MI estimation)

Public methods:

Method Returns Purpose
variance_ranking() -> pd.DataFrame one row per feature Raw variance and normalized variance (variance / mean, or coefficient of variation) per column, ranked descending
redundancy_ranking() -> pd.DataFrame DataFrame Pulled from Step 4's high-correlation/redundant-group output — which features are flagged as redundant with something else, and how many "partners" each has
mutual_information_matrix() -> pd.DataFrame N×N Pairwise MI between all numeric features
mutual_information_ranking() -> pd.DataFrame DataFrame Per feature, average/max MI with all other features — a feature highly "informationally entangled" with many others ranks differently than one that's more independent
combined_ranking() -> pd.DataFrame DataFrame Merges variance rank, redundancy flag, and MI-based independence into a single reference table — see Section 5 for what this does NOT mean
to_markdown() -> str str Full report
save(output_path: str) -> None None Writes report to disk
generate_feature_usefulness_report(config: dict) -> None

Module-level orchestrator, same pattern as prior steps.

5. Critical Framing: "Combined Ranking" Is Not a Feature-Selection Score

The combined_ranking() table must NOT present a single blended numeric "usefulness score" that implies an ordering of what to keep or drop. Three independent lenses are being reported side by side, not averaged into one number, because they measure different things and combining them arithmetically would hide why a feature ranks where it does:

A low-variance feature might still be informationally valuable (e.g. RSI_14 has a bounded 0-100 range and naturally lower variance than price levels, but that doesn't make it less useful)
A redundant feature (per Step 4) might still have unique variance/information if only mildly correlated
A feature with low average MI with everything else is "independent" — which could mean it's uniquely informative, OR could mean it's just noisy. This module cannot distinguish those two cases (that requires labels — Step 8+), and the report must say so explicitly rather than implying low-MI = good.

The report should present the three columns side-by-side per feature and let a human read the pattern, not compute a composite score. This mirrors the same discipline already established in the Step 4 addendum's KEEP/REVIEW/REMOVE CANDIDATE labels — those were explicit human-facing labels, not silent automated decisions, and this step should follow the same principle.

6. Reusing Step 4's Correlation Output (Do Not Recompute)

The redundancy ranking must be sourced from Step 4's already-generated correlation report/data structures (CorrelationAnalyzer's high_correlation_pairs(), flag_redundant_features() outputs), not by re-running Pearson/Spearman calculations independently. If Step 4's CorrelationAnalyzer doesn't currently expose a clean re-importable data object (e.g. it only writes Markdown), this is a good moment to add a lightweight method that returns the underlying DataFrame — reuse that method call directly rather than parsing the Markdown report or recalculating.

7. Report Content Requirements
   Header — dataset name, timestamp, brief statement of the three methods used and why (variance = raw signal magnitude; redundancy = linear/monotonic overlap from Step 4; MI = nonlinear dependency detection)
   Variance ranking table — all numeric features, ranked
   Redundancy ranking table — reused from Step 4, showing each feature's count of high-correlation "partners"
   Mutual information ranking table — average and max MI per feature
   Combined side-by-side table (per Section 5's framing constraint)
   Explicit non-decision statement: "This report ranks features along three independent dimensions. It does not recommend removing any feature. Feature selection decisions should be deferred until label-based (Step 8+) predictive relevance can be measured, since a feature's raw variance, redundancy with other features, or informational independence does not by itself determine whether it will be useful for predicting future market direction."
   MI vs. correlation divergence note — call out any feature pairs where MI is high but Pearson/Spearman correlation (from Step 4) was low, since this is exactly the nonlinear-relationship signal MI is uniquely suited to catch
8. Config Integration
   yaml
   eda:
   feature_usefulness:
   input_file: "data/features/nifty_features.csv"
   exclude_columns: ["Date"]
   correlation_report_source: "reports/eda/statistics/correlation_report.md"
   mi_bins: 10
   output_report_path: "reports/eda/statistics/feature_usefulness_report.md"
9. Edge Cases
   Volume's zero-inflated distribution — variance dominated by its ~29%-zeros-plus-long-tail shape. Note this in context rather than presenting raw variance in isolation.
   Rolling-indicator leading NaNs — MI computed pairwise on rows where both features have valid values; note reduced effective N where relevant.
   MI is sensitive to binning choice — state the configured mi_bins value explicitly.
   Structural near-duplicates (e.g. Close/Adj Close) will show very high MI too — flag as expected/structural, not a new finding.
10. Acceptance Criteria
    src/eda/feature_usefulness.py exists
    FeatureUsefulnessAnalyzer implements all methods in Section 4
    Redundancy ranking reuses Step 4's output rather than recomputing correlation
    Mutual information computed between features (not against any label)
    Combined ranking presents three columns side-by-side, explicitly NOT a blended composite score
    Report distinguishes what low-MI/low-variance/redundant could mean, without asserting a definitive usefulness verdict
    MI vs. correlation divergence explicitly called out
    Explicit non-decision statement present
    Known structural near-duplicates flagged as expected, not novel
    Volume's distribution quirk noted
    No features removed, transformed, or dropped anywhere
    Type hints and docstrings on all public methods
