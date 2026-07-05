import sys
import time
import datetime
import pandas as pd
import yfinance as yf
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("downloader")

def download_data(retries: int = 3, backoff_factor: int = 2) -> str:
    """
    Downloads raw daily historical data from Yahoo Finance based on config.yaml parameters.
    Implements retry logic with exponential backoff and saves raw output with a timestamp.
    Returns the path to the saved raw CSV file.
    """
    config = load_global_config()
    ticker_symbol = config.ticker
    start_date = config.start_date
    end_date = config.end_date
    
    # Resolve end date to today if it is not specified
    if not end_date:
        end_date = datetime.datetime.today().strftime('%Y-%m-%d')
        
    logger.info(f"Initiating historical daily download for ticker '{ticker_symbol}'")
    logger.info(f"Request range: {start_date} to {end_date}")
    
    df = None
    delay = 1.0
    
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Download attempt {attempt}/{retries}...")
            
            # Fetch using yfinance download
            df = yf.download(ticker_symbol, start=start_date, end=end_date)
            
            if df.empty:
                raise ValueError(f"Empty DataFrame returned for ticker {ticker_symbol}")
                
            logger.info(f"Successfully downloaded {len(df)} rows.")
            break
            
        except Exception as e:
            logger.warning(f"Download attempt {attempt} failed with error: {e}")
            if attempt == retries:
                logger.error("Exceeded maximum retry attempts. Aborting download.")
                raise e
            
            logger.info(f"Waiting {delay} seconds before retry...")
            time.sleep(delay)
            delay *= backoff_factor

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        logger.info("Normalizing MultiIndex headers...")
        df.columns = [col[0] for col in df.columns]
        
    # Reset index to export Date as a column
    df = df.reset_index()
    
    # Normalize column casing (e.g., 'open' -> 'Open')
    df.columns = [col.title() if col.lower() != 'adj close' else 'Adj Close' for col in df.columns]
    
    # Ensure all required OHLCV columns exist
    required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [c for c in required if c not in df.columns]
    if missing:
        err_msg = f"Download results missing critical columns: {missing}"
        logger.error(err_msg)
        raise ValueError(err_msg)
        
    if 'Adj Close' not in df.columns and 'Close' in df.columns:
        df['Adj Close'] = df['Close']
        
    # Standardize column order
    ordered_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    df = df[ordered_cols]
    
    # Save raw file with unique execution timestamp (immutable raw storage)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_dir = config.get_raw_data_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    raw_filepath = raw_dir / f"nsei_raw_{timestamp}.csv"
    df.to_csv(raw_filepath, index=False)
    
    logger.info(f"Immutable raw file saved at: {raw_filepath}")
    return str(raw_filepath)

if __name__ == "__main__":
    try:
        download_data()
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)
