#!/usr/bin/env python3
"""
Step 4 Test: Metadata Embedding with customers_sample.csv
Generates embeddings and stores in pgvector database
"""
import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.services.data_analytics_service.processors.data_processors.metadata_extractor import extract_metadata
from tools.services.data_analytics_service.services.data_service.semantic_enricher import enrich_metadata
from tools.services.data_analytics_service.services.data_service.metadata_embedding import get_embedding_service

async def test_metadata_embedding():
    print("🚀 Step 4: Testing Metadata Embedding with customers_sample.csv")
    print("=" * 60)
    
    # Get the customers_sample.csv file
    current_dir = Path(__file__).parent
    csv_file = current_dir / "tools/services/data_analytics_service/processors/data_processors/tests/customers_sample.csv"
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return None
        
    print(f"📁 Processing: {csv_file}")
    
    try:
        # Step 1: Get metadata (from Step 2)
        print("📊 Step 1: Extracting metadata...")
        raw_metadata = extract_metadata(str(csv_file))
        
        if "error" in raw_metadata:
            print(f"❌ Metadata extraction failed: {raw_metadata['error']}")
            return None
            
        print(f"   ✅ Found {len(raw_metadata.get('tables', []))} tables, {len(raw_metadata.get('columns', []))} columns")
        
        # Step 2: Get semantic enrichment (from Step 3)
        print("🧠 Step 2: Running semantic enrichment...")
        semantic_metadata = await enrich_metadata(raw_metadata)
        print(f"   ✅ Generated {len(semantic_metadata.business_entities)} entities, {len(semantic_metadata.semantic_tags)} tags")
        
        # Step 3: Initialize embedding service
        print("🤖 Step 3: Initializing AI Metadata Embedding Service...")
        embedding_service = get_embedding_service("customers_test_db")
        
        # Initialize service
        await embedding_service.initialize()
        
        # Check AI service availability
        ai_available = embedding_service.embedding_generator is not None
        print(f"   🤖 AI Embedding Service Available: {'✅' if ai_available else '❌ (using fallback)'}")
        
        # Step 4: Store semantic metadata with embeddings
        print("💾 Step 4: Storing semantic metadata with AI embeddings...")
        start_time = asyncio.get_event_loop().time()
        
        storage_results = await embedding_service.store_semantic_metadata(semantic_metadata)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Print comprehensive summary
        print(f"\n📊 Embedding Storage Summary (Duration: {duration:.2f}s):")
        print(f"   ✅ Stored Embeddings: {storage_results.get('stored_embeddings', 0)}")
        print(f"   ❌ Failed Embeddings: {storage_results.get('failed_embeddings', 0)}")
        print(f"   ⏰ Storage Time: {storage_results.get('storage_time', 'N/A')}")
        
        # Show errors if any
        errors = storage_results.get('errors', [])
        if errors:
            print(f"   ⚠️  Errors: {len(errors)}")
            for i, error in enumerate(errors[:3]):  # Show first 3 errors
                print(f"      {i+1}. {error}")
        
        # Billing information
        billing_info = storage_results.get('billing_info', {})
        if billing_info:
            print(f"   💰 Billing Info:")
            print(f"      Cost: ${billing_info.get('cost_usd', 0):.6f}")
            operations = billing_info.get('operations', [])
            if operations:
                for op in operations[:2]:  # Show first 2 operations
                    print(f"      Operation: {op.get('operation', 'N/A')} - ${op.get('cost', 0):.6f}")
        
        # Test search functionality
        print("\n🔍 Testing Search Functionality:")
        
        # Test basic similarity search
        print("   📊 Basic similarity search...")
        search_results = await embedding_service.search_similar_entities(
            "customer data ecommerce",
            limit=5,
            similarity_threshold=0.5
        )
        print(f"      Found {len(search_results)} results")
        
        if search_results:
            for i, result in enumerate(search_results[:3]):  # Show first 3
                print(f"      {i+1}. {result.entity_name} ({result.entity_type}) - similarity: {result.similarity_score:.3f}")
        
        # Test AI-powered reranking search
        print("   🤖 AI reranking search...")
        reranked_results = await embedding_service.search_with_reranking(
            "customer relationship management data",
            limit=5,
            similarity_threshold=0.5,
            use_reranking=True
        )
        print(f"      Found {len(reranked_results)} reranked results")
        
        if reranked_results:
            for i, result in enumerate(reranked_results[:3]):  # Show first 3
                print(f"      {i+1}. {result.entity_name} ({result.entity_type}) - score: {result.similarity_score:.3f}")
        
        # Get metadata statistics
        print("\n📈 Database Statistics:")
        stats = await embedding_service.get_metadata_stats()
        if stats.get('success'):
            print(f"   ✅ Stats retrieved successfully")
            stats_data = stats.get('stats', {})
            if isinstance(stats_data, list) and stats_data:
                stat = stats_data[0] if stats_data else {}
                print(f"      Total embeddings: {stat.get('total_embeddings', 'N/A')}")
                print(f"      Database: {stat.get('database_source', 'N/A')}")
        else:
            print(f"   ⚠️  Stats error: {stats.get('error', 'Unknown error')}")
        
        print("\n✅ Step 4 (Metadata Embedding) completed successfully!")
        
        # Prepare results for saving
        result = {
            'embedding_duration': duration,
            'ai_service_available': ai_available,
            'storage_results': storage_results,
            'search_results_count': len(search_results),
            'search_results': [
                {
                    'entity_name': r.entity_name,
                    'entity_type': r.entity_type,
                    'similarity_score': r.similarity_score,
                    'content': r.content[:100] + '...' if len(r.content) > 100 else r.content
                }
                for r in search_results[:5]
            ],
            'reranked_results_count': len(reranked_results),
            'reranked_results': [
                {
                    'entity_name': r.entity_name,
                    'entity_type': r.entity_type,
                    'similarity_score': r.similarity_score,
                    'content': r.content[:100] + '...' if len(r.content) > 100 else r.content
                }
                for r in reranked_results[:5]
            ],
            'database_stats': stats
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Metadata Embedding failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_metadata_embedding())
    
    # Save results to file
    if result:
        output_file = Path(__file__).parent / "output_step4_metadata_embedding.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")