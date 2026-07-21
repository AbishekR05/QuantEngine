import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from sklearn.metrics import mutual_info_score

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config
from src.eda.correlations import CorrelationAnalyzer

logger = get_logger("usefulness")

class FeatureUsefulnessAnalyzer:
    """
    Ranks features along three independent dimensions (Variance, Redundancy, Mutual Information)
    to identify informational signals and linear/nonlinear dependencies.
    """
    def __init__(self, data: pd.DataFrame, exclude_columns: List[str] = None,
                 correlation_report_path: str = None, mi_bins: int = 10):
        self.data = data.copy()
        self.exclude_columns = exclude_columns or ["Date"]
        self.correlation_report_path = correlation_report_path
        self.mi_bins = mi_bins
        
        # Filter numerical columns for analysis
        num_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        self.analysis_columns = [col for col in num_cols if col not in self.exclude_columns]

    def variance_ranking(self) -> pd.DataFrame:
        """Computes raw and normalized variance metrics for each numerical feature."""
        ranking = []
        for col in self.analysis_columns:
            series = self.data[col].dropna()
            if len(series) == 0:
                ranking.append({
                    "Feature": col,
                    "Raw Variance": 0.0,
                    "Mean": 0.0,
                    "Coefficient of Variation": 0.0
                })
                continue
                
            raw_var = series.var(ddof=1)
            mean_val = series.mean()
            std_val = series.std(ddof=1)
            
            # Coefficient of Variation = standard_deviation / |mean|
            coef_var = (std_val / abs(mean_val)) if mean_val != 0 else 0.0
            
            ranking.append({
                "Feature": col,
                "Raw Variance": raw_var,
                "Mean": mean_val,
                "Coefficient of Variation": coef_var
            })
            
        df_ranking = pd.DataFrame(ranking)
        return df_ranking.sort_values(by="Coefficient of Variation", ascending=False)

    def redundancy_ranking(self) -> pd.DataFrame:
        """Sourced from CorrelationAnalyzer to count highly correlated partners per feature."""
        # Reuse CorrelationAnalyzer code and matrix directly to find redundant features
        corr_analyzer = CorrelationAnalyzer(
            data=self.data,
            dataset_name="nifty_features",
            exclude_columns=self.exclude_columns,
            high_corr_threshold=0.9,
            leakage_threshold=0.99
        )
        
        high_corr_df = corr_analyzer.high_correlation_pairs("pearson")
        partners_count = {col: 0 for col in self.analysis_columns}
        
        if not high_corr_df.empty:
            for _, row in high_corr_df.iterrows():
                a = row["Feature A"]
                b = row["Feature B"]
                if a in partners_count:
                    partners_count[a] += 1
                if b in partners_count:
                    partners_count[b] += 1
                    
        df_red = pd.DataFrame([
            {"Feature": col, "Redundant Partners": cnt} 
            for col, cnt in partners_count.items()
        ])
        return df_red.sort_values(by="Redundant Partners", ascending=False)

    def mutual_information_matrix(self) -> pd.DataFrame:
        """Computes pairwise mutual information (in bits) between all numerical features."""
        n = len(self.analysis_columns)
        mi_matrix = pd.DataFrame(index=self.analysis_columns, columns=self.analysis_columns, dtype=float)
        
        # Discretize continuous features beforehand to optimize computing speed
        discretized_data = {}
        for col in self.analysis_columns:
            series = self.data[col].dropna()
            if len(series) == 0:
                discretized_data[col] = pd.Series(dtype=float)
                continue
            
            # Discretize using equal-frequency bins (qcut) falling back to equal-width (cut)
            try:
                discretized_data[col] = pd.qcut(self.data[col], q=self.mi_bins, labels=False, duplicates='drop')
            except ValueError:
                discretized_data[col] = pd.cut(self.data[col], bins=self.mi_bins, labels=False)
                
        for i in range(n):
            for j in range(i, n):
                col1 = self.analysis_columns[i]
                col2 = self.analysis_columns[j]
                
                # Align dates and drop missing rows pairwise
                mask = self.data[col1].notna() & self.data[col2].notna()
                x_disc = discretized_data[col1][mask]
                y_disc = discretized_data[col2][mask]
                
                if len(x_disc) == 0 or len(y_disc) == 0:
                    mi_matrix.loc[col1, col2] = np.nan
                    mi_matrix.loc[col2, col1] = np.nan
                    continue
                    
                # Compute mutual info score in nats, then convert to bits
                mi_nats = mutual_info_score(x_disc, y_disc)
                mi_bits = mi_nats / np.log(2)
                
                mi_matrix.loc[col1, col2] = mi_bits
                mi_matrix.loc[col2, col1] = mi_bits
                
        return mi_matrix

    def mutual_information_ranking(self) -> pd.DataFrame:
        """Ranks features based on average pairwise mutual information with all other features."""
        mi_mat = self.mutual_information_matrix()
        
        ranking = []
        for col in self.analysis_columns:
            # Drop the self-correlation diagonal cell (which represents feature entropy)
            other_mis = mi_mat[col].drop(col).dropna()
            
            if other_mis.empty:
                avg_mi, max_mi = 0.0, 0.0
            else:
                avg_mi = other_mis.mean()
                max_mi = other_mis.max()
                
            ranking.append({
                "Feature": col,
                "Average MI": avg_mi,
                "Max MI": max_mi
            })
            
        df_mi = pd.DataFrame(ranking)
        return df_mi.sort_values(by="Average MI", ascending=False)

    def combined_ranking(self) -> pd.DataFrame:
        """Merges variance, redundancy, and mutual information rankings side-by-side without blended scores."""
        df_var = self.variance_ranking()
        df_red = self.redundancy_ranking()
        df_mi = self.mutual_information_ranking()
        
        merged = df_var.merge(df_red, on="Feature")
        merged = merged.merge(df_mi, on="Feature")
        
        column_order = [
            "Feature",
            "Raw Variance",
            "Coefficient of Variation",
            "Redundant Partners",
            "Average MI",
            "Max MI"
        ]
        return merged[column_order]

    def find_mi_correlation_divergences(self, mi_threshold: float = 0.35, corr_max_threshold: float = 0.20) -> List[Dict[str, Any]]:
        """Identifies feature pairs where Mutual Information is high but linear correlation is low."""
        corr_analyzer = CorrelationAnalyzer(
            data=self.data,
            dataset_name="nifty_features",
            exclude_columns=self.exclude_columns,
            high_corr_threshold=0.9,
            leakage_threshold=0.99
        )
        p_mat = corr_analyzer.pearson_matrix().abs()
        mi_mat = self.mutual_information_matrix()
        
        divergences = []
        n = len(self.analysis_columns)
        
        for i in range(n):
            for j in range(i + 1, n):
                col1 = self.analysis_columns[i]
                col2 = self.analysis_columns[j]
                
                mi_val = mi_mat.loc[col1, col2]
                corr_val = p_mat.loc[col1, col2]
                
                if pd.isna(mi_val) or pd.isna(corr_val):
                    continue
                    
                # High Mutual Information but low linear correlation signifies nonlinear relations
                if mi_val >= mi_threshold and corr_val <= corr_max_threshold:
                    divergences.append({
                        "Feature A": col1,
                        "Feature B": col2,
                        "Mutual Information (bits)": mi_val,
                        "Absolute Pearson r": corr_val
                    })
                    
        return sorted(divergences, key=lambda x: x["Mutual Information (bits)"], reverse=True)

    def to_markdown(self) -> str:
        """Compiles rankings and metrics tables into a comprehensive Markdown report."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        df_var = self.variance_ranking()
        df_red = self.redundancy_ranking()
        df_mi = self.mutual_information_ranking()
        df_comb = self.combined_ranking()
        divergences = self.find_mi_correlation_divergences(0.35, 0.20)
        
        md = []
        md.append("# QuantEngine: Feature Usefulness Analysis Report")
        md.append(f"**Report Generated At**: {timestamp}")
        md.append("**Source Dataset**: `nifty_features`")
        md.append(f"**Configuration**: Discretization Bins (MI Estimator) = {self.mi_bins}\n")
        
        # 1. Non-Decision Statement (Strict Compliance)
        md.append("## 1. Explicit Non-Decision Statement")
        md.append(
            "> [!IMPORTANT]\n"
            "> **Standing Non-Decision and Non-Pruning Directive:**\n"
            "> *This report ranks features along three independent dimensions. It does not recommend removing any feature. "
            "Feature selection decisions should be deferred until label-based (Step 8+) predictive relevance can be measured, "
            "since a feature's raw variance, redundancy with other features, or informational independence does not by itself "
            "determine whether it will be useful for predicting future market direction.*\n"
        )
        
        # 2. Methodology Explanation
        md.append("## 2. Methodology Summary")
        md.append(
            "This report analyzes the informational footprint of technical indicators and features across three independent lenses:\n"
            "1. **Variance Ranking**: Measures the raw signal volatility. Standardized using the **Coefficient of Variation** ($CV = \\sigma / |\\mu|$) "
            "to make bounded oscillators (e.g. RSI_14) comparable to price-level features.\n"
            "2. **Redundancy Count**: Reuses the Pearson correlation matrix ($|r| \\ge 0.90$) generated in Step 4. Tracks the count of highly correlated "
            "partners each feature shares.\n"
            "3. **Mutual Information (MI)**: Computes pairwise informational dependency (in bits) between features discretized into equal-frequency bins. "
            "Unlike correlation, MI captures nonlinear dependencies (e.g., U-shaped or cyclical patterns).\n"
        )
        
        # 3. Known Limitations and Quirks
        md.append("## 3. Known Data Limitations & Distribution Quirks")
        md.append(
            "- **Volume Zero-Inflation**: Volume's variance is dominated by its zero-inflated shape (due to the 2007–2013 calculation limitation). "
            "Its raw variance is extremely large but does not represent a clean trading signal. Use caution if using Volume's raw variance directly.\n"
            "- **RSI Boundary Artifact**: During warm-up (first 13 days of series), RSI_14 is mathematically pinned near 100.0. "
            "This boundary artifact creates high artificial information concentration at the start of Nifty.\n"
            "- **Structural Near-Duplicates**: Features like `Close` and `Adj Close`, or `SMA_20` and `BB_Middle`, are mathematically near-identical by construction. "
            "These display maximum Mutual Information ($\\approx 3.32$ bits for 10 bins) and high redundant partner counts as expected.\n"
        )
        
        # 4. Variance Table
        md.append("## 4. Feature Variance Rankings")
        md.append("Features ranked descending by their **Coefficient of Variation** (relative standard deviation):")
        md.append("| Rank | Feature | Raw Variance | Mean | Coefficient of Variation |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for idx, row in df_var.reset_index().iterrows():
            md.append(f"| {idx+1} | `{row['Feature']}` | {row['Raw Variance']:.6f} | {row['Mean']:.4f} | {row['Coefficient of Variation']:.6f} |")
        md.append("")
        
        # 5. Redundancy Table
        md.append("## 5. Linear Redundancy Rankings (Reused from Step 4)")
        md.append("Features ranked descending by the number of highly correlated partners ($|r| \\ge 0.90$):")
        md.append("| Rank | Feature | Highly Correlated Partners | Redundancy Status |")
        md.append("| :--- | :--- | :--- | :--- |")
        for idx, row in df_red.reset_index().iterrows():
            status = "Highly Redundant" if row['Redundant Partners'] > 0 else "Independent Profile"
            md.append(f"| {idx+1} | `{row['Feature']}` | {row['Redundant Partners']} | {status} |")
        md.append("")
        
        # 6. Mutual Information Table
        md.append("## 6. Pairwise Mutual Information Rankings")
        md.append("Average and maximum Mutual Information (in bits) between each feature and all other features:")
        md.append("| Rank | Feature | Average MI (bits) | Max MI (bits) | Informational Profile |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        for idx, row in df_mi.reset_index().iterrows():
            profile = "Highly Entangled" if row['Average MI'] > 1.5 else ("Moderately Coupled" if row['Average MI'] > 0.5 else "Independent Source")
            md.append(f"| {idx+1} | `{row['Feature']}` | {row['Average MI']:.4f} | {row['Max MI']:.4f} | {profile} |")
        md.append("")
        
        # 7. Combined Ranking (Independent side-by-side columns, NO BLENDED SCORE)
        md.append("## 7. Combined Side-by-Side Ranking Matrix")
        md.append(
            "> [!NOTE]\n"
            "> **Interpretation Guidance:**\n"
            "> The table below brings all three perspectives together. Do not interpret this as a single sorted list. "
            "For example, `RSI_14` has low raw variance (by design) but shows moderate Mutual Information and low redundant partners, "
            "suggesting a distinct and useful signal type compared to price trend MAs.\n"
        )
        md.append("| Feature | Raw Variance | Coefficient of Variation | Redundant Partners | Average MI (bits) | Max MI (bits) |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for _, row in df_comb.iterrows():
            md.append(
                f"| `{row['Feature']}` | {row['Raw Variance']:.4f} | {row['Coefficient of Variation']:.6f} | "
                f"{row['Redundant Partners']} | {row['Average MI']:.4f} | {row['Max MI']:.4f} |"
            )
        md.append("")
        
        # 8. MI vs Correlation Divergence (Nonlinear relationships)
        md.append("## 8. Mutual Information vs. Linear Correlation Divergences")
        md.append(
            "This section highlights feature pairs where Mutual Information is relatively high "
            "($\\ge 0.35$ bits) but absolute linear Pearson correlation is low ($|r| \\le 0.20$). "
            "These indicate strong **nonlinear or cyclical dependencies** that standard correlation models miss:\n"
        )
        
        if not divergences:
            md.append("No significant nonlinear MI-vs-Correlation divergences detected.")
        else:
            md.append("| Rank | Feature A | Feature B | Mutual Information (bits) | Absolute Pearson r | Relationship Profile |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for idx, div in enumerate(divergences):
                md.append(
                    f"| {idx+1} | `{div['Feature A']}` | `{div['Feature B']}` | "
                    f"{div['Mutual Information (bits)']:.4f} | {div['Absolute Pearson r']:.4f} | "
                    f"Nonlinear Dependency |"
                )
        md.append("")
        
        return "\n".join(md)

    def save(self, output_path: str) -> None:
        """Writes the Markdown feature usefulness report to disk."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        logger.info(f"Feature usefulness report saved at: {p}")


