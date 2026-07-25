# Phase 3 — Machine Learning: Roadmap & Architecture Spec

**Status:** Draft for review (v2 — architectural refinements incorporated)
**Depends on:** Phase 2 Step 8 (Label Engineering — binary + 3-class label datasets), EDA_REPORT.md (Phase 2 Step 10 final compilation)
**Consumed by:** Antigravity (code generation), once approved

---

## 1. Objective

Phase 3 builds the ML layer of the NIFTY 50 (^NSEI) trading system. The deliverable is not a price predictor — it is a **decision classifier** that outputs one of three actions per bar, along with **calibrated confidence in that decision**:

- `CALL` — directional long signal
- `PUT` — directional short signal
- `NO_TRADE` — insufficient confidence / low-volatility / sideways conditions

This aligns the ML output directly with the trading system's action space, rather than requiring a downstream translation layer from a continuous prediction to a trade decision. Critically, the model's output is **not just a hard label** — the full class-probability distribution is preserved end-to-end so the trading engine can apply its own confidence thresholds and, later, confidence-based position sizing, rather than the ML layer forcing a binary "trade / don't trade" decision on every bar.

---

## 2. Pipeline Architecture: Feature Store as an Intermediate Stage

The pipeline is restructured to decouple feature engineering from labeling and model-specific preprocessing:

```
Raw Data
    down
Feature Engineering
    down
Feature Store  (all engineered features, pre-label, pre-scaling, pre-split)
    down
Training Dataset  (features + chosen label version + fold-specific scaling)
    down
Model Training
```

