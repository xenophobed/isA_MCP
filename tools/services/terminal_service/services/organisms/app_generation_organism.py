#!/usr/bin/env python3
"""
应用生成组织 - AppGenerationOrganism
编排整个从需求到部署的完整流程
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from tools.services.terminal_service.services.molecules.code_generation_molecule import CodeGenerationMolecule
from tools.services.terminal_service.services.molecules.deployment_molecule import DeploymentMolecule, DeploymentResult
from tools.services.terminal_service.services.atomic.requirement_parser import RequirementAnalysis
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AppDeploymentResult:
    """应用部署最终结果"""
    success: bool
    url: Optional[str] = None
    project_path: Optional[str] = None
    analysis: Optional[RequirementAnalysis] = None
    files: Optional[Dict[str, str]] = None
    deployment_info: Optional[DeploymentResult] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'success': self.success,
            'url': self.url,
            'project_path': self.project_path,
            'app_type': self.analysis.app_type if self.analysis else None,
            'tech_stack': self.analysis.tech_stack if self.analysis else None,
            'features': self.analysis.features if self.analysis else None,
            'port': self.deployment_info.port if self.deployment_info else None,
            'process_id': self.deployment_info.process_id if self.deployment_info else None,
            'error_message': self.error_message
        }


class AppGenerationOrganism:
    """应用生成组织服务 - 完整流程编排"""
    
    def __init__(self):
        self.code_generator = CodeGenerationMolecule()
        self.deployer = DeploymentMolecule()
    
    async def generate_and_deploy_app(
        self, 
        user_requirement: str,
        output_dir: Optional[str] = None,
        auto_deploy: bool = True,
        custom_port: Optional[int] = None
    ) -> AppDeploymentResult:
        """
        完整的应用生成和部署流程
        
        Args:
            user_requirement: 用户需求描述
            output_dir: 输出目录，None则自动生成
            auto_deploy: 是否自动部署
            custom_port: 自定义端口
            
        Returns:
            AppDeploymentResult: 完整的部署结果
        """
        
        try:
            logger.info(f"🚀 开始生成应用: {user_requirement}")
            
            # 阶段1: 需求分析与代码生成
            logger.info("📋 阶段1: 分析需求并生成代码...")
            analysis, files, project_path = await self.code_generator.generate_from_requirement(
                user_requirement, output_dir
            )
            
            logger.info(f"✅ 代码生成完成: {project_path}")
            logger.info(f"   应用类型: {analysis.app_type}")
            logger.info(f"   技术栈: {analysis.tech_stack}")
            logger.info(f"   功能: {', '.join(analysis.features)}")
            
            if not auto_deploy:
                return AppDeploymentResult(
                    success=True,
                    project_path=project_path,
                    analysis=analysis,
                    files=files
                )
            
            # 阶段2: 应用部署
            logger.info("🚀 阶段2: 部署应用...")
            deployment_result = await self.deployer.deploy_project(
                project_path, analysis, custom_port
            )
            
            if deployment_result.success:
                logger.info(f"✅ 应用部署成功!")
                logger.info(f"   访问地址: {deployment_result.url}")
                logger.info(f"   进程ID: {deployment_result.process_id}")
                
                return AppDeploymentResult(
                    success=True,
                    url=deployment_result.url,
                    project_path=project_path,
                    analysis=analysis,
                    files=files,
                    deployment_info=deployment_result
                )
            else:
                logger.error(f"❌ 部署失败: {deployment_result.error_message}")
                return AppDeploymentResult(
                    success=False,
                    project_path=project_path,
                    analysis=analysis,
                    files=files,
                    deployment_info=deployment_result,
                    error_message=f"部署失败: {deployment_result.error_message}"
                )
                
        except Exception as e:
            logger.error(f"❌ 应用生成失败: {e}")
            return AppDeploymentResult(
                success=False,
                error_message=str(e)
            )
    
    async def analyze_requirement_only(self, user_requirement: str) -> RequirementAnalysis:
        """仅分析需求，不生成代码"""
        return await self.code_generator.analyze_requirement_only(user_requirement)
    
    async def generate_code_only(self, user_requirement: str, output_dir: Optional[str] = None) -> AppDeploymentResult:
        """仅生成代码，不部署"""
        return await self.generate_and_deploy_app(
            user_requirement, output_dir, auto_deploy=False
        )
    
    async def deploy_existing_project(self, project_path: str, analysis: RequirementAnalysis, custom_port: Optional[int] = None) -> AppDeploymentResult:
        """部署已存在的项目"""
        try:
            deployment_result = await self.deployer.deploy_project(
                project_path, analysis, custom_port
            )
            
            if deployment_result.success:
                return AppDeploymentResult(
                    success=True,
                    url=deployment_result.url,
                    project_path=project_path,
                    analysis=analysis,
                    deployment_info=deployment_result
                )
            else:
                return AppDeploymentResult(
                    success=False,
                    project_path=project_path,
                    analysis=analysis,
                    deployment_info=deployment_result,
                    error_message=f"部署失败: {deployment_result.error_message}"
                )
                
        except Exception as e:
            return AppDeploymentResult(
                success=False,
                project_path=project_path,
                error_message=str(e)
            )
    
    async def stop_app(self, project_path: str) -> bool:
        """停止指定应用"""
        return await self.deployer.stop_service(project_path)
    
    def get_running_apps(self) -> Dict[str, Dict[str, Any]]:
        """获取所有运行中的应用"""
        return self.deployer.get_running_services()
    
    async def stop_all_apps(self) -> Dict[str, bool]:
        """停止所有运行中的应用"""
        return await self.deployer.stop_all_services()


# 全局实例，方便使用
app_generator = AppGenerationOrganism()