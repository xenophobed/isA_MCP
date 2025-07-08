# Tool Endpoints Reference

This document provides comprehensive reference for all available tools in the isA_MCP system, organized by service category.

## 📊 Data Analytics Tools

### `data_sourcing`
Extract metadata from databases and files for analysis preparation.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "connection_string": "postgresql://user:pass@host:5432/database",
  "tables": ["table1", "table2"],              // Optional: specific tables
  "generate_embeddings": true,                 // Optional: enable semantic search
  "cache_metadata": true,                      // Optional: cache results
  "include_relationships": true                // Optional: detect table relationships
}
```

#### Response
```json
{
  "status": "success",
  "action": "data_sourcing",
  "data": {
    "tables_processed": 5,
    "columns_analyzed": 47,
    "relationships_found": 12,
    "metadata": {
      "customers": {
        "columns": [
          {"name": "customer_id", "type": "integer", "primary_key": true},
          {"name": "name", "type": "varchar", "nullable": false},
          {"name": "email", "type": "varchar", "unique": true}
        ],
        "row_count": 1523,
        "business_entities": ["customer", "person", "contact"]
      }
    },
    "embeddings_generated": true
  },
  "billing": {
    "total_cost_usd": 0.0234,
    "operations": [
      {
        "operation_name": "metadata_analysis",
        "cost_usd": 0.0234,
        "timestamp": "2024-01-01T12:00:00Z"
      }
    ]
  }
}
```

#### Example Usage
```python
# Basic metadata extraction
result = await client.call_tool("data_sourcing", {
    "connection_string": "postgresql://user:pass@localhost:5432/sales_db"
})

# Advanced with specific tables and embeddings
result = await client.call_tool("data_sourcing", {
    "connection_string": "mysql://user:pass@localhost:3306/inventory", 
    "tables": ["products", "categories", "suppliers"],
    "generate_embeddings": True,
    "include_relationships": True
})
```

### `data_query`
Generate and execute SQL queries from natural language.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "query": "Show top 10 customers by revenue this quarter",
  "connection_string": "postgresql://user:pass@host:5432/database",
  "return_format": "json",                     // json, csv, table
  "explain_query": false,                      // Include SQL explanation
  "use_cache": true,                          // Use cached results if available
  "max_rows": 1000                            // Limit result size
}
```

#### Response
```json
{
  "status": "success", 
  "action": "data_query",
  "data": {
    "query_understood": "Top 10 customers by total revenue in Q4 2024",
    "sql_generated": "SELECT c.customer_id, c.name, SUM(o.total_amount) as revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_date >= '2024-10-01' GROUP BY c.customer_id, c.name ORDER BY revenue DESC LIMIT 10",
    "execution_time_ms": 245,
    "row_count": 10,
    "results": [
      {
        "customer_id": 1001,
        "name": "Acme Corp",
        "revenue": 125000.50
      }
    ],
    "explanation": "Query joins customers and orders tables, filters for Q4 2024, groups by customer, and sorts by total revenue."
  },
  "billing": {
    "total_cost_usd": 0.0156,
    "operations": [
      {
        "operation_name": "sql_generation",
        "cost_usd": 0.0156,
        "timestamp": "2024-01-01T12:05:00Z"
      }
    ]
  }
}
```

## 🧩 Graph Analytics Tools

