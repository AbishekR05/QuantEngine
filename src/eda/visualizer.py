import sys
import os
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pandas as pd
import numpy as np

# HEADLESS BACKEND FOR MATPLOTLIB (Crucial for CLI/scripts execution)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("visualizer")

class Visualizer:
    """
    Generates high-quality technical indicators and data distributions plots
    from clean stock datasets and engineered feature datasets.
    """
    def __init__(self, clean_data: pd.DataFrame, features_data: pd.DataFrame, 
                 output_dir: str, date_column: str = "Date", 
                 dpi: int = 150, figure_size: Tuple[int, int] = (12, 6),
                 rolling_volatility_window: int = 21,
                 rsi_overbought: float = 70.0, rsi_oversold: float = 30.0):
        self.clean_data = clean_data.copy()
        self.features_data = features_data.copy()
        self.output_dir = Path(output_dir)
        self.date_column = date_column
        self.dpi = dpi
        self.figure_size = figure_size
        self.vol_window = rolling_volatility_window
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert Date columns to datetime objects
        for df in [self.clean_data, self.features_data]:
            if date_column in df.columns:
                df[date_column] = pd.to_datetime(df[date_column])

    def _apply_style(self, ax: plt.Axes, title: str, xlabel: str, ylabel: str, has_legend: bool = True) -> None:
        """Applies a consistent styling, grids, titles, and formats date markers on the X axis."""
        ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
        ax.set_xlabel(xlabel, fontsize=10, labelpad=5)
        ax.set_ylabel(ylabel, fontsize=10, labelpad=5)
        ax.grid(True, linestyle='--', alpha=0.5)
        if has_legend:
            ax.legend(loc='best', fontsize=9)
            
        # If the X-axis is time-series date column, thin ticks
        if xlabel.lower() == 'date':
            ax.xaxis.set_major_locator(mdates.YearLocator(3))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            plt.setp(ax.get_xticklabels(), rotation=30, ha='right')

    def plot_closing_price(self) -> str:
        """Plots historical closing price over time from clean dataset."""
        df = self.clean_data.sort_values(self.date_column)
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        ax.plot(df[self.date_column], df['Close'], color='#1f77b4', linewidth=1.2, label='NIFTY 50 Close')
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50 Closing Price ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "Closing Index Value (Points)")
        
        out_path = self.output_dir / "closing_price.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_volume(self) -> str:
        """Plots daily trading volume, shading and annotating the historical zero-volume period."""
        df = self.clean_data.sort_values(self.date_column)
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        ax.plot(df[self.date_column], df['Volume'], color='#7f7f7f', alpha=0.8, linewidth=1.0, label='Trading Volume')
        
        # Shade zero volume limitation period (2007 to 2013-12-31)
        start_date = df[self.date_column].min()
        end_zero = pd.to_datetime('2013-12-31')
        if start_date < end_zero:
            ax.axvspan(start_date, end_zero, color='red', alpha=0.1, label='Zero-Volume (Index Feed Limitation)')
            mid_date = start_date + (end_zero - start_date) / 2
            # Highlighting annotation bubble
            ax.text(mid_date, df['Volume'].max() * 0.7, 
                    "Expected Outliers\nZero-Volume Era\n(2007-2013)", 
                    color='darkred', ha='center', fontsize=9, fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.85, edgecolor='red', boxstyle='round,pad=0.4'))
            
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50 Daily Trading Volume ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "Volume (Shares Traded)")
        
        out_path = self.output_dir / "volume.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_daily_returns(self) -> str:
        """Plots daily returns time-series from features dataset."""
        df = self.features_data.sort_values(self.date_column)
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        ax.plot(df[self.date_column], df['Daily_Return'] * 100.0, color='#2ca02c', alpha=0.6, linewidth=0.8, label='Daily Return')
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50 Daily Percentage Returns ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "Returns (%)")
        
        out_path = self.output_dir / "daily_returns.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_log_returns(self) -> str:
        """Plots log returns time-series from features dataset."""
        df = self.features_data.sort_values(self.date_column)
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        ax.plot(df[self.date_column], df['Log_Return'] * 100.0, color='#bcbd22', alpha=0.6, linewidth=0.8, label='Log Return')
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50 Daily Log Returns ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "Log Returns (%)")
        
        out_path = self.output_dir / "log_returns.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_rsi(self) -> str:
        """Plots Relative Strength Index (RSI_14) with overbought/oversold boundaries."""
        df = self.features_data.sort_values(self.date_column)
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        # Plot RSI
        ax.plot(df[self.date_column], df['RSI_14'], color='#9467bd', linewidth=1.0, label='RSI (14)')
        
        # Draw threshold boundaries
        ax.axhline(self.rsi_overbought, color='r', linestyle='--', alpha=0.7, label=f'Overbought Threshold ({self.rsi_overbought})')
        ax.axhline(self.rsi_oversold, color='g', linestyle='--', alpha=0.7, label=f'Oversold Threshold ({self.rsi_oversold})')
        ax.axhspan(self.rsi_oversold, self.rsi_overbought, color='#9467bd', alpha=0.1) # Highlight normal zone
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50 Relative Strength Index (RSI_14) ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "RSI Value")
        ax.set_ylim(0, 100)
        
        out_path = self.output_dir / "rsi_14.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_macd(self) -> str:
        """Plots MACD lines alongside bullish/bearish momentum histogram overlays."""
        df = self.features_data.sort_values(self.date_column)
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        ax.plot(df[self.date_column], df['MACD'], color='#1f77b4', linewidth=1.0, label='MACD Line')
        ax.plot(df[self.date_column], df['MACD_Signal'], color='#ff7f0e', linewidth=1.0, label='Signal Line')
        
        # Color-coded momentum shading (instead of heavy rendering bars)
        hist = df['MACD_Hist']
        ax.fill_between(df[self.date_column], hist, 0, where=(hist >= 0), color='green', alpha=0.4, label='Bullish Momentum')
        ax.fill_between(df[self.date_column], hist, 0, where=(hist < 0), color='red', alpha=0.4, label='Bearish Momentum')
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50 MACD Indicators ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "MACD / Signal value")
        
        out_path = self.output_dir / "macd.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_ema(self, period: int) -> str:
        """Plots overlaid close price vs the specified EMA indicator line."""
        df = self.features_data.sort_values(self.date_column)
        ema_col = f"EMA_{period}"
        
        if ema_col not in df.columns:
            raise KeyError(f"EMA column '{ema_col}' does not exist. Please rebuild features.")
            
        fig, ax = plt.subplots(figsize=self.figure_size)
        ax.plot(df[self.date_column], df['Close'], color='#7f7f7f', alpha=0.5, linewidth=1.0, label='Close price')
        ax.plot(df[self.date_column], df[ema_col], color='#d62728', linewidth=1.5, label=f'EMA {period}')
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50 Price vs. {period}-Period EMA ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "Price (Points)")
        
        out_path = self.output_dir / f"ema_{period}.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_atr(self) -> str:
        """Plots Average True Range (ATR_14) volatility indicator."""
        df = self.features_data.sort_values(self.date_column)
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        ax.plot(df[self.date_column], df['ATR_14'], color='#e377c2', linewidth=1.2, label='ATR (14)')
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50 Average True Range (ATR_14) ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "ATR Points (Index)")
        
        out_path = self.output_dir / "atr_14.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_bollinger_bands(self) -> str:
        """Plots Close price surrounded by shaded Bollinger Bands wrapper."""
        df = self.features_data.sort_values(self.date_column)
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        ax.plot(df[self.date_column], df['Close'], color='#7f7f7f', alpha=0.6, linewidth=1.0, label='Close price')
        ax.plot(df[self.date_column], df['BB_Middle'], color='#ff7f0e', linestyle='--', label='Middle Band')
        ax.plot(df[self.date_column], df['BB_Upper'], color='#1f77b4', alpha=0.5, label='Upper Band')
        ax.plot(df[self.date_column], df['BB_Lower'], color='#1f77b4', alpha=0.5, label='Lower Band')
        
        # Shade the gap inside Bollinger Bands
        ax.fill_between(df[self.date_column], df['BB_Lower'], df['BB_Upper'], color='#1f77b4', alpha=0.1, label='BB range')
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50 Bollinger Bands (20, 2) ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "Price (Points)")
        
        out_path = self.output_dir / "bollinger_bands.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_histogram(self, column: str) -> str:
        """Plots histogram distribution for the chosen column from its parent dataset."""
        if column in self.clean_data.columns:
            df = self.clean_data
            ds_name = "nsei_clean"
        elif column in self.features_data.columns:
            df = self.features_data
            ds_name = "nifty_features"
        else:
            raise KeyError(f"Column '{column}' not found in either dataset.")
            
        fig, ax = plt.subplots(figsize=self.figure_size)
        series = df[column].dropna()
        
        # Formulate histogram
        n, bins, patches = ax.hist(series, bins=50, color='#17becf', edgecolor='black', alpha=0.7)
        
        # Volume column needs annotation of the zero-volume outliers bin
        if column.lower() == 'volume':
            # Target first bin (0 value) and point an arrow
            ax.annotate('Zero-Volume Outliers (2007-2013 Feed)', 
                        xy=(bins[0] + (bins[1]-bins[0])/2, n[0]), 
                        xytext=(bins[1] + (bins[2]-bins[1])*10, n[0] * 0.75),
                        arrowprops=dict(facecolor='red', shrink=0.08, width=1.5, headwidth=6),
                        fontsize=9, color='darkred', fontweight='bold',
                        bbox=dict(facecolor='white', alpha=0.85, edgecolor='red', boxstyle='round,pad=0.3'))
            
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"Histogram Distribution: {column} ({ds_name}, {min_date} to {max_date})"
        self._apply_style(ax, title, column, "Frequency Count", has_legend=False)
        
        out_path = self.output_dir / f"histogram_{column.lower()}.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_boxplot(self, column: str) -> str:
        """Plots horizontal boxplot for the chosen column."""
        if column in self.clean_data.columns:
            df = self.clean_data
            ds_name = "nsei_clean"
        elif column in self.features_data.columns:
            df = self.features_data
            ds_name = "nifty_features"
        else:
            raise KeyError(f"Column '{column}' not found in either dataset.")
            
        fig, ax = plt.subplots(figsize=self.figure_size)
        series = df[column].dropna()
        
        ax.boxplot(series, vert=False, patch_artist=True,
                   boxprops=dict(facecolor='#ffbb78', color='black'),
                   medianprops=dict(color='red', linewidth=1.5))
        
        if column.lower() == 'volume':
            ax.text(series.min(), 1.15, 
                    "Includes ~1,320 days of zero volumes\ndue to exchange data limit (2007-2013)", 
                    color='darkred', fontsize=9, fontweight='bold', ha='left',
                    bbox=dict(facecolor='white', alpha=0.85, edgecolor='red', boxstyle='round,pad=0.3'))
                    
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"Boxplot distribution & outlier profile: {column} ({ds_name}, {min_date} to {max_date})"
        self._apply_style(ax, title, column, "", has_legend=False)
        ax.set_yticklabels([])
        
        out_path = self.output_dir / f"boxplot_{column.lower()}.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def plot_rolling_volatility(self, window: int) -> str:
        """Plots rolling volatility standard deviation of daily returns over time."""
        df = self.features_data.sort_values(self.date_column).copy()
        
        # Calculate daily standard deviation and convert to percentage
        df['Rolling_Vol'] = df['Daily_Return'].rolling(window=window).std() * 100.0
        
        fig, ax = plt.subplots(figsize=self.figure_size)
        ax.plot(df[self.date_column], df['Rolling_Vol'], color='#9467bd', linewidth=1.0, label=f'{window}-Day rolling std')
        
        min_date = df[self.date_column].min().strftime('%Y-%m-%d')
        max_date = df[self.date_column].max().strftime('%Y-%m-%d')
        title = f"NIFTY 50: {window}-Day Rolling Return Volatility ({min_date} to {max_date})"
        self._apply_style(ax, title, "Date", "Daily Volatility (%)")
        
        out_path = self.output_dir / f"rolling_volatility_{window}d.png"
        plt.tight_layout()
        fig.savefig(out_path, dpi=self.dpi)
        plt.close(fig)
        logger.debug(f"Saved: {out_path}")
        return str(out_path)

    def generate_all(self, ema_periods: List[int]) -> List[str]:
        """Runs and outputs all 16 figures individually, returning a manifest list."""
        logger.info("Generating all visualization plots...")
        paths = []
        paths.append(self.plot_closing_price())
        paths.append(self.plot_volume())
        paths.append(self.plot_daily_returns())
        paths.append(self.plot_log_returns())
        paths.append(self.plot_rsi())
        paths.append(self.plot_macd())
        
        # EMA plots
        for p in ema_periods:
            paths.append(self.plot_ema(p))
            
        paths.append(self.plot_atr())
        paths.append(self.plot_bollinger_bands())
        
        # Histograms
        paths.append(self.plot_histogram("Daily_Return"))
        paths.append(self.plot_histogram("Volume"))
        
        # Boxplots
        paths.append(self.plot_boxplot("Daily_Return"))
        paths.append(self.plot_boxplot("Volume"))
        
        # Rolling Volatility
        paths.append(self.plot_rolling_volatility(self.vol_window))
        
        logger.info(f"Successfully generated {len(paths)} visualization files under: {self.output_dir}")
        return paths


