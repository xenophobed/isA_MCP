# Multi-Service Container for isA Platform
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    supervisor \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy current MCP service
COPY . /app/services/mcp/

# Copy external services (these will be mounted during development)
# Agent service will be at /app/services/agent/
# Model service will be at /app/services/model/

# Install Python dependencies for all services
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Additional dependencies for agent service
RUN pip install langgraph langsmith

# Additional dependencies for model service  
RUN pip install modal replicate

# Copy supervisor configuration
COPY deployment/unified/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY deployment/unified/start-services.sh /app/start-services.sh
RUN chmod +x /app/start-services.sh

# Create logs directory
RUN mkdir -p /app/logs

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose all service ports
EXPOSE 8080 8081 8082 8100

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Start all services
CMD ["/app/start-services.sh"]