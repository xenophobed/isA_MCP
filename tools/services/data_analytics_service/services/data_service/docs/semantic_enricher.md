# AI-Powered Semantic Enricher Documentation

## Overview

The **AI-Powered Semantic Enricher** is Step 2 of the data analytics pipeline that enriches raw metadata with semantic meaning using advanced AI analysis. It has been upgraded from hardcoded pattern matching to use the `intelligence_service.text_extractor` for sophisticated AI-powered semantic analysis.

## Features

### > AI-Powered Analysis
- **Named Entity Recognition** - Extracts business entities using AI
- **Text Classification** - Classifies domains using AI text analysis  
- **Pattern Detection** - Identifies data patterns using AI reasoning
- **Business Rule Inference** - Infers business rules using AI analysis
- **Semantic Tagging** - Generates semantic tags using AI
- **Comprehensive Analysis** - Provides overall AI-powered insights

### = Fallback Mechanisms
- Graceful fallback to hardcoded methods when AI is unavailable
- Robust error handling with detailed logging
- Maintains backward compatibility

## Quick Start

```python
from semantic_enricher import AISemanticEnricher, enrich_metadata

# Basic usage with convenience function
metadata = {
    "tables": [{"table_name": "orders", "record_count": 1000}],
    "columns": [{"table_name": "orders", "column_name": "order_id", "business_type": "identifier"}]
}

enriched = await enrich_metadata(metadata)
print(f"AI Analysis: {enriched.ai_analysis['source']}")
```

## API Reference

### AISemanticEnricher Class

```python
class AISemanticEnricher:
    """AI-powered semantic enrichment service"""
    
    async def enrich_metadata(self, metadata: Dict[str, Any]) -> SemanticMetadata:
        """
        Enrich raw metadata with AI-powered semantic analysis
        
        Args:
            metadata: Raw metadata from step 1 (metadata extractor)
            
        Returns:
            SemanticMetadata with AI-enriched information
        """
```

### Convenience Function

```python
async def enrich_metadata(metadata: Dict[str, Any]) -> SemanticMetadata:
    """
    Convenience function to enrich metadata with AI analysis
    
    Args:
        metadata: Raw metadata dictionary
        
    Returns:
        SemanticMetadata with AI-enriched information
    """
```

## Input Format

The service expects metadata in the standardized format from the metadata extractor:

```json
{
  "source_info": {
    "type": "csv",
    "file_path": "/data/orders.csv"
  },
  "tables": [
    {
      "table_name": "ecommerce_orders",
      "record_count": 1000,
      "column_count": 8
    }
  ],
  "columns": [
    {
      "table_name": "ecommerce_orders",
      "column_name": "order_id",
      "data_type": "object",
      "business_type": "identifier",
      "ordinal_position": 1
    }
  ]
}
```

## Output Format

Returns a `SemanticMetadata` dataclass with AI-enriched information:

```python
@dataclass
class SemanticMetadata:
    original_metadata: Dict[str, Any]        # Original input metadata
    business_entities: List[Dict[str, Any]]  # AI-extracted entities
    semantic_tags: Dict[str, List[str]]      # AI-generated semantic tags
    data_patterns: List[Dict[str, Any]]      # AI-detected patterns
    business_rules: List[Dict[str, Any]]     # AI-inferred rules
    domain_classification: Dict[str, Any]    # AI domain classification
    confidence_scores: Dict[str, float]      # Confidence metrics
    ai_analysis: Dict[str, Any]              # Comprehensive AI analysis
```

### Example Output Structure

```json
{
  "business_entities": [
    {
      "entity_name": "ecommerce_orders",
      "entity_type": "transactional",
      "confidence": 0.8,
      "key_attributes": ["order_id", "customer_email", "order_amount"],
      "business_importance": "high",
      "ai_classification": {
        "detected_entities": [
          {"type": "ORGANIZATION", "name": "ecommerce", "confidence": 0.9}
        ]
      }
    }
  ],
  "semantic_tags": {
    "table:ecommerce_orders": [
      "pattern:transactional",
      "domain:ecommerce",
      "characteristic:customer_focused"
    ],
    "column:ecommerce_orders.order_id": [
      "semantic:identifier"
    ]
  },
  "data_patterns": [
    {
      "pattern_type": "data_model_patterns",
      "description": "Normalized transactional schema with clear entity relationships",
      "confidence": 0.75,
      "source": "ai_analysis"
    }
  ],
  "business_rules": [
    {
      "rule_type": "data_constraints",
      "description": "Order ID must be unique and non-null for transaction integrity",
      "confidence": 0.8,
      "source": "ai_inference",
      "applicable_entities": ["ecommerce_orders"]
    }
  ],
  "domain_classification": {
    "primary_domain": "ecommerce",
    "domain_scores": {
      "ecommerce": 0.9,
      "finance": 0.3,
      "crm": 0.4
    },
    "confidence": 0.85,
    "source": "ai_classification",
    "secondary_domains": ["crm"]
  },
  "confidence_scores": {
    "entity_extraction": 0.8,
    "semantic_tagging": 0.75,
    "pattern_detection": 0.7,
    "business_rules": 0.65,
    "overall": 0.73
  },
  "ai_analysis": {
    "source": "ai_comprehensive_analysis",
    "confidence": 0.78,
    "analysis": {
      "data_architecture": "Well-structured ecommerce transactional system",
      "business_value": "High-value customer transaction data for analytics",
      "data_maturity": "Production-ready with good data quality indicators",
      "usage_recommendations": "Suitable for customer analytics, revenue tracking",
      "potential_issues": "None detected in current structure",
      "integration_opportunities": "Can integrate with CRM and inventory systems"
    }
  }
}
```

