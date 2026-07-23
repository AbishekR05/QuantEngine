import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("scaling")

class ScalingAdvisor:
    """
    Examines feature distribution characteristics (skewness, excess kurtosis,
    natural boundaries, and overlap outlier flags) to recommend a scaling approach
    per feature. Does not apply any data modifications.
    """
    def __init__(self, data: pd.DataFrame, statistics_source: Any = None,
                 outlier_source: Any = None, bounded_columns: List[str] = None,
                 exclude_columns: List[str] = None):
        self.data = data.copy()
        self.exclude_columns = exclude_columns or ["Date"]
        self.bounded_columns = bounded_columns or ["RSI_14"]
        
        # Resolve statistics_source
        if statistics_source is None:
            from src.eda.statistics import StatisticalAnalyzer
            stat_analyzer = StatisticalAnalyzer(self.data, "nifty_features", self.exclude_columns)
            self.stats_df = stat_analyzer.compute_all()
        elif isinstance(statistics_source, pd.DataFrame):
            self.stats_df = statistics_source
        else:
            self.stats_df = statistics_source.compute_all()
            
        # Resolve outlier_source
        if outlier_source is None:
            from src.eda.outlier_analysis import OutlierAnalyzer
            global_config = load_global_config().model_dump()
            known_events_path = global_config["eda"]["outliers"]["known_events_path"]
            out_analyzer = OutlierAnalyzer(self.data, "nifty_features", known_events_path, self.exclude_columns)
            self.outliers_df = out_analyzer.outlier_summary()
        elif isinstance(outlier_source, pd.DataFrame):
            self.outliers_df = outlier_source
        else:
            self.outliers_df = outlier_source.outlier_summary()

        # Select columns for scaling recommendations
        num_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        self.analysis_columns = [col for col in num_cols if col not in self.exclude_columns]

    def recommend_scaler(self, column: str) -> Dict[str, str]:
        """Determines scaling recommendation and reason for a single column."""
        # Handle labels or excluded metadata
        if "Label" in column or column in self.exclude_columns:
            return {
                "scaler": "None",
                "reason": "Date column, identifier key, or target label. Scaling is omitted to preserve target semantics."
            }
            
        # Handle bounded columns (e.g. RSI_14)
        if column in self.bounded_columns:
            return {
                "scaler": "MinMaxScaler",
                "reason": f"Naturally bounded indicator (conceptual range 0-100 for {column}). MinMaxScaler preserves the bounded range interpretation."
            }
            
        # Retrieve skewness and kurtosis
        skew_val = 0.0
        kurt_val = 0.0
        if not self.stats_df.empty and column in self.stats_df["Column"].values:
            row = self.stats_df[self.stats_df["Column"] == column].iloc[0]
            try:
                skew_val = float(row["skew"]) if row["skew"] != "N/A" else 0.0
                kurt_val = float(row["kurt"]) if row["kurt"] != "N/A" else 0.0
            except (ValueError, TypeError):
                pass
                
        # Retrieve overlap outlier counts
        overlap_count = 0
        if not self.outliers_df.empty and column in self.outliers_df["Column"].values:
            row = self.outliers_df[self.outliers_df["Column"] == column].iloc[0]
            try:
                overlap_count = int(row["Overlap Count"])
            except (ValueError, TypeError):
                pass
                
        # Robust vs Standard scaling logic
        if overlap_count > 0 or abs(skew_val) >= 1.0 or kurt_val >= 3.0:
            return {
                "scaler": "RobustScaler",
                "reason": f"Heavy-tailed distribution (skew={skew_val:+.2f}, excess kurtosis={kurt_val:+.2f}) with {overlap_count} confirmed real-event outliers. RobustScaler uses median/IQR to resist outliers."
            }
            
        return {
            "scaler": "StandardScaler",
            "reason": f"Symmetric distribution (skew={skew_val:+.2f}, excess kurtosis={kurt_val:+.2f}) with no confirmed outliers. StandardScaler rescales to zero mean and unit variance."
        }

    def recommend_all(self) -> pd.DataFrame:
        """Generates scaler recommendations for all analyzed numeric features."""
        recs = []
        for col in self.analysis_columns:
            # Skip targets explicitly
            if "Label" in col:
                continue
            rec = self.recommend_scaler(col)
            recs.append({
                "Feature": col,
                "Recommended Scaler": rec["scaler"],
                "Justification": rec["reason"]
            })
        return pd.DataFrame(recs)

    def to_markdown(self) -> str:
        """Formats scaling recommendations and Phase 3 caveats into a Markdown report."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        df_recs = self.recommend_all()
        
        md = []
        md.append("# QuantEngine: Feature Scaling Recommendation Report")
        md.append(f"**Report Generated At**: {timestamp}")
        md.append("**Source Dataset**: `nifty_features`")
        md.append(f"**Configuration Bounded Columns**: {self.bounded_columns}\n")
        
        # 1. Non-Action Statement (Strict Compliance Requirement)
        md.append("## 1. Explicit Non-Action Statement")
        md.append(
            "> [!IMPORTANT]\n"
            "> **Descriptive Recommendation Framework Directive:**\n"
            "> *This report provides scaling recommendations only. No column in nifty_features.csv has been scaled, "
            "transformed, or modified. Scaler selection and fitting should occur later, during model-specific pipeline "
            "construction in Phase 3, using only training-fold statistics to avoid leakage.*\n"
        )
        
        # 2. Time-Series Train/Test Leakage Caution (Strict Compliance Requirement)
        md.append("## 2. Forward-Looking Time-Series Leakage warning")
        md.append(
            "> [!WARNING]\n"
            "> **Supervised Data-Leakage Caveat:**\n"
            "> In time-series machine learning pipelines, scalers must **never** be fitted on the entire dataset. "
            "Fitting a `StandardScaler`, `MinMaxScaler`, or `RobustScaler` on the entire series prior to splitting "
            "will inject future distribution statistics (mean, variance, bounds) into earlier periods, causing severe lookahead bias. "
            "Instead, the scaler must be initialized and **fitted strictly on the training folds**, and then applied "
            "(transform only) to the validation and testing splits.\n"
        )
        
        # 3. Column Recommendation Table
        md.append("## 3. Per-Column Scaling Recommendations")
        md.append("Below is the recommendation matrix generated based on skewness, tails, and outlier statistics:")
        md.append("| Rank | Feature | Recommended Scaler | Justification |")
        md.append("| :--- | :--- | :--- | :--- |")
        for idx, row in df_recs.reset_index().iterrows():
            md.append(f"| {idx+1} | `{row['Feature']}` | **{row['Recommended Scaler']}** | {row['Justification']} |")
        md.append("")
        
        # 4. Special Case: Volume Discussion (Section 5 Compliance)
        md.append("## 4. Special Case Analysis: Trading Volume")
        md.append(
            "Volume warrants specialized treatment compared to regular numerical oscillators or moving averages due to three "
            "compounding statistical characteristics established in prior steps:\n\n"
            "1. **Zero-Inflation**: Volume displays ~29% zero values because of the 2007–2013 calculation feed limitation documented in Step 5.\n"
            "2. **Massive Skewness & Variance**: Volume possesses a high variance profile (Coefficient of Variation $\\approx 0.95$).\n"
            "3. **Extreme Outliers**: Confirming Step 5's chronology, Volume contains numerous high-side outliers matching high-volatility events.\n\n"
            "**Modeling Guidance for Phase 3:**\n"
            "- A plain `RobustScaler` is recommended if Volume is used directly. However, standard practice for volume-like indicators "
            "is to apply a **log-transform** (e.g. `log1p(Volume)` to handle zeros gracefully) prior to scaler fitting. "
            "This compresses the high-end right-side tail, making subsequent scaling significantly more effective.\n"
            "- *Note: Consistent with the project's 'no automated modifications' rules, no log-transform has been applied to nifty_features.csv. "
            "This transform should be evaluated as an active preprocessing node in the training pipeline.*"
        )
        md.append("")
        
        # 5. RSI Special Note (Section 6 Compliance)
        md.append("## 5. Bounded Indicator Analysis: RSI")
        md.append(
            "**RSI_14 Natural Boundaries:**\n"
            "- Relative Strength Index (`RSI_14`) is mathematically bounded between `0.0` and `100.0` by construction. "
            "A `MinMaxScaler` is formally recommended here to preserve this bounded range. "
            "However, because RSI already exists within a known, small-scale bounded distribution (unlike raw price levels which "
            "have no theoretical ceiling), scaling RSI is largely a formality and can be omitted in models resistant to "
            "scale differences (e.g., decision tree ensembles).\n"
        )
        
        # 6. Returns Scaling Note (Section 8 Compliance)
        md.append("## 6. Return Indicators Analysis: Daily Return vs. Log Return")
        md.append(
            "**Scale Magnitude on Returns:**\n"
            "- Both `Daily_Return` and `Log_Return` display outlier overlap and high excess kurtosis, resulting in a `RobustScaler` recommendation. "
            "However, returns are already centered near zero and occupy small-magnitude scales (values ranging roughly between $\\pm 0.01$ and $\\pm 0.05$). "
            "The practical impact of scaling returns is significantly smaller than scaling raw price indicators (which lie in the thousands). "
            "Scaling returns is primarily useful for distance-based ML classifiers (e.g. K-Nearest Neighbors or Support Vector Machines)."
        )
        md.append("")
        
        # 7. Structural Near-Duplicates (Section 8 Compliance)
        md.append("## 7. Structural Near-Duplicate Features")
        md.append(
            "Features that are structural duplicates (such as `Close` and `Adj Close`, or `SMA_20` and `BB_Middle`) display "
            "identical statistical distributions. Consequently, they naturally receive identical scaler recommendations. "
            "This is expected and mathematically correct, rather than a redundant computation error.\n"
        )
        
        return "\n".join(md)

    def save(self, output_path: str) -> None:
        """Writes the scaling recommendation report markdown to disk."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        logger.info(f"Scaling recommendation report saved at: {p}")


def generate_scaling_report(config: dict) -> None:
    """Orchestrates loading features data, executing ScalingAdvisor, and saving reports."""
    logger.info("Initializing Feature Scaling Recommendation pipeline...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Extract configs
    s_config = config['eda']['scaling']
    input_file = config['eda']['feature_usefulness']['input_file']
    exclude_cols = config['eda']['feature_usefulness']['exclude_columns']
    bounded = s_config['bounded_columns']
    report_rel = s_config['output_report_path']
    
    # Resolve absolute paths
    input_path = project_root / input_file
    report_path = project_root / report_rel
    
    logger.info(f"Loading features dataset: {input_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Feature dataset not found: {input_path}. Please execute feature loader.")
        
    df_features = pd.read_csv(input_path)
    
    # Instantiate advisor
    advisor = ScalingAdvisor(
        data=df_features,
        bounded_columns=bounded,
        exclude_columns=exclude_cols
    )
    
    # Generate and save Markdown report
    advisor.save(str(report_path))
    logger.info("Feature Scaling Recommendation completed successfully.")


if __name__ == "__main__":
    try:
        global_config = load_global_config()
        generate_scaling_report(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to generate scaling recommendations: {e}", exc_info=True)
        sys.exit(1)
