#!/usr/bin/env python3
"""
Procedural Memory Engine
Specialized engine for procedural memory management
"""

from typing import Dict, Any, List, Optional
import json
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import ProceduralMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class ProceduralMemoryEngine(BaseMemoryEngine):
    """Engine for managing procedural memories"""
    
    def __init__(self):
        super().__init__()
        self.text_extractor = TextExtractor()
    
    @property
    def table_name(self) -> str:
        return "procedural_memories"
    
    @property
    def memory_type(self) -> str:
        return "procedural"
    
    async def store_procedural_memory(
        self,
        user_id: str,
        dialog_content: str,
        importance_score: float = 0.5
    ) -> MemoryOperationResult:
        """
        Store procedural memories by intelligently extracting procedural knowledge from dialog
        
        Args:
            user_id: User identifier
            dialog_content: Raw dialog between human and AI
            importance_score: Manual importance override (0.0-1.0)
        """
        try:
            # Extract procedural knowledge from dialog
            extraction_result = await self._extract_procedural_info(dialog_content)
            
            if not extraction_result['success']:
                logger.error(f"Failed to extract procedural info: {extraction_result.get('error')}")
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_procedural_memory",
                    message=f"Failed to extract procedural information: {extraction_result.get('error')}"
                )
            
            extracted_data = extraction_result['data']
            
            # Create procedural memory with extracted data
            procedural_memory = ProceduralMemory(
                user_id=user_id,
                content=extracted_data.get('clean_content', dialog_content[:500]),
                skill_type=extracted_data.get('skill_type', 'general_skill'),
                steps=extracted_data.get('steps', []),
                prerequisites=extracted_data.get('prerequisites', []),
                difficulty_level=extracted_data.get('difficulty_level', 'medium'),
                domain=extracted_data.get('domain', 'general'),
                importance_score=extracted_data.get('importance_score', importance_score)
            )
            
            # Store the memory
            result = await self.store_memory(procedural_memory)
            
            if result.success:
                logger.info(f"Stored intelligent procedural memory: {procedural_memory.id}")
                logger.info(f"Extracted: skill_type={extracted_data.get('skill_type')}, "
                          f"steps={len(extracted_data.get('steps', []))}, "
                          f"domain={extracted_data.get('domain')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to store procedural memory from dialog: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_procedural_memory",
                message=f"Failed to store procedural memory: {str(e)}"
            )
    
    async def update_success_rate(self, memory_id: str, success: bool) -> MemoryOperationResult:
        """Update procedure success rate based on usage"""
        try:
            memory = await self.get_memory(memory_id)
            if not memory:
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    operation="update_success_rate",
                    message="Memory not found"
                )
            
            # Calculate new success rate
            current_rate = memory.success_rate
            access_count = memory.access_count
            
            if access_count == 0:
                new_rate = 1.0 if success else 0.0
            else:
                # Weighted average
                total_successes = current_rate * access_count
                if success:
                    total_successes += 1
                new_rate = total_successes / (access_count + 1)
            
            updates = {
                'success_rate': new_rate,
                'access_count': access_count + 1
            }
            
            return await self.update_memory(memory_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to update success rate: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=memory_id,
                operation="update_success_rate",
                message=f"Failed to update success rate: {str(e)}"
            )
    
    async def search_procedures_by_domain(self, user_id: str, domain: str, limit: int = 10) -> List[ProceduralMemory]:
        """Search procedures by domain"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('domain', f'%{domain}%')\
                .order('success_rate', desc=True)\
                .limit(limit)\
                .execute()
            
            procedures = []
            for data in result.data or []:
                procedure = await self._parse_memory_data(data)
                procedures.append(procedure)
            
            return procedures
            
        except Exception as e:
            logger.error(f"Failed to search procedures by domain {domain}: {e}")
            return []

    async def search_procedures_by_skill_type(self, user_id: str, skill_type: str, limit: int = 10) -> List[ProceduralMemory]:
        """Search procedures by skill type"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('skill_type', f'%{skill_type}%')\
                .order('success_rate', desc=True)\
                .limit(limit)\
                .execute()
            
            procedures = []
            for data in result.data or []:
                procedure = await self._parse_memory_data(data)
                procedures.append(procedure)
            
            return procedures
            
        except Exception as e:
            logger.error(f"Failed to search procedures by skill type {skill_type}: {e}")
            return []

    async def search_procedures_by_difficulty(
        self, 
        user_id: str, 
        difficulty_level: str,
        limit: int = 10
    ) -> List[ProceduralMemory]:
        """Search procedures by difficulty level"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('difficulty_level', difficulty_level)\
                .order('success_rate', desc=True)\
                .order('importance_score', desc=True)\
                .limit(limit)\
                .execute()
            
            procedures = []
            for data in result.data or []:
                procedure = await self._parse_memory_data(data)
                procedures.append(procedure)
            
            return procedures
            
        except Exception as e:
            logger.error(f"Failed to search procedures by difficulty {difficulty_level}: {e}")
            return []

    async def search_procedures_by_success_rate(
        self, 
        user_id: str, 
        min_success_rate: float = 0.8,
        limit: int = 10
    ) -> List[ProceduralMemory]:
        """Search high-success-rate procedures"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('success_rate', min_success_rate)\
                .order('success_rate', desc=True)\
                .order('access_count', desc=True)\
                .limit(limit)\
                .execute()
            
            procedures = []
            for data in result.data or []:
                procedure = await self._parse_memory_data(data)
                procedures.append(procedure)
            
            return procedures
            
        except Exception as e:
            logger.error(f"Failed to search procedures by success rate: {e}")
            return []

    async def search_procedures_by_prerequisites(
        self, 
        user_id: str, 
        prerequisite: str,
        limit: int = 10
    ) -> List[ProceduralMemory]:
        """Search procedures that require a specific prerequisite"""
        try:
            # Get all procedures for user and filter by prerequisite
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .order('difficulty_level')\
                .execute()
            
            procedures = []
            for data in result.data or []:
                procedure = await self._parse_memory_data(data)
                if prerequisite.lower() in [p.lower() for p in procedure.prerequisites]:
                    procedures.append(procedure)
                    if len(procedures) >= limit:
                        break
            
            return procedures
            
        except Exception as e:
            logger.error(f"Failed to search procedures by prerequisite {prerequisite}: {e}")
            return []
    
    async def _prepare_memory_data(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare procedural memory data for storage"""
        # Add procedural-specific fields
        procedural_fields = [
            'skill_type', 'steps', 'prerequisites', 'difficulty_level',
            'success_rate', 'domain'
        ]
        
        for field in procedural_fields:
            if field not in memory_data:
                if field == 'success_rate':
                    memory_data[field] = 0.0
                elif field in ['steps', 'prerequisites']:
                    memory_data[field] = json.dumps([])
                elif field == 'difficulty_level':
                    memory_data[field] = 'medium'
                else:
                    memory_data[field] = None
        
        # Handle JSON fields
        if isinstance(memory_data.get('steps'), list):
            memory_data['steps'] = json.dumps(memory_data['steps'])
        if isinstance(memory_data.get('prerequisites'), list):
            memory_data['prerequisites'] = json.dumps(memory_data['prerequisites'])
        
        return memory_data
    
    async def _parse_memory_data(self, data: Dict[str, Any]) -> ProceduralMemory:
        """Parse procedural memory data from database"""
        # Parse JSON fields
        if 'embedding' in data and isinstance(data['embedding'], str):
            data['embedding'] = json.loads(data['embedding'])
        if 'context' in data and isinstance(data['context'], str):
            data['context'] = json.loads(data['context'])
        if 'tags' in data and isinstance(data['tags'], str):
            data['tags'] = json.loads(data['tags'])
        if 'steps' in data and isinstance(data['steps'], str):
            data['steps'] = json.loads(data['steps'])
        if 'prerequisites' in data and isinstance(data['prerequisites'], str):
            data['prerequisites'] = json.loads(data['prerequisites'])
        
        return ProceduralMemory(**data)
    
    async def _extract_procedural_info(self, dialog_content: str) -> Dict[str, Any]:
        """Extract structured procedural information from raw dialog"""
        try:
            # Define extraction schema for procedural memory
            procedural_schema = {
                "skill_type": "Type of skill or procedure being described (e.g., 'programming', 'cooking', 'problem_solving', 'analysis')",
                "clean_content": "Clean, concise description of the procedure or skill (2-3 sentences max)",
                "steps": "List of procedural steps, each with: step_number (int), description (str), importance (str: critical/important/optional), estimated_time (str), tools_needed (list)",
                "prerequisites": "List of required skills, knowledge, or conditions needed before attempting this procedure",
                "difficulty_level": "Difficulty level: 'beginner', 'intermediate', 'advanced', or 'expert'",
                "domain": "Knowledge domain (e.g., 'technology', 'cooking', 'business', 'science', 'creative')",
                "importance_score": "How important this procedure is from 0.0 (trivial) to 1.0 (critical)",
                "tools_required": "List of tools, software, or resources needed",
                "success_indicators": "How to know when the procedure has been completed successfully",
                "common_mistakes": "Common errors to avoid when following this procedure"
            }
            
            # Extract key information using text extractor
            extraction_result = await self.text_extractor.extract_key_information(
                text=dialog_content,
                schema=procedural_schema
            )
            
            if not extraction_result['success']:
                return extraction_result
            
            extracted_data = extraction_result['data']
            
            # Post-process extracted data
            processed_data = await self._process_procedural_data(extracted_data, dialog_content)
            
            return {
                'success': True,
                'data': processed_data,
                'confidence': extraction_result.get('confidence', 0.7),
                'billing_info': extraction_result.get('billing_info')
            }
            
        except Exception as e:
            logger.error(f"Procedural information extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0
            }
    
    async def _process_procedural_data(self, raw_data: Dict[str, Any], original_content: str) -> Dict[str, Any]:
        """Process and validate extracted procedural data"""
        processed = {}
        
        # Skill type processing
        skill_type = raw_data.get('skill_type', 'general_skill')
        if isinstance(skill_type, str):
            processed['skill_type'] = skill_type.lower().replace(' ', '_')
        else:
            processed['skill_type'] = 'general_skill'
        
        # Clean content
        clean_content = raw_data.get('clean_content', '')
        if not clean_content or len(clean_content) < 10:
            # Generate a basic summary if extraction failed
            words = original_content.split()[:30]
            processed['clean_content'] = ' '.join(words) + ('...' if len(words) == 30 else '')
        else:
            processed['clean_content'] = clean_content[:500]  # Limit length
        
        # Steps processing
        steps = raw_data.get('steps', [])
        if isinstance(steps, str):
            # If steps came as string, try to parse into basic format
            step_lines = [s.strip() for s in steps.split('\n') if s.strip()]
            processed_steps = []
            for i, step_desc in enumerate(step_lines[:10]):  # Limit to 10 steps
                processed_steps.append({
                    'step_number': i + 1,
                    'description': step_desc,
                    'importance': 'important',
                    'estimated_time': 'varies',
                    'tools_needed': []
                })
            processed['steps'] = processed_steps
        elif isinstance(steps, list):
            processed['steps'] = steps[:10]  # Limit to 10 steps
        else:
            processed['steps'] = []
        
        # Prerequisites processing
        prerequisites = raw_data.get('prerequisites', [])
        if isinstance(prerequisites, str):
            prerequisites = [p.strip() for p in prerequisites.split(',') if p.strip()]
        elif not isinstance(prerequisites, list):
            prerequisites = []
        processed['prerequisites'] = prerequisites[:10]  # Limit to 10 prerequisites
        
        # Difficulty level processing
        difficulty = raw_data.get('difficulty_level', 'medium')
        valid_difficulties = ['beginner', 'intermediate', 'advanced', 'expert']
        if isinstance(difficulty, str) and difficulty.lower() in valid_difficulties:
            processed['difficulty_level'] = difficulty.lower()
        else:
            processed['difficulty_level'] = 'medium'
        
        # Domain processing
        domain = raw_data.get('domain', 'general')
        if isinstance(domain, str):
            processed['domain'] = domain.lower()
        else:
            processed['domain'] = 'general'
        
        # Numerical fields with validation
        try:
            importance_score = float(raw_data.get('importance_score', 0.5))
            processed['importance_score'] = max(0.0, min(1.0, importance_score))
        except (ValueError, TypeError):
            processed['importance_score'] = 0.5
        
        # Additional context fields
        processed['tools_required'] = raw_data.get('tools_required', [])
        processed['success_indicators'] = raw_data.get('success_indicators', [])
        processed['common_mistakes'] = raw_data.get('common_mistakes', [])
        
        return processed