#!/bin/bash
#
# Test Data Seeding Script for Digital Tools
# Seeds test data for user: test_user_rag_page
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
MCP_URL="${MCP_URL:-http://localhost:8081}"
MCP_ENDPOINT="${MCP_URL}/mcp"
TEST_USER_ID="test_user_rag_page"

# Helper function for MCP calls
call_mcp_tool() {
    local tool_name=$1
    local arguments=$2

    curl -s -X POST "${MCP_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -H "Accept: text/event-stream" \
        -d "{
  \"jsonrpc\": \"2.0\",
  \"id\": 1,
  \"method\": \"tools/call\",
  \"params\": {
    \"name\": \"${tool_name}\",
    \"arguments\": ${arguments}
  }
}"
}

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║ Seeding Test Data for Digital Tools${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${YELLOW}Configuration:${NC}"
echo -e "  MCP URL: $MCP_URL"
echo -e "  Test User: $TEST_USER_ID"
echo -e "  Test Data: test_data/bk01.pdf, bk02.pdf, bk03.pdf\n"

# Check server health
echo -e "${BLUE}[1/4]${NC} Checking MCP server..."
if ! curl -s "${MCP_URL}/health" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ MCP server not reachable at ${MCP_URL}${NC}"
    exit 1
fi
echo -e "${GREEN}✓ MCP server is healthy${NC}\n"

# Store PDF 1 (bk01.pdf)
echo -e "${BLUE}[2/4]${NC} Storing test_data/bk01.pdf..."
RESULT=$(call_mcp_tool "store_knowledge" '{
  "user_id": "'"${TEST_USER_ID}"'",
  "content": "test_data/bk01.pdf",
  "content_type": "pdf",
  "metadata": {"source": "test_suite", "document": "bk01"},
  "options": {
    "rag_mode": "custom",
    "enable_vlm_analysis": true,
    "enable_minio_upload": true,
    "max_pages": 20
  }
}' | grep "event: message" -A 1 | tail -1)

if echo "$RESULT" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ bk01.pdf stored successfully${NC}\n"
else
    echo -e "${YELLOW}⚠ bk01.pdf storage may have failed (check logs)${NC}\n"
fi

# Store PDF 2 (bk02.pdf)
echo -e "${BLUE}[3/4]${NC} Storing test_data/bk02.pdf..."
RESULT=$(call_mcp_tool "store_knowledge" '{
  "user_id": "'"${TEST_USER_ID}"'",
  "content": "test_data/bk02.pdf",
  "content_type": "pdf",
  "metadata": {"source": "test_suite", "document": "bk02"},
  "options": {
    "rag_mode": "custom",
    "enable_vlm_analysis": true,
    "enable_minio_upload": true,
    "max_pages": 20
  }
}' | grep "event: message" -A 1 | tail -1)

if echo "$RESULT" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ bk02.pdf stored successfully${NC}\n"
else
    echo -e "${YELLOW}⚠ bk02.pdf storage may have failed (check logs)${NC}\n"
fi

# Store PDF 3 (bk03.pdf)
echo -e "${BLUE}[4/4]${NC} Storing test_data/bk03.pdf..."
RESULT=$(call_mcp_tool "store_knowledge" '{
  "user_id": "'"${TEST_USER_ID}"'",
  "content": "test_data/bk03.pdf",
  "content_type": "pdf",
  "metadata": {"source": "test_suite", "document": "bk03"},
  "options": {
    "rag_mode": "custom",
    "enable_vlm_analysis": true,
    "enable_minio_upload": true,
    "max_pages": 20
  }
}' | grep "event: message" -A 1 | tail -1)

if echo "$RESULT" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ bk03.pdf stored successfully${NC}\n"
else
    echo -e "${YELLOW}⚠ bk03.pdf storage may have failed (check logs)${NC}\n"
fi

# Verify data was stored
echo -e "${BLUE}[VERIFY]${NC} Testing search to verify data..."
SEARCH_RESULT=$(call_mcp_tool "search_knowledge" '{
  "user_id": "'"${TEST_USER_ID}"'",
  "query": "test",
  "search_options": {"top_k": 5}
}' | grep "event: message" -A 1 | tail -1)

TOTAL_RESULTS=$(echo "$SEARCH_RESULT" | grep -o '"total_results":[0-9]*' | grep -o '[0-9]*')

echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║ Seeding Complete${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}\n"

if [ -n "$TOTAL_RESULTS" ] && [ "$TOTAL_RESULTS" -gt 0 ]; then
    echo -e "${GREEN}✅ Success! Found ${TOTAL_RESULTS} documents for user ${TEST_USER_ID}${NC}"
    echo -e "\n${GREEN}You can now run the test suite:${NC}"
    echo -e "  ${YELLOW}./digital_tools_test.sh${NC}\n"
else
    echo -e "${YELLOW}⚠ Warning: Search returned 0 results${NC}"
    echo -e "${YELLOW}This may be expected if storage is asynchronous.${NC}"
    echo -e "${YELLOW}Wait a few seconds and try running the tests.${NC}\n"
fi

echo -e "${BLUE}Note:${NC} If tests still fail, check:"
echo -e "  1. Supabase/PostgreSQL is running"
echo -e "  2. Vector DB is configured correctly"
echo -e "  3. MinIO is accessible"
echo -e "  4. Check MCP server logs for errors\n"
