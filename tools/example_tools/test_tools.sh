#!/bin/bash
###############################################################################
# Complete Example Tools Test Suite
# Tests all tools in example_tools.py
#
# Tools Tested:
# ✓ Calculator - Basic arithmetic
# ✓ Weather Tools - Full feature demonstrations
# ✓ Context Tests - Logging, Progress, HIL
# ✓ Batch & Streaming - Multi-step operations
# ✓ Long-running & Cancellation - Operation tracking
###############################################################################

# Note: Do NOT use 'set -e' here because we want tests to continue even if some fail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# MCP server details
MCP_SERVER="${MCP_SERVER:-http://localhost:8081}"
USER_ID="test_user_$(date +%s)"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

###############################################################################
# Utility Functions
###############################################################################

print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_test() {
    ((TESTS_RUN++))
    echo -e "\n${YELLOW}▶ Test ${TESTS_RUN}: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ PASS: $1${NC}"
    ((TESTS_PASSED++))
}

print_failure() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    echo -e "${RED}   Error: $2${NC}"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${BLUE}ℹ  $1${NC}"
}

call_mcp_tool() {
    local tool_name="$1"
    local arguments="$2"

    # Add timeout to prevent hanging
    timeout 30 curl -s -X POST "${MCP_SERVER}/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 1,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"${tool_name}\",
                \"arguments\": ${arguments}
            }
        }" 2>&1 || echo "TIMEOUT_ERROR"
}

check_response() {
    local response="$1"
    local expected="$2"

    # Check for timeout error
    if echo "$response" | grep -q "TIMEOUT_ERROR"; then
        echo "Request timed out" >&2
        return 1
    fi

    if echo "$response" | grep -q "$expected"; then
        return 0
    else
        return 1
    fi
}

###############################################################################
# Calculator Tests
###############################################################################

test_calculator_add() {
    print_test "Calculator - Addition"

    local response=$(call_mcp_tool "calculator" '{
        "operation": "add",
        "a": 5,
        "b": 3,
        "user_id": "'"$USER_ID"'"
    }')

    if check_response "$response" "8" && check_response "$response" "success"; then
        print_success "5 + 3 = 8"
    else
        print_failure "Calculator addition" "Expected result 8"
    fi
}

test_calculator_divide() {
    print_test "Calculator - Division"

    local response=$(call_mcp_tool "calculator" '{
        "operation": "divide",
        "a": 10,
        "b": 2,
        "user_id": "'"$USER_ID"'"
    }')

    if check_response "$response" "5" && check_response "$response" "success"; then
        print_success "10 / 2 = 5"
    else
        print_failure "Calculator division" "Expected result 5"
    fi
}

test_calculator_error() {
    print_test "Calculator - Division by zero error"

    local response=$(call_mcp_tool "calculator" '{
        "operation": "divide",
        "a": 10,
        "b": 0,
        "user_id": "'"$USER_ID"'"
    }')

    if check_response "$response" "error" || check_response "$response" "zero"; then
        print_success "Division by zero handled correctly"
    else
        print_failure "Calculator error handling" "Expected error for division by zero"
    fi
}

###############################################################################
# Weather Tests
###############################################################################

test_weather_basic() {
    print_test "Weather - Basic query (Beijing)"

    local response=$(call_mcp_tool "get_weather" '{
        "city": "Beijing",
        "include_forecast": false,
        "user_id": "'"$USER_ID"'"
    }')

    print_info "Response preview:"
    echo "$response" | head -n 15

    if check_response "$response" "Beijing" && check_response "$response" "temperature"; then
        print_success "Weather data retrieved successfully"
    else
        print_failure "Basic weather query" "Expected Beijing weather data"
    fi
}

test_weather_with_forecast() {
    print_test "Weather - With 7-day forecast (Shanghai)"

    local response=$(call_mcp_tool "get_weather" '{
        "city": "Shanghai",
        "include_forecast": true,
        "user_id": "'"$USER_ID"'"
    }')

    if check_response "$response" "Shanghai" && \
       check_response "$response" "forecast" && \
       check_response "$response" "temperature"; then
        print_success "Weather with forecast retrieved"
    else
        print_failure "Weather with forecast" "Expected Shanghai with forecast"
    fi
}

test_batch_weather_sequential() {
    print_test "Batch Weather - Sequential processing"

    local response=$(call_mcp_tool "batch_weather" '{
        "cities": ["Beijing", "Tokyo", "London"],
        "parallel": false,
        "user_id": "'"$USER_ID"'"
    }')

    if check_response "$response" "total_cities" && \
       check_response "$response" "3"; then
        print_success "Batch sequential processing completed"
    else
        print_failure "Batch sequential" "Expected 3 cities processed"
    fi
}

test_batch_weather_parallel() {
    print_test "Batch Weather - Parallel processing"

    local response=$(call_mcp_tool "batch_weather" '{
        "cities": ["Shanghai", "New York"],
        "parallel": true,
        "user_id": "'"$USER_ID"'"
    }')

    if check_response "$response" "total_cities" && \
       check_response "$response" "2"; then
        print_success "Batch parallel processing completed"
    else
        print_failure "Batch parallel" "Expected 2 cities processed"
    fi
}

