# TradingAI — Phase 1 Architecture & Roadmap
### Historical Data Pipeline for NIFTY (^NSEI)

---

## 1. Design Philosophy

Phase 1 has exactly one job: **produce a dataset you can trust completely.** Every later phase — backtesting, ML, risk management, live trading — inherits whatever quality (or garbage) sits in this layer. So the design bias here is:

- **Idempotent**, re-runnable pipeline (running it twice produces the same result, not duplicates)
- **Versioned** outputs (never silently overwrite; always know which dataset a backtest used)
- **Config-driven**, not hardcoded (tickers, indicator periods, date ranges all live in config files)
- **Fail loud** — validation errors stop the pipeline rather than silently passing bad data downstream

---

## 2. Project Structure (Phase 1 scope)

```
TradingAI/
│
├── config/
│   ├── config.yaml            # global settings (ticker, date range, paths)
│   ├── indicators.yaml        # indicator params (MA windows, RSI period, etc.)
│   └── validation_rules.yaml  # thresholds for OHLC sanity checks
│
├── data/
│   ├── raw/                   # untouched yfinance downloads (immutable)
│   ├── processed/             # cleaned, validated data
│   ├── features/              # data + engineered indicators
│   └── versions/              # dataset snapshots with manifest files
│
├── database/
│   ├── schema.sql              # table definitions (SQLite for Phase 1)
│   └── db_manager.py           # connection handling, migrations
│
├── src/
│   ├── data_pipeline/
│   │   ├── downloader.py       # yfinance fetch logic
│   │   ├── validator.py        # data quality checks
│   │   ├── cleaner.py          # fixes for detected issues
│   │   ├── feature_engineer.py # technical indicators
│   │   └── versioner.py        # dataset snapshotting
│   │
│   ├── utils/
│   │   ├── logger.py
│   │   └── config_loader.py
│   │
│   └── reports/
│       └── validation_report.py # generates human-readable QA reports
│
├── logs/
├── tests/
│   └── test_data_pipeline/
├── notebooks/
│   └── 01_data_exploration.ipynb
├── docs/
│   └── data_dictionary.md
├── requirements.txt
└── README.md
```

---

## 3. Module-by-Module Explanation

### `config/config.yaml`
Single source of truth for: ticker symbol, start/end dates, file paths, database path. Nothing in the code should hardcode `"^NSEI"` or a date string — it all reads from here. This is what lets you later add BANKNIFTY by editing one file instead of touching code.

### `src/data_pipeline/downloader.py`
Wraps `yfinance`. Responsibilities:
- Fetch full daily history for `^NSEI`
- Retry logic with backoff (Yahoo occasionally rate-limits)
- Save raw response untouched to `data/raw/` with a timestamped filename
- Never mutates raw data — raw is your ground truth if something downstream breaks

### `src/data_pipeline/validator.py`
Runs the checks your spec calls for:
- Duplicate rows/dates
- Missing trading dates (cross-checked against NSE holiday calendar — flagged as a dependency below)
- Missing values (NaNs in OHLCV)
- Impossible OHLC relationships (e.g., `High < Low`, `Close > High`, `Open < 0`)
- Invalid/negative volume
- Corrupted rows (wrong dtypes, unparseable dates)

Outputs a structured validation result object (pass/fail per check + row-level detail) rather than just printing to console — this feeds the report generator and can gate the pipeline (stop on failure).

### `src/data_pipeline/cleaner.py`
Takes validator output and applies **only pre-approved, logged** fixes (e.g., forward-fill a single missing value, drop an exact duplicate). Every fix is logged with before/after values — nothing gets silently altered. Anything the cleaner can't confidently fix gets escalated back to you rather than guessed at.

### `src/data_pipeline/feature_engineer.py`
Reads `config/indicators.yaml` and generates indicators dynamically rather than one function per indicator hardcoded with fixed windows. E.g.:

```yaml
moving_averages: [10, 20, 50, 200]
rsi_period: 14
macd: {fast: 12, slow: 26, signal: 9}
bollinger: {period: 20, std_dev: 2}
```

The engineer reads this config and produces exactly the columns specified — no hardcoded `MA_50` column name baked into code.

### `src/data_pipeline/versioner.py`
Every time the pipeline runs end-to-end, it snapshots the final dataset into `data/versions/vYYYYMMDD_HHMM/` along with a manifest (`manifest.json`) recording: row count, date range, which config was used, validation report summary, and a hash of the file. This is what lets you say "backtest #47 used dataset version X" with certainty.