### `graph_build_knowledge`
Extract entities and relationships to build knowledge graphs.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "source_content": "Text content to analyze",     // OR use source_file
  "source_file": "/path/to/document.pdf",           // File path alternative
  "extract_entities": true,
  "extract_relations": true,
  "entity_types": ["PERSON", "ORG", "CONCEPT"],    // Optional: filter types
  "confidence_threshold": 0.8,                      // Minimum confidence
  "store_in_graph": true,                           // Save to Neo4j
  "merge_entities": true,                           // Deduplicate entities
  "chunk_size": 50000                               // Text processing chunks
}
```

#### Response
```json
{
  "status": "success",
  "action": "graph_build_knowledge", 
  "data": {
    "entities_extracted": 15,
    "relations_extracted": 23,
    "graph_nodes_created": 15,
    "graph_edges_created": 23,
    "processing_time_ms": 3240,
    "entities": [
      {
        "id": "person_dr_sarah_johnson",
        "type": "PERSON",
        "canonical_form": "Dr. Sarah Johnson",
        "confidence": 0.95,
        "mentions": 3,
        "attributes": {
          "title": "Dr.",
          "first_name": "Sarah",
          "last_name": "Johnson"
        }
      }
    ],
    "relations": [
      {
        "id": "rel_001",
        "source": "person_dr_sarah_johnson", 
        "target": "org_mit",
        "type": "WORKS_FOR",
        "confidence": 0.93,
        "context": "Dr. Sarah Johnson from MIT"
      }
    ]
  },
  "billing": {
    "total_cost_usd": 0.0445,
    "operations": [
      {
        "operation_name": "entity_extraction",
        "cost_usd": 0.0234,
        "timestamp": "2024-01-01T12:10:00Z"
      },
      {
        "operation_name": "relation_extraction", 
        "cost_usd": 0.0211,
        "timestamp": "2024-01-01T12:10:30Z"
      }
    ]
  }
}
```

### `graph_search_knowledge`
Search knowledge graphs using vector similarity and graph traversal.

**Security Level**: LOW

#### Parameters
```json
{
  "query": "quantum computing researchers",
  "search_type": "semantic",                        // semantic, exact, graph_traversal
  "entity_types": ["PERSON", "ORG"],               // Optional: filter entity types
  "max_results": 20,
  "include_relations": true,                        // Include connected entities
  "similarity_threshold": 0.7,                     // Vector similarity threshold
  "max_depth": 2                                   // For graph traversal search
}
```

#### Response
```json
{
  "status": "success",
  "action": "graph_search_knowledge",
  "data": {
    "query_processed": "quantum computing researchers",
    "search_type": "semantic",
    "results_count": 8,
    "search_time_ms": 125,
    "entities": [
      {
        "id": "person_dr_sarah_johnson",
        "type": "PERSON", 
        "canonical_form": "Dr. Sarah Johnson",
        "similarity_score": 0.89,
        "connected_entities": [
          {
            "id": "org_mit",
            "type": "ORG",
            "relation": "WORKS_FOR"
          }
        ]
      }
    ],
    "graph_insights": {
      "research_institutions": ["MIT", "Stanford", "IBM Research"],
      "key_concepts": ["quantum algorithms", "quantum entanglement"],
      "collaboration_networks": 3
    }
  }
}
```

## 🕸️ Web Services Tools

### `scrape_webpage`
Extract structured data from web pages with AI assistance.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "url": "https://example.com/products",
  "extraction_schema": {
    "products": ["name", "price", "description", "rating"]
  },
  "use_stealth": true,                              // Anti-detection measures
  "wait_for_js": true,                             // Wait for JavaScript
  "custom_headers": {                              // Custom HTTP headers
    "User-Agent": "Custom Bot"
  },
  "ai_filtering": true,                            // AI-powered content filtering
  "proxy_config": {                                // Proxy settings
    "enable": true,
    "type": "rotating"
  }
}
```

#### Response
```json
{
  "status": "success",
  "action": "scrape_webpage",
  "data": {
    "url": "https://example.com/products",
    "extraction_time_ms": 2340,
    "items_extracted": 24,
    "page_info": {
      "title": "Product Catalog",
      "status_code": 200,
      "final_url": "https://example.com/products",
      "load_time_ms": 1200
    },
    "extracted_data": {
      "products": [
        {
          "name": "Wireless Headphones",
          "price": "$99.99",
          "description": "High-quality wireless headphones with noise cancellation",
          "rating": "4.5/5"
        }
      ]
    },
    "extraction_confidence": 0.92
  },
  "billing": {
    "total_cost_usd": 0.0167,
    "operations": [
      {
        "operation_name": "content_extraction",
        "cost_usd": 0.0167,
        "timestamp": "2024-01-01T12:15:00Z"
      }
    ]
  }
}
```

