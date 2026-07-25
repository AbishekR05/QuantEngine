import os
import sys
import time
import yaml
import joblib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.calibration import calibration_curve
from sklearn.utils.class_weight import compute_sample_weight

import xgboost as xgb
import lightgbm as lgb

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("baseline_benchmarking")

# Mapping rules
LABEL_MAPPING = {"BUY": 0, "HOLD": 1, "SELL": 2}
LABEL_CLASSES = ["BUY", "HOLD", "SELL"]

class BaselineBenchmarker:
    """
    Manages benchmarking, probability calibration, and viability gating
    for 5 baseline models across walk-forward splits.
    """
    def __init__(self, config: Dict[str, Any], runs_dir: str = "data/walk_forward_runs",
                 output_dir: str = "data/benchmark_runs"):
        self.config = config
        self.runs_dir = Path(runs_dir)
        self.output_dir = Path(output_dir)
        
        # Load run configuration settings
        self.wf_config = config['eda']['walk_forward']
        self.bb_config = config['eda']['baseline_benchmarking']
        
        self.fs_version = self.bb_config['feature_store_version']
        self.label_version = self.bb_config['label_version']
        self.run_id = self.bb_config['walk_forward_run_id']
        
        # Slices directory
        self.slices_dir = self.runs_dir / self.run_id
        
        # Benchmarking output directory
        self.run_output_dir = self.output_dir / self.run_id
        self.run_output_dir.mkdir(parents=True, exist_ok=True)

    def _multiclass_brier_score(self, y_true: np.ndarray, y_probs: np.ndarray) -> float:
        """Computes standard multiclass Brier Score."""
        y_true_onehot = np.zeros_like(y_probs)
        for i, val in enumerate(y_true):
            y_true_onehot[i, val] = 1.0
        return float(np.mean(np.sum((y_probs - y_true_onehot) ** 2, axis=1)))

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_probs: np.ndarray) -> Dict[str, Any]:
        """Calculates macro classification metrics, per-class metrics, and Brier Score."""
        acc = accuracy_score(y_true, y_pred)
        macro_f1 = f1_score(y_true, y_pred, average="macro")
        
        precisions = precision_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
        recalls = recall_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
        f1s = f1_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
        
        brier = self._multiclass_brier_score(y_true, y_probs)
        conf_mat = confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist()
        
        class_metrics = {}
        for idx, class_name in enumerate(LABEL_CLASSES):
            class_metrics[class_name] = {
                "precision": float(precisions[idx]),
                "recall": float(recalls[idx]),
                "f1": float(f1s[idx])
            }
            
        # Compile reliability curves
        reliability = {}
        for idx, class_name in enumerate(LABEL_CLASSES):
            try:
                prob_true, prob_pred = calibration_curve(y_true == idx, y_probs[:, idx], n_bins=10)
                reliability[class_name] = {
                    "prob_true": prob_true.tolist(),
                    "prob_pred": prob_pred.tolist()
                }
            except Exception as e:
                logger.warning(f"Failed to calculate calibration curve for class {class_name}: {e}")
                reliability[class_name] = {"prob_true": [], "prob_pred": []}
                
        return {
            "accuracy": float(acc),
            "macro_f1": float(macro_f1),
            "brier_score": brier,
            "class_metrics": class_metrics,
            "confusion_matrix": conf_mat,
            "reliability_diagram": reliability
        }

    def _get_model_instance(self, model_name: str, model_cfg: Dict[str, Any], y_train: np.ndarray) -> Tuple[Any, Dict[str, Any]]:
        """Instantiates the scikit-learn/XGBoost/LightGBM model object with configurations."""
        seed = model_cfg.get("seed", 42)
        fit_params = {}
        
        if model_name == "logistic_regression":
            model = LogisticRegression(
                solver="lbfgs",
                class_weight=model_cfg.get("class_weight", "balanced"),
                random_state=seed,
                max_iter=1000
            )
        elif model_name == "decision_tree":
            model = DecisionTreeClassifier(
                class_weight=model_cfg.get("class_weight", "balanced"),
                random_state=seed
            )
        elif model_name == "random_forest":
            model = RandomForestClassifier(
                n_estimators=model_cfg.get("n_estimators", 100),
                class_weight=model_cfg.get("class_weight", "balanced"),
                random_state=seed
            )
        elif model_name == "xgboost":
            # Translate balanced class weighting to sample weights
            model = xgb.XGBClassifier(
                n_estimators=model_cfg.get("n_estimators", 100),
                learning_rate=model_cfg.get("learning_rate", 0.1),
                random_state=seed,
                eval_metric="mlogloss"
            )
            if model_cfg.get("scale_pos_weight_mode") == "balanced":
                sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)
                fit_params["sample_weight"] = sample_weight
        elif model_name == "lightgbm":
            # LGBM Classifier natively supports class_weight='balanced'
            model = lgb.LGBMClassifier(
                n_estimators=model_cfg.get("n_estimators", 100),
                learning_rate=model_cfg.get("learning_rate", 0.1),
                class_weight=model_cfg.get("class_weight", "balanced"),
                random_state=seed,
                verbosity=-1
            )
        else:
            raise ValueError(f"Unknown model name: {model_name}")
            
        return model, fit_params

    def benchmark_model(self, model_name: str) -> Dict[str, Any]:
        """Runs the benchmark pipeline for a single model across all folds."""
        model_cfg = self.bb_config['models'][model_name]
        logger.info(f"----------------------------------------")
        logger.info(f"Benchmarking Model: {model_name}")
        logger.info(f"----------------------------------------")
        
        folds = self.wf_config['folds']
        fold_results = {}
        
        # Ensure directories exist
        model_dir = self.run_output_dir / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        
        for idx, f_cfg in enumerate(folds):
            fold_id = idx + 1
            logger.info(f"Starting Fold {fold_id} execution...")
            
            # 1. Load Parquet files
            train_path = self.slices_dir / f"fold_{fold_id}_train.parquet"
            test_path = self.slices_dir / f"fold_{fold_id}_test.parquet"
            meta_path = self.slices_dir / f"fold_{fold_id}_metadata.yaml"
            
            if not train_path.exists() or not test_path.exists():
                raise FileNotFoundError(f"Fold {fold_id} datasets not found. Please run walk_forward split first.")
                
            train_df = pd.read_parquet(train_path)
            test_df = pd.read_parquet(test_path)
            
            # Filter out target label NaNs (e.g. last row has NaN target)
            label_col = "Label_Binary" if self.label_version == "binary" else "Label_ThreeClass"
            train_df = train_df.dropna(subset=[label_col]).reset_index(drop=True)
            test_df = test_df.dropna(subset=[label_col]).reset_index(drop=True)

            # Load metadata to verify partial flags
            with open(meta_path, "r", encoding="utf-8") as f:
                fold_meta = yaml.safe_load(f)
                
            # 2. Extract targets and features
            label_col = "Label_Binary" if self.label_version == "binary" else "Label_ThreeClass"
            X_train = train_df.drop(columns=["Date", label_col])
            y_train = train_df[label_col].map(LABEL_MAPPING).values
            
            X_test = test_df.drop(columns=["Date", label_col])
            y_test = test_df[label_col].map(LABEL_MAPPING).values
            
            # Assert target leak check
            for col in X_train.columns:
                if "Label" in col:
                    raise ValueError(f"Target column '{col}' leaked into feature input space!")
            
            # 3. Instantiate model
            model, fit_params = self._get_model_instance(model_name, model_cfg, y_train)
            
            # Fit raw model
            model.fit(X_train, y_train, **fit_params)
            
            # Predict raw outputs
            raw_probs = model.predict_proba(X_test)
            raw_preds = model.predict(X_test)
            
            # 4. Calibrate model
            cal_method = model_cfg.get("calibration_method", "platt").lower()
            method_name = "sigmoid" if cal_method == "platt" else "isotonic"
            cv_val = model_cfg.get("calibration_cv", 5)
            
            # Perform calibration fitting on training window only
            if cv_val == "prefit":
                calibrator = CalibratedClassifierCV(estimator=model, method=method_name, cv="prefit")
                calibrator.fit(X_train, y_train)
            else:
                # Instantiate fresh model for internal cross-validation fitting
                base_model, _ = self._get_model_instance(model_name, model_cfg, y_train)
                calibrator = CalibratedClassifierCV(estimator=base_model, method=method_name, cv=cv_val)
                calibrator.fit(X_train, y_train, **fit_params)
                
            # Predict calibrated outputs
            cal_probs = calibrator.predict_proba(X_test)
            cal_preds = calibrator.predict(X_test)
            
            # 5. Compute metrics
            raw_metrics = self._compute_metrics(y_test, raw_preds, raw_probs)
            cal_metrics = self._compute_metrics(y_test, cal_preds, cal_probs)
            
            # Naive baseline: always predict HOLD (1)
            y_naive = np.full_like(y_test, fill_value=1)
            naive_macro_f1 = f1_score(y_test, y_naive, average="macro", zero_division=0)
            
            # Feature importance (strictly informational)
            importance = {}
            if hasattr(model, "feature_importances_"):
                importance = dict(zip(X_train.columns, model.feature_importances_.tolist()))
            elif hasattr(model, "coef_"):
                importance = dict(zip(X_train.columns, model.coef_[0].tolist()))
                
            # Save fold metrics
            fold_results[fold_id] = {
                "naive_baseline_macro_f1": float(naive_macro_f1),
                "raw_metrics": raw_metrics,
                "calibrated_metrics": cal_metrics,
                "is_partial_test_year": fold_meta["is_partial_test_year"]
            }
            
            # 6. Save fold predictions
            pred_df = pd.DataFrame({
                "Date": test_df["Date"],
                "True_Label": test_df[label_col],
                "Raw_Pred": [LABEL_CLASSES[p] for p in raw_preds],
                "Cal_Pred": [LABEL_CLASSES[p] for p in cal_preds],
                "Raw_Prob_BUY": raw_probs[:, 0],
                "Raw_Prob_HOLD": raw_probs[:, 1],
                "Raw_Prob_SELL": raw_probs[:, 2],
                "Cal_Prob_BUY": cal_probs[:, 0],
                "Cal_Prob_HOLD": cal_probs[:, 1],
                "Cal_Prob_SELL": cal_probs[:, 2]
            })
            pred_df.to_parquet(model_dir / f"fold_{fold_id}_predictions.parquet", index=False)
            
            # Save serialized models
            joblib.dump(model, model_dir / f"fold_{fold_id}_model_raw.joblib")
            joblib.dump(calibrator, model_dir / f"fold_{fold_id}_model_calibrated.joblib")
            
            # Save metadata
            meta_out = {
                "naive_baseline_macro_f1": float(naive_macro_f1),
                "is_partial_test_year": fold_meta["is_partial_test_year"],
                "feature_importance_exploratory_only": importance
            }
            with open(model_dir / f"fold_{fold_id}_metadata.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(meta_out, f, default_flow_style=False)
                
            # Save metrics
            metrics_out = {
                "raw": raw_metrics,
                "calibrated": cal_metrics
            }
            with open(model_dir / f"fold_{fold_id}_metrics.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(metrics_out, f, default_flow_style=False)
                
            logger.info(f"Fold {fold_id} completed. Raw Macro F1: {raw_metrics['macro_f1']:.4f}, Calibrated Macro F1: {cal_metrics['macro_f1']:.4f}")
            
        # Compute cross-fold aggregates
        self._save_aggregated_model_reports(model_name, fold_results, model_dir)
        return fold_results

    def _save_aggregated_model_reports(self, model_name: str, fold_results: Dict[int, Any], model_dir: Path) -> None:
        """Saves aggregate metrics across folds, isolating Fold 8 partial-year metrics."""
        full_year_folds = [fid for fid, f in fold_results.items() if not f["is_partial_test_year"]]
        partial_folds = [fid for fid, f in fold_results.items() if f["is_partial_test_year"]]
        
        # Classification macro f1 lists
        raw_f1s = [fold_results[fid]["raw_metrics"]["macro_f1"] for fid in full_year_folds]
        cal_f1s = [fold_results[fid]["calibrated_metrics"]["macro_f1"] for fid in full_year_folds]
        
        # Brier scores lists
        raw_briers = [fold_results[fid]["raw_metrics"]["brier_score"] for fid in full_year_folds]
        cal_briers = [fold_results[fid]["calibrated_metrics"]["brier_score"] for fid in full_year_folds]
        
        summary = {
            "model_name": model_name,
            "full_year_aggregates": {
                "raw_macro_f1_mean": float(np.mean(raw_f1s)) if raw_f1s else 0.0,
                "raw_macro_f1_std": float(np.std(raw_f1s)) if raw_f1s else 0.0,
                "calibrated_macro_f1_mean": float(np.mean(cal_f1s)) if cal_f1s else 0.0,
                "calibrated_macro_f1_std": float(np.std(cal_f1s)) if cal_f1s else 0.0,
                "raw_brier_mean": float(np.mean(raw_briers)) if raw_briers else 0.0,
                "raw_brier_std": float(np.std(raw_briers)) if raw_briers else 0.0,
                "calibrated_brier_mean": float(np.mean(cal_briers)) if cal_briers else 0.0,
                "calibrated_brier_std": float(np.std(cal_briers)) if cal_briers else 0.0,
            },
            "partial_year_folds": {}
        }
        
        for fid in partial_folds:
            summary["partial_year_folds"][fid] = {
                "raw_macro_f1": fold_results[fid]["raw_metrics"]["macro_f1"],
                "calibrated_macro_f1": fold_results[fid]["calibrated_metrics"]["macro_f1"],
                "raw_brier_score": fold_results[fid]["raw_metrics"]["brier_score"],
                "calibrated_brier_score": fold_results[fid]["calibrated_metrics"]["brier_score"]
            }
            
        with open(model_dir / "cross_fold_summary.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(summary, f, default_flow_style=False)
            
        logger.info(f"Aggregated metrics generated for {model_name}. Mean Calibrated F1: {summary['full_year_aggregates']['calibrated_macro_f1_mean']:.4f}")

    def evaluate_viability_and_compare(self, all_model_results: Dict[str, Dict[int, Any]]) -> None:
        """
        Executes cross-model comparison ranking and provisional viability gating.
        Loads verification thresholds from baseline configuration parameters dynamically.
        """
        gate_cfg = self.bb_config['viability_gate']
        target_metric = gate_cfg['metric'] # e.g. macro_f1
        min_margin = gate_cfg['min_margin_over_naive_baseline']
        min_passing = gate_cfg['min_passing_folds']
        stability_limit = self.bb_config.get("stability_threshold", 0.10)
        
        logger.info("----------------------------------------")
        logger.info("Evaluating Performance Viability Gate")
        logger.info("----------------------------------------")
        
        comparison = {
            "run_id": self.run_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "models_comparison": {}
        }
        
        for m_name, fold_res in all_model_results.items():
            passing_folds_count = 0
            fold_deviations = []
            
            # Fetch means to calculate deviations
            full_year_cal_f1s = [fold_res[fid]["calibrated_metrics"]["macro_f1"] for fid in fold_res if not fold_res[fid]["is_partial_test_year"]]
            mean_cal_f1 = np.mean(full_year_cal_f1s) if full_year_cal_f1s else 0.0
            
            fold_details = {}
            for fid, res in fold_res.items():
                naive_f1 = res["naive_baseline_macro_f1"]
                cal_f1 = res["calibrated_metrics"]["macro_f1"]
                raw_f1 = res["raw_metrics"]["macro_f1"]
                
                margin = cal_f1 - naive_f1
                is_fold_pass = margin >= min_margin
                if is_fold_pass:
                    passing_folds_count += 1
                    
                # Calculate stability deviation
                if not res["is_partial_test_year"]:
                    dev = abs(cal_f1 - mean_cal_f1)
                    fold_deviations.append(dev)
                    
                fold_details[fid] = {
                    "is_partial_test_year": res["is_partial_test_year"],
                    "naive_baseline_f1": naive_f1,
                    "raw_f1": raw_f1,
                    "calibrated_f1": cal_f1,
                    "margin_over_naive": margin,
                    "viability_gate_pass": is_fold_pass
                }
                
            # Stability check
            max_dev = max(fold_deviations) if fold_deviations else 0.0
            is_stable = max_dev <= stability_limit
            
            is_viable = passing_folds_count >= min_passing
            
            comparison["models_comparison"][m_name] = {
                "overall_viability_pass": bool(is_viable),
                "passing_folds_count": passing_folds_count,
                "required_passing_folds": min_passing,
                "stability_indicator": {
                    "stable": bool(is_stable),
                    "max_deviation": float(max_dev),
                    "allowed_threshold": stability_limit
                },
                "full_year_f1_mean": float(mean_cal_f1),
                "folds": fold_details
            }
            
            status_str = "PASSED" if is_viable else "FAILED"
            logger.info(f"Model: {m_name} | Folds Passed viability: {passing_folds_count}/{len(fold_res)} | Gate Status: {status_str}")
            
        # Write comparison dashboard file
        comp_path = self.run_output_dir / "benchmark_comparison.yaml"
        with open(comp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(comparison, f, default_flow_style=False)
            
        logger.info(f"Benchmark comparison dashboard written to: {comp_path}")
        logger.info("----------------------------------------")

    def run_full_pipeline(self) -> None:
        """Runs the entire benchmarking pass sequentially for all models."""
        models_to_run = list(self.bb_config['models'].keys())
        all_results = {}
        
        # Save reproducibility config snapshot
        config_snapshot_path = self.run_output_dir / "reproducibility_config.yaml"
        with open(config_snapshot_path, "w", encoding="utf-8") as f:
            # Serialize the baseline configuration block
            yaml.safe_dump({
                "baseline_benchmarking": self.bb_config,
                "library_versions": {
                    "scikit-learn": getattr(sys.modules.get("sklearn"), "__version__", "unknown"),
                    "xgboost": getattr(sys.modules.get("xgboost"), "__version__", "unknown"),
                    "lightgbm": getattr(sys.modules.get("lightgbm"), "__version__", "unknown")
                }
            }, f, default_flow_style=False)
            
        logger.info(f"Saved reproducibility config snapshot to: {config_snapshot_path}")
        
        for m_name in models_to_run:
            all_results[m_name] = self.benchmark_model(m_name)
            
        # Compile gate analysis
        self.evaluate_viability_and_compare(all_results)
        logger.info("Benchmarking pipeline run completed successfully.")

if __name__ == "__main__":
    try:
        global_config = load_global_config()
        # Resolve folders relative to project root
        project_root = Path(__file__).resolve().parent.parent.parent
        runs_dir = project_root / "data/walk_forward_runs"
        output_dir = project_root / "data/benchmark_runs"
        
        benchmarker = BaselineBenchmarker(
            config=global_config.model_dump(),
            runs_dir=str(runs_dir),
            output_dir=str(output_dir)
        )
        benchmarker.run_full_pipeline()
    except Exception as e:
        logger.error(f"Baseline benchmarking pipeline failed: {e}", exc_info=True)
        sys.exit(1)
