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
        all_returns = []
        all_completed_trades = []
        fold_exposures = []
        fold_trades_count = []
        
        for fold_id in folds:
            history, trades = engine.run_backtest_on_fold("xgboost", fold_id, "realistic")
            
            # Daily returns
            h_df = pd.DataFrame(history)
            h_df["returns"] = h_df["portfolio_value"].pct_change().fillna(0.0)
            all_returns.append(h_df["returns"])
            
            # Collect trades
            all_completed_trades.extend(trades)
            
            # Fold level exposure
            metrics = engine._calculate_metrics(history, trades)
            fold_exposures.append(metrics["exposure_pct"])
            fold_trades_count.append(len(trades))
            
        combined_returns = pd.concat(all_returns) if all_returns else pd.Series(dtype=float)
        
        # Unified Sharpe
        std_ret = combined_returns.std(ddof=1)
        mean_ret = combined_returns.mean()
        unified_sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0.0
        
        # Unified Sortino
        downside_returns = combined_returns[combined_returns < 0]
        std_downside = downside_returns.std(ddof=1)
        unified_sortino = (mean_ret / std_downside) * np.sqrt(252) if std_downside > 0 else 0.0
        
        # Unified CAGR
        cumulative_return = np.prod(1.0 + combined_returns) - 1.0
        n_days = len(combined_returns)
        unified_cagr = (1.0 + cumulative_return) ** (252 / n_days) - 1.0 if n_days > 0 else 0.0
        
        # Unified Drawdown
        cum_returns = (1.0 + combined_returns).cumprod()
        peak = cum_returns.cummax()
        drawdown = (cum_returns - peak) / peak if not cum_returns.empty else pd.Series(dtype=float)
        unified_max_dd = drawdown.min() if not drawdown.empty else 0.0
        
        # Global Profit Factor & Expectancy
        net_profits = sum([t["net_pnl"] for t in all_completed_trades if t["net_pnl"] > 0])
        net_losses = sum([abs(t["net_pnl"]) for t in all_completed_trades if t["net_pnl"] < 0])
        
        if net_losses > 0:
            global_pf = float(net_profits / net_losses)
        else:
            global_pf = float('inf') if net_profits > 0 else 1.0
            
        global_expectancy = np.mean([t["net_pnl"] for t in all_completed_trades]) if all_completed_trades else 0.0
        mean_exposure = np.mean(fold_exposures)
        mean_trades = np.mean(fold_trades_count)
        
        sweep_results.append({
            "threshold": thresh,
            "mean_sharpe": unified_sharpe,
            "mean_sortino": unified_sortino,
            "mean_max_dd": unified_max_dd,
            "mean_profit_factor": global_pf,
            "mean_expectancy": global_expectancy,
            "mean_exposure": mean_exposure,
            "mean_trades": mean_trades,
            "mean_cagr": unified_cagr
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
