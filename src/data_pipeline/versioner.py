import sys
import json
import shutil
import hashlib
import time
import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config
from database.db_manager import DBManager

logger = get_logger("versioner")

def get_file_hash(filepath: Path) -> str:
    """Computes SHA-256 hash of a file for tracking changes."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def get_configs_hash(project_root: Path) -> str:
    """Computes a SHA-256 hash of all configuration settings."""
    hasher = hashlib.sha256()
    for filename in ["config.yaml", "indicators.yaml", "validation_rules.yaml"]:
        p = project_root / "config" / filename
        if p.exists():
            with open(p, 'rb') as f:
                hasher.update(f.read())
    return hasher.hexdigest()

def create_dataset_version(feature_filepath: str, validation_status: str = "PASS") -> str:
    """
    Snapshots the feature dataset into versions directory, generates checksums,
    writes manifest.json, and ingests price data + version info into the database.
    """
    logger.info("Starting dataset snapshot version control tracking...")
    config = load_global_config()
    project_root = Path(__file__).resolve().parent.parent.parent
    
    feature_path = Path(feature_filepath)
    if not feature_path.exists():
        err_msg = f"Feature dataset does not exist: {feature_filepath}"
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)
        
    try:
        df = pd.read_csv(feature_path)
    except Exception as e:
        logger.error(f"Failed to read feature CSV: {e}")
        raise e
        
    df['Date'] = pd.to_datetime(df['Date'])
    row_count = len(df)
    start_date = df['Date'].min().strftime('%Y-%m-%d')
    end_date = df['Date'].max().strftime('%Y-%m-%d')
    
    # Calculate hashes
    f_hash = get_file_hash(feature_path)
    c_hash = get_configs_hash(project_root)
    
    # Set Version ID prefix format: vYYYYMMDD_HHMMSS
    version_id = time.strftime("v%Y%m%d_%H%M%S")
    logger.info(f"Issuing new dataset version code: {version_id}")
    
    # Set directories
    version_dir = config.get_versions_dir() / version_id
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy dataset file
    shipped_path = version_dir / f"nsei_features_{version_id}.csv"
    shutil.copy(feature_path, shipped_path)
    logger.info(f"Dataset snapshot archived at: {shipped_path}")
    
    # Write manifest.json
    manifest = {
        "version_id": version_id,
        "symbol": config.ticker,
        "row_count": row_count,
        "start_date": start_date,
        "end_date": end_date,
        "config_hash": c_hash,
        "file_hash": f_hash,
        "validation_status": validation_status,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    manifest_path = version_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)
    logger.info(f"Manifest schema saved at: {manifest_path}")
    
    # database ingestion
    try:
        db = DBManager()
        db.init_db()  # Ensure tables exist
        
        # Save daily prices to database (idempotent / overwrite)
        db.save_prices(df, config.ticker)
        
        # Save version manifest registry to database
        db.save_version(
            version_id=version_id,
            symbol=config.ticker,
            file_path=shipped_path,
            row_count=row_count,
            start_date=start_date,
            end_date=end_date,
            config_hash=c_hash,
            file_hash=f_hash,
            validation_status=validation_status
        )
        logger.info("Database ingestion for version completed successfully.")
        
    except Exception as db_err:
        logger.error(f"Database ingestion failed during version logging: {db_err}")
        # Note: We do not fail the pipeline if DB logging fails, but we raise if critical.
        # For professional robust pipelines, let's raise if DB fails so that we fail loud.
        raise db_err
        
    return version_id

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python versioner.py <features_csv_path>")
        sys.exit(1)
    try:
        create_dataset_version(sys.argv[1])
    except Exception as e:
        logger.error(f"Versioning failed: {e}")
        sys.exit(1)