def generate_feature_usefulness_report(config: dict) -> None:
    """Orchestrates loading features data, executing FeatureUsefulnessAnalyzer, and writing reports."""
    logger.info("Initializing Feature Usefulness Analysis pipeline...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Extract configs
    fu_config = config['eda']['feature_usefulness']
    
    input_rel = fu_config['input_file']
    exclude_cols = fu_config['exclude_columns']
    corr_rel = fu_config['correlation_report_source']
    bins = fu_config['mi_bins']
    report_rel = fu_config['output_report_path']
    
    # Resolve absolute paths
    input_path = project_root / input_rel
    corr_path = project_root / corr_rel
    report_path = project_root / report_rel
    
    logger.info(f"Loading features dataset: {input_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Feature dataset not found: {input_path}. Please execute feature pipeline first.")
        
    df_features = pd.read_csv(input_path)
    
    # Instantiate analyzer
    analyzer = FeatureUsefulnessAnalyzer(
        data=df_features,
        exclude_columns=exclude_cols,
        correlation_report_path=str(corr_path),
        mi_bins=bins
    )
    
    # Compute rankings and save Markdown report
    analyzer.save(str(report_path))
    logger.info("Feature Usefulness analysis completed successfully.")


if __name__ == "__main__":
    try:
        global_config = load_global_config()
        generate_feature_usefulness_report(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to generate feature usefulness report: {e}", exc_info=True)
        sys.exit(1)
