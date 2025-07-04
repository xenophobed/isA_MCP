#!/usr/bin/env python
"""
Cognitive Memory Tools for MCP Server
Handles advanced memory operations based on cognitive science principles
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from core.monitoring import monitor_manager
from core.database.supabase_client import get_supabase_client
from core.isa_client import get_isa_client
from tools.base_tool import BaseTool

logger = get_logger(__name__)

class CognitiveMemoryManager(BaseTool):
    """认知记忆管理器 - 基于认知科学原理"""
    
    def __init__(self):
        super().__init__()
        self.supabase = get_supabase_client()
    
    async def store_factual_memory(self, user_id: str, fact_type: str, subject: str, 
                                 predicate: str, object_value: str, context: str = None,
                                 confidence: float = 0.8, importance_score: float = 0.5) -> Dict[str, Any]:
        """存储事实性记忆 - 自动检查合并"""
        return await self.merge_or_update_factual_memory(
            user_id, fact_type, subject, predicate, object_value, context, confidence, importance_score
        )

    async def merge_or_update_factual_memory(self, user_id: str, fact_type: str, 
                                            subject: str, predicate: str, object_value: str, 
                                            context: str = None, confidence: float = 0.8, 
                                            importance_score: float = 0.5) -> Dict[str, Any]:
        """合并或更新事实记忆，避免重复"""
        try:
            # 首先检查是否存在相同的记忆
            existing = self.supabase.table('factual_memories')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('fact_type', fact_type)\
                .eq('subject', subject)\
                .eq('predicate', predicate)\
                .execute()
            
            if existing.data:
                # 更新现有记忆
                memory_id = existing.data[0]['id']
                old_confidence = existing.data[0].get('confidence', 0.8)
                
                result = self.supabase.table('factual_memories')\
                    .update({
                        'object_value': object_value,
                        'context': context,
                        'last_confirmed_at': datetime.now().isoformat(),
                        'confidence': min(old_confidence + 0.1, 1.0),  # 增加置信度
                        'importance_score': max(importance_score, existing.data[0].get('importance_score', 0.5))
                    })\
                    .eq('id', memory_id)\
                    .execute()
                
                # 追踪访问
                await self._track_access(user_id, 'factual', memory_id)
                
                # 自动发现关联
                await self.discover_memory_associations(user_id, 'factual', memory_id)
                
                return {
                    'status': 'updated', 
                    'memory_type': 'factual',
                    'memory_id': memory_id, 
                    'action': 'merged',
                    'data': result.data[0] if result.data else None
                }
            else:
                # 创建新记忆
                content_for_embedding = f"{subject} {predicate} {object_value}"
                if context:
                    content_for_embedding += f" ({context})"
                
                embedding = await self._generate_embedding(content_for_embedding)
                
                result = self.supabase.table('factual_memories').insert({
                    'user_id': user_id,
                    'fact_type': fact_type,
                    'subject': subject,
                    'predicate': predicate,
                    'object_value': object_value,
                    'context': context,
                    'confidence': confidence,
                    'importance_score': importance_score,
                    'embedding': embedding,
                    'source_interaction_id': str(uuid.uuid4())
                }).execute()
                
                if result.data:
                    memory_id = result.data[0]['id']
                    # 追踪访问
                    await self._track_access(user_id, 'factual', memory_id)
                    
                    # 自动发现关联
                    await self.discover_memory_associations(user_id, 'factual', memory_id)
                    
                    return {
                        'status': 'created',
                        'memory_type': 'factual',
                        'memory_id': memory_id,
                        'action': 'new',
                        'data': result.data[0]
                    }
                else:
                    raise Exception("Failed to insert factual memory")
                    
        except Exception as e:
            logger.error(f"Error merging factual memory: {e}")
            raise

    async def store_procedural_memory(self, user_id: str, procedure_name: str, domain: str,
                                    trigger_conditions: Dict, steps: List[Dict], 
                                    expected_outcome: str = None, difficulty_level: int = 3,
                                    estimated_time_minutes: int = None) -> Dict[str, Any]:
        """存储程序性记忆"""
        try:
            # 生成embedding
            content_for_embedding = f"{procedure_name} in {domain}: {json.dumps(steps)}"
            if expected_outcome:
                content_for_embedding += f" -> {expected_outcome}"
            
            embedding = await self._generate_embedding(content_for_embedding)
            
            result = self.supabase.table('procedural_memories').insert({
                'user_id': user_id,
                'procedure_name': procedure_name,
                'domain': domain,
                'trigger_conditions': trigger_conditions,
                'steps': steps,
                'expected_outcome': expected_outcome,
                'difficulty_level': difficulty_level,
                'estimated_time_minutes': estimated_time_minutes,
                'embedding': embedding
            }).execute()
            
            if result.data:
                memory_id = result.data[0]['id']
                await self._track_access(user_id, 'procedural', memory_id)
                
                return {
                    'status': 'success',
                    'memory_type': 'procedural',
                    'memory_id': memory_id,
                    'data': result.data[0]
                }
            else:
                raise Exception("Failed to insert procedural memory")
                
        except Exception as e:
            logger.error(f"Error storing procedural memory: {e}")
            raise

    async def store_episodic_memory(self, user_id: str, episode_title: str, summary: str,
                                  key_events: List[Dict], occurred_at: datetime,
                                  participants: List[str] = None, location: str = None,
                                  emotional_context: str = None, emotional_intensity: float = 0.5,
                                  lessons_learned: str = None) -> Dict[str, Any]:
        """存储情景记忆"""
        try:
            content_for_embedding = f"{episode_title}: {summary}"
            if lessons_learned:
                content_for_embedding += f" Lessons: {lessons_learned}"
            
            embedding = await self._generate_embedding(content_for_embedding)
            
            result = self.supabase.table('episodic_memories').insert({
                'user_id': user_id,
                'episode_title': episode_title,
                'summary': summary,
                'key_events': key_events,
                'occurred_at': occurred_at.isoformat(),
                'participants': participants or [],
                'location': location,
                'emotional_context': emotional_context,
                'emotional_intensity': emotional_intensity,
                'lessons_learned': lessons_learned,
                'embedding': embedding
            }).execute()
            
            if result.data:
                memory_id = result.data[0]['id']
                await self._track_access(user_id, 'episodic', memory_id)
                
                return {
                    'status': 'success',
                    'memory_type': 'episodic',
                    'memory_id': memory_id,
                    'data': result.data[0]
                }
            else:
                raise Exception("Failed to insert episodic memory")
                
        except Exception as e:
            logger.error(f"Error storing episodic memory: {e}")
            raise

    async def store_semantic_memory(self, user_id: str, concept_name: str, concept_category: str,
                                  definition: str, properties: Dict = None, related_concepts: List[str] = None,
                                  use_cases: List[str] = None, examples: List[str] = None,
                                  mastery_level: float = 0.5) -> Dict[str, Any]:
        """存储语义记忆"""
        try:
            content_for_embedding = f"{concept_name} ({concept_category}): {definition}"
            if use_cases:
                content_for_embedding += f" Uses: {', '.join(use_cases)}"
            
            embedding = await self._generate_embedding(content_for_embedding)
            
            result = self.supabase.table('semantic_memories').insert({
                'user_id': user_id,
                'concept_name': concept_name,
                'concept_category': concept_category,
                'definition': definition,
                'properties': properties or {},
                'related_concepts': related_concepts or [],
                'use_cases': use_cases or [],
                'examples': examples or [],
                'mastery_level': mastery_level,
                'embedding': embedding
            }).execute()
            
            if result.data:
                memory_id = result.data[0]['id']
                await self._track_access(user_id, 'semantic', memory_id)
                
                return {
                    'status': 'success',
                    'memory_type': 'semantic',
                    'memory_id': memory_id,
                    'data': result.data[0]
                }
            else:
                raise Exception("Failed to insert semantic memory")
                
        except Exception as e:
            logger.error(f"Error storing semantic memory: {e}")
            raise

    async def store_working_memory(self, user_id: str, context_type: str, context_id: str,
                                 state_data: Dict, current_step: str = None,
                                 progress_percentage: float = 0.0, next_actions: List[str] = None,
                                 priority: int = 3, expires_in_hours: int = 24) -> Dict[str, Any]:
        """存储工作记忆"""
        try:
            content_for_embedding = f"{context_type} {context_id}: {current_step or 'starting'}"
            embedding = await self._generate_embedding(content_for_embedding)
            
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            
            result = self.supabase.table('working_memories').insert({
                'user_id': user_id,
                'context_type': context_type,
                'context_id': context_id,
                'state_data': state_data,
                'current_step': current_step,
                'progress_percentage': progress_percentage,
                'next_actions': next_actions or [],
                'priority': priority,
                'expires_at': expires_at.isoformat(),
                'embedding': embedding
            }).execute()
            
            if result.data:
                memory_id = result.data[0]['id']
                await self._track_access(user_id, 'working', memory_id)
                
                return {
                    'status': 'success',
                    'memory_type': 'working',
                    'memory_id': memory_id,
                    'data': result.data[0]
                }
            else:
                raise Exception("Failed to insert working memory")
                
        except Exception as e:
            logger.error(f"Error storing working memory: {e}")
            raise

    async def search_memories_semantic(self, user_id: str, query: str, 
                                     memory_types: List[str] = None, 
                                     limit: int = 10, threshold: float = 0.7) -> Dict[str, Any]:
        """基于语义相似度搜索记忆"""
        try:
            # 生成查询embedding
            query_embedding = await self._generate_embedding(query)
            
            # 默认搜索所有类型
            if not memory_types:
                memory_types = ['factual', 'procedural', 'episodic', 'semantic']
            
            # 调用数据库函数
            result = self.supabase.rpc('search_memories_by_similarity', {
                'p_user_id': user_id,
                'p_query_embedding': query_embedding,
                'p_memory_types': memory_types,
                'p_limit': limit,
                'p_threshold': threshold
            }).execute()
            
            memories = []
            if result.data:
                for item in result.data:
                    # 追踪访问
                    await self._track_access(user_id, item['memory_type'], item['memory_id'])
                    memories.append({
                        'memory_type': item['memory_type'],
                        'memory_id': item['memory_id'],
                        'content': item['content'],
                        'similarity': item['similarity']
                    })
            
            return {
                'status': 'success',
                'query': query,
                'results': memories,
                'count': len(memories)
            }
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            raise

    async def extract_memories_from_conversation(self, user_id: str, conversation_text: str) -> Dict[str, Any]:
        """从对话中提取记忆 - 使用ISA客户端"""
        try:
            # 调用ISA模型进行记忆提取
            extraction_prompt = f"""
            从以下对话中提取结构化记忆信息。请按以下格式返回JSON：
            {{
                "factual_memories": [
                    {{"fact_type": "personal_info|preference|skill|experience|knowledge", "subject": "主体", "predicate": "关系", "object_value": "值", "context": "上下文", "confidence": 0.8}}
                ],
                "procedural_memories": [
                    {{"procedure_name": "程序名", "domain": "领域", "trigger_conditions": {{}}, "steps": [], "expected_outcome": "预期结果"}}
                ],
                "episodic_memories": [
                    {{"episode_title": "标题", "summary": "摘要", "key_events": [], "emotional_context": "情感", "lessons_learned": "学到的"}}
                ],
                "semantic_memories": [
                    {{"concept_name": "概念", "concept_category": "类别", "definition": "定义", "related_concepts": []}}
                ]
            }}
            
            对话内容：
            {conversation_text}
            """
            
            # 使用ISA客户端处理
            isa_response = await self.isa_client.process_request(extraction_prompt)
            
            if not isa_response or 'response' not in isa_response:
                raise Exception("ISA client returned invalid response")
            
            # 解析ISA返回的JSON
            extracted_data = json.loads(isa_response['response'])
            
            # 存储提取的记忆
            stored_memories = {
                'factual': [],
                'procedural': [],
                'episodic': [],
                'semantic': []
            }
            
            # 存储事实记忆
            for fact in extracted_data.get('factual_memories', []):
                result = await self.store_factual_memory(
                    user_id=user_id,
                    fact_type=fact['fact_type'],
                    subject=fact['subject'],
                    predicate=fact['predicate'],
                    object_value=fact['object_value'],
                    context=fact.get('context'),
                    confidence=fact.get('confidence', 0.8)
                )
                stored_memories['factual'].append(result)
            
            # 存储程序记忆
            for proc in extracted_data.get('procedural_memories', []):
                result = await self.store_procedural_memory(
                    user_id=user_id,
                    procedure_name=proc['procedure_name'],
                    domain=proc['domain'],
                    trigger_conditions=proc['trigger_conditions'],
                    steps=proc['steps'],
                    expected_outcome=proc.get('expected_outcome')
                )
                stored_memories['procedural'].append(result)
            
            # 存储情景记忆
            for episode in extracted_data.get('episodic_memories', []):
                result = await self.store_episodic_memory(
                    user_id=user_id,
                    episode_title=episode['episode_title'],
                    summary=episode['summary'],
                    key_events=episode['key_events'],
                    occurred_at=datetime.now(),
                    emotional_context=episode.get('emotional_context'),
                    lessons_learned=episode.get('lessons_learned')
                )
                stored_memories['episodic'].append(result)
            
            # 存储语义记忆
            for concept in extracted_data.get('semantic_memories', []):
                result = await self.store_semantic_memory(
                    user_id=user_id,
                    concept_name=concept['concept_name'],
                    concept_category=concept['concept_category'],
                    definition=concept['definition'],
                    related_concepts=concept.get('related_concepts', [])
                )
                stored_memories['semantic'].append(result)
            
            # 记录提取日志
            await self._log_extraction(user_id, conversation_text, extracted_data)
            
            return {
                'status': 'success',
                'extraction_summary': {
                    'factual_count': len(stored_memories['factual']),
                    'procedural_count': len(stored_memories['procedural']),
                    'episodic_count': len(stored_memories['episodic']),
                    'semantic_count': len(stored_memories['semantic'])
                },
                'stored_memories': stored_memories
            }
            
        except Exception as e:
            logger.error(f"Error extracting memories: {e}")
            raise

    async def get_memory_statistics(self, user_id: str) -> Dict[str, Any]:
        """获取用户记忆统计"""
        try:
            stats = {}
            
            # 各类记忆数量
            for memory_type in ['factual', 'procedural', 'episodic', 'semantic', 'working']:
                count_result = self.supabase.table(f'{memory_type}_memories')\
                    .select('id', count='exact')\
                    .eq('user_id', user_id)\
                    .execute()
                stats[f'{memory_type}_count'] = count_result.count
            
            # 元数据统计
            metadata_result = self.supabase.table('memory_metadata')\
                .select('access_count,accuracy_score,relevance_score')\
                .eq('user_id', user_id)\
                .execute()
            
            if metadata_result.data:
                total_accesses = sum(item.get('access_count', 0) for item in metadata_result.data)
                avg_accuracy = sum(item.get('accuracy_score', 0) for item in metadata_result.data if item.get('accuracy_score')) / len(metadata_result.data)
                
                stats['total_accesses'] = total_accesses
                stats['average_accuracy'] = avg_accuracy
            
            return {
                'status': 'success',
                'user_id': user_id,
                'statistics': stats,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            raise

    async def _generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入向量"""
        try:
            # 使用base_tool的ISA客户端调用
            embedding_data, billing_info = await self.call_isa_with_billing(
                input_data=text,
                task="embed",
                service_type="embedding"
            )
            
            if embedding_data and isinstance(embedding_data, list):
                return embedding_data
            else:
                # 如果ISA不可用，返回零向量
                logger.warning("ISA embedding not available, using zero vector")
                return [0.0] * 1536
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * 1536

    async def _track_access(self, user_id: str, memory_type: str, memory_id: str):
        """追踪记忆访问"""
        try:
            await self.supabase.rpc('track_memory_access', {
                'p_user_id': user_id,
                'p_memory_type': memory_type,
                'p_memory_id': memory_id
            }).execute()
        except Exception as e:
            logger.error(f"Error tracking memory access: {e}")

    async def _log_extraction(self, user_id: str, source_content: str, extracted_data: Dict):
        """记录记忆提取日志"""
        try:
            import hashlib
            content_hash = hashlib.sha256(source_content.encode()).hexdigest()
            
            self.supabase.table('memory_extraction_logs').insert({
                'user_id': user_id,
                'extraction_session_id': str(uuid.uuid4()),
                'source_content_hash': content_hash,
                'extracted_memories': extracted_data,
                'extraction_method': 'isa_llm_structured'
            }).execute()
        except Exception as e:
            logger.error(f"Error logging extraction: {e}")

    # 智能化功能方法
    async def discover_memory_associations(self, user_id: str, new_memory_type: str, 
                                         new_memory_id: str) -> List[Dict[str, Any]]:
        """自动发现新记忆与现有记忆的关联"""
        try:
            # 获取新记忆的embedding
            new_memory_embedding = await self._get_memory_embedding(new_memory_type, new_memory_id)
            if not new_memory_embedding:
                return []
            
            # 在所有记忆中搜索相似的
            similar_memories = await self.supabase.rpc('search_memories_by_similarity', {
                'p_user_id': user_id,
                'p_query_embedding': new_memory_embedding,
                'p_memory_types': ['factual', 'procedural', 'episodic', 'semantic'],
                'p_limit': 5,
                'p_threshold': 0.8
            }).execute()
            
            associations = []
            if similar_memories.data:
                for similar in similar_memories.data:
                    if similar['memory_id'] != new_memory_id:
                        # 创建关联
                        association = await self._create_association(
                            user_id, new_memory_type, new_memory_id,
                            similar['memory_type'], similar['memory_id'],
                            'related_to', similar['similarity']
                        )
                        if association:
                            associations.append(association)
            
            return associations
        except Exception as e:
            logger.error(f"Error discovering associations: {e}")
            return []

    async def evaluate_memory_quality(self, user_id: str, memory_type: str, 
                                    memory_id: str) -> Dict[str, float]:
        """评估记忆质量"""
        try:
            # 获取记忆内容和元数据
            memory_data = await self._get_memory_data(memory_type, memory_id)
            metadata = await self._get_memory_metadata(user_id, memory_type, memory_id)
            
            scores = {}
            
            # 准确性评分 (基于确认次数和冲突检测)
            confirmation_count = metadata.get('confirmation_count', 0)
            scores['accuracy'] = min(0.5 + (confirmation_count * 0.1), 1.0)
            
            # 相关性评分 (基于访问频率)
            access_count = metadata.get('access_count', 0)
            scores['relevance'] = min(0.3 + (access_count * 0.05), 1.0)
            
            # 完整性评分 (基于字段完整度)
            completeness = self._calculate_completeness(memory_data)
            scores['completeness'] = completeness
            
            # 更新元数据
            await self._update_memory_metadata(user_id, memory_type, memory_id, scores)
            
            return scores
        except Exception as e:
            logger.error(f"Error evaluating memory quality: {e}")
            return {'accuracy': 0.5, 'relevance': 0.5, 'completeness': 0.5}

    async def get_memory_recommendations(self, user_id: str, context: str, 
                                       limit: int = 5) -> Dict[str, Any]:
        """基于上下文推荐相关记忆"""
        try:
            # 多维度推荐
            recommendations = {
                'similar_experiences': [],
                'relevant_procedures': [],
                'related_concepts': [],
                'applicable_facts': []
            }
            
            # 推荐相似经历
            episodic_results = await self.search_memories_semantic(
                user_id, context, ['episodic'], limit=3, threshold=0.6
            )
            recommendations['similar_experiences'] = episodic_results['results']
            
            # 推荐相关程序
            procedural_results = await self.search_memories_semantic(
                user_id, context, ['procedural'], limit=3, threshold=0.6
            )
            recommendations['relevant_procedures'] = procedural_results['results']
            
            # 推荐语义概念
            semantic_results = await self.search_memories_semantic(
                user_id, context, ['semantic'], limit=3, threshold=0.6
            )
            recommendations['related_concepts'] = semantic_results['results']
            
            # 推荐相关事实
            factual_results = await self.search_memories_semantic(
                user_id, context, ['factual'], limit=3, threshold=0.6
            )
            recommendations['applicable_facts'] = factual_results['results']
            
            return {
                'status': 'success',
                'context': context,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            raise

    async def manage_memory_lifecycle(self, user_id: str) -> Dict[str, Any]:
        """管理记忆生命周期"""
        try:
            actions = {
                'archived': 0,
                'reinforced': 0,
                'deprecated': 0,
                'associations_created': 0
            }
            
            # 获取用户配置
            config = await self._get_user_config(user_id)
            
            # 归档低重要性记忆
            low_importance = self.supabase.table('memory_metadata')\
                .select('memory_type,memory_id')\
                .eq('user_id', user_id)\
                .lt('relevance_score', config.get('auto_archive_threshold', 0.2))\
                .lt('access_count', 2)\
                .execute()
            
            for item in low_importance.data or []:
                await self._archive_memory(user_id, item['memory_type'], item['memory_id'])
                actions['archived'] += 1
            
            # 强化高价值记忆
            high_value = self.supabase.table('memory_metadata')\
                .select('memory_type,memory_id')\
                .eq('user_id', user_id)\
                .gt('access_count', 10)\
                .gt('relevance_score', 0.8)\
                .execute()
            
            for item in high_value.data or []:
                await self._reinforce_memory(user_id, item['memory_type'], item['memory_id'])
                actions['reinforced'] += 1
            
            return {
                'status': 'success',
                'actions': actions,
                'managed_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error managing memory lifecycle: {e}")
            raise

    # 辅助方法
    async def _get_memory_embedding(self, memory_type: str, memory_id: str) -> Optional[List[float]]:
        """获取记忆的embedding向量"""
        try:
            result = self.supabase.table(f'{memory_type}_memories')\
                .select('embedding')\
                .eq('id', memory_id)\
                .execute()
            
            if result.data and result.data[0].get('embedding'):
                return result.data[0]['embedding']
            return None
        except Exception as e:
            logger.error(f"Error getting memory embedding: {e}")
            return None

    async def _create_association(self, user_id: str, source_type: str, source_id: str,
                                target_type: str, target_id: str, association_type: str, 
                                strength: float) -> Optional[Dict[str, Any]]:
        """创建记忆关联"""
        try:
            result = self.supabase.table('memory_associations').insert({
                'user_id': user_id,
                'source_memory_type': source_type,
                'source_memory_id': source_id,
                'target_memory_type': target_type,
                'target_memory_id': target_id,
                'association_type': association_type,
                'strength': strength,
                'auto_discovered': True
            }).execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating association: {e}")
            return None

    async def _get_memory_data(self, memory_type: str, memory_id: str) -> Dict[str, Any]:
        """获取记忆数据"""
        try:
            result = self.supabase.table(f'{memory_type}_memories')\
                .select('*')\
                .eq('id', memory_id)\
                .execute()
            
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Error getting memory data: {e}")
            return {}

    async def _get_memory_metadata(self, user_id: str, memory_type: str, memory_id: str) -> Dict[str, Any]:
        """获取记忆元数据"""
        try:
            result = self.supabase.table('memory_metadata')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('memory_type', memory_type)\
                .eq('memory_id', memory_id)\
                .execute()
            
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Error getting memory metadata: {e}")
            return {}

    def _calculate_completeness(self, memory_data: Dict[str, Any]) -> float:
        """计算记忆完整性得分"""
        if not memory_data:
            return 0.0
        
        # 统计非空字段比例
        total_fields = len(memory_data)
        filled_fields = sum(1 for value in memory_data.values() if value is not None and value != "")
        
        return filled_fields / total_fields if total_fields > 0 else 0.0

    async def _update_memory_metadata(self, user_id: str, memory_type: str, memory_id: str, scores: Dict[str, float]):
        """更新记忆元数据"""
        try:
            self.supabase.table('memory_metadata')\
                .update({
                    'accuracy_score': scores.get('accuracy'),
                    'relevance_score': scores.get('relevance'),
                    'completeness_score': scores.get('completeness'),
                    'updated_at': datetime.now().isoformat()
                })\
                .eq('user_id', user_id)\
                .eq('memory_type', memory_type)\
                .eq('memory_id', memory_id)\
                .execute()
        except Exception as e:
            logger.error(f"Error updating memory metadata: {e}")

    async def _get_user_config(self, user_id: str) -> Dict[str, Any]:
        """获取用户配置"""
        try:
            result = self.supabase.table('memory_config')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            
            if result.data:
                return result.data[0]
            else:
                # 返回默认配置
                return {
                    'auto_archive_threshold': 0.2,
                    'enable_auto_learning': True,
                    'default_similarity_threshold': 0.7
                }
        except Exception as e:
            logger.error(f"Error getting user config: {e}")
            return {'auto_archive_threshold': 0.2}

    async def _archive_memory(self, user_id: str, memory_type: str, memory_id: str):
        """归档记忆"""
        try:
            self.supabase.table('memory_metadata')\
                .update({'lifecycle_stage': 'archived'})\
                .eq('user_id', user_id)\
                .eq('memory_type', memory_type)\
                .eq('memory_id', memory_id)\
                .execute()
        except Exception as e:
            logger.error(f"Error archiving memory: {e}")

    async def _reinforce_memory(self, user_id: str, memory_type: str, memory_id: str):
        """强化记忆"""
        try:
            result = self.supabase.table('memory_metadata')\
                .select('reinforcement_score')\
                .eq('user_id', user_id)\
                .eq('memory_type', memory_type)\
                .eq('memory_id', memory_id)\
                .execute()
            
            current_score = result.data[0].get('reinforcement_score', 0.0) if result.data else 0.0
            new_score = min(current_score + 0.1, 1.0)
            
            self.supabase.table('memory_metadata')\
                .update({'reinforcement_score': new_score})\
                .eq('user_id', user_id)\
                .eq('memory_type', memory_type)\
                .eq('memory_id', memory_id)\
                .execute()
        except Exception as e:
            logger.error(f"Error reinforcing memory: {e}")


# 全局实例
_memory_manager = CognitiveMemoryManager()

def register_memory_tools(mcp):
    """Register all cognitive memory tools with the MCP server"""
    
    security_manager = get_security_manager()
    
    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_fact(user_id: str, fact_type: str, subject: str, predicate: str, 
                        object_value: str, context: str = None, confidence: float = 0.8) -> str:
        """Store factual memory (事实记忆)
        
        Store structured factual information in subject-predicate-object format.
        
        Keywords: memory, fact, store, knowledge, information, remember
        Category: memory
        """
        try:
            _memory_manager.reset_billing()
            result = await _memory_manager.store_factual_memory(
                user_id, fact_type, subject, predicate, object_value, context, confidence
            )
            logger.info(f"Factual memory stored for user {user_id}")
            return _memory_manager.create_response(
                status="success",
                action="store_fact",
                data=result
            )
        except Exception as e:
            logger.error(f"Error storing factual memory: {e}")
            return _memory_manager.create_response(
                status="error",
                action="store_fact",
                data={"user_id": user_id, "fact_type": fact_type},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_procedure(user_id: str, procedure_name: str, domain: str,
                            trigger_conditions: str, steps: str, expected_outcome: str = None) -> str:
        """Store procedural memory (程序记忆)
        
        Store step-by-step procedures and workflows.
        
        Keywords: memory, procedure, workflow, steps, process, method
        Category: memory
        """
        try:
            _memory_manager.reset_billing()
            # 解析JSON字符串
            trigger_dict = json.loads(trigger_conditions)
            steps_list = json.loads(steps)
            
            result = await _memory_manager.store_procedural_memory(
                user_id, procedure_name, domain, trigger_dict, steps_list, expected_outcome
            )
            logger.info(f"Procedural memory stored for user {user_id}")
            return _memory_manager.create_response(
                status="success",
                action="store_procedure",
                data=result
            )
        except Exception as e:
            logger.error(f"Error storing procedural memory: {e}")
            return _memory_manager.create_response(
                status="error",
                action="store_procedure",
                data={"user_id": user_id, "procedure_name": procedure_name},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_episode(user_id: str, episode_title: str, summary: str, key_events: str,
                          participants: str = None, location: str = None, 
                          emotional_context: str = None) -> str:
        """Store episodic memory (情景记忆)
        
        Store specific events and experiences with context.
        
        Keywords: memory, episode, event, experience, story, context
        Category: memory
        """
        try:
            # 解析JSON字符串
            events_list = json.loads(key_events)
            participants_list = json.loads(participants) if participants else None
            
            result = await _memory_manager.store_episodic_memory(
                user_id, episode_title, summary, events_list, datetime.now(),
                participants_list, location, emotional_context
            )
            logger.info(f"Episodic memory stored for user {user_id}")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error storing episodic memory: {e}")
            raise

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def store_concept(user_id: str, concept_name: str, concept_category: str,
                          definition: str, related_concepts: str = None, use_cases: str = None) -> str:
        """Store semantic memory (语义记忆)
        
        Store concepts, definitions, and knowledge relationships.
        
        Keywords: memory, concept, definition, knowledge, semantic, relationship
        Category: memory
        """
        try:
            # 解析JSON字符串
            related_list = json.loads(related_concepts) if related_concepts else None
            use_cases_list = json.loads(use_cases) if use_cases else None
            
            result = await _memory_manager.store_semantic_memory(
                user_id, concept_name, concept_category, definition, 
                related_concepts=related_list, use_cases=use_cases_list
            )
            logger.info(f"Semantic memory stored for user {user_id}")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error storing semantic memory: {e}")
            raise

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def search_memories(user_id: str, query: str, memory_types: str = None, 
                            limit: int = 10, threshold: float = 0.7) -> str:
        """Search memories using semantic similarity
        
        Search across all memory types using natural language queries.
        
        Keywords: memory, search, find, query, semantic, similarity
        Category: memory
        """
        try:
            # 重置billing信息
            _memory_manager.reset_billing()
            
            # 解析memory_types
            types_list = json.loads(memory_types) if memory_types else None
            
            result = await _memory_manager.search_memories_semantic(
                user_id, query, types_list, limit, threshold
            )
            logger.info(f"Memory search completed for user {user_id}: {len(result['results'])} results")
            
            # 使用base_tool的create_response方法包含billing信息
            return _memory_manager.create_response(
                status="success",
                action="search_memories",
                data=result
            )
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return _memory_manager.create_response(
                status="error",
                action="search_memories",
                data={"user_id": user_id, "query": query},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def extract_memories(user_id: str, conversation_text: str) -> str:
        """Extract structured memories from conversation text
        
        Automatically extract and store memories from conversation using AI.
        
        Keywords: memory, extract, conversation, ai, automatic, analysis
        Category: memory
        """
        try:
            result = await _memory_manager.extract_memories_from_conversation(user_id, conversation_text)
            logger.info(f"Memory extraction completed for user {user_id}")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error extracting memories: {e}")
            raise

    @mcp.tool()
    @security_manager.security_check
    async def get_memory_stats(user_id: str) -> str:
        """Get memory statistics for user
        
        Retrieve comprehensive statistics about user's memory system.
        
        Keywords: memory, statistics, stats, analytics, summary
        Category: memory
        """
        try:
            _memory_manager.reset_billing()
            result = await _memory_manager.get_memory_statistics(user_id)
            logger.info(f"Memory statistics retrieved for user {user_id}")
            return _memory_manager.create_response(
                status="success",
                action="get_memory_stats",
                data=result
            )
        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return _memory_manager.create_response(
                status="error",
                action="get_memory_stats",
                data={"user_id": user_id},
                error_message=str(e)
            )

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def recommend_memories(user_id: str, context: str, limit: int = 5) -> str:
        """Get memory recommendations based on context
        
        Recommend relevant memories based on current context or situation.
        
        Keywords: memory, recommend, suggestion, context, relevant
        Category: memory
        """
        try:
            result = await _memory_manager.get_memory_recommendations(user_id, context, limit)
            logger.info(f"Memory recommendations generated for user {user_id}")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error generating memory recommendations: {e}")
            raise

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def evaluate_memory(user_id: str, memory_type: str, memory_id: str) -> str:
        """Evaluate memory quality and relevance
        
        Assess the accuracy, relevance, and completeness of a specific memory.
        
        Keywords: memory, evaluate, quality, accuracy, assessment
        Category: memory
        """
        try:
            result = await _memory_manager.evaluate_memory_quality(user_id, memory_type, memory_id)
            logger.info(f"Memory quality evaluated for user {user_id}")
            return json.dumps({
                'status': 'success',
                'memory_type': memory_type,
                'memory_id': memory_id,
                'quality_scores': result,
                'evaluated_at': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error evaluating memory: {e}")
            raise

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def manage_memory_lifecycle(user_id: str) -> str:
        """Manage memory lifecycle (archive, reinforce, etc.)
        
        Automatically manage memory lifecycle based on usage patterns.
        
        Keywords: memory, lifecycle, archive, manage, optimize
        Category: memory
        """
        try:
            result = await _memory_manager.manage_memory_lifecycle(user_id)
            logger.info(f"Memory lifecycle managed for user {user_id}")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error managing memory lifecycle: {e}")
            raise

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.MEDIUM)
    async def merge_factual_memory(user_id: str, fact_type: str, subject: str, predicate: str, 
                                 object_value: str, context: str = "", confidence: float = 0.8) -> str:
        """Merge or update factual memory intelligently
        
        Store factual memory with automatic duplicate detection and merging.
        
        Keywords: memory, fact, merge, update, intelligent, deduplicate
        Category: memory
        """
        try:
            result = await _memory_manager.merge_or_update_factual_memory(
                user_id, fact_type, subject, predicate, object_value, context, confidence
            )
            logger.info(f"Factual memory merged for user {user_id}: {result['action']}")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error merging factual memory: {e}")
            raise

    @mcp.tool()
    @security_manager.security_check
    @security_manager.require_authorization(SecurityLevel.LOW)
    async def discover_associations(user_id: str, memory_type: str, memory_id: str) -> str:
        """Discover memory associations automatically
        
        Find and create associations between memories based on semantic similarity.
        
        Keywords: memory, associations, discover, connections, relationships
        Category: memory
        """
        try:
            associations = await _memory_manager.discover_memory_associations(user_id, memory_type, memory_id)
            result = {
                'status': 'success',
                'memory_type': memory_type,
                'memory_id': memory_id,
                'associations_found': len(associations),
                'associations': associations,
                'discovered_at': datetime.now().isoformat()
            }
            logger.info(f"Memory associations discovered for user {user_id}: {len(associations)} found")
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error discovering memory associations: {e}")
            raise

    logger.info("Cognitive memory tools registered successfully")