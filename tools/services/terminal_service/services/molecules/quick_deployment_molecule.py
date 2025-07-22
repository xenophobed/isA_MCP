"""
快速部署分子服务
编排容器化部署流程
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

# 导入原子服务
from ..atomic.command_execution import CommandExecution
from ..atomic.port_manager import PortManager
from ..atomic.service_manager import ServiceManager


class QuickDeploymentMolecule:
    """快速部署分子服务"""
    
    def __init__(self):
        self.cmd_exec = CommandExecution()
        self.port_manager = PortManager()
        self.service_manager = ServiceManager()
        
    async def prepare_deployment(self, project_path: str) -> Dict[str, Any]:
        """准备部署环境"""
        try:
            preparation_steps = []
            
            # 1. 验证项目文件
            validation_result = self._validate_project_files(project_path)
            preparation_steps.append(("validate_files", validation_result))
            
            if not validation_result["success"]:
                return {
                    "success": False,
                    "error": "Project validation failed",
                    "preparation_steps": preparation_steps
                }
            
            # 2. 检查Docker环境
            docker_result = self._check_docker_environment()
            preparation_steps.append(("check_docker", docker_result))
            
            if not docker_result["success"]:
                return {
                    "success": False,
                    "error": "Docker environment check failed",
                    "preparation_steps": preparation_steps
                }
            
            # 3. 分配端口
            port_result = self.port_manager.allocate_port(
                service_name=os.path.basename(project_path)
            )
            preparation_steps.append(("allocate_port", port_result))
            
            if not port_result["success"]:
                return {
                    "success": False,
                    "error": "Port allocation failed",
                    "preparation_steps": preparation_steps
                }
            
            # 4. 清理旧容器（如果存在）
            cleanup_result = await self._cleanup_existing_containers(project_path)
            preparation_steps.append(("cleanup_containers", cleanup_result))
            
            return {
                "success": True,
                "allocated_port": port_result["port"],
                "preparation_steps": preparation_steps,
                "project_path": project_path,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    async def deploy_service(self, project_path: str, port: Optional[int] = None) -> Dict[str, Any]:
        """部署服务"""
        try:
            deployment_steps = []
            app_name = os.path.basename(project_path)
            
            # 1. 如果没有指定端口，分配一个
            if not port:
                port_result = self.port_manager.allocate_port(service_name=app_name)
                if not port_result["success"]:
                    return {
                        "success": False,
                        "error": "Failed to allocate port",
                        "port_error": port_result
                    }
                port = port_result["port"]
            
            # 2. 构建Docker镜像
            build_result = await self._build_docker_image(project_path, app_name)
            deployment_steps.append(("build_image", build_result))
            
            if not build_result["success"]:
                return {
                    "success": False,
                    "error": "Docker build failed",
                    "deployment_steps": deployment_steps
                }
            
            # 3. 启动容器
            start_result = await self._start_container(project_path, app_name, port)
            deployment_steps.append(("start_container", start_result))
            
            if not start_result["success"]:
                return {
                    "success": False,
                    "error": "Container start failed",
                    "deployment_steps": deployment_steps
                }
            
            # 4. 等待服务启动
            health_result = await self._wait_for_service_health(port)
            deployment_steps.append(("health_check", health_result))
            
            # 5. 注册服务到ServiceManager
            service_result = self.service_manager.start_service(
                service_name=app_name,
                command=f"docker-compose -f {project_path}/docker-compose.yml up",
                port=port,
                working_dir=project_path
            )
            deployment_steps.append(("register_service", service_result))
            
            return {
                "success": True,
                "app_name": app_name,
                "port": port,
                "service_url": f"http://localhost:{port}",
                "deployment_steps": deployment_steps,
                "container_id": start_result.get("container_id"),
                "health_status": health_result.get("status", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    async def verify_deployment(self, service_url: str) -> Dict[str, Any]:
        """验证部署是否成功"""
        try:
            verification_results = []
            
            # 1. 检查主页响应
            home_result = await self._check_endpoint(service_url)
            verification_results.append(("home_page", home_result))
            
            # 2. 检查健康检查端点
            health_result = await self._check_endpoint(f"{service_url}/health")
            verification_results.append(("health_endpoint", health_result))
            
            # 3. 检查API信息端点
            api_result = await self._check_endpoint(f"{service_url}/api/info")
            verification_results.append(("api_endpoint", api_result))
            
            # 计算验证成功率
            successful_checks = sum(1 for _, result in verification_results if result.get("success", False))
            total_checks = len(verification_results)
            success_rate = successful_checks / total_checks if total_checks > 0 else 0
            
            return {
                "success": success_rate >= 0.5,  # 至少50%的检查通过
                "service_url": service_url,
                "success_rate": round(success_rate, 2),
                "successful_checks": successful_checks,
                "total_checks": total_checks,
                "verification_results": verification_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "service_url": service_url
            }
    
    async def stop_service(self, app_name: str) -> Dict[str, Any]:
        """停止服务"""
        try:
            stop_steps = []
            
            # 1. 停止ServiceManager中的服务记录
            service_result = self.service_manager.stop_service(app_name)
            stop_steps.append(("stop_service_manager", service_result))
            
            # 2. 停止Docker容器
            docker_result = await self._stop_docker_container(app_name)
            stop_steps.append(("stop_docker", docker_result))
            
            # 3. 释放端口
            if service_result["success"] and "port" in service_result:
                port_result = self.port_manager.release_port(service_result["port"])
                stop_steps.append(("release_port", port_result))
            
            all_success = all(result.get("success", False) for _, result in stop_steps)
            
            return {
                "success": all_success,
                "app_name": app_name,
                "stop_steps": stop_steps,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app_name": app_name
            }
    
    def _validate_project_files(self, project_path: str) -> Dict[str, Any]:
        """验证项目文件完整性"""
        try:
            required_files = [
                "app.py",
                "requirements.txt", 
                "Dockerfile",
                "docker-compose.yml"
            ]
            
            missing_files = []
            existing_files = []
            
            for file_name in required_files:
                file_path = os.path.join(project_path, file_name)
                if os.path.exists(file_path):
                    existing_files.append(file_name)
                else:
                    missing_files.append(file_name)
            
            return {
                "success": len(missing_files) == 0,
                "project_path": project_path,
                "existing_files": existing_files,
                "missing_files": missing_files,
                "validation_passed": len(missing_files) == 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    def _check_docker_environment(self) -> Dict[str, Any]:
        """检查Docker环境"""
        try:
            # 检查Docker是否安装并运行
            docker_result = self.cmd_exec.execute_command("docker --version")
            
            if not docker_result["success"]:
                return {
                    "success": False,
                    "error": "Docker is not installed or not accessible",
                    "docker_check": docker_result
                }
            
            # 检查Docker守护进程是否运行
            daemon_result = self.cmd_exec.execute_command("docker info")
            
            if not daemon_result["success"]:
                return {
                    "success": False,
                    "error": "Docker daemon is not running",
                    "daemon_check": daemon_result
                }
            
            # 检查docker-compose
            compose_result = self.cmd_exec.execute_command("docker-compose --version")
            
            return {
                "success": True,
                "docker_version": docker_result["stdout"].strip(),
                "docker_compose_available": compose_result["success"],
                "docker_compose_version": compose_result["stdout"].strip() if compose_result["success"] else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _cleanup_existing_containers(self, project_path: str) -> Dict[str, Any]:
        """清理现有容器"""
        try:
            app_name = os.path.basename(project_path)
            cleanup_commands = [
                f"docker stop {app_name}_app 2>/dev/null || true",
                f"docker rm {app_name}_app 2>/dev/null || true",
                f"docker rmi {app_name}:latest 2>/dev/null || true"
            ]
            
            cleanup_results = []
            for cmd in cleanup_commands:
                result = self.cmd_exec.execute_command(cmd)
                cleanup_results.append(result)
            
            return {
                "success": True,
                "cleanup_commands": len(cleanup_commands),
                "cleanup_results": cleanup_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    async def _build_docker_image(self, project_path: str, app_name: str) -> Dict[str, Any]:
        """构建Docker镜像"""
        try:
            build_cmd = f"cd {project_path} && docker build -t {app_name}:latest ."
            
            # 构建可能需要较长时间，设置5分钟超时
            result = self.cmd_exec.execute_command(build_cmd, timeout=300)
            
            return {
                "success": result["success"],
                "app_name": app_name,
                "build_output": result.get("stdout", ""),
                "build_error": result.get("stderr", ""),
                "build_time": result.get("execution_time", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app_name": app_name
            }
    
    async def _start_container(self, project_path: str, app_name: str, port: int) -> Dict[str, Any]:
        """启动容器"""
        try:
            # 使用docker-compose启动
            start_cmd = f"cd {project_path} && docker-compose up -d"
            
            result = self.cmd_exec.execute_command(start_cmd, timeout=120)
            
            if result["success"]:
                # 获取容器ID
                container_cmd = f"docker ps -q -f name={app_name}_app"
                container_result = self.cmd_exec.execute_command(container_cmd)
                container_id = container_result["stdout"].strip() if container_result["success"] else None
                
                return {
                    "success": True,
                    "app_name": app_name,
                    "port": port,
                    "container_id": container_id,
                    "start_output": result.get("stdout", "")
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to start container",
                    "start_error": result.get("stderr", ""),
                    "app_name": app_name
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app_name": app_name
            }
    
    async def _wait_for_service_health(self, port: int, max_wait_time: int = 60) -> Dict[str, Any]:
        """等待服务健康检查通过"""
        try:
            service_url = f"http://localhost:{port}"
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                health_result = await self._check_endpoint(f"{service_url}/health")
                
                if health_result.get("success"):
                    return {
                        "success": True,
                        "status": "healthy",
                        "wait_time": round(time.time() - start_time, 2),
                        "service_url": service_url
                    }
                
                # 等待3秒后重试
                await asyncio.sleep(3)
            
            # 超时
            return {
                "success": False,
                "status": "timeout",
                "wait_time": max_wait_time,
                "service_url": service_url
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "port": port
            }
    
    async def _check_endpoint(self, url: str) -> Dict[str, Any]:
        """检查端点是否可访问"""
        try:
            # 使用curl检查端点
            curl_cmd = f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout 5 {url}"
            result = self.cmd_exec.execute_command(curl_cmd)
            
            if result["success"]:
                http_code = result["stdout"].strip()
                success = http_code.startswith("2")  # 2xx状态码
                
                return {
                    "success": success,
                    "url": url,
                    "http_code": http_code,
                    "response_time": result.get("execution_time", 0)
                }
            else:
                return {
                    "success": False,
                    "url": url,
                    "error": "Connection failed",
                    "curl_error": result.get("stderr", "")
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    async def _stop_docker_container(self, app_name: str) -> Dict[str, Any]:
        """停止Docker容器"""
        try:
            stop_cmd = f"docker stop {app_name}_app && docker rm {app_name}_app"
            result = self.cmd_exec.execute_command(stop_cmd)
            
            return {
                "success": result["success"],
                "app_name": app_name,
                "stop_output": result.get("stdout", ""),
                "stop_error": result.get("stderr", "")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app_name": app_name
            }