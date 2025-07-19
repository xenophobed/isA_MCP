#!/usr/bin/env python3
"""
Step 6 Test: SQL Generator with customers_sample.csv
Generates SQL from query context and metadata matches using LLM
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
from tools.services.data_analytics_service.services.data_service.sql_generator import LLMSQLGenerator

async def test_sql_generator():
    print("🚀 Step 6: Testing SQL Generator with customers_sample.csv")
    print("=" * 60)
    
    # Get the customers_sample.csv file
    current_dir = Path(__file__).parent
    csv_file = current_dir / "tools/services/data_analytics_service/processors/data_processors/tests/customers_sample.csv"
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return None
        
    print(f"📁 Processing: {csv_file}")
    
    try:
        # Step 1: Get semantic metadata and set up query matcher (from Step 5)
        print("📊 Step 1: Loading semantic metadata and query matcher...")
        raw_metadata = extract_metadata(str(csv_file))
        
        if "error" in raw_metadata:
            print(f"❌ Metadata extraction failed: {raw_metadata['error']}")
            return None
            
        semantic_metadata = await enrich_metadata(raw_metadata)
        print(f"   ✅ Semantic metadata loaded: {len(semantic_metadata.business_entities)} entities")
        
        # Initialize services
        embedding_service = get_embedding_service("customers_test_db")
        await embedding_service.initialize()
        query_matcher = QueryMatcher(embedding_service)
        
        # Step 2: Initialize SQL Generator
        print("🤖 Step 2: Initializing LLM SQL Generator...")
        sql_generator = LLMSQLGenerator()
        await sql_generator.initialize()
        
        llm_available = sql_generator.llm_model is not None
        print(f"   🤖 LLM Service Available: {'✅' if llm_available else '❌ (using fallback)'}")
        
        # Step 3: Test SQL generation with various queries
        test_queries = [
            "Show me all customers from New York",
            "Find customers with gmail email addresses", 
            "List companies and their customer counts",
            "Get customer contact information for ID 123",
            "Show me the first 10 customers ordered by name",
            "Find all customers in California and Texas"
        ]
        
        print(f"🔎 Step 3: Testing SQL generation for {len(test_queries)} queries...")
        
        sql_results = []
        
        for i, query in enumerate(test_queries):
            print(f"\n   Query {i+1}: '{query}'")
            start_time = asyncio.get_event_loop().time()
            
            # Step 3a: Get query context and metadata matches
            query_context, metadata_matches = await query_matcher.match_query_to_metadata(
                query, semantic_metadata
            )
            
            print(f"      📊 Found {len(metadata_matches)} metadata matches, confidence: {query_context.confidence_score:.2f}")
            
            # Step 3b: Generate SQL using LLM
            sql_generation_result = await sql_generator.generate_sql_from_context(
                query_context, metadata_matches, semantic_metadata, query
            )
            
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            
            print(f"      🛠️  SQL generated in {duration:.3f}s:")
            print(f"         SQL: {sql_generation_result.sql}")
            print(f"         Explanation: {sql_generation_result.explanation}")
            print(f"         Confidence: {sql_generation_result.confidence_score:.2f}")
            print(f"         Complexity: {sql_generation_result.complexity_level}")
            
            # Step 3c: Test business rule enhancement
            domain = semantic_metadata.domain_classification.get('primary_domain', 'general')
            if domain in ['ecommerce', 'crm']:
                print(f"      🔧 Applying {domain} business rules...")
                enhanced_result = await sql_generator.enhance_sql_with_business_rules(
                    sql_generation_result.sql, domain
                )
                print(f"         Enhanced SQL: {enhanced_result.sql}")
                print(f"         Enhancement Explanation: {enhanced_result.explanation}")
            else:
                enhanced_result = None
            
            # Store results
            sql_result = {
                'query': query,
                'generation_duration': duration,
                'llm_service_used': llm_available,
                'query_context_summary': {
                    'entities_mentioned': query_context.entities_mentioned,
                    'attributes_mentioned': query_context.attributes_mentioned,
                    'operations': query_context.operations,
                    'business_intent': query_context.business_intent,
                    'confidence_score': query_context.confidence_score
                },
                'metadata_matches_count': len(metadata_matches),
                'sql_generation': {
                    'sql': sql_generation_result.sql,
                    'explanation': sql_generation_result.explanation,
                    'confidence_score': sql_generation_result.confidence_score,
                    'complexity_level': sql_generation_result.complexity_level,
                    'estimated_execution_time': sql_generation_result.estimated_execution_time,
                    'estimated_rows': sql_generation_result.estimated_rows,
                    'alternative_sqls': sql_generation_result.alternative_sqls or []
                },
                'business_rule_enhancement': {
                    'applied': enhanced_result is not None,
                    'domain': domain,
                    'enhanced_sql': enhanced_result.sql if enhanced_result else None,
                    'enhancement_explanation': enhanced_result.explanation if enhanced_result else None
                } if enhanced_result else None
            }
            
            sql_results.append(sql_result)
        
        # Step 4: Test additional SQL Generator features
        print(f"\n🔧 Step 4: Testing additional SQL Generator features...")
        
        # Test billing info
        billing_info = sql_generator.get_service_billing_info()
        print(f"   💰 Billing Info: {billing_info}")
        
        # Test with sample business domains
        sample_sql = "SELECT * FROM customers_sample LIMIT 10"
        
        domain_tests = []
        for domain in ['ecommerce', 'crm', 'finance']:
            print(f"   🏢 Testing {domain} domain enhancement...")
            domain_enhanced = await sql_generator.enhance_sql_with_business_rules(sample_sql, domain)
            domain_tests.append({
                'domain': domain,
                'original_sql': sample_sql,
                'enhanced_sql': domain_enhanced.sql,
                'explanation': domain_enhanced.explanation,
                'confidence': domain_enhanced.confidence_score
            })
            print(f"      Enhanced: {domain_enhanced.sql}")
        
        print("\n✅ Step 6 (SQL Generator) completed successfully!")
        
        # Prepare comprehensive results
        result = {
            'total_queries_tested': len(test_queries),
            'llm_service_available': llm_available,
            'sql_generator_model': str(sql_generator.llm_model),
            'semantic_metadata_domain': semantic_metadata.domain_classification.get('primary_domain'),
            'sql_generation_results': sql_results,
            'billing_information': billing_info,
            'domain_enhancement_tests': domain_tests,
            'performance_summary': {
                'average_generation_time': sum(r['generation_duration'] for r in sql_results) / len(sql_results),
                'average_sql_confidence': sum(r['sql_generation']['confidence_score'] for r in sql_results) / len(sql_results),
                'complexity_distribution': {
                    'simple': sum(1 for r in sql_results if r['sql_generation']['complexity_level'] == 'simple'),
                    'medium': sum(1 for r in sql_results if r['sql_generation']['complexity_level'] == 'medium'),
                    'complex': sum(1 for r in sql_results if r['sql_generation']['complexity_level'] == 'complex')
                },
                'llm_usage_success_rate': sum(1 for r in sql_results if r['llm_service_used']) / len(sql_results)
            }
        }
        
        return result
        
    except Exception as e:
        print(f"❌ SQL Generator failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Clean up SQL generator
        if 'sql_generator' in locals():
            await sql_generator.close()

if __name__ == "__main__":
    result = asyncio.run(test_sql_generator())
    
    # Save results to file
    if result:
        output_file = Path(__file__).parent / "output_step6_sql_generator.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")