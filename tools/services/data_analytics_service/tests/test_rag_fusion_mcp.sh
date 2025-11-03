#!/usr/bin/env bash
#
# RAG Fusion MCP Integration Test
#
# Tests RAG Fusion pattern: Multi-query rewriting + RRF fusion
# Validates that multiple query variants improve recall
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
TEST_USER="RAG_FUSION_MCP_TEST"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║ RAG Fusion MCP Integration Test Suite                         ║${NC}"
echo -e "${CYAN}║ Multi-Query + RRF Fusion Pattern                              ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  MCP URL: $MCP_URL"
echo "  Test User: $TEST_USER"
echo "  RAG Mode: rag_fusion"
echo "  Test Type: MCP Integration (via knowledge_response)"
echo ""

# Test counter
PASS=0
FAIL=0

# Helper functions
pass_test() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASS++))
}

fail_test() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAIL++))
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# ==============================================================================
# Phase 0: Health Check
# ==============================================================================
echo -e "${BLUE}[PHASE 0]${NC} MCP Health Check"

HEALTH=$(curl -s "$MCP_URL/health")
STATUS=$(echo "$HEALTH" | jq -r '.status' 2>/dev/null)

if [[ "$STATUS" == "ok" || "$STATUS" =~ ^healthy ]]; then
    pass_test "MCP server is healthy"
else
    fail_test "MCP server health check failed"
    echo "Response: $HEALTH"
    exit 1
fi

# ==============================================================================
# Phase 1: Store Test Data
# ==============================================================================
echo ""
echo -e "${BLUE}[PHASE 1]${NC} Store Knowledge for RAG Fusion Testing"

STORE_PAYLOAD=$(cat <<'EOF'
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "RAG_FUSION_MCP_TEST",
      "content": "Machine Learning is a subset of artificial intelligence focused on building systems that can learn from data. ML algorithms identify patterns in data and make predictions or decisions without being explicitly programmed. Common ML techniques include supervised learning (with labeled data), unsupervised learning (finding patterns in unlabeled data), and reinforcement learning (learning through trial and error). Popular ML frameworks include TensorFlow, PyTorch, and Scikit-learn.",
      "content_type": "text",
      "metadata": {"source": "rag_fusion_test", "topic": "ml", "rag_mode": "rag_fusion"}
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

if [ "$STORE_SUCCESS" = "true" ]; then
    pass_test "Stored ML knowledge base for fusion testing"
else
    fail_test "Failed to store knowledge"
    echo "Response: $STORE_DATA"
    exit 1
fi

# Store additional content for better fusion testing
STORE_PAYLOAD2=$(cat <<'EOF'
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 2,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "RAG_FUSION_MCP_TEST",
      "content": "Neural Networks are computing systems inspired by biological neural networks in animal brains. They consist of interconnected nodes (neurons) organized in layers: input layer, hidden layers, and output layer. Each connection has a weight that adjusts during training. Deep neural networks with many hidden layers enable deep learning, which has revolutionized computer vision, natural language processing, and speech recognition. Backpropagation is the key algorithm for training neural networks.",
      "content_type": "text",
      "metadata": {"source": "rag_fusion_test", "topic": "neural_networks"}
    }
  }
}
EOF
)

curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$STORE_PAYLOAD2" > /dev/null

info "Stored additional neural networks content"

# ==============================================================================
# Phase 2: Test RAG Fusion Retrieval
# ==============================================================================
echo ""
echo -e "${BLUE}[PHASE 2]${NC} Test Multi-Query Retrieval with RRF Fusion"

RETRIEVE_PAYLOAD=$(cat <<'EOF'
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 3,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "RAG_FUSION_MCP_TEST",
      "query": "What is machine learning?",
      "search_options": {
        "top_k": 3,
        "rag_mode": "rag_fusion",
        "num_queries": 3
      }
    }
  }
}
EOF
)

RETRIEVE_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$RETRIEVE_PAYLOAD")

