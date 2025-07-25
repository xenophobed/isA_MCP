#!/usr/bin/env python3
"""
Semantic Memory Engine
Simple, clean implementation for semantic memory management
"""

from typing import Dict, Any, List
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import SemanticMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class SemanticMemoryEngine(BaseMemoryEngine):
    """Simple engine for managing semantic memories"""
    
    def __init__(self):
        super().__init__()
        self.text_extractor = TextExtractor()
    
    @property
    def table_name(self) -> str:
        return "semantic_memories"
    
    @property
    def memory_type(self) -> str:
        return "semantic"
    
    async def store_semantic_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Store semantic memory by extracting concepts from dialog
        
        Simple workflow: TextExtractor → SemanticMemory → base.store_memory
        """
        try:
            # Extract concepts using TextExtractor
            extraction_result = await self._extract_concepts(dialog_content)
            
            if not extraction_result['success']:
                logger.error(f"Failed to extract concepts: {extraction_result.get('error')}")
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_semantic_memory",
                    message=f"Failed to extract concepts: {extraction_result.get('error')}"
                )
            
            concept_data = extraction_result['data']
            
            # Create SemanticMemory object with proper model fields
            semantic_memory = SemanticMemory(
                user_id=user_id,
                content=concept_data.get('definition', dialog_content[:200]),  # model需要但DB没有
                concept_type=concept_data.get('concept', 'unknown'),  # model字段，映射到DB的concept_name
                definition=concept_data.get('definition', ''),
                category=concept_data.get('domain', 'general'),  # model字段，映射到DB的concept_category
                properties=concept_data.get('properties', {}),
                related_concepts=concept_data.get('related_concepts', []),
                abstraction_level=concept_data.get('abstraction_level', 'medium'),
                confidence=float(concept_data.get('confidence', 0.8)),  # model需要但DB没有
                importance_score=importance_score  # model需要但DB没有
            )
            
            # Let base engine handle embedding and storage
            result = await self.store_memory(semantic_memory)
            
            if result.success:
                logger.info(f"✅ Stored concept: {semantic_memory.concept_type} ({semantic_memory.category})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store semantic memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_semantic_memory",
                message=f"Failed to store semantic memory: {str(e)}"
            )

    async def search_concepts_by_domain(self, user_id: str, domain: str, limit: int = 10) -> List[SemanticMemory]:
        """Search concepts by domain using database field concept_category"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('concept_category', domain)\
                .order('mastery_level', desc=True)\
                .limit(limit)\
                .execute()
            
            concepts = []
            for data in result.data or []:
                concept = await self._parse_from_storage(data)
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"❌ Failed to search concepts by domain {domain}: {e}")
            return []

    async def search_concepts_by_name(self, user_id: str, concept_name: str, limit: int = 10) -> List[SemanticMemory]:
        """Search concepts by name using database field concept_name"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('concept_name', f'%{concept_name}%')\
                .order('mastery_level', desc=True)\
                .limit(limit)\
                .execute()
            
            concepts = []
            for data in result.data or []:
                concept = await self._parse_from_storage(data)
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"❌ Failed to search concepts by name {concept_name}: {e}")
            return []
    
    # Alias methods for compatibility
    async def search_concepts_by_category(self, user_id: str, category: str, limit: int = 10) -> List[SemanticMemory]:
        """Alias for search_concepts_by_domain for compatibility"""
        return await self.search_concepts_by_domain(user_id, category, limit)
    
    async def search_concepts_by_concept_type(self, user_id: str, concept_type: str, limit: int = 10) -> List[SemanticMemory]:
        """Alias for search_concepts_by_domain for compatibility"""
        return await self.search_concepts_by_domain(user_id, concept_type, limit)
    
    async def search_concepts_by_mastery_level(self, user_id: str, min_mastery: float, limit: int = 10) -> List[SemanticMemory]:
        """Search concepts by minimum mastery level"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('mastery_level', min_mastery)\
                .order('mastery_level', desc=True)\
                .limit(limit)\
                .execute()
            
            concepts = []
            for data in result.data or []:
                concept = await self._parse_from_storage(data)
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"❌ Failed to search concepts by mastery level {min_mastery}: {e}")
            return []
    
    # Private helper methods
    
    async def _extract_concepts(self, dialog_content: str) -> Dict[str, Any]:
        """Extract concepts using TextExtractor with simple schema"""
        try:
            # Schema for concept extraction - 根据数据库字段设计
            concept_schema = {
                "concept": "Main concept or term being defined or discussed",
                "definition": "Clear definition or explanation of the concept",
                "domain": "Domain or field this concept belongs to (technology, science, business, etc.)",
                "properties": "Key properties or attributes of this concept (as dict)",
                "related_concepts": "List of related concepts or terms",
                "abstraction_level": "Level of abstraction (basic, medium, advanced)",
                "use_cases": "List of use cases or applications",
                "examples": "Examples demonstrating this concept",
                "learning_source": "Source of this knowledge (conversation, document, etc.)",
                "confidence": "Confidence in extraction quality (0.0-1.0)"
            }
            
            # Use TextExtractor to extract structured information
            extraction_result = await self.text_extractor.extract_key_information(
                text=dialog_content,
                schema=concept_schema
            )
            
            if extraction_result['success']:
                # Simple validation and cleanup
                data = extraction_result['data']
                
                # Ensure required fields with safe defaults
                if not data.get('concept'):
                    data['concept'] = 'unknown'
                if not data.get('definition'):
                    data['definition'] = dialog_content[:100] + '...' if len(dialog_content) > 100 else dialog_content
                if not data.get('domain'):
                    data['domain'] = 'general'
                
                # Ensure lists are lists
                for list_field in ['related_concepts', 'use_cases', 'examples']:
                    if not isinstance(data.get(list_field), list):
                        data[list_field] = []
                
                # Ensure dict fields are dicts
                if not isinstance(data.get('properties'), dict):
                    data['properties'] = {}
                
                # Ensure string fields have defaults
                if not data.get('abstraction_level'):
                    data['abstraction_level'] = 'medium'
                if not data.get('learning_source'):
                    data['learning_source'] = 'conversation'
                
                # Ensure numeric fields are numbers
                try:
                    data['confidence'] = float(data.get('confidence', 0.8))
                except (ValueError, TypeError):
                    data['confidence'] = 0.8
                
                return {
                    'success': True,
                    'data': data,
                    'confidence': extraction_result.get('confidence', 0.7)
                }
            else:
                return extraction_result
            
        except Exception as e:
            logger.error(f"❌ Concept extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {
                    'concept': 'unknown',
                    'definition': dialog_content[:100],
                    'domain': 'general',
                    'related_concepts': [],
                    'examples': [],
                    'confidence': 0.5
                },
                'confidence': 0.0
            }
    
    # Override base engine methods for semantic-specific handling
    
    def _customize_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data before storage - handle semantic-specific fields"""
        # Remove fields that don't exist in database schema
        # DB有：concept_name, concept_category, definition, properties, related_concepts, 
        #       hierarchical_level, parent_concept_id, use_cases, examples, mastery_level, learning_source
        # DB没有：content, memory_type, tags, confidence, access_count, last_accessed_at, importance_score, abstraction_level, context
        fields_to_remove = ['content', 'memory_type', 'tags', 'confidence', 'importance_score', 'abstraction_level', 'context']
        
        for field in fields_to_remove:
            data.pop(field, None)
        
        # Map model fields to database fields
        if 'concept_type' in data:
            data['concept_name'] = data.pop('concept_type')
        if 'category' in data:
            data['concept_category'] = data.pop('category')
        
        # Set default values for database-specific fields
        if 'concept_name' not in data:
            data['concept_name'] = 'unknown'
        if 'concept_category' not in data:
            data['concept_category'] = 'general'
        if 'definition' not in data:
            data['definition'] = 'No definition available'
        if 'properties' not in data:
            data['properties'] = {}
        if 'related_concepts' not in data:
            data['related_concepts'] = []
        if 'use_cases' not in data:
            data['use_cases'] = []
        if 'examples' not in data:
            data['examples'] = []
        if 'hierarchical_level' not in data:
            data['hierarchical_level'] = 1
        if 'mastery_level' not in data:
            data['mastery_level'] = 0.5
        if 'learning_source' not in data:
            data['learning_source'] = 'conversation'
        
        return data
    
    def _customize_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data after retrieval - add model-required fields"""
        # Map database fields back to model fields
        if 'concept_name' in data and 'concept_type' not in data:
            data['concept_type'] = data['concept_name']
        if 'concept_category' in data and 'category' not in data:
            data['category'] = data['concept_category']
        
        # Reconstruct content from definition for model
        if 'content' not in data:
            data['content'] = data.get('definition', 'No definition available')
        
        # Add model-required fields with defaults (这些字段不在数据库中但model需要)
        if 'memory_type' not in data:
            data['memory_type'] = 'semantic'
        if 'tags' not in data:
            data['tags'] = []
        if 'confidence' not in data:
            data['confidence'] = 0.8
        if 'importance_score' not in data:
            data['importance_score'] = 0.5
        if 'abstraction_level' not in data:
            data['abstraction_level'] = 'medium'
        
        return data
    
    async def _create_memory_model(self, data: Dict[str, Any]) -> SemanticMemory:
        """Create SemanticMemory model from database data"""
        return SemanticMemory(**data)