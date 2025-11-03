#!/bin/bash
###############################################################################
# Step 2: Vision Analysis Test
# Tests image_analyze function with ISA Model vision API
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Step 2: Vision Analysis Test (image_analyze)                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# MCP configuration
MCP_URL="${MCP_URL:-http://localhost:8081}"
MCP_ENDPOINT="$MCP_URL/mcp"

# Test scenarios: url|task|expected_type
declare -a TEST_CASES=(
    "example.com|view page|generic"
    "httpbin.org/html|scroll down|generic"
)

PASSED=0
FAILED=0
TOTAL=${#TEST_CASES[@]}

for test_case in "${TEST_CASES[@]}"; do
    IFS='|' read -r url task expected_type <<< "$test_case"

    echo -e "${BLUE}Testing: ${url} - ${task}${NC}"
    echo "  Expected page type: ${expected_type}"

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 2,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"web_automation\",
                \"arguments\": {
                    \"url\": \"https://www.${url}\",
                    \"task\": \"${task}\",
                    \"user_id\": \"step2_test\"
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

    # Extract step2_analysis
    page_type=$(echo "$json_data" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.workflow_results.step2_analysis.page_type' 2>/dev/null)
    elements=$(echo "$json_data" | jq -r '.result.content[0].text' 2>/dev/null | jq -r '.data.workflow_results.step2_analysis.required_elements | length' 2>/dev/null)

    echo "  Detected page type: ${page_type}"
    echo "  Elements found: ${elements}"

    # Basic validation - check if page type was detected
    if [[ "$page_type" != "null" && "$page_type" != "" && "$elements" != "null" ]]; then
        echo -e "${GREEN}✅ Vision analysis completed${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ Vision analysis failed${NC}"
        ((FAILED++))
    fi
    echo ""
done

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Step 2 Summary${NC}"
echo "Passed: ${PASSED}/${TOTAL}"
echo "Failed: ${FAILED}/${TOTAL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Step 2: PASSED - Vision analysis working${NC}"
    exit 0
else
    echo -e "${RED}❌ Step 2: FAILED - Issues with vision analysis${NC}"
    exit 1
fi
