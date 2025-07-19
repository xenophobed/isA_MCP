#!/usr/bin/env python3
"""
Step 3 Test: Semantic Enricher with customers_sample.csv
Enriches metadata with AI-powered semantic analysis
"""
import asyncio
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.services.data_analytics_service.processors.data_processors.metadata_extractor import extract_metadata
from tools.services.data_analytics_service.services.data_service.semantic_enricher import AISemanticEnricher, enrich_metadata

async def test_semantic_enricher():
    print("🚀 Step 3: Testing Semantic Enricher with customers_sample.csv")
    print("=" * 60)
    
    # Get the customers_sample.csv file
    current_dir = Path(__file__).parent
    csv_file = current_dir / "tools/services/data_analytics_service/processors/data_processors/tests/customers_sample.csv"
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return None
        
    print(f"📁 Processing: {csv_file}")
    
    try:
        # Step 1: Get metadata first (from Step 2)
        print("📊 Step 1: Extracting metadata...")
        raw_metadata = extract_metadata(str(csv_file))
        
        if "error" in raw_metadata:
            print(f"❌ Metadata extraction failed: {raw_metadata['error']}")
            return None
            
        print(f"   ✅ Found {len(raw_metadata.get('tables', []))} tables, {len(raw_metadata.get('columns', []))} columns")
        
        # Step 2: Initialize semantic enricher
        print("🧠 Step 2: Initializing AI Semantic Enricher...")
        enricher = AISemanticEnricher()
        
        # Check AI service availability
        ai_available = enricher.text_extractor is not None
        print(f"   🤖 AI Service Available: {'✅' if ai_available else '❌ (using fallback)'}")
        
        # Step 3: Enrich with AI semantic analysis
        print("🔍 Step 3: Running AI semantic enrichment...")
        start_time = asyncio.get_event_loop().time()
        
        enriched_metadata = await enricher.enrich_metadata(raw_metadata)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Print comprehensive summary
        print(f"\n📊 Semantic Enrichment Summary (Duration: {duration:.2f}s):")
        
        # Business entities
        entities = enriched_metadata.business_entities
        print(f"   🏢 Business Entities: {len(entities)}")
        if entities:
            for i, entity in enumerate(entities[:3]):  # Show first 3
                print(f"      {i+1}. {entity.get('entity_name', 'N/A')} ({entity.get('entity_type', 'N/A')}) - confidence: {entity.get('confidence', 0):.2f}")
        
        # Semantic tags
        tags = enriched_metadata.semantic_tags
        print(f"   🏷️  Semantic Tags: {len(tags)} groups")
        if tags:
            for i, (entity_key, tag_list) in enumerate(list(tags.items())[:3]):  # Show first 3
                print(f"      {i+1}. {entity_key}: {tag_list[:3]}")  # Show first 3 tags per entity
        
        # Data patterns
        patterns = enriched_metadata.data_patterns
        print(f"   🔍 Data Patterns: {len(patterns)}")
        if patterns:
            for i, pattern in enumerate(patterns[:2]):  # Show first 2
                print(f"      {i+1}. {pattern.get('pattern_type', 'N/A')}: {pattern.get('description', 'N/A')[:60]}...")
        
        # Business rules
        rules = enriched_metadata.business_rules
        print(f"   📋 Business Rules: {len(rules)}")
        if rules:
            for i, rule in enumerate(rules[:2]):  # Show first 2
                print(f"      {i+1}. {rule.get('rule_type', 'N/A')}: {rule.get('description', 'N/A')[:60]}...")
        
        # Domain classification
        domain_class = enriched_metadata.domain_classification
        print(f"   🎯 Domain Classification:")
        print(f"      Primary: {domain_class.get('primary_domain', 'N/A')}")
        print(f"      Confidence: {domain_class.get('confidence', 0):.2f}")
        print(f"      Source: {domain_class.get('source', 'N/A')}")
        
        # AI analysis
        ai_analysis = enriched_metadata.ai_analysis
        print(f"   🤖 AI Analysis:")
        print(f"      Source: {ai_analysis.get('source', 'N/A')}")
        print(f"      Confidence: {ai_analysis.get('confidence', 0):.2f}")
        
        # Overall confidence scores
        confidence_scores = enriched_metadata.confidence_scores
        print(f"   📊 Confidence Scores:")
        print(f"      Overall: {confidence_scores.get('overall', 0):.2f}")
        print(f"      Entity Extraction: {confidence_scores.get('entity_extraction', 0):.2f}")
        print(f"      Semantic Tagging: {confidence_scores.get('semantic_tagging', 0):.2f}")
        
        print("\n✅ Step 3 (Semantic Enricher) completed successfully!")
        
        # Convert to serializable format for saving
        result = {
            'enrichment_duration': duration,
            'ai_service_available': ai_available,
            'business_entities_count': len(entities),
            'business_entities': entities,
            'semantic_tags_count': len(tags),
            'semantic_tags': dict(tags),  # Convert to regular dict
            'data_patterns_count': len(patterns),
            'data_patterns': patterns,
            'business_rules_count': len(rules),
            'business_rules': rules,
            'domain_classification': dict(domain_class),
            'confidence_scores': dict(confidence_scores),
            'ai_analysis': dict(ai_analysis),
            'original_metadata': enriched_metadata.original_metadata
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Semantic Enricher failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_semantic_enricher())
    
    # Save results to file
    if result:
        output_file = Path(__file__).parent / "output_step3_semantic_enricher.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")