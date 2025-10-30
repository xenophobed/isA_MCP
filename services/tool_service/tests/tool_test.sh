#!/usr/bin/env bash
#
# Tool Service Test Script
# Tests tool registration, CRUD operations, and statistics
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$SERVICE_DIR")")"

echo -e "${YELLOW}=== MCP Tool Service Tests ===${NC}\n"

# Run Python tests
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

python3 -m pytest services/tool_service/tests/test_tool_service.py -v

echo -e "\n${GREEN}✓ All tests passed${NC}"
