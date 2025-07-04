

---

## 6. Tool Testing and Discovery

**Endpoint:** `POST /discover`

All 42 MCP tools have been tested for AI-powered discovery. Below are the test results and examples.

### Tool Discovery Success Rate

- **Total Tools:** 42
- **Successfully Discoverable:** 42
- **Success Rate:** 100.0%
- **ISA Model Version:** 0.3.91 (Updated)

### Tool Categories and Examples

#### 🌤️ Weather Tools

**get_weather:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Check the weather in New York"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**clear_weather_cache:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Clear weather cache data"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**get_weather_cache_status:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Check weather cache status"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

#### 🧠 Memory Tools

**remember:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Remember some important information"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**forget:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Forget some stored information"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**update_memory:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Update my stored memories"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**search_memories:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Search through my memories"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

#### 🎨 Image Generation (ISA Client)

**generate_image:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Generate a beautiful image of a sunset"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

#### 🌐 Web Tools (ISA Client)

#### 🛒 E-commerce Tools

**search_products:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Search for laptop products"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**get_product_details:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Get details of a specific product"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**add_to_cart:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Add a product to shopping cart"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**view_cart:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "View my shopping cart"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**get_user_info:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Get my user profile information"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**save_shipping_address:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Save my shipping address"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**start_checkout:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Start the checkout process"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**process_payment:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Process payment for my order"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

#### 📚 RAG Tools (ISA Client)

**search_rag_documents:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Search for documents about machine learning"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**add_rag_documents:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Add documents to the knowledge base"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**list_rag_collections:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "List all document collections"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**get_rag_collection_stats:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Get statistics for document collections"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**delete_rag_documents:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Delete some documents"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**generate_rag_embeddings:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Generate embeddings for text"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**quick_rag_question:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Answer a question using RAG"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

#### 📊 Data Analytics (ISA Client)

**data_sourcing:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Source data from multiple databases"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**data_query:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Query database for sales analytics"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**generate_visualization:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Create a chart visualization"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

#### 🔒 Security & Monitoring

**get_authorization_requests:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Check pending authorization requests"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**approve_authorization:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Approve a security authorization"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**get_monitoring_metrics:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Get system monitoring metrics"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**get_audit_log:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "View security audit logs"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**ask_human:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Ask human for approval"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**request_authorization:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Request security authorization"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**check_security_status:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Check overall security status"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

#### ⚙️ Background Tasks

**create_background_task:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Create a background processing task"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**list_background_tasks:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "List all background tasks"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**pause_background_task:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Pause a running background task"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**resume_background_task:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Resume a paused background task"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**delete_background_task:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Delete a background task"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

#### 🤖 Autonomous Tasks

**plan_autonomous_task:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Plan an autonomous AI task"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**get_autonomous_status:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Check autonomous task status"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

#### 📝 Utility Tools

**format_response:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Format content in markdown"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

**get_event_sourcing_status:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Check event sourcing system status"}'
```

*Related tools discovered: plan_autonomous_task, get_autonomous_status, get_weather*

### ISA Client Integration Status

The following tools have been updated to use the new ISA Model client (v0.3.91):

- ✅ **generate_image** - ISA client integration verified
- ✅ **web_search** - ISA client integration verified
- ✅ **crawl_and_extract** - ISA client integration verified
- ✅ **search_rag_documents** - ISA client integration verified
- ✅ **data_query** - ISA client integration verified
- ✅ **generate_visualization** - ISA client integration verified

### Tool Discovery Examples

**Example 1 - Image Generation:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Generate a beautiful image of a sunset"}'
```

**Example 2 - Web Search:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Search the web for Python tutorials"}'
```

**Example 3 - Data Analytics:**
```bash
curl -X POST http://localhost:8081/discover \
  -H "Content-Type: application/json" \
  -d '{"request": "Query database for sales analytics"}'
```

