#!/bin/bash

# MCP Server Development Startup Script
# 只启动MCP服务器，不依赖其他服务

set -e

PROJECT_ROOT="$(pwd)"
MCP_PORT=8081

# Parse command line arguments
if [[ "$1" == "--port" ]]; then
    MCP_PORT=$2
fi

echo "🎯 Starting MCP server..."
echo "========================"

# Kill existing MCP processes
echo "🧹 Cleaning up existing MCP server..."
pkill -f "smart_mcp_server.py" 2>/dev/null || true
lsof -ti:$MCP_PORT | xargs kill 2>/dev/null || true
sleep 2

# Check if .env exists
if [[ ! -f "deployment/dev/.env" ]]; then
    echo "❌ deployment/dev/.env not found"
    exit 1
fi

# Setup environment
echo "🔧 Setting up environment..."
if [[ ! -d ".venv" ]]; then
    uv venv
fi

source .venv/bin/activate
uv pip install -r deployment/dev/requirements.txt
uv pip install -e /Users/xenodennis/Documents/Fun/isA_Model

# Load environment variables
export $(cat deployment/dev/.env | grep -v '^#' | grep -v '^$' | xargs)
if [[ -f "deployment/dev/.env.user_service" ]]; then
    export $(cat deployment/dev/.env.user_service | grep -v '^#' | xargs)
fi

# Create logs directory
mkdir -p logs

# Start MCP Server with real-time logs
echo "🎯 Starting MCP server on port $MCP_PORT..."
echo "📝 Logs will be shown in real-time and also saved to logs/mcp_server.log"
echo ""

# Use tee to show logs in terminal AND save to file
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python smart_mcp_server.py --port $MCP_PORT 2>&1 | tee logs/mcp_server.log &
MCP_PID=${PIPESTATUS[0]}
echo $MCP_PID > logs/mcp_server.pid

# Wait and check health
sleep 8
if curl -s --connect-timeout 5 --max-time 10 "http://localhost:$MCP_PORT/health" > /dev/null; then
    echo ""
    echo "✅ MCP Server started successfully!"
    echo "🌐 Server: http://localhost:$MCP_PORT"
    echo "🎯 MCP endpoint: http://localhost:$MCP_PORT/mcp/"
    echo "📝 Logs: real-time + logs/mcp_server.log"
    echo "🛑 Stop: Ctrl+C"
    echo ""
    
    trap 'echo "🛑 Stopping MCP Server..."; pkill -f "smart_mcp_server.py"; exit 0' SIGINT
    wait
else
    echo "❌ MCP Server failed to start. Check logs/mcp_server.log"
    tail -10 logs/mcp_server.log
    exit 1
fi