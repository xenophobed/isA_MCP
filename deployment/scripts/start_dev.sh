#!/bin/bash

# isA MCP Local Development Environment Starter
# 启动所有必要的服务：Neo4j, User Service, Event Sourcing Service, Smart MCP Server

set -e

PROJECT_NAME="isa_mcp"
PROJECT_ROOT="$(pwd)"

# Parse command line arguments
SKIP_CLEANUP=false
if [[ "$1" == "--skip-cleanup" ]]; then
    SKIP_CLEANUP=true
    echo "⚡ SKIP CLEANUP MODE: Will not stop existing services"
fi

echo "🚀 Starting local development environment..."
echo "============================================"

# Function to kill processes on specific ports
kill_port_processes() {
    local port=$1
    local service_name=$2
    echo "🔍 Checking port $port for $service_name..."
    
    # Find processes using the port
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    
    if [[ -n "$pids" ]]; then
        echo "🛑 Stopping existing $service_name processes on port $port..."
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 2
        
        # Force kill if still running
        local remaining_pids=$(lsof -ti:$port 2>/dev/null || true)
        if [[ -n "$remaining_pids" ]]; then
            echo "🔥 Force killing remaining $service_name processes..."
            echo "$remaining_pids" | xargs kill -KILL 2>/dev/null || true
        fi
        
        echo "✅ Port $port cleared"
    else
        echo "✅ Port $port is free"
    fi
}

# Function to kill processes by name
kill_named_processes() {
    local process_name=$1
    local service_name=$2
    echo "🔍 Checking for $service_name processes..."
    
    local pids=$(pgrep -f "$process_name" 2>/dev/null || true)
    
    if [[ -n "$pids" ]]; then
        echo "🛑 Stopping existing $service_name processes..."
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 2
        
        # Force kill if still running
        local remaining_pids=$(pgrep -f "$process_name" 2>/dev/null || true)
        if [[ -n "$remaining_pids" ]]; then
            echo "🔥 Force killing remaining $service_name processes..."
            echo "$remaining_pids" | xargs kill -KILL 2>/dev/null || true
        fi
        
        echo "✅ $service_name processes cleared"
    else
        echo "✅ No $service_name processes running"
    fi
}

# Always stop existing services (unless --skip-cleanup is used)
if [[ "$SKIP_CLEANUP" == false ]]; then
    echo "🧹 Cleaning up existing services..."
    echo "=================================="
    
    # Kill services on specific ports
    kill_port_processes 8100 "User Service"
    kill_port_processes 8101 "Event Service" 
    kill_port_processes 8081 "MCP Server"
    
    # Also kill by process name to catch any stragglers
    kill_named_processes "start_server.py" "User Service"
    kill_named_processes "event_server.py" "Event Service"
    kill_named_processes "smart_mcp_server.py" "MCP Server"
    
    # Clean up PID files
    rm -f logs/user_service.pid logs/event_service.pid logs/mcp_server.pid logs/stripe_cli.pid 2>/dev/null || true
    
    echo "✅ All existing services cleaned up"
    echo "⏳ Waiting 3 seconds before starting services..."
    sleep 3
    echo ""
fi

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
export $(cat deployment/dev/.env | grep -v '^#' | grep -v '^$' | xargs)

# Load User Service specific environment variables
if [[ -f "deployment/dev/.env.user_service" ]]; then
    echo "🔧 Loading User Service environment variables..."
    export $(cat deployment/dev/.env.user_service | grep -v '^#' | xargs)
fi

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

# Function to check if service is responding
check_service_health() {
    local url=$1
    local service_name=$2
    local max_attempts=10
    local attempt=1
    
    echo "🔍 Checking $service_name health at $url..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s --connect-timeout 2 --max-time 5 "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is responding"
            return 0
        fi
        echo "⏳ Attempt $attempt/$max_attempts - waiting for $service_name..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ $service_name failed to start or is not responding"
    return 1
}

# 2. 启动 User Service (端口 8100)
echo "👤 启动 User Service (端口 8100)..."
cd tools/services/user_service
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python start_server.py --dev --port ${USER_SERVICE_PORT:-8100} > ../../../logs/user_service.log 2>&1 &
USER_SERVICE_PID=$!
echo "User Service PID: $USER_SERVICE_PID"
cd ../../..

