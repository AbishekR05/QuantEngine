import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("statistics")

class StatisticalAnalyzer:
    """
    Computes standard descriptive statistics (mean, median, mode, sample standard deviation,
    sample variance, min, max, percentiles, skewness, excess kurtosis) for numerical columns.
    Excludes NaN values and flags high skewness, heavy tails, or zero variance.
    """
    def __init__(self, data: pd.DataFrame, dataset_name: str, exclude_columns: List[str] = None,
                 skew_threshold: float = 1.0, kurtosis_threshold: float = 3.0):
        self.data = data
        self.dataset_name = dataset_name
        self.exclude_columns = exclude_columns or ["Date"]
        self.skew_threshold = skew_threshold
        self.kurtosis_threshold = kurtosis_threshold
        self.total_dataset_rows = len(data)

    def numeric_columns(self) -> List[str]:
        """Returns the list of columns to be analyzed (numeric dtypes, minus exclusions)."""
        num_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        return [col for col in num_cols if col not in self.exclude_columns]

    def compute_stats(self, column: str) -> Dict[str, Any]:
        """
        Computes all 12 descriptive statistics for a single column.
        Gracefully handles all-NaN and single-element edge cases.
        """
        series = self.data[column].dropna()
        n = len(series)
        
        stats = {
            "n": n,
            "mean": "N/A",
            "median": "N/A",
            "mode": "N/A",
            "mode_count": 0,
            "std": "N/A",
            "var": "N/A",
            "min": "N/A",
            "max": "N/A",
            "p25": "N/A",
            "p50": "N/A",
            "p75": "N/A",
            "skew": "N/A",
            "kurt": "N/A"
        }
        
        if n == 0:
            return stats
            
        stats["mean"] = float(series.mean())
        stats["median"] = float(series.median())
        
        # Mode logic: first value + total count of unique modes
        modes = series.mode()
        if not modes.empty:
            stats["mode"] = float(modes.iloc[0])
            stats["mode_count"] = len(modes)
            
        stats["min"] = float(series.min())
        stats["max"] = float(series.max())
        stats["p25"] = float(series.quantile(0.25))
        stats["p50"] = float(series.quantile(0.50))
        stats["p75"] = float(series.quantile(0.75))
        
        # Dispersion parameters require N > 1
        if n > 1:
            stats["std"] = float(series.std(ddof=1))
            stats["var"] = float(series.var(ddof=1))
            
        # Skewness requires N >= 3
        if n >= 3:
            s_val = series.skew()
            if not pd.isna(s_val):
                stats["skew"] = float(s_val)
                
        # Kurtosis requires N >= 4
        if n >= 4:
            k_val = series.kurt()
            if not pd.isna(k_val):
                stats["kurt"] = float(k_val)
                
        return stats

    def compute_all(self) -> pd.DataFrame:
        """Computes descriptive statistics for all selected numeric columns."""
        cols = self.numeric_columns()
        rows = []
        for col in cols:
            s = self.compute_stats(col)
            s["Column"] = col
            rows.append(s)
            
        if not rows:
            return pd.DataFrame()
            
        df_stats = pd.DataFrame(rows)
        # Order columns logically
        ordered = [
            "Column", "n", "mean", "median", "mode", "mode_count", 
            "std", "var", "min", "max", "p25", "p50", "p75", "skew", "kurt"
        ]
        return df_stats[ordered]

    def to_markdown(self) -> str:
        """Generates a complete statistical summary report in Markdown format."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        df_stats = self.compute_all()
        
        md = []
        md.append(f"# Statistical summary report for: `{self.dataset_name}`")
        md.append(f"**Report Generated At**: {timestamp}")
        md.append(
            "\n*Convention Note: Excess Kurtosis is reported below. A normal distribution "
            "corresponds to a kurtosis value of 0. Kurtosis values greater than 0 indicate a fat-tailed distribution.*\n"
        )
        
        if df_stats.empty:
            md.append("No numeric columns available for analysis.")
            return "\n".join(md)
            
        # 1. Main Statistics Table
        md.append("## 1. Descriptive Statistics Table")
        headers = [
            "Column Name", "N", "Mean", "Median", "Mode (first)", "Modes Count",
            "Std Dev", "Variance", "Min", "Max", "25%", "50%", "75%", "Skewness", "Excess Kurtosis"
        ]
        md.append("| " + " | ".join(headers) + " |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        
        def fmt(v: Any) -> str:
            if v == "N/A" or pd.isna(v):
                return "N/A"
            if isinstance(v, float):
                return f"{v:.4f}"
            return str(v)
            
        for _, row in df_stats.iterrows():
            line = [
                f"`{row['Column']}`",
                str(row['n']),
                fmt(row['mean']),
                fmt(row['median']),
                fmt(row['mode']),
                str(row['mode_count']),
                fmt(row['std']),
                fmt(row['var']),
                fmt(row['min']),
                fmt(row['max']),
                fmt(row['p25']),
                fmt(row['p50']),
                fmt(row['p75']),
                fmt(row['skew']),
                fmt(row['kurt'])
            ]
            md.append("| " + " | ".join(line) + " |")
        md.append("")
        
        # 2. Interpretive Flags Section
        md.append("## 2. Interpretive Data Observations")
        
        skewed_cols = []
        heavy_tailed_cols = []
        zero_var_cols = []
        null_warmup_cols = []
        
        for _, row in df_stats.iterrows():
            col = row['Column']
            n = row['n']
            
            # Skewness check (|skew| > threshold)
            if row['skew'] != "N/A":
                if abs(row['skew']) > self.skew_threshold:
                    skewed_cols.append((col, row['skew']))
                    
            # Kurtosis check (excess kurtosis > threshold)
            if row['kurt'] != "N/A":
                if row['kurt'] > self.kurtosis_threshold:
                    heavy_tailed_cols.append((col, row['kurt']))
                    
            # Zero variance check (min == max)
            if row['min'] != "N/A" and row['max'] != "N/A" and n > 1:
                if row['min'] == row['max']:
                    zero_var_cols.append(col)
                    
            # Warm-up check (N < total rows)
            if n < self.total_dataset_rows:
                null_warmup_cols.append((col, n))
                
        # Print Skewed Columns
        md.append("### Skewness Warnings")
        if not skewed_cols:
            md.append("No columns exceed the skewness threshold of ±{:.1f}.".format(self.skew_threshold))
        else:
            md.append(f"The following columns exhibit high skewness (absolute value > {self.skew_threshold}):")
            for col, val in skewed_cols:
                md.append(f"- `{col}` (Skewness: {val:.4f})")
        md.append("")
        
        # Print Fat-tailed Columns
        md.append("### Heavy-Tail Warnings (Excess Kurtosis)")
        if not heavy_tailed_cols:
            md.append("No columns exceed the excess kurtosis threshold of {:.1f}.".format(self.kurtosis_threshold))
        else:
            md.append(f"The following columns exhibit fat-tailed distributions (excess kurtosis > {self.kurtosis_threshold}):")
            for col, val in heavy_tailed_cols:
                is_ret = "Daily_Return" in col or "Log_Return" in col
                note = " (Expected for financial return series)" if is_ret else ""
                md.append(f"- `{col}` (Excess Kurtosis: {val:.4f}){note}")
        md.append("")
        
        # Print Zero Variance Columns
        md.append("### Zero Variance Flags")
        if not zero_var_cols:
            md.append("No zero-variance columns were detected. (Data values fluctuate normally).")
        else:
            md.append(f"> [!CAUTION]\n> **Potential Data Quality Issues Detected:**\n"
                      f"> The following columns have zero variance (constant values across all sessions):\n"
                      f"> " + ", ".join([f"`{c}`" for c in zero_var_cols]))
        md.append("")
        
        # 3. Sample Size Warnings
        md.append("## 3. Variable Sample Sizes (N)")
        if not null_warmup_cols:
            md.append("All numeric columns are computed over the full sample size of **{}** records.".format(self.total_dataset_rows))
        else:
            md.append(f"The following indicators were computed over subset sample sizes due to rolling warm-ups:")
            md.append("| Column Name | Effective N | Warm-up NaNs |")
            md.append("| :--- | :--- | :--- |")
            for col, n in null_warmup_cols:
                nans = self.total_dataset_rows - n
                md.append(f"| `{col}` | {n} | {nans} |")
                
        return "\n".join(md)

    def save(self, output_path: str) -> None:
        """Writes the Markdown statistical report to the specified file path."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        logger.info(f"Statistical report written to: {p}")


