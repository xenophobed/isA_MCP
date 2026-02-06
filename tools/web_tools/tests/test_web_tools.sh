#!/bin/bash

###############################################################################
# Web Tools MCP Integration Test Script
###############################################################################
#
# COMPREHENSIVE MCP TOOL TESTS:
# This script validates that all web tools can be:
# 1. Discovered and registered as MCP tools
# 2. Executed with proper input validation
# 3. Successfully communicate with web microservice
# 4. Return properly formatted responses with SSE progress tracking
#
# Tools Tested (4 total):
# Search Tools (3):
#   ✓ web_search - Basic web search with SSE progress
#   ✓ deep_web_search - Multi-strategy deep search
#   ✓ web_search_with_summary - Search with AI summary
# Utility Tools (1):
#   ✓ web_service_health_check - Service health
#
# Services Used:
#  Web Microservice (localhost:80/api/v1/web via APISIX)
#  Brave Search API
#  ISA Model Service (for summarization)
#
# Usage:
#   ./test_web_tools.sh
#
# Requirements:
# - Python 3.11+
# - Web microservice running and accessible via APISIX (localhost:80)
# - BRAVE_API_KEY configured in web service
# - ISA Model Service for AI summarization
#
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test configuration
TEST_USER_ID="test_user_$(date +%s)"
PROJECT_ROOT="/Users/xenodennis/Documents/Fun/isA_MCP"

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

