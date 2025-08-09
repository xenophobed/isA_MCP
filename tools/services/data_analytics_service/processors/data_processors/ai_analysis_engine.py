#!/usr/bin/env python3
"""
AI Analysis Engine
Dynamic analysis strategy generation using AI to interpret data patterns
and guide analysis workflows intelligently.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
import json

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
        logging.warning("TextGenerator not available. AI analysis engine will be disabled.")

logger = logging.getLogger(__name__)

class AIAnalysisEngine:
    """
    AI-powered analysis engine that dynamically determines analysis strategies
    based on data characteristics and business context
    """
    
    def __init__(self):
        self.text_generator = None
        if TEXT_GENERATOR_AVAILABLE:
            try:
                self.text_generator = TextGenerator()
            except Exception as e:
                logger.warning(f"Could not initialize TextGenerator: {e}")
    
    async def generate_analysis_strategy(self, data_summary: Dict[str, Any], 
                                       business_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate intelligent analysis strategy based on data characteristics
        
        Args:
            data_summary: Summary of data characteristics
            business_context: Optional business context description
            
        Returns:
            Comprehensive analysis strategy
        """
        if not self.text_generator:
            return {"error": "TextGenerator not available"}
        
        try:
            # Create comprehensive data profile for AI
            data_profile = self._create_data_profile(data_summary)
            
            strategy_prompt = f"""
            You are a senior data scientist tasked with designing an optimal analysis strategy. 
            Analyze this data profile and create a comprehensive analysis plan:

            {data_profile}
            
            {f"Business Context: {business_context}" if business_context else ""}

            Design a strategic analysis approach covering:

            1. **Data Understanding Phase**:
               - Which data aspects require the deepest investigation?
               - What hidden patterns should we look for?
               - Which columns are likely to be most informative?

            2. **Quality Assessment Strategy**:
               - What are the most critical quality issues to address first?
               - Which quality dimensions need special attention?
               - How should we prioritize quality improvements?

            3. **Statistical Analysis Focus**:
               - Which statistical tests would be most revealing?
               - What correlation patterns should we investigate?
               - Which distribution analyses would be most valuable?

            4. **Feature Engineering Approach**:
               - What feature transformations would likely improve model performance?
               - Which feature interactions should be explored?
               - How should we handle categorical variables optimally?

            5. **Modeling Strategy**:
               - Which ML approaches would be most suitable?
               - What are the key preprocessing requirements?
               - How should we validate model performance?

            6. **Business Impact Analysis**:
               - What insights would be most valuable to stakeholders?
               - Which findings could drive immediate action?
               - How should results be communicated effectively?

            Provide specific, actionable recommendations with reasoning for each suggestion.
            Consider both technical excellence and business value.
            """
            
            strategy_response = await self.text_generator.generate(
                strategy_prompt, 
                temperature=0.6, 
                max_tokens=3000
            )
            
            return {
                "analysis_strategy": strategy_response,
                "generated_at": datetime.now().isoformat(),
                "data_profile_used": data_profile[:500] + "..." if len(data_profile) > 500 else data_profile
            }
            
        except Exception as e:
            logger.error(f"Error generating analysis strategy: {e}")
            return {"error": str(e)}
    
    async def interpret_analysis_results(self, analysis_results: Dict[str, Any], 
                                       business_questions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        AI interpretation of analysis results with business insights
        
        Args:
            analysis_results: Complete analysis results
            business_questions: Optional list of specific business questions
            
        Returns:
            AI interpretation and insights
        """
        if not self.text_generator:
            return {"error": "TextGenerator not available"}
        
        try:
            # Summarize key findings for AI interpretation
            findings_summary = self._summarize_key_findings(analysis_results)
            
            interpretation_prompt = f"""
            You are a senior data consultant interpreting analysis results for business stakeholders.
            
            Analysis Results Summary:
            {findings_summary}
            
            {f"Specific Business Questions: {json.dumps(business_questions, indent=2)}" if business_questions else ""}

            Provide expert interpretation covering:

            1. **Executive Summary**:
               - What are the 3 most important discoveries?
               - What do these findings mean for the business?
               - Which insights require immediate attention?

            2. **Deep Insights**:
               - What story does the data tell about the underlying business process?
               - Which patterns might indicate opportunities or risks?
               - What correlations suggest actionable relationships?

            3. **Anomaly Interpretation**:
               - What might explain any unusual patterns or outliers?
               - Are there data quality issues that mask true business patterns?
               - Which anomalies are likely data errors vs. genuine business insights?

            4. **Predictive Insights**:
               - What trends or patterns suggest future outcomes?
               - Which variables are likely to be most predictive?
               - What scenarios should the business prepare for?

            5. **Actionable Recommendations**:
               - What immediate actions should be taken based on these findings?
               - Which areas need further investigation?
               - How should the business process or strategy be adjusted?

            6. **Risk Assessment**:
               - What risks do these findings highlight?
               - Which data quality issues could impact decision-making?
               - What assumptions should be validated?

            Structure your response for business stakeholders who need both high-level insights 
            and detailed reasoning. Be specific about confidence levels and limitations.
            """
            
            interpretation_response = await self.text_generator.generate(
                interpretation_prompt,
                temperature=0.7,
                max_tokens=3500
            )
            
            return {
                "business_interpretation": interpretation_response,
                "interpreted_at": datetime.now().isoformat(),
                "business_questions_addressed": business_questions or []
            }
            
        except Exception as e:
            logger.error(f"Error interpreting analysis results: {e}")
            return {"error": str(e)}
    
    async def generate_hypothesis_framework(self, data_profile: Dict[str, Any], 
                                          domain_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate testable hypotheses based on data characteristics
        
        Args:
            data_profile: Data characteristics profile
            domain_context: Business domain context
            
        Returns:
            Framework of testable hypotheses
        """
        if not self.text_generator:
            return {"error": "TextGenerator not available"}
        
        try:
            profile_summary = self._create_data_profile(data_profile)
            
            hypothesis_prompt = f"""
            You are a research scientist designing hypotheses to test with this dataset.
            
            Data Profile:
            {profile_summary}
            
            {f"Domain Context: {domain_context}" if domain_context else ""}

            Generate a comprehensive hypothesis framework:

            1. **Primary Hypotheses** (Most testable with current data):
               - What are 5 specific, testable hypotheses about relationships in this data?
               - Which variables are most likely to show significant relationships?
               - What causal relationships might exist?

            2. **Exploratory Hypotheses** (For deeper investigation):
               - What patterns might emerge from segment analysis?
               - Which temporal relationships should be investigated?
               - What interaction effects might be present?

            3. **Quality Hypotheses** (About data generation process):
               - What might explain missing data patterns?
               - Which data collection biases might be present?
               - What external factors might influence data quality?

            4. **Business Impact Hypotheses**:
               - Which variables likely drive key business outcomes?
               - What operational factors might influence performance?
               - Which customer/product segments might behave differently?

            5. **Statistical Testing Plan**:
               - Which statistical tests would be most appropriate for each hypothesis?
               - What sample size considerations apply?
               - How should significance levels be adjusted for multiple testing?

            For each hypothesis, provide:
            - Clear, testable statement
            - Expected outcome and reasoning
            - Suggested testing approach
            - Business implications if confirmed/rejected

            Focus on hypotheses that could drive actionable business insights.
            """
            
            hypothesis_response = await self.text_generator.generate(
                hypothesis_prompt,
                temperature=0.8,
                max_tokens=3000
            )
            
            return {
                "hypothesis_framework": hypothesis_response,
                "generated_at": datetime.now().isoformat(),
                "domain_context": domain_context
            }
            
        except Exception as e:
            logger.error(f"Error generating hypothesis framework: {e}")
            return {"error": str(e)}
    
    async def suggest_advanced_analyses(self, current_analysis: Dict[str, Any],
                                      target_column: Optional[str] = None) -> Dict[str, Any]:
        """
        Suggest advanced analytical techniques based on initial analysis
        
        Args:
            current_analysis: Results from initial analysis
            target_column: Target variable if predictive modeling is the goal
            
        Returns:
            Advanced analysis suggestions
        """
        if not self.text_generator:
            return {"error": "TextGenerator not available"}
        
        try:
            analysis_summary = self._summarize_current_analysis(current_analysis)
            
            advanced_prompt = f"""
            You are an advanced analytics expert reviewing initial analysis results.
            Based on these findings, recommend sophisticated analytical approaches:

            Current Analysis Summary:
            {analysis_summary}
            
            {f"Target Variable: {target_column}" if target_column else "Exploratory analysis (no target specified)"}

            Recommend advanced analytical techniques:

            1. **Advanced Statistical Methods**:
               - Which multivariate techniques would reveal deeper insights?
               - What time series analyses might be valuable?
               - Which non-parametric methods should be considered?

            2. **Machine Learning Approaches**:
               - What unsupervised learning techniques could uncover hidden patterns?
               - Which ensemble methods might improve predictive performance?
               - What deep learning approaches might be applicable?

            3. **Specialized Analyses**:
               - Would survival analysis, causal inference, or network analysis be valuable?
               - What domain-specific analytical techniques should be considered?
               - Which simulation or optimization approaches might help?

            4. **Feature Engineering Innovations**:
               - What advanced feature engineering techniques could improve results?
               - Which dimensionality reduction methods might be helpful?
               - How could external data sources enhance the analysis?

            5. **Validation and Testing Strategies**:
               - What cross-validation approaches would be most rigorous?
               - How should model stability and robustness be tested?
               - What sensitivity analyses would be most informative?

            6. **Implementation Roadmap**:
               - Which advanced techniques should be prioritized?
               - What tools and resources would be required?
               - How should results be validated and communicated?

            For each suggestion, provide:
            - Specific methodology recommendation
            - Expected benefits and insights
            - Implementation complexity estimate
            - Resource requirements

            Focus on techniques that could significantly advance understanding beyond basic analysis.
            """
            
            advanced_response = await self.text_generator.generate(
                advanced_prompt,
                temperature=0.7,
                max_tokens=3500
            )
            
            return {
                "advanced_analysis_suggestions": advanced_response,
                "generated_at": datetime.now().isoformat(),
                "based_on_analysis": "current_analysis_results"
            }
            
        except Exception as e:
            logger.error(f"Error generating advanced analysis suggestions: {e}")
            return {"error": str(e)}
    
    def _create_data_profile(self, data_summary: Dict[str, Any]) -> str:
        """Create a comprehensive data profile for AI analysis"""
        try:
            profile_sections = []
            
            # Basic characteristics
            if "shape" in data_summary:
                shape = data_summary["shape"]
                profile_sections.append(f"Dataset Size: {shape.get('rows', 0):,} rows × {shape.get('columns', 0)} columns")
            
            # Column types
            if "column_types" in data_summary:
                types = data_summary["column_types"]
                profile_sections.append(f"Column Types: {types.get('numeric', 0)} numeric, {types.get('categorical', 0)} categorical, {types.get('datetime', 0)} datetime")
            
            # Data quality indicators
            if "quality_indicators" in data_summary:
                quality = data_summary["quality_indicators"]
                profile_sections.append(f"Quality: {quality.get('missing_percentage', 0):.1f}% missing, {quality.get('duplicate_percentage', 0):.1f}% duplicates")
            
            # Statistical summaries
            if "statistical_summary" in data_summary:
                stats = data_summary["statistical_summary"]
                if "correlations" in stats:
                    max_corr = stats["correlations"].get("max_correlation", 0)
                    profile_sections.append(f"Max correlation: {max_corr:.3f}")
                
                if "distributions" in stats:
                    dist = stats["distributions"]
                    profile_sections.append(f"Distributions: {dist.get('normal_count', 0)} normal, {dist.get('skewed_count', 0)} skewed")
            
            # Target information
            if "target_info" in data_summary:
                target = data_summary["target_info"]
                profile_sections.append(f"Target: {target.get('name', 'N/A')} ({target.get('type', 'unknown')})")
            
            return "\n".join(profile_sections)
            
        except Exception as e:
            logger.error(f"Error creating data profile: {e}")
            return "Data profile creation failed"
    
    def _summarize_key_findings(self, analysis_results: Dict[str, Any]) -> str:
        """Summarize key findings from analysis results"""
        try:
            summary_parts = []
            
            # Data quality findings
            if "data_quality_assessment" in analysis_results:
                quality = analysis_results["data_quality_assessment"]
                if "overview" in quality:
                    score = quality["overview"].get("overall_quality_score", 0)
                    grade = quality["overview"].get("quality_grade", "Unknown")
                    summary_parts.append(f"Data Quality: {score:.2f}/1.0 ({grade})")
            
            # Statistical findings
            if "statistical_analysis" in analysis_results:
                stats = analysis_results["statistical_analysis"]
                if "correlation_analysis" in stats:
                    corr = stats["correlation_analysis"]
                    if "strongest_correlation" in corr:
                        strongest = corr["strongest_correlation"]
                        summary_parts.append(f"Strongest correlation: {strongest.get('correlation', 0):.3f}")
            
            # Feature analysis findings
            if "feature_analysis" in analysis_results:
                features = analysis_results["feature_analysis"]
                if "feature_types" in features:
                    types = features["feature_types"]
                    summary_parts.append(f"Features: {types.get('total_features', 0)} total")
            
            # Model performance (if available)
            if "model_evaluation" in analysis_results:
                model = analysis_results["model_evaluation"]
                if "best_model" in model:
                    best = model["best_model"]
                    algo = best.get("algorithm", "Unknown")
                    summary_parts.append(f"Best model: {algo}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error summarizing findings: {e}")
            return "Findings summary failed"
    
    def _summarize_current_analysis(self, analysis: Dict[str, Any]) -> str:
        """Summarize current analysis for advanced suggestions"""
        try:
            summary = []
            
            # Analysis type and scope
            if "analysis_metadata" in analysis:
                metadata = analysis["analysis_metadata"]
                summary.append(f"Analysis completed at: {metadata.get('timestamp', 'Unknown')}")
                summary.append(f"Data shape: {metadata.get('data_shape', 'Unknown')}")
            
            # Key results achieved
            if "insights_and_recommendations" in analysis:
                insights = analysis["insights_and_recommendations"]
                if "key_findings" in insights:
                    findings = insights["key_findings"]
                    summary.append(f"Key findings: {len(findings)} insights generated")
            
            # Current analytical depth
            analysis_types = []
            if "statistical_analysis" in analysis:
                analysis_types.append("Statistical analysis")
            if "data_quality_assessment" in analysis:
                analysis_types.append("Quality assessment")
            if "feature_analysis" in analysis:
                analysis_types.append("Feature analysis")
            
            if analysis_types:
                summary.append(f"Completed analyses: {', '.join(analysis_types)}")
            
            return "\n".join(summary)
            
        except Exception as e:
            logger.error(f"Error summarizing current analysis: {e}")
            return "Current analysis summary failed"

# Convenience functions for easy integration
async def generate_smart_analysis_strategy(data_summary: Dict[str, Any], 
                                         business_context: Optional[str] = None) -> Dict[str, Any]:
    """Generate intelligent analysis strategy"""
    engine = AIAnalysisEngine()
    return await engine.generate_analysis_strategy(data_summary, business_context)

async def interpret_results_intelligently(analysis_results: Dict[str, Any],
                                        business_questions: Optional[List[str]] = None) -> Dict[str, Any]:
    """Get AI interpretation of analysis results"""
    engine = AIAnalysisEngine()
    return await engine.interpret_analysis_results(analysis_results, business_questions)