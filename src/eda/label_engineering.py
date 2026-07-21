import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("labels")

class LabelEngineer:
    """
    Computes forward-looking classification targets (binary and three-class)
    for supervised learning target labels. Appends them additively to feature data.
    """
    def __init__(self, data: pd.DataFrame, close_column: str = "Close",
                 three_class_threshold: float = 0.005):
        self.data = data.copy()
        self.close_column = close_column
        self.three_class_threshold = three_class_threshold
        
        # Verify close column exists
        if self.close_column not in self.data.columns:
            raise KeyError(f"Price column '{self.close_column}' not found in dataset columns: {self.data.columns.tolist()}")

    def generate_binary_label(self) -> pd.Series:
        """
        Generates binary target labels: 1 if next Close is higher than today, else 0.
        Last row is set to NaN. Exact ties are categorized as class 0.
        """
        close_curr = self.data[self.close_column]
        close_next = self.data[self.close_column].shift(-1)
        
        # 1 if Close(t+1) > Close(t), else 0
        binary_labels = (close_next > close_curr).astype(float)
        
        # Strict last-row NaN compliance
        binary_labels.iloc[-1] = np.nan
        return pd.Series(binary_labels, name="Label_Binary", index=self.data.index)

    def generate_three_class_label(self) -> pd.Series:
        """
        Generates three-class target labels: BUY if next daily return > threshold,
        SELL if next daily return < -threshold, else HOLD. Last row is set to NaN.
        """
        close_curr = self.data[self.close_column]
        close_next = self.data[self.close_column].shift(-1)
        
        # Next-day return calculation
        return_next = (close_next - close_curr) / close_curr
        
        labels = []
        for val in return_next:
            if pd.isna(val):
                labels.append(np.nan)
            elif val > self.three_class_threshold:
                labels.append("BUY")
            elif val < -self.three_class_threshold:
                labels.append("SELL")
            else:
                labels.append("HOLD")
                
        return pd.Series(labels, name="Label_ThreeClass", index=self.data.index)

    def label_distribution(self, label_column: str) -> pd.DataFrame:
        """Computes trading day counts and percentages for a specific label column."""
        if label_column == "Label_Binary":
            series = self.generate_binary_label()
        elif label_column == "Label_ThreeClass":
            series = self.generate_three_class_label()
        else:
            series = self.data[label_column]
            
        counts = series.value_counts(dropna=True)
        total = counts.sum()
        
        dist = []
        for name, cnt in counts.items():
            dist.append({
                "Class": str(name),
                "Count": cnt,
                "Percentage": (cnt / total) * 100.0 if total > 0 else 0.0
            })
            
        # Count NaNs (e.g. last row)
        nan_count = series.isna().sum()
        dist.append({
            "Class": "NaN (Last Row)",
            "Count": nan_count,
            "Percentage": (nan_count / len(series)) * 100.0
        })
        
        return pd.DataFrame(dist)

    def regime_label_cross_reference(self) -> pd.DataFrame:
        """Cross-references daily label distribution against Step 6 market regimes."""
        if "Trend_Regime" not in self.data.columns:
            try:
                global_config = load_global_config().model_dump()
                known_events_path = global_config["eda"]["regime"]["known_events_path"]
                from src.eda.regime_analysis import RegimeAnalyzer
                analyzer = RegimeAnalyzer(
                    data=self.data,
                    known_events_path=known_events_path
                )
                self.data["Trend_Regime"] = analyzer.classify_trend_regime()
            except Exception as e:
                logger.error(f"Failed to load Trend_Regime dynamically: {e}")
                self.data["Trend_Regime"] = "Unknown"
                
        three_class = self.generate_three_class_label()
        
        df_temp = pd.DataFrame({
            "Trend_Regime": self.data["Trend_Regime"],
            "Label_ThreeClass": three_class
        }).dropna()
        
        return pd.crosstab(df_temp["Trend_Regime"], df_temp["Label_ThreeClass"], margins=True)

    def save_labeled_dataset(self, version: str, output_path: str) -> None:
        """Saves features dataset appended with versioned label columns to disk."""
        df_out = self.data.copy()
        if version.lower() == "binary":
            df_out["Label_Binary"] = self.generate_binary_label()
        elif version.lower() == "threeclass":
            df_out["Label_ThreeClass"] = self.generate_three_class_label()
        else:
            raise ValueError(f"Unknown label dataset version: {version}")
            
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(p, index=False)
        logger.info(f"Saved labeled {version} features dataset to: {p}")

    def to_markdown(self) -> str:
        """Formats target label distributions, caveats, and options specifications into a Markdown report."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        dist_bin = self.label_distribution("Label_Binary")
        dist_three = self.label_distribution("Label_ThreeClass")
        crosstab = self.regime_label_cross_reference()
        
        md = []
        md.append("# QuantEngine: Label Engineering Report")
        md.append(f"**Report Generated At**: {timestamp}")
        md.append("**Source Dataset**: `nifty_features`")
        md.append(f"**Configuration Threshold**: Three-Class Return Boundary = ±{self.three_class_threshold * 100:.2f}%\n")
        
        # 1. Supervised Lookahead Warning (Compliance Requirement)
        md.append("## 1. Important Lookahead Warning")
        md.append(
            "> [!WARNING]\n"
            "> **Supervised Target Leakage Caution:**\n"
            "> These label columns are intentionally forward-looking (each label at row $t$ depends on closing price Close at row $t+1$). "
            "This is expected and correct for label data, but these versioned files must **never** be used as a feature-only input set "
            "during ML model training. **Always exclude label columns** (specifically `Label_Binary` and `Label_ThreeClass`) "
            "when using this data for feature extraction. Failing to do so will leak the future closing price into the inputs, "
            "resulting in 100% training accuracy but catastrophic failure in real-time execution.\n"
        )
        
        # 2. Version A
        md.append("## 2. Version A: Binary Classification Summary")
        md.append(
            "- **Rule**: `Label_Binary = 1` if $Close_{t+1} > Close_t$, else `0`.\n"
            "- **Flat Day Policy**: Exact-tie returns ($Close_{t+1} == Close_t$) are grouped into Class 0. This is a deliberate modeling choice "
            "for daily index series where ties are extremely rare but categorized conservatively as non-up days.\n"
            "- **Last Row Policy**: The final row has no future period ($t+1$) to compare against and is strictly populated with `NaN` (null) "
            "to prevent lookahead extrapolation.\n"
        )
        md.append("### Class Distribution (Binary)")
        md.append("| Class | Count | Percentage |")
        md.append("| :--- | :--- | :--- |")
        for _, row in dist_bin.iterrows():
            md.append(f"| {row['Class']} | {row['Count']} | {row['Percentage']:.2f}% |")
        md.append("")
        
        # 3. Version B
        md.append("## 3. Version B: Three-Class Classification Summary")
        md.append(
            f"- **Rule**: Return $R_{{t+1}} = (Close_{{t+1}} - Close_t) / Close_t$\n"
            f"  - **BUY**: $R_{{t+1}} > +{self.three_class_threshold:.4f}$ (+{self.three_class_threshold * 100:.2f}%)\n"
            f"  - **SELL**: $R_{{t+1}} < -{self.three_class_threshold:.4f}$ (-{self.three_class_threshold * 100:.2f}%)\n"
            f"  - **HOLD**: otherwise (including exact-tie zero returns)\n"
            f"- **Last Row Policy**: strictly populated with `NaN` (null).\n"
            f"- **Imbalance / Sensitivity**: The threshold is config-driven. A tight threshold (e.g. 0.50% daily) means "
            f"class distributions are naturally sensitive; larger thresholds will compress BUY/SELL counts and inflate HOLD counts. "
            f"Observe the resulting imbalance below to configure classification loss weights in Phase 3.\n"
        )
        md.append("### Class Distribution (Three-Class)")
        md.append("| Class | Count | Percentage |")
        md.append("| :--- | :--- | :--- |")
        for _, row in dist_three.iterrows():
            md.append(f"| {row['Class']} | {row['Count']} | {row['Percentage']:.2f}% |")
        md.append("")
        
        # 4. Cross-Reference Sanity Check
        md.append("## 4. Regime vs. Class Label Cross-Reference Table")
        md.append(
            "Descriptive cross-tabulation checking label behavior across Step 6 trend regimes. "
            "Expected market behavior dictates BUY frequencies should be higher in Bull regimes, while SELL frequencies should expand in Bear regimes:\n"
        )
        headers = ["Trend Regime \\ Class"] + crosstab.columns.tolist()
        md.append("| " + " | ".join(headers) + " |")
        md.append("| " + " | ".join([":---"] * len(headers)) + " |")
        for idx, row in crosstab.iterrows():
            line = [f"**{idx}**"] + [str(val) for val in row.values]
            md.append("| " + " | ".join(line) + " |")
        md.append("")
        
        # 5. Version C Spec
        md.append("## 5. Version C: Future Option-Chain Labels Design note")
        md.append(
            "> [!NOTE]\n"
            "> **Option-Chain Label Design Sketch (Design Only — No Data Output):**\n"
            ">\n"
            "> **1. Pipeline Requirements & Data Gaps:**\n"
            "> Option-chain modeling requires historical end-of-day (or tick-level) derivative chains from the exchange: "
            "Option Strike Prices, Call/Put Premium Prices (Bid/Ask/Last Close), Expiry Dates, and Implied Volatility (IV) surface charts. "
            "This project currently does not possess derivative data pipelines, making Version C unimplemented in the current database.\n"
            ">\n"
            "> **2. Proposed ATM Option Profitability Sketch:**\n"
            "> - Let $C_t$ be the premium of an At-The-Money (ATM) Call Option expiring in $D$ days, and $P_t$ be the premium of an ATM Put Option.\n"
            "> - **BUY ATM CALL (Class 2)**: If next-day price expansion exceeds premium decay: $Close_{t+1} - Close_t > C_t \\cdot (\\text{decay factor})$.\n"
            "> - **BUY ATM PUT (Class 0)**: If next-day price drop exceeds premium decay: $Close_t - Close_{t+1} > P_t \\cdot (\\text{decay factor})$.\n"
            "> - **HOLD (Class 1)**: If premium decay (theta) exceeds directional expansion, representing horizontal range-bound days.\n"
            ">\n"
            "> **3. Next Steps**: To execute this version, a separate derivative loader (Phase 1 extension) must be designed to fetch, strike-align, and map options tables before appending them to feature datasets.\n"
        )
        
        return "\n".join(md)

    def save(self, output_path: str) -> None:
        """Writes the generated Markdown target label report to disk."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        logger.info(f"Label engineering report saved at: {p}")


