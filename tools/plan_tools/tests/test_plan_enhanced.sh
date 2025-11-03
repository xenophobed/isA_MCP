#!/bin/bash
################################################################################
# Enhanced Plan Tools - MCP Tool Test Suite
# Tests plan_tools via MCP HTTP endpoint (JSON-RPC format)
#
# Based on: tools/services/web_services/tests/test_web_search.sh
# Tests: tools/plan_tools/plan_tools.py
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
MCP_URL="${MCP_URL:-http://localhost:8081}"
MCP_ENDPOINT="$MCP_URL/mcp"
SEARCH_ENDPOINT="$MCP_URL/search"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Flags
VERBOSE=false
SKIP_SERVER_CHECK=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --skip-server-check)
            SKIP_SERVER_CHECK=true
            shift
            ;;
        --url)
            MCP_URL="$2"
            MCP_ENDPOINT="$MCP_URL/mcp"
            SEARCH_ENDPOINT="$MCP_URL/search"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--verbose] [--skip-server-check] [--url http://localhost:8081]"
            exit 1
            ;;
    esac
done

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 not found. Please install it first."
        exit 1
    fi
}

################################################################################
# Environment Check
################################################################################

check_environment() {
    log_section "Environment Check"

    # Check required commands
    check_command curl
    check_command jq
    log_success "Required commands: curl, jq"

    # Check MCP server
    if [ "$SKIP_SERVER_CHECK" = false ]; then
        log_info "Checking MCP server at $MCP_URL..."
        if curl -s -f "$MCP_URL/health" > /dev/null 2>&1; then
            log_success "MCP server is running at $MCP_URL"
        else
            log_error "MCP server not accessible at $MCP_URL"
            log_info "Start server with: cd $PROJECT_ROOT && python main.py"
            log_info "Or use --skip-server-check to skip this check"
            exit 1
        fi
    else
        log_warning "Skipping server check (--skip-server-check)"
    fi
}

################################################################################
# Test 1: Search for plan tools
################################################################################

test_search_tools() {
    log_section "Test 1: Search for Plan Tools"

    log_info "Searching for 'create_execution_plan' tool..."

    response=$(curl -s -X POST "$SEARCH_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d '{
            "query": "create_execution_plan",
            "filters": {"types": ["tool"]},
            "max_results": 5
        }')

    if [ "$VERBOSE" = true ]; then
        echo "$response" | jq '.'
    fi

    # Check if tool found
    status=$(echo "$response" | jq -r '.status')
    if [ "$status" != "success" ]; then
        log_error "Search failed"
        echo "$response" | jq '.'
        exit 1
    fi

    result_count=$(echo "$response" | jq -r '.count // 0')
    if [ "$result_count" -eq 0 ]; then
        log_error "create_execution_plan tool not found"
        exit 1
    fi

    log_success "Found create_execution_plan tool"
}

################################################################################
# Test 2: Create Execution Plan
################################################################################

test_create_execution_plan() {
    log_section "Test 2: Create Execution Plan"

    log_info "Creating execution plan for security audit..."

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_execution_plan",
                "arguments": {
                    "guidance": "Analyze codebase for security vulnerabilities",
                    "available_tools": "[\"code_scanner\", \"dependency_checker\", \"security_analyzer\"]",
                    "request": "Perform comprehensive security audit on Python project",
                    "plan_id": "test_plan_001"
                }
            }
        }')

    if [ "$VERBOSE" = true ]; then
        echo "Full response:"
        echo "$response"
    fi

    # Parse event stream response
    data_line=$(echo "$response" | grep "^data: " | head -1)
    if [ -z "$data_line" ]; then
        log_error "No data line in response"
        echo "Response: $response"
        exit 1
    fi

    # Extract JSON from data line
    json_data=$(echo "$data_line" | sed 's/^data: //')

    if [ "$VERBOSE" = true ]; then
        echo "Parsed JSON:"
        echo "$json_data" | jq '.'
    fi

    # Check for errors
    is_error=$(echo "$json_data" | jq -r '.result.isError // false')
    if [ "$is_error" = "true" ]; then
        log_error "Tool call returned error"
        echo "$json_data" | jq '.result.content[0].text'
        exit 1
    fi

    # Parse tool response
    tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')

    # Parse nested JSON
    status=$(echo "$tool_response" | jq -r '.status')
    if [ "$status" != "success" ]; then
        log_error "create_execution_plan failed: $status"
        echo "$tool_response" | jq '.'
        exit 1
    fi

    # Extract plan details
    plan_id=$(echo "$tool_response" | jq -r '.data.plan_id')
    total_tasks=$(echo "$tool_response" | jq -r '.data.total_tasks')
    execution_mode=$(echo "$tool_response" | jq -r '.data.execution_mode')
    hypothesis=$(echo "$tool_response" | jq -r '.data.solution_hypothesis // "N/A"')

    log_success "Execution plan created successfully"
    log_info "Plan details:"
    echo "  Plan ID: $plan_id"
    echo "  Total tasks: $total_tasks"
    echo "  Execution mode: $execution_mode"
    echo "  Hypothesis: ${hypothesis:0:60}..."

    # Store plan ID for next tests
    export TEST_PLAN_ID="$plan_id"
}