# Wait and check User Service health
sleep 3
if ! check_service_health "http://localhost:8100/health" "User Service"; then
    echo "❌ User Service startup failed. Check logs/user_service.log"
    exit 1
fi

# 3. 启动 Event Sourcing Service (端口 8101)
echo "📝 启动 Event Sourcing Service (端口 8101)..."
cd tools/services/event_service
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python event_server.py --port 8101 > ../../../logs/event_service.log 2>&1 &
EVENT_SERVICE_PID=$!
echo "Event Service PID: $EVENT_SERVICE_PID"
cd ../../..

# Wait and check Event Service health
sleep 3
if ! check_service_health "http://localhost:8101/health" "Event Service"; then
    echo "❌ Event Service startup failed. Check logs/event_service.log"
    exit 1
fi

# 4. 启动 Stripe CLI Webhook 监听 (可选)
STRIPE_CLI_PID=""
if command -v stripe &> /dev/null; then
    echo "💳 启动 Stripe CLI Webhook 监听..."
    echo "转发到后端服务: localhost:8100/api/v1/webhooks/stripe"
    stripe listen --forward-to localhost:8100/api/v1/webhooks/stripe > logs/stripe_cli.log 2>&1 &
    STRIPE_CLI_PID=$!
    echo "Stripe CLI PID: $STRIPE_CLI_PID"
else
    echo "⚠️  Stripe CLI 未安装，跳过 webhook 监听"
    echo "如需安装: brew install stripe/stripe-cli/stripe"
fi

# 5. 启动 Smart MCP Server
echo "🎯 Starting MCP server on port ${MCP_PORT:-8081}..."
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python smart_mcp_server.py > logs/mcp_server.log 2>&1 &
MCP_PID=$!
echo "MCP Server PID: $MCP_PID"

# Wait and check MCP Server health
sleep 5
if ! check_service_health "http://localhost:${MCP_PORT:-8081}/health" "MCP Server"; then
    echo "❌ MCP Server startup failed. Check logs/mcp_server.log"
    exit 1
fi

# 保存 PID 文件用于停止服务
echo $USER_SERVICE_PID > logs/user_service.pid
echo $EVENT_SERVICE_PID > logs/event_service.pid
echo $MCP_PID > logs/mcp_server.pid
if [[ -n "$STRIPE_CLI_PID" ]]; then
    echo $STRIPE_CLI_PID > logs/stripe_cli.pid
fi

echo ""
echo "✅ Local development environment started!"
echo "========================================="
echo "📊 服务状态:"
echo "• Neo4j Browser:    http://localhost:7474"
echo "• User Service:     http://localhost:8100 (✅ Health check passed)"
echo "• Event Service:    http://localhost:8101 (✅ Health check passed)"
echo "• Smart MCP Server: http://localhost:${MCP_PORT:-8081} (✅ Health check passed)"
if [[ -n "$STRIPE_CLI_PID" ]]; then
    echo "• Stripe CLI:       监听中 (转发到 localhost:8100)"
fi
echo ""
echo "🔍 Health Checks:"
echo "• User Service:     http://localhost:8100/health"
echo "• Event Service:    http://localhost:8101/health"
echo "• MCP Server:       http://localhost:${MCP_PORT:-8081}/health"
echo ""
echo "📝 日志文件位置: logs/"
echo "🛑 停止所有服务: ./deployment/scripts/stop_dev.sh"
echo ""
echo "📖 启动选项:"
echo "• 普通启动(自动重启): ./deployment/scripts/start_dev.sh"
echo "• 跳过清理启动:      ./deployment/scripts/start_dev.sh --skip-cleanup"
echo ""
echo "Press Ctrl+C to stop all services..."

# 等待中断信号
if [[ -n "$STRIPE_CLI_PID" ]]; then
    trap 'echo "🛑 Stopping local development environment..."; kill $USER_SERVICE_PID $EVENT_SERVICE_PID $MCP_PID $STRIPE_CLI_PID 2>/dev/null; exit 0' SIGINT
else
    trap 'echo "🛑 Stopping local development environment..."; kill $USER_SERVICE_PID $EVENT_SERVICE_PID $MCP_PID 2>/dev/null; exit 0' SIGINT
fi
wait $MCP_PID