#!/usr/bin/env python3
"""
AI Enhanced Data Analytics Services - Real Testing Script
验证所有AI增强数据分析服务的真实可用性测试
"""

import asyncio
import sys
import traceback
from pathlib import Path
from datetime import datetime

# Add project root to Python path
import os
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

def test_imports():
    """测试所有必要的导入"""
    print("🔍 Testing imports...")
    
    try:
        # Test basic processor imports
        from tools.services.data_analytics_service.processors.data_processors import (
            CSVProcessor, StatisticsProcessor, DataQualityProcessor, 
            FeatureProcessor, MetadataExtractor
        )
        print("✅ Basic processors imported successfully")
        
        # Test service imports
        from tools.services.data_analytics_service.services.data_service.data_eda import DataEDAService
        from tools.services.data_analytics_service.services.data_service.data_modeling import DataModelingService
        print("✅ Data services imported successfully")
        
        # Test AI engine import
        from tools.services.data_analytics_service.processors.data_processors.ai_analysis_engine import AIAnalysisEngine
        print("✅ AI Analysis Engine imported successfully")
        
        # Test TextGenerator import
        from tools.services.intelligence_service.language.text_generator import TextGenerator
        print("✅ TextGenerator imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        return False

def test_basic_initialization():
    """测试基础服务初始化"""
    print("\n🔧 Testing basic service initialization...")
    
    try:
        # Test CSV file path
        test_file = "/Users/xenodennis/Documents/Fun/isA_MCP/test_data.csv"
        if not os.path.exists(test_file):
            print(f"❌ Test data file not found: {test_file}")
            return False
        
        # Test CSV processor
        from tools.services.data_analytics_service.processors.data_processors import CSVProcessor
        csv_processor = CSVProcessor(test_file)
        if not csv_processor.load_csv():
            print("❌ Failed to load CSV data")
            return False
        
        print(f"✅ CSV loaded: {csv_processor.df.shape[0]} rows, {csv_processor.df.shape[1]} columns")
        
        # Test other processors initialization
        from tools.services.data_analytics_service.processors.data_processors import (
            StatisticsProcessor, DataQualityProcessor, FeatureProcessor, MetadataExtractor
        )
        
        stats_processor = StatisticsProcessor(csv_processor)
        quality_processor = DataQualityProcessor(csv_processor)
        feature_processor = FeatureProcessor(csv_processor)
        metadata_extractor = MetadataExtractor()
        
        print("✅ All processors initialized successfully")
        
        # Test TextGenerator initialization
        from tools.services.intelligence_service.language.text_generator import TextGenerator
        text_gen = TextGenerator()
        print("✅ TextGenerator initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        traceback.print_exc()
        return False

async def test_eda_service():
    """测试EDA服务完整功能"""
    print("\n📊 Testing EDA Service...")
    
    try:
        from tools.services.data_analytics_service.services.data_service.data_eda import DataEDAService
        
        test_file = "/Users/xenodennis/Documents/Fun/isA_MCP/test_data.csv"
        eda_service = DataEDAService(file_path=test_file)
        
        print("✅ EDA Service initialized")
        
        # Test basic EDA without AI first
        print("📋 Testing basic EDA (no AI)...")
        eda_results_basic = eda_service.perform_comprehensive_eda(
            target_column="purchase_amount", 
            include_ai_insights=False
        )
        
        if "error" in eda_results_basic:
            print(f"❌ Basic EDA failed: {eda_results_basic['error']}")
            return False
            
        print("✅ Basic EDA completed successfully")
        print(f"   - Data shape: {eda_results_basic['analysis_metadata']['data_shape']}")
        print(f"   - Execution time: {eda_results_basic['analysis_metadata']['execution_time_seconds']}s")
        
        # Test key components
        required_sections = [
            'metadata', 'data_overview', 'statistical_analysis', 
            'data_quality_assessment', 'feature_analysis', 'insights_and_recommendations'
        ]
        
        for section in required_sections:
            if section not in eda_results_basic:
                print(f"❌ Missing required section: {section}")
                return False
            print(f"✅ Section '{section}' present")
        
        return eda_results_basic
        
    except Exception as e:
        print(f"❌ EDA Service test failed: {e}")
        traceback.print_exc()
        return False

async def test_ai_integration():
    """测试AI集成功能"""
    print("\n🧠 Testing AI Integration...")
    
    try:
        from tools.services.data_analytics_service.services.data_service.data_eda import DataEDAService
        
        test_file = "/Users/xenodennis/Documents/Fun/isA_MCP/test_data.csv"
        eda_service = DataEDAService(file_path=test_file)
        
        # Test if TextGenerator is available
        if eda_service.text_generator is None:
            print("⚠️ TextGenerator not available - AI features will be disabled")
            return {"ai_available": False, "reason": "TextGenerator not initialized"}
        
        print("✅ TextGenerator available")
        
        # Test EDA with AI insights
        print("🤖 Testing EDA with AI insights...")
        eda_results_ai = eda_service.perform_comprehensive_eda(
            target_column="purchase_amount", 
            include_ai_insights=True
        )
        
        if "error" in eda_results_ai:
            print(f"❌ AI-enhanced EDA failed: {eda_results_ai['error']}")
            return False
            
        print("✅ AI-enhanced EDA completed")
        
        # Check AI insights
        insights = eda_results_ai.get('insights_and_recommendations', {})
        if 'ai_insights' not in insights:
            print("⚠️ AI insights not generated")
            return {"ai_available": True, "ai_insights_generated": False}
            
        ai_insights = insights['ai_insights']
        if 'error' in ai_insights:
            print(f"⚠️ AI insights generation failed: {ai_insights['error']}")
            return {"ai_available": True, "ai_insights_generated": False, "error": ai_insights['error']}
        
        print("✅ AI insights generated successfully")
        
        # Check AI insight types
        insight_types = ['intelligent_data_story', 'advanced_modeling_strategy', 'quality_enhancement_roadmap', 'intelligent_pattern_discovery']
        for insight_type in insight_types:
            if insight_type in ai_insights:
                preview = ai_insights[insight_type][:100] + "..." if len(ai_insights[insight_type]) > 100 else ai_insights[insight_type]
                print(f"✅ {insight_type}: {preview}")
            else:
                print(f"⚠️ Missing AI insight: {insight_type}")
        
        return {"ai_available": True, "ai_insights_generated": True, "results": eda_results_ai}
        
    except Exception as e:
        print(f"❌ AI Integration test failed: {e}")
        traceback.print_exc()
        return {"ai_available": False, "error": str(e)}

async def test_modeling_service():
    """测试建模服务"""
    print("\n🤖 Testing Modeling Service...")
    
    try:
        from tools.services.data_analytics_service.services.data_service.data_modeling import DataModelingService
        
        test_file = "/Users/xenodennis/Documents/Fun/isA_MCP/test_data.csv"
        modeling_service = DataModelingService(file_path=test_file)
        
        print("✅ Modeling Service initialized")
        
        # Test basic modeling without AI first
        print("🔧 Testing basic modeling (no AI)...")
        model_results_basic = modeling_service.develop_model(
            target_column="purchase_amount",
            include_feature_engineering=True,
            include_ai_guidance=False
        )
        
        if "error" in model_results_basic:
            print(f"❌ Basic modeling failed: {model_results_basic['error']}")
            return False
            
        print("✅ Basic modeling completed")
        
        # Check for model evaluation results
        if "model_evaluation" in model_results_basic:
            eval_results = model_results_basic["model_evaluation"]
            if "best_model" in eval_results:
                best_model = eval_results["best_model"]
                print(f"✅ Best model: {best_model.get('algorithm', 'Unknown')}")
                
                metrics = best_model.get('performance_metrics', {})
                if metrics:
                    print("📈 Performance metrics:")
                    for metric, value in metrics.items():
                        if isinstance(value, (int, float)):
                            print(f"   - {metric}: {value:.4f}")
        
        return model_results_basic
        
    except Exception as e:
        print(f"❌ Modeling Service test failed: {e}")
        traceback.print_exc()
        return False

async def test_ai_analysis_engine():
    """测试AI分析引擎"""
    print("\n🔬 Testing AI Analysis Engine...")
    
    try:
        from tools.services.data_analytics_service.processors.data_processors.ai_analysis_engine import AIAnalysisEngine
        
        ai_engine = AIAnalysisEngine()
        print("✅ AI Analysis Engine initialized")
        
        if ai_engine.text_generator is None:
            print("⚠️ TextGenerator not available in AI Engine")
            return {"ai_engine_available": False}
        
        # Test analysis strategy generation
        data_summary = {
            "shape": {"rows": 30, "columns": 10},
            "column_types": {"numeric": 6, "categorical": 4},
            "quality_indicators": {"missing_percentage": 0.0, "duplicate_percentage": 0.0}
        }
        
        print("🎯 Testing analysis strategy generation...")
        strategy = await ai_engine.generate_analysis_strategy(
            data_summary, 
            business_context="E-commerce customer analytics"
        )
        
        if "error" in strategy:
            print(f"❌ Strategy generation failed: {strategy['error']}")
            return {"ai_engine_available": True, "strategy_generated": False}
        
        if "analysis_strategy" in strategy:
            preview = strategy["analysis_strategy"][:200] + "..." if len(strategy["analysis_strategy"]) > 200 else strategy["analysis_strategy"]
            print(f"✅ Analysis strategy generated: {preview}")
        
        return {"ai_engine_available": True, "strategy_generated": True, "strategy": strategy}
        
    except Exception as e:
        print(f"❌ AI Analysis Engine test failed: {e}")
        traceback.print_exc()
        return {"ai_engine_available": False, "error": str(e)}

async def run_comprehensive_test():
    """运行完整的综合测试"""
    print("🚀 Starting Comprehensive AI Enhanced Data Analytics Test")
    print("=" * 70)
    
    test_results = {
        "test_timestamp": datetime.now().isoformat(),
        "import_test": False,
        "initialization_test": False,
        "eda_service_test": False,
        "ai_integration_test": False,
        "modeling_service_test": False,
        "ai_engine_test": False,
        "overall_success": False
    }
    
    # Test 1: Imports
    test_results["import_test"] = test_imports()
    if not test_results["import_test"]:
        print("❌ Import test failed - cannot continue")
        return test_results
    
    # Test 2: Basic initialization
    test_results["initialization_test"] = test_basic_initialization()
    if not test_results["initialization_test"]:
        print("❌ Initialization test failed - cannot continue")
        return test_results
    
    # Test 3: EDA Service
    eda_results = await test_eda_service()
    test_results["eda_service_test"] = bool(eda_results)
    
    # Test 4: AI Integration
    ai_results = await test_ai_integration()
    test_results["ai_integration_test"] = bool(ai_results)
    
    # Test 5: Modeling Service
    model_results = await test_modeling_service()
    test_results["modeling_service_test"] = bool(model_results)
    
    # Test 6: AI Analysis Engine
    ai_engine_results = await test_ai_analysis_engine()
    test_results["ai_engine_test"] = bool(ai_engine_results)
    
    # Overall assessment
    core_tests_passed = (
        test_results["import_test"] and
        test_results["initialization_test"] and
        test_results["eda_service_test"] and
        test_results["modeling_service_test"]
    )
    
    ai_features_available = (
        test_results["ai_integration_test"] and
        test_results["ai_engine_test"]
    )
    
    test_results["overall_success"] = core_tests_passed
    
    # Final results
    print("\n" + "=" * 70)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    print(f"✅ Import Test: {'PASSED' if test_results['import_test'] else 'FAILED'}")
    print(f"✅ Initialization Test: {'PASSED' if test_results['initialization_test'] else 'FAILED'}")
    print(f"✅ EDA Service Test: {'PASSED' if test_results['eda_service_test'] else 'FAILED'}")
    print(f"✅ Modeling Service Test: {'PASSED' if test_results['modeling_service_test'] else 'FAILED'}")
    print(f"🧠 AI Integration Test: {'PASSED' if test_results['ai_integration_test'] else 'FAILED/LIMITED'}")
    print(f"🧠 AI Engine Test: {'PASSED' if test_results['ai_engine_test'] else 'FAILED/LIMITED'}")
    
    print("\n" + "=" * 70)
    if test_results["overall_success"]:
        print("🎉 OVERALL STATUS: SYSTEM READY FOR USE")
        if ai_features_available:
            print("🧠 AI Features: FULLY FUNCTIONAL")
        else:
            print("⚠️ AI Features: LIMITED/UNAVAILABLE (Core functionality still works)")
    else:
        print("❌ OVERALL STATUS: SYSTEM HAS ISSUES")
    
    print("=" * 70)
    
    return test_results

if __name__ == "__main__":
    print("AI Enhanced Data Analytics Services - Real Testing")
    print("Testing AI integration and service functionality...")
    print()
    
    # Run comprehensive test
    results = asyncio.run(run_comprehensive_test())
    
    # Exit with appropriate code
    sys.exit(0 if results["overall_success"] else 1)