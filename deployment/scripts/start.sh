#!/bin/bash

# isA MCP Environment Starter Script
# Usage: ./start.sh [local|test|production]

set -e

ENV=${1:-local}
PROJECT_NAME="isa_mcp"

show_help() {
    echo "isA MCP Environment Starter"
    echo ""
    echo "Usage: ./start.sh [ENVIRONMENT]"
    echo ""
    echo "Environments:"
    echo "  local      - Start local development environment (default)"
    echo "  test       - Start Docker testing environment"
    echo "  production - Deploy to Railway production"
    echo ""
    echo "Examples:"
    echo "  ./start.sh           # Start local development"
    echo "  ./start.sh local     # Start local development"
    echo "  ./start.sh test      # Start Docker testing"
    echo "  ./start.sh production # Deploy to Railway"
}

check_requirements() {
    echo "🔍 Checking requirements..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is required but not installed"
        exit 1
    fi
    
    # Check uv for local development
    if [[ "$ENV" == "local" ]] && ! command -v uv &> /dev/null; then
        echo "❌ uv is required for local development"
        echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    # Check Docker for test/production
    if [[ "$ENV" == "test" ]] && ! command -v docker &> /dev/null; then
        echo "❌ Docker is required for testing environment"
        exit 1
    fi
    
    # Check Railway CLI for production
    if [[ "$ENV" == "production" ]] && ! command -v railway &> /dev/null; then
        echo "❌ Railway CLI is required for production deployment"
        echo "Install with: npm install -g @railway/cli"
        exit 1
    fi
    
    echo "✅ Requirements check passed"
}

start_local() {
    echo "🚀 Starting local development environment..."
    echo "🔧 Delegating to start_dev.sh for complete service startup"
    
    # Check if start_dev.sh exists
    if [[ ! -f "deployment/scripts/start_dev.sh" ]]; then
        echo "❌ deployment/scripts/start_dev.sh not found."
        exit 1
    fi
    
    # Make script executable
    chmod +x deployment/scripts/start_dev.sh
    
    # Execute the development startup script
    exec ./deployment/scripts/start_dev.sh
}

start_test() {
    echo "🧪 Starting Docker testing environment..."
    
    # Check if .env.test exists
    if [[ ! -f "deployment/.env.test" ]]; then
        echo "❌ deployment/.env.test not found. Please configure your test environment variables."
        exit 1
    fi
    
    # Check if test requirements exist
    if [[ ! -f "deployment/.env.test.requirements.txt" ]]; then
        echo "❌ deployment/.env.test.requirements.txt not found."
        exit 1
    fi
    
    echo "📋 Environment: Docker Testing"
    echo "🔧 Loading deployment/.env.test"
    echo "📦 Using test-specific requirements"
    
    # Stop any existing test containers
    echo "🧹 Cleaning up existing test containers..."
    docker-compose -f deployment/test/docker-compose.test.yml down --remove-orphans 2>/dev/null || true
    
    # Build and start test environment
    echo "🔨 Building test containers..."
    docker-compose -f deployment/test/docker-compose.test.yml build
    
    echo "🚀 Starting test environment..."
    docker-compose -f deployment/test/docker-compose.test.yml up -d
    
    echo "⏳ Waiting for services to be healthy..."
    sleep 10
    
    # Check service health
    echo "🔍 Checking service health..."
    for service in isa_mcp_test isa_service_user_test isa_service_event_test; do
        if docker-compose -f docker-compose.test.yml ps "$service" | grep -q "healthy\|running"; then
            echo "✅ $service is running"
        else
            echo "❌ $service failed to start"
        fi
    done
    
    echo "✅ Test environment started!"
    echo "📊 MCP Server: http://localhost:8082"
    echo "👤 User Service: http://localhost:8102"
    echo "📅 Event Service: http://localhost:8103"
    echo ""
    echo "To view logs: docker-compose -f docker-compose.test.yml logs -f"
    echo "To stop: docker-compose -f docker-compose.test.yml down"
}

start_production() {
    echo "🚀 Deploying to Railway production environment..."
    
    # Check if logged into Railway
    if ! railway status &> /dev/null; then
        echo "❌ Not logged into Railway. Please run: railway login"
        exit 1
    fi
    
    echo "📋 Environment: Railway Production"
    
    # Check if railway.json exists
    if [[ ! -f "railway.json" ]]; then
        echo "❌ railway.json not found. Please configure your Railway deployment."
        exit 1
    fi
    
    # Check if production env template exists
    if [[ ! -f ".env.production.template" ]]; then
        echo "❌ .env.production.template not found. Please configure your production environment template."
        exit 1
    fi
    
    echo "🔧 Checking Railway project..."
    railway status
    
    echo "📦 Deploying services..."
    
    # Deploy main MCP service
    echo "🚀 Deploying main MCP service..."
    railway up --service isa-mcp
    
    # Deploy user service
    echo "👤 Deploying user service..."
    railway up --service isa-user-service
    
    # Deploy event service  
    echo "📅 Deploying event service..."
    railway up --service isa-event-service
    
    echo "✅ Production deployment completed!"
    echo "🌐 Check Railway dashboard for service URLs"
    echo "📊 Monitor with: railway logs"
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

echo "🎯 Starting isA MCP - Environment: $ENV"
echo "================================================"

check_requirements

case "$ENV" in
    local)
        start_local
        ;;
    test)
        start_test
        ;;
    production)
        start_production
        ;;
esac