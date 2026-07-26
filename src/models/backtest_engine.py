import os
import sys
import yaml
import time
import joblib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from sklearn.calibration import CalibratedClassifierCV
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("backtest_engine")

# Mapping rules
LABEL_MAPPING = {"BUY": 0, "HOLD": 1, "SELL": 2}
LABEL_CLASSES = ["BUY", "HOLD", "SELL"]

class Position:
    """Represents a single open or closed trading position."""
    def __init__(self, direction: str, entry_date: str, entry_price: float, size: float,
                 stop_loss_pct: Optional[float] = None, take_profit_pct: Optional[float] = None):
        self.direction = direction # "LONG" or "SHORT"
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.size = size # units of the asset
        self.status = "OPEN" # "OPEN" or "CLOSED"
        self.exit_date = None
        self.exit_price = None
        self.exit_reason = None
        self.holding_days = 0
        self.entry_cost = 0.0
        self.exit_cost = 0.0
        
        # Stop loss / Take profit price levels
        if stop_loss_pct is not None and stop_loss_pct > 0:
            self.stop_loss = entry_price * (1 - stop_loss_pct) if direction == "LONG" else entry_price * (1 + stop_loss_pct)
        else:
            self.stop_loss = None
            
        if take_profit_pct is not None and take_profit_pct > 0:
            self.take_profit = entry_price * (1 + take_profit_pct) if direction == "LONG" else entry_price * (1 - take_profit_pct)
        else:
            self.take_profit = None

    def update_holding_days(self):
        self.holding_days += 1

    def close(self, exit_date: str, exit_price: float, reason: str, exit_cost: float = 0.0):
        self.status = "CLOSED"
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = reason
        self.exit_cost = exit_cost

    def get_realized_pnl(self) -> float:
        """Returns gross realized P&L."""
        if self.status != "CLOSED":
            return 0.0
        if self.direction == "LONG":
            return (self.exit_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.exit_price) * self.size

    def get_unrealized_pnl(self, current_price: float) -> float:
        """Returns current paper P&L."""
        if self.status != "OPEN":
            return 0.0
        if self.direction == "LONG":
            return (current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - current_price) * self.size


class Portfolio:
    """Simulates cash allocation, equity curves, and executes trade accounting."""
    def __init__(self, initial_capital: float, costs_config: Dict[str, float]):
        self.initial_capital = initial_capital
        self.costs_config = costs_config
        self.cash = initial_capital
        self.portfolio_value = initial_capital
        
        self.active_position: Optional[Position] = None
        self.trade_log: List[Position] = []
        self.history: List[Dict[str, Any]] = []

    def compute_transaction_cost(self, price: float, size: float) -> float:
        """Applies slippage, brokerage, and taxes on executed size value."""
        notional = price * size
        brokerage = self.costs_config.get("brokerage", 0.0) * notional
        slippage = self.costs_config.get("slippage", 0.0) * notional
        exchange_fees = self.costs_config.get("exchange_fees", 0.0) * notional
        taxes = self.costs_config.get("taxes", 0.0) * notional
        spread = self.costs_config.get("spread", 0.0) * notional
        commission = self.costs_config.get("commission", 0.0) * notional
        return brokerage + slippage + exchange_fees + taxes + spread + commission

    def open_position(self, direction: str, date: str, price: float, size_val: float,
                      stop_loss_pct: Optional[float] = None, take_profit_pct: Optional[float] = None) -> bool:
        if self.active_position is not None:
            return False # Single open position allowed
            
        cost = self.compute_transaction_cost(price, size_val)
        total_entry_val = price * size_val + cost
        
        # Verify margin/cash limits
        if total_entry_val > self.cash:
            # Adjust size down to maximum available cash
            max_value = self.cash - self.compute_transaction_cost(price, self.cash / price)
            size_val = max(0.0, max_value / price)
            cost = self.compute_transaction_cost(price, size_val)
            total_entry_val = price * size_val + cost
            if size_val <= 0.0:
                return False
                
        self.cash -= total_entry_val
        self.active_position = Position(direction, date, price, size_val, stop_loss_pct, take_profit_pct)
        self.active_position.entry_cost = cost
        return True

    def close_position(self, date: str, price: float, reason: str):
        if self.active_position is None:
            return
            
        pos = self.active_position
        cost = self.compute_transaction_cost(price, pos.size)
        
        pos.close(date, price, reason, cost)
        
        # Settle cash
        if pos.direction == "LONG":
            self.cash += (price * pos.size) - cost
        else:
            self.cash += (pos.entry_price * pos.size) + pos.get_realized_pnl() - cost
            
        self.trade_log.append(pos)
        self.active_position = None

    def update_history(self, date: str, current_price: float):
        """Records daily equity value."""
        open_val = 0.0
        if self.active_position is not None:
            pos = self.active_position
            pos.update_holding_days()
            # Position equity value
            if pos.direction == "LONG":
                open_val = current_price * pos.size
            else:
                open_val = (pos.entry_price * pos.size) + pos.get_unrealized_pnl(current_price)
                
        self.portfolio_value = self.cash + open_val
        self.history.append({
            "date": date,
            "portfolio_value": float(self.portfolio_value),
            "cash": float(self.cash),
            "open_position_value": float(open_val)
        })


