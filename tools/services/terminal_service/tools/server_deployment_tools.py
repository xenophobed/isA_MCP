"""
Server Deployment Tools for Linux Server Operations
在Linux服务器上实现完整的开发部署流程
"""

import os
import json
import uuid
import socket
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from .terminal_tools import TerminalTools
from ..services.terminal_service import TerminalService
from tools.base_tool import BaseTool


class ServerDeploymentTools(BaseTool):
    """Linux服务器上的完整部署工具集"""
    
    def __init__(self):
        super().__init__()
        self.terminal_tools = TerminalTools()
        self.terminal_service = TerminalService()
        self.server_config = {
            "projects_base": "/home/projects",  # 项目根目录
            "services_base": "/opt/services",   # 服务部署目录
            "nginx_sites": "/etc/nginx/sites-available",  # Nginx配置
            "systemd_services": "/etc/systemd/system",    # 系统服务
            "logs_base": "/var/log/deployed_services"     # 日志目录
        }
    
    async def create_project_workspace(
        self,
        project_name: str,
        project_type: str = "web",
        description: Optional[str] = None
    ) -> str:
        """
        创建新的项目工作空间
        
        Keywords: project, workspace, create, folder, directory
        Category: project_management
        
        Args:
            project_name: 项目名称
            project_type: 项目类型 (web, api, service, database)
            description: 项目描述
        """
        try:
            session_id = f"project_{project_name}_{uuid.uuid4().hex[:8]}"
            project_path = f"{self.server_config['projects_base']}/{project_name}"
            
            # 1. 创建项目目录结构
            structure_result = await self._create_project_structure(
                project_name, project_path, project_type, session_id
            )
            
            if not structure_result["success"]:
                return self.create_response(
                    status="error",
                    action="create_project_workspace",
                    data={"project_name": project_name},
                    error_message=structure_result["error"]
                )
            
            # 2. 初始化项目配置
            config_result = await self._initialize_project_config(
                project_path, project_name, project_type, description, session_id
            )
            
            # 3. 设置基础文件
            files_result = await self._setup_base_files(
                project_path, project_type, session_id
            )
            
            return self.create_response(
                status="success",
                action="create_project_workspace",
                data={
                    "project_name": project_name,
                    "project_path": project_path,
                    "project_type": project_type,
                    "session_id": session_id,
                    "structure": structure_result["structure"],
                    "files_created": files_result.get("files", []),
                    "created_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="create_project_workspace",
                data={"project_name": project_name},
                error_message=str(e)
            )
    
    async def create_code_file(
        self,
        project_name: str,
        file_path: str,
        file_content: str,
        file_type: str = "python",
        executable: bool = False
    ) -> str:
        """
        在项目中创建代码文件
        
        Keywords: file, create, code, write, implement
        Category: file_management
        
        Args:
            project_name: 项目名称
            file_path: 文件相对路径 (如: src/main.py)
            file_content: 文件内容
            file_type: 文件类型 (python, javascript, shell, config)
            executable: 是否设置为可执行
        """
        try:
            session_id = f"file_{project_name}_{uuid.uuid4().hex[:8]}"
            full_project_path = f"{self.server_config['projects_base']}/{project_name}"
            full_file_path = f"{full_project_path}/{file_path}"
            
            # 检查项目是否存在
            check_result = await self.terminal_tools.execute_command(
                f"test -d {full_project_path}", session_id=session_id
            )
            check_data = json.loads(check_result)
            
            if check_data["status"] != "success":
                return self.create_response(
                    status="error",
                    action="create_code_file",
                    data={"project_name": project_name, "file_path": file_path},
                    error_message=f"Project {project_name} does not exist"
                )
            
            # 创建文件目录
            file_dir = os.path.dirname(full_file_path)
            if file_dir != full_project_path:
                await self.terminal_tools.execute_command(
                    f"mkdir -p {file_dir}", session_id=session_id
                )
            
            # 写入文件内容
            await self.terminal_tools.execute_command(
                f"cat > {full_file_path} << 'EOF'\n{file_content}\nEOF",
                session_id=session_id
            )
            
            # 设置文件权限
            if executable:
                await self.terminal_tools.execute_command(
                    f"chmod +x {full_file_path}", session_id=session_id
                )
            
            # 验证文件创建
            verify_result = await self.terminal_tools.execute_command(
                f"ls -la {full_file_path}", session_id=session_id
            )
            
            return self.create_response(
                status="success",
                action="create_code_file",
                data={
                    "project_name": project_name,
                    "file_path": file_path,
                    "full_path": full_file_path,
                    "file_type": file_type,
                    "executable": executable,
                    "file_info": json.loads(verify_result)["data"].get("stdout", ""),
                    "created_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="create_code_file",
                data={"project_name": project_name, "file_path": file_path},
                error_message=str(e)
            )
    
    async def deploy_database_service(
        self,
        project_name: str,
        db_type: str = "postgresql",
        db_name: Optional[str] = None,
        port: int = 5432,
        username: str = "app_user",
        password: Optional[str] = None
    ) -> str:
        """
        部署数据库服务
        
        Keywords: database, deploy, postgresql, mysql, mongodb
        Category: database
        
        Args:
            project_name: 项目名称
            db_type: 数据库类型 (postgresql, mysql, mongodb, redis)
            db_name: 数据库名称
            port: 数据库端口
            username: 用户名
            password: 密码 (如果为None则自动生成)
        """
        try:
            session_id = f"db_{project_name}_{db_type}_{uuid.uuid4().hex[:8]}"
            
            if not db_name:
                db_name = f"{project_name}_db"
            
            if not password:
                password = f"pwd_{uuid.uuid4().hex[:12]}"
            
            # 1. 创建数据库数据目录
            data_dir = f"{self.server_config['services_base']}/{project_name}/database"
            await self.terminal_tools.execute_command(
                f"sudo mkdir -p {data_dir}", session_id=session_id
            )
            
            # 2. 部署数据库服务
            if db_type == "postgresql":
                deploy_result = await self._deploy_postgresql(
                    project_name, db_name, port, username, password, data_dir, session_id
                )
            elif db_type == "mysql":
                deploy_result = await self._deploy_mysql(
                    project_name, db_name, port, username, password, data_dir, session_id
                )
            elif db_type == "mongodb":
                deploy_result = await self._deploy_mongodb(
                    project_name, db_name, port, username, password, data_dir, session_id
                )
            elif db_type == "redis":
                deploy_result = await self._deploy_redis(
                    project_name, port, data_dir, session_id
                )
            else:
                return self.create_response(
                    status="error",
                    action="deploy_database_service",
                    data={"project_name": project_name, "db_type": db_type},
                    error_message=f"Unsupported database type: {db_type}"
                )
            
            if not deploy_result["success"]:
                return self.create_response(
                    status="error",
                    action="deploy_database_service",
                    data={"project_name": project_name, "db_type": db_type},
                    error_message=deploy_result["error"]
                )
            
            return self.create_response(
                status="success",
                action="deploy_database_service",
                data={
                    "project_name": project_name,
                    "db_type": db_type,
                    "db_name": db_name,
                    "port": port,
                    "username": username,
                    "password": password,
                    "data_directory": data_dir,
                    "service_name": deploy_result["service_name"],
                    "connection_url": deploy_result["connection_url"],
                    "status": "running"
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="deploy_database_service",
                data={"project_name": project_name, "db_type": db_type},
                error_message=str(e)
            )
    
    async def deploy_web_server(
        self,
        project_name: str,
        server_type: str = "nginx",
        port: int = 80,
        ssl_enabled: bool = False,
        domain: Optional[str] = None
    ) -> str:
        """
        部署Web服务器
        
        Keywords: web, server, nginx, apache, deploy
        Category: web_server
        
        Args:
            project_name: 项目名称
            server_type: 服务器类型 (nginx, apache)
            port: 端口号
            ssl_enabled: 是否启用SSL
            domain: 域名 (如果没有则使用IP)
        """
        try:
            session_id = f"web_{project_name}_{uuid.uuid4().hex[:8]}"
            
            # 获取服务器IP
            if not domain:
                ip_result = await self.terminal_tools.execute_command(
                    "curl -s ifconfig.me || hostname -I | awk '{print $1}'", 
                    session_id=session_id
                )
                ip_data = json.loads(ip_result)
                server_ip = ip_data["data"].get("stdout", "localhost").strip()
                domain = server_ip
            
            # 部署对应的Web服务器
            if server_type == "nginx":
                deploy_result = await self._deploy_nginx(
                    project_name, port, ssl_enabled, domain, session_id
                )
            elif server_type == "apache":
                deploy_result = await self._deploy_apache(
                    project_name, port, ssl_enabled, domain, session_id
                )
            else:
                return self.create_response(
                    status="error",
                    action="deploy_web_server",
                    data={"project_name": project_name, "server_type": server_type},
                    error_message=f"Unsupported server type: {server_type}"
                )
            
            if not deploy_result["success"]:
                return self.create_response(
                    status="error",
                    action="deploy_web_server",
                    data={"project_name": project_name, "server_type": server_type},
                    error_message=deploy_result["error"]
                )
            
            # 生成访问URL
            protocol = "https" if ssl_enabled else "http"
            url = f"{protocol}://{domain}" + (f":{port}" if port not in [80, 443] else "")
            
            return self.create_response(
                status="success",
                action="deploy_web_server",
                data={
                    "project_name": project_name,
                    "server_type": server_type,
                    "port": port,
                    "domain": domain,
                    "ssl_enabled": ssl_enabled,
                    "service_url": url,
                    "config_file": deploy_result["config_file"],
                    "service_name": deploy_result["service_name"],
                    "status": "running"
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="deploy_web_server",
                data={"project_name": project_name, "server_type": server_type},
                error_message=str(e)
            )
    
    async def deploy_application_service(
        self,
        project_name: str,
        app_type: str = "python",
        main_file: str = "main.py",
        port: int = 8000,
        environment: Optional[Dict[str, str]] = None
    ) -> str:
        """
        部署应用服务
        
        Keywords: application, service, python, node, deploy, systemd
        Category: application
        
        Args:
            project_name: 项目名称
            app_type: 应用类型 (python, node, go, java)
            main_file: 主文件名
            port: 服务端口
            environment: 环境变量
        """
        try:
            session_id = f"app_{project_name}_{uuid.uuid4().hex[:8]}"
            project_path = f"{self.server_config['projects_base']}/{project_name}"
            
            # 检查项目和主文件是否存在
            check_result = await self.terminal_tools.execute_command(
                f"test -f {project_path}/{main_file}", session_id=session_id
            )
            check_data = json.loads(check_result)
            
            if check_data["status"] != "success":
                return self.create_response(
                    status="error",
                    action="deploy_application_service",
                    data={"project_name": project_name, "main_file": main_file},
                    error_message=f"Main file {main_file} not found in project {project_name}"
                )
            
            # 根据应用类型部署
            if app_type == "python":
                deploy_result = await self._deploy_python_app(
                    project_name, project_path, main_file, port, environment, session_id
                )
            elif app_type == "node":
                deploy_result = await self._deploy_node_app(
                    project_name, project_path, main_file, port, environment, session_id
                )
            elif app_type == "go":
                deploy_result = await self._deploy_go_app(
                    project_name, project_path, main_file, port, environment, session_id
                )
            else:
                return self.create_response(
                    status="error",
                    action="deploy_application_service",
                    data={"project_name": project_name, "app_type": app_type},
                    error_message=f"Unsupported application type: {app_type}"
                )
            
            if not deploy_result["success"]:
                return self.create_response(
                    status="error",
                    action="deploy_application_service",
                    data={"project_name": project_name, "app_type": app_type},
                    error_message=deploy_result["error"]
                )
            
            # 生成服务URL
            ip_result = await self.terminal_tools.execute_command(
                "hostname -I | awk '{print $1}'", session_id=session_id
            )
            ip_data = json.loads(ip_result)
            server_ip = ip_data["data"].get("stdout", "localhost").strip()
            service_url = f"http://{server_ip}:{port}"
            
            return self.create_response(
                status="success",
                action="deploy_application_service",
                data={
                    "project_name": project_name,
                    "app_type": app_type,
                    "main_file": main_file,
                    "port": port,
                    "service_url": service_url,
                    "service_name": deploy_result["service_name"],
                    "systemd_file": deploy_result["systemd_file"],
                    "status": "running",
                    "logs_command": f"sudo journalctl -f -u {deploy_result['service_name']}"
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="deploy_application_service",
                data={"project_name": project_name, "app_type": app_type},
                error_message=str(e)
            )
    
    async def get_server_status(self) -> str:
        """
        获取服务器状态和部署的服务列表
        
        Keywords: status, services, list, running
        Category: monitoring
        """
        try:
            session_id = f"status_{uuid.uuid4().hex[:8]}"
            
            # 系统信息
            system_info = await self._get_system_info(session_id)
            
            # 运行的服务
            services_info = await self._get_running_services(session_id)
            
            # 项目列表
            projects_info = await self._get_projects_list(session_id)
            
            # 端口使用情况
            ports_info = await self._get_ports_usage(session_id)
            
            return self.create_response(
                status="success",
                action="get_server_status",
                data={
                    "system": system_info,
                    "services": services_info,
                    "projects": projects_info,
                    "ports": ports_info,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_server_status",
                data={},
                error_message=str(e)
            )
    
    # 私有方法实现...
    
    async def _create_project_structure(
        self, project_name: str, project_path: str, project_type: str, session_id: str
    ) -> Dict[str, Any]:
        """创建项目目录结构"""
        try:
            # 基础目录结构
            base_dirs = ["src", "config", "logs", "docs", "tests"]
            
            # 根据项目类型添加特定目录
            if project_type == "web":
                base_dirs.extend(["static", "templates", "assets"])
            elif project_type == "api":
                base_dirs.extend(["models", "routes", "middleware"])
            elif project_type == "service":
                base_dirs.extend(["services", "workers", "queues"])
            elif project_type == "database":
                base_dirs.extend(["migrations", "seeds", "schemas"])
            
            # 创建主项目目录
            await self.terminal_tools.execute_command(
                f"sudo mkdir -p {project_path}", session_id=session_id
            )
            
            # 创建子目录
            for dir_name in base_dirs:
                await self.terminal_tools.execute_command(
                    f"mkdir -p {project_path}/{dir_name}", session_id=session_id
                )
            
            # 设置权限
            await self.terminal_tools.execute_command(
                f"sudo chown -R $USER:$USER {project_path}", session_id=session_id
            )
            
            return {
                "success": True,
                "structure": base_dirs,
                "project_path": project_path
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _deploy_postgresql(
        self, project_name: str, db_name: str, port: int, username: str, 
        password: str, data_dir: str, session_id: str
    ) -> Dict[str, Any]:
        """部署PostgreSQL数据库"""
        try:
            service_name = f"postgresql-{project_name}"
            
            # 创建Docker Compose配置
            compose_content = f"""version: '3.8'
services:
  postgres:
    image: postgres:15
    container_name: {service_name}
    environment:
      POSTGRES_DB: {db_name}
      POSTGRES_USER: {username}
      POSTGRES_PASSWORD: {password}
    ports:
      - "{port}:5432"
    volumes:
      - {data_dir}:/var/lib/postgresql/data
    restart: unless-stopped
"""
            
            # 写入配置文件
            compose_file = f"{data_dir}/docker-compose.yml"
            await self.terminal_tools.execute_command(
                f"cat > {compose_file} << 'EOF'\n{compose_content}\nEOF",
                session_id=session_id
            )
            
            # 启动服务
            await self.terminal_tools.execute_command(
                f"cd {data_dir} && docker-compose up -d", 
                session_id=session_id,
                require_confirmation=True
            )
            
            connection_url = f"postgresql://{username}:{password}@localhost:{port}/{db_name}"
            
            return {
                "success": True,
                "service_name": service_name,
                "connection_url": connection_url
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _deploy_nginx(
        self, project_name: str, port: int, ssl_enabled: bool, domain: str, session_id: str
    ) -> Dict[str, Any]:
        """部署Nginx配置"""
        try:
            config_file = f"{self.server_config['nginx_sites']}/{project_name}"
            
            # 生成Nginx配置
            if ssl_enabled:
                nginx_config = f"""server {{
    listen 80;
    listen 443 ssl http2;
    server_name {domain};
    
    # SSL配置
    ssl_certificate /etc/ssl/certs/{project_name}.crt;
    ssl_certificate_key /etc/ssl/private/{project_name}.key;
    
    # 重定向HTTP到HTTPS
    if ($scheme != "https") {{
        return 301 https://$server_name$request_uri;
    }}
    
    location / {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}"""
            else:
                nginx_config = f"""server {{
    listen {port};
    server_name {domain};
    
    location / {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}"""
            
            # 写入配置文件
            await self.terminal_tools.execute_command(
                f"sudo bash -c 'cat > {config_file} << \"EOF\"\n{nginx_config}\nEOF'",
                session_id=session_id
            )
            
            # 启用站点
            await self.terminal_tools.execute_command(
                f"sudo ln -sf {config_file} /etc/nginx/sites-enabled/{project_name}",
                session_id=session_id
            )
            
            # 测试并重载Nginx
            await self.terminal_tools.execute_command(
                "sudo nginx -t && sudo systemctl reload nginx",
                session_id=session_id,
                require_confirmation=True
            )
            
            return {
                "success": True,
                "service_name": f"nginx-{project_name}",
                "config_file": config_file
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _deploy_python_app(
        self, project_name: str, project_path: str, main_file: str, 
        port: int, environment: Optional[Dict[str, str]], session_id: str
    ) -> Dict[str, Any]:
        """部署Python应用为systemd服务"""
        try:
            service_name = f"{project_name}-app"
            systemd_file = f"{self.server_config['systemd_services']}/{service_name}.service"
            
            # 安装依赖 (如果存在requirements.txt)
            await self.terminal_tools.execute_command(
                f"cd {project_path} && if [ -f requirements.txt ]; then pip3 install -r requirements.txt; fi",
                session_id=session_id
            )
            
            # 准备环境变量
            env_vars = ""
            if environment:
                env_vars = "\n".join([f"Environment={k}={v}" for k, v in environment.items()])
            env_vars += f"\nEnvironment=PORT={port}"
            
            # 创建systemd服务文件
            systemd_content = f"""[Unit]
Description={project_name} Application Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory={project_path}
ExecStart=/usr/bin/python3 {main_file}
Restart=always
RestartSec=10
{env_vars}

[Install]
WantedBy=multi-user.target
"""
            
            # 写入systemd文件
            await self.terminal_tools.execute_command(
                f"sudo bash -c 'cat > {systemd_file} << \"EOF\"\n{systemd_content}\nEOF'",
                session_id=session_id
            )
            
            # 启用并启动服务
            await self.terminal_tools.execute_command(
                f"sudo systemctl daemon-reload && sudo systemctl enable {service_name} && sudo systemctl start {service_name}",
                session_id=session_id,
                require_confirmation=True
            )
            
            return {
                "success": True,
                "service_name": service_name,
                "systemd_file": systemd_file
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def register_all_tools(self, mcp):
        """注册所有服务器部署工具"""
        self.register_tool(mcp, self.create_project_workspace)
        self.register_tool(mcp, self.create_code_file)
        self.register_tool(mcp, self.deploy_database_service)
        self.register_tool(mcp, self.deploy_web_server)
        self.register_tool(mcp, self.deploy_application_service)
        self.register_tool(mcp, self.get_server_status)


def register_server_deployment_tools(mcp):
    """注册服务器部署工具"""
    server_tools = ServerDeploymentTools()
    server_tools.register_all_tools(mcp) 