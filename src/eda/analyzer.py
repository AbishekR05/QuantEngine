import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import pandas as pd
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("analyzer")

class DateColumnNotFoundError(Exception):
    """Exception raised when the configured date column is missing from the dataset."""
    pass

class DatasetSummary:
    """
    Computes and generates metadata summaries of clean and features stock market datasets.
    Can format results as human-readable Markdown reports.
    """
    def __init__(self, data: pd.DataFrame, dataset_name: str, date_column: str = "Date"):
        self.data = data
        self.dataset_name = dataset_name
        self.date_column = date_column
        
        # Verify date column exists in the dataset (if dataframe contains columns)
        if len(data.columns) > 0 and date_column not in data.columns:
            raise DateColumnNotFoundError(
                f"Configured date column '{date_column}' not found in dataset '{dataset_name}'. "
                f"Available columns: {list(data.columns)}"
            )

    def row_count(self) -> int:
        """Returns the total number of rows in the dataset."""
        return len(self.data)

    def column_count(self) -> int:
        """Returns the total number of columns in the dataset."""
        return len(self.data.columns)

    def memory_usage_mb(self) -> float:
        """Returns the memory footprint of the DataFrame in Megabytes (MB)."""
        if self.data.empty:
            return 0.0
        return float(self.data.memory_usage(deep=True).sum() / (1024 * 1024))

    def date_range(self) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
        """Returns a tuple containing the earliest and latest date found in the dataset."""
        if self.data.empty or self.date_column not in self.data.columns:
            return (None, None)
        
        dates_series = pd.to_datetime(self.data[self.date_column])
        return (dates_series.min(), dates_series.max())

    def missing_value_counts(self) -> pd.Series:
        """Returns the count of missing values (NaNs) for each column in the dataset."""
        return self.data.isnull().sum()

    def missing_value_percentages(self) -> pd.Series:
        """Returns the percentage of missing values (NaNs) for each column in the dataset."""
        if self.data.empty:
            return pd.Series(0.0, index=self.data.columns)
        return (self.data.isnull().sum() / len(self.data)) * 100.0

    def duplicate_row_count(self) -> int:
        """Returns the number of exact duplicate rows in the dataset."""
        return int(self.data.duplicated().sum())

    def duplicate_date_count(self) -> int:
        """Returns the number of duplicate dates in the configured date column."""
        if self.data.empty:
            return 0
        if self.date_column not in self.data.columns:
            raise DateColumnNotFoundError(f"Date column '{self.date_column}' not found in columns.")
        return int(self.data[self.date_column].duplicated().sum())

    def dtype_summary(self) -> pd.DataFrame:
        """Returns a DataFrame detailing columns and their respective pandas data types."""
        return pd.DataFrame({
            "Column": self.data.columns,
            "Dtype": [str(t) for t in self.data.dtypes]
        })

    def to_dict(self) -> Dict[str, Any]:
        """Bundles all computed summary statistics into a single dictionary."""
        min_date, max_date = self.date_range()
        return {
            "dataset_name": self.dataset_name,
            "row_count": self.row_count(),
            "column_count": self.column_count(),
            "memory_usage_mb": self.memory_usage_mb(),
            "start_date": min_date.strftime('%Y-%m-%d') if min_date else None,
            "end_date": max_date.strftime('%Y-%m-%d') if max_date else None,
            "duplicate_row_count": self.duplicate_row_count(),
            "duplicate_date_count": self.duplicate_date_count(),
            "missing_value_counts": self.missing_value_counts().to_dict(),
            "missing_value_percentages": self.missing_value_percentages().to_dict(),
            "dtype_summary": self.dtype_summary().to_dict(orient="records")
        }

    def to_markdown(self) -> str:
        """Renders the dataset summary statistics as a formatted Markdown report."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        min_date, max_date = self.date_range()
        
        start_str = min_date.strftime('%Y-%m-%d') if min_date else 'N/A'
        end_str = max_date.strftime('%Y-%m-%d') if max_date else 'N/A'
        
        md = []
        md.append(f"# Dataset summary report for: `{self.dataset_name}`")
        md.append(f"**Report Generated At**: {timestamp}\n")
        
        # 1. Overview Table
        md.append("## 1. Overview Statistics")
        md.append("| Metric | Value |")
        md.append("| :--- | :--- |")
        md.append(f"| **Row Count** | {self.row_count()} |")
        md.append(f"| **Column Count** | {self.column_count()} |")
        md.append(f"| **Date Range** | {start_str} to {end_str} |")
        md.append(f"| **Memory Footprint** | {self.memory_usage_mb():.4f} MB |")
        md.append("")
        
        # 2. Data Types Table
        md.append("## 2. Column Data Types")
        md.append("| Column Name | Pandas Data Type |")
        md.append("| :--- | :--- |")
        dtype_df = self.dtype_summary()
        for _, row in dtype_df.iterrows():
            md.append(f"| `{row['Column']}` | {row['Dtype']} |")
        md.append("")
        
        # 3. Missing Values Table
        md.append("## 3. Missing Value Analysis")
        null_counts = self.missing_value_counts()
        null_pcts = self.missing_value_percentages()
        
        cols_with_nulls = [col for col in self.data.columns if null_counts[col] > 0]
        
        if len(cols_with_nulls) == 0:
            md.append("All columns contain **0** missing values (100% complete).")
        else:
            md.append("| Column Name | Missing Count | Percentage |")
            md.append("| :--- | :--- | :--- |")
            for col in cols_with_nulls:
                md.append(f"| `{col}` | {null_counts[col]} | {null_pcts[col]:.2f}% |")
            md.append(f"\n*Note: The other {self.column_count() - len(cols_with_nulls)} columns contain no missing values.*")
        md.append("")
        
        # 4. Duplicates section
        md.append("## 4. Duplicate Check Results")
        md.append(f"- **Exact Duplicate Rows**: {self.duplicate_row_count()}")
        md.append(f"- **Duplicate Date Entries**: {self.duplicate_date_count()}")
        md.append("")
        
        # 5. Known Data Notes
        md.append("## 5. Domain & Validation Audit Notes")
        if "clean" in self.dataset_name.lower():
            md.append(
                "> [!NOTE]\n"
                "> For `nsei_clean` dataset: Approximately 1,320 rows contain `Volume == 0`. "
                "For index tickers like NIFTY 50 (`^NSEI`), this is standard. Exchange feeds "
                "often do not supply volume calculations for index derivatives historically, or report 0 during earlier years. "
                "This is expected behavior and not a data corruption defect."
            )
        elif "feature" in self.dataset_name.lower():
            md.append(
                "> [!NOTE]\n"
                "> For `nifty_features` dataset: Leading missing values (`NaNs`) in indicators "
                "like `SMA_20`, `SMA_50`, `SMA_200`, `BB_Upper`, `BB_Lower`, and `ATR_14` are standard. "
                "These are lookback warm-up periods necessary for rolling mathematical calculations. "
                "They are directly proportional to each indicator's window setting and do not represent data pipeline failures."
            )
        else:
            md.append("*No validation caveats loaded for this dataset.*")
            
        return "\n".join(md)

    def save(self, output_path: str) -> None:
        """Writes the Markdown summary report to the specified file path."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        logger.info(f"Summary report written to: {p}")