### `scrape_multiple_pages`
Batch scraping with pagination support.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "base_url": "https://example.com/articles",
  "max_pages": 5,
  "extraction_schema": {
    "articles": ["title", "author", "content", "date"]
  },
  "pagination_config": {
    "type": "url_pattern",                          // url_pattern, next_button, infinite_scroll
    "pattern": "?page={page}",
    "start_page": 1
  },
  "filtering": {
    "min_content_length": 100,                      // Filter short content
    "keywords": ["technology", "AI"],               // Keyword filtering
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  },
  "delay_config": {
    "min_delay": 1,                                 // Minimum delay between pages
    "max_delay": 3                                  // Maximum delay between pages
  }
}
```

#### Response
```json
{
  "status": "success",
  "action": "scrape_multiple_pages",
  "data": {
    "pages_processed": 5,
    "total_items_extracted": 87,
    "processing_time_ms": 12340,
    "pages_summary": [
      {
        "page_number": 1,
        "url": "https://example.com/articles?page=1",
        "items_found": 20,
        "success": true
      }
    ],
    "extracted_data": {
      "articles": [
        {
          "title": "The Future of AI",
          "author": "John Smith",
          "content": "Article content...",
          "date": "2024-01-15"
        }
      ]
    },
    "filtering_stats": {
      "total_items_found": 102,
      "items_after_filtering": 87,
      "filtered_out": 15
    }
  }
}
```

## 📚 RAG & Document Tools

### `quick_rag_question`
Ask questions about specific documents.

**Security Level**: LOW

#### Parameters
```json
{
  "file_path": "/path/to/document.pdf",            // OR use file_content
  "file_content": "Direct text content",          // Alternative to file_path
  "question": "What are the main findings?",       // OR use questions for multiple
  "questions": [                                   // Multiple questions
    "What is the executive summary?",
    "What are the recommendations?"
  ],
  "include_sources": true,                         // Include source references
  "context_window": 3,                            // Number of surrounding chunks
  "response_format": "detailed"                   // simple, detailed, structured
}
```

#### Response
```json
{
  "status": "success",
  "action": "quick_rag_question",
  "data": {
    "file_processed": "/path/to/document.pdf",
    "file_info": {
      "pages": 45,
      "word_count": 12340,
      "format": "PDF"
    },
    "question": "What are the main findings?",
    "answer": "The main findings of this research include: 1) Significant improvement in accuracy using the proposed method, 2) Reduced computational requirements compared to baseline approaches, 3) Strong generalization across different datasets.",
    "confidence": 0.87,
    "sources": [
      {
        "chunk_id": "chunk_23",
        "page": 15,
        "content": "Results show 23% improvement in accuracy...",
        "relevance_score": 0.92
      }
    ],
    "processing_time_ms": 2100
  },
  "billing": {
    "total_cost_usd": 0.0089,
    "operations": [
      {
        "operation_name": "document_qa",
        "cost_usd": 0.0089,
        "timestamp": "2024-01-01T12:20:00Z"
      }
    ]
  }
}
```

### `add_rag_documents`
Add documents to searchable collections.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "collection_name": "company_policies",
  "documents": [
    {
      "path": "/docs/policy1.pdf",
      "metadata": {"department": "HR", "version": "2.1"}
    },
    {
      "content": "Direct text content",
      "metadata": {"type": "memo", "author": "John Doe"}
    }
  ],
  "chunk_size": 1000,                             // Text chunk size
  "overlap": 200,                                 // Chunk overlap
  "update_existing": true,                        // Update if exists
  "generate_summary": true                        // Generate document summaries
}
```

#### Response
```json
{
  "status": "success",
  "action": "add_rag_documents",
  "data": {
    "collection_name": "company_policies",
    "documents_processed": 2,
    "chunks_created": 45,
    "embeddings_generated": 45,
    "processing_time_ms": 3450,
    "documents_summary": [
      {
        "document_id": "doc_001",
        "path": "/docs/policy1.pdf",
        "chunks": 23,
        "summary": "Document outlining HR policies for remote work...",
        "metadata": {"department": "HR", "version": "2.1"}
      }
    ],
    "collection_stats": {
      "total_documents": 15,
      "total_chunks": 234
    }
  }
}
```

### `search_rag_documents`
Search across document collections.

**Security Level**: LOW

#### Parameters
```json
{
  "collection_name": "company_policies",
  "query": "remote work guidelines",
  "n_results": 10,
  "include_metadata": true,
  "filter": {                                     // Metadata filtering
    "department": "HR",
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  },
  "search_type": "hybrid",                        // vector, keyword, hybrid
  "rerank": true                                  // Re-rank results
}
```

#### Response
```json
{
  "status": "success",
  "action": "search_rag_documents",
  "data": {
    "collection_name": "company_policies",
    "query": "remote work guidelines",
    "search_type": "hybrid",
    "results_count": 8,
    "search_time_ms": 156,
    "documents": [
      {
        "document_id": "doc_001",
        "chunk_id": "chunk_12",
        "content": "Remote work policy allows employees to work from home up to 3 days per week...",
        "score": 0.89,
        "metadata": {
          "department": "HR",
          "document_title": "Remote Work Policy 2024",
          "page": 3
        }
      }
    ],
    "facets": {
      "departments": {"HR": 5, "IT": 2, "Finance": 1},
      "document_types": {"policy": 6, "memo": 2}
    }
  }
}
```