def generate_label_datasets(config: dict) -> None:
    """Orchestrates loading features, computing targets, saving versioned CSVs, and generating reports."""
    logger.info("Initializing Label Engineering pipeline...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Extract configs
    le_config = config['eda']['label_engineering']
    
    input_rel = le_config['input_file']
    close_col = le_config['close_column']
    threshold = le_config['three_class_threshold']
    output_dir_rel = le_config['output_dir']
    binary_fn = le_config['binary_output_filename']
    three_class_fn = le_config['three_class_output_filename']
    report_rel = le_config['report_output_path']
    
    # Resolve absolute paths
    input_path = project_root / input_rel
    output_dir = project_root / output_dir_rel
    binary_path = output_dir / binary_fn
    three_class_path = output_dir / three_class_fn
    report_path = project_root / report_rel
    
    logger.info(f"Loading features dataset: {input_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Feature dataset not found: {input_path}. Please execute feature loader.")
        
    df_features = pd.read_csv(input_path)
    
    # Instantiate engineer
    engineer = LabelEngineer(
        data=df_features,
        close_column=close_col,
        three_class_threshold=threshold
    )
    
    # Save target CSV datasets (Additive labels, preserving features)
    engineer.save_labeled_dataset("binary", str(binary_path))
    engineer.save_labeled_dataset("threeclass", str(three_class_path))
    
    # Save Markdown report
    engineer.save(str(report_path))
    logger.info("Label Engineering completed successfully.")


if __name__ == "__main__":
    try:
        global_config = load_global_config()
        generate_label_datasets(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to generate labeled datasets: {e}", exc_info=True)
        sys.exit(1)