## AI Integration Details

### Text Extractor Integration

The service uses the `intelligence_service.text_extractor` for:

1. **Entity Extraction** - `extract_entities()` with confidence filtering
2. **Text Classification** - `classify_text()` for domain classification  
3. **Key Information Extraction** - `extract_key_information()` with custom schemas
4. **Comprehensive Analysis** - Multi-step AI analysis workflow

### AI Methods

#### Business Entity Extraction
```python
async def _extract_business_entities_ai(self, metadata) -> List[Dict]:
    """Extract business entities using AI-powered NER"""
    # Uses extract_entities() with business context
    # Analyzes table names, column patterns, and relationships
    # Returns entities with AI confidence scores
```

#### Semantic Tag Generation  
```python
async def _generate_semantic_tags_ai(self, metadata) -> Dict[str, List[str]]:
    """Generate semantic tags using AI text analysis"""
    # Uses extract_key_information() with semantic schema
    # Analyzes data patterns, business domains, characteristics
    # Returns structured semantic tags
```

#### Domain Classification
```python
async def _classify_domain_ai(self, metadata) -> Dict[str, Any]:
    """Classify business domain using AI"""
    # Uses classify_text() with domain categories
    # Multi-label classification for complex domains
    # Returns primary domain with confidence scores
```

#### Pattern Detection
```python
async def _detect_data_patterns_ai(self, metadata) -> List[Dict]:
    """Detect data patterns using AI analysis"""
    # Uses extract_key_information() with pattern schema
    # Identifies modeling patterns, relationships, processes
    # Returns structured pattern descriptions
```

#### Business Rule Inference
```python
async def _infer_business_rules_ai(self, metadata) -> List[Dict]:
    """Infer business rules using AI reasoning"""
    # Uses extract_key_information() with business context
    # Analyzes constraints, validation rules, business logic
    # Returns actionable business rules
```

## Usage Examples

### Basic Enrichment

```python
import asyncio
from semantic_enricher import enrich_metadata

async def main():
    metadata = {
        "tables": [{"table_name": "customers", "record_count": 5000}],
        "columns": [
            {"table_name": "customers", "column_name": "email", "business_type": "email"}
        ]
    }
    
    result = await enrich_metadata(metadata)
    
    print(f"Domain: {result.domain_classification['primary_domain']}")
    print(f"Entities: {len(result.business_entities)}")
    print(f"AI Source: {result.ai_analysis['source']}")

asyncio.run(main())
```

### Advanced Usage with Custom Analysis

```python
from semantic_enricher import AISemanticEnricher

async def analyze_data_source():
    enricher = AISemanticEnricher()
    
    # Check AI availability
    if enricher.text_extractor is None:
        print("AI service not available - using fallback")
    
    # Your metadata from step 1
    metadata = load_metadata_from_step1()
    
    # Enrich with AI analysis
    enriched = await enricher.enrich_metadata(metadata)
    
    # Process results
    if enriched.ai_analysis['source'] == 'ai_comprehensive_analysis':
        print(" Full AI analysis completed")
        
        # Access AI insights
        architecture = enriched.ai_analysis['analysis']['data_architecture']
        recommendations = enriched.ai_analysis['analysis']['usage_recommendations']
        
        print(f"Architecture: {architecture}")
        print(f"Recommendations: {recommendations}")
    
    return enriched
```

### Pipeline Integration

```python
from metadata_extractor import extract_metadata
from semantic_enricher import enrich_metadata

async def full_analysis_pipeline(data_source_path):
    """Complete Step 1 + Step 2 pipeline"""
    
    # Step 1: Extract metadata
    raw_metadata = extract_metadata(data_source_path)
    
    if 'error' in raw_metadata:
        return {'error': f"Metadata extraction failed: {raw_metadata['error']}"}
    
    # Step 2: Enrich with AI semantic analysis
    enriched_metadata = await enrich_metadata(raw_metadata)
    
    return {
        'success': True,
        'raw_metadata': raw_metadata,
        'enriched_metadata': enriched_metadata,
        'ai_source': enriched_metadata.ai_analysis['source'],
        'confidence': enriched_metadata.confidence_scores['overall']
    }
```

## Error Handling

### Graceful Fallback

The service automatically falls back to hardcoded methods when AI is unavailable:

