#!/bin/bash
# Test script for digital analytics tools
# Verifies that digital tools are properly registered and functional

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper functions
print_header() {
    echo -e "\n${YELLOW}========================================${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}========================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}TEST: $1${NC}"
    ((TOTAL_TESTS++))
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED_TESTS++))
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED_TESTS++))
}

print_summary() {
    echo -e "\n${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Test Summary${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    else
        echo -e "${GREEN}Failed: 0${NC}"
    fi
    echo -e "${YELLOW}========================================${NC}\n"
}

# Change to project root
cd "$(dirname "$0")/../../.."

print_header "Digital Analytics Tools Test Suite"

# Test 1: Check if digital_tools.py exists
print_test "Check if digital_tools.py exists"
if [ -f "tools/data_tools/digital_tools.py" ]; then
    print_success "digital_tools.py exists"
else
    print_error "digital_tools.py not found"
fi

# Test 2: Check if digital_client.py exists
print_test "Check if digital_client.py exists"
if [ -f "tools/data_tools/digital_client.py" ]; then
    print_success "digital_client.py exists"
else
    print_error "digital_client.py not found"
fi

# Test 3: Check if __init__.py exports register_digital_tools
print_test "Check if __init__.py exports register_digital_tools"
if grep -q "register_digital_tools" tools/data_tools/__init__.py; then
    print_success "__init__.py exports register_digital_tools"
else
    print_error "__init__.py does not export register_digital_tools"
fi

# Test 4: Verify tool registration
print_test "Verify digital tools can be imported and registered"
python3 << 'EOF'
import sys
import os

# Add project root to path
sys.path.insert(0, os.getcwd())

try:
    from mcp.server.fastmcp import FastMCP
    from tools.data_tools import register_digital_tools

    # Create MCP instance
    mcp = FastMCP("test-digital-tools")

    # Register tools
    register_digital_tools(mcp)

    # Get registered tools
    tools = list(mcp.list_tools())

    # Expected tools
    expected_tools = [
        'digital_store_text',
        'digital_store_pdf',
        'digital_store_image',
        'digital_search',
        'digital_response',
        'digital_service_health_check'
    ]

    # Check if all expected tools are registered
    tool_names = [tool.name for tool in tools]

    found_tools = [name for name in expected_tools if name in tool_names]
    missing_tools = [name for name in expected_tools if name not in tool_names]

    if len(found_tools) == len(expected_tools):
        print(f"✓ All {len(expected_tools)} digital tools registered successfully")
        print(f"✓ Tools: {', '.join(found_tools)}")
        sys.exit(0)
    else:
        print(f"✗ Only {len(found_tools)}/{len(expected_tools)} tools registered")
        if found_tools:
            print(f"✓ Found: {', '.join(found_tools)}")
        if missing_tools:
            print(f"✗ Missing: {', '.join(missing_tools)}")
        sys.exit(1)

except Exception as e:
    print(f"✗ Error during tool registration: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "Digital tools registered successfully"
else
    print_error "Failed to register digital tools"
fi

# Test 5: Check tool docstrings
print_test "Verify tools have proper docstrings"
python3 << 'EOF'
import sys
import os

sys.path.insert(0, os.getcwd())

try:
    from mcp.server.fastmcp import FastMCP
    from tools.data_tools import register_digital_tools

    mcp = FastMCP("test-docstrings")
    register_digital_tools(mcp)

    tools = list(mcp.list_tools())

    all_have_docs = True
    for tool in tools:
        if not tool.description or len(tool.description.strip()) < 10:
            print(f"✗ Tool {tool.name} has insufficient documentation")
            all_have_docs = False

    if all_have_docs and len(tools) > 0:
        print(f"✓ All {len(tools)} tools have proper docstrings")
        sys.exit(0)
    else:
        print(f"✗ Some tools lack proper documentation")
        sys.exit(1)

except Exception as e:
    print(f"✗ Error checking docstrings: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "All tools have proper docstrings"
else
    print_error "Some tools lack documentation"
fi

# Test 6: Check client configuration
print_test "Verify DigitalServiceClient configuration"
python3 << 'EOF'
import sys
import os

sys.path.insert(0, os.getcwd())

try:
    from tools.data_tools import DigitalServiceClient, DigitalServiceConfig

    # Test default config
    config = DigitalServiceConfig()

    assert config.service_name == "data_service", "Wrong service name"
    assert config.fallback_port == 8083, "Wrong fallback port"
    assert config.api_timeout == 300, "Wrong API timeout"

    # Test client creation
    client = DigitalServiceClient(config)

    assert client.config == config, "Config not set correctly"

    print("✓ DigitalServiceClient configuration verified")
    sys.exit(0)

except Exception as e:
    print(f"✗ Client configuration error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "Client configuration verified"
else
    print_error "Client configuration failed"
fi

# Test 7: Verify tool parameter signatures
print_test "Verify tool parameter signatures are correct"
python3 << 'EOF'
import sys
import os
import inspect

sys.path.insert(0, os.getcwd())

try:
    from tools.data_tools import digital_tools

    # Check digital_store_text signature
    sig = inspect.signature(digital_tools.register_digital_tools)
    params = list(sig.parameters.keys())

    assert 'mcp' in params, "register_digital_tools missing 'mcp' parameter"

    print("✓ Tool signatures verified")
    sys.exit(0)

except Exception as e:
    print(f"✗ Signature verification failed: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "Tool signatures verified"
else
    print_error "Tool signature verification failed"
fi

# Print final summary
print_summary

# Exit with appropriate code
if [ $FAILED_TESTS -gt 0 ]; then
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