class BacktestEngine:
    def __init__(self, config: Dict[str, Any], runs_dir: str = "data/walk_forward_runs",
                 hpo_dir: str = "data/hpo_runs", output_dir: str = "data/backtest_runs"):
        self.config = config
        self.runs_dir = Path(runs_dir)
        self.hpo_dir = Path(hpo_dir)
        self.output_dir = Path(output_dir)
        
        self.wf_config = config['eda']['walk_forward']
        self.bt_config = config['eda']['backtesting']
        
        self.fs_version = self.bt_config['versioning']['feature_store_version']
        self.label_version = self.bt_config['versioning']['label_version']
        self.run_id = self.bt_config['versioning']['walk_forward_run_id']
        
        self.slices_dir = self.runs_dir / self.run_id
        self.run_output_dir = self.output_dir / self.run_id
        self.run_output_dir.mkdir(parents=True, exist_ok=True)
        self.best_model_src = self.hpo_dir / self.run_id
        
        # Load raw prices to prevent trading on scaled z-scores
        raw_csv_path = Path(__file__).resolve().parent.parent.parent / "data/processed/nsei_clean.csv"
        if not raw_csv_path.exists():
            raise FileNotFoundError(f"Clean NSE data CSV not found at: {raw_csv_path}")
        raw_df = pd.read_csv(raw_csv_path)
        self.raw_prices = raw_df[["Date", "Close", "High", "Low"]].copy()
        self.raw_prices["Date"] = self.raw_prices["Date"].astype(str)
        self.raw_prices.rename(columns={"Close": "Raw_Close", "High": "Raw_High", "Low": "Raw_Low"}, inplace=True)

    def _calculate_metrics(self, history: List[Dict[str, Any]], trade_log: List[Position]) -> Dict[str, Any]:
        """Calculates risk, Sharpe, Sortino, drawdowns, and CAGR return rates."""
        if not history:
            return {}
            
        df = pd.DataFrame(history)
        df["returns"] = df["portfolio_value"].pct_change().fillna(0.0)
        
        total_ret = (df["portfolio_value"].iloc[-1] / df["portfolio_value"].iloc[0]) - 1
        
        # Annualized CAGR return
        n_days = len(df)
        cagr = (df["portfolio_value"].iloc[-1] / df["portfolio_value"].iloc[0]) ** (252 / n_days) - 1 if n_days > 0 else 0.0
        
        # Max drawdown
        df["peak"] = df["portfolio_value"].cummax()
        df["drawdown"] = (df["portfolio_value"] - df["peak"]) / df["peak"]
        max_dd = df["drawdown"].min()
        
        # Sharpe ratio (risk free rate assumed 0)
        std_ret = df["returns"].std(ddof=1)
        mean_ret = df["returns"].mean()
        sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0.0
        
        # Sortino ratio (downside deviation)
        downside_returns = df["returns"][df["returns"] < 0]
        std_downside = downside_returns.std(ddof=1)
        sortino = (mean_ret / std_downside) * np.sqrt(252) if std_downside > 0 else 0.0
        
        # Calmar ratio
        calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
        
        # Trade log stats
        n_trades = len(trade_log)
        wins = [t for t in trade_log if t["net_pnl"] > 0]
        win_rate = len(wins) / n_trades if n_trades > 0 else 0.0
        
        net_profits = sum([t["net_pnl"] for t in trade_log if t["net_pnl"] > 0])
        net_losses = sum([abs(t["net_pnl"]) for t in trade_log if t["net_pnl"] < 0])
        profit_factor = float(net_profits / net_losses) if net_losses > 0 else (float('inf') if net_profits > 0 else 1.0)
        
        avg_holding = np.mean([t["holding_days"] for t in trade_log]) if n_trades > 0 else 0.0
        
        # Exposure %
        exposure_days = sum([1 for h in history if h["open_position_value"] > 0])
        exposure_pct = exposure_days / n_days if n_days > 0 else 0.0
        
        # Expectancy (average net P&L per trade)
        net_pnls = [t["net_pnl"] for t in trade_log]
        expectancy = np.mean(net_pnls) if n_trades > 0 else 0.0
        
        return {
            "total_return": float(total_ret),
            "annualized_return_cagr": float(cagr),
            "max_drawdown": float(max_dd),
            "sharpe_ratio": float(sharpe),
            "sortino_ratio": float(sortino),
            "calmar_ratio": float(calmar),
            "number_of_trades": int(n_trades),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "average_holding_period": float(avg_holding),
            "exposure_pct": float(exposure_pct),
            "expectancy": float(expectancy)
        }

    def _generate_signals(self, model_name: str, y_probs: np.ndarray) -> List[str]:
        """Applies symmetric thresholds to generate BUY, SELL, or HOLD signals."""
        signals = []
        enabled = self.bt_config["signal_generation"]["thresholding_enabled"]
        
        # Default thresholds
        buy_thresh = 0.55
        sell_thresh = 0.55
        
        if enabled:
            model_thresh = self.bt_config["signal_generation"]["confidence_thresholds"].get(model_name, {})
            buy_thresh = model_thresh.get("buy_threshold", 0.55)
            sell_thresh = model_thresh.get("sell_threshold", 0.55)
            
        for i in range(len(y_probs)):
            p = y_probs[i]
            # p order is [BUY, HOLD, SELL]
            argmax_idx = np.argmax(p)
            
            if argmax_idx == 0: # BUY
                if p[0] >= buy_thresh:
                    signals.append("BUY")
                else:
                    signals.append("HOLD")
            elif argmax_idx == 2: # SELL
                if p[2] >= sell_thresh:
                    signals.append("SELL")
                else:
                    signals.append("HOLD")
            else:
                signals.append("HOLD")
                
        return signals

    def run_backtest_on_fold(self, model_name: str, fold_id: int, cost_mode: str,
                             use_default_step4_model: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Simulates walk-forward portfolio execution daily on a specific split."""
        # 1. Load data
        test_path = self.slices_dir / f"fold_{fold_id}_test.parquet"
        test_df = pd.read_parquet(test_path)
        
        label_col = "Label_Binary" if self.label_version == "binary" else "Label_ThreeClass"
        test_df = test_df.dropna(subset=[label_col]).reset_index(drop=True)
        
        # Convert Date to string for merging
        test_df["Date"] = test_df["Date"].astype(str)
        test_df = test_df.merge(self.raw_prices, on="Date", how="left")
        
        dates = test_df["Date"].tolist()
        close_prices = test_df["Raw_Close"].values
        high_prices = test_df["Raw_High"].values
        low_prices = test_df["Raw_Low"].values
        
        X_test = test_df.drop(columns=["Date", label_col, "Raw_Close", "Raw_High", "Raw_Low"])
        
        # 2. Get predictions probabilities
        if use_default_step4_model:
            # Load default step 4 baseline model
            src_dir = Path("data/benchmark_runs") / self.run_id / model_name
            model_path = src_dir / f"fold_{fold_id}_model_calibrated.joblib"
            cal_model = joblib.load(model_path)
        else:
            # Load optimized step 5 model
            src_dir = self.best_model_src / model_name / "best_trial"
            model_path = src_dir / f"fold_{fold_id}_model_calibrated.joblib"
            cal_model = joblib.load(model_path)
            
        y_probs = cal_model.predict_proba(X_test)
        signals = self._generate_signals(model_name, y_probs)
        
        # 3. Initialize Portfolio
        initial_cap = self.bt_config["initial_capital"]
        costs = self.bt_config["transaction_costs"][cost_mode]
        portfolio = Portfolio(initial_cap, costs)
        
        risk_cfg = self.bt_config["risk_management"]
        stop_loss_pct = risk_cfg["stop_loss"]["value"] if risk_cfg["stop_loss"]["enabled"] else None
        take_profit_pct = risk_cfg["take_profit"]["value"] if risk_cfg["take_profit"]["enabled"] else None
        max_holding = risk_cfg["max_holding_days"]
        risk_per_trade = risk_cfg["risk_per_trade"]
        
        execution_lag = self.bt_config["execution_lag_days"]
        
        pending_signal = None
        pending_signal_day = -1
        
        # 4. Daily simulation loop
        for t in range(len(test_df)):
            date = dates[t]
            close_p = close_prices[t]
            high_p = high_prices[t]
            low_p = low_prices[t]
            
            # Position management evaluations (evaluate rules on current price bar)
            if portfolio.active_position is not None:
                pos = portfolio.active_position
                
                # Check stop loss / take profit triggers
                exit_triggered = False
                exit_price = close_p
                reason = ""
                
                if pos.direction == "LONG":
                    if pos.stop_loss is not None and low_p <= pos.stop_loss:
                        exit_triggered = True
                        exit_price = pos.stop_loss
                        reason = "STOP_LOSS"
                    elif pos.take_profit is not None and high_p >= pos.take_profit:
                        exit_triggered = True
                        exit_price = pos.take_profit
                        reason = "TAKE_PROFIT"
                else: # SHORT position
                    if pos.stop_loss is not None and high_p >= pos.stop_loss:
                        exit_triggered = True
                        exit_price = pos.stop_loss
                        reason = "STOP_LOSS"
                    elif pos.take_profit is not None and low_p <= pos.take_profit:
                        exit_triggered = True
                        exit_price = pos.take_profit
                        reason = "TAKE_PROFIT"
                        
                # Check max holding days
                if not exit_triggered and pos.holding_days >= max_holding:
                    exit_triggered = True
                    exit_price = close_p
                    reason = "MAX_HOLDING_DAYS"
                    
                if exit_triggered:
                    portfolio.close_position(date, exit_price, reason)
                    pending_signal = None # Clear signals
                    
            # Check for signal generation today
            today_signal = signals[t]
            if today_signal in ["BUY", "SELL"]:
                pending_signal = today_signal
                pending_signal_day = t
                
            # Process trade entries based on pending signals with lag
            if pending_signal is not None and (t - pending_signal_day) >= execution_lag:
                if portfolio.active_position is None:
                    # Execute entry at today's Close
                    direction = "LONG" if pending_signal == "BUY" else "SHORT"
                    
                    # Risk-based position sizing: size = (Capital * risk_per_trade) / (price * stop_loss_pct)
                    risk_capital = portfolio.portfolio_value * risk_per_trade
                    sl_pct = stop_loss_pct if stop_loss_pct is not None else 0.02
                    max_loss_per_share = close_p * sl_pct
                    size = risk_capital / max_loss_per_share if max_loss_per_share > 0 else (portfolio.cash / close_p)
                    
                    # Limit size by available cash
                    max_cash_size = (portfolio.cash * 0.95) / close_p
                    size = min(size, max_cash_size)
                    
                    portfolio.open_position(direction, date, close_p, size, stop_loss_pct, take_profit_pct)
                else:
                    # Opposing signal exits existing position
                    pos = portfolio.active_position
                    if (pos.direction == "LONG" and pending_signal == "SELL") or \
                       (pos.direction == "SHORT" and pending_signal == "BUY"):
                        portfolio.close_position(date, close_p, "OPPOSING_SIGNAL")
                        
                pending_signal = None # Signal consumed
                
            portfolio.update_history(date, close_p)
            
        # Forced close at the end of the fold
        if portfolio.active_position is not None:
            last_date = dates[-1]
            last_close = close_prices[-1]
            portfolio.close_position(last_date, last_close, "FORCED_FOLD_END")
            portfolio.update_history(last_date, last_close)
            
        # Compile trade log outputs
        trades_out = []
        for p in portfolio.trade_log:
            trades_out.append({
                "direction": p.direction,
                "entry_date": p.entry_date,
                "entry_price": float(p.entry_price),
                "exit_date": p.exit_date,
                "exit_price": float(p.exit_price),
                "exit_reason": p.exit_reason,
                "holding_days": int(p.holding_days),
                "entry_cost": float(p.entry_cost),
                "exit_cost": float(p.exit_cost),
                "realized_pnl": float(p.get_realized_pnl()),
                "net_pnl": float(p.get_realized_pnl() - p.entry_cost - p.exit_cost)
            })
            
        return portfolio.history, trades_out

    def run_benchmark_strategy(self, strategy_name: str, fold_id: int) -> List[Dict[str, Any]]:
        """Simulates passive benchmark trading strategies."""
        test_path = self.slices_dir / f"fold_{fold_id}_test.parquet"
        test_df = pd.read_parquet(test_path)
        
        label_col = "Label_Binary" if self.label_version == "binary" else "Label_ThreeClass"
        test_df = test_df.dropna(subset=[label_col]).reset_index(drop=True)
        
        test_df["Date"] = test_df["Date"].astype(str)
        test_df = test_df.merge(self.raw_prices, on="Date", how="left")
        
        dates = test_df["Date"].tolist()
        close_prices = test_df["Raw_Close"].values
        
        initial_cap = self.bt_config["initial_capital"]
        cash = initial_cap
        portfolio_value = initial_cap
        
        history = []
        
        if strategy_name == "buy_and_hold" or strategy_name == "always_long":
            # Buy on day 1 close and hold to end
            entry_price = close_prices[0]
            size = cash / entry_price
            cash = 0.0
            
            for t in range(len(test_df)):
                date = dates[t]
                close_p = close_prices[t]
                portfolio_value = size * close_p
                history.append({
                    "date": date,
                    "portfolio_value": float(portfolio_value),
                    "cash": 0.0,
                    "open_position_value": float(portfolio_value)
                })
        else: # naive_classifier, always_flat
            # Never trade, cash stays idle
            for t in range(len(test_df)):
                date = dates[t]
                history.append({
                    "date": date,
                    "portfolio_value": float(initial_cap),
                    "cash": float(initial_cap),
                    "open_position_value": 0.0
                })
                
        return history

    def _compile_and_save_comparisons(self, model_name: str, fold_id: int, cost_mode: str,
                                      metrics: Dict[str, Any], fold_dir: Path) -> None:
        """Saves side-by-side performance records vs passive benchmarks."""
        comparisons = {
            "model_strategy": metrics
        }
        
        for bench in self.bt_config["benchmarks"]:
            if bench == "previous_step_baseline":
                # Run backtest on default step 4 baseline model
                h, t = self.run_backtest_on_fold(model_name, fold_id, cost_mode, use_default_step4_model=True)
                b_metrics = self._calculate_metrics(h, t)
            else:
                h = self.run_benchmark_strategy(bench, fold_id)
                b_metrics = self._calculate_metrics(h, [])
                
            comparisons[bench] = b_metrics
            
        with open(fold_dir / "benchmark_comparison.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(comparisons, f, default_flow_style=False)

    def _compile_aggregate_reports(self, model_name: str, cost_mode: str,
                                   fold_metrics: Dict[int, Dict[str, Any]],
                                   fold_histories: Dict[int, List[Dict[str, Any]]],
                                   fold_trades: Dict[int, List[Dict[str, Any]]],
                                   model_dir: Path) -> None:
        """Rolls up performance metrics across folds 1-7 using unified statistics."""
        folds = self.wf_config['folds']
        full_year_folds = [idx + 1 for idx, f_cfg in enumerate(folds) if not f_cfg.get("partial", False)]
        partial_folds = [idx + 1 for idx, f_cfg in enumerate(folds) if f_cfg.get("partial", False)]
        
        # Stitched daily returns compilation
        all_returns = []
        for fid in full_year_folds:
            h_df = pd.DataFrame(fold_histories[fid])
            h_df["returns"] = h_df["portfolio_value"].pct_change().fillna(0.0)
            all_returns.append(h_df["returns"])
            
        combined_returns = pd.concat(all_returns) if all_returns else pd.Series(dtype=float)
        
        # Unified Sharpe
        std_ret = combined_returns.std(ddof=1)
        mean_ret = combined_returns.mean()
        unified_sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0.0
        
        # Annualized Sharpe standard error and 95% CI (Lo 2002)
        n_obs = len(combined_returns)
        if n_obs > 0 and std_ret > 0:
            se_sharpe = np.sqrt((252 + 0.5 * (unified_sharpe ** 2)) / n_obs)
            sharpe_ci_lower = unified_sharpe - 1.96 * se_sharpe
            sharpe_ci_upper = unified_sharpe + 1.96 * se_sharpe
        else:
            sharpe_ci_lower, sharpe_ci_upper = 0.0, 0.0
            
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
        all_completed_trades = []
        for fid in full_year_folds:
            all_completed_trades.extend(fold_trades[fid])
            
        n_total_trades = len(all_completed_trades)
        
        # Net-P&L based winning and losing sum
        net_profits = sum([t["net_pnl"] for t in all_completed_trades if t["net_pnl"] > 0])
        net_losses = sum([abs(t["net_pnl"]) for t in all_completed_trades if t["net_pnl"] < 0])
        
        if net_losses > 0:
            global_profit_factor = float(net_profits / net_losses)
        else:
            global_profit_factor = "inf" if net_profits > 0 else 1.0
            
        global_expectancy = np.mean([t["net_pnl"] for t in all_completed_trades]) if n_total_trades > 0 else 0.0
        global_win_rate = len([t for t in all_completed_trades if t["net_pnl"] > 0]) / n_total_trades if n_total_trades > 0 else 0.0
        
        # Exposure (simple arithmetic average of fold exposures is acceptable)
        mean_exposure = np.mean([fold_metrics[fid]["exposure_pct"] for fid in full_year_folds])
        
        # Trade Count stats
        mean_trades = np.mean([len(fold_trades[fid]) for fid in full_year_folds])
        
        agg = {
            "mean_annualized_return_cagr": float(unified_cagr),
            "mean_sharpe_ratio": float(unified_sharpe),
            "mean_sharpe_ci_lower": float(sharpe_ci_lower),
            "mean_sharpe_ci_upper": float(sharpe_ci_upper),
            "mean_sortino_ratio": float(unified_sortino),
            "mean_max_drawdown": float(unified_max_dd),
            "global_profit_factor": global_profit_factor,
            "mean_expectancy": float(global_expectancy),
            "mean_win_rate": float(global_win_rate),
            "mean_exposure_pct": float(mean_exposure),
            "mean_trades_per_fold": float(mean_trades),
            "total_trades_count": int(n_total_trades)
        }
        
        with open(model_dir / cost_mode / "aggregate_folds_1_7.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(agg, f, default_flow_style=False)
            
        # Rollup Fold 8 (Partial)
        if partial_folds:
            p_fid = partial_folds[0]
            with open(model_dir / cost_mode / "fold_8_partial.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(fold_metrics[p_fid], f, default_flow_style=False)

    def run_backtest_pipeline(self) -> None:
        """Sequential coordinator running model simulations under both cost modes."""
        logger.info("Initializing Backtesting Simulation Engine...")
        
        # Save config snapshot
        config_snapshot = self.run_output_dir / "run_config_snapshot.yaml"
        with open(config_snapshot, "w", encoding="utf-8") as f:
            yaml.safe_dump({"backtesting": self.bt_config}, f, default_flow_style=False)
            
        models = self.config["eda"]["hyperparameter_optimization"]["eligible_models"]
        
        for m_name in models:
            logger.info(f"----------------------------------------")
            logger.info(f"Backtesting Model: {m_name}")
            logger.info(f"----------------------------------------")
            
            model_dir = self.run_output_dir / m_name
            
            for cost_mode in ["idealized", "realistic"]:
                logger.info(f"Simulating Mode: {cost_mode}...")
                cost_dir = model_dir / cost_mode
                cost_dir.mkdir(parents=True, exist_ok=True)
                
                fold_metrics = {}
                fold_histories = {}
                fold_trades = {}
                folds = self.wf_config['folds']
                
                for idx, f_cfg in enumerate(folds):
                    fold_id = idx + 1
                    fold_dir = cost_dir / f"fold_{fold_id}"
                    fold_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Run simulated trades
                    history, trades = self.run_backtest_on_fold(m_name, fold_id, cost_mode)
                    fold_histories[fold_id] = history
                    fold_trades[fold_id] = trades
                    
                    # Compute statistics
                    metrics = self._calculate_metrics(history, trades)
                    fold_metrics[fold_id] = metrics
                    
                    # Export individual files
                    with open(fold_dir / "trade_log.yaml", "w", encoding="utf-8") as f:
                        yaml.safe_dump(trades, f, default_flow_style=False)
                        
                    # Save portfolio logs and equity history series
                    port_hist = [
                        {"date": h["date"], "portfolio_value": h["portfolio_value"]}
                        for h in history
                    ]
                    with open(fold_dir / "portfolio_history.yaml", "w", encoding="utf-8") as f:
                        yaml.safe_dump(history, f, default_flow_style=False)
                        
                    with open(fold_dir / "equity_curve.yaml", "w", encoding="utf-8") as f:
                        yaml.safe_dump(port_hist, f, default_flow_style=False)
                        
                    with open(fold_dir / "performance_metrics.yaml", "w", encoding="utf-8") as f:
                        yaml.safe_dump(metrics, f, default_flow_style=False)
                        
                    # Compile comparisons vs Buy & Hold floor
                    self._compile_and_save_comparisons(m_name, fold_id, cost_mode, metrics, fold_dir)
                    
                # Compile aggregations
                self._compile_aggregate_reports(m_name, cost_mode, fold_metrics, fold_histories, fold_trades, model_dir)
                
        logger.info("Backtesting Pipeline run completed successfully.")

if __name__ == "__main__":
    try:
        global_config = load_global_config()
        # Resolve folders relative to project root
        project_root = Path(__file__).resolve().parent.parent.parent
        runs_dir = project_root / "data/walk_forward_runs"
        hpo_dir = project_root / "data/hpo_runs"
        output_dir = project_root / "data/backtest_runs"
        
        engine = BacktestEngine(
            config=global_config.model_dump(),
            runs_dir=str(runs_dir),
            hpo_dir=str(hpo_dir),
            output_dir=str(output_dir)
        )
        engine.run_backtest_pipeline()
    except Exception as e:
        logger.error(f"Backtest run failed: {e}", exc_info=True)
        sys.exit(1)
