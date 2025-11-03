#!/bin/bash

###############################################################################
# Web Automation Tools Test Suite
# 
# Tests the 5-step atomic workflow with progress tracking and HIL support
# via MCP HTTP endpoint (the actual user-facing interface)
#
# Based on: test_web_search.sh pattern
# Tests: tools/services/web_services/tools/web_automation_tools.py -> web_automation tool
#
# Test Scenarios:
# 1. Basic search automation
# 2. Form interaction
# 3. Multi-step navigation
# 4. HIL detection (login, CAPTCHA)
# 5. Error handling
#
# Usage: ./test_web_automation.sh [--verbose] [--url http://localhost:8081]
###############################################################################

set -e  # Exit on error

# Flags
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --url)
            MCP_URL="$2"
            MCP_ENDPOINT="$MCP_URL/mcp"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--verbose] [--url http://localhost:8081]"
            exit 1
            ;;
    esac
done

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MCP_URL="${MCP_URL:-http://localhost:8081}"
MCP_ENDPOINT="$MCP_URL/mcp"
USER_ID="test_user_$(date +%s)"
RESULTS_DIR="./results/automation_$(date +%Y%m%d_%H%M%S)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED_TESTS++))
}

error() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED_TESTS++))
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Test function
run_test() {
    local test_name="$1"
    local url="$2"
    local task="$3"
    local user_id="${4:-$USER_ID}"
    local output_file="$RESULTS_DIR/test_$(echo $test_name | tr ' ' '_').json"
    
    ((TOTAL_TESTS++))
    
    log "Running test: $test_name"
    echo "  URL: $url"
    echo "  Task: $task"
    echo "  User: $user_id"
    echo ""
    
    # Make request with JSON-RPC format (like test_web_search.sh)
    local response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": $TOTAL_TESTS,
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"web_automation\",
                \"arguments\": {
                    \"url\": \"$url\",
                    \"task\": \"$task\",
                    \"user_id\": \"$user_id\"
                }
            }
        }" \
        2>&1)
    
    # Save response
    echo "$response" > "$output_file"
    
    # Check if request succeeded
    if [ $? -eq 0 ]; then
        # Parse event stream response (like test_web_search.sh)
        local data_line=$(echo "$response" | grep "^data: " | head -1)
        
        if [ -z "$data_line" ]; then
            error "No data line in response: $test_name"
            echo "  Response: $response"
            echo ""
            return
        fi
        
        # Extract JSON from data line
        local json_data=$(echo "$data_line" | sed 's/^data: //')
        
        # Check for errors
        local is_error=$(echo "$json_data" | jq -r '.result.isError // false')
        if [ "$is_error" = "true" ]; then
            error "Tool call returned error: $test_name"
            echo "$json_data" | jq '.result.content[0].text'
            echo ""
            return
        fi
        
        # Parse tool response
        local tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')
        
        # Parse nested JSON (handle both string JSON and already parsed JSON)
        local status=$(echo "$tool_response" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        if [ "$status" = "unknown" ]; then
            # Try parsing as string JSON
            local parsed=$(echo "$tool_response" | jq -r '.' 2>/dev/null)
            if [ $? -eq 0 ]; then
                status=$(echo "$parsed" | jq -r '.status // "unknown"')
            fi
        fi
        
        local action=$(echo "$tool_response" | jq -r '.action // "unknown"' 2>/dev/null || echo "unknown")
        local success=$(echo "$tool_response" | jq -r '.data.success // false' 2>/dev/null || echo "false")
        
        echo "  Status: $status"
        echo "  Action: $action"
        echo "  Success: $success"
        echo ""
        
        # Check result
        if [ "$status" = "success" ]; then
            success "Test passed: $test_name"
            
            # Extract workflow details
            local actions_executed=$(echo "$tool_response" | jq -r '.data.workflow_results.step5_execution.actions_executed // 0')
            local task_completed=$(echo "$tool_response" | jq -r '.data.workflow_results.step5_execution.task_completed // false')
            
            echo "  📊 Workflow Summary:"
            echo "     - Actions executed: $actions_executed"
            echo "     - Task completed: $task_completed"
            echo ""
            
        elif [ "$status" = "authorization_required" ] || [ "$status" = "credential_required" ]; then
            warning "HIL required: $test_name (expected behavior)"
            
            # Extract HIL details
            local intervention_type=$(echo "$tool_response" | jq -r '.data.intervention_type // "unknown"')
            local provider=$(echo "$tool_response" | jq -r '.data.provider // "unknown"')
            
            echo "  🤚 HIL Details:"
            echo "     - Intervention type: $intervention_type"
            echo "     - Provider: $provider"
            echo "     - Action: $action"
            echo ""
            
            ((PASSED_TESTS++))  # HIL is expected behavior
            
        else
            error "Test failed: $test_name (status: $status)"
            # Show error details
            local error_msg=$(echo "$tool_response" | jq -r '.error // .data.error // .data.error_details // empty' 2>/dev/null)
            if [ -n "$error_msg" ] && [ "$error_msg" != "null" ] && [ "$error_msg" != "" ]; then
                # Extract first line of error message (usually the key issue)
                local first_line=$(echo "$error_msg" | head -1)
                echo "  Error: $first_line"
                # If verbose, show full error
                if [ "$VERBOSE" = true ]; then
                    echo "  Full error:"
                    echo "$error_msg" | sed 's/^/    /'
                fi
            fi
            if [ "$VERBOSE" = true ]; then
                echo "  Full response:"
                echo "$tool_response" | jq '.' 2>/dev/null || echo "$tool_response"
            fi
            echo ""
        fi
    else
        error "Request failed: $test_name"
        echo "  Error: $response"
        echo ""
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    if ! command -v curl &> /dev/null; then
        error "curl not found. Please install curl."
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        error "jq not found. Please install jq for JSON parsing."
        exit 1
    fi
    
    echo -e "${GREEN}✅ Required commands: curl, jq${NC}"
    echo ""
}

