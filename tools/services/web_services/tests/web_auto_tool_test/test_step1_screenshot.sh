#!/bin/bash
###############################################################################
# Step 1: Screenshot Test
# Tests Playwright screenshot functionality
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                 Step 1: Screenshot Test (Playwright)                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# MCP configuration
MCP_URL="${MCP_URL:-http://localhost:8081}"
MCP_ENDPOINT="$MCP_URL/mcp"

# Test URLs
TEST_URLS=(
    "https://www.example.com"
    "https://httpbin.org/html"
)

PASSED=0
FAILED=0

for url in "${TEST_URLS[@]}"; do
    echo -e "${BLUE}Testing: ${url}${NC}"

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 1,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"web_automation\",
                \"arguments\": {
                    \"url\": \"${url}\",
                    \"task\": \"take screenshot\",
                    \"user_id\": \"step1_test\"
                }
            }
        }")

    # Extract data from event stream response
    data_line=$(echo "$response" | grep "^data: " | head -1)
    if [ -z "$data_line" ]; then
        echo -e "${RED}❌ No event stream data in response${NC}"
        ((FAILED++))
        continue
    fi

    # Extract JSON from data line
    json_data=$(echo "$data_line" | sed 's/^data: //')

    # Check if screenshot was taken
    screenshot=$(echo "$json_data" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.workflow_results.step1_screenshot' 2>/dev/null)

    if [ "$screenshot" != "null" ] && [ -n "$screenshot" ] && [ -f "$screenshot" ]; then
        echo -e "${GREEN}✅ Screenshot saved: ${screenshot}${NC}"
        echo "   Size: $(du -h "$screenshot" 2>/dev/null | cut -f1)"
        ((PASSED++))
    else
        echo -e "${RED}❌ Screenshot not found or invalid${NC}"
        ((FAILED++))
    fi
    echo ""
done

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Step 1 Summary${NC}"
echo "Passed: ${PASSED}/${#TEST_URLS[@]}"
echo "Failed: ${FAILED}/${#TEST_URLS[@]}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Step 1: PASSED - Screenshot functionality working${NC}"
    exit 0
else
    echo -e "${RED}❌ Step 1: FAILED - Issues with screenshot${NC}"
    exit 1
fi
