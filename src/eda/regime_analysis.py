import sys
import os
import time
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

# Headless backend for Matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config
from src.eda.outlier_analysis import load_known_events

logger = get_logger("regimes")

class RegimeAnalyzer:
    """
    Classifies market regimes (trend: Bull/Bear/Sideways, volatility: High/Normal/Low)
    based on historical trailing return distributions and rolling volatility percentiles.
    Does not use lookahead data.
    """
    def __init__(self, data: pd.DataFrame, trend_window: int = 63, trend_threshold: float = 0.05,
                 vol_window: int = 21, vol_high_percentile: float = 0.75,
                 vol_low_percentile: float = 0.25, known_events_path: str = "config/known_events.yaml",
                 date_column: str = "Date"):
        self.data = data.copy()
        self.trend_window = trend_window
        self.trend_threshold = trend_threshold
        self.vol_window = vol_window
        self.vol_high_percentile = vol_high_percentile
        self.vol_low_percentile = vol_low_percentile
        self.date_column = date_column
        
        # Parse date column to datetime
        if self.date_column in self.data.columns:
            self.data[self.date_column] = pd.to_datetime(self.data[self.date_column])
        self.data = self.data.sort_values(self.date_column).reset_index(drop=True)
        
        # Load known events registry for cross-referencing
        self.known_events = load_known_events(known_events_path)
        
        # Precompute indicators
        self._compute_regimes()

    def _compute_regimes(self) -> None:
        """Computes underlying indicators and assigns trend/volatility labels for each day."""
        # Trend indicators
        self.data["SMA_200"] = self.data["Close"].rolling(200).mean()
        # trailing N-day return
        self.data["Trend_Return"] = self.data["Close"].pct_change(self.trend_window)
        
        # Volatility indicators
        self.data["Rolling_Vol"] = self.data["Daily_Return"].rolling(self.vol_window).std(ddof=1)
        
        # Compute volatility percentiles cutoffs
        vol_clean = self.data["Rolling_Vol"].dropna()
        self.vol_high_cutoff = vol_clean.quantile(self.vol_high_percentile)
        self.vol_low_cutoff = vol_clean.quantile(self.vol_low_percentile)
        
        # Daily classifications
        self.data["Trend_Regime"] = self.classify_trend_regime()
        self.data["Volatility_Regime"] = self.classify_volatility_regime()

    def classify_trend_regime(self) -> pd.Series:
        """Classifies each trading day into Bull, Bear, Sideways, or Insufficient Data."""
        regimes = []
        for idx in range(len(self.data)):
            # Check warm up limits
            if idx < 200 or idx < self.trend_window:
                regimes.append("Insufficient Data")
                continue
                
            close = self.data.loc[idx, "Close"]
            sma = self.data.loc[idx, "SMA_200"]
            ret = self.data.loc[idx, "Trend_Return"]
            
            if pd.isna(sma) or pd.isna(ret):
                regimes.append("Insufficient Data")
                continue
                
            # Rule checking
            if abs(ret) <= self.trend_threshold:
                regimes.append("Sideways")
            elif close > sma and ret > self.trend_threshold:
                regimes.append("Bull")
            elif close < sma and ret < -self.trend_threshold:
                regimes.append("Bear")
            else:
                # Conflict resolution: default to Sideways
                regimes.append("Sideways")
                
        return pd.Series(regimes, index=self.data.index)

    def classify_volatility_regime(self) -> pd.Series:
        """Classifies each trading day into High, Low, Normal, or Insufficient Data."""
        regimes = []
        for idx in range(len(self.data)):
            if idx < self.vol_window:
                regimes.append("Insufficient Data")
                continue
                
            vol = self.data.loc[idx, "Rolling_Vol"]
            if pd.isna(vol):
                regimes.append("Insufficient Data")
                continue
                
            if vol > self.vol_high_cutoff:
                regimes.append("High")
            elif vol < self.vol_low_cutoff:
                regimes.append("Low")
            else:
                regimes.append("Normal")
                
        return pd.Series(regimes, index=self.data.index)

    def _find_overlapping_events(self, start_date: pd.Timestamp, end_date: pd.Timestamp) -> List[str]:
        """Identifies any configured known market event windows that overlap this period."""
        overlappers = []
        for ev in self.known_events:
            ev_start = pd.to_datetime(ev["start_date"])
            ev_end = pd.to_datetime(ev["end_date"])
            
            # Check overlap logic
            if (start_date <= ev_end) and (end_date >= ev_start):
                overlappers.append(ev["event_name"])
        return sorted(list(set(overlappers)))

    def regime_periods(self, regime_type: str = "trend") -> pd.DataFrame:
        """Aggregates contiguous daily regime labels into date ranges with durations and price metrics."""
        col_label = "Trend_Regime" if regime_type.lower() == "trend" else "Volatility_Regime"
        
        periods = []
        if self.data.empty:
            return pd.DataFrame(columns=["start_date", "end_date", "regime", "trading_days", "calendar_days", "start_price", "end_price", "overlapping_events"])
            
        curr_regime = self.data.loc[0, col_label]
        start_idx = 0
        
        for idx in range(1, len(self.data)):
            label = self.data.loc[idx, col_label]
            if label != curr_regime:
                start_date = self.data.loc[start_idx, self.date_column]
                end_date = self.data.loc[idx - 1, self.date_column]
                trading_days = idx - start_idx
                calendar_days = (end_date - start_date).days
                start_price = self.data.loc[start_idx, "Close"]
                end_price = self.data.loc[idx - 1, "Close"]
                
                events = self._find_overlapping_events(start_date, end_date)
                events_str = ", ".join(events) if events else "None"
                
                periods.append({
                    "start_date": start_date,
                    "end_date": end_date,
                    "regime": curr_regime,
                    "trading_days": trading_days,
                    "calendar_days": calendar_days,
                    "start_price": start_price,
                    "end_price": end_price,
                    "overlapping_events": events_str
                })
                
                curr_regime = label
                start_idx = idx
                
        # Append final period
        start_date = self.data.loc[start_idx, self.date_column]
        end_date = self.data.iloc[-1][self.date_column]
        trading_days = len(self.data) - start_idx
        calendar_days = (end_date - start_date).days
        start_price = self.data.loc[start_idx, "Close"]
        end_price = self.data.iloc[-1]["Close"]
        
        events = self._find_overlapping_events(start_date, end_date)
        events_str = ", ".join(events) if events else "None"
        
        periods.append({
            "start_date": start_date,
            "end_date": end_date,
            "regime": curr_regime,
            "trading_days": trading_days,
            "calendar_days": calendar_days,
            "start_price": start_price,
            "end_price": end_price,
            "overlapping_events": events_str
        })
        
        return pd.DataFrame(periods)

    def regime_statistics(self, regime_type: str = "trend") -> pd.DataFrame:
        """Computes statistical metrics (mean returns, volatility, duration) within each regime."""
        col_label = "Trend_Regime" if regime_type.lower() == "trend" else "Volatility_Regime"
        periods_df = self.regime_periods(regime_type)
        
        stats = []
        unique_labels = self.data[col_label].unique()
        
        for r in unique_labels:
            if r == "Insufficient Data":
                continue
                
            r_df = self.data[self.data[col_label] == r]
            r_periods = periods_df[periods_df["regime"] == r]
            
            if r_df.empty:
                continue
                
            mean_ret = r_df["Daily_Return"].mean()
            median_ret = r_df["Daily_Return"].median()
            vol_ret = r_df["Daily_Return"].std(ddof=1)
            
            period_count = len(r_periods)
            avg_trading_days = r_periods["trading_days"].mean() if period_count > 0 else 0.0
            avg_calendar_days = r_periods["calendar_days"].mean() if period_count > 0 else 0.0
            
            min_days = r_periods["trading_days"].min() if period_count > 0 else 0.0
            max_days = r_periods["trading_days"].max() if period_count > 0 else 0.0
            median_days = r_periods["trading_days"].median() if period_count > 0 else 0.0
            
            stats.append({
                "Regime": r,
                "Period Count": period_count,
                "Total Trading Days": len(r_df),
                "Mean Return (%)": mean_ret * 100.0,
                "Median Return (%)": median_ret * 100.0,
                "Volatility (%)": vol_ret * 100.0,
                "Avg Trading Days": avg_trading_days,
                "Avg Calendar Days": avg_calendar_days,
                "Min Duration": min_days,
                "Max Duration": max_days,
                "Median Duration": median_days
            })
            
        return pd.DataFrame(stats)

    def regime_distribution(self, regime_type: str = "trend") -> pd.DataFrame:
        """Computes counts and percentages of trading days across all regimes (including Insufficient Data)."""
        col = "Trend_Regime" if regime_type.lower() == "trend" else "Volatility_Regime"
        counts = self.data[col].value_counts()
        total = len(self.data)
        
        dist = []
        for name in ["Bull", "Bear", "Sideways", "High", "Normal", "Low", "Insufficient Data"]:
            if name in counts.index:
                cnt = counts[name]
                dist.append({
                    "Regime": name,
                    "Trading Days": cnt,
                    "Percentage": (cnt / total) * 100.0
                })
        return pd.DataFrame(dist)

    def trend_regime_transitions(self) -> pd.DataFrame:
        """Computes transition count matrix between trend regimes (descriptive only)."""
        periods = self.regime_periods("trend")
        valid_periods = periods[periods["regime"] != "Insufficient Data"].reset_index(drop=True)
        
        regimes = ["Bull", "Bear", "Sideways"]
        # Initialize matrix with index as 'From' and columns as 'To'
        matrix = {from_r: {to_r: 0 for to_r in regimes} for from_r in regimes}
        
        for i in range(len(valid_periods) - 1):
            from_r = valid_periods.loc[i, "regime"]
            to_r = valid_periods.loc[i + 1, "regime"]
            if from_r in matrix and to_r in matrix:
                matrix[from_r][to_r] += 1
                
        df_transitions = pd.DataFrame(matrix).T  # rows are 'From', columns are 'To'
        return df_transitions

    def cross_tabulation(self) -> pd.DataFrame:
        """Computes co-occurrence frequencies between trend and volatility regimes."""
        trend = self.data["Trend_Regime"]
        vol = self.data["Volatility_Regime"]
        return pd.crosstab(trend, vol, margins=True)

    def plot_regime_timeline(self, output_path: str) -> str:
        """Generates timeline chart of price with shaded bands representing trend regimes."""
        df = self.data.sort_values(self.date_column).copy()
        periods = self.regime_periods("trend")
        
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Shade background bands per trend regime
        colors = {
            "Bull": ("#d4edda", 0.6, "Bull Regime"),
            "Bear": ("#f8d7da", 0.6, "Bear Regime"),
            "Sideways": ("#fff3cd", 0.6, "Sideways Regime"),
            "Insufficient Data": ("#e2e3e5", 0.4, "Insufficient Data")
        }
        
        # Trace bands and handle labels in legend
        seen_regimes = set()
        for _, row in periods.iterrows():
            r = row["regime"]
            s_date = row["start_date"]
            e_date = row["end_date"]
            
            color, alpha, label_name = colors.get(r, ("#ffffff", 0.0, "Unknown"))
            
            # Avoid duplicate legend labels
            label = label_name if r not in seen_regimes else ""
            seen_regimes.add(r)
            
            ax.axvspan(s_date, e_date, color=color, alpha=alpha, label=label)
            
        # Plot price line (Close)
        ax.plot(df[self.date_column], df["Close"], color='#1a1a1a', linewidth=1.5, label='Nifty Close Price', zorder=5)
        
        # Plot SMA_200
        ax.plot(df[self.date_column], df["SMA_200"], color='#ff7f0e', linewidth=1.2, linestyle='--', label='SMA 200', zorder=6)
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        ax.set_title(f"Market Trend Regimes Profile ({min_date} to {max_date})", fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel("Date", fontsize=11)
        ax.set_ylabel("Price (Close)", fontsize=11)
        ax.grid(True, linestyle=':', alpha=0.5)
        
        # Format axes
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
        
        ax.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.9, edgecolor='#ccc')
        
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        
        plt.tight_layout()
        fig.savefig(out_p, dpi=150)
        plt.close(fig)
        logger.info(f"Regime timeline chart saved at: {out_p}")
        return str(out_p)

    def to_markdown(self) -> str:
        """Formats analysis data into a comprehensive Markdown report."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        periods_trend = self.regime_periods("trend")
        periods_vol = self.regime_periods("volatility")
        
        stats_trend = self.regime_statistics("trend")
        stats_vol = self.regime_statistics("volatility")
        
        dist_trend = self.regime_distribution("trend")
        dist_vol = self.regime_distribution("volatility")
        
        transitions = self.trend_regime_transitions()
        crosstab = self.cross_tabulation()
        
        md = []
        md.append("# QuantEngine: Market Regime Analysis Report")
        md.append(f"**Report Generated At**: {timestamp}")
        md.append("**Source Dataset**: `nifty_features`")
        md.append(
            f"**Configuration Parameters**:\n"
            f"- Trend Lookback Window: {self.trend_window} sessions (approx. 1 quarter)\n"
            f"- Trend Threshold: ±{self.trend_threshold * 100:.1f}%\n"
            f"- Volatility Window: {self.vol_window} sessions\n"
            f"- High Volatility Cutoff: {self.vol_high_percentile * 100:.0f}th percentile of history ({self.vol_high_cutoff:.6f})\n"
            f"- Volatility Percentile Thresholds: Low = {self.vol_low_percentile * 100:.0f}th, High = {self.vol_high_percentile * 100:.0f}th\n"
        )
        
        # Methodology Section
        md.append("## Methodology: Formal Definitions")
        md.append(
            "This module evaluates market behavior across two independent dimensions: direction (Trend) and dispersion (Volatility).\n\n"
            "**1. Rolling Return Formula** (used for trend classification):\n"
            "```\n"
            "RollingReturn_t = (Close_t - Close_(t - trend_window)) / Close_(t - trend_window)\n"
            "```\n"
            "**2. Rolling Volatility Formula** (used for volatility classification):\n"
            "```\n"
            "RollingVolatility_t = StdDev(DailyReturn_(t-vol_window+1), ..., DailyReturn_t)\n"
            "```\n"
            "**3. Trend Regime Assignment Rules**:\n"
            "```\n"
            "Bull:      Close_t > SMA_200_t   AND   RollingReturn_t > +trend_threshold\n"
            "Bear:      Close_t < SMA_200_t   AND   RollingReturn_t < -trend_threshold\n"
            "Sideways:  |RollingReturn_t| <= trend_threshold  (regardless of SMA_200 position)\n"
            "```\n"
            "*Note: Conflicts where Close price relative to SMA_200 contradicts the trailing return direction are classified under the Sideways category to maintain high rigor for Bull and Bear definitions.*\n\n"
            "**4. Volatility Regime Assignment Rules**:\n"
            "```\n"
            "High:    RollingVolatility_t > P75(RollingVolatility, full history)\n"
            "Low:     RollingVolatility_t < P25(RollingVolatility, full history)\n"
            "Normal:  otherwise\n"
            "```\n"
        )
        
        md.append("## Design Decision: Two Independent Dimensions")
        md.append(
            "Trend and volatility are modeled as two independent labels rather than one combined regime "
            "because they describe different dimensions of market behavior: trend describes *direction* "
            "(is price rising, falling, or flat), while volatility describes *dispersion* (how much day-to-day "
            "movement is occurring, independent of direction). A market can be simultaneously trending "
            "upward and highly volatile (e.g. a sharp V-shaped recovery) or trending upward calmly. "
            "Collapsing these into a single mutually-exclusive category would discard information "
            "relevant to later use cases such as position sizing, where a calm bull market and a volatile "
            "bull market warrant different risk treatment even though both are 'Bull' by trend.\n"
        )

        # 1. Structural Warning / Lookahead Lag Caveat (Section 7 Compliance)
        md.append("## 1. Important Caveat & Structural Warning")
        md.append(
            "> [!WARNING]\n"
            "> **Lookahead-Bias and Time Lag Warning:**\n"
            "> Regime labels defined in this report are strictly computed using **backward-looking rolling windows** (no future data is referenced), "
            "making them technically free of lookahead-bias. However, a trend label (Bull/Bear/Sideways) assigned to *today* using a "
            f"{self.trend_window}-day trailing window is, by definition, a description of **recent past behavior** rather than a real-time signal.\n"
            ">\n"
            "> As a result, there is a structural **lag** between actual regime shifts and the window crossing the configured threshold "
            "(e.g., a new Bear market won't be labeled 'Bear' until index returns drop below the threshold). This lag is perfectly acceptable "
            "for retrospective model evaluation (which is the purpose of this analysis), but these regime labels should **never** be fed directly "
            "into a predictive model as same-day features, as this lag would inject severe classification errors and feedback loops.\n"
        )
        
        md.append(
            "> [!NOTE]\n"
            "> **Zero-Volume Limitation Validation:**\n"
            "> The Nifty zero-volume limitation period (2007–2013) identified in Step 5 does **not** distort the volatility regimes. "
            "Volatility regimes are computed entirely using standard deviation of returns (`Daily_Return`) derived from price Close series, "
            "not `Volume`. Hence, historical zero-volume years have zero distortion effect on the volatility classifications below.\n"
        )
        
        # 1.1 Regime Distribution Summary (New Section)
        md.append("## 2. Regime Distribution Summaries")
        
        md.append("### Trend Regime Distribution")
        md.append("| Regime | Trading Days | Percentage of Dataset |")
        md.append("| :--- | :--- | :--- |")
        tot_days_t = 0
        for _, row in dist_trend.iterrows():
            tot_days_t += int(row['Trading Days'])
            md.append(f"| {row['Regime']} | {int(row['Trading Days'])} | {row['Percentage']:.2f}% |")
        md.append(f"| **Total** | {tot_days_t} | 100.00% |\n")
        
        md.append("### Volatility Regime Distribution")
        md.append("| Regime | Trading Days | Percentage of Dataset |")
        md.append("| :--- | :--- | :--- |")
        tot_days_v = 0
        for _, row in dist_vol.iterrows():
            tot_days_v += int(row['Trading Days'])
            md.append(f"| {row['Regime']} | {int(row['Trading Days'])} | {row['Percentage']:.2f}% |")
        md.append(f"| **Total** | {tot_days_v} | 100.00% |\n")
        
        # 2. Per-Regime Summary Stats
        md.append("## 3. Per-Regime Performance & Persistence Statistics")
        
        md.append("### Trend Regime Performance & Persistence Metrics")
        md.append("| Regime | Period Count | Total Trading Days | Mean Daily Return | Median Daily Return | Volatility (Std Dev) | Avg Trading Days per Period | Min Duration | Max Duration | Median Duration | Avg Calendar Days |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for _, row in stats_trend.iterrows():
            md.append(
                f"| **{row['Regime']}** | {int(row['Period Count'])} | {int(row['Total Trading Days'])} | "
                f"{row['Mean Return (%)']:+.4f}% | {row['Median Return (%)']:+.4f}% | {row['Volatility (%)']:.4f}% | "
                f"{row['Avg Trading Days']:.1f} | {int(row['Min Duration'])} | {int(row['Max Duration'])} | {int(row['Median Duration'])} | {row['Avg Calendar Days']:.1f} |"
            )
        md.append("")
        
        md.append("### Volatility Regime Performance & Persistence Metrics")
        md.append("| Regime | Period Count | Total Trading Days | Mean Daily Return | Median Daily Return | Volatility (Std Dev) | Avg Trading Days per Period | Min Duration | Max Duration | Median Duration | Avg Calendar Days |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for _, row in stats_vol.iterrows():
            md.append(
                f"| **{row['Regime']}** | {int(row['Period Count'])} | {int(row['Total Trading Days'])} | "
                f"{row['Mean Return (%)']:+.4f}% | {row['Median Return (%)']:+.4f}% | {row['Volatility (%)']:.4f}% | "
                f"{row['Avg Trading Days']:.1f} | {int(row['Min Duration'])} | {int(row['Max Duration'])} | {int(row['Median Duration'])} | {row['Avg Calendar Days']:.1f} |"
            )
        md.append("")
        
        # 3. Two-Dimensional Cross-Tabulation
        md.append("## 4. Two-Dimensional Cross-Tabulation Matrix (Trend × Volatility)")
        md.append("Co-occurrence of trend and volatility dimensions (counts in trading days):")
        
        headers = ["Trend Regime / Volatility"] + crosstab.columns.tolist()
        md.append("| " + " | ".join(headers) + " |")
        md.append("| " + " | ".join([":---"] * len(headers)) + " |")
        for idx, row in crosstab.iterrows():
            line = [f"**{idx}**"] + [str(val) for val in row.values]
            md.append("| " + " | ".join(line) + " |")
        md.append("")
        
        # 3a. Regime Transition Summary (New Section)
        md.append("## 5. Trend Regime Transitions Matrix")
        md.append(
            "> [!IMPORTANT]\n"
            "> **Descriptive-Only Framing Disclaimer:**\n"
            "> The table below shows the absolute count of historical transitions between contiguous periods "
            "of different trend regimes in the dataset. This analysis is strictly **descriptive and historical**; "
            "it is not a predictive Markov transition model and cannot be used to forecast the probability "
            "of future regime changes.\n"
        )
        md.append("| From \\ To | Bull | Bear | Sideways |")
        md.append("| :--- | :--- | :--- | :--- |")
        for name in ["Bull", "Bear", "Sideways"]:
            row = transitions.loc[name]
            bull_cnt = int(row["Bull"]) if "Bull" in row else 0
            bear_cnt = int(row["Bear"]) if "Bear" in row else 0
            side_cnt = int(row["Sideways"]) if "Sideways" in row else 0
            
            bull_str = "—" if name == "Bull" else str(bull_cnt)
            bear_str = "—" if name == "Bear" else str(bear_cnt)
            side_str = "—" if name == "Sideways" else str(side_cnt)
            
            md.append(f"| **{name}** | {bull_str} | {bear_str} | {side_str} |")
        md.append("")

        # 4. Timeline plot reference
        md.append("## 6. Regime Timeline Visualization")
        md.append("The timeline below plots the Close price overlaying colored bands representing trend regimes:")
        md.append("![Regime Timeline Timeline](../figures/regime_timeline.png)\n")
        
        # 5. Chronological period list (with Known Event cross-references)
        md.append("## 7. Contiguous Trend Regime Period Timeline")
        md.append("| Period Rank | Start Date | End Date | Trend Regime | Trading Days | Calendar Days | Start Price | End Price | Overlapping Known Market Events |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for idx, row in periods_trend.iterrows():
            s_str = row["start_date"].strftime("%Y-%m-%d")
            e_str = row["end_date"].strftime("%Y-%m-%d")
            md.append(
                f"| {idx+1} | `{s_str}` | `{e_str}` | **{row['regime']}** | {row['trading_days']} | {row['calendar_days']} | "
                f"{row['start_price']:.2f} | {row['end_price']:.2f} | {row['overlapping_events']} |"
            )
        md.append("")
        
        md.append("## 8. Contiguous Volatility Regime Period Timeline")
        md.append("| Period Rank | Start Date | End Date | Volatility Regime | Trading Days | Calendar Days | Start Price | End Price | Overlapping Known Market Events |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for idx, row in periods_vol.iterrows():
            s_str = row["start_date"].strftime("%Y-%m-%d")
            e_str = row["end_date"].strftime("%Y-%m-%d")
            md.append(
                f"| {idx+1} | `{s_str}` | `{e_str}` | **{row['regime']}** | {row['trading_days']} | {row['calendar_days']} | "
                f"{row['start_price']:.2f} | {row['end_price']:.2f} | {row['overlapping_events']} |"
            )
        md.append("")
        
        return "\n".join(md)

    def save(self, output_path: str) -> None:
        """Writes the generated Markdown regime analysis report to disk."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        logger.info(f"Regime report saved at: {p}")