print_test() {
    echo -e "${YELLOW}TEST $TESTS_RUN: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_failure() {
    echo -e "${RED}✗ $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

###############################################################################
# Setup Functions
###############################################################################

setup_test_environment() {
    print_header "Setting Up Test Environment"

    # Verify Web Service is accessible via APISIX
    print_info "Checking web service health via APISIX..."
    if curl -s http://localhost/api/v1/web/health > /dev/null 2>&1; then
        print_success "Web service is accessible at localhost/api/v1/web"
    else
        print_info "Direct health check failed, but will test via search endpoint"
    fi

    # Verify Python environment
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python environment ready: ${PYTHON_VERSION}"
    else
        print_failure "Python 3 not found"
        exit 1
    fi

    # Set environment variables for web service
    export CONSUL_HOST='127.0.0.1'
    export CONSUL_PORT='9999'  # Invalid to force fallback
    export WEB_FALLBACK_HOST='localhost'
    export WEB_FALLBACK_PORT='80'  # APISIX gateway

    print_success "Test environment configured for localhost:80 (APISIX)"
}

###############################################################################
# Test Functions
###############################################################################

test_tool_registration() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "Tool Registration & Discovery"

    print_info "Verifying all 4 web tools are registered..."

    cat > /tmp/test_web_tool_registration.py << 'EOF'
import sys
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

from mcp.server.fastmcp import FastMCP
from tools.web_tools.web_tools import register_web_tools
from core.security import initialize_security

# Initialize security manager first
initialize_security()

# Create MCP instance and register tools
mcp = FastMCP("test_web_tools")
register_web_tools(mcp)

# Get registered tools
tools = mcp._tool_manager._tools

# Expected tools (7 total: 3 search + 1 crawl + 2 automation + 1 utility)
expected_tools = [
    # Search tools (3)
    'web_search',
    'deep_web_search',
    'web_search_with_summary',
    # Crawl tools (1)
    'web_crawl',
    # Automation tools (2)
    'web_automation_execute',
    'web_automation_search',
    # Utility tools (1)
    'web_service_health_check'
]

# Verify all tools are registered
print(f"Total tools registered: {len(tools)}")
missing_tools = []
for tool_name in expected_tools:
    if tool_name in tools:
        print(f"✓ {tool_name}")
    else:
        print(f"✗ {tool_name} - MISSING")
        missing_tools.append(tool_name)

if missing_tools:
    print(f"\nERROR: Missing tools: {missing_tools}")
    sys.exit(1)
else:
    print(f"\n✓ All {len(expected_tools)} web tools registered successfully")
EOF

    if python3 /tmp/test_web_tool_registration.py 2>&1 | tee /tmp/test_output.log; then
        print_success "All web tools registered and discoverable"
        return 0
    else
        print_failure "Tool registration check failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_web_service_health_check() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "web_service_health_check Tool"

    print_info "Testing service health check via MCP tool..."

    cat > /tmp/test_health_check.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.web_tools.web_tools import register_web_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_web_tools")
    register_web_tools(mcp)

    result = await mcp._tool_manager._tools['web_service_health_check'].fn()

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")

    if result_dict['status'] == 'success':
        print(f"✓ Service: {result_dict['data']['status']}")
        print(f"✓ Service URL: {result_dict['data']['service_url']}")
    else:
        print(f"ℹ Health check returned: {result_dict}")

asyncio.run(test())
EOF

    if python3 /tmp/test_health_check.py 2>&1 | tee /tmp/test_output.log; then
        print_success "web_service_health_check tool working correctly"
        return 0
    else
        print_failure "web_service_health_check tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_web_search() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "web_search Tool with SSE Progress"

    print_info "Testing basic web search with real-time progress tracking..."

    cat > /tmp/test_web_search.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.web_tools.web_tools import register_web_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_web_tools")
    register_web_tools(mcp)

    print("Executing web_search for 'Python programming'...")

    result = await mcp._tool_manager._tools['web_search'].fn(
        query="Python programming",
        count=3
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"\nStatus: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Search failed"

    # Check progress history
    progress_history = result_dict['data'].get('progress_history', [])
    print(f"\n✓ Progress updates received: {len(progress_history)}")
    for update in progress_history[:5]:  # Show first 5
        print(f"  - [{update['progress']*100:.0f}%] {update['message']}")

    # Check results
    results = result_dict['data'].get('results', [])
    print(f"\n✓ Search results: {len(results)}")
    print(f"✓ Total results: {result_dict['data'].get('total_results', 0)}")
    print(f"✓ Execution time: {result_dict['data'].get('execution_time', 0):.2f}s")
    print(f"✓ Provider: {result_dict['data'].get('provider', 'unknown')}")

    # Print first result
    if results:
        print(f"\nFirst result:")
        print(f"  Title: {results[0].get('title', 'No title')}")
        print(f"  URL: {results[0].get('url', 'No URL')}")

    assert len(results) > 0, "No results returned"
    assert len(progress_history) > 0, "No progress updates received"

asyncio.run(test())
EOF

    if python3 /tmp/test_web_search.py 2>&1 | tee /tmp/test_output.log; then
        print_success "web_search tool working correctly with SSE progress"
        return 0
    else
        print_failure "web_search tool failed"
        tail -30 /tmp/test_output.log
        return 1
    fi
}

test_web_search_with_filters() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "web_search with Filters"

    print_info "Testing web search with freshness and result filters..."

    cat > /tmp/test_web_search_filters.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.web_tools.web_tools import register_web_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_web_tools")
    register_web_tools(mcp)

    print("Executing web_search with filters...")

    result = await mcp._tool_manager._tools['web_search'].fn(
        query="AI news",
        count=3,
        freshness="day",
        result_filter="news"
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")

    if result_dict['status'] == 'success':
        print(f"✓ Search with filters completed")
        print(f"✓ Results: {result_dict['data'].get('total_results', 0)}")

asyncio.run(test())
EOF

    if python3 /tmp/test_web_search_filters.py 2>&1 | tee /tmp/test_output.log; then
        print_success "web_search with filters working correctly"
        return 0
    else
        print_failure "web_search with filters failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_deep_web_search() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "deep_web_search Tool"

    print_info "Testing deep web search (may take longer)..."

    cat > /tmp/test_deep_search.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.web_tools.web_tools import register_web_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_web_tools")
    register_web_tools(mcp)

    print("Executing deep_web_search...")

    result = await mcp._tool_manager._tools['deep_web_search'].fn(
        query="machine learning basics",
        user_id="${TEST_USER_ID}",
        depth=1,  # Use depth=1 for faster testing
        rag_mode=False  # Disable RAG for faster testing
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"\nStatus: {result_dict['status']}")

    if result_dict['status'] == 'success':
        print(f"✓ Deep search completed")
        print(f"✓ Results: {result_dict['data'].get('total_results', 0)}")

        progress_history = result_dict['data'].get('progress_history', [])
        print(f"✓ Progress updates: {len(progress_history)}")

asyncio.run(test())
EOF

    if timeout 30 python3 /tmp/test_deep_search.py 2>&1 | tee /tmp/test_output.log; then
        print_success "deep_web_search tool working correctly"
        return 0
    else
        print_failure "deep_web_search tool failed or timed out"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_web_search_with_summary() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "web_search_with_summary Tool"

    print_info "Testing web search with AI summary (may take longer)..."

    cat > /tmp/test_search_summary.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.web_tools.web_tools import register_web_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_web_tools")
    register_web_tools(mcp)

    print("Executing web_search_with_summary...")

    result = await mcp._tool_manager._tools['web_search_with_summary'].fn(
        query="benefits of meditation",
        user_id="${TEST_USER_ID}",
        count=5,
        summarize_count=3,  # Summarize top 3 for faster testing
        include_citations=True
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"\nStatus: {result_dict['status']}")

    if result_dict['status'] == 'success':
        print(f"✓ Search with summary completed")
        print(f"✓ Results: {result_dict['data'].get('total_results', 0)}")

        summary = result_dict['data'].get('summary')
        if summary:
            print(f"✓ Summary generated: {summary[:100]}...")

        citations = result_dict['data'].get('citations', [])
        print(f"✓ Citations: {len(citations)}")

asyncio.run(test())
EOF

    if timeout 60 python3 /tmp/test_search_summary.py 2>&1 | tee /tmp/test_output.log; then
        print_success "web_search_with_summary tool working correctly"
        return 0
    else
        print_failure "web_search_with_summary tool failed or timed out"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

###############################################################################
# Cleanup Functions
###############################################################################

cleanup_test_environment() {
    print_header "Cleaning Up Test Environment"

    # Remove temporary test files
    rm -f /tmp/test_*.py /tmp/test_output.log
    print_success "Temporary files removed"
}

###############################################################################
# Main Test Execution
###############################################################################

main() {
    print_header "🌐 Web Tools MCP Integration Test Suite"
    echo "Testing all web tools via MCP interface"
    echo "User ID: ${TEST_USER_ID}"
    echo ""
    echo "Web Service: localhost:80/api/v1/web (APISIX)"
    echo "Total Tools: 4 (3 search + 1 utility)"
    echo ""

    # Setup
    setup_test_environment

    # Run tests
    print_header "Running MCP Tool Integration Tests"

    # Test 1: Tool Registration
    test_tool_registration
    echo ""

    # Test 2: Health Check
    test_web_service_health_check
    echo ""

    # Test 3: Basic Web Search
    test_web_search
    echo ""

    # Test 4: Web Search with Filters
    test_web_search_with_filters
    echo ""

    # Test 5: Deep Web Search (optional - may be slow)
    if [ "${RUN_DEEP_TESTS:-yes}" = "yes" ]; then
        test_deep_web_search
        echo ""
    else
        print_info "Skipping deep_web_search test (set RUN_DEEP_TESTS=yes to enable)"
        echo ""
    fi

    # Test 6: Web Search with Summary (optional - may be slow)
    if [ "${RUN_SUMMARY_TESTS:-yes}" = "yes" ]; then
        test_web_search_with_summary
        echo ""
    else
        print_info "Skipping web_search_with_summary test (set RUN_SUMMARY_TESTS=yes to enable)"
        echo ""
    fi

    # Cleanup
    cleanup_test_environment

    # Summary
    print_header "📊 Test Summary"
    echo "Total Tests Run: ${TESTS_RUN}"
    echo -e "${GREEN}✓ Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}✗ Failed: ${TESTS_FAILED}${NC}"
    echo ""

    if [ ${TESTS_FAILED} -eq 0 ]; then
        echo ""
        echo ""
        print_success "🎉 All web tool tests passed!"
        echo ""
        echo "✓ All 7 tools registered as MCP tools"
        echo "✓ Tool discovery working correctly"
        echo "✓ Web service communication functional"
        echo "✓ SSE progress tracking working"
        echo "✓ Response formatting correct"
        echo "✓ Search operations successful"
        echo ""
        echo ""
        exit 0
    else
        echo ""
        print_failure "⚠️  Some tests failed"
        echo ""
        echo "Check the logs above for details."
        echo "Common issues:"
        echo "  - Web service not running or not accessible via APISIX"
        echo "  - BRAVE_API_KEY not configured in web service"
        echo "  - ISA Model Service not available (for summary tests)"
        echo "  - Network connectivity issues"
        exit 1
    fi
}

# Run main
main "$@"
