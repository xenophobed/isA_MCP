#!/bin/bash

# User Service Development Startup Script
# 单独启动用户服务，自动检查并启动依赖服务

set -e

PROJECT_ROOT="$(pwd)"
USER_SERVICE_PORT=8100
USER_SERVICE_DIR="tools/services/user_service"

# Parse command line arguments
AUTO_START_DEPS=true
if [[ "$1" == "--port" ]]; then
    USER_SERVICE_PORT=$2
elif [[ "$1" == "--no-deps" ]]; then
    AUTO_START_DEPS=false
elif [[ "$1" == "--port" && "$3" == "--no-deps" ]]; then
    USER_SERVICE_PORT=$2
    AUTO_START_DEPS=false
fi

echo "👤 Starting User Service..."
echo "========================"

# Function to check if a service is running on a port
check_port() {
    local port=$1
    lsof -ti:$port > /dev/null 2>&1
}

# Function to check if a service is responding
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

# Function to start a service if not running
start_dependency() {
    local service_name=$1
    local port=$2
    local start_command=$3
    local health_check_url=$4
    
    if check_port $port; then
        echo "✅ $service_name is already running on port $port"
        return 0
    fi
    
    if [[ "$AUTO_START_DEPS" == "true" ]]; then
        echo "🚀 Starting $service_name..."
        eval $start_command &
        sleep 3
        
        if [[ -n "$health_check_url" ]]; then
            if check_service_health "$health_check_url" "$service_name"; then
                echo "✅ $service_name started successfully"
                return 0
            else
                echo "❌ Failed to start $service_name"
                return 1
            fi
        else
            echo "✅ $service_name started (no health check available)"
            return 0
        fi
    else
        echo "❌ $service_name is not running on port $port"
        echo "   Start it manually or run without --no-deps flag"
        return 1
    fi
}

# Kill existing User Service processes
echo "🧹 Cleaning up existing User Service..."
pkill -f "user_service.*server.py" 2>/dev/null || true
pkill -f "uvicorn.*server:app" 2>/dev/null || true
lsof -ti:$USER_SERVICE_PORT | xargs kill 2>/dev/null || true
sleep 2

# Check and start dependencies
echo "🔧 Checking dependencies..."
echo "=========================="

# Check Supabase (port 54321)
if ! start_dependency "Supabase" 54321 "supabase start" "http://localhost:54321/rest/v1/"; then
    echo "⚠️  Supabase not available. Ensure DATABASE_URL is configured in .env"
fi

# Check Redis (port 6379)
if ! start_dependency "Redis" 6379 "redis-server --daemonize yes" ""; then
    echo "⚠️  Redis not available. Session management may be affected"
fi

# Check MinIO (port 9000)
if ! start_dependency "MinIO" 9000 "minio server ~/minio-data --console-address :9001" "http://localhost:9000/minio/health/live"; then
    echo "⚠️  MinIO not available. File uploads may not work"
fi

# Check if .env exists
if [[ ! -f "deployment/dev/.env" ]]; then
    echo "❌ deployment/dev/.env not found"
    exit 1
fi

# Check if user service directory exists
if [[ ! -d "$USER_SERVICE_DIR" ]]; then
    echo "❌ $USER_SERVICE_DIR not found"
    exit 1
fi

# Check if server.py exists
if [[ ! -f "$USER_SERVICE_DIR/server.py" ]]; then
    echo "❌ $USER_SERVICE_DIR/server.py not found"
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

# Set port for user service
export PORT=$USER_SERVICE_PORT

# Create logs directory
mkdir -p logs

# Start User Service with real-time logs
echo "👤 Starting User Service on port $USER_SERVICE_PORT..."
echo "📝 Logs will be shown in real-time and also saved to logs/user_service.log"
echo ""

cd $USER_SERVICE_DIR
# Use tee to show logs in terminal AND save to file
PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python server.py 2>&1 | tee "$PROJECT_ROOT/logs/user_service.log" &
USER_SERVICE_PID=${PIPESTATUS[0]}
echo $USER_SERVICE_PID > "$PROJECT_ROOT/logs/user_service.pid"

# Go back to project root
cd "$PROJECT_ROOT"

# Wait and check health
sleep 8
if curl -s --connect-timeout 5 --max-time 10 "http://localhost:$USER_SERVICE_PORT/health" > /dev/null; then
    echo ""
    echo "✅ User Service started successfully!"
    echo "🌐 Server: http://localhost:$USER_SERVICE_PORT"
    echo "📚 API Docs: http://localhost:$USER_SERVICE_PORT/docs"
    echo "🔍 Redoc: http://localhost:$USER_SERVICE_PORT/redoc"
    echo "📝 Logs: real-time + logs/user_service.log"
    echo "🛑 Stop: Ctrl+C"
    echo ""
    echo "💡 Usage:"
    echo "  Normal start:     ./deployment/scripts/start_user_dev.sh"
    echo "  Custom port:      ./deployment/scripts/start_user_dev.sh --port 8200"
    echo "  Skip dependencies: ./deployment/scripts/start_user_dev.sh --no-deps"
    echo ""
    
    trap 'echo "🛑 Stopping User Service..."; pkill -f "user_service.*server.py"; exit 0' SIGINT
    wait
else
    echo "❌ User Service failed to start. Check logs/user_service.log"
    tail -10 logs/user_service.log
    exit 1
fi