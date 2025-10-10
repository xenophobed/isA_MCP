#!/bin/bash

# Smart MCP Service Startup Script
# Multi-environment support: development, test, staging, production
# Infrastructure checks: Docker, Supabase, Neo4j, Redis, Consul

set -e

# ============================================
# Configuration and Defaults
# ============================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MCP_PORT=8081
VERBOSE_LOGS=false
REGISTER_CONSUL=false
SKIP_INFRA_CHECKS=false
ENV="development"  # Default environment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# Parse Command Line Arguments
# ============================================

show_help() {
    cat << EOF
Usage: $0 [OPTIONS] [ENVIRONMENT] [ACTION]

Smart MCP Service Management Script with Multi-Environment Support

NEW FORMAT (Recommended):
    $0 -e <env> <action>              # -e flag with environment and action
    $0 -e dev start                   # Start development environment
    $0 -e test stop                   # Stop test environment
    $0 -e production restart          # Restart production environment

LEGACY FORMAT (Still supported):
    $0 [dev|test|staging|production] [OPTIONS]

ENVIRONMENTS:
    dev, development       Local development with native Supabase
    test                   Local Docker-based testing environment
    staging                Staging environment (Docker/Remote)
    production, prod       Production environment (Docker/Remote)

ACTIONS:
    start                  Start the MCP service (default)
    stop                   Stop the MCP service
    status                 Check service status
    restart                Restart the MCP service

OPTIONS:
    -e, --env ENV          Specify environment (dev|test|staging|production)
    --port PORT            MCP server port (default: 8081)
    --verbose, -v          Show detailed logs
    --consul               Register with Consul for service discovery
    --skip-checks          Skip infrastructure health checks
    --help, -h             Show this help message

EXAMPLES:
    # New format
    $0 -e dev start                      # Start development
    $0 -e test start --port 8082         # Start test on port 8082
    $0 -e production start --consul      # Start production with Consul
    $0 -e dev stop                       # Stop development

    # Legacy format (still works)
    $0 dev                               # Start development
    $0 test --port 8082                  # Start test on port 8082
    $0 production --consul -v            # Start production with Consul

INFRASTRUCTURE DEPENDENCIES:
    - Docker (required for test/staging/production)
    - Supabase (required for dev)
    - Neo4j (optional - graph analytics)
    - Redis (optional - caching)
    - Consul (optional - service discovery)

EOF
}

# Parse arguments - support both new (-e env action) and legacy (env) formats
ACTION="start"  # Default action

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            # New format: -e <env>
            case $2 in
                dev|development)
                    ENV="development"
                    ;;
                test)
                    ENV="test"
                    ;;
                staging)
                    ENV="staging"
                    ;;
                prod|production)
                    ENV="production"
                    ;;
                *)
                    echo -e "${RED}❌ Invalid environment: $2${NC}"
                    echo "Valid environments: dev, test, staging, production"
                    exit 1
                    ;;
            esac
            shift 2
            ;;
        start|stop|status|restart)
            # Action specified
            ACTION=$1
            shift
            ;;
        --port)
            MCP_PORT=$2
            shift 2
            ;;
        --verbose|-v)
            VERBOSE_LOGS=true
            shift
            ;;
        --consul)
            REGISTER_CONSUL=true
            shift
            ;;
        --skip-checks)
            SKIP_INFRA_CHECKS=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        dev|development)
            # Legacy format: positional environment
            ENV="development"
            shift
            ;;
        test)
            ENV="test"
            shift
            ;;
        staging)
            ENV="staging"
            shift
            ;;
        prod|production)
            ENV="production"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================
# Validate Environment
# ============================================

if [[ ! "$ENV" =~ ^(development|test|staging|production)$ ]]; then
    echo -e "${RED}❌ Invalid environment: $ENV${NC}"
    echo "Valid environments: development, test, staging, production"
    exit 1
fi

# ============================================
# Environment-Specific Configuration
# ============================================

DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"
ENV_DIR=""
ENV_FILE=""
REQUIREMENTS_FILE=""
DOCKER_COMPOSE_FILE=""
USE_DOCKER=false

