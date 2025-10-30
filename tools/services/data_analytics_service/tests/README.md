# Digital Tools Test Suite

## Overview

This directory contains comprehensive tests for the Digital Tools 3-function interface:
- `store_knowledge` - Universal storage for text, documents, images, and PDFs
- `search_knowledge` - Universal search with semantic, hybrid, and filtered options
- `knowledge_response` - Universal RAG response generation

## Test Files

### 1. `digital_tools_test.sh`
Comprehensive test suite with 23 tests covering:
- **9 Search Tests**: PDF search, text search, hybrid/semantic modes, filters, edge cases
- **8 RAG Response Tests**: Custom RAG, PDF context, multimodal, citations, temperature
- **4 Store Tests**: Text, document, PDF, image (currently skipped)
- **1 RAG Factory Test**: Mode switching validation
- **1 Service Status Test**: Health check

### 2. `seed_test_data.sh`
Seeds test data for the test user (`test_user_rag_page`) by storing 3 PDF documents:
- `test_data/bk01.pdf` - Large manual (10MB)
- `test_data/bk02.pdf` - Medium manual (8MB)
- `test_data/bk03.pdf` - Small manual (475KB)

### 3. `RAG_FACTORY_TEST_SUMMARY.md`
Documents the RAG Factory architecture migration and validation

## Quick Start

### Prerequisites

1. **MCP Server Running**
   ```bash
   # From project root
   python main.py
   # Should be accessible at http://localhost:8081
   ```

2. **Dependencies Running**
   - Supabase/PostgreSQL (for vector storage)
   - MinIO (for PDF image storage)
   - Consul (optional, for service discovery)

3. **Test Data Available**
   ```bash
   ls test_data/
   # Should show: bk01.pdf, bk02.pdf, bk03.pdf
   ```

### Running Tests

**Step 1: Seed Test Data** (First time only)
```bash
cd tools/services/data_analytics_service/tests
./seed_test_data.sh
```

Expected output:
```
✓ MCP server is healthy
✓ bk01.pdf stored successfully
✓ bk02.pdf stored successfully
✓ bk03.pdf stored successfully
✅ Success! Found X documents for user test_user_rag_page
```

**Step 2: Run Test Suite**
```bash
./digital_tools_test.sh
```

Expected output:
```
Total Tests:    23
Passed:         23
Failed:         0
Success Rate:   100.0%

🎉 ALL TESTS PASSED! ✓
```

## Understanding Test Failures

### Common Issues

#### 1. No Data Found (All Search/RAG Tests Fail)
**Symptom:**
```
[✗ FAIL] Search failed
[✗ FAIL] PDF RAG failed
Total Results: 0
```

**Root Cause:** No data seeded for `test_user_rag_page`

**Solution:**
```bash
./seed_test_data.sh
```

#### 2. MCP Server Not Reachable
**Symptom:**
```
[✗ FAIL] MCP server not reachable at http://localhost:8081
```

**Root Cause:** Server not running or wrong URL

**Solution:**
```bash
# Start server
python main.py

# Or specify different URL
MCP_URL=http://localhost:8080 ./digital_tools_test.sh
```

#### 3. Database Connection Errors
**Symptom:**
```
[✗ FAIL] Storage failed: connection refused
```

**Root Cause:** Supabase/PostgreSQL not running

**Solution:**
```bash
# Check resources/dbs/supabase/dev/docker-compose.yml
cd resources/dbs/supabase/dev
docker-compose up -d
```

#### 4. MinIO Upload Failures
**Symptom:**
```
⚠ PDF stored but photos=0 (expected >0)
```

**Root Cause:** MinIO not running or misconfigured

**Solution:**
```bash
# Check core/config.py for MinIO settings
# Start MinIO if using docker
docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"
```

## Test Architecture

### Test Flow

```
1. Health Check
   └─> curl /health endpoint

2. Search Tests
   ├─> Call search_knowledge with various options
   ├─> Parse SSE response
   ├─> Extract JSON from data field
   └─> Validate response structure

3. RAG Response Tests
   ├─> Call knowledge_response with query
   ├─> Check retrieval from vector DB
   ├─> Validate generated response
   └─> Check inline citations

4. Factory Tests
   └─> Validate RAG mode switching
```

### Response Format

All tools return standardized responses:

```json
{
  "status": "success",
  "action": "search_knowledge",
  "data": {
    "success": true,
    "search_results": [...],
    "total_results": 10,
    "total_photos": 5,
    "search_method": "custom_rag_multimodal",
    "context": {
      "timestamp": "2025-10-22T...",
      "user_id": "test_user_rag_page",
      "request_id": "1"
    }
  }
}
```

### SSE Parsing

