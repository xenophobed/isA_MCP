# User Guide

Welcome to the isA_MCP User Guide! This comprehensive guide will help you master all the features and capabilities of the AI-powered Smart MCP Server.

## 🎯 What You'll Learn

This guide covers:
- **🔧 Basic Usage** - Essential operations and common workflows
- **🚀 Advanced Features** - AI-powered tools and automation
- **💡 Best Practices** - Optimization tips and recommendations  
- **🛠️ Troubleshooting** - Common issues and solutions
- **📊 Real-World Examples** - Practical use cases and scenarios

## 🌟 Key Capabilities Overview

### AI-Powered Intelligence
isA_MCP automatically selects the right tools for your queries using natural language understanding:

```
You: "I need to analyze sales data from my PostgreSQL database"
isA_MCP: Automatically selects ['data_sourcing', 'data_query'] tools
```

### Comprehensive Service Suite
- **📊 Data Analytics**: 5-step workflow for database analysis
- **🧩 Graph Analytics**: Entity extraction and knowledge graphs
- **🕸️ Web Services**: Intelligent web scraping with anti-detection
- **📚 Document Processing**: RAG-powered document Q&A
- **🛍️ E-commerce**: Full Shopify integration
- **🧮 Memory System**: Persistent information storage
- **🖼️ Image Generation**: AI-powered image creation

## 🚀 Quick Start Examples

### 1. Data Analysis Made Simple
```python
# Natural language to SQL - automatically handles the complexity
await client.call_tool("data_query", {
    "query": "Show me the top 10 customers by revenue this quarter",
    "connection_string": "postgresql://user:pass@host:5432/sales_db"
})

# The system automatically:
# 1. Analyzes your database schema
# 2. Understands your business entities  
# 3. Generates optimized SQL
# 4. Returns formatted results
```

### 2. Intelligent Web Scraping
```python
# AI-powered content extraction
await client.call_tool("scrape_webpage", {
    "url": "https://news.ycombinator.com",
    "extraction_schema": {
        "articles": ["title", "author", "score", "comments"]
    },
    "use_stealth": True,  # Anti-detection enabled
    "ai_filtering": True  # Smart content filtering
})
```

### 3. Knowledge Graph Building
```python
# Transform text into structured knowledge
await client.call_tool("graph_build_knowledge", {
    "source_content": "Dr. Sarah Johnson from MIT published a paper on quantum computing in Nature magazine in 2023.",
    "extract_entities": True,
    "extract_relations": True
})

# Automatically extracts:
# - Entities: Dr. Sarah Johnson (PERSON), MIT (ORG), Nature (ORG)
# - Relations: WORKS_FOR, PUBLISHED_IN, HAPPENED_AT
```

### 4. Document Question-Answering
```python
# Quick Q&A on any document
await client.call_tool("quick_rag_question", {
    "file_path": "/path/to/research_paper.pdf",
    "question": "What are the main findings of this research?"
})

# Supports: PDF, DOCX, PPT, TXT, and more
```

## 📋 Tool Categories & Usage

### 📊 Data Analytics Tools

#### `data_sourcing` - Database Metadata Extraction
**Purpose**: Analyze database structure and prepare for queries

```python
# Extract metadata from your database
result = await client.call_tool("data_sourcing", {
    "connection_string": "postgresql://user:pass@host:5432/db_name",
    "tables": ["customers", "orders", "products"],  # Optional: specific tables
    "generate_embeddings": True  # Enable semantic search
})

# Returns:
# - Table schemas and relationships
# - Column types and constraints  
# - Business entity mappings
# - Semantic embeddings for natural language queries
```

#### `data_query` - Natural Language to SQL
**Purpose**: Generate and execute SQL from natural language

```python
# Natural language database queries
result = await client.call_tool("data_query", {
    "query": "What are our best-selling products in the last 30 days?",
    "connection_string": "postgresql://user:pass@host:5432/db_name",
    "return_format": "json",  # json, csv, or table
    "explain_query": True     # Include SQL explanation
})

# Advanced queries
complex_result = await client.call_tool("data_query", {
    "query": "Compare revenue by region for Q3 vs Q4, show percentage change",
    "connection_string": "postgresql://user:pass@host:5432/db_name",
    "use_cache": True,        # Cache results for performance
    "max_rows": 1000         # Limit result size
})
```