def generate_all_statistics(config: dict) -> None:
    """Loads datasets from config paths, runs statistical checks, and saves reports."""
    logger.info("Starting descriptive statistical analyzer pipeline...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Extract configurations
    clean_rel = config['eda']['input_files']['clean']
    feat_rel = config['eda']['input_files']['features']
    output_dir_rel = config['eda']['output_dir']
    
    exclude_cols = config['eda']['statistics']['exclude_columns']
    skew_th = config['eda']['statistics']['skew_threshold']
    kurt_th = config['eda']['statistics']['kurtosis_threshold']
    
    # Resolve paths
    clean_path = project_root / clean_rel
    features_path = project_root / feat_rel
    output_dir = project_root / output_dir_rel
    
    logger.info(f"Loading files: {clean_path} & {features_path}")
    
    if not clean_path.exists() or not features_path.exists():
        raise FileNotFoundError("Clean or features dataset files missing. Please run pipeline orchestrator.")
        
    df_clean = pd.read_csv(clean_path)
    df_features = pd.read_csv(features_path)
    
    # Generate statistics for clean dataset
    analyzer_clean = StatisticalAnalyzer(
        df_clean, "nsei_clean", exclude_cols, skew_th, kurt_th
    )
    clean_out = output_dir / "statistical_summary_clean.md"
    analyzer_clean.save(str(clean_out))
    
    # Generate statistics for features dataset
    analyzer_features = StatisticalAnalyzer(
        df_features, "nifty_features", exclude_cols, skew_th, kurt_th
    )
    feat_out = output_dir / "statistical_summary_features.md"
    analyzer_features.save(str(feat_out))
    
    logger.info("Statistical summary reports generated successfully.")


if __name__ == "__main__":
    try:
        global_config = load_global_config()
        generate_all_statistics(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to generate statistics: {e}", exc_info=True)
        sys.exit(1)
