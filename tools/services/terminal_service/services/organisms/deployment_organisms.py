"""
部署组织服务
编排完整的"写代码 → 部署服务 → 返回链接"流程

这是最高层的服务，组合所有分子服务来实现完整的自动化部署
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# 导入分子服务
from ..molecules.project_molecules import ProjectMolecule
from ..atomic.command_execution import CommandExecution

# 导入AI文本生成服务
from tools.services.intelligence_service.language.text_generator import generate


class DeploymentOrganism:
    """部署组织服务 - 完整的部署流程编排"""
    
    def __init__(self):
        self.project_molecule = ProjectMolecule()
        self.cmd_exec = CommandExecution()
    
    async def complete_deployment_workflow(
        self,
        project_name: str,
        project_description: str,
        project_type: str = "web",
        deployment_requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        完整的部署工作流：写代码 → 部署服务 → 返回链接
        
        这是用户请求的核心功能！
        """
        try:
            workflow_results = []
            
            print(f"🚀 开始完整部署流程: {project_name}")
            
            # 阶段1: 创建项目并生成代码
            print("📝 阶段1: 项目创建和代码生成")
            project_result = await self._stage_create_project_with_code(
                project_name, project_description, project_type
            )
            workflow_results.append(("create_project_with_code", project_result))
            
            if not project_result["success"]:
                return self._create_result(False, {"workflow_results": workflow_results}, 
                                         f"项目创建失败: {project_result['error']}")
            
            # 阶段2: 智能生成部署配置
            print("🔧 阶段2: 智能生成部署配置")
            config_result = await self._stage_generate_deployment_config(
                project_name, project_type, deployment_requirements
            )
            workflow_results.append(("generate_deployment_config", config_result))
            
            # 阶段3: 执行部署命令
            print("🚀 阶段3: 执行部署")
            deploy_result = await self._stage_execute_deployment(
                project_name, project_type
            )
            workflow_results.append(("execute_deployment", deploy_result))
            
            # 阶段4: 生成访问链接
            print("🔗 阶段4: 生成服务链接")
            link_result = await self._stage_generate_service_links(
                project_name, project_type, deploy_result
            )
            workflow_results.append(("generate_service_links", link_result))
            
            # 检查整体流程是否成功
            all_success = all(result[1]["success"] for result in workflow_results if result[1].get("success") is not None)
            
            # 生成最终结果
            final_result = self._create_result(all_success, {
                "project_name": project_name,
                "project_type": project_type,
                "project_description": project_description,
                "workflow_stages": len(workflow_results),
                "workflow_results": workflow_results,
                "service_urls": link_result.get("data", {}).get("service_urls", []) if link_result.get("success") else [],
                "project_path": project_result.get("data", {}).get("project_path"),
                "deployment_summary": self._generate_deployment_summary(workflow_results)
            })
            
            print("✅ 完整部署流程完成!")
            return final_result
            
        except Exception as e:
            return self._create_result(False, error=f"部署流程异常: {str(e)}")
    
    async def _stage_create_project_with_code(
        self, 
        project_name: str, 
        project_description: str, 
        project_type: str
    ) -> Dict[str, Any]:
        """阶段1: 创建项目并使用AI生成代码"""
        try:
            # 使用ProjectMolecule创建项目
            project_result = await self.project_molecule.create_project_workspace(
                project_name=project_name,
                project_type=project_type,
                description=project_description
            )
            
            if not project_result["success"]:
                return project_result
            
            # 根据项目描述，生成更详细的业务代码
            enhanced_code_result = await self._generate_enhanced_business_code(
                project_result["data"]["project_path"], 
                project_name, 
                project_type, 
                project_description
            )
            
            return {
                "success": project_result["success"] and enhanced_code_result["success"],
                "data": {
                    "project_path": project_result["data"]["project_path"],
                    "directories_created": project_result["data"].get("directories_created", []),
                    "enhanced_code": enhanced_code_result["success"],
                    "code_files": enhanced_code_result.get("data", {}).get("files_created", [])
                },
                "stage": "create_project_with_code"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "stage": "create_project_with_code"}
    
    async def _generate_enhanced_business_code(
        self, 
        project_path: str, 
        project_name: str, 
        project_type: str, 
        description: str
    ) -> Dict[str, Any]:
        """根据项目描述生成增强的业务代码"""
        try:
            files_created = []
            
            # 生成API路由文件（如果是web或api项目）
            if project_type in ["web", "api"]:
                api_result = await self._generate_api_routes(
                    project_path, project_name, description
                )
                if api_result["success"]:
                    files_created.append(("api_routes", api_result))
            
            # 生成数据模型文件
            model_result = await self._generate_data_models(
                project_path, project_name, description
            )
            if model_result["success"]:
                files_created.append(("data_models", model_result))
            
            # 生成配置文件
            config_result = await self._generate_app_config(
                project_path, project_name, project_type
            )
            if config_result["success"]:
                files_created.append(("app_config", config_result))
            
            return {
                "success": len(files_created) > 0,
                "data": {"files_created": files_created},
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_api_routes(self, project_path: str, project_name: str, description: str) -> Dict[str, Any]:
        """生成API路由代码"""
        try:
            routes_path = os.path.join(project_path, "src", "routes.py")
            
            prompt = f"""Create API routes for a {project_name} application.

Project description: {description}

Generate Flask routes that implement the core functionality described. Include:
1. RESTful API endpoints (GET, POST, PUT, DELETE)
2. Proper error handling and status codes
3. Request validation
4. JSON responses
5. Basic authentication if needed
6. CORS handling

Make the routes relevant to the project description. Only return Python code, no explanations."""

            routes_code = await generate(prompt, temperature=0.3, max_tokens=1200)
            
            return self.project_molecule.file_ops.create_file(routes_path, routes_code)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_data_models(self, project_path: str, project_name: str, description: str) -> Dict[str, Any]:
        """生成数据模型代码"""
        try:
            models_path = os.path.join(project_path, "src", "models.py")
            
            prompt = f"""Create data models for a {project_name} application.

Project description: {description}

Generate Python classes that represent the main data entities. Include:
1. Class definitions with proper attributes
2. Data validation methods
3. Serialization methods (to_dict, from_dict)
4. String representations (__str__, __repr__)
5. Any business logic methods

Make the models relevant to the project description. Only return Python code, no explanations."""

            models_code = await generate(prompt, temperature=0.3, max_tokens=1000)
            
            return self.project_molecule.file_ops.create_file(models_path, models_code)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_app_config(self, project_path: str, project_name: str, project_type: str) -> Dict[str, Any]:
        """生成应用配置文件"""
        try:
            config_path = os.path.join(project_path, "src", "config.py")
            
            prompt = f"""Create a configuration file for a {project_type} application named {project_name}.

Include:
1. Environment-based configuration (development, production, testing)
2. Database configuration
3. API keys and secrets management
4. Logging configuration
5. CORS settings
6. Rate limiting settings

Use environment variables for sensitive data. Only return Python code, no explanations."""

            config_code = await generate(prompt, temperature=0.2, max_tokens=800)
            
            return self.project_molecule.file_ops.create_file(config_path, config_code)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _stage_generate_deployment_config(
        self, 
        project_name: str, 
        project_type: str, 
        requirements: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """阶段2: 智能生成部署配置"""
        try:
            project_path = f"/home/projects/{project_name}"
            config_files = []
            
            # 生成Dockerfile
            dockerfile_result = await self._generate_dockerfile(project_path, project_type)
            if dockerfile_result["success"]:
                config_files.append(("Dockerfile", dockerfile_result))
            
            # 生成docker-compose.yml
            compose_result = await self._generate_docker_compose(
                project_path, project_name, project_type
            )
            if compose_result["success"]:
                config_files.append(("docker-compose.yml", compose_result))
            
            # 生成启动脚本
            script_result = await self._generate_startup_script(
                project_path, project_name, project_type
            )
            if script_result["success"]:
                config_files.append(("startup_script", script_result))
            
            return {
                "success": len(config_files) > 0,
                "data": {"config_files": config_files},
                "stage": "generate_deployment_config"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "stage": "generate_deployment_config"}
    
    async def _generate_dockerfile(self, project_path: str, project_type: str) -> Dict[str, Any]:
        """生成Dockerfile"""
        try:
            dockerfile_path = os.path.join(project_path, "Dockerfile")
            
            prompt = f"""Create a Dockerfile for a {project_type} Python application.

Requirements:
1. Use Python 3.11 slim base image
2. Set working directory to /app
3. Copy and install requirements.txt first (for better caching)
4. Copy application code
5. Expose appropriate port (5000 for Flask, 8000 for FastAPI)
6. Set proper CMD to run the application
7. Include health check
8. Use non-root user for security

Only return the Dockerfile content, no explanations."""

            dockerfile_content = await generate(prompt, temperature=0.2, max_tokens=500)
            
            return self.project_molecule.file_ops.create_file(dockerfile_path, dockerfile_content)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_docker_compose(self, project_path: str, project_name: str, project_type: str) -> Dict[str, Any]:
        """生成docker-compose.yml"""
        try:
            compose_path = os.path.join(project_path, "docker-compose.yml")
            
            prompt = f"""Create a docker-compose.yml file for a {project_type} application named {project_name}.

Include:
1. Main application service
2. Database service (PostgreSQL or Redis if needed)
3. Proper networking
4. Volume mounts for development
5. Environment variables
6. Health checks
7. Restart policies
8. Port mappings

Make it production-ready. Only return the YAML content, no explanations."""

            compose_content = await generate(prompt, temperature=0.2, max_tokens=800)
            
            return self.project_molecule.file_ops.create_file(compose_path, compose_content)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_startup_script(self, project_path: str, project_name: str, project_type: str) -> Dict[str, Any]:
        """生成启动脚本"""
        try:
            script_path = os.path.join(project_path, "start.sh")
            
            prompt = f"""Create a startup script for a {project_type} application named {project_name}.

The script should:
1. Check if Docker is running
2. Build the Docker image
3. Start the services with docker-compose
4. Show service status
5. Display access URLs
6. Include error handling
7. Add logging

Make it user-friendly with clear output messages. Only return the bash script, no explanations."""

            script_content = await generate(prompt, temperature=0.3, max_tokens=600)
            
            return self.project_molecule.file_ops.create_file(script_path, script_content, executable=True)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _stage_execute_deployment(self, project_name: str, project_type: str) -> Dict[str, Any]:
        """阶段3: 执行部署"""
        try:
            project_path = f"/home/projects/{project_name}"
            deployment_results = []
            
            # 1. 构建Docker镜像
            print("🔨 构建Docker镜像...")
            build_result = self.cmd_exec.execute_command(
                f"cd {project_path} && docker build -t {project_name}:latest .",
                timeout=300
            )
            deployment_results.append(("docker_build", build_result))
            
            # 2. 启动服务
            print("🚀 启动服务...")
            start_result = self.cmd_exec.execute_command(
                f"cd {project_path} && docker-compose up -d",
                timeout=120
            )
            deployment_results.append(("docker_compose_up", start_result))
            
            # 3. 等待服务启动
            print("⏳ 等待服务启动...")
            import asyncio
            await asyncio.sleep(10)  # 等待服务启动
            
            # 4. 检查服务状态
            status_result = self.cmd_exec.execute_command(
                f"cd {project_path} && docker-compose ps",
                timeout=30
            )
            deployment_results.append(("service_status", status_result))
            
            # 检查部署是否成功
            deployment_success = build_result["success"] and start_result["success"]
            
            return {
                "success": deployment_success,
                "data": {
                    "deployment_results": deployment_results,
                    "services_running": status_result["success"]
                },
                "stage": "execute_deployment"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "stage": "execute_deployment"}
    
    async def _stage_generate_service_links(
        self, 
        project_name: str, 
        project_type: str, 
        deploy_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """阶段4: 生成服务访问链接"""
        try:
            # 获取服务器IP
            ip_result = self.cmd_exec.execute_command("hostname -I | awk '{print $1}'")
            server_ip = ip_result["stdout"].strip() if ip_result["success"] else "localhost"
            
            # 根据项目类型确定端口
            port_mapping = {
                "web": 5000,
                "api": 8000,
                "python": 8000
            }
            port = port_mapping.get(project_type, 5000)
            
            # 生成服务链接
            service_urls = [
                {
                    "name": "主服务",
                    "url": f"http://{server_ip}:{port}",
                    "description": "应用主入口"
                },
                {
                    "name": "健康检查",
                    "url": f"http://{server_ip}:{port}/health",
                    "description": "服务健康状态"
                }
            ]
            
            if project_type in ["api", "web"]:
                service_urls.append({
                    "name": "API文档",
                    "url": f"http://{server_ip}:{port}/docs",
                    "description": "API接口文档"
                })
            
            return {
                "success": True,
                "data": {
                    "server_ip": server_ip,
                    "port": port,
                    "service_urls": service_urls
                },
                "stage": "generate_service_links"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "stage": "generate_service_links"}
    
    def _generate_deployment_summary(self, workflow_results: List) -> Dict[str, Any]:
        """生成部署总结"""
        summary = {
            "total_stages": len(workflow_results),
            "successful_stages": 0,
            "failed_stages": 0,
            "stage_details": []
        }
        
        for stage_name, result in workflow_results:
            if result.get("success"):
                summary["successful_stages"] += 1
            else:
                summary["failed_stages"] += 1
            
            summary["stage_details"].append({
                "stage": stage_name,
                "success": result.get("success", False),
                "error": result.get("error")
            })
        
        return summary
    
    def _create_result(self, success: bool, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> Dict[str, Any]:
        """创建标准化结果"""
        return {
            "success": success,
            "data": data or {},
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "organism_type": "DeploymentOrganism",
            "workflow": "complete_deployment"
        } 