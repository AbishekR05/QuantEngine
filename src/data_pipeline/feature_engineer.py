import sys
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config, load_indicators_config

logger = get_logger("feature_engineer")

def calculate_features(clean_filepath: str, output_filepath: Optional[str] = None) -> str:
    """
    Calculates technical indicators dynamically as specified in config/indicators.yaml.
    Saves the computed feature dataset to data/features/nsei_features.csv.
    """
    logger.info(f"Starting technical indicator feature engineering using cleaned source: {clean_filepath}")
    
    config = load_global_config()
    indicators = load_indicators_config()
    
    file_path = Path(clean_filepath)
    if not file_path.exists():
        err_msg = f"Cleaned data file not found at: {clean_filepath}"
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)
        
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise e
        
    # Standardize types and sort ascending
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    logger.info("Computing custom indicators dynamically...")
    
    # 1. Simple & Exponential Moving Averages
    ma = indicators.moving_averages
    for window in ma.sma:
        col_name = f"SMA_{window}"
        df[col_name] = df['Close'].rolling(window=window).mean()
        logger.debug(f"Calculated SMA with window={window}")
        
    for window in ma.ema:
        col_name = f"EMA_{window}"
        df[col_name] = df['Close'].ewm(span=window, adjust=False).mean()
        logger.debug(f"Calculated EMA with window={window}")
        
    # 2. Relative Strength Index (RSI)
    rsi_p = indicators.rsi.period
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Apply Wilder's moving average (alpha = 1 / N)
    avg_gain = gain.ewm(alpha=1/rsi_p, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/rsi_p, adjust=False).mean()
    
    # Prevent division by zero errors
    rs = np.where(avg_loss == 0, np.nan, avg_gain / avg_loss)
    rsi_vals = np.where(avg_loss == 0, 100.0, 100.0 - (100.0 / (1.0 + rs)))
    rsi_vals = np.where((avg_gain == 0) & (avg_loss == 0), 50.0, rsi_vals)
    
    df[f"RSI_{rsi_p}"] = rsi_vals
    logger.debug(f"Calculated RSI with period={rsi_p}")
    
    # 3. Moving Average Convergence Divergence (MACD)
    macd_c = indicators.macd
    ema_fast = df['Close'].ewm(span=macd_c.fast, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=macd_c.slow, adjust=False).mean()
    
    df['MACD'] = ema_fast - ema_slow
    df['MACD_Signal'] = df['MACD'].ewm(span=macd_c.signal, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    logger.debug(f"Calculated MACD ({macd_c.fast}, {macd_c.slow}, {macd_c.signal})")
    
    # 4. Bollinger Bands
    bb = indicators.bollinger_bands
    bb_sma = df['Close'].rolling(window=bb.period).mean()
    bb_std = df['Close'].rolling(window=bb.period).std()
    
    df['BB_Middle'] = bb_sma
    df['BB_Upper'] = bb_sma + (bb.std_dev * bb_std)
    df['BB_Lower'] = bb_sma - (bb.std_dev * bb_std)
    logger.debug(f"Calculated Bollinger Bands (period={bb.period}, std={bb.std_dev})")
    
    # 5. Average True Range (ATR)
    atr_p = indicators.atr.period
    hl = df['High'] - df['Low']
    hc_prev = (df['High'] - df['Close'].shift(1)).abs()
    lc_prev = (df['Low'] - df['Close'].shift(1)).abs()
    
    tr = pd.concat([hl, hc_prev, lc_prev], axis=1).max(axis=1)
    df[f"ATR_{atr_p}"] = tr.ewm(alpha=1/atr_p, adjust=False).mean()
    logger.debug(f"Calculated ATR with period={atr_p}")
    
    # 6. Basic Price Returns
    df['Daily_Return'] = df['Close'].pct_change()
    df['Log_Return'] = np.log(df['Close'] / df['Close'].shift(1))
    logger.debug("Calculated Daily and Log Returns.")
    
    # Save the output CSV
    if output_filepath:
        features_filepath = Path(output_filepath)
        features_filepath.parent.mkdir(parents=True, exist_ok=True)
    else:
        features_dir = config.get_features_data_dir()
        features_dir.mkdir(parents=True, exist_ok=True)
        features_filepath = features_dir / "nsei_features.csv"
        
    df.to_csv(features_filepath, index=False)
    
    logger.info(f"Engineered feature dataset successfully saved to: {features_filepath}")
    return str(features_filepath)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python feature_engineer.py <cleaned_csv_path>")
        sys.exit(1)
    try:
        calculate_features(sys.argv[1])
    except Exception as e:
        logger.error(f"Feature engineering failed: {e}")
        sys.exit(1)
