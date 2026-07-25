import os
import yaml
from pathlib import Path

def generate_report():
    project_root = Path(__file__).resolve().parent.parent.parent
    comparison_path = project_root / "data/benchmark_runs/fs_v1_threeclass_embargo0/benchmark_comparison.yaml"
    report_path = project_root / "reports/Results/raw_vs_calibrated_report.md"
    
    if not comparison_path.exists():
        raise FileNotFoundError(f"Benchmark comparison dashboard not found at: {comparison_path}")
        
    with open(comparison_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    models_comparison = data.get("models_comparison", {})
    
    # Custom display names mapping
    display_names = {
        "logistic_regression": "Logistic Regression",
        "decision_tree": "Decision Tree",
        "random_forest": "Random Forest",
        "xgboost": "XGBoost",
        "lightgbm": "LightGBM"
    }
    
    lines = []
    lines.append("# QuantEngine: Baseline Models - Raw vs. Calibrated Macro F1 Report")
    lines.append("")
    lines.append(f"**Generated on:** {data.get('timestamp', 'unknown')}")
    lines.append(f"**Walk-Forward Run ID:** {data.get('run_id', 'unknown')}")
    lines.append("")
    lines.append("This report presents the fold-by-fold classification comparison before (Raw) and after (Calibrated) probability calibration for each baseline model.")
    lines.append("")
    
    for model_key, model_name in display_names.items():
        if model_key not in models_comparison:
            continue
            
        m_data = models_comparison[model_key]
        folds = m_data.get("folds", {})
        
        lines.append("---")
        lines.append(f"## {model_name}")
        lines.append("")
        lines.append("| Fold | Raw Macro F1 | Calibrated Macro F1 | Difference | Status |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        
        raw_f1_sum = 0.0
        cal_f1_sum = 0.0
        diff_sum = 0.0
        count = 0
        
        # Sort folds numerically
        for fid in sorted(folds.keys(), key=int):
            fold_info = folds[fid]
            raw_f1 = fold_info["raw_f1"]
            cal_f1 = fold_info["calibrated_f1"]
            diff = cal_f1 - raw_f1
            
            is_partial = fold_info.get("is_partial_test_year", False)
            fold_label = f"Fold {fid} (Partial)" if is_partial else f"Fold {fid}"
            
            status = "**PASS**" if fold_info.get("viability_gate_pass", False) else "FAIL"
            
            lines.append(f"| {fold_label} | {raw_f1:.4f} | {cal_f1:.4f} | {diff:+.4f} | {status} |")
            
            if not is_partial:
                raw_f1_sum += raw_f1
                cal_f1_sum += cal_f1
                diff_sum += diff
                count += 1
                
        # Calculate averages for full year folds
        if count > 0:
            avg_raw = raw_f1_sum / count
            avg_cal = cal_f1_sum / count
            avg_diff = diff_sum / count
            lines.append(f"| **Average (Full Years)** | **{avg_raw:.4f}** | **{avg_cal:.4f}** | **{avg_diff:+.4f}** | - |")
            
        lines.append("")
        
        # Add summary insights
        pass_count = m_data.get("passing_folds_count", 0)
        req_count = m_data.get("required_passing_folds", 5)
        overall_pass = "PASSED" if m_data.get("overall_viability_pass", False) else "FAILED"
        
        lines.append(f"**Viability Summary:** {overall_pass} (Passed folds: {pass_count}/{len(folds)} vs. {req_count} required)")
        lines.append("")
        
        stability = m_data.get("stability_indicator", {})
        stable_str = "Stable" if stability.get("stable", False) else "Unstable"
        max_dev = stability.get("max_deviation", 0.0)
        allowed = stability.get("allowed_threshold", 0.10)
        lines.append(f"**Stability Indicator:** {stable_str} (Max deviation: {max_dev:.4f} vs. {allowed:.4f} allowed)")
        lines.append("")
        
    # Write to file
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"Report generated successfully at: {report_path}")

if __name__ == "__main__":
    generate_report()