## 🛍️ E-commerce Tools (Shopify)

### `search_products`
Search Shopify product catalog.

**Security Level**: LOW

#### Parameters
```json
{
  "query": "wireless headphones",
  "limit": 20,
  "filters": {
    "price_range": {"min": 50, "max": 300},
    "availability": "available",                   // available, unavailable, any
    "tags": ["electronics", "audio"],
    "vendor": "Brand Name",
    "product_type": "Electronics"
  },
  "sort_by": "relevance",                         // relevance, price_asc, price_desc, newest
  "include_variants": true,                       // Include product variants
  "include_images": true                          // Include product images
}
```

#### Response
```json
{
  "status": "success",
  "action": "search_products",
  "data": {
    "query": "wireless headphones",
    "total_found": 23,
    "returned": 20,
    "search_time_ms": 234,
    "products": [
      {
        "id": "prod_001",
        "title": "Premium Wireless Headphones",
        "handle": "premium-wireless-headphones",
        "price": "$199.99",
        "compare_at_price": "$249.99",
        "availability": "available",
        "inventory_quantity": 45,
        "description": "High-quality wireless headphones with active noise cancellation",
        "vendor": "AudioTech",
        "product_type": "Electronics",
        "tags": ["electronics", "audio", "wireless", "premium"],
        "images": [
          {
            "url": "https://cdn.shopify.com/image1.jpg",
            "alt": "Front view of headphones"
          }
        ],
        "variants": [
          {
            "id": "var_001",
            "title": "Black",
            "price": "$199.99",
            "available": true,
            "inventory_quantity": 25
          }
        ]
      }
    ],
    "facets": {
      "price_ranges": {
        "$0-$50": 2,
        "$50-$100": 8,
        "$100-$200": 10,
        "$200+": 3
      },
      "vendors": {
        "AudioTech": 5,
        "SoundPro": 4,
        "WirelessPlus": 3
      }
    }
  }
}
```

### `add_to_cart`
Add products to shopping cart.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "product_id": "prod_001",
  "quantity": 2,
  "variant_id": "var_001",                        // Optional: specific variant
  "cart_id": "cart_123",                          // Optional: existing cart
  "line_item_properties": {                       // Optional: custom properties
    "gift_message": "Happy Birthday!",
    "engraving": "John's Headphones"
  }
}
```

#### Response
```json
{
  "status": "success",
  "action": "add_to_cart",
  "data": {
    "cart_id": "cart_123",
    "line_item_added": {
      "id": "line_001",
      "product_id": "prod_001",
      "variant_id": "var_001",
      "title": "Premium Wireless Headphones - Black",
      "quantity": 2,
      "price": "$199.99",
      "line_price": "$399.98",
      "properties": {
        "gift_message": "Happy Birthday!"
      }
    },
    "cart_summary": {
      "item_count": 3,
      "total_price": "$599.97",
      "subtotal_price": "$599.97",
      "total_weight": 850,
      "currency": "USD"
    }
  }
}
```

## 🧮 Memory Tools

### `remember`
Store information with categories and keywords.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "key": "customer_john_doe_preferences",
  "value": "Prefers email notifications, interested in tech products, budget range $100-500",
  "category": "customer_data",                    // Optional: categorization
  "keywords": ["john", "doe", "email", "tech"],  // Optional: manual keywords
  "metadata": {                                   // Optional: additional metadata
    "source": "CRM",
    "confidence": 0.9,
    "last_updated": "2024-01-01"
  },
  "expiration": "2025-12-31",                     // Optional: expiration date
  "auto_keywords": true                           // Auto-generate keywords
}
```

#### Response
```json
{
  "status": "success",
  "action": "remember",
  "data": {
    "memory_id": "mem_001",
    "key": "customer_john_doe_preferences",
    "stored": true,
    "category": "customer_data",
    "keywords": ["john", "doe", "email", "tech", "preferences", "budget"],
    "embedding_generated": true,
    "expiration": "2025-12-31",
    "storage_time_ms": 123
  }
}
```

### `search_memories`
Search stored memories with semantic similarity.

**Security Level**: LOW

#### Parameters
```json
{
  "query": "customer email preferences",
  "category": "customer_data",                    // Optional: filter by category
  "limit": 10,
  "include_keywords": true,
  "include_metadata": true,
  "similarity_threshold": 0.7,                   // Minimum similarity score
  "sort_by": "relevance",                        // relevance, date, alphabetical
  "date_range": {                                // Optional: date filtering
    "start": "2024-01-01",
    "end": "2024-12-31"
  }
}
```

