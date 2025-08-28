#!/usr/bin/env python3
"""
Data EDA Service
Comprehensive Exploratory Data Analysis service that integrates all data processors
and leverages TextGenerator for intelligent analysis and insights.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging
import json
from pathlib import Path

# Import processors with correct paths
from ....processors.data_processors.analytics.statistics_processor import StatisticsProcessor
from ....processors.data_processors.preprocessors.csv_processor import CSVProcessor
from ....processors.data_processors.management.metadata.metadata_extractor import MetadataExtractor
from ....processors.data_processors.core.data_quality_processor import DataQualityProcessor
from ....processors.data_processors.utilities.feature_processor import FeatureProcessor

STATISTICS_PROCESSOR_AVAILABLE = True
CSV_PROCESSOR_AVAILABLE = True
METADATA_EXTRACTOR_AVAILABLE = True
DATA_QUALITY_PROCESSOR_AVAILABLE = True
FEATURE_PROCESSOR_AVAILABLE = True

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
        logging.warning("TextGenerator not available. AI-driven insights will be disabled.")

logger = logging.getLogger(__name__)

class DataEDAService:
    """
    Comprehensive EDA service that integrates multiple data processors
    and provides AI-driven insights through TextGenerator integration
    """
    
    def __init__(self, file_path: Optional[str] = None, csv_processor: Optional[CSVProcessor] = None):
        """
        Initialize EDA service
        
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
        self.statistics_processor = None
        self.quality_processor = None
        self.feature_processor = None
        self.metadata_extractor = None
        self.text_generator = None
        
        # Analysis cache
        self.analysis_cache = {}
        self.analysis_history = []
        
        # Load data and initialize processors
        self._initialize_processors()
    
    def _initialize_processors(self) -> bool:
        """Initialize all data processors"""
        try:
            # Load CSV data first
            if not self.csv_processor.load_csv():
                logger.error("Failed to load CSV data")
                return False
            
            # Initialize specialized processors
            self.statistics_processor = StatisticsProcessor(self.csv_processor)
            self.quality_processor = DataQualityProcessor(self.csv_processor)
            self.feature_processor = FeatureProcessor(self.csv_processor)
            self.metadata_extractor = MetadataExtractor()
            
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
    
    def perform_comprehensive_eda(self, target_column: Optional[str] = None, 
                                 include_ai_insights: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive exploratory data analysis
        
        Args:
            target_column: Target variable for supervised analysis
            include_ai_insights: Whether to generate AI-driven insights
            
        Returns:
            Complete EDA results with insights
        """
        logger.info("Starting comprehensive EDA analysis")
        start_time = datetime.now()
        
        try:
            # Core data analysis
            eda_results = {
                "metadata": {},
                "data_overview": {},
                "statistical_analysis": {},
                "data_quality_assessment": {},
                "feature_analysis": {},
                "insights_and_recommendations": {},
                "analysis_metadata": {
                    "timestamp": start_time.isoformat(),
                    "target_column": target_column,
                    "ai_insights_enabled": include_ai_insights and self.text_generator is not None
                }
            }
            
            # 1. Extract metadata
            logger.info("Extracting metadata...")
            metadata_result = self.metadata_extractor.extract_metadata(
                self.csv_processor.file_path, "csv"
            )
            eda_results["metadata"] = metadata_result
            
            # 2. Basic data overview
            logger.info("Generating data overview...")
            eda_results["data_overview"] = self._generate_data_overview()
            
            # 3. Statistical analysis
            logger.info("Performing statistical analysis...")
            statistical_analysis = self.statistics_processor.get_full_statistical_analysis()
            eda_results["statistical_analysis"] = statistical_analysis
            self.analysis_cache["statistics"] = statistical_analysis
            
            # 4. Data quality assessment
            logger.info("Assessing data quality...")
            quality_assessment = self.quality_processor.get_full_quality_assessment()
            eda_results["data_quality_assessment"] = quality_assessment
            self.analysis_cache["quality"] = quality_assessment
            
            # 5. Feature analysis
            logger.info("Analyzing features...")
            feature_analysis = self.feature_processor.get_full_feature_engineering_analysis(target_column)
            eda_results["feature_analysis"] = feature_analysis
            self.analysis_cache["features"] = feature_analysis
            
            # 6. Generate insights and recommendations
            logger.info("Generating insights and recommendations...")
            insights = self._generate_insights_and_recommendations(
                eda_results, target_column, include_ai_insights
            )
            eda_results["insights_and_recommendations"] = insights
            
            # Update metadata with execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            eda_results["analysis_metadata"]["execution_time_seconds"] = round(execution_time, 2)
            eda_results["analysis_metadata"]["data_shape"] = list(self.csv_processor.df.shape)
            
            # Cache complete results
            self.analysis_cache["complete_eda"] = eda_results
            self.analysis_history.append({
                "timestamp": start_time.isoformat(),
                "analysis_type": "comprehensive_eda",
                "target_column": target_column,
                "execution_time": execution_time
            })
            
            logger.info(f"EDA analysis completed in {execution_time:.2f} seconds")
            return eda_results
            
        except Exception as e:
            logger.error(f"Error performing comprehensive EDA: {e}")
            return {
                "error": str(e),
                "analysis_metadata": {
                    "timestamp": start_time.isoformat(),
                    "failed": True
                }
            }
    
    def _generate_data_overview(self) -> Dict[str, Any]:
        """Generate comprehensive data overview"""
        try:
            df = self.csv_processor.df
            
            overview = {
                "basic_info": {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
                    "file_size_mb": self.csv_processor.analyze_file_info().get("file_size_mb", 0)
                },
                "column_types": {
                    "numeric": len(df.select_dtypes(include=[np.number]).columns),
                    "categorical": len(df.select_dtypes(include=['object', 'category']).columns),
                    "datetime": 0  # Will be detected separately
                },
                "missing_data": {
                    "total_missing_cells": int(df.isnull().sum().sum()),
                    "missing_percentage": round(df.isnull().sum().sum() / df.size * 100, 2),
                    "columns_with_missing": df.columns[df.isnull().any()].tolist(),
                    "rows_with_missing": int(df.isnull().any(axis=1).sum())
                },
                "duplicates": {
                    "duplicate_rows": int(df.duplicated().sum()),
                    "duplicate_percentage": round(df.duplicated().sum() / len(df) * 100, 2)
                }
            }
            
            # Detect datetime columns
            datetime_cols = []
            for col in df.columns:
                try:
                    pd.to_datetime(df[col], errors='raise')
                    datetime_cols.append(col)
                except:
                    pass
            
            overview["column_types"]["datetime"] = len(datetime_cols)
            overview["datetime_columns"] = datetime_cols
            
            # Sample data
            overview["sample_data"] = {
                "head": df.head(3).to_dict('records'),
                "tail": df.tail(2).to_dict('records')
            }
            
            # Column summary
            column_summary = []
            for col in df.columns:
                col_info = {
                    "name": col,
                    "type": str(df[col].dtype),
                    "unique_values": int(df[col].nunique()),
                    "missing_count": int(df[col].isnull().sum()),
                    "missing_percentage": round(df[col].isnull().sum() / len(df) * 100, 2)
                }
                
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_info.update({
                        "min": float(df[col].min()) if not df[col].empty else None,
                        "max": float(df[col].max()) if not df[col].empty else None,
                        "mean": float(df[col].mean()) if not df[col].empty else None
                    })
                else:
                    col_info["most_frequent"] = df[col].mode().iloc[0] if not df[col].mode().empty else None
                
                column_summary.append(col_info)
            
            overview["column_summary"] = column_summary
            
            return overview
            
        except Exception as e:
            logger.error(f"Error generating data overview: {e}")
            return {"error": str(e)}
    
    def _generate_insights_and_recommendations(self, eda_results: Dict[str, Any], 
                                             target_column: Optional[str], 
                                             include_ai_insights: bool) -> Dict[str, Any]:
        """Generate comprehensive insights and recommendations"""
        try:
            insights = {
                "key_findings": [],
                "data_quality_insights": [],
                "statistical_insights": [],
                "feature_insights": [],
                "modeling_recommendations": [],
                "next_steps": []
            }
            
            # Generate rule-based insights
            insights.update(self._generate_rule_based_insights(eda_results, target_column))
            
            # Generate AI-driven insights if available
            if include_ai_insights and self.text_generator is not None:
                try:
                    import asyncio
                    import concurrent.futures
                    
                    # Use a thread pool to avoid event loop conflicts
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # Create a new event loop in the thread
                        def run_ai_insights():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                return loop.run_until_complete(self._generate_ai_insights(eda_results, target_column))
                            finally:
                                loop.close()
                        
                        future = executor.submit(run_ai_insights)
                        ai_insights = future.result(timeout=30)  # 30 second timeout
                    
                    insights["ai_insights"] = ai_insights
                except Exception as e:
                    logger.warning(f"Could not generate AI insights: {e}")
                    insights["ai_insights"] = {"error": "AI insights generation failed", "details": str(e)}
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {"error": str(e)}
    
    def _generate_rule_based_insights(self, eda_results: Dict[str, Any], 
                                    target_column: Optional[str]) -> Dict[str, Any]:
        """Generate rule-based insights from analysis results"""
        insights = {
            "key_findings": [],
            "data_quality_insights": [],
            "statistical_insights": [],
            "feature_insights": [],
            "modeling_recommendations": []
        }
        
        try:
            # Data quality insights
            quality_data = eda_results.get("data_quality_assessment", {})
            if "overview" in quality_data:
                overall_quality = quality_data["overview"].get("overall_quality_score", 0)
                
                if overall_quality >= 0.9:
                    insights["data_quality_insights"].append({
                        "type": "positive",
                        "message": f"Excellent data quality (score: {overall_quality:.2f}). Data is ready for analysis.",
                        "priority": "info"
                    })
                elif overall_quality >= 0.7:
                    insights["data_quality_insights"].append({
                        "type": "warning",
                        "message": f"Good data quality (score: {overall_quality:.2f}) with some issues to address.",
                        "priority": "medium"
                    })
                else:
                    insights["data_quality_insights"].append({
                        "type": "critical",
                        "message": f"Poor data quality (score: {overall_quality:.2f}). Significant data cleaning required.",
                        "priority": "high"
                    })
            
            # Missing data insights
            overview_data = eda_results.get("data_overview", {})
            if "missing_data" in overview_data:
                missing_pct = overview_data["missing_data"].get("missing_percentage", 0)
                
                if missing_pct > 20:
                    insights["data_quality_insights"].append({
                        "type": "critical",
                        "message": f"High missing data rate ({missing_pct:.1f}%). Consider imputation strategies or data collection improvements.",
                        "priority": "high"
                    })
                elif missing_pct > 5:
                    insights["data_quality_insights"].append({
                        "type": "warning",
                        "message": f"Moderate missing data ({missing_pct:.1f}%). Plan imputation strategy before modeling.",
                        "priority": "medium"
                    })
            
            # Statistical insights
            stats_data = eda_results.get("statistical_analysis", {})
            if "correlation_analysis" in stats_data:
                corr_analysis = stats_data["correlation_analysis"]
                if "strongest_correlation" in corr_analysis:
                    strongest = corr_analysis["strongest_correlation"]
                    if abs(strongest.get("correlation", 0)) > 0.8:
                        insights["statistical_insights"].append({
                            "type": "finding",
                            "message": f"Strong correlation detected between {strongest.get('variables', [])} (r={strongest.get('correlation', 0):.3f})",
                            "priority": "medium"
                        })
            
            # Feature insights
            feature_data = eda_results.get("feature_analysis", {})
            if "dimensionality_analysis" in feature_data:
                dim_analysis = feature_data["dimensionality_analysis"]
                curse_risk = dim_analysis.get("curse_of_dimensionality_risk", "low")
                
                if curse_risk == "high":
                    insights["feature_insights"].append({
                        "type": "warning",
                        "message": "High risk of curse of dimensionality. Consider dimensionality reduction techniques.",
                        "priority": "high"
                    })
            
            # Modeling recommendations
            if target_column:
                df = self.csv_processor.df
                if target_column in df.columns:
                    target_type = "classification" if not pd.api.types.is_numeric_dtype(df[target_column]) else "regression"
                    
                    if target_type == "classification":
                        unique_classes = df[target_column].nunique()
                        if unique_classes == 2:
                            insights["modeling_recommendations"].append({
                                "type": "recommendation",
                                "message": "Binary classification problem. Start with Logistic Regression and Random Forest.",
                                "priority": "info"
                            })
                        else:
                            insights["modeling_recommendations"].append({
                                "type": "recommendation", 
                                "message": f"Multi-class classification ({unique_classes} classes). Consider Random Forest and XGBoost.",
                                "priority": "info"
                            })
                    else:
                        insights["modeling_recommendations"].append({
                            "type": "recommendation",
                            "message": "Regression problem. Start with Linear Regression and Random Forest Regressor.",
                            "priority": "info"
                        })
            
            # Key findings summary
            total_insights = (len(insights["data_quality_insights"]) + 
                            len(insights["statistical_insights"]) + 
                            len(insights["feature_insights"]))
            
            insights["key_findings"] = [
                f"Analysis completed with {total_insights} insights generated",
                f"Data contains {overview_data.get('basic_info', {}).get('rows', 0)} rows and {overview_data.get('basic_info', {}).get('columns', 0)} columns",
                f"Overall data quality score: {quality_data.get('overview', {}).get('overall_quality_score', 0):.2f}"
            ]
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating rule-based insights: {e}")
            return insights
    
    async def _generate_ai_insights(self, eda_results: Dict[str, Any], 
                            target_column: Optional[str]) -> Dict[str, Any]:
        """Generate AI-driven insights using TextGenerator"""
        try:
            if not self.text_generator:
                return {"error": "TextGenerator not available"}
            
            # Create a comprehensive summary for AI analysis
            analysis_summary = self._create_analysis_summary_for_ai(eda_results, target_column)
            
            # Generate different types of AI insights
            ai_insights = {}
            
            # 1. Intelligent data story generation
            data_story_prompt = f"""
            You are a senior data scientist analyzing a dataset. Based on the following comprehensive analysis:

            {analysis_summary}

            Please provide an expert interpretation covering:

            1. **Data Story**: What narrative does this data tell? What are the key business insights?
            2. **Critical Findings**: What are the most important discoveries from this analysis?
            3. **Hidden Patterns**: What patterns might be overlooked by basic statistical analysis?
            4. **Business Impact**: How should this analysis influence business decisions?
            5. **Risk Assessment**: What data-related risks should be addressed immediately?

            Format your response as structured insights that a business stakeholder would find valuable.
            Be specific, actionable, and highlight both opportunities and concerns.
            """
            
            data_story = await self.text_generator.generate(data_story_prompt, temperature=0.7, max_tokens=1500)
            ai_insights["intelligent_data_story"] = data_story
            
            # 2. Advanced modeling strategy (if target specified)
            if target_column:
                modeling_prompt = f"""
                As an ML engineering expert, analyze this dataset for predicting '{target_column}':

                {analysis_summary}

                Provide strategic recommendations:

                1. **Algorithmic Approach**: Which ML algorithms would be most effective and why?
                2. **Feature Strategy**: What feature engineering approaches would likely yield the best results?
                3. **Data Preparation**: What are the critical preprocessing steps, prioritized by impact?
                4. **Evaluation Strategy**: How should model performance be measured and validated?
                5. **Implementation Challenges**: What technical challenges should be anticipated?
                6. **Performance Expectations**: What performance metrics can realistically be achieved?

                Consider the data characteristics, business context, and technical constraints.
                Provide specific, implementable recommendations.
                """
                
                modeling_advice = await self.text_generator.generate(modeling_prompt, temperature=0.5, max_tokens=2000)
                ai_insights["advanced_modeling_strategy"] = modeling_advice
            
            # 3. Data quality enhancement roadmap
            quality_prompt = f"""
            As a data quality expert, create a comprehensive improvement plan based on:

            {analysis_summary}

            Deliver a structured improvement roadmap:

            1. **Immediate Actions** (0-30 days): Critical issues requiring immediate attention
            2. **Short-term Improvements** (1-3 months): Important quality enhancements
            3. **Long-term Strategy** (3-12 months): Systematic data quality improvements
            4. **Monitoring Framework**: How to continuously monitor and maintain data quality
            5. **Resource Requirements**: What tools, skills, and resources are needed
            6. **ROI Estimation**: Expected impact and business value of these improvements

            Prioritize actions by business impact and implementation difficulty.
            Include specific metrics and success criteria.
            """
            
            quality_roadmap = await self.text_generator.generate(quality_prompt, temperature=0.6, max_tokens=1800)
            ai_insights["quality_enhancement_roadmap"] = quality_roadmap
            
            # 4. Intelligent pattern discovery
            pattern_prompt = f"""
            As an expert data detective, analyze this dataset for hidden insights:

            {analysis_summary}

            Investigate and report on:

            1. **Anomaly Interpretation**: What might explain unusual patterns or outliers?
            2. **Correlation Insights**: What do the correlations suggest about underlying relationships?
            3. **Distribution Analysis**: What do the data distributions reveal about the underlying process?
            4. **Temporal Patterns**: If applicable, what time-based trends are significant?
            5. **Segmentation Opportunities**: How could this data be segmented for deeper analysis?
            6. **External Factors**: What external data sources might enhance this analysis?

            Think like a domain expert who understands both the technical and business aspects.
            Provide hypotheses that could guide further investigation.
            """
            
            pattern_insights = await self.text_generator.generate(pattern_prompt, temperature=0.8, max_tokens=1600)
            ai_insights["intelligent_pattern_discovery"] = pattern_insights
            
            return ai_insights
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return {"error": str(e), "details": str(e)}
    
    def _create_analysis_summary_for_ai(self, eda_results: Dict[str, Any], 
                                      target_column: Optional[str]) -> str:
        """Create a comprehensive structured summary for AI analysis"""
        try:
            summary_sections = []
            
            # Dataset Overview
            overview = eda_results.get("data_overview", {})
            basic_info = overview.get("basic_info", {})
            
            dataset_section = f"""
=== DATASET OVERVIEW ===
• Size: {basic_info.get('rows', 0):,} rows × {basic_info.get('columns', 0)} columns
• Memory Usage: {basic_info.get('memory_usage_mb', 0)} MB
• File Size: {basic_info.get('file_size_mb', 0)} MB"""
            summary_sections.append(dataset_section)
            
            # Data Quality Assessment
            quality = eda_results.get("data_quality_assessment", {})
            if "overview" in quality:
                quality_info = quality["overview"]
                quality_section = f"""
=== DATA QUALITY ===
• Overall Quality Score: {quality_info.get('overall_quality_score', 0):.2f}/1.0
• Quality Grade: {quality_info.get('quality_grade', 'Unknown')}
• Component Scores:
  - Completeness: {quality_info.get('component_scores', {}).get('completeness', 0):.2f}
  - Uniqueness: {quality_info.get('component_scores', {}).get('uniqueness', 0):.2f}
  - Validity: {quality_info.get('component_scores', {}).get('validity', 0):.2f}
  - Consistency: {quality_info.get('component_scores', {}).get('consistency', 0):.2f}"""
                summary_sections.append(quality_section)
            
            # Missing Data Analysis
            missing_data = overview.get("missing_data", {})
            missing_section = f"""
=== MISSING DATA ===
• Missing Percentage: {missing_data.get('missing_percentage', 0):.1f}%
• Total Missing Cells: {missing_data.get('total_missing_cells', 0):,}
• Columns with Missing Data: {len(missing_data.get('columns_with_missing', []))}
• Rows with Missing Data: {missing_data.get('rows_with_missing', 0):,}"""
            summary_sections.append(missing_section)
            
            # Column Type Distribution
            col_types = overview.get("column_types", {})
            column_section = f"""
=== COLUMN ANALYSIS ===
• Numeric Columns: {col_types.get('numeric', 0)}
• Categorical Columns: {col_types.get('categorical', 0)}  
• DateTime Columns: {col_types.get('datetime', 0)}
• Duplicate Rows: {overview.get('duplicates', {}).get('duplicate_rows', 0)} ({overview.get('duplicates', {}).get('duplicate_percentage', 0):.1f}%)"""
            summary_sections.append(column_section)
            
            # Statistical Insights
            stats = eda_results.get("statistical_analysis", {})
            if "correlation_analysis" in stats:
                corr_analysis = stats["correlation_analysis"]
                stats_section = "=== STATISTICAL INSIGHTS ==="
                
                if "strongest_correlation" in corr_analysis:
                    strongest = corr_analysis["strongest_correlation"]
                    corr_value = strongest.get("correlation", 0)
                    if abs(corr_value) > 0.5:
                        vars_str = " ↔ ".join(strongest.get("variables", []))
                        stats_section += f"\n• Strongest Correlation: {vars_str} (r={corr_value:.3f})"
                
                # Add distribution analysis insights
                if "distribution_analysis" in stats:
                    dist_analysis = stats["distribution_analysis"]
                    normal_count = 0
                    skewed_count = 0
                    
                    for col, analysis in dist_analysis.items():
                        if isinstance(analysis, dict):
                            if analysis.get("likely_normal", False):
                                normal_count += 1
                            shape = analysis.get("distribution_shape", {})
                            if abs(shape.get("skewness", 0)) > 1:
                                skewed_count += 1
                    
                    if normal_count > 0:
                        stats_section += f"\n• Normal Distributions: {normal_count} columns"
                    if skewed_count > 0:
                        stats_section += f"\n• Skewed Distributions: {skewed_count} columns"
                
                summary_sections.append(stats_section)
            
            # Target Column Analysis (if specified)
            if target_column:
                target_section = f"""
=== TARGET ANALYSIS ===
• Target Column: {target_column}"""
                
                # Add target-specific insights from column summary
                column_summary = overview.get("column_summary", [])
                for col_info in column_summary:
                    if col_info.get("name") == target_column:
                        target_section += f"""
• Data Type: {col_info.get('type', 'Unknown')}
• Unique Values: {col_info.get('unique_values', 0)}
• Missing Values: {col_info.get('missing_count', 0)} ({col_info.get('missing_percentage', 0):.1f}%)"""
                        
                        if 'min' in col_info:
                            target_section += f"""
• Value Range: {col_info.get('min', 0):.2f} to {col_info.get('max', 0):.2f}
• Mean: {col_info.get('mean', 0):.2f}"""
                        elif 'most_frequent' in col_info:
                            target_section += f"""
• Most Frequent Value: {col_info.get('most_frequent', 'N/A')}"""
                        break
                
                summary_sections.append(target_section)
            
            # Data Quality Issues Summary
            quality_issues = []
            completeness_data = quality.get("completeness", {})
            if "by_column" in completeness_data:
                high_missing_cols = [
                    col["column_name"] for col in completeness_data["by_column"] 
                    if col.get("missing_percentage", 0) > 20
                ]
                if high_missing_cols:
                    quality_issues.append(f"High missing data: {', '.join(high_missing_cols[:3])}")
            
            uniqueness_data = quality.get("uniqueness", {})
            if "by_column" in uniqueness_data:
                duplicate_issues = [
                    col["column_name"] for col in uniqueness_data["by_column"]
                    if col.get("is_likely_identifier", False) and col.get("uniqueness_rate", 1) < 0.95
                ]
                if duplicate_issues:
                    quality_issues.append(f"Identifier duplicates: {', '.join(duplicate_issues[:2])}")
            
            if quality_issues:
                issues_section = f"""
=== KEY QUALITY ISSUES ===
{chr(10).join(f'• {issue}' for issue in quality_issues)}"""
                summary_sections.append(issues_section)
            
            # Business Domain Context (if detected)
            patterns = eda_results.get("statistical_analysis", {}).get("patterns", {})
            if patterns and "primary_domain" in patterns:
                domain = patterns["primary_domain"]
                confidence = patterns.get("confidence", 0)
                if confidence > 0.3:
                    domain_section = f"""
=== BUSINESS CONTEXT ===
• Detected Domain: {domain.title()}
• Confidence: {confidence:.1%}"""
                    summary_sections.append(domain_section)
            
            return "\n".join(summary_sections)
            
        except Exception as e:
            logger.error(f"Error creating comprehensive AI summary: {e}")
            return "Error creating comprehensive analysis summary"
    
    def get_quick_insights(self, target_column: Optional[str] = None) -> Dict[str, Any]:
        """Get quick insights without full EDA"""
        try:
            # Check if we have cached results
            if "complete_eda" in self.analysis_cache:
                return self.analysis_cache["complete_eda"]["insights_and_recommendations"]
            
            # Generate quick analysis
            quick_results = {
                "data_overview": self._generate_data_overview(),
                "basic_quality": self.quality_processor.assess_overall_quality(),
                "basic_stats": self.statistics_processor.calculate_basic_statistics()
            }
            
            # Generate insights from quick analysis
            insights = self._generate_rule_based_insights({
                "data_overview": quick_results["data_overview"],
                "data_quality_assessment": {"overview": quick_results["basic_quality"]},
                "statistical_analysis": {"basic_statistics": quick_results["basic_stats"]}
            }, target_column)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting quick insights: {e}")
            return {"error": str(e)}
    
    def generate_eda_report(self, output_path: str, target_column: Optional[str] = None,
                           include_ai_insights: bool = True) -> bool:
        """Generate comprehensive EDA report"""
        try:
            # Perform comprehensive EDA if not cached
            if "complete_eda" not in self.analysis_cache:
                eda_results = self.perform_comprehensive_eda(target_column, include_ai_insights)
            else:
                eda_results = self.analysis_cache["complete_eda"]
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(eda_results, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"EDA report saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating EDA report: {e}")
            return False
    
    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """Get history of analyses performed"""
        return self.analysis_history
    
    def clear_cache(self) -> None:
        """Clear analysis cache"""
        self.analysis_cache.clear()
        logger.info("Analysis cache cleared")

# Convenience functions
def perform_eda(file_path: str, target_column: Optional[str] = None, 
               output_path: Optional[str] = None, include_ai_insights: bool = True) -> Dict[str, Any]:
    """
    Convenience function to perform comprehensive EDA
    
    Args:
        file_path: Path to data file
        target_column: Target variable for analysis
        output_path: Optional path to save report
        include_ai_insights: Whether to include AI insights
        
    Returns:
        EDA results
    """
    eda_service = DataEDAService(file_path=file_path)
    results = eda_service.perform_comprehensive_eda(target_column, include_ai_insights)
    
    if output_path:
        eda_service.generate_eda_report(output_path, target_column, include_ai_insights)
    
    return results

def get_data_insights(file_path: str, target_column: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to get quick data insights
    
    Args:
        file_path: Path to data file
        target_column: Target variable for analysis
        
    Returns:
        Quick insights
    """
    eda_service = DataEDAService(file_path=file_path)
    return eda_service.get_quick_insights(target_column)