# Linux服务器部署工作流

## 概述

在一台Linux服务器上通过Terminal Service实现完整的开发部署流程，包括项目创建、代码编写、数据库部署、Web服务器配置和应用服务部署。

## 🎯 核心功能

### 完整的服务器操作流程
- **📁 项目工作空间管理**: 创建项目目录结构
- **📝 代码文件操作**: 创建和编辑代码文件
- **🗄️ 数据库部署**: PostgreSQL、MySQL、MongoDB、Redis
- **🌐 Web服务器部署**: Nginx、Apache配置
- **🚀 应用服务部署**: Python、Node.js、Go应用
- **📊 服务监控**: 服务状态和系统监控

### 服务器目录结构
```
/home/projects/           # 项目开发目录
├── project1/
│   ├── src/             # 源代码
│   ├── config/          # 配置文件
│   ├── logs/            # 日志文件
│   └── tests/           # 测试文件
│
/opt/services/           # 服务部署目录
├── project1/
│   ├── database/        # 数据库数据
│   └── application/     # 应用服务
│
/etc/nginx/sites-available/ # Nginx配置
/etc/systemd/system/        # 系统服务
/var/log/deployed_services/ # 服务日志
```

## 🛠️ 使用示例

### 1. 创建项目工作空间

```python
# 创建一个Web项目工作空间
result = await server_tools.create_project_workspace(
    project_name="my-web-app",
    project_type="web",
    description="一个现代化的Web应用"
)

# 响应示例
{
  "status": "success",
  "data": {
    "project_name": "my-web-app",
    "project_path": "/home/projects/my-web-app",
    "project_type": "web",
    "structure": ["src", "config", "logs", "docs", "tests", "static", "templates", "assets"],
    "session_id": "project_my-web-app_abc12345"
  }
}
```

### 2. 创建代码文件

```python
# 创建Python主应用文件
result = await server_tools.create_code_file(
    project_name="my-web-app",
    file_path="src/main.py",
    file_content="""#!/usr/bin/env python3
from flask import Flask, render_template, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'running',
        'version': '1.0.0',
        'environment': os.getenv('ENVIRONMENT', 'development')
    })

@app.route('/api/users')
def get_users():
    # 这里可以连接数据库获取用户数据
    return jsonify({
        'users': [
            {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
            {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'}
        ]
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
""",
    file_type="python",
    executable=True
)
```

```python
# 创建HTML模板文件
result = await server_tools.create_code_file(
    project_name="my-web-app",
    file_path="templates/index.html",
    file_content="""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的Web应用</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .api-section { margin: 20px 0; padding: 20px; background: #f5f5f5; }
        button { background: #007bff; color: white; border: none; padding: 10px 20px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <h1>欢迎使用我的Web应用</h1>
        <p>这是一个通过Terminal Service部署的应用示例</p>
        
        <div class="api-section">
            <h3>API测试</h3>
            <button onclick="testStatus()">测试状态API</button>
            <button onclick="testUsers()">获取用户数据</button>
            <div id="result"></div>
        </div>
    </div>

    <script>
        async function testStatus() {
            const response = await fetch('/api/status');
            const data = await response.json();
            document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }

        async function testUsers() {
            const response = await fetch('/api/users');
            const data = await response.json();
            document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }
    </script>
</body>
</html>
""",
    file_type="html"
)
```

```python
# 创建依赖文件
result = await server_tools.create_code_file(
    project_name="my-web-app",
    file_path="requirements.txt",
    file_content="""Flask==2.3.3
psycopg2-binary==2.9.7
python-dotenv==1.0.0
gunicorn==21.2.0
""",
    file_type="config"
)
```

### 3. 部署数据库服务

```python
# 部署PostgreSQL数据库
result = await server_tools.deploy_database_service(
    project_name="my-web-app",
    db_type="postgresql",
    db_name="webapp_db",
    port=5432,
    username="webapp_user",
    # password会自动生成
)

# 响应示例
{
  "status": "success",
  "data": {
    "project_name": "my-web-app",
    "db_type": "postgresql",
    "db_name": "webapp_db",
    "port": 5432,
    "username": "webapp_user",
    "password": "pwd_a1b2c3d4e5f6",
    "connection_url": "postgresql://webapp_user:pwd_a1b2c3d4e5f6@localhost:5432/webapp_db",
    "service_name": "postgresql-my-web-app",
    "status": "running"
  }
}
```

