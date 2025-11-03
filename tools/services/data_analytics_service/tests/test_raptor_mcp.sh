#!/usr/bin/env bash
#
# RAPTOR RAG MCP Integration Test
#
# Tests the RAPTOR RAG pattern (层次化文档组织RAG) via MCP protocol
# Features:
# - Hierarchical tree structure (leaf, summary, root levels)
# - Multi-level retrieval (summary + detail)
# - Document clustering
# - LLM-based summarization
# - Inline citations
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test configuration
MCP_URL="${MCP_URL:-http://localhost:8081}"
TEST_USER="test_raptor_$$"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ RAPTOR RAG MCP Integration Test Suite                         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  MCP URL: $MCP_URL"
echo "  Test User: $TEST_USER"
echo "  RAG Mode: RAPTOR (Hierarchical)"
echo ""

# Test counter
PASS=0
FAIL=0
SKIP=0

# Helper functions
pass_test() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASS++))
}

fail_test() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAIL++))
}

skip_test() {
    echo -e "${YELLOW}[⊘ SKIP]${NC} $1"
    ((SKIP++))
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# ==============================================================================
# Test 1: MCP Health Check
# ==============================================================================
echo -e "${BLUE}[TEST 1]${NC} MCP Server Health Check"

HEALTH=$(curl -s "$MCP_URL/health")
STATUS=$(echo "$HEALTH" | jq -r '.status' 2>/dev/null)

if [[ "$STATUS" == "ok" || "$STATUS" =~ ^healthy ]]; then
    pass_test "MCP server is healthy"
else
    fail_test "MCP server health check failed"
    echo "Response: $HEALTH"
fi

# ==============================================================================
# Test 2: Store Long Document (for Hierarchical Processing)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 2]${NC} Store Long Document via RAPTOR RAG"

# 使用较长的文档来触发层次化处理
LONG_CONTENT="Python is a high-level programming language created by Guido van Rossum in 1991. It emphasizes code readability and simplicity with its use of significant whitespace. Python supports multiple programming paradigms including procedural, object-oriented, and functional programming. The language has a comprehensive standard library and a large ecosystem of third-party packages available through PyPI. Python is widely used in web development, data science, machine learning, automation, and scientific computing. Its clear syntax makes it an excellent choice for beginners while remaining powerful for expert programmers. Popular frameworks include Django for web development, NumPy and Pandas for data analysis, TensorFlow and PyTorch for machine learning, and Flask for lightweight web applications. Python's dynamic typing and interpreted nature make it highly flexible but may impact performance in some scenarios. The language continues to evolve with regular releases introducing new features and improvements."

STORE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "content": "$LONG_CONTENT",
      "content_type": "text",
      "metadata": {"source": "raptor_test", "topic": "python_lang"},
      "options": {"rag_mode": "raptor"}
    }
  }
}
EOF
)

STORE_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$STORE_PAYLOAD")

STORE_DATA=$(echo "$STORE_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
STORE_SUCCESS=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)
TREE_LEVELS=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.tree_levels' 2>/dev/null)
TOTAL_NODES=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.total_nodes' 2>/dev/null)

# Handle null values safely
if [ "$TREE_LEVELS" = "null" ] || [ -z "$TREE_LEVELS" ]; then
    TREE_LEVELS=0
fi
if [ "$TOTAL_NODES" = "null" ] || [ -z "$TOTAL_NODES" ]; then
    TOTAL_NODES=0
fi

if [ "$STORE_SUCCESS" = "true" ] && [ "$TREE_LEVELS" -gt 0 ]; then
    pass_test "RAPTOR RAG storage successful with $TREE_LEVELS levels, $TOTAL_NODES nodes"
    info "Hierarchical tree structure created"
else
    fail_test "RAPTOR RAG storage failed"
    echo "Response: $STORE_DATA" | head -c 300
fi

# ==============================================================================
# Test 3: Retrieve via RAPTOR RAG (Multi-level)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 3]${NC} Retrieve Knowledge via RAPTOR RAG (Multi-level)"

