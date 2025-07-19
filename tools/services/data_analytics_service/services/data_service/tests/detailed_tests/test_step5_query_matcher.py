#!/usr/bin/env python3
"""
Step 5 Test: Query Matcher with customers_sample.csv metadata
Matches natural language queries to stored metadata embeddings
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
from tools.services.data_analytics_service.services.data_service.query_matcher import QueryMatcher

async def test_query_matcher():
    print("🚀 Step 5: Testing Query Matcher with customers_sample.csv")
    print("=" * 60)
    
    # Get the customers_sample.csv file
    current_dir = Path(__file__).parent
    csv_file = current_dir / "tools/services/data_analytics_service/processors/data_processors/tests/customers_sample.csv"
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return None
        
    print(f"📁 Processing: {csv_file}")
    
    try:
        # Step 1: Get semantic metadata (from previous steps)
        print("📊 Step 1: Loading semantic metadata...")
        raw_metadata = extract_metadata(str(csv_file))
        
        if "error" in raw_metadata:
            print(f"❌ Metadata extraction failed: {raw_metadata['error']}")
            return None
            
        print(f"   ✅ Found {len(raw_metadata.get('tables', []))} tables, {len(raw_metadata.get('columns', []))} columns")
        
        # Get semantic enrichment
        semantic_metadata = await enrich_metadata(raw_metadata)
        print(f"   ✅ Generated {len(semantic_metadata.business_entities)} entities, {len(semantic_metadata.semantic_tags)} tags")
        
        # Step 2: Initialize embedding service (already has stored embeddings)
        print("🤖 Step 2: Initializing Embedding Service...")
        embedding_service = get_embedding_service("customers_test_db")
        await embedding_service.initialize()
        
        ai_available = embedding_service.embedding_generator is not None
        print(f"   🤖 AI Embedding Service Available: {'✅' if ai_available else '❌ (using fallback)'}")
        
        # Step 3: Initialize Query Matcher
        print("🔍 Step 3: Initializing Query Matcher...")
        query_matcher = QueryMatcher(embedding_service)
        
        # Step 4: Test with various natural language queries
        test_queries = [
            "Show me all customers from New York",
            "Find customers with gmail email addresses", 
            "List companies and their customer counts",
            "Get customer contact information",
            "Show me the first 10 customers",
            "Find all customers in California"
        ]
        
        print(f"🔎 Step 4: Testing {len(test_queries)} natural language queries...")
        
        query_results = []
        
        for i, query in enumerate(test_queries):
            print(f"\n   Query {i+1}: '{query}'")
            start_time = asyncio.get_event_loop().time()
            
            # Match query to metadata
            query_context, metadata_matches = await query_matcher.match_query_to_metadata(
                query, semantic_metadata
            )
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            
            print(f"      📊 Context extracted in {duration:.3f}s:")
            print(f"         Entities: {query_context.entities_mentioned}")
            print(f"         Attributes: {query_context.attributes_mentioned}")
            print(f"         Operations: {query_context.operations}")
            print(f"         Intent: {query_context.business_intent}")
            print(f"         Confidence: {query_context.confidence_score:.2f}")
            
            print(f"      🎯 Found {len(metadata_matches)} metadata matches:")
            for j, match in enumerate(metadata_matches[:3]):  # Show first 3
                print(f"         {j+1}. {match.entity_name} ({match.entity_type}) - {match.match_type}, score: {match.similarity_score:.3f}")
            
            # Generate query plan
            print(f"      📋 Generating query plan...")
            query_plan = await query_matcher.generate_query_plan(
                query_context, metadata_matches, semantic_metadata
            )
            
            print(f"         Primary Tables: {query_plan.primary_tables}")
            print(f"         Select Columns: {query_plan.select_columns}")
            print(f"         Where Conditions: {query_plan.where_conditions}")
            print(f"         Plan Confidence: {query_plan.confidence_score:.2f}")
            
            # Get suggestions
            suggestions = await query_matcher.suggest_query_improvements(query, query_plan)
            if suggestions:
                print(f"         💡 Suggestions: {suggestions[:2]}")  # Show first 2
            
            # Store results
            query_result = {
                'query': query,
                'matching_duration': duration,
                'context': {
                    'entities_mentioned': query_context.entities_mentioned,
                    'attributes_mentioned': query_context.attributes_mentioned,
                    'operations': query_context.operations,
                    'filters': query_context.filters,
                    'aggregations': query_context.aggregations,
                    'temporal_references': query_context.temporal_references,
                    'business_intent': query_context.business_intent,
                    'confidence_score': query_context.confidence_score
                },
                'metadata_matches_count': len(metadata_matches),
                'metadata_matches': [
                    {
                        'entity_name': m.entity_name,
                        'entity_type': m.entity_type,
                        'match_type': m.match_type,
                        'similarity_score': m.similarity_score,
                        'relevant_attributes': m.relevant_attributes
                    }
                    for m in metadata_matches[:5]  # Store first 5
                ],
                'query_plan': {
                    'primary_tables': query_plan.primary_tables,
                    'required_joins': query_plan.required_joins,
                    'select_columns': query_plan.select_columns,
                    'where_conditions': query_plan.where_conditions,
                    'aggregations': query_plan.aggregations,
                    'order_by': query_plan.order_by,
                    'confidence_score': query_plan.confidence_score,
                    'alternative_plans_count': len(query_plan.alternative_plans)
                },
                'suggestions': suggestions
            }
            
            query_results.append(query_result)
        
        print("\n✅ Step 5 (Query Matcher) completed successfully!")
        
        # Prepare comprehensive results
        result = {
            'total_queries_tested': len(test_queries),
            'ai_service_available': ai_available,
            'embedding_service_database': "customers_test_db",
            'semantic_metadata_summary': {
                'business_entities_count': len(semantic_metadata.business_entities),
                'semantic_tags_count': len(semantic_metadata.semantic_tags),
                'domain_classification': dict(semantic_metadata.domain_classification)
            },
            'query_results': query_results,
            'performance_summary': {
                'average_matching_time': sum(r['matching_duration'] for r in query_results) / len(query_results),
                'average_matches_found': sum(r['metadata_matches_count'] for r in query_results) / len(query_results),
                'average_context_confidence': sum(r['context']['confidence_score'] for r in query_results) / len(query_results),
                'average_plan_confidence': sum(r['query_plan']['confidence_score'] for r in query_results) / len(query_results)
            }
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Query Matcher failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_query_matcher())
    
    # Save results to file
    if result:
        output_file = Path(__file__).parent / "output_step5_query_matcher.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")