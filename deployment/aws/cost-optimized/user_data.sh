#!/bin/bash

# EC2 用户数据脚本 - 自动配置 isA MCP 环境
set -e

PROJECT_NAME="${project_name}"
AWS_REGION="${aws_region}"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a /var/log/isa-mcp-setup.log
}

log "开始设置 isA MCP 环境..."

# 更新系统
log "更新系统包..."
yum update -y

# 安装必要软件
log "安装 Docker 和其他必要软件..."
yum install -y docker git jq awscli

# 安装 Docker Compose
log "安装 Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 启动 Docker
log "启动 Docker 服务..."
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# 创建项目目录
log "创建项目目录..."
mkdir -p /home/ec2-user/isa-mcp
cd /home/ec2-user/isa-mcp

# 创建环境变量文件
log "创建环境变量文件..."
cat > .env << 'EOF'
# 这些值将从 AWS Secrets Manager 获取
NODE_ENV=production
PYTHONPATH=/app
PYTHONUNBUFFERED=1
DISPLAY=:99
# 其他环境变量将在运行时从 Secrets Manager 加载
EOF

# 创建 Docker Compose 文件
log "创建 Docker Compose 配置..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # MCP 服务器
  isa_mcp:
    image: your-account.dkr.ecr.us-east-1.amazonaws.com/isa-mcp:latest
    ports:
      - "8081:8081"
    environment:
      - NODE_ENV=production
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
      - DISPLAY=:99
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 用户服务
  isa_user_service:
    image: your-account.dkr.ecr.us-east-1.amazonaws.com/isa-user-service:latest
    ports:
      - "8100:8100"
    environment:
      - NODE_ENV=production
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 事件服务
  isa_event_service:
    image: your-account.dkr.ecr.us-east-1.amazonaws.com/isa-event-service:latest
    ports:
      - "8101:8101"
    environment:
      - NODE_ENV=production
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8101/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - isa_mcp
      - isa_user_service
      - isa_event_service
    restart: unless-stopped

networks:
  default:
    name: isa-mcp-network
EOF

# 创建 Nginx 配置
log "创建 Nginx 配置..."
cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream mcp_server {
        server isa_mcp:8081;
    }
    
    upstream user_service {
        server isa_user_service:8100;
    }
    
    upstream event_service {
        server isa_event_service:8101;
    }

    server {
        listen 80;
        server_name _;

        # MCP 服务路由
        location /mcp/ {
            proxy_pass http://mcp_server/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 用户服务路由
        location ~ ^/(api/users|api/auth|api/billing)/ {
            proxy_pass http://user_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 事件服务路由
        location ~ ^/(api/events|api/analytics)/ {
            proxy_pass http://event_service;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 健康检查
        location /health {
            return 200 'OK';
            add_header Content-Type text/plain;
        }

        # 默认路由到 MCP 服务
        location / {
            proxy_pass http://mcp_server;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# 创建部署脚本
log "创建部署脚本..."
cat > deploy.sh << 'EOF'
#!/bin/bash

# 简单部署脚本
set -e

AWS_REGION="us-east-1"
PROJECT_NAME="isa-mcp"

echo "获取 AWS 账户 ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "登录 ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "拉取最新镜像..."
docker-compose pull

echo "停止现有服务..."
docker-compose down

echo "启动服务..."
docker-compose up -d

echo "检查服务状态..."
docker-compose ps

echo "部署完成！"
echo "访问地址: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
EOF

chmod +x deploy.sh

# 创建 secrets 获取脚本
log "创建 secrets 获取脚本..."
cat > load-secrets.sh << 'EOF'
#!/bin/bash

# 从 AWS Secrets Manager 加载密钥到环境变量
PROJECT_NAME="isa-mcp"
AWS_REGION="us-east-1"

# 函数：获取密钥值
get_secret() {
    local secret_name=$1
    aws secretsmanager get-secret-value \
        --secret-id "$PROJECT_NAME/$secret_name" \
        --region "$AWS_REGION" \
        --query SecretString \
        --output text 2>/dev/null || echo ""
}

# 加载所有密钥
export DATABASE_URL=$(get_secret "database-url")
export REDIS_URL=$(get_secret "redis-url")
export JWT_SECRET_KEY=$(get_secret "jwt-secret")
export NEXT_PUBLIC_SUPABASE_URL=$(get_secret "supabase-url")
export SUPABASE_SERVICE_ROLE_KEY=$(get_secret "supabase-service-key")
export AUTH0_DOMAIN=$(get_secret "auth0-domain")
export AUTH0_AUDIENCE=$(get_secret "auth0-audience")
export AUTH0_CLIENT_ID=$(get_secret "auth0-client-id")
export AUTH0_CLIENT_SECRET=$(get_secret "auth0-client-secret")
export STRIPE_SECRET_KEY=$(get_secret "stripe-secret-key")
export STRIPE_WEBHOOK_SECRET=$(get_secret "stripe-webhook-secret")

# 导出到 .env 文件
cat > .env << END_ENV
NODE_ENV=production
PYTHONPATH=/app
PYTHONUNBUFFERED=1
DISPLAY=:99
DATABASE_URL=$DATABASE_URL
REDIS_URL=$REDIS_URL
JWT_SECRET_KEY=$JWT_SECRET_KEY
NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY
AUTH0_DOMAIN=$AUTH0_DOMAIN
AUTH0_AUDIENCE=$AUTH0_AUDIENCE
AUTH0_CLIENT_ID=$AUTH0_CLIENT_ID
AUTH0_CLIENT_SECRET=$AUTH0_CLIENT_SECRET
STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET
END_ENV

echo "密钥已加载到 .env 文件"
EOF

chmod +x load-secrets.sh

# 设置文件所有权
chown -R ec2-user:ec2-user /home/ec2-user/isa-mcp

log "isA MCP 环境设置完成！"
log "登录后运行: cd /home/ec2-user/isa-mcp && ./load-secrets.sh && ./deploy.sh"