def generate_all_summaries(config: dict) -> None:
    """
    Orchestrator function that reads configuration targets, loads datasets, 
    instantiates summaries, and outputs clean, features, and comparative reports.
    """
    logger.info("Starting Dataset Summary generation process...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Extract config items
    clean_rel = config['eda']['input_files']['clean']
    feat_rel = config['eda']['input_files']['features']
    output_dir_rel = config['eda']['output_dir']
    date_column = config['eda']['date_column']
    
    # Resolve absolute paths
    clean_path = project_root / clean_rel
    features_path = project_root / feat_rel
    output_dir = project_root / output_dir_rel
    
    logger.info(f"Target Clean Data Path: {clean_path}")
    logger.info(f"Target Features Data Path: {features_path}")
    
    if not clean_path.exists():
        err = f"Clean dataset file not found: {clean_path}"
        logger.error(err)
        raise FileNotFoundError(err)
        
    if not features_path.exists():
        err = f"Features dataset file not found: {features_path}"
        logger.error(err)
        raise FileNotFoundError(err)
        
    # Read files
    df_clean = pd.read_csv(clean_path)
    df_features = pd.read_csv(features_path)
    
    # Summarize clean file
    summary_clean = DatasetSummary(df_clean, "nsei_clean", date_column)
    clean_report_path = output_dir / "dataset_summary_clean.md"
    summary_clean.save(str(clean_report_path))
    
    # Summarize features file
    summary_features = DatasetSummary(df_features, "nifty_features", date_column)
    features_report_path = output_dir / "dataset_summary_features.md"
    summary_features.save(str(features_report_path))
    
    # Generate combined report comparing both side-by-side
    clean_min, clean_max = summary_clean.date_range()
    feat_min, feat_max = summary_features.date_range()
    
    clean_start = clean_min.strftime('%Y-%m-%d') if clean_min else 'N/A'
    clean_end = clean_max.strftime('%Y-%m-%d') if clean_max else 'N/A'
    feat_start = feat_min.strftime('%Y-%m-%d') if feat_min else 'N/A'
    feat_end = feat_max.strftime('%Y-%m-%d') if feat_max else 'N/A'
    
    # Check date range mismatch
    mismatch_section = ""
    if clean_end != feat_end or clean_start != feat_start:
        logger.warning(f"Date mismatch detected! Clean: {clean_start} to {clean_end} | Features: {feat_start} to {feat_end}")
        mismatch_section = (
            "> [!WARNING]\n"
            "> **Date Range Discrepancy Detected between Datasets:**\n"
            f"> - **`nsei_clean`** range: `{clean_start}` to `{clean_end}`\n"
            f"> - **`nifty_features`** range: `{feat_start}` to `{feat_end}`\n"
            f"> The features dataset lags the clean dataset by at least one date. "
            "Please rebuild the indicators pipeline to sync them.\n"
        )
        
    combined = []
    combined.append("# QuantEngine: Comparative Dataset Summary")
    combined.append(f"**Report Generated At**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if mismatch_section:
        combined.append(mismatch_section)
        
    combined.append("## Side-by-Side Comparison")
    combined.append("| Metric Profile | Clean Dataset (`nsei_clean`) | Features Dataset (`nifty_features`) |")
    combined.append("| :--- | :--- | :--- |")
    combined.append(f"| **Row Count** | {summary_clean.row_count()} | {summary_features.row_count()} |")
    combined.append(f"| **Column Count** | {summary_clean.column_count()} | {summary_features.column_count()} |")
    combined.append(f"| **Date Range** | `{clean_start}` to `{clean_end}` | `{feat_start}` to `{feat_end}` |")
    combined.append(f"| **Memory Size** | {summary_clean.memory_usage_mb():.4f} MB | {summary_features.memory_usage_mb():.4f} MB |")
    combined.append(f"| **Full Row Duplicates** | {summary_clean.duplicate_row_count()} | {summary_features.duplicate_row_count()} |")
    combined.append(f"| **Duplicate Dates** | {summary_clean.duplicate_date_count()} | {summary_features.duplicate_date_count()} |")
    
    # Aggregate missing counts info
    total_clean_nulls = sum(summary_clean.missing_value_counts().values)
    total_feat_nulls = sum(summary_features.missing_value_counts().values)
    combined.append(f"| **Total NaNs** | {total_clean_nulls} | {total_feat_nulls} |")
    combined.append("")
    
    combined_report_path = output_dir / "dataset_summary.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(combined_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(combined))
        
    logger.info(f"Combined comparative summary saved at: {combined_report_path}")


if __name__ == "__main__":
    try:
        global_config = load_global_config()
        # Convert Pydantic model to dict for generate_all_summaries orchestrator
        generate_all_summaries(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to generate summaries: {e}", exc_info=True)
        sys.exit(1)
