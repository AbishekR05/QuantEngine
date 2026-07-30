# QuantEngine: ML Market Prediction & Option Signaling for Nifty 50 (`^NSEI`)

QuantEngine is an institutional-grade quantitative research and machine learning pipeline designed to download, validate, clean, analyze, scale, and build predictive model signals on the Nifty 50 Index (`^NSEI`). The engine supports walk-forward cross-validation, model calibration, SHAP-based feature attribution, and chronological daily portfolio backtesting with realistic transaction costs and risk-management boundaries.

---

## 1. Project Architecture & Pipeline Phases

The project is structured around a modular quantitative research pipeline divided into four distinct phases:

### Phase 1: Feature Engineering & Preprocessing
1. **Download Data**: Fetches daily stock data from Yahoo Finance (`^NSEI`) covering the years 2007–2026.
2. **Validate Data**: Checks for anomalies, gaps, and formats.
3. **Preprocess Data**: Cleans duplicates and handles missing values.
4. **Indicators**: Calculates 22 technical indicators spanning price trend, momentum, and statistical dispersion categories.

### Phase 2: Exploratory Data Analysis (EDA) & Label Engineering
1. **Descriptive Statistics**: Computes standard moments (skewness, excess kurtosis, percentiles) for all features.
2. **Correlation & Redundancy**: Identifies multicollinear indicators using Pearson/Spearman matrix profiling.
3. **Market Regimes**: Identifies Trend (Bull/Bear/Sideways) and Volatility (High/Normal/Low) regimes as two independent dimensions.
4. **Feature Usefulness**: Evaluates features using raw variance, redundancy counts, and Mutual Information (MI).
5. **Label Engineering**: Generates supervised learning targets:
   - **Version A (Binary)**: Daily direction target (1 if Next Close > Today's Close, 0 otherwise).
   - **Version B (Three-Class)**: BUY / SELL / HOLD thresholds (BUY if Next Return > +0.50%, SELL if Next Return < -0.50%, HOLD otherwise).
   - **Version C (Option-Chain Roadmap)**: ATM Option Signaling design note modeling ATM Call/Put premium decay (theta) net profitability.
6. **Feature Scaling Recommendations**: Recommends appropriate scaling methods (StandardScaler, MinMaxScaler, RobustScaler) per column based on tails and outlier profiles.

### Phase 3: Machine Learning Model Development & Calibration
1. **Purged & Embargoed Cross-Validation**: Implements chronological walk-forward splits with purging and embargo margins to prevent leakage.
2. **Baseline Benchmarking**: Establishes performance baselines for Logistic Regression and XGBoost classifiers.
3. **Hyperparameter Optimization (HPO)**: Optimizes model hyperparameters across walk-forward folds 1-8.
4. **Model Calibration**: Implements Platt scaling (Logistic Regression) and Isotonic/Beta calibration (XGBoost) to calibrate trade entry probabilities.
5. **Model Explainability**: Runs walk-forward interpretability analyses:
   - Standardized coefficients for linear models.
   - TreeSHAP attributions for tree models with 500-sample background distributions.
   - Cross-fold stability evaluation (Jaccard similarity and Spearman rank correlations).

### Phase 4: Portfolio Backtesting & Strategy Tuning
1. **Chronological Backtesting**: Simulates daily trading portfolio execution with a 1-day lag on raw unscaled prices merged by date.
2. **Symmetric Confidence Filtering**: Enforces probability thresholds on trade signals to downgrade low-conviction signals to `HOLD`.
3. **Realistic Frictional Drag**: Models idealized vs. realistic cost modes (slippage, brokerage, spread, taxes, and exchange commissions).
4. **Risk Management Limits**: Integrates Stop Loss, Take Profit, and Max Holding Days limits, along with risk-based position sizing.
5. **Unified Statistics Compilation**: Evaluates performance on unified daily return series, worst-case peak-to-trough drawdowns, global net Profit Factor, and Lo (2002) Sharpe Ratio 95% Confidence Intervals.

---

## 2. Directory Structure

```text
QuantEngine/
│
├── config/
│   ├── config.yaml                     # Application settings & parameters
│   └── known_events.yaml               # Historic market shock date registries
│
├── data/
│   ├── raw/                            # Raw NSEI index data
│   ├── processed/                      # Cleaned features (nifty_features.csv)
│   ├── labels/                         # Labeled datasets (v1_binary, v2_threeclass)
│   ├── walk_forward_runs/              # Walk-forward fold datasets
│   ├── hpo_runs/                       # Hyperparameter optimized model checkpoints
│   ├── backtest_runs/                  # Simulated trade logs and fold-level metrics
│   └── logs/                           # Executional system logs
│
├── reports/
│   ├── eda/
│   │   ├── figures/                    # Generated charts & regime timelines
│   │   ├── statistics/                 # Sub-reports on outliers, regimes, etc.
│   │   └── EDA_REPORT.md               # Master Consolidated EDA Report
│   │
│   └── Results/
│       ├── phase3_results_report.md    # HPO, Calibration, and Explainability Report
│       ├── backtesting_performance_report.md  # Main Portfolio Backtest Results Report
│       ├── xgboost_threshold_sweep.md  # Symmetrical Threshold Sweep Report
│       ├── backtesting_methodology.md  # Aggregation Methodology & Math Formulations
│       ├── backtesting_changelog.md    # Changelog of backtesting engine corrections
│       └── backtesting_engineering_audit.md # Engineering Audit & limitations assessments
│
├── src/
│   ├── eda/                            # Analysis modules
│   │   ├── correlations.py
│   │   ├── outlier_analysis.py
│   │   ├── regime_analysis.py
│   │   ├── feature_usefulness.py
│   │   ├── label_engineering.py
│   │   ├── scaling_recommendation.py
│   │   └── generate_final_report.py
│   │
│   ├── models/                         # ML modules
│   │   ├── baseline_benchmarking.py
│   │   ├── hyperparameter_optimization.py
│   │   ├── model_explainability.py
│   │   ├── backtest_engine.py          # Chronological trade simulation engine
│   │   └── threshold_sweep.py          # Threshold sweep optimization script
│   │
│   ├── reports/
│   │   └── generate_backtest_report.py # Backtest markdown report generator
│   │
│   ├── download_data.py
│   ├── validate_data.py
│   ├── preprocess.py
│   ├── indicators.py
│   └── utils/
│       └── config_loader.py            # Pydantic configuration loader
│
├── requirements.txt
└── README.md
```

---

## 3. Installation & Execution

### Setup
1. Clone the repository and install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Execution Flow
Run the modules sequentially to execute the full pipeline:

1. **Fetch & Clean NSEI Data**:
   ```bash
   python src/download_data.py
   python src/validate_data.py
   python src/preprocess.py
   python src/indicators.py
   ```
2. **Run EDA Pipeline**:
   ```bash
   python -m src.eda.generate_final_report
   ```
3. **Execute ML Training & Calibration**:
   ```bash
   python -m src.models.baseline_benchmarking
   python -m src.models.hyperparameter_optimization
   ```
4. **Compute Explainability & Feature Attributions**:
   ```bash
   python -m src.models.model_explainability
   ```
5. **Run Backtesting Pipeline**:
   ```bash
   python -m src.models.backtest_engine
   ```
6. **Sweep Decision Thresholds (Exploratory)**:
   ```bash
   python -m src.models.threshold_sweep
   ```
7. **Compile Performance Dashboard**:
   ```bash
   python -m src.reports.generate_backtest_report
   ```

---

## 4. Key Performance Research Findings

*   **Risk-Adjusted Outperformance**: Under realistic transaction fees, **Logistic Regression** acts as a low-activity overlay (exposure: $1.4\%$), yielding **`1.07%` CAGR** with a unified Sharpe of **`0.53 [-0.22, 1.28]`** and worst peak-to-trough drawdown of only **`-3.82%`**.
*   **Strategy Filtering Sweet-Spot**: Symmetrically sweeping the decision threshold on **XGBoost** reveals an optimal execution coordinate at **`0.69`**. Raising the threshold from `0.55` to `0.69` successfully filters out high-noise signals, doubling realistic net returns to **`0.84%` CAGR** with a unified Sharpe of **`0.28 [-0.47, 1.03]`** and constraining max drawdown to **`-5.62%`**.
