#!/bin/bash
###############################################################################
# Master Test Runner: Run All 5 Step Tests Sequentially
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           Web Automation 5-Step Workflow - Sequential Test Runner         ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Test Directory: ${TEST_DIR}"
echo "Start Time: $(date)"
echo ""

# Check MCP server
echo -e "${CYAN}Checking MCP server...${NC}"
if curl -s -f "http://localhost:8081/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MCP server is running${NC}"
else
    echo -e "${RED}❌ MCP server not running at http://localhost:8081${NC}"
    exit 1
fi
echo ""

# Test results
declare -A RESULTS
STEPS=(
    "1:step1_screenshot:Step 1 - Screenshot"
    "2:step2_vision:Step 2 - Vision Analysis"
    "3:step3_ui_detection:Step 3 - UI Detection"
    "4:step4_actions:Step 4 - Action Generation"
    "5:step5_execution:Step 5 - Execution"
)

TOTAL_PASSED=0
TOTAL_FAILED=0
START_TIME=$(date +%s)

# Run each step test
for step_info in "${STEPS[@]}"; do
    IFS=':' read -r step_num step_id step_name <<< "$step_info"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${CYAN}Running: ${step_name}${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    test_start=$(date +%s)

    # Run test
    if bash "${TEST_DIR}/test_${step_id}.sh"; then
        RESULTS[$step_num]="PASSED"
        ((TOTAL_PASSED++))
        test_status="${GREEN}✅ PASSED${NC}"
    else
        RESULTS[$step_num]="FAILED"
        ((TOTAL_FAILED++))
        test_status="${RED}❌ FAILED${NC}"
    fi

    test_end=$(date +%s)
    test_duration=$((test_end - test_start))

    echo ""
    echo -e "${step_name}: ${test_status} (${test_duration}s)"
    echo ""

    # Stop on first failure (optional - comment out to continue)
    # if [ "${RESULTS[$step_num]}" = "FAILED" ]; then
    #     echo -e "${RED}Stopping tests due to failure${NC}"
    #     break
    # fi
done

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

# Final Summary
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                          Test Suite Summary                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Results table
echo "Test Results:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "%-35s %s\n" "Step" "Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for step_info in "${STEPS[@]}"; do
    IFS=':' read -r step_num step_id step_name <<< "$step_info"
    status="${RESULTS[$step_num]}"

    if [ "$status" = "PASSED" ]; then
        status_display="${GREEN}✅ PASSED${NC}"
    else
        status_display="${RED}❌ FAILED${NC}"
    fi

    printf "%-35s " "$step_name"
    echo -e "$status_display"
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Total Steps:  ${#STEPS[@]}"
echo "Passed:       ${TOTAL_PASSED}"
echo "Failed:       ${TOTAL_FAILED}"
echo "Duration:     ${TOTAL_DURATION}s"
echo "End Time:     $(date)"
echo ""

# Final verdict
if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ✅ ALL 5 STEPS PASSED! 🎉                                ║${NC}"
    echo -e "${GREEN}║              5-Step Workflow is Fully Functional                           ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    ❌ SOME STEPS FAILED                                     ║${NC}"
    echo -e "${RED}║                 Please review the logs above                               ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
