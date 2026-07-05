from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("db_manager")

class DBManager:
    def __init__(self):
        self.config = load_global_config()
        self.db_path = self.config.get_db_path()
        # Ensure target database folder exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Setup SQLAlchemy engine (SQLite connection URL)
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        
    def init_db(self):
        """Initializes the database schema using schema.sql."""
        schema_path = Path(__file__).resolve().parent / "schema.sql"
        if not schema_path.exists():
            logger.error(f"Database schema file not found at: {schema_path}")
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
            
        logger.info(f"Reading database schema from {schema_path}...")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            
        with self.engine.begin() as conn:
            # Use the raw DBAPI connection to run executescript for schema definitions
            raw_conn = conn.connection
            raw_conn.executescript(schema_sql)
            
        logger.info("Database schema initialized successfully.")

    def save_prices(self, df: pd.DataFrame, symbol: str):
        """
        Saves NIFTY daily price data. If records exist for the same (date, symbol), 
        they are overwritten (idempotent / UPSERT logic).
        """
        df_db = df.copy()
        df_db['symbol'] = symbol
        
        # Rename columns to match schema columns
        df_db = df_db.rename(columns={
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume'
        })
        
        # Cast date to YYYY-MM-DD string
        if pd.api.types.is_datetime64_any_dtype(df_db['date']):
            df_db['date'] = df_db['date'].dt.strftime('%Y-%m-%d')
        else:
            df_db['date'] = df_db['date'].astype(str)
            
        # Select and order required columns
        db_cols = ['date', 'symbol', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
        df_db = df_db[db_cols]
        
        logger.info(f"Saving {len(df_db)} price entries for {symbol} to SQLite database...")
        
        # SQLite idempotent Insert/Replace statement
        upsert_query = """
        INSERT OR REPLACE INTO daily_prices (date, symbol, open, high, low, close, adj_close, volume)
        VALUES (:date, :symbol, :open, :high, :low, :close, :adj_close, :volume)
        """
        
        records = df_db.to_dict(orient='records')
        with self.engine.begin() as conn:
            conn.execute(text(upsert_query), records)
            
        logger.info("Price data saved successfully.")

    def save_version(self, version_id: str, symbol: str, file_path: Path, 
                     row_count: int, start_date: str, end_date: str, 
                     config_hash: str, file_hash: str, validation_status: str):
        """
        Inserts or replaces a dataset version manifest registry record.
        """
        logger.info(f"Saving dataset version registry for {version_id}...")
        
        upsert_query = """
        INSERT OR REPLACE INTO dataset_versions 
        (version_id, symbol, file_path, row_count, start_date, end_date, config_hash, file_hash, validation_status)
        VALUES 
        (:version_id, :symbol, :file_path, :row_count, :start_date, :end_date, :config_hash, :file_hash, :validation_status)
        """
        
        params = {
            "version_id": version_id,
            "symbol": symbol,
            "file_path": str(file_path),
            "row_count": row_count,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "config_hash": config_hash,
            "file_hash": file_hash,
            "validation_status": validation_status
        }
        
        with self.engine.begin() as conn:
            conn.execute(text(upsert_query), params)
            
        logger.info(f"Dataset version {version_id} registry saved.")
