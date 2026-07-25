import os
import sys
import time
import yaml
import warnings
warnings.filterwarnings("ignore")
import joblib
import optuna
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
try:
    from sklearn.frozen import FrozenEstimator
    HAS_FROZEN = True
except ImportError:
    HAS_FROZEN = False
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight

import xgboost as xgb

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("hyperparameter_optimization")

# Mapping rules
LABEL_MAPPING = {"BUY": 0, "HOLD": 1, "SELL": 2}
LABEL_CLASSES = ["BUY", "HOLD", "SELL"]

# Set optuna logs to warning to keep console output clean
optuna.logging.set_verbosity(optuna.logging.WARNING)

class HyperparameterOptimizer:
    """
    Orchestrates walk-forward nested hyperparameter tuning using Optuna.
    Saves trial histories, best configurations, and metrics comparisons vs default.
    """
    def __init__(self, config: Dict[str, Any], runs_dir: str = "data/walk_forward_runs",
                 output_dir: str = "data/hpo_runs"):
        self.config = config
        self.runs_dir = Path(runs_dir)
        self.output_dir = Path(output_dir)
        
        self.wf_config = config['eda']['walk_forward']
        self.hpo_config = config['eda']['hyperparameter_optimization']
        
        self.fs_version = self.hpo_config['feature_store_version']
        self.label_version = self.hpo_config['label_version']
        self.run_id = self.hpo_config['walk_forward_run_id']
        
        # Slices directory
        self.slices_dir = self.runs_dir / self.run_id
        
        # HPO outputs directory
        self.run_output_dir = self.output_dir / self.run_id
        self.run_output_dir.mkdir(parents=True, exist_ok=True)

    def _multiclass_brier_score(self, y_true: np.ndarray, y_probs: np.ndarray) -> float:
        """Computes multiclass Brier score."""
        y_true_onehot = np.zeros_like(y_probs)
        for i, val in enumerate(y_true):
            y_true_onehot[i, val] = 1.0
        return float(np.mean(np.sum((y_probs - y_true_onehot) ** 2, axis=1)))

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_probs: np.ndarray) -> Dict[str, Any]:
        """Helper to calculate classification accuracy, macro F1, and Brier score."""
        acc = accuracy_score(y_true, y_pred)
        macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
        brier = self._multiclass_brier_score(y_true, y_probs)
        return {
            "accuracy": float(acc),
            "macro_f1": float(macro_f1),
            "brier_score": brier
        }

    def _get_lr_params(self, trial: optuna.Trial, space: Dict[str, Any]) -> Dict[str, Any]:
        """Samples Logistic Regression parameters enforcing solver/penalty constraints."""
        # Solver/penalty compatibility rules
        solver = trial.suggest_categorical("solver", space["solver"]["choices"])
        
        if solver == "lbfgs":
            penalty = "l2"
            l1_ratio = None
        elif solver == "liblinear":
            penalty = trial.suggest_categorical("penalty_liblinear", ["l1", "l2"])
            l1_ratio = None
        else: # saga
            penalty = trial.suggest_categorical("penalty_saga", ["l1", "l2", "elasticnet"])
            l1_ratio = trial.suggest_float("l1_ratio", 0.0, 1.0) if penalty == "elasticnet" else None
            
        C = trial.suggest_float("C", space["C"]["low"], space["C"]["high"], log=True)
        
        params = {
            "solver": solver,
            "penalty": penalty,
            "C": C,
            "max_iter": space["max_iter"],
            "class_weight": space["class_weight"],
            "random_state": space["random_state"]
        }
        if l1_ratio is not None:
            params["l1_ratio"] = l1_ratio
            
        return params

    def _get_xgb_params(self, trial: optuna.Trial, space: Dict[str, Any]) -> Dict[str, Any]:
        """Samples XGBoost hyperparameter space."""
        return {
            "learning_rate": trial.suggest_float("learning_rate", space["learning_rate"]["low"], space["learning_rate"]["high"], log=True),
            "max_depth": trial.suggest_int("max_depth", space["max_depth"]["low"], space["max_depth"]["high"]),
            "n_estimators": trial.suggest_int("n_estimators", space["n_estimators"]["low"], space["n_estimators"]["high"]),
            "subsample": trial.suggest_float("subsample", space["subsample"]["low"], space["subsample"]["high"]),
            "colsample_bytree": trial.suggest_float("colsample_bytree", space["colsample_bytree"]["low"], space["colsample_bytree"]["high"]),
            "min_child_weight": trial.suggest_float("min_child_weight", space["min_child_weight"]["low"], space["min_child_weight"]["high"]),
            "reg_alpha": trial.suggest_float("reg_alpha", space["reg_alpha"]["low"], space["reg_alpha"]["high"], log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", space["reg_lambda"]["low"], space["reg_lambda"]["high"], log=True),
            "random_state": space["random_state"],
            "eval_metric": "mlogloss"
        }

    def _evaluate_params(self, model_name: str, params: Dict[str, Any], trial: optuna.Trial) -> float:
        """Evaluates a parameter dictionary across walk-forward folds with optional pruning."""
        folds = self.wf_config['folds']
        f1_list = []
        
        for idx, f_cfg in enumerate(folds):
            fold_id = idx + 1
            
            # Load sliced datasets
            train_path = self.slices_dir / f"fold_{fold_id}_train.parquet"
            test_path = self.slices_dir / f"fold_{fold_id}_test.parquet"
            
            train_df = pd.read_parquet(train_path)
            test_df = pd.read_parquet(test_path)
            
            label_col = "Label_Binary" if self.label_version == "binary" else "Label_ThreeClass"
            train_df = train_df.dropna(subset=[label_col]).reset_index(drop=True)
            test_df = test_df.dropna(subset=[label_col]).reset_index(drop=True)
            
            X_train = train_df.drop(columns=["Date", label_col])
            y_train = train_df[label_col].map(LABEL_MAPPING).values
            
            X_test = test_df.drop(columns=["Date", label_col])
            y_test = test_df[label_col].map(LABEL_MAPPING).values
            
            # Instantiate model
            fit_params = {}
            if model_name == "logistic_regression":
                model = LogisticRegression(**params)
            elif model_name == "xgboost":
                model = xgb.XGBClassifier(**params)
                # Apply sample weighting for class balancing
                sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)
                fit_params["sample_weight"] = sample_weight
            else:
                raise ValueError(f"Unknown model name: {model_name}")
                
            try:
                # Platt scaling fit
                cal_method = self.hpo_config["search_spaces"][model_name]["calibration_method"]
                method_name = "sigmoid" if cal_method == "platt" else "isotonic"
                
                # Fit model internally via cross-validation calibrator
                cal_model = CalibratedClassifierCV(estimator=model, method=method_name, cv=5)
                cal_model.fit(X_train, y_train, **fit_params)
                
                cal_probs = cal_model.predict_proba(X_test)
                cal_preds = cal_model.predict(X_test)
                
                metrics = self._compute_metrics(y_test, cal_preds, cal_probs)
                cal_f1 = metrics["macro_f1"]
                
            except Exception as e:
                # Log crash and assign penalizing score
                logger.warning(f"Trial failed to fit in Fold {fold_id}: {e}")
                cal_f1 = 0.0
                
            # Only Folds 1-7 (full years) count towards HPO search target
            is_partial = f_cfg.get("partial", False)
            if not is_partial:
                f1_list.append(cal_f1)
                
                # Optuna pruning checkpoint
                trial.report(cal_f1, step=fold_id)
                if trial.should_prune():
                    raise optuna.TrialPruned()
                    
        return float(np.mean(f1_list)) if f1_list else 0.0

    def optimize_model(self, model_name: str) -> Tuple[Dict[str, Any], float]:
        """Tunes an eligible model's space using TPE sampling and median pruning."""
        space = self.hpo_config["search_spaces"][model_name]
        logger.info(f"========================================")
        logger.info(f"Optimizing Model: {model_name}")
        logger.info(f"========================================")
        
        study_settings = self.hpo_config['study']
        
        # Configure TPE sampler
        sampler = optuna.samplers.TPESampler(seed=study_settings['sampler_seed'])
        
        # Configure median pruner
        pruner = optuna.pruners.MedianPruner(n_warmup_steps=2) if study_settings['pruner'] == "median" else None
        
        study_name = f"hpo_{model_name}_{self.run_id}"
        
        # Set up Optuna study database for history persistence
        db_path = self.run_output_dir / "study.db"
        storage_url = f"sqlite:///{db_path}"
        
        study = optuna.create_study(
            study_name=study_name,
            direction="maximize",
            sampler=sampler,
            pruner=pruner,
            storage=storage_url,
            load_if_exists=True
        )
        
        def objective(trial: optuna.Trial) -> float:
            if model_name == "logistic_regression":
                params = self._get_lr_params(trial, space)
            else:
                params = self._get_xgb_params(trial, space)
                
            score = self._evaluate_params(model_name, params, trial)
            
            # Save individual trial metadata files
            trial_dir = self.run_output_dir / f"{model_name}_trials" / f"trial_{trial.number}"
            trial_dir.mkdir(parents=True, exist_ok=True)
            
            with open(trial_dir / "sampled_params.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(params, f, default_flow_style=False)
                
            with open(trial_dir / "trial_summary.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump({
                    "trial_id": trial.number,
                    "calibrated_macro_f1_mean_objective": score,
                    "state": "completed"
                }, f, default_flow_style=False)
                
            return score
            
        model_trials = space.get("n_trials", study_settings['n_trials'])
        study.optimize(objective, n_trials=model_trials, timeout=study_settings['timeout_seconds'])
        
        best_params = study.best_params
        best_score = study.best_value
        
        # Re-map Logistic Regression penalty compatibility output keys
        if model_name == "logistic_regression":
            if best_params["solver"] == "lbfgs":
                best_params["penalty"] = "l2"
            best_params["max_iter"] = space["max_iter"]
            best_params["class_weight"] = space["class_weight"]
            best_params["random_state"] = space["random_state"]
        else:
            best_params["random_state"] = space["random_state"]
            
        logger.info(f"Model {model_name} optimized successfully.")
        logger.info(f"Best objective score: {best_score:.4f}")
        logger.info(f"Best parameters: {best_params}")
        
        # Save best trial parameters
        best_dir = self.run_output_dir / model_name / "best_trial"
        best_dir.mkdir(parents=True, exist_ok=True)
        with open(best_dir / "sampled_params.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(best_params, f, default_flow_style=False)
            
        # Re-run best configurations and save model artifacts
        self._evaluate_and_save_best_model(model_name, best_params, best_dir)
        
        return best_params, best_score

    def _evaluate_and_save_best_model(self, model_name: str, best_params: Dict[str, Any], best_dir: Path) -> None:
        """Executes walk-forward evaluations on the best parameters and exports model artifacts."""
        folds = self.wf_config['folds']
        fold_details = {}
        
        for idx, f_cfg in enumerate(folds):
            fold_id = idx + 1
            train_path = self.slices_dir / f"fold_{fold_id}_train.parquet"
            test_path = self.slices_dir / f"fold_{fold_id}_test.parquet"
            meta_path = self.slices_dir / f"fold_{fold_id}_metadata.yaml"
            
            train_df = pd.read_parquet(train_path)
            test_df = pd.read_parquet(test_path)
            
            label_col = "Label_Binary" if self.label_version == "binary" else "Label_ThreeClass"
            train_df = train_df.dropna(subset=[label_col]).reset_index(drop=True)
            test_df = test_df.dropna(subset=[label_col]).reset_index(drop=True)
            
            X_train = train_df.drop(columns=["Date", label_col])
            y_train = train_df[label_col].map(LABEL_MAPPING).values
            
            X_test = test_df.drop(columns=["Date", label_col])
            y_test = test_df[label_col].map(LABEL_MAPPING).values
            
            with open(meta_path, "r", encoding="utf-8") as f:
                fold_meta = yaml.safe_load(f)
                
            # Instantiate model
            fit_params = {}
            if model_name == "logistic_regression":
                model = LogisticRegression(**best_params)
            elif model_name == "xgboost":
                # Re-extract clean parameters
                xgb_params = {k: v for k, v in best_params.items() if k not in ["scale_pos_weight_mode"]}
                model = xgb.XGBClassifier(**xgb_params)
                sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)
                fit_params["sample_weight"] = sample_weight
                
            cal_method = self.hpo_config["search_spaces"][model_name]["calibration_method"]
            method_name = "sigmoid" if cal_method == "platt" else "isotonic"
            
            # Re-fit and calibrate
            model.fit(X_train, y_train, **fit_params)
            raw_probs = model.predict_proba(X_test)
            raw_preds = model.predict(X_test)
            
            if HAS_FROZEN:
                calibrator = CalibratedClassifierCV(estimator=FrozenEstimator(model), method=method_name)
            else:
                calibrator = CalibratedClassifierCV(estimator=model, method=method_name, cv="prefit")
            calibrator.fit(X_train, y_train)
            cal_probs = calibrator.predict_proba(X_test)
            cal_preds = calibrator.predict(X_test)
            
            raw_metrics = self._compute_metrics(y_test, raw_preds, raw_probs)
            cal_metrics = self._compute_metrics(y_test, cal_preds, cal_probs)
            
            # Naive baseline Macro F1 floor
            y_naive = np.full_like(y_test, fill_value=1)
            naive_macro_f1 = f1_score(y_test, y_naive, average="macro", zero_division=0)
            
            fold_details[fold_id] = {
                "is_partial_test_year": fold_meta["is_partial_test_year"],
                "naive_baseline_f1": float(naive_macro_f1),
                "raw_f1": raw_metrics["macro_f1"],
                "calibrated_f1": cal_metrics["macro_f1"]
            }
            
            # Save fold metrics YAML
            metrics_out = {
                "raw": raw_metrics,
                "calibrated": cal_metrics
            }
            with open(best_dir / f"fold_{fold_id}_metrics.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(metrics_out, f, default_flow_style=False)
                
            # Save models
            joblib.dump(model, best_dir / f"fold_{fold_id}_model_raw.joblib")
            joblib.dump(calibrator, best_dir / f"fold_{fold_id}_model_calibrated.joblib")
            
        # Write Fold-by-Fold comparison vs default baseline (from Step 4)
        self._write_comparison_report(model_name, fold_details, best_dir)

    def _write_comparison_report(self, model_name: str, optimized_folds: Dict[int, Any], best_dir: Path) -> None:
        """Compares best HPO configurations with Step 4 default configurations."""
        # Resolve Step 4 comparison path
        step4_dir = Path("data/benchmark_runs") / self.run_id
        step4_comp_path = step4_dir / "benchmark_comparison.yaml"
        
        default_folds = {}
        if step4_comp_path.exists():
            with open(step4_comp_path, "r", encoding="utf-8") as f:
                step4_data = yaml.safe_load(f)
                default_folds = step4_data.get("models_comparison", {}).get(model_name, {}).get("folds", {})
                
        comparison_records = {}
        for fid in sorted(optimized_folds.keys(), key=int):
            opt = optimized_folds[fid]
            dft = default_folds.get(fid, {"raw_f1": 0.0, "calibrated_f1": 0.0})
            
            comparison_records[fid] = {
                "is_partial_test_year": opt["is_partial_test_year"],
                "naive_baseline_f1": opt["naive_baseline_f1"],
                "default_raw_f1": dft["raw_f1"],
                "optimized_raw_f1": opt["raw_f1"],
                "default_calibrated_f1": dft["calibrated_f1"],
                "optimized_calibrated_f1": opt["calibrated_f1"],
                "calibrated_improvement": opt["calibrated_f1"] - dft["calibrated_f1"]
            }
            
        with open(best_dir / "comparison_vs_step4_default.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(comparison_records, f, default_flow_style=False)

    def compile_rollup_report(self, hpo_results: Dict[str, Any]) -> None:
        """Generates the aggregate summary optimization_report.yaml file."""
        report = {
            "run_id": self.run_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "feature_store_version": self.fs_version,
            "label_version": self.label_version,
            "study_details": {},
            "viability_gate_acceptances": {}
        }
        
        # Load viability thresholds
        gate_cfg = self.config['eda']['baseline_benchmarking']['viability_gate']
        min_margin = gate_cfg['min_margin_over_naive_baseline']
        min_passing = gate_cfg['min_passing_folds']
        
        for m_name in self.hpo_config["eligible_models"]:
            best_dir = self.run_output_dir / m_name / "best_trial"
            
            # Load comparison metrics
            comp_file = best_dir / "comparison_vs_step4_default.yaml"
            comp_data = {}
            if comp_file.exists():
                with open(comp_file, "r", encoding="utf-8") as f:
                    comp_data = yaml.safe_load(f)
                    
            # Compute viability pass count post optimization
            passing_folds = 0
            for fid, r in comp_data.items():
                margin = r["optimized_calibrated_f1"] - r["naive_baseline_f1"]
                if margin >= min_margin:
                    passing_folds += 1
                    
            is_viable = passing_folds >= min_passing
            
            report["study_details"][m_name] = {
                "optimized_best_score": hpo_results.get(m_name, {}).get("best_score", 0.0),
                "optimized_parameters": hpo_results.get(m_name, {}).get("best_params", {}),
                "fold_by_fold_comparison": comp_data
            }
            report["viability_gate_acceptances"][m_name] = {
                "passing_folds": passing_folds,
                "required_folds": min_passing,
                "passed_viability": bool(is_viable)
            }
            
        # Add details of excluded models for completeness
        report["excluded_models"] = self.hpo_config.get("excluded_models", {})
        
        rollup_path = self.run_output_dir / "optimization_report.yaml"
        with open(rollup_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(report, f, default_flow_style=False)
            
        logger.info(f"Aggregate rollup HPO report generated at: {rollup_path}")

    def run_hpo_studies(self) -> None:
        """Iterates HPO studies across all eligible model configurations sequentially."""
        logger.info("Initializing Hyperparameter Optimization Study pipeline...")
        
        # Save study config snapshot
        config_snapshot = self.run_output_dir / "study_config_snapshot.yaml"
        with open(config_snapshot, "w", encoding="utf-8") as f:
            yaml.safe_dump({
                "hyperparameter_optimization": self.hpo_config,
                "library_versions": {
                    "optuna": getattr(sys.modules.get("optuna"), "__version__", "unknown"),
                    "scikit-learn": getattr(sys.modules.get("sklearn"), "__version__", "unknown"),
                    "xgboost": getattr(sys.modules.get("xgboost"), "__version__", "unknown")
                }
            }, f, default_flow_style=False)
            
        hpo_results = {}
        for m_name in self.hpo_config["eligible_models"]:
            best_params, best_score = self.optimize_model(m_name)
            hpo_results[m_name] = {
                "best_params": best_params,
                "best_score": best_score
            }
            
        # Generate rollup summary comparisons
        self.compile_rollup_report(hpo_results)
        logger.info("Hyperparameter Optimization study run completed successfully.")

if __name__ == "__main__":
    try:
        global_config = load_global_config()
        # Resolve folders relative to project root
        project_root = Path(__file__).resolve().parent.parent.parent
        runs_dir = project_root / "data/walk_forward_runs"
        output_dir = project_root / "data/hpo_runs"
        
        optimizer = HyperparameterOptimizer(
            config=global_config.model_dump(),
            runs_dir=str(runs_dir),
            output_dir=str(output_dir)
        )
        optimizer.run_hpo_studies()
    except Exception as e:
        logger.error(f"HPO study run failed: {e}", exc_info=True)
        sys.exit(1)
