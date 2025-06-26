#!/bin/bash
# setup-deployment.sh - Complete MCP Server Deployment Setup

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLORS=true

# Color functions
if $COLORS; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    PURPLE='\033[0;35m'
    CYAN='\033[0;36m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    PURPLE=''
    CYAN=''
    NC=''
fi

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create SSL certificates for development
create_ssl_certs() {
    log_info "Creating SSL certificates for development..."
    mkdir -p ssl
    
    if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout ssl/key.pem \
            -out ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        log_success "SSL certificates created"
    else
        log_info "SSL certificates already exist"
    fi
}

# Function to setup directories
setup_directories() {
    log_info "Setting up directories..."
    mkdir -p logs pids data ssl
    log_success "Directories created"
}

# Function to check Python dependencies
check_python_deps() {
    log_info "Checking Python dependencies..."
    
    if ! command_exists python3; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    if ! command_exists pip3; then
        log_error "pip3 is required but not installed"
        exit 1
    fi
    
    # Check if requirements.txt exists
    if [ ! -f requirements.txt ]; then
        log_error "requirements.txt not found"
        exit 1
    fi
    
    log_info "Installing Python dependencies..."
    pip3 install -r requirements.txt
    log_success "Python dependencies installed"
}

# Function to test MCP server
test_mcp_server() {
    log_info "Testing MCP server startup..."
    
    # Start server in background for testing
    python3 multi_mcp_server.py --port 8888 &
    TEST_PID=$!
    
    # Wait a bit for startup
    sleep 5
    
    # Test health endpoint
    if command_exists curl; then
        if curl -f http://localhost:8888/health >/dev/null 2>&1; then
            log_success "MCP server test passed"
        else
            log_error "MCP server health check failed"
            kill $TEST_PID 2>/dev/null
            exit 1
        fi
    else
        log_warning "curl not available, skipping health check test"
    fi
    
    # Clean up test server
    kill $TEST_PID 2>/dev/null
    sleep 2
}

# Function to setup Docker deployment
setup_docker() {
    log_info "Setting up Docker deployment..."
    
    if ! command_exists docker; then
        log_error "Docker is required but not installed"
        log_info "Please install Docker: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    if ! command_exists docker-compose; then
        log_error "Docker Compose is required but not installed"
        log_info "Please install Docker Compose: https://docs.docker.com/compose/install/"
        return 1
    fi
    
    # Build and start services
    log_info "Building Docker images..."
    docker-compose build
    
    log_info "Starting services..."
    docker-compose up -d
    
    # Wait for services to start
    log_info "Waiting for services to start..."
    sleep 10
    
    # Test services
    for port in 8001 8002 8003; do
        if curl -f http://localhost:$port/health >/dev/null 2>&1; then
            log_success "Service on port $port is healthy"
        else
            log_warning "Service on port $port may not be ready yet"
        fi
    done
    
    log_success "Docker deployment completed"
    return 0
}

# Function to setup systemd services
setup_systemd() {
    log_info "Setting up systemd services..."
    
    if [ "$EUID" -ne 0 ]; then
        log_error "Systemd setup requires root privileges"
        log_info "Run: sudo ./setup-deployment.sh --systemd"
        return 1
    fi
    
    ./start-mcp-servers.sh
    log_success "Systemd services configured"
    return 0
}

# Function to setup process management
setup_process_manager() {
    log_info "Setting up process manager..."
    
    # Make scripts executable
    chmod +x manage-mcp.sh
    
    # Start servers
    ./manage-mcp.sh start
    
    log_success "Process manager setup completed"
    return 0
}

