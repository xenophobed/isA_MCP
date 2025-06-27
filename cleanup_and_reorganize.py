#!/usr/bin/env python3
"""
项目清理和重组脚本
清理不需要的文件，重组目录结构，为生产部署做准备
"""
import os
import shutil
from pathlib import Path

def cleanup_and_reorganize():
    """清理和重组项目结构"""
    print("🧹 开始清理和重组项目结构...")
    
    # 当前目录
    root_dir = Path.cwd()
    
    # 1. 删除不需要的文件和目录
    print("\n1. 删除不需要的文件...")
    
    files_to_delete = [
        # 测试和调试文件
        "fix_missing_embeddings.py",
        "test_vector_search_debug.py", 
        "mcp_server.log",
        
        # 重复的Dockerfile
        "Dockerfile.graphrag",
        "Dockerfile.rag",
        
        # 旧的配置文件
        "config.yaml",
        "setup.py",
        "pyproject.toml",
    ]
    
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"   ✅ 删除: {file_path}")
    
    # 删除不需要的目录
    dirs_to_delete = [
        "generated_images",
        "screenshots", 
        "sessions",
        "scripts",
        "models",
        "logs",  # 生产环境会用新的日志系统
    ]
    
    for dir_path in dirs_to_delete:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"   ✅ 删除目录: {dir_path}")
    
    # 2. 重组目录结构
    print("\n2. 重组目录结构...")
    
    # 创建生产环境目录结构
    production_dirs = [
        "deployment/production",
        "deployment/staging", 
        "deployment/development",
        "config",
        "scripts/deployment",
        "scripts/maintenance",
        "tests/integration",
        "tests/unit",
        "monitoring/dashboards",
        "monitoring/alerts",
    ]
    
    for dir_path in production_dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"   ✅ 创建目录: {dir_path}")
    
    # 3. 移动文件到正确位置
    print("\n3. 移动文件到正确位置...")
    
    # 移动部署相关文件
    moves = [
        ("production_setup.py", "scripts/deployment/"),
        ("production_schema.sql", "deployment/production/"),
        ("requirements.production.txt", "deployment/production/"),
        ("Dockerfile.production", "deployment/production/"),
        ("monitoring/prometheus.yml", "monitoring/"),
    ]
    
    for src, dst_dir in moves:
        if os.path.exists(src):
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(src))
            shutil.move(src, dst)
            print(f"   ✅ 移动: {src} → {dst}")
    
    # 4. 重命名主要文件
    print("\n4. 重命名主要文件...")
    
    renames = [
        ("Dockerfile", "deployment/production/Dockerfile"),
        ("docker-compose.yml", "deployment/development/docker-compose.yml"),
    ]
    
    for src, dst in renames:
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            print(f"   ✅ 重命名: {src} → {dst}")
    
    # 5. 创建生产环境配置文件
    print("\n5. 创建生产环境配置文件...")
    
    # 生产环境的docker-compose文件
    production_compose = """version: '3.8'

services:
  mcp-service:
    build:
      context: ../../
      dockerfile: deployment/production/Dockerfile.production
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    ports:
      - "4321:4321"
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4321/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl/certs:ro
    depends_on:
      - mcp-service
    restart: unless-stopped

volumes:
  redis_data:
"""
    
    with open("deployment/production/docker-compose.yml", "w") as f:
        f.write(production_compose)
    print("   ✅ 创建: deployment/production/docker-compose.yml")
    
    # 6. 清理测试文件位置
    print("\n6. 重组测试文件...")
    
    # 移动测试文件到正确位置
    test_moves = [
        ("tools/tests/test_rag.py", "tests/unit/"),
        ("tools/tests/test_memory.py", "tests/unit/"),
        ("tools/tests/test_image_gen.py", "tests/unit/"),
        ("tools/tests/test_shopify.py", "tests/unit/"),
        ("tools/tests/test_web_login.py", "tests/unit/"),
    ]
    
    for src, dst_dir in test_moves:
        if os.path.exists(src):
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(src))
            shutil.move(src, dst)
            print(f"   ✅ 移动测试: {src} → {dst}")
    
    # 删除空的tests目录
    if os.path.exists("tools/tests") and not os.listdir("tools/tests"):
        os.rmdir("tools/tests")
        print("   ✅ 删除空目录: tools/tests")
    
    # 7. 创建项目配置文件
    print("\n7. 创建项目配置文件...")
    
    # 创建生产就绪的requirements.txt
    requirements_content = """# Core dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
httpx>=0.25.0

# Database
supabase>=1.0.0
asyncpg>=0.29.0
SQLAlchemy>=2.0.0

# AI and ML
sentence-transformers>=2.2.0
openai>=1.0.0
tiktoken>=0.5.0

# Web automation
playwright>=1.40.0
beautifulsoup4>=4.12.0
selenium>=4.15.0

# Security and Auth
cryptography>=41.0.0
PyJWT>=2.8.0
bcrypt>=4.1.0
passlib>=1.7.0

# Monitoring and Logging
structlog>=23.2.0
prometheus-client>=0.19.0
sentry-sdk>=1.38.0

# Redis and Caching
redis>=5.0.0
hiredis>=2.2.0

# Image processing
Pillow>=10.0.0
opencv-python>=4.8.0

# Utilities
python-dotenv>=1.0.0
pyyaml>=6.0
click>=8.1.0
rich>=13.6.0
"""
    
    with open("requirements.txt", "w") as f:
        f.write(requirements_content)
    print("   ✅ 更新: requirements.txt")
    
    # 8. 创建启动脚本
    print("\n8. 创建启动脚本...")
    
    start_script = """#!/bin/bash
# 生产环境启动脚本

set -e

echo "🚀 启动MCP智能服务 (生产环境)"

# 检查环境变量
if [ -z "$DATABASE_URL" ]; then
    echo "❌ 错误: DATABASE_URL 环境变量未设置"
    exit 1
fi

# 启动服务
echo "📦 启动服务容器..."
cd deployment/production
docker-compose up -d

# 健康检查
echo "🔍 检查服务健康状态..."
sleep 30

if curl -f http://localhost:4321/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo "🌐 服务地址: http://localhost:4321"
    echo "📊 监控地址: http://localhost:3000"
else
    echo "❌ 服务启动失败"
    docker-compose logs mcp-service
    exit 1
fi
"""
    
    with open("scripts/deployment/start_production.sh", "w") as f:
        f.write(start_script)
    os.chmod("scripts/deployment/start_production.sh", 0o755)
    print("   ✅ 创建: scripts/deployment/start_production.sh")
    
    # 9. 更新.gitignore
    print("\n9. 更新.gitignore...")
    
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv/

