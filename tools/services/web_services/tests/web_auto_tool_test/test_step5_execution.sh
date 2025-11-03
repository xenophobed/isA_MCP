#!/bin/bash
###############################################################################
# Step 5: Execution & Analysis Test
# Tests action execution + result analysis
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║             Step 5: Execution & Analysis Test (ActionExecutor)            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# MCP configuration
MCP_URL="${MCP_URL:-http://localhost:8081}"
MCP_ENDPOINT="$MCP_URL/mcp"

# Test scenarios: url|task|expected_action
declare -a TEST_CASES=(
    "example.com|scroll down 500 pixels|scroll"
    "httpbin.org/html|scroll to bottom|scroll"
)

PASSED=0
FAILED=0
TOTAL=${#TEST_CASES[@]}

for test_case in "${TEST_CASES[@]}"; do
    IFS='|' read -r url task expected_action <<< "$test_case"

    echo -e "${BLUE}Testing: ${url} - ${task}${NC}"
    echo "  Expected action type: ${expected_action}"

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 5,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"web_automation\",
                \"arguments\": {
                    \"url\": \"https://www.${url}\",
                    \"task\": \"${task}\",
                    \"user_id\": \"step5_test\"
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

    # Extract step5_execution results
    actions_executed=$(echo "$json_data" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.workflow_results.step5_execution.actions_executed' 2>/dev/null)
    actions_successful=$(echo "$json_data" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.workflow_results.step5_execution.actions_successful' 2>/dev/null)
    task_completed=$(echo "$json_data" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.workflow_results.step5_execution.task_completed' 2>/dev/null)

    echo "  Actions executed: ${actions_executed}"
    echo "  Actions successful: ${actions_successful}"
    echo "  Task completed: ${task_completed}"

    if [ "$actions_executed" != "null" ] && [ "$actions_executed" -gt 0 ]; then
        echo -e "${GREEN}✅ Action execution successful${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ Action execution failed${NC}"
        ((FAILED++))
    fi
    echo ""
done

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Step 5 Summary${NC}"
echo "Passed: ${PASSED}/${TOTAL}"
echo "Failed: ${FAILED}/${TOTAL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Step 5: PASSED - Action execution working${NC}"
    exit 0
else
    echo -e "${RED}❌ Step 5: FAILED - Issues with action execution${NC}"
    exit 1
fi
