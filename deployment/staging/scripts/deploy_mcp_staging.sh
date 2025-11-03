#!/bin/bash
# ============================================
# Build & Deploy MCP Staging Container
# Rebuilds image every time to capture latest code changes
# Uses Docker layer caching to speed up unchanged parts
#
# Usage:
#   ./deploy_mcp_staging.sh           # Build with cache (fast)
#   ./deploy_mcp_staging.sh --no-cache # Full rebuild without cache
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse command line arguments
NO_CACHE=""
if [[ "$1" == "--no-cache" ]]; then
    NO_CACHE="--no-cache"
    echo -e "${YELLOW}⚠️  No-cache mode enabled - full rebuild${NC}"
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  MCP Staging - Build & Deploy${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Configuration
PROJECT_ROOT="/Users/xenodennis/Documents/Fun/isA_MCP"
IMAGE_NAME="isa-mcp-staging"
IMAGE_TAG="latest"
DOCKERFILE="deployment/staging/Dockerfile.staging"
COMPOSE_FILE="deployment/staging/mcp_staging.yml"
ENV_FILE="deployment/staging/config/.env.staging"
CONTAINER_NAME="mcp-staging"

# Change to project root
cd "$PROJECT_ROOT"

echo ""
echo -e "${BLUE}📋 Configuration:${NC}"
echo -e "${YELLOW}   Working directory: $(pwd)${NC}"
echo -e "${YELLOW}   Dockerfile: $DOCKERFILE${NC}"
echo -e "${YELLOW}   Image: $IMAGE_NAME:$IMAGE_TAG${NC}"
echo -e "${YELLOW}   Compose file: $COMPOSE_FILE${NC}"
echo ""

# ============================================
# Pre-flight Checks
# ============================================
echo -e "${BLUE}🔍 Running pre-flight checks...${NC}"

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
    echo -e "${RED}❌ Error: Dockerfile not found at $DOCKERFILE${NC}"
    exit 1
fi

# Check if requirements file exists
if [ ! -f "deployment/staging/config/requirements.staging.txt" ]; then
    echo -e "${RED}❌ Error: requirements.staging.txt not found${NC}"
    exit 1
fi

# Check if docker-compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}❌ Error: Docker compose file not found at $COMPOSE_FILE${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: Environment file not found at $ENV_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Pre-flight checks passed${NC}"
echo ""

# ============================================
# Build Docker Image
# ============================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Step 1: Building Docker Image${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🔨 Building image with latest code changes...${NC}"
if [ -z "$NO_CACHE" ]; then
    echo -e "${YELLOW}   (Docker will cache unchanged layers for speed)${NC}"
else
    echo -e "${YELLOW}   (Building without cache - this will take longer)${NC}"
fi
echo ""

# Build the image for AMD64 platform with BuildKit for ultra-fast caching
# BuildKit enables:
# - Cache mounts for apt, pip, uv (persistent across builds)
# - Parallel layer execution
# - Improved caching strategy
# Layer cache is preserved for dependencies (requirements.txt)
# But application code (main.py, scripts) will be rebuilt if changed
DOCKER_BUILDKIT=1 docker build \
    --platform linux/amd64 \
    --pull \
    $NO_CACHE \
    -f "$DOCKERFILE" \
    -t "$IMAGE_NAME:$IMAGE_TAG" \
    --progress=plain \
    .

# Check build status
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Build completed successfully!${NC}"
echo ""

# Show image info
echo -e "${BLUE}📦 Image Information:${NC}"
docker images "$IMAGE_NAME:$IMAGE_TAG" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo ""

# ============================================
# Stop and Remove Old Container
# ============================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Step 2: Preparing Deployment${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🔍 Checking for existing container...${NC}"

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}   Found existing container: ${CONTAINER_NAME}${NC}"

    # Check if container is running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${YELLOW}   Stopping running container...${NC}"
        docker stop "${CONTAINER_NAME}" > /dev/null 2>&1
    fi

    # Remove the container
    echo -e "${YELLOW}   Removing old container...${NC}"
    docker rm "${CONTAINER_NAME}" > /dev/null 2>&1
    echo -e "${GREEN}   ✅ Old container removed${NC}"
else
    echo -e "${BLUE}   No existing container found${NC}"
fi

echo ""

# ============================================
# Deploy New Container
# ============================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Step 3: Deploying Container${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🚀 Starting MCP Staging container with fresh build...${NC}"

docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# Check if container started successfully
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Failed to start container!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Container started successfully!${NC}"
echo ""

# Wait a moment for the container to initialize
sleep 3

# ============================================
# Verification
# ============================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Step 4: Verification${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Show container status
echo -e "${BLUE}📊 Container Status:${NC}"
docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Show logs
echo -e "${BLUE}📜 Container Logs (last 20 lines):${NC}"
echo "────────────────────────────────────────"
docker logs --tail 20 "$CONTAINER_NAME"
echo "────────────────────────────────────────"
echo ""

# Health check
echo -e "${BLUE}🏥 Waiting for health check...${NC}"
HEALTH_CHECK_PASSED=false
for i in {1..12}; do
    if docker inspect "$CONTAINER_NAME" --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
        echo -e "${GREEN}   ✅ Container is healthy!${NC}"
        HEALTH_CHECK_PASSED=true
        break
    fi
    echo -e "${YELLOW}   ⏳ Waiting... ($i/12)${NC}"
    sleep 5
done

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    echo -e "${YELLOW}   ⚠️  Health check timeout (container may still be starting)${NC}"
fi

echo ""

# ============================================
# Success Summary
# ============================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✨ Deployment Complete!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🌐 Service Endpoints:${NC}"
echo "   • MCP Service:  http://localhost:8081"
echo "   • Health Check: http://localhost:8081/health"
echo ""
echo -e "${BLUE}🛠️  Useful Commands:${NC}"
echo "   • View logs:     docker logs -f $CONTAINER_NAME"
echo "   • Check status:  docker ps --filter name=$CONTAINER_NAME"
echo "   • Stop service:  docker-compose -f $COMPOSE_FILE down"
echo "   • Restart:       docker restart $CONTAINER_NAME"
echo "   • Shell access:  docker exec -it $CONTAINER_NAME /bin/bash"
echo ""
echo -e "${BLUE}💡 Notes:${NC}"
echo "   • Image rebuilt with latest code changes"
if [ -z "$NO_CACHE" ]; then
    echo "   • Docker cached unchanged layers for speed"
else
    echo "   • Full rebuild performed (no cache used)"
fi
echo "   • Source code mounted via volumes for live updates"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