case $ENV in
    development)
        ENV_DIR="$DEPLOYMENT_DIR/dev"
        ENV_FILE="$ENV_DIR/.env"
        REQUIREMENTS_FILE="$ENV_DIR/requirements.txt"
        USE_DOCKER=false
        ;;
    test)
        ENV_DIR="$DEPLOYMENT_DIR/test"
        ENV_FILE="$ENV_DIR/.env.test"
        REQUIREMENTS_FILE="$ENV_DIR/requirements.test.txt"
        DOCKER_COMPOSE_FILE="$ENV_DIR/docker-compose.test.yml"
        USE_DOCKER=true
        ;;
    staging)
        ENV_DIR="$DEPLOYMENT_DIR/staging"
        ENV_FILE="$ENV_DIR/.env.staging"
        REQUIREMENTS_FILE="$ENV_DIR/requirements.staging.txt"
        DOCKER_COMPOSE_FILE="$ENV_DIR/docker-compose.staging.yml"
        USE_DOCKER=true
        ;;
    production)
        ENV_DIR="$DEPLOYMENT_DIR/production"
        ENV_FILE="$ENV_DIR/.env.production"
        REQUIREMENTS_FILE="$ENV_DIR/requirements.production.txt"
        DOCKER_COMPOSE_FILE="$ENV_DIR/docker-compose.yml"
        USE_DOCKER=true
        ;;
esac

