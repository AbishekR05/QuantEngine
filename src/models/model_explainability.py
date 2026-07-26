import os
import sys
import yaml
import time
import joblib
import shap
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, f1_score
import xgboost as xgb

from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("model_explainability")

# Mapping rules
LABEL_MAPPING = {"BUY": 0, "HOLD": 1, "SELL": 2}
LABEL_CLASSES = ["BUY", "HOLD", "SELL"]

class ModelExplainer:
    def __init__(self, config: Dict[str, Any], runs_dir: str = "data/walk_forward_runs",
                 hpo_dir: str = "data/hpo_runs", output_dir: str = "explainability_runs"):
        self.config = config
        self.runs_dir = Path(runs_dir)
        self.hpo_dir = Path(hpo_dir)
        self.output_dir = Path(output_dir)
        
        self.wf_config = config['eda']['walk_forward']
        self.exp_config = config['eda']['explainability']
        
        self.fs_version = self.exp_config['versioning']['feature_store_version']
        self.label_version = self.exp_config['versioning']['label_version']
        self.run_id = self.exp_config['versioning']['walk_forward_run_id']
        
        # Slices directory
        self.slices_dir = self.runs_dir / self.run_id
        
        # Explainability outputs directory
        self.run_output_dir = self.output_dir / self.run_id
        self.run_output_dir.mkdir(parents=True, exist_ok=True)
        
        # HPO outputs directory (best model source)
        self.best_model_src = self.hpo_dir / self.run_id
        
    def _compute_standardized_coefficients(self, coef_raw: np.ndarray, std_train: np.ndarray) -> np.ndarray:
        """
        Multiplies raw coefficients by the training-set standard deviation of each feature
        to align magnitudes across varying pre-scaling mechanisms.
        """
        # coef_raw has shape (n_classes, n_features)
        return coef_raw * std_train

    def explain_logistic_regression(self) -> Dict[str, Any]:
        """Performs interpretability analysis on Logistic Regression weights across all folds."""
        logger.info("Explaining Logistic Regression...")
        folds = self.wf_config['folds']
        lr_output_dir = self.run_output_dir / "logistic_regression"
        lr_output_dir.mkdir(parents=True, exist_ok=True)
        
        best_lr_dir = self.best_model_src / "logistic_regression" / "best_trial"
        if not best_lr_dir.exists():
            raise FileNotFoundError(f"Best Logistic Regression trial outputs not found at: {best_lr_dir}")
            
        fold_coefficients = {}
        features_list = []
        
        for idx, f_cfg in enumerate(folds):
            fold_id = idx + 1
            fold_dir = lr_output_dir / f"fold_{fold_id}"
            fold_dir.mkdir(parents=True, exist_ok=True)
            
            # Load fold train/test sets to get scaling standard deviation and feature lists
            train_path = self.slices_dir / f"fold_{fold_id}_train.parquet"
            train_df = pd.read_parquet(train_path)
            label_col = "Label_Binary" if self.label_version == "binary" else "Label_ThreeClass"
            train_df = train_df.dropna(subset=[label_col]).reset_index(drop=True)
            
            X_train = train_df.drop(columns=["Date", label_col])
            features_list = list(X_train.columns)
            std_train = X_train.std(ddof=0).values # population standard deviation
            
            # Load raw trained model
            model_path = best_lr_dir / f"fold_{fold_id}_model_raw.joblib"
            model = joblib.load(model_path)
            
            # coefficients have shape (n_classes, n_features) or (1, n_features) for binary
            raw_coef = model.coef_
            
            # For multi-class (3 classes), coef_ shape is (3, n_features)
            # Ensure n_classes dimension is present
            if raw_coef.ndim == 1:
                raw_coef = raw_coef.reshape(1, -1)
                
            n_classes = raw_coef.shape[0]
            
            # Compute standardized coefficients
            std_coef = self._compute_standardized_coefficients(raw_coef, std_train)
            
            # Save raw and standardized coefficients per class
            raw_dict = {}
            std_dict = {}
            ranking_dict = {}
            sign_dict = {}
            
            for c_idx in range(n_classes):
                class_name = LABEL_CLASSES[c_idx] if n_classes == 3 else "TARGET"
                raw_dict[class_name] = {features_list[j]: float(raw_coef[c_idx, j]) for j in range(len(features_list))}
                std_dict[class_name] = {features_list[j]: float(std_coef[c_idx, j]) for j in range(len(features_list))}
                
                # Ranking by absolute standardized coefficient
                sorted_features = sorted(range(len(features_list)), key=lambda j: abs(std_coef[c_idx, j]), reverse=True)
                ranking_dict[class_name] = [
                    {
                        "rank": rank + 1,
                        "feature": features_list[j],
                        "std_coefficient": float(std_coef[c_idx, j]),
                        "raw_coefficient": float(raw_coef[c_idx, j])
                    }
                    for rank, j in enumerate(sorted_features)
                ]
                
                # Sign checks
                sign_dict[class_name] = {
                    features_list[j]: "positive" if std_coef[c_idx, j] > 0 else "negative" if std_coef[c_idx, j] < 0 else "zero"
                    for j in range(len(features_list))
                }
                
            with open(fold_dir / "coefficients_raw.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(raw_dict, f, default_flow_style=False)
                
            with open(fold_dir / "coefficients_standardized.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(std_dict, f, default_flow_style=False)
                
            with open(fold_dir / "coefficient_ranking.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(ranking_dict, f, default_flow_style=False)
                
            with open(fold_dir / "sign_analysis.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(sign_dict, f, default_flow_style=False)
                
            fold_coefficients[fold_id] = {
                "std_coef": std_coef,
                "sign_dict": sign_dict,
                "ranking_dict": ranking_dict
            }
            
        # Global Ranking rollup (mean rank across full-year folds 1-7)
        global_rank = self._calculate_global_lr_ranking(fold_coefficients, features_list, folds)
        with open(lr_output_dir / "global_ranking.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(global_rank, f, default_flow_style=False)
            
        # Stability report
        stability_report = self._calculate_lr_stability(fold_coefficients, features_list, folds)
        with open(lr_output_dir / "stability_report.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(stability_report, f, default_flow_style=False)
            
        return {
            "global_ranking": global_rank,
            "stability_report": stability_report
        }

    def _calculate_global_lr_ranking(self, fold_coefficients: Dict[int, Any], features: List[str], folds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregates standardized coefficient feature ranks across Folds 1-7 (excluding partial Fold 8)."""
        full_year_folds = [idx + 1 for idx, f_cfg in enumerate(folds) if not f_cfg.get("partial", False)]
        n_classes = len(fold_coefficients[1]["ranking_dict"].keys())
        
        global_ranking = {}
        for class_name in fold_coefficients[1]["ranking_dict"].keys():
            feature_rank_sums = {feat: 0.0 for feat in features}
            
            for fold_id in full_year_folds:
                fold_ranks = fold_coefficients[fold_id]["ranking_dict"][class_name]
                for item in fold_ranks:
                    feature_rank_sums[item["feature"]] += item["rank"]
                    
            # Compute mean rank
            mean_ranks = {feat: rank_sum / len(full_year_folds) for feat, rank_sum in feature_rank_sums.items()}
            sorted_features = sorted(mean_ranks.items(), key=lambda x: x[1])
            
            global_ranking[class_name] = [
                {
                    "rank": rank + 1,
                    "feature": feat,
                    "mean_rank": float(mean_rank)
                }
                for rank, (feat, mean_rank) in enumerate(sorted_features)
            ]
            
        return global_ranking

    def _calculate_lr_stability(self, fold_coefficients: Dict[int, Any], features: List[str], folds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Computes rank correlations and sign consistency checking across folds."""
        top_k = self.exp_config['stability']['top_k']
        full_year_folds = [idx + 1 for idx, f_cfg in enumerate(folds) if not f_cfg.get("partial", False)]
        n_classes = len(fold_coefficients[1]["ranking_dict"].keys())
        
        stability_report = {
            "rank_correlation_matrix": {},
            "top_k_features_stability": {},
            "sign_consistency": {}
        }
        
        # 1. Sign consistency
        for class_name in fold_coefficients[1]["sign_dict"].keys():
            consistency = {}
            for feat in features:
                signs = [fold_coefficients[fid]["sign_dict"][class_name][feat] for fid in fold_coefficients.keys()]
                unique_signs = set(signs)
                if len(unique_signs) == 1:
                    consistency[feat] = f"consistent_{list(unique_signs)[0]}"
                else:
                    consistency[feat] = f"unstable (flips: {', '.join(unique_signs)})"
            stability_report["sign_consistency"][class_name] = consistency
            
        # 2. Spearman rank correlation and Top-K stability per class
        for class_name in fold_coefficients[1]["ranking_dict"].keys():
            # Rank correlation matrix (across all 8 folds)
            corr_matrix = {}
            for fid1 in fold_coefficients.keys():
                corr_matrix[fid1] = {}
                for fid2 in fold_coefficients.keys():
                    ranks1 = {item["feature"]: item["rank"] for item in fold_coefficients[fid1]["ranking_dict"][class_name]}
                    ranks2 = {item["feature"]: item["rank"] for item in fold_coefficients[fid2]["ranking_dict"][class_name]}
                    
                    r_vector1 = [ranks1[feat] for feat in features]
                    r_vector2 = [ranks2[feat] for feat in features]
                    
                    corr, _ = spearmanr(r_vector1, r_vector2)
                    corr_matrix[fid1][fid2] = float(corr)
                    
            stability_report["rank_correlation_matrix"][class_name] = corr_matrix
            
            # Top-K features stability across full-year folds
            top_k_frequencies = {feat: 0 for feat in features}
            for fold_id in full_year_folds:
                top_k_feats = [item["feature"] for item in fold_coefficients[fold_id]["ranking_dict"][class_name][:top_k]]
                for feat in top_k_feats:
                    top_k_frequencies[feat] += 1
                    
            # Ratio of folds each feature appears in top-K
            top_k_ratios = {
                feat: float(count / len(full_year_folds))
                for feat, count in sorted(top_k_frequencies.items(), key=lambda x: x[1], reverse=True)
                if count > 0
            }
            stability_report["top_k_features_stability"][class_name] = top_k_ratios
            
        return stability_report

    def explain_xgboost(self) -> Dict[str, Any]:
        """Computes native gain, coverage metrics, TreeSHAP values, and pairwise interactions for XGBoost."""
        logger.info("Explaining XGBoost Classifier...")
        folds = self.wf_config['folds']
        xgb_output_dir = self.run_output_dir / "xgboost"
        xgb_output_dir.mkdir(parents=True, exist_ok=True)
        
        best_xgb_dir = self.best_model_src / "xgboost" / "best_trial"
        if not best_xgb_dir.exists():
            raise FileNotFoundError(f"Best XGBoost trial outputs not found at: {best_xgb_dir}")
            
        fold_shap_summaries = {}
        features_list = []
        
        for idx, f_cfg in enumerate(folds):
            fold_id = idx + 1
            fold_dir = xgb_output_dir / f"fold_{fold_id}"
            fold_dir.mkdir(parents=True, exist_ok=True)
            
            # Load fold datasets
            train_path = self.slices_dir / f"fold_{fold_id}_train.parquet"
            test_path = self.slices_dir / f"fold_{fold_id}_test.parquet"
            train_df = pd.read_parquet(train_path)
            test_df = pd.read_parquet(test_path)
            
            label_col = "Label_Binary" if self.label_version == "binary" else "Label_ThreeClass"
            train_df = train_df.dropna(subset=[label_col]).reset_index(drop=True)
            test_df = test_df.dropna(subset=[label_col]).reset_index(drop=True)
            
            X_train = train_df.drop(columns=["Date", label_col])
            X_test = test_df.drop(columns=["Date", label_col])
            y_test = test_df[label_col].map(LABEL_MAPPING).values
            features_list = list(X_train.columns)
            
            # Load raw trained model
            model_path = best_xgb_dir / f"fold_{fold_id}_model_raw.joblib"
            model = joblib.load(model_path)
            
            # 1. Native feature importance
            booster = model.get_booster()
            native_gain = booster.get_score(importance_type="gain")
            native_weight = booster.get_score(importance_type="weight")
            native_cover = booster.get_score(importance_type="cover")
            
            native_importance = {}
            for feat in features_list:
                native_importance[feat] = {
                    "gain": float(native_gain.get(feat, 0.0)),
                    "weight": float(native_weight.get(feat, 0.0)),
                    "cover": float(native_cover.get(feat, 0.0))
                }
            with open(fold_dir / "native_importance.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(native_importance, f, default_flow_style=False)
                
            # 2. SHAP Background Reference Distribution
            bg_size = self.exp_config["shap"]["background_sample_size"]
            if len(X_train) > bg_size:
                X_bg = X_train.sample(n=bg_size, random_state=self.exp_config["shap"]["seed"])
            else:
                X_bg = X_train
                
            # Compute exact TreeSHAP values
            explainer = shap.TreeExplainer(model, data=X_bg)
            
            # shap_values returns shape (n_samples, n_features, n_classes)
            # check version/shape layout
            shap_results = explainer(X_test)
            shap_vals = shap_results.values
            
            # Standardize multidimensional SHAP arrays
            # shap_vals has shape (n_samples, n_features, n_classes) or (n_samples, n_features) for binary
            if shap_vals.ndim == 2:
                # Add third axis for compatibility
                shap_vals = shap_vals[:, :, np.newaxis]
                
            n_classes = shap_vals.shape[2]
            
            # Save SHAP Summary (mean absolute SHAP per feature per class)
            shap_summary = {}
            for c_idx in range(n_classes):
                class_name = LABEL_CLASSES[c_idx] if n_classes == 3 else "TARGET"
                mean_abs_shaps = np.mean(np.abs(shap_vals[:, :, c_idx]), axis=0)
                
                # Sorted ranking
                sorted_idx = np.argsort(mean_abs_shaps)[::-1]
                shap_summary[class_name] = [
                    {
                        "rank": rank + 1,
                        "feature": features_list[j],
                        "mean_abs_shap": float(mean_abs_shaps[j])
                    }
                    for rank, j in enumerate(sorted_idx)
                ]
            with open(fold_dir / "shap_summary.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(shap_summary, f, default_flow_style=False)
                
            fold_shap_summaries[fold_id] = shap_summary
            
            # Save Raw SHAP Dependence data (pairs of feature-value and SHAP-value)
            dep_data = {}
            for c_idx in range(n_classes):
                class_name = LABEL_CLASSES[c_idx] if n_classes == 3 else "TARGET"
                dep_data[class_name] = {}
                for j, feat in enumerate(features_list):
                    dep_data[class_name][feat] = [
                        {
                            "feature_value": float(X_test.iloc[i, j]),
                            "shap_value": float(shap_vals[i, j, c_idx])
                        }
                        for i in range(len(X_test))
                    ]
            with open(fold_dir / "shap_dependence_data.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(dep_data, f, default_flow_style=False)
                
            # 3. Gated Pairwise Interactions
            ceiling = self.exp_config["shap"]["interaction_row_ceiling"]
            if len(X_test) <= ceiling:
                try:
                    # shap_interaction returns array of shape (n_samples, n_features, n_features, n_classes)
                    inter_vals = explainer.shap_interaction_values(X_test)
                    if inter_vals.ndim == 3:
                        inter_vals = inter_vals[:, :, :, np.newaxis]
                        
                    inter_dict = {}
                    for c_idx in range(n_classes):
                        class_name = LABEL_CLASSES[c_idx] if n_classes == 3 else "TARGET"
                        inter_dict[class_name] = {}
                        for j1, feat1 in enumerate(features_list):
                            inter_dict[class_name][feat1] = {}
                            for j2, feat2 in enumerate(features_list):
                                mean_abs_inter = float(np.mean(np.abs(inter_vals[:, j1, j2, c_idx])))
                                inter_dict[class_name][feat1][feat2] = mean_abs_inter
                                
                    with open(fold_dir / "shap_interaction.yaml", "w", encoding="utf-8") as f:
                        yaml.safe_dump(inter_dict, f, default_flow_style=False)
                except Exception as e:
                    logger.warning(f"Failed to calculate SHAP interactions on fold {fold_id}: {e}")
                    with open(fold_dir / "shap_interaction.yaml", "w", encoding="utf-8") as f:
                        yaml.safe_dump({"skipped_with_reason": f"Calculation failed: {e}"}, f)
            else:
                with open(fold_dir / "shap_interaction.yaml", "w", encoding="utf-8") as f:
                    yaml.safe_dump({
                        "skipped_with_reason": f"Test set row count ({len(X_test)}) exceeded ceiling ({ceiling})"
                    }, f)
                    
            # 4. Local prediction explanations
            local_exp = self._generate_local_shap_explanations(
                model, X_test, y_test, shap_vals, features_list, n_classes
            )
            with open(fold_dir / "local_explanations.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(local_exp, f, default_flow_style=False)
                
        # Global Ranking rollup (mean rank across full-year folds 1-7)
        global_rank = self._calculate_global_xgb_ranking(fold_shap_summaries, features_list, folds)
        with open(xgb_output_dir / "global_ranking.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(global_rank, f, default_flow_style=False)
            
        # Stability report
        stability_report = self._calculate_xgb_stability(fold_shap_summaries, features_list, folds)
        with open(xgb_output_dir / "stability_report.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(stability_report, f, default_flow_style=False)
            
        return {
            "global_ranking": global_rank,
            "stability_report": stability_report
        }

    def _generate_local_shap_explanations(self, model: xgb.XGBClassifier, X_test: pd.DataFrame, y_true: np.ndarray,
                                         shap_vals: np.ndarray, features: List[str], n_classes: int) -> Dict[str, Any]:
        """Generates row-level local explanations for high-confidence correct and misclassified predictions."""
        local_cfg = self.exp_config["local_explanations"]
        n_correct = local_cfg["n_correct_samples_per_class"]
        n_misclassed = local_cfg["n_misclassified_samples"]
        seed = local_cfg["seed"]
        
        y_probs = model.predict_proba(X_test)
        y_preds = model.predict(X_test)
        
        local_explanations = {
            "correct_predictions": {},
            "misclassified_predictions": []
        }
        
        # 1. Correct classifications (highest confidence per class)
        np.random.seed(seed)
        for c_idx in range(n_classes):
            class_name = LABEL_CLASSES[c_idx] if n_classes == 3 else "TARGET"
            local_explanations["correct_predictions"][class_name] = []
            
            # Rows correctly classified as c_idx
            correct_indices = np.where((y_preds == c_idx) & (y_true == c_idx))[0]
            if len(correct_indices) > 0:
                # Sort by confidence probability
                sorted_indices = correct_indices[np.argsort(y_probs[correct_indices, c_idx])[::-1]]
                selected = sorted_indices[:n_correct]
                
                for idx in selected:
                    contrib = {
                        features[j]: float(shap_vals[idx, j, c_idx])
                        for j in range(len(features))
                    }
                    sorted_contrib = sorted(contrib.items(), key=lambda x: abs(x[1]), reverse=True)
                    
                    local_explanations["correct_predictions"][class_name].append({
                        "test_row_index": int(idx),
                        "actual_label": class_name,
                        "prediction_probability": float(y_probs[idx, c_idx]),
                        "feature_contributions": [
                            {"feature": feat, "shap_contribution": val}
                            for feat, val in sorted_contrib
                        ]
                    })
                    
        # 2. Misclassified classifications (highest confidence failures)
        misclass_indices = np.where(y_preds != y_true)[0]
        if len(misclass_indices) > 0:
            # Sort by error confidence probability (predicted probability of incorrect class)
            error_probs = np.max(y_probs[misclass_indices], axis=1)
            sorted_indices = misclass_indices[np.argsort(error_probs)[::-1]]
            selected = sorted_indices[:n_misclassed]
            
            for idx in selected:
                pred_class = y_preds[idx]
                true_class = y_true[idx]
                
                pred_name = LABEL_CLASSES[pred_class] if n_classes == 3 else f"CLASS_{pred_class}"
                true_name = LABEL_CLASSES[true_class] if n_classes == 3 else f"CLASS_{true_class}"
                
                contrib = {
                    features[j]: float(shap_vals[idx, j, pred_class])
                    for j in range(len(features))
                }
                sorted_contrib = sorted(contrib.items(), key=lambda x: abs(x[1]), reverse=True)
                
                local_explanations["misclassified_predictions"].append({
                    "test_row_index": int(idx),
                    "actual_label": true_name,
                    "predicted_label": pred_name,
                    "prediction_probability": float(y_probs[idx, pred_class]),
                    "feature_contributions_to_prediction": [
                        {"feature": feat, "shap_contribution": val}
                        for feat, val in sorted_contrib
                    ]
                })
                
        return local_explanations

    def _calculate_global_xgb_ranking(self, fold_shap_summaries: Dict[int, Any], features: List[str], folds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Rolls up mean absolute SHAP value feature ranks across folds 1-7."""
        full_year_folds = [idx + 1 for idx, f_cfg in enumerate(folds) if not f_cfg.get("partial", False)]
        
        global_ranking = {}
        for class_name in fold_shap_summaries[1].keys():
            feature_rank_sums = {feat: 0.0 for feat in features}
            
            for fold_id in full_year_folds:
                fold_ranks = fold_shap_summaries[fold_id][class_name]
                for item in fold_ranks:
                    feature_rank_sums[item["feature"]] += item["rank"]
                    
            # Compute mean rank
            mean_ranks = {feat: rank_sum / len(full_year_folds) for feat, rank_sum in feature_rank_sums.items()}
            sorted_features = sorted(mean_ranks.items(), key=lambda x: x[1])
            
            global_ranking[class_name] = [
                {
                    "rank": rank + 1,
                    "feature": feat,
                    "mean_rank": float(mean_rank)
                }
                for rank, (feat, mean_rank) in enumerate(sorted_features)
            ]
            
        return global_ranking

    def _calculate_xgb_stability(self, fold_shap_summaries: Dict[int, Any], features: List[str], folds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Computes rank correlations and Top-K frequency check across folds for XGBoost."""
        top_k = self.exp_config['stability']['top_k']
        full_year_folds = [idx + 1 for idx, f_cfg in enumerate(folds) if not f_cfg.get("partial", False)]
        
        stability_report = {
            "rank_correlation_matrix": {},
            "top_k_features_stability": {}
        }
        
        for class_name in fold_shap_summaries[1].keys():
            # Rank correlation matrix (across all 8 folds)
            corr_matrix = {}
            for fid1 in fold_shap_summaries.keys():
                corr_matrix[fid1] = {}
                for fid2 in fold_shap_summaries.keys():
                    ranks1 = {item["feature"]: item["rank"] for item in fold_shap_summaries[fid1][class_name]}
                    ranks2 = {item["feature"]: item["rank"] for item in fold_shap_summaries[fid2][class_name]}
                    
                    r_vector1 = [ranks1[feat] for feat in features]
                    r_vector2 = [ranks2[feat] for feat in features]
                    
                    corr, _ = spearmanr(r_vector1, r_vector2)
                    corr_matrix[fid1][fid2] = float(corr)
                    
            stability_report["rank_correlation_matrix"][class_name] = corr_matrix
            
            # Top-K features stability across full-year folds
            top_k_frequencies = {feat: 0 for feat in features}
            for fold_id in full_year_folds:
                top_k_feats = [item["feature"] for item in fold_shap_summaries[fold_id][class_name][:top_k]]
                for feat in top_k_feats:
                    top_k_frequencies[feat] += 1
                    
            # Ratio of folds each feature appears in top-K
            top_k_ratios = {
                feat: float(count / len(full_year_folds))
                for feat, count in sorted(top_k_frequencies.items(), key=lambda x: x[1], reverse=True)
                if count > 0
            }
            stability_report["top_k_features_stability"][class_name] = top_k_ratios
            
        return stability_report

    def generate_model_comparison_report(self, lr_results: Dict[str, Any], xgb_results: Dict[str, Any]) -> None:
        """Saves model overlap, directional correlation analysis and cross-model ranking correlations."""
        top_k = self.exp_config['stability']['top_k']
        
        comparison = {
            "run_id": self.run_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "top_k_value": top_k,
            "features_overlap_jaccard": {}
        }
        
        lr_ranks = lr_results["global_ranking"]
        xgb_ranks = xgb_results["global_ranking"]
        
        # Compute Jaccard Overlap per class in Top-K ranking
        for class_name in lr_ranks.keys():
            if class_name in xgb_ranks:
                lr_top_k = set([item["feature"] for item in lr_ranks[class_name][:top_k]])
                xgb_top_k = set([item["feature"] for item in xgb_ranks[class_name][:top_k]])
                
                intersection = lr_top_k.intersection(xgb_top_k)
                union = lr_top_k.union(xgb_top_k)
                jaccard = len(intersection) / len(union) if union else 0.0
                
                comparison["features_overlap_jaccard"][class_name] = {
                    "shared_features": list(intersection),
                    "jaccard_similarity": float(jaccard)
                }
                
        # Save comparison YAML file
        comp_path = self.run_output_dir / "model_comparison_report.yaml"
        with open(comp_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(comparison, f, default_flow_style=False)
            
        logger.info(f"Cross-model explainability comparison report written to: {comp_path}")

    def run_explainability_pipeline(self) -> None:
        """Executes the explainability workflow for all eligible models sequentially."""
        logger.info("Initializing Explainability Pipeline...")
        
        # Save run config snapshot
        config_snapshot = self.run_output_dir / "run_config_snapshot.yaml"
        with open(config_snapshot, "w", encoding="utf-8") as f:
            yaml.safe_dump({
                "explainability": self.exp_config,
                "library_versions": {
                    "shap": getattr(sys.modules.get("shap"), "__version__", "unknown"),
                    "scipy": getattr(sys.modules.get("scipy"), "__version__", "unknown"),
                    "scikit-learn": getattr(sys.modules.get("sklearn"), "__version__", "unknown")
                }
            }, f, default_flow_style=False)
            
        # Explain Logistic Regression coefficients
        lr_results = self.explain_logistic_regression()
        
        # Explain XGBoost SHAP values
        xgb_results = self.explain_xgboost()
        
        # Perform cross-model comparison
        self.generate_model_comparison_report(lr_results, xgb_results)
        
        logger.info("Explainability pipeline completed successfully.")

if __name__ == "__main__":
    try:
        global_config = load_global_config()
        # Resolve folders relative to project root
        project_root = Path(__file__).resolve().parent.parent.parent
        runs_dir = project_root / "data/walk_forward_runs"
        hpo_dir = project_root / "data/hpo_runs"
        output_dir = project_root / "data/explainability_runs"
        
        explainer = ModelExplainer(
            config=global_config.model_dump(),
            runs_dir=str(runs_dir),
            hpo_dir=str(hpo_dir),
            output_dir=str(output_dir)
        )
        explainer.run_explainability_pipeline()
    except Exception as e:
        logger.error(f"Explainability run failed: {e}", exc_info=True)
        sys.exit(1)
