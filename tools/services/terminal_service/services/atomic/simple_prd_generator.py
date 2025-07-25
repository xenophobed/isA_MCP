#!/usr/bin/env python3
"""
简单PRD生成器 - 原子服务
使用AI和模板生成定制化的Product Requirements Document
"""

import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

# 导入AI文本生成服务
import sys
import os
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
sys.path.insert(0, project_root)

from tools.services.intelligence_service.language.text_generator import TextGenerator

class SimplePRDGenerator:
    """简单PRD生成器原子服务"""
    
    def __init__(self):
        self.text_generator = TextGenerator()
        self.templates = {
            "blog": self._get_blog_template,
            "ecommerce": self._get_ecommerce_template,
            "dashboard": self._get_dashboard_template,
            "tool": self._get_tool_template,
            "api": self._get_api_template,
            "chat": self._get_chat_template,
            "web": self._get_web_template
        }
    
    async def generate_prd(self, 
                          user_description: str,
                          app_type: str,
                          app_name: Optional[str] = None) -> Dict[str, Any]:
        """
        使用AI根据用户需求生成定制化PRD
        
        Args:
            user_description: 用户的自然语言需求描述
            app_type: 应用类型 (blog, ecommerce, dashboard, tool, api, chat, web)
            app_name: 应用名称 (可选)
            
        Returns:
            包含AI生成的定制化PRD的结果字典
        """
        try:
            # 获取参考模板
            template_func = self.templates.get(app_type, self._get_web_template)
            reference_template = template_func()
            
            # 使用AI生成定制化PRD
            ai_prd = await self._generate_prd_with_ai(user_description, app_type, reference_template)
            
            if ai_prd["success"]:
                prd = ai_prd["prd"]
                
                # 设置应用名称
                if app_name:
                    prd["app_name"] = app_name
                elif "app_name" not in prd or not prd["app_name"]:
                    prd["app_name"] = f"{app_type}_app_{uuid.uuid4().hex[:8]}"
                
                # 添加元数据
                prd["metadata"] = {
                    "generated_by": "SimplePRDGenerator",
                    "generation_method": "ai_structured_prompting",
                    "template_version": "1.0.0",
                    "created_at": datetime.now().isoformat(),
                    "app_type": app_type,
                    "user_description": user_description
                }
                
                return {
                    "success": True,
                    "prd": prd,
                    "generation_method": "ai_guided",
                    "template_type": app_type,
                    "customized": True
                }
            else:
                # AI生成失败，回退到参考模板
                return self._fallback_to_template(reference_template, user_description, app_type, app_name)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "user_description": user_description,
                "app_type": app_type,
                "available_types": list(self.templates.keys())
            }
    
    async def _generate_prd_with_ai(self, description: str, app_type: str, reference_template: Dict) -> Dict[str, Any]:
        """使用AI生成定制化PRD"""
        try:
            prompt = f"""Based on this user request: "{description}"

Generate a detailed Product Requirements Document in JSON format.

Use this template structure as reference but customize for the user's specific needs:
{json.dumps(reference_template, indent=2, ensure_ascii=False)}

Generate a complete PRD that:
1. Adapts the template structure to match user requirements
2. Adds/removes/modifies features based on user needs  
3. Specifies exact API endpoints needed
4. Defines precise database schema
5. Details UI components and their interactions
6. Includes specific technical implementation details

User Requirements: "{description}"
App Type: {app_type}

Return a JSON with this structure:
{{
  "app_name": "suggested_name_based_on_description",
  "app_type": "{app_type}",
  "description": "detailed_description_based_on_user_needs",
  "features": [
    {{
      "id": "feature_id",
      "name": "Feature Name",
      "description": "What this feature does specifically for user needs",
      "priority": "high|medium|low",
      "user_stories": ["As a user, I want to..."],
      "api_endpoints": [
        {{"path": "/api/endpoint", "method": "GET|POST|PUT|DELETE", "description": "specific purpose"}}
      ],
      "ui_components": [
        {{"name": "ComponentName", "type": "form|button|table|etc", "description": "specific UI behavior"}}
      ],
      "database_models": [
        {{"name": "ModelName", "fields": {{"field_name": "field_type"}}, "relationships": []}}
      ]
    }}
  ],
  "technical_requirements": {{
    "framework": "Flask",
    "database": "SQLite|PostgreSQL|Redis",
    "deployment": "Docker",
    "dependencies": ["specific_packages_needed"]
  }},
  "ui_design": {{
    "theme": "design_style_matching_user_needs",
    "responsive": true,
    "layout": "layout_type",
    "components": ["specific_UI_sections"]
  }},
  "routes": [
    {{"path": "/specific/route", "template": "template.html", "description": "page purpose"}}
  ]
}}

Focus on being specific about user's actual requirements. If user mentions specific features, include them. If user mentions specific technologies, incorporate them.

Return only valid JSON, no explanations."""

            ai_response = await self.text_generator.generate(
                prompt, 
                temperature=0.3, 
                max_tokens=3000
            )
            
            try:
                prd = json.loads(ai_response.strip())
                return {
                    "success": True,
                    "prd": prd,
                    "generation_method": "ai_structured_prompting"
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"AI response JSON decode error: {str(e)}",
                    "raw_response": ai_response[:500]  # 截取前500字符用于调试
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"AI generation error: {str(e)}"
            }
    
    def _fallback_to_template(self, template: Dict, description: str, app_type: str, app_name: Optional[str]) -> Dict[str, Any]:
        """AI失败时的模板回退方案"""
        if app_name:
            template["app_name"] = app_name
        else:
            template["app_name"] = f"{app_type}_app_{uuid.uuid4().hex[:8]}"
        
        template["description"] = description
        template["metadata"] = {
            "generated_by": "SimplePRDGenerator",
            "generation_method": "template_fallback",
            "template_version": "1.0.0", 
            "created_at": datetime.now().isoformat(),
            "app_type": app_type,
            "user_description": description
        }
        
        return {
            "success": True,
            "prd": template,
            "generation_method": "template_fallback",
            "template_type": app_type,
            "customized": False
        }
    
    def get_available_templates(self) -> Dict[str, Any]:
        """获取所有可用模板信息"""
        templates_info = {}
        
        for app_type in self.templates.keys():
            template = self.templates[app_type]()
            templates_info[app_type] = {
                "description": template.get("description", ""),
                "features_count": len(template.get("features", [])),
                "main_features": [f["name"] for f in template.get("features", [])[:3]],
                "tech_stack": template.get("technical_requirements", {}).get("dependencies", [])
            }
        
        return {
            "success": True,
            "available_templates": templates_info,
            "total_templates": len(templates_info)
        }
    
    def _get_customizable_fields(self, app_type: str) -> Dict[str, Any]:
        """获取可定制字段信息"""
        return {
            "basic_info": ["app_name", "description"],
            "features": ["可以添加、删除或修改功能"],
            "api_endpoints": ["可以定制API路径和参数"],
            "ui_components": ["可以调整UI组件和布局"],
            "tech_stack": ["可以修改技术栈和依赖"]
        }
    
    def _get_blog_template(self) -> Dict[str, Any]:
        """博客应用PRD模板"""
        return {
            "app_name": "blog_app",
            "app_type": "blog",
            "description": "个人博客网站，支持文章发布和管理",
            "features": [
                {
                    "id": "blog_001",
                    "name": "文章管理",
                    "description": "创建、编辑、删除和发布博客文章",
                    "priority": "high",
                    "user_stories": [
                        "作为作者，我想创建新的博客文章",
                        "作为作者，我想编辑已发布的文章",
                        "作为访客，我想浏览文章列表",
                        "作为访客，我想阅读文章详情"
                    ],
                    "api_endpoints": [
                        {"path": "/api/posts", "method": "GET", "description": "获取文章列表"},
                        {"path": "/api/posts", "method": "POST", "description": "创建新文章"},
                        {"path": "/api/posts/{id}", "method": "GET", "description": "获取文章详情"},
                        {"path": "/api/posts/{id}", "method": "PUT", "description": "更新文章"},
                        {"path": "/api/posts/{id}", "method": "DELETE", "description": "删除文章"}
                    ],
                    "ui_components": [
                        {"name": "PostEditor", "type": "form", "description": "Markdown文章编辑器"},
                        {"name": "PostList", "type": "list", "description": "文章列表展示"},
                        {"name": "PostDetail", "type": "page", "description": "文章详情页面"},
                        {"name": "PostCard", "type": "card", "description": "文章卡片组件"}
                    ],
                    "database_models": [
                        {
                            "name": "Post",
                            "fields": {
                                "id": "Integer",
                                "title": "String(200)",
                                "content": "Text",
                                "summary": "String(500)", 
                                "status": "String(20)",
                                "created_at": "DateTime",
                                "updated_at": "DateTime",
                                "published_at": "DateTime"
                            }
                        }
                    ]
                },
                {
                    "id": "blog_002",
                    "name": "分类标签",
                    "description": "文章分类和标签管理",
                    "priority": "medium",
                    "user_stories": [
                        "作为作者，我想为文章添加分类",
                        "作为访客，我想按分类浏览文章",
                        "作为访客，我想通过标签查找相关文章"
                    ],
                    "api_endpoints": [
                        {"path": "/api/categories", "method": "GET", "description": "获取分类列表"},
                        {"path": "/api/tags", "method": "GET", "description": "获取标签列表"},
                        {"path": "/api/posts/category/{id}", "method": "GET", "description": "按分类获取文章"}
                    ],
                    "ui_components": [
                        {"name": "CategoryNav", "type": "navigation", "description": "分类导航"},
                        {"name": "TagCloud", "type": "component", "description": "标签云"},
                        {"name": "TagFilter", "type": "filter", "description": "标签筛选器"}
                    ],
                    "database_models": [
                        {
                            "name": "Category",
                            "fields": {
                                "id": "Integer",
                                "name": "String(100)",
                                "description": "String(500)"
                            }
                        },
                        {
                            "name": "Tag", 
                            "fields": {
                                "id": "Integer",
                                "name": "String(50)",
                                "color": "String(7)"
                            }
                        }
                    ]
                }
            ],
            "technical_requirements": {
                "framework": "Flask",
                "database": "SQLite",
                "deployment": "Docker",
                "dependencies": ["Flask==2.3.3", "SQLAlchemy==2.0.23", "Markdown==3.5", "Flask-Migrate==4.0.5"]
            },
            "ui_design": {
                "theme": "clean and minimal",
                "responsive": True,
                "layout": "single column with sidebar",
                "components": ["header", "navigation", "main content", "sidebar", "footer"]
            },
            "routes": [
                {"path": "/", "template": "index.html", "description": "主页 - 文章列表"},
                {"path": "/post/<int:id>", "template": "post_detail.html", "description": "文章详情页"},
                {"path": "/category/<int:id>", "template": "category.html", "description": "分类页面"},
                {"path": "/admin", "template": "admin.html", "description": "管理后台"}
            ]
        }
    
    def _get_ecommerce_template(self) -> Dict[str, Any]:
        """电商应用PRD模板"""
        return {
            "app_name": "ecommerce_app",
            "app_type": "ecommerce",
            "description": "在线商店，支持商品展示、购物车和订单管理",
            "features": [
                {
                    "id": "ecom_001",
                    "name": "商品目录",
                    "description": "展示和管理商品信息",
                    "priority": "high",
                    "user_stories": [
                        "作为客户，我想浏览商品列表",
                        "作为客户，我想查看商品详情",
                        "作为客户，我想搜索商品",
                        "作为管理员，我想添加新商品"
                    ],
                    "api_endpoints": [
                        {"path": "/api/products", "method": "GET", "description": "获取商品列表"},
                        {"path": "/api/products/{id}", "method": "GET", "description": "获取商品详情"},
                        {"path": "/api/products/search", "method": "GET", "description": "搜索商品"},
                        {"path": "/api/products", "method": "POST", "description": "添加商品(管理员)"}
                    ],
                    "ui_components": [
                        {"name": "ProductGrid", "type": "grid", "description": "商品网格展示"},
                        {"name": "ProductCard", "type": "card", "description": "商品卡片"},
                        {"name": "ProductDetail", "type": "page", "description": "商品详情页"},
                        {"name": "SearchBar", "type": "input", "description": "商品搜索框"}
                    ],
                    "database_models": [
                        {
                            "name": "Product",
                            "fields": {
                                "id": "Integer",
                                "name": "String(200)",
                                "description": "Text",
                                "price": "Decimal(10,2)",
                                "stock": "Integer",
                                "image_url": "String(500)",
                                "category_id": "Integer",
                                "created_at": "DateTime"
                            }
                        }
                    ]
                },
                {
                    "id": "ecom_002", 
                    "name": "购物车",
                    "description": "管理用户选择的商品",
                    "priority": "high",
                    "user_stories": [
                        "作为客户，我想添加商品到购物车",
                        "作为客户，我想查看购物车内容",
                        "作为客户，我想修改商品数量",
                        "作为客户，我想删除购物车商品"
                    ],
                    "api_endpoints": [
                        {"path": "/api/cart", "method": "GET", "description": "获取购物车"},
                        {"path": "/api/cart/items", "method": "POST", "description": "添加商品到购物车"},
                        {"path": "/api/cart/items/{id}", "method": "PUT", "description": "更新商品数量"},
                        {"path": "/api/cart/items/{id}", "method": "DELETE", "description": "删除购物车商品"}
                    ],
                    "ui_components": [
                        {"name": "CartSidebar", "type": "sidebar", "description": "购物车侧边栏"},
                        {"name": "CartItem", "type": "component", "description": "购物车商品项"},
                        {"name": "CartSummary", "type": "component", "description": "购物车总结"},
                        {"name": "CheckoutButton", "type": "button", "description": "结账按钮"}
                    ],
                    "database_models": [
                        {
                            "name": "CartItem",
                            "fields": {
                                "id": "Integer",
                                "session_id": "String(100)",
                                "product_id": "Integer", 
                                "quantity": "Integer",
                                "added_at": "DateTime"
                            }
                        }
                    ]
                },
                {
                    "id": "ecom_003",
                    "name": "订单管理",
                    "description": "处理客户订单和支付",
                    "priority": "high",
                    "user_stories": [
                        "作为客户，我想下单购买商品",
                        "作为客户，我想查看订单历史",
                        "作为管理员，我想管理订单状态"
                    ],
                    "api_endpoints": [
                        {"path": "/api/orders", "method": "POST", "description": "创建订单"},
                        {"path": "/api/orders/{id}", "method": "GET", "description": "获取订单详情"},
                        {"path": "/api/orders", "method": "GET", "description": "获取订单列表"}
                    ],
                    "ui_components": [
                        {"name": "CheckoutForm", "type": "form", "description": "结账表单"},
                        {"name": "OrderSummary", "type": "component", "description": "订单摘要"},
                        {"name": "OrderHistory", "type": "list", "description": "订单历史"}
                    ],
                    "database_models": [
                        {
                            "name": "Order",
                            "fields": {
                                "id": "Integer",
                                "customer_email": "String(100)",
                                "total_amount": "Decimal(10,2)",
                                "status": "String(20)",
                                "created_at": "DateTime"
                            }
                        }
                    ]
                }
            ],
            "technical_requirements": {
                "framework": "Flask",
                "database": "PostgreSQL",
                "deployment": "Docker",
                "dependencies": ["Flask==2.3.3", "SQLAlchemy==2.0.23", "Stripe==7.8.0", "Flask-WTF==1.2.1"]
            },
            "ui_design": {
                "theme": "modern ecommerce",
                "responsive": True,
                "layout": "multi-column with filters",
                "components": ["header", "search", "product grid", "cart", "footer"]
            },
            "routes": [
                {"path": "/", "template": "index.html", "description": "商店主页"},
                {"path": "/product/<int:id>", "template": "product_detail.html", "description": "商品详情"},
                {"path": "/cart", "template": "cart.html", "description": "购物车页面"},
                {"path": "/checkout", "template": "checkout.html", "description": "结账页面"}
            ]
        }
    
    def _get_tool_template(self) -> Dict[str, Any]:
        """工具应用PRD模板"""
        return {
            "app_name": "utility_tool",
            "app_type": "tool",
            "description": "实用工具应用，提供数据处理和转换功能",
            "features": [
                {
                    "id": "tool_001",
                    "name": "数据处理",
                    "description": "核心数据处理和转换功能",
                    "priority": "high",
                    "user_stories": [
                        "作为用户，我想上传数据文件",
                        "作为用户，我想选择处理方式",
                        "作为用户，我想查看处理结果",
                        "作为用户，我想下载处理后的数据"
                    ],
                    "api_endpoints": [
                        {"path": "/api/upload", "method": "POST", "description": "上传数据文件"},
                        {"path": "/api/process", "method": "POST", "description": "处理数据"},
                        {"path": "/api/result/{id}", "method": "GET", "description": "获取处理结果"},
                        {"path": "/api/download/{id}", "method": "GET", "description": "下载结果文件"}
                    ],
                    "ui_components": [
                        {"name": "FileUpload", "type": "input", "description": "文件上传组件"},
                        {"name": "ProcessingOptions", "type": "form", "description": "处理选项表单"},
                        {"name": "ResultDisplay", "type": "component", "description": "结果展示"},
                        {"name": "DownloadButton", "type": "button", "description": "下载按钮"}
                    ],
                    "database_models": [
                        {
                            "name": "ProcessingJob",
                            "fields": {
                                "id": "Integer",
                                "filename": "String(200)",
                                "processing_type": "String(50)",
                                "status": "String(20)",
                                "input_data": "Text",
                                "output_data": "Text",
                                "created_at": "DateTime",
                                "completed_at": "DateTime"
                            }
                        }
                    ]
                }
            ],
            "technical_requirements": {
                "framework": "Flask",
                "database": "SQLite",
                "deployment": "Docker",
                "dependencies": ["Flask==2.3.3", "pandas==2.1.4", "numpy==1.25.2", "openpyxl==3.1.2"]
            },
            "ui_design": {
                "theme": "functional and clean",
                "responsive": True,
                "layout": "single column centered",
                "components": ["header", "upload area", "processing options", "results area", "footer"]
            },
            "routes": [
                {"path": "/", "template": "index.html", "description": "工具主页"},
                {"path": "/upload", "template": "upload.html", "description": "文件上传页"},
                {"path": "/result/<int:id>", "template": "result.html", "description": "结果展示页"}
            ]
        }
    
    def _get_dashboard_template(self) -> Dict[str, Any]:
        """仪表板应用PRD模板"""
        return {
            "app_name": "analytics_dashboard",
            "app_type": "dashboard", 
            "description": "数据分析仪表板，展示关键指标和图表",
            "features": [
                {
                    "id": "dash_001",
                    "name": "关键指标展示",
                    "description": "显示重要的业务指标卡片",
                    "priority": "high",
                    "user_stories": [
                        "作为用户，我想查看关键指标概览",
                        "作为用户，我想看到指标变化趋势",
                        "作为用户，我想自定义显示的指标"
                    ],
                    "api_endpoints": [
                        {"path": "/api/metrics", "method": "GET", "description": "获取关键指标"},
                        {"path": "/api/metrics/trends", "method": "GET", "description": "获取指标趋势"},
                        {"path": "/api/metrics/config", "method": "POST", "description": "配置显示指标"}
                    ],
                    "ui_components": [
                        {"name": "MetricCard", "type": "card", "description": "指标展示卡片"},
                        {"name": "TrendIndicator", "type": "component", "description": "趋势指示器"},
                        {"name": "MetricGrid", "type": "grid", "description": "指标网格布局"}
                    ],
                    "database_models": [
                        {
                            "name": "Metric",
                            "fields": {
                                "id": "Integer",
                                "name": "String(100)",
                                "value": "Float",
                                "unit": "String(20)",
                                "category": "String(50)",
                                "timestamp": "DateTime"
                            }
                        }
                    ]
                },
                {
                    "id": "dash_002",
                    "name": "数据可视化",
                    "description": "各种图表和数据可视化组件",
                    "priority": "high",
                    "user_stories": [
                        "作为用户，我想查看数据趋势图",
                        "作为用户，我想查看数据分布图",
                        "作为用户，我想筛选时间范围"
                    ],
                    "api_endpoints": [
                        {"path": "/api/charts/line", "method": "GET", "description": "获取线图数据"},
                        {"path": "/api/charts/pie", "method": "GET", "description": "获取饼图数据"},
                        {"path": "/api/charts/bar", "method": "GET", "description": "获取柱状图数据"}
                    ],
                    "ui_components": [
                        {"name": "LineChart", "type": "chart", "description": "线性图表"},
                        {"name": "PieChart", "type": "chart", "description": "饼图"},
                        {"name": "BarChart", "type": "chart", "description": "柱状图"},
                        {"name": "DateRangePicker", "type": "input", "description": "日期范围选择器"}
                    ],
                    "database_models": [
                        {
                            "name": "ChartData",
                            "fields": {
                                "id": "Integer",
                                "chart_type": "String(50)",
                                "label": "String(100)",
                                "value": "Float",
                                "date": "Date",
                                "category": "String(50)"
                            }
                        }
                    ]
                }
            ],
            "technical_requirements": {
                "framework": "Flask",
                "database": "PostgreSQL",
                "deployment": "Docker",
                "dependencies": ["Flask==2.3.3", "SQLAlchemy==2.0.23", "Chart.js==4.4.0", "Bootstrap==5.3.2"]
            },
            "ui_design": {
                "theme": "professional dashboard",
                "responsive": True,
                "layout": "grid layout with sidebar",
                "components": ["sidebar navigation", "main dashboard", "chart grid", "filter panel"]
            },
            "routes": [
                {"path": "/", "template": "dashboard.html", "description": "主仪表板"},
                {"path": "/metrics", "template": "metrics.html", "description": "指标详情页"},
                {"path": "/charts", "template": "charts.html", "description": "图表页面"}
            ]
        }
    
    def _get_api_template(self) -> Dict[str, Any]:
        """API服务PRD模板"""
        return {
            "app_name": "rest_api_service",
            "app_type": "api",
            "description": "RESTful API服务，提供数据接口和文档",
            "features": [
                {
                    "id": "api_001", 
                    "name": "数据API",
                    "description": "提供标准的RESTful数据接口",
                    "priority": "high",
                    "user_stories": [
                        "作为开发者，我想获取数据列表",
                        "作为开发者，我想创建新数据",
                        "作为开发者，我想更新现有数据",
                        "作为开发者，我想删除数据"
                    ],
                    "api_endpoints": [
                        {"path": "/api/v1/data", "method": "GET", "description": "获取数据列表"},
                        {"path": "/api/v1/data", "method": "POST", "description": "创建新数据"},
                        {"path": "/api/v1/data/{id}", "method": "GET", "description": "获取单条数据"},
                        {"path": "/api/v1/data/{id}", "method": "PUT", "description": "更新数据"},
                        {"path": "/api/v1/data/{id}", "method": "DELETE", "description": "删除数据"}
                    ],
                    "ui_components": [
                        {"name": "ApiDocs", "type": "page", "description": "API文档页面"},
                        {"name": "ApiExplorer", "type": "component", "description": "API测试工具"}
                    ],
                    "database_models": [
                        {
                            "name": "DataModel",
                            "fields": {
                                "id": "Integer",
                                "name": "String(100)",
                                "description": "Text",
                                "data": "JSON",
                                "status": "String(20)",
                                "created_at": "DateTime",
                                "updated_at": "DateTime"
                            }
                        }
                    ]
                },
                {
                    "id": "api_002",
                    "name": "API文档",
                    "description": "自动生成的API文档和测试界面",
                    "priority": "medium",
                    "user_stories": [
                        "作为开发者，我想查看API文档",
                        "作为开发者，我想测试API接口",
                        "作为开发者，我想查看接口示例"
                    ],
                    "api_endpoints": [
                        {"path": "/docs", "method": "GET", "description": "API文档页面"},
                        {"path": "/api/v1/openapi.json", "method": "GET", "description": "OpenAPI规范"}
                    ],
                    "ui_components": [
                        {"name": "SwaggerUI", "type": "component", "description": "Swagger文档界面"},
                        {"name": "ApiTester", "type": "form", "description": "API测试表单"}
                    ],
                    "database_models": []
                }
            ],
            "technical_requirements": {
                "framework": "Flask",
                "database": "PostgreSQL",
                "deployment": "Docker",
                "dependencies": ["Flask==2.3.3", "Flask-RESTful==0.3.10", "marshmallow==3.20.2", "flasgger==0.9.7"]
            },
            "ui_design": {
                "theme": "api documentation",
                "responsive": True,
                "layout": "documentation layout",
                "components": ["api explorer", "documentation", "examples", "response viewer"]
            },
            "routes": [
                {"path": "/", "template": "index.html", "description": "API主页"},
                {"path": "/docs", "template": "swagger.html", "description": "API文档"},
                {"path": "/examples", "template": "examples.html", "description": "使用示例"}
            ]
        }
    
    def _get_chat_template(self) -> Dict[str, Any]:
        """聊天应用PRD模板"""
        return {
            "app_name": "chat_application",
            "app_type": "chat",
            "description": "实时聊天应用，支持多人聊天和消息历史",
            "features": [
                {
                    "id": "chat_001",
                    "name": "实时消息",
                    "description": "发送和接收实时聊天消息",
                    "priority": "high",
                    "user_stories": [
                        "作为用户，我想发送消息",
                        "作为用户，我想实时接收消息",
                        "作为用户，我想查看消息历史",
                        "作为用户，我想知道消息发送状态"
                    ],
                    "api_endpoints": [
                        {"path": "/api/messages", "method": "GET", "description": "获取消息历史"},
                        {"path": "/api/messages", "method": "POST", "description": "发送消息"},
                        {"path": "/ws/chat", "method": "WebSocket", "description": "实时消息连接"}
                    ],
                    "ui_components": [
                        {"name": "MessageList", "type": "list", "description": "消息列表"},
                        {"name": "MessageInput", "type": "input", "description": "消息输入框"},
                        {"name": "MessageBubble", "type": "component", "description": "消息气泡"},
                        {"name": "TypingIndicator", "type": "component", "description": "正在输入指示器"}
                    ],
                    "database_models": [
                        {
                            "name": "Message",
                            "fields": {
                                "id": "Integer",
                                "room": "String(100)",
                                "sender": "String(100)",
                                "content": "Text",
                                "message_type": "String(20)",
                                "timestamp": "DateTime"
                            }
                        }
                    ]
                },
                {
                    "id": "chat_002",
                    "name": "用户管理",
                    "description": "管理在线用户和聊天室",
                    "priority": "medium",
                    "user_stories": [
                        "作为用户，我想设置昵称",
                        "作为用户，我想看到在线用户列表",
                        "作为用户，我想加入不同聊天室"
                    ],
                    "api_endpoints": [
                        {"path": "/api/users/online", "method": "GET", "description": "获取在线用户"},
                        {"path": "/api/rooms", "method": "GET", "description": "获取聊天室列表"},
                        {"path": "/api/rooms/{id}/join", "method": "POST", "description": "加入聊天室"}
                    ],
                    "ui_components": [
                        {"name": "UserList", "type": "sidebar", "description": "在线用户列表"},
                        {"name": "RoomSelector", "type": "dropdown", "description": "聊天室选择器"},
                        {"name": "UserProfile", "type": "modal", "description": "用户资料"}
                    ],
                    "database_models": [
                        {
                            "name": "User",
                            "fields": {
                                "id": "Integer",
                                "nickname": "String(50)",
                                "session_id": "String(100)",
                                "last_seen": "DateTime",
                                "current_room": "String(100)"
                            }
                        },
                        {
                            "name": "Room",
                            "fields": {
                                "id": "Integer",
                                "name": "String(100)",
                                "description": "String(500)",
                                "created_at": "DateTime"
                            }
                        }
                    ]
                }
            ],
            "technical_requirements": {
                "framework": "Flask",
                "database": "Redis",
                "deployment": "Docker",
                "dependencies": ["Flask==2.3.3", "Flask-SocketIO==5.3.6", "Redis==5.0.1", "python-socketio==5.10.0"]
            },
            "ui_design": {
                "theme": "modern chat interface",
                "responsive": True,
                "layout": "chat layout with sidebar",
                "components": ["chat window", "message input", "user list", "room selector"]
            },
            "routes": [
                {"path": "/", "template": "chat.html", "description": "聊天主界面"},
                {"path": "/rooms", "template": "rooms.html", "description": "聊天室列表"}
            ]
        }
    
    def _get_web_template(self) -> Dict[str, Any]:
        """默认Web应用PRD模板"""
        return {
            "app_name": "web_application", 
            "app_type": "web",
            "description": "通用Web应用，提供基础网站功能",
            "features": [
                {
                    "id": "web_001",
                    "name": "基础页面",
                    "description": "提供基本的网站页面和导航",
                    "priority": "high",
                    "user_stories": [
                        "作为访客，我想访问网站主页",
                        "作为访客，我想了解网站信息",
                        "作为访客，我想联系网站管理员",
                        "作为访客，我想在页面间导航"
                    ],
                    "api_endpoints": [
                        {"path": "/", "method": "GET", "description": "网站主页"},
                        {"path": "/about", "method": "GET", "description": "关于页面"},
                        {"path": "/contact", "method": "GET", "description": "联系页面"},
                        {"path": "/api/contact", "method": "POST", "description": "提交联系表单"}
                    ],
                    "ui_components": [
                        {"name": "Navigation", "type": "nav", "description": "主导航栏"},
                        {"name": "Hero", "type": "section", "description": "首页横幅"},
                        {"name": "ContactForm", "type": "form", "description": "联系表单"},
                        {"name": "Footer", "type": "footer", "description": "页脚"}
                    ],
                    "database_models": [
                        {
                            "name": "ContactMessage",
                            "fields": {
                                "id": "Integer",
                                "name": "String(100)",
                                "email": "String(100)",
                                "subject": "String(200)", 
                                "message": "Text",
                                "created_at": "DateTime"
                            }
                        }
                    ]
                },
                {
                    "id": "web_002",
                    "name": "内容管理",
                    "description": "基础的内容展示和管理",
                    "priority": "medium",
                    "user_stories": [
                        "作为管理员，我想更新网站内容",
                        "作为访客，我想查看最新内容",
                        "作为访客，我想搜索网站内容"
                    ],
                    "api_endpoints": [
                        {"path": "/api/content", "method": "GET", "description": "获取内容列表"},
                        {"path": "/api/content/{id}", "method": "GET", "description": "获取内容详情"},
                        {"path": "/api/search", "method": "GET", "description": "搜索内容"}
                    ],
                    "ui_components": [
                        {"name": "ContentList", "type": "list", "description": "内容列表"},
                        {"name": "ContentCard", "type": "card", "description": "内容卡片"},
                        {"name": "SearchBox", "type": "input", "description": "搜索框"}
                    ],
                    "database_models": [
                        {
                            "name": "Content",
                            "fields": {
                                "id": "Integer",
                                "title": "String(200)",
                                "body": "Text",
                                "type": "String(50)",
                                "published": "Boolean",
                                "created_at": "DateTime"
                            }
                        }
                    ]
                }
            ],
            "technical_requirements": {
                "framework": "Flask",
                "database": "SQLite",
                "deployment": "Docker",
                "dependencies": ["Flask==2.3.3", "SQLAlchemy==2.0.23", "WTForms==3.1.1", "Flask-WTF==1.2.1"]
            },
            "ui_design": {
                "theme": "clean and professional",
                "responsive": True,
                "layout": "standard website layout",
                "components": ["header", "navigation", "main content", "sidebar", "footer"]
            },
            "routes": [
                {"path": "/", "template": "index.html", "description": "网站主页"},
                {"path": "/about", "template": "about.html", "description": "关于页面"},
                {"path": "/contact", "template": "contact.html", "description": "联系页面"},
                {"path": "/content", "template": "content.html", "description": "内容页面"}
            ]
        }