The test script handles Server-Sent Events (SSE):

```bash
# Raw response has multiple events
event: message
data: {"method":"notifications/message",...}

event: message
data: {"jsonrpc":"2.0","id":1,"result":{...}}

# Script extracts the final result event
parse_sse_response() {
    echo "$response" | grep "^data: " | sed 's/^data: //' | head -1
}
```

## Configuration

### Environment Variables

```bash
# MCP Server URL (default: http://localhost:8081)
export MCP_URL=http://localhost:8081

# Test user (default: test_user_rag_page)
export TEST_USER_ID=test_user_rag_page

# Test data directory (default: test_data)
export TEST_DATA_DIR=test_data
```

### Test Parameters

Edit `digital_tools_test.sh` to modify:

- `top_k`: Number of search results (lines 119, 154, 176, etc.)
- `rag_mode`: RAG strategy ("custom", "simple", "crag", etc.)
- `context_limit`: Max context items for RAG
- `model`: LLM model ("gpt-4o-mini", "gpt-4o", etc.)
- `temperature`: Response creativity (0.0-1.0)

## Debugging

### Enable Verbose Output

```bash
# Add -x to see all commands
bash -x ./digital_tools_test.sh

# Or manually test single call
curl -X POST "http://localhost:8081/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "search_knowledge",
      "arguments": {
        "user_id": "test_user_rag_page",
        "query": "test",
        "search_options": {"top_k": 3}
      }
    }
  }'
```

### Check Server Logs

```bash
# Look for errors in main.py output
grep ERROR main.py.log

# Or run server with debug logging
LOG_LEVEL=DEBUG python main.py
```

### Verify Database

```bash
# Check if data was stored
# Connect to Supabase/PostgreSQL
psql -h localhost -U postgres -d postgres

# Query knowledge table
SELECT user_id, COUNT(*)
FROM knowledge_base
WHERE user_id = 'test_user_rag_page'
GROUP BY user_id;
```

## Test Coverage

### Covered Scenarios

✅ PDF multimodal search with custom RAG
✅ Filtered search (content_type, top_k)
✅ Hybrid vs semantic search modes
✅ Image search (if images stored)
✅ Mixed content search
✅ Reranking (if enabled)
✅ Context format returns
✅ Empty query handling
✅ Custom RAG mode with PDF context
✅ Auto-detect PDF content
✅ Multimodal RAG with images
✅ Inline citations
✅ Variable context limits
✅ Temperature variations
✅ No context edge cases
✅ RAG Factory mode switching
✅ Service health check

### Not Yet Covered

❌ Store operations (require write permissions setup)
❌ Concurrent requests
❌ Rate limiting
❌ Authentication/authorization
❌ Performance benchmarks
❌ Error recovery

## Contributing

### Adding New Tests

1. Add test function to `digital_tools_test.sh`:
```bash
test_my_new_feature() {
    print_test "my_new_feature - Description"
    TESTS_RUN=$((TESTS_RUN + 1))

    # Test logic here

    if [ success ]; then
        print_success "Test passed"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "Test failed"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}
```

2. Call it in `main()`:
```bash
main() {
    # ... existing tests ...
    test_my_new_feature
    # ...
}
```

3. Update test count in header:
```bash
echo -e "  Total Tests: 24 (9 search + 8 RAG + 4 store + 1 factory + 1 status + 1 new)"
```

### Test Guidelines

- **Descriptive names**: `test_search_pdf_with_citations`
- **Clear output**: Use `print_success`/`print_error`/`print_skip`
- **Validate structure**: Check both status and data fields
- **Handle edge cases**: Empty results, errors, timeouts
- **Document assumptions**: Data requirements, dependencies

## Troubleshooting Guide

| Issue | Check | Solution |
|-------|-------|----------|
| All tests fail | MCP server | `curl http://localhost:8081/health` |
| 0 results | Data seeded | `./seed_test_data.sh` |
| Connection refused | PostgreSQL | `docker-compose up -d` |
| MinIO errors | Storage config | Check `core/config.py` |
| Slow tests | Timeouts | Increase timeout in script |
| Random failures | Async timing | Add delays between tests |

## Status

**Last Updated:** 2025-10-22
**Test Suite Version:** v1.1
**Architecture:** RAG Factory with Unified Interface
**Total Tests:** 23
**Expected Pass Rate:** 100% (with data seeded)

## Next Steps

1. **Data Seeding** ✅ - Script created
2. **Run Full Suite** - Pending data seed
3. **CI/CD Integration** - Add to GitHub Actions
4. **Performance Tests** - Benchmark response times
5. **Load Tests** - Concurrent user simulation
6. **Error Recovery** - Test failure scenarios