- The **Feature Store** holds engineered features only — no labels, no scaling, no train/test split applied. This is the reusable, canonical dataset.
- Different label versions (fixed +/-0.50% Version B, and the future ATR-relative addendum) and different preprocessing strategies (scaler choice, log1p(Volume)) are applied **downstream** of the Feature Store, as separate "Training Dataset" builds.
- Practical effect: comparing Version B vs. ATR-relative labels later (Section 3's deferred decision) does not require recomputing feature engineering — only a new labeling + preprocessing pass over the same Feature Store.
- This becomes a concrete deliverable in Step 2 (Feature Store schema/storage spec) rather than an abstract diagram — exact storage format (e.g. parquet/versioned CSV) and versioning scheme are defined there.

---

## 3. Label Strategy (confirmed against actual Phase 2 Step 8 / EDA_REPORT.md output)

- **Target:** 3-class label, implemented as `Label_ThreeClass` = `{BUY, HOLD, SELL}` (mapping conceptually to `CALL / NO_TRADE / PUT` in trading-system terms).
- **Actual construction (Version B, as built):**
  - Horizon: next-bar (t+1) forward return, R_(t+1) = (Close_(t+1) - Close_t) / Close_t.
  - Threshold: **fixed +/-0.50%** -- BUY if R_(t+1) > +0.50%, SELL if R_(t+1) < -0.50%, HOLD otherwise.
  - Last row: NaN (no future bar to compare against) -- excluded from training/eval, not imputed.
  - Class distribution is healthy, not degenerate: HOLD 43.76% / BUY 30.31% / SELL 25.93%.
- **Design note (resolved for Phase 3 kickoff):** the fixed threshold is regime-agnostic -- a 0.50% move means something different in a High-volatility regime (~2.15% avg daily vol) than a Low-volatility one (~0.59%). This is a real design tension against the "keep the model out of low-conviction/sideways markets" goal, but it is **not being resolved before Phase 3 starts**:
  - **Phase 3 baseline (Steps 4 onward) uses the existing Version B labels as-is** -- already built and validated, no reason to block kickoff on relabeling.
  - **An ATR-relative label version is planned as an addendum**, to be built and compared against baseline results once Step 4 establishes a performance floor. This decision is revisited at the Step 4-to-5 gate, not before. The Feature Store architecture (Section 2) means this comparison is cheap to run when the time comes.
- Version C (option-chain-based labels) remains deferred and out of scope for Phase 3 -- data pipeline for derivatives does not yet exist.

---

## 4. Validation Strategy: Walk-Forward (Rolling-Origin), with Configurable Purge/Embargo

Random splits and K-Fold CV are explicitly excluded -- both leak future information into training for time-series data.

**Adopted scheme:**

Dataset spans 2007-09-17 to 2026-07-09 (confirmed via EDA_REPORT.md), but 2007-2013 is excluded from training due to the documented Volume zero-inflation limitation (~29% zero values, known data-feed artifact, not a real signal). Anchored start is therefore **2014**, not the full dataset range.

| Fold | Train Window | Test Window |
|------|-------------|-------------|
| 1 | 2014-2018 | 2019 |
| 2 | 2014-2019 | 2020 |
| 3 | 2014-2020 | 2021 |
| 4 | 2014-2021 | 2022 |
| 5 | 2014-2022 | 2023 |
| 6 | 2014-2023 | 2024 |
| 7 | 2014-2024 | 2025 |
| 8 | 2014-2025 | 2026 (partial year -- data through 2026-07-09) |

- Train window **expands** (anchored start at 2014), test window rolls forward one year at a time. This matches how the model would actually be retrained and redeployed in production.
- 2007-2013 exclusion is a Phase 3 default, not a permanent decision -- reclaiming that period (e.g. with Volume masked/excluded for that subrange only) is a candidate future addendum, not in scope now.
- Fold 8's test window is a partial year; this is flagged explicitly in evaluation reporting rather than silently averaged with full-year folds.
- Fold boundaries, expanding-vs-rolling window choice, and window length are config-driven parameters, not hardcoded -- so this can later be adjusted to a fixed-length rolling window without a spec rewrite.
- Each fold's test-set performance is reported individually, not just averaged, so degradation in specific regimes (e.g., 2020 COVID year) is visible rather than masked.
- **Purge/embargo gap (new, configurable, default off):** the splitter interface supports an optional gap inserted between the end of each training window and the start of its test window (e.g. embargo_days: int, default 0). Current t+1 labels don't need this -- there's no overlap between a training-window label's forward return and the test window. It's built into the splitter now so that a longer prediction horizon or overlapping-label scheme introduced later doesn't require redesigning the validation harness, only setting a non-zero config value.

---

## 5. Model Progression

Per project discipline (baseline before complexity), Phase 3 is split into two implementation steps:

### Step 4 -- Baseline Tier
- Logistic Regression (multinomial)
- Decision Tree
- Random Forest
- XGBoost / LightGBM

These establish the performance floor and are fast to iterate on. Tree-based models are expected to be competitive-to-superior on tabular financial features -- this will be established empirically before any deep learning work is justified.

- **Class weighting support (new):** every baseline classifier in the training framework must support class weighting (class_weight='balanced' or equivalent, e.g. scale_pos_weight/per-class weights for XGBoost/LightGBM) as a configurable option. Current class distribution doesn't require it (Section 3), but this is built in from the start so the pipeline is robust if label distribution shifts under the ATR-relative addendum or in future data.

### Step 5 -- Advanced Tier (conditional on Step 4 results)
- LSTM
- GRU
- Temporal CNN
- Transformer / Temporal Fusion Transformer (optional, gated on dataset size)

Advanced tier is only built out if baseline tier fails to meet the trading-metric promotion bar defined in Section 6 -- deep learning is not pursued by default just because it's available.

---

## 6. Evaluation Framework & Baseline Promotion Criteria

Accuracy alone is insufficient -- and is explicitly **not** used as the promotion gate. A model is only promoted past baseline tier if it demonstrates consistent trading performance, evaluated on the combination below (full metric definitions and thresholds specified in Step 4's evaluation spec):

- **Classification quality:** Macro F1, per-class Precision/Recall for BUY and SELL specifically (not just HOLD, which is the majority class), confusion matrix per walk-forward fold.
- **Trading performance (primary signal):** backtested cumulative return, Sharpe Ratio, Profit Factor, Maximum Drawdown.
- **Stability:** consistency of the above across walk-forward folds (Section 4) -- a model that performs well on 2019-2022 but collapses in 2023 is not promoted on the strength of its average.

Class balance per fold is also tracked (label distribution can drift across market regimes), since a shift there can explain a metric shift without indicating a model defect.

### Probability Calibration (new)

Because trading decisions depend on probability *quality*, not just the predicted class, the baseline evaluation pipeline includes explicit calibration:

- Each baseline classifier's raw output probabilities are calibrated (e.g. via CalibratedClassifierCV -- Platt scaling or isotonic regression, chosen per-model based on how well-behaved the raw scores are) before being treated as production-quality confidence.
- Calibration quality itself is checked (e.g. reliability diagrams / Brier score) as part of the evaluation spec -- a model isn't considered "done" just because it's calibrated; the calibration has to actually hold on held-out folds.
- Calibrated probabilities, not raw scores, are what gets persisted (Section 7) and what the trading engine consumes downstream.

---

## 7. Fold-Level Artifact Persistence (new)

For every walk-forward fold, the training pipeline saves:

- Trained model (serialized)
- Metrics (classification + trading, per Section 6)
- Confusion matrix
- Feature importance (where available -- tree-based models natively, others via permutation importance)
- Calibrated prediction probabilities on the test window
- Evaluation summary (human-readable rollup of the above)

Only the final promoted model was originally in scope for persistence; saving every fold's artifacts instead makes debugging, reproducibility, and fold-by-fold comparison possible without rerunning training. Storage layout and naming convention (e.g. models/fold_{n}/...) is defined concretely in Step 4's spec.

---

## 8. Proposed Phase 3 Step Sequence

| Step | Deliverable |
|------|-------------|
| 1 | This roadmap/architecture spec (current document) |
| 2 | Feature Store schema spec + feature set finalization for ML -- which Phase 2 features feed the store, storage/versioning format, ML-specific transforms (scaling, log1p(Volume)), and label-informed feature selection method |
| 3 | Walk-forward split implementation spec -- exact fold boundaries, purge/embargo config schema, data leakage checks |
| 4 | Baseline model training + evaluation spec -- includes class weighting config, calibration method per model, fold-level artifact persistence, and trading-metric promotion criteria |
| 5 | Advanced model training spec (conditional on Step 4 outcome) -- also where the ATR-relative label addendum is built and compared |
| 6 | Full evaluation & backtest framework spec |
| 7 | Model selection + final artifact spec (which model, why, what gets promoted forward) |

Each step is reviewed against actual Antigravity output before the next step begins, per existing project discipline. No step's code is generated until its spec is approved.

---

## 9. Carry-Forward Notes from Phase 2

These remain relevant context for feature/label work in Step 2, not re-derived here:

- Zero-volume limitation (index-ticker behavior) -- any volume-based features must account for this.
- RSI warm-up artifact (RSI_14 pinned at 100.0 for first 13 trading days) -- must not silently poison early-window training folds.
- Structural near-duplicate correlations -- feature selection in Step 2 should reference the existing KEEP/REVIEW/REMOVE CANDIDATE correlation report rather than redoing that analysis.
- Known extreme-return events (2008 crisis, 2009 election circuit halt, 2020 COVID crash) -- confirmed real, not data errors; walk-forward folds that contain these should be interpreted with that in mind rather than treated as anomalous model failure.

---

## 10. Inputs Confirmed from EDA_REPORT.md (Phase 2 Step 10 final compilation)

These are now locked in as Step 2 inputs, not re-derived:

- **Scaling recommendations are fully specified per-column** (StandardScaler for symmetric price/MA features, RobustScaler for heavy-tailed features like Volume, MACD, MACD_Hist, ATR_14, Daily_Return, Log_Return, MinMaxScaler for bounded RSI_14). Step 2 consumes this table directly.
- **Train-fold-only scaler fitting is already flagged** as mandatory in the source report -- consistent with the walk-forward scheme in Section 4 above.
- **log1p(Volume) is recommended** as a preprocessing node prior to scaling, to compress zero-inflation and right-tail skew. Not yet applied to any file -- this becomes an active pipeline step in Step 2/3, downstream of the Feature Store.
- **Feature selection is explicitly deferred to label-based relevance**, per the source report's own stance: raw variance, redundancy, and mutual-information rankings do not by themselves justify dropping a feature. Step 2 must specify a label-informed selection method (e.g. permutation importance or tree-based importances against Label_ThreeClass), not just prune the |r| >= 0.99 structural duplicates.
- **Label columns (Label_Binary, Label_ThreeClass) must be excluded from feature inputs** -- explicitly flagged as a lookahead-leakage risk in the source report, and structurally enforced by the Feature Store holding features only, pre-label (Section 2). This will be a hard assertion in the Step 2/3 pipeline spec, not just a convention.

## 11. Open Decisions for Review

Before proceeding to Step 2, please confirm or amend:

1. ~~Forward horizon for labels~~ -- resolved: next-bar (t+1), fixed +/-0.50% threshold (Section 3).
2. ~~Fold start year~~ -- resolved: 2014, excluding the zero-volume era (Section 4).
3. ~~Baseline promotion criteria~~ -- resolved: trading-metric combination in Section 6, not accuracy.
4. Whether the ATR-relative label addendum (Section 3) should be scoped now as a placeholder in Step 2's Feature Store spec, or left entirely unscoped until Step 4 results are in.
5. Calibration method default: Platt scaling (parametric, better for smaller folds) vs. isotonic regression (more flexible, needs more data) -- pick one as the Step 4 default, or leave it as a per-model choice made in Step 4's spec.
