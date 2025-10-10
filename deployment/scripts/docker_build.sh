#!/bin/bash

# ISA MCP Docker Build Script
#
# This script handles Docker image builds with proper cleanup and verification
#
# Usage:
#   ./docker_build.sh [OPTIONS]
#
# Options:
#   -t, --tag TAG          Image tag (default: isa-mcp:latest)
#   -f, --file FILE        Dockerfile path (default: deployment/Dockerfile.mcp)
#   -p, --platform PLAT    Platform (e.g., linux/amd64,linux/arm64)
#   --no-cache             Build without cache
#   --push                 Push to registry after build
#   --clean-all            Remove all unused Docker resources
#   -h, --help             Show this help message

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_TAG="isa-mcp:latest"
DOCKERFILE="deployment/Dockerfile.mcp"
PLATFORM=""
NO_CACHE=""
PUSH_IMAGE=false
CLEAN_ALL=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Logging functions
log_info() {
    echo -e "${BLUE}9 ${NC}$1"
}

log_success() {
    echo -e "${GREEN} ${NC}$1"
}

log_warning() {
    echo -e "${YELLOW}   ${NC}$1"
}

log_error() {
    echo -e "${RED}L ${NC}$1"
}

show_help() {
    cat << EOF
ISA MCP Docker Build Script

Usage: ./docker_build.sh [OPTIONS]

Options:
  -t, --tag TAG          Image tag (default: isa-mcp:latest)
  -f, --file FILE        Dockerfile path (default: deployment/Dockerfile.mcp)
  -p, --platform PLAT    Platform (e.g., linux/amd64,linux/arm64)
  --no-cache             Build without cache
  --push                 Push to registry after build
  --clean-all            Remove all unused Docker resources
  -h, --help             Show this help message

Examples:
  # Basic build
  ./docker_build.sh

  # Build with custom tag
  ./docker_build.sh -t isa-mcp:v1.0.0

  # Multi-platform build
  ./docker_build.sh -p linux/amd64,linux/arm64

  # Build and push to registry
  ./docker_build.sh -t myregistry/isa-mcp:latest --push

  # Clean build (no cache)
  ./docker_build.sh --no-cache --clean-all

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -f|--file)
            DOCKERFILE="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        --clean-all)
            CLEAN_ALL=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Change to project root
cd "$PROJECT_ROOT"

echo ""
log_info "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP"
log_info "  ISA MCP Docker Build"
log_info "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

log_success "Docker is running"

# Display build configuration
log_info "Build Configuration:"
log_info "  Image Tag:    $IMAGE_TAG"
log_info "  Dockerfile:   $DOCKERFILE"
log_info "  Platform:     ${PLATFORM:-default}"
log_info "  No Cache:     ${NO_CACHE:-false}"
log_info "  Push:         $PUSH_IMAGE"
echo ""

# Verify Dockerfile exists
if [[ ! -f "$DOCKERFILE" ]]; then
    log_error "Dockerfile not found: $DOCKERFILE"
    exit 1
fi

log_success "Dockerfile found: $DOCKERFILE"

# Clean all unused Docker resources if requested
if [[ "$CLEAN_ALL" == "true" ]]; then
    log_warning "Cleaning all unused Docker resources..."
    docker system prune -af --volumes || true
    log_success "Docker cleanup completed"
fi

# Remove previous images with same tag
log_info "Checking for existing images with tag: $IMAGE_TAG"
EXISTING_IMAGES=$(docker images -q "$IMAGE_TAG" 2>/dev/null || true)

if [[ -n "$EXISTING_IMAGES" ]]; then
    log_warning "Found existing image(s) with tag: $IMAGE_TAG"

    # Get image details before deletion
    docker images "$IMAGE_TAG" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}"

    log_info "Removing existing images..."
    docker rmi -f $EXISTING_IMAGES 2>/dev/null || true
    log_success "Old images removed"
else
    log_info "No existing images found"
fi

# Check for related images (e.g., mcp-service-*, isa-mcp-*)
log_info "Checking for related ISA MCP images..."
RELATED_IMAGES=$(docker images | grep -E "isa-mcp|isa_mcp|mcp-service" | grep -v "$IMAGE_TAG" || true)

