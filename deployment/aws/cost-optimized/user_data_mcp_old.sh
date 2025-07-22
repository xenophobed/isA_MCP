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

# Create application directory
mkdir -p /opt/${project_name}
cd /opt/${project_name}

# Clone repository (placeholder - update with actual repo)
# git clone https://github.com/your-org/isA_MCP.git .

# Create basic environment file
cat > .env << EOF
# AWS Configuration
AWS_REGION=${aws_region}
NODE_ENV=production

# Services Configuration - MCP Services Instance
MCP_SERVICE_URL=http://localhost:8081
USER_SERVICE_URL=http://localhost:8100
EVENT_SERVICE_URL=http://localhost:8101

# External Services (will be updated with actual IPs)
MODEL_SERVICE_URL=http://MODEL_EC2_PRIVATE_IP:8082
AGENT_SERVICE_URL=http://AGENT_EC2_PRIVATE_IP:8080

# Database Configuration (Supabase Cloud - Staging)
SUPABASE_URL=https://bsvstczwobwxozzmykhx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJzdnN0Y3p3b2J3eG96em15a2h4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzA5NDIzMiwiZXhwIjoyMDY4NjcwMjMyfQ.X6Yx9-St40iRvzpUbVEJ025scL5LotCpKxcZ9Jbv-GY

# Authentication (Auth0) - Placeholder
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret

# Payment (Stripe) - Placeholder
STRIPE_SECRET_KEY=sk_live_your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret

# Feature Flags
REQUIRE_AUTH=true
DEBUG=false
ENABLE_ANALYTICS=true
EOF

# Create basic docker-compose for MCP services
cat > docker-compose.yml << EOF
version: '3.8'

services:
  mcp-service:
    image: ${project_name}/mcp-service:latest
    ports:
      - "8081:8081"
    environment:
      - PORT=8081
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  user-service:
    image: ${project_name}/user-service:latest
    ports:
      - "8100:8100"
    environment:
      - PORT=8100
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  event-service:
    image: ${project_name}/event-service:latest
    ports:
      - "8101:8101"
    environment:
      - PORT=8101
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8101/health"]
      interval: 30s
      timeout: 10s
      retries: 3
EOF

# Set proper permissions
chown -R ec2-user:ec2-user /opt/${project_name}

# Create systemd service for auto-start
cat > /etc/systemd/system/${project_name}-mcp.service << EOF
[Unit]
Description=${project_name} MCP Services
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
systemctl enable ${project_name}-mcp.service

# Log completion
echo "MCP Services instance initialization completed at $(date)" >> /var/log/user-data.log