# ============================================
# Display Startup Banner
# ============================================

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 Smart MCP Service Startup${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Environment:        ${GREEN}$ENV${NC}"
echo -e "Port:               ${GREEN}$MCP_PORT${NC}"
echo -e "Project Root:       ${GREEN}$PROJECT_ROOT${NC}"
echo -e "Deployment Mode:    ${GREEN}$([ "$USE_DOCKER" = true ] && echo 'Docker' || echo 'Native')${NC}"
echo -e "Verbose Logs:       ${GREEN}$([ "$VERBOSE_LOGS" = true ] && echo 'Yes' || echo 'No')${NC}"
echo -e "Consul Registration: ${GREEN}$([ "$REGISTER_CONSUL" = true ] && echo 'Yes' || echo 'No')${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ============================================
# Infrastructure Health Checks
# ============================================

check_docker() {
    echo "🐳 Checking Docker..."
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running${NC}"

        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "   Starting Docker Desktop..."
            open -a Docker
            echo "   Waiting for Docker to start (up to 60 seconds)..."

            for i in {1..60}; do
                if docker info >/dev/null 2>&1; then
                    echo -e "${GREEN}✅ Docker daemon connected${NC}"
                    sleep 2
                    return 0
                fi
                sleep 1
            done

            echo -e "${RED}❌ Docker failed to start within 60 seconds${NC}"
            echo "   Please start Docker Desktop manually and try again"
            return 1
        else
            echo -e "${RED}   Please start Docker manually${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✅ Docker is running${NC}"
        return 0
    fi
}

check_supabase() {
    local supabase_dir="$PROJECT_ROOT/resources/dbs/supabase/dev"

    echo "🗄️  Checking Supabase..."

    if [ ! -d "$supabase_dir" ]; then
        echo -e "${YELLOW}⚠️  Supabase directory not found at $supabase_dir${NC}"
        return 1
    fi

    cd "$supabase_dir"

    # Check if Supabase is running
    SUPABASE_STATUS=$(supabase status 2>&1)

    if echo "$SUPABASE_STATUS" | grep -q "is not ready\|container is not\|is already running"; then
        echo -e "${YELLOW}⚠️  Supabase is in an inconsistent state, restarting...${NC}"
        supabase stop >/dev/null 2>&1
        sleep 3
        echo "   Starting fresh Supabase instance..."
        supabase start

        # Wait for Supabase to be ready
        for i in {1..30}; do
            if supabase status 2>&1 | grep -q "supabase local development setup is running"; then
                echo -e "${GREEN}✅ Supabase started successfully${NC}"
                cd "$PROJECT_ROOT"
                return 0
            fi
            sleep 2
        done

        echo -e "${YELLOW}⚠️  Supabase may not have started properly${NC}"
        cd "$PROJECT_ROOT"
        return 1

    elif ! supabase status >/dev/null 2>&1; then
        echo "🚀 Starting Supabase..."
        supabase start

        # Wait for Supabase to be ready
        for i in {1..30}; do
            if supabase status 2>&1 | grep -q "supabase local development setup is running"; then
                echo -e "${GREEN}✅ Supabase started successfully${NC}"
                cd "$PROJECT_ROOT"
                return 0
            fi
            sleep 2
        done

        echo -e "${YELLOW}⚠️  Supabase may not have started properly${NC}"
        cd "$PROJECT_ROOT"
        return 1
    else
        echo -e "${GREEN}✅ Supabase is already running${NC}"
        cd "$PROJECT_ROOT"
        return 0
    fi
}

check_neo4j() {
    echo "🔗 Checking Neo4j..."

    local neo4j_uri="${NEO4J_URI:-bolt://localhost:7687}"
    local neo4j_host=$(echo "$neo4j_uri" | sed -E 's#.*://([^:]+).*#\1#')

    # Neo4j browser usually runs on port 7474
    if curl -sf --connect-timeout 2 "http://${neo4j_host}:7474" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Neo4j is running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Neo4j not available (optional - graph analytics disabled)${NC}"
        return 1
    fi
}

check_redis() {
    echo "📦 Checking Redis..."

    local redis_host="${REDIS_HOST:-localhost}"
    local redis_port="${REDIS_PORT:-6379}"

    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -h "$redis_host" -p "$redis_port" ping >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis is running${NC}"
            return 0
        fi
    fi

    echo -e "${YELLOW}⚠️  Redis not available (optional - caching disabled)${NC}"
    return 1
}

check_consul() {
    echo "🔍 Checking Consul..."

    local consul_host="${CONSUL_HOST:-localhost}"
    local consul_port="${CONSUL_PORT:-8500}"

    if curl -sf --connect-timeout 2 "http://${consul_host}:${consul_port}/v1/status/leader" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Consul is running at ${consul_host}:${consul_port}${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Consul not available (service discovery disabled)${NC}"
        return 1
    fi
}

verify_consul_registration() {
    local service_name="${1:-mcp}"
    local consul_host="${CONSUL_HOST:-localhost}"
    local consul_port="${CONSUL_PORT:-8500}"
    local service_host="${SERVICE_HOST:-localhost}"
    local service_id="${service_name}-${service_host}-${MCP_PORT}"

    echo ""
    echo "🔍 Verifying Consul service registration..."
    echo "   Service ID: $service_id"
    echo "   Consul: http://${consul_host}:${consul_port}"

    # Check if service is registered
    local max_attempts=10
    for i in $(seq 1 $max_attempts); do
        # Query Consul for the service
        local response=$(curl -sf "http://${consul_host}:${consul_port}/v1/agent/services" 2>/dev/null)

        if echo "$response" | grep -q "\"$service_id\""; then
            echo -e "${GREEN}✅ Service successfully registered with Consul${NC}"

            # Get service details
            local service_info=$(echo "$response" | grep -A 10 "\"$service_id\"" | head -15)
            echo "   Service details:"
            echo "$response" | python3 -m json.tool 2>/dev/null | grep -A 15 "\"$service_id\"" | head -20 || echo "   (registered)"

            # Check service health
            local health_response=$(curl -sf "http://${consul_host}:${consul_port}/v1/health/service/${service_name}" 2>/dev/null)
            if echo "$health_response" | grep -q "\"Status\":\"passing\""; then
                echo -e "${GREEN}✅ Service health check: passing${NC}"
            else
                echo -e "${YELLOW}⚠️  Service health check: pending${NC}"
            fi

            return 0
        fi

        if [ $i -lt $max_attempts ]; then
            echo "   Attempt $i/$max_attempts: Service not yet registered, waiting..."
            sleep 2
        fi
    done

    echo -e "${RED}❌ Service registration verification failed${NC}"
    echo "   Service ID '$service_id' not found in Consul"
    return 1
}

run_infrastructure_checks() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}🔍 Infrastructure Health Checks${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    local checks_passed=0
    local checks_failed=0

    # Docker check (required for non-development environments)
    if [[ "$USE_DOCKER" = true ]]; then
        if check_docker; then
            ((checks_passed++))
        else
            ((checks_failed++))
            echo -e "${RED}❌ Docker is required for $ENV environment${NC}"
            return 1
        fi
    fi

    # Supabase check (required for development)
    if [[ "$ENV" = "development" ]]; then
        if check_supabase; then
            ((checks_passed++))
        else
            ((checks_failed++))
            echo -e "${YELLOW}⚠️  Supabase check failed, continuing anyway...${NC}"
        fi
    fi

    # Optional service checks
    if [[ -n "${NEO4J_URI:-}" ]]; then
        check_neo4j && ((checks_passed++)) || true
    fi

    if [[ -n "${REDIS_URL:-}" ]] || [[ -n "${REDIS_HOST:-}" ]]; then
        check_redis && ((checks_passed++)) || true
    fi

    # Check Consul if registration is requested
    if [[ "$REGISTER_CONSUL" = true ]]; then
        if check_consul; then
            ((checks_passed++))
        else
            echo -e "${RED}❌ Consul is required when --consul flag is used${NC}"
            echo "   Please start Consul first:"
            echo "   brew install consul"
            echo "   consul agent -dev"
            return 1
        fi
    elif [[ -n "${CONSUL_HOST:-}" ]]; then
        check_consul && ((checks_passed++)) || true
    fi

    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Checks Passed: $checks_passed${NC}"
    if [[ $checks_failed -gt 0 ]]; then
        echo -e "${RED}❌ Checks Failed: $checks_failed${NC}"
    fi
    echo -e "${BLUE}========================================${NC}"
    echo ""

    return 0
}

# ============================================
# Environment Setup
# ============================================

setup_environment() {
    echo ""
    echo "🔧 Setting up environment..."

    # Check if .env file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        echo -e "${RED}❌ Environment file not found: $ENV_FILE${NC}"
        echo "   Please create the environment file first"
        exit 1
    fi

    echo -e "${GREEN}✅ Environment file found: $ENV_FILE${NC}"

    # Check if requirements file exists (for native execution)
    if [[ "$USE_DOCKER" = false ]] && [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        echo -e "${RED}❌ Requirements file not found: $REQUIREMENTS_FILE${NC}"
        echo "   Please create the requirements file first"
        exit 1
    fi

    # For native execution (development)
    if [[ "$USE_DOCKER" = false ]]; then
        # Setup Python virtual environment
        if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
            echo "   Creating Python virtual environment..."
            cd "$PROJECT_ROOT"
            uv venv
        fi

        echo "   Activating virtual environment..."
        source "$PROJECT_ROOT/.venv/bin/activate"

        echo "   Installing dependencies..."
        uv pip install -q -r "$REQUIREMENTS_FILE"

        # Install isA_Model with cloud extras (reduced package size)
        if [[ -d "/Users/xenodennis/Documents/Fun/isA_Model" ]]; then
            echo "   Installing ISA Model (cloud mode)..."
            uv pip install -q -e "/Users/xenodennis/Documents/Fun/isA_Model[cloud]"
        fi

        # Load environment variables (filter out comments and inline comments)
        set -a  # Auto-export all variables
        source <(cat "$ENV_FILE" | grep -v '^#' | grep -v '^$' | sed 's/#.*//' | sed '/^$/d')
        set +a

        # Load additional env files if they exist
        if [[ -f "$ENV_DIR/.env.user_service" ]]; then
            set -a
            source <(cat "$ENV_DIR/.env.user_service" | grep -v '^#' | grep -v '^$' | sed 's/#.*//' | sed '/^$/d')
            set +a
        fi

        # Set environment-specific variables
        export ENV="$ENV"
        export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
        export PYTHONUNBUFFERED=1

        echo -e "${GREEN}✅ Environment configured${NC}"
    fi
}

# ============================================
# Service Startup Functions
# ============================================

start_native_service() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}🎯 Starting MCP Server (Native)${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # Clean up existing processes
    echo "🧹 Cleaning up existing MCP processes..."
    pkill -f "main.py" 2>/dev/null || true
    lsof -ti:$MCP_PORT | xargs kill 2>/dev/null || true
    sleep 2

    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs"

    # Log filtering function
    filter_logs() {
        while IFS= read -r line; do
            if echo "$line" | grep -qE "(INFO.*✅ Registered|INFO.*Loaded|INFO.*initialized|INFO.*registered successfully|Registered service type|Registered external service|Registered tools from|Registered prompts from|Registered resources from|Registered resource:)"; then
                :
            elif echo "$line" | grep -qE "^\\[.*\\]\\s+INFO\\s+"; then
                if echo "$line" | grep -qE "(📊 Discovery summary|🎉 Auto-registration complete|Found [0-9]+ tools in MCP|Found [0-9]+ prompts in MCP|Found [0-9]+ resources in MCP|Tool modules:|Prompt modules:|Resource modules:|Tools discovered:)"; then
                    echo "$line"
                fi
            elif echo "$line" | grep -qE "^[🎯✅❌⚠️🚀🌐🧠📦🔧📝📊🎨🎧🛒🛡️🧪💡🔍]"; then
                echo "$line"
            elif echo "$line" | grep -qE "(ERROR|WARNING|Failed to|failed|error)"; then
                echo "$line"
            elif echo "$line" | grep -qE "(Starting MCP server|Initializing Smart MCP Server|Auto-discovery completed|Server started successfully|Smart MCP Server initialized successfully|AI selectors initialized|Management portal mounted|Uvicorn running|Application startup complete|Started server process)"; then
                echo "$line"
            elif echo "$line" | grep -qE "^(Server:|🎯 MCP endpoint:|🎯 Management Portal:|🎯 API endpoints:|INFO:.*Started server|INFO:.*Application startup|INFO:.*Uvicorn running)"; then
                echo "$line"
            fi

            echo "$line" >> "$PROJECT_ROOT/logs/mcp_server.log"
        done
    }

    # Start the server
    echo "🚀 Starting MCP server on port $MCP_PORT..."
    if [[ "$VERBOSE_LOGS" = true ]]; then
        echo "📝 Detailed logs will be shown in real-time"
        PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python "$PROJECT_ROOT/main.py" --port $MCP_PORT 2>&1 | tee "$PROJECT_ROOT/logs/mcp_server.log" &
    else
        echo "📝 Filtered logs shown (use --verbose for all logs)"
        echo "📝 All logs saved to logs/mcp_server.log"
        PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python "$PROJECT_ROOT/main.py" --port $MCP_PORT 2>&1 | filter_logs &
    fi

    MCP_PID=$!
    echo $MCP_PID > "$PROJECT_ROOT/logs/mcp_server.pid"

    # Wait and check health
    echo ""

    # Check if fast startup mode is enabled
    local lazy_ai="${LAZY_LOAD_AI_SELECTORS:-false}"
    local lazy_external="${LAZY_LOAD_EXTERNAL_SERVICES:-false}"

    if [[ "$lazy_ai" == "true" ]] || [[ "$lazy_external" == "true" ]]; then
        echo "⏳ Fast startup mode enabled (background loading)..."
        echo "   Expected startup time: ~10-15 seconds"
        local max_wait=30
    else
        echo "⏳ Waiting for server to start (synchronous mode)..."
        echo "   Expected startup time: ~60-90 seconds"
        local max_wait=120
    fi

    local wait_interval=2
    local elapsed=0
    local server_healthy=false
    local uvicorn_started=false

    while [ $elapsed -lt $max_wait ]; do
        sleep $wait_interval
        elapsed=$((elapsed + wait_interval))

        # Check if Uvicorn has started (signal from logs)
        if grep -q "Uvicorn running" "$PROJECT_ROOT/logs/mcp_server.log" 2>/dev/null; then
            uvicorn_started=true
        fi

        # Try health check
        if curl -sf --connect-timeout 2 --max-time 5 "http://localhost:$MCP_PORT/health" > /dev/null 2>&1; then
            server_healthy=true
            break
        fi

        # Show progress every 10 seconds
        if [ $((elapsed % 10)) -eq 0 ]; then
            if [ "$uvicorn_started" = true ]; then
                echo "   Server started, finalizing... ($elapsed/${max_wait}s)"
            else
                echo "   Still initializing... ($elapsed/${max_wait}s)"
            fi
        fi

        # Check if process died
        if ! kill -0 $MCP_PID 2>/dev/null; then
            echo -e "${RED}❌ Server process died during startup${NC}"
            break
        fi
    done

    if [ "$server_healthy" = true ]; then
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}✅ MCP Server Started Successfully!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo -e "🌐 Server:          http://localhost:$MCP_PORT"
        echo -e "🎯 MCP Endpoint:    http://localhost:$MCP_PORT/mcp/"
        echo -e "📊 Health Check:    http://localhost:$MCP_PORT/health"
        echo -e "📝 Logs:            logs/mcp_server.log"
        echo -e "🛑 Stop:            Ctrl+C or pkill -f main.py"
        echo -e "${GREEN}========================================${NC}"
        echo ""

        # Register with Consul if requested
        if [[ "$REGISTER_CONSUL" = true ]]; then
            register_with_consul
        fi

        # Keep running with proper cleanup
        cleanup() {
            echo ""
            echo "🛑 Stopping MCP Server..."

            # Stop MCP server
            pkill -f "main.py" 2>/dev/null || true

            # Stop Consul registration process if running
            if [[ -f "$PROJECT_ROOT/logs/consul_registration.pid" ]]; then
                CONSUL_PID=$(cat "$PROJECT_ROOT/logs/consul_registration.pid")
                if kill -0 "$CONSUL_PID" 2>/dev/null; then
                    echo "🔍 Deregistering from Consul..."
                    kill "$CONSUL_PID" 2>/dev/null || true
                fi
                rm -f "$PROJECT_ROOT/logs/consul_registration.pid"
            fi

            echo "✅ Cleanup complete"
            exit 0
        }

        trap cleanup SIGINT SIGTERM
        wait
    else
        echo ""
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}❌ MCP Server failed to start${NC}"
        echo -e "${RED}========================================${NC}"
        echo "   Health check failed after ${max_wait}s"
        echo ""

        # Check if process is still running
        if kill -0 $MCP_PID 2>/dev/null; then
            echo -e "${YELLOW}⚠️  Server process is still running (PID: $MCP_PID)${NC}"
            echo "   The server may still be initializing..."
            echo "   Check: curl http://localhost:$MCP_PORT/health"
        else
            echo -e "${RED}❌ Server process has died${NC}"
        fi

        echo ""
        echo "📝 Last 30 lines of logs:"
        echo "---"
        tail -30 "$PROJECT_ROOT/logs/mcp_server.log"
        echo "---"
        echo ""
        echo "Full logs: tail -f logs/mcp_server.log"
        exit 1
    fi
}

