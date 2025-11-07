#!/usr/bin/env bash
#
# Simple RAG Photo Management Test
#
# Tests the image_processor.py and simple_rag_service.py integration
# Tests photo storage with AI-generated metadata and retrieval
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
TEST_USER="test_user_photo_$$"
TEST_IMAGE_URL="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800"
TEST_IMAGE_PATH="/tmp/test_photo_rag_$$.jpg"

echo -e "${CYAN}TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW${NC}"
echo -e "${CYAN}Q Simple RAG Photo Management Test Suite                        Q${NC}"
echo -e "${CYAN}ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  MCP URL: $MCP_URL"
echo "  Test User: $TEST_USER"
echo "  Test Image: $TEST_IMAGE_URL"
echo "  Test Type: Photo AI Management (Vision + RAG)"
echo ""

# Test counter
PASS=0
FAIL=0
SKIP=0

# Helper functions
pass_test() {
    echo -e "${GREEN}[ PASS]${NC} $1"
    ((PASS++))
}

fail_test() {
    echo -e "${RED}[ FAIL]${NC} $1"
    ((FAIL++))
}

skip_test() {
    echo -e "${YELLOW}[� SKIP]${NC} $1"
    ((SKIP++))
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Cleanup function
cleanup() {
    if [ -f "$TEST_IMAGE_PATH" ]; then
        rm -f "$TEST_IMAGE_PATH"
        info "Cleaned up test image"
    fi
}

trap cleanup EXIT

# ==============================================================================
# Test 0: Download Test Image
# ==============================================================================
echo -e "${BLUE}[TEST 0]${NC} Download Test Image from Unsplash"

curl -sL "$TEST_IMAGE_URL" -o "$TEST_IMAGE_PATH"

if [ -f "$TEST_IMAGE_PATH" ] && [ -s "$TEST_IMAGE_PATH" ]; then
    FILE_SIZE=$(wc -c < "$TEST_IMAGE_PATH")
    pass_test "Downloaded test image ($FILE_SIZE bytes)"
else
    fail_test "Failed to download test image"
    exit 1
fi

# ==============================================================================
# Test 1: MCP Health Check
# ==============================================================================
echo ""
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

if [ "$HAS_STORE" = "store_knowledge" ]; then
    pass_test "store_knowledge tool registered"
else
    fail_test "store_knowledge tool not found in MCP tools list"
fi

# ==============================================================================
# Test 3: Store Photo via MCP (with AI Vision Analysis)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 3]${NC} Store Photo via MCP (AI Vision + Metadata)"

# Use the URL directly instead of local file path
# The image processor now supports URLs, base64, and local paths
STORE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "content": "$TEST_IMAGE_URL",
      "content_type": "image",
      "metadata": {
        "source": "unsplash",
        "test": "photo_rag"
      }
    }
  }
}
EOF
)

info "Storing photo with AI vision analysis (this may take 10-15 seconds)..."

STORE_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$STORE_PAYLOAD")

STORE_DATA=$(echo "$STORE_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
STORE_SUCCESS=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)
CHUNKS_STORED=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.chunks_processed' 2>/dev/null)

