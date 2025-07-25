"""
快速代码生成分子服务
根据应用规格快速生成完整的项目代码
"""

import os
import uuid
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime

# 导入原子服务
from ..atomic.template_engine import TemplateEngine
from ..atomic.file_operations import FileOperations
from ..atomic.directory_operations import DirectoryOperations


class QuickCodeMolecule:
    """快速代码生成分子服务"""
    
    def __init__(self):
        self.template_engine = TemplateEngine()
        self.file_ops = FileOperations()
        self.dir_ops = DirectoryOperations()
        
    def generate_app_code(self, app_spec: Dict[str, Any]) -> Dict[str, Any]:
        """生成应用代码（支持PRD和传统app_spec）"""
        try:
            # 检查是否传入的是PRD格式
            if "prd" in app_spec and app_spec["prd"] is not None:
                prd = app_spec["prd"]
                app_name = prd.get("app_name", f"quickapp_{uuid.uuid4().hex[:8]}")
                app_type = prd.get("app_type", "web")
                description = prd.get("description", "A quick application")
                port = app_spec.get("port", 5000)
                
                # 从PRD提取技术需求
                tech_req = prd.get("technical_requirements", {})
                framework = tech_req.get("framework", "Flask")
                database = tech_req.get("database", "SQLite")
                dependencies = tech_req.get("dependencies", [])
                
                # 从PRD提取特性信息用于代码生成
                features = prd.get("features", [])
                prd_routes = prd.get("routes", [])
                
            else:
                # 传统app_spec格式
                app_name = app_spec.get("app_name", f"quickapp_{uuid.uuid4().hex[:8]}")
                app_type = app_spec.get("app_type", "web")
                description = app_spec.get("description", "A quick application")
                port = app_spec.get("port", 5000)
                
                # 传统格式的默认值
                framework = "Flask"
                database = "SQLite"
                dependencies = []
                features = []
                prd_routes = []
            
            # 创建项目结构
            project_result = self.create_project_structure(app_name, app_type)
            if not project_result["success"]:
                return project_result
            
            project_path = project_result["project_path"]
            
            # 生成应用代码文件
            code_results = []
            
            # 1. 生成主应用文件（传递PRD信息）
            app_context = {
                "app_name": app_name,
                "app_type": app_type,
                "description": description,
                "port": port,
                "framework": framework,
                "database": database,
                "dependencies": dependencies,
                "features": features,
                "prd_routes": prd_routes
            }
            app_result = self._generate_main_app_with_prd(project_path, app_context)
            code_results.append(("main_app", app_result))
            
            # 2. 生成HTML模板
            html_result = self._generate_html_template(project_path, app_name, description)
            code_results.append(("html_template", html_result))
            
            # 3. 生成requirements.txt（使用PRD依赖）
            req_result = self._generate_requirements_with_prd(project_path, app_type, dependencies)
            code_results.append(("requirements", req_result))
            
            # 4. 生成Dockerfile
            docker_result = self._generate_dockerfile(project_path, port)
            code_results.append(("dockerfile", docker_result))
            
            # 5. 生成docker-compose.yml
            compose_result = self._generate_docker_compose(project_path, app_name, port)
            code_results.append(("docker_compose", compose_result))
            
            # 6. 生成启动脚本
            script_result = self._generate_start_script(project_path, app_name, port)
            code_results.append(("start_script", script_result))
            
            # 检查所有文件是否生成成功
            all_success = all(result[1]["success"] for result in code_results)
            failed_files = [name for name, result in code_results if not result["success"]]
            
            return {
                "success": all_success,
                "app_name": app_name,
                "project_path": project_path,
                "generated_files": len([r for r in code_results if r[1]["success"]]),
                "failed_files": failed_files,
                "code_generation_results": code_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app_spec": app_spec
            }
    
    def create_project_structure(self, app_name: str, app_type: str) -> Dict[str, Any]:
        """创建项目目录结构"""
        try:
            # 基础项目路径
            base_path = "/tmp/quickapps"
            project_path = os.path.join(base_path, app_name)
            
            # 基础目录结构
            directories = ["templates", "static", "static/css", "static/js", "logs"]
            
            # 根据应用类型添加特定目录
            if app_type in ["api", "web"]:
                directories.extend(["config", "models"])
            
            # 创建项目根目录
            root_result = self.dir_ops.create_directory(project_path)
            if not root_result["success"]:
                return root_result
            
            # 创建子目录
            structure_result = self.dir_ops.create_directory_structure(project_path, directories)
            
            return {
                "success": structure_result["success"],
                "project_path": project_path,
                "directories_created": structure_result.get("created_directories", []),
                "structure": directories
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app_name": app_name
            }
    
    def generate_dependencies(self, app_type: str, additional_deps: Optional[list] = None) -> Dict[str, Any]:
        """生成依赖清单"""
        try:
            base_deps = {
                "web": ["Flask==2.3.3", "Jinja2==3.1.2"],
                "api": ["Flask==2.3.3", "Flask-RESTful==0.3.10", "marshmallow==3.20.1"],
                "blog": ["Flask==2.3.3", "Flask-SQLAlchemy==3.0.5", "Markdown==3.5"],
                "dashboard": ["Flask==2.3.3", "pandas==2.1.1", "plotly==5.17.0"],
                "chat": ["Flask==2.3.3", "Flask-SocketIO==5.3.6", "redis==5.0.1"],
                "tool": ["Flask==2.3.3", "python-dateutil==2.8.2"]
            }
            
            # 通用依赖
            common_deps = [
                "Werkzeug==2.3.7",
                "python-dotenv==1.0.0",
                "gunicorn==21.2.0",
                "psutil==5.9.6"
            ]
            
            # 获取特定类型的依赖
            type_deps = base_deps.get(app_type, base_deps["web"])
            
            # 合并所有依赖
            all_deps = type_deps + common_deps
            if additional_deps:
                all_deps.extend(additional_deps)
            
            # 去重
            unique_deps = list(set(all_deps))
            unique_deps.sort()
            
            return {
                "success": True,
                "app_type": app_type,
                "dependencies": unique_deps,
                "total_count": len(unique_deps)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "app_type": app_type
            }
    
    def _generate_main_app_with_prd(self, project_path: str, app_context: Dict[str, Any]) -> Dict[str, Any]:
        """基于PRD生成主应用文件"""
        try:
            app_file_path = os.path.join(project_path, "app.py")
            
            # 从PRD特性生成自定义路由
            custom_routes = self._generate_routes_from_prd(
                app_context.get("features", []),
                app_context.get("prd_routes", []),
                app_context.get("app_type", "web")
            )
            
            # 准备模板变量
            variables = {
                "app_name": app_context.get("app_name", "quickapp"),
                "description": app_context.get("description", "A quick application"),
                "port": app_context.get("port", 5000),
                "timestamp": datetime.now().isoformat(),
                "secret_key": secrets.token_hex(16),
                "custom_routes": custom_routes,
                "framework": app_context.get("framework", "Flask"),
                "database": app_context.get("database", "SQLite")
            }
            
            # 渲染Flask应用模板
            render_result = self.template_engine.render_template("flask_app", variables)
            if not render_result["success"]:
                return render_result
            
            # 写入文件
            return self.file_ops.create_file(app_file_path, render_result["rendered_content"], executable=True)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }

    def _generate_main_app(self, project_path: str, app_name: str, app_type: str, description: str, port: int) -> Dict[str, Any]:
        """生成主应用文件"""
        try:
            app_file_path = os.path.join(project_path, "app.py")
            
            # 生成自定义路由（基于应用类型）
            custom_routes = self._generate_custom_routes(app_type)
            
            # 准备模板变量
            variables = {
                "app_name": app_name,
                "description": description,
                "port": port,
                "timestamp": datetime.now().isoformat(),
                "secret_key": secrets.token_hex(16),
                "custom_routes": custom_routes
            }
            
            # 渲染Flask应用模板
            render_result = self.template_engine.render_template("flask_app", variables)
            if not render_result["success"]:
                return render_result
            
            # 写入文件
            return self.file_ops.create_file(app_file_path, render_result["rendered_content"], executable=True)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    def _generate_html_template(self, project_path: str, app_name: str, description: str) -> Dict[str, Any]:
        """生成HTML模板"""
        try:
            template_path = os.path.join(project_path, "templates", "index.html")
            
            variables = {
                "app_name": app_name,
                "description": description,
                "timestamp": datetime.now().isoformat()
            }
            
            render_result = self.template_engine.render_template("html_index", variables)
            if not render_result["success"]:
                return render_result
            
            return self.file_ops.create_file(template_path, render_result["rendered_content"])
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    def _generate_requirements_with_prd(self, project_path: str, app_type: str, prd_dependencies: List[str]) -> Dict[str, Any]:
        """基于PRD生成requirements.txt"""
        try:
            req_path = os.path.join(project_path, "requirements.txt")
            
            if prd_dependencies:
                # 使用PRD指定的依赖
                requirements_content = "\n".join(prd_dependencies)
            else:
                # 回退到默认依赖生成
                deps_result = self.generate_dependencies(app_type)
                if not deps_result["success"]:
                    return deps_result
                requirements_content = "\n".join(deps_result["dependencies"])
            
            return self.file_ops.create_file(req_path, requirements_content)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }

    def _generate_requirements(self, project_path: str, app_type: str) -> Dict[str, Any]:
        """生成requirements.txt"""
        try:
            req_path = os.path.join(project_path, "requirements.txt")
            
            deps_result = self.generate_dependencies(app_type)
            if not deps_result["success"]:
                return deps_result
            
            requirements_content = "\n".join(deps_result["dependencies"])
            
            variables = {
                "additional_requirements": ""  # 可以根据需要添加额外依赖
            }
            
            render_result = self.template_engine.render_template("requirements", variables)
            if render_result["success"]:
                # 使用模板内容
                content = render_result["rendered_content"]
            else:
                # 使用生成的依赖列表
                content = requirements_content
            
            return self.file_ops.create_file(req_path, content)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    def _generate_dockerfile(self, project_path: str, port: int) -> Dict[str, Any]:
        """生成Dockerfile"""
        try:
            dockerfile_path = os.path.join(project_path, "Dockerfile")
            
            variables = {
                "port": port
            }
            
            render_result = self.template_engine.render_template("dockerfile", variables)
            if not render_result["success"]:
                return render_result
            
            return self.file_ops.create_file(dockerfile_path, render_result["rendered_content"])
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    def _generate_docker_compose(self, project_path: str, app_name: str, port: int) -> Dict[str, Any]:
        """生成docker-compose.yml"""
        try:
            compose_path = os.path.join(project_path, "docker-compose.yml")
            
            variables = {
                "app_name": app_name,
                "port": port,
                "secret_key": secrets.token_hex(16)
            }
            
            render_result = self.template_engine.render_template("docker_compose", variables)
            if not render_result["success"]:
                return render_result
            
            return self.file_ops.create_file(compose_path, render_result["rendered_content"])
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    def _generate_start_script(self, project_path: str, app_name: str, port: int) -> Dict[str, Any]:
        """生成启动脚本"""
        try:
            script_path = os.path.join(project_path, "start.sh")
            
            variables = {
                "app_name": app_name,
                "port": port,
                "timestamp": datetime.now().isoformat()
            }
            
            render_result = self.template_engine.render_template("start_script", variables)
            if not render_result["success"]:
                return render_result
            
            return self.file_ops.create_file(script_path, render_result["rendered_content"], executable=True)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": project_path
            }
    
    def _generate_custom_routes(self, app_type: str) -> str:
        """根据应用类型生成自定义路由"""
        route_templates = {
            "api": '''
@app.route('/api/data')
def get_data():
    """获取数据API"""
    return jsonify({
        "data": "This is sample data",
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    })

@app.route('/api/data', methods=['POST'])
def post_data():
    """提交数据API"""
    data = request.get_json()
    return jsonify({
        "message": "Data received",
        "received_data": data,
        "timestamp": datetime.now().isoformat()
    })
''',
            "blog": '''
@app.route('/posts')
def list_posts():
    """文章列表"""
    sample_posts = [
        {"id": 1, "title": "欢迎使用博客系统", "content": "这是一个示例文章"},
        {"id": 2, "title": "快速开始", "content": "开始使用您的新博客"}
    ]
    return jsonify({"posts": sample_posts})

@app.route('/post/<int:post_id>')
def get_post(post_id):
    """获取单篇文章"""
    return jsonify({
        "id": post_id,
        "title": f"文章 {post_id}",
        "content": "这是文章内容"
    })
''',
            "dashboard": '''
@app.route('/api/stats')
def get_stats():
    """获取统计数据"""
    return jsonify({
        "users": 1234,
        "orders": 567,
        "revenue": 89012,
        "growth": 15.6
    })

@app.route('/api/chart-data')
def get_chart_data():
    """获取图表数据"""
    return jsonify({
        "labels": ["一月", "二月", "三月", "四月", "五月"],
        "data": [65, 59, 80, 81, 56]
    })
''',
            "chat": '''
@app.route('/api/messages')
def get_messages():
    """获取消息"""
    return jsonify({
        "messages": [
            {"user": "系统", "text": "欢迎使用聊天应用", "time": datetime.now().isoformat()}
        ]
    })
''',
            "tool": '''
@app.route('/api/process', methods=['POST'])
def process_data():
    """数据处理工具"""
    data = request.get_json()
    # 示例处理逻辑
    result = {
        "input": data,
        "processed": True,
        "result": "处理完成",
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(result)
'''
        }
        
        return route_templates.get(app_type, '''
@app.route('/api/example')
def example_api():
    """示例API"""
    return jsonify({
        "message": "这是一个示例API",
        "timestamp": datetime.now().isoformat()
    })
''')
    
    def _generate_routes_from_prd(self, features: List[Dict], prd_routes: List[Dict], app_type: str) -> str:
        """从PRD特性生成路由代码"""
        try:
            if not features and not prd_routes:
                # 如果没有PRD特性，回退到传统方法
                return self._generate_custom_routes(app_type)
            
            routes_code = ""
            
            # 从PRD路由生成基础路由
            for route in prd_routes:
                path = route.get("path", "/")
                template = route.get("template", "index.html")
                description = route.get("description", "路由")
                
                if path != "/":  # 主页路由已在模板中
                    route_name = path.strip("/").replace("/", "_") or "page"
                    routes_code += f'''
@app.route('{path}')
def {route_name}():
    """{description}"""
    return render_template('{template}')
'''
            
            # 从特性生成API路由
            for feature in features:
                api_endpoints = feature.get("api_endpoints", [])
                for endpoint in api_endpoints:
                    path = endpoint.get("path", "")
                    method = endpoint.get("method", "GET")
                    desc = endpoint.get("description", "API endpoint")
                    
                    if path.startswith("/api/") and path not in ["/api/info"]:  # 避免重复
                        route_name = path.replace("/api/", "").replace("/", "_").replace("{", "").replace("}", "") or "api"
                        
                        if method == "GET":
                            routes_code += f'''
@app.route('{path}')
def {route_name}():
    """{desc}"""
    return jsonify({{
        "message": "{desc}",
        "data": "Sample data for {path}",
        "timestamp": datetime.now().isoformat()
    }})
'''
                        elif method == "POST":
                            routes_code += f'''
@app.route('{path}', methods=['POST'])
def {route_name}():
    """{desc}"""
    data = request.get_json()
    return jsonify({{
        "message": "{desc}",
        "received_data": data,
        "timestamp": datetime.now().isoformat()
    }})
'''
            
            # 如果没有生成任何路由，使用默认的
            if not routes_code.strip():
                routes_code = self._generate_custom_routes(app_type)
            
            return routes_code
            
        except Exception as e:
            # 出错时回退到传统方法
            return self._generate_custom_routes(app_type)