start_docker_service() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}🐳 Starting MCP Services (Docker)${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    cd "$PROJECT_ROOT"

    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
        echo -e "${RED}❌ Docker Compose file not found: $DOCKER_COMPOSE_FILE${NC}"
        exit 1
    fi

    echo "🚀 Starting services with Docker Compose..."
    echo "📄 Using: $DOCKER_COMPOSE_FILE"
    echo ""

    # Stop existing containers
    echo "🧹 Stopping existing containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down 2>/dev/null || true

    # Start services
    echo "🚀 Starting containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

    # Wait for services to be healthy
    echo ""
    echo "⏳ Waiting for services to be healthy..."
    sleep 10

    # Check health
    if curl -sf --connect-timeout 5 --max-time 10 "http://localhost:$MCP_PORT/health" > /dev/null; then
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}✅ MCP Services Started Successfully!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo -e "🌐 Server:          http://localhost:$MCP_PORT"
        echo -e "🎯 MCP Endpoint:    http://localhost:$MCP_PORT/mcp/"
        echo -e "📊 Health Check:    http://localhost:$MCP_PORT/health"
        echo -e "📝 Logs:            docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
        echo -e "🛑 Stop:            docker-compose -f $DOCKER_COMPOSE_FILE down"
        echo -e "${GREEN}========================================${NC}"
        echo ""

        # Register with Consul if requested
        if [[ "$REGISTER_CONSUL" = true ]]; then
            register_with_consul
        fi

        # Follow logs
        echo "📝 Following logs (Ctrl+C to exit)..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
    else
        echo -e "${RED}❌ Services failed to start${NC}"
        echo "Check logs: docker-compose -f $DOCKER_COMPOSE_FILE logs"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail=50
        exit 1
    fi
}

