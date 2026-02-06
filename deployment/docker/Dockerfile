# =============================================================================
# ISA MCP Service - Production Dockerfile
# =============================================================================
# Inherits from Harbor python-base image (shared platform SDK)
#
# Image Hierarchy:
#   harbor.local:30443/isa/python-base:latest  <- Platform SDK
#   └── harbor.local:30443/isa/mcp-service     <- This file
#
# Build & Push:
#   docker build -t harbor.local:30443/isa/mcp-service:latest -f deployment/k8s/Dockerfile.mcp .
#   docker push harbor.local:30443/isa/mcp-service:latest
#
# Deploy:
#   helm upgrade --install mcp-service ./charts/isa-service -f values/mcp.yaml -n isa-cloud-staging
# =============================================================================

# =============================================================================
# Stage 1: Builder - Install MCP-specific dependencies
# =============================================================================
FROM harbor.local:30443/isa/python-base:latest AS builder

# Install build tools for MCP packages
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package installation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy only requirements first (Docker layer caching)
WORKDIR /app
COPY deployment/requirements/project.txt /tmp/project.txt

# Install MCP-specific packages
RUN uv pip install --system --no-cache -r /tmp/project.txt

# Install Playwright browsers (needed for web automation)
RUN playwright install chromium --with-deps

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM harbor.local:30443/isa/python-base:latest

# Runtime arguments
ARG ENVIRONMENT=production
ARG VERSION=latest
ARG BUILD_DATE
ARG VCS_REF

# Labels
LABEL org.opencontainers.image.title="ISA MCP Service" \
      org.opencontainers.image.description="Model Context Protocol Server with FastMCP" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="ISA Platform"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=${ENVIRONMENT}

# Install Playwright runtime dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r mcp && useradd -r -g mcp mcp

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy Playwright browsers
COPY --from=builder /root/.cache/ms-playwright /home/mcp/.cache/ms-playwright

# Copy application code
COPY --chown=mcp:mcp . .

# Create directories
RUN mkdir -p /app/logs /app/cache /app/data_storage && \
    chown -R mcp:mcp /app/logs /app/cache /app/data_storage /home/mcp/.cache

# Switch to non-root user
USER mcp

# Expose MCP server port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Default command
CMD ["python", "main.py", "--port", "8081"]

# =============================================================================
# Build Examples:
# =============================================================================
# Development:
#   docker build -f deployment/k8s/Dockerfile.mcp \
#     --build-arg ENVIRONMENT=dev \
#     -t harbor.local:30443/isa/mcp-service:dev .
#   docker push harbor.local:30443/isa/mcp-service:dev
#
# Production:
#   docker build -f deployment/k8s/Dockerfile.mcp \
#     --build-arg ENVIRONMENT=production \
#     --build-arg VERSION=$(git describe --tags 2>/dev/null || echo "latest") \
#     --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
#     --build-arg VCS_REF=$(git rev-parse --short HEAD) \
#     -t harbor.local:30443/isa/mcp-service:latest .
#   docker push harbor.local:30443/isa/mcp-service:latest
#
# Deploy:
#   helm upgrade --install mcp-service ./charts/isa-service \
#     -f values/mcp.yaml -n isa-cloud-staging
# =============================================================================
