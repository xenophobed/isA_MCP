#!/usr/bin/env python3
"""
Persona Generator Service - 基于ML分析结果生成专业用户画像文本描述
Gold Data -> ML Analysis -> AI-Generated Persona -> pgvector存储
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from core.logging import get_logger
from core.database import get_supabase_client
from tools.services.intelligence_service.language.text_generator import text_generator

logger = get_logger(__name__)

class PersonaGenerator:
    """
    专业用户画像生成器
    
    功能：
    1. 基于ML分析结果构建专业的persona prompt
    2. 调用text_generator生成完整用户画像文本
    3. 提取关键特征并存储到pgvector
    4. 支持persona版本管理和更新
    """
    
    def __init__(self):
        self.db_client = get_supabase_client()
        
    async def generate_user_persona(self, user_id: str, ml_features: Dict[str, Any], 
                                  gold_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成用户的专业persona描述"""
        try:
            logger.info(f"🎭 Generating persona for user: {user_id}")
            
            # 1. 构建专业的persona生成prompt
            persona_prompt = self._build_persona_prompt(user_id, ml_features, gold_data)
            
            # 2. 使用text_generator生成persona文本
            persona_text = await text_generator.generate(
                prompt=persona_prompt,
                temperature=0.7,  # 适中的创造性
                max_tokens=1500   # 足够详细的描述
            )
            
            # 3. 解析和结构化persona内容
            structured_persona = self._parse_persona_response(persona_text)
            
            # 4. 生成persona向量特征（用于pgvector）
            persona_vector = await self._generate_persona_embedding(persona_text)
            
            # 5. 构建完整的persona记录
            persona_record = {
                "user_id": user_id,
                "persona_text": persona_text,
                "structured_persona": structured_persona,
                "persona_vector": persona_vector,
                "ml_features_used": ml_features,
                "gold_data_summary": self._summarize_gold_data(gold_data),
                "generation_timestamp": datetime.now().isoformat(),
                "persona_version": "1.0",
                "confidence_score": self._calculate_persona_confidence(ml_features, gold_data),
                "persona_tags": self._extract_persona_tags(structured_persona)
            }
            
            # 6. 存储到数据库
            await self._store_persona(persona_record)
            
            logger.info(f"✅ Persona generated successfully for user: {user_id}")
            logger.info(f"📝 Persona length: {len(persona_text)} characters")
            logger.info(f"🏷️ Tags: {', '.join(persona_record['persona_tags'])}")
            
            return {
                "success": True,
                "user_id": user_id,
                "persona_text": persona_text,
                "structured_persona": structured_persona,
                "confidence_score": persona_record["confidence_score"],
                "persona_tags": persona_record["persona_tags"]
            }
            
        except Exception as e:
            logger.error(f"❌ Persona generation failed for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e), "user_id": user_id}
    
    def _build_persona_prompt(self, user_id: str, ml_features: Dict[str, Any], 
                            gold_data: Dict[str, Any]) -> str:
        """构建专业的persona生成prompt"""
        
        # 提取关键ML特征
        work_pattern = ml_features.get('primary_work_pattern', 'flexible')
        usage_intensity = ml_features.get('usage_intensity', 'moderate')
        peak_hours = ml_features.get('peak_activity_hours', [])
        consistency = ml_features.get('behavior_consistency', 'moderate')
        
        # 提取金数据特征
        technical_skills = gold_data.get('technical_skills', [])
        knowledge_domains = gold_data.get('knowledge_domains', [])
        key_insights = gold_data.get('key_insights', [])
        
        prompt = f"""You are a professional user experience researcher and data analyst. Based on comprehensive behavioral analysis and machine learning insights, create a detailed, professional user persona.

## User Behavioral Analysis Data

### Time & Work Patterns (ML-Analyzed)
- Work Pattern: {work_pattern}
- Usage Intensity: {usage_intensity} 
- Peak Activity Hours: {peak_hours}
- Behavior Consistency: {consistency}
- Analysis Period: {ml_features.get('analysis_period_days', 'N/A')} days
- Total Data Points: {ml_features.get('total_data_points', 'N/A')}
- Pattern Confidence: {ml_features.get('pattern_confidence', 0):.2f}

### Technical Competencies (Content-Analyzed)
- Technical Skills: {', '.join(technical_skills) if technical_skills else 'General user'}
- Knowledge Domains: {', '.join(knowledge_domains) if knowledge_domains else 'Not specified'}
- Key Professional Insights: {'. '.join(key_insights) if key_insights else 'Limited technical activity'}

### Content Analysis Summary
- Total Content Analyzed: {gold_data.get('content_length', 0)} characters
- Data Completeness: {gold_data.get('data_completeness_score', 0):.2f}

## Persona Generation Instructions

Create a comprehensive, professional user persona following this structure:

### 1. PROFESSIONAL IDENTITY
- Role/Title (inferred from activities and skills)
- Industry/Domain focus
- Experience level assessment

### 2. WORK STYLE & PREFERENCES  
- Detailed work pattern analysis (based on peak hours and consistency data)
- Preferred working environment
- Task management approach
- Communication style

### 3. TECHNICAL PROFILE
- Core technical competencies 
- Learning approach and preferences
- Problem-solving methodology
- Tool preferences and proficiency

### 4. BEHAVIORAL CHARACTERISTICS
- Usage intensity and engagement patterns
- Consistency in routine vs. flexibility
- Response to different types of tasks
- Collaboration vs. independent work preference

### 5. GROWTH TRAJECTORY
- Current skill development areas
- Learning velocity and patterns
- Potential career progression
- Recommended development paths

### 6. INTERACTION PREFERENCES
- Preferred communication style
- Information consumption patterns
- Feedback and guidance preferences
- Optimal support approaches

## Writing Guidelines:
- Write in third person, professional tone
- Be specific and actionable, not generic
- Base all observations on provided data
- Include confidence indicators where appropriate  
- Make persona relatable and realistic
- Focus on professional context and capabilities

Generate a comprehensive persona (800-1200 words) that would be valuable for personalized user experience design, content customization, and professional development recommendations."""

        return prompt
    
    def _parse_persona_response(self, persona_text: str) -> Dict[str, str]:
        """解析AI生成的persona文本，提取结构化信息"""
        try:
            structured = {}
            
            # 简单的文本解析，提取主要段落
            sections = [
                "PROFESSIONAL IDENTITY", "WORK STYLE & PREFERENCES", 
                "TECHNICAL PROFILE", "BEHAVIORAL CHARACTERISTICS",
                "GROWTH TRAJECTORY", "INTERACTION PREFERENCES"
            ]
            
            current_section = "overview"
            current_content = []
            
            for line in persona_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # 检查是否是新的段落标题
                section_found = None
                for section in sections:
                    if section in line.upper():
                        section_found = section.lower().replace(' ', '_').replace('&', 'and')
                        break
                
                if section_found:
                    # 保存前一个段落
                    if current_content:
                        structured[current_section] = '\n'.join(current_content)
                    
                    # 开始新段落
                    current_section = section_found
                    current_content = []
                else:
                    current_content.append(line)
            
            # 保存最后一个段落
            if current_content:
                structured[current_section] = '\n'.join(current_content)
            
            # 如果解析失败，至少保留完整文本
            if not structured or len(structured) < 3:
                structured = {"full_text": persona_text}
            
            return structured
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse persona response: {e}")
            return {"full_text": persona_text}
    
    async def _generate_persona_embedding(self, persona_text: str) -> List[float]:
        """生成persona文本的向量表示（用于pgvector存储）- 使用现有的embedding_generator"""
        try:
            # 使用现有的embedding_generator服务
            from tools.services.intelligence_service.language.embedding_generator import embedding_generator
            
            # 截取合适长度避免token限制
            max_chars = 5000  # embedding_generator内部会处理长度限制
            truncated_text = persona_text[:max_chars] if len(persona_text) > max_chars else persona_text
            
            # 生成embedding向量
            embedding_vector = await embedding_generator.embed_single(
                text=truncated_text,
                model="text-embedding-3-small"  # 1536维向量
            )
            
            logger.info(f"📊 Generated {len(embedding_vector)}-dimensional embedding vector using ISA")
            return embedding_vector
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to generate persona embedding with ISA: {e}")
            # 返回零向量作为fallback (1536维匹配text-embedding-3-small)
            return [0.0] * 1536
    
    def _summarize_gold_data(self, gold_data: Dict[str, Any]) -> Dict[str, Any]:
        """汇总金数据用于存储"""
        return {
            "content_length": gold_data.get('content_length', 0),
            "technical_skills_count": len(gold_data.get('technical_skills', [])),
            "knowledge_domains_count": len(gold_data.get('knowledge_domains', [])),
            "data_completeness_score": gold_data.get('data_completeness_score', 0),
            "key_insights_count": len(gold_data.get('key_insights', []))
        }
    
    def _calculate_persona_confidence(self, ml_features: Dict[str, Any], gold_data: Dict[str, Any]) -> float:
        """计算persona置信度评分"""
        try:
            confidence_factors = []
            
            # ML特征质量
            pattern_confidence = ml_features.get('pattern_confidence', 0)
            confidence_factors.append(pattern_confidence * 0.4)
            
            # 数据完整性
            data_completeness = gold_data.get('data_completeness_score', 0)
            confidence_factors.append(data_completeness * 0.3)
            
            # 分析时间跨度
            analysis_days = ml_features.get('analysis_period_days', 1)
            time_factor = min(1.0, analysis_days / 7)  # 7天为满分
            confidence_factors.append(time_factor * 0.2)
            
            # 技术特征丰富度
            tech_skills = len(gold_data.get('technical_skills', []))
            tech_factor = min(1.0, tech_skills / 5)  # 5个技能为满分
            confidence_factors.append(tech_factor * 0.1)
            
            total_confidence = sum(confidence_factors)
            return round(total_confidence, 2)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate persona confidence: {e}")
            return 0.5
    
    def _extract_persona_tags(self, structured_persona: Dict[str, str]) -> List[str]:
        """从结构化persona中提取标签"""
        try:
            tags = []
            
            # 从文本内容提取关键标签
            full_text = ' '.join(structured_persona.values()).lower()
            
            # 技术标签
            tech_terms = ['python', 'javascript', 'java', 'sql', 'react', 'fastapi', 'django', 'aws', 'docker', 'kubernetes']
            for term in tech_terms:
                if term in full_text:
                    tags.append(f"tech_{term}")
            
            # 角色标签
            if 'developer' in full_text or 'engineer' in full_text:
                tags.append('role_developer')
            if 'data' in full_text and ('scientist' in full_text or 'analyst' in full_text):
                tags.append('role_data_professional')
            if 'student' in full_text or 'learning' in full_text:
                tags.append('role_learner')
            
            # 工作模式标签
            if 'morning' in full_text:
                tags.append('pattern_morning_person')
            elif 'night' in full_text or 'evening' in full_text:
                tags.append('pattern_night_owl')
            
            # 使用强度标签
            if 'heavy' in full_text or 'intensive' in full_text:
                tags.append('usage_heavy')
            elif 'moderate' in full_text:
                tags.append('usage_moderate')
            elif 'light' in full_text:
                tags.append('usage_light')
            
            # 限制标签数量
            return tags[:10]
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract persona tags: {e}")
            return ['general_user']
    
    async def _store_persona(self, persona_record: Dict[str, Any]):
        """存储persona到数据库"""
        try:
            # 检查是否已存在persona
            existing_response = self.db_client.table('user_personas')\
                .select('id')\
                .eq('user_id', persona_record['user_id'])\
                .execute()
            
            if existing_response.data:
                # 更新现有persona
                update_data = {
                    **persona_record,
                    'updated_at': datetime.now().isoformat()
                }
                self.db_client.table('user_personas')\
                    .update(update_data)\
                    .eq('user_id', persona_record['user_id'])\
                    .execute()
                logger.info(f"📝 Updated existing persona for user: {persona_record['user_id']}")
            else:
                # 创建新persona
                insert_data = {
                    **persona_record,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                self.db_client.table('user_personas')\
                    .insert(insert_data)\
                    .execute()
                logger.info(f"🆕 Created new persona for user: {persona_record['user_id']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store persona: {e}")
            raise
    
    async def get_user_persona(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的persona"""
        try:
            response = self.db_client.table('user_personas')\
                .select('*')\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            return response.data if response.data else None
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get persona for user {user_id}: {e}")
            return None
    
    async def generate_persona_from_ml_analysis(self, user_id: str) -> Dict[str, Any]:
        """完整的pipeline：从用户ID生成persona（集成前面的ML分析）"""
        try:
            # 这里应该调用前面的ML分析服务
            # 为演示目的，使用模拟数据
            logger.info(f"🔄 Running complete persona generation pipeline for: {user_id}")
            
            # 1. 收集Gold Data（模拟，实际中调用ETL服务）
            gold_data = {
                "technical_skills": ["python", "sql"],
                "knowledge_domains": ["Setting up a Python web application using FastAPI", "Database integration with FastAPI"],
                "key_insights": ["Python 3.9 is installed", "FastAPI and Uvicorn installed via pip", "PostgreSQL chosen for production"],
                "content_length": 3464,
                "data_completeness_score": 1.0
            }
            
            # 2. ML特征（模拟，实际中调用ML分析服务）
            ml_features = {
                "peak_activity_hours": [8, 9],
                "primary_work_pattern": "morning_person", 
                "usage_intensity": "heavy",
                "behavior_consistency": "variable",
                "total_data_points": 50,
                "analysis_period_days": 2,
                "pattern_confidence": 1.0
            }
            
            # 3. 生成persona
            return await self.generate_user_persona(user_id, ml_features, gold_data)
            
        except Exception as e:
            logger.error(f"❌ Complete persona generation pipeline failed: {e}")
            return {"success": False, "error": str(e)}

# 全局实例
persona_generator = PersonaGenerator()

# 便捷函数
async def generate_user_persona(user_id: str) -> Dict[str, Any]:
    """生成用户persona（完整pipeline）"""
    return await persona_generator.generate_persona_from_ml_analysis(user_id)

async def get_persona(user_id: str) -> Optional[Dict[str, Any]]:
    """获取用户persona"""
    return await persona_generator.get_user_persona(user_id)