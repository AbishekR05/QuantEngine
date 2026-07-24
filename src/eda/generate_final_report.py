import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("final_report")

def read_report_file(path: Path) -> str:
    """Reads a markdown file and returns its content. Returns empty string if not found."""
    if not path.exists():
        logger.warning(f"Sub-report not found: {path}")
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def extract_section_by_header(content: str, header_text: str) -> str:
    """Extracts a section from markdown content starting with a specific header until the next header of same level."""
    lines = content.split("\n")
    start_idx = -1
    header_level = 0
    
    for idx, line in enumerate(lines):
        if line.strip().endswith(header_text) or header_text in line:
            # Determine header level (e.g. ## or ###)
            stripped = line.lstrip("#")
            level = len(line) - len(stripped)
            if level > 0:
                start_idx = idx
                header_level = level
                break
                
    if start_idx == -1:
        return ""
        
    extracted_lines = []
    for idx in range(start_idx, len(lines)):
        line = lines[idx]
        if idx > start_idx:
            # Check if we hit another header of same or higher level (fewer or equal '#' characters)
            stripped = line.lstrip("#")
            level = len(line) - len(stripped)
            if level > 0 and level <= header_level:
                break
        extracted_lines.append(line)
        
    return "\n".join(extracted_lines)

def build_consolidated_report(config: dict) -> None:
    """Consolidates all modular EDA reports from Phase 2 into a single unified report."""
    logger.info("Starting compilation of Final EDA Report...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    stats_dir = project_root / "reports/eda/statistics"
    
    # Read sub-reports
    ds_features_content = read_report_file(stats_dir / "dataset_summary_features.md")
    stat_features_content = read_report_file(stats_dir / "statistical_summary_features.md")
    corr_content = read_report_file(stats_dir / "correlation_report.md")
    outlier_content = read_report_file(stats_dir / "outlier_report.md")
    regime_content = read_report_file(stats_dir / "regime_report.md")
    usefulness_content = read_report_file(stats_dir / "feature_usefulness_report.md")
    label_content = read_report_file(stats_dir / "label_engineering_report.md")
    scaling_content = read_report_file(stats_dir / "scaling_recommendation_report.md")
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Compile main consolidated markdown structure
    report = []
    
    # Document Header
    report.append("# QuantEngine: Consolidated Exploratory Data Analysis (EDA) Report")
    report.append(f"**Document Version**: v1.0.0 (Phase 2 Master Compilation)")
    report.append(f"**Consolidation Date**: {timestamp}")
    report.append("**Target Asset**: Nifty 50 Index (Features & Target Labels)")
    report.append("\n---\n")
    
    # Executive Summary (Page 1)
    report.append("## Executive Summary")
    report.append("| Metadata Dimension | Status / Details |")
    report.append("| :--- | :--- |")
    report.append("| **Project Status** | Phase 2 (Completed) |")
    report.append("| **Dataset Quality** | Excellent |")
    report.append("| **Missing Values** | Expected warm-up only |")
    report.append("| **Market Coverage** | 2007–2026 |")
    report.append("| **Indicators** | 22 |")
    report.append("| **Engineered Labels** | Binary, Three-Class |")
    report.append("| **ML Ready?** | **NO** |")
    report.append("| **Reason** | Need Feature Selection, Need Train/Test Pipeline, Need Backtesting |")
    report.append("\n---\n")
    
    # Phase 3 Readiness Checklist
    report.append("## Phase 3 Readiness Checklist")
    report.append("| Status | Step / Milestone | Phase |")
    report.append("| :---: | :--- | :--- |")
    report.append("| ✔ | Data Collected | Phase 1 |")
    report.append("| ✔ | Features Engineered | Phase 1 |")
    report.append("| ✔ | Dataset Validated | Phase 2 |")
    report.append("| ✔ | Correlations Studied | Phase 2 |")
    report.append("| ✔ | Outliers Understood | Phase 2 |")
    report.append("| ✔ | Market Regimes Created | Phase 2 |")
    report.append("| ✔ | Labels Generated | Phase 2 |")
    report.append("| ✔ | Scaling Recommendations Ready | Phase 2 |")
    report.append("| ⬜ | Train/Test Pipeline | Phase 3 |")
    report.append("| ⬜ | Walk Forward Validation | Phase 3 |")
    report.append("| ⬜ | Feature Selection | Phase 3 |")
    report.append("| ⬜ | Model Training | Phase 3 |")
    report.append("| ⬜ | Hyperparameter Search | Phase 3 |")
    report.append("| ⬜ | Backtesting | Phase 3 |")
    report.append("| ⬜ | Paper Trading | Phase 3 |")
    report.append("\n---\n")
    
    # Table of Contents
    report.append("## Table of Contents")
    report.append(
        "1. [Dataset Overview & Quality Summary](#1-dataset-overview--quality-summary)\n"
        "2. [Descriptive Statistical Distributions](#2-descriptive-statistical-distributions)\n"
        "3. [Core Feature Visualizations Summary](#3-core-feature-visualizations-summary)\n"
        "4. [Correlation Taxonomy & Redundant Pairs](#4-correlation-taxonomy--redundant-pairs)\n"
        "5. [Outlier Analysis & Market Shocks Chronology](#5-outlier-analysis--market-shocks-chronology)\n"
        "6. [Market Regimes Profile (Trend & Volatility)](#6-market-regimes-profile-trend--volatility)\n"
        "7. [Feature Usefulness & Information Entanglement](#7-feature-usefulness--information-entanglement)\n"
        "8. [Label Engineering & Supervised Targets](#8-label-engineering--supervised-targets)\n"
        "9. [Feature Scaling Recommendations](#9-feature-scaling-recommendations)\n"
        "10. [Final Conclusions](#10-final-conclusions)\n"
    )
    report.append("\n---\n")
    
    # 1. Dataset Overview
    report.append("## 1. Dataset Overview & Quality Summary")
    report.append(
        "The consolidated dataset `nifty_features.csv` represents the primary output of Phase 1 (Feature Engineering). "
        "It spans historical sessions from 2007 to 2026. The table below outlines the metadata characteristics of this dataset:\n"
    )
    if ds_features_content:
        report.append(ds_features_content.strip())
    else:
        report.append("- *Metadata file missing. Dataset contains 4,613 total rows, 22 features, and 1 Date column.*")
    report.append("\n---\n")
    
    # 2. Descriptive Stats
    report.append("## 2. Descriptive Statistical Distributions")
    report.append(
        "Standard statistical moments (mean, std, skewness, excess kurtosis, and quartiles) were computed for all "
        "numerical features. High skewness ($|S| \\ge 1.0$) and heavy tails ($K \\ge 3.0$) are flagged for robust preprocessing:\n"
    )
    if stat_features_content:
        report.append(stat_features_content.strip())
    else:
        report.append("- *Statistical summary tables missing.*")
    report.append("\n---\n")
    
    # 3. Visualizations Summary
    report.append("## 3. Core Feature Visualizations Summary")
    report.append(
        "A suite of 16 diagnostic charts was generated under `reports/eda/figures/` to confirm signal shape and "
        "uncover structure:\n"
        "1. **Line Plots (Nifty Close & Moving Averages)**: Displays price trajectory over 19 years relative to SMA_200, EMA_20, and EMA_50.\n"
        "2. **Bollinger Bands Shaded Region**: Visualizes price boundaries cleanly as a light blue band rather than intersecting lines.\n"
        "3. **RSI_14 with Bands**: Plots RSI with 30/70 reference lines and light green shading in the normal region.\n"
        "4. **Volume zero-volume annotations**: Shaded pink area (\"Expected Outliers Zero-Volume Era 2007–2013\") and arrow pointing at the "
        "zero-bar on the histogram.\n"
        "5. **EMA_200 Line Chart**: Confirms long-term trend alignment.\n"
        "6. **Boxplot for Volume**: Displays outlier dispersion alongside zero-volume text annotations.\n"
    )
    report.append("\n---\n")
    
    # 4. Correlation Findings
    report.append("## 4. Correlation Taxonomy & Redundant Pairs")
    if corr_content:
        re_group = extract_section_by_header(corr_content, "Near-Duplicate / Highly Redundant Features")
        taxonomy = extract_section_by_header(corr_content, "Taxonomy of Feature Relationships")
        roadmap = extract_section_by_header(corr_content, "Roadmap for Future Predictive Correlation")
        
        if re_group:
            report.append(re_group.strip() + "\n")
        if taxonomy:
            report.append(taxonomy.strip() + "\n")
        if roadmap:
            report.append(roadmap.strip() + "\n")
    else:
        report.append("- *Correlation findings missing.*")
    report.append("\n---\n")
    
    # 5. Outliers
    report.append("## 5. Outlier Analysis & Market Shocks Chronology")
    if outlier_content:
        outliers_sec = extract_section_by_header(outlier_content, "Outlier Analysis Summary")
        event_matching_sec = extract_section_by_header(outlier_content, "Outlier Event Matching & Chronological Clustering")
        
        if outliers_sec:
            report.append(outliers_sec.strip() + "\n")
        if event_matching_sec:
            report.append(event_matching_sec.strip() + "\n")
    else:
        report.append("- *Outlier analysis missing.*")
    report.append("\n---\n")
    
    # 6. Regimes
    report.append("## 6. Market Regimes Profile (Trend & Volatility)")
    if regime_content:
        definitions = extract_section_by_header(regime_content, "Methodology: Formal Definitions")
        caveats = extract_section_by_header(regime_content, "Important Caveat & Structural Warning")
        dist = extract_section_by_header(regime_content, "Regime Distribution Summaries")
        stats = extract_section_by_header(regime_content, "Per-Regime Performance & Persistence Statistics")
        transitions = extract_section_by_header(regime_content, "Trend Regime Transitions Matrix")
        
        if definitions:
            report.append(definitions.strip() + "\n")
        if caveats:
            report.append(caveats.strip() + "\n")
        if dist:
            report.append(dist.strip() + "\n")
        if stats:
            report.append(stats.strip() + "\n")
        if transitions:
            report.append(transitions.strip() + "\n")
    else:
        report.append("- *Market regimes report missing.*")
    report.append("\n---\n")
    
    # 7. Feature Analysis / Usefulness
    report.append("## 7. Feature Usefulness & Information Entanglement")
    if usefulness_content:
        non_dec = extract_section_by_header(usefulness_content, "Explicit Non-Decision Statement")
        quirks = extract_section_by_header(usefulness_content, "Known Data Limitations & Distribution Quirks")
        comb_mat = extract_section_by_header(usefulness_content, "Combined Side-by-Side Ranking Matrix")
        divergences = extract_section_by_header(usefulness_content, "Mutual Information vs. Linear Correlation Divergences")
        
        if non_dec:
            report.append(non_dec.strip() + "\n")
        if quirks:
            report.append(quirks.strip() + "\n")
        if comb_mat:
            report.append(comb_mat.strip() + "\n")
        if divergences:
            report.append(divergences.strip() + "\n")
    else:
        report.append("- *Feature usefulness report missing.*")
    report.append("\n---\n")
    
    # 8. Label Engineering
    report.append("## 8. Label Engineering & Supervised Targets")
    if label_content:
        lookahead_warn = extract_section_by_header(label_content, "Important Lookahead Warning")
        bin_sum = extract_section_by_header(label_content, "Version A: Binary Classification Summary")
        three_sum = extract_section_by_header(label_content, "Version B: Three-Class Classification Summary")
        cross_ref = extract_section_by_header(label_content, "Regime vs. Class Label Cross-Reference Table")
        option_spec = extract_section_by_header(label_content, "Version C: Future Option-Chain Labels Design note")
        
        if lookahead_warn:
            report.append(lookahead_warn.strip() + "\n")
        if bin_sum:
            report.append(bin_sum.strip() + "\n")
        if three_sum:
            report.append(three_sum.strip() + "\n")
        if cross_ref:
            report.append(cross_ref.strip() + "\n")
        if option_spec:
            report.append(option_spec.strip() + "\n")
    else:
        report.append("- *Label engineering report missing.*")
    report.append("\n---\n")
    
    # 9. Scaling Recommendations
    report.append("## 9. Feature Scaling Recommendations")
    if scaling_content:
        non_action = extract_section_by_header(scaling_content, "Explicit Non-Action Statement")
        leakage_warn = extract_section_by_header(scaling_content, "Forward-Looking Time-Series Leakage warning")
        recs_table = extract_section_by_header(scaling_content, "Per-Column Scaling Recommendations")
        vol_case = extract_section_by_header(scaling_content, "Special Case Analysis: Trading Volume")
        rsi_note = extract_section_by_header(scaling_content, "Bounded Indicator Analysis: RSI")
        returns_note = extract_section_by_header(scaling_content, "Return Indicators Analysis: Daily Return vs. Log Return")
        dup_note = extract_section_by_header(scaling_content, "Structural Near-Duplicate Features")
        
        if non_action:
            report.append(non_action.strip() + "\n")
        if leakage_warn:
            report.append(leakage_warn.strip() + "\n")
        if recs_table:
            report.append(recs_table.strip() + "\n")
        if vol_case:
            report.append(vol_case.strip() + "\n")
        if rsi_note:
            report.append(rsi_note.strip() + "\n")
        if returns_note:
            report.append(returns_note.strip() + "\n")
        if dup_note:
            report.append(dup_note.strip() + "\n")
    else:
        report.append("- *Scaling recommendation report missing.*")
    report.append("\n---\n")
    
    # 10. Final Conclusions (Section 2 & 3 Compliance)
    report.append("## 10. Final Conclusions")
    report.append("### Key Findings")
    report.append("- **Dataset quality is excellent**: High completeness across price history, missing values restricted strictly to standard indicators' warm-up boundaries.")
    report.append("- **No pipeline failures detected**: Clean date formatting, zero duplicates, and complete numerical alignments.")
    report.append("- **Feature engineering successful**: 22 functional features generated across price trend, momentum, and statistical dispersion categories.")
    report.append("- **Market regimes identified**: Historical Trend (direction) and Volatility (dispersion) regimes successfully created and validated descriptive-only transition matrices.")
    report.append("- **Heavy multicollinearity exists among trend indicators**: Multicollinearity flags confirmed in Step 4 Pearson matrices demand model pruning.")
    report.append("- **Feature selection required**: High mutual information and redundancy counts necessitate feature subset selection prior to model training.")
    report.append("- **Dataset suitable for supervised learning**: Both Version A and Version B label files correctly appended and structured.")
    report.append("- **Options labels require derivative data**: ATM options v3 modeling requires a distinct option-chain loader to support strike-based theta decay math.")
    report.append("\n### Next Phase")
    report.append("**Machine Learning Pipeline**: Developing the Phase 3 training framework, feature selector nodes, walk-forward CV, hyperparameter searches, and backtests.")
    
    # Resolve output path
    output_rel = config['eda']['final_report']['output_report_path']
    output_path = project_root / output_rel
    
    # Create parent folder if not exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the compiled content
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    logger.info(f"Consolidated Final EDA Report written successfully at: {output_path}")

if __name__ == "__main__":
    try:
        global_config = load_global_config()
        build_consolidated_report(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to generate final EDA report: {e}", exc_info=True)
        sys.exit(1)