# Check MCP server
check_server() {
    log "Checking MCP server at $MCP_URL..."
    
    if curl -s -f "$MCP_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ MCP server is running at $MCP_URL${NC}"
    else
        error "MCP server not accessible at $MCP_URL"
        warning "Please start the MCP server first"
        log "Start server with: cd $PROJECT_ROOT && python main.py"
        exit 1
    fi
    echo ""
}

###############################################################################
# Test Suite
###############################################################################

main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║                   Web Automation Tools Test Suite                         ║"
    echo "║                   5-Step Workflow + HIL Support                            ║"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Checks
    check_dependencies
    check_server
    
    log "Starting test suite..."
    echo "Results will be saved to: $RESULTS_DIR"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Test 1: Basic Search Automation
    log "Test Category: Basic Automation"
    run_test \
        "Basic Search - Google" \
        "https://www.google.com" \
        "search for python programming"
    
    # Test 2: Simple Navigation
    run_test \
        "Simple Navigation" \
        "https://www.example.com" \
        "scroll down 500 pixels"
    
    # Test 3: Form Interaction (if test form exists)
    log "Test Category: Form Interaction"
    run_test \
        "Form Interaction" \
        "https://httpbin.org/forms/post" \
        "fill customer name 'John Doe', email 'john@example.com'"
    
    # Test 4: Multi-step Task
    log "Test Category: Multi-Step Workflow"
    run_test \
        "Multi-Step Search" \
        "https://www.duckduckgo.com" \
        "search for 'web automation', click first result"
    
    # Test 5: HIL Detection - Login (Expected HIL)
    log "Test Category: HIL Detection"
    warning "The following tests are expected to trigger HIL..."
    echo ""
    
    run_test \
        "HIL - Google Login" \
        "https://accounts.google.com/signin" \
        "login to gmail" \
        "hil_test_user"
    
    # Test 6: HIL Detection - Generic Login
    run_test \
        "HIL - Generic Auth Page" \
        "https://github.com/login" \
        "login to github" \
        "hil_test_user"
    
    # Test 7: Error Handling - Invalid URL
    log "Test Category: Error Handling"
    run_test \
        "Error - Invalid URL" \
        "not-a-valid-url" \
        "search for something"
    
    # Test 8: Error Handling - Timeout (slow site)
    run_test \
        "Error - Unreachable Site" \
        "https://httpstat.us/500" \
        "click something"
    
    # Test 9: Complex Task
    log "Test Category: Complex Tasks"
    run_test \
        "Complex Multi-Action Task" \
        "https://www.wikipedia.org" \
        "search for 'artificial intelligence', scroll to see results, click first article"
    
    # Test 10: E-commerce Simulation
    run_test \
        "E-commerce Flow" \
        "https://www.amazon.com" \
        "search for wireless headphones"
    
    # Summary
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║                           Test Summary                                     ║"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Total Tests:  $TOTAL_TESTS"
    echo "Passed:       $PASSED_TESTS"
    echo "Failed:       $FAILED_TESTS"
    echo ""
    
    if [ $FAILED_TESTS -eq 0 ]; then
        success "All tests passed! 🎉"
        echo ""
        echo "Test results saved to: $RESULTS_DIR"
        exit 0
    else
        error "Some tests failed"
        echo ""
        echo "Test results saved to: $RESULTS_DIR"
        echo "Please check the logs for details"
        exit 1
    fi
}

