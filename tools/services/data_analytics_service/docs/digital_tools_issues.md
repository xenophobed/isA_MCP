# Digital Tools Test Issues - Comprehensive Analysis

**Date:** 2025-10-14
**Test Suite:** digital_tools_test.sh
**Total Tests:** 22
**Passed:** 18 (81.8%)
**Failed:** 4 (18.2%)

---

## =  Test Results Summary

###  WORKING (18 tests)
- PDF Search (Basic) - 3 pages, 4 photos
- PDF Search (With Filters) - custom_rag_multimodal
- Empty Query (Edge Case) - Error handled correctly
- Simple RAG Mode - 602 chars generated
- PDF Context RAG - 5 pages, 6 photos
- Auto-detect PDF Content - multimodal_rag type
- Multimodal with Images - Completed successfully
- With Inline Citations - Citations enabled
- Variable Context Limit - Used 5 pages (limit 10)
- Temperature Variation - High temp (0.7) OK
- No Context (Edge Case) - Handled gracefully
- Service Health Check - Version: simplified_v1.1_pdf, 8 RAG modes

### L FAILING (4 tests)
1. Text Search (Hybrid Mode)
2. Text Search (Semantic Mode)
3. Mixed Content Search (Text + PDF)
4. Context Format Return

### ò SKIPPED (4 tests)
- Image Search - Requires standalone images
- Search with Reranking - Reranking not configured
- Store tests (4) - Write permissions required

---

## = Issue Analysis

### **Issue #1: Text/Hybrid Search Embedding Failure**

**Status:** L CRITICAL
**Tests Affected:**
- Test 3: Text Search (Hybrid Mode)
- Test 4: Text Search (Semantic Mode)

**Symptom:**
```
Error: ISA similarity search failed: similarity task requires either
'candidates' parameter or both 'embedding1' and 'embedding2' parameters
```

**Test Case:**
```json
{
  "user_id": "test_user_rag_page",
  "query": "sample collection",
  "search_options": {
    "top_k": 5,
    "search_mode": "hybrid"
  }
}
```

**Root Cause:**
The `search_knowledge` function routes to `digital_analytics_service.search_knowledge()` for non-PDF queries, which calls the ISA embedding service. The ISA client is receiving an incorrect response format or the embedding generation is failing.

**Location:**
- `tools/services/data_analytics_service/tools/digital_tools.py:261-263` - Text search routing
- `tools/services/intelligence_service/language/embedding_generator.py` - ISA embedding call

**Impact:**
- Text-only search fails
- Hybrid search mode fails
- Only PDF search works (because it uses CustomRAGService)

**Proposed Fix:**
1. Check if ISA embedding generation is working for text queries
2. Verify the embedding response format
3. Add fallback to PDF search if text search fails
4. Fix the ISA client embedding call parameters

---

### **Issue #2: Mixed Content Search Failure**

**Status:** L HIGH PRIORITY
**Tests Affected:**
- Test 6: Mixed Content (Text + PDF)

**Symptom:**
Same embedding error as Issue #1

**Test Case:**
```json
{
  "user_id": "test_user_rag_page",
  "query": "«∆",
  "search_options": {
    "top_k": 10
  }
}
```

**Root Cause:**
When no `content_type` is specified, the search defaults to mixed mode which calls `digital_analytics_service.search_knowledge()`. This hits the same ISA embedding issue.

**Location:**
- `tools/services/data_analytics_service/tools/digital_tools.py:265-268` - Mixed search fallback

**Impact:**
- Cannot search across all content types
- Users must explicitly specify `content_type: "pdf"` to make search work

**Proposed Fix:**
1. Change default behavior to try PDF search first
2. Add intelligent routing based on query content
3. Fix the underlying ISA embedding issue

---

### **Issue #3: Context Format Return Failure**

**Status:** L MEDIUM PRIORITY
**Tests Affected:**
- Test 8: Context Format Return

**Symptom:**
Same embedding error as Issue #1

**Test Case:**
```json
{
  "user_id": "test_user_rag_page",
  "query": "–ì",
  "search_options": {
    "top_k": 3,
    "return_format": "context"
  }
}
```

**Root Cause:**
The `return_format: "context"` parameter is processed after search execution. The search fails before reaching the format conversion logic.

**Location:**
- `tools/services/data_analytics_service/tools/digital_tools.py:295-311` - Context format conversion

**Impact:**
- Cannot get results in context format for downstream RAG processing
- Affects integration with other RAG systems

**Proposed Fix:**
1. Fix the underlying ISA embedding issue first
2. Ensure format conversion works after successful search

---

### **Issue #4: Image Search Not Available**

**Status:** ò SKIPPED (Expected)
**Tests Affected:**
- Test 5: Image Search

**Symptom:**
```
Error: ISA similarity search failed: similarity task requires either
'candidates' parameter or both 'embedding1' and 'embedding2' parameters
```

