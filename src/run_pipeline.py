import sys
from src.utils.logger import get_logger
from src.data_pipeline.downloader import download_data
from src.data_pipeline.cleaner import clean_data
from src.data_pipeline.feature_engineer import calculate_features
from src.data_pipeline.versioner import create_dataset_version
from src.reports.validation_report import generate_report

logger = get_logger("pipeline_orchestrator")

def run_pipeline():
    """
    Orchestrates the entire historical market data pipeline:
    1. Downloads raw data with retry logic.
    2. Runs validator and cleaner to enforce integrity constraints.
    3. Calculates technical features dynamically.
    4. Versions dataset snapshot and ingests prices + log to database.
    5. Compiles human-readable Markdown validation and audit reports.
    """
    logger.info("=========================================")
    logger.info("Starting QuantEngine End-to-End Pipeline")
    logger.info("=========================================")
    
    try:
        # Step 1: Download raw yfinance daily data
        raw_filepath = download_data()
        
        # Step 2: Clean and validate raw data
        clean_filepath = clean_data(raw_filepath)
        
        # Step 3: Engineer technical indicator features
        features_filepath = calculate_features(clean_filepath)
        
        # Step 4: Archive and register dataset version (triggers DB ingestion)
        version_id = create_dataset_version(features_filepath, validation_status="PASS")
        
        # Step 5: Render validation summary report
        report_filepath = generate_report(version_id)
        
        logger.info("=========================================")
        logger.info(f"Pipeline executed successfully! Version: {version_id}")
        logger.info(f"Audit report saved at: {report_filepath}")
        logger.info("=========================================")
        
    except Exception as e:
        logger.error(f"Pipeline execution aborted due to error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()
