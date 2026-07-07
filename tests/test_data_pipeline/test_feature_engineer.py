import pandas as pd
import numpy as np
import pytest
from pathlib import Path
from src.data_pipeline.feature_engineer import calculate_features

def test_feature_engineering_indicators(tmp_path):
    """
    Verifies that the feature engineering module correctly generates 
    all requested columns and handles the math for technical indicators.
    """
    # Create simple series of 25 days to allow Bollinger Bands and SMA/EMA 20 computation
    dates = pd.date_range(start="2023-01-01", periods=25, freq="D")
    close_prices = 100.0 + 10.0 * np.sin(np.arange(25))
    df = pd.DataFrame({
        "Date": dates,
        "Open": close_prices,
        "High": close_prices + 2.0,
        "Low": close_prices - 2.0,
        "Close": close_prices,
        "Adj Close": close_prices,
        "Volume": [1000] * 25
    })
    
    csv_path = tmp_path / "mock_clean.csv"
    df.to_csv(csv_path, index=False)
    
    features_filepath = calculate_features(str(csv_path), output_filepath=str(tmp_path / "nsei_features.csv"))
    df_feat = pd.read_csv(features_filepath)
    
    # Assert columns exist
    expected_cols = [
        "SMA_20", "SMA_50", "SMA_200", 
        "EMA_20", "EMA_50", 
        "RSI_14", 
        "MACD", "MACD_Signal", "MACD_Hist",
        "BB_Middle", "BB_Upper", "BB_Lower",
        "ATR_14", 
        "Daily_Return", "Log_Return"
    ]
    
    for col in expected_cols:
        assert col in df_feat.columns, f"Indicator column {col} was not generated."
        
    # Verify shape
    assert len(df_feat) == 25
    
    # Verify Daily Return and Log Return mathematical definitions
    daily_ret = df_feat.loc[1, "Daily_Return"]
    log_ret = df_feat.loc[1, "Log_Return"]
    
    close_today = df_feat.loc[1, "Close"]
    close_yesterday = df_feat.loc[0, "Close"]
    
    expected_daily = (close_today - close_yesterday) / close_yesterday
    expected_log = np.log(close_today / close_yesterday)
    
    assert pytest.approx(daily_ret) == expected_daily
    assert pytest.approx(log_ret) == expected_log
