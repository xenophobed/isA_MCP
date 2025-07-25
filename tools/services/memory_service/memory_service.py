#!/usr/bin/env python3
"""
Memory Service
Main service class integrating all memory engines with atomic adapter pattern
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

from core.logging import get_logger
# Simple direct import
from core.database.supabase_client import get_supabase_client
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator

from .models import (
    MemoryType, MemoryModel, MemorySearchQuery, MemorySearchResult, 
    MemoryOperationResult, MemoryAssociation,
    FactualMemory, ProceduralMemory, EpisodicMemory, 
    SemanticMemory, WorkingMemory, SessionMemory
)
from .engines import (
    FactualMemoryEngine, ProceduralMemoryEngine, EpisodicMemoryEngine,
    SemanticMemoryEngine, WorkingMemoryEngine, SessionMemoryEngine
)

logger = get_logger(__name__)


class MemoryService:
    """
    Unified memory service providing intelligent memory processing
    Each engine manages its own adapters for optimal performance and isolation
    Supports all memory types: factual, procedural, episodic, semantic, working, session
    """
    
    def __init__(self):
        """Initialize memory service - engines handle their own adapters"""
        # Keep centralized adapters for service-level operations
        self.db = get_supabase_client()
        self.embedder = EmbeddingGenerator()
        
        # Memory type engines - each engine manages its own database and embedding adapters
        self.engines = {
            MemoryType.FACTUAL: FactualMemoryEngine(),
            MemoryType.PROCEDURAL: ProceduralMemoryEngine(),
            MemoryType.EPISODIC: EpisodicMemoryEngine(),
            MemoryType.SEMANTIC: SemanticMemoryEngine(),
            MemoryType.WORKING: WorkingMemoryEngine(),
            MemoryType.SESSION: SessionMemoryEngine()
        }
        
        logger.info("Memory service initialized - engines use independent adapters")
    
    def get_engine(self, memory_type: MemoryType):
        """Get the appropriate engine for a memory type"""
        return self.engines.get(memory_type)
    
    # Unified memory operations
    async def store_memory(self, memory: MemoryModel) -> MemoryOperationResult:
        """Store a memory using the appropriate engine"""
        engine = self.get_engine(memory.memory_type)
        if not engine:
            return MemoryOperationResult(
                success=False,
                operation="store",
                message=f"No engine found for memory type: {memory.memory_type}"
            )
        
        return await engine.store_memory(memory)
    
    async def get_memory(self, memory_id: str, memory_type: MemoryType) -> Optional[MemoryModel]:
        """Get a memory by ID and type"""
        engine = self.get_engine(memory_type)
        if not engine:
            return None
        
        return await engine.get_memory(memory_id)
    
    async def search_memories(self, query: MemorySearchQuery) -> List[MemorySearchResult]:
        """Search across specified memory types or all types"""
        if not query.memory_types:
            # Search all memory types
            memory_types = list(MemoryType)
        else:
            memory_types = query.memory_types
        
        all_results = []
        
        # Search each memory type
        for memory_type in memory_types:
            engine = self.get_engine(memory_type)
            if engine:
                type_results = await engine.search_memories(query)
                all_results.extend(type_results)
        
        # Sort by similarity score and re-rank
        all_results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Update ranks and limit results
        for i, result in enumerate(all_results[:query.top_k]):
            result.rank = i + 1
        
        return all_results[:query.top_k]
    
    async def update_memory(
        self, 
        memory_id: str, 
        memory_type: MemoryType, 
        updates: Dict[str, Any]
    ) -> MemoryOperationResult:
        """Update a memory"""
        engine = self.get_engine(memory_type)
        if not engine:
            return MemoryOperationResult(
                success=False,
                operation="update",
                message=f"No engine found for memory type: {memory_type}"
            )
        
        return await engine.update_memory(memory_id, updates)
    
    async def delete_memory(self, memory_id: str, memory_type: MemoryType) -> MemoryOperationResult:
        """Delete a memory"""
        engine = self.get_engine(memory_type)
        if not engine:
            return MemoryOperationResult(
                success=False,
                operation="delete",
                message=f"No engine found for memory type: {memory_type}"
            )
        
        return await engine.delete_memory(memory_id)
    
    # Intelligent memory processing - primary interface
    
    # Factual memory operations
    async def store_factual_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Store factual memory from dialog using intelligent processing"""
        engine = self.engines[MemoryType.FACTUAL]
        return await engine.store_factual_memory(
            user_id, dialog_content, importance_score
        )
    
    async def search_facts_by_subject(self, user_id: str, subject: str, limit: int = 10) -> List[FactualMemory]:
        """Search facts by subject"""
        engine = self.engines[MemoryType.FACTUAL]
        return await engine.search_facts_by_subject(user_id, subject, limit)
    
    async def search_facts_by_fact_type(self, user_id: str, fact_type: str, limit: int = 10) -> List[FactualMemory]:
        """Search facts by type"""
        engine = self.engines[MemoryType.FACTUAL]
        return await engine.search_facts_by_type(user_id, fact_type, limit)
    
    async def search_facts_by_confidence(self, user_id: str, min_confidence: float = 0.7, limit: int = 10) -> List[FactualMemory]:
        """Search high-confidence facts"""
        engine = self.engines[MemoryType.FACTUAL]
        return await engine.search_facts_by_confidence(user_id, min_confidence, limit)
    
    async def search_facts_by_source(self, user_id: str, source: str, limit: int = 10) -> List[FactualMemory]:
        """Search facts by source"""
        engine = self.engines[MemoryType.FACTUAL]
        return await engine.search_facts_by_source(user_id, source, limit)
    
    async def search_facts_by_verification(self, user_id: str, verification_status: str, limit: int = 10) -> List[FactualMemory]:
        """Search facts by verification status"""
        engine = self.engines[MemoryType.FACTUAL]
        return await engine.search_facts_by_verification(user_id, verification_status, limit)
    
    # Procedural memory operations
    async def store_procedural_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Store procedural memory from dialog using intelligent processing"""
        engine = self.engines[MemoryType.PROCEDURAL]
        return await engine.store_procedural_memory(
            user_id, dialog_content, importance_score
        )
    
    async def search_procedures_by_domain(self, user_id: str, domain: str, limit: int = 10) -> List[ProceduralMemory]:
        """Search procedures by domain"""
        engine = self.engines[MemoryType.PROCEDURAL]
        return await engine.search_procedures_by_domain(user_id, domain, limit)
    
    async def search_procedures_by_skill_type(self, user_id: str, skill_type: str, limit: int = 10) -> List[ProceduralMemory]:
        """Search procedures by skill type"""
        engine = self.engines[MemoryType.PROCEDURAL]
        return await engine.search_procedures_by_skill_type(user_id, skill_type, limit)
    
    async def search_procedures_by_difficulty(self, user_id: str, difficulty_level: int, limit: int = 10) -> List[ProceduralMemory]:
        """Search procedures by difficulty level"""
        engine = self.engines[MemoryType.PROCEDURAL]
        return await engine.search_procedures_by_difficulty(user_id, difficulty_level, limit)
    
    # Episodic memory operations
    async def store_episodic_memory(
        self,
        user_id: str,
        dialog_content: str,
        episode_date: Optional[datetime] = None,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Store episodic memory from dialog using intelligent processing"""
        engine = self.engines[MemoryType.EPISODIC]
        return await engine.store_episode(
            user_id, dialog_content, importance_score=importance_score
        )
    
    async def search_episodes_by_timeframe(
        self, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime,
        limit: int = 10
    ) -> List[EpisodicMemory]:
        """Search episodes in a timeframe"""
        engine = self.engines[MemoryType.EPISODIC]
        return await engine.search_episodes_by_timeframe(user_id, start_date, end_date, limit)
    
    async def search_episodes_by_participant(self, user_id: str, participant: str, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes by participant"""
        engine = self.engines[MemoryType.EPISODIC]
        return await engine.search_episodes_by_participant(user_id, participant, limit)
    
    async def search_episodes_by_event_type(self, user_id: str, event_type: str, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes by event type"""
        engine = self.engines[MemoryType.EPISODIC]
        return await engine.search_episodes_by_event_type(user_id, event_type, limit)
    
    async def search_episodes_by_location(self, user_id: str, location: str, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes by location"""
        engine = self.engines[MemoryType.EPISODIC]
        return await engine.search_episodes_by_location(user_id, location, limit)
    
    async def search_episodes_by_emotional_valence(self, user_id: str, min_valence: float, max_valence: float, limit: int = 10) -> List[EpisodicMemory]:
        """Search episodes by emotional valence range"""
        engine = self.engines[MemoryType.EPISODIC]
        return await engine.search_episodes_by_emotional_valence(user_id, min_valence, max_valence, limit)
    
    # Semantic memory operations  
    async def store_semantic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Store semantic memory from dialog using intelligent processing"""
        engine = self.engines[MemoryType.SEMANTIC]
        return await engine.store_semantic_memory(
            user_id, dialog_content, importance_score
        )
    
    async def search_concepts_by_category(self, user_id: str, category: str, limit: int = 10) -> List[SemanticMemory]:
        """Search concepts by category"""
        engine = self.engines[MemoryType.SEMANTIC]
        return await engine.search_concepts_by_category(user_id, category, limit)
    
    async def search_concepts_by_concept_type(self, user_id: str, concept_type: str, limit: int = 10) -> List[SemanticMemory]:
        """Search concepts by concept type"""
        engine = self.engines[MemoryType.SEMANTIC]
        return await engine.search_concepts_by_concept_type(user_id, concept_type, limit)
    
    async def search_concepts_by_mastery_level(self, user_id: str, min_mastery: float, limit: int = 10) -> List[SemanticMemory]:
        """Search concepts by mastery level"""
        engine = self.engines[MemoryType.SEMANTIC]
        return await engine.search_concepts_by_mastery_level(user_id, min_mastery, limit)
    
    # Working memory operations
    async def store_working_memory(
        self,
        user_id: str,
        dialog_content: str,
        current_task_context: Optional[Dict[str, Any]] = None,
        ttl_seconds: int = 3600,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Store working memory from dialog using intelligent processing"""
        engine = self.engines[MemoryType.WORKING]
        # Convert ttl_seconds to expires_at datetime
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        # Map to engine's actual method signature
        return await engine.store_working_memory(
            user_id, dialog_content, priority="medium", expires_at=expires_at
        )
    
    async def get_active_working_memories(self, user_id: str) -> List[WorkingMemory]:
        """Get active working memories"""
        engine = self.engines[MemoryType.WORKING]
        return await engine.get_active_working_memories(user_id)
    
    async def search_working_memories_by_context_type(self, user_id: str, context_type: str, limit: int = 10) -> List[WorkingMemory]:
        """Search working memories by context type"""
        engine = self.engines[MemoryType.WORKING]
        return await engine.search_working_memories_by_context_type(user_id, context_type, limit)
    
    async def search_working_memories_by_priority(self, user_id: str, min_priority: int, limit: int = 10) -> List[WorkingMemory]:
        """Search working memories by priority level"""
        engine = self.engines[MemoryType.WORKING]
        return await engine.search_working_memories_by_priority(user_id, min_priority, limit)
    
    # Session memory operations
    async def store_session_message(
        self,
        user_id: str,
        session_id: str,
        message_content: str,
        message_type: str = "human",
        role: str = "user",
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """Store session message with intelligent processing"""
        engine = self.engines[MemoryType.SESSION]
        # Map to engine's actual method signature
        return await engine.store_session_memory(
            user_id, session_id, message_content, message_count=1
        )

    async def summarize_session(
        self,
        user_id: str,
        session_id: str,
        force_update: bool = False,
        compression_level: str = "medium"
    ) -> MemoryOperationResult:
        """Summarize session conversation intelligently"""
        engine = self.engines[MemoryType.SESSION]
        return await engine.summarize_session(
            user_id, session_id, force_update, compression_level
        )

    async def get_session_context(
        self,
        user_id: str,
        session_id: str,
        include_summaries: bool = True,
        max_recent_messages: int = 5
    ) -> Dict[str, Any]:
        """Get comprehensive session context"""
        engine = self.engines[MemoryType.SESSION]
        return await engine.get_session_context(
            user_id, session_id, include_summaries, max_recent_messages
        )

    
    async def get_session_memories(self, user_id: str, session_id: str) -> List[SessionMemory]:
        """Get session memories"""
        engine = self.engines[MemoryType.SESSION]
        return await engine.get_session_memories(user_id, session_id)
    
    # Advanced memory operations
    async def find_memory_associations(
        self, 
        memory_id: str, 
        memory_type: MemoryType,
        limit: int = 10
    ) -> List[MemoryAssociation]:
        """Find associations for a memory"""
        try:
            result = self.db.table('memory_associations')\
                .select('*')\
                .eq('source_memory_id', memory_id)\
                .order('strength', desc=True)\
                .limit(limit)\
                .execute()
            
            associations = []
            for data in result.data or []:
                association = MemoryAssociation(**data)
                associations.append(association)
            
            return associations
            
        except Exception as e:
            logger.error(f"Failed to find memory associations: {e}")
            return []
    
    async def create_memory_association(
        self,
        source_memory_id: str,
        target_memory_id: str,
        association_type: str,
        strength: float,
        user_id: str
    ) -> MemoryOperationResult:
        """Create an association between memories"""
        try:
            association = MemoryAssociation(
                source_memory_id=source_memory_id,
                target_memory_id=target_memory_id,
                association_type=association_type,
                strength=strength,
                user_id=user_id
            )
            
            result = self.db.table('memory_associations')\
                .insert(association.model_dump())\
                .execute()
            
            if result.data:
                return MemoryOperationResult(
                    success=True,
                    operation="create_association",
                    message="Association created successfully",
                    data={"association": result.data[0]}
                )
            else:
                raise Exception("No data returned from insert")
                
        except Exception as e:
            logger.error(f"Failed to create memory association: {e}")
            return MemoryOperationResult(
                success=False,
                operation="create_association",
                message=f"Failed to create association: {str(e)}"
            )
    
    async def get_memory_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive memory statistics for a user with performance optimization"""
        try:
            stats = {
                'user_id': user_id,
                'total_memories': 0,
                'by_type': {},
                'recent_activity': {},
                'last_accessed': {},
                'intelligence_metrics': {}
            }
            
            # Count memories by type with parallel queries for better performance
            import asyncio
            count_tasks = []
            
            for memory_type in MemoryType:
                engine = self.get_engine(memory_type)
                if engine and hasattr(engine, 'table_name'):
                    async def count_memories(mem_type, eng):
                        try:
                            result = self.db.table(eng.table_name)\
                                .select('id', count='exact')\
                                .eq('user_id', user_id)\
                                .execute()
                            
                            count = result.count if hasattr(result, 'count') else 0
                            return mem_type.value, count
                        except Exception as e:
                            logger.warning(f"Failed to count {mem_type} memories: {e}")
                            return mem_type.value, 0
                    
                    count_tasks.append(count_memories(memory_type, engine))
            
            # Execute all counts in parallel
            if count_tasks:
                results = await asyncio.gather(*count_tasks, return_exceptions=True)
                for result in results:
                    if not isinstance(result, Exception):
                        memory_type_name, count = result
                        stats['by_type'][memory_type_name] = count
                        stats['total_memories'] += count
            
            # Add intelligence metrics
            if stats['total_memories'] > 0:
                stats['intelligence_metrics'] = {
                    'knowledge_diversity': len([count for count in stats['by_type'].values() if count > 0]),
                    'memory_distribution': stats['by_type'],
                    'total_knowledge_items': stats['total_memories']
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get memory statistics: {e}")
            return {'error': str(e), 'user_id': user_id}
    
    async def batch_store_memories(self, memories: List[MemoryModel]) -> List[MemoryOperationResult]:
        """Store multiple memories efficiently using batch processing"""
        try:
            # Group memories by type for optimized batch processing
            memory_groups = {}
            for memory in memories:
                memory_type = memory.memory_type
                if memory_type not in memory_groups:
                    memory_groups[memory_type] = []
                memory_groups[memory_type].append(memory)
            
            # Process each group with its specialized engine
            import asyncio
            batch_tasks = []
            
            for memory_type, memory_list in memory_groups.items():
                engine = self.get_engine(memory_type)
                if engine:
                    # Create batch storage task for each engine
                    async def store_batch(eng, mem_list):
                        results = []
                        for memory in mem_list:
                            result = await eng.store_memory(memory)
                            results.append(result)
                        return results
                    
                    batch_tasks.append(store_batch(engine, memory_list))
            
            # Execute all batch operations in parallel
            if batch_tasks:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Flatten results
                all_results = []
                for batch_result in batch_results:
                    if not isinstance(batch_result, Exception):
                        all_results.extend(batch_result)
                    else:
                        logger.error(f"Batch storage failed: {batch_result}")
                
                return all_results
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to batch store memories: {e}")
            return []
    
    async def intelligent_memory_consolidation(self, user_id: str) -> Dict[str, Any]:
        """Perform intelligent memory consolidation and optimization"""
        try:
            consolidation_stats = {
                'user_id': user_id,
                'consolidation_date': datetime.now().isoformat(),
                'actions_taken': [],
                'memory_optimizations': {}
            }
            
            # Clean up expired working memories
            cleanup_result = await self.cleanup_expired_memories(user_id)
            if cleanup_result.success:
                consolidation_stats['actions_taken'].append('cleaned_expired_working_memories')
            
            # Get memory statistics for analysis
            stats = await self.get_memory_statistics(user_id)
            consolidation_stats['memory_optimizations'] = stats.get('intelligence_metrics', {})
            
            # Optimize each memory type
            for memory_type in MemoryType:
                engine = self.get_engine(memory_type)
                if engine and hasattr(engine, 'optimize_memory_storage'):
                    try:
                        optimization_result = await engine.optimize_memory_storage(user_id)
                        consolidation_stats['actions_taken'].append(f'optimized_{memory_type.value}_storage')
                    except Exception as e:
                        logger.warning(f"Memory optimization failed for {memory_type}: {e}")
            
            logger.info(f"Memory consolidation completed for user {user_id}")
            return consolidation_stats
            
        except Exception as e:
            logger.error(f"Failed to perform memory consolidation: {e}")
            return {'error': str(e), 'user_id': user_id}
    
    # Resource compatibility methods
    def get_database_client(self):
        """Get database client for resource access"""
        return self.db
    
    async def get_memory_resource_data(self, memory_type: str, user_id: str, **filters) -> List[Dict[str, Any]]:
        """Get raw memory data for resource files - maintains compatibility with existing resources"""
        try:
            engine = None
            table_name = None
            
            # Map memory types to engines and table names
            type_mapping = {
                'factual': (MemoryType.FACTUAL, 'factual_memories'),
                'procedural': (MemoryType.PROCEDURAL, 'procedural_memories'),
                'episodic': (MemoryType.EPISODIC, 'episodic_memories'),
                'semantic': (MemoryType.SEMANTIC, 'semantic_memories'),
                'working': (MemoryType.WORKING, 'working_memories'),
                'session': (MemoryType.SESSION, 'session_memories')
            }
            
            if memory_type in type_mapping:
                memory_enum, table_name = type_mapping[memory_type]
                engine = self.get_engine(memory_enum)
            
            if not engine or not table_name:
                return []
            
            # Build query
            query = self.db.table(table_name).select('*').eq('user_id', user_id)
            
            # Apply filters
            for key, value in filters.items():
                if key == 'limit':
                    query = query.limit(value)
                elif key == 'order_by':
                    desc = filters.get('desc', False)
                    query = query.order(value, desc=desc)
                elif key == 'is_active':
                    query = query.eq('is_active', value)
                else:
                    query = query.eq(key, value)
            
            result = query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get memory resource data: {e}")
            return []
    
    async def cleanup_expired_memories(self, user_id: Optional[str] = None) -> MemoryOperationResult:
        """Clean up expired working memories"""
        engine = self.engines[MemoryType.WORKING]
        return await engine.cleanup_expired_memories(user_id)
    
    async def backup_user_memories(self, user_id: str) -> Dict[str, Any]:
        """Create a backup of all user memories"""
        try:
            backup = {
                'user_id': user_id,
                'backup_date': datetime.now().isoformat(),
                'memories': {}
            }
            
            # Backup each memory type
            for memory_type in MemoryType:
                engine = self.get_engine(memory_type)
                if engine:
                    try:
                        result = self.db.table(engine.table_name)\
                            .select('*')\
                            .eq('user_id', user_id)\
                            .execute()
                        
                        backup['memories'][memory_type.value] = result.data or []
                        
                    except Exception as e:
                        logger.warning(f"Failed to backup {memory_type} memories: {e}")
                        backup['memories'][memory_type.value] = []
            
            return backup
            
        except Exception as e:
            logger.error(f"Failed to backup user memories: {e}")
            return {'error': str(e)}


# Global instance for easy import - uses shared adapters for efficiency
memory_service = MemoryService()

# Convenience functions for core operations
async def store_memory(memory: MemoryModel) -> MemoryOperationResult:
    """Store a memory using the appropriate engine"""
    return await memory_service.store_memory(memory)

async def search_memories(query: MemorySearchQuery) -> List[MemorySearchResult]:
    """Search memories across types using semantic similarity"""
    return await memory_service.search_memories(query)

# Intelligent processing convenience functions
async def store_factual_memory(user_id: str, dialog_content: str, importance_score: float = 0.5) -> MemoryOperationResult:
    """Store factual memory from dialog using intelligent processing"""
    return await memory_service.store_factual_memory(user_id, dialog_content, importance_score)

async def store_episodic_memory(user_id: str, dialog_content: str, episode_date: Optional[datetime] = None, importance_score: float = 0.5) -> MemoryOperationResult:
    """Store episodic memory from dialog using intelligent processing"""
    return await memory_service.store_episodic_memory(user_id, dialog_content, episode_date, importance_score)

async def store_semantic_memory(user_id: str, dialog_content: str, importance_score: float = 0.5) -> MemoryOperationResult:
    """Store semantic memory from dialog using intelligent processing"""
    return await memory_service.store_semantic_memory(user_id, dialog_content, importance_score)

async def store_procedural_memory(user_id: str, dialog_content: str, importance_score: float = 0.5) -> MemoryOperationResult:
    """Store procedural memory from dialog using intelligent processing"""
    return await memory_service.store_procedural_memory(user_id, dialog_content, importance_score)

async def store_working_memory(user_id: str, dialog_content: str, current_task_context: Optional[Dict[str, Any]] = None, ttl_seconds: int = 3600, importance_score: float = 0.5) -> MemoryOperationResult:
    """Store working memory from dialog using intelligent processing"""
    return await memory_service.store_working_memory(user_id, dialog_content, current_task_context, ttl_seconds, importance_score)

# Batch and optimization functions
async def batch_store_memories(memories: List[MemoryModel]) -> List[MemoryOperationResult]:
    """Store multiple memories efficiently using batch processing"""
    return await memory_service.batch_store_memories(memories)

async def intelligent_memory_consolidation(user_id: str) -> Dict[str, Any]:
    """Perform intelligent memory consolidation and optimization"""
    return await memory_service.intelligent_memory_consolidation(user_id)

async def get_memory_statistics(user_id: str) -> Dict[str, Any]:
    """Get comprehensive memory statistics for a user"""
    return await memory_service.get_memory_statistics(user_id)