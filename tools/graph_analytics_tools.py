#!/usr/bin/env python3
"""
Graph Analytics Tools for MCP Server
Provides comprehensive GraphRAG and knowledge graph analytics workflow
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from core.security import get_security_manager, SecurityLevel
from core.logging import get_logger
from tools.base_tool import BaseTool

# Import graph analytics services
from tools.services.graph_analytics_service.core.entity_extractor import EntityExtractor
from tools.services.graph_analytics_service.core.relation_extractor import RelationExtractor
from tools.services.graph_analytics_service.core.attribute_extractor import AttributeExtractor
from tools.services.graph_analytics_service.core.graph_constructor import GraphConstructor
from tools.services.graph_analytics_service.services.neo4j_client import get_neo4j_client
from tools.services.graph_analytics_service.services.neo4j_graphrag_client import get_neo4j_graphrag_client
from tools.services.graph_analytics_service.services.knowledge_graph import KnowledgeGraph
from tools.services.graph_analytics_service.services.graphrag_retriever import GraphRAGRetriever
from tools.services.graph_analytics_service.utils.embedding_utils import get_embedding_service
from tools.services.graph_analytics_service.utils.graph_utils import validate_graph_structure, calculate_centrality, find_communities

logger = get_logger(__name__)

class GraphAnalyticsTools(BaseTool):
    """Graph Analytics Tools using BaseTool"""
    
    def __init__(self):
        super().__init__()
        self.entity_extractor = None
        self.relation_extractor = None
        self.attribute_extractor = None
        self.graph_constructor = None
        self.neo4j_client = None
        self.graphrag_client = None
        self.knowledge_graph = None
        self.embedding_service = None
    
    async def _initialize_services(self):
        """Initialize services lazily"""
        if self.entity_extractor is None:
            self.entity_extractor = EntityExtractor()
            self.relation_extractor = RelationExtractor()
            self.attribute_extractor = AttributeExtractor()
            self.graph_constructor = GraphConstructor()
            self.neo4j_client = await get_neo4j_client()
            
            if self.neo4j_client:
                self.graphrag_client = await get_neo4j_graphrag_client()
                if self.graphrag_client:
                    self.knowledge_graph = KnowledgeGraph(self.graphrag_client)
            
            self.embedding_service = get_embedding_service()
    
    def register_all_tools(self, mcp):
        """Register all graph analytics tools"""
        
        # Get security manager for applying decorators
        security_manager = get_security_manager()
        
        async def extract_knowledge_graph(
            text: str,
            source_id: Optional[str] = None,
            extraction_methods: Optional[List[str]] = None,
            generate_embeddings: bool = True
        ) -> str:
            """
            Complete knowledge graph extraction workflow: Text -> Knowledge Graph
            
            Steps:
            1. Entity Extraction
            2. Relation Extraction 
            3. Attribute Extraction
            4. Graph Construction
            5. Embedding & Storage
            
            Args:
                text: Input text to analyze
                source_id: Optional source document identifier
                extraction_methods: Extraction methods ['llm', 'pattern', 'hybrid']
                generate_embeddings: Whether to generate and store embeddings
                
            Returns:
                JSON string containing knowledge graph extraction results
                
            Keywords: knowledge, graph, entity, relation, extraction, nlp, graphrag, neo4j
            Category: graph
            """
            try:
                await self._initialize_services()
                
                # Security check
                if not hasattr(security_manager, 'check_permission') or not security_manager.check_permission("graph_analytics", SecurityLevel.MEDIUM):
                    logger.warning("Proceeding without full security check")
                
                logger.info(f"Starting knowledge graph extraction for text ({len(text)} chars)")
                
                workflow_results = {
                    "workflow": "extract_knowledge_graph",
                    "start_time": datetime.now().isoformat(),
                    "text_length": len(text),
                    "source_id": source_id,
                    "steps_completed": [],
                    "step_results": {}
                }
                
                extraction_methods = extraction_methods or ['hybrid']
                
                # === STEP 1: ENTITY EXTRACTION ===
                logger.info("Step 1: Extracting entities from text")
                step1_start = datetime.now()
                
                entities = await self.entity_extractor.extract_entities(
                    text=text, 
                    methods=extraction_methods
                )
                
                step1_time = (datetime.now() - step1_start).total_seconds()
                workflow_results["steps_completed"].append("entity_extraction")
                workflow_results["step_results"]["step1_entity_extraction"] = {
                    "execution_time_seconds": step1_time,
                    "entities_found": len(entities),
                    "entity_types": list(set(e.entity_type.value for e in entities)),
                    "methods_used": extraction_methods,
                    "status": "completed"
                }
                
                logger.info(f"Step 1 completed in {step1_time:.2f}s - Found {len(entities)} entities")
                
                # === STEP 2: RELATION EXTRACTION ===
                logger.info("Step 2: Extracting relationships between entities")
                step2_start = datetime.now()
                
                relations = await self.relation_extractor.extract_relations(
                    text=text,
                    entities=entities,
                    methods=extraction_methods
                )
                
                step2_time = (datetime.now() - step2_start).total_seconds()
                workflow_results["steps_completed"].append("relation_extraction")
                workflow_results["step_results"]["step2_relation_extraction"] = {
                    "execution_time_seconds": step2_time,
                    "relations_found": len(relations),
                    "relation_types": list(set(r.relation_type.value for r in relations)),
                    "methods_used": extraction_methods,
                    "status": "completed"
                }
                
                logger.info(f"Step 2 completed in {step2_time:.2f}s - Found {len(relations)} relations")
                
                # === STEP 3: ATTRIBUTE EXTRACTION ===
                logger.info("Step 3: Extracting entity attributes")
                step3_start = datetime.now()
                
                entity_attributes = await self.attribute_extractor.extract_entity_attributes_batch(
                    text=text,
                    entities=entities
                )
                
                step3_time = (datetime.now() - step3_start).total_seconds()
                total_attributes = sum(len(attrs) for attrs in entity_attributes.values())
                
                workflow_results["steps_completed"].append("attribute_extraction")
                workflow_results["step_results"]["step3_attribute_extraction"] = {
                    "execution_time_seconds": step3_time,
                    "attributes_found": total_attributes,
                    "entities_with_attributes": len([e for e, a in entity_attributes.items() if a]),
                    "methods_used": extraction_methods,
                    "status": "completed"
                }
                
                logger.info(f"Step 3 completed in {step3_time:.2f}s - Found {total_attributes} attributes")
                
                # === STEP 4: GRAPH CONSTRUCTION ===
                logger.info("Step 4: Constructing knowledge graph")
                step4_start = datetime.now()
                
                knowledge_graph = self.graph_constructor.construct_graph(
                    entities=entities,
                    relations=relations,
                    entity_attributes=entity_attributes,
                    source_text=text
                )
                
                # Optimize graph
                optimized_graph = self.graph_constructor.optimize_graph(knowledge_graph)
                
                # Validate graph
                validation_result = self.graph_constructor.validate_graph(optimized_graph)
                
                step4_time = (datetime.now() - step4_start).total_seconds()
                workflow_results["steps_completed"].append("graph_construction")
                workflow_results["step_results"]["step4_graph_construction"] = {
                    "execution_time_seconds": step4_time,
                    "nodes_created": len(optimized_graph.nodes),
                    "edges_created": len(optimized_graph.edges),
                    "graph_valid": validation_result["valid"],
                    "validation_errors": len(validation_result["errors"]),
                    "validation_warnings": len(validation_result["warnings"]),
                    "graph_statistics": validation_result["statistics"],
                    "status": "completed"
                }
                
                logger.info(f"Step 4 completed in {step4_time:.2f}s - Created graph with {len(optimized_graph.nodes)} nodes")
                
                # === STEP 5: EMBEDDING & STORAGE ===
                step5_results = {}
                if generate_embeddings and self.graphrag_client:
                    logger.info("Step 5: Generating embeddings and storing in Neo4j")
                    step5_start = datetime.now()
                    
                    try:
                        storage_result = await self.graphrag_client.extract_and_store_from_text(
                            text=text,
                            source_id=source_id or f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            chunk_id=None
                        )
                        
                        step5_time = (datetime.now() - step5_start).total_seconds()
                        workflow_results["steps_completed"].append("embedding_storage")
                        step5_results = {
                            "execution_time_seconds": step5_time,
                            "entities_stored": storage_result.get("entities_stored", 0),
                            "relationships_stored": storage_result.get("relationships_stored", 0),
                            "neo4j_available": True,
                            "status": "completed"
                        }
                        
                        logger.info(f"Step 5 completed in {step5_time:.2f}s - Stored in Neo4j")
                        
                    except Exception as e:
                        logger.warning(f"Neo4j storage failed: {e}")
                        step5_results = {
                            "execution_time_seconds": 0,
                            "entities_stored": 0,
                            "relationships_stored": 0,
                            "neo4j_available": False,
                            "error": str(e),
                            "status": "failed"
                        }
                else:
                    step5_results = {
                        "execution_time_seconds": 0,
                        "entities_stored": 0,
                        "relationships_stored": 0,
                        "neo4j_available": False,
                        "status": "skipped"
                    }
                
                workflow_results["step_results"]["step5_embedding_storage"] = step5_results
                
                # === WORKFLOW COMPLETION ===
                total_time = (datetime.now() - datetime.fromisoformat(workflow_results["start_time"])).total_seconds()
                workflow_results["end_time"] = datetime.now().isoformat()
                workflow_results["total_execution_time_seconds"] = total_time
                workflow_results["status"] = "success"
                
                logger.info(f"Knowledge graph extraction completed successfully in {total_time:.2f}s")
                
                # Format response
                response = {
                    "status": "success",
                    "action": "extract_knowledge_graph",
                    "data": {
                        "workflow_results": workflow_results,
                        "knowledge_graph": {
                            "nodes": [
                                {
                                    "id": node.id,
                                    "entity": {
                                        "text": node.entity.text,
                                        "type": node.entity.entity_type.value,
                                        "canonical_form": node.entity.canonical_form,
                                        "confidence": node.entity.confidence
                                    },
                                    "attributes": {
                                        name: {
                                            "value": attr.value,
                                            "type": attr.attribute_type.value,
                                            "confidence": attr.confidence
                                        }
                                        for name, attr in node.attributes.items()
                                    }
                                }
                                for node in optimized_graph.nodes.values()
                            ],
                            "edges": [
                                {
                                    "id": edge.id,
                                    "source": edge.source_id,
                                    "target": edge.target_id,
                                    "relation": {
                                        "type": edge.relation.relation_type.value,
                                        "predicate": edge.relation.predicate,
                                        "confidence": edge.relation.confidence
                                    },
                                    "weight": edge.weight
                                }
                                for edge in optimized_graph.edges.values()
                            ],
                            "metadata": optimized_graph.metadata
                        },
                        "validation_result": validation_result,
                        "message": f"Knowledge graph extracted: {len(entities)} entities, {len(relations)} relations, {len(optimized_graph.nodes)} nodes, {len(optimized_graph.edges)} edges"
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                return json.dumps(response, ensure_ascii=False, indent=2)
                
            except Exception as e:
                error_response = {
                    "status": "error",
                    "action": "extract_knowledge_graph",
                    "data": {
                        "text_length": len(text),
                        "error": str(e),
                        "workflow_results": workflow_results if 'workflow_results' in locals() else {},
                        "message": "Knowledge graph extraction failed"
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.error(f"Knowledge graph extraction failed: {e}")
                return json.dumps(error_response, ensure_ascii=False)

        async def graphrag_query(
            query: str,
            top_k: int = 10,
            similarity_threshold: float = 0.7,
            expand_context: bool = True,
            context_depth: int = 2
        ) -> str:
            """
            GraphRAG semantic query using graph-enhanced retrieval
            
            Args:
                query: Natural language query
                top_k: Number of top results to return
                similarity_threshold: Similarity threshold
                expand_context: Whether to expand graph context
                context_depth: Context expansion depth
                
            Returns:
                JSON string containing query results and graph context
                
            Keywords: query, graphrag, semantic, search, retrieval, context, knowledge
            Category: graph
            """
            try:
                await self._initialize_services()
                
                if not self.graphrag_client:
                    raise Exception("GraphRAG client not available - Neo4j may not be configured")
                
                logger.info(f"Starting GraphRAG query: {query[:100]}...")
                
                # Generate query embedding
                query_embedding = await self.embedding_service.generate_single_embedding(query)
                
                # Initialize retriever
                retriever = GraphRAGRetriever(self.graphrag_client)
                
                # Perform retrieval
                if expand_context:
                    results = await retriever.retrieve(
                        query=query,
                        query_embedding=query_embedding,
                        top_k=top_k,
                        similarity_threshold=similarity_threshold,
                        graph_expansion_depth=context_depth,
                        include_graph_context=True
                    )
                else:
                    results = await retriever.retrieve(
                        query=query,
                        query_embedding=query_embedding,
                        top_k=top_k,
                        similarity_threshold=similarity_threshold,
                        graph_expansion_depth=0,
                        include_graph_context=False
                    )
                
                # Format results
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "content": result.content,
                        "score": result.score,
                        "source_id": result.source_id,
                        "chunk_id": result.chunk_id,
                        "entity_context": result.entity_context,
                        "graph_context": result.graph_context,
                        "metadata": result.metadata
                    })
                
                response = {
                    "status": "success",
                    "action": "graphrag_query",
                    "data": {
                        "query": query,
                        "results": formatted_results,
                        "results_count": len(formatted_results),
                        "query_params": {
                            "top_k": top_k,
                            "similarity_threshold": similarity_threshold,
                            "expand_context": expand_context,
                            "context_depth": context_depth
                        },
                        "message": f"Found {len(formatted_results)} relevant results"
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"GraphRAG query completed: {len(formatted_results)} results")
                return json.dumps(response, ensure_ascii=False, indent=2)
                
            except Exception as e:
                error_response = {
                    "status": "error",
                    "action": "graphrag_query",
                    "data": {
                        "query": query,
                        "error": str(e),
                        "message": "GraphRAG query failed"
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.error(f"GraphRAG query failed: {e}")
                return json.dumps(error_response, ensure_ascii=False)

        # Register tools using base_tool functionality
        self.register_tool(mcp, extract_knowledge_graph)
        self.register_tool(mcp, graphrag_query)

# Create global instance
graph_analytics_tools = GraphAnalyticsTools()

def register_graph_analytics_tools(mcp):
    """Register graph analytics tools with the MCP server"""
    logger.info("Registering graph analytics tools...")
    graph_analytics_tools.register_all_tools(mcp)
    logger.info("Graph analytics tools registered successfully")