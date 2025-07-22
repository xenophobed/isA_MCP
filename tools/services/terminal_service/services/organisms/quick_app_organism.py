"""
快速应用组织服务
编排完整的"描述 → 应用 → 链接"流程
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime

# 导入分子服务
from ..molecules.app_analysis_molecule import AppAnalysisMolecule
from ..molecules.quick_code_molecule import QuickCodeMolecule
from ..molecules.quick_deployment_molecule import QuickDeploymentMolecule


class QuickAppOrganism:
    """快速应用组织服务 - 最高层的业务流程编排"""
    
    def __init__(self):
        self.app_analysis = AppAnalysisMolecule()
        self.code_generator = QuickCodeMolecule()
        self.deployment = QuickDeploymentMolecule()
        
    async def create_quick_app(self, description: str, app_name: Optional[str] = None) -> Dict[str, Any]:
        """
        一键创建快速应用
        
        完整流程: 描述分析 → 代码生成 → 服务部署 → 返回链接
        
        Args:
            description: 应用描述
            app_name: 可选的应用名称
            
        Returns:
            包含service_url和完整流程信息的结果
        """
        try:
            # 生成唯一的工作流ID
            workflow_id = f"quickapp_{uuid.uuid4().hex[:8]}"
            workflow_start_time = datetime.now()
            
            print(f"🚀 开始QuickApp创建流程: {workflow_id}")
            print(f"📝 描述: {description}")
            
            workflow_results = []
            
            # === 阶段1: 应用分析 ===
            print("🔍 阶段1: 应用分析...")
            analysis_result = await self._stage_analyze_application(description)
            workflow_results.append(("app_analysis", analysis_result))
            
            if not analysis_result["success"]:
                return self._create_workflow_result(
                    False, workflow_id, workflow_results, 
                    error="应用分析失败", 
                    stage="app_analysis"
                )
            
            # 从分析结果中提取应用规格
            app_spec = self._extract_app_spec(analysis_result, app_name, description)
            
            # === 阶段2: 代码生成 ===
            print("💻 阶段2: 代码生成...")
            code_result = await self._stage_generate_code(app_spec)
            workflow_results.append(("code_generation", code_result))
            
            if not code_result["success"]:
                return self._create_workflow_result(
                    False, workflow_id, workflow_results,
                    error="代码生成失败",
                    stage="code_generation"
                )
            
            # === 阶段3: 部署准备 ===
            print("🔧 阶段3: 部署准备...")
            project_path = code_result["project_path"]
            prep_result = await self.deployment.prepare_deployment(project_path)
            workflow_results.append(("deployment_preparation", prep_result))
            
            if not prep_result["success"]:
                return self._create_workflow_result(
                    False, workflow_id, workflow_results,
                    error="部署准备失败",
                    stage="deployment_preparation"
                )
            
            # === 阶段4: 服务部署 ===
            print("🚀 阶段4: 服务部署...")
            allocated_port = prep_result["allocated_port"]
            deploy_result = await self.deployment.deploy_service(project_path, allocated_port)
            workflow_results.append(("service_deployment", deploy_result))
            
            if not deploy_result["success"]:
                return self._create_workflow_result(
                    False, workflow_id, workflow_results,
                    error="服务部署失败",
                    stage="service_deployment"
                )
            
            # === 阶段5: 部署验证 ===
            print("✅ 阶段5: 部署验证...")
            service_url = deploy_result["service_url"]
            verify_result = await self.deployment.verify_deployment(service_url)
            workflow_results.append(("deployment_verification", verify_result))
            
            # === 生成最终结果 ===
            workflow_end_time = datetime.now()
            total_time = (workflow_end_time - workflow_start_time).total_seconds()
            
            final_result = self._create_workflow_result(
                True, workflow_id, workflow_results,
                service_url=service_url,
                app_name=app_spec["app_name"],
                total_time=total_time,
                verification_passed=verify_result.get("success", False)
            )
            
            print(f"🎉 QuickApp创建完成! 访问: {service_url}")
            print(f"⏱️  总耗时: {total_time:.1f}秒")
            
            return final_result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"QuickApp创建异常: {str(e)}",
                "workflow_id": workflow_id if 'workflow_id' in locals() else "unknown",
                "stage": "exception",
                "timestamp": datetime.now().isoformat()
            }
    
    async def list_quick_apps(self) -> Dict[str, Any]:
        """列出所有快速应用"""
        try:
            # 使用ServiceManager获取运行中的服务
            services_result = self.deployment.service_manager.list_running_services()
            
            if not services_result["success"]:
                return services_result
            
            # 过滤QuickApp服务（名称包含quickapp的）
            quickapps = []
            for service in services_result["running_services"]:
                service_name = service["service_name"]
                if "quickapp" in service_name.lower() or service_name.startswith("quickapp_"):
                    # 获取详细状态
                    status_result = self.deployment.service_manager.get_service_status(service_name)
                    
                    app_info = {
                        "app_name": service_name,
                        "port": service.get("port"),
                        "service_url": f"http://localhost:{service.get('port')}" if service.get("port") else None,
                        "status": "running" if service.get("actual_status") == "running" else "stopped",
                        "started_at": service.get("started_at"),
                        "cpu_percent": service.get("cpu_percent", 0),
                        "memory_mb": service.get("memory_mb", 0)
                    }
                    
                    quickapps.append(app_info)
            
            return {
                "success": True,
                "quickapps_count": len(quickapps),
                "quickapps": quickapps,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop_quick_app(self, app_name: str) -> Dict[str, Any]:
        """停止快速应用"""
        try:
            # 使用部署服务停止应用
            stop_result = await self.deployment.stop_service(app_name)
            
            return {
                "success": stop_result["success"],
                "app_name": app_name,
                "stop_details": stop_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app_name": app_name
            }
    
    async def get_quick_app_status(self, app_name: str) -> Dict[str, Any]:
        """获取快速应用状态"""
        try:
            # 获取服务状态
            status_result = self.deployment.service_manager.get_service_status(app_name)
            
            if not status_result["success"]:
                return status_result
            
            service_info = status_result["service_info"]
            
            # 如果服务在运行，验证部署
            verification_result = None
            if service_info.get("running") and service_info.get("port"):
                service_url = f"http://localhost:{service_info['port']}"
                verification_result = await self.deployment.verify_deployment(service_url)
            
            return {
                "success": True,
                "app_name": app_name,
                "service_info": service_info,
                "verification": verification_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app_name": app_name
            }
    
    async def _stage_analyze_application(self, description: str) -> Dict[str, Any]:
        """阶段1: 应用分析"""
        try:
            analysis_result = await self.app_analysis.analyze_app_description(description)
            
            if analysis_result["success"]:
                analysis_data = analysis_result["analysis"]
                
                return {
                    "success": True,
                    "app_type": analysis_data.get("app_type", "web"),
                    "complexity": analysis_data.get("complexity", "simple"),
                    "estimated_time": analysis_data.get("estimated_time", "30分钟"),
                    "tech_stack": analysis_data.get("tech_stack", []),
                    "requirements": analysis_data.get("requirements", {}),
                    "confidence": analysis_data.get("confidence", 0.5),
                    "stage": "app_analysis"
                }
            else:
                return {
                    "success": False,
                    "error": analysis_result.get("error", "Analysis failed"),
                    "stage": "app_analysis"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stage": "app_analysis"
            }
    
    async def _stage_generate_code(self, app_spec: Dict[str, Any]) -> Dict[str, Any]:
        """阶段2: 代码生成"""
        try:
            code_result = self.code_generator.generate_app_code(app_spec)
            
            return {
                "success": code_result["success"],
                "project_path": code_result.get("project_path"),
                "generated_files": code_result.get("generated_files", 0),
                "failed_files": code_result.get("failed_files", []),
                "stage": "code_generation"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stage": "code_generation"
            }
    
    def _extract_app_spec(self, analysis_result: Dict[str, Any], app_name: Optional[str], description: str) -> Dict[str, Any]:
        """从分析结果中提取应用规格"""
        return {
            "app_name": app_name or f"quickapp_{uuid.uuid4().hex[:8]}",
            "app_type": analysis_result.get("app_type", "web"),
            "description": description,
            "complexity": analysis_result.get("complexity", "simple"),
            "tech_stack": analysis_result.get("tech_stack", []),
            "port": None  # 将在部署阶段分配
        }
    
    def _create_workflow_result(
        self, 
        success: bool, 
        workflow_id: str, 
        workflow_results: list,
        error: Optional[str] = None,
        stage: Optional[str] = None,
        service_url: Optional[str] = None,
        app_name: Optional[str] = None,
        total_time: Optional[float] = None,
        verification_passed: Optional[bool] = None
    ) -> Dict[str, Any]:
        """创建工作流结果"""
        
        result = {
            "success": success,
            "workflow_id": workflow_id,
            "organism_type": "QuickAppOrganism",
            "timestamp": datetime.now().isoformat()
        }
        
        if success:
            # 成功结果
            result.update({
                "service_url": service_url,
                "app_name": app_name,
                "total_time_seconds": total_time,
                "verification_passed": verification_passed,
                "workflow_stages": len(workflow_results),
                "quick_links": {
                    "主页": service_url,
                    "健康检查": f"{service_url}/health",
                    "API信息": f"{service_url}/api/info"
                } if service_url else {}
            })
        else:
            # 失败结果
            result.update({
                "error": error,
                "failed_stage": stage,
                "completed_stages": len([r for r in workflow_results if r[1].get("success")])
            })
        
        # 添加详细的工作流信息
        result["workflow_details"] = {
            "total_stages": len(workflow_results),
            "stage_results": workflow_results
        }
        
        return result
    
    def get_organism_info(self) -> Dict[str, Any]:
        """获取组织服务信息"""
        return {
            "organism_name": "QuickAppOrganism",
            "description": "快速应用创建和管理服务",
            "capabilities": [
                "应用描述分析",
                "自动代码生成", 
                "容器化部署",
                "服务验证",
                "应用管理"
            ],
            "supported_app_types": [
                "web", "api", "blog", "dashboard", "chat", "ecommerce", "tool"
            ],
            "average_creation_time": "2-5分钟",
            "dependencies": {
                "molecules": ["AppAnalysisMolecule", "QuickCodeMolecule", "QuickDeploymentMolecule"],
                "external": ["Docker", "AI文本生成服务"]
            },
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }