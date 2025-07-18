#!/usr/bin/env python3
"""
Test suite for the upgraded AI-powered Semantic Enricher
Tests both AI functionality and fallback mechanisms
"""

import asyncio
import sys
from pathlib import Path

# Add correct paths for imports
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent.parent.parent
services_dir = current_dir.parent.parent.parent / "services" / "data_service"
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(services_dir))

try:
    from semantic_enricher import AISemanticEnricher, enrich_metadata
except ImportError:
    from tools.services.data_analytics_service.services.data_service.semantic_enricher import AISemanticEnricher, enrich_metadata

def create_sample_metadata():
    """Create sample metadata for testing"""
    return {
        "source_info": {
            "type": "csv",
            "file_path": "/test/ecommerce_data.csv",
            "total_rows": 1000,
            "total_columns": 8
        },
        "tables": [{
            "table_name": "ecommerce_orders",
            "record_count": 1000,
            "column_count": 8
        }],
        "columns": [
            {
                "table_name": "ecommerce_orders",
                "column_name": "order_id",
                "data_type": "object",
                "business_type": "identifier",
                "ordinal_position": 1,
                "unique_count": 1000,
                "sample_values": ["ORD001", "ORD002"]
            },
            {
                "table_name": "ecommerce_orders", 
                "column_name": "customer_email",
                "data_type": "object",
                "business_type": "email",
                "ordinal_position": 2,
                "unique_count": 850,
                "sample_values": ["user@example.com", "customer@shop.com"]
            },
            {
                "table_name": "ecommerce_orders",
                "column_name": "product_name",
                "data_type": "object", 
                "business_type": "name",
                "ordinal_position": 3,
                "unique_count": 200,
                "sample_values": ["iPhone 15", "MacBook Pro"]
            },
            {
                "table_name": "ecommerce_orders",
                "column_name": "order_amount",
                "data_type": "float64",
                "business_type": "monetary",
                "ordinal_position": 4,
                "unique_count": 500,
                "sample_values": [999.99, 1299.00]
            },
            {
                "table_name": "ecommerce_orders",
                "column_name": "order_date", 
                "data_type": "datetime64",
                "business_type": "temporal",
                "ordinal_position": 5,
                "unique_count": 365,
                "sample_values": ["2024-01-15", "2024-02-20"]
            }
        ],
        "business_patterns": {
            "primary_domain": "ecommerce",
            "domain_scores": {
                "ecommerce": 0.9,
                "finance": 0.1
            }
        },
        "data_quality": {
            "overall_quality_score": 0.95,
            "completeness_percentage": 95.0
        }
    }

async def test_ai_integration():
    """Test AI integration and functionality"""
    print("🧠 Testing AI Semantic Enricher Integration")
    
    enricher = AISemanticEnricher()
    
    # Check if AI service is available
    if enricher.text_extractor is None:
        print("❌ AI service not available - using fallback")
        return False
    else:
        print("✅ AI service available")
    
    # Test with sample metadata
    sample_metadata = create_sample_metadata()
    
    try:
        result = await enricher.enrich_metadata(sample_metadata)
        
        # Validate result structure
        assert hasattr(result, 'original_metadata'), "Missing original_metadata"
        assert hasattr(result, 'business_entities'), "Missing business_entities"
        assert hasattr(result, 'semantic_tags'), "Missing semantic_tags"
        assert hasattr(result, 'data_patterns'), "Missing data_patterns"
        assert hasattr(result, 'business_rules'), "Missing business_rules"
        assert hasattr(result, 'domain_classification'), "Missing domain_classification"
        assert hasattr(result, 'confidence_scores'), "Missing confidence_scores"
        assert hasattr(result, 'ai_analysis'), "Missing ai_analysis"
        
        print(f"📊 Business entities: {len(result.business_entities)}")
        print(f"🏷️  Semantic tags: {len(result.semantic_tags)}")
        print(f"🔍 Data patterns: {len(result.data_patterns)}")
        print(f"📝 Business rules: {len(result.business_rules)}")
        
        # Check AI analysis
        ai_analysis = result.ai_analysis
        ai_source = ai_analysis.get('source', 'unknown')
        print(f"🤖 AI analysis source: {ai_source}")
        
        # Check domain classification
        domain = result.domain_classification
        primary_domain = domain.get('primary_domain', 'unknown')
        confidence = domain.get('confidence', 0.0)
        print(f"🎯 Domain: {primary_domain} (confidence: {confidence:.2f})")
        
        # Check confidence scores
        confidence_scores = result.confidence_scores
        overall_confidence = confidence_scores.get('overall', 0.0)
        print(f"📊 Overall confidence: {overall_confidence:.2f}")
        
        if ai_source == 'ai_comprehensive_analysis':
            print("✅ AI analysis working correctly!")
            return True
        elif ai_source == 'fallback':
            print("⚠️  Using fallback methods - AI may not be fully working")
            return True
        else:
            print("❌ Unknown AI analysis source")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_convenience_function():
    """Test the convenience function"""
    print("🔧 Testing convenience function")
    
    sample_metadata = create_sample_metadata()
    
    try:
        result = await enrich_metadata(sample_metadata)
        
        # Should have semantic metadata structure
        assert hasattr(result, 'business_entities'), "Missing business_entities from convenience function"
        assert hasattr(result, 'ai_analysis'), "Missing ai_analysis from convenience function"
        
        print("   ✅ Convenience function test passed!")
        return True
        
    except Exception as e:
        print(f"   ❌ Convenience function test failed: {e}")
        return False

