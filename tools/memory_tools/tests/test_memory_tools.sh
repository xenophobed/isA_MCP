#!/bin/bash

###############################################################################
# Memory Tools MCP Integration Test Script
###############################################################################
#
# COMPREHENSIVE MCP TOOL TESTS:
# This script validates that all memory tools can be:
# 1. Discovered and registered as MCP tools
# 2. Executed with proper input validation
# 3. Successfully communicate with memory microservice
# 4. Return properly formatted responses
# Tools Tested (15 total):
# Storage Tools (6):
#   ✓ store_factual_memory - AI-powered fact extraction
#   ✓ store_episodic_memory - Event memory extraction
#   ✓ store_semantic_memory - Concept memory extraction
#   ✓ store_procedural_memory - Procedure extraction
#   ✓ store_working_memory - Short-term memory storage
#   ✓ store_session_message - Conversation tracking
# Search Tools (4):
#   ✓ search_memories - Universal search across all types
#   ✓ search_facts_by_subject - Factual search
#   ✓ search_episodes_by_event_type - Episodic search
#   ✓ search_concepts_by_category - Semantic search
# Retrieval Tools (3):
#   ✓ get_session_context - Session retrieval
#   ✓ summarize_session - AI session summarization
#   ✓ get_active_working_memories - Working memory retrieval
# Utility Tools (2):
#   ✓ get_memory_statistics - User memory stats
#   ✓ memory_health_check - Service health
#
#
# Services Used:
#  Memory Microservice (localhost:8223)
#  PostgreSQL (via microservice)
#  Qdrant Vector DB (via microservice)
#  OpenAI/Claude (for AI extraction)
#
# Usage:
#   ./test_memory_tools.sh
#
# Requirements:
# - Python 3.11+
# - Memory microservice running on localhost:8223
# - PostgreSQL and Qdrant accessible via microservice
# - AI model access for extraction operations
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
TEST_SESSION_ID="test_session_$(date +%s)"
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
    echo -e "${GREEN} $1${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_failure() {
    echo -e "${RED} $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

print_info() {
    echo -e "${CYAN}9 $1${NC}"
}

###############################################################################
# Setup Functions
###############################################################################

