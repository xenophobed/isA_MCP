#!/bin/bash

# isA MCP Local Development Environment Starter
# 启动所有必要的服务：Neo4j, User Service, Event Sourcing Service, Smart MCP Server

set -e

PROJECT_NAME="isa_mcp"

echo "🚀 Starting local development environment..."
echo "============================================"

# Check if dev .env exists
if [[ ! -f "deployment/dev/.env" ]]; then
    echo "❌ deployment/dev/.env not found. Please configure your development environment variables."
    exit 1
fi

echo "📋 Environment: Local Development"
echo "🔧 Loading deployment/dev/.env"

# Create/activate uv virtual environment
if [[ ! -d ".venv" ]]; then
    echo "📦 Creating uv virtual environment..."
    uv venv
fi

echo "📦 Activating uv virtual environment..."
source .venv/bin/activate

echo "📦 Installing dependencies with uv..."
uv pip install -r deployment/dev/requirements.txt

echo "📦 Installing isA_Model independently..."
uv pip install -e /Users/xenodennis/Documents/Fun/isA_Model

# Set environment variables
export $(cat deployment/dev/.env | grep -v '^#' | xargs)

# Debug: Show loaded environment variables
echo "🔍 Environment variables loaded:"
echo "  DB_SCHEMA: $DB_SCHEMA"
echo "  SUPABASE_LOCAL_URL: $SUPABASE_LOCAL_URL"

# Set service URLs
export USER_SERVICE_URL="http://localhost:8100"
export EVENT_SERVICE_URL="http://localhost:8101"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"

# Create logs directory
mkdir -p logs

# 1. 启动 Neo4j (如果未运行)
echo "🗄️  检查 Neo4j 状态..."
if ! pgrep -f "neo4j" > /dev/null; then
    echo "启动 Neo4j..."
    if command -v neo4j &> /dev/null; then
        neo4j start &
        echo "Neo4j 启动中..."
        sleep 5
    else
        echo "❌ Neo4j 未找到，请先安装 Neo4j"
        echo "安装命令: brew install neo4j"
        exit 1
    fi
else
    echo "✅ Neo4j 已运行"
fi

# 2. 启动 User Service (端口 8100)
echo "👤 启动 User Service (端口 8100)..."
cd tools/services/user_service
python start_server.py --port 8100 &
USER_SERVICE_PID=$!
echo "User Service PID: $USER_SERVICE_PID"
cd ../../..

# 3. 启动 Event Sourcing Service (端口 8101)
echo "📝 启动 Event Sourcing Service (端口 8101)..."
cd tools/services/event_sourcing_service
python event_feedback_server.py --port 8101 &
EVENT_SERVICE_PID=$!
echo "Event Service PID: $EVENT_SERVICE_PID"
cd ../../..

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 4. 启动 Smart MCP Server
echo "🎯 Starting MCP server on port ${MCP_PORT:-8081}..."
source .venv/bin/activate && python smart_mcp_server.py &
MCP_PID=$!

# 保存 PID 文件用于停止服务
echo $USER_SERVICE_PID > logs/user_service.pid
echo $EVENT_SERVICE_PID > logs/event_service.pid
echo $MCP_PID > logs/mcp_server.pid

echo ""
echo "✅ Local development environment started!"
echo "========================================="
echo "📊 服务状态:"
echo "• Neo4j Browser:    http://localhost:7474"
echo "• User Service:     http://localhost:8100"
echo "• Event Service:    http://localhost:8101"
echo "• Smart MCP Server: http://localhost:${MCP_PORT:-8081}"
echo "🔍 Health Check: http://localhost:${MCP_PORT:-8081}/health"
echo ""
echo "📝 日志文件位置: logs/"
echo "🛑 停止所有服务: ./deployment/scripts/stop_dev.sh"
echo ""
echo "Press Ctrl+C to stop all services..."

# 等待中断信号
trap 'echo "🛑 Stopping local development environment..."; kill $USER_SERVICE_PID $EVENT_SERVICE_PID $MCP_PID 2>/dev/null; exit 0' SIGINT
wait $MCP_PID