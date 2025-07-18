#!/bin/bash

# isA MCP Local Development Environment Stopper
# 停止所有本地开发服务

set -e

echo "🛑 Stopping local development environment..."
echo "============================================"

# Stop services using PID files
if [[ -f "logs/user_service.pid" ]]; then
    USER_SERVICE_PID=$(cat logs/user_service.pid)
    echo "👤 Stopping User Service (PID: $USER_SERVICE_PID)..."
    kill $USER_SERVICE_PID 2>/dev/null || echo "  ⚠️  User Service already stopped"
    rm -f logs/user_service.pid
fi

if [[ -f "logs/event_service.pid" ]]; then
    EVENT_SERVICE_PID=$(cat logs/event_service.pid)
    echo "📝 Stopping Event Service (PID: $EVENT_SERVICE_PID)..."
    kill $EVENT_SERVICE_PID 2>/dev/null || echo "  ⚠️  Event Service already stopped"
    rm -f logs/event_service.pid
fi

if [[ -f "logs/mcp_server.pid" ]]; then
    MCP_PID=$(cat logs/mcp_server.pid)
    echo "🧠 Stopping Smart MCP Server (PID: $MCP_PID)..."
    kill $MCP_PID 2>/dev/null || echo "  ⚠️  MCP Server already stopped"
    rm -f logs/mcp_server.pid
fi

if [[ -f "logs/stripe_cli.pid" ]]; then
    STRIPE_CLI_PID=$(cat logs/stripe_cli.pid)
    echo "💳 Stopping Stripe CLI (PID: $STRIPE_CLI_PID)..."
    kill $STRIPE_CLI_PID 2>/dev/null || echo "  ⚠️  Stripe CLI already stopped"
    rm -f logs/stripe_cli.pid
fi

# Stop Neo4j if running
echo "🗄️  Stopping Neo4j..."
if pgrep -f "neo4j" > /dev/null; then
    if command -v neo4j &> /dev/null; then
        neo4j stop
        echo "✅ Neo4j stopped"
    else
        echo "⚠️  Neo4j command not found, attempting to kill process..."
        pkill -f "neo4j" 2>/dev/null || echo "  ⚠️  Neo4j already stopped"
    fi
else
    echo "✅ Neo4j was not running"
fi

# Kill any remaining Python processes related to our services
echo "🧹 Cleaning up remaining processes..."
pkill -f "start_server.py" 2>/dev/null || true
pkill -f "event_feedback_server.py" 2>/dev/null || true
pkill -f "smart_mcp_server.py" 2>/dev/null || true
pkill -f "stripe listen" 2>/dev/null || true

echo ""
echo "✅ All local development services stopped!"
echo "=========================================="