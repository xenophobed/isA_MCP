"""
项目管理分子服务
组合原子服务来实现项目创建、配置等功能
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# 导入原子服务
from ..atomic.file_operations import FileOperations
from ..atomic.directory_operations import DirectoryOperations
from ..atomic.command_execution import CommandExecution

# 导入AI文本生成服务
import sys
import os
# 添加项目根目录到路径
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
sys.path.insert(0, project_root)

from tools.services.intelligence_service.language.text_generator import generate


class ProjectMolecule:
    """项目管理分子服务"""
    
    def __init__(self):
        self.file_ops = FileOperations()
        self.dir_ops = DirectoryOperations()
        self.cmd_exec = CommandExecution()
    
    async def create_project_workspace(
        self, 
        project_name: str, 
        project_type: str, 
        description: Optional[str] = None,
        base_path: str = "/home/projects"
    ) -> Dict[str, Any]:
        """创建完整的项目工作空间"""
        try:
            results = []
            project_path = os.path.join(base_path, project_name)
            
            # 1. 创建项目根目录
            root_result = self.dir_ops.create_directory(project_path)
            results.append(("create_root_directory", root_result))
            
            if not root_result["success"]:
                return self._create_result(False, {"results": results}, root_result["error"])
            
            # 2. 使用AI生成项目目录结构
            structure_result = await self._generate_project_structure(project_path, project_type)
            results.append(("create_project_structure", structure_result))
            
            # 3. 生成并创建项目配置文件
            config_result = await self._create_project_config(
                project_path, project_name, project_type, description
            )
            results.append(("create_project_config", config_result))
            
            # 4. 生成并创建README文件
            readme_result = await self._create_readme_file(
                project_path, project_name, project_type, description
            )
            results.append(("create_readme", readme_result))
            
            # 5. 生成基础代码文件
            if project_type in ["web", "api", "python"]:
                code_result = await self._create_basic_code_files(
                    project_path, project_type, project_name
                )
                results.append(("create_basic_code", code_result))
            
            # 检查所有操作是否成功
            all_success = all(result[1]["success"] for result in results)
            
            return self._create_result(all_success, {
                "project_name": project_name,
                "project_path": project_path,
                "project_type": project_type,
                "description": description,
                "operations": results,
                "directories_created": structure_result["data"].get("created_directories", []) if structure_result["success"] else []
            })
            
        except Exception as e:
            return self._create_result(False, error=str(e))
    
    async def _generate_project_structure(self, project_path: str, project_type: str) -> Dict[str, Any]:
        """使用AI生成项目目录结构"""
        try:
            # 构建AI提示
            prompt = f"""Generate a directory structure for a {project_type} project.

Return only a JSON array of directory names to create, like:
["src", "config", "tests", "docs", "static", "templates"]

Consider best practices for {project_type} projects. Include common directories like:
- src (source code)
- tests (test files)  
- docs (documentation)
- config (configuration files)
- logs (log files)

For web projects, also include:
- static (CSS, JS, images)
- templates (HTML templates)

For API projects, also include:
- models (data models)
- routes (API endpoints)
- middleware (middleware functions)

Return only the JSON array, no explanations."""

            # 使用AI生成结构
            structure_json = await generate(prompt, temperature=0.2, max_tokens=300)
            
            # 解析AI生成的结构
            try:
                directories = json.loads(structure_json.strip())
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用默认结构
                directories = ["src", "config", "logs", "docs", "tests"]
                if project_type == "web":
                    directories.extend(["static", "templates", "assets"])
                elif project_type == "api":
                    directories.extend(["models", "routes", "middleware"])
            
            # 创建目录结构
            return self.dir_ops.create_directory_structure(project_path, directories)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_project_config(
        self, 
        project_path: str, 
        project_name: str, 
        project_type: str, 
        description: Optional[str]
    ) -> Dict[str, Any]:
        """创建项目配置文件"""
        config_path = os.path.join(project_path, "config", "project.json")
        
        config_data = {
            "name": project_name,
            "type": project_type,
            "description": description or f"Auto-generated {project_type} project",
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "author": "Terminal Service Auto-Generator",
            "structure": "atomic -> molecules -> organisms"
        }
        
        return self.file_ops.create_file(
            config_path,
            json.dumps(config_data, indent=2)
        )
    
    async def _create_readme_file(
        self, 
        project_path: str, 
        project_name: str, 
        project_type: str, 
        description: Optional[str]
    ) -> Dict[str, Any]:
        """使用AI生成README文件"""
        try:
            readme_path = os.path.join(project_path, "README.md")
            
            # 构建AI提示
            prompt = f"""Create a comprehensive README.md for a {project_type} project named '{project_name}'.

