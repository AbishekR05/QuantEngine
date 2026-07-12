import sys
import os
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

# Headless backend for Matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("correlations")

class CorrelationAnalyzer:
    """
    Computes Pearson and Spearman correlation matrices for numeric features,
    plots visual heatmaps, identifies redundant clusters and potential leakage,
    and documents observations in a structured report.
    """
    def __init__(self, data: pd.DataFrame, dataset_name: str, exclude_columns: List[str] = None,
                 high_corr_threshold: float = 0.9, leakage_threshold: float = 0.99,
                 top_n_pairs: int = 20, heatmap_output_dir: str = "reports/eda/figures/",
                 dpi: int = 150):
        self.data = data.copy()
        self.dataset_name = dataset_name
        self.exclude_columns = exclude_columns or ["Date"]
        self.high_corr_threshold = high_corr_threshold
        self.leakage_threshold = leakage_threshold
        self.top_n_pairs = top_n_pairs
        self.heatmap_output_dir = Path(heatmap_output_dir)
        self.dpi = dpi
        
        # Ensure heatmap directory exists
        self.heatmap_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine analysis columns (numerical minus exclusions)
        num_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        self.analysis_columns = [col for col in num_cols if col not in self.exclude_columns]
        
        # Restrict dataframe to analysis columns
        self.analysis_df = self.data[self.analysis_columns]

    def pearson_matrix(self) -> pd.DataFrame:
        """Computes the full pairwise Pearson correlation matrix."""
        return self.analysis_df.corr(method="pearson")

    def spearman_matrix(self) -> pd.DataFrame:
        """Computes the full pairwise Spearman correlation matrix."""
        return self.analysis_df.corr(method="spearman")

    def ranked_pairs(self, method: str = "pearson") -> pd.DataFrame:
        """
        Ranks all unique feature pairs by their absolute correlation coefficients.
        Returns a DataFrame sorted descending by |Correlation|.
        """
        corr_matrix = self.pearson_matrix() if method.lower() == "pearson" else self.spearman_matrix()
        cols = corr_matrix.columns
        
        pairs = []
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                col1, col2 = cols[i], cols[j]
                val = corr_matrix.iloc[i, j]
                # In case of constant columns (NaN correlation)
                if pd.isna(val):
                    abs_val = -1.0  # Put NaNs at the end
                else:
                    abs_val = abs(val)
                pairs.append({
                    "Feature A": col1,
                    "Feature B": col2,
                    "Correlation": val,
                    "Abs_Correlation": abs_val
                })
                
        df_pairs = pd.DataFrame(pairs)
        if df_pairs.empty:
            return pd.DataFrame(columns=["Feature A", "Feature B", "Correlation", "Abs_Correlation"])
            
        df_pairs = df_pairs.sort_values(by="Abs_Correlation", ascending=False)
        # Restore NaN markers for constant columns
        df_pairs.loc[df_pairs["Abs_Correlation"] == -1.0, ["Correlation", "Abs_Correlation"]] = np.nan
        return df_pairs

    def high_correlation_pairs(self, method: str = "pearson") -> pd.DataFrame:
        """Returns feature pairs exceeding the configured high_corr_threshold."""
        df_ranked = self.ranked_pairs(method)
        if df_ranked.empty:
            return df_ranked
        return df_ranked[df_ranked["Abs_Correlation"] >= self.high_corr_threshold]

    def flag_redundant_features(self, method: str = "pearson") -> List[List[str]]:
        """
        Finds clusters of highly correlated features using a connected components algorithm.
        Returns a list of groups where components are closely linked.
        """
        df_corr = self.pearson_matrix() if method.lower() == "pearson" else self.spearman_matrix()
        cols = df_corr.columns.tolist()
        
        # Build adjacency graph for highly correlated variables
        adj = {c: set() for c in cols}
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                col1, col2 = cols[i], cols[j]
                val = df_corr.iloc[i, j]
                if not pd.isna(val) and abs(val) >= self.high_corr_threshold:
                    adj[col1].add(col2)
                    adj[col2].add(col1)
                    
        # Compute connected components
        visited = set()
        components = []
        for col in cols:
            if col not in visited:
                comp = []
                queue = [col]
                visited.add(col)
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                if len(comp) >= 2:
                    components.append(sorted(comp))
                    
        return components

    def flag_potential_leakage(self, method: str = "pearson") -> pd.DataFrame:
        """Identifies feature pairs with suspicious correlation values approaching 1.0 (>= leakage_threshold)."""
        df_ranked = self.ranked_pairs(method)
        if df_ranked.empty:
            return df_ranked
        return df_ranked[df_ranked["Abs_Correlation"] >= self.leakage_threshold]

    def correlation_divergence(self, threshold: float = 0.20) -> pd.DataFrame:
        """
        Flags column pairs where Pearson (linear) and Spearman (monotonic rank)
        correlation values diverge significantly.
        """
        p_matrix = self.pearson_matrix()
        s_matrix = self.spearman_matrix()
        cols = p_matrix.columns.tolist()
        
        divergences = []
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                col1, col2 = cols[i], cols[j]
                p_val = p_matrix.iloc[i, j]
                s_val = s_matrix.iloc[i, j]
                
                if pd.isna(p_val) or pd.isna(s_val):
                    continue
                    
                diff = abs(p_val - s_val)
                if diff >= threshold:
                    divergences.append({
                        "Feature A": col1,
                        "Feature B": col2,
                        "Pearson": p_val,
                        "Spearman": s_val,
                        "Difference": p_val - s_val,
                        "Abs_Difference": diff
                    })
                    
        df_div = pd.DataFrame(divergences)
        if df_div.empty:
            return pd.DataFrame(columns=["Feature A", "Feature B", "Pearson", "Spearman", "Difference", "Abs_Difference"])
        return df_div.sort_values(by="Abs_Difference", ascending=False)

    def _annotate_pair_reason(self, col1: str, col2: str) -> str:
        """Annotates expected, known-by-construction feature correlations."""
        c1, c2 = col1.lower(), col2.lower()
        
        # Close & Adj Close
        if ("close" in c1 and "close" in c2) and ("adj" in c1 or "adj" in c2):
            return "Identical by construction; representing index close values without dividend distributions."
            
        # OHLC snapshots
        ohlc = ["open", "high", "low", "close", "adj close"]
        if c1 in ohlc and c2 in ohlc:
            return "Structural intraday price markers representing snapshots of the same daily session."
            
        # Bollinger Bands & SMA_20
        bb_sma = ["sma_20", "ema_20", "bb_middle"]
        if c1 in bb_sma and c2 in bb_sma:
            return "BB Middle Band is mathematically equivalent to SMA_20 by configuration design."
            
        # MACD & MACD_Signal
        if "macd" in c1 and "macd" in c2:
            return "MACD Signal is computed as a smoothed exponential moving average of MACD."
            
        # Returns
        if "return" in c1 and "return" in c2:
            return "Daily return and log return are mathematically near-identical for typical daily percentage shifts."
            
        # Similarly configured averages (e.g. SMA_50 vs EMA_50)
        n1 = re.findall(r'\d+', col1)
        n2 = re.findall(r'\d+', col2)
        if n1 and n2 and n1[0] == n2[0] and ("sma" in c1 or "ema" in c1) and ("sma" in c2 or "ema" in c2):
            return f"Moving averages of the same window length ({n1[0]}) tracking the same smoothed price wave."
            
        return "Standard correlation expected between lagging price indicators."

    def plot_heatmap(self, method: str = "pearson") -> str:
        """Renders and saves a high-quality correlation matrix heatmap using Matplotlib."""
        df_corr = self.pearson_matrix() if method.lower() == "pearson" else self.spearman_matrix()
        
        fig, ax = plt.subplots(figsize=(12, 10))
        # Draw matrix grid using coolwarm
        cax = ax.imshow(df_corr.values, cmap='coolwarm', vmin=-1.0, vmax=1.0)
        
        # Color bar indicator
        fig.colorbar(cax, fraction=0.046, pad=0.04)
        
        # Tick parameters
        ticks = np.arange(len(df_corr.columns))
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_xticklabels(df_corr.columns, fontsize=8, rotation=45, ha='right')
        ax.set_yticklabels(df_corr.columns, fontsize=8)
        
        # Draw correlation values text in cells
        for i in range(len(df_corr.columns)):
            for j in range(len(df_corr.columns)):
                val = df_corr.iloc[i, j]
                if pd.isna(val):
                    text_val = "NaN"
                    color = "black"
                else:
                    text_val = f"{val:.2f}"
                    color = 'black' if abs(val) < 0.6 else 'white'
                ax.text(j, i, text_val, ha='center', va='center', color=color, fontsize=7)
                
        timestamp = time.strftime("%Y-%m-%d")
        title = f"Correlation Heatmap ({method.upper()}) - {self.dataset_name}\nGenerated: {timestamp}"
        ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
        
        out_path = self.heatmap_output_dir / f"correlation_heatmap_{method.lower()}.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.info(f"Saved {method.upper()} heatmap at: {out_path}")
        return str(out_path)

    def to_markdown(self) -> str:
        """Formats correlation analysis observations into a complete Markdown report."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        md = []
        md.append(f"# QuantEngine: Feature Correlation Analysis Report")
        md.append(f"**Report Generated At**: {timestamp}")
        md.append(f"**Number of Analyzed Features**: {len(self.analysis_columns)}\n")
        
        # 1. Methodology explanation
        md.append("## 1. Methodology Summary")
        md.append(
            "This report evaluates pairwise linear (**Pearson**) and rank-based (**Spearman**) "
            "correlations between all technical indicators.\n"
            "- **Pearson correlation** captures linear relationships. It assumes normal distributions.\n"
            "- **Spearman correlation** evaluates monotonic relationships and is less sensitive to extreme outliers "
            "or nonlinear mappings. Disagreements between Pearson and Spearman reveal non-linear patterns.\n"
            "Constant columns yield `NaN` values. Pairwise correlations skip missing data (warm-up periods) dynamically.\n"
        )
        
        # 2. Top-N ranked pairs
        md.append("## 2. Highest Correlation Pairs (Top Ranked)")
        
        for method in ["pearson", "spearman"]:
            md.append(f"### Top {self.top_n_pairs} Pairs: {method.upper()}")
            md.append("| Rank | Feature A | Feature B | Coefficient | Abs Value |")
            md.append("| :--- | :--- | :--- | :--- | :--- |")
            
            df_ranked = self.ranked_pairs(method).head(self.top_n_pairs)
            for idx, row in df_ranked.reset_index().iterrows():
                coef = row['Correlation']
                coef_str = f"{coef:.4f}" if not pd.isna(coef) else "N/A"
                abs_str = f"{row['Abs_Correlation']:.4f}" if not pd.isna(row['Abs_Correlation']) else "N/A"
                md.append(f"| {idx+1} | `{row['Feature A']}` | `{row['Feature B']}` | {coef_str} | {abs_str} |")
            md.append("")
            
        # 3. High Correlation & Annotations
        md.append(f"## 3. Redundancy & Domain Observations ($|r| \\ge {self.high_corr_threshold}$)")
        df_high = self.high_correlation_pairs("pearson")
        
        if df_high.empty:
            md.append(f"No feature pairs exceed the correlation threshold of {self.high_corr_threshold}.")
        else:
            md.append(f"The following feature pairs exhibit strong correlations (above threshold {self.high_corr_threshold}):")
            md.append("| Feature A | Feature B | Pearson $r$ | Context / Domain Caveat |")
            md.append("| :--- | :--- | :--- | :--- |")
            for _, row in df_high.iterrows():
                reason = self._annotate_pair_reason(row['Feature A'], row['Feature B'])
                md.append(f"| `{row['Feature A']}` | `{row['Feature B']}` | {row['Correlation']:.4f} | {reason} |")
        md.append("")
        
        # 4. Redundant clusters
        md.append("## 4. Redundant Feature Groupings")
        md.append(
            "Below are groups of features clustered together via connected components "
            f"where every connection has an absolute Pearson correlation $\\ge {self.high_corr_threshold}$."
            " Sparing one variable per group is advised during model feature selection:\n"
        )
        redundant_groups = self.flag_redundant_features("pearson")
        if not redundant_groups:
            md.append("No redundant groups detected.")
        else:
            for idx, group in enumerate(redundant_groups):
                features_list = ", ".join([f"`{f}`" for f in group])
                md.append(f"**Group {idx+1}**: [{features_list}]")
        md.append("")
        
        # 5. Potential Leakage flags
        md.append("## 5. Potential Data Leakage / Near-Duplicate Flags")
        df_leak = self.flag_potential_leakage("pearson")
        if df_leak.empty:
            md.append("No suspicious near-perfect correlations (>= {}) detected.".format(self.leakage_threshold))
        else:
            md.append(
                f"> [!WARNING]\n"
                f"> **Potential lookahead/leakage risk detected (Pearson $|r| \\ge {self.leakage_threshold}$):**\n"
                f"> These features are nearly identical. Using both in regression or neural network models "
                f"causes extreme multicollinearity or validation leakage. Review if they represent identical inputs:\n"
            )
            for _, row in df_leak.iterrows():
                md.append(f"> - `{row['Feature A']}` ↔ `{row['Feature B']}` (Correlation: {row['Correlation']:.6f})")
        md.append("")
        
        # 6. Divergence analysis
        md.append("## 6. Pearson vs. Spearman Disagreement (Non-linear Monotonic Patterns)")
        df_div = self.correlation_divergence(0.20)
        if df_div.empty:
            md.append("No significant divergences (|Pearson - Spearman| >= 0.20) detected. Price/indicator relationships remain linear.")
        else:
            md.append(
                "The following indicator pairs show significant difference between Pearson and Spearman coefficients. "
                "This indicates that while the relationship is monotonic, it is highly non-linear:\n"
            )
            md.append("| Feature A | Feature B | Pearson | Spearman | Difference |")
            md.append("| :--- | :--- | :--- | :--- | :--- |")
            for _, row in df_div.iterrows():
                md.append(f"| `{row['Feature A']}` | `{row['Feature B']}` | {row['Pearson']:.4f} | {row['Spearman']:.4f} | {row['Difference']:.4f} |")
        md.append("")
        
        # 7. Visual heatmaps references
        md.append("## 7. Correlation Matrix Heatmaps")
        md.append("Heatmaps are plotted individually for inspection:")
        md.append("### Pearson Linear Correlation")
        md.append("![Pearson Heatmap](../figures/correlation_heatmap_pearson.png)\n")
        md.append("### Spearman Monotonic Correlation")
        md.append("![Spearman Heatmap](../figures/correlation_heatmap_spearman.png)")
        
        return "\n".join(md)

    def save(self, output_path: str) -> None:
        """Writes the generated Markdown correlation report to the specified file path."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        logger.info(f"Correlation report saved at: {p}")


