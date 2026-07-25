import os
import time
import hashlib
import yaml
from pathlib import Path
from typing import Tuple, Dict, Any, List
import pandas as pd
import numpy as np

from src.utils.logger import get_logger

logger = get_logger("feature_store")

# Metadata mapping of all engineered features based on Phase 2
FEATURE_METADATA = {
    "Open": {
        "name": "Open", "source": "raw", "feature_group": "structural",
        "formula": "raw passthrough", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": None, "units": "INR", "nullability": "Non-nullable"
    },
    "High": {
        "name": "High", "source": "raw", "feature_group": "structural",
        "formula": "raw passthrough", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": None, "units": "INR", "nullability": "Non-nullable"
    },
    "Low": {
        "name": "Low", "source": "raw", "feature_group": "structural",
        "formula": "raw passthrough", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": None, "units": "INR", "nullability": "Non-nullable"
    },
    "Close": {
        "name": "Close", "source": "raw", "feature_group": "structural",
        "formula": "raw passthrough", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": None, "units": "INR", "nullability": "Non-nullable"
    },
    "Adj Close": {
        "name": "Adj Close", "source": "raw", "feature_group": "structural",
        "formula": "raw passthrough", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": None, "units": "INR", "nullability": "Non-nullable"
    },
    "Volume": {
        "name": "Volume", "source": "raw", "feature_group": "structural",
        "formula": "raw passthrough", "dtype": "int64", "scaler_recommendation": "RobustScaler",
        "lag": 0, "rolling_window": None, "units": "index points", "nullability": "Non-nullable, zero-inflation present 2007-2013"
    },
    "SMA_20": {
        "name": "SMA_20", "source": "derived", "feature_group": "indicator",
        "formula": "20-day Simple Moving Average", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": 20, "units": "INR", "nullability": "Nullable during warm-up (first 19 rows)"
    },
    "SMA_50": {
        "name": "SMA_50", "source": "derived", "feature_group": "indicator",
        "formula": "50-day Simple Moving Average", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": 50, "units": "INR", "nullability": "Nullable during warm-up (first 49 rows)"
    },
    "SMA_200": {
        "name": "SMA_200", "source": "derived", "feature_group": "indicator",
        "formula": "200-day Simple Moving Average", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": 200, "units": "INR", "nullability": "Nullable during warm-up (first 199 rows)"
    },
    "EMA_20": {
        "name": "EMA_20", "source": "derived", "feature_group": "indicator",
        "formula": "20-day Exponential Moving Average", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": 20, "units": "INR", "nullability": "Nullable during warm-up (first 19 rows)"
    },
    "EMA_50": {
        "name": "EMA_50", "source": "derived", "feature_group": "indicator",
        "formula": "50-day Exponential Moving Average", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": 50, "units": "INR", "nullability": "Nullable during warm-up (first 49 rows)"
    },
    "EMA_200": {
        "name": "EMA_200", "source": "derived", "feature_group": "indicator",
        "formula": "200-day Exponential Moving Average", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": 200, "units": "INR", "nullability": "Nullable during warm-up (first 199 rows)"
    },
    "RSI_14": {
        "name": "RSI_14", "source": "derived", "feature_group": "indicator",
        "formula": "14-day Relative Strength Index", "dtype": "float64", "scaler_recommendation": "MinMaxScaler",
        "lag": 0, "rolling_window": 14, "units": "dimensionless", "nullability": "Nullable during warm-up (first 1 row), artifact 100.0 first 13 rows"
    },
    "MACD": {
        "name": "MACD", "source": "derived", "feature_group": "indicator",
        "formula": "EMA_12 - EMA_26", "dtype": "float64", "scaler_recommendation": "RobustScaler",
        "lag": 0, "rolling_window": 26, "units": "dimensionless", "nullability": "Nullable during warm-up (first 25 rows)"
    },
    "MACD_Signal": {
        "name": "MACD_Signal", "source": "derived", "feature_group": "indicator",
        "formula": "9-day EMA of MACD", "dtype": "float64", "scaler_recommendation": "RobustScaler",
        "lag": 0, "rolling_window": 9, "units": "dimensionless", "nullability": "Nullable during warm-up (first 33 rows)"
    },
    "MACD_Hist": {
        "name": "MACD_Hist", "source": "derived", "feature_group": "indicator",
        "formula": "MACD - MACD_Signal", "dtype": "float64", "scaler_recommendation": "RobustScaler",
        "lag": 0, "rolling_window": 9, "units": "dimensionless", "nullability": "Nullable during warm-up (first 33 rows)"
    },
    "BB_Middle": {
        "name": "BB_Middle", "source": "derived", "feature_group": "indicator",
        "formula": "20-day Simple Moving Average", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": 20, "units": "INR", "nullability": "Nullable during warm-up (first 19 rows)"
    },
    "BB_Upper": {
        "name": "BB_Upper", "source": "derived", "feature_group": "indicator",
        "formula": "BB_Middle + (2 * 20-day standard deviation)", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": 20, "units": "INR", "nullability": "Nullable during warm-up (first 19 rows)"
    },
    "BB_Lower": {
        "name": "BB_Lower", "source": "derived", "feature_group": "indicator",
        "formula": "BB_Middle - (2 * 20-day standard deviation)", "dtype": "float64", "scaler_recommendation": "StandardScaler",
        "lag": 0, "rolling_window": 20, "units": "INR", "nullability": "Nullable during warm-up (first 19 rows)"
    },
    "ATR_14": {
        "name": "ATR_14", "source": "derived", "feature_group": "indicator",
        "formula": "14-day Average True Range", "dtype": "float64", "scaler_recommendation": "RobustScaler",
        "lag": 0, "rolling_window": 14, "units": "INR", "nullability": "Nullable during warm-up (first 14 rows)"
    },
    "Daily_Return": {
        "name": "Daily_Return", "source": "derived", "feature_group": "derived",
        "formula": "(Close_t - Close_{t-1}) / Close_{t-1}", "dtype": "float64", "scaler_recommendation": "RobustScaler",
        "lag": 1, "rolling_window": None, "units": "%", "nullability": "Nullable during warm-up (first 1 row)"
    },
    "Log_Return": {
        "name": "Log_Return", "source": "derived", "feature_group": "derived",
        "formula": "ln(Close_t / Close_{t-1})", "dtype": "float64", "scaler_recommendation": "RobustScaler",
        "lag": 1, "rolling_window": None, "units": "%", "nullability": "Nullable during warm-up (first 1 row)"
    }
}

