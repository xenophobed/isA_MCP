#!/usr/bin/env python3
"""
AI Enhanced Data Analysis Demo
Demonstrates the intelligent, AI-powered analysis capabilities
"""

import asyncio
import json
from datetime import datetime
from typing import Optional

# Import the enhanced services
try:
    from tools.services.data_analytics_service.services.data_service.data_eda import DataEDAService
    from tools.services.data_analytics_service.services.data_service.data_modeling import DataModelingService
    from tools.services.data_analytics_service.processors.data_processors.ai_analysis_engine import AIAnalysisEngine
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory")
    exit(1)

class AIEnhancedAnalysisDemo:
    """Demonstrate AI-enhanced analysis capabilities"""
    
    def __init__(self, csv_file_path: str):
        self.csv_file_path = csv_file_path
        self.ai_engine = AIAnalysisEngine()
    
    async def demonstrate_intelligent_eda(self, target_column: Optional[str] = None):
        """Demonstrate AI-enhanced EDA"""
        print("🔍 Starting AI-Enhanced Exploratory Data Analysis...")
        print("=" * 60)
        
        try:
            # Initialize EDA service
            eda_service = DataEDAService(file_path=self.csv_file_path)
            
            # Phase 1: Generate intelligent analysis strategy
            print("📋 Phase 1: Generating AI Analysis Strategy...")
            data_summary = {
                "shape": {"rows": len(eda_service.csv_processor.df), "columns": len(eda_service.csv_processor.df.columns)},
                "column_types": {
                    "numeric": len(eda_service.csv_processor.df.select_dtypes(include=['number']).columns),
                    "categorical": len(eda_service.csv_processor.df.select_dtypes(include=['object', 'category']).columns)
                }
            }
            
            strategy = await self.ai_engine.generate_analysis_strategy(
                data_summary, 
                business_context="E-commerce dataset analysis for customer insights"
            )
            
            if "analysis_strategy" in strategy:
                print("✅ AI Analysis Strategy Generated:")
                print(strategy["analysis_strategy"][:500] + "..." if len(strategy["analysis_strategy"]) > 500 else strategy["analysis_strategy"])
                print()
            
            # Phase 2: Perform comprehensive EDA with AI insights
            print("🧠 Phase 2: Performing AI-Enhanced EDA...")
            eda_results = eda_service.perform_comprehensive_eda(
                target_column=target_column,
                include_ai_insights=True
            )
            
            # Display AI insights
            if "insights_and_recommendations" in eda_results and "ai_insights" in eda_results["insights_and_recommendations"]:
                ai_insights = eda_results["insights_and_recommendations"]["ai_insights"]
                
                print("🎯 AI-Generated Data Story:")
                if "intelligent_data_story" in ai_insights:
                    story = ai_insights["intelligent_data_story"]
                    print(story[:800] + "..." if len(story) > 800 else story)
                    print()
                
                if target_column and "advanced_modeling_strategy" in ai_insights:
                    print("🚀 AI Modeling Strategy:")
                    strategy = ai_insights["advanced_modeling_strategy"]
                    print(strategy[:600] + "..." if len(strategy) > 600 else strategy)
                    print()
            
            # Phase 3: Intelligent result interpretation
            print("🔬 Phase 3: AI Result Interpretation...")
            interpretation = await self.ai_engine.interpret_analysis_results(
                eda_results,
                business_questions=[
                    "What are the key drivers of customer behavior?",
                    "Which data quality issues need immediate attention?",
                    "What patterns suggest business opportunities?"
                ]
            )
            
            if "business_interpretation" in interpretation:
                print("💡 AI Business Interpretation:")
                interp = interpretation["business_interpretation"]
                print(interp[:700] + "..." if len(interp) > 700 else interp)
                print()
            
            # Phase 4: Generate testable hypotheses
            print("🧪 Phase 4: Generating Testable Hypotheses...")
            hypothesis_framework = await self.ai_engine.generate_hypothesis_framework(
                data_summary,
                domain_context="E-commerce customer analytics"
            )
            
            if "hypothesis_framework" in hypothesis_framework:
                print("🔍 AI-Generated Hypothesis Framework:")
                framework = hypothesis_framework["hypothesis_framework"]
                print(framework[:600] + "..." if len(framework) > 600 else framework)
                print()
            
            return eda_results
            
        except Exception as e:
            print(f"❌ Error in AI-enhanced EDA: {e}")
            return None
    
    async def demonstrate_intelligent_modeling(self, target_column: str):
        """Demonstrate AI-enhanced modeling"""
        print("🤖 Starting AI-Enhanced Machine Learning...")
        print("=" * 60)
        
        try:
            # Initialize modeling service
            modeling_service = DataModelingService(file_path=self.csv_file_path)
            
            # Phase 1: AI-guided model development
            print("🚀 Phase 1: AI-Guided Model Development...")
            model_results = modeling_service.develop_model(
                target_column=target_column,
                include_feature_engineering=True,
                include_ai_guidance=True
            )
            
            # Display AI guidance
            if "ai_guidance" in model_results:
                ai_guidance = model_results["ai_guidance"]
                
                if "comprehensive_strategy" in ai_guidance:
                    print("📊 AI Comprehensive Strategy:")
                    strategy = ai_guidance["comprehensive_strategy"]
                    print(strategy[:700] + "..." if len(strategy) > 700 else strategy)
                    print()
                
                if "production_architecture" in ai_guidance:
                    print("🏗️ AI Production Architecture Advice:")
                    architecture = ai_guidance["production_architecture"]
                    print(architecture[:600] + "..." if len(architecture) > 600 else architecture)
                    print()
            
            # Phase 2: Advanced analysis suggestions
            print("🔬 Phase 2: AI Advanced Analysis Suggestions...")
            advanced_suggestions = await self.ai_engine.suggest_advanced_analyses(
                model_results,
                target_column=target_column
            )
            
            if "advanced_analysis_suggestions" in advanced_suggestions:
                print("💡 AI Advanced Analysis Suggestions:")
                suggestions = advanced_suggestions["advanced_analysis_suggestions"]
                print(suggestions[:700] + "..." if len(suggestions) > 700 else suggestions)
                print()
            
            # Display model performance summary
            if "model_evaluation" in model_results:
                evaluation = model_results["model_evaluation"]
                if "best_model" in evaluation:
                    best = evaluation["best_model"]
                    print(f"🏆 Best Model: {best.get('algorithm', 'Unknown')}")
                    
                    metrics = best.get("performance_metrics", {})
                    if metrics:
                        print("📈 Performance Metrics:")
                        for metric, value in metrics.items():
                            if isinstance(value, (int, float)):
                                print(f"  • {metric}: {value:.4f}")
                        print()
            
            return model_results
            
        except Exception as e:
            print(f"❌ Error in AI-enhanced modeling: {e}")
            return None
    
    async def demonstrate_full_ai_workflow(self, target_column: Optional[str] = None):
        """Demonstrate complete AI-enhanced workflow"""
        print("🌟 AI-Enhanced Data Science Workflow Demo")
        print("=" * 80)
        print(f"📁 Dataset: {self.csv_file_path}")
        print(f"🎯 Target: {target_column or 'Exploratory Analysis'}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # EDA Phase
        eda_results = await self.demonstrate_intelligent_eda(target_column)
        
        # Modeling Phase (if target specified)
        if target_column and eda_results:
            print("\n" + "=" * 80)
            model_results = await self.demonstrate_intelligent_modeling(target_column)
            
            # Save comprehensive results
            if model_results:
                output_file = f"ai_enhanced_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                comprehensive_results = {
                    "workflow_metadata": {
                        "dataset": self.csv_file_path,
                        "target_column": target_column,
                        "completion_time": datetime.now().isoformat(),
                        "ai_enhanced": True
                    },
                    "eda_results": eda_results,
                    "modeling_results": model_results
                }
                
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(comprehensive_results, f, indent=2, ensure_ascii=False, default=str)
                    
                    print(f"💾 Complete results saved to: {output_file}")
                except Exception as e:
                    print(f"⚠️ Could not save results: {e}")
        
        print("\n✨ AI-Enhanced Analysis Complete!")
        print("=" * 80)

