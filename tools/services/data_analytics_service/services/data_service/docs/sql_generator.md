# SQL Generator Service

## Overview
Step 5 of the data analytics pipeline: Generates SQL queries using AI-powered text generation based on query context and metadata matches.

## Architecture
- Uses `text_generator.py` from intelligence service for AI-powered SQL generation
- Supports multi-language prompts (English/Chinese)
- Includes domain-specific business rules and validation
- Provides fallback template-based generation

## Key Functions

### `generate_sql_from_context(query_context, metadata_matches, semantic_metadata, original_query)`

**Input:**
- `query_context` (QueryContext): Extracted query context from matcher
- `metadata_matches` (List[MetadataMatch]): Matched database entities
- `semantic_metadata` (SemanticMetadata): Full database metadata
- `original_query` (str): Original natural language query

**Output:**
- `sql_result` (SQLGenerationResult): Generated SQL with metadata

**Example:**
```python
result = await generator.generate_sql_from_context(
    context, matches, metadata, "Show customers with sales over 100"
)

# result.sql = "SELECT c.customer_name, SUM(e.total_amount) as total_sales 
#               FROM ecommerce_sales e 
#               JOIN customers c ON e.customer_id = c.customer_id 
#               WHERE e.total_amount > 100 
#               GROUP BY c.customer_name 
#               ORDER BY total_sales DESC LIMIT 1000;"
# result.explanation = "Query shows customers with total sales over 100"
# result.confidence_score = 0.9
# result.complexity_level = "medium"
```

### `enhance_sql_with_business_rules(sql, business_domain)`

**Input:**
- `sql` (str): Base SQL query to enhance
- `business_domain` (str): Business domain ('customs', 'ecommerce', etc.)

**Output:**
- `enhanced_result` (SQLGenerationResult): SQL with applied business rules

**Example:**
```python
enhanced = await generator.enhance_sql_with_business_rules(
    "SELECT * FROM orders", 
    "ecommerce"
)

# enhanced.sql = "SELECT * FROM orders WHERE order_status IN ('completed', 'shipped')"
```

### Internal Functions

#### `_build_enhanced_prompt(original_query, query_context, metadata_matches, semantic_metadata)`
Builds comprehensive AI prompt with schema information, business context, and examples.

#### `_extract_sql_from_text(text)`
Extracts SQL statements from AI text responses using regex patterns.

#### `_validate_against_schema(sql, semantic_metadata)`
Validates generated SQL against available database schema.

## Usage
```python
from tools.services.data_analytics_service.services.data_service.sql_generator import LLMSQLGenerator

# Initialize
generator = LLMSQLGenerator()
await generator.initialize()

# Generate SQL from query context
result = await generator.generate_sql_from_context(
    query_context,
    metadata_matches, 
    semantic_metadata,
    "Show me customer sales data"
)

print(f"Generated SQL: {result.sql}")
print(f"Confidence: {result.confidence_score}")
```

## AI Integration
The service integrates with the intelligence service's `text_generator.py`:
```python
from tools.services.intelligence_service.language.text_generator import generate

# AI call with low temperature for consistent SQL
response = await generate(prompt, temperature=0.1)
```

## Features
- **Multi-language support**: English and Chinese queries
- **Domain awareness**: Customs, ecommerce, finance business rules
- **Safety measures**: Automatic LIMIT clauses, SQL injection prevention
- **Validation**: Schema validation and auto-fixing
- **Fallback**: Template-based generation when AI unavailable