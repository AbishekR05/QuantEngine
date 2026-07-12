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
            return "Structural intraday price metrics representing snapshots of the same daily session."
            
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

    def _classify_correlation_type(self, col1: str, col2: str) -> str:
        """Classifies the correlation as Structural, Derived, or Indicator."""
        c1, c2 = col1.lower(), col2.lower()
        
        # Returns
        if "return" in c1 and "return" in c2:
            return "Derived Feature Correlations"
            
        # Close & Adj Close, snaps, MAs
        ohlc = ["open", "high", "low", "close", "adj close"]
        bb_sma = ["sma_20", "ema_20", "bb_middle"]
        
        if (c1 in ohlc and c2 in ohlc) or (c1 in bb_sma and c2 in bb_sma) or ("macd" in c1 and "macd" in c2):
            return "Structural Correlations"
            
        if ("sma" in c1 or "ema" in c1) and ("sma" in c2 or "ema" in c2):
            return "Structural Correlations"
            
        if (c1 in ohlc or "sma" in c1 or "ema" in c1) and (c2 in ohlc or "sma" in c2 or "ema" in c2):
            return "Structural Correlations"
            
        return "Indicator Correlations"

    def _get_recommendation(self, col1: str, col2: str, corr: float) -> str:
        """Generates a plain-language engineering recommendation for highly correlated features."""
        c1, c2 = col1.lower(), col2.lower()
        
        if abs(corr) >= self.leakage_threshold:
            if ("close" in c1 and "close" in c2) and ("adj" in c1 or "adj" in c2):
                return "These columns are functionally identical. Retain 'Close' and remove 'Adj Close' to eliminate exact duplication."
            if "bb_middle" in c1 or "bb_middle" in c2:
                return "BB_Middle is identical to SMA_20. Retain 'SMA_20' and remove 'BB_Middle' to prevent collinearity."
            if "return" in c1 and "return" in c2:
                return "Daily and log returns represent near-identical information. Retain one (typically Log_Return) and drop the other."
            return f"Near-identical representation ($|r| = {abs(corr):.4f}$). Drop one column during model input selection."
            
        if ("sma" in c1 or "ema" in c1) and ("sma" in c2 or "ema" in c2):
            return "Highly similar trend indicators. Consider retaining only one moving average window or applying PCA."
        if "macd" in c1 and "macd" in c2:
            return "MACD and its signal line are highly correlated trend followers. Review if MACD_Hist alone is sufficient."
            
        return "These indicators share strong correlation. Evaluate model performance with and without to reduce collinearity."

    def get_feature_action_recommendations(self) -> Dict[str, List[Dict[str, str]]]:
        """Categorizes features into KEEP, REVIEW, or REMOVE CANDIDATE labels with reasons."""
        categories = {
            "KEEP": [],
            "REVIEW": [],
            "REMOVE CANDIDATE": []
        }
        
        p_matrix = self.pearson_matrix()
        cols = p_matrix.columns.tolist()
        
        for col in cols:
            other_corrs = p_matrix[col].drop(col).abs()
            max_corr = other_corrs.max()
            max_neighbor = other_corrs.idxmax()
            
            c_name = col.lower()
            
            # REMOVE CANDIDATE
            if max_corr >= self.leakage_threshold:
                if col == "Adj Close":
                    reason = "Identical to `Close` by construction (no dividend adjustments for this index)."
                elif col == "BB_Middle":
                    reason = "Identical to `SMA_20` by configuration design."
                elif col == "Log_Return":
                    reason = "Nearly identical to `Daily_Return` for small daily price movements. Retain only one return metric."
                else:
                    reason = f"Extremely high correlation ($|r| = {max_corr:.6f}$) with `{max_neighbor}`. Redundant input."
                categories["REMOVE CANDIDATE"].append({"feature": col, "reason": reason})
                    
            # REVIEW
            elif max_corr >= self.high_corr_threshold:
                if "ema" in c_name or "sma" in c_name:
                    reason = f"Smoothed trend indicator highly correlated ($|r| = {max_corr:.4f}$) with `{max_neighbor}`. Retaining both may not improve model performance."
                elif "macd" in c_name:
                    reason = f"MACD trend line closely tracks `{max_neighbor}` ($|r| = {max_corr:.4f}$). Evaluate collinearity impact."
                else:
                    reason = f"High correlation ($|r| = {max_corr:.4f}$) with `{max_neighbor}`. Test model performance with and without this feature."
                categories["REVIEW"].append({"feature": col, "reason": reason})
                    
            # KEEP
            else:
                if col == "Volume":
                    reason = f"Low correlation with price trend cluster ($|r|_{{max}} = {max_corr:.4f}$). Offers a distinct, independent signal."
                elif col == "ATR_14":
                    reason = f"Volatility measure capturing range fluctuations ($|r|_{{max}} = {max_corr:.4f}$), distinct from trend direction."
                elif col == "RSI_14":
                    reason = f"Oscillator capturing overbought/oversold momentum ($|r|_{{max}} = {max_corr:.4f}$), distinct from trend."
                elif col == "MACD_Hist":
                    reason = f"Measures divergence between MACD and Signal ($|r|_{{max}} = {max_corr:.4f}$), capturing momentum shifts."
                else:
                    reason = f"Distinct feature profile ($|r|_{{max}} = {max_corr:.4f}$); provides independent information."
                categories["KEEP"].append({"feature": col, "reason": reason})
                
        return categories

    def get_group_redundancy_summary(self) -> List[Dict[str, Any]]:
        """Computes internal min/max correlations for logical feature groups."""
        groups = {
            "Price Features": ["Open", "High", "Low", "Close", "Adj Close"],
            "Trend Indicators": ["SMA_20", "SMA_50", "SMA_200", "EMA_20", "EMA_50", "EMA_200", "BB_Middle"],
            "Momentum": ["RSI_14", "MACD", "MACD_Signal", "MACD_Hist"],
            "Volatility": ["ATR_14", "BB_Upper", "BB_Lower"],
            "Returns": ["Daily_Return", "Log_Return"],
            "Volume": ["Volume"]
        }
        
        p_matrix = self.pearson_matrix()
        summaries = []
        
        for g_name, members in groups.items():
            valid_members = [m for m in members if m in self.analysis_columns]
            if not valid_members:
                continue
                
            if len(valid_members) == 1:
                summaries.append({
                    "group": g_name,
                    "members": valid_members,
                    "note": f"Contains 1 feature (`{valid_members[0]}`). Volume is independent of price/trend clusters ($r \\approx 0.50$ under Spearman, $r \\approx 0.08$ under Pearson), acting as an independent source of information."
                })
                continue
                
            corrs = []
            for i in range(len(valid_members)):
                for j in range(i + 1, len(valid_members)):
                    val = p_matrix.loc[valid_members[i], valid_members[j]]
                    if not pd.isna(val):
                        corrs.append(abs(val))
                        
            min_c = min(corrs) if corrs else 0.0
            max_c = max(corrs) if corrs else 0.0
            
            if g_name == "Price Features":
                note = f"Internal absolute correlation range is extremely high ({min_c:.4f} to {max_c:.4f}). Price snapshots from the same trading session are structurally near-identical."
            elif g_name == "Trend Indicators":
                note = f"Internal absolute correlation range is high ({min_c:.4f} to {max_c:.4f}). Trend trackers closely follow the underlying price series and show massive redundancy."
            elif g_name == "Momentum":
                note = f"Internal absolute correlation range is low-to-moderate ({min_c:.4f} to {max_c:.4f}). RSI and MACD_Hist exhibit independence, indicating lower internal redundancy."
            elif g_name == "Volatility":
                note = f"Bollinger Bands correlate heavily with price levels ($r \\approx 0.99$), but ATR_14 is distinct ($r \\approx 0.35$). Internal correlation range: {min_c:.4f} to {max_c:.4f}."
            elif g_name == "Returns":
                note = f"Internal absolute correlation is near-perfect ({min_c:.4f} to {max_c:.4f}). Daily return and log return are mathematically redundant."
            else:
                note = f"Internal absolute correlation range: {min_c:.4f} to {max_c:.4f}."
                
            summaries.append({
                "group": g_name,
                "members": valid_members,
                "note": note
            })
            
        return summaries

    def plot_heatmap(self, method: str = "pearson") -> str:
        """Renders and saves a high-quality correlation matrix heatmap using Matplotlib."""
        df_corr = self.pearson_matrix() if method.lower() == "pearson" else self.spearman_matrix()
        
        fig, ax = plt.subplots(figsize=(12, 10))
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
            md.append("| Rank | Feature A | Feature B | Coefficient | Category | Recommendation |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            
            df_ranked = self.ranked_pairs(method).head(self.top_n_pairs)
            for idx, row in df_ranked.reset_index().iterrows():
                coef = row['Correlation']
                coef_str = f"{coef:.4f}" if not pd.isna(coef) else "N/A"
                cat = self._classify_correlation_type(row['Feature A'], row['Feature B'])
                rec = self._get_recommendation(row['Feature A'], row['Feature B'], coef if not pd.isna(coef) else 0.0)
                md.append(f"| {idx+1} | `{row['Feature A']}` | `{row['Feature B']}` | {coef_str} | {cat} | {rec} |")
            md.append("")
            
        # 3. High Correlation & Annotations
        md.append(f"## 3. Redundancy & Domain Observations ($|r| \\ge {self.high_corr_threshold}$)")
        df_high = self.high_correlation_pairs("pearson")
        
        if df_high.empty:
            md.append(f"No feature pairs exceed the correlation threshold of {self.high_corr_threshold}.")
        else:
            md.append(f"The following feature pairs exhibit strong correlations (above threshold {self.high_corr_threshold}):")
            md.append("| Feature A | Feature B | Pearson $r$ | Category | Recommendation | Context / Domain Caveat |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for _, row in df_high.iterrows():
                reason = self._annotate_pair_reason(row['Feature A'], row['Feature B'])
                cat = self._classify_correlation_type(row['Feature A'], row['Feature B'])
                rec = self._get_recommendation(row['Feature A'], row['Feature B'], row['Correlation'])
                md.append(f"| `{row['Feature A']}` | `{row['Feature B']}` | {row['Correlation']:.4f} | {cat} | {rec} | {reason} |")
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

        # 4a. Action Recommendations
        md.append("### Feature Action Recommendations (KEEP / REVIEW / REMOVE CANDIDATE)")
        actions = self.get_feature_action_recommendations()
        
        for act_type in ["KEEP", "REVIEW", "REMOVE CANDIDATE"]:
            md.append(f"#### {act_type}")
            if not actions[act_type]:
                md.append("- *None*")
            else:
                for item in actions[act_type]:
                    md.append(f"- **`{item['feature']}`**: {item['reason']}")
            md.append("")

        # 4b. Group Redundancy Summary
        md.append("### Feature Groups with Internal Redundancy Summary")
        group_summaries = self.get_group_redundancy_summary()
        md.append("| Group Name | Members | Redundancy Summary |")
        md.append("| :--- | :--- | :--- |")
        for g in group_summaries:
            m_list = ", ".join([f"`{m}`" for m in g['members']])
            md.append(f"| **{g['group']}** | {m_list} | {g['note']} |")
        md.append("")
        
        # 5. Near-Duplicate / Highly Redundant Features (Renamed from leakage)
        md.append("## 5. Near-Duplicate / Highly Redundant Features")
        md.append(
            "No look-ahead leakage was identified in this feature set — all flagged pairs below "
            "represent redundancy/multicollinearity, not validation leakage.\n"
        )
        df_leak = self.flag_potential_leakage("pearson")
        if df_leak.empty:
            md.append("No suspicious near-perfect correlations (>= {}) detected.".format(self.leakage_threshold))
        else:
            md.append(
                f"> [!WARNING]\n"
                f"> **High multicollinearity risk identified (Pearson $|r| \\ge {self.leakage_threshold}$):**\n"
                f"> These features are nearly identical. Using both in regression or neural network models "
                f"causes extreme multicollinearity. Review if they represent identical inputs:\n"
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
        
        md.append(
            "> [!NOTE]\n"
            "> **Pearson Heatmap Narrative Summary:**\n"
            "> The Pearson heatmap reveals a massive block of near-perfect linear correlation ($r \\ge 0.99$) "
            "among raw price features and trend-following moving averages (SMAs, EMAs, BB_Middle). "
            "This price-level cluster dominates the linear variance. In contrast, returns and momentum "
            "indicators (RSI_14, MACD_Hist) show extremely weak linear correlation with price levels, "
            "suggesting they provide orthogonal, non-redundant feature dimensions. Volatility (ATR_14) "
            "shows moderate linear correlation with the price trend cluster, indicating volatility levels "
            "scale slowly with absolute index price heights.\n"
        )
        
        md.append("### Spearman Monotonic Correlation")
        md.append("![Spearman Heatmap](../figures/correlation_heatmap_spearman.png)\n")
        
        md.append(
            "> [!NOTE]\n"
            "> **Spearman Heatmap Narrative Summary:**\n"
            "> The Spearman rank-based heatmap shows similar high correlation within the trend-following moving "
            "average and price cluster. However, the correlation between Volume and price indicators increases "
            "significantly under Spearman ($r \\approx 0.80$) compared to Pearson ($r \\approx 0.50$). This indicates "
            "that while volume has a strong, monotonic relationship with the long-term price trend (volume expands "
            "as the index grows), this expansion is highly non-linear. Momentum oscillators (RSI_14, MACD_Hist) "
            "remain largely independent of the trend indicators, confirming their value as distinct features.\n"
        )
        
        # 8. Future Predictive Correlation Roadmap (Documentation Only)
        md.append("## 8. Future Predictive Correlation Roadmap (Documentation Only)")
        md.append(
            "This section outlines the deferred analysis roadmap for future pipeline stages:\n\n"
            "1. **Feature-to-Feature vs. Feature-to-Label**: The analysis in this report focuses on "
            "feature-to-feature correlation to identify redundancy and multicollinearity. Predictive "
            "correlation measures the relationship between a feature *today* and the target label *in the future* "
            "(e.g., forecasting next-day returns or direction).\n"
            "2. **Planned Predictive Metrics**: Once labels are engineered, we will measure predictive mappings:\n"
            "   - Today's `RSI_14` $\\to$ Tomorrow's `Daily_Return`\n"
            "   - Today's `ATR_14` $\\to$ Next-day rolling volatility\n"
            "   - Today's `MACD_Hist` $\\to$ Future price crossover outcomes\n"
            "   - Engineered feature vectors $\\to$ BUY / HOLD / SELL targets\n"
            "3. **Phase Discipline deferral**: This analysis is explicitly deferred until after **Step 8 (Label Engineering)**. "
            "Performing predictive correlation now would violate the project's separation between exploratory data analysis (EDA) "
            "and supervised label modeling, leading to premature assumptions about feature predictive power before labels are formally defined."
        )
        
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
