"""
模板引擎原子服务
提供简单的模板渲染功能
"""

import os
import re
import json
from typing import Dict, Any, Optional
from datetime import datetime


class TemplateEngine:
    """模板引擎原子服务"""
    
    def __init__(self):
        self.templates = {}
        self._load_builtin_templates()
    
    def render_template(self, template_name: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """渲染模板"""
        try:
            if template_name not in self.templates:
                return {
                    "success": False,
                    "error": f"Template '{template_name}' not found",
                    "available_templates": list(self.templates.keys())
                }
            
            template_content = self.templates[template_name]
            rendered_content = self._render_content(template_content, variables)
            
            return {
                "success": True,
                "template_name": template_name,
                "rendered_content": rendered_content,
                "variables_used": list(variables.keys()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "template_name": template_name
            }
    
    def load_template(self, file_path: str, template_name: Optional[str] = None) -> Dict[str, Any]:
        """从文件加载模板"""
        try:
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"Template file '{file_path}' not found",
                    "file_path": file_path
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            name = template_name or os.path.basename(file_path)
            self.templates[name] = content
            
            return {
                "success": True,
                "template_name": name,
                "file_path": file_path,
                "content_length": len(content),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def register_template(self, template_name: str, content: str) -> Dict[str, Any]:
        """注册模板内容"""
        try:
            self.templates[template_name] = content
            
            return {
                "success": True,
                "template_name": template_name,
                "content_length": len(content),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "template_name": template_name
            }
    
    def list_templates(self) -> Dict[str, Any]:
        """列出所有可用模板"""
        try:
            template_info = []
            for name, content in self.templates.items():
                # 提取模板中的变量
                variables = self._extract_variables(content)
                
                template_info.append({
                    "name": name,
                    "content_length": len(content),
                    "variables": variables,
                    "is_builtin": name in self._get_builtin_template_names()
                })
            
            return {
                "success": True,
                "template_count": len(template_info),
                "templates": template_info,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _render_content(self, content: str, variables: Dict[str, Any]) -> str:
        """渲染内容"""
        # 替换 {variable} 格式的变量
        def replace_variable(match):
            var_name = match.group(1)
            if var_name in variables:
                value = variables[var_name]
                # 如果值是字典或列表，转换为JSON
                if isinstance(value, (dict, list)):
                    return json.dumps(value, indent=2)
                return str(value)
            else:
                # 保留原始格式如果变量不存在
                return match.group(0)
        
        # 使用正则表达式替换变量
        rendered = re.sub(r'\\{([^}]+)\\}', replace_variable, content)
        
        return rendered
    
    def _extract_variables(self, content: str) -> list:
        """提取模板中的变量"""
        # 查找所有 {variable} 格式的变量
        variables = re.findall(r'\\{([^}]+)\\}', content)
        return list(set(variables))  # 去重
    
    def _load_builtin_templates(self):
        """加载内置模板"""
        
        # Flask应用模板
        self.templates["flask_app"] = '''#!/usr/bin/env python3
"""
{app_name} - Flask Application
Generated: {timestamp}
"""

from flask import Flask, jsonify, request, render_template
import os
import logging
from datetime import datetime

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '{secret_key}')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    """主页"""
    return render_template('index.html', 
                         app_name="{app_name}",
                         description="{description}")

@app.route('/health')
def health():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "app_name": "{app_name}"
    })

@app.route('/api/info')
def api_info():
    """API信息"""
    return jsonify({
        "app_name": "{app_name}",
        "description": "{description}",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })

{custom_routes}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', {port}))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting {app_name} on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
'''

        # HTML模板
        self.templates["html_index"] = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{app_name}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        .description {
            text-align: center;
            font-size: 18px;
            color: #7f8c8d;
            margin-bottom: 40px;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .feature {
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .api-info {
            background: #e8f5e8;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            color: #95a5a6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>{app_name}</h1>
        <div class="description">
            {description}
        </div>
        
        <div class="features">
            <div class="feature">
                <h3>🚀 Quick Start</h3>
                <p>Your application is up and running! This is a fully functional web application generated automatically.</p>
            </div>
            <div class="feature">
                <h3>🛠️ Built with Flask</h3>
                <p>Powered by Flask framework with modern Python practices and best security standards.</p>
            </div>
            <div class="feature">
                <h3>📱 Responsive Design</h3>
                <p>Mobile-friendly design that works great on all devices and screen sizes.</p>
            </div>
            <div class="feature">
                <h3>🔧 Easy to Customize</h3>
                <p>Clean, well-structured code that's easy to modify and extend for your needs.</p>
            </div>
        </div>
        
        <div class="api-info">
            <h3>📡 API Endpoints</h3>
            <ul>
                <li><strong>GET /</strong> - This homepage</li>
                <li><strong>GET /health</strong> - Health check endpoint</li>
                <li><strong>GET /api/info</strong> - Application information</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>Generated by QuickApp Service • {timestamp}</p>
        </div>
    </div>
    
    <script>
        // Add some basic interactivity
        document.addEventListener('DOMContentLoaded', function() {
            console.log('{app_name} loaded successfully!');
            
            // Add click animations to features
            const features = document.querySelectorAll('.feature');
            features.forEach(feature => {
                feature.addEventListener('click', function() {
                    this.style.transform = 'scale(1.05)';
                    setTimeout(() => {
                        this.style.transform = 'scale(1)';
                    }, 200);
                });
            });
        });
    </script>
</body>
</html>
'''

        # Dockerfile模板
        self.templates["dockerfile"] = '''FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/logs && chown -R app:app /app

# 切换到非root用户
USER app

# 暴露端口
EXPOSE {port}

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{port}/health || exit 1

# 启动命令
CMD ["python", "app.py"]
'''

        # requirements.txt模板
        self.templates["requirements"] = '''Flask==2.3.3
Werkzeug==2.3.7
Jinja2==3.1.2
MarkupSafe==2.1.3
itsdangerous==2.1.2
click==8.1.7
blinker==1.6.3
python-dotenv==1.0.0
gunicorn==21.2.0
psutil==5.9.6
{additional_requirements}
'''

        # docker-compose.yml模板
        self.templates["docker_compose"] = '''version: '3.8'

services:
  {app_name}:
    build: .
    container_name: {app_name}_app
    ports:
      - "{port}:{port}"
    environment:
      - PORT={port}
      - DEBUG=false
      - SECRET_KEY={secret_key}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  default:
    name: {app_name}_network
'''

        # 启动脚本模板
        self.templates["start_script"] = '''#!/bin/bash

# {app_name} 启动脚本
# 生成时间: {timestamp}

set -e

APP_NAME="{app_name}"
PORT={port}

echo "🚀 启动 $APP_NAME"
echo "📅 时间: $(date)"
echo "🔧 端口: $PORT"
echo ""

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

# 检查端口是否被占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口 $PORT 已被占用"
    echo "请检查是否有其他服务在使用此端口"
    echo ""
    echo "当前占用端口的进程:"
    lsof -Pi :$PORT -sTCP:LISTEN
    exit 1
fi

# 构建镜像
echo "🔨 构建 Docker 镜像..."
docker build -t $APP_NAME:latest .

if [ $? -ne 0 ]; then
    echo "❌ 镜像构建失败"
    exit 1
fi

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ 服务启动失败"
    exit 1
fi

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 显示访问信息
echo ""
echo "✅ $APP_NAME 启动成功!"
echo ""
echo "🌐 访问地址:"
echo "   主页: http://localhost:$PORT"
echo "   健康检查: http://localhost:$PORT/health"
echo "   API信息: http://localhost:$PORT/api/info"
echo ""
echo "📋 管理命令:"
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
echo ""
'''

    def _get_builtin_template_names(self) -> list:
        """获取内置模板名称列表"""
        return [
            "flask_app",
            "html_index", 
            "dockerfile",
            "requirements",
            "docker_compose",
            "start_script"
        ]