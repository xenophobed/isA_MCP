#!/usr/bin/env python
"""
Cognitive Memory Resources for MCP Server
Provides access to memory metadata, statistics and analytics as resources
"""
import json
from datetime import datetime, timedelta

from core.logging import get_logger
from core.monitoring import monitor_manager
from core.database.supabase_client import get_supabase_client

logger = get_logger(__name__)

def register_memory_resources(mcp):
    """Register all cognitive memory resources with the MCP server"""
    
    @mcp.resource("memory://statistics/{user_id}")
    async def get_memory_statistics(user_id: str) -> str:
        """Get comprehensive memory statistics for a user"""
        monitor_manager.log_request("get_memory_statistics", user_id, True, 0.1, "LOW")
        
        supabase = get_supabase_client()
        try:
            stats = {}
            
            # 获取各类记忆数量
            memory_types = ['factual', 'procedural', 'episodic', 'semantic', 'working']
            for memory_type in memory_types:
                count_result = supabase.table(f'{memory_type}_memories')\
                    .select('id')\
                    .eq('user_id', user_id)\
                    .execute()
                stats[f'{memory_type}_count'] = len(count_result.data) if count_result.data else 0
            
            # 获取元数据统计
            metadata_result = supabase.table('memory_metadata')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            
            if metadata_result.data:
                total_accesses = sum(item.get('access_count', 0) for item in metadata_result.data)
                memories_with_accuracy = [item for item in metadata_result.data if item.get('accuracy_score')]
                avg_accuracy = sum(item.get('accuracy_score', 0) for item in memories_with_accuracy) / len(memories_with_accuracy) if memories_with_accuracy else 0
                
                # 生命周期统计
                lifecycle_counts = {}
                for item in metadata_result.data:
                    stage = item.get('lifecycle_stage', 'active')
                    lifecycle_counts[stage] = lifecycle_counts.get(stage, 0) + 1
                
                stats.update({
                    'total_accesses': total_accesses,
                    'average_accuracy': round(avg_accuracy, 3) if avg_accuracy else 0,
                    'total_memories_with_metadata': len(metadata_result.data),
                    'lifecycle_distribution': lifecycle_counts
                })
            
            # 获取配置信息
            config_result = supabase.table('memory_config')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            
            config_data = config_result.data[0] if config_result.data else None
            
            result = {
                "status": "success",
                "user_id": user_id,
                "statistics": stats,
                "configuration": config_data,
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"Memory statistics resource accessed for user {user_id}")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            raise

    @mcp.resource("memory://factual/{user_id}")
    async def get_factual_memories(user_id: str) -> str:
        """Get all factual memories for a user"""
        supabase = get_supabase_client()
        try:
            result = supabase.table('factual_memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('is_active', True)\
                .order('importance_score', desc=True)\
                .limit(100)\
                .execute()
            
            memories = []
            for mem in result.data or []:
                memories.append({
                    "id": mem.get('id'),
                    "fact_type": mem.get('fact_type'),
                    "subject": mem.get('subject'),
                    "predicate": mem.get('predicate'),
                    "object_value": mem.get('object_value'),
                    "context": mem.get('context'),
                    "confidence": mem.get('confidence'),
                    "importance_score": mem.get('importance_score'),
                    "created_at": mem.get('created_at'),
                    "last_confirmed_at": mem.get('last_confirmed_at')
                })
            
            response = {
                "status": "success",
                "memory_type": "factual",
                "user_id": user_id,
                "memories": memories,
                "count": len(memories),
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Factual memories resource accessed for user {user_id}: {len(memories)} items")
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error getting factual memories: {e}")
            raise

    @mcp.resource("memory://procedural/{user_id}")
    async def get_procedural_memories(user_id: str) -> str:
        """Get all procedural memories for a user"""
        supabase = get_supabase_client()
        try:
            result = supabase.table('procedural_memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('usage_count', desc=True)\
                .limit(100)\
                .execute()
            
            memories = []
            for mem in result.data or []:
                memories.append({
                    "id": mem.get('id'),
                    "procedure_name": mem.get('procedure_name'),
                    "domain": mem.get('domain'),
                    "trigger_conditions": mem.get('trigger_conditions'),
                    "steps": mem.get('steps'),
                    "expected_outcome": mem.get('expected_outcome'),
                    "success_rate": mem.get('success_rate'),
                    "usage_count": mem.get('usage_count'),
                    "difficulty_level": mem.get('difficulty_level'),
                    "estimated_time_minutes": mem.get('estimated_time_minutes'),
                    "created_at": mem.get('created_at'),
                    "last_used_at": mem.get('last_used_at')
                })
            
            response = {
                "status": "success",
                "memory_type": "procedural",
                "user_id": user_id,
                "memories": memories,
                "count": len(memories),
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Procedural memories resource accessed for user {user_id}: {len(memories)} items")
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error getting procedural memories: {e}")
            raise

    @mcp.resource("memory://episodic/{user_id}")
    async def get_episodic_memories(user_id: str) -> str:
        """Get all episodic memories for a user"""
        supabase = get_supabase_client()
        try:
            result = supabase.table('episodic_memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('occurred_at', desc=True)\
                .limit(100)\
                .execute()
            
            memories = []
            for mem in result.data or []:
                memories.append({
                    "id": mem.get('id'),
                    "episode_title": mem.get('episode_title'),
                    "summary": mem.get('summary'),
                    "participants": mem.get('participants'),
                    "location": mem.get('location'),
                    "temporal_context": mem.get('temporal_context'),
                    "key_events": mem.get('key_events'),
                    "emotional_context": mem.get('emotional_context'),
                    "emotional_intensity": mem.get('emotional_intensity'),
                    "lessons_learned": mem.get('lessons_learned'),
                    "recall_frequency": mem.get('recall_frequency'),
                    "occurred_at": mem.get('occurred_at'),
                    "created_at": mem.get('created_at'),
                    "last_recalled_at": mem.get('last_recalled_at')
                })
            
            response = {
                "status": "success",
                "memory_type": "episodic",
                "user_id": user_id,
                "memories": memories,
                "count": len(memories),
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Episodic memories resource accessed for user {user_id}: {len(memories)} items")
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error getting episodic memories: {e}")
            raise

    @mcp.resource("memory://semantic/{user_id}")
    async def get_semantic_memories(user_id: str) -> str:
        """Get all semantic memories for a user"""
        supabase = get_supabase_client()
        try:
            result = supabase.table('semantic_memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('mastery_level', desc=True)\
                .limit(100)\
                .execute()
            
            memories = []
            for mem in result.data or []:
                memories.append({
                    "id": mem.get('id'),
                    "concept_name": mem.get('concept_name'),
                    "concept_category": mem.get('concept_category'),
                    "definition": mem.get('definition'),
                    "properties": mem.get('properties'),
                    "related_concepts": mem.get('related_concepts'),
                    "hierarchical_level": mem.get('hierarchical_level'),
                    "parent_concept_id": mem.get('parent_concept_id'),
                    "use_cases": mem.get('use_cases'),
                    "examples": mem.get('examples'),
                    "mastery_level": mem.get('mastery_level'),
                    "learning_source": mem.get('learning_source'),
                    "created_at": mem.get('created_at')
                })
            
            response = {
                "status": "success",
                "memory_type": "semantic",
                "user_id": user_id,
                "memories": memories,
                "count": len(memories),
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Semantic memories resource accessed for user {user_id}: {len(memories)} items")
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error getting semantic memories: {e}")
            raise

    @mcp.resource("memory://working/{user_id}")
    async def get_working_memories(user_id: str) -> str:
        """Get all active working memories for a user"""
        supabase = get_supabase_client()
        try:
            result = supabase.table('working_memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('is_active', True)\
                .order('priority', desc=True)\
                .limit(50)\
                .execute()
            
            memories = []
            for mem in result.data or []:
                memories.append({
                    "id": mem.get('id'),
                    "context_type": mem.get('context_type'),
                    "context_id": mem.get('context_id'),
                    "state_data": mem.get('state_data'),
                    "current_step": mem.get('current_step'),
                    "progress_percentage": mem.get('progress_percentage'),
                    "next_actions": mem.get('next_actions'),
                    "dependencies": mem.get('dependencies'),
                    "blocking_issues": mem.get('blocking_issues'),
                    "priority": mem.get('priority'),
                    "expires_at": mem.get('expires_at'),
                    "created_at": mem.get('created_at')
                })
            
            response = {
                "status": "success",
                "memory_type": "working",
                "user_id": user_id,
                "memories": memories,
                "count": len(memories),
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Working memories resource accessed for user {user_id}: {len(memories)} items")
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error getting working memories: {e}")
            raise

    @mcp.resource("memory://associations/{user_id}")
    async def get_memory_associations(user_id: str) -> str:
        """Get memory associations for a user"""
        supabase = get_supabase_client()
        try:
            result = supabase.table('memory_associations')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('strength', desc=True)\
                .limit(100)\
                .execute()
            
            associations = []
            for assoc in result.data or []:
                associations.append({
                    "id": assoc.get('id'),
                    "source_memory_type": assoc.get('source_memory_type'),
                    "source_memory_id": assoc.get('source_memory_id'),
                    "target_memory_type": assoc.get('target_memory_type'),
                    "target_memory_id": assoc.get('target_memory_id'),
                    "association_type": assoc.get('association_type'),
                    "strength": assoc.get('strength'),
                    "context": assoc.get('context'),
                    "auto_discovered": assoc.get('auto_discovered'),
                    "confirmation_count": assoc.get('confirmation_count'),
                    "created_at": assoc.get('created_at')
                })
            
            response = {
                "status": "success",
                "user_id": user_id,
                "associations": associations,
                "count": len(associations),
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Memory associations resource accessed for user {user_id}: {len(associations)} items")
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error getting memory associations: {e}")
            raise

    @mcp.resource("memory://metadata/{user_id}")
    async def get_memory_metadata(user_id: str) -> str:
        """Get memory metadata and analytics for a user"""
        supabase = get_supabase_client()
        try:
            result = supabase.table('memory_metadata')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('access_count', desc=True)\
                .limit(100)\
                .execute()
            
            metadata_list = []
            for meta in result.data or []:
                metadata_list.append({
                    "id": meta.get('id'),
                    "memory_type": meta.get('memory_type'),
                    "memory_id": meta.get('memory_id'),
                    "access_count": meta.get('access_count'),
                    "last_accessed_at": meta.get('last_accessed_at'),
                    "modification_count": meta.get('modification_count'),
                    "version": meta.get('version'),
                    "accuracy_score": meta.get('accuracy_score'),
                    "relevance_score": meta.get('relevance_score'),
                    "completeness_score": meta.get('completeness_score'),
                    "user_rating": meta.get('user_rating'),
                    "lifecycle_stage": meta.get('lifecycle_stage'),
                    "priority_level": meta.get('priority_level'),
                    "dependency_count": meta.get('dependency_count'),
                    "reference_count": meta.get('reference_count'),
                    "reinforcement_score": meta.get('reinforcement_score'),
                    "system_flags": meta.get('system_flags'),
                    "created_at": meta.get('created_at')
                })
            
            response = {
                "status": "success",
                "user_id": user_id,
                "metadata": metadata_list,
                "count": len(metadata_list),
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Memory metadata resource accessed for user {user_id}: {len(metadata_list)} items")
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error getting memory metadata: {e}")
            raise

    @mcp.resource("memory://extraction_logs/{user_id}")
    async def get_extraction_logs(user_id: str) -> str:
        """Get memory extraction logs for a user"""
        supabase = get_supabase_client()
        try:
            result = supabase.table('memory_extraction_logs')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(50)\
                .execute()
            
            logs = []
            for log in result.data or []:
                logs.append({
                    "id": log.get('id'),
                    "extraction_session_id": log.get('extraction_session_id'),
                    "source_content_hash": log.get('source_content_hash'),
                    "extracted_memories": log.get('extracted_memories'),
                    "extraction_method": log.get('extraction_method'),
                    "confidence_score": log.get('confidence_score'),
                    "created_at": log.get('created_at')
                })
            
            response = {
                "status": "success",
                "user_id": user_id,
                "extraction_logs": logs,
                "count": len(logs),
                "retrieved_at": datetime.now().isoformat()
            }
            
            logger.info(f"Memory extraction logs resource accessed for user {user_id}: {len(logs)} items")
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error getting extraction logs: {e}")
            raise

    @mcp.resource("memory://analytics/summary")
    async def get_global_memory_analytics() -> str:
        """Get global memory system analytics and insights"""
        supabase = get_supabase_client()
        try:
            analytics = {}
            
            # 全局统计
            memory_types = ['factual', 'procedural', 'episodic', 'semantic', 'working']
            for memory_type in memory_types:
                count_result = supabase.table(f'{memory_type}_memories')\
                    .select('id')\
                    .execute()
                analytics[f'total_{memory_type}_memories'] = len(count_result.data) if count_result.data else 0
            
            # 用户活跃度
            users_result = supabase.table('users')\
                .select('user_id')\
                .execute()
            analytics['total_users'] = len(users_result.data) if users_result.data else 0
            
            # 最近提取活动
            recent_extractions = supabase.table('memory_extraction_logs')\
                .select('id')\
                .gte('created_at', (datetime.now() - timedelta(days=7)).isoformat())\
                .execute()
            analytics['recent_extractions_7days'] = len(recent_extractions.data) if recent_extractions.data else 0
            
            # 系统健康度
            active_working_memories = supabase.table('working_memories')\
                .select('id')\
                .eq('is_active', True)\
                .execute()
            analytics['active_working_memories'] = len(active_working_memories.data) if active_working_memories.data else 0
            
            response = {
                "status": "success",
                "analytics": analytics,
                "system_health": {
                    "memory_system_active": True,
                    "total_memories": sum(analytics.get(f'total_{t}_memories', 0) for t in memory_types),
                    "active_users": analytics['total_users'],
                    "extraction_activity": analytics['recent_extractions_7days']
                },
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info("Global memory analytics resource accessed")
            return json.dumps(response)
        except Exception as e:
            logger.error(f"Error getting global analytics: {e}")
            raise


    logger.info("Cognitive memory resources registered successfully")