def generate_correlation_report(config: dict) -> None:
    """Orchestrates loading indicators data, running correlation analyzer, and generating heatmaps/reports."""
    logger.info("Initializing Feature Correlation Analyzer pipeline...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Extract configs
    input_rel = config['eda']['correlation']['input_file']
    exclude_cols = config['eda']['correlation']['exclude_columns']
    high_corr_th = config['eda']['correlation']['high_corr_threshold']
    leakage_th = config['eda']['correlation']['leakage_threshold']
    top_n = config['eda']['correlation']['top_n_pairs']
    heatmap_dir_rel = config['eda']['correlation']['heatmap_output_dir']
    report_path_rel = config['eda']['correlation']['report_output_path']
    
    dpi = config['eda']['figures']['dpi']
    
    # Resolve absolute paths
    input_path = project_root / input_rel
    heatmap_dir = project_root / heatmap_dir_rel
    report_path = project_root / report_path_rel
    
    logger.info(f"Target Indicators CSV: {input_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Feature dataset not found: {input_path}. Run pipeline orchestrator first.")
        
    df_features = pd.read_csv(input_path)
    
    # Initialize Correlation Analyzer
    analyzer = CorrelationAnalyzer(
        data=df_features,
        dataset_name="nifty_features",
        exclude_columns=exclude_cols,
        high_corr_threshold=high_corr_th,
        leakage_threshold=leakage_th,
        top_n_pairs=top_n,
        heatmap_output_dir=str(heatmap_dir),
        dpi=dpi
    )
    
    # Generate Heatmaps
    analyzer.plot_heatmap("pearson")
    analyzer.plot_heatmap("spearman")
    
    # Save Report
    analyzer.save(str(report_path))
    logger.info("Feature Correlation reports generated successfully.")


if __name__ == "__main__":
    try:
        global_config = load_global_config()
        generate_correlation_report(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to generate correlations: {e}", exc_info=True)
        sys.exit(1)