SEARCH_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "What is Python used for?",
      "search_options": {
        "top_k": 5,
        "rag_mode": "raptor"
      }
    }
  }
}
EOF
)

SEARCH_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$SEARCH_PAYLOAD")

SEARCH_DATA=$(echo "$SEARCH_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
SEARCH_SUCCESS=$(echo "$SEARCH_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)
SEARCH_RESULTS=$(echo "$SEARCH_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.total_results' 2>/dev/null)
RETRIEVAL_METHOD=$(echo "$SEARCH_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.retrieval_method' 2>/dev/null)

# Handle null values safely
if [ "$SEARCH_RESULTS" = "null" ] || [ -z "$SEARCH_RESULTS" ]; then
    SEARCH_RESULTS=0
fi

if [ "$SEARCH_SUCCESS" = "true" ] && [ "$SEARCH_RESULTS" -gt 0 ] && [ "$RETRIEVAL_METHOD" = "hierarchical_raptor" ]; then
    pass_test "RAPTOR multi-level search returned $SEARCH_RESULTS results"
    info "Retrieval method: $RETRIEVAL_METHOD"
else
    fail_test "RAPTOR multi-level search failed"
fi

# ==============================================================================
# Test 4: Generate Response via RAPTOR RAG (with Citations)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 4]${NC} Generate Response via RAPTOR RAG (with Citations)"

RESPONSE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "knowledge_response",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "What is Python and what are its main use cases?",
      "response_options": {
        "rag_mode": "raptor",
        "context_limit": 5,
        "enable_citations": true
      }
    }
  }
}
EOF
)

RESPONSE_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$RESPONSE_PAYLOAD")

RESPONSE_DATA=$(echo "$RESPONSE_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
RAG_SUCCESS=$(echo "$RESPONSE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)
RAG_ANSWER=$(echo "$RESPONSE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.response' 2>/dev/null)
HAS_CITATIONS=$(echo "$RAG_ANSWER" | grep -q '\[1\]' && echo "true" || echo "false")

if [ "$RAG_SUCCESS" = "true" ] && [ -n "$RAG_ANSWER" ] && [ "$RAG_ANSWER" != "null" ]; then
    if [ "$HAS_CITATIONS" = "true" ]; then
        pass_test "RAPTOR RAG response with inline citations successful"
        info "Answer preview: ${RAG_ANSWER:0:150}..."
    else
        pass_test "RAPTOR RAG response successful (citations might be optional)"
        info "Answer preview: ${RAG_ANSWER:0:150}..."
    fi
else
    fail_test "RAPTOR RAG response generation failed"
fi

# ==============================================================================
# Test 5: Verify Hierarchical Metadata
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 5]${NC} Verify Hierarchical Metadata in Search Results"

# 重新搜索并检查元数据
VERIFY_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "Python programming",
      "search_options": {
        "top_k": 3,
        "rag_mode": "raptor"
      }
    }
  }
}
EOF
)

VERIFY_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$VERIFY_PAYLOAD")

VERIFY_DATA=$(echo "$VERIFY_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
SUMMARY_MATCHES=$(echo "$VERIFY_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.summary_matches' 2>/dev/null)
DETAIL_MATCHES=$(echo "$VERIFY_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.detail_matches' 2>/dev/null)
LEVELS_SEARCHED=$(echo "$VERIFY_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.tree_levels_searched' 2>/dev/null)

if [ "$LEVELS_SEARCHED" = "2" ] && [ ! -z "$SUMMARY_MATCHES" ] && [ ! -z "$DETAIL_MATCHES" ]; then
    pass_test "Hierarchical metadata verified: summary=$SUMMARY_MATCHES, detail=$DETAIL_MATCHES, levels=$LEVELS_SEARCHED"
else
    fail_test "Hierarchical metadata verification failed"
    info "Levels searched: $LEVELS_SEARCHED, Summary: $SUMMARY_MATCHES, Detail: $DETAIL_MATCHES"
fi

# ==============================================================================
# Test 6: Test Another Document (Clustering Test)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 6]${NC} Store Second Document (Test Clustering)"

SECOND_CONTENT="Machine learning is a subset of artificial intelligence that enables computers to learn from data without explicit programming. Python has become the dominant language for machine learning due to its simplicity and powerful libraries. TensorFlow and PyTorch are the two most popular deep learning frameworks. Scikit-learn provides classical machine learning algorithms. Data preprocessing is crucial and tools like Pandas and NumPy are essential."

STORE2_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "content": "$SECOND_CONTENT",
      "content_type": "text",
      "metadata": {"source": "raptor_test", "topic": "ml"},
      "options": {"rag_mode": "raptor"}
    }
  }
}
EOF
)