# Function to show status
show_status() {
    echo
    log_info "=== MCP Server Deployment Status ==="
    echo
    
    # Check Docker
    if command_exists docker && docker-compose ps >/dev/null 2>&1; then
        echo -e "${CYAN}Docker Services:${NC}"
        docker-compose ps
        echo
    fi
    
    # Check systemd
    if systemctl is-active --quiet mcp-server-8001 2>/dev/null; then
        echo -e "${CYAN}Systemd Services:${NC}"
        systemctl status mcp-server-8001 mcp-server-8002 mcp-server-8003 --no-pager -l
        echo
    fi
    
    # Check process manager
    if [ -f manage-mcp.sh ]; then
        echo -e "${CYAN}Process Manager:${NC}"
        ./manage-mcp.sh status
        echo
    fi
    
    # Health checks
    echo -e "${CYAN}Health Checks:${NC}"
    for port in 8001 8002 8003; do
        if command_exists curl; then
            if curl -f http://localhost:$port/health >/dev/null 2>&1; then
                echo -e "  Port $port: ${GREEN}✅ Healthy${NC}"
            else
                echo -e "  Port $port: ${RED}❌ Unhealthy${NC}"
            fi
        else
            echo -e "  Port $port: ${YELLOW}? Unknown (curl not available)${NC}"
        fi
    done
    
    echo
    log_info "=== Useful Commands ==="
    echo
    echo "Docker:"
    echo "  docker-compose up -d          # Start all services"
    echo "  docker-compose down           # Stop all services"
    echo "  docker-compose logs -f        # View logs"
    echo "  docker-compose ps             # Check status"
    echo
    echo "Systemd:"
    echo "  sudo systemctl status mcp-server-8001"
    echo "  sudo systemctl restart mcp-server-8002"
    echo "  sudo journalctl -u mcp-server-8003 -f"
    echo
    echo "Process Manager:"
    echo "  ./manage-mcp.sh start|stop|restart|status"
    echo
    echo "Health Checks:"
    echo "  curl http://localhost:8001/health"
    echo "  curl http://localhost:8002/health"
    echo "  curl http://localhost:8003/health"
    echo
}

# Main function
main() {
    echo -e "${PURPLE}"
    echo "🚀 MCP Server Deployment Setup"
    echo "==============================="
    echo -e "${NC}"
    
    # Parse arguments
    SETUP_DOCKER=false
    SETUP_SYSTEMD=false
    SETUP_PROCESS=false
    SHOW_STATUS=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --docker)
                SETUP_DOCKER=true
                shift
                ;;
            --systemd)
                SETUP_SYSTEMD=true
                shift
                ;;
            --process)
                SETUP_PROCESS=true
                shift
                ;;
            --status)
                SHOW_STATUS=true
                shift
                ;;
            --all)
                SETUP_DOCKER=true
                SETUP_PROCESS=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --docker      Setup Docker deployment"
                echo "  --systemd     Setup systemd services (requires sudo)"
                echo "  --process     Setup process manager"
                echo "  --all         Setup Docker and process manager"
                echo "  --status      Show deployment status"
                echo "  -h, --help    Show this help message"
                echo ""
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # If no specific option, show help
    if [ "$SETUP_DOCKER" = false ] && [ "$SETUP_SYSTEMD" = false ] && [ "$SETUP_PROCESS" = false ] && [ "$SHOW_STATUS" = false ]; then
        log_info "No deployment method specified. Use --help for options."
        log_info "Recommended: ./setup-deployment.sh --all"
        exit 1
    fi
    
    # Common setup
    setup_directories
    create_ssl_certs
    check_python_deps
    test_mcp_server
    
    # Specific setups
    if [ "$SETUP_DOCKER" = true ]; then
        setup_docker
    fi
    
    if [ "$SETUP_SYSTEMD" = true ]; then
        setup_systemd
    fi
    
    if [ "$SETUP_PROCESS" = true ]; then
        setup_process_manager
    fi
    
    if [ "$SHOW_STATUS" = true ]; then
        show_status
    fi
    
    echo
    log_success "🎉 MCP Server deployment setup completed!"
    echo
    log_info "Next steps:"
    echo "1. Configure your domain in nginx.conf"
    echo "2. Update SSL certificates for production"
    echo "3. Test the MCP endpoints"
    echo "4. Monitor the logs"
    echo
    log_info "Run './setup-deployment.sh --status' to check deployment status"
}

# Run main function
main "$@" 