### 🧩 Graph Analytics Tools

#### `graph_build_knowledge` - Knowledge Graph Construction
**Purpose**: Extract entities and relationships to build knowledge graphs

```python
# Process documents for knowledge extraction
result = await client.call_tool("graph_build_knowledge", {
    "source_file": "/path/to/document.pdf",
    "extract_entities": True,
    "extract_relations": True,
    "entity_types": ["PERSON", "ORG", "CONCEPT"],  # Filter entity types
    "confidence_threshold": 0.8,                   # Quality control
    "store_in_graph": True                         # Save to Neo4j
})

# Process text content directly
text_result = await client.call_tool("graph_build_knowledge", {
    "source_content": "Large text content here...",
    "chunk_size": 50000,      # Process in chunks for large texts
    "merge_entities": True,   # Deduplicate similar entities
    "extract_citations": True # Extract academic citations
})
```

#### `graph_search_knowledge` - Knowledge Graph Search
**Purpose**: Search and explore knowledge graphs

```python
# Semantic search in knowledge graph
search_result = await client.call_tool("graph_search_knowledge", {
    "query": "artificial intelligence researchers at Stanford",
    "search_type": "semantic",    # semantic, exact, or fuzzy
    "entity_types": ["PERSON", "ORG"],
    "max_results": 20,
    "include_relations": True,    # Include connected entities
    "similarity_threshold": 0.7   # Vector similarity threshold
})

# Graph traversal queries
traversal_result = await client.call_tool("graph_search_knowledge", {
    "query": "Show connections between MIT and quantum computing",
    "search_type": "graph_traversal",
    "max_depth": 3,              # Relationship depth
    "relation_types": ["WORKS_FOR", "RESEARCHES", "COLLABORATES_WITH"]
})
```

### 🕸️ Web Services Tools

#### `scrape_webpage` - Intelligent Web Scraping
**Purpose**: Extract structured data from web pages

```python
# Basic web scraping
result = await client.call_tool("scrape_webpage", {
    "url": "https://example-ecommerce.com/products",
    "extraction_schema": {
        "products": ["name", "price", "description", "rating"]
    }
})

# Advanced scraping with anti-detection
advanced_result = await client.call_tool("scrape_webpage", {
    "url": "https://protected-site.com",
    "extraction_schema": {
        "articles": ["title", "author", "content", "date"]
    },
    "use_stealth": True,          # Anti-detection measures
    "wait_for_js": True,          # Wait for JavaScript execution
    "custom_headers": {           # Custom HTTP headers
        "User-Agent": "Custom Agent"
    },
    "proxy_config": {             # Proxy configuration
        "enable": True,
        "type": "rotating"
    }
})
```

#### `scrape_multiple_pages` - Batch Web Scraping
**Purpose**: Scrape multiple pages with pagination support

```python
# Batch scraping with pagination
batch_result = await client.call_tool("scrape_multiple_pages", {
    "base_url": "https://news-site.com/articles",
    "max_pages": 10,
    "extraction_schema": {
        "articles": ["headline", "summary", "author", "date"]
    },
    "pagination_config": {
        "type": "url_pattern",     # url_pattern, next_button, or infinite_scroll
        "pattern": "?page={page}"
    },
    "filtering": {
        "min_content_length": 100, # Filter short articles
        "keywords": ["technology", "AI"]  # Content filtering
    }
})
```

### 📚 RAG & Document Tools

#### `quick_rag_question` - Document Q&A
**Purpose**: Ask questions about specific documents

```python
# Quick document analysis
result = await client.call_tool("quick_rag_question", {
    "file_path": "/path/to/contract.pdf",
    "question": "What are the termination clauses?",
    "include_sources": True,      # Include source references
    "context_window": 3          # Number of surrounding chunks
})

# Multiple questions on same document
multi_question = await client.call_tool("quick_rag_question", {
    "file_path": "/path/to/report.docx", 
    "questions": [
        "What is the executive summary?",
        "What are the key recommendations?",
        "What are the financial projections?"
    ],
    "response_format": "structured"  # Structured multi-answer response
})
```

