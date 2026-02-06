#!/bin/bash
# E2E Test: MCP Protocol Compliance
# Tests basic MCP JSON-RPC 2.0 protocol operations

set -e

MCP_URL="${MCP_URL:-http://localhost:8000}"
VERBOSE="${VERBOSE:-false}"

log() {
    if [ "$VERBOSE" = "true" ]; then
        echo "[$(date '+%H:%M:%S')] $1"
    fi
}

check_response() {
    local response="$1"
    local expected_key="$2"

    if echo "$response" | jq -e ".$expected_key" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

echo "=== MCP Protocol E2E Test ==="
echo "Server: $MCP_URL"
echo ""

# Test 1: Initialize
echo "1. Testing initialize..."
INIT_RESPONSE=$(curl -s -X POST "$MCP_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "e2e_test", "version": "1.0.0"}
        }
    }')

if check_response "$INIT_RESPONSE" "result"; then
    echo "   ✓ Initialize successful"
    log "   Response: $INIT_RESPONSE"
else
    echo "   ✗ Initialize failed"
    echo "   Response: $INIT_RESPONSE"
    exit 1
fi

# Test 2: List Tools
echo "2. Testing tools/list..."
TOOLS_RESPONSE=$(curl -s -X POST "$MCP_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }')

if check_response "$TOOLS_RESPONSE" "result.tools"; then
    TOOL_COUNT=$(echo "$TOOLS_RESPONSE" | jq '.result.tools | length')
    echo "   ✓ Listed $TOOL_COUNT tools"
    log "   Response: $TOOLS_RESPONSE"
else
    echo "   ✗ tools/list failed"
    echo "   Response: $TOOLS_RESPONSE"
    exit 1
fi

# Test 3: List Prompts
echo "3. Testing prompts/list..."
PROMPTS_RESPONSE=$(curl -s -X POST "$MCP_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 3,
        "method": "prompts/list",
        "params": {}
    }')

if check_response "$PROMPTS_RESPONSE" "result.prompts"; then
    PROMPT_COUNT=$(echo "$PROMPTS_RESPONSE" | jq '.result.prompts | length')
    echo "   ✓ Listed $PROMPT_COUNT prompts"
    log "   Response: $PROMPTS_RESPONSE"
else
    echo "   ✗ prompts/list failed"
    echo "   Response: $PROMPTS_RESPONSE"
    exit 1
fi

# Test 4: List Resources
echo "4. Testing resources/list..."
RESOURCES_RESPONSE=$(curl -s -X POST "$MCP_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 4,
        "method": "resources/list",
        "params": {}
    }')

if check_response "$RESOURCES_RESPONSE" "result.resources"; then
    RESOURCE_COUNT=$(echo "$RESOURCES_RESPONSE" | jq '.result.resources | length')
    echo "   ✓ Listed $RESOURCE_COUNT resources"
    log "   Response: $RESOURCES_RESPONSE"
else
    echo "   ✗ resources/list failed"
    echo "   Response: $RESOURCES_RESPONSE"
    exit 1
fi

# Test 5: Error handling (invalid method)
echo "5. Testing error handling..."
ERROR_RESPONSE=$(curl -s -X POST "$MCP_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": 5,
        "method": "invalid/method",
        "params": {}
    }')

if check_response "$ERROR_RESPONSE" "error"; then
    echo "   ✓ Error response received correctly"
    log "   Response: $ERROR_RESPONSE"
else
    echo "   ✗ Expected error response"
    echo "   Response: $ERROR_RESPONSE"
    exit 1
fi

echo ""
echo "=== All MCP Protocol Tests Passed ==="
exit 0
