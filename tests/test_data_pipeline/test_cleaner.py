import pandas as pd
import pytest
from pathlib import Path
from src.data_pipeline.cleaner import clean_data

def test_cleaner_corrections(tmp_path):
    """
    Verifies that cleaner module correctly handles duplicates, logical OHLC corrections,
    negative volumes, and missing value interpolation via forward fill.
    """
    # Create input with duplicates, high < low, negative volumes, and missing values
    dates = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-03", "2023-01-04"])
    df = pd.DataFrame({
        "Date": dates,
        "Open": [100.0, 101.0, 102.0, 102.0, 103.0],
        "High": [105.0, 106.0, 95.0, 95.0, 108.0],    # High (95) < Low (102) on Jan 3
        "Low": [95.0, 96.0, 102.0, 102.0, 97.0],
        "Close": [102.0, 103.0, 104.0, 104.0, None],   # Close is missing on Jan 4
        "Adj Close": [102.0, 103.0, 104.0, 104.0, 106.0],
        "Volume": [1000, 1100, -100, -100, 1300]       # Negative volume on Jan 3
    })
    
    csv_path = tmp_path / "mock_unclean.csv"
    df.to_csv(csv_path, index=False)
    
    # Execute cleaning
    clean_filepath = clean_data(str(csv_path), output_filepath=str(tmp_path / "nsei_clean.csv"))
    
    # Reload and assert modifications
    df_clean = pd.read_csv(clean_filepath)
    
    # 1. Exact duplicates dropped (size reduced from 5 to 4)
    assert len(df_clean) == 4
    
    # 2. Only single session for Jan 3 exists
    assert df_clean[df_clean['Date'] == '2023-01-03'].shape[0] == 1
    
    row_jan3 = df_clean[df_clean['Date'] == '2023-01-03'].iloc[0]
    
    # 3. High corrected to match Close (104.0) since Close was higher than Low (102.0)
    assert row_jan3['High'] == 104.0
    
    # 4. Negative volume replaced with 0
    assert row_jan3['Volume'] == 0
    
    # 5. Missing close value on Jan 4 filled from Jan 3 close (104.0) via ffill
    row_jan4 = df_clean[df_clean['Date'] == '2023-01-04'].iloc[0]
    assert row_jan4['Close'] == 104.0

def test_cleaner_fails_loud_on_zero_price(tmp_path):
    """Verifies that the cleaner fails loud and halts execution on critical pricing anomalies (<= 0)."""
    dates = pd.date_range(start="2023-01-01", periods=2, freq="D")
    df = pd.DataFrame({
        "Date": dates,
        "Open": [100.0, 0.0],  # Critical zero price value
        "High": [105.0, 106.0],
        "Low": [95.0, 96.0],
        "Close": [102.0, 103.0],
        "Adj Close": [102.0, 103.0],
        "Volume": [1000, 1100]
    })
    
    csv_path = tmp_path / "mock_zero_price.csv"
    df.to_csv(csv_path, index=False)
    
    with pytest.raises(ValueError, match="Critical pricing error"):
        clean_data(str(csv_path), output_filepath=str(tmp_path / "nsei_clean.csv"))
