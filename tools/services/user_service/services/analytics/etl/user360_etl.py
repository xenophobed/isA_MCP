#!/usr/bin/env python3
"""
User360 ETL Service - 用户大宽表ETL处理
从现有数据源计算汇总指标，使用lang_extractor分析文本内容，生成User360大宽表
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
from core.logging import get_logger
from core.database import get_supabase_client
from tools.services.data_analytics_service.services.data_service.transformation.lang_extractor import LangExtractor, ExtractionType

logger = get_logger(__name__)

class User360ETL:
    """
    User360 ETL服务 - 简单直接的设计
    
    功能:
    1. 从现有表(users, sessions, memory_*, etc.)读取原始数据
    2. 使用lang_extractor分析文本内容
    3. 计算各种汇总指标
    4. 写入user_360_profile表
    """
    
    def __init__(self):
        self.db_client = get_supabase_client()
        self.lang_extractor = LangExtractor()
        
    async def process_user(self, user_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """处理单个用户的User360数据"""
        try:
            logger.info(f"🔄 Processing User360 for user: {user_id}")
            
            # 检查是否需要处理
            if not force_refresh:
                recent_profile = await self._check_recent_profile(user_id)
                if recent_profile:
                    logger.info(f"⚠️ User {user_id} already processed recently, skipping")
                    return {"processed": False, "reason": "recent_profile_exists"}
            
            # 1. 获取基础用户信息
            user_profile = await self._get_user_profile(user_id)
            if not user_profile:
                return {"processed": False, "reason": "user_not_found"}
            
            # 2. 计算会话统计
            session_stats = await self._calculate_session_stats(user_id)
            
            # 3. 计算Memory统计
            memory_stats = await self._calculate_memory_stats(user_id)
            
            # 4. 收集并分析文本内容
            content_text = await self._collect_user_text_content(user_id)
            content_insights = await self._analyze_content_with_lang_extractor(content_text)
            
            # 5. 提取时间行为统计指标
            time_behavior_stats = await self._extract_time_behavior_stats(user_id)
            
            # 6. 组装User360记录
            user360_record = {
                # 基础信息
                "user_id": user_id,
                "org_id": user_profile.get("organization_id"),
                "email": user_profile.get("email"),
                "username": user_profile.get("name"),
                "registration_date": user_profile.get("created_at"),
                "last_login_at": user_profile.get("updated_at"),
                "account_status": "active" if user_profile.get("is_active") else "inactive",
                "subscription_tier": user_profile.get("subscription_status", "free"),
                
                # 会话统计
                **session_stats,
                
                # Memory统计  
                **memory_stats,
                
                # 内容洞察
                **content_insights,
                
                # 时间行为统计指标
                **time_behavior_stats,
                
                # ETL元数据
                "last_etl_run_at": datetime.now().isoformat(),
                "data_completeness_score": self._calculate_completeness_score(session_stats, memory_stats, content_insights),
                "schema_version": "1.0"
            }
            
            # 6. 写入User360表
            await self._upsert_user360_profile(user360_record)
            
            logger.info(f"✅ Successfully processed User360 for user: {user_id}")
            return {"processed": True, "user_id": user_id, "record": user360_record}
            
        except Exception as e:
            logger.error(f"❌ Failed to process User360 for user {user_id}: {e}")
            raise
    
    async def _check_recent_profile(self, user_id: str, hours_threshold: int = 6) -> bool:
        """检查用户是否最近已处理过"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_threshold)
            response = self.db_client.table('user_360_profile')\
                .select('last_etl_run_at')\
                .eq('user_id', user_id)\
                .gte('last_etl_run_at', cutoff_time.isoformat())\
                .execute()
            return bool(response.data)
        except Exception:
            return False
    
    async def _get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户基础信息"""
        try:
            response = self.db_client.table('users').select('*').eq('user_id', user_id).single().execute()
            return response.data
        except Exception as e:
            logger.warning(f"⚠️ Failed to get user profile for {user_id}: {e}")
            return None
    
    async def _calculate_session_stats(self, user_id: str) -> Dict[str, Any]:
        """计算会话统计数据"""
        try:
            # 获取所有会话数据
            response = self.db_client.table('sessions').select('*').eq('user_id', user_id).execute()
            sessions = response.data or []
            
            if not sessions:
                return {
                    "total_sessions": 0,
                    "total_session_duration_minutes": 0.0,
                    "avg_session_duration_minutes": 0.0,
                    "max_session_duration_minutes": 0.0,
                    "sessions_last_7_days": 0,
                    "sessions_last_30_days": 0,
                    "last_session_date": None,
                    "peak_usage_hours": [],
                    "session_frequency_score": 0.0
                }
            
            # 计算统计指标
            total_sessions = len(sessions)
            durations = []
            session_hours = []
            recent_sessions_7d = 0
            recent_sessions_30d = 0
            last_session = None
            
            cutoff_7d = datetime.now() - timedelta(days=7)
            cutoff_30d = datetime.now() - timedelta(days=30)
            
            for session in sessions:
                # 时长计算
                if session.get('duration'):
                    durations.append(float(session['duration']) / 60)  # 转换为分钟
                
                # 时间分析
                if session.get('created_at'):
                    session_time = datetime.fromisoformat(session['created_at'].replace('Z', '+00:00'))
                    session_hours.append(session_time.hour)
                    
                    if session_time >= cutoff_7d:
                        recent_sessions_7d += 1
                    if session_time >= cutoff_30d:
                        recent_sessions_30d += 1
                    
                    if not last_session or session_time > last_session:
                        last_session = session_time
            
            # 计算活跃时段
            hour_counts = {}
            for hour in session_hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            peak_usage_hours = [hour for hour, _ in peak_hours]
            
            return {
                "total_sessions": total_sessions,
                "total_session_duration_minutes": sum(durations),
                "avg_session_duration_minutes": sum(durations) / len(durations) if durations else 0.0,
                "max_session_duration_minutes": max(durations) if durations else 0.0,
                "sessions_last_7_days": recent_sessions_7d,
                "sessions_last_30_days": recent_sessions_30d,
                "last_session_date": last_session.isoformat() if last_session else None,
                "peak_usage_hours": peak_usage_hours,
                "session_frequency_score": min(1.0, recent_sessions_7d / 7.0)  # 简单的频率评分
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate session stats for {user_id}: {e}")
            return {"total_sessions": 0}
    
    async def _calculate_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """计算Memory相关统计"""
        try:
            # 并行查询各种memory表
            tasks = [
                self._count_table_records('session_memories', user_id),
                self._count_table_records('factual_memories', user_id),
                self._count_table_records('episodic_memories', user_id),
                self._count_table_records('procedural_memories', user_id),
                self._count_table_records('semantic_memories', user_id),
                self._count_table_records('working_memories', user_id)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            session_memory_count = results[0] if not isinstance(results[0], Exception) else 0
            factual_memory_count = results[1] if not isinstance(results[1], Exception) else 0
            episodic_memory_count = results[2] if not isinstance(results[2], Exception) else 0
            procedural_memory_count = results[3] if not isinstance(results[3], Exception) else 0
            semantic_memory_count = results[4] if not isinstance(results[4], Exception) else 0
            working_memory_count = results[5] if not isinstance(results[5], Exception) else 0
            
            # 计算会话消息统计
            total_messages = await self._count_table_records('session_messages', user_id)
            
            return {
                "session_memory_count": session_memory_count,
                "factual_memory_count": factual_memory_count,
                "episodic_memory_count": episodic_memory_count,
                "procedural_memory_count": procedural_memory_count,
                "semantic_memory_count": semantic_memory_count,
                "working_memory_usage_score": min(1.0, working_memory_count / 10.0),
                "total_messages": total_messages,
                "total_conversations": session_memory_count  # session_memories 约等于 conversations
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate memory stats for {user_id}: {e}")
            return {"total_messages": 0, "total_conversations": 0}
    
    async def _count_table_records(self, table_name: str, user_id: str) -> int:
        """计算表中用户记录数"""
        try:
            response = self.db_client.table(table_name)\
                .select('*', count='exact')\
                .eq('user_id', user_id)\
                .execute()
            return response.count or 0
        except Exception as e:
            logger.warning(f"⚠️ Failed to count {table_name} for user {user_id}: {e}")
            return 0
    
    async def _analyze_content_with_lang_extractor(self, content_text: str) -> Dict[str, Any]:
        """使用lang_extractor分析用户内容 - 重新设计版本，提取真正有价值的洞察"""
        try:
            if not content_text or len(content_text) < 50:
                logger.info(f"⚠️ Insufficient text content ({len(content_text)} chars), skipping analysis")
                return {
                    "knowledge_domains": [],
                    "primary_use_cases": [],
                    "communication_style": "unknown",
                    "programming_languages": {},
                    "frameworks_and_tools": {},
                    "domain_expertise": {}
                }
            
            # 使用lang_extractor进行深度分析
            logger.info(f"🧠 Analyzing {len(content_text)} characters of rich content")
            
            # 使用最有效的关键信息提取方法
            key_info_result = await self.lang_extractor.extract(
                content_text, 
                ExtractionType.KEY_INFORMATION, 
                max_info=20
            )
            
            # 处理提取结果
            knowledge_domains = []
            primary_use_cases = []
            programming_languages = {}
            frameworks_tools = {}
            domain_expertise = {}
            communication_style = "conversational"
            
            # 关键信息提取结果 - 提取技术栈和工具
            if key_info_result.success and key_info_result.data:
                key_info = key_info_result.data
                
                # 从主题中提取知识领域
                main_topics = key_info.get('main_topics', [])
                knowledge_domains = main_topics[:8]
                
                # 从关键事实中分析技术栈
                key_facts = key_info.get('key_facts', [])
                prog_langs = ['Python', 'JavaScript', 'Java', 'C++', 'Go', 'Rust', 'TypeScript', 'SQL', 'R', 'Scala']
                frameworks = ['React', 'Vue', 'Angular', 'Django', 'Flask', 'FastAPI', 'Spring', 'Node.js', 'Express']
                tools = ['Docker', 'Kubernetes', 'Git', 'Jenkins', 'AWS', 'Azure', 'GCP', 'Redis', 'MongoDB', 'PostgreSQL']
                
                # 分析所有文本内容（原始内容 + 提取的事实和主题）
                full_text = (content_text + ' ' + ' '.join(key_facts) + ' ' + ' '.join(main_topics)).lower()
                
                # 识别编程语言
                for lang in prog_langs:
                    if lang.lower() in full_text:
                        count = full_text.count(lang.lower())
                        confidence = min(0.9, 0.3 + count * 0.1)
                        programming_languages[lang] = round(confidence, 2)
                
                # 识别框架和工具
                for item in frameworks + tools:
                    if item.lower() in full_text:
                        count = full_text.count(item.lower())
                        confidence = min(0.9, 0.4 + count * 0.1)
                        frameworks_tools[item] = round(confidence, 2)
                
                # 基于内容推断使用场景
                if any(lang in programming_languages for lang in ['Python', 'R', 'SQL']):
                    primary_use_cases.append('data_analysis')
                if any(lang in programming_languages for lang in ['Python', 'TensorFlow', 'PyTorch']):
                    primary_use_cases.append('machine_learning')
                if any(item in frameworks_tools for item in ['React', 'Vue', 'Angular', 'JavaScript']):
                    primary_use_cases.append('web_development')
                if any(item in frameworks_tools for item in ['Docker', 'Kubernetes', 'AWS', 'Azure']):
                    primary_use_cases.append('devops')
                
                # 推断专业领域水平
                total_tech_items = len(programming_languages) + len(frameworks_tools)
                if total_tech_items >= 5:
                    domain_expertise['programming'] = 'advanced'
                elif total_tech_items >= 2:
                    domain_expertise['programming'] = 'intermediate'
                elif total_tech_items > 0:
                    domain_expertise['programming'] = 'beginner'
                
                logger.info(f"🔍 Extracted: {len(knowledge_domains)} domains, {len(programming_languages)} languages, {len(frameworks_tools)} tools")
                logger.info(f"📊 Languages: {list(programming_languages.keys())}")
                logger.info(f"🛠️ Tools: {list(frameworks_tools.keys())}")
                
            else:
                logger.warning("⚠️ Key information extraction failed")
            
            # 构建完整的分析结果
            analysis_result = {
                "knowledge_domains": knowledge_domains,
                "primary_use_cases": primary_use_cases,
                "communication_style": communication_style,
                "programming_languages": programming_languages,
                "frameworks_and_tools": frameworks_tools,
                "domain_expertise": domain_expertise
            }
            
            logger.info(f"✅ Content analysis completed: {len(knowledge_domains)} domains, {len(primary_use_cases)} use cases")
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Content analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "knowledge_domains": [],
                "primary_use_cases": [],
                "communication_style": "unknown",
                "programming_languages": {},
                "frameworks_and_tools": {},
                "domain_expertise": {}
            }
    
    async def _collect_user_text_content(self, user_id: str, limit: int = 4000) -> str:
        """收集用户的文本内容用于分析 - 修正版本，使用正确的字段名"""
        try:
            content_parts = []
            
            # 从session_messages获取用户消息
            response = self.db_client.table('session_messages')\
                .select('content')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(50)\
                .execute()
            
            if response.data:
                for msg in response.data:
                    if msg.get('content'):
                        content_parts.append(f"Message: {msg['content']}")
            
            # 从factual_memories获取结构化事实
            try:
                response = self.db_client.table('factual_memories')\
                    .select('subject, predicate, object_value, context')\
                    .eq('user_id', user_id)\
                    .limit(30)\
                    .execute()
                
                if response.data:
                    for fact in response.data:
                        # 构造自然语言描述
                        fact_text = f"{fact.get('subject', '')} {fact.get('predicate', '')} {fact.get('object_value', '')}"
                        if fact.get('context'):
                            fact_text += f" ({fact['context']})"
                        content_parts.append(f"Fact: {fact_text}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get factual memories: {e}")
            
            # 从episodic_memories获取经历内容
            try:
                response = self.db_client.table('episodic_memories')\
                    .select('episode_title, summary, key_events, lessons_learned')\
                    .eq('user_id', user_id)\
                    .limit(20)\
                    .execute()
                
                if response.data:
                    for episode in response.data:
                        episode_text = episode.get('episode_title', '') + ': ' + episode.get('summary', '')
                        if episode.get('lessons_learned'):
                            episode_text += f" Learned: {episode.get('lessons_learned')}"
                        if episode_text.strip(':'):
                            content_parts.append(f"Experience: {episode_text}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get episodic memories: {e}")
            
            # 从semantic_memories获取概念知识
            try:
                response = self.db_client.table('semantic_memories')\
                    .select('concept_name, definition, properties')\
                    .eq('user_id', user_id)\
                    .limit(20)\
                    .execute()
                
                if response.data:
                    for concept in response.data:
                        concept_text = f"{concept.get('concept_name', '')} is {concept.get('definition', '')}"
                        if concept.get('properties'):
                            concept_text += f" Properties: {concept.get('properties')}"
                        content_parts.append(f"Concept: {concept_text}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get semantic memories: {e}")
            
            # 从procedural_memories获取流程知识
            try:
                response = self.db_client.table('procedural_memories')\
                    .select('procedure_name, domain, steps, expected_outcome')\
                    .eq('user_id', user_id)\
                    .limit(15)\
                    .execute()
                
                if response.data:
                    for procedure in response.data:
                        proc_text = f"Procedure: {procedure.get('procedure_name', '')} in {procedure.get('domain', '')}"
                        if procedure.get('steps'):
                            proc_text += f" Steps: {procedure.get('steps')}"
                        if procedure.get('expected_outcome'):
                            proc_text += f" Outcome: {procedure.get('expected_outcome')}"
                        content_parts.append(proc_text)
            except Exception as e:
                logger.warning(f"⚠️ Failed to get procedural memories: {e}")
            
            # 合并并限制长度
            full_content = ' '.join(content_parts)
            logger.info(f"📄 Collected {len(full_content)} characters from {len(content_parts)} content parts for user {user_id}")
            
            return full_content[:limit] if len(full_content) > limit else full_content
            
        except Exception as e:
            logger.error(f"❌ Failed to collect user content for {user_id}: {e}")
            return ""
    
    def _calculate_completeness_score(self, session_stats: Dict, memory_stats: Dict, content_insights: Dict) -> float:
        """计算数据完整性评分"""
        score = 0.0
        
        # 会话数据完整性 (40%)
        if session_stats.get('total_sessions', 0) > 0:
            score += 0.4
        
        # Memory数据完整性 (30%)
        total_memories = sum([
            memory_stats.get('session_memory_count', 0),
            memory_stats.get('factual_memory_count', 0),
            memory_stats.get('episodic_memory_count', 0)
        ])
        if total_memories > 0:
            score += 0.3
        
        # 内容分析完整性 (30%)
        if (content_insights.get('knowledge_domains') and 
            len(content_insights.get('knowledge_domains', [])) > 0):
            score += 0.3
        
        return round(score, 2)
    
    async def _upsert_user360_profile(self, record: Dict[str, Any]):
        """插入或更新User360档案"""
        try:
            # Upsert操作
            response = self.db_client.table('user_360_profile')\
                .upsert(record, on_conflict='user_id')\
                .execute()
            
            if not response.data:
                raise Exception("Upsert failed - no data returned")
                
            logger.info(f"✅ User360 profile upserted for user: {record['user_id']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to upsert User360 profile: {e}")
            raise
    
    async def _extract_time_behavior_stats(self, user_id: str) -> Dict[str, Any]:
        """提取时间行为统计指标 - 为time series和persona分析提供数据基础"""
        try:
            # 1. 从sessions提取活动时间模式统计
            sessions_stats = await self._extract_sessions_time_stats(user_id)
            
            # 2. 从user_events提取事件时间模式统计 
            events_stats = await self._extract_events_time_stats(user_id)
            
            # 3. 从session_messages提取消息时间模式统计
            messages_stats = await self._extract_messages_time_stats(user_id)
            
            return {
                # 高峰时段统计
                "peak_usage_hours": sessions_stats.get("peak_hours", []),
                "preferred_work_hours": sessions_stats.get("preferred_hours", {}),
                
                # 周/日模式统计  
                "weekly_usage_pattern": sessions_stats.get("weekly_pattern", {}),
                "cyclical_behaviors": sessions_stats.get("cyclical_patterns", {}),
                
                
                # 会话统计指标
                "sessions_last_7_days": sessions_stats.get("sessions_7d", 0),
                "sessions_last_30_days": sessions_stats.get("sessions_30d", 0),
                "avg_session_duration_minutes": sessions_stats.get("avg_duration", 0.0),
                
                # 消息统计指标 - 使用已存在的字段
                "avg_messages_per_conversation": messages_stats.get("messages_per_session", 0.0),
                
                # 时区和适应性指标
                "timezone": sessions_stats.get("timezone", "UTC"),
                "timezone_adaptation_score": sessions_stats.get("timezone_score", 0.5)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract time behavior stats for {user_id}: {e}")
            return {
                "peak_usage_hours": [],
                "preferred_work_hours": {},
                "weekly_usage_pattern": {},
                "sessions_last_7_days": 0,
                "sessions_last_30_days": 0
            }
    
    async def _extract_sessions_time_stats(self, user_id: str) -> Dict[str, Any]:
        """从sessions表提取时间统计指标 + 时间-主题关联分析"""
        try:
            # 1. 基础会话统计
            sessions_response = self.db_client.table('sessions')\
                .select('created_at, session_id')\
                .eq('user_id', user_id)\
                .execute()
            
            if not sessions_response.data:
                return {}
            
            sessions = sessions_response.data
            from datetime import datetime, timedelta
            now = datetime.now()
            
            # 基础时间统计 - 修复时区问题
            from datetime import timezone
            now_utc = datetime.now(timezone.utc)
            
            sessions_7d = 0
            sessions_30d = 0
            
            for s in sessions:
                created_at_str = s['created_at']
                if created_at_str:
                    # 处理时区
                    if created_at_str.endswith('Z'):
                        created_at_str = created_at_str[:-1] + '+00:00'
                    elif '+' not in created_at_str and 'T' in created_at_str:
                        created_at_str += '+00:00'
                    
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                        if created_at.tzinfo is None:
                            created_at = created_at.replace(tzinfo=timezone.utc)
                        
                        if created_at > now_utc - timedelta(days=7):
                            sessions_7d += 1
                        if created_at > now_utc - timedelta(days=30):
                            sessions_30d += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to parse timestamp {created_at_str}: {e}")
                        continue
            
            # 2. 准备时间序列数据 - 供后续模型分析使用
            time_series_data = self._prepare_time_series_data(sessions)
            
            return {
                "sessions_7d": sessions_7d,
                "sessions_30d": sessions_30d,
                "peak_hours": time_series_data.get("peak_hours", []),
                "preferred_hours": time_series_data.get("hourly_distribution", {}),
                "weekly_pattern": time_series_data.get("daily_distribution", {}),
                "timezone": "UTC"
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract session time stats: {e}")
            return {}
    
    async def _extract_events_time_stats(self, user_id: str) -> Dict[str, Any]:
        """从user_events表提取事件时间统计指标"""
        try:
            response = self.db_client.table('user_events')\
                .select('event_name, timestamp, event_category')\
                .eq('user_id', user_id)\
                .execute()
            
            if response.data:
                events = response.data
                return {
                    "events_per_day": len(events) / 30.0 if events else 0.0,
                    "common_events": list(set([e['event_name'] for e in events[:5]]))
                }
            
            return {"events_per_day": 0.0, "common_events": []}
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract events time stats: {e}")
            return {"events_per_day": 0.0, "common_events": []}
    
    async def _extract_messages_time_stats(self, user_id: str) -> Dict[str, Any]:
        """从session_messages表提取消息时间统计指标"""
        try:
            response = self.db_client.table('session_messages')\
                .select('created_at, session_id')\
                .eq('user_id', user_id)\
                .execute()
            
            if response.data:
                messages = response.data
                session_count = len(set([m['session_id'] for m in messages]))
                avg_messages_per_session = len(messages) / session_count if session_count > 0 else 0.0
                
                return {
                    "messages_per_session": avg_messages_per_session,
                    "timing_patterns": {}
                }
            
            return {"messages_per_session": 0.0, "timing_patterns": {}}
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract messages time stats: {e}")
            return {"messages_per_session": 0.0, "timing_patterns": {}}
    
    def _prepare_time_series_data(self, sessions: list) -> Dict[str, Any]:
        """准备时间序列数据 - 供模型服务分析使用"""
        try:
            if not sessions:
                return {}
            
            from datetime import datetime
            hourly_counts = {}
            daily_counts = {}
            
            for session in sessions:
                created_at_str = session['created_at']
                if not created_at_str:
                    continue
                    
                # 处理时区
                if created_at_str.endswith('Z'):
                    created_at_str = created_at_str[:-1] + '+00:00'
                elif '+' not in created_at_str and 'T' in created_at_str:
                    created_at_str += '+00:00'
                
                try:
                    from datetime import timezone
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    
                    hour = created_at.hour
                    day_of_week = created_at.weekday()  # 0=Monday
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse session timestamp {created_at_str}: {e}")
                    continue
                
                # 统计每小时活动
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
                
                # 统计每天活动
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                day_name = day_names[day_of_week] if day_of_week < 7 else "Unknown"
                daily_counts[day_name] = daily_counts.get(day_name, 0) + 1
            
            # 找出高峰时段 (活动量 > 平均值)
            if hourly_counts:
                avg_activity = sum(hourly_counts.values()) / len(hourly_counts)
                peak_hours = [hour for hour, count in hourly_counts.items() if count > avg_activity]
            else:
                peak_hours = []
            
            return {
                "hourly_distribution": hourly_counts,
                "daily_distribution": daily_counts,
                "peak_hours": peak_hours,
                "total_sessions": len(sessions)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to prepare time series data: {e}")
            return {}

# 全局实例
user360_etl = User360ETL()

# 便捷函数
async def process_user(user_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """处理单个用户的User360数据"""
    return await user360_etl.process_user(user_id, force_refresh)