if [[ -n "$RELATED_IMAGES" ]]; then
    log_warning "Found related ISA MCP images:"
    echo "$RELATED_IMAGES"

    read -p "Remove related images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        RELATED_IDS=$(echo "$RELATED_IMAGES" | awk '{print $3}')
        docker rmi -f $RELATED_IDS 2>/dev/null || true
        log_success "Related images removed"
    else
        log_info "Keeping related images"
    fi
fi

# Build the image
echo ""
log_info "Building Docker image..."
log_info "This may take several minutes..."
echo ""

BUILD_CMD="docker build -f $DOCKERFILE -t $IMAGE_TAG $NO_CACHE"

# Add platform if specified
if [[ -n "$PLATFORM" ]]; then
    BUILD_CMD="docker buildx build --platform $PLATFORM -f $DOCKERFILE -t $IMAGE_TAG $NO_CACHE"

    # Add --load for local builds or --push for registry
    if [[ "$PUSH_IMAGE" == "true" ]]; then
        BUILD_CMD="$BUILD_CMD --push"
    else
        BUILD_CMD="$BUILD_CMD --load"
    fi
fi

BUILD_CMD="$BUILD_CMD ."

# Execute build
log_info "Running: $BUILD_CMD"
echo ""

if $BUILD_CMD; then
    echo ""
    log_success "Docker image built successfully!"
else
    echo ""
    log_error "Docker build failed"
    exit 1
fi

# Verify the image
log_info "Verifying built image..."

if docker inspect "$IMAGE_TAG" > /dev/null 2>&1; then
    log_success "Image verified: $IMAGE_TAG"

    # Display image details
    echo ""
    log_info "Image Details:"
    IMAGE_SIZE=$(docker inspect "$IMAGE_TAG" --format='{{.Size}}' | awk '{size=$1/1024/1024; printf "%.2f MB", size}')
    IMAGE_ID=$(docker inspect "$IMAGE_TAG" --format='{{.Id}}' | cut -d: -f2 | cut -c1-12)
    IMAGE_CREATED=$(docker inspect "$IMAGE_TAG" --format='{{.Created}}' | cut -d'.' -f1 | sed 's/T/ /')

    echo ""
    echo "  Repository:    $(echo $IMAGE_TAG | cut -d: -f1)"
    echo "  Tag:           $(echo $IMAGE_TAG | cut -d: -f2)"
    echo "  Image ID:      $IMAGE_ID"
    echo "  Size:          $IMAGE_SIZE"
    echo "  Created:       $IMAGE_CREATED"
    echo ""
else
    log_error "Image verification failed"
    exit 1
fi

# List all ISA MCP images
log_info "Current ISA MCP images:"
docker images | grep -E "REPOSITORY|isa-mcp|isa_mcp|mcp-service" || log_warning "No ISA MCP images found"

# Push to registry if requested
if [[ "$PUSH_IMAGE" == "true" ]] && [[ -z "$PLATFORM" ]]; then
    echo ""
    log_info "Pushing image to registry..."

    if docker push "$IMAGE_TAG"; then
        log_success "Image pushed to registry: $IMAGE_TAG"
    else
        log_error "Failed to push image to registry"
        exit 1
    fi
fi

# Clean up build cache (optional)
echo ""
read -p "Clean up Docker build cache? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Cleaning Docker build cache..."
    docker builder prune -f
    log_success "Build cache cleaned"
fi

# Display success summary
echo ""
log_success "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP"
log_success "  Build Complete!"
log_success "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP"
echo ""
log_info "To run the image:"
echo ""
echo "  # With environment file:"
echo "  docker run -p 8081:8081 --env-file deployment/dev/.env $IMAGE_TAG"
echo ""
echo "  # With environment variables:"
echo "  docker run -p 8081:8081 \\"
echo "    -e SUPABASE_LOCAL_URL=http://... \\"
echo "    -e SUPABASE_LOCAL_ANON_KEY=eyJ... \\"
echo "    -e LOKI_ENABLED=true \\"
echo "    -e LOKI_URL=http://localhost:3100 \\"
echo "    $IMAGE_TAG"
echo ""
echo "  # Using docker-compose:"
echo "  cd /path/to/isA_Cloud/deployments && docker-compose up -d mcp"
echo ""
log_info "To test the image:"
echo ""
echo "  docker run --rm $IMAGE_TAG python -c 'from core.config import get_settings; print(\"MCP Server Ready\")'"
echo ""
