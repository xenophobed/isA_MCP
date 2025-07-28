#!/usr/bin/env python3
"""
Factual Memory Engine
Simple, clean implementation for factual memory management
"""

from typing import Dict, Any, List
from datetime import datetime
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import FactualMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class FactualMemoryEngine(BaseMemoryEngine):
    """Simple engine for managing factual memories"""
    
    def __init__(self):
        super().__init__()
        self.text_extractor = TextExtractor()
    
    @property
    def table_name(self) -> str:
        return "factual_memories"
    
    @property
    def memory_type(self) -> str:
        return "factual"
    
    async def store_factual_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Store factual memories by extracting facts from dialog
        
        Simple workflow: TextExtractor → FactualMemory → base.store_memory
        """
        try:
            # Extract facts using TextExtractor
            extraction_result = await self._extract_facts(dialog_content)
            
            if not extraction_result['success']:
                logger.error(f"Failed to extract facts: {extraction_result.get('error')}")
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_factual_memory",
                    message=f"Failed to extract facts: {extraction_result.get('error')}"
                )
            
            facts_data = extraction_result['data']
            stored_facts = []
            
            # Create and store each fact
            for fact in facts_data.get('facts', []):
                if self._is_valid_fact(fact):
                    # Create simple FactualMemory object with safe data conversion
                    object_value = fact.get('object_value', '')
                    if isinstance(object_value, list):
                        object_value = ', '.join(str(item) for item in object_value)
                    else:
                        object_value = str(object_value)
                    
                    factual_memory = FactualMemory(
                        user_id=user_id,
                        content=self._create_fact_content(fact),
                        fact_type=fact.get('fact_type', 'general'),
                        subject=str(fact.get('subject', '')),
                        predicate=str(fact.get('predicate', '')),
                        object_value=object_value,
                        context=str(fact.get('context', '')) if fact.get('context') else None,
                        confidence=float(fact.get('confidence', 0.8)),
                        importance_score=importance_score
                    )
                    
                    # Use upsert logic to handle duplicate facts
                    result = await self._store_or_update_fact(factual_memory)
                    
                    if result.success:
                        stored_facts.append(result.memory_id)
                        logger.info(f"✅ Stored/Updated fact: {factual_memory.subject} {factual_memory.predicate} {factual_memory.object_value}")
            
            if stored_facts:
                return MemoryOperationResult(
                    success=True,
                    memory_id=stored_facts[0] if len(stored_facts) == 1 else "",
                    operation="store_factual_memory",
                    message=f"Successfully stored {len(stored_facts)} factual memories",
                    data={"stored_facts": stored_facts, "total_facts": len(stored_facts)}
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_factual_memory",
                    message="No valid facts could be extracted and stored"
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to store factual memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_factual_memory",
                message=f"Failed to store factual memory: {str(e)}"
            )
    
    async def _store_or_update_fact(self, factual_memory: FactualMemory) -> MemoryOperationResult:
        """Store factual memory with upsert logic to handle duplicates"""
        try:
            # Generate embedding if not provided
            if not factual_memory.embedding:
                factual_memory.embedding = await self.embedder.embed_single(factual_memory.content)
            
            # Check if fact already exists (based on unique constraint)
            existing_result = self.db.table(self.table_name)\
                .select('id')\
                .eq('user_id', factual_memory.user_id)\
                .eq('fact_type', factual_memory.fact_type)\
                .eq('subject', factual_memory.subject)\
                .eq('predicate', factual_memory.predicate)\
                .execute()
            
            memory_data = self._prepare_for_storage(factual_memory)
            
            if existing_result.data:
                # Update existing fact
                existing_id = existing_result.data[0]['id']
                memory_data['updated_at'] = datetime.now().isoformat()
                
                result = self.db.table(self.table_name)\
                    .update(memory_data)\
                    .eq('id', existing_id)\
                    .execute()
                
                if result.data:
                    logger.info(f"✅ Updated existing fact: {factual_memory.subject} {factual_memory.predicate}")
                    return MemoryOperationResult(
                        success=True,
                        memory_id=existing_id,
                        operation="update",
                        message=f"Successfully updated factual memory",
                        data={"memory": result.data[0]}
                    )
            else:
                # Insert new fact
                result = self.db.table(self.table_name).insert(memory_data).execute()
                
                if result.data:
                    logger.info(f"✅ Inserted new fact: {factual_memory.subject} {factual_memory.predicate}")
                    return MemoryOperationResult(
                        success=True,
                        memory_id=factual_memory.id,
                        operation="store",
                        message=f"Successfully stored factual memory",
                        data={"memory": result.data[0]}
                    )
            
            # If we get here, something went wrong
            raise Exception("No data returned from database operation")
            
        except Exception as e:
            logger.error(f"❌ Failed to store/update factual memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=factual_memory.id,
                operation="store_or_update",
                message=f"Failed to store/update memory: {str(e)}"
            )
    
    async def search_facts_by_subject(self, user_id: str, subject: str, limit: int = 10) -> List[FactualMemory]:
        """Search facts by subject using database query"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('subject', f'%{subject}%')\
                .order('importance_score', desc=True)\
                .limit(limit)\
                .execute()
            
            facts = []
            for data in result.data or []:
                fact = await self._parse_from_storage(data)
                facts.append(fact)
            
            return facts
            
        except Exception as e:
            logger.error(f"❌ Failed to search facts by subject {subject}: {e}")
            return []

    async def search_facts_by_type(self, user_id: str, fact_type: str, limit: int = 10) -> List[FactualMemory]:
        """Search facts by type using database query"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('fact_type', fact_type)\
                .order('confidence', desc=True)\
                .limit(limit)\
                .execute()
            
            facts = []
            for data in result.data or []:
                fact = await self._parse_from_storage(data)
                facts.append(fact)
            
            return facts
            
        except Exception as e:
            logger.error(f"❌ Failed to search facts by type {fact_type}: {e}")
            return []
    
    # Alias for compatibility
    async def search_facts_by_fact_type(self, user_id: str, fact_type: str, limit: int = 10) -> List[FactualMemory]:
        """Alias for search_facts_by_type for compatibility"""
        return await self.search_facts_by_type(user_id, fact_type, limit)
    
    # Private helper methods
    
    async def _extract_facts(self, dialog_content: str) -> Dict[str, Any]:
        """Extract facts using TextExtractor with simple schema"""
        try:
            # Simple schema for fact extraction
            factual_schema = {
                "facts": "List of factual statements. Each fact should have: fact_type, subject, predicate, object_value, context, confidence (0.0-1.0)",
                "extraction_confidence": "Overall confidence in extraction quality (0.0-1.0)"
            }
            
            # Use TextExtractor to extract structured information
            extraction_result = await self.text_extractor.extract_key_information(
                text=dialog_content,
                schema=factual_schema
            )
            
            if extraction_result['success']:
                # Simple validation and cleanup
                data = extraction_result['data']
                if 'facts' not in data or not isinstance(data['facts'], list):
                    data['facts'] = []
                
                return {
                    'success': True,
                    'data': data,
                    'confidence': extraction_result.get('confidence', 0.7)
                }
            else:
                return extraction_result
            
        except Exception as e:
            logger.error(f"❌ Fact extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {'facts': []},
                'confidence': 0.0
            }
    
    def _is_valid_fact(self, fact: Dict[str, Any]) -> bool:
        """Simple validation for extracted facts"""
        required_fields = ['subject', 'predicate', 'object_value']
        return all(fact.get(field) for field in required_fields)
    
    def _create_fact_content(self, fact: Dict[str, Any]) -> str:
        """Create content string for embedding from fact structure"""
        subject = fact.get('subject', '')
        predicate = fact.get('predicate', '')
        object_value = fact.get('object_value', '')
        context = fact.get('context', '')
        
        content = f"{subject} {predicate} {object_value}"
        if context:
            content += f" ({context})"
        
        return content
    
    # Override base engine methods for factual-specific handling
    
    def _customize_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data before storage - remove model-only fields"""
        # Remove factual-specific fields that don't exist in database schema
        # 实际数据库有：context, confidence，但没有：content, memory_type, tags, related_facts, source, verification_status
        fields_to_remove = ['content', 'memory_type', 'tags', 'related_facts', 'source', 'verification_status']
        
        for field in fields_to_remove:
            data.pop(field, None)
        
        # Ensure required fields have defaults
        if 'fact_type' not in data:
            data['fact_type'] = 'general'
        if 'subject' not in data:
            data['subject'] = 'unknown'
        if 'predicate' not in data:
            data['predicate'] = 'is'
        if 'object_value' not in data:
            data['object_value'] = 'unknown'
        if 'confidence' not in data:
            data['confidence'] = 0.8
        
        return data
    
    def _customize_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data after retrieval - add model-required fields"""
        # Reconstruct content from fact structure for model
        if 'content' not in data:
            subject = data.get('subject', 'unknown')
            predicate = data.get('predicate', 'is')
            object_value = data.get('object_value', 'unknown')
            data['content'] = f"{subject} {predicate} {object_value}"
        
        # Add model-required fields with defaults (这些字段不在数据库中但model需要)
        if 'memory_type' not in data:
            data['memory_type'] = 'factual'
        if 'tags' not in data:
            data['tags'] = []
        if 'related_facts' not in data:
            data['related_facts'] = []
        if 'source' not in data:
            data['source'] = None
        if 'verification_status' not in data:
            data['verification_status'] = 'unverified'
        
        return data
    
    async def _create_memory_model(self, data: Dict[str, Any]) -> FactualMemory:
        """Create FactualMemory model from database data"""
        return FactualMemory(**data)