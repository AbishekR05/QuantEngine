# Phase 3 Step 7 — Backtesting Framework: Implementation Specification

**Status:** Draft for review
**Depends on (frozen, not re-discussed here):** Step 1 (Architecture), Step 2 (Feature Store), Step 3 (Walk-Forward), Step 4 (Baseline Benchmarking), Step 5 (Hyperparameter Optimization), Step 6 (Model Explainability)
**Consumed by:** Antigravity
**Frozen models entering this step:** Logistic Regression (Step 5 best trial), XGBoost (Step 5 best trial) — XGBoost currently the stronger predictive model per Step 4/5 results. No model training occurs here.

---

## 1. Scope and Objectives

Step 7 evaluates whether the frozen models produce **profitable trading behavior**, not just correct classifications, when their predictions are converted into simulated trades executed strictly in chronological order. This is the first step in the project where a classification output becomes a trading decision — everything before this point (Steps 4–6) evaluated the models as classifiers. Model accuracy is not the target here; realized, cost-aware, risk-aware trading performance is.

**Architectural addition to this step (not part of the original Step 1 roadmap, adopted here):** predictions are not converted to trades via a raw argmax of `{BUY, SELL, HOLD}`. Instead, a **configurable confidence threshold** is applied to each class's calibrated probability before a directional trade is taken (Section 6). This is a direct, practical use of Step 1's original architectural decision to treat calibrated probabilities as a first-class model output rather than collapsing them into a hard label immediately — this step is where that decision starts paying off.

---

## 2. Inputs and Outputs

**Inputs:**
- Frozen per-fold model artifacts for both eligible models (Step 5 best-trial outputs) — loaded, never refit.
- Per-fold `test_df` from Step 3 (walk-forward boundaries, unchanged) — the chronological price/feature series each fold's simulated trading run executes against.
- Calibrated class probabilities per row, per model, per fold — reused from Step 4/5's calibration pipeline output, not recomputed here.

**Outputs:**
- Per-fold, per-model trade logs and portfolio histories (Section 8).
- Per-fold, per-model performance and risk metrics (Section 12).
- Per-fold benchmark comparison reports (Section 13).
- An aggregate report across Folds 1–7 (full-year folds), per model, with Fold 8 reported separately (Section 11).

---

## 3. Backtesting Philosophy

- **The framework operates exactly as a live trader would.** At the point a trade decision is made for a given day, only information available up to and including that day may be used. This is the same forward-only constraint already enforced in Steps 3–6, applied here to trade execution instead of model training or explanation.
- **No hindsight adjustment of any kind.** A trade's entry/exit is never revised after the fact based on what the market did afterward; stop-loss/take-profit/trailing-stop logic (Section 10) evaluates only using information available at or before the current simulated day.
- **Trades occur strictly in chronological order**, one day at a time, within each fold's test window — there is no batch-vectorized shortcut that could implicitly leak a later day's information into an earlier day's decision.
- **The purpose is trading evaluation, not model improvement.** Nothing discovered during backtesting (e.g. a strategy performing poorly) triggers retraining, retuning, or feature changes within this step — such findings are written into the reports (Section 16) for a future step or addendum to act on, not acted on here.

---

## 4. Eligible Models

