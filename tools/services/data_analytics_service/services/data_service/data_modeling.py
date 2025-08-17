#!/usr/bin/env python3
"""
Data Modeling Service
Comprehensive machine learning modeling service that integrates data processors,
feature engineering, and leverages TextGenerator for intelligent model development and insights.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import logging
import json
from pathlib import Path

# Import our processors
try:
    from ...processors.data_processors import (
        CSVProcessor, FeatureProcessor, MLProcessor, 
        DataQualityProcessor, StatisticsProcessor
    )
except ImportError:
    from tools.services.data_analytics_service.processors.data_processors import (
        CSVProcessor, FeatureProcessor, MLProcessor,
        DataQualityProcessor, StatisticsProcessor
    )

# Import TextGenerator for AI-driven insights
TEXT_GENERATOR_AVAILABLE = False
try:
    from ....intelligence_service.language.text_generator import TextGenerator
    TEXT_GENERATOR_AVAILABLE = True
except ImportError:
    try:
        from tools.services.intelligence_service.language.text_generator import TextGenerator
        TEXT_GENERATOR_AVAILABLE = True
    except ImportError:
        TEXT_GENERATOR_AVAILABLE = False
        logging.warning("TextGenerator not available. AI-driven model insights will be disabled.")

logger = logging.getLogger(__name__)

class DataModelingService:
    """
    Comprehensive modeling service that integrates feature engineering, ML algorithms,
    and provides AI-driven model development guidance
    """
    
    def __init__(self, file_path: Optional[str] = None, csv_processor: Optional[CSVProcessor] = None):
        """
        Initialize modeling service
        
        Args:
            file_path: Path to data file
            csv_processor: Existing CSV processor instance
        """
        # Initialize base CSV processor
        if csv_processor:
            self.csv_processor = csv_processor
        elif file_path:
            self.csv_processor = CSVProcessor(file_path)
        else:
            raise ValueError("Either file_path or csv_processor must be provided")
        
        # Initialize specialized processors
        self.feature_processor = None
        self.ml_processor = None
        self.quality_processor = None
        self.statistics_processor = None
        self.text_generator = None
        
        # Model tracking
        self.models = {}
        self.experiments = []
        self.best_model = None
        self.modeling_history = []
        
        # Load data and initialize processors
        self._initialize_processors()
    
    def _initialize_processors(self) -> bool:
        """Initialize all processors"""
        try:
            # Load CSV data first
            if not self.csv_processor.load_csv():
                logger.error("Failed to load CSV data")
                return False
            
            # Initialize specialized processors
            self.feature_processor = FeatureProcessor(self.csv_processor)
            self.ml_processor = MLProcessor(self.csv_processor)
            self.quality_processor = DataQualityProcessor(self.csv_processor)
            self.statistics_processor = StatisticsProcessor(self.csv_processor)
            
            # Initialize TextGenerator if available
            if TEXT_GENERATOR_AVAILABLE:
                try:
                    self.text_generator = TextGenerator()
                except Exception as e:
                    logger.warning(f"Could not initialize TextGenerator: {e}")
                    self.text_generator = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize processors: {e}")
            return False
    
    def develop_model(self, target_column: str, problem_type: Optional[str] = None,
                     include_feature_engineering: bool = True, 
                     include_ai_guidance: bool = True) -> Dict[str, Any]:
        """
        Comprehensive model development workflow
        
        Args:
            target_column: Target variable
            problem_type: 'classification', 'regression', or auto-detect
            include_feature_engineering: Whether to perform feature engineering
            include_ai_guidance: Whether to include AI guidance and insights
            
        Returns:
            Complete model development results
        """
        logger.info(f"Starting model development for target: {target_column}")
        start_time = datetime.now()
        
        try:
            # Initialize experiment
            experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            results = {
                "experiment_id": experiment_id,
                "target_column": target_column,
                "problem_analysis": {},
                "data_preparation": {},
                "feature_engineering": {},
                "model_development": {},
                "model_evaluation": {},
                "recommendations": {},
                "ai_guidance": {},
                "experiment_metadata": {
                    "timestamp": start_time.isoformat(),
                    "ai_guidance_enabled": include_ai_guidance and self.text_generator is not None
                }
            }
            
            # 1. Problem Analysis
            logger.info("Analyzing ML problem...")
            problem_analysis = self.ml_processor.get_ml_analysis(target_column, problem_type)
            results["problem_analysis"] = problem_analysis
            
            # 2. Data Preparation Analysis
            logger.info("Analyzing data preparation needs...")
            data_prep_analysis = self._analyze_data_preparation(target_column)
            results["data_preparation"] = data_prep_analysis
            
            # 3. Feature Engineering (if requested)
            if include_feature_engineering:
                logger.info("Performing feature engineering...")
                feature_results = self._perform_feature_engineering(target_column)
                results["feature_engineering"] = feature_results
            
            # 4. Model Development
            logger.info("Developing models...")
            modeling_results = self._develop_models(target_column, problem_analysis)
            results["model_development"] = modeling_results
            
            # 5. Model Evaluation
            logger.info("Evaluating models...")
            evaluation_results = self._evaluate_models(target_column, modeling_results)
            results["model_evaluation"] = evaluation_results
            
            # 6. Generate Recommendations
            logger.info("Generating recommendations...")
            recommendations = self._generate_modeling_recommendations(results)
            results["recommendations"] = recommendations
            
            # 7. AI Guidance (if available)
            if include_ai_guidance and self.text_generator is not None:
                logger.info("Generating AI guidance...")
                try:
                    import asyncio
                    import concurrent.futures
                    
                    # Use a thread pool to avoid event loop conflicts
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # Create a new event loop in the thread
                        def run_ai_guidance():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                return loop.run_until_complete(self._generate_ai_guidance(results, target_column))
                            finally:
                                loop.close()
                        
                        future = executor.submit(run_ai_guidance)
                        ai_guidance = future.result(timeout=30)  # 30 second timeout
                    
                    results["ai_guidance"] = ai_guidance
                except Exception as e:
                    logger.warning(f"Could not generate AI guidance: {e}")
                    results["ai_guidance"] = {"error": "AI guidance generation failed", "details": str(e)}
            
            # Update metadata
            execution_time = (datetime.now() - start_time).total_seconds()
            results["experiment_metadata"]["execution_time_seconds"] = round(execution_time, 2)
            results["experiment_metadata"]["data_shape"] = list(self.csv_processor.df.shape)
            
            # Store experiment
            self.experiments.append(results)
            self.modeling_history.append({
                "experiment_id": experiment_id,
                "timestamp": start_time.isoformat(),
                "target_column": target_column,
                "execution_time": execution_time,
                "best_model": evaluation_results.get("best_model", {}).get("algorithm", "unknown")
            })
            
            logger.info(f"Model development completed in {execution_time:.2f} seconds")
            return results
            
        except Exception as e:
            logger.error(f"Error in model development: {e}")
            return {
                "error": str(e),
                "experiment_metadata": {
                    "timestamp": start_time.isoformat(),
                    "failed": True
                }
            }
    
    def _analyze_data_preparation(self, target_column: str) -> Dict[str, Any]:
        """Analyze data preparation requirements"""
        try:
            preparation_analysis = {
                "data_quality_summary": {},
                "preprocessing_requirements": {},
                "feature_readiness": {},
                "target_analysis": {}
            }
            
            # Get data quality summary
            quality_assessment = self.quality_processor.assess_overall_quality()
            preparation_analysis["data_quality_summary"] = quality_assessment
            
            # Get preprocessing requirements from ML processor
            prep_needs = self.ml_processor.analyze_data_preparation_needs(target_column)
            preparation_analysis["preprocessing_requirements"] = prep_needs
            
            # Analyze target variable
            df = self.csv_processor.df
            target_series = df[target_column].dropna()
            
            target_analysis = {
                "target_type": self._determine_target_type(target_series),
                "missing_values": int(df[target_column].isnull().sum()),
                "missing_percentage": round(df[target_column].isnull().sum() / len(df) * 100, 2),
                "unique_values": int(target_series.nunique()),
                "distribution_summary": {}
            }
            
            if pd.api.types.is_numeric_dtype(target_series):
                target_analysis["distribution_summary"] = {
                    "mean": float(target_series.mean()),
                    "std": float(target_series.std()),
                    "min": float(target_series.min()),
                    "max": float(target_series.max()),
                    "skewness": float(target_series.skew())
                }
            else:
                value_counts = target_series.value_counts()
                target_analysis["distribution_summary"] = {
                    "most_frequent_class": value_counts.index[0],
                    "most_frequent_count": int(value_counts.iloc[0]),
                    "class_distribution": value_counts.head(10).to_dict(),
                    "is_imbalanced": self._check_class_imbalance(value_counts)
                }
            
            preparation_analysis["target_analysis"] = target_analysis
            
            # Feature readiness assessment
            features_df = df.drop(columns=[target_column])
            preparation_analysis["feature_readiness"] = {
                "total_features": len(features_df.columns),
                "numeric_features": len(features_df.select_dtypes(include=[np.number]).columns),
                "categorical_features": len(features_df.select_dtypes(include=['object', 'category']).columns),
                "features_with_missing": features_df.columns[features_df.isnull().any()].tolist(),
                "high_cardinality_features": [
                    col for col in features_df.select_dtypes(include=['object', 'category']).columns
                    if features_df[col].nunique() > 50
                ]
            }
            
            return preparation_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing data preparation: {e}")
            return {"error": str(e)}
    
    def _perform_feature_engineering(self, target_column: str) -> Dict[str, Any]:
        """Perform comprehensive feature engineering"""
        try:
            feature_results = {
                "feature_analysis": {},
                "transformations_applied": [],
                "new_features_created": 0,
                "feature_selection_results": {}
            }
            
            # Get feature engineering analysis
            feature_analysis = self.feature_processor.get_full_feature_engineering_analysis(target_column)
            feature_results["feature_analysis"] = feature_analysis
            
            # Apply automatic feature engineering based on recommendations
            original_columns = len(self.csv_processor.df.columns)
            
            # 1. Handle datetime features
            datetime_cols = [col for col in self.csv_processor.df.columns 
                           if any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated'])]
            
            for col in datetime_cols:
                success = self.feature_processor.create_datetime_features(col)
                if success:
                    feature_results["transformations_applied"].append({
                        "type": "datetime_extraction",
                        "column": col,
                        "success": True
                    })
            
            # 2. Apply encoding for categorical variables
            categorical_cols = self.csv_processor.df.select_dtypes(include=['object', 'category']).columns
            categorical_cols = [col for col in categorical_cols if col != target_column]
            
            for col in categorical_cols:
                unique_count = self.csv_processor.df[col].nunique()
                
                if unique_count == 2:
                    success = self.feature_processor.apply_encoding(col, "label_encoding")
                elif unique_count <= 10:
                    success = self.feature_processor.apply_encoding(col, "onehot_encoding")
                else:
                    success = self.feature_processor.apply_encoding(col, "frequency_encoding")
                
                if success:
                    feature_results["transformations_applied"].append({
                        "type": "categorical_encoding",
                        "column": col,
                        "method": "label" if unique_count == 2 else "onehot" if unique_count <= 10 else "frequency",
                        "success": True
                    })
            
            # 3. Apply scaling for numeric features
            numeric_cols = self.csv_processor.df.select_dtypes(include=[np.number]).columns
            numeric_cols = [col for col in numeric_cols if col != target_column]
            
            if len(numeric_cols) > 0:
                success = self.feature_processor.apply_scaling(numeric_cols, "standard")
                if success:
                    feature_results["transformations_applied"].append({
                        "type": "numeric_scaling",
                        "columns": numeric_cols,
                        "method": "standard",
                        "success": True
                    })
            
            # Calculate new features created
            new_columns = len(self.feature_processor.df.columns) - original_columns
            feature_results["new_features_created"] = new_columns
            
            # Update processors to use the engineered features
            self.ml_processor.df = self.feature_processor.df.copy()
            
            return feature_results
            
        except Exception as e:
            logger.error(f"Error in feature engineering: {e}")
            return {"error": str(e)}
    
    def _develop_models(self, target_column: str, problem_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Develop multiple models"""
        try:
            modeling_results = {
                "models_trained": [],
                "training_details": {},
                "algorithm_performance": {}
            }
            
            # Get problem type
            problem_type = problem_analysis.get("ml_metadata", {}).get("problem_type", "classification")
            
            # Select algorithms based on problem type and data characteristics
            if problem_type == "classification":
                algorithms = ["logistic_regression", "random_forest_classifier", "decision_tree_classifier"]
                
                # Add more algorithms based on data size
                data_size = len(self.csv_processor.df)
                if data_size < 10000:
                    algorithms.append("svm_classifier")
                    algorithms.append("knn_classifier")
            else:
                algorithms = ["linear_regression", "random_forest_regressor", "ridge"]
                
                data_size = len(self.csv_processor.df)
                if data_size < 10000:
                    algorithms.append("svm_regressor")
            
            # Train models
            for algorithm in algorithms:
                try:
                    logger.info(f"Training {algorithm}...")
                    model_results = self.ml_processor.train_model(target_column, algorithm)
                    
                    if "error" not in model_results:
                        modeling_results["models_trained"].append(model_results)
                        self.models[model_results["model_id"]] = model_results
                        
                        logger.info(f"Successfully trained {algorithm}")
                    else:
                        logger.warning(f"Failed to train {algorithm}: {model_results['error']}")
                        
                except Exception as e:
                    logger.warning(f"Error training {algorithm}: {e}")
            
            # Compare models if multiple were trained successfully
            if len(modeling_results["models_trained"]) > 1:
                try:
                    comparison_results = self.ml_processor.compare_models(target_column, algorithms)
                    modeling_results["model_comparison"] = comparison_results
                except Exception as e:
                    logger.warning(f"Error comparing models: {e}")
            
            return modeling_results
            
        except Exception as e:
            logger.error(f"Error developing models: {e}")
            return {"error": str(e)}
    
    def _evaluate_models(self, target_column: str, modeling_results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate and rank models"""
        try:
            evaluation_results = {
                "model_rankings": [],
                "best_model": {},
                "performance_analysis": {},
                "model_interpretability": {}
            }
            
            trained_models = modeling_results.get("models_trained", [])
            
            if not trained_models:
                return {"error": "No models were successfully trained"}
            
            # Rank models by performance
            problem_type = trained_models[0].get("problem_type", "classification")
            
            if problem_type == "classification":
                # Rank by accuracy, then by F1-score
                primary_metric = "accuracy"
                secondary_metric = "f1_score"
            else:
                # Rank by R� score, then by RMSE (lower is better for RMSE)
                primary_metric = "r2_score"
                secondary_metric = "root_mean_squared_error"
            
            # Sort models by primary metric
            if secondary_metric == "root_mean_squared_error":
                # For RMSE, lower is better, so we need special handling
                ranked_models = sorted(trained_models, 
                                     key=lambda x: (x.get("metrics", {}).get(primary_metric, 0), 
                                                  -x.get("metrics", {}).get(secondary_metric, float('inf'))), 
                                     reverse=True)
            else:
                ranked_models = sorted(trained_models, 
                                     key=lambda x: (x.get("metrics", {}).get(primary_metric, 0),
                                                  x.get("metrics", {}).get(secondary_metric, 0)), 
                                     reverse=True)
            
            # Create ranking with performance details
            for i, model in enumerate(ranked_models):
                rank_info = {
                    "rank": i + 1,
                    "model_id": model.get("model_id"),
                    "algorithm": model.get("algorithm"),
                    "primary_metric_value": model.get("metrics", {}).get(primary_metric, 0),
                    "all_metrics": model.get("metrics", {}),
                    "training_time": model.get("training_time_seconds", 0)
                }
                evaluation_results["model_rankings"].append(rank_info)
            
            # Identify best model
            if ranked_models:
                best_model = ranked_models[0]
                evaluation_results["best_model"] = {
                    "model_id": best_model.get("model_id"),
                    "algorithm": best_model.get("algorithm"),
                    "performance_metrics": best_model.get("metrics", {}),
                    "feature_importance": best_model.get("feature_importance", []),
                    "coefficients": best_model.get("coefficients", []),
                    "hyperparameters": best_model.get("hyperparameters", {})
                }
                
                self.best_model = best_model
            
            # Performance analysis
            evaluation_results["performance_analysis"] = {
                "best_algorithm": evaluation_results["best_model"].get("algorithm"),
                "performance_gap": self._calculate_performance_gap(ranked_models, primary_metric),
                "training_time_analysis": self._analyze_training_times(ranked_models),
                "metric_summary": self._summarize_metrics(ranked_models)
            }
            
            # Model interpretability analysis
            evaluation_results["model_interpretability"] = self._analyze_model_interpretability(ranked_models)
            
            return evaluation_results
            
        except Exception as e:
            logger.error(f"Error evaluating models: {e}")
            return {"error": str(e)}
    
    def _generate_modeling_recommendations(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive modeling recommendations"""
        try:
            recommendations = {
                "immediate_actions": [],
                "model_improvement_suggestions": [],
                "production_considerations": [],
                "next_experiments": []
            }
            
            # Analyze results for recommendations
            evaluation = results.get("model_evaluation", {})
            best_model = evaluation.get("best_model", {})
            
            if best_model:
                algorithm = best_model.get("algorithm", "unknown")
                metrics = best_model.get("performance_metrics", {})
                
                # Performance-based recommendations
                if "accuracy" in metrics:
                    accuracy = metrics["accuracy"]
                    if accuracy < 0.7:
                        recommendations["immediate_actions"].append({
                            "action": "Improve data quality and feature engineering",
                            "reason": f"Low accuracy ({accuracy:.2f}) suggests data quality or feature issues",
                            "priority": "high"
                        })
                    elif accuracy > 0.95:
                        recommendations["immediate_actions"].append({
                            "action": "Check for data leakage or overfitting",
                            "reason": f"Very high accuracy ({accuracy:.2f}) may indicate data leakage",
                            "priority": "high"
                        })
                
                if "r2_score" in metrics:
                    r2 = metrics["r2_score"]
                    if r2 < 0.5:
                        recommendations["immediate_actions"].append({
                            "action": "Consider non-linear models or polynomial features",
                            "reason": f"Low R� score ({r2:.2f}) suggests model complexity issues",
                            "priority": "high"
                        })
            
            # Model improvement suggestions
            data_prep = results.get("data_preparation", {})
            quality_summary = data_prep.get("data_quality_summary", {})
            
            if isinstance(quality_summary, dict) and "overall_quality_score" in quality_summary:
                quality_score = quality_summary["overall_quality_score"]
                if quality_score < 0.8:
                    recommendations["model_improvement_suggestions"].append({
                        "suggestion": "Improve data quality before modeling",
                        "details": f"Data quality score is {quality_score:.2f}. Focus on missing value handling and outlier treatment.",
                        "expected_impact": "Medium to High"
                    })
            
            # Feature engineering suggestions
            feature_eng = results.get("feature_engineering", {})
            if "new_features_created" in feature_eng and feature_eng["new_features_created"] == 0:
                recommendations["model_improvement_suggestions"].append({
                    "suggestion": "Implement feature engineering",
                    "details": "No new features were created. Consider polynomial features, interactions, or domain-specific features.",
                    "expected_impact": "Medium"
                })
            
            # Algorithm-specific recommendations
            if best_model and "algorithm" in best_model:
                algo_recommendations = self._get_algorithm_specific_recommendations(best_model["algorithm"])
                recommendations["model_improvement_suggestions"].extend(algo_recommendations)
            
            # Production considerations
            recommendations["production_considerations"] = [
                {
                    "consideration": "Model monitoring",
                    "details": "Set up performance monitoring and data drift detection",
                    "importance": "High"
                },
                {
                    "consideration": "Model versioning",
                    "details": "Implement model versioning and rollback capabilities",
                    "importance": "Medium"
                },
                {
                    "consideration": "Inference latency",
                    "details": f"Best model ({best_model.get('algorithm', 'unknown')}) training time: {best_model.get('training_time', 0):.2f}s",
                    "importance": "Medium"
                }
            ]
            
            # Next experiments
            recommendations["next_experiments"] = [
                {
                    "experiment": "Hyperparameter tuning",
                    "description": f"Optimize hyperparameters for {best_model.get('algorithm', 'best model')}",
                    "expected_effort": "Medium"
                },
                {
                    "experiment": "Ensemble methods",
                    "description": "Combine top performing models using voting or stacking",
                    "expected_effort": "Medium"
                },
                {
                    "experiment": "Advanced feature engineering",
                    "description": "Create domain-specific features and interactions",
                    "expected_effort": "High"
                }
            ]
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {"error": str(e)}
    
    async def _generate_ai_guidance(self, results: Dict[str, Any], target_column: str) -> Dict[str, Any]:
        """Generate AI-driven modeling guidance"""
        try:
            if not self.text_generator:
                return {"error": "TextGenerator not available"}
            
            ai_guidance = {}
            
            # Create modeling summary for AI
            modeling_summary = self._create_modeling_summary_for_ai(results, target_column)
            
            # 1. Comprehensive model development strategy
            strategy_prompt = f"""
            You are a senior ML engineer reviewing this experiment. Analyze these results:

            {modeling_summary}

            Provide expert strategic guidance:

            1. **Algorithm Analysis**: Why did certain algorithms perform better? What does this tell us about the data?
            2. **Performance Interpretation**: Are the current results satisfactory? What's the realistic ceiling?
            3. **Optimization Priorities**: Which improvements would yield the highest ROI?
            4. **Risk Assessment**: What are the biggest risks with the current approach?
            5. **Next Experiment Design**: What should be the next 3 experiments to run?
            6. **Resource Allocation**: Where should the team focus their time and effort?

            Be specific about technical implementations and business trade-offs.
            Consider both immediate improvements and long-term strategy.
            """
            
            strategy_guidance = await self.text_generator.generate(strategy_prompt, temperature=0.6, max_tokens=2000)
            ai_guidance["comprehensive_strategy"] = strategy_guidance
            
            # 2. Advanced feature engineering recommendations
            feature_prompt = f"""
            As a feature engineering specialist, analyze these modeling results:

            {modeling_summary}

            Design an advanced feature engineering strategy:

            1. **Current Feature Assessment**: What do the model results tell us about existing features?
            2. **Domain-Specific Opportunities**: What domain knowledge could be encoded as features?
            3. **Interaction Discovery**: Which feature interactions should be explored?
            4. **Temporal Engineering**: How can time-based patterns be better captured?
            5. **Dimensionality Strategy**: When to add vs. reduce features?
            6. **Feature Selection Roadmap**: Systematic approach to identify optimal feature set
            7. **Engineering Pipeline**: How to automate and scale feature creation?

            Provide concrete implementation guidance with expected impact estimates.
            """
            
            feature_guidance = await self.text_generator.generate(feature_prompt, temperature=0.7, max_tokens=2200)
            ai_guidance["advanced_feature_strategy"] = feature_guidance
            
            # 3. Production deployment architecture
            deployment_prompt = f"""
            As an ML infrastructure expert, design the production deployment for:

            {modeling_summary}

            Create a comprehensive deployment strategy:

            1. **Architecture Design**: What's the optimal serving architecture for this model?
            2. **Scalability Planning**: How to handle traffic growth and model updates?
            3. **Monitoring Framework**: What metrics and alerts are essential?
            4. **A/B Testing Strategy**: How to safely roll out model improvements?
            5. **Failure Recovery**: Rollback strategies and circuit breakers
            6. **Data Pipeline**: How to maintain data quality in production?
            7. **Cost Optimization**: How to balance performance and cost?
            8. **Team Operations**: What processes and roles are needed?

            Consider both technical implementation and operational excellence.
            Include specific tools and technologies where applicable.
            """
            
            deployment_guidance = await self.text_generator.generate(deployment_prompt, temperature=0.5, max_tokens=2500)
            ai_guidance["production_architecture"] = deployment_guidance
            
            # 4. Model interpretability and business alignment
            interpretability_prompt = f"""
            As an ML product manager, analyze the business implications:

            {modeling_summary}

            Provide business-focused guidance:

            1. **Model Explainability**: How can this model's decisions be explained to stakeholders?
            2. **Business Metrics**: What business KPIs should be tracked beyond model metrics?
            3. **Stakeholder Communication**: How to present model performance to non-technical teams?
            4. **Bias and Fairness**: What bias considerations are important for this use case?
            5. **Regulatory Compliance**: What compliance requirements might apply?
            6. **ROI Measurement**: How to measure and demonstrate business value?
            7. **User Experience**: How will this model impact end users?

            Bridge the gap between technical performance and business value.
            """
            
            business_guidance = await self.text_generator.generate(interpretability_prompt, temperature=0.6, max_tokens=1800)
            ai_guidance["business_alignment"] = business_guidance
            
            return ai_guidance
            
        except Exception as e:
            logger.error(f"Error generating AI guidance: {e}")
            return {"error": str(e), "details": str(e)}
    
    def _create_modeling_summary_for_ai(self, results: Dict[str, Any], target_column: str) -> str:
        """Create structured modeling summary for AI analysis"""
        try:
            summary_parts = []
            
            # Problem overview
            problem_analysis = results.get("problem_analysis", {})
            if "problem_analysis" in problem_analysis:
                problem_info = problem_analysis["problem_analysis"]
                summary_parts.append(f"Problem Type: {problem_info.get('problem_type', 'unknown')}")
                summary_parts.append(f"Target Column: {target_column}")
            
            # Data characteristics
            if "analysis_metadata" in problem_analysis:
                metadata = problem_analysis["analysis_metadata"]
                data_shape = metadata.get("data_shape", [0, 0])
                summary_parts.append(f"Dataset Size: {data_shape[0]} rows, {data_shape[1]} columns")
            
            # Model performance
            evaluation = results.get("model_evaluation", {})
            if "best_model" in evaluation:
                best_model = evaluation["best_model"]
                summary_parts.append(f"Best Algorithm: {best_model.get('algorithm', 'unknown')}")
                
                metrics = best_model.get("performance_metrics", {})
                if metrics:
                    metric_strs = [f"{k}: {v:.3f}" for k, v in metrics.items() if isinstance(v, (int, float))]
                    summary_parts.append(f"Performance Metrics: {', '.join(metric_strs)}")
            
            # Data quality
            data_prep = results.get("data_preparation", {})
            if "data_quality_summary" in data_prep:
                quality = data_prep["data_quality_summary"]
                if isinstance(quality, dict) and "overall_quality_score" in quality:
                    summary_parts.append(f"Data Quality Score: {quality['overall_quality_score']:.2f}")
            
            # Feature engineering
            feature_eng = results.get("feature_engineering", {})
            if "new_features_created" in feature_eng:
                summary_parts.append(f"New Features Created: {feature_eng['new_features_created']}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error creating modeling summary: {e}")
            return "Error creating modeling summary"
    
    # Model optimization methods
    
    def optimize_best_model(self, target_column: str, optimization_type: str = "hyperparameter") -> Dict[str, Any]:
        """Optimize the best performing model"""
        try:
            if not self.best_model:
                return {"error": "No best model found. Run develop_model first."}
            
            best_algorithm = self.best_model.get("algorithm")
            
            if optimization_type == "hyperparameter":
                # Perform hyperparameter tuning
                tuning_results = self.ml_processor.hyperparameter_tuning(
                    target_column, best_algorithm
                )
                return tuning_results
            
            elif optimization_type == "feature_selection":
                # Perform feature selection optimization
                return {"message": "Feature selection optimization not yet implemented"}
            
            else:
                return {"error": f"Unknown optimization type: {optimization_type}"}
                
        except Exception as e:
            logger.error(f"Error optimizing model: {e}")
            return {"error": str(e)}
    
    def create_ensemble_model(self, target_column: str, ensemble_type: str = "voting") -> Dict[str, Any]:
        """Create ensemble model from best performers"""
        try:
            # Get top 3 models for ensemble
            if len(self.models) < 2:
                return {"error": "Need at least 2 models for ensemble"}
            
            # This would require implementation of ensemble methods
            return {"message": "Ensemble model creation not yet implemented"}
            
        except Exception as e:
            logger.error(f"Error creating ensemble: {e}")
            return {"error": str(e)}
    
    # Utility methods
    
    def _determine_target_type(self, target_series: pd.Series) -> str:
        """Determine target variable type"""
        if pd.api.types.is_numeric_dtype(target_series):
            unique_count = target_series.nunique()
            total_count = len(target_series)
            
            if unique_count <= 20 and unique_count < total_count * 0.1:
                return "classification"
            else:
                return "regression"
        else:
            return "classification"
    
    def _check_class_imbalance(self, class_distribution: pd.Series) -> bool:
        """Check if classes are imbalanced"""
        if len(class_distribution) <= 1:
            return False
        
        majority_count = class_distribution.iloc[0]
        minority_count = class_distribution.iloc[-1]
        
        return minority_count < majority_count * 0.3
    
    def _calculate_performance_gap(self, models: List[Dict], metric: str) -> float:
        """Calculate performance gap between best and worst model"""
        if len(models) < 2:
            return 0.0
        
        performances = [model.get("metrics", {}).get(metric, 0) for model in models]
        return max(performances) - min(performances)
    
    def _analyze_training_times(self, models: List[Dict]) -> Dict[str, Any]:
        """Analyze training time characteristics"""
        times = [model.get("training_time_seconds", 0) for model in models]
        
        return {
            "fastest_algorithm": min(models, key=lambda x: x.get("training_time_seconds", float('inf'))).get("algorithm"),
            "slowest_algorithm": max(models, key=lambda x: x.get("training_time_seconds", 0)).get("algorithm"),
            "average_training_time": round(np.mean(times), 2),
            "training_time_range": [min(times), max(times)]
        }
    
    def _summarize_metrics(self, models: List[Dict]) -> Dict[str, Any]:
        """Summarize performance metrics across models"""
        all_metrics = {}
        
        for model in models:
            metrics = model.get("metrics", {})
            for metric_name, value in metrics.items():
                if metric_name not in all_metrics:
                    all_metrics[metric_name] = []
                all_metrics[metric_name].append(value)
        
        summary = {}
        for metric_name, values in all_metrics.items():
            summary[metric_name] = {
                "best": max(values),
                "worst": min(values),
                "average": round(np.mean(values), 3),
                "std": round(np.std(values), 3)
            }
        
        return summary
    
    def _analyze_model_interpretability(self, models: List[Dict]) -> Dict[str, Any]:
        """Analyze model interpretability characteristics"""
        interpretability_map = {
            "linear_regression": "High",
            "logistic_regression": "High", 
            "decision_tree": "High",
            "random_forest": "Medium",
            "svm": "Low",
            "neural_network": "Low"
        }
        
        interpretability_analysis = []
        
        for model in models:
            algorithm = model.get("algorithm", "unknown")
            base_algorithm = algorithm.replace("_classifier", "").replace("_regressor", "")
            
            interpretability = interpretability_map.get(base_algorithm, "Unknown")
            
            analysis = {
                "algorithm": algorithm,
                "interpretability_level": interpretability,
                "has_feature_importance": "feature_importance" in model,
                "has_coefficients": "coefficients" in model
            }
            
            interpretability_analysis.append(analysis)
        
        return {
            "model_interpretability": interpretability_analysis,
            "most_interpretable": max(interpretability_analysis, 
                                    key=lambda x: {"High": 3, "Medium": 2, "Low": 1}.get(x["interpretability_level"], 0))
        }
    
    def _get_algorithm_specific_recommendations(self, algorithm: str) -> List[Dict[str, Any]]:
        """Get algorithm-specific improvement recommendations"""
        recommendations = []
        
        if "random_forest" in algorithm:
            recommendations.append({
                "suggestion": "Tune Random Forest hyperparameters",
                "details": "Optimize n_estimators, max_depth, and min_samples_split for better performance",
                "expected_impact": "Medium"
            })
        
        elif "logistic_regression" in algorithm:
            recommendations.append({
                "suggestion": "Try regularization tuning",
                "details": "Optimize C parameter and try different solvers (lbfgs, liblinear)",
                "expected_impact": "Low to Medium"
            })
        
        elif "decision_tree" in algorithm:
            recommendations.append({
                "suggestion": "Consider ensemble methods",
                "details": "Decision trees prone to overfitting. Try Random Forest or Gradient Boosting",
                "expected_impact": "High"
            })
        
        return recommendations
    
    # Model management methods
    
    def get_experiment_history(self) -> List[Dict[str, Any]]:
        """Get history of modeling experiments"""
        return self.modeling_history
    
    def get_best_model_details(self) -> Dict[str, Any]:
        """Get detailed information about the best model"""
        if not self.best_model:
            return {"error": "No best model available"}
        
        return self.best_model
    
    def save_model_results(self, output_path: str, experiment_id: Optional[str] = None) -> bool:
        """Save modeling results to file"""
        try:
            if experiment_id:
                # Save specific experiment
                experiment = next((exp for exp in self.experiments if exp.get("experiment_id") == experiment_id), None)
                if not experiment:
                    logger.error(f"Experiment {experiment_id} not found")
                    return False
                data_to_save = experiment
            else:
                # Save all experiments
                data_to_save = {
                    "experiments": self.experiments,
                    "modeling_history": self.modeling_history,
                    "best_model": self.best_model
                }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Model results saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model results: {e}")
            return False

# Convenience functions
def develop_ml_model(file_path: str, target_column: str, problem_type: Optional[str] = None,
                    output_path: Optional[str] = None, include_ai_guidance: bool = True) -> Dict[str, Any]:
    """
    Convenience function for comprehensive model development
    
    Args:
        file_path: Path to data file
        target_column: Target variable
        problem_type: 'classification', 'regression', or auto-detect
        output_path: Optional path to save results
        include_ai_guidance: Whether to include AI guidance
        
    Returns:
        Model development results
    """
    modeling_service = DataModelingService(file_path=file_path)
    results = modeling_service.develop_model(target_column, problem_type, 
                                           include_feature_engineering=True,
                                           include_ai_guidance=include_ai_guidance)
    
    if output_path:
        modeling_service.save_model_results(output_path, results.get("experiment_id"))
    
    return results

def quick_model_comparison(file_path: str, target_column: str) -> Dict[str, Any]:
    """
    Convenience function for quick model comparison
    
    Args:
        file_path: Path to data file
        target_column: Target variable
        
    Returns:
        Model comparison results
    """
    modeling_service = DataModelingService(file_path=file_path)
    
    # Quick analysis without full feature engineering
    problem_analysis = modeling_service.ml_processor.get_ml_analysis(target_column)
    problem_type = problem_analysis.get("ml_metadata", {}).get("problem_type", "classification")
    
    if problem_type == "classification":
        algorithms = ["logistic_regression", "random_forest_classifier", "decision_tree_classifier"]
    else:
        algorithms = ["linear_regression", "random_forest_regressor", "ridge"]
    
    return modeling_service.ml_processor.compare_models(target_column, algorithms)