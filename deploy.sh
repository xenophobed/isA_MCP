#!/bin/bash

# MCP Server Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${ENVIRONMENT:-development}
PLATFORM=${1:-docker}
ACTION=${2:-up}

echo -e "${BLUE}🚀 MCP Server Deployment Script${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Platform: ${PLATFORM}${NC}"
echo -e "${BLUE}Action: ${ACTION}${NC}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"
    
    case $PLATFORM in
        docker)
            if ! command -v docker &> /dev/null; then
                echo -e "${RED}❌ Docker is not installed${NC}"
                exit 1
            fi
            if ! command -v docker-compose &> /dev/null; then
                echo -e "${RED}❌ Docker Compose is not installed${NC}"
                exit 1
            fi
            ;;
        k8s|kubernetes)
            if ! command -v kubectl &> /dev/null; then
                echo -e "${RED}❌ kubectl is not installed${NC}"
                exit 1
            fi
            ;;
        local)
            if ! command -v python3 &> /dev/null; then
                echo -e "${RED}❌ Python 3 is not installed${NC}"
                exit 1
            fi
            ;;
    esac
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

# Function to build Docker image
build_image() {
    echo -e "${YELLOW}🔨 Building Docker image...${NC}"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker build --target production -t mcp-server:latest .
    else
        docker build --target development -t mcp-server:latest .
    fi
    
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
}

# Function to deploy with Docker Compose
deploy_docker() {
    case $ACTION in
        up|start)
            echo -e "${YELLOW}🚀 Starting services with Docker Compose...${NC}"
            build_image
            docker-compose up -d
            
            echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
            sleep 10
            
            # Check health
            if curl -f http://localhost/health >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Services are healthy and ready!${NC}"
                echo -e "${BLUE}📊 Service URLs:${NC}"
                echo -e "  • Load Balancer: http://localhost"
                echo -e "  • MCP Protocol: http://localhost:8080/mcp"
                echo -e "  • Individual instances:"
                echo -e "    - Instance 1: http://localhost:3001"
                echo -e "    - Instance 2: http://localhost:3002"
                echo -e "    - Instance 3: http://localhost:3003"
                echo -e "  • Monitoring:"
                echo -e "    - Prometheus: http://localhost:9090"
                echo -e "    - Grafana: http://localhost:3000 (admin/admin)"
            else
                echo -e "${RED}❌ Services may not be ready yet. Check logs with: docker-compose logs${NC}"
            fi
            ;;
        down|stop)
            echo -e "${YELLOW}🛑 Stopping services...${NC}"
            docker-compose down
            echo -e "${GREEN}✅ Services stopped${NC}"
            ;;
        restart)
            echo -e "${YELLOW}🔄 Restarting services...${NC}"
            docker-compose down
            build_image
            docker-compose up -d
            echo -e "${GREEN}✅ Services restarted${NC}"
            ;;
        logs)
            docker-compose logs -f
            ;;
        *)
            echo -e "${RED}❌ Unknown action: $ACTION${NC}"
            exit 1
            ;;
    esac
}

# Function to deploy to Kubernetes
deploy_k8s() {
    case $ACTION in
        up|apply)
            echo -e "${YELLOW}🚀 Deploying to Kubernetes...${NC}"
            
            # Build and tag image
            build_image
            
            # Apply manifests
            kubectl apply -f k8s/namespace.yaml
            kubectl apply -f k8s/configmap.yaml
            kubectl apply -f k8s/pvc.yaml
            kubectl apply -f k8s/deployment.yaml
            kubectl apply -f k8s/service.yaml
            kubectl apply -f k8s/hpa.yaml
            
            echo -e "${YELLOW}⏳ Waiting for deployment to be ready...${NC}"
            kubectl wait --for=condition=available --timeout=300s deployment/mcp-server -n mcp-server
            
            # Get service info
            echo -e "${GREEN}✅ Kubernetes deployment completed!${NC}"
            echo -e "${BLUE}📊 Service Information:${NC}"
            kubectl get services -n mcp-server
            echo ""
            echo -e "${BLUE}📋 Pod Status:${NC}"
            kubectl get pods -n mcp-server
            ;;
        down|delete)
            echo -e "${YELLOW}🛑 Deleting Kubernetes resources...${NC}"
            kubectl delete -f k8s/ --ignore-not-found=true
            echo -e "${GREEN}✅ Kubernetes resources deleted${NC}"
            ;;
        status)
            echo -e "${BLUE}📊 Kubernetes Status:${NC}"
            kubectl get all -n mcp-server
            ;;
        logs)
            kubectl logs -f deployment/mcp-server -n mcp-server
            ;;
        *)
            echo -e "${RED}❌ Unknown action: $ACTION${NC}"
            exit 1
            ;;
    esac
}

# Function to run locally
run_local() {
    case $ACTION in
        up|start)
            echo -e "${YELLOW}🚀 Starting MCP server locally...${NC}"
            
            # Install dependencies
            if [ ! -d "venv" ]; then
                echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
                python3 -m venv venv
            fi
            
            echo -e "${YELLOW}📦 Installing dependencies...${NC}"
            source venv/bin/activate
            pip install -r requirements.txt
            
            # Run server
            echo -e "${YELLOW}🚀 Starting FastAPI wrapper...${NC}"
            export ENVIRONMENT=development
            python fastapi_mcp_server.py
            ;;
        stop)
            echo -e "${YELLOW}🛑 Stopping local server...${NC}"
            pkill -f "fastapi_mcp_server.py" || echo "No running processes found"
            ;;
        *)
            echo -e "${RED}❌ Unknown action: $ACTION${NC}"
            exit 1
            ;;
    esac
}

# Main execution
main() {
    check_prerequisites
    
    case $PLATFORM in
        docker)
            deploy_docker
            ;;
        k8s|kubernetes)
            deploy_k8s
            ;;
        local)
            run_local
            ;;
        *)
            echo -e "${RED}❌ Unknown platform: $PLATFORM${NC}"
            echo "Usage: $0 [docker|k8s|local] [up|down|restart|logs|status]"
            exit 1
            ;;
    esac
}

# Help function
show_help() {
    echo "MCP Server Deployment Script"
    echo ""
    echo "Usage: $0 [PLATFORM] [ACTION]"
    echo ""
    echo "PLATFORMS:"
    echo "  docker     - Deploy using Docker Compose (default)"
    echo "  k8s        - Deploy to Kubernetes cluster"
    echo "  local      - Run locally with Python"
    echo ""
    echo "ACTIONS:"
    echo "  up/start   - Start services (default)"
    echo "  down/stop  - Stop services"
    echo "  restart    - Restart services (Docker only)"
    echo "  logs       - View logs"
    echo "  status     - Check status (K8s only)"
    echo ""
    echo "ENVIRONMENT VARIABLES:"
    echo "  ENVIRONMENT - Set to 'production' or 'development'"
    echo ""
    echo "Examples:"
    echo "  $0 docker up          # Start with Docker Compose"
    echo "  $0 k8s apply          # Deploy to Kubernetes"
    echo "  $0 local start        # Run locally"
    echo "  ENVIRONMENT=production $0 docker up"
}

# Check for help
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main