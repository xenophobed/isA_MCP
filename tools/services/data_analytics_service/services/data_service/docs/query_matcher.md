# Query Matcher Service

## Overview
Step 4 of the data analytics pipeline: Extracts context from natural language queries and matches them to available metadata using AI-powered embedding search.

## Architecture
- Uses `AIMetadataEmbeddingService` for semantic similarity search
- Extracts entities, attributes, operations, and business intent from queries
- Generates structured query plans for SQL generation

## Key Functions

### `match_query_to_metadata(query, semantic_metadata)`

**Input:**
- `query` (str): Natural language query (English/Chinese)
- `semantic_metadata` (SemanticMetadata): Available database metadata

**Output:**
- `query_context` (QueryContext): Extracted context information
- `metadata_matches` (List[MetadataMatch]): Matched database entities

**Example:**
```python
query = "Show customers with total sales over 100"
context, matches = await matcher.match_query_to_metadata(query, metadata)

# context.entities_mentioned = ['customers', 'sales']
# context.attributes_mentioned = ['total']
# context.business_intent = 'reporting'
# matches[0].entity_name = 'ecommerce_sales'
# matches[0].similarity_score = 0.85
```

### `generate_query_plan(query_context, metadata_matches, semantic_metadata)`

**Input:**
- `query_context` (QueryContext): Extracted query context
- `metadata_matches` (List[MetadataMatch]): Matched metadata entities
- `semantic_metadata` (SemanticMetadata): Full metadata

**Output:**
- `query_plan` (QueryPlan): Structured execution plan

**Example:**
```python
plan = await matcher.generate_query_plan(context, matches, metadata)

# plan.primary_tables = ['ecommerce_sales', 'customers']
# plan.select_columns = ['customer_name', 'total_amount']
# plan.required_joins = [{'left_table': 'ecommerce_sales', ...}]
# plan.confidence_score = 0.9
```

### `find_related_entities(entity_name, relationship_type)`

**Input:**
- `entity_name` (str): Name of entity to find relations for
- `relationship_type` (str): Type of relationship ('any', 'foreign_key', etc.)

**Output:**
- `related_entities` (List[SearchResult]): Related entities with similarity scores

## Usage
```python
from tools.services.data_analytics_service.services.data_service.query_matcher import QueryMatcher
from tools.services.data_analytics_service.services.data_service.metadata_embedding import AIMetadataEmbeddingService

# Initialize
embedding_service = AIMetadataEmbeddingService()
matcher = QueryMatcher(embedding_service)

# Extract context and find matches
context, matches = await matcher.match_query_to_metadata(
    "Find high-value customers",
    semantic_metadata
)

# Generate execution plan
plan = await matcher.generate_query_plan(context, matches, semantic_metadata)
```