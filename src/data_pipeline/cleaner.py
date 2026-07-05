import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config
from src.data_pipeline.validator import run_validation

logger = get_logger("cleaner")

def clean_data(raw_filepath: str) -> str:
    """
    Reads the raw stock prices data, executes validator checks, applies 
    pre-approved data corrections (deduplication, gap filling, and boundary corrections),
    logs each transformation, and saves the cleaned dataset.
    
    Escalates (fails loud) on critical errors that cannot be confidently cleaned automatically.
    """
    logger.info(f"Executing data cleaner pipeline on: {raw_filepath}")
    
    config = load_global_config()
    
    # Run validator check first
    report = run_validation(raw_filepath)
    
    # Check for empty dataset or critical error
    if not report.get("passed", False) and "error" in report:
        err = f"Validation failed immediately: {report['error']}"
        logger.error(err)
        raise ValueError(err)
        
    try:
        df = pd.read_csv(raw_filepath)
    except Exception as e:
        logger.error(f"Failed to load raw CSV: {e}")
        raise e
        
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    initial_rows = len(df)
    cleaning_log = []
    
    # 1. Handle Duplicates
    if report["checks"]["duplicates"]["status"] == "FAIL":
        # Drop exact duplicates
        dup_rows_cnt = df.duplicated().sum()
        if dup_rows_cnt > 0:
            df = df.drop_duplicates().reset_index(drop=True)
            cleaning_log.append({
                "stage": "duplicates",
                "action": "drop_duplicate_rows",
                "impact": f"Removed {dup_rows_cnt} exact duplicate rows"
            })
            logger.info(f"Dropped {dup_rows_cnt} duplicate rows.")
            
        # Drop duplicate dates (keeping first occurrence)
        dup_dates_cnt = df['Date'].duplicated().sum()
        if dup_dates_cnt > 0:
            dup_dates = df[df['Date'].duplicated()]['Date'].dt.strftime('%Y-%m-%d').tolist()
            df = df.drop_duplicates(subset=['Date'], keep='first').reset_index(drop=True)
            cleaning_log.append({
                "stage": "duplicates",
                "action": "drop_duplicate_dates",
                "impact": f"Removed {dup_dates_cnt} duplicate dates, keeping first occurrence",
                "details": {"duplicate_dates": dup_dates}
            })
            logger.warning(f"Removed {dup_dates_cnt} duplicate dates: {dup_dates}")

    # 2. Handle Missing Values (NaNs)
    if report["checks"]["missing_values"]["status"] == "FAIL":
        nulls = df.isnull().sum()
        cols_to_fill = [col for col, cnt in nulls.items() if cnt > 0]
        for col in cols_to_fill:
            missing_dates = df[df[col].isnull()]['Date'].dt.strftime('%Y-%m-%d').tolist()
            
            # Forward fill then backward fill
            df[col] = df[col].ffill().bfill()
            
            cleaning_log.append({
                "stage": "missing_values",
                "column": col,
                "action": "forward_fill_then_backward_fill",
                "impact": f"Filled {len(missing_dates)} null value(s)",
                "details": {"affected_dates": missing_dates}
            })
            logger.info(f"Filled missing value(s) in '{col}' on dates: {missing_dates}")

    # 3. Handle OHLC Constraint Violations
    if report["checks"]["ohlc_constraints"]["status"] == "FAIL":
        # Enforce High >= Low
        hl_violators = df['High'] < df['Low']
        if hl_violators.any():
            for idx in df[hl_violators].index:
                row = df.loc[idx]
                df.loc[idx, 'High'] = row['Low']
                cleaning_log.append({
                    "stage": "ohlc_constraints",
                    "date": row['Date'].strftime('%Y-%m-%d'),
                    "action": "adjust_high_to_low",
                    "before": {"High": float(row['High']), "Low": float(row['Low'])},
                    "after": {"High": float(row['Low']), "Low": float(row['Low'])}
                })
                logger.warning(f"Set High to Low on {row['Date'].strftime('%Y-%m-%d')}")
                
        # Enforce High >= Open
        ho_violators = df['High'] < df['Open']
        if ho_violators.any():
            for idx in df[ho_violators].index:
                row = df.loc[idx]
                df.loc[idx, 'High'] = row['Open']
                cleaning_log.append({
                    "stage": "ohlc_constraints",
                    "date": row['Date'].strftime('%Y-%m-%d'),
                    "action": "adjust_high_to_open",
                    "before": {"High": float(row['High']), "Open": float(row['Open'])},
                    "after": {"High": float(row['Open']), "Open": float(row['Open'])}
                })
                logger.warning(f"Set High to Open on {row['Date'].strftime('%Y-%m-%d')}")
                
        # Enforce High >= Close
        hc_violators = df['High'] < df['Close']
        if hc_violators.any():
            for idx in df[hc_violators].index:
                row = df.loc[idx]
                df.loc[idx, 'High'] = row['Close']
                cleaning_log.append({
                    "stage": "ohlc_constraints",
                    "date": row['Date'].strftime('%Y-%m-%d'),
                    "action": "adjust_high_to_close",
                    "before": {"High": float(row['High']), "Close": float(row['Close'])},
                    "after": {"High": float(row['Close']), "Close": float(row['Close'])}
                })
                logger.warning(f"Set High to Close on {row['Date'].strftime('%Y-%m-%d')}")
                
        # Enforce Low <= Open
        lo_violators = df['Low'] > df['Open']
        if lo_violators.any():
            for idx in df[lo_violators].index:
                row = df.loc[idx]
                df.loc[idx, 'Low'] = row['Open']
                cleaning_log.append({
                    "stage": "ohlc_constraints",
                    "date": row['Date'].strftime('%Y-%m-%d'),
                    "action": "adjust_low_to_open",
                    "before": {"Low": float(row['Low']), "Open": float(row['Open'])},
                    "after": {"Low": float(row['Open']), "Open": float(row['Open'])}
                })
                logger.warning(f"Set Low to Open on {row['Date'].strftime('%Y-%m-%d')}")
                
        # Enforce Low <= Close
        lc_violators = df['Low'] > df['Close']
        if lc_violators.any():
            for idx in df[lc_violators].index:
                row = df.loc[idx]
                df.loc[idx, 'Low'] = row['Close']
                cleaning_log.append({
                    "stage": "ohlc_constraints",
                    "date": row['Date'].strftime('%Y-%m-%d'),
                    "action": "adjust_low_to_close",
                    "before": {"Low": float(row['Low']), "Close": float(row['Close'])},
                    "after": {"Low": float(row['Close']), "Close": float(row['Close'])}
                })
                logger.warning(f"Set Low to Close on {row['Date'].strftime('%Y-%m-%d')}")

    # 4. Handle Price Bounds (prices <= 0)
    # Price <= 0 is a critical, uncorrectable logic error for indices. Fail loud.
    if report["checks"]["price_bounds"]["status"] == "FAIL":
        err_msg = "Critical pricing error: Negative or zero prices detected. cleaner.py cannot auto-correct this."
        logger.error(err_msg)
        raise ValueError(err_msg)

    # 5. Handle Volume Bounds
    if report["checks"]["volume_bounds"]["status"] == "FAIL":
        vol_violators = df['Volume'] < 0
        if vol_violators.any():
            for idx in df[vol_violators].index:
                row = df.loc[idx]
                df.loc[idx, 'Volume'] = 0
                cleaning_log.append({
                    "stage": "volume_bounds",
                    "date": row['Date'].strftime('%Y-%m-%d'),
                    "action": "adjust_negative_volume",
                    "before": {"Volume": int(row['Volume'])},
                    "after": {"Volume": 0}
                })
                logger.warning(f"Set negative volume to 0 on {row['Date'].strftime('%Y-%m-%d')}")

    # Save output clean dataset
    processed_dir = config.get_processed_data_dir()
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    clean_filepath = processed_dir / "nsei_clean.csv"
    df.to_csv(clean_filepath, index=False)
    
    # Save detailed cleaning audit trail to logs
    log_dir = processed_dir.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_filepath = log_dir / "cleaning_log.json"
    
    with open(log_filepath, "w", encoding="utf-8") as f:
        json.dump(cleaning_log, f, indent=4)
        
    logger.info(f"Preprocessed cleaned data saved at: {clean_filepath}")
    logger.info(f"Cleaning logs generated at: {log_filepath}")
    
    return str(clean_filepath)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python cleaner.py <raw_csv_path>")
        sys.exit(1)
    try:
        clean_data(sys.argv[1])
    except Exception as e:
        logger.error(f"Clean process failed: {e}")
        sys.exit(1)
