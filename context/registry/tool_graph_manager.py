from ..source.tool_extractor import ToolMetadataExtractor
from ..source.tool_embedder import ToolVectorEmbedder
from app.services.db.graph.neo4j.service import Neo4jService
from app.services.db.graph.neo4j.queries.tools_capabilities import ToolCapabilitiesQueries
from langchain_core.tools import BaseTool
import logging
import numpy as np
import hashlib
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from .query_parser import ToolQueryParser
from app.services.ai.models.ai_factory import AIFactory
import asyncio
from app.config.config_manager import config_manager

logger = logging.getLogger(__name__)

class SearchWeights(BaseModel):
    semantic: float = 0.4
    functional: float = 0.3
    contextual: float = 0.3

class SearchResult(BaseModel):
    tool_id: str
    name: str
    description: str
    concept: Optional[str] = None
    domain: Optional[str] = None
    operation: Optional[str] = None
    usage_context: Optional[str] = None
    score: Optional[float] = None

class ToolGraphManager:
    def __init__(self, uri=None, user=None, password=None):
        self.extractor = ToolMetadataExtractor()
        self.embedder = ToolVectorEmbedder()
        self.graph_db = Neo4jService(uri=uri, user=user, password=password)
        self.queries = ToolCapabilitiesQueries()
        self.query_parser = ToolQueryParser()
        self.embed_service = None
        self.gds_available = False  # Track GDS availability
        
    @classmethod
    async def create(cls, uri=None, user=None, password=None):
        manager = cls(uri=uri, user=user, password=password)
        await manager.graph_db.initialize()
        await manager.query_parser.initialize()
        manager.embed_service = AIFactory.get_instance().get_embedding(
            model_name="bge-m3",
            provider="ollama"
        )
        
        # Check GDS library
        try:
            result = await manager.graph_db.query("""
            CALL gds.list()
            YIELD name
            RETURN count(name) as count
            """)
            if result and result[0]['count'] >= 0:
                logger.info("Graph Data Science library is available")
                manager.gds_available = True
        except Exception as e:
            logger.warning(f"GDS library not available, using fallback similarity: {e}")
            # Continue without GDS - we'll use fallback similarity
        
        return manager
        
    def _prepare_vector(self, vector) -> List[float]:
        """Prepare vector for storage by converting to list of floats"""
        if isinstance(vector, np.ndarray):
            return [float(x) for x in vector.tolist()]
        elif isinstance(vector, list):
            if len(vector) == 0:
                raise ValueError("Empty vector")
            
            # If it's a list of vectors, combine them
            if isinstance(vector[0], (list, np.ndarray)):
                # Convert any numpy arrays to lists
                vectors = [v.tolist() if isinstance(v, np.ndarray) else v for v in vector]
                # Calculate mean of vectors element-wise
                combined = [
                    sum(v[i] for v in vectors) / len(vectors)
                    for i in range(len(vectors[0]))
                ]
                return [float(x) for x in combined]
            
            # Single vector as list
            return [float(x) for x in vector]
        else:
            raise ValueError(f"Unsupported vector type: {type(vector)}")
        
    def _calculate_tool_hash(self, tool: BaseTool, metadata) -> str:
        """Calculate hash of tool metadata to detect changes"""
        tool_data = {
            "name": tool.name,
            "description": tool.description,
            "metadata": metadata.dict()
        }
        return hashlib.sha256(json.dumps(tool_data, sort_keys=True).encode()).hexdigest()

    async def get_tool_hash(self, tool_id: str) -> str:
        """Get stored tool hash from Neo4j"""
        query = """
        MATCH (t:Tool {id: $tool_id})
        RETURN t.hash as hash
        """
        result = await self.graph_db.query(query, {"tool_id": tool_id})
        return result[0]["hash"] if result else None

    async def register_tool(self, tool: BaseTool, force_update: bool = False):
        """Register or update a tool in the graph"""
        try:
            # 1. Extract metadata
            metadata = self.extractor.extract_from_tool(tool)
            
            # 2. Calculate tool hash
            tool_hash = self._calculate_tool_hash(tool, metadata)
            
            # 3. Check if tool needs update
            existing_hash = await self.get_tool_hash(metadata.capability_id)
            if existing_hash and not force_update:
                if existing_hash == tool_hash:
                    logger.info(f"Tool {tool.name} is up to date")
                    return
                
            # 4. Generate vectors
            vectors = await self.embedder.generate_vectors(metadata)
            
            # 5. Prepare parameters
            params = {
                "tool_id": metadata.capability_id,
                "name": tool.name,
                "description": tool.description,
                "hash": tool_hash,
                "semantic_core_concept": metadata.semantic_vector.core_concept,
                "semantic_domain": metadata.semantic_vector.domain,
                "semantic_service_type": metadata.semantic_vector.service_type,
                "semantic_vector": self._prepare_vector(vectors["semantic_vector"]),
                "functional_operation": metadata.functional_vector.operation,
                "functional_vector": self._prepare_vector(vectors["functional_vector"]),
                "contextual_usage_context": metadata.contextual_vector.usage_context,
                "contextual_vector": self._prepare_vector(vectors["contextual_vector"])
            }
            
            # 6. Delete existing tool if updating
            if existing_hash:
                await self.delete_tool(metadata.capability_id)
            
            # 7. Create new tool
            await self.graph_db.query(
                self.queries.CREATE_TOOL_CAPABILITY.query,
                params,
                read_only=False
            )
            
            logger.info(f"Successfully {'updated' if existing_hash else 'registered'} tool {tool.name}")
            
        except Exception as e:
            logger.error(f"Error registering tool {tool.name}: {str(e)}")
            raise

    async def delete_tool(self, tool_id: str):
        """Delete a tool and its vectors from the graph"""
        query = """
        MATCH (t:Tool {id: $tool_id})
        OPTIONAL MATCH (t)-[:HAS_SEMANTIC]->(sv:SemanticVector)
        OPTIONAL MATCH (t)-[:HAS_FUNCTIONAL]->(fv:FunctionalVector)
        OPTIONAL MATCH (t)-[:HAS_CONTEXTUAL]->(cv:ContextualVector)
        DETACH DELETE t, sv, fv, cv
        """
        await self.graph_db.query(query, {"tool_id": tool_id}, read_only=False)

    async def sync_tools(self, tools: List[BaseTool]):
        """Sync all tools with the graph"""
        # Get all tool IDs from graph
        query = "MATCH (t:Tool) RETURN t.id as id"
        result = await self.graph_db.query(query)
        existing_ids = {r["id"] for r in result}
        
        # Register/update provided tools
        for tool in tools:
            await self.register_tool(tool)
        
        # Remove tools that no longer exist
        current_ids = {f"tool_{tool.name}" for tool in tools}
        for old_id in existing_ids - current_ids:
            await self.delete_tool(old_id)

    async def get_registry_status(self) -> Dict[str, Any]:
        """Get status of tool registry"""
        try:
            query = """
            MATCH (t:Tool)
            RETURN count(t) as tool_count,
                   collect(t.name) as tool_names,
                   collect(t.hash) as tool_hashes
            """
            result = await self.graph_db.query(query)
            return {
                "total_tools": result[0]["tool_count"],
                "registered_tools": result[0]["tool_names"],
                "health_status": "healthy",
                "last_sync": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "health_status": "error",
                "error": str(e)
            }

    async def verify_tool_integrity(self, tools: List[BaseTool]) -> List[Dict[str, Any]]:
        """Verify integrity of tool registry"""
        issues = []
        for tool in tools:
            try:
                metadata = self.extractor.extract_from_tool(tool)
                current_hash = self._calculate_tool_hash(tool, metadata)
                stored_hash = await self.get_tool_hash(metadata.capability_id)
                
                if stored_hash != current_hash:
                    issues.append({
                        "tool": tool.name,
                        "issue": "hash_mismatch",
                        "current_hash": current_hash,
                        "stored_hash": stored_hash
                    })
            except Exception as e:
                issues.append({
                    "tool": tool.name,
                    "issue": "verification_failed",
                    "error": str(e)
                })
        return issues

    async def search_by_capability(self, 
        query_text: str,
        weights: Optional[SearchWeights] = None,
        threshold: float = 0.6,
        limit: int = 5
    ) -> List[SearchResult]:
        """Search tools by capability using vector similarity"""
        try:
            # Parse query into structured metadata
            query_metadata = await self.query_parser.parse_query(query_text)
            
            # Create embedding texts
            embed_texts = [
                f"concept: {query_metadata.core_concept}",
                f"domain: {query_metadata.domain}",
                f"service: {query_metadata.service_type}",
                f"operation: {query_metadata.operation}",
                f"context: {query_metadata.usage_context}",
                query_metadata.description
            ]
            
            # Generate embeddings
            vectors = await asyncio.gather(*[
                self.embed_service.create_text_embedding(text)
                for text in embed_texts
            ])
            
            # Combine vectors by type
            semantic_vectors = vectors[0:3]  # Concept, domain, service
            functional_vector = vectors[3]   # Operation
            contextual_vectors = vectors[4:] # Context and description
            
            # Prepare search parameters
            weights = weights or SearchWeights()
            params = {
                "semantic_vector": self._prepare_vector(semantic_vectors),
                "functional_vector": self._prepare_vector(functional_vector),
                "contextual_vector": self._prepare_vector(contextual_vectors),
                "weights": {
                    k: float(v) for k, v in weights.dict().items()
                },
                "threshold": float(threshold),
                "limit": int(limit)
            }
            
            # Execute search
            results = await self.graph_db.query(
                self.queries.SEARCH_BY_VECTOR.query,
                params
            )
            
            return [SearchResult(**result) for result in results]
            
        except Exception as e:
            logger.error(f"Error searching tools by capability: {str(e)}")
            raise

    async def search_by_text(self, 
        query: str,
        limit: int = 5
    ) -> List[SearchResult]:
        """Simple text-based search for tools"""
        try:
            results = await self.graph_db.query(
                self.queries.SEARCH_BY_TEXT.query,
                {"query": query, "limit": limit}
            )
            return [SearchResult(**result) for result in results]
            
        except Exception as e:
            logger.error(f"Error searching tools by text: {str(e)}")
            raise