test_stream_weather() {
    print_test "Stream Weather - Real-time updates"

    local response=$(call_mcp_tool "stream_weather" '{
        "city": "Tokyo",
        "updates": 3,
        "user_id": "'"$USER_ID"'"
    }')

    if check_response "$response" "total_updates" && \
       check_response "$response" "3"; then
        print_success "Streaming weather updates completed"
    else
        print_failure "Stream weather" "Expected 3 updates"
    fi
}

test_long_running_analysis() {
    print_test "Long-running Analysis - Background task (5s)"

    local analysis_id="test_analysis_$(date +%s)"

    print_info "Starting 5-second analysis..."

    # Start analysis in background
    call_mcp_tool "long_weather_analysis" '{
        "city": "London",
        "analysis_id": "'"$analysis_id"'",
        "duration_seconds": 5,
        "user_id": "'"$USER_ID"'"
    }' > /tmp/analysis_result.json &

    local bg_pid=$!

    # Wait for completion
    sleep 2
    print_info "Analysis running... (pid: $bg_pid)"

    if ps -p $bg_pid > /dev/null 2>&1; then
        print_success "Long-running task started successfully"
        wait $bg_pid || true
    else
        print_failure "Long-running task" "Process completed too quickly"
    fi
}

test_cancel_analysis() {
    print_test "Cancel Analysis - Operation cancellation"

    local analysis_id="cancel_test_$(date +%s)"

    print_info "Starting 60s analysis to cancel..."

    # Start long analysis in background
    call_mcp_tool "long_weather_analysis" '{
        "city": "Beijing",
        "analysis_id": "'"$analysis_id"'",
        "duration_seconds": 60,
        "user_id": "'"$USER_ID"'"
    }' > /tmp/cancel_test.json &

    local bg_pid=$!
    sleep 2

    print_info "Attempting to cancel: $analysis_id"

    local cancel_response=$(call_mcp_tool "cancel_weather_analysis" '{
        "analysis_id": "'"$analysis_id"'"
    }')

    # Kill background process
    kill $bg_pid 2>/dev/null || true

    if check_response "$cancel_response" "cancelled" || \
       check_response "$cancel_response" "not_found"; then
        print_success "Cancellation mechanism working"
    else
        print_failure "Cancel analysis" "Expected cancellation status"
    fi
}

###############################################################################
# Context Tests
###############################################################################

test_context_info() {
    print_test "Context - Information extraction"

    local response=$(call_mcp_tool "test_context_info" '{
        "test_message": "Testing context extraction"
    }')

    if check_response "$response" "context_info" && \
       check_response "$response" "context_available"; then
        print_success "Context info extraction working"
    else
        print_failure "Context info" "Expected context information"
    fi
}

test_context_logging() {
    print_test "Context - Logging (info/debug/warning/error)"

    local response=$(call_mcp_tool "test_context_logging" '{
        "test_all_levels": true
    }')

    if check_response "$response" "logs_sent" && \
       check_response "$response" "total_logs"; then
        print_success "Context logging working"
    else
        print_failure "Context logging" "Expected log entries"
    fi
}

test_context_progress() {
    print_test "Context - Progress reporting (10 steps)"

    local response=$(call_mcp_tool "test_context_progress" '{
        "total_steps": 10,
        "delay_ms": 50
    }')

    if check_response "$response" "progress_reports" && \
       check_response "$response" "10"; then
        print_success "Context progress reporting working"
    else
        print_failure "Context progress" "Expected 10 progress reports"
    fi
}

test_context_comprehensive() {
    print_test "Context - Comprehensive workflow"

    local response=$(call_mcp_tool "test_context_comprehensive" '{
        "scenario_name": "Complete workflow test"
    }')

    if check_response "$response" "features_tested" && \
       check_response "$response" "steps_completed"; then
        print_success "Comprehensive context test completed"
    else
        print_failure "Context comprehensive" "Expected workflow completion"
    fi
}

###############################################################################
# Main Test Execution
###############################################################################

main() {
    print_header "🧪 Complete Example Tools Test Suite"
    echo -e "${BLUE}MCP Server: ${MCP_SERVER}${NC}"
    echo -e "${BLUE}Test User ID: ${USER_ID}${NC}"
    echo -e "${BLUE}Timestamp: $(date)${NC}"

    print_header "📊 Calculator Tests"
    test_calculator_add
    test_calculator_divide
    test_calculator_error

    print_header "🌤️  Weather Tools Tests"
    test_weather_basic
    test_weather_with_forecast
    test_batch_weather_sequential
    test_batch_weather_parallel
    test_stream_weather

    print_header "⏱️  Long-running & Cancellation Tests"
    test_long_running_analysis
    test_cancel_analysis

    print_header "🔍 Context Tests"
    test_context_info
    test_context_logging
    test_context_progress
    test_context_comprehensive

    # Summary
    print_header "📋 Test Summary"
    echo -e "${BLUE}Total Tests: ${TESTS_RUN}${NC}"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}============================================================${NC}"
        echo -e "${GREEN}✓ ALL TESTS PASSED! 🎉${NC}"
        echo -e "${GREEN}============================================================${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}============================================================${NC}"
        echo -e "${RED}✗ SOME TESTS FAILED${NC}"
        echo -e "${RED}============================================================${NC}"
        exit 1
    fi
}

# Run main function
main
