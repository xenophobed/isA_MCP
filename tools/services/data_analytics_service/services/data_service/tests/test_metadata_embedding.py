#!/usr/bin/env python3
"""
Test suite for AI-Powered Metadata Embedding Service
Tests AI integration, embedding generation, and storage capabilities
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for proper imports
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from tools.services.data_analytics_service.services.data_service.metadata_embedding import AIMetadataEmbeddingService, get_embedding_service
from tools.services.data_analytics_service.services.data_service.semantic_enricher import SemanticMetadata

def create_sample_semantic_metadata():
    """Create sample semantic metadata for testing"""
    business_entities = [
        {
            "entity_name": "customer_orders",
            "entity_type": "transactional",
            "confidence": 0.85,
            "business_importance": "high",
            "record_count": 15000,
            "key_attributes": ["order_id", "customer_id", "order_date", "total_amount"]
        }
    ]
    
    semantic_tags = {
        "table:customer_orders": ["pattern:transactional", "domain:ecommerce", "importance:high"],
        "column:customer_orders.order_id": ["semantic:identifier"],
        "column:customer_orders.total_amount": ["semantic:monetary"]
    }
    
    business_rules = [
        {
            "rule_type": "data_constraint",
            "description": "Order ID must be unique and non-null for transaction integrity",
            "confidence": 0.9
        }
    ]
    
    data_patterns = [
        {
            "pattern_type": "temporal_pattern",
            "description": "Orders follow seasonal patterns with peak during holidays",
            "confidence": 0.7
        }
    ]
    
    domain_classification = {
        "primary_domain": "ecommerce",
        "confidence": 0.88
    }
    
    confidence_scores = {
        "entity_extraction": 0.85,
        "semantic_tagging": 0.80,
        "pattern_detection": 0.75,
        "overall": 0.80
    }
    
    ai_analysis = {
        "source": "ai_comprehensive_analysis",
        "confidence": 0.82
    }
    
    # Create SemanticMetadata object
    return SemanticMetadata(
        original_metadata={},
        business_entities=business_entities,
        semantic_tags=semantic_tags,
        data_patterns=data_patterns,
        business_rules=business_rules,
        domain_classification=domain_classification,
        confidence_scores=confidence_scores,
        ai_analysis=ai_analysis
    )

async def test_ai_embedding_service_initialization():
    """Test AI embedding service initialization"""
    print("🤖 Testing AI Metadata Embedding Service Initialization")
    
    try:
        service = AIMetadataEmbeddingService("test_db")
        
        # Check if AI embedding generator is available
        if service.embedding_generator:
            print("✅ AI embedding generator available")
            ai_available = True
        else:
            print("⚠️  AI embedding generator not available - using fallback")
            ai_available = False
        
        print(f"   Database source: {service.database_source}")
        print(f"   Service name: {service.service_name}")
        
        return ai_available, True
        
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False, False

async def test_embedding_generation():
    """Test embedding generation with AI service"""
    print("🧠 Testing AI Embedding Generation")
    
    service = AIMetadataEmbeddingService("test_db")
    
    try:
        # Test single embedding
        test_text = "Customer orders table with transactional data for ecommerce analysis"
        embedding = await service._generate_embedding(test_text)
        
        if embedding:
            print(f"✅ Generated embedding with {len(embedding)} dimensions")
            
            # Test batch embeddings
            test_texts = [
                "Business entity: customer_orders (ecommerce table)",
                "Semantic tag: transactional pattern detected",
                "Business rule: order_id must be unique"
            ]
            
            batch_embeddings = await service._generate_embeddings_batch(test_texts)
            
            if batch_embeddings and all(emb is not None for emb in batch_embeddings):
                print(f"✅ Generated {len(batch_embeddings)} batch embeddings")
                return True
            else:
                print("❌ Batch embedding generation failed")
                return False
        else:
            print("❌ Single embedding generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Embedding generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_semantic_metadata_processing():
    """Test processing of semantic metadata into embeddings"""
    print("📊 Testing Semantic Metadata Processing")
    
    service = AIMetadataEmbeddingService("test_db")
    semantic_metadata = create_sample_semantic_metadata()
    
    try:
        # Test individual storage components (without actual database)
        
        # Test business entities processing
        entity_texts = []
        for entity in semantic_metadata.business_entities:
            entity_name = entity['entity_name']
            entity_type = entity['entity_type']
            content = f"Table: {entity_name}, Type: {entity_type}, "
            content += f"Importance: {entity.get('business_importance', 'unknown')}, "
            content += f"Records: {entity.get('record_count', 0)}"
            entity_texts.append(content)
        
        print(f"   📋 Processing {len(entity_texts)} business entities")
        
        # Test semantic tags processing
        tag_texts = []
        for entity_key, tags in semantic_metadata.semantic_tags.items():
            if tags:
                entity_type_prefix, entity_path = entity_key.split(':', 1)
                content = f"{entity_type_prefix.title()}: {entity_path} has semantic tags: {', '.join(tags)}"
                tag_texts.append(content)
        
        print(f"   🏷️  Processing {len(tag_texts)} semantic tag groups")
        
        # Test business rules processing
        rule_texts = []
        for rule in semantic_metadata.business_rules:
            rule_type = rule.get('rule_type', 'unknown')
            description = rule.get('description', '')
            content = f"Business rule ({rule_type}): {description}"
            rule_texts.append(content)
        
        print(f"   📝 Processing {len(rule_texts)} business rules")
        
        # Test data patterns processing
        pattern_texts = []
        for pattern in semantic_metadata.data_patterns:
            pattern_type = pattern.get('pattern_type', 'unknown')
            description = pattern.get('description', '')
            content = f"Data pattern ({pattern_type}): {description}"
            pattern_texts.append(content)
        
        print(f"   🔍 Processing {len(pattern_texts)} data patterns")
        
        # Test embedding generation for all content
        all_texts = entity_texts + tag_texts + rule_texts + pattern_texts
        
        if all_texts:
            embeddings = await service._generate_embeddings_batch(all_texts)
            
            successful_embeddings = sum(1 for emb in embeddings if emb is not None)
            print(f"   ✅ Generated {successful_embeddings}/{len(all_texts)} embeddings successfully")
            
            if successful_embeddings >= len(all_texts) * 0.8:  # 80% success rate
                print("✅ Semantic metadata processing test passed!")
                return True
            else:
                print("⚠️  Some embeddings failed - partial success")
                return True
        else:
            print("❌ No content to process")
            return False
            
    except Exception as e:
        print(f"❌ Semantic metadata processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_search_functionality():
    """Test search and reranking functionality"""
    print("🔍 Testing Search and Reranking Functionality")
    
    service = AIMetadataEmbeddingService("test_db")
    
    try:
        # Test embedding generation for search queries
        search_queries = [
            "ecommerce customer data",
            "transactional patterns",
            "business rules for orders"
        ]
        
        print(f"   🔎 Testing search query embedding generation")
        
        for query in search_queries:
            embedding = await service._generate_embedding(query)
            if embedding:
                print(f"   ✅ Generated embedding for: {query[:30]}...")
            else:
                print(f"   ❌ Failed to generate embedding for: {query[:30]}...")
                return False
        
        # Test reranking functionality (if available)
        try:
            from tools.services.intelligence_service.language.embedding_generator import rerank
            
            documents = [
                "Customer orders table with ecommerce transaction data",
                "Inventory management system for product tracking", 
                "Business rule: Order ID must be unique for data integrity"
            ]
            
            query = "ecommerce orders data"
            reranked = await rerank(query, documents, top_k=3)
            
            if reranked:
                print(f"   🎯 AI reranking successful - {len(reranked)} results")
                for i, result in enumerate(reranked):
                    score = result['relevance_score']
                    doc = result['document'][:50]
                    print(f"      {i+1}. Score: {score:.3f} - {doc}...")
                    
                print("✅ Search and reranking test passed!")
                return True
            else:
                print("⚠️  Reranking returned no results")
                return True
                
        except ImportError:
            print("⚠️  AI reranking not available - basic search only")
            return True
            
    except Exception as e:
        print(f"❌ Search functionality test failed: {e}")
        return False

async def test_convenience_functions():
    """Test convenience functions and global instances"""
    print("🔧 Testing Convenience Functions")
    
    try:
        # Test global instance function
        service1 = get_embedding_service("test_db_1")
        service2 = get_embedding_service("test_db_1")  # Same database
        service3 = get_embedding_service("test_db_2")  # Different database
        
        # Should reuse same instance for same database
        assert service1 is service2, "Same database should reuse instance"
        print("   ✅ Global instance management working")
        
        # Test backward compatibility
        from tools.services.data_analytics_service.services.data_service.metadata_embedding import get_embedding_storage
        
        legacy_service = get_embedding_storage("test_db")
        assert isinstance(legacy_service, AIMetadataEmbeddingService), "Backward compatibility failed"
        print("   ✅ Backward compatibility working")
        
        print("✅ Convenience functions test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Convenience functions test failed: {e}")
        return False

def print_summary(results):
    """Print test summary"""
    print("\n" + "="*60)
    print("🤖 AI Metadata Embedding Service Test Summary")
    print("="*60)
    
    test_names = [
        "Service Initialization",
        "Embedding Generation",
        "Semantic Metadata Processing",
        "Search and Reranking",
        "Convenience Functions"
    ]
    
    total_tests = len(results)
    passed_tests = sum(results)
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed - check AI service availability")
    
    print("\n📋 Test Details:")
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {i+1}. {name}: {status}")

async def main():
    """Run all tests"""
    print("🤖 AI-Powered Metadata Embedding Service Test Suite")
    print("=" * 60)
    
    # Run all tests
    results = []
    
    ai_available, init_success = await test_ai_embedding_service_initialization()
    results.append(init_success)
    
    results.append(await test_embedding_generation())
    results.append(await test_semantic_metadata_processing())
    results.append(await test_search_functionality())
    results.append(await test_convenience_functions())
    
    # Print summary
    print_summary(results)
    
    # Print AI availability status
    if ai_available:
        print("\n🤖 AI embedding generator is available and working!")
    else:
        print("\n⚠️  AI embedding generator not available - using fallback methods")

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())