Project details:
- Name: {project_name}
- Type: {project_type}
- Description: {description or f'A {project_type} project'}

Include the following sections:
1. Project title and description
2. Installation instructions
3. Usage examples
4. Project structure
5. Contributing guidelines
6. License information

Make it professional and well-formatted with proper Markdown syntax.
Only return the README content, no explanations."""

            # 使用AI生成README内容
            readme_content = await generate(prompt, temperature=0.3, max_tokens=1000)
            
            return self.file_ops.create_file(readme_path, readme_content)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_basic_code_files(
        self, 
        project_path: str, 
        project_type: str, 
        project_name: str
    ) -> Dict[str, Any]:
        """生成基础代码文件"""
        try:
            results = []
            
            if project_type == "python" or project_type == "api":
                # 创建main.py
                main_result = await self._create_main_file(project_path, project_type, project_name)
                results.append(("main_file", main_result))
                
                # 创建requirements.txt
                req_result = await self._create_requirements_file(project_path, project_type)
                results.append(("requirements_file", req_result))
            
            elif project_type == "web":
                # 创建app.py (Flask应用)
                app_result = await self._create_web_app_file(project_path, project_name)
                results.append(("app_file", app_result))
                
                # 创建基础HTML模板
                template_result = await self._create_html_template(project_path, project_name)
                results.append(("template_file", template_result))
            
            all_success = all(result[1]["success"] for result in results)
            
            return {
                "success": all_success,
                "files_created": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_main_file(self, project_path: str, project_type: str, project_name: str) -> Dict[str, Any]:
        """创建主程序文件"""
        try:
            main_path = os.path.join(project_path, "src", "main.py")
            
            prompt = f"""Create a main.py file for a {project_type} project named '{project_name}'.

Requirements:
1. Include proper imports and error handling
2. Add docstrings and comments
3. Follow PEP 8 style guidelines
4. Make it production-ready
5. Include a main function and if __name__ == "__main__" guard
6. Add basic logging setup

For API projects, include a simple Flask or FastAPI setup.
Only return the Python code, no explanations."""

            code_content = await generate(prompt, temperature=0.3, max_tokens=800)
            
            return self.file_ops.create_file(main_path, code_content, executable=True)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_requirements_file(self, project_path: str, project_type: str) -> Dict[str, Any]:
        """创建requirements.txt文件"""
        try:
            req_path = os.path.join(project_path, "requirements.txt")
            
            prompt = f"""Create a requirements.txt file for a {project_type} project.

Include common packages for {project_type} development:
- For API projects: Flask or FastAPI, requests, python-dotenv
- For general Python: pytest, black, flake8
- Add version numbers for stability

Only return the requirements content, no explanations."""

            req_content = await generate(prompt, temperature=0.2, max_tokens=300)
            
            return self.file_ops.create_file(req_path, req_content)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_web_app_file(self, project_path: str, project_name: str) -> Dict[str, Any]:
        """创建Web应用文件"""
        try:
            app_path = os.path.join(project_path, "src", "app.py")
            
            prompt = f"""Create a Flask web application file for project '{project_name}'.

Requirements:
1. Import Flask and necessary modules
2. Create Flask app instance
3. Add basic routes (/, /health, /api/status)
4. Include error handling
5. Add logging setup
6. Make it production-ready with proper configuration
7. Include if __name__ == "__main__" with app.run()

Only return the Python code, no explanations."""

            app_content = await generate(prompt, temperature=0.3, max_tokens=800)
            
            return self.file_ops.create_file(app_path, app_content, executable=True)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_html_template(self, project_path: str, project_name: str) -> Dict[str, Any]:
        """创建HTML模板文件"""
        try:
            template_path = os.path.join(project_path, "templates", "index.html")
            
            prompt = f"""Create an HTML template file for project '{project_name}'.

Requirements:
1. Use modern HTML5 structure
2. Include responsive CSS
3. Add basic JavaScript for interactivity
4. Make it visually appealing
5. Include proper meta tags
6. Add navigation and basic content structure

Only return the HTML code, no explanations."""

            html_content = await generate(prompt, temperature=0.4, max_tokens=1000)
            
            return self.file_ops.create_file(template_path, html_content)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_result(self, success: bool, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> Dict[str, Any]:
        """创建标准化结果"""
        return {
            "success": success,
            "data": data or {},
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "molecule_type": "ProjectMolecule"
        } 