setup_test_environment() {
    print_header "Setting Up Test Environment"

    # Verify Memory Service is running
    print_info "Checking memory service health..."
    if curl -s http://localhost:8223/health > /dev/null 2>&1; then
        HEALTH=$(curl -s http://localhost:8223/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['status'])")
        if [ "$HEALTH" == "operational" ]; then
            print_success "Memory service is operational at localhost:8223"
        else
            print_failure "Memory service is not operational"
            exit 1
        fi
    else
        print_failure "Cannot connect to memory service at localhost:8223"
        echo "Please start the memory microservice first"
        exit 1
    fi

    # Verify Python environment
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python environment ready: ${PYTHON_VERSION}"
    else
        print_failure "Python 3 not found"
        exit 1
    fi

    # Set environment variables to force localhost connection
    export CONSUL_HOST='127.0.0.1'
    export CONSUL_PORT='9999'
    export MEMORY_FALLBACK_HOST='localhost'
    export MEMORY_FALLBACK_PORT='8223'

    print_success "Test environment configured for localhost:8223"
}

###############################################################################
# Test Functions
###############################################################################

test_tool_registration() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "Tool Registration & Discovery"

    print_info "Verifying all 14 memory tools are registered..."

    cat > /tmp/test_memory_tool_registration.py << 'EOF'
import sys
sys.path.insert(0, '/Users/xenodennis/Documents/Fun/isA_MCP')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

# Initialize security manager first
initialize_security()

# Create MCP instance and register tools
mcp = FastMCP("test_memory_tools")
register_memory_tools(mcp)

# Get registered tools
tools = mcp._tool_manager._tools

# Expected tools (15 total: 6 storage + 4 search + 3 retrieval + 2 utility)
expected_tools = [
    # Storage tools (6)
    'store_factual_memory',
    'store_episodic_memory',
    'store_semantic_memory',
    'store_procedural_memory',
    'store_working_memory',
    'store_session_message',
    # Search tools (4) - All implemented!
    'search_memories',  # Universal search across all types
    'search_facts_by_subject',
    'search_episodes_by_event_type',
    'search_concepts_by_category',
    # Retrieval tools (3)
    'get_session_context',
    'summarize_session',
    'get_active_working_memories',
    # Utility tools (2)
    'get_memory_statistics',
    'memory_health_check'
]

# Verify all tools are registered
print(f"Total tools registered: {len(tools)}")
missing_tools = []
for tool_name in expected_tools:
    if tool_name in tools:
        print(f" {tool_name}")
    else:
        print(f" {tool_name} - MISSING")
        missing_tools.append(tool_name)

if missing_tools:
    print(f"\nERROR: Missing tools: {missing_tools}")
    sys.exit(1)
else:
    print(f"\n All {len(expected_tools)} memory tools registered successfully")
EOF

    if python3 /tmp/test_memory_tool_registration.py 2>&1 | tee /tmp/test_output.log; then
        print_success "All memory tools registered and discoverable"
        return 0
    else
        print_failure "Tool registration check failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_memory_health_check() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "memory_health_check Tool"

    print_info "Testing service health check via MCP tool..."

    cat > /tmp/test_health_check.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['memory_health_check'].fn()
    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Health check failed"
    assert result_dict['data']['status'] == 'operational', "Service not operational"

    print(f" Service: {result_dict['data']['service']}")
    print(f" Version: {result_dict['data']['version']}")
    print(f" Database Connected: {result_dict['data']['database_connected']}")

asyncio.run(test())
EOF

    if python3 /tmp/test_health_check.py 2>&1 | tee /tmp/test_output.log; then
        print_success "memory_health_check tool working correctly"
        return 0
    else
        print_failure "memory_health_check tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_store_factual_memory() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "store_factual_memory Tool"

    print_info "Testing AI-powered factual memory extraction..."

    cat > /tmp/test_store_factual.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['store_factual_memory'].fn(
        user_id="${TEST_USER_ID}",
        dialog_content="My favorite programming language is Python and I work as a software engineer.",
        importance_score=0.8
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Store failed"
    assert result_dict['data']['success'] == True, "Extraction not successful"

    print(f" Memories stored: {result_dict['data'].get('affected_count', 'N/A')}")
    print(f" Message: {result_dict['data']['message']}")

asyncio.run(test())
EOF

    if python3 /tmp/test_store_factual.py 2>&1 | tee /tmp/test_output.log; then
        print_success "store_factual_memory tool working correctly"
        return 0
    else
        print_failure "store_factual_memory tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_store_episodic_memory() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "store_episodic_memory Tool"

    print_info "Testing AI-powered episodic memory extraction..."

    cat > /tmp/test_store_episodic.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['store_episodic_memory'].fn(
        user_id="${TEST_USER_ID}",
        dialog_content="Last Tuesday I attended a team meeting where we discussed the new project roadmap.",
        importance_score=0.7
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Store failed"

    print(f" Message: {result_dict['data']['message']}")

asyncio.run(test())
EOF

    if python3 /tmp/test_store_episodic.py 2>&1 | tee /tmp/test_output.log; then
        print_success "store_episodic_memory tool working correctly"
        return 0
    else
        print_failure "store_episodic_memory tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_store_semantic_memory() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "store_semantic_memory Tool"

    print_info "Testing AI-powered semantic memory extraction..."

    cat > /tmp/test_store_semantic.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['store_semantic_memory'].fn(
        user_id="${TEST_USER_ID}",
        dialog_content="Machine learning is a subset of artificial intelligence that focuses on data-driven algorithms.",
        importance_score=0.6
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Store failed"

    print(f" Message: {result_dict['data']['message']}")

asyncio.run(test())
EOF

    if python3 /tmp/test_store_semantic.py 2>&1 | tee /tmp/test_output.log; then
        print_success "store_semantic_memory tool working correctly"
        return 0
    else
        print_failure "store_semantic_memory tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_store_procedural_memory() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "store_procedural_memory Tool"

    print_info "Testing AI-powered procedural memory extraction..."

    cat > /tmp/test_store_procedural.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['store_procedural_memory'].fn(
        user_id="${TEST_USER_ID}",
        dialog_content="To deploy the application, first run tests, then build the Docker image, and finally push to production.",
        importance_score=0.9
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Store failed"

    print(f" Message: {result_dict['data']['message']}")

asyncio.run(test())
EOF

    if python3 /tmp/test_store_procedural.py 2>&1 | tee /tmp/test_output.log; then
        print_success "store_procedural_memory tool working correctly"
        return 0
    else
        print_failure "store_procedural_memory tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_store_working_memory() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "store_working_memory Tool"

    print_info "Testing working memory storage with TTL..."

    cat > /tmp/test_store_working.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['store_working_memory'].fn(
        user_id="${TEST_USER_ID}",
        dialog_content="Currently reviewing PR #456, waiting for feedback from team",
        ttl_seconds=3600,
        importance_score=0.5
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Store failed"

    print(f" Message: {result_dict['data']['message']}")

asyncio.run(test())
EOF

    if python3 /tmp/test_store_working.py 2>&1 | tee /tmp/test_output.log; then
        print_success "store_working_memory tool working correctly"
        return 0
    else
        print_failure "store_working_memory tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_store_session_message() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "store_session_message Tool"

    print_info "Testing session message storage..."

    cat > /tmp/test_store_session.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    # Store first message
    result1 = await mcp._tool_manager._tools['store_session_message'].fn(
        user_id="${TEST_USER_ID}",
        session_id="${TEST_SESSION_ID}",
        message_content="Hello, I need help with Python",
        message_type="human",
        role="user"
    )

    # Store second message
    result2 = await mcp._tool_manager._tools['store_session_message'].fn(
        user_id="${TEST_USER_ID}",
        session_id="${TEST_SESSION_ID}",
        message_content="I can help you with Python. What do you need?",
        message_type="ai",
        role="assistant"
    )

    # Handle both dict and string responses
    if isinstance(result1, str):
        result_dict = json.loads(result1)
    else:
        result_dict = result1

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Store failed"

    print(f" Messages stored in session: ${TEST_SESSION_ID}")

asyncio.run(test())
EOF

    if python3 /tmp/test_store_session.py 2>&1 | tee /tmp/test_output.log; then
        print_success "store_session_message tool working correctly"
        return 0
    else
        print_failure "store_session_message tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_search_facts_by_subject() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "search_facts_by_subject Tool"

    print_info "Testing factual memory search..."

    cat > /tmp/test_search_facts.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['search_facts_by_subject'].fn(
        user_id="${TEST_USER_ID}",
        subject="programming",
        limit=10
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Search failed"

    print(f" Search completed successfully")
    results = result_dict['data'].get('results', [])
    print(f" Results found: {len(results)}")

asyncio.run(test())
EOF

    if python3 /tmp/test_search_facts.py 2>&1 | tee /tmp/test_output.log; then
        print_success "search_facts_by_subject tool working correctly"
        return 0
    else
        print_failure "search_facts_by_subject tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_search_memories() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "search_memories Tool (Universal Search)"

    print_info "Testing universal memory search across all types..."

    cat > /tmp/test_search_memories.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    # Test 1: Search all memory types
    result1 = await mcp._tool_manager._tools['search_memories'].fn(
        user_id="${TEST_USER_ID}",
        query="python programming",
        top_k=10
    )

    # Handle both dict and string responses
    if isinstance(result1, str):
        result_dict1 = json.loads(result1)
    else:
        result_dict1 = result1

    print(f"Status: {result_dict1['status']}")
    assert result_dict1['status'] == 'success', "Universal search failed"
    print(f"✓ Search all types completed")

    # Test 2: Search specific memory types
    result2 = await mcp._tool_manager._tools['search_memories'].fn(
        user_id="${TEST_USER_ID}",
        query="python",
        memory_types=["factual", "semantic"],
        top_k=5
    )

    if isinstance(result2, str):
        result_dict2 = json.loads(result2)
    else:
        result_dict2 = result2

    print(f"✓ Search specific types (factual, semantic) completed")

asyncio.run(test())
EOF

    if python3 /tmp/test_search_memories.py 2>&1 | tee /tmp/test_output.log; then
        print_success "search_memories tool working correctly"
        return 0
    else
        print_failure "search_memories tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_search_episodes_by_event_type() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "search_episodes_by_event_type Tool"

    print_info "Testing episodic memory search by event type..."

    cat > /tmp/test_search_episodes.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['search_episodes_by_event_type'].fn(
        user_id="${TEST_USER_ID}",
        event_type="meeting",
        limit=10
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Search failed"

    print(f"✓ Search completed successfully")
    results = result_dict['data'].get('results', [])
    print(f"✓ Results found: {len(results)}")

asyncio.run(test())
EOF

    if python3 /tmp/test_search_episodes.py 2>&1 | tee /tmp/test_output.log; then
        print_success "search_episodes_by_event_type tool working correctly"
        return 0
    else
        print_failure "search_episodes_by_event_type tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_search_concepts_by_category() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "search_concepts_by_category Tool"

    print_info "Testing semantic concept search..."

    cat > /tmp/test_search_concepts.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['search_concepts_by_category'].fn(
        user_id="${TEST_USER_ID}",
        category="technology",
        limit=10
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Search failed"

    print(f" Search completed successfully")
    results = result_dict['data'].get('results', [])
    print(f" Results found: {len(results)}")

asyncio.run(test())
EOF

    if python3 /tmp/test_search_concepts.py 2>&1 | tee /tmp/test_output.log; then
        print_success "search_concepts_by_category tool working correctly"
        return 0
    else
        print_failure "search_concepts_by_category tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_get_session_context() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "get_session_context Tool"

    print_info "Testing session context retrieval..."

    cat > /tmp/test_get_session.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['get_session_context'].fn(
        user_id="${TEST_USER_ID}",
        session_id="${TEST_SESSION_ID}",
        include_summaries=True,
        max_recent_messages=5
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Get session failed"

    print(f" Session context retrieved")

asyncio.run(test())
EOF

    if python3 /tmp/test_get_session.py 2>&1 | tee /tmp/test_output.log; then
        print_success "get_session_context tool working correctly"
        return 0
    else
        print_failure "get_session_context tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_summarize_session() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "summarize_session Tool"

    print_info "Testing AI-powered session summarization..."

    cat > /tmp/test_summarize_session.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['summarize_session'].fn(
        user_id="${TEST_USER_ID}",
        session_id="${TEST_SESSION_ID}",
        force_update=True,
        compression_level="medium"
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Summarize session failed"

    print(f"✓ Session summarized successfully")
    if 'summary' in result_dict.get('data', {}):
        summary = result_dict['data']['summary']
        print(f"✓ Summary generated: {summary[:100]}...")

asyncio.run(test())
EOF

    if python3 /tmp/test_summarize_session.py 2>&1 | tee /tmp/test_output.log; then
        print_success "summarize_session tool working correctly"
        return 0
    else
        print_failure "summarize_session tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_get_active_working_memories() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "get_active_working_memories Tool"

    print_info "Testing active working memories retrieval..."

    cat > /tmp/test_get_working.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['get_active_working_memories'].fn(
        user_id="${TEST_USER_ID}"
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Get working memories failed"

    print(f" Active working memories retrieved")

asyncio.run(test())
EOF

    if python3 /tmp/test_get_working.py 2>&1 | tee /tmp/test_output.log; then
        print_success "get_active_working_memories tool working correctly"
        return 0
    else
        print_failure "get_active_working_memories tool failed"
        tail -20 /tmp/test_output.log
        return 1
    fi
}

test_get_memory_statistics() {
    TESTS_RUN=$((TESTS_RUN + 1))
    print_test "get_memory_statistics Tool"

    print_info "Testing memory statistics retrieval..."

    cat > /tmp/test_get_stats.py << EOF
import asyncio
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}')

from mcp.server.fastmcp import FastMCP
from tools.memory_tools.memory_tools import register_memory_tools
from core.security import initialize_security

async def test():
    initialize_security()
    mcp = FastMCP("test_memory_tools")
    register_memory_tools(mcp)

    result = await mcp._tool_manager._tools['get_memory_statistics'].fn(
        user_id="${TEST_USER_ID}"
    )

    # Handle both dict and string responses
    if isinstance(result, str):
        result_dict = json.loads(result)
    else:
        result_dict = result

    print(f"Status: {result_dict['status']}")
    assert result_dict['status'] == 'success', "Get statistics failed"

    print(f" User ID: {result_dict['data']['user_id']}")
    print(f" Total memories: {result_dict['data'].get('total_memories', 0)}")

    by_type = result_dict['data'].get('by_type', {})
    if by_type:
        print(f" Factual: {by_type.get('factual', 0)}")
        print(f" Episodic: {by_type.get('episodic', 0)}")
        print(f" Semantic: {by_type.get('semantic', 0)}")
        print(f" Procedural: {by_type.get('procedural', 0)}")
        print(f" Working: {by_type.get('working', 0)}")
        print(f" Session: {by_type.get('session', 0)}")

asyncio.run(test())
EOF

    if python3 /tmp/test_get_stats.py 2>&1 | tee /tmp/test_output.log; then
        print_success "get_memory_statistics tool working correctly"
        return 0
    else
        print_failure "get_memory_statistics tool failed"
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
    print_header ">� Memory Tools MCP Integration Test Suite"
    echo "Testing all memory tools via MCP interface"
    echo "User ID: ${TEST_USER_ID}"
    echo "Session ID: ${TEST_SESSION_ID}"
    echo ""
    echo "Memory Service: localhost:8223"
    echo "Total Tools: 15 (6 storage + 4 search + 3 retrieval + 2 utility)"
    echo ""

    # Setup
    setup_test_environment

    # Run tests
    print_header "Running MCP Tool Integration Tests"

    # Test 1: Tool Registration
    test_tool_registration
    echo ""

    # Test 2: Health Check
    test_memory_health_check
    echo ""

    # Test 3: Store Factual Memory
    test_store_factual_memory
    echo ""

    # Test 4: Store Episodic Memory
    test_store_episodic_memory
    echo ""

    # Test 5: Store Semantic Memory
    test_store_semantic_memory
    echo ""

    # Test 6: Store Procedural Memory
    test_store_procedural_memory
    echo ""

    # Test 7: Store Working Memory
    test_store_working_memory
    echo ""

    # Test 8: Store Session Messages
    test_store_session_message
    echo ""

    # Test 9: Search Facts
    test_search_facts_by_subject
    echo ""

    # Test 10: Universal Search (All Types)
    test_search_memories
    echo ""

    # Test 11: Search Episodes by Event Type
    test_search_episodes_by_event_type
    echo ""

    # Test 12: Search Concepts by Category
    test_search_concepts_by_category
    echo ""

    # Test 13: Get Session Context
    test_get_session_context
    echo ""

    # Test 14: Summarize Session
    test_summarize_session
    echo ""

    # Test 15: Get Active Working Memories
    test_get_active_working_memories
    echo ""

    # Test 16: Get Memory Statistics
    test_get_memory_statistics
    echo ""

    # Cleanup
    cleanup_test_environment

    # Summary
    print_header "<� Test Summary"
    echo "Total Tests Run: ${TESTS_RUN}"
    echo -e "${GREEN} Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED} Failed: ${TESTS_FAILED}${NC}"
    echo ""

    if [ ${TESTS_FAILED} -eq 0 ]; then
        echo ""
        echo ""
        print_success "<� All memory tool tests passed!"
        echo ""
        echo " All 15 tools registered as MCP tools"
        echo " Tool discovery working correctly"
        echo " Memory service communication functional"
        echo " Response formatting correct"
        echo " Storage operations successful"
        echo " Search operations functional"
        echo " Session management working"
        echo " Statistics retrieval operational"
        echo ""
        echo ""
        exit 0
    else
        echo ""
        print_failure "�  Some tests failed"
        echo ""
        echo "Check the logs above for details."
        echo "Common issues:"
        echo "  - Memory service not running (start on port 8223)"
        echo "  - Database connection issues"
        echo "  - AI model access not configured"
        echo "  - Missing Python dependencies"
        exit 1
    fi
}

# Run main
main "$@"
