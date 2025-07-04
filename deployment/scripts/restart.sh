#!/bin/bash

# isA MCP Environment Restart Script
# Usage: ./restart.sh [local|test|production]

set -e

ENV=${1:-local}

show_help() {
    echo "isA MCP Environment Restart Script"
    echo ""
    echo "Usage: ./restart.sh [ENVIRONMENT]"
    echo ""
    echo "Environments:"
    echo "  local      - Restart local development environment (default)"
    echo "  test       - Restart Docker testing environment"
    echo "  production - Restart Railway production services"
    echo ""
    echo "Examples:"
    echo "  ./restart.sh           # Restart local development"
    echo "  ./restart.sh local     # Restart local development"
    echo "  ./restart.sh test      # Restart Docker testing"
    echo "  ./restart.sh production # Restart Railway services"
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

echo "🔄 Restarting isA MCP - Environment: $ENV"
echo "================================================"

# Stop the environment
echo "🛑 Stopping $ENV environment..."
./stop.sh $ENV

# Wait a moment for clean shutdown
echo "⏳ Waiting for clean shutdown..."
sleep 2

# Start the environment
echo "🚀 Starting $ENV environment..."
./start.sh $ENV