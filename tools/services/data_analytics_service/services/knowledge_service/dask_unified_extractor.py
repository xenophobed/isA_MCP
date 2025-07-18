#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dask-Optimized Unified Knowledge Extractor

Processes text chunks in parallel using Dask for much faster knowledge extraction.
Replaces the slow sequential entity->relation->attribute pipeline with unified parallel processing.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
import json
from dataclasses import dataclass

import dask
from dask import delayed
from dask.distributed import Client

import logging

logger = logging.getLogger(__name__)

@dataclass
class UnifiedKnowledgeResult:
    """Simple knowledge extraction result"""
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    attributes: Dict[str, Dict[str, Any]]
    processing_time: float
    success: bool
    error: Optional[str] = None

@dataclass
class DaskKnowledgeResult:
    """Dask-optimized knowledge extraction result"""
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    attributes: Dict[str, Dict[str, Any]]
    processing_time: float
    chunks_processed: int
    success: bool
    error: Optional[str] = None
    parallel_execution_time: float = 0.0

class DaskUnifiedExtractor:
    """
    Dask-Optimized Unified Knowledge Extractor
    
    Features:
    - Parallel processing of text chunks using Dask
    - Single LLM call per chunk (unified extraction)
    - Automatic result merging and deduplication
    - Much faster than sequential processing
    """
    
    def __init__(self, chunk_size: int = 1500, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.confidence_threshold = 0.7
        self.dask_client = None
        logger.info("DaskUnifiedExtractor initialized")
    
    async def initialize_dask(self, workers: int = 4, threads_per_worker: int = 2):
        """Initialize Dask client for parallel processing"""
        try:
            self.dask_client = Client(
                processes=True, 
                n_workers=workers,
                threads_per_worker=threads_per_worker,
                silence_logs=False
            )
            logger.info(f"Dask client initialized: {workers} workers, {threads_per_worker} threads each")
            return True
        except Exception as e:
            logger.warning(f"Dask initialization failed: {e}")
            return False
    
    def close_dask(self):
        """Close Dask client"""
        if self.dask_client:
            try:
                self.dask_client.close()
                self.dask_client = None
                logger.info("Dask client closed")
            except Exception as e:
                logger.warning(f"Dask close error: {e}")
    
    def _create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Create overlapping text chunks for parallel processing"""
        if len(text) <= self.chunk_size:
            return [{"id": 0, "text": text, "start": 0, "end": len(text)}]
        
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # Try to end at sentence boundary
            if end < len(text):
                sentence_end = text.rfind('.', start + self.chunk_size - 300, end)
                if sentence_end > start + 500:  # Ensure meaningful content
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "start": start,
                    "end": end
                })
                chunk_id += 1
            
            # Move to next chunk with overlap
            start = max(start + 1, end - self.overlap)
            if start >= len(text):
                break
        
        return chunks
    
    async def _process_single_chunk_direct(self, text: str, domain: Optional[str], confidence_threshold: float) -> UnifiedKnowledgeResult:
        """Process a single chunk directly using ISA client"""
        start_time = time.time()
        
        try:
            from isa_model.client import ISAModelClient
            
            # Create prompt for direct LLM call
            text_content = text[:4000]  # Limit length
            domain_context = f"This text is from the {domain} domain. " if domain else ""
            
            prompt = f"""Extract key information from the following text. {domain_context}Return ONLY a valid JSON object.

Text: {text_content}

Return this EXACT JSON format:
{{
    "entities": [
        {{"name": "entity_name", "type": "PERSON", "confidence": 0.9}}
    ],
    "relationships": [
        {{"subject": "entity1", "predicate": "relationship", "object": "entity2", "confidence": 0.8}}
    ],
    "attributes": {{
        "entity_name": {{"key": "value"}}
    }}
}}

IMPORTANT: 
- Return ONLY valid JSON, no markdown formatting
- Use entity types: PERSON, ORGANIZATION, LOCATION, CONCEPT only
- Include confidence scores between 0.7-1.0
- Keep it concise but accurate"""

            # Use ISA client directly
            client = ISAModelClient()
            response = await client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text",
                model="gpt-4o-mini",
                temperature=0.1,
                stream=False
            )
            
            if not response.get('success'):
                raise Exception(f"ISA generation failed: {response.get('error', 'Unknown error')}")
            
            # Process response
            result_content = response.get('result', '')
            if hasattr(result_content, 'content'):
                result_text = result_content.content
            elif isinstance(result_content, str):
                result_text = result_content
            else:
                result_text = str(result_content)
            
            # Parse JSON response
            import json
            import re
            
            try:
                # Clean the response
                clean_text = result_text.strip()
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]
                
                knowledge_data = json.loads(clean_text)
            except json.JSONDecodeError:
                # Try to extract JSON from text
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    knowledge_data = json.loads(json_str)
                else:
                    # Return empty but successful result
                    knowledge_data = {"entities": [], "relationships": [], "attributes": {}}
            
            # Extract and filter results
            entities = [e for e in knowledge_data.get('entities', []) 
                      if isinstance(e, dict) and e.get('confidence', 0) >= confidence_threshold]
            relationships = [r for r in knowledge_data.get('relationships', []) 
                           if isinstance(r, dict) and r.get('confidence', 0) >= confidence_threshold]
            attributes = knowledge_data.get('attributes', {})
            
            return UnifiedKnowledgeResult(
                entities=entities,
                relationships=relationships,
                attributes=attributes,
                processing_time=time.time() - start_time,
                success=True,
                error=None
            )
            
        except Exception as e:
            return UnifiedKnowledgeResult(
                entities=[],
                relationships=[],
                attributes={},
                processing_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
    
    async def extract_knowledge_parallel(
        self,
        text: str,
        domain: Optional[str] = None,
        confidence_threshold: float = 0.7,
        max_workers: int = 4
    ) -> DaskKnowledgeResult:
        """
        Extract knowledge from text using parallel Dask processing
        
        Args:
            text: Text to analyze
            domain: Domain type (e.g. 'medical', 'business')
            confidence_threshold: Confidence threshold for filtering
            max_workers: Maximum number of parallel workers
            
        Returns:
            DaskKnowledgeResult with merged results from all chunks
        """
        start_time = time.time()
        
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a non-empty string")
            
            # Create text chunks
            chunks = self._create_chunks(text)
            logger.info(f"Created {len(chunks)} chunks for parallel processing")
            
            if len(chunks) == 1:
                # Single chunk, use direct ISA processing
                result = await self._process_single_chunk_direct(chunks[0]["text"], domain, confidence_threshold)
                
                return DaskKnowledgeResult(
                    entities=result.entities,
                    relationships=result.relationships,
                    attributes=result.attributes,
                    processing_time=time.time() - start_time,
                    chunks_processed=1,
                    success=result.success,
                    error=result.error,
                    parallel_execution_time=0.0
                )
            
            # Process chunks in parallel
            if self.dask_client:
                results = await self._process_chunks_with_dask(chunks, domain, confidence_threshold)
            else:
                results = await self._process_chunks_with_asyncio(chunks, domain, confidence_threshold, max_workers)
            
            parallel_time = time.time() - start_time
            
            # Merge results from all chunks
            merged_result = self._merge_chunk_results(results)
            
            total_time = time.time() - start_time
            
            logger.info(f"✅ Dask parallel extraction completed: {len(merged_result['entities'])} entities, "
                       f"{len(merged_result['relationships'])} relationships, "
                       f"{len(merged_result['attributes'])} attributed entities "
                       f"from {len(chunks)} chunks in {total_time:.3f}s")
            
            return DaskKnowledgeResult(
                entities=merged_result['entities'],
                relationships=merged_result['relationships'],
                attributes=merged_result['attributes'],
                processing_time=total_time,
                chunks_processed=len(chunks),
                success=True,
                parallel_execution_time=parallel_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Dask knowledge extraction failed: {e}")
            return DaskKnowledgeResult(
                entities=[],
                relationships=[],
                attributes={},
                processing_time=processing_time,
                chunks_processed=0,
                success=False,
                error=str(e)
            )
    
    async def _process_chunks_with_dask(
        self, 
        chunks: List[Dict[str, Any]], 
        domain: Optional[str], 
        confidence_threshold: float
    ) -> List[UnifiedKnowledgeResult]:
        """Process chunks in parallel using Dask"""
        try:
            @delayed
            def extract_chunk_knowledge(chunk_data: Dict[str, Any]) -> Dict[str, Any]:
                """Dask delayed function for knowledge extraction"""
                import asyncio
                import sys
                from pathlib import Path
                
                # Add project root to path for Dask workers
                project_root = Path(__file__).parent.parent.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                async def _extract():
                    try:
                        # Initialize ISA client directly within worker (avoid unified_extractor singleton issues)
                        from isa_model.client import ISAModelClient
                        
                        # Create prompt for direct LLM call
                        text_content = chunk_data["text"][:4000]  # Limit length
                        domain_context = f"This text is from the {domain} domain. " if domain else ""
                        
                        prompt = f"""Extract key information from the following text. {domain_context}Return ONLY a valid JSON object.

Text: {text_content}

Return this EXACT JSON format:
{{
    "entities": [
        {{"name": "entity_name", "type": "PERSON", "confidence": 0.9}}
    ],
    "relationships": [
        {{"subject": "entity1", "predicate": "relationship", "object": "entity2", "confidence": 0.8}}
    ],
    "attributes": {{
        "entity_name": {{"key": "value"}}
    }}
}}

IMPORTANT: 
- Return ONLY valid JSON, no markdown formatting
- Use entity types: PERSON, ORGANIZATION, LOCATION, CONCEPT only
- Include confidence scores between 0.7-1.0
- Keep it concise but accurate"""

                        # Use ISA client directly
                        client = ISAModelClient()
                        response = await client.invoke(
                            input_data=prompt,
                            task="chat",
                            service_type="text",
                            model="gpt-4o-mini",
                            temperature=0.1,
                            stream=False
                        )
                        
                        if not response.get('success'):
                            raise Exception(f"ISA generation failed: {response.get('error', 'Unknown error')}")
                        
                        # Process response
                        result_content = response.get('result', '')
                        if hasattr(result_content, 'content'):
                            result_text = result_content.content
                        elif isinstance(result_content, str):
                            result_text = result_content
                        else:
                            result_text = str(result_content)
                        
                        # Parse JSON response
                        import json
                        import re
                        
                        try:
                            # Clean the response
                            clean_text = result_text.strip()
                            if clean_text.startswith('```json'):
                                clean_text = clean_text[7:]
                            if clean_text.endswith('```'):
                                clean_text = clean_text[:-3]
                            
                            knowledge_data = json.loads(clean_text)
                        except json.JSONDecodeError:
                            # Try to extract JSON from text
                            json_match = re.search(r'\\{.*\\}', result_text, re.DOTALL)
                            if json_match:
                                json_str = json_match.group()
                                knowledge_data = json.loads(json_str)
                            else:
                                # Return empty but successful result
                                knowledge_data = {"entities": [], "relationships": [], "attributes": {}}
                        
                        # Extract and filter results
                        entities = [e for e in knowledge_data.get('entities', []) 
                                  if isinstance(e, dict) and e.get('confidence', 0) >= confidence_threshold]
                        relationships = [r for r in knowledge_data.get('relationships', []) 
                                       if isinstance(r, dict) and r.get('confidence', 0) >= confidence_threshold]
                        attributes = knowledge_data.get('attributes', {})
                        
                        return {
                            "chunk_id": chunk_data["id"],
                            "entities": entities,
                            "relationships": relationships,
                            "attributes": attributes,
                            "success": True,
                            "error": None,
                            "processing_time": 0.0
                        }
                        
                    except Exception as e:
                        return {
                            "chunk_id": chunk_data["id"],
                            "entities": [],
                            "relationships": [],
                            "attributes": {},
                            "success": False,
                            "error": str(e),
                            "processing_time": 0.0
                        }
                
                # Run async function in new event loop for Dask
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(_extract())
                finally:
                    loop.close()
            
            # Create delayed tasks for each chunk
            tasks = [extract_chunk_knowledge(chunk) for chunk in chunks]
            
            # Execute in parallel with Dask
            logger.info(f"Executing {len(tasks)} knowledge extraction tasks with Dask...")
            dask_results = dask.compute(*tasks)
            
            # Convert to UnifiedKnowledgeResult objects
            results = []
            for result_data in dask_results:
                result = UnifiedKnowledgeResult(
                    entities=result_data["entities"],
                    relationships=result_data["relationships"],
                    attributes=result_data["attributes"],
                    processing_time=result_data["processing_time"],
                    success=result_data["success"],
                    error=result_data["error"]
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Dask chunk processing failed: {e}")
            # Fallback to asyncio
            return await self._process_chunks_with_asyncio(chunks, domain, confidence_threshold, 4)
    
    async def _process_chunks_with_asyncio(
        self, 
        chunks: List[Dict[str, Any]], 
        domain: Optional[str], 
        confidence_threshold: float,
        max_workers: int
    ) -> List[UnifiedKnowledgeResult]:
        """Process chunks with asyncio (fallback)"""
        try:
            semaphore = asyncio.Semaphore(max_workers)
            
            async def extract_single_chunk(chunk_data: Dict[str, Any]) -> UnifiedKnowledgeResult:
                async with semaphore:
                    try:
                        return await self._process_single_chunk_direct(
                            chunk_data["text"], domain, confidence_threshold
                        )
                    except Exception as e:
                        logger.warning(f"Chunk {chunk_data['id']} extraction failed: {e}")
                        return UnifiedKnowledgeResult(
                            entities=[],
                            relationships=[],
                            attributes={},
                            processing_time=0.0,
                            success=False,
                            error=str(e)
                        )
            
            # Execute with asyncio
            logger.info(f"Executing {len(chunks)} knowledge extraction tasks with asyncio...")
            tasks = [extract_single_chunk(chunk) for chunk in chunks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Chunk {i} processing exception: {result}")
                    processed_results.append(UnifiedKnowledgeResult(
                        entities=[],
                        relationships=[],
                        attributes={},
                        processing_time=0.0,
                        success=False,
                        error=str(result)
                    ))
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Asyncio chunk processing failed: {e}")
            return []
    
    def _merge_chunk_results(self, results: List[UnifiedKnowledgeResult]) -> Dict[str, Any]:
        """Merge and deduplicate results from multiple chunks"""
        merged_entities = []
        merged_relationships = []
        merged_attributes = {}
        
        # Track seen entities for deduplication
        seen_entities = set()
        seen_relationships = set()
        
        for result in results:
            if not result.success:
                continue
            
            # Merge entities with deduplication
            for entity in result.entities:
                entity_key = (entity.get('name', '').lower(), entity.get('type', ''))
                if entity_key not in seen_entities and entity_key[0]:
                    seen_entities.add(entity_key)
                    merged_entities.append(entity)
            
            # Merge relationships with deduplication
            for rel in result.relationships:
                rel_key = (
                    rel.get('subject', '').lower(),
                    rel.get('predicate', '').lower(),
                    rel.get('object', '').lower()
                )
                if rel_key not in seen_relationships and all(rel_key):
                    seen_relationships.add(rel_key)
                    merged_relationships.append(rel)
            
            # Merge attributes (combine attributes for same entities)
            for entity_name, attrs in result.attributes.items():
                if entity_name not in merged_attributes:
                    merged_attributes[entity_name] = attrs
                else:
                    # Merge attributes for existing entity
                    for attr_name, attr_data in attrs.items():
                        if attr_name not in merged_attributes[entity_name]:
                            merged_attributes[entity_name][attr_name] = attr_data
        
        return {
            'entities': merged_entities,
            'relationships': merged_relationships,
            'attributes': merged_attributes
        }

# Global instance
dask_unified_extractor = DaskUnifiedExtractor()

# Convenience function
async def extract_knowledge_parallel(text: str, **kwargs) -> DaskKnowledgeResult:
    """Convenience function for parallel knowledge extraction"""
    return await dask_unified_extractor.extract_knowledge_parallel(text, **kwargs)