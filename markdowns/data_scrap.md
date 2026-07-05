You are my lead AI/ML engineer and quantitative developer.

We are building a professional AI-powered trading system for the Indian stock market. This is a long-term project that will eventually support:

- NIFTY Options (Call/Put prediction)
- Risk management
- Position sizing
- Backtesting
- Paper trading
- Live trading integration (later)

IMPORTANT:
Do NOT jump into machine learning yet.

Our first objective is to build a clean and reliable historical data pipeline.

## Phase 1 Goal

Create a Python project that downloads, validates, cleans, and stores historical NIFTY 50 index data.

### Data Source

Use the `yfinance` library.

Ticker:
^NSEI

Download the maximum available DAILY historical data from the earliest available date until today.

### Requirements

Create a clean project structure like this:

stock_ai/
│
├── data/
│ ├── raw/
│ ├── processed/
│ └── logs/
│
├── src/
│ ├── download_data.py
│ ├── validate_data.py
│ ├── preprocess.py
│ ├── indicators.py
│ └── utils.py
│
├── notebooks/
│
├── models/
│
├── requirements.txt
│
└── README.md

## Step 1

Write download_data.py

It should:

- Download the complete historical DAILY dataset for ^NSEI
- Include:
  Date
  Open
  High
  Low
  Close
  Adj Close
  Volume

- Save the raw CSV inside:

data/raw/nifty_daily.csv

- Print:
  earliest date
  latest date
  total trading days
  number of missing values

## Step 2

Create validate_data.py

It should verify:

- duplicate rows
- missing dates
- missing values
- High >= Low
- High >= Open
- High >= Close
- Low <= Open
- Low <= Close
- invalid or negative prices
- invalid volume values

Generate a validation report.

## Step 3

Create preprocess.py

It should:

- remove duplicates
- handle missing values
- sort by date
- create a cleaned dataset

Save as:

data/processed/nifty_daily_clean.csv

## Step 4

Create indicators.py

Calculate and append at least:

- SMA 20
- SMA 50
- SMA 200
- EMA 20
- EMA 50
- RSI 14
- MACD
- Signal Line
- Bollinger Bands
- ATR
- Daily Returns
- Log Returns

Save as:

data/processed/nifty_features.csv

## Requirements

Use:

- pandas
- numpy
- yfinance

Keep the code modular, production-quality, well documented, and ready for future expansion.

Do not write any machine learning code yet.

Focus entirely on creating a robust historical market dataset that will later be used for AI model training.