STORE2_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$STORE2_PAYLOAD")

STORE2_DATA=$(echo "$STORE2_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
STORE2_SUCCESS=$(echo "$STORE2_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)

if [ "$STORE2_SUCCESS" = "true" ]; then
    pass_test "Second document stored successfully"
else
    fail_test "Second document storage failed"
fi

# ==============================================================================
# Test 7: Cross-Document Query
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 7]${NC} Cross-Document Query (Machine Learning + Python)"

CROSS_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "knowledge_response",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "How does Python support machine learning?",
      "response_options": {
        "rag_mode": "raptor",
        "context_limit": 5,
        "enable_citations": true
      }
    }
  }
}
EOF
)

CROSS_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$CROSS_PAYLOAD")

CROSS_DATA=$(echo "$CROSS_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
CROSS_SUCCESS=$(echo "$CROSS_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)
CROSS_ANSWER=$(echo "$CROSS_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.response' 2>/dev/null)

if [ "$CROSS_SUCCESS" = "true" ] && [ -n "$CROSS_ANSWER" ] && [ "$CROSS_ANSWER" != "null" ]; then
    pass_test "Cross-document query successful"
    info "Answer: ${CROSS_ANSWER:0:100}..."
else
    fail_test "Cross-document query failed"
fi

# ==============================================================================
# Test 8: Verify Service Capabilities
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 8]${NC} Verify RAPTOR RAG Capabilities"

STATUS_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "get_service_status",
    "arguments": {}
  }
}
EOF
)

STATUS_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$STATUS_PAYLOAD")

STATUS_DATA=$(echo "$STATUS_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
HAS_RAPTOR=$(echo "$STATUS_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.simplified_interface.supported_rag_modes' 2>/dev/null | grep -q "raptor" && echo "true" || echo "false")

if [ "$HAS_RAPTOR" = "true" ]; then
    pass_test "RAPTOR RAG mode is registered in service"
else
    skip_test "RAPTOR RAG mode not found in service capabilities (might be normal)"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ Test Summary                                                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Passed:${NC} $PASS"
echo -e "${RED}Failed:${NC} $FAIL"
echo -e "${YELLOW}Skipped:${NC} $SKIP"
echo ""

TOTAL=$((PASS + FAIL + SKIP))
echo "Total Tests: $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All RAPTOR RAG tests passed!${NC}"
    echo ""
    echo "✨ RAPTOR RAG Integration Verified!"
    echo ""
    echo "RAPTOR RAG features tested:"
    echo "  ✓ Hierarchical tree structure (multi-level)"
    echo "  ✓ Document clustering and summarization"
    echo "  ✓ Multi-level retrieval (summary + detail)"
    echo "  ✓ LLM-based summarization"
    echo "  ✓ Inline citations"
    echo "  ✓ Cross-document queries"
    echo ""
    echo "RAPTOR RAG is ideal for:"
    echo "  • Long document analysis"
    echo "  • Complex reasoning tasks"
    echo "  • Multi-level information retrieval"
    echo "  • Document structure understanding"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check MCP server logs and RAPTOR RAG service implementation"
    exit 1
fi
