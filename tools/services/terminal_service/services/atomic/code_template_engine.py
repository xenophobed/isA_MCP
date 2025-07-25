#!/usr/bin/env python3
"""
代码模板引擎原子 - CodeTemplateEngine
根据需求分析生成项目代码文件
"""

from typing import Dict, List
from pathlib import Path
from tools.services.terminal_service.services.atomic.requirement_parser import RequirementAnalysis
from tools.services.intelligence_service.language.text_generator import generate


class CodeTemplateEngine:
    """代码模板生成引擎"""
    
    def __init__(self):
        self.templates = {
            'python-flask': self._get_flask_templates(),
            'node-express': self._get_express_templates(),
            'python-fastapi': self._get_fastapi_templates()
        }
    
    async def generate_project_files(
        self, 
        analysis: RequirementAnalysis,
        project_name: str = "generated_app"
    ) -> Dict[str, str]:
        """
        根据需求分析生成完整项目文件
        
        Args:
            analysis: 需求分析结果
            project_name: 项目名称
            
        Returns:
            Dict[str, str]: 文件路径 -> 文件内容的映射
        """
        
        files = {}
        
        # 获取对应技术栈的模板
        templates = self.templates.get(analysis.tech_stack, self.templates['python-flask'])
        
        # 生成基础文件结构
        for file_path, template_func in templates.items():
            if callable(template_func):
                # 检查是否是async函数
                import asyncio
                if asyncio.iscoroutinefunction(template_func):
                    content = await template_func(analysis, project_name)
                else:
                    content = template_func(analysis, project_name)
            else:
                content = template_func
            files[file_path] = content
        
        return files
    
    def _get_flask_templates(self) -> Dict[str, callable]:
        """Flask项目模板 - 前后端分离架构"""
        return {
            'app.py': self._generate_flask_backend,
            'static/index.html': self._generate_frontend_html,
            'static/style.css': self._generate_modern_css,
            'static/script.js': self._generate_frontend_js,
            'requirements.txt': lambda analysis, name: self._get_flask_requirements(analysis),
            'README.md': self._generate_readme,
        }
    
    def _get_express_templates(self) -> Dict[str, callable]:
        """Express项目模板"""
        return {
            'server.js': self._generate_express_app,
            'package.json': self._generate_package_json,
            'public/index.html': self._generate_html_template,
            'public/style.css': self._generate_css,
            'README.md': self._generate_readme,
        }
    
    def _get_fastapi_templates(self) -> Dict[str, callable]:
        """FastAPI项目模板"""
        return {
            'main.py': self._generate_fastapi_app,
            'requirements.txt': lambda analysis, name: self._get_fastapi_requirements(analysis),
            'README.md': self._generate_readme,
        }
    
    async def _generate_flask_backend(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """后端团队：生成Flask API服务"""
        
        prompt = f"""
作为后端开发工程师，创建一个Flask API服务：

应用类型: {analysis.app_type}
功能需求: {', '.join(analysis.features)}

要求：
1. 前后端分离架构
2. Flask提供静态文件服务（app.static_folder = 'static'）
3. 定义API路由提供JSON数据（如 /api/data）
4. 主路由'/'返回静态HTML文件
5. 包含CORS支持（from flask_cors import CORS）
6. 最后加上 if __name__ == '__main__': app.run(host='0.0.0.0', port=5000, debug=True)

只返回Python代码：
"""
        
        code = await generate(prompt, temperature=0.2)
        return self._clean_code_response(code)
    
    async def _generate_express_app(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """生成Express应用主文件"""
        
        prompt = f"""
生成一个Express.js应用的完整代码，要求：

应用类型: {analysis.app_type}
功能需求: {', '.join(analysis.features)}

要求：
1. 完整可运行的Express应用
2. 包含所有需要的路由
3. 设置静态文件服务
4. 监听端口3000
5. 简洁实用，核心功能完整

只返回JavaScript代码，不要解释：
"""
        
        return await generate(prompt, temperature=0.3)
    
    async def _generate_fastapi_app(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """生成FastAPI应用主文件"""
        
        prompt = f"""
生成一个FastAPI应用的完整代码，要求：

应用类型: {analysis.app_type}
功能需求: {', '.join(analysis.features)}

要求：
1. 完整可运行的FastAPI应用
2. 包含所有需要的API端点
3. 包含启动代码 uvicorn.run(app, host="0.0.0.0", port=8000)
4. 简洁实用，核心功能完整

只返回Python代码，不要解释：
"""
        
        return await generate(prompt, temperature=0.3)
    
    async def _generate_html_template(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """生成HTML模板"""
        
        ui_framework = analysis.ui_framework or 'bootstrap'
        features = ', '.join(analysis.features)
        
        prompt = f"""
生成一个完整的HTML页面，要求：

应用类型: {analysis.app_type}
功能特性: {features}
UI框架: {ui_framework}

要求：
1. 完整的HTML5页面结构
2. 引入{ui_framework}样式框架
3. 包含应用的主要功能界面
4. 简洁美观的设计
5. 响应式布局

只返回HTML代码，不要解释：
"""
        
        return await generate(prompt, temperature=0.4)
    
    def _generate_css(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """生成基础CSS样式"""
        return """
/* 基础样式 */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1, h2, h3 {
    color: #333;
}

.btn {
    background-color: #007bff;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
}

.btn:hover {
    background-color: #0056b3;
}
"""
    
    async def _generate_readme(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """生成README文档"""
        
        tech_stack = analysis.tech_stack
        features = ', '.join(analysis.features)
        
        if 'flask' in tech_stack:
            run_cmd = "python app.py"
            install_cmd = "pip install -r requirements.txt"
        elif 'express' in tech_stack:
            run_cmd = "node server.js"
            install_cmd = "npm install"
        elif 'fastapi' in tech_stack:
            run_cmd = "python main.py"
            install_cmd = "pip install -r requirements.txt"
        else:
            run_cmd = "python app.py"
            install_cmd = "pip install -r requirements.txt"
        
        return f"""# {project_name}

## 项目简介

这是一个基于 {tech_stack} 的 {analysis.app_type} 应用。

## 功能特性

{features}

## 快速开始

1. 安装依赖:
   ```bash
   {install_cmd}
   ```

2. 运行应用:
   ```bash
   {run_cmd}
   ```

3. 访问应用:
   - 本地访问: http://localhost:5000 (Flask) 或 http://localhost:3000 (Express) 或 http://localhost:8000 (FastAPI)

## 技术栈

- 后端: {tech_stack}
- 数据库: {analysis.database or 'None'}
- UI: {analysis.ui_framework or 'None'}

## 项目结构

自动生成的项目包含了完整的应用架构和核心功能实现。
"""
    
    def _clean_code_response(self, code: str) -> str:
        """清理AI生成的代码响应，移除markdown标记等"""
        import re
        
        # 移除markdown代码块标记
        code = re.sub(r'^```[a-zA-Z]*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n```$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```$', '', code, flags=re.MULTILINE)
        
        # 移除开头和结尾的空白
        code = code.strip()
        
        return code
    
    async def _generate_frontend_html(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """前端团队：生成现代化HTML页面"""
        
        prompt = f"""
作为前端开发工程师，创建一个现代化的HTML页面：

应用类型: {analysis.app_type}
功能需求: {', '.join(analysis.features)}

要求：
1. 使用HTML5标准结构
2. 引入Bootstrap 5.3.0 CDN
3. 引入Font Awesome图标库
4. 响应式设计，移动端友好
5. 现代化的UI组件（导航栏、卡片、按钮等）
6. 包含页面标题、导航菜单、主要内容区域、页脚
7. 预留JavaScript交互接口
8. 使用语义化标签

只返回HTML代码，不要解释：
"""
        
        code = await generate(prompt, temperature=0.3)
        return self._clean_code_response(code)
    
    async def _generate_modern_css(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """前端团队：生成现代化CSS样式"""
        
        prompt = f"""
作为前端UI/UX设计师，创建现代化的CSS样式：

应用类型: {analysis.app_type}
功能需求: {', '.join(analysis.features)}

要求：
1. 现代化设计风格（扁平化、渐变、阴影等）
2. 流畅的动画效果（hover、transition等）
3. 响应式布局（flexbox、grid）
4. 美观的配色方案
5. 优雅的字体搭配
6. 自定义组件样式
7. 深色模式支持（可选）
8. 移动端优化

只返回CSS代码，不要解释：
"""
        
        code = await generate(prompt, temperature=0.4)
        return self._clean_code_response(code)
    
    async def _generate_frontend_js(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """前端团队：生成JavaScript交互代码"""
        
        prompt = f"""
作为前端JavaScript工程师，创建交互功能：

应用类型: {analysis.app_type}
功能需求: {', '.join(analysis.features)}

要求：
1. 现代ES6+语法
2. 与后端API交互（fetch请求）
3. DOM操作和事件处理
4. 平滑的页面交互效果
5. 响应式交互行为
6. 错误处理和用户反馈
7. 代码结构清晰
8. 适当的注释

只返回JavaScript代码，不要解释：
"""
        
        code = await generate(prompt, temperature=0.3)
        return self._clean_code_response(code)
    
    def _get_flask_requirements(self, analysis: RequirementAnalysis) -> str:
        """获取Flask项目依赖"""
        requirements = [
            "Flask==2.3.3",
            "Flask-CORS==4.0.0"
        ]
        
        if analysis.database == 'sqlite':
            requirements.append("SQLAlchemy==2.0.23")
            requirements.append("Flask-SQLAlchemy==3.1.1")
        
        return '\n'.join(requirements)
    
    def _get_fastapi_requirements(self, analysis: RequirementAnalysis) -> str:
        """获取FastAPI项目依赖"""
        requirements = [
            "fastapi==0.104.1",
            "uvicorn==0.24.0"
        ]
        
        if analysis.database == 'sqlite':
            requirements.append("SQLAlchemy==2.0.23")
        
        return '\n'.join(requirements)
    
    async def _generate_package_json(self, analysis: RequirementAnalysis, project_name: str) -> str:
        """生成package.json文件"""
        
        return f"""{{
  "name": "{project_name}",
  "version": "1.0.0",
  "description": "Generated {analysis.app_type} application",
  "main": "server.js",
  "scripts": {{
    "start": "node server.js",
    "dev": "node server.js"
  }},
  "dependencies": {{
    "express": "^4.18.2"
  }},
  "keywords": ["{analysis.app_type}"],
  "author": "Generated by ISA MCP",
  "license": "MIT"
}}"""