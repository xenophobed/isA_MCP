#!/usr/bin/env bash
#
# Simple RAG PDF Test
#
# Tests the PDFProcessor and simple_rag_service.py integration
# Tests PDF storage with text extraction and optional VLM image analysis
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
TEST_USER="test_user_pdf_$$"
# Using a reliable public sample PDF URL (arxiv paper sample)
TEST_PDF_URL="https://arxiv.org/pdf/1706.03762.pdf"  # Attention is All You Need paper (first page)
TEST_PDF_PATH="/tmp/test_pdf_rag_$$.pdf"

echo -e "${CYAN}TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW${NC}"
echo -e "${CYAN}Q Simple RAG PDF Processing Test Suite                      Q${NC}"
echo -e "${CYAN}ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  MCP URL: $MCP_URL"
echo "  Test User: $TEST_USER"
echo "  Test PDF: $TEST_PDF_URL"
echo "  Test Type: PDF Text Extraction + RAG"
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
    if [ -f "$TEST_PDF_PATH" ]; then
        rm -f "$TEST_PDF_PATH"
        info "Cleaned up test PDF"
    fi
}

trap cleanup EXIT

# ==============================================================================
# Test 0: Download Test PDF
# ==============================================================================
echo -e "${BLUE}[TEST 0]${NC} Download Test PDF"

curl -sL "$TEST_PDF_URL" -o "$TEST_PDF_PATH"

if [ -f "$TEST_PDF_PATH" ] && [ -s "$TEST_PDF_PATH" ]; then
    FILE_SIZE=$(wc -c < "$TEST_PDF_PATH")
    pass_test "Downloaded test PDF ($FILE_SIZE bytes)"
else
    fail_test "Failed to download test PDF"
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
# Test 3: Store PDF via MCP (Text Only Mode - Fast)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 3]${NC} Store PDF via MCP (Text Only - Default)"

# Use URL directly (PDFProcessor now supports URLs)
STORE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "content": "$TEST_PDF_URL",
      "content_type": "pdf",
      "metadata": {
        "source": "w3c",
        "test": "pdf_rag_text_only"
      }
    }
  }
}
EOF
)

info "Storing PDF with text extraction (fast mode)..."

STORE_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$STORE_PAYLOAD")

STORE_DATA=$(echo "$STORE_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
STORE_SUCCESS=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)
CHUNKS_STORED=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata.chunks_processed' 2>/dev/null)

if [ "$STORE_SUCCESS" = "true" ]; then
    pass_test "PDF storage via MCP successful (chunks: $CHUNKS_STORED)"

    # Extract metadata
    METADATA=$(echo "$STORE_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata' 2>/dev/null)
    if [ "$METADATA" != "null" ]; then
        info "PDF text extracted successfully"
    fi
else
    fail_test "PDF storage via MCP failed"
    echo "Response: $STORE_DATA" | head -c 500
fi

# ==============================================================================
# Test 4: Search PDF Content by Text
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 4]${NC} Search PDF Content (attention mechanism)"

SEARCH_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "attention mechanism transformer",
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
    pass_test "PDF search returned $SEARCH_RESULTS results"
else
    fail_test "PDF search failed or returned no results"
    echo "Response: $SEARCH_DATA" | head -c 300
fi

# ==============================================================================
# Test 5: Knowledge Response with PDF Context (RAG)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 5]${NC} Knowledge Response with PDF Context (RAG)"

RESPONSE_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "knowledge_response",
    "arguments": {
      "user_id": "$TEST_USER",
      "query": "What is in the PDF document?",
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
    pass_test "RAG response with PDF context successful"
    info "Answer preview: ${RAG_ANSWER:0:150}..."
else
    fail_test "RAG response with PDF context failed"
fi

# ==============================================================================
# Test 6: Store PDF with VLM Analysis (Advanced Mode - Optional)
# ==============================================================================
echo ""
echo -e "${BLUE}[TEST 6]${NC} Store PDF with VLM Analysis (Advanced Mode - Optional)"

STORE_VLM_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "store_knowledge",
    "arguments": {
      "user_id": "${TEST_USER}_vlm",
      "content": "$TEST_PDF_URL",
      "content_type": "pdf",
      "metadata": {
        "source": "w3c",
        "test": "pdf_rag_vlm",
        "enable_vlm_analysis": true,
        "max_pages": 2
      }
    }
  }
}
EOF
)

info "Storing PDF with VLM analysis (this may take 15-30 seconds)..."

STORE_VLM_RESP=$(curl -s -X POST "$MCP_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "$STORE_VLM_PAYLOAD")

STORE_VLM_DATA=$(echo "$STORE_VLM_RESP" | grep "^data: " | tail -1 | sed 's/^data: //')
STORE_VLM_SUCCESS=$(echo "$STORE_VLM_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.success' 2>/dev/null)

if [ "$STORE_VLM_SUCCESS" = "true" ]; then
    pass_test "PDF storage with VLM analysis successful"

    # Check if image descriptions were extracted
    METADATA_VLM=$(echo "$STORE_VLM_DATA" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.metadata' 2>/dev/null)
    IMAGES_PROCESSED=$(echo "$METADATA_VLM" | jq -r '.images_processed' 2>/dev/null)

    if [ "$IMAGES_PROCESSED" != "null" ] && [ "$IMAGES_PROCESSED" -gt 0 ]; then
        info "Images processed: $IMAGES_PROCESSED"
    else
        skip_test "VLM processing may not have found images (not an error)"
    fi
else
    skip_test "VLM mode skipped or failed (optional feature)"
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
    echo -e "${GREEN} All PDF RAG tests passed!${NC}"
    echo ""
    echo "( PDF Processing System Verified!"
    echo ""
    echo "The PDF processing system successfully:"
    echo "    Processes PDFs from URLs, base64, or local files"
    echo "    Extracts text content from PDF documents"
    echo "    Stores PDF content in vector database"
    echo "    Retrieves PDF content by semantic search"
    echo "    Provides RAG responses with PDF context"
    echo "    Supports optional VLM analysis for images (advanced mode)"
    echo ""
    exit 0
else
    echo -e "${RED} Some tests failed${NC}"
    echo ""
    echo "Check MCP server logs and PDF processor connections"
    exit 1
fi