################################################################################
# Test 3: Get Plan Status
################################################################################

test_get_plan_status() {
    log_section "Test 3: Get Plan Status"

    log_info "Getting status for plan: $TEST_PLAN_ID..."

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 2,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"get_plan_status\",
                \"arguments\": {
                    \"plan_id\": \"$TEST_PLAN_ID\"
                }
            }
        }")

    data_line=$(echo "$response" | grep "^data: " | head -1)
    json_data=$(echo "$data_line" | sed 's/^data: //')
    is_error=$(echo "$json_data" | jq -r '.result.isError // false')

    if [ "$is_error" = "false" ]; then
        tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')
        status=$(echo "$tool_response" | jq -r '.status')

        if [ "$status" = "success" ]; then
            plan_status=$(echo "$tool_response" | jq -r '.data.status')
            progress=$(echo "$tool_response" | jq -r '.data.progress_percentage')
            completed=$(echo "$tool_response" | jq -r '.data.completed_tasks')
            total=$(echo "$tool_response" | jq -r '.data.total_tasks')

            log_success "Plan status retrieved"
            log_info "Status: $plan_status"
            log_info "Progress: $progress% ($completed/$total tasks)"
        else
            log_error "get_plan_status failed: $status"
            exit 1
        fi
    else
        log_error "get_plan_status returned error"
        exit 1
    fi
}

################################################################################
# Test 4: Update Task Status
################################################################################

test_update_task_status() {
    log_section "Test 4: Update Task Status"

    log_info "Updating task 1 to 'in_progress'..."

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 3,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"update_task_status\",
                \"arguments\": {
                    \"plan_id\": \"$TEST_PLAN_ID\",
                    \"task_id\": 1,
                    \"status\": \"in_progress\"
                }
            }
        }")

    data_line=$(echo "$response" | grep "^data: " | head -1)
    json_data=$(echo "$data_line" | sed 's/^data: //')
    tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')
    status=$(echo "$tool_response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        log_success "Task status updated to 'in_progress'"
    else
        log_error "Failed to update task status"
        exit 1
    fi

    # Update to completed
    log_info "Updating task 1 to 'completed'..."

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 4,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"update_task_status\",
                \"arguments\": {
                    \"plan_id\": \"$TEST_PLAN_ID\",
                    \"task_id\": 1,
                    \"status\": \"completed\",
                    \"result_json\": \"{\\\"output\\\": \\\"Task completed successfully\\\"}\"
                }
            }
        }")

    data_line=$(echo "$response" | grep "^data: " | head -1)
    json_data=$(echo "$data_line" | sed 's/^data: //')
    tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')
    status=$(echo "$tool_response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        log_success "Task status updated to 'completed'"
    else
        log_error "Failed to update task status to completed"
        exit 1
    fi
}

################################################################################
# Test 5: Adjust Plan - Expand
################################################################################

test_adjust_plan_expand() {
    log_section "Test 5: Adjust Plan - Expand"

    log_info "Expanding plan with new tasks..."

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 5,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"adjust_plan\",
                \"arguments\": {
                    \"plan_id\": \"$TEST_PLAN_ID\",
                    \"adjustment_type\": \"expand\",
                    \"new_tasks_json\": \"[{\\\"title\\\": \\\"Additional Security Check\\\", \\\"description\\\": \\\"Perform additional validation\\\", \\\"tools\\\": [\\\"security_validator\\\"], \\\"execution_type\\\": \\\"sequential\\\", \\\"dependencies\\\": [], \\\"expected_output\\\": \\\"Validation report\\\", \\\"verification_criteria\\\": \\\"All checks pass\\\", \\\"priority\\\": \\\"medium\\\"}]\",
                    \"reasoning\": \"Additional security checks required\"
                }
            }
        }")

    data_line=$(echo "$response" | grep "^data: " | head -1)
    json_data=$(echo "$data_line" | sed 's/^data: //')
    tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')
    status=$(echo "$tool_response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        log_success "Plan expanded successfully"
    else
        log_error "Failed to expand plan"
        exit 1
    fi
}