def generate_all_plots(config: dict) -> List[str]:
    """Orchestrates loading datasets, initializing visualizer, and generating files."""
    project_root = Path(__file__).resolve().parent.parent.parent
    
    clean_rel = config['eda']['input_files']['clean']
    feat_rel = config['eda']['input_files']['features']
    fig_config = config['eda']['figures']
    
    clean_path = project_root / clean_rel
    features_path = project_root / feat_rel
    output_dir = project_root / fig_config['output_dir']
    
    logger.info(f"Loading data paths: {clean_path} & {features_path}")
    
    if not clean_path.exists() or not features_path.exists():
        raise FileNotFoundError("Clean or features dataset files missing. Please run pipeline first.")
        
    df_clean = pd.read_csv(clean_path)
    df_features = pd.read_csv(features_path)
    
    # Initialize Visualizer
    fig_size = tuple(fig_config['figure_size'])
    viz = Visualizer(
        clean_data=df_clean,
        features_data=df_features,
        output_dir=str(output_dir),
        date_column=config['eda']['date_column'],
        dpi=fig_config['dpi'],
        figure_size=fig_size,
        rolling_volatility_window=fig_config['rolling_volatility_window'],
        rsi_overbought=fig_config['rsi_overbought'],
        rsi_oversold=fig_config['rsi_oversold']
    )
    
    return viz.generate_all(fig_config['ema_periods'])


if __name__ == "__main__":
    try:
        global_config = load_global_config()
        saved_paths = generate_all_plots(global_config.model_dump())
        print(f"Generated {len(saved_paths)} charts successfully.")
    except Exception as e:
        logger.error(f"Failed to generate plots: {e}", exc_info=True)
        sys.exit(1)
