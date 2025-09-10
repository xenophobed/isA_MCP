#!/usr/bin/env python3
"""
用户画像生成管道服务 - 完整的Gold Data -> ML -> Persona生成流程
协调ETL 2.0处理器 + ML分析器 + Persona生成器
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from core.logging import get_logger
from core.database import get_supabase_client

# 导入子模块服务
from .etl.etl_2_0_processor import etl_2_processor, run_etl_2_pipeline
from .ml.user_behavior_ml_analyzer import user_behavior_ml_analyzer, analyze_user_ml_behavior
from .persona.persona_generator import persona_generator, generate_user_persona

logger = get_logger(__name__)

class UserPersonaPipeline:
    """
    用户画像生成管道服务
    
    完整流程：
    1. ETL 2.0 数据处理 (Gold Data生成)
    2. ML行为分析 (时间行为模式分析)
    3. AI Persona生成 (基于Gold Data + ML特征)
    4. pgvector存储和索引
    """
    
    def __init__(self):
        self.db_client = get_supabase_client()
        self.pipeline_id = f"persona_pipeline_{int(datetime.now().timestamp())}"
        
    async def run_complete_persona_pipeline(self, user_ids: List[str] = None, 
                                          batch_size: int = 10) -> Dict[str, Any]:
        """运行完整的用户画像生成管道"""
        try:
            logger.info(f"🚀 Starting Complete User Persona Pipeline - ID: {self.pipeline_id}")
            
            if not user_ids:
                user_ids = await self._get_active_users_for_persona_generation()
                
            if not user_ids:
                return {
                    "pipeline_id": self.pipeline_id,
                    "success": False,
                    "message": "No active users found for persona generation"
                }
            
            logger.info(f"📊 Processing {len(user_ids)} users (batch size: {batch_size})")
            
            # Stage 1: ETL 2.0 数据处理 (Gold Data)
            logger.info("🏗️ Stage 1: ETL 2.0 Data Processing (Gold Data Generation)")
            etl_results = await self._run_etl_stage(user_ids, batch_size)
            
            # Stage 2: ML行为分析
            logger.info("🧠 Stage 2: ML Behavior Analysis")
            ml_results = await self._run_ml_analysis_stage(user_ids[:batch_size])
            
            # Stage 3: AI Persona生成
            logger.info("🎭 Stage 3: AI Persona Generation")
            persona_results = await self._run_persona_generation_stage(user_ids[:batch_size], ml_results)
            
            # 汇总结果
            pipeline_results = {
                "pipeline_id": self.pipeline_id,
                "completed_at": datetime.now().isoformat(),
                "total_users_processed": len(user_ids),
                "batch_size": batch_size,
                "success": True,
                
                # 各阶段结果
                "etl_stage": etl_results,
                "ml_analysis_stage": ml_results,
                "persona_generation_stage": persona_results,
                
                # 汇总统计
                "summary": {
                    "etl_successful_users": etl_results.get("successful_users", 0),
                    "ml_analyzed_users": len([r for r in ml_results.values() if r.get("success", False)]),
                    "personas_generated": len([r for r in persona_results.values() if r.get("success", False)]),
                    "total_processing_time_seconds": self._calculate_processing_time()
                }
            }
            
            logger.info(f"✅ Complete User Persona Pipeline completed successfully")
            logger.info(f"📈 Generated {pipeline_results['summary']['personas_generated']} personas")
            
            return pipeline_results
            
        except Exception as e:
            logger.error(f"❌ User Persona Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "pipeline_id": self.pipeline_id,
                "success": False,
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
    
    async def _run_etl_stage(self, user_ids: List[str], batch_size: int) -> Dict[str, Any]:
        """运行ETL 2.0阶段 - 生成Gold Data"""
        try:
            logger.info("🔄 Running ETL 2.0 Processor...")
            etl_results = await run_etl_2_pipeline(user_ids, batch_size)
            
            logger.info(f"✅ ETL Stage completed - {etl_results.get('interaction_facts', {}).get('successful_users', 0)} users processed")
            return etl_results
            
        except Exception as e:
            logger.error(f"❌ ETL Stage failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _run_ml_analysis_stage(self, user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """运行ML行为分析阶段"""
        try:
            logger.info(f"🔄 Running ML Behavior Analysis for {len(user_ids)} users...")
            
            ml_results = {}
            
            # 并行处理多个用户的ML分析
            analysis_tasks = []
            for user_id in user_ids:
                task = self._analyze_single_user_ml_behavior(user_id)
                analysis_tasks.append(task)
            
            # 执行并收集结果
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                user_id = user_ids[i]
                if isinstance(result, Exception):
                    logger.error(f"❌ ML Analysis failed for {user_id}: {result}")
                    ml_results[user_id] = {"success": False, "error": str(result)}
                else:
                    ml_results[user_id] = {"success": True, "analysis": result}
                    logger.info(f"✅ ML Analysis completed for {user_id}")
            
            successful_analyses = len([r for r in ml_results.values() if r.get("success", False)])
            logger.info(f"✅ ML Analysis Stage completed - {successful_analyses}/{len(user_ids)} users analyzed")
            
            return ml_results
            
        except Exception as e:
            logger.error(f"❌ ML Analysis Stage failed: {e}")
            return {}
    
    async def _run_persona_generation_stage(self, user_ids: List[str], 
                                          ml_results: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """运行AI Persona生成阶段"""
        try:
            logger.info(f"🔄 Running AI Persona Generation for {len(user_ids)} users...")
            
            persona_results = {}
            
            # 并行处理多个用户的persona生成
            generation_tasks = []
            for user_id in user_ids:
                # 获取该用户的ML分析结果
                user_ml_result = ml_results.get(user_id, {})
                if user_ml_result.get("success"):
                    ml_analysis = user_ml_result["analysis"]
                    task = self._generate_single_user_persona(user_id, ml_analysis)
                    generation_tasks.append((user_id, task))
                else:
                    persona_results[user_id] = {
                        "success": False, 
                        "error": "ML analysis failed or unavailable"
                    }
            
            # 执行persona生成任务
            if generation_tasks:
                tasks = [task for _, task in generation_tasks]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(results):
                    user_id = generation_tasks[i][0]
                    if isinstance(result, Exception):
                        logger.error(f"❌ Persona generation failed for {user_id}: {result}")
                        persona_results[user_id] = {"success": False, "error": str(result)}
                    else:
                        persona_results[user_id] = result
                        if result.get("success"):
                            logger.info(f"✅ Persona generated for {user_id}")
            
            successful_personas = len([r for r in persona_results.values() if r.get("success", False)])
            logger.info(f"✅ Persona Generation Stage completed - {successful_personas}/{len(user_ids)} personas generated")
            
            return persona_results
            
        except Exception as e:
            logger.error(f"❌ Persona Generation Stage failed: {e}")
            return {}
    
    async def _analyze_single_user_ml_behavior(self, user_id: str) -> Dict[str, Any]:
        """分析单个用户的ML行为"""
        try:
            return await analyze_user_ml_behavior(user_id)
        except Exception as e:
            logger.error(f"❌ ML behavior analysis failed for {user_id}: {e}")
            raise
    
    async def _generate_single_user_persona(self, user_id: str, ml_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """为单个用户生成persona"""
        try:
            # 从ML分析结果中提取特征
            ml_features = ml_analysis.get("ml_user_features", {})
            
            # 构建Gold Data（从ML分析结果中提取）
            gold_data = {
                "technical_skills": self._extract_technical_skills_from_ml(ml_analysis),
                "knowledge_domains": self._extract_knowledge_domains_from_ml(ml_analysis),
                "key_insights": self._extract_key_insights_from_ml(ml_analysis),
                "content_length": ml_analysis.get("data_points", 0),
                "data_completeness_score": ml_analysis.get("analysis_quality", {}).get("data_completeness", 0.5)
            }
            
            # 生成persona
            return await persona_generator.generate_user_persona(user_id, ml_features, gold_data)
            
        except Exception as e:
            logger.error(f"❌ Single user persona generation failed for {user_id}: {e}")
            raise
    
    def _extract_technical_skills_from_ml(self, ml_analysis: Dict[str, Any]) -> List[str]:
        """从ML分析结果中提取技术技能"""
        try:
            skills = []
            
            # 从activity patterns中推断技能
            activity_patterns = ml_analysis.get("activity_patterns", {})
            content_patterns = activity_patterns.get("content_patterns", {})
            
            for hour_data in content_patterns.values():
                activity_scores = hour_data.get("activity_scores", {})
                if "coding" in activity_scores and activity_scores["coding"] > 2:
                    skills.extend(["python", "programming"])
                if "data_analysis" in activity_scores and activity_scores["data_analysis"] > 2:
                    skills.extend(["sql", "data_analysis"])
            
            return list(set(skills))  # 去重
            
        except Exception:
            return ["general_usage"]
    
    def _extract_knowledge_domains_from_ml(self, ml_analysis: Dict[str, Any]) -> List[str]:
        """从ML分析结果中提取知识领域"""
        try:
            domains = []
            
            # 基于dominant activity推断领域
            ml_features = ml_analysis.get("ml_user_features", {})
            dominant_activity = ml_features.get("dominant_activity_type")
            
            if dominant_activity == "coding":
                domains.append("Software Development")
            elif dominant_activity == "data_analysis":
                domains.append("Data Science")
            elif dominant_activity == "learning":
                domains.append("Education & Learning")
            else:
                domains.append("General Technology")
            
            return domains
            
        except Exception:
            return ["General Usage"]
    
    def _extract_key_insights_from_ml(self, ml_analysis: Dict[str, Any]) -> List[str]:
        """从ML分析结果中提取关键洞察"""
        try:
            insights = []
            
            ml_features = ml_analysis.get("ml_user_features", {})
            
            # 工作模式洞察
            work_pattern = ml_features.get("primary_work_pattern", "")
            if work_pattern:
                insights.append(f"Primary work pattern: {work_pattern}")
            
            # 使用强度洞察
            usage_intensity = ml_features.get("usage_intensity", "")
            if usage_intensity:
                insights.append(f"Usage intensity: {usage_intensity}")
            
            # 一致性洞察
            consistency = ml_features.get("behavior_consistency", "")
            if consistency:
                insights.append(f"Behavior consistency: {consistency}")
            
            return insights
            
        except Exception:
            return ["Basic usage patterns observed"]
    
    async def _get_active_users_for_persona_generation(self, limit: int = 50) -> List[str]:
        """获取需要生成persona的活跃用户"""
        try:
            # 获取最近活跃但还没有persona的用户
            response = self.db_client.table('sessions')\
                .select('user_id')\
                .gte('created_at', (datetime.now() - timedelta(days=7)).isoformat())\
                .limit(limit)\
                .execute()
            
            if not response.data:
                return []
            
            # 获取已有persona的用户
            existing_personas_response = self.db_client.table('user_personas')\
                .select('user_id')\
                .execute()
            
            existing_user_ids = set()
            if existing_personas_response.data:
                existing_user_ids = {p['user_id'] for p in existing_personas_response.data}
            
            # 过滤出还没有persona的用户
            all_user_ids = list(set([session['user_id'] for session in response.data]))
            new_user_ids = [uid for uid in all_user_ids if uid not in existing_user_ids]
            
            logger.info(f"📊 Found {len(new_user_ids)} users needing persona generation")
            return new_user_ids
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get active users for persona generation: {e}")
            return []
    
    def _calculate_processing_time(self) -> float:
        """计算处理时间"""
        # 简单实现，实际中可以跟踪开始时间
        return 0.0
    
    async def run_single_user_persona_pipeline(self, user_id: str) -> Dict[str, Any]:
        """为单个用户运行完整的persona生成管道"""
        try:
            logger.info(f"🎯 Running single user persona pipeline for: {user_id}")
            
            # 1. ETL处理
            etl_result = await run_etl_2_pipeline([user_id], 1)
            
            # 2. ML分析
            ml_result = await analyze_user_ml_behavior(user_id)
            
            # 3. Persona生成
            if not ml_result.get("error"):
                ml_features = ml_result.get("ml_user_features", {})
                gold_data = {
                    "technical_skills": self._extract_technical_skills_from_ml(ml_result),
                    "knowledge_domains": self._extract_knowledge_domains_from_ml(ml_result),
                    "key_insights": self._extract_key_insights_from_ml(ml_result),
                    "content_length": ml_result.get("data_points", 0),
                    "data_completeness_score": ml_result.get("analysis_quality", {}).get("data_completeness", 0.5)
                }
                
                persona_result = await persona_generator.generate_user_persona(user_id, ml_features, gold_data)
            else:
                persona_result = {"success": False, "error": "ML analysis failed"}
            
            return {
                "user_id": user_id,
                "pipeline_completed": True,
                "etl_success": etl_result.get("success", False),
                "ml_success": not bool(ml_result.get("error")),
                "persona_success": persona_result.get("success", False),
                "persona_result": persona_result
            }
            
        except Exception as e:
            logger.error(f"❌ Single user persona pipeline failed for {user_id}: {e}")
            return {
                "user_id": user_id,
                "pipeline_completed": False,
                "error": str(e)
            }

# 全局实例
user_persona_pipeline = UserPersonaPipeline()

# 便捷函数
async def run_complete_persona_pipeline(user_ids: List[str] = None, batch_size: int = 10) -> Dict[str, Any]:
    """运行完整的用户画像生成管道"""
    return await user_persona_pipeline.run_complete_persona_pipeline(user_ids, batch_size)

async def generate_single_user_persona(user_id: str) -> Dict[str, Any]:
    """为单个用户生成完整persona"""
    return await user_persona_pipeline.run_single_user_persona_pipeline(user_id)