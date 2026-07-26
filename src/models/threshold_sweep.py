import os
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from src.models.backtest_engine import BacktestEngine
from src.utils.config_loader import load_global_config

def main():
    project_root = Path(__file__).resolve().parent.parent.parent
    global_config = load_global_config()
    
    # Instantiate engine
    runs_dir = project_root / "data/walk_forward_runs"
    hpo_dir = project_root / "data/hpo_runs"
    output_dir = project_root / "data/backtest_runs"
    
    engine = BacktestEngine(
        config=global_config.model_dump(),
        runs_dir=str(runs_dir),
        hpo_dir=str(hpo_dir),
        output_dir=str(output_dir)
    )
    
    # We will sweep buy/sell thresholds symmetrically from 0.66 to 0.74 (step 0.01)
    thresholds = [0.66, 0.67, 0.68, 0.69, 0.70, 0.71, 0.72, 0.73, 0.74]
    
    sweep_results = []
    
    print("Starting XGBoost threshold sweep...")
    
    # Target full year folds (Folds 1-7)
    folds = [1, 2, 3, 4, 5, 6, 7]
    
    for thresh in thresholds:
        print(f"Evaluating Threshold: {thresh:.2f}...")
        
        # Override config thresholds temporarily
        engine.bt_config["signal_generation"]["confidence_thresholds"]["xgboost"]["buy_threshold"] = thresh
        engine.bt_config["signal_generation"]["confidence_thresholds"]["xgboost"]["sell_threshold"] = thresh
        
        fold_cagrs = []
        fold_sharpes = []
        fold_sortinos = []
        fold_drawdowns = []
        fold_pfs = []
        fold_exps = []
        fold_exposures = []
        fold_trades_count = []
        
        for fold_id in folds:
            history, trades = engine.run_backtest_on_fold("xgboost", fold_id, "realistic")
            metrics = engine._calculate_metrics(history, trades)
            
            fold_cagrs.append(metrics["annualized_return_cagr"])
            fold_sharpes.append(metrics["sharpe_ratio"])
            fold_sortinos.append(metrics["sortino_ratio"])
            fold_drawdowns.append(metrics["max_drawdown"])
            fold_pfs.append(metrics["profit_factor"])
            fold_exps.append(metrics["expectancy"])
            fold_exposures.append(metrics["exposure_pct"])
            fold_trades_count.append(metrics["number_of_trades"])
            
        sweep_results.append({
            "threshold": thresh,
            "mean_sharpe": np.mean(fold_sharpes),
            "mean_sortino": np.mean(fold_sortinos),
            "mean_max_dd": np.mean(fold_drawdowns),
            "mean_profit_factor": np.mean(fold_pfs),
            "mean_expectancy": np.mean(fold_exps),
            "mean_exposure": np.mean(fold_exposures),
            "mean_trades": np.mean(fold_trades_count),
            "mean_cagr": np.mean(fold_cagrs)
        })
        
    # Generate Markdown report
    report_lines = []
    report_lines.append("# QuantEngine: XGBoost Decision Threshold Sweep Report")
    report_lines.append(f"\n*Evaluated under realistic transaction costs across Folds 1–7.*")
    report_lines.append("\n---")
    report_lines.append("\n## 1. Threshold Sweep Results Table")
    report_lines.append("| Threshold | Mean Sharpe | Mean Sortino | Mean Max DD | Mean Profit Factor | Mean Expectancy (₹) | Mean Exposure | Mean Trades Count | Mean CAGR |")
    report_lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    for res in sweep_results:
        report_lines.append(
            f"| **{res['threshold']:.2f}** | "
            f"{res['mean_sharpe']:.2f} | "
            f"{res['mean_sortino']:.2f} | "
            f"{res['mean_max_dd']*100:.2f}% | "
            f"{res['mean_profit_factor']:.2f} | "
            f"{res['mean_expectancy']:.2f} | "
            f"{res['mean_exposure']*100:.1f}% | "
            f"{res['mean_trades']:.1f} | "
            f"{res['mean_cagr']*100:.2f}% |"
        )
        
    report_lines.append("\n## 2. Strategic Insights")
    
    # Find best threshold based on Sharpe
    best_res = max(sweep_results, key=lambda x: x["mean_sharpe"])
    report_lines.append(f"- **Optimal Decision Coordinate**: Symmetrical threshold of **`{best_res['threshold']:.2f}`** yields the highest risk-adjusted profile with a Sharpe of **`{best_res['mean_sharpe']:.2f}`** and CAGR of **`{best_res['mean_cagr']*100:.2f}%`**.")
    report_lines.append(f"- **Trade Frequency Optimization**: Raising the threshold restricts marginal trades, lowering the transaction cost drag (mean trades count goes from `{sweep_results[0]['mean_trades']:.1f}` to `{sweep_results[-1]['mean_trades']:.1f}`).")
    
    # Save file
    report_path = project_root / "reports/Results/xgboost_threshold_sweep.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Sweep completed successfully. Report generated at: {report_path}")

if __name__ == "__main__":
    main()
