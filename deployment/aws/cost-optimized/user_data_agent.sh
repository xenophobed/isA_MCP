#!/bin/bash

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Git and Python
yum install -y git python3 python3-pip

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Create application directory
mkdir -p /opt/${project_name}
cd /opt/${project_name}

# Clone repository (placeholder - update with actual repo)
# git clone https://github.com/your-org/isA_Agent.git .

# Create Agent service environment file with proper service discovery
cat > .env << EOF
# Environment Configuration
ENVIRONMENT=staging
AWS_REGION=${aws_region}

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080
API_DEBUG=false

# ISA Model Service Configuration
ISA_MODE=api
ISA_API_URL=http://${model_private_ip}:8082

# MCP Server Configuration  
MCP_SERVER_URL=http://${mcp_private_ip}:8081/mcp/

# Database Configuration (Supabase Cloud - Staging)
SUPABASE_CLOUD_URL=https://bsvstczwobwxozzmykhx.supabase.co
SUPABASE_CLOUD_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJzdnN0Y3p3b2J3eG96em15a2h4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzA5NDIzMiwiZXhwIjoyMDY4NjcwMjMyfQ.X6Yx9-St40iRvzpUbVEJ025scL5LotCpKxcZ9Jbv-GY

# AI Configuration
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
AI_TEMPERATURE=0

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Security
API_MASTER_KEY=your-api-master-key
CORS_ORIGINS=*

# Feature Flags
DEBUG=false
ENABLE_ANALYTICS=true
EOF

# Create requirements.txt for Agent service
cat > requirements.txt << EOF
fastapi>=0.100.0
uvicorn>=0.23.0
python-dotenv>=1.0.0
httpx>=0.24.0
pydantic>=2.0.0
aiofiles>=23.0.0
supabase>=2.0.0
python-multipart>=0.0.6
langgraph>=0.2.0
langchain>=0.2.0
anthropic>=0.20.0
openai>=1.0.0
requests>=2.31.0
EOF

# Create simple Dockerfile for Agent service
cat > Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8080/health || exit 1

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

# Create docker-compose for Agent service
cat > docker-compose.yml << EOF
version: '3.8'

services:
  agent-service:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - ./logs:/app/logs
      - ./storage:/app/storage
EOF

# Set proper permissions
chown -R ec2-user:ec2-user /opt/${project_name}

# Create systemd service for auto-start
cat > /etc/systemd/system/${project_name}-agent.service << EOF
[Unit]
Description=${project_name} Agent Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/${project_name}
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ec2-user

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl enable ${project_name}-agent.service

# Log completion
echo "Agent Service instance initialization completed at $(date)" >> /var/log/user-data.log