class FeatureStoreManager:
    """
    Manages building, validating, and loading the canonical model-agnostic Feature Store.
    Supports downstream Training Dataset building (scaling, log1p, label merging).
    """
    def __init__(self, output_dir: str = "data/feature_store", format_type: str = "parquet",
                 validation_level: str = "warn_non_critical"):
        self.output_dir = Path(output_dir)
        self.format_type = format_type.lower()
        self.validation_level = validation_level.lower()
        
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _compute_schema_checksum(self, columns: List[str]) -> str:
        """Computes a unique SHA-256 hash checksum of the schema columns."""
        sorted_cols = sorted(columns)
        serialized = ",".join(sorted_cols).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def build_feature_store(self, features_csv_path: str, version: int = 1) -> Tuple[str, str]:
        """
        Processes features CSV, extracts canonical features, runs validation passes,
        and saves store files (Parquet/CSV, manifest, validation report).
        """
        logger.info(f"Building Feature Store v{version} from: {features_csv_path}")
        df = pd.read_csv(features_csv_path)
        
        # Verify Date column is present and parse it
        if "Date" not in df.columns:
            raise KeyError("Feature dataset must contain a 'Date' column acting as primary key.")
            
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        
        # Ensure we drop any downstream label columns if they mistakenly crept in
        exclude_labels = ["Label_Binary", "Label_ThreeClass"]
        df_store = df.drop(columns=[col for col in exclude_labels if col in df.columns])
        
        # Filter strictly for Date + metadata features
        target_columns = ["Date"] + list(FEATURE_METADATA.keys())
        missing_from_source = [col for col in target_columns if col not in df_store.columns]
        if missing_from_source:
            raise KeyError(f"The source dataset is missing required feature store columns: {missing_from_source}")
            
        df_store = df_store[target_columns]
        
        # Convert dtypes based on schema specification
        for col, meta in FEATURE_METADATA.items():
            if meta["dtype"] == "int64":
                # Cast to int64, handling float NaN conversion if needed
                df_store[col] = df_store[col].fillna(0).astype(np.int64)
            elif meta["dtype"] == "float64":
                df_store[col] = df_store[col].astype(np.float64)
                
        # Determine store filenames
        ext = "parquet" if self.format_type == "parquet" else "csv"
        store_filename = f"feature_store_v{version}.{ext}"
        store_path = self.output_dir / store_filename
        
        # Save canonical dataset
        if ext == "parquet":
            df_store.to_parquet(store_path, engine="pyarrow", index=False)
        else:
            df_store.to_csv(store_path, index=False)
        logger.info(f"Feature Store dataset written to: {store_path}")
        
        # Perform validation checks
        validation_report, schema_checksum = self._validate_store(df_store, features_csv_path)
        
        # Save validation report
        val_report_path = self.output_dir / f"feature_store_v{version}_validation_report.yaml"
        with open(val_report_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(validation_report, f, default_flow_style=False)
            
        # Compile manifest sidecar
        manifest = {
            "version": version,
            "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": features_csv_path,
            "source_hash": self._compute_file_hash(features_csv_path),
            "row_count": len(df_store),
            "start_date": df_store["Date"].min().strftime("%Y-%m-%d"),
            "end_date": df_store["Date"].max().strftime("%Y-%m-%d"),
            "schema_checksum": schema_checksum,
            "features": FEATURE_METADATA
        }
        
        manifest_path = self.output_dir / f"feature_store_v{version}_manifest.yaml"
        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(manifest, f, default_flow_style=False)
            
        logger.info(f"Manifest written to: {manifest_path}")
        logger.info(f"Validation report written to: {val_report_path}")
        
        # Handle validation check fails
        if not validation_report["overall_pass"]:
            msg = f"Feature Store v{version} validation failed! Details in {val_report_path}"
            if self.validation_level == "hard_fail":
                raise ValueError(msg)
            else:
                logger.warning(msg)
                
        return str(store_path), str(manifest_path)

    def _compute_file_hash(self, filepath: str) -> str:
        """Computes SHA-256 hash of a file for checksum integrity validation."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    def _validate_store(self, df: pd.DataFrame, source_path: str) -> Tuple[Dict[str, Any], str]:
        """Runs the validation checks to verify schema integrity and datatypes."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source_path": source_path,
            "schema_integrity": True,
            "datatype_match": True,
            "duplicate_dates": False,
            "missing_column_check": True,
            "expected_row_count": True,
            "null_check": True,
            "null_summary": {},
            "errors": [],
            "overall_pass": True
        }
        
        # 1. Duplicate dates check
        duplicates = df["Date"].duplicated().sum()
        if duplicates > 0:
            report["duplicate_dates"] = True
            report["errors"].append(f"Detected {duplicates} duplicate date entries.")
            report["overall_pass"] = False
            
        # 2. Schema integrity (manifest column count)
        expected_cols = ["Date"] + list(FEATURE_METADATA.keys())
        if len(df.columns) != len(expected_cols):
            report["schema_integrity"] = False
            report["errors"].append(f"Column count mismatch. Expected {len(expected_cols)}, found {len(df.columns)}")
            report["overall_pass"] = False
            
        # 3. Datatype and column presence check
        for col in df.columns:
            if col == "Date":
                continue
            if col not in FEATURE_METADATA:
                report["missing_column_check"] = False
                report["errors"].append(f"Undocumented column in store: {col}")
                report["overall_pass"] = False
                continue
                
            expected_dtype = FEATURE_METADATA[col]["dtype"]
            actual_dtype = str(df[col].dtype)
            
            # Simple mapping check
            is_match = False
            if expected_dtype == "float64" and "float" in actual_dtype:
                is_match = True
            elif expected_dtype == "int64" and ("int" in actual_dtype or "long" in actual_dtype):
                is_match = True
                
            if not is_match:
                report["datatype_match"] = False
                report["errors"].append(f"Column {col} datatype mismatch. Expected {expected_dtype}, found {actual_dtype}")
                report["overall_pass"] = False

        # 4. Null checks (specifically post-2014 checks where warm-up nulls are expected to be 0)
        df_post_2014 = df[df["Date"] >= "2014-01-01"]
        for col in FEATURE_METADATA.keys():
            nulls = df_post_2014[col].isna().sum()
            report["null_summary"][col] = int(nulls)
            
            # Post-2014 features should have zero null values
            if nulls > 0:
                report["null_check"] = False
                report["errors"].append(f"Column {col} has {nulls} unexpected missing values post-2014.")
                report["overall_pass"] = False
                
        checksum = self._compute_schema_checksum(df.columns.tolist())
        return report, checksum

    def load_feature_store(self, version: int = 1) -> pd.DataFrame:
        """Loads canonical features from Parquet/CSV store on disk."""
        ext = "parquet" if self.format_type == "parquet" else "csv"
        store_path = self.output_dir / f"feature_store_v{version}.{ext}"
        
        if not store_path.exists():
            raise FileNotFoundError(f"Feature Store version {version} not found at: {store_path}")
            
        if ext == "parquet":
            df = pd.read_parquet(store_path)
        else:
            df = pd.read_csv(store_path)
            df["Date"] = pd.to_datetime(df["Date"])
            
        return df

    def build_training_dataset(self, store_version: int = 1,
                               label_version: str = "threeclass",
                               labels_dir: str = "data/labels") -> pd.DataFrame:
        """
        Builds the final downstream model-specific Training Dataset:
        1. Loads features from Feature Store.
        2. Merges labeled targets.
        3. Transforms Volume via log1p.
        4. Assures lookahead-leakage compliance (verifies no labels are in features).
        """
        df_features = self.load_feature_store(store_version)
        
        # Resolve target files
        labels_path = Path(labels_dir)
        if label_version.lower() == "binary":
            lbl_file = labels_path / "nifty_labels_v1_binary.csv"
            lbl_col = "Label_Binary"
        elif label_version.lower() == "threeclass":
            lbl_file = labels_path / "nifty_labels_v2_threeclass.csv"
            lbl_col = "Label_ThreeClass"
        else:
            raise ValueError(f"Unknown label version requested: {label_version}")
            
        if not lbl_file.exists():
            raise FileNotFoundError(f"Label dataset file not found at: {lbl_file}. Please engineer labels first.")
            
        df_labels = pd.read_csv(lbl_file)
        df_labels["Date"] = pd.to_datetime(df_labels["Date"])
        
        # Merge on Date (Ensure only columns Date and the target label are merged)
        df_labels_slice = df_labels[["Date", lbl_col]]
        df_merged = df_features.merge(df_labels_slice, on="Date", how="inner")
        
        # Apply log1p(Volume) transform as specified downstream
        df_merged["Volume"] = np.log1p(df_merged["Volume"])
        
        # Strict hard validation check: assure target labels are never in inputs
        feature_cols = [c for c in df_merged.columns if c not in ["Date", lbl_col]]
        for col in feature_cols:
            if "Label" in col:
                raise ValueError(f"Leakage validation error: Target label column '{col}' is present among feature inputs!")
                
        logger.info(f"Built training dataset version: {label_version}. Total rows: {len(df_merged)}")
        return df_merged