register_with_consul() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}🔍 Consul Service Registration${NC}"
    echo -e "${BLUE}========================================${NC}"

    local consul_host="${CONSUL_HOST:-localhost}"
    local consul_port="${CONSUL_PORT:-8500}"

    # First, check if Consul is available
    if ! curl -sf --connect-timeout 2 "http://${consul_host}:${consul_port}/v1/status/leader" >/dev/null 2>&1; then
        echo -e "${RED}❌ Consul is not available at ${consul_host}:${consul_port}${NC}"
        echo "   Skipping Consul registration"
        return 1
    fi

    echo -e "${GREEN}✅ Consul is available${NC}"

    # Check if Consul registration script exists
    if [[ ! -f "$DEPLOYMENT_DIR/scripts/register_consul.py" ]]; then
        echo -e "${RED}❌ Consul registration script not found: $DEPLOYMENT_DIR/scripts/register_consul.py${NC}"
        return 1
    fi

    # Export environment variables for the registration script
    export CONSUL_HOST="$consul_host"
    export CONSUL_PORT="$consul_port"
    export SERVICE_PORT="$MCP_PORT"
    export SERVICE_HOST="${SERVICE_HOST:-localhost}"

    echo "📝 Registration parameters:"
    echo "   Consul: http://${consul_host}:${consul_port}"
    echo "   Service: mcp"
    echo "   Port: $MCP_PORT"
    echo "   Host: ${SERVICE_HOST:-localhost}"
    echo ""

    # Run registration script in background
    echo "🚀 Starting Consul registration..."
    PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python3 "$DEPLOYMENT_DIR/scripts/register_consul.py" &
    CONSUL_PID=$!
    echo $CONSUL_PID > "$PROJECT_ROOT/logs/consul_registration.pid"
    echo -e "${GREEN}✅ Consul registration process started (PID: $CONSUL_PID)${NC}"

    # Wait a moment for registration to complete
    sleep 3

    # Verify registration
    if verify_consul_registration "mcp"; then
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}✅ Consul Registration Successful${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo "   View services: http://${consul_host}:${consul_port}/ui/dc1/services"
        echo ""
        return 0
    else
        echo -e "${RED}❌ Consul registration verification failed${NC}"
        echo "   Check logs: tail -f logs/mcp_server.log"
        # Don't fail the entire startup, just warn
        return 1
    fi
}