### 4. 部署应用服务

```python
# 部署Python Flask应用
result = await server_tools.deploy_application_service(
    project_name="my-web-app",
    app_type="python",
    main_file="src/main.py",
    port=5000,
    environment={
        "ENVIRONMENT": "production",
        "DATABASE_URL": "postgresql://webapp_user:pwd_a1b2c3d4e5f6@localhost:5432/webapp_db",
        "SECRET_KEY": "your-secret-key-here"
    }
)

# 响应示例
{
  "status": "success",
  "data": {
    "project_name": "my-web-app",
    "app_type": "python",
    "main_file": "src/main.py",
    "port": 5000,
    "service_url": "http://192.168.1.100:5000",
    "service_name": "my-web-app-app",
    "systemd_file": "/etc/systemd/system/my-web-app-app.service",
    "status": "running",
    "logs_command": "sudo journalctl -f -u my-web-app-app"
  }
}
```

### 5. 部署Web服务器 (Nginx反向代理)

```python
# 部署Nginx作为反向代理
result = await server_tools.deploy_web_server(
    project_name="my-web-app",
    server_type="nginx",
    port=80,
    ssl_enabled=False,
    domain="192.168.1.100"  # 或者使用域名
)

# 响应示例
{
  "status": "success",
  "data": {
    "project_name": "my-web-app",
    "server_type": "nginx",
    "port": 80,
    "domain": "192.168.1.100",
    "ssl_enabled": false,
    "service_url": "http://192.168.1.100",
    "config_file": "/etc/nginx/sites-available/my-web-app",
    "service_name": "nginx-my-web-app",
    "status": "running"
  }
}
```

### 6. 查看服务器状态

```python
# 获取完整的服务器状态
result = await server_tools.get_server_status()

# 响应示例
{
  "status": "success",
  "data": {
    "system": {
      "hostname": "my-server",
      "os": "Ubuntu 22.04.3 LTS",
      "kernel": "5.15.0-83-generic",
      "uptime": "5 days, 12:34:56",
      "load_average": [0.15, 0.25, 0.30],
      "memory": {
        "total": "8GB",
        "used": "2.1GB",
        "free": "5.9GB"
      },
      "disk": {
        "total": "100GB",
        "used": "25GB",
        "free": "75GB"
      }
    },
    "services": [
      {
        "name": "my-web-app-app",
        "status": "active",
        "since": "2025-01-21 10:30:45"
      },
      {
        "name": "postgresql-my-web-app",
        "status": "active",
        "since": "2025-01-21 10:25:30"
      },
      {
        "name": "nginx",
        "status": "active",
        "since": "2025-01-21 10:35:12"
      }
    ],
    "projects": [
      {
        "name": "my-web-app",
        "path": "/home/projects/my-web-app",
        "type": "web",
        "files_count": 15,
        "size": "2.5MB"
      }
    ],
    "ports": [
      {"port": 80, "service": "nginx", "status": "listening"},
      {"port": 5000, "service": "my-web-app-app", "status": "listening"},
      {"port": 5432, "service": "postgresql", "status": "listening"}
    ]
  }
}
```

## 🔧 完整的部署流程

### 场景: 部署一个博客系统

