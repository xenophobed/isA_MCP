#!/usr/bin/env python3
"""
AI Functionality Real Test
专门测试AI增强功能的真实可用性
"""

import asyncio
import sys
import os
import traceback
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

async def test_textgenerator_direct():
    """直接测试TextGenerator"""
    print("🧠 Testing TextGenerator directly...")
    
    try:
        from tools.services.intelligence_service.language.text_generator import TextGenerator
        
        text_gen = TextGenerator()
        print("✅ TextGenerator initialized")
        
        # Test simple generation
        test_prompt = "What is machine learning? Please explain in 2 sentences."
        print(f"🎯 Testing generation with prompt: {test_prompt}")
        
        response = await text_gen.generate(test_prompt, temperature=0.7, max_tokens=100)
        
        if response:
            print(f"✅ AI Response generated:")
            print(f"   Response: {response[:200]}{'...' if len(response) > 200 else ''}")
            return {"success": True, "response": response}
        else:
            print("❌ Empty response from TextGenerator")
            return {"success": False, "error": "Empty response"}
        
    except Exception as e:
        print(f"❌ TextGenerator test failed: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

async def test_ai_analysis_engine():
    """测试AI分析引擎"""
    print("\n🔬 Testing AI Analysis Engine...")
    
    try:
        from tools.services.data_analytics_service.processors.data_processors.ai_analysis_engine import AIAnalysisEngine
        
        ai_engine = AIAnalysisEngine()
        print("✅ AI Analysis Engine initialized")
        
        if not ai_engine.text_generator:
            print("❌ TextGenerator not available in AI Engine")
            return {"success": False, "error": "TextGenerator not available"}
        
        print("✅ TextGenerator available in AI Engine")
        
        # Test data summary
        data_summary = {
            "shape": {"rows": 30, "columns": 10},
            "column_types": {"numeric": 6, "categorical": 4, "datetime": 0},
            "quality_indicators": {
                "missing_percentage": 0.0, 
                "duplicate_percentage": 0.0
            },
            "target_info": {
                "name": "purchase_amount",
                "type": "numeric"
            }
        }
        
        print("🎯 Testing analysis strategy generation...")
        strategy = await ai_engine.generate_analysis_strategy(
            data_summary, 
            business_context="E-commerce customer analytics and purchase prediction"
        )
        
        if "error" in strategy:
            print(f"❌ Strategy generation failed: {strategy['error']}")
            return {"success": False, "error": strategy['error']}
        
        if "analysis_strategy" in strategy and strategy["analysis_strategy"]:
            print("✅ Analysis strategy generated successfully")
            preview = strategy["analysis_strategy"][:300] + "..." if len(strategy["analysis_strategy"]) > 300 else strategy["analysis_strategy"]
            print(f"   Strategy preview: {preview}")
            
            return {
                "success": True, 
                "strategy_generated": True,
                "strategy_length": len(strategy["analysis_strategy"]),
                "strategy_preview": preview
            }
        else:
            print("❌ Strategy generation returned empty result")
            return {"success": False, "error": "Empty strategy generated"}
        
    except Exception as e:
        print(f"❌ AI Analysis Engine test failed: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

async def test_eda_ai_integration():
    """测试EDA服务的AI集成"""
    print("\n📊 Testing EDA AI Integration...")
    
    try:
        from tools.services.data_analytics_service.services.data_service.data_eda import DataEDAService
        
        test_file = "/Users/xenodennis/Documents/Fun/isA_MCP/test_data.csv"
        eda_service = DataEDAService(file_path=test_file)
        
        print("✅ EDA Service initialized")
        
        if not eda_service.text_generator:
            print("❌ TextGenerator not available in EDA service")
            return {"success": False, "error": "TextGenerator not available"}
        
        print("✅ TextGenerator available in EDA service")
        
        # Test AI insights generation directly
        print("🧠 Testing AI insights generation...")
        
        # Create mock EDA results for AI insight generation
        mock_eda_results = {
            "data_overview": {
                "basic_info": {"rows": 30, "columns": 10},
                "column_types": {"numeric": 6, "categorical": 4},
                "missing_data": {"missing_percentage": 0.0}
            },
            "data_quality_assessment": {
                "overview": {"overall_quality_score": 0.95, "quality_grade": "A"}
            },
            "statistical_analysis": {
                "correlation_analysis": {
                    "strongest_correlation": {"correlation": 0.75, "variables": ["age", "income"]}
                }
            }
        }
        
        ai_insights = await eda_service._generate_ai_insights(mock_eda_results, "purchase_amount")
        
        if "error" in ai_insights:
            print(f"❌ AI insights generation failed: {ai_insights['error']}")
            return {"success": False, "error": ai_insights['error']}
        
        print("✅ AI insights generated successfully")
        
        # Check insight types
        insight_types = ['intelligent_data_story', 'advanced_modeling_strategy', 'quality_enhancement_roadmap', 'intelligent_pattern_discovery']
        generated_insights = []
        
        for insight_type in insight_types:
            if insight_type in ai_insights and ai_insights[insight_type]:
                generated_insights.append(insight_type)
                preview = ai_insights[insight_type][:150] + "..." if len(ai_insights[insight_type]) > 150 else ai_insights[insight_type]
                print(f"✅ {insight_type}: {preview}")
        
        return {
            "success": True,
            "insights_generated": len(generated_insights),
            "insight_types": generated_insights,
            "total_insights": len(ai_insights)
        }
        
    except Exception as e:
        print(f"❌ EDA AI integration test failed: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

async def test_modeling_ai_integration():
    """测试建模服务的AI集成"""
    print("\n🤖 Testing Modeling AI Integration...")
    
    try:
        from tools.services.data_analytics_service.services.data_service.data_modeling import DataModelingService
        
        test_file = "/Users/xenodennis/Documents/Fun/isA_MCP/test_data.csv"
        modeling_service = DataModelingService(file_path=test_file)
        
        print("✅ Modeling Service initialized")
        
        if not modeling_service.text_generator:
            print("❌ TextGenerator not available in modeling service")
            return {"success": False, "error": "TextGenerator not available"}
        
        print("✅ TextGenerator available in modeling service")
        
        # Test AI guidance generation directly
        print("🧠 Testing AI guidance generation...")
        
        # Create mock modeling results for AI guidance generation
        mock_model_results = {
            "model_evaluation": {
                "best_model": {
                    "algorithm": "random_forest_regressor",
                    "performance_metrics": {
                        "r2_score": 0.72,
                        "mean_squared_error": 198.5,
                        "mean_absolute_error": 12.3
                    }
                }
            },
            "feature_engineering": {
                "feature_count": 15,
                "selected_features": 10
            }
        }
        
        ai_guidance = await modeling_service._generate_ai_guidance(mock_model_results, "purchase_amount")
        
        if "error" in ai_guidance:
            print(f"❌ AI guidance generation failed: {ai_guidance['error']}")
            return {"success": False, "error": ai_guidance['error']}
        
        print("✅ AI guidance generated successfully")
        
        # Check guidance types
        guidance_types = ['comprehensive_strategy', 'feature_enhancement', 'production_architecture', 'business_impact']
        generated_guidance = []
        
        for guidance_type in guidance_types:
            if guidance_type in ai_guidance and ai_guidance[guidance_type]:
                generated_guidance.append(guidance_type)
                preview = ai_guidance[guidance_type][:150] + "..." if len(ai_guidance[guidance_type]) > 150 else ai_guidance[guidance_type]
                print(f"✅ {guidance_type}: {preview}")
        
        return {
            "success": True,
            "guidance_generated": len(generated_guidance),
            "guidance_types": generated_guidance,
            "total_guidance": len(ai_guidance)
        }
        
    except Exception as e:
        print(f"❌ Modeling AI integration test failed: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}

async def run_ai_functionality_test():
    """运行完整的AI功能测试"""
    print("🧠 AI Functionality Comprehensive Test")
    print("=" * 60)
    print(f"🕒 Started at: {datetime.now().isoformat()}")
    print()
    
    test_results = {
        "test_timestamp": datetime.now().isoformat(),
        "textgenerator_direct": {},
        "ai_analysis_engine": {},
        "eda_ai_integration": {},
        "modeling_ai_integration": {},
        "overall_ai_success": False
    }
    
    # Test 1: Direct TextGenerator
    textgen_result = await test_textgenerator_direct()
    test_results["textgenerator_direct"] = textgen_result
    
    if not textgen_result.get("success", False):
        print("\n❌ TextGenerator not functional - AI features unavailable")
        print("=" * 60)
        return test_results
    
    # Test 2: AI Analysis Engine
    ai_engine_result = await test_ai_analysis_engine()
    test_results["ai_analysis_engine"] = ai_engine_result
    
    # Test 3: EDA AI Integration
    eda_ai_result = await test_eda_ai_integration()
    test_results["eda_ai_integration"] = eda_ai_result
    
    # Test 4: Modeling AI Integration
    modeling_ai_result = await test_modeling_ai_integration()
    test_results["modeling_ai_integration"] = modeling_ai_result
    
    # Overall assessment
    ai_tests_passed = [
        textgen_result.get("success", False),
        ai_engine_result.get("success", False),
        eda_ai_result.get("success", False),
        modeling_ai_result.get("success", False)
    ]
    
    test_results["overall_ai_success"] = all(ai_tests_passed)
    
    # Final results
    print("\n" + "=" * 60)
    print("🎯 AI FUNCTIONALITY TEST RESULTS")
    print("=" * 60)
    
    print(f"🧠 Direct TextGenerator: {'✅ PASSED' if textgen_result.get('success', False) else '❌ FAILED'}")
    print(f"🔬 AI Analysis Engine: {'✅ PASSED' if ai_engine_result.get('success', False) else '❌ FAILED'}")
    print(f"📊 EDA AI Integration: {'✅ PASSED' if eda_ai_result.get('success', False) else '❌ FAILED'}")
    print(f"🤖 Modeling AI Integration: {'✅ PASSED' if modeling_ai_result.get('success', False) else '❌ FAILED'}")
    
    print("\n" + "=" * 60)
    if test_results["overall_ai_success"]:
        print("🎉 AI FUNCTIONALITY: FULLY OPERATIONAL")
        print("✅ All AI-enhanced features are working properly")
        print("✅ TextGenerator integration successful")
        print("✅ Intelligent analysis and insights available")
    else:
        print("⚠️ AI FUNCTIONALITY: PARTIALLY OPERATIONAL")
        print("⚠️ Some AI features may be limited or unavailable")
        
        # Show which components are working
        working_components = [
            ("Direct TextGenerator", textgen_result.get("success", False)),
            ("AI Analysis Engine", ai_engine_result.get("success", False)),
            ("EDA AI Integration", eda_ai_result.get("success", False)),
            ("Modeling AI Integration", modeling_ai_result.get("success", False))
        ]
        
        for component, is_working in working_components:
            status = "✅ Working" if is_working else "❌ Not Working"
            print(f"   {component}: {status}")
    
    print("=" * 60)
    
    return test_results

if __name__ == "__main__":
    print("🧠 AI Enhanced Data Analytics - AI Functionality Test")
    print("Testing real AI integration and intelligent features...")
    print()
    
    # Run AI functionality test
    results = asyncio.run(run_ai_functionality_test())
    
    # Exit with appropriate code
    sys.exit(0 if results["overall_ai_success"] else 1)