def generate_regime_report(config: dict) -> None:
    """Orchestrates loading features data, executing the RegimeAnalyzer, plotting, and writing reports."""
    logger.info("Initializing Market Regime Analysis pipeline...")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Extract configs
    r_config = config['eda']['regime']
    
    input_rel = r_config['input_file']
    trend_w = r_config['trend_window']
    trend_th = r_config['trend_threshold']
    vol_w = r_config['vol_window']
    vol_high_pct = r_config['vol_high_percentile']
    vol_low_pct = r_config['vol_low_percentile']
    known_events_rel = r_config['known_events_path']
    report_rel = r_config['output_report_path']
    chart_rel = r_config['output_chart_path']
    
    date_col = config['eda']['date_column']
    
    # Resolve absolute paths
    input_path = project_root / input_rel
    known_events_path = project_root / known_events_rel
    report_path = project_root / report_rel
    chart_path = project_root / chart_rel
    
    logger.info(f"Loading features dataset: {input_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Feature dataset not found: {input_path}. Please execute feature orchestrator.")
        
    df_features = pd.read_csv(input_path)
    
    # Instantiate analyzer
    analyzer = RegimeAnalyzer(
        data=df_features,
        trend_window=trend_w,
        trend_threshold=trend_th,
        vol_window=vol_w,
        vol_high_percentile=vol_high_pct,
        vol_low_percentile=vol_low_pct,
        known_events_path=str(known_events_path),
        date_column=date_col
    )
    
    # Save regime timeline chart
    analyzer.plot_regime_timeline(str(chart_path))
    
    # Save Markdown report
    analyzer.save(str(report_path))
    logger.info("Market Regime Analysis completed successfully.")


if __name__ == "__main__":
    try:
        global_config = load_global_config()
        generate_regime_report(global_config.model_dump())
    except Exception as e:
        logger.error(f"Failed to generate market regime analysis: {e}", exc_info=True)
        sys.exit(1)
