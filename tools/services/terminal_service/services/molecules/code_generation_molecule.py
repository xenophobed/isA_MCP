#!/usr/bin/env python3
"""
代码生成分子 - CodeGenerationMolecule
组合需求解析和代码生成原子，完成从需求到代码的转换
"""

from typing import Dict, Tuple
from pathlib import Path
import os
from tools.services.terminal_service.services.atomic.requirement_parser import RequirementParser, RequirementAnalysis
from tools.services.terminal_service.services.atomic.code_template_engine import CodeTemplateEngine
from tools.services.terminal_service.services.atomic.file_operations import FileOperations


class CodeGenerationMolecule:
    """代码生成分子服务"""
    
    def __init__(self):
        self.requirement_parser = RequirementParser()
        self.template_engine = CodeTemplateEngine()
        self.file_ops = FileOperations()
    
    async def generate_from_requirement(
        self, 
        user_requirement: str,
        output_dir: str = None
    ) -> Tuple[RequirementAnalysis, Dict[str, str], str]:
        """
        从用户需求生成完整项目代码
        
        Args:
            user_requirement: 用户需求描述
            output_dir: 输出目录路径，如果为None则自动生成
            
        Returns:
            Tuple[RequirementAnalysis, Dict[str, str], str]: 
            (需求分析结果, 生成的文件内容, 项目目录路径)
        """
        
        # 1. 解析用户需求
        analysis = await self.requirement_parser.parse(user_requirement)
        
        # 2. 生成项目名称
        project_name = self._generate_project_name(analysis)
        
        # 3. 确定输出目录
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "generated_apps", project_name)
        
        # 4. 生成项目文件内容
        files = await self.template_engine.generate_project_files(analysis, project_name)
        
        # 5. 创建项目目录并写入文件
        project_path = await self._create_project_structure(output_dir, files)
        
        return analysis, files, project_path
    
    def _generate_project_name(self, analysis: RequirementAnalysis) -> str:
        """根据分析结果生成项目名称"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        base_name = analysis.app_type.replace(' ', '_').lower()
        return f"{base_name}_{timestamp}"
    
    async def _create_project_structure(self, output_dir: str, files: Dict[str, str]) -> str:
        """创建项目目录结构并写入文件"""
        
        # 创建主目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 写入所有文件
        for file_path, content in files.items():
            full_path = os.path.join(output_dir, file_path)
            
            # 创建文件的父目录
            parent_dir = os.path.dirname(full_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # 写入文件内容
            self.file_ops.create_file(full_path, content)
        
        return output_dir
    
    async def analyze_requirement_only(self, user_requirement: str) -> RequirementAnalysis:
        """仅分析需求，不生成代码"""
        return await self.requirement_parser.parse(user_requirement)