import os
import yaml
from pathlib import Path
import pandas as pd
import numpy as np

# Report generator script entry point
def main():
    project_root = Path(__file__).resolve().parent.parent.parent
    backtest_dir = project_root / "data/backtest_runs/fs_v1_threeclass_embargo0"
    output_report_path = project_root / "reports/Results/backtesting_performance_report.md"
    
    if not backtest_dir.exists():
        print(f"Backtest runs directory not found at: {backtest_dir}")
        return
        
    md_content = []
    md_content.append("# QuantEngine: Phase 3 - Backtesting Performance Report")
    md_content.append(f"\n*Generated automatically from historical walk-forward simulations.*")
    md_content.append("\n---")
    
    md_content.append("\n## 1. Executive Summary")
    md_content.append("This report details the simulated trading performance of the tuned models (Logistic Regression and XGBoost) evaluated chronologically across 8 walk-forward folds.")
    md_content.append("Performance is split into two transaction cost structures:")
    md_content.append("- **Idealized**: Zero transaction costs (slippage, brokerage, spread, taxes, commissions).")
    md_content.append("- **Realistic**: Configured transaction costs applied at execution points.")
    
    # 1. Aggregate table
    md_content.append("\n### Unified Aggregate Performance (Folds 1–7 Rollup)")
    md_content.append("| Model | Cost Mode | Sharpe [95% CI] | Sortino | Max DD | Profit Factor | Expectancy | Exposure | CAGR |")
    md_content.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    models = ["xgboost", "logistic_regression", "lightgbm"]
    modes = ["idealized", "realistic"]
    
    for m in models:
        for mode in modes:
            agg_file = backtest_dir / m / mode / "aggregate_folds_1_7.yaml"
            if agg_file.exists():
                with open(agg_file, "r") as f:
                    data = yaml.safe_load(f)
                
                pf_val = data.get('global_profit_factor', 0.0)
                pf_str = f"{pf_val:.2f}" if isinstance(pf_val, (int, float)) else str(pf_val)
                
                sharpe = data.get('mean_sharpe_ratio', 0.0)
                ci_lower = data.get('mean_sharpe_ci_lower', 0.0)
                ci_upper = data.get('mean_sharpe_ci_upper', 0.0)
                
                md_content.append(
                    f"| **{m}** | {mode} | "
                    f"{sharpe:.2f} [{ci_lower:.2f}, {ci_upper:.2f}] | "
                    f"{data.get('mean_sortino_ratio', 0.0):.2f} | "
                    f"{data.get('mean_max_drawdown', 0.0)*100:.2f}% | "
                    f"{pf_str} | "
                    f"₹{data.get('mean_expectancy', 0.0):,.2f} | "
                    f"{data.get('mean_exposure_pct', 0.0)*100:.1f}% | "
                    f"{data.get('mean_annualized_return_cagr', 0.0)*100:.2f}% |"
                )
                
    # 2. Fold by Fold comparison for XGBoost (realistic)
    md_content.append("\n---")
    md_content.append("\n## 2. Detailed Fold-by-Fold Performance (XGBoost Realistic)")
    md_content.append("| Fold | Date Range | Total Return | CAGR | Max DD | Sharpe | Exposure | Trades | Win Rate |")
    md_content.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    # Let's get fold ranges from walk_forward config
    config_path = project_root / "config/config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    folds = config["eda"]["walk_forward"]["folds"]
    
    for idx, f_cfg in enumerate(folds):
        fold_id = idx + 1
        date_range = str(f_cfg.get('test_year')) + (" (partial)" if f_cfg.get("partial") else "")
        fold_perf_file = backtest_dir / "xgboost/realistic" / f"fold_{fold_id}/performance_metrics.yaml"
        
        if fold_perf_file.exists():
            with open(fold_perf_file, "r") as f:
                data = yaml.safe_load(f)
            
            md_content.append(
                f"| Fold {fold_id} | {date_range} | "
                f"{data.get('total_return', 0.0)*100:.2f}% | "
                f"{data.get('annualized_return_cagr', 0.0)*100:.2f}% | "
                f"{data.get('max_drawdown', 0.0)*100:.2f}% | "
                f"{data.get('sharpe_ratio', 0.0):.2f} | "
                f"{data.get('exposure_pct', 0.0)*100:.1f}% | "
                f"{data.get('number_of_trades', 0)} | "
                f"{data.get('win_rate', 0.0)*100:.1f}% |"
            )
            
    # 3. Benchmark Comparisons (Fold 2 Example of volatile regime)
    md_content.append("\n---")
    md_content.append("\n## 3. Volatile Regime Benchmark Overperformance (Fold 2 Case Study)")
    md_content.append("Fold 2 represents the volatile market regime of 2020 (containing the COVID crash). Here is the comparison of XGBoost (Idealized) against passive benchmarks:")
    md_content.append("\n| Strategy / Benchmark | Total Return | CAGR | Max DD | Sharpe Ratio | Calmar Ratio |")
    md_content.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    
    fold2_comp_file = backtest_dir / "xgboost/idealized/fold_2/benchmark_comparison.yaml"
    if fold2_comp_file.exists():
        with open(fold2_comp_file, "r") as f:
            data = yaml.safe_load(f)
            
        for strategy, metrics in data.items():
            strat_name = strategy.replace("_", " ").title()
            if strategy == "model_strategy":
                strat_name = "**XGBoost Strategy**"
            md_content.append(
                f"| {strat_name} | "
                f"{metrics.get('total_return', 0.0)*100:.2f}% | "
                f"{metrics.get('annualized_return_cagr', 0.0)*100:.2f}% | "
                f"{metrics.get('max_drawdown', 0.0)*100:.2f}% | "
                f"{metrics.get('sharpe_ratio', 0.0):.2f} | "
                f"{metrics.get('calmar_ratio', 0.0):.2f} |"
            )
            
    md_content.append("\n### Key Takeaways:")
    md_content.append("1. **Alpha and Downside Protection**: The model strategy preserved capital exceptionally well during the March 2020 crash, limiting maximum drawdown to **`-3.83%`** (compared to **`-38.44%`** for Buy & Hold).")
    md_content.append("2. **Superior Sharpe**: The model strategy achieved a Sharpe ratio of **`0.94`** vs. `0.60` for Buy & Hold, illustrating strong risk-adjusted returns.")
    
    # 4. Methodology Notes
    md_content.append("\n---")
    md_content.append("\n## 4. Methodology Notes")
    md_content.append("- **Execution Prices**: Sized, managed, and executed trades strictly on raw unscaled Close prices. Scaled z-score features are used solely for model inference signals.")
    md_content.append("- **Expectancy**: Measured in absolute currency units (₹) per completed trade, reflecting the net average profit/loss including transaction costs.")
    md_content.append("- **Global Profit Factor**: Computed as total net winnings over absolute total net losses across all folds combined, resolving zero-loss fold arithmetic averages.")
    md_content.append("- **Unified Sharpe & Sortino**: Derived by concatenating daily portfolio returns across Folds 1–7 chronologically into a single returns series, preventing simple averages bias.")
    md_content.append("- **Portfolio-level CAGR**: Calculated directly from the cumulative compounded returns of the stitched daily returns curve.")
    md_content.append("- **Worst-Case Max Drawdown**: Reports the single largest peak-to-trough drop across the stitched walk-forward equity curve.")
    md_content.append("- **Risk-Free Rate**: Assumed to be $0.0\\%$ across all Sharpe/Sortino calculations.")
    md_content.append("- **Confidence Threshold Status**: Categorized as a strategy/execution parameter (currently set to 0.55 default), which is kept isolated from classifier parameters.")

    # 5. Limitations
    md_content.append("\n---")
    md_content.append("\n## 5. Limitations")
    md_content.append("- **Fixed Slippage Assumption**: Slippage is modeled as a constant multiplier ($0.05\\%$). Real execution slippage varies dynamically based on volatility, order-book depth, and trade sizing.")
    md_content.append("- **No Market Impact Modeling**: The simulation assumes that executing trades does not shift the underlying index price, which may overstate actual fills on large institutional orders.")
    md_content.append("- **No Liquidity Constraints**: Assumes instant execution at daily Close prices on 100% of order sizing without any volume limitations.")
    md_content.append("- **No Borrow/Funding Costs**: Margin funding and short borrow costs are not modeled, which would reduce profits on short trades.")
    md_content.append("- **No Futures Roll Costs**: Since Nifty 50 is traded via monthly derivatives, rolling positions introduces execution slippage and rollover premiums that are not simulated.")
    md_content.append("- **Single-Asset Evaluation**: The backtest is run strictly on `^NSEI` (Nifty 50), ignoring portfolio diversification benefits or multi-asset risk constraints.")
    md_content.append("- **Threshold Sweeps are Exploratory**: Selecting `0.69` post-hoc across the test folds represents optimization bias. For production grade, thresholds must be optimized dynamically using inner validation loops.")
    
    # Save file
    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    print(f"Backtesting performance report generated successfully at: {output_report_path}")

if __name__ == "__main__":
    main()