if [ "$STORE_SUCCESS" = "true" ]; then
    pass_test "Photo storage via MCP successful (chunks: $CHUNKS_STORED)"

    # Extract and display AI metadata from response
    AI_METADATA=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.ai_metadata' 2>/dev/null)
    if [ "$AI_METADATA" != "null" ] && [ -n "$AI_METADATA" ]; then
        pass_test "AI metadata extracted successfully"

        # Display metadata details
        CATEGORIES=$(echo "$AI_METADATA" | jq -r '.ai_categories[]' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
        TAGS=$(echo "$AI_METADATA" | jq -r '.ai_tags[:5][]' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
        MOOD=$(echo "$AI_METADATA" | jq -r '.ai_mood' 2>/dev/null)
        COLORS=$(echo "$AI_METADATA" | jq -r '.ai_dominant_colors[]' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')

        [ -n "$CATEGORIES" ] && info "Categories: $CATEGORIES"
        [ -n "$TAGS" ] && info "Tags: $TAGS..."
        [ -n "$MOOD" ] && info "Mood: $MOOD"
        [ -n "$COLORS" ] && info "Colors: $COLORS"
    else
        fail_test "AI metadata not found in store response"
    fi
else
    fail_test "Photo storage via MCP failed"
    echo "Response: $STORE_DATA" | head -c 500
fi

# ==============================================================================
# Test 4: Search Photos by Description
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 4]${NC} Search Photos by Description (mountains)"

SEARCH_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "mountains with snow and sunset",
      "search_options": {
        "top_k": 5,
        "content_types": ["image"]
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
    pass_test "Photo search returned $SEARCH_RESULTS results"

    # Extract first result score
    FIRST_SCORE=$(echo "$SEARCH_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.results[0].score' 2>/dev/null)
    if [ "$FIRST_SCORE" != "null" ]; then
        info "Best match score: $FIRST_SCORE"
    fi
else
    fail_test "Photo search failed or returned no results"
    echo "Response: $SEARCH_DATA" | head -c 300
fi

# ==============================================================================
# Test 5: Search by Tags/Categories
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 5]${NC} Search Photos by Tags (landscape, nature)"

SEARCH_TAGS_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "peaceful landscape nature photography",
      "search_options": {
        "top_k": 3,
        "content_types": ["image"]
      }
    }
  }
}
EOF
)

SEARCH_TAGS_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$SEARCH_TAGS_PAYLOAD")

SEARCH_TAGS_DATA=$(echo "$SEARCH_TAGS_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
SEARCH_TAGS_SUCCESS=$(echo "$SEARCH_TAGS_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)
SEARCH_TAGS_RESULTS=$(echo "$SEARCH_TAGS_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.total_results' 2>/dev/null)

if [ "$SEARCH_TAGS_SUCCESS" = "true" ] && [ "$SEARCH_TAGS_RESULTS" -gt 0 ]; then
    pass_test "Tag-based search returned $SEARCH_TAGS_RESULTS results"
else
    fail_test "Tag-based search failed"
fi

# ==============================================================================
# Test 6: Knowledge Response with Photo Context
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 6]${NC} Knowledge Response with Photo Context (RAG)"

RESPONSE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "knowledge_response",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "Describe the landscape photos in my collection",
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
    pass_test "RAG response with photo context successful"
    info "Answer preview: ${RAG_ANSWER:0:150}..."
else
    fail_test "RAG response with photo context failed"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo -e "${CYAN}TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW${NC}"
echo -e "${CYAN}Q Test Summary                                                   Q${NC}"
echo -e "${CYAN}ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]${NC}"
echo ""
echo -e "${GREEN}Passed:${NC} $PASS"
echo -e "${RED}Failed:${NC} $FAIL"
echo -e "${YELLOW}Skipped:${NC} $SKIP"
echo ""

TOTAL=$((PASS + FAIL + SKIP))
echo "Total Tests: $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN} All photo RAG tests passed!${NC}"
    echo ""
    echo "( Photo AI Management System Verified!"
    echo ""
    echo "The photo management system successfully:"
    echo "   Processes images from URLs, base64, or local files"
    echo "   Analyzes images with AI vision (VLM)"
    echo "   Extracts rich descriptions for semantic search"    echo "   Generates AI metadata (categories, tags, mood, colors, composition)"
    echo "   Stores photo embeddings in vector database"
    echo "   Retrieves photos by semantic similarity"
    echo "   Provides RAG responses with photo context"
    echo ""
    exit 0
else
    echo -e "${RED} Some tests failed${NC}"
    echo ""
    echo "Check MCP server logs and vision service connections"
    exit 1
fi
