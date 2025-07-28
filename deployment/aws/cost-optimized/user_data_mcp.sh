#!/bin/bash

# 更新系统
yum update -y

# 安装Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 安装Git和其他依赖
yum install -y git python3 python3-pip

# 安装X11和GUI支持 (for Playwright)
yum install -y xorg-x11-server-Xvfb xorg-x11-xauth xorg-x11-utils xorg-x11-xinit
yum install -y chromium firefox

# 安装额外的开发工具
yum groupinstall -y "Development Tools"

# 安装AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# 创建应用目录
mkdir -p /opt/${project_name}
cd /opt/${project_name}

# Clone MCP repository  
git clone https://github.com/xenodennis/isA_MCP.git .
git checkout develop || git checkout main

# 创建MCP服务的环境配置
cat > .env << EOF
# Environment Configuration  
ENV=staging
AWS_REGION=${aws_region}
NODE_ENV=production
PYTHONPATH=/app
PYTHONUNBUFFERED=1

# MCP Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=8081
MCP_SERVER_NAME=Enhanced Secure MCP Server

# ISA Model Service Configuration
ISA_SERVICE_URL=http://${model_private_ip}:8082
ISA_API_KEY=your-model-service-api-key
REQUIRE_ISA_AUTH=false

# Database Configuration (Supabase Cloud - Staging)
SUPABASE_CLOUD_URL=https://bsvstczwobwxozzmykhx.supabase.co
SUPABASE_CLOUD_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJzdnN0Y3p3b2J3eG96em15a2h4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzA5NDIzMiwiZXhwIjoyMDY4NjcwMjMyfQ.X6Yx9-St40iRvzpUbVEJ025scL5LotCpKxcZ9Jbv-GY

# Security Configuration
MCP_REQUIRE_AUTH=false
MCP_SECURITY_REQUIRE_AUTHORIZATION=true
MCP_SECURITY_AUTO_APPROVE_LOW=true

# Logging Configuration
MCP_LOG_LOG_LEVEL=INFO
MCP_LOG_LOG_FILE=mcp_server.log

# UI and Browser Configuration
DISPLAY=:99
PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers

# External API Keys (需要后续配置)
OPENWEATHER_API_KEY=your-openweather-key
OPENAI_API_KEY=your-openai-key
BRAVE_TOKEN=your-brave-search-key

# Feature Flags
DEBUG=false
ENABLE_ANALYTICS=true
EOF

# 创建requirements.txt for MCP service
cat > requirements.txt << EOF
mcp>=1.0.0
supabase>=2.0.0
python-dotenv>=1.0.0
requests>=2.31.0
openai>=1.0.0
anthropic>=0.20.0
psycopg2-binary>=2.9.0
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
httpx>=0.24.0
aiofiles>=23.0.0
python-multipart>=0.0.6
playwright>=1.40.0
beautifulsoup4>=4.12.0
selenium>=4.15.0
EOF

# 创建MCP服务的Dockerfile with UI support
cat > Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖 (including GUI support)
RUN apt-get update && apt-get install -y \\
    curl \\
    git \\
    xvfb \\
    chromium \\
    firefox-esr \\
    fonts-liberation \\
    libasound2 \\
    libatk-bridge2.0-0 \\
    libdrm2 \\
    libxcomposite1 \\
    libxdamage1 \\
    libxrandr2 \\
    libgbm1 \\
    libxss1 \\
    libnss3 \\
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装Playwright browsers
RUN playwright install chromium
RUN playwright install firefox

# 复制MCP服务代码
COPY . .

# 创建目录
RUN mkdir -p /app/logs /app/data

# 暴露端口
EXPOSE 8081

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8081/health || exit 1

# 启动脚本
COPY start_mcp.sh /app/start_mcp.sh
RUN chmod +x /app/start_mcp.sh

# 启动命令
CMD ["/app/start_mcp.sh"]
EOF

# 创建MCP启动脚本
cat > start_mcp.sh << 'EOF'
#!/bin/bash

# 启动Xvfb for headless UI support
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

# 等待Xvfb启动
sleep 3

# 启动MCP服务器和其他服务
python smart_mcp_server.py --port 8081 &

# 启动User Service (8100端口)
cd tools/services/user_service && python -m uvicorn api_server:app --host 0.0.0.0 --port 8100 &

# 启动Event Service (8101端口)  
cd ../event_service && python -m uvicorn main:app --host 0.0.0.0 --port 8101 &

# 等待所有服务启动
wait
EOF

chmod +x start_mcp.sh

# 创建docker-compose for MCP service
cat > docker-compose.yml << EOF
version: '3.8'

services:
  mcp-service:
    build: .
    ports:
      - "8081:8081"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
    environment:
      - DISPLAY=:99
    privileged: true
    cap_add:
      - SYS_ADMIN
    security_opt:
      - seccomp:unconfined

  xvfb:
    image: jlesage/docker-xvfb:latest
    restart: unless-stopped
    environment:
      - DISPLAY_WIDTH=1920
      - DISPLAY_HEIGHT=1080
      - VNC_PASSWORD=password123
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
    ports:
      - "5900:5900"  # VNC port for remote access if needed
EOF

# 创建健康检查脚本
cat > health_check.py << 'EOF'
#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "mcp", "ui_support": true}')
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server():
    server = HTTPServer(('0.0.0.0', 8081), HealthHandler)
    server.serve_forever()

if __name__ == '__main__':
    start_health_server()
EOF

chmod +x health_check.py

# 创建日志和数据目录
mkdir -p logs data

# 设置权限
chown -R ec2-user:ec2-user /opt/${project_name}

# 创建systemd服务
cat > /etc/systemd/system/${project_name}-mcp.service << EOF
[Unit]
Description=${project_name} MCP Server with UI Support
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

# 启用服务
systemctl enable ${project_name}-mcp.service

# 启动Xvfb服务
cat > /etc/systemd/system/xvfb.service << EOF
[Unit]
Description=X Virtual Framebuffer for headless applications
After=network.target

[Service]
Type=simple
User=ec2-user
ExecStart=/usr/bin/Xvfb :99 -screen 0 1920x1080x24
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable xvfb.service
systemctl start xvfb.service

# 启动健康检查服务（临时的，直到真正的MCP服务部署）
nohup python3 /opt/${project_name}/health_check.py > /opt/${project_name}/logs/health.log 2>&1 &

# 记录完成
echo "MCP Server with UI support initialization completed at $(date)" >> /var/log/user-data.log
echo "MCP服务初始化完成，支持Playwright和UI操作，等待代码部署..." >> /opt/${project_name}/logs/init.log