#### `add_rag_documents` - Document Collection Management
**Purpose**: Build searchable document collections

```python
# Add documents to collection
result = await client.call_tool("add_rag_documents", {
    "collection_name": "company_policies",
    "documents": [
        {"path": "/docs/hr_policy.pdf", "metadata": {"department": "HR"}},
        {"path": "/docs/security_policy.docx", "metadata": {"department": "IT"}},
        {"content": "Direct text content", "metadata": {"type": "memo"}}
    ],
    "chunk_size": 1000,           # Text chunk size
    "overlap": 200,               # Chunk overlap
    "update_existing": True       # Update if documents exist
})
```

#### `search_rag_documents` - Collection Search
**Purpose**: Search across document collections

```python
# Search document collections
search_result = await client.call_tool("search_rag_documents", {
    "collection_name": "company_policies",
    "query": "remote work guidelines",
    "n_results": 10,
    "include_metadata": True,
    "filter": {                   # Metadata filtering
        "department": "HR",
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-12-31"
        }
    }
})
```

### 🛍️ E-commerce Tools (Shopify Integration)

#### `search_products` - Product Catalog Search
```python
# Search Shopify products
products = await client.call_tool("search_products", {
    "query": "wireless headphones",
    "limit": 20,
    "filters": {
        "price_range": {"min": 50, "max": 300},
        "availability": "available",
        "tags": ["electronics", "audio"]
    },
    "sort_by": "relevance"       # relevance, price, popularity
})
```

#### Complete E-commerce Workflow
```python
# 1. Search products
products = await client.call_tool("search_products", {
    "query": "smartphone cases"
})

# 2. Add to cart
cart = await client.call_tool("add_to_cart", {
    "product_id": products["data"]["products"][0]["id"],
    "quantity": 2,
    "variant_id": "specific_variant_id"  # Optional
})

# 3. View cart
cart_contents = await client.call_tool("view_cart", {
    "cart_id": cart["data"]["cart_id"]
})

# 4. Start checkout
checkout = await client.call_tool("start_checkout", {
    "cart_id": cart["data"]["cart_id"],
    "customer_info": {
        "email": "customer@example.com",
        "shipping_address": {
            "first_name": "John",
            "last_name": "Doe", 
            "address1": "123 Main St",
            "city": "New York",
            "zip": "10001",
            "country": "US"
        }
    }
})
```

### 🧮 Memory System Tools

#### Persistent Information Storage
```python
# Store information with categories
await client.call_tool("remember", {
    "key": "customer_preferences_john_doe",
    "value": "Prefers email notifications, interested in tech products, budget range $100-500",
    "category": "customer_data",
    "keywords": ["preferences", "email", "technology", "budget"],
    "expiration": "2025-12-31"   # Optional expiration date
})

# Search stored memories
memories = await client.call_tool("search_memories", {
    "query": "customer email preferences",
    "category": "customer_data",  # Optional category filter
    "limit": 10,
    "include_keywords": True
})

# Update existing memory
await client.call_tool("update_memory", {
    "key": "customer_preferences_john_doe",
    "value": "Updated preferences: SMS notifications preferred, increased budget to $1000",
    "update_keywords": True      # Regenerate keywords
})
```

### 🖼️ Image Generation Tools

#### AI Image Creation
```python
# Generate images from text
image_result = await client.call_tool("generate_image", {
    "prompt": "A futuristic cityscape with flying cars at sunset",
    "style": "photorealistic",   # photorealistic, artistic, cartoon
    "dimensions": "1024x1024",   # Standard sizes or custom
    "quality": "high"            # standard, high, ultra
})

# Generate and save to file
file_result = await client.call_tool("generate_image_to_file", {
    "prompt": "Logo design for a tech startup, minimalist style",
    "output_path": "/images/logo.png",
    "format": "PNG",             # PNG, JPG, WEBP
    "dimensions": "512x512"
})

# Transform existing images
transform_result = await client.call_tool("image_to_image", {
    "input_image_path": "/images/sketch.jpg",
    "prompt": "Convert this sketch to a photorealistic image",
    "strength": 0.7,             # Transformation strength (0.0-1.0)
    "output_path": "/images/realistic.jpg"
})
```