### `database/`
Phase 1 uses **SQLite** (not Postgres yet) — no reason to run a database server for a single-instrument daily dataset. Schema is designed so `option_chain`, `news`, `economic_events`, `trade_history`, `portfolio_history` tables can be added later without restructuring what's already there (each gets its own table with a foreign key on `date` / `symbol`).

### `src/reports/validation_report.py`
Generates a readable Markdown/HTML report per pipeline run: what was checked, what passed, what failed, and what the cleaner changed. This is your audit trail.

---

## 4. Data Flow (Phase 1)

```
config.yaml
     │
     ▼
downloader.py ──► data/raw/nsei_raw_<timestamp>.csv
     │
     ▼
validator.py ──► validation_report (pass/fail + detail)
     │
     ▼
cleaner.py ──► data/processed/nsei_clean.csv  +  cleaning_log.json
     │
     ▼
feature_engineer.py ──► data/features/nsei_features.csv
     │
     ▼
versioner.py ──► data/versions/vYYYYMMDD_HHMM/ (+ manifest.json)
     │
     ▼
database/  (SQLite ingestion)
```

---

## 5. Dependencies

| Package | Purpose |
|---|---|
| `yfinance` | Historical OHLCV download |
| `pandas` | Data manipulation |
| `numpy` | Numeric ops |
| `pandas-ta` or `ta` | Technical indicators (avoids reinventing RSI/MACD math) |
| `pyyaml` | Config loading |
| `sqlalchemy` | DB abstraction (makes swapping SQLite → Postgres later trivial) |
| `pydantic` | Config/schema validation with type safety |
| `pytest` | Unit tests |
| `great-expectations` *(optional, heavier)* | If you want industrial-strength data validation instead of hand-rolled checks |

**External dependency to flag:** validating "missing trading dates" properly requires an **NSE trading holiday calendar** (yfinance data alone won't tell you which gaps are holidays vs. genuinely missing data). Recommend the `nsepy`/`mcal` (`pandas-market-calendars` with an NSE/XNSE exchange calendar) approach, or a static holiday list you maintain in `config/`.

---

## 6. Recommendations / Things to Decide Before We Code

1. **Adjusted vs. raw prices** — `^NSEI` is an index so there are no dividend adjustments to worry about (unlike individual stocks), but worth confirming you want `auto_adjust=True` default behavior understood explicitly rather than left implicit.
2. **Timezone handling** — yfinance sometimes returns tz-naive or UTC-shifted timestamps for NSE data. Decide now: store everything in `Asia/Kolkata` or naive-date-only. Getting this wrong causes subtle off-by-one-day bugs in backtesting later.
3. **SQLite now vs. Postgres later** — I'd stick with SQLite through Phase 1–2 and only move to Postgres when you add option chain / tick-level data where concurrent writes matter more.
4. **Great Expectations vs. hand-rolled validator** — hand-rolled is simpler to reason about for one instrument; Great Expectations pays off once you're validating many data sources (Phase 2+ news/sentiment/option chain). Lean hand-rolled for now, revisit later.
5. **Testing data** — recommend a small frozen synthetic CSV with deliberately broken rows (negative volume, High < Low, a duplicate date) as a fixture, so `validator.py` has something concrete to be tested against from day one.

---

## 7. Implementation Roadmap (Phase 1, module by module)

| Step | Module | Depends on | Approval gate |
|---|---|---|---|
| 1 | `config/` + `utils/config_loader.py` | — | You review config schema |
| 2 | `downloader.py` | Step 1 | You confirm raw download works, inspect raw CSV |
| 3 | `validator.py` | Step 2 | You review validation rule set against real data |
| 4 | `cleaner.py` | Step 3 | You review cleaning log for correctness |
| 5 | `feature_engineer.py` | Step 4 | You review generated indicators |
| 6 | `versioner.py` + `database/` | Step 5 | You review schema + manifest format |
| 7 | `reports/validation_report.py` | Step 3 | You review report readability |
| 8 | `tests/` | All above | You review coverage |

We build **one module at a time**, you review/approve, then we move to the next — exactly as your spec asks.

---

## Next Step

Once you upload the CSV/data you pulled via yfinance, I'll:
1. Run it through the validation checks described above (manually first, before we've even built `validator.py`) so we know what real-world issues this dataset actually has.
2. Use those findings to calibrate `validation_rules.yaml` so it's not guessing at thresholds — it's built against your real data.

After that, we start with **Step 1 (config + config_loader)** if this architecture looks good to you.