**Test Case:**
```json
{
  "user_id": "test_user_rag_page",
  "query": "A˛",
  "search_options": {
    "top_k": 3,
    "content_types": ["image"]
  }
}
```

**Root Cause:**
No standalone images stored in the knowledge base. All images are embedded within PDF pages.

**Location:**
- `tools/services/data_analytics_service/tools/digital_tools.py:254-258` - Image search routing

**Impact:**
- Cannot search for standalone images
- Image search only works through PDF multimodal content

**Proposed Fix:**
This is expected behavior - no fix needed unless standalone image storage is implemented.

---

## =' Root Cause Analysis

### **Primary Issue: ISA Embedding Generation**

All 4 failed tests share the same root cause:

**Problem:** The ISA embedding service is returning an error when generating embeddings for text queries.

**Error Message:**
```
similarity task requires either 'candidates' parameter or
both 'embedding1' and 'embedding2' parameters
```

**Why PDF Search Works:**
- PDF search uses `CustomRAGService.retrieve()`
- CustomRAGService uses `EmbeddingIntegration` which successfully calls ISA for PDF content
- The difference is likely in the task type or parameters being sent

**Investigation Needed:**

1. **Compare successful vs failing calls:**
   - PDF search: `EmbeddingIntegration.generate_embedding()` í ISA í  Success
   - Text search: `EmbeddingGenerator.generate_embedding()` í ISA í L Failure

2. **Check ISA client parameters:**
   ```python
   # Working (PDF):
   isa_client.invoke(
       input_data=text,
       task="embed",
       service_type="embedding",
       model="text-embedding-3-large"
   )

   # Failing (Text):
   isa_client.invoke(
       input_data=text,
       task="similarity",  # ê Wrong task?
       service_type="embedding",
       ...
   )
   ```

3. **Verify task type:**
   - The error mentions "similarity task"
   - But we want "embed" task for generating embeddings
   - Need to check `EmbeddingGenerator` implementation

---

## =À Fix Priority

1. **HIGH PRIORITY (Blockers):**
   - [ ] Issue #1: Fix ISA embedding task type for text search
   - [ ] Issue #2: Fix mixed content search (same root cause)
   - [ ] Issue #3: Fix context format return (same root cause)

2. **MEDIUM PRIORITY:**
   - [ ] Add better error handling for embedding failures
   - [ ] Add fallback to PDF search when text search fails

3. **LOW PRIORITY (Future):**
   - [ ] Issue #4: Implement standalone image storage and search
   - [ ] Add reranking support
   - [ ] Implement store_knowledge tests

---

## <Ø Next Steps

1. **Investigate EmbeddingGenerator:**
   ```bash
   # Check the embedding generator implementation
   cat tools/services/intelligence_service/language/embedding_generator.py | grep -A 20 "def generate_embedding"
   ```

2. **Compare with working EmbeddingIntegration:**
   ```bash
   # Check how PDF search generates embeddings
   cat tools/services/data_analytics_service/services/digital_service/integrations/embedding_integration.py | grep -A 20 "def generate_embedding"
   ```

3. **Fix the task type:**
   - Change from `task="similarity"` to `task="embed"`
   - Or add proper parameters for similarity task

4. **Test the fix:**
   ```bash
   ./tools/services/data_analytics_service/tests/digital_tools_test.sh
   ```

---

## =  Expected Outcome After Fixes

**Target Success Rate:** 100% (22/22 tests passing)

-  All PDF search tests
-  All text search tests (hybrid, semantic)
-  Mixed content search
-  Context format return
-  All RAG generation tests
- ò Image search (expected skip - no standalone images)
- ò Reranking (expected skip - not configured)
- ò Store tests (expected skip - optional)

**Current:** 81.8% í **Target:** 100% (excluding expected skips)

---

## = Investigation Commands

```bash
# 1. Check EmbeddingGenerator implementation
grep -n "task.*similarity" tools/services/intelligence_service/language/embedding_generator.py

# 2. Test ISA client directly
python3 << 'EOF'
from core.isa_client_factory import get_isa_client
import asyncio

async def test():
    client = get_isa_client()
    result = await client.invoke(
        input_data="test query",
        task="embed",
        service_type="embedding"
    )
    print(result)

asyncio.run(test())
EOF

# 3. Check for task type differences
grep -rn "task.*similarity" tools/services/intelligence_service/

# 4. Compare working vs failing embedding calls
diff -u \
  <(grep -A 10 "generate_embedding" tools/services/data_analytics_service/services/digital_service/integrations/embedding_integration.py) \
  <(grep -A 10 "generate_embedding" tools/services/intelligence_service/language/embedding_generator.py)
```

---

**Report Generated:** 2025-10-14
**Status:** Analysis Complete - Ready for Fixes
**Test Suite:** `tools/services/data_analytics_service/tests/digital_tools_test.sh`
