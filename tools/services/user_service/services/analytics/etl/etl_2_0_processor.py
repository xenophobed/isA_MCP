#!/usr/bin/env python3
"""
ETL 2.0 Processor - 基于现有user360_etl.py重新架构的星形模式ETL处理器
混合事实表架构：session_messages + memory为核心，user_events为补充
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
import json
from core.logging import get_logger
from core.database import get_supabase_client
from tools.services.data_analytics_service.services.data_service.transformation.lang_extractor import LangExtractor, ExtractionType

logger = get_logger(__name__)

class ETL2Processor:
    """
    ETL 2.0处理器 - 重新架构的星形模式数据仓库ETL
    
    核心理念：
    1. 复用现有user360_etl.py的数据收集和分析逻辑
    2. 实现混合事实表架构：interaction_facts + behavior_facts + time_behavior_facts
    3. 支持增量处理和实时更新
    4. 为persona生成提供结构化数据基础
    """
    
    def __init__(self):
        self.db_client = get_supabase_client()
        self.lang_extractor = LangExtractor()
        self.batch_id = f"etl2_batch_{int(datetime.now().timestamp())}"
        
    async def run_full_pipeline(self, user_ids: List[str] = None, batch_size: int = 50) -> Dict[str, Any]:
        """运行完整的ETL 2.0管道"""
        try:
            logger.info(f"🚀 Starting ETL 2.0 Pipeline - Batch ID: {self.batch_id}")
            
            # 1. 刷新维度表
            await self._refresh_dimensions()
            
            # 2. 处理用户交互事实（核心）
            interaction_results = await self._process_interaction_facts(user_ids, batch_size)
            
            # 3. 处理行为事件事实（补充）
            behavior_results = await self._process_behavior_facts(user_ids, batch_size)
            
            # 4. 生成时间行为聚合
            time_behavior_results = await self._process_time_behavior_facts(user_ids)
            
            # 5. 更新用户画像快照
            snapshot_results = await self._update_profile_snapshots(user_ids)
            
            pipeline_results = {
                "batch_id": self.batch_id,
                "processed_at": datetime.now().isoformat(),
                "interaction_facts": interaction_results,
                "behavior_facts": behavior_results,
                "time_behavior_facts": time_behavior_results,
                "profile_snapshots": snapshot_results,
                "success": True
            }
            
            logger.info(f"✅ ETL 2.0 Pipeline completed successfully")
            return pipeline_results
            
        except Exception as e:
            logger.error(f"❌ ETL 2.0 Pipeline failed: {e}")
            raise
    
    async def _refresh_dimensions(self):
        """刷新维度表数据"""
        try:
            logger.info("🔄 Refreshing dimension tables...")
            
            # 刷新用户维度（SCD Type 2）
            await self._refresh_user_dimension()
            
            # 刷新会话维度
            await self._refresh_session_dimension()
            
            logger.info("✅ Dimension tables refreshed")
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh dimensions: {e}")
            raise
    
    async def _refresh_user_dimension(self):
        """刷新用户维度表 - 复用user360_etl的用户数据获取逻辑"""
        try:
            # 获取需要更新的用户（新用户或信息变更的用户）
            users_response = self.db_client.table('users').select('*').execute()
            
            if not users_response.data:
                return
            
            for user_data in users_response.data:
                user_id = user_data['user_id']
                
                # 检查是否已存在当前记录
                existing_response = self.db_client.table('user_dimension')\
                    .select('*')\
                    .eq('user_id', user_id)\
                    .eq('is_current', True)\
                    .execute()
                
                needs_update = True
                if existing_response.data:
                    existing = existing_response.data[0]
                    # 简单检查关键字段是否变化
                    if (existing.get('email') == user_data.get('email') and
                        existing.get('subscription_tier') == user_data.get('subscription_status')):
                        needs_update = False
                
                if needs_update:
                    # 复用user360_etl的内容分析逻辑来推断用户分类
                    user_segment, user_persona = await self._infer_user_classification(user_id)
                    
                    # 创建新的用户维度记录
                    user_dim_record = {
                        "user_id": user_id,
                        "email": user_data.get("email"),
                        "username": user_data.get("name"),
                        "organization_id": user_data.get("organization_id"),
                        "subscription_tier": user_data.get("subscription_status", "free"),
                        "account_status": "active" if user_data.get("is_active") else "inactive",
                        "registration_date": user_data.get("created_at"),
                        "timezone": "UTC",  # 默认值，实际中可从用户设置获取
                        "user_segment": user_segment,
                        "user_persona": user_persona,
                        "effective_date": datetime.now().date(),
                        "is_current": True,
                        "etl_batch_id": self.batch_id
                    }
                    
                    # 如果有现有记录，先设置为历史记录
                    if existing_response.data:
                        await self._expire_user_dimension(user_id)
                    
                    # 插入新记录
                    self.db_client.table('user_dimension').insert(user_dim_record).execute()
                    
                    logger.info(f"📊 Updated user dimension for: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh user dimension: {e}")
            raise
    
    async def _infer_user_classification(self, user_id: str) -> Tuple[str, str]:
        """推断用户分类 - 复用user360_etl的内容分析"""
        try:
            # 复用现有的内容收集逻辑
            from .user360_etl import user360_etl
            content_text = await user360_etl._collect_user_text_content(user_id, limit=2000)
            
            if len(content_text) < 100:
                return "new_user", "general"
            
            # 复用现有的内容分析逻辑
            content_insights = await user360_etl._analyze_content_with_lang_extractor(content_text)
            
            # 基于分析结果推断分类
            programming_languages = content_insights.get('programming_languages', {})
            primary_use_cases = content_insights.get('primary_use_cases', [])
            domain_expertise = content_insights.get('domain_expertise', {})
            
            # 推断用户角色
            user_persona = "general"
            if 'data_analysis' in primary_use_cases or 'machine_learning' in primary_use_cases:
                user_persona = "data_scientist"
            elif 'web_development' in primary_use_cases:
                user_persona = "developer"
            elif len(programming_languages) >= 3:
                user_persona = "developer"
            elif 'programming' in domain_expertise:
                if domain_expertise['programming'] in ['advanced', 'expert']:
                    user_persona = "developer"
                else:
                    user_persona = "learner"
            
            # 推断用户活跃度分段
            total_tech_items = len(programming_languages) + len(primary_use_cases)
            if total_tech_items >= 5:
                user_segment = "power_user"
            elif total_tech_items >= 2:
                user_segment = "regular_user"
            else:
                user_segment = "casual_user"
            
            return user_segment, user_persona
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to infer user classification for {user_id}: {e}")
            return "unknown", "general"
    
    async def _expire_user_dimension(self, user_id: str):
        """设置用户维度记录为历史记录（SCD Type 2）"""
        try:
            self.db_client.table('user_dimension')\
                .update({
                    "is_current": False,
                    "expiry_date": datetime.now().date()
                })\
                .eq('user_id', user_id)\
                .eq('is_current', True)\
                .execute()
        except Exception as e:
            logger.warning(f"⚠️ Failed to expire user dimension for {user_id}: {e}")
    
    async def _refresh_session_dimension(self):
        """刷新会话维度表"""
        try:
            # 获取最近的会话数据
            cutoff_date = datetime.now() - timedelta(days=7)
            sessions_response = self.db_client.table('sessions')\
                .select('*')\
                .gte('created_at', cutoff_date.isoformat())\
                .execute()
            
            if not sessions_response.data:
                return
            
            for session_data in sessions_response.data:
                session_id = session_data['id']
                
                # 检查是否已存在
                existing_response = self.db_client.table('session_dimension')\
                    .select('session_key')\
                    .eq('session_id', session_id)\
                    .execute()
                
                if not existing_response.data:
                    # 复用user360_etl的逻辑推断会话类型
                    session_type = await self._infer_session_type(session_id)
                    
                    session_dim_record = {
                        "session_id": session_id,
                        "session_start_time": session_data.get("created_at"),
                        "session_end_time": session_data.get("updated_at"),
                        "session_duration_minutes": session_data.get("duration", 0),
                        "session_type": session_type,
                        "device_type": "web",  # 默认值
                        "browser_type": "unknown",  # 需要从user_events获取
                        "interaction_count": 0,  # 稍后计算
                        "etl_batch_id": self.batch_id
                    }
                    
                    self.db_client.table('session_dimension').insert(session_dim_record).execute()
                    
        except Exception as e:
            logger.error(f"❌ Failed to refresh session dimension: {e}")
            raise
    
    async def _infer_session_type(self, session_id: str) -> str:
        """推断会话类型 - 基于消息内容"""
        try:
            # 获取会话消息示例
            messages_response = self.db_client.table('session_messages')\
                .select('content')\
                .eq('session_id', session_id)\
                .limit(5)\
                .execute()
            
            if not messages_response.data:
                return "unknown"
            
            # 简单的关键词分析
            all_content = ' '.join([msg['content'] for msg in messages_response.data if msg.get('content')])
            content_lower = all_content.lower()
            
            if any(keyword in content_lower for keyword in ['code', 'function', 'debug', 'error']):
                return "coding"
            elif any(keyword in content_lower for keyword in ['learn', 'explain', 'how to', 'what is']):
                return "learning"
            elif any(keyword in content_lower for keyword in ['data', 'analysis', 'model', 'predict']):
                return "data_analysis"
            else:
                return "general"
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to infer session type for {session_id}: {e}")
            return "unknown"
    
    async def _process_interaction_facts(self, user_ids: List[str] = None, batch_size: int = 50) -> Dict[str, Any]:
        """处理用户交互事实表 - 核心表，基于session_messages和memory"""
        try:
            logger.info("🔄 Processing interaction facts (core)...")
            
            processed_count = 0
            success_count = 0
            
            # 获取待处理的用户
            if not user_ids:
                user_ids = await self._get_active_users()
            
            for user_id in user_ids[:batch_size]:
                try:
                    # 复用user360_etl的数据收集逻辑
                    from .user360_etl import user360_etl
                    
                    # 1. 收集用户内容
                    content_text = await user360_etl._collect_user_text_content(user_id)
                    
                    if len(content_text) < 50:
                        continue
                    
                    # 2. 使用现有的内容分析
                    content_insights = await user360_etl._analyze_content_with_lang_extractor(content_text)
                    
                    # 3. 获取相关维度键
                    user_key = await self._get_user_key(user_id)
                    time_key = int(datetime.now().strftime('%Y%m%d%H%M'))
                    
                    # 4. 从session_messages创建交互事实记录
                    await self._create_interaction_facts_from_messages(
                        user_id, user_key, time_key, content_insights
                    )
                    
                    # 5. 从memory创建交互事实记录
                    await self._create_interaction_facts_from_memory(
                        user_id, user_key, time_key, content_insights
                    )
                    
                    success_count += 1
                    logger.info(f"✅ Processed interaction facts for user: {user_id}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process interaction facts for {user_id}: {e}")
                
                processed_count += 1
            
            return {
                "processed_users": processed_count,
                "successful_users": success_count,
                "table": "user_interaction_facts"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process interaction facts: {e}")
            raise
    
    async def _create_interaction_facts_from_messages(self, user_id: str, user_key: int, time_key: int, content_insights: Dict):
        """从session_messages创建交互事实记录"""
        try:
            # 获取最近的消息
            cutoff_date = datetime.now() - timedelta(hours=24)  # 只处理最近24小时的数据
            messages_response = self.db_client.table('session_messages')\
                .select('id, session_id, content, created_at, message_type')\
                .eq('user_id', user_id)\
                .gte('created_at', cutoff_date.isoformat())\
                .limit(20)\
                .execute()
            
            if not messages_response.data:
                return
            
            for message in messages_response.data:
                if not message.get('content') or len(message['content']) < 10:
                    continue
                
                # 获取session_key
                session_key = await self._get_session_key(message['session_id'])
                
                # 推断需求类别
                need_category = self._infer_need_category(message['content'], content_insights)
                
                interaction_fact = {
                    "user_key": user_key,
                    "time_key": time_key,
                    "session_key": session_key,
                    "content_type_key": 1,  # 默认内容类型
                    "source_id": message['id'],
                    "source_type": "session_message",
                    "content_length": len(message['content']),
                    "content_summary": message['content'][:500],
                    "need_category": need_category,
                    "primary_domain": content_insights.get('knowledge_domains', ['general'])[0] if content_insights.get('knowledge_domains') else 'general',
                    "interaction_quality_score": 0.8,  # 基于消息类型和长度的简单评分
                    "etl_batch_id": self.batch_id
                }
                
                # 插入事实表
                self.db_client.table('user_interaction_facts').insert(interaction_fact).execute()
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to create interaction facts from messages for {user_id}: {e}")
    
    async def _create_interaction_facts_from_memory(self, user_id: str, user_key: int, time_key: int, content_insights: Dict):
        """从memory表创建交互事实记录"""
        try:
            # 获取各类memory数据 - 复用user360_etl的逻辑
            memory_tables = ['factual_memories', 'episodic_memories', 'semantic_memories']
            
            for table_name in memory_tables:
                try:
                    response = self.db_client.table(table_name)\
                        .select('*')\
                        .eq('user_id', user_id)\
                        .limit(10)\
                        .execute()
                    
                    if not response.data:
                        continue
                    
                    for memory in response.data:
                        # 构造内容摘要
                        content_summary = self._extract_memory_content(memory, table_name)
                        
                        if len(content_summary) < 10:
                            continue
                        
                        memory_fact = {
                            "user_key": user_key,
                            "time_key": time_key,
                            "session_key": -1,  # memory没有session
                            "content_type_key": 2,  # memory内容类型
                            "source_id": str(memory['id']),
                            "source_type": table_name,
                            "content_length": len(content_summary),
                            "content_summary": content_summary[:500],
                            "need_category": "knowledge_building",
                            "primary_domain": content_insights.get('knowledge_domains', ['general'])[0] if content_insights.get('knowledge_domains') else 'general',
                            "domain_confidence_score": memory.get('confidence_score', 0.5),
                            "etl_batch_id": self.batch_id
                        }
                        
                        self.db_client.table('user_interaction_facts').insert(memory_fact).execute()
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process {table_name} for {user_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"⚠️ Failed to create interaction facts from memory for {user_id}: {e}")
    
    def _extract_memory_content(self, memory: Dict, table_name: str) -> str:
        """从memory记录中提取内容摘要"""
        if table_name == 'factual_memories':
            return f"{memory.get('subject', '')} {memory.get('predicate', '')} {memory.get('object_value', '')}"
        elif table_name == 'episodic_memories':
            return f"{memory.get('episode_title', '')}: {memory.get('summary', '')}"
        elif table_name == 'semantic_memories':
            return f"{memory.get('concept_name', '')} - {memory.get('definition', '')}"
        else:
            return str(memory)[:200]
    
    def _infer_need_category(self, content: str, content_insights: Dict) -> str:
        """推断用户需求类别"""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['help', 'how to', 'explain']):
            return 'learning'
        elif any(keyword in content_lower for keyword in ['error', 'bug', 'fix', 'debug']):
            return 'problem_solving'
        elif any(keyword in content_lower for keyword in ['create', 'build', 'develop']):
            return 'development'
        elif content_insights.get('primary_use_cases'):
            use_case = content_insights['primary_use_cases'][0]
            if use_case == 'data_analysis':
                return 'data_analysis'
            elif use_case == 'machine_learning':
                return 'ml_modeling'
        
        return 'general'
    
    async def _process_behavior_facts(self, user_ids: List[str] = None, batch_size: int = 50) -> Dict[str, Any]:
        """处理用户行为事实表 - 补充表，基于user_events"""
        try:
            logger.info("🔄 Processing behavior facts (supplemental)...")
            
            processed_count = 0
            success_count = 0
            
            if not user_ids:
                user_ids = await self._get_active_users()
            
            for user_id in user_ids[:batch_size]:
                try:
                    # 获取最近的用户事件
                    cutoff_date = datetime.now() - timedelta(hours=24)
                    events_response = self.db_client.table('user_events')\
                        .select('*')\
                        .eq('user_id', user_id)\
                        .gte('timestamp', cutoff_date.isoformat())\
                        .limit(50)\
                        .execute()
                    
                    if not events_response.data:
                        continue
                    
                    user_key = await self._get_user_key(user_id)
                    
                    for event in events_response.data:
                        # 创建行为事实记录
                        time_key = int(datetime.fromisoformat(event['timestamp']).strftime('%Y%m%d%H%M'))
                        session_key = await self._get_session_key(event.get('session_id')) if event.get('session_id') else -1
                        
                        behavior_fact = {
                            "user_key": user_key,
                            "time_key": time_key,
                            "session_key": session_key,
                            "event_type_key": 1,  # 默认事件类型
                            "event_id": str(event['id']),
                            "event_name": event['event_name'],
                            "page_path": event.get('properties', {}).get('page_path', ''),
                            "feature_used": event.get('properties', {}).get('feature_used', ''),
                            "event_timestamp": event['timestamp'],
                            "etl_batch_id": self.batch_id
                        }
                        
                        self.db_client.table('user_behavior_facts').insert(behavior_fact).execute()
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process behavior facts for {user_id}: {e}")
                
                processed_count += 1
            
            return {
                "processed_users": processed_count,
                "successful_users": success_count,
                "table": "user_behavior_facts"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process behavior facts: {e}")
            raise
    
    async def _process_time_behavior_facts(self, user_ids: List[str] = None) -> Dict[str, Any]:
        """处理时间行为聚合事实表 - 分析用户什么时间做什么"""
        try:
            logger.info("🔄 Processing time behavior aggregation...")
            
            processed_count = 0
            success_count = 0
            
            if not user_ids:
                user_ids = await self._get_active_users()
            
            for user_id in user_ids:
                try:
                    user_key = await self._get_user_key(user_id)
                    
                    # 复用user360_etl的时间行为分析逻辑
                    from .user360_etl import user360_etl
                    time_stats = await user360_etl._extract_time_behavior_stats(user_id)
                    
                    # 为每个活跃小时创建时间行为记录
                    peak_hours = time_stats.get('peak_usage_hours', [])
                    
                    for hour in peak_hours:
                        time_period_key = hour + 1  # 简单映射到time_period_dimension
                        
                        # 分析该时间段的主要活动
                        dominant_activity = await self._analyze_hourly_activity(user_id, hour)
                        
                        time_behavior_fact = {
                            "user_key": user_key,
                            "time_period_key": time_period_key,
                            "behavior_pattern_key": 1,  # 默认模式
                            "analysis_date": datetime.now().date(),
                            "hour_of_day": hour,
                            "dominant_need_category": "general",
                            "dominant_activity": dominant_activity,
                            "total_interactions": time_stats.get('sessions_last_7_days', 0),
                            "productivity_score": 0.7,  # 基于peak hour的假设评分
                            "etl_batch_id": self.batch_id
                        }
                        
                        self.db_client.table('user_time_behavior_facts').insert(time_behavior_fact).execute()
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process time behavior facts for {user_id}: {e}")
                
                processed_count += 1
            
            return {
                "processed_users": processed_count,
                "successful_users": success_count,
                "table": "user_time_behavior_facts"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process time behavior facts: {e}")
            raise
    
    async def _analyze_hourly_activity(self, user_id: str, hour: int) -> str:
        """分析用户在特定小时的主要活动"""
        try:
            # 简化版本：基于该时间段的事件类型分析
            events_response = self.db_client.table('user_events')\
                .select('event_name, event_category')\
                .eq('user_id', user_id)\
                .execute()
            
            if not events_response.data:
                return "general"
            
            # 统计事件类型
            event_counts = {}
            for event in events_response.data:
                event_name = event.get('event_name', 'unknown')
                event_counts[event_name] = event_counts.get(event_name, 0) + 1
            
            # 返回最频繁的活动
            if event_counts:
                dominant = max(event_counts.items(), key=lambda x: x[1])[0]
                return dominant
            
            return "general"
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to analyze hourly activity for {user_id} at {hour}: {e}")
            return "general"
    
    async def _update_profile_snapshots(self, user_ids: List[str] = None) -> Dict[str, Any]:
        """更新用户画像快照 - 为persona生成准备数据"""
        try:
            logger.info("🔄 Updating user profile snapshots...")
            
            processed_count = 0
            success_count = 0
            
            if not user_ids:
                user_ids = await self._get_active_users()
            
            for user_id in user_ids:
                try:
                    user_key = await self._get_user_key(user_id)
                    
                    # 复用user360_etl的完整分析能力
                    from .user360_etl import user360_etl
                    user_profile = await user360_etl.process_user(user_id, force_refresh=True)
                    
                    if user_profile.get('processed'):
                        record = user_profile['record']
                        
                        # 创建画像快照
                        snapshot_record = {
                            "user_key": user_key,
                            "snapshot_date_key": int(datetime.now().strftime('%Y%m%d')),
                            "effective_date": datetime.now().date(),
                            "is_current": True,
                            
                            # 技能评估
                            "technical_skill_level": self._assess_skill_level(record),
                            "domain_expertise_scores": record.get('domain_expertise', {}),
                            "problem_solving_maturity": "intermediate",  # 基于交互复杂度
                            
                            # 行为特征
                            "usage_intensity": self._assess_usage_intensity(record),
                            "preferred_interaction_style": record.get('communication_style', 'conversational'),
                            "tool_proficiency_scores": record.get('frameworks_and_tools', {}),
                            
                            # 时间模式
                            "peak_productivity_hours": record.get('peak_usage_hours', []),
                            "work_pattern_type": self._infer_work_pattern(record),
                            
                            # 预测特征
                            "user_lifecycle_stage": "active",  # 基于最近活动
                            "engagement_trend": "stable",
                            "churn_risk_score": 0.1,  # 低风险（活跃用户）
                            "personalization_readiness": record.get('data_completeness_score', 0.5),
                            
                            # 元数据
                            "data_quality_score": record.get('data_completeness_score', 0.5),
                            "completeness_percentage": record.get('data_completeness_score', 0.5) * 100,
                            "confidence_level": 0.8,
                            "etl_batch_id": self.batch_id
                        }
                        
                        # 先失效现有快照
                        self.db_client.table('user_profile_snapshots')\
                            .update({"is_current": False, "expiry_date": datetime.now().date()})\
                            .eq('user_key', user_key)\
                            .eq('is_current', True)\
                            .execute()
                        
                        # 插入新快照
                        self.db_client.table('user_profile_snapshots').insert(snapshot_record).execute()
                        
                        success_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update profile snapshot for {user_id}: {e}")
                
                processed_count += 1
            
            return {
                "processed_users": processed_count,
                "successful_users": success_count,
                "table": "user_profile_snapshots"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to update profile snapshots: {e}")
            raise
    
    def _assess_skill_level(self, record: Dict) -> str:
        """评估技术技能水平"""
        programming_languages = record.get('programming_languages', {})
        frameworks_tools = record.get('frameworks_and_tools', {})
        
        total_items = len(programming_languages) + len(frameworks_tools)
        avg_confidence = 0
        
        if programming_languages:
            avg_confidence = sum(programming_languages.values()) / len(programming_languages)
        
        if total_items >= 5 and avg_confidence > 0.7:
            return "expert"
        elif total_items >= 3 and avg_confidence > 0.5:
            return "advanced"
        elif total_items >= 1:
            return "intermediate"
        else:
            return "beginner"
    
    def _assess_usage_intensity(self, record: Dict) -> str:
        """评估使用强度"""
        total_sessions = record.get('total_sessions', 0)
        sessions_7d = record.get('sessions_last_7_days', 0)
        
        if sessions_7d >= 5:
            return "heavy"
        elif sessions_7d >= 2:
            return "moderate"
        elif total_sessions > 10:
            return "light"
        else:
            return "minimal"
    
    def _infer_work_pattern(self, record: Dict) -> str:
        """推断工作模式"""
        peak_hours = record.get('peak_usage_hours', [])
        
        if not peak_hours:
            return "flexible"
        
        morning_hours = [h for h in peak_hours if 6 <= h <= 10]
        evening_hours = [h for h in peak_hours if 18 <= h <= 23]
        
        if len(morning_hours) >= 2:
            return "morning_person"
        elif len(evening_hours) >= 2:
            return "night_owl"
        else:
            return "flexible"
    
    # 辅助方法
    async def _get_active_users(self, limit: int = 100) -> List[str]:
        """获取活跃用户列表"""
        try:
            cutoff_date = datetime.now() - timedelta(days=30)
            response = self.db_client.table('sessions')\
                .select('user_id')\
                .gte('created_at', cutoff_date.isoformat())\
                .limit(limit)\
                .execute()
            
            if response.data:
                return list(set([session['user_id'] for session in response.data]))
            return []
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get active users: {e}")
            return []
    
    async def _get_user_key(self, user_id: str) -> int:
        """获取用户维度键"""
        try:
            response = self.db_client.table('user_dimension')\
                .select('user_key')\
                .eq('user_id', user_id)\
                .eq('is_current', True)\
                .single()\
                .execute()
            
            if response.data:
                return response.data['user_key']
            else:
                # 如果找不到，返回默认值或创建新记录
                return -1
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to get user_key for {user_id}: {e}")
            return -1
    
    async def _get_session_key(self, session_id: str) -> int:
        """获取会话维度键"""
        try:
            response = self.db_client.table('session_dimension')\
                .select('session_key')\
                .eq('session_id', session_id)\
                .single()\
                .execute()
            
            if response.data:
                return response.data['session_key']
            else:
                return -1
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to get session_key for {session_id}: {e}")
            return -1

# 全局实例
etl_2_processor = ETL2Processor()

# 便捷函数
async def run_etl_2_pipeline(user_ids: List[str] = None, batch_size: int = 50) -> Dict[str, Any]:
    """运行ETL 2.0完整管道"""
    return await etl_2_processor.run_full_pipeline(user_ids, batch_size)