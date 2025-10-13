#!/bin/bash
# ============================================
# Build MCP Staging Container for AMD64
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=( Building MCP Staging Container (AMD64)${NC}"
echo "============================================"

# Configuration
IMAGE_NAME="isa-mcp-staging"
IMAGE_TAG="latest"
DOCKERFILE="deployment/staging/Dockerfile.staging"
PROJECT_ROOT="/Users/xenodennis/Documents/Fun/isA_MCP"

# Change to project root
cd "$PROJECT_ROOT"

echo -e "${YELLOW}=Á Working directory: $(pwd)${NC}"
echo -e "${YELLOW}=3 Dockerfile: $DOCKERFILE${NC}"
echo -e "${YELLOW}<÷  Image: $IMAGE_NAME:$IMAGE_TAG${NC}"
echo ""

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
    echo -e "${RED}L Error: Dockerfile not found at $DOCKERFILE${NC}"
    exit 1
fi

# Check if requirements file exists
if [ ! -f "deployment/staging/requirements.staging.txt" ]; then
    echo -e "${RED}L Error: requirements.staging.txt not found${NC}"
    exit 1
fi

echo -e "${GREEN} Pre-flight checks passed${NC}"
echo ""

# Build the image for AMD64 platform
echo -e "${BLUE}=( Building Docker image for AMD64...${NC}"
docker build \
    --platform linux/amd64 \
    -f "$DOCKERFILE" \
    -t "$IMAGE_NAME:$IMAGE_TAG" \
    --progress=plain \
    .

# Check build status
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN} Build completed successfully!${NC}"
    echo ""

    # Show image info
    echo -e "${BLUE}=Ê Image Information:${NC}"
    docker images "$IMAGE_NAME:$IMAGE_TAG" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo ""

    echo -e "${GREEN}<‰ Ready to deploy with: ./deployment/staging/deploy_mcp_staging.sh${NC}"
else
    echo ""
    echo -e "${RED}L Build failed!${NC}"
    exit 1
fi