```python
# AI service unavailable - automatic fallback
enriched = await enrich_metadata(metadata)
assert enriched.ai_analysis['source'] == 'fallback'
```

### Input Validation

```python
# Safe handling of None/empty inputs
result = await enrich_metadata({'tables': None, 'columns': None})
# Returns valid structure with empty/default values
```

### Error Recovery

```python
try:
    enriched = await enrich_metadata(metadata)
    if enriched.ai_analysis['source'] == 'error':
        print(f"Error: {enriched.ai_analysis['error']}")
except Exception as e:
    print(f"Enrichment failed: {e}")
```

## Performance & Billing

### AI Service Costs
- Entity extraction: ~$0.001-0.005 per request
- Text classification: ~$0.001-0.003 per request  
- Pattern analysis: ~$0.002-0.008 per request
- Total enrichment: ~$0.01-0.05 per metadata set

### Processing Time
- Small datasets (1-5 tables): 2-8 seconds
- Medium datasets (5-20 tables): 8-30 seconds
- Large datasets (20+ tables): 30-120 seconds

### Optimization Tips
- Use confidence thresholds to reduce AI calls
- Cache results for frequently analyzed datasets
- Batch multiple enrichments when possible

## Configuration

### AI Service Configuration

The service automatically detects and uses the intelligence_service text_extractor. No additional configuration required.

### Confidence Thresholds

```python
# Custom confidence settings for entity extraction
entity_result = await extract_entities(text, confidence_threshold=0.8)
```

### Domain Categories

The service uses these predefined domain categories:
- `ecommerce` - Online retail, shopping, products
- `finance` - Banking, payments, investments
- `healthcare` - Medical, patient data, treatments
- `education` - Schools, students, courses
- `hr` - Human resources, employees, payroll
- `crm` - Customer relationship management
- `manufacturing` - Production, inventory, quality
- `logistics` - Shipping, warehousing, supply chain
- `marketing` - Campaigns, leads, analytics
- `legal` - Contracts, compliance, regulations
- `research` - Academic, scientific data

## Testing

### Test Suite

Run the comprehensive test suite:

```bash
cd tools/services/data_analytics_service/processors/data_processors/tests
python test_semantic_enricher.py
```

### Expected Results

```
>à AI-Powered Semantic Enricher Test Suite
==================================================
>à Testing AI Semantic Enricher Integration
 AI service available
=Ê Business entities: 1
<÷  Semantic tags: 2
= Data patterns: 5
=Ý Business rules: 5
> AI analysis source: ai_comprehensive_analysis
 AI analysis working correctly!

=' Testing convenience function
    Convenience function test passed!

= Testing fallback mechanisms
   =Ê Fallback generated 1 business entities
    Fallback mechanism test passed!

   Testing error handling
    Error handling test passed!

============================================================
>à AI Semantic Enricher Test Summary
============================================================
Total tests: 4
Passed: 4
Failed: 0
 All tests passed!

=Ë Test Details:
   1. AI Integration:  PASS
   2. Convenience Function:  PASS
   3. Fallback Mechanisms:  PASS
   4. Error Handling:  PASS
```

## Integration with Data Analytics Pipeline

### Step 1 ’ Step 2 Flow

```python
# Complete pipeline from raw data to enriched metadata
from metadata_extractor import extract_metadata
from semantic_enricher import enrich_metadata

# Step 1: Extract raw metadata
raw_metadata = extract_metadata('data.csv')

# Step 2: Enrich with AI semantic analysis
enriched_metadata = await enrich_metadata(raw_metadata)

# Continue to Step 3: Embedding storage
# Step 4: Query matching
# Step 5: SQL generation
# Step 6: Execution
```

### Pipeline Benefits

1. **Automated Analysis** - No manual domain expertise required
2. **Consistent Results** - Standardized semantic enrichment
3. **Business Context** - AI understands business meaning
4. **Scalable Processing** - Handles any dataset size
5. **Quality Insights** - Identifies data quality and patterns

## Limitations

- Requires active intelligence_service for full AI functionality
- AI analysis costs may accumulate with large-scale usage
- English text produces best AI results
- Complex nested relationships may need manual validation
- Domain classification limited to predefined categories

## Dependencies

- `tools.services.intelligence_service.language.text_extractor`
- `typing` - Type hints
- `asyncio` - Async/await support  
- `json` - JSON processing
- `logging` - Error and info logging
- `dataclasses` - Structured data classes
- `collections.defaultdict` - Default dictionaries

## Summary

The AI-Powered Semantic Enricher successfully transforms raw metadata into semantically rich, business-context-aware information using advanced AI analysis. It provides:

- **7 AI-powered analysis capabilities** for comprehensive semantic enrichment
- **Robust fallback mechanisms** ensuring reliability
- **Structured output format** for consistent downstream processing  
- **High-quality results** with confidence scoring and detailed insights
- **Production-ready performance** with error handling and optimization

Use this service as Step 2 in your data analytics pipeline to add business intelligence and semantic understanding to your data analysis workflows.