###############################################################################
# Helper Functions for Advanced Testing
###############################################################################

# Test progress tracking (requires MCP progress monitoring)
test_progress_tracking() {
    log "Testing progress tracking..."
    
    # This would require monitoring MCP progress notifications
    # Implementation depends on your MCP client setup
    
    warning "Progress tracking test requires MCP client with progress monitoring"
    echo "Skipping for now..."
    echo ""
}

# Test HIL workflow end-to-end
test_hil_workflow() {
    log "Testing complete HIL workflow..."
    
    # Step 1: Trigger HIL
    local hil_response=$(curl -s -X POST "$MCP_ENDPOINT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {
                "name": "web_automation",
                "arguments": {
                    "url": "https://accounts.google.com/signin",
                    "task": "login to gmail",
                    "user_id": "hil_workflow_test"
                }
            }
        }')
    
    # Parse event stream
    local data_line=$(echo "$hil_response" | grep "^data: " | head -1)
    local json_data=$(echo "$data_line" | sed 's/^data: //')
    local tool_response=$(echo "$json_data" | jq -r '.result.content[0].text')
    local action=$(echo "$tool_response" | jq -r '.action')
    
    if [ "$action" = "request_authorization" ] || [ "$action" = "ask_human" ]; then
        success "HIL triggered successfully"
        echo "  Action: $action"
        echo ""
        
        # Step 2: In real scenario, user would approve or provide credentials
        warning "In production, Agent would handle user interaction here"
        echo ""
    else
        warning "HIL not triggered (might be normal if page changed)"
        echo ""
    fi
}

# Test action types coverage
test_action_types() {
    log "Testing various action types..."
    
    # Test different action types
    local action_tests=(
        "click|https://www.example.com|click the 'More information' link"
        "type|https://www.google.com|type 'hello world' in search box"
        "scroll|https://www.example.com|scroll down to bottom"
        "hover|https://www.example.com|hover over the heading"
        "navigate|https://www.example.com|navigate to about page"
    )
    
    for test_spec in "${action_tests[@]}"; do
        IFS='|' read -r action_type url task <<< "$test_spec"
        run_test \
            "Action Type: $action_type" \
            "$url" \
            "$task"
    done
}

# Performance test
test_performance() {
    log "Running performance test..."
    
    local start_time=$(date +%s)
    
    run_test \
        "Performance Test" \
        "https://www.example.com" \
        "scroll down and take screenshot"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo "  ⏱️  Duration: ${duration}s"
    
    if [ $duration -lt 30 ]; then
        success "Performance test passed (< 30s)"
    else
        warning "Performance test slow (${duration}s)"
    fi
    echo ""
}

###############################################################################
# Run Main Test Suite
###############################################################################

main "$@"


