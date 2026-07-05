import pandas as pd
import numpy as np
import pytest
from pathlib import Path
from src.data_pipeline.validator import run_validation

def test_validation_clean_data(tmp_path):
    """Verifies that clean data without anomalies successfully passes validation."""
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    df = pd.DataFrame({
        "Date": dates,
        "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
        "High": [105.0, 106.0, 107.0, 108.0, 109.0],
        "Low": [95.0, 96.0, 97.0, 98.0, 99.0],
        "Close": [102.0, 103.0, 104.0, 105.0, 106.0],
        "Adj Close": [102.0, 103.0, 104.0, 105.0, 106.0],
        "Volume": [1000, 1100, 1200, 1300, 1400]
    })
    
    csv_path = tmp_path / "mock_clean.csv"
    df.to_csv(csv_path, index=False)
    
    report = run_validation(str(csv_path))
    assert report["passed"] is True
    assert report["summary"]["status"] == "PASS"
    assert report["checks"]["duplicates"]["status"] == "PASS"
    assert report["checks"]["missing_values"]["status"] == "PASS"
    assert report["checks"]["ohlc_constraints"]["status"] == "PASS"
    assert report["checks"]["price_bounds"]["status"] == "PASS"
    assert report["checks"]["volume_bounds"]["status"] == "PASS"

def test_validation_corrupt_ohlcv_bounds(tmp_path):
    """Verifies that validation correctly fails and flags logical OHLC and Volume bounds errors."""
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    df = pd.DataFrame({
        "Date": dates,
        "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
        # Index 2: High (100) < Low (105)
        "High": [105.0, 106.0, 100.0, 108.0, 109.0],
        "Low": [95.0, 96.0, 105.0, 98.0, 99.0],
        "Close": [102.0, 103.0, 104.0, 105.0, 106.0],
        "Adj Close": [102.0, 103.0, 104.0, 105.0, 106.0],
        # Index 3: Negative volume
        "Volume": [1000, 1100, 1200, -500, 1400]
    })
    
    csv_path = tmp_path / "mock_corrupt.csv"
    df.to_csv(csv_path, index=False)
    
    report = run_validation(str(csv_path))
    assert report["passed"] is False
    assert report["summary"]["status"] == "FAIL"
    assert report["checks"]["ohlc_constraints"]["status"] == "FAIL"
    assert report["checks"]["volume_bounds"]["status"] == "FAIL"
    
    # Verify count details
    assert report["checks"]["ohlc_constraints"]["count"] == 5
    assert report["checks"]["volume_bounds"]["count"] == 1
