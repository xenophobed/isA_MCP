"""
QuickApp Tools for MCP Integration
快速应用工具 - 简化的MCP接口
"""

import sys
import os
import json
from typing import Optional, Dict, Any

# Add parent directories to path for imports
current_file = __file__
tools_dir = os.path.dirname(current_file)
terminal_service_dir = os.path.dirname(tools_dir)
services_dir = os.path.dirname(terminal_service_dir)
tools_root = os.path.dirname(services_dir)
project_root = os.path.dirname(tools_root)
sys.path.insert(0, project_root)

from tools.base_tool import BaseTool
from ..services.organisms.quick_app_organism import QuickAppOrganism


class QuickAppTools(BaseTool):
    """QuickApp工具集 - 调用QuickAppOrganism服务"""
    
    def __init__(self):
        super().__init__()
        self.quick_app_organism = QuickAppOrganism()
    
    async def create_quick_app(
        self,
        description: str,
        app_name: Optional[str] = None
    ) -> str:
        """
        一键创建快速应用
        
        从用户描述直接创建可访问的Web应用
        
        Keywords: create, app, quick, deploy, web, service
        Category: quickapp
        
        Args:
            description: 应用描述，例如 "创建一个简单的博客网站"
            app_name: 可选的应用名称，不提供则自动生成
        """
        try:
            print(f"🚀 开始创建快速应用...")
            print(f"📝 描述: {description}")
            if app_name:
                print(f"📛 名称: {app_name}")
            
            result = await self.quick_app_organism.create_quick_app(description, app_name)
            
            if result["success"]:
                return self.create_response(
                    status="success",
                    action="create_quick_app",
                    data={
                        "app_name": result["app_name"],
                        "service_url": result["service_url"],
                        "total_time_seconds": result["total_time_seconds"],
                        "verification_passed": result["verification_passed"],
                        "quick_links": result["quick_links"],
                        "workflow_id": result["workflow_id"],
                        "summary": f"✅ 应用 '{result['app_name']}' 创建成功！访问: {result['service_url']}"
                    }
                )
            else:
                return self.create_response(
                    status="error",
                    action="create_quick_app",
                    data={
                        "failed_stage": result.get("failed_stage"),
                        "completed_stages": result.get("completed_stages", 0),
                        "workflow_id": result.get("workflow_id")
                    },
                    error_message=result["error"]
                )
                
        except Exception as e:
            return self.create_response(
                status="error",
                action="create_quick_app",
                data={"description": description},
                error_message=str(e)
            )
    
    async def list_quick_apps(self) -> str:
        """
        列出所有快速应用
        
        显示当前运行中的所有快速应用及其状态
        
        Keywords: list, apps, running, status
        Category: quickapp
        """
        try:
            result = await self.quick_app_organism.list_quick_apps()
            
            if result["success"]:
                apps_data = []
                for app in result["quickapps"]:
                    apps_data.append({
                        "app_name": app["app_name"],
                        "service_url": app["service_url"],
                        "status": app["status"],
                        "port": app["port"],
                        "started_at": app["started_at"],
                        "resource_usage": {
                            "cpu_percent": app["cpu_percent"],
                            "memory_mb": app["memory_mb"]
                        }
                    })
                
                return self.create_response(
                    status="success",
                    action="list_quick_apps",
                    data={
                        "total_apps": result["quickapps_count"],
                        "running_apps": apps_data,
                        "summary": f"共找到 {result['quickapps_count']} 个快速应用"
                    }
                )
            else:
                return self.create_response(
                    status="error",
                    action="list_quick_apps",
                    data={},
                    error_message=result["error"]
                )
                
        except Exception as e:
            return self.create_response(
                status="error",
                action="list_quick_apps",
                data={},
                error_message=str(e)
            )
    
    async def stop_quick_app(self, app_name: str) -> str:
        """
        停止快速应用
        
        停止指定的快速应用并释放资源
        
        Keywords: stop, app, shutdown, kill
        Category: quickapp
        
        Args:
            app_name: 要停止的应用名称
        """
        try:
            result = await self.quick_app_organism.stop_quick_app(app_name)
            
            if result["success"]:
                return self.create_response(
                    status="success",
                    action="stop_quick_app",
                    data={
                        "app_name": app_name,
                        "stop_details": result["stop_details"],
                        "summary": f"✅ 应用 '{app_name}' 已成功停止"
                    }
                )
            else:
                return self.create_response(
                    status="error",
                    action="stop_quick_app",
                    data={"app_name": app_name},
                    error_message=result["error"]
                )
                
        except Exception as e:
            return self.create_response(
                status="error",
                action="stop_quick_app",
                data={"app_name": app_name},
                error_message=str(e)
            )
    
    async def get_quick_app_status(self, app_name: str) -> str:
        """
        获取快速应用状态
        
        查看指定应用的详细运行状态和健康信息
        
        Keywords: status, health, info, check
        Category: quickapp
        
        Args:
            app_name: 应用名称
        """
        try:
            result = await self.quick_app_organism.get_quick_app_status(app_name)
            
            if result["success"]:
                service_info = result["service_info"]
                verification = result.get("verification")
                
                status_data = {
                    "app_name": app_name,
                    "running": service_info.get("running", False),
                    "port": service_info.get("port"),
                    "service_url": f"http://localhost:{service_info['port']}" if service_info.get("port") else None,
                    "started_at": service_info.get("started_at"),
                    "resource_usage": {
                        "cpu_percent": service_info.get("cpu_percent", 0),
                        "memory_info": service_info.get("memory_info", {}),
                        "num_threads": service_info.get("num_threads", 0)
                    }
                }
                
                if verification:
                    status_data["health_check"] = {
                        "verification_passed": verification.get("success", False),
                        "success_rate": verification.get("success_rate", 0),
                        "successful_checks": verification.get("successful_checks", 0),
                        "total_checks": verification.get("total_checks", 0)
                    }
                
                return self.create_response(
                    status="success",
                    action="get_quick_app_status",
                    data=status_data
                )
            else:
                return self.create_response(
                    status="error",
                    action="get_quick_app_status",
                    data={"app_name": app_name},
                    error_message=result["error"]
                )
                
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_quick_app_status",
                data={"app_name": app_name},
                error_message=str(e)
            )
    
    async def get_quickapp_info(self) -> str:
        """
        获取QuickApp服务信息
        
        显示QuickApp服务的能力和支持的应用类型
        
        Keywords: info, capabilities, help, about
        Category: quickapp
        """
        try:
            organism_info = self.quick_app_organism.get_organism_info()
            
            return self.create_response(
                status="success",
                action="get_quickapp_info",
                data={
                    "service_name": organism_info["organism_name"],
                    "description": organism_info["description"],
                    "capabilities": organism_info["capabilities"],
                    "supported_app_types": organism_info["supported_app_types"],
                    "average_creation_time": organism_info["average_creation_time"],
                    "version": organism_info["version"],
                    "usage_examples": [
                        "创建一个简单的博客网站",
                        "构建一个数据展示仪表板",
                        "开发一个API服务",
                        "制作一个在线工具"
                    ]
                }
            )
            
        except Exception as e:
            return self.create_response(
                status="error",
                action="get_quickapp_info",
                data={},
                error_message=str(e)
            )
    
    def register_all_tools(self, mcp):
        """注册所有QuickApp工具"""
        self.register_tool(mcp, self.create_quick_app)
        self.register_tool(mcp, self.list_quick_apps)
        self.register_tool(mcp, self.stop_quick_app)
        self.register_tool(mcp, self.get_quick_app_status)
        self.register_tool(mcp, self.get_quickapp_info)


def register_quick_app_tools(mcp):
    """注册QuickApp工具到MCP服务器"""
    quick_app_tools = QuickAppTools()
    quick_app_tools.register_all_tools(mcp)