################################################################################
# Test 6: Get Execution History
################################################################################

test_get_execution_history() {
    log_section "Test 6: Get Execution History"

    log_info "Getting execution history..."

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": 6,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"get_execution_history\",
                \"arguments\": {
                    \"plan_id\": \"$TEST_PLAN_ID\"
                }
            }
        }")

    data_line=$(echo "$response" | grep "^data: " | head -1)
    json_data=$(echo "$data_line" | sed 's/^data: //')
    tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')
    status=$(echo "$tool_response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        event_count=$(echo "$tool_response" | jq -r '.data.event_count')
        log_success "Execution history retrieved"
        log_info "Total events: $event_count"
    else
        log_error "Failed to get execution history"
        exit 1
    fi
}

################################################################################
# Test 7: List Active Plans
################################################################################

test_list_active_plans() {
    log_section "Test 7: List Active Plans"

    log_info "Listing all active plans..."

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "list_active_plans",
                "arguments": {}
            }
        }')

    data_line=$(echo "$response" | grep "^data: " | head -1)
    json_data=$(echo "$data_line" | sed 's/^data: //')
    tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')
    status=$(echo "$tool_response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        plan_count=$(echo "$tool_response" | jq -r '.data.plan_count')
        log_success "Active plans listed"
        log_info "Total active plans: $plan_count"
    else
        log_error "Failed to list active plans"
        exit 1
    fi
}

################################################################################
# Test 8: Replan Execution
################################################################################

test_replan_execution() {
    log_section "Test 8: Replan Execution"

    log_info "Testing replanning based on feedback..."

    response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "replan_execution",
                "arguments": {
                    "original_request": "Perform security audit",
                    "previous_plan": "{\"execution_mode\": \"sequential\", \"tasks\": [{\"id\": 1, \"title\": \"Initial Task\", \"status\": \"completed\"}, {\"id\": 2, \"title\": \"Failed Task\", \"status\": \"failed\"}]}",
                    "execution_status": "{\"completed_tasks\": 1, \"failed_tasks\": 1, \"status\": \"failed\", \"issues\": [\"Task 2 encountered error\"]}",
                    "feedback": "Need to add authentication setup before task 2",
                    "available_tools": "[\"auth_setup\", \"code_scanner\", \"dependency_checker\"]"
                }
            }
        }')

    data_line=$(echo "$response" | grep "^data: " | head -1)
    json_data=$(echo "$data_line" | sed 's/^data: //')
    tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')
    status=$(echo "$tool_response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        total_tasks=$(echo "$tool_response" | jq -r '.data.total_tasks')
        improvement_notes=$(echo "$tool_response" | jq -r '.data.improvement_notes // "N/A"')
        log_success "Replanning successful"
        log_info "New plan tasks: $total_tasks"
        log_info "Improvements: ${improvement_notes:0:60}..."
    else
        log_error "Replanning failed"
        exit 1
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    log_section "Enhanced Plan Tools - MCP Test Suite"
    log_info "Testing via MCP endpoint: $MCP_URL"
    log_info "Started at: $(date)"

    check_environment
    test_search_tools
    test_create_execution_plan
    test_get_plan_status
    test_update_task_status
    test_adjust_plan_expand
    test_get_execution_history
    test_list_active_plans
    test_replan_execution

    log_section "Test Complete"
    log_success "All tests passed!"

    echo ""
    log_info "Summary:"
    echo "  - Plan tools are accessible via MCP"
    echo "  - Execution plan creation works"
    echo "  - Task status updates work"
    echo "  - Plan adjustment (expand) works"
    echo "  - Execution history tracking works"
    echo "  - Active plan listing works"
    echo "  - Replanning functionality works"
    echo ""
    log_info "Next: Deploy to staging/production"
}

# Run main
main