# Example usage functions
async def demo_with_sample_data():
    """Demo with sample data (you would replace with actual CSV path)"""
    
    # For demo purposes - you would replace this with actual data path
    sample_csv_path = "/path/to/your/data.csv"  # Replace with actual path
    
    print("🚀 AI-Enhanced Data Analytics Demo")
    print("Note: Please replace 'sample_csv_path' with actual CSV file path")
    
    demo = AIEnhancedAnalysisDemo(sample_csv_path)
    
    try:
        # Demo exploratory analysis
        await demo.demonstrate_full_ai_workflow(target_column="target_column_name")  # Replace with actual target
    except Exception as e:
        print(f"Demo error: {e}")
        print("Please ensure:")
        print("1. CSV file path is correct")
        print("2. Target column name exists in the data")
        print("3. TextGenerator service is available")

def show_ai_enhancement_features():
    """Show what AI enhancements are available"""
    print("🧠 AI Enhancement Features:")
    print("=" * 50)
    print("✅ Intelligent Analysis Strategy Generation")
    print("✅ Dynamic Data Story Creation")
    print("✅ Business-Focused Insight Interpretation")
    print("✅ Advanced Modeling Strategy Recommendations")
    print("✅ Production Architecture Guidance")
    print("✅ Hypothesis Framework Generation")
    print("✅ Advanced Analysis Suggestions")
    print("✅ Context-Aware Business Recommendations")
    print()
    print("🔧 Technical Improvements:")
    print("✅ Async AI Integration with proper error handling")
    print("✅ Comprehensive data profiling for AI context")
    print("✅ Structured prompts for consistent AI responses")
    print("✅ Business context integration throughout analysis")
    print("✅ Multi-temperature AI generation for different use cases")
    print()

if __name__ == "__main__":
    print("AI-Enhanced Data Analytics System")
    print("=" * 40)
    
    show_ai_enhancement_features()
    
    print("To run the demo:")
    print("1. Update 'sample_csv_path' with your CSV file path")
    print("2. Update 'target_column_name' with your target column")
    print("3. Ensure TextGenerator service is available")
    print("4. Run: python demo_ai_enhanced_analysis.py")
    print()
    print("Example:")
    print("```python")
    print("demo = AIEnhancedAnalysisDemo('/path/to/sales_data.csv')")
    print("await demo.demonstrate_full_ai_workflow('revenue')")
    print("```")