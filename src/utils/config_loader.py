import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Project root resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class EdaInputFiles(BaseModel):
    clean: str
    features: str

class EdaStatisticsConfig(BaseModel):
    exclude_columns: List[str]
    skew_threshold: float
    kurtosis_threshold: float

class EdaFiguresConfig(BaseModel):
    output_dir: str
    dpi: int
    figure_size: List[int]
    rolling_volatility_window: int
    ema_periods: List[int]
    rsi_overbought: float
    rsi_oversold: float

    def get_output_dir(self) -> Path:
        return PROJECT_ROOT / self.output_dir

class EdaCorrelationConfig(BaseModel):
    input_file: str
    exclude_columns: List[str]
    high_corr_threshold: float
    leakage_threshold: float
    top_n_pairs: int
    heatmap_output_dir: str
    report_output_path: str

    def get_input_file_path(self) -> Path:
        return PROJECT_ROOT / self.input_file

    def get_heatmap_output_dir(self) -> Path:
        return PROJECT_ROOT / self.heatmap_output_dir

    def get_report_output_path(self) -> Path:
        return PROJECT_ROOT / self.report_output_path

class EdaOutliersConfig(BaseModel):
    known_events_path: str
    exclude_columns: List[str]
    iqr_multiplier: float
    zscore_threshold: float
    top_n_per_column: int
    output_dir: str
    report_output_path: str

    def get_output_dir(self) -> Path:
        return PROJECT_ROOT / self.output_dir

    def get_report_output_path(self) -> Path:
        return PROJECT_ROOT / self.report_output_path

    def get_known_events_path(self) -> Path:
        return PROJECT_ROOT / self.known_events_path

class EdaRegimeConfig(BaseModel):
    input_file: str
    trend_window: int
    trend_threshold: float
    vol_window: int
    vol_high_percentile: float
    vol_low_percentile: float
    known_events_path: str
    output_report_path: str
    output_chart_path: str

    def get_input_file_path(self) -> Path:
        return PROJECT_ROOT / self.input_file

    def get_known_events_path(self) -> Path:
        return PROJECT_ROOT / self.known_events_path

    def get_output_report_path(self) -> Path:
        return PROJECT_ROOT / self.output_report_path

    def get_output_chart_path(self) -> Path:
        return PROJECT_ROOT / self.output_chart_path

class EdaFeatureUsefulnessConfig(BaseModel):
    input_file: str
    exclude_columns: List[str]
    correlation_report_source: str
    mi_bins: int
    output_report_path: str

    def get_input_file_path(self) -> Path:
        return PROJECT_ROOT / self.input_file

    def get_output_report_path(self) -> Path:
        return PROJECT_ROOT / self.output_report_path

class EdaLabelEngineeringConfig(BaseModel):
    input_file: str
    close_column: str
    three_class_threshold: float
    output_dir: str
    binary_output_filename: str
    three_class_output_filename: str
    report_output_path: str

    def get_input_file_path(self) -> Path:
        return PROJECT_ROOT / self.input_file

    def get_output_dir_path(self) -> Path:
        return PROJECT_ROOT / self.output_dir

    def get_binary_output_path(self) -> Path:
        return self.get_output_dir_path() / self.binary_output_filename

    def get_three_class_output_path(self) -> Path:
        return self.get_output_dir_path() / self.three_class_output_filename

    def get_report_output_path(self) -> Path:
        return PROJECT_ROOT / self.report_output_path

class EdaScalingConfig(BaseModel):
    bounded_columns: List[str]
    output_report_path: str

    def get_output_report_path(self) -> Path:
        return PROJECT_ROOT / self.output_report_path

class EdaConfig(BaseModel):
    input_files: EdaInputFiles
    output_dir: str
    date_column: str
    statistics: EdaStatisticsConfig
    figures: EdaFiguresConfig
    correlation: EdaCorrelationConfig
    outliers: EdaOutliersConfig
    regime: EdaRegimeConfig
    feature_usefulness: EdaFeatureUsefulnessConfig
    label_engineering: EdaLabelEngineeringConfig
    scaling: EdaScalingConfig

    def get_clean_input_path(self) -> Path:
        return PROJECT_ROOT / self.input_files.clean

    def get_features_input_path(self) -> Path:
        return PROJECT_ROOT / self.input_files.features

    def get_output_dir(self) -> Path:
        return PROJECT_ROOT / self.output_dir

class GlobalConfig(BaseModel):
    ticker: str
    start_date: str
    end_date: Optional[str] = None
    db_path: str
    raw_data_dir: str
    processed_data_dir: str
    features_data_dir: str
    versions_dir: str
    eda: EdaConfig

    def get_db_path(self) -> Path:
        return PROJECT_ROOT / self.db_path

    def get_raw_data_dir(self) -> Path:
        return PROJECT_ROOT / self.raw_data_dir

    def get_processed_data_dir(self) -> Path:
        return PROJECT_ROOT / self.processed_data_dir

    def get_features_data_dir(self) -> Path:
        return PROJECT_ROOT / self.features_data_dir

    def get_versions_dir(self) -> Path:
        return PROJECT_ROOT / self.versions_dir

class IndicatorMAConfig(BaseModel):
    sma: List[int]
    ema: List[int]

class IndicatorRSIConfig(BaseModel):
    period: int

class IndicatorMACDConfig(BaseModel):
    fast: int
    slow: int
    signal: int

class IndicatorBBConfig(BaseModel):
    period: int
    std_dev: float

class IndicatorATRConfig(BaseModel):
    period: int

class IndicatorsConfig(BaseModel):
    moving_averages: IndicatorMAConfig
    rsi: IndicatorRSIConfig
    macd: IndicatorMACDConfig
    bollinger_bands: IndicatorBBConfig
    atr: IndicatorATRConfig

class OHLCConstraints(BaseModel):
    high_ge_low: bool
    high_ge_open: bool
    high_ge_close: bool
    low_le_open: bool
    low_le_close: bool

class ValidationRulesConfig(BaseModel):
    price_columns: List[str]
    volume_column: str
    max_gap_days: int
    ohlc_constraints: OHLCConstraints


def _load_yaml(file_path: Path) -> Dict[str, Any]:
    """Loads a YAML file from the given path."""
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_global_config() -> GlobalConfig:
    """Loads and validates global configuration settings."""
    config_data = _load_yaml(PROJECT_ROOT / "config" / "config.yaml")
    return GlobalConfig(**config_data)

def load_indicators_config() -> IndicatorsConfig:
    """Loads and validates technical indicator configurations."""
    config_data = _load_yaml(PROJECT_ROOT / "config" / "indicators.yaml")
    return IndicatorsConfig(**config_data)

def load_validation_rules() -> ValidationRulesConfig:
    """Loads and validates data validation constraints."""
    config_data = _load_yaml(PROJECT_ROOT / "config" / "validation_rules.yaml")
    return ValidationRulesConfig(**config_data)
