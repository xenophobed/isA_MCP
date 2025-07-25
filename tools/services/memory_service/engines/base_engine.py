#!/usr/bin/env python3
"""
Base Memory Engine
Clean, efficient base class for all memory type engines
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Clean imports
from core.database.supabase_client import get_supabase_client
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator
from core.logging import get_logger
from ..models import MemoryModel, MemorySearchQuery, MemorySearchResult, MemoryOperationResult

logger = get_logger(__name__)


class BaseMemoryEngine(ABC):
    """Base class for memory engines - clean and efficient"""
    
    def __init__(self):
        self._db = None
        self._embedder = None
    
    @property
    def db(self):
        """Lazy-loaded database client"""
        if self._db is None:
            self._db = get_supabase_client()
        return self._db
    
    @property
    def embedder(self):
        """Lazy-loaded embedding generator"""
        if self._embedder is None:
            self._embedder = EmbeddingGenerator()
        return self._embedder
        
    @property
    @abstractmethod
    def table_name(self) -> str:
        """Name of the database table for this memory type"""
        pass
    
    @property  
    @abstractmethod
    def memory_type(self) -> str:
        """Memory type identifier"""
        pass
    
    async def store_memory(self, memory: MemoryModel) -> MemoryOperationResult:
        """Store a memory with automatic embedding generation"""
        try:
            # Generate embedding if not provided
            if not memory.embedding:
                memory.embedding = await self.embedder.embed_single(memory.content)
            
            # Prepare data for storage
            memory_data = self._prepare_for_storage(memory)
            
            # Insert into database
            result = self.db.table(self.table_name).insert(memory_data).execute()
            
            if result.data:
                logger.info(f"✅ Stored {self.memory_type} memory: {memory.id}")
                return MemoryOperationResult(
                    success=True,
                    memory_id=memory.id,
                    operation="store",
                    message=f"Successfully stored {self.memory_type} memory",
                    data={"memory": result.data[0]}
                )
            else:
                raise Exception("No data returned from insert")
                
        except Exception as e:
            logger.error(f"❌ Failed to store {self.memory_type} memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory.id,
                operation="store",
                message=f"Failed to store memory: {str(e)}"
            )
    
    async def get_memory(self, memory_id: str) -> Optional[MemoryModel]:
        """Get a memory by ID"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('id', memory_id)\
                .single()\
                .execute()
            
            if result.data:
                return await self._parse_from_storage(result.data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get {self.memory_type} memory {memory_id}: {e}")
            return None
    
    async def search_memories(self, query: MemorySearchQuery) -> List[MemorySearchResult]:
        """Search memories using vector similarity - optimized"""
        try:
            # Build database query with filters first (more efficient)
            db_query = self.db.table(self.table_name).select('*')
            
            if query.user_id:
                db_query = db_query.eq('user_id', query.user_id)
            
            # Apply other filters early to reduce dataset
            if query.importance_min:
                db_query = db_query.gte('importance_score', query.importance_min)
            if query.confidence_min:
                db_query = db_query.gte('confidence', query.confidence_min)
            if query.created_after:
                db_query = db_query.gte('created_at', query.created_after.isoformat())
            if query.created_before:
                db_query = db_query.lte('created_at', query.created_before.isoformat())
            
            # Limit initial results for performance
            db_query = db_query.limit(min(query.top_k * 3, 100))  # Get more than needed for filtering
            
            result = db_query.execute()
            
            if not result.data:
                return []
            
            # Calculate similarities in parallel for better performance
            search_results = []
            similarity_tasks = []
            
            for memory_data in result.data:
                memory = await self._parse_from_storage(memory_data)
                if memory.embedding:
                    task = self._calculate_similarity(query.query, memory)
                    similarity_tasks.append((task, memory))
            
            # Process similarities concurrently
            for task, memory in similarity_tasks:
                try:
                    similarity = await task
                    if similarity >= query.similarity_threshold:
                        search_results.append(MemorySearchResult(
                            memory=memory,
                            similarity_score=similarity,
                            rank=1  # Temporary value, will be set after sorting
                        ))
                except Exception as e:
                    logger.warning(f"⚠️ Failed to calculate similarity for memory {memory.id}: {e}")
            
            # Sort by similarity and assign ranks
            search_results.sort(key=lambda x: x.similarity_score, reverse=True)
            for i, result in enumerate(search_results):
                result.rank = i + 1
            
            return search_results[:query.top_k]
            
        except Exception as e:
            logger.error(f"❌ Failed to search {self.memory_type} memories: {e}")
            return []
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> MemoryOperationResult:
        """Update a memory with automatic embedding regeneration"""
        try:
            # If content is updated, regenerate embedding
            if 'content' in updates:
                updates['embedding'] = json.dumps(
                    await self.embedder.embed_single(updates['content'])
                )
            
            # Add timestamp
            updates['updated_at'] = datetime.now().isoformat()
            
            # Handle JSON serialization
            updates = self._serialize_json_fields(updates)
            
            result = self.db.table(self.table_name)\
                .update(updates)\
                .eq('id', memory_id)\
                .execute()
            
            if result.data:
                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    operation="update",
                    message=f"Successfully updated {self.memory_type} memory",
                    data={"memory": result.data[0]}
                )
            else:
                raise Exception("No data returned from update")
                
        except Exception as e:
            logger.error(f"❌ Failed to update {self.memory_type} memory {memory_id}: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="update",
                message=f"Failed to update memory: {str(e)}"
            )
    
    async def delete_memory(self, memory_id: str) -> MemoryOperationResult:
        """Delete a memory"""
        try:
            self.db.table(self.table_name)\
                .delete()\
                .eq('id', memory_id)\
                .execute()
            
            logger.info(f"🗑️ Deleted {self.memory_type} memory: {memory_id}")
            return MemoryOperationResult(
                success=True,
                memory_id=memory_id,
                operation="delete",
                message=f"Successfully deleted {self.memory_type} memory"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to delete {self.memory_type} memory {memory_id}: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="delete",
                message=f"Failed to delete memory: {str(e)}"
            )
    
    async def find_related_memories(self, memory_id: str, limit: int = 5) -> List[MemorySearchResult]:
        """Find memories related to a given memory"""
        try:
            # Get the source memory
            source_memory = await self.get_memory(memory_id)
            if not source_memory:
                return []
            
            # Search for similar memories
            query = MemorySearchQuery(
                query=source_memory.content,
                user_id=source_memory.user_id,
                top_k=limit + 1,  # +1 to exclude self
                similarity_threshold=0.6
            )
            
            results = await self.search_memories(query)
            
            # Remove the source memory from results
            related = [r for r in results if r.memory.id != memory_id]
            return related[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to find related memories for {memory_id}: {e}")
            return []
    
    # Helper methods for data processing
    
    def _prepare_for_storage(self, memory: MemoryModel) -> Dict[str, Any]:
        """Prepare memory data for database storage"""
        # Get serialized data
        memory_data = memory.model_dump(mode='json')
        
        # Handle embedding and JSON fields
        memory_data['embedding'] = json.dumps(memory.embedding)
        memory_data = self._serialize_json_fields(memory_data)
        
        # Convert datetime objects
        memory_data = self._serialize_datetime_fields(memory_data)
        
        # Remove common fields that don't exist in database schemas
        # 注意：importance_score在factual_memories中存在，但在episodic_memories中不存在
        common_fields_to_remove = ['access_count', 'last_accessed_at']
        for field in common_fields_to_remove:
            memory_data.pop(field, None)
        
        # Allow subclasses to customize
        return self._customize_for_storage(memory_data)
    
    async def _parse_from_storage(self, data: Dict[str, Any]) -> MemoryModel:
        """Parse memory data from database"""
        # Parse JSON fields
        data = self._deserialize_json_fields(data)
        
        # Allow subclasses to customize
        data = self._customize_from_storage(data)
        
        return await self._create_memory_model(data)
    
    def _serialize_json_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize JSON fields for storage"""
        json_fields = ['context', 'tags', 'participants', 'key_events', 'outcomes']
        for field in json_fields:
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field])
        return data
    
    def _deserialize_json_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize JSON fields from storage"""
        json_fields = ['embedding', 'context', 'tags', 'participants', 'key_events', 'outcomes']
        for field in json_fields:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except (json.JSONDecodeError, TypeError):
                    # Keep as string if can't parse
                    pass
        return data
    
    def _serialize_datetime_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime objects to ISO strings"""
        datetime_fields = ['created_at', 'updated_at', 'last_accessed_at', 'expires_at', 'episode_date', 'occurred_at']
        for field in datetime_fields:
            if field in data and isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
        return data
    
    async def _calculate_similarity(self, query: str, memory: MemoryModel) -> float:
        """Calculate similarity between query and memory content"""
        try:
            return await self.embedder.compute_similarity(query, memory.content)
        except Exception as e:
            logger.warning(f"⚠️ Similarity calculation failed: {e}")
            return 0.0
    
    # Abstract methods for subclasses to override
    
    def _customize_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses to customize data before storage"""
        return data
    
    def _customize_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses to customize data after retrieval"""
        return data
    
    @abstractmethod
    async def _create_memory_model(self, data: Dict[str, Any]) -> MemoryModel:
        """Override in subclasses to create the correct memory model type"""
        pass