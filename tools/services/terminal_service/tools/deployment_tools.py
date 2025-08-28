"""
Deployment Tools for Code-to-Service Pipeline
Extends Terminal Service for complete deployment workflows
"""

import os
import json
import tempfile
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from tools.services.terminal_service.tools.terminal_tools import TerminalTools
from tools.services.terminal_service.services.terminal_service import TerminalService
from tools.base_tool import BaseTool


class DeploymentTools(BaseTool):
    """Extended terminal tools for deployment workflows"""
    
    def __init__(self):
        super().__init__()
        self.terminal_tools = TerminalTools()
        self.terminal_service = TerminalService()
        self.deployment_configs = {
            "railway": {
                "base_url": "https://{service_name}.railway.app",
                "deploy_cmd": "railway up --service {service_name}"
            },
            "docker": {
                "base_url": "http://localhost:{port}",
                "deploy_cmd": "docker-compose up -d"
            },
            "vercel": {
                "base_url": "https://{project_name}.vercel.app",
                "deploy_cmd": "vercel --prod"
            }
        }
    
    async def create_and_deploy_service(
        self,
        project_name: str,
        code_content: str,
        service_type: str = "fastapi",
        deployment_platform: str = "railway",
        port: int = 8000,
        requirements: Optional[List[str]] = None
    ) -> str:
        """
        Complete workflow: Create code -> Deploy service -> Return URL
        
        Keywords: deploy, create, service, full-stack, automation
        Category: deployment
        
        Args:
            project_name: Name for the project/service
            code_content: Python code content for the service
            service_type: Type of service (fastapi, flask, simple)
            deployment_platform: Platform to deploy to (railway, docker, vercel)
            port: Port number for the service
            requirements: Additional Python packages needed
        """
        try:
            session_id = f"deploy_{project_name}_{uuid.uuid4().hex[:8]}"
            
            # Step 1: Create project structure
            project_result = await self._create_project_structure(
                project_name, code_content, service_type, port, requirements, session_id
            )
            
            if not project_result["success"]:
                return self.create_response(
                    status="error",
                    action="create_and_deploy_service",
                    data={"step": "project_creation"},
                    error_message=project_result["error"]
                )
            
            # Step 2: Deploy service
            deploy_result = await self._deploy_service(
                project_name, deployment_platform, session_id
            )
            
            if not deploy_result["success"]:
                return self.create_response(
                    status="error", 
                    action="create_and_deploy_service",
                    data={"step": "deployment"},
                    error_message=deploy_result["error"]
                )
            
            # Step 3: Generate service URL
            service_url = self._generate_service_url(
                project_name, deployment_platform, port
            )
            
            return self.create_response(
                status="success",
                action="create_and_deploy_service",
                data={
                    "project_name": project_name,
                    "service_url": service_url,
                    "deployment_platform": deployment_platform,
                    "port": port,
                    "project_path": project_result["project_path"],
                    "deployment_logs": deploy_result.get("logs", []),
                    "service_type": service_type,
                    "created_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="create_and_deploy_service",
                data={"project_name": project_name},
                error_message=str(e)
            )
    
    async def _create_project_structure(
        self, project_name: str, code_content: str, service_type: str, 
        port: int, requirements: Optional[List[str]], session_id: str
    ) -> Dict[str, Any]:
        """Create complete project structure"""
        try:
            # Create project directory
            project_path = f"/tmp/deployments/{project_name}"
            
            # Create directories
            await self.terminal_tools.execute_command(
                f"mkdir -p {project_path}", session_id=session_id
            )
            
            # Change to project directory
            await self.terminal_tools.change_directory(project_path, session_id)
            
            # Create main application file
            app_content = self._generate_app_code(code_content, service_type, port)
            
            # Write main app file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(app_content)
                temp_file = f.name
            
            await self.terminal_tools.execute_command(
                f"cp {temp_file} {project_path}/main.py", session_id=session_id
            )
            
            # Create requirements.txt
            requirements_content = self._generate_requirements(service_type, requirements)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(requirements_content)
                temp_req = f.name
            
            await self.terminal_tools.execute_command(
                f"cp {temp_req} {project_path}/requirements.txt", session_id=session_id
            )
            
            # Create deployment configuration
            config_result = await self._create_deployment_config(
                project_name, project_path, service_type, port, session_id
            )
            
            # Clean up temp files
            os.unlink(temp_file)
            os.unlink(temp_req)
            
            return {
                "success": True,
                "project_path": project_path,
                "config": config_result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_app_code(self, user_code: str, service_type: str, port: int) -> str:
        """Generate complete application code based on service type"""
        
        if service_type == "fastapi":
            return f'''#!/usr/bin/env python3
"""
Auto-generated FastAPI service
Created: {datetime.now().isoformat()}
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
from datetime import datetime

app = FastAPI(
    title="Auto-deployed Service",
    description="Service created and deployed via isA MCP Terminal Service",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {{
        "message": "Service is running!",
        "service": "Auto-deployed via isA MCP",
        "deployed_at": "{datetime.now().isoformat()}",
        "status": "healthy"
    }}

@app.get("/health")
async def health_check():
    return {{"status": "healthy", "timestamp": datetime.now().isoformat()}}

# User-defined code
{user_code}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", {port}))
    uvicorn.run(app, host="0.0.0.0", port=port)
'''
        
        elif service_type == "flask":
            return f'''#!/usr/bin/env python3
"""
Auto-generated Flask service
Created: {datetime.now().isoformat()}
"""

from flask import Flask, jsonify
import os
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def root():
    return jsonify({{
        "message": "Service is running!",
        "service": "Auto-deployed via isA MCP",
        "deployed_at": "{datetime.now().isoformat()}",
        "status": "healthy"
    }})

@app.route("/health")
def health_check():
    return jsonify({{"status": "healthy", "timestamp": datetime.now().isoformat()}})

# User-defined code
{user_code}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", {port}))
    app.run(host="0.0.0.0", port=port)
'''
        
        else:  # simple
            return f'''#!/usr/bin/env python3
"""
Auto-generated Simple HTTP service
Created: {datetime.now().isoformat()}
"""

import http.server
import socketserver
import json
import os
from datetime import datetime

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {{
                "message": "Service is running!",
                "service": "Auto-deployed via isA MCP",
                "deployed_at": "{datetime.now().isoformat()}",
                "status": "healthy"
            }}
            self.wfile.write(json.dumps(response).encode())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {{"status": "healthy", "timestamp": datetime.now().isoformat()}}
            self.wfile.write(json.dumps(response).encode())
        else:
            super().do_GET()

# User-defined code
{user_code}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", {port}))
    with socketserver.TCPServer(("", port), SimpleHandler) as httpd:
        print(f"Server running on port {{port}}")
        httpd.serve_forever()
'''
    
    def _generate_requirements(self, service_type: str, extra_requirements: Optional[List[str]]) -> str:
        """Generate requirements.txt based on service type"""
        base_requirements = {
            "fastapi": ["fastapi>=0.100.0", "uvicorn[standard]>=0.23.0"],
            "flask": ["flask>=2.3.0", "gunicorn>=21.0.0"],
            "simple": []
        }
        
        requirements = base_requirements.get(service_type, [])
        
        if extra_requirements:
            requirements.extend(extra_requirements)
        
        return "\n".join(requirements)
    
    async def _create_deployment_config(
        self, project_name: str, project_path: str, service_type: str, 
        port: int, session_id: str
    ) -> Dict[str, Any]:
        """Create deployment configuration files"""
        
        # Create Dockerfile
        dockerfile_content = f'''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE {port}

CMD ["python", "main.py"]
'''
        
        # Create docker-compose.yml
        compose_content = f'''version: '3.8'

services:
  {project_name}:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - PORT={port}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
'''
        
        # Create railway.json for Railway deployment
        railway_config = {
            "build": {"builder": "DOCKERFILE"},
            "deploy": {"startCommand": "python main.py"},
            "variables": {"PORT": port}
        }
        
        # Write configuration files
        configs = {
            "Dockerfile": dockerfile_content,
            "docker-compose.yml": compose_content,
            "railway.json": json.dumps(railway_config, indent=2)
        }
        
        for filename, content in configs.items():
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(content)
                temp_file = f.name
            
            await self.terminal_tools.execute_command(
                f"cp {temp_file} {project_path}/{filename}", session_id=session_id
            )
            os.unlink(temp_file)
        
        return {"configs_created": list(configs.keys())}
    
    async def _deploy_service(
        self, project_name: str, platform: str, session_id: str
    ) -> Dict[str, Any]:
        """Deploy the service to specified platform"""
        try:
            if platform == "docker":
                # Local Docker deployment
                result = await self.terminal_tools.execute_command(
                    "docker-compose up -d", session_id=session_id, require_confirmation=True
                )
                
            elif platform == "railway":
                # Railway deployment
                result = await self.terminal_tools.execute_command(
                    f"railway up --service {project_name}", 
                    session_id=session_id, 
                    require_confirmation=True
                )
                
            elif platform == "vercel":
                # Vercel deployment (for web services)
                result = await self.terminal_tools.execute_command(
                    "vercel --prod", session_id=session_id, require_confirmation=True
                )
            
            else:
                return {"success": False, "error": f"Unsupported platform: {platform}"}
            
            # Parse result
            result_data = json.loads(result)
            
            if result_data["status"] == "success":
                return {
                    "success": True,
                    "logs": [result_data["data"].get("stdout", "")]
                }
            else:
                return {
                    "success": False,
                    "error": result_data.get("error_message", "Deployment failed")
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_service_url(self, project_name: str, platform: str, port: int) -> str:
        """Generate the service URL based on deployment platform"""
        config = self.deployment_configs.get(platform, {})
        base_url = config.get("base_url", "http://localhost:{port}")
        
        if platform == "railway":
            return base_url.format(service_name=project_name)
        elif platform == "docker":
            return base_url.format(port=port)
        elif platform == "vercel":
            return base_url.format(project_name=project_name)
        else:
            return f"http://localhost:{port}"
    
    async def list_deployed_services(self) -> str:
        """
        List all deployed services and their URLs
        
        Keywords: list, deployed, services, status
        Category: deployment
        """
        try:
            # Check Docker services
            docker_result = await self.terminal_tools.execute_command("docker ps --format 'table {{.Names}}\\t{{.Ports}}\\t{{.Status}}'")
            
            # Check Railway services (if available)
            railway_result = None
            try:
                railway_result = await self.terminal_tools.execute_command("railway status")
            except:
                pass
            
            services = []
            
            # Parse Docker services
            if docker_result:
                docker_data = json.loads(docker_result)
                if docker_data["status"] == "success":
                    stdout = docker_data["data"].get("stdout", "")
                    for line in stdout.split("\\n")[1:]:  # Skip header
                        if line.strip():
                            parts = line.split("\\t")
                            if len(parts) >= 3:
                                services.append({
                                    "name": parts[0],
                                    "ports": parts[1],
                                    "status": parts[2],
                                    "platform": "docker"
                                })
            
            return self.create_response(
                status="success",
                action="list_deployed_services",
                data={
                    "services": services,
                    "count": len(services),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="list_deployed_services",
                data={},
                error_message=str(e)
            )
    
    def register_all_tools(self, mcp):
        """Register all deployment tools with MCP server"""
        self.register_tool(mcp, self.create_and_deploy_service)
        self.register_tool(mcp, self.list_deployed_services)


def register_deployment_tools(mcp):
    """Register deployment tools with MCP server"""
    deployment_tools = DeploymentTools()
    deployment_tools.register_all_tools(mcp) 