#### Response
```json
{
  "status": "success",
  "action": "search_memories",
  "data": {
    "query": "customer email preferences",
    "results_count": 3,
    "search_time_ms": 89,
    "memories": [
      {
        "memory_id": "mem_001",
        "key": "customer_john_doe_preferences",
        "value": "Prefers email notifications, interested in tech products, budget range $100-500",
        "category": "customer_data",
        "similarity_score": 0.92,
        "keywords": ["john", "doe", "email", "tech", "preferences"],
        "metadata": {
          "source": "CRM",
          "last_updated": "2024-01-01"
        },
        "created_at": "2024-01-01T10:00:00Z"
      }
    ],
    "facets": {
      "categories": {"customer_data": 3, "preferences": 2},
      "keywords": {"email": 3, "tech": 2, "preferences": 3}
    }
  }
}
```

## 🖼️ Image Generation Tools

### `generate_image`
Create images from text prompts.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "prompt": "A futuristic cityscape with flying cars at sunset",
  "style": "photorealistic",                     // photorealistic, artistic, cartoon, anime
  "dimensions": "1024x1024",                     // 512x512, 1024x1024, 1024x1792, etc.
  "quality": "high",                             // standard, high, ultra
  "negative_prompt": "blurry, low quality",     // What to avoid
  "steps": 30,                                   // Generation steps
  "guidance_scale": 7.5,                        // Prompt adherence
  "seed": 12345                                  // Optional: reproducible results
}
```

#### Response
```json
{
  "status": "success",
  "action": "generate_image",
  "data": {
    "prompt": "A futuristic cityscape with flying cars at sunset",
    "image_generated": true,
    "image_data": "base64_encoded_image_data...",
    "image_format": "PNG",
    "dimensions": "1024x1024",
    "generation_time_ms": 4500,
    "parameters_used": {
      "style": "photorealistic",
      "quality": "high",
      "steps": 30,
      "seed": 12345
    }
  },
  "billing": {
    "total_cost_usd": 0.0234,
    "operations": [
      {
        "operation_name": "image_generation",
        "cost_usd": 0.0234,
        "timestamp": "2024-01-01T12:30:00Z"
      }
    ]
  }
}
```

### `generate_image_to_file`
Generate and save images to files.

**Security Level**: MEDIUM

#### Parameters
```json
{
  "prompt": "Logo design for a tech startup, minimalist style",
  "output_path": "/images/logo.png",
  "format": "PNG",                               // PNG, JPG, WEBP
  "dimensions": "512x512",
  "style": "artistic",
  "background": "transparent",                   // transparent, white, black
  "quality": "high"
}
```

#### Response
```json
{
  "status": "success",
  "action": "generate_image_to_file",
  "data": {
    "prompt": "Logo design for a tech startup, minimalist style",
    "output_path": "/images/logo.png",
    "file_saved": true,
    "file_size_bytes": 245760,
    "dimensions": "512x512",
    "format": "PNG",
    "generation_time_ms": 3200
  }
}
```

---

## 🔧 Common Parameters

### Security Levels
- **LOW**: Read-only operations, basic queries
- **MEDIUM**: Data modification, API calls with costs  
- **HIGH**: Administrative functions, data deletion

### Response Format
All tools return responses in this standardized format:
```json
{
  "status": "success|error",
  "action": "tool_name",
  "data": { /* tool-specific response data */ },
  "billing": { /* cost tracking information */ },
  "timestamp": "2024-01-01T12:00:00Z",
  "error": "error message if status is error"
}
```

### Billing Information
Cost tracking is included in all AI-powered operations:
```json
{
  "billing": {
    "total_cost_usd": 0.0234,
    "operations": [
      {
        "operation_name": "llm_call",
        "cost_usd": 0.0234,
        "tokens_used": 1500,
        "model": "gpt-4.1-nano",
        "timestamp": "2024-01-01T12:00:00Z"
      }
    ],
    "currency": "USD"
  }
}
```

### Error Handling
Error responses include detailed information:
```json
{
  "status": "error",
  "action": "tool_name",
  "error": "Detailed error message",
  "error_code": "VALIDATION_ERROR",
  "error_details": {
    "field": "parameter_name",
    "reason": "Parameter is required"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

**Related Documentation:**
- [API Authentication](authentication.md) - Authentication and authorization
- [Service APIs](services.md) - Service-specific endpoints
- [Error Handling](error-handling.md) - Error codes and troubleshooting