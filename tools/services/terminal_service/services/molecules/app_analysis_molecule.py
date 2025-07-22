"""
应用分析分子服务
分析用户描述，确定应用类型和技术栈
"""

import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# 导入AI文本生成服务
import sys
import os
# 添加项目根目录到路径
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
sys.path.insert(0, project_root)

from tools.services.intelligence_service.language.text_generator import generate


class AppAnalysisMolecule:
    """应用分析分子服务"""
    
    def __init__(self):
        self.app_type_keywords = {
            "web": ["网站", "web", "页面", "前端", "界面", "展示", "html", "css", "bootstrap"],
            "api": ["api", "接口", "rest", "服务端", "后端", "数据", "json", "restful"],
            "blog": ["博客", "blog", "文章", "内容管理", "cms", "发布"],
            "dashboard": ["仪表板", "dashboard", "管理", "监控", "统计", "图表"],
            "chat": ["聊天", "chat", "消息", "通信", "实时"],
            "ecommerce": ["商城", "电商", "购物", "商品", "订单", "支付"],
            "tool": ["工具", "tool", "实用", "计算", "转换", "处理"]
        }
        
        self.complexity_indicators = {
            "simple": ["简单", "基础", "快速", "demo", "原型", "测试"],
            "medium": ["功能", "完整", "用户", "数据库", "登录", "管理"],
            "complex": ["企业", "大型", "复杂", "集成", "微服务", "分布式"]
        }
    
    async def analyze_app_description(self, description: str) -> Dict[str, Any]:
        """分析应用描述"""
        try:
            # 基础分析
            basic_analysis = self._basic_analysis(description)
            
            # AI增强分析
            ai_analysis = await self._ai_enhanced_analysis(description)
            
            # 合并结果
            final_analysis = self._merge_analysis(basic_analysis, ai_analysis)
            
            return {
                "success": True,
                "analysis": final_analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": description
            }
    
    def determine_app_type(self, description: str) -> Dict[str, Any]:
        """确定应用类型"""
        try:
            description_lower = description.lower()
            type_scores = {}
            
            # 计算每种类型的匹配分数
            for app_type, keywords in self.app_type_keywords.items():
                score = 0
                matched_keywords = []
                
                for keyword in keywords:
                    if keyword in description_lower:
                        score += 1
                        matched_keywords.append(keyword)
                
                if score > 0:
                    type_scores[app_type] = {
                        "score": score,
                        "matched_keywords": matched_keywords
                    }
            
            # 确定最佳匹配
            if type_scores:
                best_type = max(type_scores.keys(), key=lambda k: type_scores[k]["score"])
                confidence = type_scores[best_type]["score"] / len(self.app_type_keywords[best_type])
            else:
                # 默认类型
                best_type = "web"
                confidence = 0.3
                type_scores[best_type] = {
                    "score": 0,
                    "matched_keywords": []
                }
            
            return {
                "success": True,
                "app_type": best_type,
                "confidence": round(confidence, 2),
                "all_scores": type_scores,
                "recommended_tech_stack": self._get_tech_stack(best_type)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": description
            }
    
    def extract_requirements(self, description: str) -> Dict[str, Any]:
        """提取功能需求"""
        try:
            requirements = {
                "functional": [],
                "technical": [],
                "ui_elements": [],
                "data_needs": []
            }
            
            description_lower = description.lower()
            
            # 功能需求关键词
            functional_patterns = {
                "用户管理": ["用户", "登录", "注册", "账号", "profile"],
                "数据展示": ["显示", "展示", "列表", "表格", "图表"],
                "搜索功能": ["搜索", "查找", "过滤", "筛选"],
                "文件处理": ["上传", "下载", "文件", "图片", "附件"],
                "通知系统": ["通知", "消息", "提醒", "邮件"],
                "权限控制": ["权限", "角色", "访问控制", "admin"]
            }
            
            # UI元素
            ui_patterns = {
                "导航菜单": ["菜单", "导航", "nav"],
                "表单": ["表单", "输入", "提交", "form"],
                "按钮": ["按钮", "点击", "button"],
                "模态框": ["弹窗", "对话框", "modal"],
                "响应式": ["手机", "移动端", "响应式", "responsive"]
            }
            
            # 检测功能需求
            for requirement, keywords in functional_patterns.items():
                if any(keyword in description_lower for keyword in keywords):
                    requirements["functional"].append(requirement)
            
            # 检测UI需求
            for element, keywords in ui_patterns.items():
                if any(keyword in description_lower for keyword in keywords):
                    requirements["ui_elements"].append(element)
            
            # 检测数据需求
            data_keywords = ["数据库", "存储", "mysql", "postgresql", "redis", "mongodb"]
            if any(keyword in description_lower for keyword in data_keywords):
                requirements["data_needs"].append("数据库存储")
            
            # 检测技术需求
            tech_keywords = ["实时", "websocket", "ajax", "api", "json"]
            if any(keyword in description_lower for keyword in tech_keywords):
                requirements["technical"].append("实时通信")
            
            return {
                "success": True,
                "requirements": requirements,
                "total_requirements": sum(len(v) for v in requirements.values())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": description
            }
    
    def estimate_complexity(self, description: str, requirements: Optional[Dict] = None) -> Dict[str, Any]:
        """评估应用复杂度"""
        try:
            description_lower = description.lower()
            complexity_score = 0
            indicators = []
            
            # 基于关键词评估
            for complexity, keywords in self.complexity_indicators.items():
                for keyword in keywords:
                    if keyword in description_lower:
                        if complexity == "simple":
                            complexity_score += 1
                        elif complexity == "medium":
                            complexity_score += 3
                        elif complexity == "complex":
                            complexity_score += 5
                        indicators.append(f"{keyword} ({complexity})")
            
            # 基于需求数量评估
            if requirements:
                total_reqs = requirements.get("total_requirements", 0)
                if total_reqs > 8:
                    complexity_score += 4
                elif total_reqs > 4:
                    complexity_score += 2
                else:
                    complexity_score += 1
            
            # 确定复杂度级别
            if complexity_score <= 3:
                level = "simple"
                estimated_time = "15-30分钟"
            elif complexity_score <= 8:
                level = "medium" 
                estimated_time = "30-60分钟"
            else:
                level = "complex"
                estimated_time = "1-2小时"
            
            return {
                "success": True,
                "complexity_level": level,
                "complexity_score": complexity_score,
                "estimated_time": estimated_time,
                "indicators": indicators
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": description
            }
    
    async def _ai_enhanced_analysis(self, description: str) -> Dict[str, Any]:
        """AI增强分析"""
        try:
            prompt = f"""分析以下应用描述，返回JSON格式的分析结果：

描述: {description}

请分析：
1. 应用类型 (web/api/blog/dashboard/chat/ecommerce/tool)
2. 主要功能列表
3. 推荐的技术栈
4. 复杂度级别 (simple/medium/complex)
5. 核心特性

返回格式：
{{
    "app_type": "类型",
    "main_features": ["功能1", "功能2"],
    "tech_stack": ["技术1", "技术2"],
    "complexity": "级别",
    "core_features": ["特性1", "特性2"]
}}

只返回JSON，不要其他说明。"""

            ai_response = await generate(prompt, temperature=0.3, max_tokens=500)
            
            try:
                # 尝试解析AI返回的JSON
                ai_result = json.loads(ai_response.strip())
                return {
                    "success": True,
                    "ai_analysis": ai_result
                }
            except json.JSONDecodeError:
                # AI返回格式不正确，返回默认分析
                return {
                    "success": False,
                    "error": "AI response format error",
                    "raw_response": ai_response
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _basic_analysis(self, description: str) -> Dict[str, Any]:
        """基础分析（不依赖AI）"""
        app_type_result = self.determine_app_type(description)
        requirements_result = self.extract_requirements(description)
        complexity_result = self.estimate_complexity(
            description, 
            requirements_result.get("requirements") if requirements_result["success"] else None
        )
        
        return {
            "app_type": app_type_result.get("app_type", "web"),
            "confidence": app_type_result.get("confidence", 0.5),
            "requirements": requirements_result.get("requirements", {}),
            "complexity": complexity_result.get("complexity_level", "simple"),
            "estimated_time": complexity_result.get("estimated_time", "30分钟"),
            "tech_stack": app_type_result.get("recommended_tech_stack", [])
        }
    
    def _merge_analysis(self, basic: Dict[str, Any], ai: Dict[str, Any]) -> Dict[str, Any]:
        """合并基础分析和AI分析结果"""
        if not ai.get("success"):
            return basic
        
        ai_data = ai.get("ai_analysis", {})
        
        # 优先使用AI分析结果，基础分析作为备用
        return {
            "app_type": ai_data.get("app_type", basic["app_type"]),
            "confidence": basic["confidence"],  # 保持基础分析的置信度
            "main_features": ai_data.get("main_features", []),
            "requirements": basic["requirements"],  # 保持详细的需求分析
            "complexity": ai_data.get("complexity", basic["complexity"]),
            "estimated_time": basic["estimated_time"],
            "tech_stack": ai_data.get("tech_stack", basic["tech_stack"]),
            "core_features": ai_data.get("core_features", []),
            "analysis_method": "ai_enhanced" if ai.get("success") else "basic_only"
        }
    
    def _get_tech_stack(self, app_type: str) -> List[str]:
        """根据应用类型推荐技术栈"""
        tech_stacks = {
            "web": ["Flask", "HTML", "CSS", "JavaScript", "Bootstrap"],
            "api": ["Flask", "SQLAlchemy", "PostgreSQL", "REST"],
            "blog": ["Flask", "SQLAlchemy", "Markdown", "Bootstrap"],
            "dashboard": ["Flask", "Chart.js", "Bootstrap", "SQLAlchemy"],
            "chat": ["Flask", "WebSocket", "JavaScript", "Redis"],
            "ecommerce": ["Flask", "SQLAlchemy", "PostgreSQL", "Stripe"],
            "tool": ["Flask", "Python", "HTML", "JavaScript"]
        }
        
        return tech_stacks.get(app_type, ["Flask", "HTML", "CSS"])