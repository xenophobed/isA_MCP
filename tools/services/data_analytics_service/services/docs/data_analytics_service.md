# Data Analytics Service

The Data Analytics Service provides two main functions for complete data analytics workflows: data ingestion and natural language querying.

## Architecture

The service is split into two clear functions:

1. **Function 1**: Data Ingestion (Steps 1-3) - Process raw data into searchable format
2. **Function 2**: Query Processing (Steps 4-6) - Answer natural language queries

## Function 1: Data Ingestion

### Purpose
Processes data sources and stores them in SQLite database + pgvector embeddings for querying.

### Method
```python
await service.ingest_data_source(source_path, source_type=None, request_id=None)
```

### Input
- `source_path` (str): Path to data source (CSV, Excel, JSON, database)
- `source_type` (str, optional): Source type override ("csv", "json", etc.)
- `request_id` (str, optional): Custom request identifier

### Output
```json
{
  "success": true,
  "request_id": "ingest_123456789",
  "source_path": "/path/to/data.csv",
  "sqlite_database_path": "/path/to/sqlite/data.db",
  "pgvector_database": "analytics_db",
  "metadata_pipeline": {
    "tables_found": 1,
    "columns_found": 12,
    "business_entities": 5,
    "semantic_tags": 8,
    "embeddings_stored": 24,
    "search_ready": true,
    "ai_analysis_source": "intelligence_service"
  },
  "processing_time_ms": 5230.1,
  "cost_usd": 0.0012,
  "created_at": "2024-01-15T10:30:00"
}
```

## Function 2: Query Processing

### Purpose
Processes natural language queries against ingested data using SQLite database + pgvector embeddings.

### Method
```python
await service.query_with_language(natural_language_query, sqlite_database_path, pgvector_database=None, request_id=None)
```

### Input
- `natural_language_query` (str): User's natural language query
- `sqlite_database_path` (str): Path to SQLite database with the data
- `pgvector_database` (str, optional): Name of pgvector database (defaults to service database)
- `request_id` (str, optional): Custom request identifier

### Output
```json
{
  "success": true,
  "request_id": "query_123456789",
  "original_query": "Show customers from China",
  "sqlite_database_path": "/path/to/sqlite/data.db",
  "pgvector_database": "analytics_db",
  "query_processing": {
    "metadata_matches": 3,
    "sql_confidence": 0.85,
    "generated_sql": "SELECT * FROM customers WHERE Country = 'China'",
    "sql_explanation": "Query to find all customers located in China"
  },
  "results": {
    "row_count": 15,
    "data": [
      {"Customer Id": 1, "First Name": "John", "Country": "China"},
      {"Customer Id": 2, "First Name": "Mary", "Country": "China"}
    ],
    "columns": ["Customer Id", "First Name", "Last Name", "Country"]
  },
  "fallback_attempts": 0,
  "processing_time_ms": 1250.3,
  "error_message": null,
  "warnings": []
}
```

## Usage Example

```python
from tools.services.data_analytics_service.services.data_analytics_service import DataAnalyticsService

# Initialize service
service = DataAnalyticsService("my_analytics_db")

# Step 1: Ingest data source
ingestion_result = await service.ingest_data_source(
    source_path="./data/customers.csv",
    source_type="csv"
)

if ingestion_result["success"]:
    # Step 2: Query the data
    query_result = await service.query_with_language(
        natural_language_query="Show customers from China",
        sqlite_database_path=ingestion_result["sqlite_database_path"],
        pgvector_database=ingestion_result["pgvector_database"]
    )
    
    if query_result["success"]:
        print(f"Found {query_result['results']['row_count']} results")
        print(f"SQL: {query_result['query_processing']['generated_sql']}")
```

## Convenience Method

For end-to-end processing, use the convenience method that combines both functions:

```python
# Combined processing (Function 1 + Function 2)
result = await service.process_data_source_and_query(
    source_path="./data/customers.csv",
    natural_language_query="Show customers from China"
)
```

## Error Handling

Both functions return structured error information:

```json
{
  "success": false,
  "request_id": "error_123456789",
  "error_message": "CSV processing failed: File not found",
  "processing_time_ms": 120.5
}
```

## Dependencies

- SQLite database for structured data storage
- pgvector database for semantic embeddings
- AI services for semantic enrichment and SQL generation
- Intelligence service for fallback processing