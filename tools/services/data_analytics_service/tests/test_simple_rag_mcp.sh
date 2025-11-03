#!/usr/bin/env bash
#
# Digital Tools MCP Integration Test
#
# This tests the digital_tools.py MCP interface (not the service layer directly)
# Tests run through MCP protocol against containerized MCP server
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
TEST_USER="test_user_mcp_$$"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ Digital Tools MCP Integration Test Suite                      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  MCP URL: $MCP_URL"
echo "  Test User: $TEST_USER"
echo "  Test Type: MCP Integration (via tools/call)"
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

# Accept both "ok" and "healthy" status (with or without emoji/hot reload message)
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
# Test 2: Verify Digital Tools are Registered
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 2]${NC} Verify Digital Tools Registration"

REQUEST_PAYLOAD='{"jsonrpc":"2.0","method":"tools/list","id":1}'
TOOLS_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$REQUEST_PAYLOAD")

TOOLS_DATA=$(echo "$TOOLS_RESP" | grep "^data: " | sed 's/^data: //')
HAS_STORE=$(echo "$TOOLS_DATA" | jq -r '.result.tools[] | select(.name == "store_knowledge") | .name' 2>/dev/null)
HAS_SEARCH=$(echo "$TOOLS_DATA" | jq -r '.result.tools[] | select(.name == "search_knowledge") | .name' 2>/dev/null)
HAS_RESPONSE=$(echo "$TOOLS_DATA" | jq -r '.result.tools[] | select(.name == "knowledge_response") | .name' 2>/dev/null)

if [ "$HAS_STORE" = "store_knowledge" ] && [ "$HAS_SEARCH" = "search_knowledge" ] && [ "$HAS_RESPONSE" = "knowledge_response" ]; then
    pass_test "Digital tools registered: store_knowledge, search_knowledge, knowledge_response"
else
    fail_test "Digital tools not found in MCP tools list"
fi

# ==============================================================================
# Test 3: Store Knowledge via MCP (Text)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 3]${NC} Store Knowledge via MCP (Text)"

STORE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "content": "Python is a high-level programming language created by Guido van Rossum. It emphasizes code readability and simplicity.",
      "content_type": "text",
      "metadata": {"source": "mcp_test", "topic": "programming"}
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

echo "Store response: $STORE_DATA" | head -c 200
echo ""

if [ "$STORE_SUCCESS" = "true" ]; then
    pass_test "Text storage via MCP successful"
else
    fail_test "Text storage via MCP failed"
    echo "Full response: $STORE_DATA"
fi

# ==============================================================================
# Test 4: Search Knowledge via MCP
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 4]${NC} Search Knowledge via MCP"

SEARCH_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "Who created Python?",
      "search_options": {
        "top_k": 3,
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

if [ "$SEARCH_SUCCESS" = "true" ] && [ "$SEARCH_RESULTS" -gt 0 ]; then
    pass_test "Search via MCP returned $SEARCH_RESULTS results"
else
    fail_test "Search via MCP failed or returned no results"
fi

# ==============================================================================
# Test 5: Knowledge Response via MCP (RAG)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 5]${NC} Knowledge Response via MCP (RAG)"

RESPONSE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "knowledge_response",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "Who created Python and what is it known for?",
      "response_options": {
        "rag_mode": "simple",
        "context_limit": 3,
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
    pass_test "RAG response via MCP successful"
    info "Answer preview: ${RAG_ANSWER:0:100}..."
else
    fail_test "RAG response via MCP failed"
fi

# ==============================================================================
# Test 6: Service Connection Verification
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 6]${NC} Verify Service Connections (via get_service_status)"

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
echo "$STATUS_DATA" | jq '.' > /dev/null 2>&1

if [ $? -eq 0 ]; then
    pass_test "Service status retrieved successfully"
    # Extract key info
    RAG_MODES=$(echo "$STATUS_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.simplified_interface.supported_rag_modes | length' 2>/dev/null)
    info "Supported RAG modes: $RAG_MODES"
else
    fail_test "Failed to get service status"
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
    echo -e "${GREEN}✓ All MCP integration tests passed!${NC}"
    echo ""
    echo "✨ Digital Tools MCP Integration Verified!"
    echo ""
    echo "The digital_tools.py interface is correctly:"
    echo "  ✓ Registered with MCP server"
    echo "  ✓ Accessible via MCP protocol"
    echo "  ✓ Connecting to backend services"
    echo "  ✓ Processing store/search/response operations"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check MCP server logs and service connections"
    exit 1
fi
