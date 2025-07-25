#!/usr/bin/env python3
"""
需求解析原子 - RequirementParser
解析用户需求文本，提取关键信息
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from tools.services.intelligence_service.language.text_generator import generate


@dataclass
class RequirementAnalysis:
    """需求分析结果"""
    app_type: str  # 应用类型：blog, api, dashboard, etc
    tech_stack: str  # 技术栈：python-flask, node-express, etc
    features: List[str]  # 功能列表
    database: Optional[str] = None  # 数据库类型
    ui_framework: Optional[str] = None  # UI框架
    complexity: str = "simple"  # 复杂度：simple, medium, complex


class RequirementParser:
    """需求文本解析器"""
    
    async def parse(self, user_requirement: str) -> RequirementAnalysis:
        """
        解析用户需求并提取结构化信息
        
        Args:
            user_requirement: 用户需求描述
            
        Returns:
            RequirementAnalysis: 结构化的需求分析结果
        """
        
        # 构造解析提示词
        prompt = f"""
分析以下用户需求，返回JSON格式的结构化信息：

用户需求: "{user_requirement}"

请分析并返回以下JSON格式：
{{
    "app_type": "应用类型(blog/api/dashboard/ecommerce/chat/other)",
    "tech_stack": "推荐技术栈(python-flask/node-express/python-fastapi)",
    "features": ["功能1", "功能2", "功能3"],
    "database": "数据库类型(sqlite/none)",
    "ui_framework": "UI框架(bootstrap/tailwind/none)",
    "complexity": "复杂度(simple/medium/complex)"
}}

分析原则：
1. 优先选择简单轻量的技术栈
2. 如果没有明确要求数据库，默认用sqlite
3. 复杂度基于功能数量：1-3个功能=simple，4-6个=medium，7+个=complex
4. 只返回JSON，不要其他解释文字
"""
        
        try:
            # 使用现有的text_generator服务
            response = await generate(prompt, temperature=0.3)
            
            # 尝试解析JSON
            import json
            # 清理响应，提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                return RequirementAnalysis(
                    app_type=data.get('app_type', 'other'),
                    tech_stack=data.get('tech_stack', 'python-flask'),
                    features=data.get('features', []),
                    database=data.get('database'),
                    ui_framework=data.get('ui_framework'),
                    complexity=data.get('complexity', 'simple')
                )
            else:
                # 如果JSON解析失败，返回默认值
                return self._get_default_analysis(user_requirement)
                
        except Exception as e:
            # 出错时返回默认分析
            return self._get_default_analysis(user_requirement)
    
    def _get_default_analysis(self, requirement: str) -> RequirementAnalysis:
        """返回默认的需求分析结果"""
        
        # 简单的关键词匹配作为兜底
        req_lower = requirement.lower()
        
        if any(word in req_lower for word in ['blog', '博客']):
            app_type = 'blog'
            features = ['文章发布', '文章列表', '文章详情']
        elif any(word in req_lower for word in ['api', '接口']):
            app_type = 'api'
            features = ['RESTful API', '数据处理']
        elif any(word in req_lower for word in ['dashboard', '仪表板', '管理']):
            app_type = 'dashboard'
            features = ['数据展示', '图表显示']
        else:
            app_type = 'other'
            features = ['基础功能']
        
        return RequirementAnalysis(
            app_type=app_type,
            tech_stack='python-flask',
            features=features,
            database='sqlite',
            ui_framework='bootstrap',
            complexity='simple'
        )