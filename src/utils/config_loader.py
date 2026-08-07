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

class EdaFinalReportConfig(BaseModel):
    output_report_path: str

    def get_output_report_path(self) -> Path:
        return PROJECT_ROOT / self.output_report_path

class EdaFeatureStoreConfig(BaseModel):
    output_dir: str
    version: int
    format: str
    validation_level: str

    def get_output_dir_path(self) -> Path:
        return PROJECT_ROOT / self.output_dir

class EdaWalkForwardFold(BaseModel):
    train_end_year: int
    test_year: int
    partial: Optional[bool] = False

class EdaWalkForwardConfig(BaseModel):
    anchor_start_year: int
    fold_schedule: str
    folds: List[EdaWalkForwardFold]
    embargo_days: int
    feature_store_version: int
    label_version: str
    persist_fold_artifacts: bool

class EdaLogisticRegressionConfig(BaseModel):
    seed: int
    class_weight: str
    calibration_method: str
    calibration_cv: int

class EdaDecisionTreeConfig(BaseModel):
    seed: int
    class_weight: str
    calibration_method: str
    calibration_cv: int

class EdaRandomForestConfig(BaseModel):
    seed: int
    n_estimators: int
    class_weight: str
    calibration_method: str
    calibration_cv: int

class EdaXGBoostConfig(BaseModel):
    seed: int
    n_estimators: int
    learning_rate: float
    scale_pos_weight_mode: str
    calibration_method: str
    calibration_cv: int

class EdaLightGBMConfig(BaseModel):
    seed: int
    n_estimators: int
    learning_rate: float
    class_weight: str
    calibration_method: str
    calibration_cv: int

class EdaBaselineModelsConfig(BaseModel):
    logistic_regression: EdaLogisticRegressionConfig
    decision_tree: EdaDecisionTreeConfig
    random_forest: EdaRandomForestConfig
    xgboost: EdaXGBoostConfig
    lightgbm: EdaLightGBMConfig

class EdaViabilityGateConfig(BaseModel):
    metric: str
    min_margin_over_naive_baseline: float
    min_passing_folds: int

class EdaBaselineBenchmarkingConfig(BaseModel):
    models: EdaBaselineModelsConfig
    viability_gate: EdaViabilityGateConfig
    stability_threshold: float
    feature_store_version: int
    label_version: str
    walk_forward_run_id: str

class EdaHpoParamLogUniform(BaseModel):
    type: str
    low: float
    high: float

class EdaHpoParamCategorical(BaseModel):
    type: str
    choices: List[Any]

class EdaHpoParamUniform(BaseModel):
    type: str
    low: float
    high: float

class EdaHpoParamInt(BaseModel):
    type: str
    low: int
    high: int

class EdaHpoLogisticRegressionSpace(BaseModel):
    active: bool
    C: EdaHpoParamLogUniform
    penalty: EdaHpoParamCategorical
    solver: EdaHpoParamCategorical
    l1_ratio: EdaHpoParamUniform
    max_iter: int
    class_weight: str
    random_state: int
    calibration_method: str
    n_trials: Optional[int] = None

class EdaHpoXGBoostSpace(BaseModel):
    active: bool
    learning_rate: EdaHpoParamLogUniform
    max_depth: EdaHpoParamInt
    n_estimators: EdaHpoParamInt
    subsample: EdaHpoParamUniform
    colsample_bytree: EdaHpoParamUniform
    min_child_weight: EdaHpoParamUniform
    reg_alpha: EdaHpoParamLogUniform
    reg_lambda: EdaHpoParamLogUniform
    random_state: int
    calibration_method: str
    n_trials: Optional[int] = None

class EdaHpoLightGBMSpace(BaseModel):
    active: bool
    learning_rate: EdaHpoParamLogUniform
    max_depth: EdaHpoParamInt
    num_leaves: EdaHpoParamInt
    n_estimators: EdaHpoParamInt
    min_child_samples: EdaHpoParamInt
    subsample: EdaHpoParamUniform
    colsample_bytree: EdaHpoParamUniform
    reg_alpha: EdaHpoParamLogUniform
    reg_lambda: EdaHpoParamLogUniform
    class_weight: str
    random_state: int
    calibration_method: str
    n_trials: Optional[int] = None

class EdaHpoSearchSpaces(BaseModel):
    logistic_regression: EdaHpoLogisticRegressionSpace
    xgboost: EdaHpoXGBoostSpace
    lightgbm: EdaHpoLightGBMSpace

class EdaHpoStudyConfig(BaseModel):
    sampler: str
    sampler_seed: int
    n_trials: int
    timeout_seconds: Optional[int] = None
    pruner: str

class EdaHpoObjectiveConfig(BaseModel):
    primary_metric: str
    aggregate_folds: List[int]
    secondary_metric: str

class EdaHyperparameterOptimizationConfig(BaseModel):
    eligible_models: List[str]
    excluded_models: Dict[str, str]
    study: EdaHpoStudyConfig
    objective: EdaHpoObjectiveConfig
    search_spaces: EdaHpoSearchSpaces
    feature_store_version: int
    label_version: str
    walk_forward_run_id: str

class EdaExplainabilityShapConfig(BaseModel):
    background_sample_size: int
    interaction_row_ceiling: int
    seed: int

class EdaExplainabilityLocalConfig(BaseModel):
    n_correct_samples_per_class: int
    n_misclassified_samples: int
    seed: int

class EdaExplainabilityStabilityConfig(BaseModel):
    top_k: int

class EdaExplainabilityVersioningConfig(BaseModel):
    feature_store_version: int
    label_version: str
    walk_forward_run_id: str

class EdaExplainabilityConfig(BaseModel):
    enabled_methods: Dict[str, List[str]]
    shap: EdaExplainabilityShapConfig
    local_explanations: EdaExplainabilityLocalConfig
    stability: EdaExplainabilityStabilityConfig
    output: Dict[str, str]
    versioning: EdaExplainabilityVersioningConfig

class EdaBacktestThresholds(BaseModel):
    buy_threshold: float
    sell_threshold: float

class EdaBacktestSignalGen(BaseModel):
    thresholding_enabled: bool
    confidence_thresholds: Dict[str, EdaBacktestThresholds]

class EdaBacktestPositionConfig(BaseModel):
    max_open_positions: int
    allow_scaling_into_position: bool

class EdaBacktestCostStructure(BaseModel):
    brokerage: float
    slippage: float
    exchange_fees: float
    taxes: float
    spread: float
    commission: float

class EdaBacktestRiskConfig(BaseModel):
    stop_loss: Dict[str, Any]
    take_profit: Dict[str, Any]
    trailing_stop: Dict[str, Any]
    max_holding_days: int
    risk_per_trade: float

class EdaBacktestingVersioningConfig(BaseModel):
    feature_store_version: int
    label_version: str
    walk_forward_run_id: str

class EdaBacktestingConfig(BaseModel):
    initial_capital: float
    execution_lag_days: int
    signal_generation: EdaBacktestSignalGen
    position: EdaBacktestPositionConfig
    transaction_costs: Dict[str, EdaBacktestCostStructure]
    risk_management: EdaBacktestRiskConfig
    benchmarks: List[str]
    versioning: EdaBacktestingVersioningConfig

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
    final_report: EdaFinalReportConfig
    feature_store: EdaFeatureStoreConfig
    walk_forward: EdaWalkForwardConfig
    baseline_benchmarking: EdaBaselineBenchmarkingConfig
    hyperparameter_optimization: EdaHyperparameterOptimizationConfig
    explainability: EdaExplainabilityConfig
    backtesting: EdaBacktestingConfig

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
