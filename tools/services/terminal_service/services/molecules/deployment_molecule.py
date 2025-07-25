#!/usr/bin/env python3
"""
部署分子 - DeploymentMolecule  
组合服务启动和端口管理原子，完成项目部署
"""

import asyncio
import os
import signal
import psutil
from typing import Optional, Dict, Any
from pathlib import Path
from tools.services.terminal_service.services.atomic.port_manager import PortManager
from tools.services.terminal_service.services.atomic.service_manager import ServiceManager
from tools.services.terminal_service.services.atomic.requirement_parser import RequirementAnalysis
from core.logging import get_logger

logger = get_logger(__name__)


class DeploymentResult:
    """部署结果"""
    def __init__(self, success: bool, url: Optional[str] = None, 
                 port: Optional[int] = None, process_id: Optional[int] = None,
                 error_message: Optional[str] = None):
        self.success = success
        self.url = url
        self.port = port
        self.process_id = process_id
        self.error_message = error_message


class DeploymentMolecule:
    """部署分子服务"""
    
    def __init__(self):
        self.port_manager = PortManager()
        self.service_manager = ServiceManager()
        self.running_services = {}  # 跟踪运行中的服务
    
    async def deploy_project(
        self, 
        project_path: str, 
        analysis: RequirementAnalysis,
        custom_port: Optional[int] = None
    ) -> DeploymentResult:
        """
        部署项目并启动服务
        
        Args:
            project_path: 项目目录路径
            analysis: 需求分析结果
            custom_port: 自定义端口，如果为None则自动分配
            
        Returns:
            DeploymentResult: 部署结果
        """
        
        try:
            # 1. 获取可用端口
            if custom_port:
                port_check = self.port_manager.check_port_available(custom_port)
                if not port_check["success"] or not port_check["available"]:
                    return DeploymentResult(
                        success=False, 
                        error_message=f"端口 {custom_port} 不可用"
                    )
                port = custom_port
            else:
                port_result = self.port_manager.allocate_port("app_service")
                if not port_result["success"]:
                    return DeploymentResult(
                        success=False, 
                        error_message=f"无法分配端口: {port_result['error']}"
                    )
                port = port_result["port"]
            
            # 2. 安装依赖
            install_success = await self._install_dependencies(project_path, analysis)
            if not install_success:
                return DeploymentResult(
                    success=False, 
                    error_message="依赖安装失败"
                )
            
            # 3. 启动服务
            process_id = await self._start_service(project_path, analysis, port)
            if not process_id:
                return DeploymentResult(
                    success=False, 
                    error_message="服务启动失败"
                )
            
            # 4. 验证服务是否正常运行
            await asyncio.sleep(2)  # 等待服务启动
            if not self._is_service_running(process_id):
                return DeploymentResult(
                    success=False, 
                    error_message="服务启动后立即停止"
                )
            
            # 5. 生成访问URL
            url = f"http://localhost:{port}"
            
            # 6. 记录运行中的服务
            self.running_services[project_path] = {
                'process_id': process_id,
                'port': port,
                'url': url
            }
            
            logger.info(f"✅ 项目部署成功: {url}")
            
            return DeploymentResult(
                success=True,
                url=url,
                port=port,
                process_id=process_id
            )
            
        except Exception as e:
            logger.error(f"部署失败: {e}")
            return DeploymentResult(
                success=False, 
                error_message=str(e)
            )
    
    async def _install_dependencies(self, project_path: str, analysis: RequirementAnalysis) -> bool:
        """安装项目依赖"""
        
        try:
            tech_stack = analysis.tech_stack
            logger.info(f"🔧 开始安装依赖，技术栈: {tech_stack}")
            
            if 'python' in tech_stack:
                # Python项目依赖安装
                requirements_file = os.path.join(project_path, 'requirements.txt')
                if os.path.exists(requirements_file):
                    logger.info(f"📦 发现requirements.txt，开始安装Python依赖")
                    
                    # 读取requirements内容用于日志
                    with open(requirements_file, 'r') as f:
                        deps = f.read().strip()
                        logger.info(f"📋 依赖列表:\n{deps}")
                    
                    # 简化安装，直接使用pip命令
                    result = await self.service_manager.run_command(
                        f"pip3 install -r {requirements_file}",
                        cwd=project_path
                    )
                    
                    logger.info(f"📦 依赖安装结果: {result['success']}")
                    if not result['success']:
                        logger.error(f"❌ 依赖安装失败: {result.get('stderr', '')}")
                    else:
                        logger.info(f"✅ 依赖安装成功: {result.get('stdout', '')}")
                    
                    return result["success"]
                else:
                    logger.info("📦 未发现requirements.txt，跳过依赖安装")
                    
            elif 'node' in tech_stack:
                # Node.js项目依赖安装
                package_file = os.path.join(project_path, 'package.json')
                if os.path.exists(package_file):
                    logger.info(f"📦 发现package.json，开始安装Node.js依赖")
                    result = await self.service_manager.run_command(
                        "npm install",
                        cwd=project_path
                    )
                    
                    logger.info(f"📦 Node依赖安装结果: {result['success']}")
                    if not result['success']:
                        logger.error(f"❌ Node依赖安装失败: {result.get('stderr', '')}")
                    
                    return result["success"]
                else:
                    logger.info("📦 未发现package.json，跳过依赖安装")
            
            return True  # 如果没有依赖文件，认为安装成功
            
        except Exception as e:
            logger.error(f"❌ 依赖安装异常: {e}")
            return False
    
    async def _start_service(self, project_path: str, analysis: RequirementAnalysis, port: int) -> Optional[int]:
        """启动服务进程"""
        
        try:
            tech_stack = analysis.tech_stack
            logger.info(f"🚀 开始启动服务，技术栈: {tech_stack}，端口: {port}")
            
            if 'flask' in tech_stack:
                # Flask应用启动
                app_file = os.path.join(project_path, 'app.py')
                if os.path.exists(app_file):
                    logger.info(f"📄 发现Flask应用文件: {app_file}")
                    
                    # 修改app.py中的端口配置
                    await self._update_port_in_file(app_file, port, 'flask')
                    logger.info(f"🔧 已更新端口配置为: {port}")
                    
                    # 检查文件内容
                    with open(app_file, 'r') as f:
                        content = f.read()
                        logger.info(f"📋 app.py前200字符: {content[:200]}")
                    
                    # 使用python3启动服务
                    process = await self.service_manager.start_background_service(
                        f"python3 app.py",
                        cwd=project_path
                    )
                    
                    if process:
                        logger.info(f"✅ Flask服务启动成功，PID: {process.pid}")
                        return process.pid
                    else:
                        logger.error("❌ Flask服务启动失败，未获得进程")
                        return None
                else:
                    logger.error(f"❌ 未找到Flask应用文件: {app_file}")
                    return None
                    
            elif 'fastapi' in tech_stack:
                # FastAPI应用启动
                main_file = os.path.join(project_path, 'main.py')
                if os.path.exists(main_file):
                    # 修改main.py中的端口配置
                    await self._update_port_in_file(main_file, port, 'fastapi')
                    
                    process = await self.service_manager.start_background_service(
                        f"python main.py",
                        cwd=project_path
                    )
                    return process.pid if process else None
                    
            elif 'express' in tech_stack:
                # Express应用启动
                server_file = os.path.join(project_path, 'server.js')
                if os.path.exists(server_file):
                    # 修改server.js中的端口配置
                    await self._update_port_in_file(server_file, port, 'express')
                    
                    process = await self.service_manager.start_background_service(
                        f"node server.js",
                        cwd=project_path
                    )
                    return process.pid if process else None
            
            return None
            
        except Exception as e:
            logger.error(f"服务启动失败: {e}")
            return None
    
    async def _update_port_in_file(self, file_path: str, port: int, tech_type: str):
        """更新文件中的端口配置"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if tech_type == 'flask':
                # 替换Flask端口配置
                import re
                content = re.sub(
                    r'app\.run\([^)]*\)',
                    f'app.run(host="0.0.0.0", port={port}, debug=True)',
                    content
                )
            elif tech_type == 'fastapi':
                # 替换FastAPI端口配置
                import re
                content = re.sub(
                    r'uvicorn\.run\([^)]*\)',
                    f'uvicorn.run(app, host="0.0.0.0", port={port})',
                    content
                )
            elif tech_type == 'express':
                # 替换Express端口配置
                import re
                content = re.sub(
                    r'\.listen\(\d+',
                    f'.listen({port}',
                    content
                )
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            logger.error(f"更新端口配置失败: {e}")
    
    def _is_service_running(self, process_id: int) -> bool:
        """检查服务进程是否在运行"""
        try:
            return psutil.pid_exists(process_id)
        except:
            return False
    
    async def stop_service(self, project_path: str) -> bool:
        """停止指定项目的服务"""
        
        if project_path not in self.running_services:
            return False
        
        try:
            service_info = self.running_services[project_path]
            process_id = service_info['process_id']
            
            # 终止进程
            if psutil.pid_exists(process_id):
                process = psutil.Process(process_id)
                process.terminate()
                
                # 等待进程结束
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    process.kill()  # 强制杀死进程
            
            # 释放端口
            port = service_info['port']
            self.port_manager.release_port(port)
            
            # 从运行列表中移除
            del self.running_services[project_path]
            
            logger.info(f"✅ 服务已停止: {project_path}")
            return True
            
        except Exception as e:
            logger.error(f"停止服务失败: {e}")
            return False
    
    def get_running_services(self) -> Dict[str, Dict[str, Any]]:
        """获取所有运行中的服务信息"""
        return self.running_services.copy()
    
    async def stop_all_services(self) -> Dict[str, bool]:
        """停止所有运行中的服务"""
        results = {}
        
        for project_path in list(self.running_services.keys()):
            results[project_path] = await self.stop_service(project_path)
        
        return results