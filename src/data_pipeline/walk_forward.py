import os
import sys
import time
import hashlib
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config
from src.data_pipeline.feature_store import FEATURE_METADATA, FeatureStoreManager

logger = get_logger("walk_forward")

class WalkForwardSplitter:
    """
    Slices Training Datasets into walk-forward expanding folds, refitting scalers
    on training splits only, and asserting leakage boundaries strictly.
    """
    def __init__(self, anchor_start_year: int = 2014, fold_schedule: str = "expanding",
                 folds: List[Dict[str, Any]] = None, embargo_days: int = 0,
                 feature_store_version: int = 1, label_version: str = "threeclass",
                 persist_fold_artifacts: bool = True, output_dir: str = "data/walk_forward_runs"):
        self.anchor_start_year = anchor_start_year
        self.fold_schedule = fold_schedule.lower()
        self.folds = folds or []
        self.embargo_days = embargo_days
        self.feature_store_version = feature_store_version
        self.label_version = label_version.lower()
        self.persist_fold_artifacts = persist_fold_artifacts
        
        # Unique run ID tying together version variables
        self.run_id = f"fs_v{feature_store_version}_{self.label_version}_embargo{embargo_days}"
        self.output_dir = Path(output_dir) / self.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _compute_scaler_config_hash(self, columns: List[str]) -> str:
        """Computes a unique signature hash of the column-to-scaler mappings for traceability."""
        scaler_mapping = {}
        for col in columns:
            meta = FEATURE_METADATA.get(col, {})
            scaler_mapping[col] = meta.get("scaler_recommendation", "StandardScaler")
        
        serialized = str(sorted(scaler_mapping.items())).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def split_and_scale(self, training_dataset: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]]:
        """
        Executes slicing, train-split scaling, leakage asserts, and artifact persisting
        across all configured walk-forward folds.
        """
        logger.info(f"Initiating walk-forward splits. Total folds: {len(self.folds)}. Run ID: {self.run_id}")
        
        # Verify Date column datatype
        df = training_dataset.copy()
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        
        # Resolve target labels column
        label_col = "Label_Binary" if self.label_version == "binary" else "Label_ThreeClass"
        if label_col not in df.columns:
            raise KeyError(f"Target label column '{label_col}' not found in the Training Dataset.")
            
        feature_cols = [col for col in df.columns if col not in ["Date", label_col]]
        scaler_hash = self._compute_scaler_config_hash(feature_cols)
        
        folds_data = []
        validation_report = {
            "run_id": self.run_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_pass": True,
            "folds_status": {}
        }
        
        for idx, f_cfg in enumerate(self.folds):
            fold_id = idx + 1
            train_end_yr = f_cfg["train_end_year"]
            test_yr = f_cfg["test_year"]
            is_partial = f_cfg.get("partial", False)
            
            logger.info(f"Processing Fold {fold_id}: Train expanding up to {train_end_yr}, Test roll in {test_yr}")
            
            # Slicing ranges
            train_start = pd.to_datetime(f"{self.anchor_start_year}-01-01")
            train_end = pd.to_datetime(f"{train_end_yr}-12-31")
            
            # Apply calendar purge/embargo gap if configured
            if self.embargo_days > 0:
                train_end = train_end - pd.Timedelta(days=self.embargo_days)
                
            test_start = pd.to_datetime(f"{test_yr}-01-01")
            test_end = pd.to_datetime(f"{test_yr}-12-31")
            
            # Slice subsets
            train_df = df[(df["Date"] >= train_start) & (df["Date"] <= train_end)].copy().reset_index(drop=True)
            test_df = df[(df["Date"] >= test_start) & (df["Date"] <= test_end)].copy().reset_index(drop=True)
            
            # Execute assertions and diagnostics on unscaled slices first
            fold_errors = []
            
            # 1. Row count validations
            if train_df.empty:
                fold_errors.append("Training subset is empty.")
            if test_df.empty:
                fold_errors.append("Testing subset is empty.")
                
            # Skip operations if subset sizes are invalid to prevent scale crashes
            if fold_errors:
                validation_report["folds_status"][fold_id] = {"pass": False, "errors": fold_errors}
                validation_report["overall_pass"] = False
                logger.error(f"Fold {fold_id} failed validations: {fold_errors}")
                continue
                
            # 2. Strict Date intersection leakage check
            intersect_dates = set(train_df["Date"]).intersection(set(test_df["Date"]))
            if intersect_dates:
                fold_errors.append(f"Overlap detected: Train and Test share {len(intersect_dates)} overlapping sessions.")
                
            # 3. Boundary validation
            if train_df["Date"].max() >= (test_df["Date"].min() - pd.Timedelta(days=self.embargo_days)):
                fold_errors.append("Leakage alert: Training maximum date is overlapping with the embargo test start boundary.")
                
            # 4. Date uniqueness check
            if train_df["Date"].duplicated().any():
                fold_errors.append("Training subset contains duplicate date records.")
            if test_df["Date"].duplicated().any():
                fold_errors.append("Testing subset contains duplicate date records.")
                
            # 5. Label exclusion leakage assertion
            for col in feature_cols:
                if "Label" in col:
                    fold_errors.append(f"Leakage validation error: Target label column '{col}' is present among feature inputs.")
                    
            # Refit scalers strictly on training window only
            for col in feature_cols:
                meta = FEATURE_METADATA.get(col, {})
                rec = meta.get("scaler_recommendation", "StandardScaler")
                
                if rec == "StandardScaler":
                    scaler = StandardScaler()
                elif rec == "MinMaxScaler":
                    scaler = MinMaxScaler()
                elif rec == "RobustScaler":
                    scaler = RobustScaler()
                else:
                    # Skip none/unknown scaling recommendations
                    continue
                    
                # Fit model on training slice
                scaler.fit(train_df[[col]])
                
                # Transform train/test sets
                train_df[col] = scaler.transform(train_df[[col]])
                test_df[col] = scaler.transform(test_df[[col]])
                
            # 6. Post-scaling NaN checks
            for col in feature_cols:
                train_nans = train_df[col].isna().sum()
                test_nans = test_df[col].isna().sum()
                if train_nans > 0:
                    fold_errors.append(f"Feature column '{col}' contains {train_nans} NaNs post-scaling inside the training set.")
                if test_nans > 0:
                    fold_errors.append(f"Feature column '{col}' contains {test_nans} NaNs post-scaling inside the testing set.")
            
            # Record fold pass status
            is_pass = len(fold_errors) == 0
            validation_report["folds_status"][fold_id] = {
                "pass": is_pass,
                "errors": fold_errors,
                "train_rows": len(train_df),
                "test_rows": len(test_df)
            }
            if not is_pass:
                validation_report["overall_pass"] = False
                logger.error(f"Fold {fold_id} failed validation checks: {fold_errors}")
                raise ValueError(f"Walk-forward validation check failed for Fold {fold_id}: {fold_errors}")
                
            # Compile metadata
            metadata = {
                "fold_id": fold_id,
                "train_start": train_df["Date"].min().strftime("%Y-%m-%d"),
                "train_end": train_df["Date"].max().strftime("%Y-%m-%d"),
                "test_start": test_df["Date"].min().strftime("%Y-%m-%d"),
                "test_end": test_df["Date"].max().strftime("%Y-%m-%d"),
                "embargo_days": self.embargo_days,
                "is_partial_test_year": bool(is_partial),
                "train_row_count": len(train_df),
                "test_row_count": len(test_df),
                "feature_store_version": str(self.feature_store_version),
                "label_version": self.label_version,
                "scaler_config_hash": scaler_hash
            }
            
            # Persist fold files if enabled
            if self.persist_fold_artifacts:
                train_path = self.output_dir / f"fold_{fold_id}_train.parquet"
                test_path = self.output_dir / f"fold_{fold_id}_test.parquet"
                meta_path = self.output_dir / f"fold_{fold_id}_metadata.yaml"
                
                train_df.to_parquet(train_path, index=False)
                test_df.to_parquet(test_path, index=False)
                
                with open(meta_path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(metadata, f, default_flow_style=False)
                    
                logger.info(f"Persisted Fold {fold_id} artifacts at: {self.output_dir}")
                
            folds_data.append((train_df, test_df, metadata))
            
        # Write walk-forward validation summary report
        report_path = self.output_dir / "walk_forward_validation_report.yaml"
        with open(report_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(validation_report, f, default_flow_style=False)
            
        logger.info(f"Walk-forward split run validation report generated at: {report_path}")
        return folds_data

def run_walk_forward_splitter(config: dict) -> None:
    """Orchestrates loading features, requesting target labels, executing splitter, and writing audits."""
    logger.info("Initializing Walk-Forward Splitter pipeline...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Extract configs
    wf_config = config['eda']['walk_forward']
    fs_config = config['eda']['feature_store']
    le_config = config['eda']['label_engineering']
    
    anchor_yr = wf_config['anchor_start_year']
    schedule = wf_config['fold_schedule']
    folds = wf_config['folds']
    embargo = wf_config['embargo_days']
    fs_ver = wf_config['feature_store_version']
    label_ver = wf_config['label_version']
    persist = wf_config['persist_fold_artifacts']
    
    # Convert configuration models into standard dictionaries if needed
    processed_folds = []
    for f in folds:
        processed_folds.append({
            "train_end_year": f["train_end_year"],
            "test_year": f["test_year"],
            "partial": f.get("partial", False)
        })
        
    # Resolve folders
    store_dir = project_root / fs_config['output_dir']
    labels_dir = project_root / le_config['output_dir']
    runs_dir = project_root / "data/walk_forward_runs"
    
    # Instantiate FeatureStoreManager
    store_mgr = FeatureStoreManager(
        output_dir=str(store_dir),
        format_type=fs_config['format'],
        validation_level=fs_config['validation_level']
    )
    
    # Build downstream Training Dataset
    training_dataset = store_mgr.build_training_dataset(
        store_version=fs_ver,
        label_version=label_ver,
        labels_dir=str(labels_dir)
    )
    
    # Slicing and scaling
    splitter = WalkForwardSplitter(
        anchor_start_year=anchor_yr,
        fold_schedule=schedule,
        folds=processed_folds,
        embargo_days=embargo,
        feature_store_version=fs_ver,
        label_version=label_ver,
        persist_fold_artifacts=persist,
        output_dir=str(runs_dir)
    )
    
    splitter.split_and_scale(training_dataset)
    logger.info("Walk-Forward Splitting completed successfully.")

if __name__ == "__main__":
    try:
        global_config = load_global_config()
        run_walk_forward_splitter(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to execute walk-forward validation split: {e}", exc_info=True)
        sys.exit(1)