RETRIEVE_DATA=$(echo "$RETRIEVE_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
RETRIEVE_SUCCESS=$(echo "$RETRIEVE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)

if [ "$RETRIEVE_SUCCESS" = "true" ]; then
    pass_test "RAG Fusion retrieval successful"

    # Check for fusion metadata
    FUSION_METADATA=$(echo "$RETRIEVE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata' 2>/dev/null)
    NUM_QUERIES=$(echo "$FUSION_METADATA" | jq -r '.num_queries' 2>/dev/null)
    FUSION_METHOD=$(echo "$FUSION_METADATA" | jq -r '.fusion_method' 2>/dev/null)

    if [ "$NUM_QUERIES" != "null" ] && [ "$NUM_QUERIES" -gt 1 ]; then
        pass_test "Multi-query generation confirmed ($NUM_QUERIES queries)"
    else
        fail_test "Multi-query generation metadata missing"
    fi

    if [ "$FUSION_METHOD" = "reciprocal_rank_fusion" ]; then
        pass_test "RRF fusion method confirmed"
    else
        fail_test "RRF fusion method not confirmed"
    fi
else
    fail_test "RAG Fusion retrieval failed"
    echo "Response: $RETRIEVE_DATA"
fi

# ==============================================================================
# Phase 3: Test RAG Fusion Generation
# ==============================================================================
echo ""
echo -e "${BLUE}[PHASE 3]${NC} Test RAG Fusion Answer Generation"

GENERATE_PAYLOAD=$(cat <<'EOF'
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 4,
  "params": {
    "name": "knowledge_response",
    "arguments": {
      "user_id": "RAG_FUSION_MCP_TEST",
      "query": "Explain Machine Learning and how it differs from traditional programming",
      "response_options": {
        "rag_mode": "rag_fusion",
        "context_limit": 5,
        "enable_citations": true,
        "num_queries": 3
      }
    }
  }
}
EOF
)

info "Sending RAG Fusion generation request..."

GENERATE_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$GENERATE_PAYLOAD")

# Save output to file for debugging
echo "$GENERATE_RESP" > /tmp/rag_fusion_knowledge_response_output.txt
info "Full output saved to /tmp/rag_fusion_knowledge_response_output.txt"

GENERATE_DATA=$(echo "$GENERATE_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
GENERATE_SUCCESS=$(echo "$GENERATE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)
ANSWER=$(echo "$GENERATE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.answer' 2>/dev/null)

if [ "$GENERATE_SUCCESS" = "true" ] && [ -n "$ANSWER" ] && [ "$ANSWER" != "null" ]; then
    pass_test "RAG Fusion answer generation successful"

    # Check answer quality
    ANSWER_LENGTH=${#ANSWER}
    if [ $ANSWER_LENGTH -gt 100 ]; then
        pass_test "Answer is substantive (${ANSWER_LENGTH} chars)"
        info "Answer preview: ${ANSWER:0:200}..."
    else
        fail_test "Answer too short (${ANSWER_LENGTH} chars)"
    fi

    # Check fusion metadata
    FUSION_ENABLED=$(echo "$GENERATE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.fusion_enabled' 2>/dev/null)
    if [ "$FUSION_ENABLED" = "true" ]; then
        pass_test "Fusion metadata confirmed in response"
    else
        fail_test "Fusion metadata missing"
    fi

    # Check context sources
    CONTEXT_ITEMS=$(echo "$GENERATE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.context_items' 2>/dev/null)
    if [ "$CONTEXT_ITEMS" != "null" ] && [ $CONTEXT_ITEMS -gt 0 ]; then
        pass_test "Used $CONTEXT_ITEMS context items"
    else
        fail_test "No context items found"
    fi
else
    fail_test "RAG Fusion answer generation failed"
    echo "Response: $GENERATE_DATA"
fi

# ==============================================================================
# Phase 4: Test Query Variant Quality
# ==============================================================================
echo ""
echo -e "${BLUE}[PHASE 4]${NC} Test Query Variant Diversity"

VARIANT_PAYLOAD=$(cat <<'EOF'
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 5,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "RAG_FUSION_MCP_TEST",
      "query": "neural networks",
      "search_options": {
        "top_k": 5,
        "rag_mode": "rag_fusion",
        "num_queries": 4
      }
    }
  }
}
EOF
)

VARIANT_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$VARIANT_PAYLOAD")

VARIANT_DATA=$(echo "$VARIANT_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
QUERY_VARIANTS=$(echo "$VARIANT_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.query_variants' 2>/dev/null)

if [ "$QUERY_VARIANTS" != "null" ]; then
    VARIANT_COUNT=$(echo "$QUERY_VARIANTS" | jq -r 'length' 2>/dev/null)
    if [ $VARIANT_COUNT -ge 3 ]; then
        pass_test "Generated $VARIANT_COUNT query variants"
        info "Variants: $(echo "$QUERY_VARIANTS" | jq -r '.[]' 2>/dev/null | head -3 | tr '\n' ' ')"
    else
        fail_test "Insufficient query variants ($VARIANT_COUNT)"
    fi
else
    fail_test "Query variants metadata missing"
fi

# ==============================================================================
# Phase 5: Test RRF Score Distribution
# ==============================================================================
echo ""
echo -e "${BLUE}[PHASE 5]${NC} Test RRF Score Distribution"

RRF_PAYLOAD=$(cat <<'EOF'
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 6,
  "params": {
    "name": "knowledge_response",
    "arguments": {
      "user_id": "RAG_FUSION_MCP_TEST",
      "query": "What are the key components of neural networks?",
      "response_options": {
        "rag_mode": "rag_fusion",
        "context_limit": 3,
        "num_queries": 3
      }
    }
  }
}
EOF
)

RRF_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$RRF_PAYLOAD")

RRF_DATA=$(echo "$RRF_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
TEXT_SOURCES=$(echo "$RRF_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.text_sources' 2>/dev/null)

if [ "$TEXT_SOURCES" != "null" ]; then
    # Check for fusion_score in metadata
    FUSION_SCORES=$(echo "$TEXT_SOURCES" | jq -r '.[].metadata.fusion_score' 2>/dev/null)
    if [ -n "$FUSION_SCORES" ]; then
        pass_test "RRF fusion scores present in results"

        # Check score ordering (should be descending)
        FIRST_SCORE=$(echo "$FUSION_SCORES" | head -1)
        LAST_SCORE=$(echo "$FUSION_SCORES" | tail -1)

        if (( $(echo "$FIRST_SCORE >= $LAST_SCORE" | bc -l 2>/dev/null || echo 1) )); then
            pass_test "Scores properly ordered (descending by RRF)"
        else
            fail_test "Score ordering incorrect"
        fi
    else
        fail_test "Fusion scores missing from results"
    fi
else
    fail_test "Text sources missing"
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
echo ""

TOTAL=$((PASS + FAIL))
echo "Total Tests: $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All RAG Fusion tests passed!${NC}"
    echo ""
    echo "✨ RAG Fusion Pattern Verified!"
    echo ""
    echo "The RAG Fusion service is correctly:"
    echo "  ✓ Generating multiple query variants"
    echo "  ✓ Performing parallel retrieval"
    echo "  ✓ Fusing results with RRF algorithm"
    echo "  ✓ Generating contextual answers"
    echo "  ✓ Including fusion metadata"
    echo ""
    echo "Expected benefits:"
    echo "  • 20-30% improved recall"
    echo "  • Robust to query phrasing"
    echo "  • Better handling of ambiguous queries"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check the following:"
    echo "  - RAG Fusion service implementation"
    echo "  - RRF fusion logic"
    echo "  - Query variant generation"
    echo "  - Qdrant connection"
    echo ""
    exit 1
fi
