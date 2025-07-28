#!/usr/bin/env python3
"""
Procedural Memory Engine
Simple, clean implementation for procedural memory management
"""

from typing import Dict, Any, List
from datetime import datetime
from core.logging import get_logger
from .base_engine import BaseMemoryEngine
from ..models import ProceduralMemory, MemoryOperationResult
from tools.services.intelligence_service.language.text_extractor import TextExtractor

logger = get_logger(__name__)


class ProceduralMemoryEngine(BaseMemoryEngine):
    """Simple engine for managing procedural memories"""
    
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
        Store procedural memory by extracting procedures from dialog
        
        Simple workflow: TextExtractor → ProceduralMemory → base.store_memory
        """
        try:
            # Extract procedures using TextExtractor
            extraction_result = await self._extract_procedures(dialog_content)
            
            if not extraction_result['success']:
                logger.error(f"Failed to extract procedures: {extraction_result.get('error')}")
                return MemoryOperationResult(
                    success=False,
                    memory_id="",
                    operation="store_procedural_memory",
                    message=f"Failed to extract procedures: {extraction_result.get('error')}"
                )
            
            procedure_data = extraction_result['data']
            
            # Create ProceduralMemory object with proper model fields
            # Ensure difficulty_level is string for model validation
            difficulty_level = procedure_data.get('difficulty_level', 'medium')
            if isinstance(difficulty_level, int):
                level_map = {1: 'easy', 2: 'medium', 3: 'hard'}
                difficulty_level = level_map.get(difficulty_level, 'medium')
            
            procedural_memory = ProceduralMemory(
                user_id=user_id,
                content=procedure_data.get('expected_outcome', dialog_content[:200]),  # model需要但DB没有
                skill_type=procedure_data.get('task_description', 'unknown'),  # model字段，映射到DB的procedure_name
                domain=procedure_data.get('domain', 'general'),  # model和DB都有
                steps=procedure_data.get('steps', []),
                prerequisites=procedure_data.get('prerequisites', []),
                difficulty_level=difficulty_level,  # 确保是字符串
                success_rate=float(procedure_data.get('success_rate', 0.0)),
                confidence=float(procedure_data.get('confidence', 0.8)),  # model需要但DB没有
                importance_score=importance_score  # model需要但DB没有
            )
            
            # Use upsert logic to handle duplicate procedures
            result = await self._store_or_update_procedure(procedural_memory)
            
            if result.success:
                logger.info(f"✅ Stored procedure: {procedural_memory.skill_type[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store procedural memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id="",
                operation="store_procedural_memory",
                message=f"Failed to store procedural memory: {str(e)}"
            )
    
    async def _store_or_update_procedure(self, procedural_memory: ProceduralMemory) -> MemoryOperationResult:
        """Store procedural memory with upsert logic to handle duplicates"""
        try:
            # Generate embedding if not provided
            if not procedural_memory.embedding:
                procedural_memory.embedding = await self.embedder.embed_single(procedural_memory.content)
            
            # Check if procedure already exists (based on unique constraint)
            existing_result = self.db.table(self.table_name)\
                .select('id')\
                .eq('user_id', procedural_memory.user_id)\
                .eq('procedure_name', procedural_memory.skill_type)\
                .eq('domain', procedural_memory.domain)\
                .execute()
            
            memory_data = self._prepare_for_storage(procedural_memory)
            
            if existing_result.data:
                # Update existing procedure
                existing_id = existing_result.data[0]['id']
                memory_data['updated_at'] = datetime.now().isoformat()
                
                result = self.db.table(self.table_name)\
                    .update(memory_data)\
                    .eq('id', existing_id)\
                    .execute()
                
                if result.data:
                    logger.info(f"✅ Updated existing procedure: {procedural_memory.skill_type}")
                    return MemoryOperationResult(
                        success=True,
                        memory_id=existing_id,
                        operation="update",
                        message=f"Successfully updated procedural memory",
                        data={"memory": result.data[0]}
                    )
            else:
                # Insert new procedure
                result = self.db.table(self.table_name).insert(memory_data).execute()
                
                if result.data:
                    logger.info(f"✅ Inserted new procedure: {procedural_memory.skill_type}")
                    return MemoryOperationResult(
                        success=True,
                        memory_id=procedural_memory.id,
                        operation="store",
                        message=f"Successfully stored procedural memory",
                        data={"memory": result.data[0]}
                    )
            
            # If we get here, something went wrong
            raise Exception("No data returned from database operation")
            
        except Exception as e:
            logger.error(f"❌ Failed to store/update procedural memory: {e}")
            return MemoryOperationResult(
                success=False,
                memory_id=procedural_memory.id,
                operation="store_or_update",
                message=f"Failed to store/update memory: {str(e)}"
            )

    async def search_procedures_by_task(self, user_id: str, task_name: str, limit: int = 10) -> List[ProceduralMemory]:
        """Search procedures by task using database field procedure_name"""
        try:
            result = self.db.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .ilike('procedure_name', f'%{task_name}%')\
                .order('success_rate', desc=True)\
                .limit(limit)\
                .execute()
            
            procedures = []
            for data in result.data or []:
                procedure = await self._parse_from_storage(data)
                procedures.append(procedure)
            
            return procedures
            
        except Exception as e:
            logger.error(f"❌ Failed to search procedures by task {task_name}: {e}")
            return []
    
    # Private helper methods
    
    async def _extract_procedures(self, dialog_content: str) -> Dict[str, Any]:
        """Extract procedures using TextExtractor with simple schema"""
        try:
            # Schema for procedure extraction - 根据数据库字段设计
            procedure_schema = {
                "task_description": "Brief description of the task or procedure (maps to procedure_name)",
                "domain": "Domain or category this procedure belongs to",
                "steps": "List of steps to complete the task",
                "prerequisites": "List of required prior knowledge or conditions",
                "trigger_conditions": "When or under what conditions to use this procedure",
                "expected_outcome": "What should happen when this procedure is completed",
                "difficulty_level": "Difficulty level (easy=1, medium=2, hard=3)",
                "success_rate": "Success rate when this procedure is applied (0.0-1.0)",
                "estimated_time_minutes": "Estimated time to complete in minutes",
                "required_tools": "List of tools or resources needed",
                "confidence": "Confidence in extraction quality (0.0-1.0)"
            }
            
            # Use TextExtractor to extract structured information
            extraction_result = await self.text_extractor.extract_key_information(
                text=dialog_content,
                schema=procedure_schema
            )
            
            if extraction_result['success']:
                # Simple validation and cleanup
                data = extraction_result['data']
                
                # Ensure required fields with safe defaults
                if not data.get('task_description'):
                    data['task_description'] = 'Unknown task'
                if not data.get('domain'):
                    data['domain'] = 'general'
                if not data.get('expected_outcome'):
                    data['expected_outcome'] = 'Task completion'
                if not data.get('difficulty_level'):
                    data['difficulty_level'] = 'medium'
                
                # Ensure lists are lists and convert strings to proper format
                for list_field in ['prerequisites', 'trigger_conditions', 'required_tools']:
                    if not isinstance(data.get(list_field), list):
                        data[list_field] = []
                
                # Handle steps - convert string list to dict list for model
                if not isinstance(data.get('steps'), list):
                    data['steps'] = []
                else:
                    # Convert string steps to dict format for model
                    formatted_steps = []
                    for i, step in enumerate(data['steps']):
                        if isinstance(step, str):
                            formatted_steps.append({
                                'step_number': i + 1,
                                'description': step,
                                'details': ''
                            })
                        elif isinstance(step, dict):
                            formatted_steps.append(step)
                    data['steps'] = formatted_steps
                
                # Ensure numeric fields are numbers
                for numeric_field in ['confidence', 'success_rate', 'estimated_time_minutes']:
                    try:
                        if numeric_field == 'estimated_time_minutes':
                            data[numeric_field] = int(data.get(numeric_field, 30))
                        else:
                            data[numeric_field] = float(data.get(numeric_field, 0.8 if numeric_field == 'confidence' else 0.0))
                    except (ValueError, TypeError):
                        data[numeric_field] = 30 if numeric_field == 'estimated_time_minutes' else (0.8 if numeric_field == 'confidence' else 0.0)
                
                return {
                    'success': True,
                    'data': data,
                    'confidence': extraction_result.get('confidence', 0.7)
                }
            else:
                return extraction_result
            
        except Exception as e:
            logger.error(f"❌ Procedure extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {
                    'task_description': 'Unknown task',
                    'steps': [],
                    'context': {},
                    'expected_outcome': 'Task completion',
                    'difficulty_level': 'medium',
                    'confidence': 0.5
                },
                'confidence': 0.0
            }
    
    # Override base engine methods for procedural-specific handling
    
    def _customize_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data before storage - handle procedural-specific fields"""
        # Remove fields that don't exist in database schema
        # DB有：procedure_name, domain, trigger_conditions, steps, expected_outcome, success_rate, 
        #       usage_count, last_used_at, difficulty_level, estimated_time_minutes, required_tools
        # DB没有：content, memory_type, tags, confidence, access_count, last_accessed_at, importance_score, prerequisites, context
        fields_to_remove = ['content', 'memory_type', 'tags', 'confidence', 'importance_score', 'prerequisites', 'context']
        
        for field in fields_to_remove:
            data.pop(field, None)
        
        # Map model fields to database fields
        if 'skill_type' in data:
            data['procedure_name'] = data.pop('skill_type')
        
        # Convert difficulty level string to int for database
        if 'difficulty_level' in data and isinstance(data['difficulty_level'], str):
            difficulty_map = {'easy': 1, 'medium': 2, 'hard': 3}
            data['difficulty_level'] = difficulty_map.get(data['difficulty_level'].lower(), 2)
        
        # Set default values for database-specific fields
        if 'procedure_name' not in data:
            data['procedure_name'] = 'Unknown task'
        if 'domain' not in data:
            data['domain'] = 'general'
        if 'trigger_conditions' not in data:
            data['trigger_conditions'] = []
        if 'steps' not in data:
            data['steps'] = []
        if 'expected_outcome' not in data:
            data['expected_outcome'] = 'Task completion'
        if 'success_rate' not in data:
            data['success_rate'] = 0.0
        if 'usage_count' not in data:
            data['usage_count'] = 0
        if 'difficulty_level' not in data:
            data['difficulty_level'] = 2
        if 'estimated_time_minutes' not in data:
            data['estimated_time_minutes'] = 30
        if 'required_tools' not in data:
            data['required_tools'] = []
        
        return data
    
    def _customize_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Customize data after retrieval - add model-required fields"""
        # Map database fields back to model fields
        if 'procedure_name' in data and 'skill_type' not in data:
            data['skill_type'] = data['procedure_name']
        
        # Convert difficulty level int back to string for model
        if 'difficulty_level' in data and isinstance(data['difficulty_level'], int):
            level_map = {1: 'easy', 2: 'medium', 3: 'hard'}
            data['difficulty_level'] = level_map.get(data['difficulty_level'], 'medium')
        
        # Reconstruct content from expected_outcome for model
        if 'content' not in data:
            data['content'] = data.get('expected_outcome', 'Unknown task')
        
        # Add model-required fields with defaults (这些字段不在数据库中但model需要)
        if 'memory_type' not in data:
            data['memory_type'] = 'procedural'
        if 'tags' not in data:
            data['tags'] = []
        if 'confidence' not in data:
            data['confidence'] = 0.8
        if 'importance_score' not in data:
            data['importance_score'] = 0.5
        if 'prerequisites' not in data:
            data['prerequisites'] = []
        
        return data
    
    async def _create_memory_model(self, data: Dict[str, Any]) -> ProceduralMemory:
        """Create ProceduralMemory model from database data"""
        return ProceduralMemory(**data)