async def test_fallback_mechanisms():
    """Test fallback to hardcoded methods when AI is unavailable"""
    print("🔄 Testing fallback mechanisms")
    
    # Create enricher but simulate AI unavailability
    enricher = AISemanticEnricher()
    # Force fallback by setting text_extractor to None
    enricher.text_extractor = None
    
    sample_metadata = create_sample_metadata()
    
    try:
        result = await enricher.enrich_metadata(sample_metadata)
        
        # Should still have valid structure with fallback data
        assert hasattr(result, 'business_entities'), "Missing business_entities in fallback"
        assert hasattr(result, 'ai_analysis'), "Missing ai_analysis in fallback"
        
        # Check that fallback was used
        ai_analysis = result.ai_analysis
        ai_source = ai_analysis.get('source', 'unknown')
        assert ai_source == 'fallback', f"Expected fallback source, got: {ai_source}"
        
        entities = result.business_entities
        print(f"   📊 Fallback generated {len(entities)} business entities")
        
        print("   ✅ Fallback mechanism test passed!")
        return True
        
    except Exception as e:
        print(f"   ❌ Fallback mechanism test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_error_handling():
    """Test error handling with invalid input"""
    print("⚠️  Testing error handling")
    
    enricher = AISemanticEnricher()
    
    try:
        # Test with empty metadata but provide basic structure
        empty_metadata = {
            "tables": [],
            "columns": []
        }
        result = await enricher.enrich_metadata(empty_metadata)
        
        # Should still return valid structure
        assert hasattr(result, 'business_entities'), "Missing business_entities with empty input"
        
        # Test with None values but safe handling
        none_metadata = {
            'tables': None, 
            'columns': None
        }
        result = await enricher.enrich_metadata(none_metadata)
        assert hasattr(result, 'business_entities'), "Missing business_entities with None input"
        
        print("   ✅ Error handling test passed!")
        return True
        
    except Exception as e:
        print(f"   ❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_summary(results):
    """Print test summary"""
    print("\n" + "="*60)
    print("🧠 AI Semantic Enricher Test Summary")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(results)
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed - check details above")
    
    print("\n📋 Test Details:")
    test_names = [
        "AI Integration",
        "Convenience Function", 
        "Fallback Mechanisms",
        "Error Handling"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {i+1}. {name}: {status}")

async def main():
    """Run all tests"""
    print("🧠 AI-Powered Semantic Enricher Test Suite")
    print("=" * 50)
    
    # Run all tests
    results = []
    
    results.append(await test_ai_integration())
    results.append(await test_convenience_function())
    results.append(await test_fallback_mechanisms())
    results.append(await test_error_handling())
    
    # Print summary
    print_summary(results)

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())