```python
# 1. 创建项目
await server_tools.create_project_workspace(
    project_name="blog-system",
    project_type="web",
    description="个人博客系统"
)

# 2. 创建数据库模型文件
await server_tools.create_code_file(
    project_name="blog-system",
    file_path="src/models.py",
    file_content="""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 数据库连接
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/blog_db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)
""",
    file_type="python"
)

# 3. 创建主应用文件
await server_tools.create_code_file(
    project_name="blog-system",
    file_path="src/app.py",
    file_content="""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import Post, SessionLocal, create_tables
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# 初始化数据库
create_tables()

@app.route('/')
def index():
    db = SessionLocal()
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    db.close()
    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    db = SessionLocal()
    post = db.query(Post).filter(Post.id == post_id).first()
    db.close()
    if not post:
        flash('文章不存在')
        return redirect(url_for('index'))
    return render_template('post.html', post=post)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/admin/create', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form['author']
        
        db = SessionLocal()
        post = Post(title=title, content=content, author=author)
        db.add(post)
        db.commit()
        db.close()
        
        flash('文章创建成功!')
        return redirect(url_for('admin'))
    
    return render_template('create_post.html')

@app.route('/api/posts')
def api_posts():
    db = SessionLocal()
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    db.close()
    
    return jsonify([{
        'id': post.id,
        'title': post.title,
        'author': post.author,
        'created_at': post.created_at.isoformat()
    } for post in posts])

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
""",
    file_type="python",
    executable=True
)

# 4. 部署PostgreSQL数据库
await server_tools.deploy_database_service(
    project_name="blog-system",
    db_type="postgresql",
    db_name="blog_db",
    port=5433,  # 使用不同端口避免冲突
    username="blog_user"
)

# 5. 部署应用服务
await server_tools.deploy_application_service(
    project_name="blog-system",
    app_type="python",
    main_file="src/app.py",
    port=5001,
    environment={
        "ENVIRONMENT": "production",
        "DATABASE_URL": "postgresql://blog_user:generated_password@localhost:5433/blog_db",
        "SECRET_KEY": "blog-secret-key-2025"
    }
)

# 6. 配置Nginx反向代理
await server_tools.deploy_web_server(
    project_name="blog-system",
    server_type="nginx",
    port=8080,  # 使用8080端口
    ssl_enabled=False
)
```

## 🗂️ 支持的服务类型

### 数据库服务
- **PostgreSQL**: 全功能关系型数据库
- **MySQL**: 流行的关系型数据库
- **MongoDB**: NoSQL文档数据库
- **Redis**: 内存缓存数据库

### Web服务器
- **Nginx**: 高性能反向代理服务器
- **Apache**: 传统Web服务器

### 应用服务
- **Python**: Flask、Django、FastAPI应用
- **Node.js**: Express、Koa应用
- **Go**: 原生Go应用

## 🔒 安全特性

### 继承Terminal Service安全机制
- **命令验证**: 只允许安全的系统命令
- **权限控制**: 使用sudo进行权限提升
- **目录隔离**: 限制文件操作范围

### 服务安全
- **用户隔离**: 每个服务使用独立用户
- **端口管理**: 自动分配和管理端口
- **日志审计**: 完整的操作日志记录

## 📊 监控和管理

### 系统监控
```bash
# 查看服务状态
sudo systemctl status my-web-app-app

# 查看服务日志
sudo journalctl -f -u my-web-app-app

# 查看端口使用
sudo netstat -tulpn | grep LISTEN

# 查看资源使用
htop
df -h
free -h
```

### 服务管理命令
```bash
# 重启应用服务
sudo systemctl restart my-web-app-app

# 重载Nginx配置
sudo nginx -t && sudo systemctl reload nginx

# 查看数据库状态
docker ps | grep postgresql
```

## 🚀 扩展功能

### 负载均衡
可以部署多个应用实例并配置Nginx负载均衡:

```nginx
upstream blog_backend {
    server localhost:5001;
    server localhost:5002;
    server localhost:5003;
}

server {
    listen 80;
    location / {
        proxy_pass http://blog_backend;
    }
}
```

### SSL证书
自动配置Let's Encrypt SSL证书:

```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d yourdomain.com
```

### 备份策略
自动化数据库和文件备份:

```bash
# 数据库备份
pg_dump -h localhost -U blog_user blog_db > backup_$(date +%Y%m%d).sql

# 文件备份
tar -czf project_backup_$(date +%Y%m%d).tar.gz /home/projects/blog-system
```

这个方案真正实现了在Linux服务器上通过Terminal命令完成从项目创建到服务部署的全流程自动化! 🎯 