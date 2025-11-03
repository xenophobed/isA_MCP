#!/usr/bin/env bash
#
# Graph RAG MCP Integration Test
#
# Tests Graph RAG functionality through MCP protocol
# Similar to test_simple_rag_mcp.sh but specifically for Graph RAG mode
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
TEST_USER="test_graph_rag_mcp_$$"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ Graph RAG MCP Integration Test Suite                          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  MCP URL: $MCP_URL"
echo "  Test User: $TEST_USER"
echo "  Test Type: Graph RAG via MCP (tools/call)"
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
TOOLS=$(echo "$HEALTH" | jq -r '.capabilities.tools' 2>/dev/null)

if [[ "$STATUS" == "ok" || "$STATUS" =~ ^healthy ]]; then
    if [ "$TOOLS" -gt 0 ]; then
        pass_test "MCP server is healthy with $TOOLS tools"
    else
        fail_test "MCP server health check failed - no tools registered"
        echo "Response: $HEALTH"
    fi
else
    fail_test "MCP server health check failed"
    echo "Response: $HEALTH"
fi

# ==============================================================================
# Test 2: Store Knowledge with Graph RAG Mode
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 2]${NC} Store Knowledge with Graph RAG Mode"

STORE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "content": "Artificial Intelligence was pioneered by John McCarthy. Machine Learning is a subset of AI developed by Arthur Samuel. Deep Learning is a subset of Machine Learning that uses neural networks. TensorFlow was created by Google and PyTorch by Facebook.",
      "content_type": "text",
      "metadata": {
        "source": "graph_rag_test",
        "topic": "AI_relationships"
      },
      "store_options": {
        "rag_mode": "graph",
        "chunk_size": 400
      }
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

echo "Store response preview: $(echo "$STORE_DATA" | head -c 200)"
echo ""

if [ "$STORE_SUCCESS" = "true" ]; then
    pass_test "Graph RAG storage successful"

    # Check if graph processing was used
    GRAPH_USED=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.graph_processing_used' 2>/dev/null)
    if [ "$GRAPH_USED" = "true" ]; then
        ENTITIES=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.entities_count' 2>/dev/null)
        RELATIONS=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.relationships_count' 2>/dev/null)
        info "Graph processing: $ENTITIES entities, $RELATIONS relationships"
    else
        info "Fallback mode used (graph components unavailable)"
    fi
else
    fail_test "Graph RAG storage failed"
    echo "Full response: $STORE_DATA"
fi

# ==============================================================================
# Test 3: Search with Graph RAG
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 3]${NC} Search Knowledge with Graph RAG"

SEARCH_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "What is the relationship between AI and Machine Learning?",
      "search_options": {
        "top_k": 5,
        "content_types": ["text"]
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

if [ "$SEARCH_SUCCESS" = "true" ]; then
    pass_test "Search with Graph RAG returned $SEARCH_RESULTS results"
else
    fail_test "Search with Graph RAG failed"
fi

# ==============================================================================
# Test 4: Knowledge Response with Graph RAG Mode
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 4]${NC} Knowledge Response with Graph RAG Mode"

RESPONSE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "knowledge_response",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "Explain the relationship between AI, Machine Learning, and Deep Learning",
      "response_options": {
        "rag_mode": "graph",
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

if [ "$RAG_SUCCESS" = "true" ] && [ -n "$RAG_ANSWER" ] && [ "$RAG_ANSWER" != "null" ]; then
    pass_test "Graph RAG response successful"
    info "Answer preview: ${RAG_ANSWER:0:150}..."

    # Check if graph RAG was used
    GRAPH_USED=$(echo "$RESPONSE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.graph_rag_used' 2>/dev/null)
    if [ "$GRAPH_USED" = "true" ]; then
        info "✓ Graph RAG retrieval was used"
    else
        info "Fallback retrieval method was used"
    fi
else
    fail_test "Graph RAG response failed"
fi

# ==============================================================================
# Test 5: Compare Graph RAG with Simple RAG
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 5]${NC} Store Same Content with Simple RAG (for comparison)"

SIMPLE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "${TEST_USER}_simple",
      "content": "Artificial Intelligence was pioneered by John McCarthy. Machine Learning is a subset of AI.",
      "content_type": "text",
      "metadata": {"source": "simple_rag_test"},
      "store_options": {
        "rag_mode": "simple"
      }
    }
  }
}
EOF
)

SIMPLE_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$SIMPLE_PAYLOAD")

SIMPLE_DATA=$(echo "$SIMPLE_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
SIMPLE_SUCCESS=$(echo "$SIMPLE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)

if [ "$SIMPLE_SUCCESS" = "true" ]; then
    pass_test "Simple RAG storage successful (comparison baseline)"
else
    skip_test "Simple RAG storage failed (comparison skipped)"
fi

# ==============================================================================
# Test 6: Verify Graph RAG is Registered in Available Modes
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 6]${NC} Verify Graph RAG Mode is Available"

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
RAG_MODES=$(echo "$STATUS_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.simplified_interface.supported_rag_modes[]' 2>/dev/null)

if echo "$RAG_MODES" | grep -q "graph"; then
    pass_test "Graph RAG mode is registered and available"
    info "Available RAG modes: $(echo "$RAG_MODES" | tr '\n' ', ' | sed 's/,$//')"
else
    fail_test "Graph RAG mode not found in available modes"
    echo "Available modes: $RAG_MODES"
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
    echo -e "${GREEN}✓ All Graph RAG MCP integration tests passed!${NC}"
    echo ""
    echo "✨ Graph RAG Integration Verified!"
    echo ""
    echo "The Graph RAG service is correctly:"
    echo "  ✓ Registered with MCP server"
    echo "  ✓ Accessible via MCP protocol"
    echo "  ✓ Processing store/search/response operations"
    echo "  ✓ Listed in available RAG modes"
    echo "  ✓ Using knowledge graph when available (with graceful fallback)"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check MCP server logs and Neo4j service availability"
    echo ""
    echo "Note: Graph RAG will fallback to traditional RAG if:"
    echo "  - Neo4j service is unavailable"
    echo "  - Graph components fail to initialize"
    echo "  - Entity extraction fails"
    echo ""
    exit 1
fi