Both frozen models from Step 5 are backtested — there is no additional filtering at this stage (consistent with Step 6's approach: this step evaluates what exists, it does not re-litigate which models "deserve" evaluation).

| Model | Source Artifact | Notes |
|---|---|---|
| Logistic Regression | Step 5 best trial, per fold | |
| XGBoost | Step 5 best trial, per fold | Currently the stronger predictive model per Step 4/5 — not assumed to also be the stronger *trading* model; that is exactly what this step tests. |

---

## 5. Trading Workflow

Fixed pipeline, applied per day, per fold, per model:

```
Prediction (frozen model, calibrated probabilities)
    ↓
Signal Generation (confidence-thresholded — Section 6)
    ↓
Position Entry (Section 7)
    ↓
Position Management (Section 10 — stop loss / take profit / trailing stop / max holding days)
    ↓
Position Exit (Section 7)
    ↓
Trade Logging (Section 8)
    ↓
Portfolio Update (Section 8)
```

Each stage consumes only the current day's model output and current/prior portfolio state — no stage looks ahead to a later day's data.

---

## 6. Signal Generation (including Confidence Thresholds)

This is where the calibrated class probabilities (Step 4/5 output) are converted into one of `{BUY, SELL, HOLD}` as an actual trading signal — and where the newly-adopted confidence-threshold mechanism lives.

- **Default (no threshold) behavior:** the signal is the argmax of the three calibrated class probabilities — whichever of `BUY`/`SELL`/`HOLD` has the highest probability for that row.
- **Threshold-gated behavior (the adopted default going forward):**
  - A directional signal (`BUY` or `SELL`) is only emitted if that class's calibrated probability meets or exceeds its configured threshold.
  - If the argmax class is `BUY` or `SELL` but its probability is **below** the configured threshold for that class, the signal is downgraded to `HOLD` — the model's directional lean exists but is not acted on.
  - `HOLD` itself has no threshold requirement — it is never downgraded further; there is no more conservative fallback than not trading.
- **Thresholds are fully configurable, not hardcoded (Section 15):**
  - Independently configurable **per class** (`buy_threshold`, `sell_threshold`) — they are not required to be symmetric. A 0.70 default is used for both in this specification, but nothing in the mechanism assumes they must match.
  - Independently configurable **per model** — Logistic Regression and XGBoost may use different thresholds, since Step 4/6 already showed the two models have different calibration behavior (`raw_vs_calibrated_report.md`) and there is no reason to assume the same threshold is equally appropriate for both.
  - A **threshold of `0.0` (or a config flag `thresholding_enabled: false`) reduces the mechanism to plain argmax** — this is required, not incidental: the "Naive Classifier"/argmax comparison in the benchmark suite (Section 13) needs exactly this mode to isolate the effect of thresholding from the effect of the underlying model.
- This mechanism is deliberately kept as a standalone, swappable stage between Prediction and Position Entry in the workflow (Section 5) — future addenda (e.g. a dynamic, volatility-conditioned threshold) can replace this stage's internals without touching anything upstream (model inference) or downstream (execution engine).

---

## 7. Trade Execution Engine

- **Signal-to-position mapping:** `BUY` signal → open/maintain a long position; `SELL` signal → open/maintain a short position; `HOLD` signal → no new position action (an existing open position is left to Position Management, Section 10, not force-closed by a `HOLD` signal alone).
- **Single open position by default:** only one position may be open at a time, configurable (Section 15) to allow multiple concurrent positions later without redesigning this engine — the default constraint is deliberately conservative.
- **Position entry:** executed at the next available price after a qualifying signal (i.e. the signal generated from day *t*'s data results in entry priced at day *t*'s close or day *t+1*'s open, per a configurable `execution_lag` setting — Section 15) — this detail is made explicit and configurable specifically to avoid an implicit look-ahead assumption (using day *t*'s close to both generate and price the same day's entry is a common, easy-to-miss leakage source, so the lag is a named, visible config value rather than an implicit zero).
- **Position exit:** triggered by either an opposing signal (e.g. `SELL` signal while long), a risk-management rule firing (Section 10), or the end of the fold's test window (forced close, logged distinctly from a rule-triggered exit).
- **Signal conflict handling:** if a new signal in the same direction as an already-open position arrives (e.g. `BUY` while already long), the existing convention is "maintain position, do not add" by default — sizing up on repeated same-direction signals is a configurable variant (Section 15), not the default.

---

## 8. Portfolio Management

- **Trade Log:** one record per completed trade — entry date/price, exit date/price, direction, size, holding period, gross P&L, transaction costs applied (Section 9), net P&L, and the signal/probability values that triggered entry and exit.
- **Portfolio History:** running capital, open-position state, and daily mark-to-market value across the entire fold's test window — this is the basis for the equity curve (Section 12).
- **Capital allocation:** governed by the risk-management configuration (Section 10) — position size per trade is not hardcoded to "all available capital," to avoid a default that silently produces unrealistic all-in sizing.

---

## 9. Transaction Cost Model

- Configurable, independently toggleable components: brokerage, slippage, exchange fees, taxes, spread, commission (Section 15) — each has its own config entry so a specific cost component can be isolated or removed without touching the others.
- **Two required backtest modes:**
  - **Idealized (zero-cost):** all cost components set to zero — isolates pure signal quality from execution friction.
  - **Realistic (configured cost):** the components above applied at their configured values.
  - Both modes are run and reported side by side for every fold/model combination (Section 16) — not one or the other by choice, since the gap between the two is itself a diagnostic (a strategy that only looks profitable idealized is a materially different finding than one that survives realistic costs).
- Cost application timing: costs are deducted at the point of trade execution (entry and exit each incur their configured components), not batched or approximated at the fold level — consistent with the day-by-day chronological execution philosophy (Section 3).

---

## 10. Risk Management

Configurable, default-simple (Section 15):

- **Stop Loss / Take Profit / Trailing Stop:** each independently configurable (enabled/disabled, and threshold value if enabled) — evaluated using only the current and prior days' prices for the open position, never a future price.
- **Maximum Holding Days:** a position open longer than this configured limit is force-closed — default value provided but adjustable.
- **Position Size / Capital Allocation / Risk Per Trade:** position size is computed from a configured risk-per-trade fraction of current capital by default (a simple, standard sizing convention), not a fixed share count — so sizing scales with the portfolio's actual state rather than being detached from it.
- **Maximum Open Positions:** default `1` (Section 7), configurable upward.
- All risk parameters are declared, not auto-tuned, in this step — **no optimization of trading rules occurs here** (per the explicit exclusion, Section 18); a value is set in configuration and used as-is for the entire backtest run.

---

## 11. Walk-Forward Backtesting Workflow

- Backtesting uses the **identical fold boundaries from Step 3** — no re-slicing, no new fold logic introduced.
- Each fold's test window (Step 3 Section 2) is backtested **independently** — a fold's simulated portfolio starts fresh (reset capital, no carried-over open positions) rather than continuing from the prior fold's ending state. This keeps each fold's performance report attributable to that fold's own market period, not contaminated by a position opened under a different fold's model.
- **No pooled backtest** — there is no single continuous simulation spanning 2019–2026 that ignores fold boundaries; that would mix predictions from different fold-specific trained models into one chronological stream, which is exactly the kind of shortcut the walk-forward discipline exists to prevent.
- **Fold 8 remains partial** — reported independently, exactly as in Steps 3–6, and excluded from the Folds 1–7 aggregate (Section 12).
- **Aggregate reports combine Folds 1–7 only** — computed as a rollup of the independent per-fold results (e.g. mean/median of per-fold metrics, and a concatenated-for-display-only equity curve that visually shows fold transitions rather than pretending they're one continuous simulation).

---

## 12. Performance Metrics

Computed per fold, per model, per cost mode (idealized / realistic):

- Total Return
- Annualized Return (CAGR)
- Maximum Drawdown
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Profit Factor
- Expectancy
- Average Trade (P&L per trade)
- Win Rate / Loss Rate
- Average Holding Period
- Number of Trades
- Exposure % (fraction of the fold's test window with an open position)
- Equity Curve (data series)
- Rolling Returns (data series)
- Drawdown Curve (data series)
- Trade Distribution (P&L histogram data, not a rendered chart)
- Monthly Returns
- Yearly Returns

All of the above are also computed at the **Folds 1–7 aggregate level**, per model, per cost mode, with Fold 8 shown as a separate, clearly-labeled entry rather than blended into the aggregate — consistent with every prior step's Fold 8 handling.

---

## 13. Benchmark Comparisons

Every strategy (per model, per fold, per cost mode) is compared against:

- **Buy & Hold** — hold a long position for the entire fold's test window.
- **Naive Classifier** — the same "always predict `HOLD`" floor used in Step 4's viability gate, applied here to trading (i.e., a strategy that never trades, included as a literal zero-activity baseline).
- **Always Long** — a long position held continuously regardless of any model signal (distinct from Buy & Hold only in that it's explicitly framed as a directional-bias baseline rather than a passive benchmark, though mechanically similar under this framework's default single-position constraint).
- **Always Flat** — never in a position, capital sits idle (distinct from Naive Classifier in that it makes no reference to model output at all — it's a pure zero-activity control).
- **Previous Step Baseline** — the model's own Step 4 default-configuration classification performance is not itself a trading benchmark, but is included in the comparison report as reference context (e.g. "did the Step 5 optimization and Step 7 thresholding combination change trading outcomes versus what the unoptimized Step 4 model would have produced under the same trading rules") — computed by running the Step 4 default-configuration model's calibrated probabilities through this same Section 5–11 pipeline, not by re-deriving a separate metric.

Comparison reports are generated automatically per fold and per aggregate, for every model/cost-mode combination — not produced manually or only on request.

---

## 14. Artifact Directory Structure

```
backtest_runs/{run_id}/
  logistic_regression/
    idealized/
      fold_{n}/
        trade_log.yaml
        portfolio_history.yaml
        equity_curve.yaml
        performance_metrics.yaml
        risk_metrics.yaml
        benchmark_comparison.yaml
      aggregate_folds_1_7.yaml
      fold_8_partial.yaml
    realistic/
      fold_{n}/ ...                    # same structure as idealized/
      aggregate_folds_1_7.yaml
      fold_8_partial.yaml
  xgboost/
    idealized/ ...                     # same structure as logistic_regression/
    realistic/ ...
  run_config_snapshot.yaml
```

`run_id` follows the same convention as Steps 3–6: tied to Feature Store version, label version, Walk-Forward run ID, and the Step 5 run ID whose frozen artifacts are being backtested.

---

## 15. Configuration Schema

```yaml
backtesting:
  initial_capital: 1000000
  execution_lag_days: 1                # signal from day t executes at day t+1's price
  signal_generation:
    thresholding_enabled: true
    confidence_thresholds:
      logistic_regression:
        buy_threshold: 0.70
        sell_threshold: 0.70
      xgboost:
        buy_threshold: 0.70
        sell_threshold: 0.70
  position:
    max_open_positions: 1
    allow_scaling_into_position: false
  transaction_costs:
    idealized:
      brokerage: 0.0
      slippage: 0.0
      exchange_fees: 0.0
      taxes: 0.0
      spread: 0.0
      commission: 0.0
    realistic:
      brokerage: 0.0003
      slippage: 0.0005
      exchange_fees: 0.0001
      taxes: 0.001
      spread: 0.0002
      commission: 0.0002
  risk_management:
    stop_loss: {enabled: true, value: 0.02}
    take_profit: {enabled: true, value: 0.04}
    trailing_stop: {enabled: false, value: null}
    max_holding_days: 10
    risk_per_trade: 0.01
  benchmarks:
    - "buy_and_hold"
    - "naive_classifier"
    - "always_long"
    - "always_flat"
    - "previous_step_baseline"
  versioning:
    feature_store_version: "v1"
    label_version: "version_b"
    walk_forward_run_id: "fs_v1_threeclass_embargo0"
    hpo_run_id_logistic_regression: "<from Step 5>"
    hpo_run_id_xgboost: "<from Step 5>"
```

- `signal_generation.confidence_thresholds` is the mechanism described in Section 6 — nested per model, per class, exactly so it can be tuned independently for either model without touching anything else in this schema. Setting `thresholding_enabled: false` reduces signal generation to plain argmax for a given run (used for the Naive Classifier / argmax-isolation comparisons in Section 13).
- All values shown are illustrative defaults, not tuned or optimized — per this step's own exclusion (Section 18), no search over these values occurs within this document's scope.

---

## 16. Generated Reports

- Trade Log (per fold, per model, per cost mode).
- Portfolio History (per fold, per model, per cost mode).
- Daily Equity Curve (data series, no chart).
- Performance Metrics (Section 12).
- Monthly Returns / Annual Returns.
- Risk Metrics (drawdown, exposure, etc., Section 12).
- Benchmark Comparison (Section 13).
- Fold Summary (per fold, per model, per cost mode).
- Aggregate Summary (Folds 1–7, per model, per cost mode; Fold 8 shown separately).

All reports are machine-readable data exports — no chart or image file is produced by this module; any downstream visualization consumes this exported data separately.

---

## 17. Acceptance Criteria

- **Chronological execution:** every simulated trade decision is verifiably based only on data available up to and including its decision date — verified via an explicit assertion (no row's decision references a later row's data), not just by code review.
- **Zero leakage:** confirmed consistent with Steps 3–6's leakage-prevention discipline — extended here to cover trade execution timing (Section 7's `execution_lag_days`) and risk-management evaluation (Section 10), not just model training/scaling/calibration.
- **Walk-forward compliance:** fold boundaries match Step 3 exactly; no pooled backtest exists as an artifact (Section 11).
- **Deterministic replay:** given the same frozen model artifacts, same fold data, and same configuration, a repeated backtest run produces identical trade logs and metrics — no unseeded randomness is introduced anywhere in this framework (position sizing, cost application, and signal generation are all deterministic functions of price/probability data and configuration).
- **Complete trade logging:** every position opened has a corresponding logged entry and exit (or an explicit forced-close-at-fold-end record) — no position silently vanishes from the trade log.
- **Reproducible portfolio metrics:** all Section 12 metrics are recomputable directly from the persisted trade log and portfolio history, without needing to re-run the simulation — i.e., the trade log is a sufficient source of truth for metric verification.
- **Benchmark generation:** all five benchmarks (Section 13) are generated automatically for every fold/model/cost-mode combination, not on a case-by-case basis.

---

## 18. Explicit Exclusions

This step must NOT:
- Train models or tune hyperparameters (Steps 4/5 remain frozen).
- Engineer new features or modify Feature Store contents (Step 2).
- Modify or reopen explainability outputs (Step 6).
- Change Walk-Forward fold boundaries, purge/embargo configuration, or leakage-prevention assertions (Step 3).
- Perform paper trading or execute live trades — this is a historical simulation only.
- Access future prices at any stage, including within risk-management rule evaluation.
- **Optimize trading rules** — confidence thresholds (Section 6), risk-management parameters (Section 10), and cost assumptions (Section 9) are all configurable, but none are searched, tuned, or automatically adjusted within this step. Any future systematic search over these values (e.g. a Step 8 "trading rule optimization") is out of scope here — this step only makes such a future search possible by ensuring every relevant value is a named config entry rather than a hardcoded constant.

---

## 19. Open Decisions

1. Confidence threshold defaults (`0.70` for both classes, both models, Section 15) are placeholder values pending real backtest results — confirm as the starting point for the "realistic" runs, or start lower (e.g. `0.55–0.60`) to avoid over-restricting trade frequency on the first pass.
2. `execution_lag_days: 1` (signal from day *t* executes at day *t+1*'s price) is the safer, more realistic default — confirm, or prefer same-day execution at day *t*'s close if that better matches the intended live-deployment assumption (Phase 4 territory, but the assumption needs to be set now).
3. Realistic transaction cost values (Section 15) are illustrative placeholders, not sourced from actual NSE brokerage/tax schedules — confirm whether real cost figures should be researched and substituted before this spec is finalized, or left as configurable placeholders for Antigravity/the user to fill in with actual figures later.
4. Whether the "Previous Step Baseline" benchmark (Section 13) should also be run through both idealized and realistic cost modes (doubling that benchmark's report count) or only realistic, since its purpose is comparative context rather than a primary result.
