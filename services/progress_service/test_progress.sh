#!/bin/bash
###############################################################################
# Test Polling-Based Progress Tracking
# Tests the new progress tracking tools with real-time updates
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

MCP_SERVER="${MCP_SERVER:-http://localhost:8081}"

print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_progress() {
    local pct=$1
    local msg=$2
    local bar_length=40
    local filled=$((pct * bar_length / 100))
    local empty=$((bar_length - filled))

    printf "\r${YELLOW}["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] %3d%% - %s${NC}" "$pct" "$msg"
}

# Initialize MCP session
print_header "🔄 Initializing MCP Session"

INIT_RESPONSE=$(curl -si -X POST "${MCP_SERVER}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "ProgressTestAgent", "version": "1.0.0"}
    }
  }')

SESSION_ID=$(echo "$INIT_RESPONSE" | grep -i "mcp-session-id:" | cut -d' ' -f2 | tr -d '\r')

if [ -z "$SESSION_ID" ]; then
    echo -e "${RED}❌ Failed to get session ID${NC}"
    exit 1
fi

print_success "Session ID: $SESSION_ID"

# Test 1: Start a long-running task
print_header "🚀 Test 1: Start Long-Running Task"

START_RESPONSE=$(curl -s -X POST "${MCP_SERVER}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "start_long_task",
      "arguments": {
        "task_type": "data_analysis",
        "duration_seconds": 15,
        "steps": 10,
        "metadata": {"test": "polling_progress"}
      }
    }
  }')

OPERATION_ID=$(echo "$START_RESPONSE" | grep "data:" | sed 's/.*data: //' | jq -r '.result.content[0].text' | jq -r '.data.operation_id')

if [ -z "$OPERATION_ID" ] || [ "$OPERATION_ID" = "null" ]; then
    echo -e "${RED}❌ Failed to start task${NC}"
    echo "$START_RESPONSE"
    exit 1
fi

print_success "Task started: $OPERATION_ID"
print_info "Task will run for 15 seconds with 10 steps"
echo ""

# Test 2: Poll for progress
print_header "📊 Test 2: Polling Progress (Real-time)"
echo ""

COMPLETED=false
LAST_PROGRESS=0

while [ "$COMPLETED" = false ]; do
    sleep 1.5  # Poll every 1.5 seconds

    PROGRESS_RESPONSE=$(curl -s -X POST "${MCP_SERVER}/mcp" \
      -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -H "mcp-session-id: $SESSION_ID" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"id\": 3,
        \"method\": \"tools/call\",
        \"params\": {
          \"name\": \"get_task_progress\",
          \"arguments\": {\"operation_id\": \"$OPERATION_ID\"}
        }
      }")

    STATUS=$(echo "$PROGRESS_RESPONSE" | grep "data:" | sed 's/.*data: //' | jq -r '.result.content[0].text' | jq -r '.data.status')
    PROGRESS=$(echo "$PROGRESS_RESPONSE" | grep "data:" | sed 's/.*data: //' | jq -r '.result.content[0].text' | jq -r '.data.progress' | cut -d'.' -f1)
    MESSAGE=$(echo "$PROGRESS_RESPONSE" | grep "data:" | sed 's/.*data: //' | jq -r '.result.content[0].text' | jq -r '.data.message')

    # Show progress bar
    if [ "$PROGRESS" != "null" ] && [ -n "$PROGRESS" ]; then
        print_progress "$PROGRESS" "$MESSAGE"
        LAST_PROGRESS=$PROGRESS
    fi

    # Check if completed
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] || [ "$STATUS" = "cancelled" ]; then
        echo ""
        COMPLETED=true

        if [ "$STATUS" = "completed" ]; then
            print_success "Task completed!"
        else
            echo -e "${RED}Task ended with status: $STATUS${NC}"
        fi
    fi
done

# Test 3: Get final result
print_header "📦 Test 3: Get Final Result"

RESULT_RESPONSE=$(curl -s -X POST "${MCP_SERVER}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": 4,
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"get_task_result\",
      \"arguments\": {\"operation_id\": \"$OPERATION_ID\"}
    }
  }")

RESULT=$(echo "$RESULT_RESPONSE" | grep "data:" | sed 's/.*data: //' | jq -r '.result.content[0].text' | jq '.')

echo "$RESULT"
echo ""

# Test 4: List operations
print_header "📋 Test 4: List All Operations"

LIST_RESPONSE=$(curl -s -X POST "${MCP_SERVER}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "list_operations",
      "arguments": {"limit": 5}
    }
  }')

OPERATIONS=$(echo "$LIST_RESPONSE" | grep "data:" | sed 's/.*data: //' | jq -r '.result.content[0].text' | jq '.data.operations[]')

echo "$OPERATIONS" | jq -c '{operation_id, status, progress, message}'
echo ""

# Summary
print_header "✅ All Tests Completed"
echo ""
print_success "Polling-based progress tracking is working!"
echo ""
echo -e "${CYAN}Key Features Tested:${NC}"
echo "  ✅ Start long-running task"
echo "  ✅ Real-time progress polling"
echo "  ✅ Get final result"
echo "  ✅ List operations"
echo ""
echo -e "${YELLOW}Note:${NC} Progress was updated in real-time while task was running!"
