Module: Label Engineering

Status: Ready for implementation
Depends on: Step 1 (analyzer.py), Step 6 (regime_analysis.py — regime labels can be cross-referenced for sanity-checking label distributions, not required), Step 7 (feature_usefulness.py — this step is what finally unlocks the "Future Predictive Correlation Roadmap" documented back in the Step 4 addendum)
Consumes: nifty_features.csv
Produces: data/labels/nifty_labels_v1_binary.csv, data/labels/nifty_labels_v2_threeclass.csv, plus a design document for the future v3 (no CSV output for v3 — see Section 4)

This document is a specification, not code. Hand it to your code-generation tool as-is.

Reminder from the original Phase 2 spec: "Do NOT train any model. Design multiple possible target labels. Generate three candidate datasets." This step produces label columns appended to (or joined with) the existing feature data — it does not train, split, or evaluate anything.

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
   ├── feature_usefulness.py (already exists — Step 7)
   └── label_engineering.py ← implement in this step

data/
└── labels/ ← new directory for label datasets 2. Module Responsibility

label_engineering.py defines a LabelEngineer class that computes forward-looking target labels from nifty_features.csv and writes them as new dataset versions. This module does not:

Train any model
Split data into train/test
Evaluate any label's predictive quality (that's Phase 3's job)
Modify any existing feature column — labels are additive, appended alongside features, never replacing them

Critical structural note — this is the one module in the entire EDA phase that deliberately introduces forward-looking information. Every other module (Steps 1–7) was built specifically to avoid lookahead. Labels are, by definition, about the future relative to the feature row they're attached to — that's the whole point of a label. This is fine and expected here, but it means this dataset must never be used as an input feature set without dropping the label columns first. This should be stated explicitly and prominently in the module's output.

3. Label Dataset Versions
   Version A — Binary Classification
   Label = 1 if Close*(t+1) > Close_t
   Label = 0 otherwise (including Close*(t+1) == Close*t)
   Column name: Label_Binary
   The last row of the dataset will have no t+1 to compare against — must be NaN/null, not silently dropped or filled with a guessed value. Document this in the output file (e.g. a trailing comment row or a companion note in the report).
   State explicitly: this label treats a flat day (Close*(t+1) == Close*t) as class 0, same as a down day. Worth flagging as a modeling choice, not an oversight — with only ~4,600 daily rows, exact ties are rare but not impossible, and a future reader should know how they were handled.
   Version B — Three-Class Classification (BUY / HOLD / SELL)
   Return*(t+1) = (Close\_(t+1) - Close_t) / Close_t

BUY if Return*(t+1) > +threshold
SELL if Return*(t+1) < -threshold
HOLD otherwise
Column name: Label_ThreeClass
threshold must be config-driven, not hardcoded (e.g. default 0.5% per the original spec's example) — this is a value future experimentation will almost certainly want to tune.
Report the resulting class balance (count and % of BUY/HOLD/SELL) as part of this step's output — with a small threshold like 0.5% on daily NIFTY returns, class balance could be heavily skewed toward HOLD, and that imbalance is something Phase 3 needs to know about upfront, not discover later.
Version C — Future Trading Labels (Design Only — No Data Output)

Per the original Phase 2 spec: "Design a placeholder structure... No implementation yet. Only define how this label could be generated once historical option-chain data becomes available."

This is a documentation deliverable, not a CSV. Produce a design note (can live in the same report as A/B, or a separate short markdown file) covering:

What data would be required (option chain: strikes, premiums, implied volatility, expiry dates) that doesn't exist yet in this project
A proposed label logic sketch, e.g.: "BUY CALL if next-day return exceeds a threshold AND an at-the-money call option would have been profitable net of premium decay; BUY PUT under the symmetric condition; HOLD otherwise" — explicitly caveated as a sketch, not a finalized rule
Why this can't be implemented now (no option-chain data source has been built in this project yet — that's a data pipeline gap, not an EDA gap)
What would need to happen first (a new data source/pipeline for option chain data — likely its own future phase or Phase 1 extension, not something to shoehorn into the current feature file) 4. Class Design
LabelEngineer