# ============================================
# Action Handlers
# ============================================

action_start() {
    echo -e "${BLUE}🚀 Starting MCP Service...${NC}"

    # Run infrastructure checks
    if [[ "$SKIP_INFRA_CHECKS" = false ]]; then
        if ! run_infrastructure_checks; then
            echo -e "${RED}❌ Infrastructure checks failed${NC}"
            echo "Use --skip-checks to bypass health checks"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  Skipping infrastructure checks${NC}"
    fi

    # Setup environment
    setup_environment

    # Start service based on deployment mode
    if [[ "$USE_DOCKER" = true ]]; then
        start_docker_service
    else
        start_native_service
    fi
}

action_stop() {
    echo -e "${BLUE}🛑 Stopping MCP Service...${NC}"

    if [[ "$USE_DOCKER" = true ]]; then
        # Stop Docker containers
        if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
            echo "Stopping Docker containers..."
            docker-compose -f "$DOCKER_COMPOSE_FILE" down
            echo -e "${GREEN}✅ Docker containers stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  Docker compose file not found${NC}"
        fi
    else
        # Stop native process
        if [[ -f "$PROJECT_ROOT/logs/mcp_server.pid" ]]; then
            local pid=$(cat "$PROJECT_ROOT/logs/mcp_server.pid")
            if kill -0 $pid 2>/dev/null; then
                echo "Stopping MCP server (PID: $pid)..."
                kill $pid
                sleep 2
                if kill -0 $pid 2>/dev/null; then
                    echo "Force killing..."
                    kill -9 $pid
                fi
                rm -f "$PROJECT_ROOT/logs/mcp_server.pid"
                echo -e "${GREEN}✅ MCP server stopped${NC}"
            else
                echo -e "${YELLOW}⚠️  Process not running${NC}"
                rm -f "$PROJECT_ROOT/logs/mcp_server.pid"
            fi
        else
            # Try generic kill
            pkill -f "main.py" && echo -e "${GREEN}✅ MCP server stopped${NC}" || echo -e "${YELLOW}⚠️  No MCP server found running${NC}"
        fi

        # Stop Consul registration
        if [[ -f "$PROJECT_ROOT/logs/consul_registration.pid" ]]; then
            local consul_pid=$(cat "$PROJECT_ROOT/logs/consul_registration.pid")
            kill $consul_pid 2>/dev/null || true
            rm -f "$PROJECT_ROOT/logs/consul_registration.pid"
        fi
    fi
}

