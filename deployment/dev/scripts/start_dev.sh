#!/bin/bash
# ============================================
# ISA MCP Local Development Startup Script
# ============================================
# This script starts the MCP service locally (no Docker)
# All services use localhost connections
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the project root directory
# Script is in deployment/dev/scripts/, so go up 3 levels
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEV_CONFIG_DIR="$PROJECT_ROOT/deployment/dev/config"
ENV_FILE="$DEV_CONFIG_DIR/.env"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}ISA MCP - Local Development Server${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found at $ENV_FILE${NC}"
    echo -e "${YELLOW}Please create the .env file from .env.example${NC}"
    exit 1
fi

# Load environment variables
echo -e "${GREEN}✓ Loading environment variables from $ENV_FILE${NC}"
set -a
source "$ENV_FILE"
set +a

# Check if virtual environment exists
VENV_DIR="$PROJECT_ROOT/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
    echo -e "${YELLOW}Please create it with: python3 -m venv .venv${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠ uv is not installed. Installing...${NC}"
    pip install uv
fi

# Check if dependencies are installed
echo -e "${BLUE}Checking Python dependencies...${NC}"
if ! python -c "import fastapi, uvicorn, mcp" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Some dependencies are missing. Installing with uv...${NC}"
    uv pip install -r "$DEV_CONFIG_DIR/requirements.txt"
else
    echo -e "${GREEN}✓ All required dependencies are installed${NC}"
fi

# Check Supabase (optional but recommended)
echo -e "${BLUE}Checking Supabase...${NC}"
if curl -s --connect-timeout 2 "http://localhost:54321/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Supabase is running on localhost:54321${NC}"
else
    echo -e "${YELLOW}⚠ Supabase is not running${NC}"
    echo -e "${YELLOW}  Start with: cd $PROJECT_ROOT/resources/dbs/supabase/dev && supabase start${NC}"
fi

# Check Neo4j (optional)
echo -e "${BLUE}Checking Neo4j...${NC}"
if nc -z localhost 7687 2>/dev/null; then
    echo -e "${GREEN}✓ Neo4j is running on localhost:7687${NC}"
else
    echo -e "${YELLOW}⚠ Neo4j is not running (optional)${NC}"
    echo -e "${YELLOW}  Start with: neo4j start${NC}"
fi

# Check ISA Model Service (optional)
echo -e "${BLUE}Checking ISA Model Service...${NC}"
if curl -s --connect-timeout 2 "http://localhost:8082/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ISA Model Service is running on localhost:8082${NC}"
else
    echo -e "${YELLOW}⚠ ISA Model Service is not running${NC}"
    echo -e "${YELLOW}  The service will use fallback configurations${NC}"
fi

# Check if MinIO is running (optional)
echo -e "${BLUE}Checking MinIO...${NC}"
if curl -s --connect-timeout 2 "http://localhost:9000/minio/health/live" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MinIO is running on localhost:9000${NC}"
else
    echo -e "${YELLOW}⚠ MinIO is not running (optional)${NC}"
    echo -e "${YELLOW}  Start with: minio server /path/to/data --console-address :9001${NC}"
fi

# Create necessary directories
echo -e "${BLUE}Creating necessary directories...${NC}"
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/cache"
echo -e "${GREEN}✓ Directories created${NC}"

# Check if port 8081 is already in use
if lsof -Pi :8081 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}Error: Port 8081 is already in use${NC}"
    echo -e "${YELLOW}Kill the process with: lsof -ti:8081 | xargs kill -9${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}Starting MCP Service on http://localhost:8081${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${YELLOW}Environment: ${ENV}${NC}"
echo -e "${YELLOW}Log Level: ${LOG_LEVEL}${NC}"
echo -e "${YELLOW}Hot Reload: Enabled${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Change to project root and start the server
cd "$PROJECT_ROOT"

# Export PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT"

# Start uvicorn with hot reload (using venv python)
python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8081 \
    --reload \
    --reload-dir "$PROJECT_ROOT" \
    --log-level info \
    --env-file "$ENV_FILE"