Constructor inputs:

data: pd.DataFrame — nifty_features.csv
close_column: str = "Close"
three_class_threshold: float — from config

Public methods:

Method Returns Purpose
generate_binary_label() -> pd.Series Series aligned to input rows Version A
generate_three_class_label() -> pd.Series Series Version B
label_distribution(label_column: str) -> pd.DataFrame counts + percentages Class balance report for either label
save_labeled_dataset(version: str, output_path: str) -> None None Writes features + label column(s) to a new versioned CSV (does not overwrite nifty_features.csv)
to_markdown() -> str str Full report, including the Version C design note
generate_label_datasets(config: dict) -> None

Module-level orchestrator: loads nifty_features.csv, computes both label versions, saves each as its own file, generates the report.

5. Report Content Requirements
   Header — dataset name, timestamp, config values used (three_class_threshold, etc.)
   Version A summary — binary label distribution (count/% of 1s and 0s), explicit note on the last-row NaN and the flat-day-as-0 convention
   Version B summary — three-class distribution, explicit class imbalance callout if any class is heavily over/under-represented
   Version C design note — the sketch described in Section 3, clearly marked as design-only, no data produced
   Lookahead warning (prominent, near the top, not buried at the end): "These label columns are intentionally forward-looking (each label at row t depends on Close at row t+1). This is expected and correct for label data, but these files must never be used as a feature-only input set — always exclude label columns when using this data for anything other than supervised learning targets."
   Cross-reference to Step 6 regimes (optional but valuable): note whether the three-class label's BUY/SELL rates differ meaningfully across Bull/Bear/Sideways regime periods — this is a legitimate descriptive observation (not a predictive claim) and gives an early sanity check that the labels behave sensibly (e.g. BUY should be more frequent during Bull-classified periods)
6. Config Integration
   yaml
   eda:
   label_engineering:
   input_file: "data/features/nifty_features.csv"
   close_column: "Close"
   three_class_threshold: 0.005
   output_dir: "data/labels/"
   binary_output_filename: "nifty_labels_v1_binary.csv"
   three_class_output_filename: "nifty_labels_v2_threeclass.csv"
   report_output_path: "reports/eda/statistics/label_engineering_report.md"
7. Edge Cases
   Last row of the dataset — no t+1 exists; label must be NaN, never dropped silently or back-filled. Row count in the labeled output should match the feature file exactly (same N, last row's label is null).
   Exact-tie returns (Return*(t+1) == 0 exactly, or Close*(t+1) == Close_t exactly) — state explicitly which class they fall into for both Version A and B (Version A: class 0 per Section 3; Version B: falls into HOLD since it won't exceed either threshold).
   Threshold sensitivity — briefly note in the report that three_class_threshold is a modeling assumption, not a derived constant, and changing it will shift class balance — this connects directly to why it's config-driven rather than fixed.
   Rolling-indicator NaNs elsewhere in the row (e.g. early SMA_200 warm-up rows) — these are unrelated to the label computation and should NOT be dropped or modified by this module; the label columns are additive only, existing NaN patterns in feature columns are untouched.
8. Acceptance Criteria
   src/eda/label_engineering.py exists
   LabelEngineer implements all methods in Section 4
   Version A and B saved as separate CSV files, both including all original feature columns plus the new label column (not label-only files)
   Version C exists only as a documented design sketch — no code, no data file
   Last-row NaN handled correctly and explicitly documented
   Class balance reported for both label versions
   Prominent lookahead-bias warning present near the top of the report
   three_class_threshold is config-driven
   No modification to existing nifty_features.csv or its NaN patterns
   No model training, splitting, or evaluation anywhere in this module
   Type hints and docstrings on all public methods
