import sys
import os
import time
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

# Headless backend for Matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("outliers")

def load_known_market_events() -> Dict[str, str]:
    """Loads known market events dictionary from YAML lookup file."""
    project_root = Path(__file__).resolve().parent.parent.parent
    yaml_path = project_root / "config" / "known_market_events.yaml"
    if not yaml_path.exists():
        logger.warning(f"known_market_events.yaml not found at {yaml_path}. Using empty events list.")
        return {}
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        events_dict = {}
        for event in data.get("events", []):
            date_str = pd.to_datetime(event["date"]).strftime("%Y-%m-%d")
            events_dict[date_str] = event["name"]
        return events_dict
    except Exception as e:
        logger.error(f"Failed to load known market events lookup: {e}")
        return {}


class OutlierAnalyzer:
    """
    Identifies statistical outliers using IQR and Z-score methods.
    Analyzes, cross-references with known market crashes, and visualizes outlier profiles.
    Does not modify or mutate raw data.
    """
    def __init__(self, data: pd.DataFrame, dataset_name: str, exclude_columns: List[str] = None,
                 iqr_multiplier: float = 1.5, zscore_threshold: float = 3.0,
                 top_n_per_column: int = 20, output_dir: str = "reports/eda/figures/outliers/",
                 dpi: int = 150, date_column: str = "Date"):
        self.data = data.copy()
        self.dataset_name = dataset_name
        self.exclude_columns = exclude_columns or ["Date"]
        self.iqr_multiplier = iqr_multiplier
        self.zscore_threshold = zscore_threshold
        self.top_n_per_column = top_n_per_column
        self.output_dir = Path(output_dir)
        self.dpi = dpi
        self.date_column = date_column
        
        self.total_rows = len(self.data)
        
        # Parse date column to datetime if present
        if self.date_column in self.data.columns:
            self.data[self.date_column] = pd.to_datetime(self.data[self.date_column])
            
        # Determine analysis columns
        num_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        self.analysis_columns = [col for col in num_cols if col not in self.exclude_columns]
        
        # Load known events registry
        self.known_events = load_known_market_events()
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def iqr_outliers(self, column: str) -> pd.DataFrame:
        """Returns rows where values lie outside Q1 - k*IQR or Q3 + k*IQR bounds."""
        series = self.data[column].dropna()
        if len(series) == 0:
            return pd.DataFrame(columns=self.data.columns)
            
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr
        
        outliers_mask = (self.data[column] < lower_bound) | (self.data[column] > upper_bound)
        return self.data[outliers_mask].copy()

    def zscore_outliers(self, column: str) -> pd.DataFrame:
        """Returns rows where absolute value of z-score exceeds the threshold."""
        series = self.data[column].dropna()
        if len(series) <= 1:
            return pd.DataFrame(columns=self.data.columns)
            
        mean = series.mean()
        std = series.std(ddof=1)
        
        if std == 0:
            return pd.DataFrame(columns=self.data.columns)
            
        z_scores = (self.data[column] - mean) / std
        outliers_mask = z_scores.abs() > self.zscore_threshold
        return self.data[outliers_mask].copy()

    def outlier_overlap(self, column: str) -> pd.DataFrame:
        """Returns rows flagged as outliers by BOTH the IQR and Z-score methods."""
        iqr_df = self.iqr_outliers(column)
        z_df = self.zscore_outliers(column)
        overlap_idx = iqr_df.index.intersection(z_df.index)
        return self.data.loc[overlap_idx].copy()

    def outlier_summary(self) -> pd.DataFrame:
        """Computes statistical counts and percentages of outliers for each method."""
        summary = []
        for col in self.analysis_columns:
            non_nulls = self.data[col].dropna()
            total_n = len(non_nulls)
            
            if total_n == 0:
                summary.append({
                    "Column": col,
                    "IQR Count": 0, "IQR %": 0.0,
                    "Z-Score Count": 0, "Z-Score %": 0.0,
                    "Overlap Count": 0, "Overlap %": 0.0
                })
                continue
                
            iqr_cnt = len(self.iqr_outliers(col))
            z_cnt = len(self.zscore_outliers(col))
            overlap_cnt = len(self.outlier_overlap(col))
            
            summary.append({
                "Column": col,
                "IQR Count": iqr_cnt,
                "IQR %": (iqr_cnt / total_n) * 100.0,
                "Z-Score Count": z_cnt,
                "Z-Score %": (z_cnt / total_n) * 100.0,
                "Overlap Count": overlap_cnt,
                "Overlap %": (overlap_cnt / total_n) * 100.0
            })
            
        return pd.DataFrame(summary)

    def annotate_known_events(self, outlier_df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Appends event categories or volume limitations labels to flagged outliers."""
        df = outlier_df.copy()
        if df.empty or self.date_column not in df.columns:
            df["known_event"] = pd.Series(dtype=str)
            return df
            
        annotations = []
        for _, row in df.iterrows():
            date_str = pd.to_datetime(row[self.date_column]).strftime("%Y-%m-%d")
            
            # Check known events lookup
            if date_str in self.known_events:
                annotations.append(self.known_events[date_str])
            # Check zero volume limitations
            elif column.lower() == "volume" and row["Volume"] == 0:
                annotations.append("Known Volume Limit Era (2007-2013)")
            else:
                annotations.append("Unexplained")
                
        df["known_event"] = annotations
        return df

    def get_chronological_outlier_clusters(self) -> List[Dict[str, Any]]:
        """Identifies dates where multiple columns flagged overlap outliers simultaneously."""
        date_map = {}
        for col in self.analysis_columns:
            overlap = self.outlier_overlap(col)
            if overlap.empty or self.date_column not in overlap.columns:
                continue
            for _, row in overlap.iterrows():
                date_str = pd.to_datetime(row[self.date_column]).strftime("%Y-%m-%d")
                if date_str not in date_map:
                    date_map[date_str] = []
                date_map[date_str].append(col)
                
        clusters = []
        for date_str, cols in date_map.items():
            if len(cols) >= 2:
                clusters.append({
                    "date": date_str,
                    "count": len(cols),
                    "columns": sorted(cols),
                    "event": self.known_events.get(date_str, "Unexplained")
                })
        return sorted(clusters, key=lambda x: x["date"])

    def plot_outliers(self, column: str) -> str:
        """Plots time-series with normal vs outlier points highlighted."""
        df = self.data.sort_values(self.date_column).copy()
        
        # Get outliers
        iqr_df = self.iqr_outliers(column)
        z_df = self.zscore_outliers(column)
        overlap_df = self.outlier_overlap(column)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot full series line (light gray)
        ax.plot(df[self.date_column], df[column], color='#d3d3d3', alpha=0.7, label='Time Series')
        
        # Highlight outliers
        iqr_only_idx = iqr_df.index.difference(overlap_df.index)
        iqr_only_df = df.loc[iqr_only_idx]
        if not iqr_only_df.empty:
            ax.scatter(iqr_only_df[self.date_column], iqr_only_df[column], 
                       color='#ff7f0e', s=20, alpha=0.7, label='IQR-only Outlier')
                       
        z_only_idx = z_df.index.difference(overlap_df.index)
        z_only_df = df.loc[z_only_idx]
        if not z_only_df.empty:
            ax.scatter(z_only_df[self.date_column], z_only_df[column], 
                       color='#1f77b4', s=20, alpha=0.7, label='Z-score-only Outlier')
                       
        # Overlap (Flagged by both)
        if not overlap_df.empty:
            ax.scatter(overlap_df[self.date_column], overlap_df[column], 
                       color='#d62728', s=45, marker='o', edgecolor='black', zorder=5, label='Overlap (Both Methods)')
            
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        ax.set_title(f"Outlier Identification Profile: {column} ({self.dataset_name}, {min_date} to {max_date})", 
                     fontsize=12, fontweight='bold', pad=10)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel(f"Value ({column})", fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend(loc='best', fontsize=9)
        
        # Date ticks format
        ax.xaxis.set_major_locator(mdates.YearLocator(3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
        
        out_path = self.output_dir / f"outliers_{column.lower()}.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.info(f"Saved outlier plot for {column} at: {out_path}")
        return str(out_path)

    def to_markdown(self) -> str:
        """Generates a complete outlier analysis report in Markdown format."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        df_summary = self.outlier_summary()
        
        md = []
        md.append(f"# QuantEngine: Statistical Outlier Analysis Report")
        md.append(f"**Report Generated At**: {timestamp}")
        md.append(f"**Source Dataset**: `{self.dataset_name}`")
        md.append(f"**Configuration Limits**: IQR multiplier = {self.iqr_multiplier} | Z-score threshold = {self.zscore_threshold}\n")
        
        # 1. Non-action statement (Verbatim Compliance)
        md.append(
            "> [!IMPORTANT]\n"
            "> **Standing Non-Action Statement:**\n"
            "> *No outliers identified in this report have been removed, capped, or modified. "
            "This report is for visibility only. Any decision to treat a specific point as erroneous "
            "vs. a genuine market event is a human judgment call, not an automated one.*\n"
        )
        
        # 2. Outlier summary table
        md.append("## 1. Outlier Summary Metrics Table")
        md.append("| Column Name | IQR Count | IQR % | Z-Score Count | Z-Score % | Overlap Count | Overlap % |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for _, row in df_summary.iterrows():
            line = [
                f"`{row['Column']}`",
                str(row['IQR Count']), f"{row['IQR %']:.2f}%",
                str(row['Z-Score Count']), f"{row['Z-Score %']:.2f}%",
                str(row['Overlap Count']), f"{row['Overlap %']:.2f}%"
            ]
            md.append("| " + " | ".join(line) + " |")
        md.append("")
        
        # 3. Chronological clusters
        md.append("## 2. Chronological Outlier Clustering")
        md.append("Dates where multiple columns flagged overlap outliers simultaneously (indicating market shocks):\n")
        clusters = self.get_chronological_outlier_clusters()
        if not clusters:
            md.append("No multi-column outlier clusters detected.")
        else:
            md.append("| Date | Columns Flagged Count | Flagged Columns List | Associated Market Event |")
            md.append("| :--- | :--- | :--- | :--- |")
            for c in clusters:
                cols_str = ", ".join([f"`{col}`" for col in c['columns']])
                md.append(f"| `{c['date']}` | {c['count']} | {cols_str} | {c['event']} |")
        md.append("")
        
        # 4. Per-column detail (Explained vs Unexplained)
        md.append("## 3. Detailed Outlier Lists per Column")
        md.append(
            f"The tables below list the top {self.top_n_per_column} outliers (by deviation magnitude) "
            "flagged by the overlap method, categorized into **Explained** and **Unexplained**.\n"
        )
        
        for col in self.analysis_columns:
            overlap_df = self.outlier_overlap(col)
            if overlap_df.empty:
                continue
                
            # Calculate absolute deviation from mean to sort by magnitude
            series = self.data[col].dropna()
            mean = series.mean()
            overlap_df["dev_magnitude"] = (overlap_df[col] - mean).abs()
            overlap_df = overlap_df.sort_values(by="dev_magnitude", ascending=False).head(self.top_n_per_column)
            
            annotated_df = self.annotate_known_events(overlap_df, col)
            
            md.append(f"### `{col}` Outlier Detail")
            
            explained = annotated_df[annotated_df["known_event"] != "Unexplained"]
            unexplained = annotated_df[annotated_df["known_event"] == "Unexplained"]
            
            # Sub-table Explained
            md.append("#### Explained / Expected Outliers")
            if explained.empty:
                md.append("- No explained outliers flagged.")
            else:
                md.append("| Date | Value | Deviation from Mean | Context Note |")
                md.append("| :--- | :--- | :--- | :--- |")
                for _, row in explained.iterrows():
                    date_str = pd.to_datetime(row[self.date_column]).strftime("%Y-%m-%d")
                    dev = row[col] - mean
                    md.append(f"| `{date_str}` | {row[col]:.4f} | {dev:+.4f} | {row['known_event']} |")
            md.append("")
            
            # Sub-table Unexplained
            md.append("#### Unexplained Outliers (Potential Anomalies)")
            if unexplained.empty:
                md.append("- No unexplained outliers flagged (all match known events).")
            else:
                md.append("| Date | Value | Deviation from Mean | Context Note |")
                md.append("| :--- | :--- | :--- | :--- |")
                for _, row in unexplained.iterrows():
                    date_str = pd.to_datetime(row[self.date_column]).strftime("%Y-%m-%d")
                    dev = row[col] - mean
                    md.append(f"| `{date_str}` | {row[col]:.4f} | {dev:+.4f} | Unclassified extreme point |")
            md.append("")
            
            # Visual plot reference
            rel_plot_path = f"../figures/outliers/outliers_{col.lower()}.png"
            md.append(f"**Visual Outlier Chart**: ![Outlier Plot {col}]({rel_plot_path})\n")
            md.append("---")
            
        return "\n".join(md)

    def save(self, output_path: str) -> None:
        """Writes the Markdown statistical report to the specified file path."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        logger.info(f"Outlier report saved at: {p}")


def generate_outlier_report(config: dict) -> None:
    """Orchestrates loading data, running OutlierAnalyzer, generating plots, and saving the report."""
    logger.info("Initializing Outlier Analysis pipeline...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Extract configs
    clean_rel = config['eda']['input_files']['clean']
    feat_rel = config['eda']['input_files']['features']
    out_config = config['eda']['outliers']
    
    exclude_cols = out_config['exclude_columns']
    iqr_mult = out_config['iqr_multiplier']
    z_th = out_config['zscore_threshold']
    top_n = out_config['top_n_per_column']
    output_dir_rel = out_config['output_dir']
    report_path_rel = out_config['report_output_path']
    
    dpi = config['eda']['figures']['dpi']
    date_col = config['eda']['date_column']
    
    # Resolve paths
    clean_path = project_root / clean_rel
    features_path = project_root / feat_rel
    output_dir = project_root / output_dir_rel
    report_path = project_root / report_path_rel
    
    logger.info(f"Loading data: {clean_path} & {features_path}")
    
    if not clean_path.exists() or not features_path.exists():
        raise FileNotFoundError("Clean or features dataset files missing. Please run pipeline orchestrator.")
        
    df_features = pd.read_csv(features_path)
    
    # Instantiate OutlierAnalyzer on features dataset (contains technical indicators + returns)
    analyzer = OutlierAnalyzer(
        data=df_features,
        dataset_name="nifty_features",
        exclude_columns=exclude_cols,
        iqr_multiplier=iqr_mult,
        zscore_threshold=z_th,
        top_n_per_column=top_n,
        output_dir=str(output_dir),
        dpi=dpi,
        date_column=date_col
    )
    
    # Generate outlier plots for each numerical feature
    for col in analyzer.analysis_columns:
        analyzer.plot_outliers(col)
        
    # Save Report
    analyzer.save(str(report_path))
    logger.info("Outlier analysis completed successfully.")


if __name__ == "__main__":
    try:
        global_config = load_global_config()
        generate_outlier_report(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to run outlier analysis: {e}", exc_info=True)
        sys.exit(1)