# 测试和使用示例
async def test_ai_prd_generator():
    """测试AI驱动的PRD生成器"""
    generator = SimplePRDGenerator()
    
    print("=== 测试AI驱动的SimplePRDGenerator原子服务 ===\n")
    
    # 测试获取可用模板
    templates_info = generator.get_available_templates()
    print("📋 可用模板:")
    for app_type, info in templates_info["available_templates"].items():
        print(f"  {app_type}: {info['description']}")
        print(f"    主要功能: {', '.join(info['main_features'])}")
        print(f"    技术栈: {', '.join(info['tech_stack'][:3])}")
        print()
    
    # 测试AI生成定制化PRD
    test_cases = [
        ("blog", "my_tech_blog", "创建一个技术博客，支持Markdown编辑、代码高亮、评论系统和RSS订阅功能"),
        ("ecommerce", "fashion_store", "开发一个时尚服装在线商店，需要商品展示、尺码选择、愿望清单、促销优惠券和用户评价功能"),
        ("tool", "csv_processor", "构建一个CSV数据处理工具，支持文件上传、数据清洗、格式转换、统计分析和批量导出功能")
    ]
    
    for app_type, app_name, user_description in test_cases:
        print(f"=== AI生成 {app_type} PRD ===")
        print(f"📝 用户需求: {user_description}")
        
        result = await generator.generate_prd(user_description, app_type, app_name)
        
        if result["success"]:
            prd = result["prd"]
            print(f"✅ 生成方法: {result['generation_method']}")
            print(f"✅ 应用名称: {prd['app_name']}")
            print(f"✅ 应用描述: {prd['description']}")
            print(f"✅ 功能数量: {len(prd.get('features', []))}")
            
            # 显示AI生成的具体功能
            if prd.get('features'):
                print("🎯 AI识别的功能:")
                for feature in prd['features'][:3]:  # 显示前3个功能
                    print(f"   - {feature.get('name', 'N/A')}: {feature.get('description', 'N/A')}")
            
            print(f"✅ 数据模型数量: {sum(len(f.get('database_models', [])) for f in prd.get('features', []))}")
            print(f"✅ API端点数量: {sum(len(f.get('api_endpoints', [])) for f in prd.get('features', []))}")
            print(f"✅ 技术栈: {prd.get('technical_requirements', {}).get('framework', 'N/A')}")
            print(f"✅ 定制化: {result.get('customized', False)}")
        else:
            print(f"❌ 生成失败: {result['error']}")
        print()

# 简单同步测试（不使用AI）
def test_template_fallback():
    """测试模板回退功能"""
    generator = SimplePRDGenerator()
    
    print("=== 测试模板回退功能 ===")
    
    # 测试模板回退（模拟AI失败场景）
    template = generator._get_blog_template()
    result = generator._fallback_to_template(
        template, 
        "创建一个博客应用", 
        "blog", 
        "fallback_blog"
    )
    
    if result["success"]:
        print("✅ 模板回退功能正常")
        print(f"✅ 生成方法: {result['generation_method']}")
        print(f"✅ 应用名称: {result['prd']['app_name']}")
    else:
        print(f"❌ 模板回退失败: {result['error']}")

if __name__ == "__main__":
    import asyncio
    
    print("选择测试模式:")
    print("1. AI驱动测试 (需要AI服务)")
    print("2. 模板回退测试 (无需AI)")
    
    choice = input("请选择 (1 或 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_ai_prd_generator())
    elif choice == "2":
        test_template_fallback()
    else:
        print("运行所有测试...")
        test_template_fallback()
        print("\n")
        asyncio.run(test_ai_prd_generator())