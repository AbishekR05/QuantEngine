# QuantEngine: Market Prediction & Option Signaling for Nifty 50 (`^NSEI`)

QuantEngine is a modular quantitative research and machine learning pipeline designed to download, validate, clean, analyze, and build predictive target signals for the Nifty 50 Index (`^NSEI`). The ultimate objective of this engine is to generate **CALL** and **PUT** option trading signals based on historical and real-time market data.

---

## 1. Project Overview & Architecture

The project is structured around a modular pipeline divided into three distinct phases:

### Phase 1: Feature Engineering
1. **Download Data**: Fetches daily stock data from Yahoo Finance (`^NSEI`) covering the years 2007–2026.
2. **Validate Data**: Checks for anomalies, gaps, and formats.
3. **Preprocess Data**: Cleans duplicates and handles missing values.
4. **Indicators**: Calculates 22 technical indicators spanning price trend, momentum, and statistical dispersion categories.

### Phase 2: Exploratory Data Analysis (EDA) & Label Engineering
1. **Descriptive Statistics**: Computes standard moments (skewness, excess kurtosis, percentiles) for all features.
2. **Correlation & Redundancy**: Identifies multicollinear indicators and redundancy pairs using Pearson/Spearman matrix profiling.
3. **Outlier Analysis & Shocks**: Maps and matches anomalies chronologically with major market shocks (GFC, COVID, Election windows) and zero-volume limitations.
4. **Market Regimes**: Identifies Trend (Bull/Bear/Sideways) and Volatility (High/Normal/Low) regimes as two independent dimensions.
5. **Feature Usefulness**: Evaluates features using raw variance, redundancy counts, and Mutual Information (MI).
6. **Label Engineering**: Generates supervised learning targets:
   - **Version A (Binary)**: Classification target (1 if Next Close > Today's Close, 0 otherwise).
   - **Version B (Three-Class)**: BUY / SELL / HOLD thresholds (BUY if Next Return > +0.50%, SELL if Next Return < -0.50%, HOLD otherwise).
   - **Version C (Option-Chain Roadmap)**: ATM Option Signaling design note modeling ATM Call/Put premium decay (theta) net profitability.
7. **Feature Scaling Recommendations**: Recommends appropriate scaling methods (StandardScaler, MinMaxScaler, RobustScaler) per column based on tails and outlier profiles.

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
│   └── logs/                           # Executional system logs
│
├── reports/
│   ├── eda/
│   │   ├── figures/                    # Generated charts & regime timelines
│   │   ├── statistics/                 # Sub-reports on outliers, regimes, etc.
│   │   └── EDA_REPORT.md               # Master Consolidated EDA Report
│
├── src/
│   ├── eda/                            # Analysis modules
│   │   ├── correlations.py
│   │   ├── outlier_analysis.py
│   │   ├── regime_analysis.py
│   │   ├── feature_usefulness.py
│   │   ├── label_engineering.py
│   │   ├── scaling_recommendation.py
│   │   └── generate_final_report.py    # Report consolidator script
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

## 3. Installation & Usage

### Setup
1. Clone the repository and install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Execution Flow
Run the modules sequentially to execute the full pipeline:

1. **Download Data**:
   ```bash
   python src/download_data.py
   ```
2. **Validate Data**:
   ```bash
   python src/validate_data.py
   ```
3. **Preprocess Data**:
   ```bash
   python src/preprocess.py
   ```
4. **Calculate Indicators**:
   ```bash
   python src/indicators.py
   ```
5. **Run Market Regime Profiler**:
   ```bash
   python -m src.eda.regime_analysis
   ```
6. **Evaluate Feature Usefulness**:
   ```bash
   python -m src.eda.feature_usefulness
   ```
7. **Engineer Target Labels**:
   ```bash
   python -m src.eda.label_engineering
   ```
8. **Recommend Feature Scaling**:
   ```bash
   python -m src.eda.scaling_recommendation
   ```
9. **Compile Master EDA Report**:
   ```bash
   python -m src.eda.generate_final_report
   ```

---

## 4. Current Status: Ready for Phase 3 (Machine Learning)
The exploratory data analysis and target engineering have been fully validated, frozen, and tagged under **`Phase2_final`**. 

The next phase will focus on developing:
- Walk-forward time-series cross-validation pipelines.
- Feature selection filters to manage indicator multicollinearity.
- Model training and hyperparameter search for classification/signaling algorithms.
- Historical option strategy backtesting.
