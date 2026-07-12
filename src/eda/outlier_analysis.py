import sys
import os
import time
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
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

def load_known_events(config_path: str) -> List[Dict[str, Any]]:
    """Loads known market events and data limitations from the YAML configuration."""
    p = Path(config_path)
    if not p.exists():
        err_msg = f"Known events configuration file not found at: {p}"
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)
        
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("known_events", [])
    except Exception as e:
        logger.error(f"Failed to load or parse known events file: {e}")
        raise e


class OutlierAnalyzer:
    """
    Identifies statistical outliers using IQR and Z-score methods.
    Analyzes, cross-references with known market event windows, and visualizes outlier profiles.
    Does not modify or mutate raw data.
    """
    def __init__(self, data: pd.DataFrame, dataset_name: str, known_events_path: str,
                 exclude_columns: List[str] = None, iqr_multiplier: float = 1.5,
                 zscore_threshold: float = 3.0, top_n_per_column: int = 20,
                 output_dir: str = "reports/eda/figures/outliers/",
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
        self.known_events = load_known_events(known_events_path)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Precompute overlap outlier indices and flagged counts per date
        self._precompute_outliers()

    def _precompute_outliers(self) -> None:
        """Precomputes outlier DataFrames and date flagged counts to optimize execution speed."""
        self._iqr_cache = {}
        self._z_cache = {}
        self._overlap_cache = {}
        self.date_flagged_count = {}
        
        for col in self.analysis_columns:
            series = self.data[col].dropna()
            if len(series) == 0:
                self._iqr_cache[col] = pd.DataFrame(columns=self.data.columns)
                self._z_cache[col] = pd.DataFrame(columns=self.data.columns)
                self._overlap_cache[col] = pd.DataFrame(columns=self.data.columns)
                continue
                
            # Compute IQR
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - self.iqr_multiplier * iqr
            upper_bound = q3 + self.iqr_multiplier * iqr
            iqr_mask = (self.data[col] < lower_bound) | (self.data[col] > upper_bound)
            self._iqr_cache[col] = self.data[iqr_mask].copy()
            
            # Compute Z-score
            mean = series.mean()
            std = series.std(ddof=1)
            if std == 0:
                self._z_cache[col] = pd.DataFrame(columns=self.data.columns)
                self._overlap_cache[col] = pd.DataFrame(columns=self.data.columns)
                continue
                
            z_mask = ((self.data[col] - mean) / std).abs() > self.zscore_threshold
            self._z_cache[col] = self.data[z_mask].copy()
            
            # Compute Overlap
            overlap_idx = self._iqr_cache[col].index.intersection(self._z_cache[col].index)
            self._overlap_cache[col] = self.data.loc[overlap_idx].copy()
            
            # Populate date flagged count map
            if self.date_column in self.data.columns and not self._overlap_cache[col].empty:
                for _, row in self._overlap_cache[col].iterrows():
                    date_str = pd.to_datetime(row[self.date_column]).strftime("%Y-%m-%d")
                    self.date_flagged_count[date_str] = self.date_flagged_count.get(date_str, 0) + 1

    def iqr_outliers(self, column: str) -> pd.DataFrame:
        """Returns rows where values lie outside IQR bounds (cached)."""
        return self._iqr_cache.get(column, pd.DataFrame(columns=self.data.columns))

    def zscore_outliers(self, column: str) -> pd.DataFrame:
        """Returns rows where absolute value of z-score exceeds the threshold (cached)."""
        return self._z_cache.get(column, pd.DataFrame(columns=self.data.columns))

    def outlier_overlap(self, column: str) -> pd.DataFrame:
        """Returns rows flagged as outliers by BOTH the IQR and Z-score methods (cached)."""
        return self._overlap_cache.get(column, pd.DataFrame(columns=self.data.columns))

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
        """Appends matching event details (names, categories, descriptions) to outlier dates."""
        df = outlier_df.copy()
        if df.empty or self.date_column not in df.columns:
            df["event_name"] = pd.Series(dtype=str)
            df["category"] = pd.Series(dtype=str)
            df["description"] = pd.Series(dtype=str)
            return df
            
        names, categories, descriptions = [], [], []
        
        for _, row in df.iterrows():
            row_date = pd.to_datetime(row[self.date_column])
            
            matched = []
            for ev in self.known_events:
                start = pd.to_datetime(ev["start_date"])
                end = pd.to_datetime(ev["end_date"])
                
                # Range check
                if start <= row_date <= end:
                    # Check column constraints
                    if "affected_columns" in ev and ev["affected_columns"]:
                        if column not in ev["affected_columns"]:
                            continue
                    matched.append(ev)
                    
            if matched:
                names.append(" & ".join([m["event_name"] for m in matched]))
                categories.append(matched[0]["category"])  # Default to primary category
                descriptions.append(" | ".join([m["description"] for m in matched]))
            else:
                names.append("Unexplained")
                categories.append("unexplained")
                descriptions.append("No historical market event matches this outlier date.")
                
        df["event_name"] = names
        df["category"] = categories
        df["description"] = descriptions
        return df

    def classify_outlier(self, row: pd.Series, date_str: str) -> str:
        """Returns one of the four specification category labels based on matching context."""
        cat = row.get("category", "unexplained")
        
        if cat == "known_market_event":
            return "Known Market Event"
        elif cat == "known_data_limitation":
            return "Known Data Limitation"
            
        # Evaluate co-occurrence clusters for unexplained events
        count = self.date_flagged_count.get(date_str, 0)
        if count >= 2:
            return "Potential Unknown Event"
        else:
            return "Potential Data Quality Issue"

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
                # Find any matching event names for the cluster row date
                row_date = pd.to_datetime(date_str)
                event_names = []
                for ev in self.known_events:
                    start = pd.to_datetime(ev["start_date"])
                    end = pd.to_datetime(ev["end_date"])
                    if start <= row_date <= end:
                        if not ev.get("affected_columns"): # Apply only to market-wide events
                            event_names.append(ev["event_name"])
                            
                event_label = " & ".join(event_names) if event_names else "Unexplained"
                
                clusters.append({
                    "date": date_str,
                    "count": len(cols),
                    "columns": sorted(cols),
                    "event": event_label
                })
        return sorted(clusters, key=lambda x: x["date"])

    def get_event_window_summary(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Computes summary statistics for a specific event window present in the dataset."""
        start = pd.to_datetime(event["start_date"])
        end = pd.to_datetime(event["end_date"])
        
        # 1. Trading days in window
        window_days = self.data[(self.data[self.date_column] >= start) & (self.data[self.date_column] <= end)]
        trading_count = len(window_days)
        if trading_count == 0:
            return None
            
        outlier_dates = set()
        feature_counts = {}
        simultaneous_flags = []
        
        for _, row in window_days.iterrows():
            date_str = row[self.date_column].strftime("%Y-%m-%d")
            flagged = []
            for col in self.analysis_columns:
                overlap_df = self.outlier_overlap(col)
                if not overlap_df.empty:
                    # Convert index or date column
                    dates_list = pd.to_datetime(overlap_df[self.date_column]).dt.strftime("%Y-%m-%d").tolist()
                    if date_str in dates_list:
                        # Check column constraints if any
                        if "affected_columns" in event and event["affected_columns"]:
                            if col not in event["affected_columns"]:
                                continue
                        flagged.append(col)
                        
            if flagged:
                outlier_dates.add(date_str)
                simultaneous_flags.append(len(flagged))
                for col in flagged:
                    feature_counts[col] = feature_counts.get(col, 0) + 1
                    
        max_sim = max(simultaneous_flags) if simultaneous_flags else 0
        freq_features = sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "name": event["event_name"],
            "start": event["start_date"],
            "end": event["end_date"],
            "category": event["category"],
            "description": event["description"],
            "trading_days": trading_count,
            "outlier_days": len(outlier_dates),
            "max_simultaneous": max_sim,
            "frequent_features": freq_features
        }

    def plot_outliers(self, column: str) -> str:
        """Plots time-series with normal vs outlier points highlighted."""
        df = self.data.sort_values(self.date_column).copy()
        
        iqr_df = self.iqr_outliers(column)
        z_df = self.zscore_outliers(column)
        overlap_df = self.outlier_overlap(column)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot full series line
        ax.plot(df[self.date_column], df[column], color='#d3d3d3', alpha=0.7, label='Time Series')
        
        # Plot IQR-only
        iqr_only_idx = iqr_df.index.difference(overlap_df.index)
        iqr_only_df = df.loc[iqr_only_idx]
        if not iqr_only_df.empty:
            ax.scatter(iqr_only_df[self.date_column], iqr_only_df[column], 
                       color='#ff7f0e', s=20, alpha=0.7, label='IQR-only Outlier')
                       
        # Z-score-only
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
        
        # 3. Chronological clusters and summaries
        md.append("## 2. Chronological Outlier Clustering & Window Analysis")
        md.append("### Event Window Summary Metrics")
        
        for ev in self.known_events:
            summary = self.get_event_window_summary(ev)
            if not summary:
                continue
                
            md.append(f"#### {summary['name']} Window ({summary['start']} to {summary['end']})")
            md.append(f"- **Description**: {summary['description']}")
            md.append(f"- **Category**: `{summary['category']}`")
            md.append(f"- **Trading Days in Window**: {summary['trading_days']}")
            md.append(f"- **Outlier Days in Window**: {summary['outlier_days']}")
            md.append(f"- **Maximum Simultaneous Features Flagged (single day)**: {summary['max_simultaneous']}")
            md.append("- **Most Frequently Flagged Features**:")
            if not summary['frequent_features']:
                md.append("  - *None*")
            else:
                for col, count in summary['frequent_features']:
                    md.append(f"  - `{col}` ({count} day(s))")
            md.append("")
            
        md.append("### Chronological Day-by-Day Flags Table")
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
            f"The sections below list the top {self.top_n_per_column} outliers (by deviation magnitude) "
            "flagged by the overlap method, categorized by their classification labels.\n"
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
            
            # Apply the four-category classification label to each row
            labels = []
            for idx, row in annotated_df.iterrows():
                date_str = pd.to_datetime(row[self.date_column]).strftime("%Y-%m-%d")
                labels.append(self.classify_outlier(row, date_str))
            annotated_df["class_label"] = labels
            
            md.append(f"### `{col}` Outlier Detail")
            
            # Group by class labels and generate subsections
            for cat_label in ["Known Market Event", "Known Data Limitation", "Potential Unknown Event", "Potential Data Quality Issue"]:
                sub_df = annotated_df[annotated_df["class_label"] == cat_label]
                if sub_df.empty:
                    continue
                    
                md.append(f"#### {cat_label}")
                md.append("| Date | Value | Deviation from Mean | Context Description |")
                md.append("| :--- | :--- | :--- | :--- |")
                for _, row in sub_df.iterrows():
                    date_str = pd.to_datetime(row[self.date_column]).strftime("%Y-%m-%d")
                    dev = row[col] - mean
                    
                    if cat_label in ["Known Market Event", "Known Data Limitation"]:
                        context = row["description"]
                    elif cat_label == "Potential Unknown Event":
                        context = f"Simultaneous flags triggered in {self.date_flagged_count[date_str]} columns."
                    else:
                        context = "Isolated single-column outlier; potential data integrity check."
                        
                    md.append(f"| `{date_str}` | {row[col]:.4f} | {dev:+.4f} | {context} |")
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
    known_events_rel = out_config['known_events_path']
    
    dpi = config['eda']['figures']['dpi']
    date_col = config['eda']['date_column']
    
    # Resolve paths
    clean_path = project_root / clean_rel
    features_path = project_root / feat_rel
    output_dir = project_root / output_dir_rel
    report_path = project_root / report_path_rel
    known_events_path = project_root / known_events_rel
    
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
        date_column=date_col,
        known_events_path=str(known_events_path)
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