## 💡 Best Practices

### 1. **Optimize Database Queries**
```python
# Good: Specific and clear queries
query = "Show revenue by product category for Q4 2024, sorted by revenue descending"

# Avoid: Vague queries
query = "show me some data"

# Best: Include context and constraints
query = "Show top 10 customers by total order value in the last 6 months, include customer name, total spent, and number of orders"
```

### 2. **Efficient Web Scraping**
```python
# Use appropriate delays and stealth for protected sites
scrape_config = {
    "url": "https://example.com",
    "use_stealth": True,
    "delay_range": {"min": 1, "max": 3},  # Random delays
    "respect_robots_txt": True            # Follow site guidelines
}

# Cache results for repeated scraping
scrape_config = {
    "use_cache": True,
    "cache_duration": 3600  # 1 hour cache
}
```

### 3. **Memory Management**
```python
# Use descriptive keys and categories
good_memory = {
    "key": "customer_john_doe_preferences_2024",
    "category": "customer_preferences",
    "keywords": ["john", "doe", "email", "preferences"]
}

# Regular cleanup of expired memories
cleanup_config = {
    "auto_cleanup": True,
    "max_age_days": 365
}
```

### 4. **Cost Optimization**
```python
# Use caching to reduce AI API calls
query_config = {
    "use_cache": True,
    "cache_duration": 1800  # 30 minutes
}

# Batch operations when possible
batch_config = {
    "batch_size": 10,
    "concurrent_limit": 3
}
```

## 🎯 Common Workflows

### Business Intelligence Dashboard
```python
# 1. Connect to data sources
await client.call_tool("data_sourcing", {
    "connection_string": "postgresql://...",
    "tables": ["sales", "customers", "products"]
})

# 2. Generate insights
revenue_trend = await client.call_tool("data_query", {
    "query": "Show monthly revenue trend for the last 12 months"
})

top_products = await client.call_tool("data_query", {
    "query": "Top 10 products by revenue this quarter"
})

customer_analysis = await client.call_tool("data_query", {
    "query": "Customer segmentation by purchase frequency and value"
})
```

### Content Research & Analysis
```python
# 1. Scrape competitor websites
competitor_data = await client.call_tool("scrape_multiple_pages", {
    "base_url": "https://competitor.com/blog",
    "max_pages": 5,
    "extraction_schema": {"articles": ["title", "content", "date"]}
})

# 2. Build knowledge graph from content
knowledge = await client.call_tool("graph_build_knowledge", {
    "source_content": competitor_data["data"]["content"],
    "extract_entities": True,
    "extract_relations": True
})

# 3. Store insights in memory
await client.call_tool("remember", {
    "key": "competitor_analysis_q4_2024",
    "value": json.dumps(knowledge["data"]),
    "category": "market_research"
})
```

### Document Processing Pipeline
```python
# 1. Add documents to collection
await client.call_tool("add_rag_documents", {
    "collection_name": "legal_docs",
    "documents": [
        {"path": "/docs/contract1.pdf"},
        {"path": "/docs/contract2.pdf"}
    ]
})

# 2. Extract key information
key_terms = await client.call_tool("search_rag_documents", {
    "collection_name": "legal_docs",
    "query": "termination clauses and notice periods"
})

# 3. Build knowledge graph
contract_graph = await client.call_tool("graph_build_knowledge", {
    "source_content": key_terms["data"]["documents"],
    "entity_types": ["PERSON", "ORG", "DATE", "MONEY"],
    "extract_relations": True
})
```

---

**Next Sections:**
- [Basic Usage](basic-usage.md) - Step-by-step tutorials
- [Advanced Features](advanced-features.md) - Power user techniques
- [Best Practices](best-practices.md) - Optimization and efficiency tips
- [Troubleshooting](troubleshooting.md) - Common issues and solutions