# Environment variables
.env
.env.local
.env.production
.env.staging

# Database
*.db
*.sqlite
*.sqlite3

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.docker/

# Temporary files
tmp/
temp/
sessions/
screenshots/
generated_images/

# Production secrets
ssl/
secrets/
"""
    
    with open(".gitignore", "w") as f:
        f.write(gitignore_content)
    print("   ✅ 更新: .gitignore")
    
    print("\n🎉 项目清理和重组完成！")
    print("\n📁 新的项目结构:")
    print("├── core/                    # 核心模块")
    print("├── tools/                   # 工具模块") 
    print("├── resources/               # 资源管理")
    print("├── prompts/                 # 提示词")
    print("├── deployment/              # 部署配置")
    print("│   ├── production/          # 生产环境")
    print("│   ├── staging/             # 测试环境")
    print("│   └── development/         # 开发环境")
    print("├── scripts/                 # 脚本工具")
    print("│   ├── deployment/          # 部署脚本")
    print("│   └── maintenance/         # 维护脚本")
    print("├── tests/                   # 测试文件")
    print("│   ├── unit/                # 单元测试")
    print("│   └── integration/         # 集成测试")
    print("├── monitoring/              # 监控配置")
    print("├── docs/                    # 文档")
    print("└── smart_mcp_server.py      # 主服务文件")

if __name__ == "__main__":
    cleanup_and_reorganize()