action_status() {
    echo -e "${BLUE}📊 MCP Service Status${NC}"
    echo ""

    if [[ "$USE_DOCKER" = true ]]; then
        # Check Docker containers
        if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
            docker-compose -f "$DOCKER_COMPOSE_FILE" ps
        else
            echo -e "${RED}❌ Docker compose file not found${NC}"
        fi
    else
        # Check native process
        if [[ -f "$PROJECT_ROOT/logs/mcp_server.pid" ]]; then
            local pid=$(cat "$PROJECT_ROOT/logs/mcp_server.pid")
            if kill -0 $pid 2>/dev/null; then
                echo -e "${GREEN}✅ MCP Server: Running (PID: $pid)${NC}"

                # Check health endpoint
                if curl -sf "http://localhost:$MCP_PORT/health" >/dev/null 2>&1; then
                    echo -e "${GREEN}✅ Health Check: Passing${NC}"
                    curl -s "http://localhost:$MCP_PORT/health" | jq '.' 2>/dev/null || curl -s "http://localhost:$MCP_PORT/health"
                else
                    echo -e "${RED}❌ Health Check: Failing${NC}"
                fi
            else
                echo -e "${RED}❌ MCP Server: Not Running (stale PID file)${NC}"
                rm -f "$PROJECT_ROOT/logs/mcp_server.pid"
            fi
        else
            echo -e "${RED}❌ MCP Server: Not Running${NC}"
        fi

        # Check Consul registration
        if [[ -f "$PROJECT_ROOT/logs/consul_registration.pid" ]]; then
            local consul_pid=$(cat "$PROJECT_ROOT/logs/consul_registration.pid")
            if kill -0 $consul_pid 2>/dev/null; then
                echo -e "${GREEN}✅ Consul Registration: Active (PID: $consul_pid)${NC}"
            else
                echo -e "${YELLOW}⚠️  Consul Registration: Not Active${NC}"
            fi
        fi
    fi
}

action_restart() {
    echo -e "${BLUE}🔄 Restarting MCP Service...${NC}"
    action_stop
    sleep 3
    action_start
}

# ============================================
# Main Execution
# ============================================

main() {
    cd "$PROJECT_ROOT"

    # Execute action
    case $ACTION in
        start)
            action_start
            ;;
        stop)
            action_stop
            ;;
        status)
            action_status
            ;;
        restart)
            action_restart
            ;;
        *)
            echo -e "${RED}❌ Unknown action: $ACTION${NC}"
            echo "Valid actions: start, stop, status, restart"
            exit 1
            ;;
    esac
}

# Run main function
main
