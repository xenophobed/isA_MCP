#!/bin/bash
# ============================================
# Deploy MCP Staging Container
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=� Deploying MCP Staging Container${NC}"
echo "============================================"

# Configuration
PROJECT_ROOT="/Users/xenodennis/Documents/Fun/isA_MCP"
COMPOSE_FILE="deployment/staging/mcp_staging.yml"
ENV_FILE="deployment/staging/.env.staging"
CONTAINER_NAME="mcp-staging-test"

# Change to project root
cd "$PROJECT_ROOT"

echo -e "${YELLOW}=� Working directory: $(pwd)${NC}"
echo -e "${YELLOW}=3 Compose file: $COMPOSE_FILE${NC}"
echo -e "${YELLOW}= Env file: $ENV_FILE${NC}"
echo ""

# Check if docker-compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}L Error: Docker compose file not found at $COMPOSE_FILE${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}L Error: Environment file not found at $ENV_FILE${NC}"
    exit 1
fi

# Check if image exists
if ! docker images isa-mcp-staging:latest | grep -q isa-mcp-staging; then
    echo -e "${YELLOW}�  Image not found. Building first...${NC}"
    ./deployment/staging/build_mcp_staging.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}L Build failed!${NC}"
        exit 1
    fi
fi

echo -e "${GREEN} Pre-flight checks passed${NC}"
echo ""

# Stop and remove existing container if it exists
echo -e "${BLUE}Checking for existing container...${NC}"
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}Found existing container: ${CONTAINER_NAME}${NC}"

    # Check if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${YELLOW}Stopping running container...${NC}"
        docker stop "${CONTAINER_NAME}" > /dev/null 2>&1
    fi

    # Remove the container
    echo -e "${YELLOW}Removing old container...${NC}"
    docker rm "${CONTAINER_NAME}" > /dev/null 2>&1
    echo -e "${GREEN}Old container removed successfully${NC}"
else
    echo -e "${BLUE}No existing container found, proceeding with fresh deployment${NC}"
fi

# Start the container
echo ""
echo -e "${BLUE}=� Starting MCP Staging container...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# Check if container started successfully
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN} Container started successfully!${NC}"
    echo ""

    # Wait a moment for the container to initialize
    sleep 3

    # Show container status
    echo -e "${BLUE}=� Container Status:${NC}"
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""

    # Show logs
    echo -e "${BLUE}=� Container Logs (last 20 lines):${NC}"
    echo "============================================"
    docker logs --tail 20 "$CONTAINER_NAME"
    echo "============================================"
    echo ""

    # Health check
    echo -e "${BLUE}<� Waiting for health check...${NC}"
    for i in {1..12}; do
        if docker inspect "$CONTAINER_NAME" --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
            echo -e "${GREEN} Container is healthy!${NC}"
            break
        fi
        echo -e "${YELLOW}� Waiting... ($i/12)${NC}"
        sleep 5
    done

    echo ""
    echo -e "${GREEN}<� Deployment complete!${NC}"
    echo ""
    echo -e "${BLUE}=� Service Endpoints:${NC}"
    echo "  - MCP Service: http://localhost:8081"
    echo "  - Health Check: http://localhost:8081/health"
    echo ""
    echo -e "${BLUE}=� Useful Commands:${NC}"
    echo "  - View logs: docker logs -f $CONTAINER_NAME"
    echo "  - Check status: docker ps --filter name=$CONTAINER_NAME"
    echo "  - Stop service: docker-compose -f $COMPOSE_FILE down"
    echo "  - Restart service: docker restart $CONTAINER_NAME"
    echo "  - Shell access: docker exec -it $CONTAINER_NAME /bin/bash"

else
    echo ""
    echo -e "${RED}L Failed to start container!${NC}"
    exit 1
fi
