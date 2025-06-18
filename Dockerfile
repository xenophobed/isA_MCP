# Multi-stage Docker build for MCP Server
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 3000 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health/live || exit 1

# Default command
CMD ["python", "fastapi_mcp_server.py"]

# Production stage
FROM base as production

# Override for production settings
ENV ENVIRONMENT=production

# Use gunicorn for production
RUN pip install gunicorn

# Production command
CMD ["gunicorn", "fastapi_mcp_server:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:3000", "--access-logfile", "-", "--error-logfile", "-"]

# Development stage
FROM base as development

# Install development dependencies
RUN pip install pytest pytest-asyncio httpx

ENV ENVIRONMENT=development

# Development command with hot reload
CMD ["python", "fastapi_mcp_server.py"]