#!/bin/bash

# isA MCP Environment Stopper Script
# Usage: ./stop.sh [local|test|production]

set -e

ENV=${1:-local}

show_help() {
    echo "isA MCP Environment Stopper"
    echo ""
    echo "Usage: ./stop.sh [ENVIRONMENT]"
    echo ""
    echo "Environments:"
    echo "  local      - Stop local development processes (default)"
    echo "  test       - Stop Docker testing environment"
    echo "  production - Stop Railway production services"
    echo ""
    echo "Examples:"
    echo "  ./stop.sh           # Stop local development"
    echo "  ./stop.sh local     # Stop local development"
    echo "  ./stop.sh test      # Stop Docker testing"
    echo "  ./stop.sh production # Stop Railway services"
}

stop_local() {
    echo "🛑 Stopping local development environment..."
    
    # Kill Python processes running MCP server
    echo "🔍 Finding MCP server processes..."
    
    # Find and kill MCP server processes
    pkill -f "smart_mcp_server.py" 2>/dev/null || echo "No MCP server processes found"
    pkill -f "uvicorn.*smart_mcp_server" 2>/dev/null || echo "No uvicorn processes found"
    
    # Kill any other related processes
    pkill -f "python.*mcp" 2>/dev/null || true
    
    echo "✅ Local environment stopped!"
}

stop_test() {
    echo "🛑 Stopping Docker testing environment..."
    
    # Stop and remove test containers
    if [[ -f "docker-compose.test.yml" ]]; then
        echo "🐳 Stopping test containers..."
        docker-compose -f docker-compose.test.yml down --remove-orphans
        
        echo "🧹 Cleaning up test networks..."
        docker network rm isa_test_network 2>/dev/null || true
        
        echo "🗑️  Removing test volumes (optional)..."
        read -p "Remove test database volumes? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker volume rm $(docker volume ls -q | grep test) 2>/dev/null || true
            echo "✅ Test volumes removed"
        fi
    else
        echo "❌ docker-compose.test.yml not found"
    fi
    
    echo "✅ Test environment stopped!"
}

stop_production() {
    echo "🛑 Stopping Railway production services..."
    
    # Check if logged into Railway
    if ! railway status &> /dev/null; then
        echo "❌ Not logged into Railway. Cannot stop services."
        exit 1
    fi
    
    echo "⚠️  WARNING: This will stop your production services!"
    read -p "Are you sure you want to stop production services? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚂 Stopping Railway services..."
        
        # Note: Railway doesn't have a direct "stop" command
        # Services are typically scaled down or removed
        echo "🔧 To stop Railway services, you need to:"
        echo "   1. Scale down services: railway scale --replicas 0"
        echo "   2. Or remove services from Railway dashboard"
        echo "   3. Or delete the entire project: railway project delete"
        
        echo "📊 Current service status:"
        railway status
        
        echo "💡 Use Railway dashboard or CLI to manage production services"
    else
        echo "❌ Production stop cancelled"
    fi
}

# Main script logic
case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
    local|"")
        ENV="local"
        ;;
    test)
        ENV="test"
        ;;
    production)
        ENV="production"
        ;;
    *)
        echo "❌ Unknown environment: $1"
        show_help
        exit 1
        ;;
esac

echo "🛑 Stopping isA MCP - Environment: $ENV"
echo "================================================"

case "$ENV" in
    local)
        stop_local
        ;;
    test)
        stop_test
        ;;
    production)
        stop_production
        ;;
esac