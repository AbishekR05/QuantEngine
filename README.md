# QuantEngine: Historical Data Pipeline for Indian Stock Market

This project downloads, validates, cleans, and generates technical features for the NIFTY 50 Index (`^NSEI`).

## Project Structure

```text
QuantEngine/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── logs/
│
├── src/
│   ├── download_data.py
│   ├── validate_data.py
│   ├── preprocess.py
│   ├── indicators.py
│   └── utils.py
│
├── notebooks/
├── models/
├── requirements.txt
└── README.md
```

## Setup

1. Install Python 3.8+
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Pipeline

The pipeline is run sequentially:
1. **Download Data**: `python src/download_data.py`
   Downloads daily history from Yahoo Finance and saves raw data to `data/raw/nifty_daily.csv`.
2. **Validate Data**: `python src/validate_data.py`
   Validates data integrity and prints a report.
3. **Preprocess Data**: `python src/preprocess.py`
   Cleans duplicates, handles gaps, and saves to `data/processed/nifty_daily_clean.csv`.
4. **Calculate Indicators**: `python src/indicators.py`
   Calculates SMA, EMA, RSI, MACD, Bollinger Bands, ATR, Daily Returns, and Log Returns, saving to `data/processed/nifty_features.csv`.
