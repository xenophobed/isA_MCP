#!/bin/bash
###############################################################################
# Step 4: Action Generation Test
# Tests generate_playwright_actions function (LLM action reasoning)
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Step 4: Action Generation Test (generate_playwright_actions)     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# MCP configuration
MCP_URL="${MCP_URL:-http://localhost:8081}"
MCP_ENDPOINT="$MCP_URL/mcp"

# Test scenarios: url|task|min_actions
declare -a TEST_CASES=(
    "example.com|scroll down 500 pixels|1"
    "httpbin.org/html|scroll to bottom|1"
)

PASSED=0
FAILED=0
TOTAL=${#TEST_CASES[@]}

for test_case in "${TEST_CASES[@]}"; do
    IFS='|' read -r url task min_actions <<< "$test_case"

    echo -e "${BLUE}Testing: ${url} - ${task}${NC}"
    echo "  Expecting at least ${min_actions} action(s)"

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 4,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"web_automation\",
                \"arguments\": {
                    \"url\": \"https://www.${url}\",
                    \"task\": \"${task}\",
                    \"user_id\": \"step4_test\"
                }
            }
        }")

    # Extract data from event stream
    data_line=$(echo "$response" | grep "^data: " | head -1)
    if [ -z "$data_line" ]; then
        echo -e "${RED}❌ No event stream data${NC}"
        ((FAILED++))
        echo ""
        continue
    fi

    json_data=$(echo "$data_line" | sed 's/^data: //')

    # Extract step4_actions array length
    action_count=$(echo "$json_data" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.workflow_results.step4_actions | length' 2>/dev/null)

    if [ "$action_count" = "null" ]; then
        action_count="0"
    fi

    echo "  Actions generated: ${action_count}"

    if [ "$action_count" -ge "$min_actions" ]; then
        echo -e "${GREEN}✅ Action generation successful (${action_count} actions)${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ Action generation failed (${action_count} actions, expected ${min_actions})${NC}"
        ((FAILED++))
    fi
    echo ""
done

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Step 4 Summary${NC}"
echo "Passed: ${PASSED}/${TOTAL}"
echo "Failed: ${FAILED}/${TOTAL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Step 4: PASSED - Action generation working${NC}"
    exit 0
else
    echo -e "${RED}❌ Step 4: FAILED - Issues with action generation${NC}"
    exit 1
fi
