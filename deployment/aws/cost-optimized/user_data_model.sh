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

# Install Git
yum install -y git

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Install Python 3.9+ for AI/ML workloads
amazon-linux-extras install python3.8 -y
pip3 install --upgrade pip

# Create application directory
mkdir -p /opt/${project_name}
cd /opt/${project_name}

# Clone repository (placeholder - update with actual repo)
# git clone https://github.com/your-org/isA_MCP.git .

# Create basic environment file for Model service
cat > .env << EOF
# Environment Configuration
ISA_ENV=staging
AWS_REGION=${aws_region}

# Port Configuration  
PORT=8082

# Database Configuration (Supabase Cloud - Staging)
SUPABASE_URL=https://bsvstczwobwxozzmykhx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJzdnN0Y3p3b2J3eG96em15a2h4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzA5NDIzMiwiZXhwIjoyMDY4NjcwMjMyfQ.X6Yx9-St40iRvzpUbVEJ025scL5LotCpKxcZ9Jbv-GY

# AI/ML Provider Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_BASE=https://api.openai.com/v1
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_API_KEY=your-google-api-key
REPLICATE_API_TOKEN=your-replicate-token
HF_TOKEN=your-huggingface-token

# Logging Configuration
LOG_LEVEL=INFO
VERBOSE_LOGGING=false

# Feature Flags
DEBUG=false
ENABLE_ANALYTICS=true
EOF

# Create requirements.txt for Model service
cat > requirements.txt << EOF
fastapi>=0.100.0
uvicorn>=0.23.0
python-dotenv>=1.0.0
pydantic>=2.0.0
httpx>=0.24.0
aiofiles>=23.0.0
supabase>=2.0.0
openai>=1.0.0
anthropic>=0.20.0
google-generativeai>=0.3.0
replicate>=0.15.0
transformers>=4.30.0
torch>=2.0.0
requests>=2.31.0
pyyaml>=6.0.0
python-multipart>=0.0.6
EOF

# Create Dockerfile for Model service
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

# Create directories
RUN mkdir -p /app/logs /app/models

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8082/health || exit 1

# Start command
CMD ["uvicorn", "isa_model.serving.api.fastapi_server:app", "--host", "0.0.0.0", "--port", "8082"]
EOF

# Create docker-compose for Model service
cat > docker-compose.yml << EOF
version: '3.8'

services:
  model-service:
    build: .
    ports:
      - "8082:8082"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
EOF

# Set proper permissions
chown -R ec2-user:ec2-user /opt/${project_name}

# Create systemd service for auto-start
cat > /etc/systemd/system/${project_name}-model.service << EOF
[Unit]
Description=${project_name} Model Service
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
systemctl enable ${project_name}-model.service

# Log completion
echo "Model Service instance initialization completed at $(date)" >> /var/log/user-data.log