#!/usr/bin/env python3
"""
Base Memory Engine
Common functionality for all memory type engines
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json

import sys
import os
import importlib.util

# Import supabase client directly without triggering database __init__.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
supabase_client_path = os.path.join(project_root, 'core', 'database', 'supabase_client.py')

spec = importlib.util.spec_from_file_location("supabase_client", supabase_client_path)
supabase_client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supabase_client_module)

get_supabase_client = supabase_client_module.get_supabase_client
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator
from core.logging import get_logger
from ..models import MemoryModel, MemorySearchQuery, MemorySearchResult, MemoryOperationResult

logger = get_logger(__name__)


class BaseMemoryEngine(ABC):
    """Base class for memory engines using atomic adapter pattern"""
    
    def __init__(self):
        # Centralized adapters
        self.db = get_supabase_client()
        self.embedder = EmbeddingGenerator()
        
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
        """Store a memory with embedding generation"""
        try:
            # Generate embedding if not provided
            if not memory.embedding:
                memory.embedding = await self.embedder.embed_single(memory.content)
            
            # Prepare data for database using model_dump with serialization mode
            memory_data = memory.model_dump(mode='json')
            memory_data['embedding'] = json.dumps(memory.embedding)  # Store as JSON
            memory_data['context'] = json.dumps(memory.context)
            memory_data['tags'] = json.dumps(memory.tags)
            
            # Handle datetime fields - convert to ISO format strings
            datetime_fields = ['created_at', 'updated_at', 'last_accessed_at', 'expires_at', 'episode_date']
            for field in datetime_fields:
                if field in memory_data and isinstance(memory_data[field], datetime):
                    memory_data[field] = memory_data[field].isoformat()
            
            # Additional check for any remaining datetime objects
            def serialize_datetime_recursive(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: serialize_datetime_recursive(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_datetime_recursive(item) for item in obj]
                return obj
            
            memory_data = serialize_datetime_recursive(memory_data)
            
            # Custom fields for specific memory types
            memory_data = await self._prepare_memory_data(memory_data)
            
            # Insert into database
            result = self.db.table(self.table_name).insert(memory_data).execute()
            
            if result.data:
                logger.info(f"Stored {self.memory_type} memory: {memory.id}")
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
            logger.error(f"Failed to store {self.memory_type} memory: {e}")
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
                # Update access tracking - temporarily disabled
                # await self._track_access(memory_id)
                return await self._parse_memory_data(result.data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get {self.memory_type} memory {memory_id}: {e}")
            return None
    
    async def search_memories(self, query: MemorySearchQuery) -> List[MemorySearchResult]:
        """Search memories using vector similarity"""
        try:
            # Generate embedding for query
            query_embedding = await self.embedder.embed_single(query.query)
            
            # Get all memories for the user (could be optimized with vector search)
            db_query = self.db.table(self.table_name).select('*')
            
            if query.user_id:
                db_query = db_query.eq('user_id', query.user_id)
            
            # Apply filters
            if query.importance_min:
                db_query = db_query.gte('importance_score', query.importance_min)
            if query.confidence_min:
                db_query = db_query.gte('confidence', query.confidence_min)
            if query.created_after:
                db_query = db_query.gte('created_at', query.created_after.isoformat())
            if query.created_before:
                db_query = db_query.lte('created_at', query.created_before.isoformat())
            
            result = db_query.execute()
            
            if not result.data:
                return []
            
            # Calculate similarities and rank
            search_results = []
            for i, memory_data in enumerate(result.data):
                memory = await self._parse_memory_data(memory_data)
                
                if memory.embedding:
                    # Use ISA client for similarity calculation
                    similarity = await self.embedder.compute_similarity(
                        query.query, 
                        memory.content
                    )
                    
                    if similarity >= query.similarity_threshold:
                        search_results.append(MemorySearchResult(
                            memory=memory,
                            similarity_score=similarity,
                            rank=len(search_results) + 1
                        ))
            
            # Sort by similarity and limit results
            search_results.sort(key=lambda x: x.similarity_score, reverse=True)
            return search_results[:query.top_k]
            
        except Exception as e:
            logger.error(f"Failed to search {self.memory_type} memories: {e}")
            return []
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> MemoryOperationResult:
        """Update a memory"""
        try:
            # If content is updated, regenerate embedding
            if 'content' in updates:
                updates['embedding'] = json.dumps(
                    await self.embedder.embed_single(updates['content'])
                )
            
            updates['updated_at'] = datetime.now().isoformat()
            
            # Handle JSON fields
            if 'context' in updates:
                updates['context'] = json.dumps(updates['context'])
            if 'tags' in updates:
                updates['tags'] = json.dumps(updates['tags'])
            
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
            logger.error(f"Failed to update {self.memory_type} memory {memory_id}: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="update",
                message=f"Failed to update memory: {str(e)}"
            )
    
    async def delete_memory(self, memory_id: str) -> MemoryOperationResult:
        """Delete a memory"""
        try:
            result = self.db.table(self.table_name)\
                .delete()\
                .eq('id', memory_id)\
                .execute()
            
            return MemoryOperationResult(
                success=True,
                memory_id=memory_id,
                operation="delete",
                message=f"Successfully deleted {self.memory_type} memory"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete {self.memory_type} memory {memory_id}: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="delete",
                message=f"Failed to delete memory: {str(e)}"
            )
    
    async def _track_access(self, memory_id: str, user_id: str = None) -> None:
        """Track memory access for cognitive decay modeling using metadata table"""
        try:
            # Skip tracking if no user_id available
            if not user_id:
                return
                
            # Update memory_metadata table instead of direct table access
            await self.db.table('memory_metadata')\
                .upsert({
                    'memory_id': memory_id,
                    'memory_type': self.memory_type,
                    'user_id': user_id,
                    'access_count': 1,  # This will be incremented by a database trigger
                    'last_accessed_at': datetime.now().isoformat()
                })\
                .execute()
        except Exception as e:
            logger.warning(f"Failed to track access for memory {memory_id}: {e}")
    
    async def _prepare_memory_data(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare memory data for storage - override in subclasses"""
        return memory_data
    
    async def _parse_memory_data(self, data: Dict[str, Any]) -> MemoryModel:
        """Parse memory data from database - override in subclasses"""
        # Parse JSON fields
        if 'embedding' in data and isinstance(data['embedding'], str):
            data['embedding'] = json.loads(data['embedding'])
        if 'context' in data and isinstance(data['context'], str):
            data['context'] = json.loads(data['context']) 
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags'])
        
        return MemoryModel(**data)
    
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
            logger.error(f"Failed to find related memories for {memory_id}: {e}")
            return []