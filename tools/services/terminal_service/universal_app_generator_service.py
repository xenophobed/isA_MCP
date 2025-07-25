#!/usr/bin/env python3
"""
通用应用生成服务 - UniversalAppGeneratorService
最顶层服务接口，实现 需求 -> 部署URL + 代码 的完整功能
"""

from typing import Optional, Dict, Any
from tools.services.terminal_service.services.organisms.app_generation_organism import AppGenerationOrganism, AppDeploymentResult
from tools.services.terminal_service.services.atomic.requirement_parser import RequirementAnalysis
from core.logging import get_logger

logger = get_logger(__name__)


class UniversalAppGeneratorService:
    """通用应用生成器服务 - 服务层接口"""
    
    def __init__(self):
        self.app_generator = AppGenerationOrganism()
    
    async def generate_app(
        self, 
        user_requirement: str,
        output_dir: Optional[str] = None,
        custom_port: Optional[int] = None,
        deploy_immediately: bool = True
    ) -> AppDeploymentResult:
        """
        核心接口：从用户需求生成并部署应用
        
        Args:
            user_requirement: 用户需求描述文本
            output_dir: 项目输出目录（可选）
            custom_port: 自定义端口（可选）
            deploy_immediately: 是否立即部署（默认True）
            
        Returns:
            AppDeploymentResult: 包含部署URL、项目代码、部署信息的完整结果
        """
        
        logger.info(f"🎯 UniversalAppGenerator 开始处理需求")
        logger.info(f"   需求: {user_requirement}")
        logger.info(f"   输出目录: {output_dir or '自动生成'}")
        logger.info(f"   自定义端口: {custom_port or '自动分配'}")
        logger.info(f"   立即部署: {deploy_immediately}")
        
        # 调用组织层完成完整流程
        result = await self.app_generator.generate_and_deploy_app(
            user_requirement=user_requirement,
            output_dir=output_dir,
            auto_deploy=deploy_immediately,
            custom_port=custom_port
        )
        
        if result.success:
            if deploy_immediately and result.url:
                logger.info(f"🎉 应用生成并部署成功!")
                logger.info(f"   🌐 访问地址: {result.url}")
                logger.info(f"   📁 项目路径: {result.project_path}")
                logger.info(f"   🔧 技术栈: {result.analysis.tech_stack}")
            else:
                logger.info(f"✅ 代码生成成功!")
                logger.info(f"   📁 项目路径: {result.project_path}")
        else:
            logger.error(f"❌ 应用生成失败: {result.error_message}")
        
        return result
    
    async def analyze_requirement(self, user_requirement: str) -> RequirementAnalysis:
        """
        仅分析用户需求，不生成代码
        
        Args:
            user_requirement: 用户需求描述
            
        Returns:
            RequirementAnalysis: 需求分析结果
        """
        return await self.app_generator.analyze_requirement_only(user_requirement)
    
    async def generate_code_only(
        self, 
        user_requirement: str, 
        output_dir: Optional[str] = None
    ) -> AppDeploymentResult:
        """
        仅生成代码，不部署
        
        Args:
            user_requirement: 用户需求描述
            output_dir: 输出目录
            
        Returns:
            AppDeploymentResult: 代码生成结果
        """
        return await self.app_generator.generate_code_only(user_requirement, output_dir)
    
    async def deploy_existing_project(
        self, 
        project_path: str, 
        analysis: RequirementAnalysis, 
        custom_port: Optional[int] = None
    ) -> AppDeploymentResult:
        """
        部署已存在的项目
        
        Args:
            project_path: 项目路径
            analysis: 需求分析结果
            custom_port: 自定义端口
            
        Returns:
            AppDeploymentResult: 部署结果
        """
        return await self.app_generator.deploy_existing_project(
            project_path, analysis, custom_port
        )
    
    async def stop_app(self, project_path: str) -> bool:
        """
        停止指定应用
        
        Args:
            project_path: 项目路径
            
        Returns:
            bool: 是否成功停止
        """
        return await self.app_generator.stop_app(project_path)
    
    def get_running_apps(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有运行中的应用信息
        
        Returns:
            Dict: 应用信息字典
        """
        return self.app_generator.get_running_apps()
    
    async def stop_all_apps(self) -> Dict[str, bool]:
        """
        停止所有运行中的应用
        
        Returns:
            Dict[str, bool]: 各应用的停止结果
        """
        return await self.app_generator.stop_all_apps()
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态信息
        
        Returns:
            Dict: 服务状态信息
        """
        running_apps = self.get_running_apps()
        
        return {
            'service_name': 'UniversalAppGeneratorService',
            'status': 'running',
            'running_apps_count': len(running_apps),
            'running_apps': running_apps,
            'supported_tech_stacks': [
                'python-flask',
                'python-fastapi', 
                'node-express'
            ],
            'supported_app_types': [
                'blog',
                'api',
                'dashboard',
                'ecommerce',
                'chat',
                'other'
            ]
        }


# 全局服务实例
universal_app_generator = UniversalAppGeneratorService()


# 便捷函数
async def generate_app(user_requirement: str, **kwargs) -> AppDeploymentResult:
    """
    便捷函数：生成并部署应用
    
    Args:
        user_requirement: 用户需求
        **kwargs: 其他参数
        
    Returns:
        AppDeploymentResult: 部署结果
    """
    return await universal_app_generator.generate_app(user_requirement, **kwargs)


async def analyze_requirement(user_requirement: str) -> RequirementAnalysis:
    """
    便捷函数：分析用户需求
    
    Args:
        user_requirement: 用户需求
        
    Returns:
        RequirementAnalysis: 分析结果
    """
    return await universal_app_generator.analyze_requirement(user_requirement)