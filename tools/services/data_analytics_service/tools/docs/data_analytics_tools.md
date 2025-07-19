# Data Analytics Tools

MCP tools for intelligent data analytics workflows using the Data Analytics Service.

## Overview

The Data Analytics Tools provide five main MCP tools that wrap the Data Analytics Service functionality, making it accessible through the MCP protocol for AI agents and applications.

## Available Tools

### 1. `ingest_data_source`
**Function 1: Data Ingestion (Steps 1-3)**

Processes data sources and stores them in SQLite database + pgvector embeddings.

**Parameters:**
- `source_path` (required): Path to data source (CSV, Excel, JSON, database)
- `database_name` (optional): Analytics database name (default: "default_analytics")
- `source_type` (optional): Source type override ("csv", "json", "excel", etc.)
- `request_id` (optional): Custom request identifier

**Returns:**
- SQLite database path
- pgvector database name
- Processing metrics (tables found, columns found, embeddings stored)
- Cost and timing information

### 2. `query_with_language`
**Function 2: Query Processing (Steps 4-6)**

Processes natural language queries against ingested data using SQLite + pgvector embeddings.

**Parameters:**
- `natural_language_query` (required): User's natural language query
- `sqlite_database_path` (required): Path to SQLite database with the data
- `pgvector_database` (optional): Name of pgvector database
- `request_id` (optional): Custom request identifier

**Returns:**
- Generated SQL query
- Query results with row count and data
- Processing metrics (confidence, timing, fallback attempts)
- Query explanation

### 3. `process_data_source_and_query`
**Convenience Method: Complete End-to-End Processing**

Combines both functions for complete data analytics workflow.

**Parameters:**
- `source_path` (required): Path to data source
- `natural_language_query` (required): User's natural language query
- `database_name` (optional): Analytics database name (default: "default_analytics")
- `source_type` (optional): Source type override
- `request_id` (optional): Custom request identifier

**Returns:**
- Combined results from both ingestion and query processing
- Total processing time and cost
- Complete workflow status

### 4. `search_available_data`
**Search Processed Metadata**

Searches through all previously ingested data using semantic search.

**Parameters:**
- `search_query` (required): Natural language search query
- `database_name` (optional): Analytics database name (default: "default_analytics")
- `limit` (optional): Maximum results to return (default: 10)

**Returns:**
- Search results with similarity scores
- Entity names, types, and metadata
- Search statistics

### 5. `get_analytics_status`
**Service Status and Statistics**

Gets comprehensive analytics service status and statistics.

**Parameters:**
- `database_name` (optional): Analytics database name (default: "default_analytics")

**Returns:**
- Service configuration and health status
- Processing statistics (requests, success rates, costs)
- Database summary and available data
- Recent processing history

## Usage Examples

### Basic Two-Function Workflow

```python
# Step 1: Ingest data
result1 = await ingest_data_source(
    source_path="./data/customers.csv",
    database_name="customer_analytics"
)

# Step 2: Query the data
result2 = await query_with_language(
    natural_language_query="Show customers from China",
    sqlite_database_path=result1["sqlite_database_path"],
    pgvector_database=result1["pgvector_database"]
)
```

### End-to-End Processing

```python
# Complete workflow in one call
result = await process_data_source_and_query(
    source_path="./data/customers.csv",
    natural_language_query="Show customers from China",
    database_name="customer_analytics"
)
```

### Search and Status

```python
# Search processed data
search_results = await search_available_data(
    search_query="customer contact information",
    database_name="customer_analytics"
)

# Get service status
status = await get_analytics_status(
    database_name="customer_analytics"
)
```

## Tool Categories and Keywords

**Keywords for Discovery:**
- **Data Processing**: ingest, data, csv, excel, json, database, metadata, embeddings, process
- **Querying**: query, language, sql, natural, search, ask, find, show, list, get
- **Workflow**: complete, end-to-end, analytics, process, query, data, workflow
- **Search**: search, metadata, find, discover, explore, available, data
- **Monitoring**: status, analytics, statistics, service, info, health, summary

**Category**: `data_analytics`

## Pipeline Architecture

The tools implement a complete 6-step data analytics pipeline:

**Steps 1-3 (Data Ingestion):**
1. Metadata extraction from data sources
2. AI semantic enrichment of metadata
3. Embedding generation and pgvector storage

**Steps 4-6 (Query Processing):**
4. Query context extraction and metadata matching
5. AI-powered SQL generation
6. SQL execution with fallback mechanisms

## Error Handling

All tools return structured JSON responses with:
- `status`: "success" or "error"
- `operation`: Tool name that was called
- `data`: Tool-specific response data
- `message`: Error message if applicable
- `timestamp`: Response timestamp

## Performance

**Typical Performance:**
- Data Ingestion: 30-120 seconds depending on data size
- Query Processing: 5-15 seconds per query
- End-to-End: Sum of both operations
- Search: <1 second for metadata search
- Status: <1 second for status retrieval

## Dependencies

- Data Analytics Service
- SQLite for structured data storage
- pgvector for semantic embeddings
- AI services for enrichment and SQL generation
- Intelligence service for fallback processing