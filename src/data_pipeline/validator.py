import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import pandas_market_calendars as mcal
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config, load_validation_rules

logger = get_logger("validator")

def run_validation(raw_filepath: str) -> Dict[str, Any]:
    """
    Validates the data integrity of a raw stock prices CSV file using
    the rules in config/validation_rules.yaml.
    Cross-checks trading days against the NSE holiday calendar (XNSE).
    Returns a structured validation result dictionary.
    """
    logger.info(f"Running data validation checks on: {raw_filepath}")
    
    # Load configurations
    global_config = load_global_config()
    rules = load_validation_rules()
    
    file_path = Path(raw_filepath)
    if not file_path.exists():
        err = f"Raw file not found: {raw_filepath}"
        logger.error(err)
        raise FileNotFoundError(err)
        
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Failed to load raw CSV file: {e}")
        raise e
        
    if df.empty:
        logger.error("Dataset is empty. Validation failed.")
        return {"passed": False, "error": "Empty dataset"}
        
    # Standardize Date column
    df['Date'] = pd.to_datetime(df['Date'])
    df_sorted = df.sort_values('Date').reset_index(drop=True)
    
    total_rows = len(df)
    issues_count = 0
    checks = {}
    
    # --- Check 1: Duplicate Dates / Rows ---
    duplicate_rows_cnt = df.duplicated().sum()
    duplicate_dates_cnt = df['Date'].duplicated().sum()
    
    dup_passed = (duplicate_rows_cnt == 0) and (duplicate_dates_cnt == 0)
    dup_details = []
    if duplicate_rows_cnt > 0:
        dup_details.append(f"Found {duplicate_rows_cnt} exact duplicate rows.")
    if duplicate_dates_cnt > 0:
        dup_details.append(f"Found {duplicate_dates_cnt} duplicate date stamps.")
        
    checks["duplicates"] = {
        "status": "PASS" if dup_passed else "FAIL",
        "count": int(duplicate_rows_cnt + duplicate_dates_cnt),
        "details": dup_details
    }
    if not dup_passed:
        issues_count += 1
        
    # --- Check 2: Missing Values (NaNs) ---
    null_counts = df.isnull().sum()
    total_nulls = null_counts.sum()
    null_details = {}
    for col, val in null_counts.items():
        if val > 0:
            null_details[col] = int(val)
            
    checks["missing_values"] = {
        "status": "PASS" if total_nulls == 0 else "FAIL",
        "count": int(total_nulls),
        "details": null_details
    }
    if total_nulls > 0:
        issues_count += 1
        
    # --- Check 3: OHLC Logical Relations ---
    ohlc = rules.ohlc_constraints
    ohlc_issues = []
    
    if ohlc.high_ge_low:
        h_lt_l = df[df['High'] < df['Low']]
        if not h_lt_l.empty:
            ohlc_issues.append({
                "rule": "High >= Low",
                "count": len(h_lt_l),
                "samples": h_lt_l['Date'].dt.strftime('%Y-%m-%d').head(3).tolist()
            })
            
    if ohlc.high_ge_open:
        h_lt_o = df[df['High'] < df['Open']]
        if not h_lt_o.empty:
            ohlc_issues.append({
                "rule": "High >= Open",
                "count": len(h_lt_o),
                "samples": h_lt_o['Date'].dt.strftime('%Y-%m-%d').head(3).tolist()
            })
            
    if ohlc.high_ge_close:
        h_lt_c = df[df['High'] < df['Close']]
        if not h_lt_c.empty:
            ohlc_issues.append({
                "rule": "High >= Close",
                "count": len(h_lt_c),
                "samples": h_lt_c['Date'].dt.strftime('%Y-%m-%d').head(3).tolist()
            })
            
    if ohlc.low_le_open:
        l_gt_o = df[df['Low'] > df['Open']]
        if not l_gt_o.empty:
            ohlc_issues.append({
                "rule": "Low <= Open",
                "count": len(l_gt_o),
                "samples": l_gt_o['Date'].dt.strftime('%Y-%m-%d').head(3).tolist()
            })
            
    if ohlc.low_le_close:
        l_gt_c = df[df['Low'] > df['Close']]
        if not l_gt_c.empty:
            ohlc_issues.append({
                "rule": "Low <= Close",
                "count": len(l_gt_c),
                "samples": l_gt_c['Date'].dt.strftime('%Y-%m-%d').head(3).tolist()
            })
            
    checks["ohlc_constraints"] = {
        "status": "PASS" if len(ohlc_issues) == 0 else "FAIL",
        "count": sum([x['count'] for x in ohlc_issues]),
        "details": ohlc_issues
    }
    if len(ohlc_issues) > 0:
        issues_count += 1
        
    # --- Check 4: Price Bounds ---
    price_issues = []
    for col in rules.price_columns:
        if col in df.columns:
            invalid_prices = df[df[col] <= 0]
            if not invalid_prices.empty:
                price_issues.append({
                    "column": col,
                    "count": len(invalid_prices),
                    "samples": invalid_prices['Date'].dt.strftime('%Y-%m-%d').head(3).tolist()
                })
                
    checks["price_bounds"] = {
        "status": "PASS" if len(price_issues) == 0 else "FAIL",
        "count": sum([x['count'] for x in price_issues]),
        "details": price_issues
    }
    if len(price_issues) > 0:
        issues_count += 1
        
    # --- Check 5: Volume Bounds ---
    vol_col = rules.volume_column
    vol_issues_cnt = 0
    vol_samples = []
    if vol_col in df.columns:
        invalid_vols = df[df[vol_col] < 0]
        if not invalid_vols.empty:
            vol_issues_cnt = len(invalid_vols)
            vol_samples = invalid_vols['Date'].dt.strftime('%Y-%m-%d').head(3).tolist()
            
    checks["volume_bounds"] = {
        "status": "PASS" if vol_issues_cnt == 0 else "FAIL",
        "count": vol_issues_cnt,
        "details": vol_samples
    }
    if vol_issues_cnt > 0:
        issues_count += 1
        
    # --- Check 6: Missing Dates (Exchange holiday check) ---
    missing_dates_list = []
    try:
        # Load the National Stock Exchange of India (XNSE) calendar schedule
        nse_cal = mcal.get_calendar('XNSE')
        start_dt = df_sorted['Date'].min()
        end_dt = df_sorted['Date'].max()
        
        # Fetch expected calendar days from market calendar schedule
        schedule = nse_cal.schedule(start_date=start_dt, end_date=end_dt)
        expected_dates = schedule.index.tz_localize(None).normalize()
        
        actual_dates = df_sorted['Date'].dt.normalize()
        
        # Check expected dates that are missing in actual trading dates
        missing_dts = expected_dates[~expected_dates.isin(actual_dates)]
        missing_dates_list = missing_dts.strftime('%Y-%m-%d').tolist()
        
    except Exception as calendar_error:
        logger.warning(f"Could not check calendar holidays using pandas-market-calendars: {calendar_error}")
        
    # We label missing dates as a WARNING rather than pipeline blocking FAIL
    checks["missing_dates"] = {
        "status": "PASS" if len(missing_dates_list) == 0 else "WARNING",
        "count": len(missing_dates_list),
        "details": missing_dates_list
    }
    
    # Overall pipeline gate status: True only if no FAIL checks exist.
    # WARNING checks (like missing dates) do not block pipeline continuation.
    passed = all([c["status"] in ["PASS", "WARNING"] for c in checks.values()])
    
    validation_report = {
        "passed": passed,
        "summary": {
            "total_rows": total_rows,
            "issues_count": issues_count,
            "status": "PASS" if passed else "FAIL"
        },
        "checks": checks
    }
    
    # Save the report as a JSON audit log
    log_dir = Path(global_config.get_processed_data_dir()).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    report_file = log_dir / "latest_validation_report.json"
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, indent=4)
        
    logger.info(f"Validation finished. Result: {validation_report['summary']['status']}. Report saved to {report_file}")
    return validation_report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python validator.py <raw_csv_path>")
        sys.exit(1)
    run_validation(sys.argv[1])
