#!/usr/bin/env python3
"""
Factual Memory Engine
Specialized engine for factual memory management
"""

from typing import Dict, Any, List, Optional
import json
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import FactualMemory, MemoryModel, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class FactualMemoryEngine(BaseMemoryEngine):
    """Engine for managing factual memories"""
    
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
        Store factual memories by intelligently extracting facts from dialog
        
        Args:
            user_id: User identifier
            dialog_content: Raw dialog between human and AI
            importance_score: Manual importance override (0.0-1.0)
        """
        try:
            # Extract facts from dialog
            extraction_result = await self._extract_factual_info(dialog_content)
            
            if not extraction_result['success']:
                logger.error(f"Failed to extract factual info: {extraction_result.get('error')}")
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_factual_memory",
                    message=f"Failed to extract factual information: {extraction_result.get('error')}"
                )
            
            facts_data = extraction_result['data']
            stored_facts = []
            
            # Process each extracted fact
            for fact_data in facts_data.get('facts', []):
                # Check for existing facts with same structure
                existing = await self._find_existing_fact(
                    user_id, 
                    fact_data.get('fact_type'), 
                    fact_data.get('subject'), 
                    fact_data.get('predicate')
                )
                
                if existing:
                    # Update existing fact
                    result = await self._merge_factual_memory(
                        existing, 
                        fact_data.get('object_value'),
                        fact_data.get('context'),
                        fact_data.get('confidence', 0.8),
                        importance_score,
                        facts_data.get('source')
                    )
                else:
                    # Create new factual memory
                    content = f"{fact_data.get('subject')} {fact_data.get('predicate')} {fact_data.get('object_value')}"
                    if fact_data.get('context'):
                        content += f" ({fact_data.get('context')})"
                    
                    factual_memory = FactualMemory(
                        user_id=user_id,
                        content=content,
                        fact_type=fact_data.get('fact_type', 'general'),
                        subject=fact_data.get('subject'),
                        predicate=fact_data.get('predicate'),
                        object_value=fact_data.get('object_value'),
                        context=fact_data.get('context'),
                        confidence=fact_data.get('confidence', 0.8),
                        importance_score=importance_score,
                        source=facts_data.get('source')
                    )
                    
                    result = await self.store_memory(factual_memory)
                
                if result.success:
                    stored_facts.append(result.memory_id)
                    logger.info(f"Stored intelligent factual memory: {result.memory_id}")
            
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
                    message="No facts could be extracted or stored"
                )
                
        except Exception as e:
            logger.error(f"Failed to store factual memory from dialog: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_factual_memory",
                message=f"Failed to store factual memory: {str(e)}"
            )
    
    async def _find_existing_fact(
        self, 
        user_id: str, 
        fact_type: str, 
        subject: str, 
        predicate: str
    ) -> Optional[FactualMemory]:
        """Find existing fact with same structure"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('fact_type', fact_type)\
                .eq('subject', subject)\
                .eq('predicate', predicate)\
                .execute()
            
            if result.data:
                return await self._parse_memory_data(result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find existing fact: {e}")
            return None
    
    async def _merge_factual_memory(
        self,
        existing: FactualMemory,
        new_object_value: str,
        new_context: Optional[str],
        new_confidence: float,
        new_importance: float,
        new_source: Optional[str]
    ) -> MemoryOperationResult:
        """Merge new fact information with existing"""
        try:
            # Update confidence (increase with confirmation)
            updated_confidence = min(existing.confidence + 0.1, 1.0)
            
            # Update importance (take maximum)
            updated_importance = max(existing.importance_score, new_importance)
            
            # Update content if object value changed
            content = f"{existing.subject} {existing.predicate} {new_object_value}"
            if new_context:
                content += f" ({new_context})"
            
            # Merge context - handle both string and dict context
            if hasattr(existing, 'context') and existing.context:
                if new_context:
                    merged_context = f"{existing.context}; {new_context}"
                else:
                    merged_context = existing.context
            else:
                merged_context = new_context or ""
            
            updates = {
                'object_value': new_object_value,
                'context': merged_context,
                'confidence': updated_confidence,
                'importance_score': updated_importance,
                'last_confirmed_at': existing.updated_at.isoformat()
            }
            
            if new_source:
                updates['source'] = new_source
            
            result = await self.update_memory(existing.id, updates)
            
            if result.success:
                # Track associations with related facts
                await self._discover_fact_associations(existing.id, existing.user_id)
                
                result.message = "Factual memory merged and updated"
                result.data = result.data or {}
                result.data['action'] = 'merged'
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to merge factual memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=existing.id,
                operation="merge",
                message=f"Failed to merge factual memory: {str(e)}"
            )
    
    async def _discover_fact_associations(self, memory_id: str, user_id: str) -> None:
        """Discover associations between facts using semantic similarity"""
        try:
            # Get the current fact
            current_fact = await self.get_memory(memory_id)
            if not current_fact:
                return
            
            # Find related facts
            related_facts = await self.find_related_memories(memory_id, limit=5)
            
            # Store associations in memory associations table
            for related in related_facts:
                try:
                    association_data = {
                        'source_memory_id': memory_id,
                        'target_memory_id': related.memory.id,
                        'association_type': 'semantic_similarity',
                        'strength': related.similarity_score,
                        'user_id': user_id
                    }
                    
                    # Check if association already exists
                    existing = self.db.table('memory_associations')\
                        .select('*')\
                        .eq('source_memory_id', memory_id)\
                        .eq('target_memory_id', related.memory.id)\
                        .execute()
                    
                    if not existing.data:
                        self.db.table('memory_associations').insert(association_data).execute()
                        
                except Exception as e:
                    logger.warning(f"Failed to store association: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to discover fact associations: {e}")
    
    
    async def verify_fact(self, memory_id: str, verification_status: str) -> MemoryOperationResult:
        """Update fact verification status"""
        updates = {
            'verification_status': verification_status,
            'confidence': 0.9 if verification_status == 'verified' else 0.3
        }
        
        return await self.update_memory(memory_id, updates)

    async def search_facts_by_subject(self, user_id: str, subject: str, limit: int = 10) -> List[FactualMemory]:
        """Search facts by subject"""
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
                fact = await self._parse_memory_data(data)
                facts.append(fact)
            
            return facts
            
        except Exception as e:
            logger.error(f"Failed to search facts by subject {subject}: {e}")
            return []

    async def search_facts_by_fact_type(self, user_id: str, fact_type: str, limit: int = 10) -> List[FactualMemory]:
        """Search facts by fact type"""
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
                fact = await self._parse_memory_data(data)
                facts.append(fact)
            
            return facts
            
        except Exception as e:
            logger.error(f"Failed to search facts by type {fact_type}: {e}")
            return []

    async def search_facts_by_confidence(
        self, 
        user_id: str, 
        min_confidence: float = 0.7,
        limit: int = 10
    ) -> List[FactualMemory]:
        """Search high-confidence facts"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('confidence', min_confidence)\
                .order('confidence', desc=True)\
                .order('importance_score', desc=True)\
                .limit(limit)\
                .execute()
            
            facts = []
            for data in result.data or []:
                fact = await self._parse_memory_data(data)
                facts.append(fact)
            
            return facts
            
        except Exception as e:
            logger.error(f"Failed to search facts by confidence: {e}")
            return []

    async def search_facts_by_source(self, user_id: str, source: str, limit: int = 10) -> List[FactualMemory]:
        """Search facts by source"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('source', f'%{source}%')\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            facts = []
            for data in result.data or []:
                fact = await self._parse_memory_data(data)
                facts.append(fact)
            
            return facts
            
        except Exception as e:
            logger.error(f"Failed to search facts by source {source}: {e}")
            return []

    async def search_facts_by_verification(
        self, 
        user_id: str, 
        verification_status: str,
        limit: int = 10
    ) -> List[FactualMemory]:
        """Search facts by verification status"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('verification_status', verification_status)\
                .order('confidence', desc=True)\
                .limit(limit)\
                .execute()
            
            facts = []
            for data in result.data or []:
                fact = await self._parse_memory_data(data)
                facts.append(fact)
            
            return facts
            
        except Exception as e:
            logger.error(f"Failed to search facts by verification {verification_status}: {e}")
            return []

    async def _extract_factual_info(self, dialog_content: str) -> Dict[str, Any]:
        """Extract structured factual information from raw dialog"""
        try:
            # Define extraction schema for factual memory
            factual_schema = {
                "facts": "List of factual statements from the dialog. Each fact should have: fact_type (e.g., 'personal_info', 'preference', 'skill', 'knowledge', 'relationship'), subject (what/who the fact is about), predicate (relationship/property), object_value (the value/object), context (additional context), confidence (0.0-1.0 confidence in this fact)",
                "source": "Source of the information (e.g., 'user_statement', 'ai_knowledge', 'external_reference')",
                "domain": "Domain or category of knowledge (e.g., 'technology', 'personal', 'business', 'science')",
                "extraction_confidence": "Overall confidence in the extraction quality (0.0-1.0)"
            }
            
            # Extract key information using text extractor
            extraction_result = await self.text_extractor.extract_key_information(
                text=dialog_content,
                schema=factual_schema
            )
            
            if not extraction_result['success']:
                return extraction_result
            
            extracted_data = extraction_result['data']
            
            # Post-process extracted facts
            processed_data = await self._process_factual_data(extracted_data, dialog_content)
            
            return {
                'success': True,
                'data': processed_data,
                'confidence': extraction_result.get('confidence', 0.7),
                'billing_info': extraction_result.get('billing_info')
            }
            
        except Exception as e:
            logger.error(f"Factual information extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0
            }

    async def _process_factual_data(self, raw_data: Dict[str, Any], original_content: str) -> Dict[str, Any]:
        """Process and validate extracted factual data"""
        processed = {
            'facts': [],
            'source': 'dialog_extraction',
            'domain': 'general',
            'extraction_confidence': 0.7
        }
        
        # Process source
        source = raw_data.get('source', 'dialog_extraction')
        if isinstance(source, str):
            processed['source'] = source.lower().replace(' ', '_')
        
        # Process domain
        domain = raw_data.get('domain', 'general')
        if isinstance(domain, str):
            processed['domain'] = domain.lower()
        
        # Process extraction confidence
        try:
            extraction_confidence = float(raw_data.get('extraction_confidence', 0.7))
            processed['extraction_confidence'] = max(0.0, min(1.0, extraction_confidence))
        except (ValueError, TypeError):
            processed['extraction_confidence'] = 0.7
        
        # Process facts
        facts = raw_data.get('facts', [])
        if not isinstance(facts, list):
            facts = []
        
        for fact in facts:
            if isinstance(fact, dict):
                processed_fact = self._process_single_fact(fact)
                if processed_fact:
                    processed['facts'].append(processed_fact)
        
        # If no facts extracted, try to extract basic statements
        if not processed['facts']:
            basic_facts = self._extract_basic_facts(original_content)
            processed['facts'].extend(basic_facts)
        
        return processed

    def _process_single_fact(self, fact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and validate a single fact"""
        try:
            # Required fields
            subject = fact.get('subject')
            predicate = fact.get('predicate')
            object_value = fact.get('object_value')
            
            if not all([subject, predicate, object_value]):
                return None
            
            processed_fact = {
                'subject': str(subject).strip(),
                'predicate': str(predicate).strip(),
                'object_value': str(object_value).strip(),
                'fact_type': str(fact.get('fact_type', 'general')).lower().replace(' ', '_'),
                'context': str(fact.get('context', '')).strip() if fact.get('context') else None,
            }
            
            # Process confidence
            try:
                confidence = float(fact.get('confidence', 0.8))
                processed_fact['confidence'] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                processed_fact['confidence'] = 0.8
            
            return processed_fact
            
        except Exception as e:
            logger.warning(f"Failed to process fact: {e}")
            return None

    def _extract_basic_facts(self, content: str) -> List[Dict[str, Any]]:
        """Extract basic facts when structured extraction fails"""
        facts = []
        
        # Simple heuristics for basic fact extraction
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        
        for sentence in sentences[:3]:  # Limit to first 3 sentences
            if len(sentence) > 20 and len(sentence) < 200:
                # Look for is/are/was/were patterns
                for verb in ['is', 'are', 'was', 'were', 'has', 'have']:
                    if f' {verb} ' in sentence.lower():
                        parts = sentence.lower().split(f' {verb} ', 1)
                        if len(parts) == 2:
                            subject = parts[0].strip()
                            object_value = parts[1].strip()
                            
                            facts.append({
                                'subject': subject,
                                'predicate': verb,
                                'object_value': object_value,
                                'fact_type': 'statement',
                                'context': None,
                                'confidence': 0.6
                            })
                            break
        
        return facts[:2]  # Limit to 2 basic facts
    
    async def _prepare_memory_data(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare factual memory data for storage"""
        # Add factual-specific fields if not present
        factual_fields = [
            'fact_type', 'subject', 'predicate', 'object_value',
            'source', 'verification_status', 'related_facts'
        ]
        
        for field in factual_fields:
            if field not in memory_data:
                if field == 'verification_status':
                    memory_data[field] = 'unverified'
                elif field == 'related_facts':
                    memory_data[field] = json.dumps([])
                else:
                    memory_data[field] = None
        
        # Handle JSON fields
        if isinstance(memory_data.get('related_facts'), list):
            memory_data['related_facts'] = json.dumps(memory_data['related_facts'])
        
        return memory_data
    
    async def _parse_memory_data(self, data: Dict[str, Any]) -> FactualMemory:
        """Parse factual memory data from database"""
        # Parse JSON fields
        if 'embedding' in data and isinstance(data['embedding'], str):
            data['embedding'] = json.loads(data['embedding'])
        if 'context' in data and isinstance(data['context'], str):
            data['context'] = json.loads(data['context'])
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags'])
        if 'related_facts' in data and isinstance(data['related_facts'], str):
            data['related_facts'] = json.loads(data['related_facts'])
        
        return FactualMemory(**data)