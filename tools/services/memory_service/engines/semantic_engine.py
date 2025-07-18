#!/usr/bin/env python3
"""
Semantic Memory Engine  
Specialized engine for semantic memory management
"""

from typing import Dict, Any, List, Optional
import json
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import SemanticMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class SemanticMemoryEngine(BaseMemoryEngine):
    """Engine for managing semantic memories"""
    
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
        Store semantic memories by intelligently extracting concepts and knowledge from dialog
        
        Args:
            user_id: User identifier
            dialog_content: Raw dialog between human and AI
            importance_score: Manual importance override (0.0-1.0)
        """
        try:
            # Extract semantic concepts from dialog
            extraction_result = await self._extract_semantic_info(dialog_content)
            
            if not extraction_result['success']:
                logger.error(f"Failed to extract semantic info: {extraction_result.get('error')}")
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_semantic_memory",
                    message=f"Failed to extract semantic information: {extraction_result.get('error')}"
                )
            
            concepts_data = extraction_result['data']
            stored_concepts = []
            
            # Process each extracted concept
            for concept_data in concepts_data.get('concepts', []):
                # Check for existing concepts with same type and definition
                existing = await self._find_existing_concept(
                    user_id, 
                    concept_data.get('concept_type'), 
                    concept_data.get('definition')
                )
                
                if existing:
                    # Update existing concept
                    result = await self._merge_semantic_concept(
                        existing, 
                        concept_data.get('properties', {}),
                        concept_data.get('related_concepts', []),
                        concept_data.get('category'),
                        importance_score
                    )
                else:
                    # Create new semantic memory
                    content = f"{concept_data.get('concept_type', 'concept')}: {concept_data.get('definition', '')}"
                    if concept_data.get('properties'):
                        prop_str = ", ".join([f"{k}: {v}" for k, v in concept_data.get('properties', {}).items()])
                        content += f" ({prop_str})"
                    
                    semantic_memory = SemanticMemory(
                        user_id=user_id,
                        content=content,
                        concept_type=concept_data.get('concept_type', 'general_concept'),
                        definition=concept_data.get('definition', ''),
                        properties=concept_data.get('properties', {}),
                        abstraction_level=concept_data.get('abstraction_level', 'medium'),
                        related_concepts=concept_data.get('related_concepts', []),
                        category=concept_data.get('category', 'general'),
                        importance_score=concept_data.get('importance_score', importance_score)
                    )
                    
                    result = await self.store_memory(semantic_memory)
                
                if result.success:
                    stored_concepts.append(result.memory_id)
                    logger.info(f"Stored intelligent semantic concept: {result.memory_id}")
            
            if stored_concepts:
                return MemoryOperationResult(
                    success=True,
                    memory_id=stored_concepts[0] if len(stored_concepts) == 1 else "",
                    operation="store_semantic_memory",
                    message=f"Successfully stored {len(stored_concepts)} semantic concepts",
                    data={"stored_concepts": stored_concepts, "total_concepts": len(stored_concepts)}
                )
            else:
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_semantic_memory",
                    message="No concepts could be extracted or stored"
                )
                
        except Exception as e:
            logger.error(f"Failed to store semantic memory from dialog: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_semantic_memory",
                message=f"Failed to store semantic memory: {str(e)}"
            )
    
    async def search_concepts_by_category(self, user_id: str, category: str, limit: int = 10) -> List[SemanticMemory]:
        """Search concepts by category"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('category', f'%{category}%')\
                .order('importance_score', desc=True)\
                .limit(limit)\
                .execute()
            
            concepts = []
            for data in result.data or []:
                concept = await self._parse_memory_data(data)
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"Failed to search concepts by category {category}: {e}")
            return []
    
    async def search_concepts_by_abstraction_level(
        self, 
        user_id: str, 
        abstraction_level: str,
        limit: int = 10
    ) -> List[SemanticMemory]:
        """Search concepts by abstraction level"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('abstraction_level', abstraction_level)\
                .order('importance_score', desc=True)\
                .limit(limit)\
                .execute()
            
            concepts = []
            for data in result.data or []:
                concept = await self._parse_memory_data(data)
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"Failed to search concepts by abstraction level {abstraction_level}: {e}")
            return []

    async def search_concepts_by_type(self, user_id: str, concept_type: str, limit: int = 10) -> List[SemanticMemory]:
        """Search concepts by concept type"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('concept_type', f'%{concept_type}%')\
                .order('importance_score', desc=True)\
                .limit(limit)\
                .execute()
            
            concepts = []
            for data in result.data or []:
                concept = await self._parse_memory_data(data)
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"Failed to search concepts by type {concept_type}: {e}")
            return []

    async def search_concepts_by_definition(self, user_id: str, definition_keyword: str, limit: int = 10) -> List[SemanticMemory]:
        """Search concepts by definition content"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('definition', f'%{definition_keyword}%')\
                .order('importance_score', desc=True)\
                .limit(limit)\
                .execute()
            
            concepts = []
            for data in result.data or []:
                concept = await self._parse_memory_data(data)
                concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"Failed to search concepts by definition {definition_keyword}: {e}")
            return []

    async def search_concepts_by_related_concept(
        self, 
        user_id: str, 
        related_concept_id: str,
        limit: int = 10
    ) -> List[SemanticMemory]:
        """Search concepts that are related to a specific concept"""
        try:
            # Get all concepts for user and filter by related concept
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .order('importance_score', desc=True)\
                .execute()
            
            concepts = []
            for data in result.data or []:
                concept = await self._parse_memory_data(data)
                if related_concept_id in concept.related_concepts:
                    concepts.append(concept)
                    if len(concepts) >= limit:
                        break
            
            return concepts
            
        except Exception as e:
            logger.error(f"Failed to search concepts by related concept {related_concept_id}: {e}")
            return []
    
    async def add_concept_relation(
        self, 
        source_concept_id: str, 
        target_concept_id: str
    ) -> MemoryOperationResult:
        """Add relationship between concepts"""
        try:
            # Get source concept
            source_concept = await self.get_memory(source_concept_id)
            if not source_concept:
                return MemoryOperationResult(
                    success=False,
                    memory_id=source_concept_id,
                    operation="add_relation",
                    message="Source concept not found"
                )
            
            # Add to related concepts if not already there
            related_concepts = source_concept.related_concepts
            if target_concept_id not in related_concepts:
                related_concepts.append(target_concept_id)
                
                updates = {'related_concepts': related_concepts}
                return await self.update_memory(source_concept_id, updates)
            
            return MemoryOperationResult(
                success=True,
                memory_id=source_concept_id,
                operation="add_relation",
                message="Relation already exists"
            )
            
        except Exception as e:
            logger.error(f"Failed to add concept relation: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=source_concept_id,
                operation="add_relation",
                message=f"Failed to add relation: {str(e)}"
            )
    
    async def update_concept_properties(
        self, 
        memory_id: str, 
        new_properties: Dict[str, Any]
    ) -> MemoryOperationResult:
        """Update concept properties"""
        try:
            concept = await self.get_memory(memory_id)
            if not concept:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="update_properties",
                    message="Concept not found"
                )
            
            # Merge properties
            merged_properties = concept.properties.copy()
            merged_properties.update(new_properties)
            
            # Update content to reflect new properties
            prop_str = ", ".join([f"{k}: {v}" for k, v in merged_properties.items()])
            content = f"{concept.concept_type}: {concept.definition}"
            if merged_properties:
                content += f" ({prop_str})"
            
            updates = {
                'properties': merged_properties,
                'content': content
            }
            
            return await self.update_memory(memory_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to update concept properties: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="update_properties",
                message=f"Failed to update properties: {str(e)}"
            )
    
    async def _prepare_memory_data(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare semantic memory data for storage"""
        # Add semantic-specific fields
        semantic_fields = [
            'concept_type', 'definition', 'properties', 'abstraction_level',
            'related_concepts', 'category'
        ]
        
        for field in semantic_fields:
            if field not in memory_data:
                if field in ['properties']:
                    memory_data[field] = json.dumps({})
                elif field == 'related_concepts':
                    memory_data[field] = json.dumps([])
                elif field == 'abstraction_level':
                    memory_data[field] = 'medium'
                else:
                    memory_data[field] = None
        
        # Handle JSON fields
        if isinstance(memory_data.get('properties'), dict):
            memory_data['properties'] = json.dumps(memory_data['properties'])
        if isinstance(memory_data.get('related_concepts'), list):
            memory_data['related_concepts'] = json.dumps(memory_data['related_concepts'])
        
        return memory_data
    
    async def _parse_memory_data(self, data: Dict[str, Any]) -> SemanticMemory:
        """Parse semantic memory data from database"""
        # Parse JSON fields
        if 'embedding' in data and isinstance(data['embedding'], str):
            data['embedding'] = json.loads(data['embedding'])
        if 'context' in data and isinstance(data['context'], str):
            data['context'] = json.loads(data['context'])
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags'])
        if 'properties' in data and isinstance(data['properties'], str):
            data['properties'] = json.loads(data['properties'])
        if 'related_concepts' in data and isinstance(data['related_concepts'], str):
            data['related_concepts'] = json.loads(data['related_concepts'])
        
        return SemanticMemory(**data)
    
    async def _find_existing_concept(
        self, 
        user_id: str, 
        concept_type: str, 
        definition: str
    ) -> Optional[SemanticMemory]:
        """Find existing concept with similar structure"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('concept_type', concept_type)\
                .ilike('definition', f'%{definition[:50]}%')\
                .execute()
            
            if result.data:
                return await self._parse_memory_data(result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find existing concept: {e}")
            return None
    
    async def _merge_semantic_concept(
        self,
        existing: SemanticMemory,
        new_properties: Dict[str, Any],
        new_related_concepts: List[str],
        new_category: Optional[str],
        new_importance: float
    ) -> MemoryOperationResult:
        """Merge new concept information with existing"""
        try:
            # Update importance (take maximum)
            updated_importance = max(existing.importance_score, new_importance)
            
            # Merge properties
            merged_properties = existing.properties.copy()
            merged_properties.update(new_properties)
            
            # Merge related concepts
            merged_related = list(set(existing.related_concepts + new_related_concepts))
            
            # Update content
            prop_str = ", ".join([f"{k}: {v}" for k, v in merged_properties.items()])
            content = f"{existing.concept_type}: {existing.definition}"
            if merged_properties:
                content += f" ({prop_str})"
            
            updates = {
                'properties': merged_properties,
                'related_concepts': merged_related,
                'content': content,
                'importance_score': updated_importance,
                'access_count': existing.access_count + 1
            }
            
            if new_category:
                updates['category'] = new_category
            
            result = await self.update_memory(existing.id, updates)
            
            if result.success:
                result.message = "Semantic concept merged and updated"
                result.data = result.data or {}
                result.data['action'] = 'merged'
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to merge semantic concept: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=existing.id,
                operation="merge",
                message=f"Failed to merge semantic concept: {str(e)}"
            )
    
    async def _extract_semantic_info(self, dialog_content: str) -> Dict[str, Any]:
        """Extract structured semantic information from raw dialog"""
        try:
            # Define extraction schema for semantic memory
            semantic_schema = {
                "concepts": "List of semantic concepts discussed. Each concept should have: concept_type (e.g., 'definition', 'principle', 'theory', 'classification', 'relationship'), definition (clear explanation of the concept), properties (key attributes as dict), abstraction_level ('concrete', 'medium', 'abstract'), category (domain like 'technology', 'science', 'business'), related_concepts (list of related concept names), importance_score (0.0-1.0)",
                "knowledge_domain": "Primary domain of knowledge discussed (e.g., 'technology', 'science', 'philosophy', 'business')",
                "abstraction_level": "Overall level of abstraction in the discussion ('concrete', 'medium', 'abstract')",
                "key_relationships": "Important relationships between concepts mentioned",
                "extraction_confidence": "Overall confidence in the extraction quality (0.0-1.0)"
            }
            
            # Extract key information using text extractor
            extraction_result = await self.text_extractor.extract_key_information(
                text=dialog_content,
                schema=semantic_schema
            )
            
            if not extraction_result['success']:
                return extraction_result
            
            extracted_data = extraction_result['data']
            
            # Post-process extracted concepts
            processed_data = await self._process_semantic_data(extracted_data, dialog_content)
            
            return {
                'success': True,
                'data': processed_data,
                'confidence': extraction_result.get('confidence', 0.7),
                'billing_info': extraction_result.get('billing_info')
            }
            
        except Exception as e:
            logger.error(f"Semantic information extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0
            }
    
    async def _process_semantic_data(self, raw_data: Dict[str, Any], original_content: str) -> Dict[str, Any]:
        """Process and validate extracted semantic data"""
        processed = {
            'concepts': [],
            'knowledge_domain': 'general',
            'abstraction_level': 'medium',
            'key_relationships': [],
            'extraction_confidence': 0.7
        }
        
        # Process knowledge domain
        domain = raw_data.get('knowledge_domain', 'general')
        if isinstance(domain, str):
            processed['knowledge_domain'] = domain.lower()
        
        # Process abstraction level
        abstraction = raw_data.get('abstraction_level', 'medium')
        valid_levels = ['concrete', 'medium', 'abstract']
        if isinstance(abstraction, str) and abstraction.lower() in valid_levels:
            processed['abstraction_level'] = abstraction.lower()
        
        # Process extraction confidence
        try:
            extraction_confidence = float(raw_data.get('extraction_confidence', 0.7))
            processed['extraction_confidence'] = max(0.0, min(1.0, extraction_confidence))
        except (ValueError, TypeError):
            processed['extraction_confidence'] = 0.7
        
        # Process key relationships
        relationships = raw_data.get('key_relationships', [])
        if isinstance(relationships, list):
            processed['key_relationships'] = relationships[:5]  # Limit to 5 relationships
        elif isinstance(relationships, str):
            processed['key_relationships'] = [relationships]
        
        # Process concepts
        concepts = raw_data.get('concepts', [])
        if not isinstance(concepts, list):
            concepts = []
        
        for concept in concepts:
            if isinstance(concept, dict):
                processed_concept = self._process_single_concept(concept, processed['knowledge_domain'], processed['abstraction_level'])
                if processed_concept:
                    processed['concepts'].append(processed_concept)
        
        # If no concepts extracted, try to extract basic concepts
        if not processed['concepts']:
            basic_concepts = self._extract_basic_concepts(original_content)
            processed['concepts'].extend(basic_concepts)
        
        return processed
    
    def _process_single_concept(self, concept: Dict[str, Any], default_domain: str, default_abstraction: str) -> Optional[Dict[str, Any]]:
        """Process and validate a single concept"""
        try:
            # Required fields
            definition = concept.get('definition')
            if not definition or len(str(definition).strip()) < 5:
                return None
            
            processed_concept = {
                'concept_type': str(concept.get('concept_type', 'general_concept')).lower().replace(' ', '_'),
                'definition': str(definition).strip(),
                'properties': concept.get('properties', {}) if isinstance(concept.get('properties'), dict) else {},
                'category': str(concept.get('category', default_domain)).lower(),
                'related_concepts': concept.get('related_concepts', []) if isinstance(concept.get('related_concepts'), list) else [],
            }
            
            # Process abstraction level
            abstraction = concept.get('abstraction_level', default_abstraction)
            valid_levels = ['concrete', 'medium', 'abstract']
            if isinstance(abstraction, str) and abstraction.lower() in valid_levels:
                processed_concept['abstraction_level'] = abstraction.lower()
            else:
                processed_concept['abstraction_level'] = default_abstraction
            
            # Process importance score
            try:
                importance_score = float(concept.get('importance_score', 0.5))
                processed_concept['importance_score'] = max(0.0, min(1.0, importance_score))
            except (ValueError, TypeError):
                processed_concept['importance_score'] = 0.5
            
            return processed_concept
            
        except Exception as e:
            logger.warning(f"Failed to process concept: {e}")
            return None
    
    def _extract_basic_concepts(self, content: str) -> List[Dict[str, Any]]:
        """Extract basic concepts when structured extraction fails"""
        concepts = []
        
        # Simple heuristics for basic concept extraction
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        
        for sentence in sentences[:3]:  # Limit to first 3 sentences
            if len(sentence) > 30 and len(sentence) < 300:
                # Look for definition patterns
                for pattern in [' is ', ' are ', ' means ', ' refers to ']:
                    if pattern in sentence.lower():
                        parts = sentence.lower().split(pattern, 1)
                        if len(parts) == 2:
                            concept_name = parts[0].strip()
                            definition = parts[1].strip()
                            
                            concepts.append({
                                'concept_type': 'definition',
                                'definition': f"{concept_name} {pattern.strip()} {definition}",
                                'properties': {},
                                'abstraction_level': 'medium',
                                'category': 'general',
                                'related_concepts': [],
                                'importance_score': 0.6
                            })
                            break
        
        return concepts[:2]  # Limit to 2 basic concepts