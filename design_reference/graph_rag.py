#!/usr/bin/env python3
"""
Advanced GraphRAG MCP Server with Neo4j Aura Cloud
Combines vector embeddings with graph relationships for complex knowledge retrieval
"""

import json
import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import re

# Core dependencies
from sentence_transformers import SentenceTransformer
from neo4j import AsyncGraphDatabase
import spacy

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    CallToolResult,
    ListResourcesResult,
    ListToolsResult,
    ReadResourceResult,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GraphRAGConfig:
    """Configuration for GraphRAG system"""
    # Neo4j connection
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    
    # Embedding configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # Graph configuration
    similarity_threshold: float = 0.7
    max_hop_distance: int = 3
    community_algorithm: str = "louvain"
    
    # NLP configuration
    spacy_model: str = "en_core_web_sm"

class GraphRAGServer:
    """Advanced GraphRAG MCP Server"""
    
    def __init__(self, config: GraphRAGConfig):
        self.config = config
        self.server = Server("graphrag-server")
        self.neo4j_driver = None
        self.embedding_model = None
        self.nlp = None
        self._setup_handlers()
    
    async def initialize(self):
        """Initialize all components"""
        try:
            # Initialize Neo4j connection
            self.neo4j_driver = AsyncGraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password)
            )
            
            # Test connection
            await self.neo4j_driver.verify_connectivity()
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(self.config.embedding_model)
            
            # Initialize spaCy for NER and parsing
            try:
                self.nlp = spacy.load(self.config.spacy_model)
            except OSError:
                logger.warning(f"SpaCy model {self.config.spacy_model} not found. Install with: python -m spacy download {self.config.spacy_model}")
                self.nlp = None
            
            # Setup graph schema
            await self._setup_graph_schema()
            
            logger.info("GraphRAG server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG server: {e}")
            raise
    
    async def _setup_graph_schema(self):
        """Setup Neo4j schema and indexes"""
        async with self.neo4j_driver.session() as session:
            # Create indexes for performance
            schema_queries = [
                # Node indexes
                "CREATE INDEX node_id_index IF NOT EXISTS FOR (n:Entity) ON (n.id)",
                "CREATE INDEX document_id_index IF NOT EXISTS FOR (d:Document) ON (d.id)",
                "CREATE INDEX concept_name_index IF NOT EXISTS FOR (c:Concept) ON (c.name)",
                "CREATE INDEX community_id_index IF NOT EXISTS FOR (com:Community) ON (com.id)",
                
                # Vector indexes (Neo4j 5.x)
                """CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS 
                   FOR (e:Entity) ON (e.embedding) 
                   OPTIONS {indexConfig: {
                     `vector.dimensions`: $dimension,
                     `vector.similarity_function`: 'cosine'
                   }}""",
                   
                """CREATE VECTOR INDEX document_embeddings IF NOT EXISTS 
                   FOR (d:Document) ON (d.embedding) 
                   OPTIONS {indexConfig: {
                     `vector.dimensions`: $dimension,
                     `vector.similarity_function`: 'cosine'
                   }}""",
                
                # Text search indexes
                "CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.description]",
                "CREATE FULLTEXT INDEX document_fulltext IF NOT EXISTS FOR (d:Document) ON EACH [d.title, d.content]",
            ]
            
            for query in schema_queries:
                try:
                    await session.run(query, dimension=self.config.embedding_dimension)
                except Exception as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Schema setup warning: {e}")
    
    def _extract_entities(self, text: str) -> List[Dict]:
        """Extract entities from text using spaCy"""
        if not self.nlp:
            return []
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "description": spacy.explain(ent.label_) or ent.label_
            })
        
        return entities
    
    def _extract_relationships(self, text: str, entities: List[Dict]) -> List[Dict]:
        """Extract relationships between entities"""
        if not self.nlp:
            return []
        
        doc = self.nlp(text)
        relationships = []
        
        # Simple pattern-based relationship extraction
        patterns = [
            (r"(.+?)\s+(?:is|are|was|were)\s+(.+)", "IS_A"),
            (r"(.+?)\s+(?:has|have|had)\s+(.+)", "HAS"),
            (r"(.+?)\s+(?:uses|use|used)\s+(.+)", "USES"),
            (r"(.+?)\s+(?:contains|contain|contained)\s+(.+)", "CONTAINS"),
            (r"(.+?)\s+(?:part of|belongs to)\s+(.+)", "PART_OF"),
            (r"(.+?)\s+(?:connected to|linked to|related to)\s+(.+)", "RELATED_TO"),
        ]
        
        for pattern, rel_type in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                source = match.group(1).strip()
                target = match.group(2).strip()
                if len(source) > 2 and len(target) > 2:
                    relationships.append({
                        "source": source,
                        "target": target,
                        "type": rel_type,
                        "confidence": 0.8
                    })
        
        return relationships
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_resources()
        async def list_resources() -> ListResourcesResult:
            """List GraphRAG resources"""
            resources = [
                Resource(
                    uri="graphrag://graph/schema",
                    name="Graph Schema",
                    description="Neo4j graph database schema information",
                    mimeType="application/json"
                ),
                Resource(
                    uri="graphrag://graph/statistics",
                    name="Graph Statistics",
                    description="Graph database statistics and metrics",
                    mimeType="application/json"
                ),
                Resource(
                    uri="graphrag://entities/all",
                    name="All Entities",
                    description="List of all entities in the knowledge graph",
                    mimeType="application/json"
                ),
                Resource(
                    uri="graphrag://documents/all",
                    name="All Documents",
                    description="List of all documents in the knowledge base",
                    mimeType="application/json"
                ),
                Resource(
                    uri="graphrag://communities/all",
                    name="All Communities",
                    description="List of detected communities in the graph",
                    mimeType="application/json"
                ),
            ]
            
            return ListResourcesResult(resources=resources)
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> ReadResourceResult:
            """Read GraphRAG resources"""
            
            async with self.neo4j_driver.session() as session:
                if uri == "graphrag://graph/schema":
                    # Get graph schema information
                    result = await session.run("""
                        CALL db.schema.visualization()
                        YIELD nodes, relationships
                        RETURN nodes, relationships
                    """)
                    schema_data = await result.single()
                    
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps({
                                "nodes": schema_data["nodes"] if schema_data else [],
                                "relationships": schema_data["relationships"] if schema_data else []
                            }, indent=2)
                        )]
                    )
                
                elif uri == "graphrag://graph/statistics":
                    # Get graph statistics
                    stats_query = """
                    CALL {
                        MATCH (n) RETURN labels(n) as label, count(n) as count
                    }
                    WITH collect({label: label[0], count: count}) as node_stats
                    CALL {
                        MATCH ()-[r]->() RETURN type(r) as type, count(r) as count
                    }
                    WITH node_stats, collect({type: type, count: count}) as rel_stats
                    RETURN node_stats, rel_stats
                    """
                    
                    result = await session.run(stats_query)
                    stats_data = await result.single()
                    
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps({
                                "node_statistics": stats_data["node_stats"] if stats_data else [],
                                "relationship_statistics": stats_data["rel_stats"] if stats_data else [],
                                "timestamp": datetime.now().isoformat()
                            }, indent=2)
                        )]
                    )
                
                elif uri == "graphrag://entities/all":
                    # Get all entities
                    result = await session.run("""
                        MATCH (e:Entity)
                        RETURN e.id as id, e.name as name, e.type as type, 
                               e.description as description, e.confidence as confidence
                        ORDER BY e.name
                        LIMIT 1000
                    """)
                    
                    entities = []
                    async for record in result:
                        entities.append(dict(record))
                    
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps(entities, indent=2)
                        )]
                    )
                
                elif uri == "graphrag://documents/all":
                    # Get all documents
                    result = await session.run("""
                        MATCH (d:Document)
                        RETURN d.id as id, d.title as title, d.source as source,
                               d.created_at as created_at, size(d.content) as content_length
                        ORDER BY d.created_at DESC
                        LIMIT 1000
                    """)
                    
                    documents = []
                    async for record in result:
                        documents.append(dict(record))
                    
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps(documents, indent=2)
                        )]
                    )
                
                elif uri == "graphrag://communities/all":
                    # Get all communities
                    result = await session.run("""
                        MATCH (c:Community)
                        RETURN c.id as id, c.name as name, c.description as description,
                               c.size as size, c.density as density
                        ORDER BY c.size DESC
                    """)
                    
                    communities = []
                    async for record in result:
                        communities.append(dict(record))
                    
                    return ReadResourceResult(
                        contents=[TextContent(
                            type="text",
                            text=json.dumps(communities, indent=2)
                        )]
                    )
            
            raise ValueError(f"Unknown resource URI: {uri}")
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List GraphRAG tools"""
            tools = [
                Tool(
                    name="ingest_document",
                    description="Ingest and process a document into the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Document content"},
                            "title": {"type": "string", "description": "Document title"},
                            "source": {"type": "string", "description": "Document source/URL"},
                            "metadata": {"type": "object", "description": "Additional metadata"}
                        },
                        "required": ["content"]
                    }
                ),
                Tool(
                    name="semantic_search",
                    description="Perform semantic search across entities and documents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "search_type": {"type": "string", "enum": ["entities", "documents", "both"], "default": "both"},
                            "limit": {"type": "integer", "default": 10, "description": "Number of results"},
                            "similarity_threshold": {"type": "number", "default": 0.7}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="graph_traversal",
                    description="Traverse the knowledge graph to find connected information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_entity": {"type": "string", "description": "Starting entity name or ID"},
                            "relationship_types": {"type": "array", "items": {"type": "string"}, "description": "Relationship types to follow"},
                            "max_depth": {"type": "integer", "default": 3, "description": "Maximum traversal depth"},
                            "return_paths": {"type": "boolean", "default": False, "description": "Return full paths"}
                        },
                        "required": ["start_entity"]
                    }
                ),
                Tool(
                    name="community_detection",
                    description="Detect and analyze communities in the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "algorithm": {"type": "string", "enum": ["louvain", "leiden", "scc"], "default": "louvain"},
                            "min_community_size": {"type": "integer", "default": 3},
                            "resolution": {"type": "number", "default": 1.0}
                        }
                    }
                ),
                Tool(
                    name="graphrag_query",
                    description="Perform complex GraphRAG query combining vector search and graph traversal",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Natural language query"},
                            "context_depth": {"type": "integer", "default": 2, "description": "Graph traversal depth for context"},
                            "max_entities": {"type": "integer", "default": 10, "description": "Maximum entities to consider"},
                            "include_communities": {"type": "boolean", "default": True, "description": "Include community context"},
                            "reasoning_mode": {"type": "string", "enum": ["local", "global", "hybrid"], "default": "hybrid"}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="entity_linking",
                    description="Link entities across documents and resolve duplicates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "similarity_threshold": {"type": "number", "default": 0.85},
                            "merge_duplicates": {"type": "boolean", "default": True}
                        }
                    }
                ),
                Tool(
                    name="graph_summarization",
                    description="Generate summaries of graph neighborhoods or communities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "Entity ID, community ID, or 'global' for entire graph"},
                            "summary_type": {"type": "string", "enum": ["entities", "relationships", "comprehensive"], "default": "comprehensive"},
                            "max_length": {"type": "integer", "default": 500}
                        },
                        "required": ["target"]
                    }
                )
            ]
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle GraphRAG tool calls"""
            
            try:
                if name == "ingest_document":
                    return await self._ingest_document(arguments)
                elif name == "semantic_search":
                    return await self._semantic_search(arguments)
                elif name == "graph_traversal":
                    return await self._graph_traversal(arguments)
                elif name == "community_detection":
                    return await self._community_detection(arguments)
                elif name == "graphrag_query":
                    return await self._graphrag_query(arguments)
                elif name == "entity_linking":
                    return await self._entity_linking(arguments)
                elif name == "graph_summarization":
                    return await self._graph_summarization(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
    
    async def _ingest_document(self, arguments: dict) -> CallToolResult:
        """Ingest and process document"""
        content = arguments["content"]
        title = arguments.get("title", "Untitled Document")
        source = arguments.get("source", "unknown")
        metadata = arguments.get("metadata", {})
        
        # Generate document embedding
        doc_embedding = self.embedding_model.encode(content)
        
        # Extract entities and relationships
        entities = self._extract_entities(content)
        relationships = self._extract_relationships(content, entities)
        
        doc_id = str(uuid.uuid4())
        
        async with self.neo4j_driver.session() as session:
            # Create document node
            await session.run("""
                CREATE (d:Document {
                    id: $doc_id,
                    title: $title,
                    content: $content,
                    source: $source,
                    embedding: $embedding,
                    created_at: datetime(),
                    metadata: $metadata
                })
            """, doc_id=doc_id, title=title, content=content, source=source,
                embedding=doc_embedding.tolist(), metadata=metadata)
            
            # Create entities and link to document
            entity_ids = []
            for entity in entities:
                entity_id = str(uuid.uuid4())
                entity_ids.append(entity_id)
                
                entity_embedding = self.embedding_model.encode(entity["text"])
                
                await session.run("""
                    CREATE (e:Entity {
                        id: $entity_id,
                        name: $name,
                        type: $type,
                        description: $description,
                        embedding: $embedding,
                        confidence: 0.8
                    })
                    WITH e
                    MATCH (d:Document {id: $doc_id})
                    CREATE (d)-[:MENTIONS]->(e)
                """, entity_id=entity_id, name=entity["text"], type=entity["label"],
                    description=entity["description"], embedding=entity_embedding.tolist(),
                    doc_id=doc_id)
            
            # Create relationships between entities
            for rel in relationships:
                await session.run("""
                    MATCH (e1:Entity {name: $source})
                    MATCH (e2:Entity {name: $target})
                    CREATE (e1)-[:RELATIONSHIP {
                        type: $rel_type,
                        confidence: $confidence,
                        source_document: $doc_id
                    }]->(e2)
                """, source=rel["source"], target=rel["target"], 
                    rel_type=rel["type"], confidence=rel["confidence"], doc_id=doc_id)
        
        result = {
            "document_id": doc_id,
            "entities_extracted": len(entities),
            "relationships_extracted": len(relationships),
            "status": "success"
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))]
        )
    
    async def _semantic_search(self, arguments: dict) -> CallToolResult:
        """Perform semantic search"""
        query = arguments["query"]
        search_type = arguments.get("search_type", "both")
        limit = arguments.get("limit", 10)
        threshold = arguments.get("similarity_threshold", 0.7)
        
        query_embedding = self.embedding_model.encode(query)
        
        results = {"entities": [], "documents": []}
        
        async with self.neo4j_driver.session() as session:
            if search_type in ["entities", "both"]:
                # Vector search for entities
                entity_results = await session.run("""
                    CALL db.index.vector.queryNodes('entity_embeddings', $limit, $embedding)
                    YIELD node, score
                    WHERE score >= $threshold
                    RETURN node.id as id, node.name as name, node.type as type,
                           node.description as description, score
                    ORDER BY score DESC
                """, embedding=query_embedding.tolist(), limit=limit, threshold=threshold)
                
                async for record in entity_results:
                    results["entities"].append(dict(record))
            
            if search_type in ["documents", "both"]:
                # Vector search for documents
                doc_results = await session.run("""
                    CALL db.index.vector.queryNodes('document_embeddings', $limit, $embedding)
                    YIELD node, score
                    WHERE score >= $threshold
                    RETURN node.id as id, node.title as title, node.source as source,
                           substring(node.content, 0, 200) as preview, score
                    ORDER BY score DESC
                """, embedding=query_embedding.tolist(), limit=limit, threshold=threshold)
                
                async for record in doc_results:
                    results["documents"].append(dict(record))
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(results, indent=2))]
        )
    
    async def _graphrag_query(self, arguments: dict) -> CallToolResult:
        """Perform comprehensive GraphRAG query"""
        query = arguments["query"]
        context_depth = arguments.get("context_depth", 2)
        max_entities = arguments.get("max_entities", 10)
        include_communities = arguments.get("include_communities", True)
        reasoning_mode = arguments.get("reasoning_mode", "hybrid")
        
        # Step 1: Semantic search for relevant entities
        semantic_results = await self._semantic_search({
            "query": query,
            "search_type": "entities",
            "limit": max_entities
        })
        
        semantic_data = json.loads(semantic_results.content[0].text)
        relevant_entities = semantic_data["entities"]
        
        if not relevant_entities:
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({
                    "query": query,
                    "context": "No relevant entities found",
                    "reasoning": "No semantic matches above threshold"
                }, indent=2))]
            )
        
        # Step 2: Graph traversal for context
        context_graph = {"nodes": [], "relationships": [], "communities": []}
        
        async with self.neo4j_driver.session() as session:
            for entity in relevant_entities[:5]:  # Top 5 entities
                # Get neighborhood
                neighborhood = await session.run("""
                    MATCH path = (e:Entity {id: $entity_id})-[*1..$depth]-(connected)
                    WITH nodes(path) as path_nodes, relationships(path) as path_rels
                    UNWIND path_nodes as node
                    WITH collect(DISTINCT {
                        id: node.id, 
                        name: node.name, 
                        type: labels(node)[0],
                        description: node.description
                    }) as nodes
                    MATCH (e:Entity {id: $entity_id})-[r]-(connected)
                    WITH nodes, collect(DISTINCT {
                        source: e.name,
                        target: connected.name,
                        type: type(r),
                        properties: properties(r)
                    }) as relationships
                    RETURN nodes, relationships
                """, entity_id=entity["id"], depth=context_depth)
                
                async for record in neighborhood:
                    context_graph["nodes"].extend(record["nodes"])
                    context_graph["relationships"].extend(record["relationships"])
        
        # Step 3: Community context (if requested)
        if include_communities:
            community_context = await session.run("""
                MATCH (e:Entity)-[:BELONGS_TO]->(c:Community)
                WHERE e.id IN $entity_ids
                RETURN c.name as community, c.description as description,
                       collect(e.name) as members
            """, entity_ids=[e["id"] for e in relevant_entities])
            
            async for record in community_context:
                context_graph["communities"].append(dict(record))
        
        # Step 4: Generate comprehensive context
        context_parts = []
        
        # Entity context
        entity_context = "Relevant Entities:\n"
        for entity in relevant_entities[:3]:
            entity_context += f"- {entity['name']} ({entity['type']}): {entity.get('description', 'No description')}\n"
        context_parts.append(entity_context)
        
        # Relationship context
        if context_graph["relationships"]:
            rel_context = "Key Relationships:\n"
            for rel in context_graph["relationships"][:5]:
                rel_context += f"- {rel['source']} {rel['type']} {rel['target']}\n"
            context_parts.append(rel_context)
        
        # Community context
        if context_graph["communities"]:
            comm_context = "Community Context:\n"
            for comm in context_graph["communities"]:
                comm_context += f"- {comm['community']}: {comm['description']}\n"
            context_parts.append(comm_context)
        
        full_context = "\n\n".join(context_parts)
        
        result = {
            "query": query,
            "reasoning_mode": reasoning_mode,
            "relevant_entities": len(relevant_entities),
            "context_nodes": len(set(n["id"] for n in context_graph["nodes"])),
            "context_relationships": len(context_graph["relationships"]),
            "communities_involved": len(context_graph["communities"]),
            "context": full_context,
            "graph_data": context_graph,
            "rag_prompt": f"Based on this knowledge graph context:\n\n{full_context}\n\nQuestion: {query}\n\nProvide a comprehensive answer using the graph relationships and entity information:"
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, indent=2))]
        )
    
    async def _graph_traversal(self, arguments: dict) -> CallToolResult:
        """Perform graph traversal"""
        start_entity = arguments["start_entity"]
        rel_types = arguments.get("relationship_types", [])
        max_depth = arguments.get("max_depth", 3)
        return_paths = arguments.get("return_paths", False)
        
        async with self.neo4j_driver.session() as session:
            if rel_types:
                rel_filter = "|".join(rel_types)
                query = f"""
                    MATCH path = (start:Entity {{name: $start}})-[:{rel_filter}*1..{max_depth}]-(connected)
                    RETURN path
                    LIMIT 100
                """
            else:
                query = f"""
                    MATCH path = (start:Entity {{name: $start}})-[*1..{max_depth}]-(connected)
                    RETURN path
                    LIMIT 100
                """
            
            result = await session.run(query, start=start_entity)
            
            paths = []
            nodes = set()
            relationships = set()
            
            async for record in result:
                path = record["path"]
                path_nodes = []
                path_rels = []
                
                for node in path.nodes:
                    node_data = {
                        "id": node["id"],
                        "name": node["name"],
                        "type": list(node.labels)[0]
                    }
                    nodes.add(json.dumps(node_data, sort_keys=True))
                    path_nodes.append(node_data)
                
                for rel in path.relationships:
                    rel_data = {
                        "type": rel.type,
                        "start": rel.start_node["name"],
                        "end": rel.end_node["name"]
                    }
                    relationships.add(json.dumps(rel_data, sort_keys=True))
                    path_rels.append(rel_data)
                
                if return_paths:
                    paths.append({
                        "nodes": path_nodes,
                        "relationships": path_rels,
                        "length": len(path_nodes)
                    })
            
            traversal_result = {
                "start_entity": start_entity,
                "max_depth": max_depth,
                "unique_nodes": len(nodes),
                "unique_relationships": len(relationships),
                "nodes": [json.loads(n) for n in nodes],
                "relationships": [json.loads(r) for r in relationships]
            }
            
            if return_paths:
                traversal_result["paths"] = paths
            
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(traversal_result, indent=2))]
            )
    
    async def _community_detection(self, arguments: dict) -> CallToolResult:
        """Detect communities in the graph"""
        algorithm = arguments.get("algorithm", "louvain")
        min_size = arguments.get("min_community_size", 3)
        resolution = arguments.get("resolution", 1.0)
        
        async with self.neo4j_driver.session() as session:
            # Run community detection algorithm
            if algorithm == "louvain":
                community_query = """
                    CALL gds.louvain.stream('myGraph', {
                        relationshipWeightProperty: 'confidence'
                    })
                    YIELD nodeId, communityId
                    WITH gds.util.asNode(nodeId) as node, communityId
                    WHERE node:Entity
                    RETURN communityId, collect(node.name) as members, count(*) as size
                    HAVING size >= $min_size
                    ORDER BY size DESC
                """
            elif algorithm == "leiden":
                community_query = """
                    CALL gds.leiden.stream('myGraph', {
                        gamma: $resolution
                    })
                    YIELD nodeId, communityId
                    WITH gds.util.asNode(nodeId) as node, communityId
                    WHERE node:Entity
                    RETURN communityId, collect(node.name) as members, count(*) as size
                    HAVING size >= $min_size
                    ORDER BY size DESC
                """
            else:  # scc (strongly connected components)
                community_query = """
                    CALL gds.scc.stream('myGraph')
                    YIELD nodeId, componentId
                    WITH gds.util.asNode(nodeId) as node, componentId
                    WHERE node:Entity
                    RETURN componentId as communityId, collect(node.name) as members, count(*) as size
                    HAVING size >= $min_size
                    ORDER BY size DESC
                """
            
            try:
                # First, ensure graph projection exists
                await session.run("""
                    CALL gds.graph.exists('myGraph')
                    YIELD exists
                    WITH exists
                    CALL apoc.when(exists, 
                        'CALL gds.graph.drop("myGraph") YIELD graphName RETURN graphName',
                        'RETURN "no graph" as graphName'
                    )
                    YIELD value
                    RETURN value
                """)
                
                # Create graph projection
                await session.run("""
                    CALL gds.graph.project(
                        'myGraph',
                        'Entity',
                        'RELATIONSHIP',
                        {
                            relationshipProperties: 'confidence'
                        }
                    )
                """)
                
                # Run community detection
                result = await session.run(community_query, min_size=min_size, resolution=resolution)
                
                communities = []
                async for record in result:
                    community_id = str(record["communityId"])
                    members = record["members"]
                    size = record["size"]
                    
                    # Calculate community density
                    density_query = """
                        MATCH (e1:Entity)-[r]-(e2:Entity)
                        WHERE e1.name IN $members AND e2.name IN $members
                        WITH count(r) as internal_edges, $size as size
                        RETURN toFloat(internal_edges) / (size * (size - 1)) as density
                    """
                    density_result = await session.run(density_query, members=members, size=size)
                    density_record = await density_result.single()
                    density = density_record["density"] if density_record else 0.0
                    
                    # Create or update community node
                    await session.run("""
                        MERGE (c:Community {id: $community_id})
                        SET c.name = 'Community ' + $community_id,
                            c.size = $size,
                            c.density = $density,
                            c.algorithm = $algorithm,
                            c.detected_at = datetime()
                        WITH c
                        UNWIND $members as member_name
                        MATCH (e:Entity {name: member_name})
                        MERGE (e)-[:BELONGS_TO]->(c)
                    """, community_id=community_id, size=size, density=density, 
                        algorithm=algorithm, members=members)
                    
                    communities.append({
                        "id": community_id,
                        "size": size,
                        "density": density,
                        "members": members,
                        "algorithm": algorithm
                    })
                
                # Clean up graph projection
                await session.run("CALL gds.graph.drop('myGraph')")
                
            except Exception as e:
                # Fallback: Simple connected components without GDS
                logger.warning(f"GDS not available, using fallback: {e}")
                
                fallback_query = """
                    MATCH (e:Entity)
                    WITH collect(e) as entities
                    UNWIND entities as entity
                    MATCH path = (entity)-[:RELATIONSHIP*]-(connected:Entity)
                    WITH entity, collect(DISTINCT connected.name) + [entity.name] as component
                    WHERE size(component) >= $min_size
                    RETURN component, size(component) as size
                    ORDER BY size DESC
                    LIMIT 20
                """
                
                result = await session.run(fallback_query, min_size=min_size)
                communities = []
                
                async for record in result:
                    community_id = str(hash(tuple(sorted(record["component"]))))
                    communities.append({
                        "id": community_id,
                        "size": record["size"],
                        "density": 0.0,
                        "members": record["component"],
                        "algorithm": "connected_components_fallback"
                    })
        
        detection_result = {
            "algorithm": algorithm,
            "min_community_size": min_size,
            "communities_found": len(communities),
            "communities": communities,
            "total_entities_in_communities": sum(c["size"] for c in communities)
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(detection_result, indent=2))]
        )
    
    async def _entity_linking(self, arguments: dict) -> CallToolResult:
        """Link similar entities and resolve duplicates"""
        similarity_threshold = arguments.get("similarity_threshold", 0.85)
        merge_duplicates = arguments.get("merge_duplicates", True)
        
        async with self.neo4j_driver.session() as session:
            # Find potentially similar entities using vector similarity
            similar_pairs = []
            
            # Get all entities with embeddings
            entities_result = await session.run("""
                MATCH (e:Entity)
                WHERE e.embedding IS NOT NULL
                RETURN e.id as id, e.name as name, e.embedding as embedding, e.type as type
            """)
            
            entities = []
            async for record in entities_result:
                entities.append(dict(record))
            
            # Compare embeddings for similarity
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    if entity1["type"] == entity2["type"]:  # Only compare same type
                        emb1 = np.array(entity1["embedding"])
                        emb2 = np.array(entity2["embedding"])
                        
                        # Cosine similarity
                        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                        
                        if similarity >= similarity_threshold:
                            similar_pairs.append({
                                "entity1_id": entity1["id"],
                                "entity1_name": entity1["name"],
                                "entity2_id": entity2["id"],
                                "entity2_name": entity2["name"],
                                "similarity": float(similarity),
                                "type": entity1["type"]
                            })
            
            # Create similarity relationships
            linked_count = 0
            merged_count = 0
            
            for pair in similar_pairs:
                # Create SIMILAR_TO relationship
                await session.run("""
                    MATCH (e1:Entity {id: $id1})
                    MATCH (e2:Entity {id: $id2})
                    MERGE (e1)-[r:SIMILAR_TO]-(e2)
                    SET r.similarity = $similarity, r.created_at = datetime()
                """, id1=pair["entity1_id"], id2=pair["entity2_id"], 
                    similarity=pair["similarity"])
                
                linked_count += 1
                
                # Merge entities if requested and high similarity
                if merge_duplicates and pair["similarity"] > 0.95:
                    # Merge the entities (keep the first, merge relationships from second)
                    await session.run("""
                        MATCH (e1:Entity {id: $id1})
                        MATCH (e2:Entity {id: $id2})
                        WITH e1, e2
                        MATCH (e2)-[r]-(other)
                        WHERE other <> e1
                        CREATE (e1)-[nr:RELATIONSHIP]->(other)
                        SET nr = properties(r)
                        WITH e1, e2, count(r) as rels_merged
                        DETACH DELETE e2
                        RETURN rels_merged
                    """, id1=pair["entity1_id"], id2=pair["entity2_id"])
                    
                    merged_count += 1
        
        linking_result = {
            "similarity_threshold": similarity_threshold,
            "merge_duplicates": merge_duplicates,
            "entities_compared": len(entities),
            "similar_pairs_found": len(similar_pairs),
            "entities_linked": linked_count,
            "entities_merged": merged_count,
            "similar_pairs": similar_pairs
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(linking_result, indent=2))]
        )
    
    async def _graph_summarization(self, arguments: dict) -> CallToolResult:
        """Generate graph summaries"""
        target = arguments["target"]
        summary_type = arguments.get("summary_type", "comprehensive")
        max_length = arguments.get("max_length", 500)
        
        async with self.neo4j_driver.session() as session:
            summary_parts = []
            
            if target == "global":
                # Global graph summary
                stats_result = await session.run("""
                    MATCH (n)
                    WITH labels(n) as node_labels, count(n) as count
                    UNWIND node_labels as label
                    WITH label, sum(count) as total_count
                    WHERE label IN ['Entity', 'Document', 'Community', 'Concept']
                    RETURN label, total_count
                    ORDER BY total_count DESC
                """)
                
                node_stats = {}
                async for record in stats_result:
                    node_stats[record["label"]] = record["total_count"]
                
                rel_result = await session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as rel_type, count(r) as count
                    ORDER BY count DESC
                    LIMIT 10
                """)
                
                rel_stats = {}
                async for record in rel_result:
                    rel_stats[record["rel_type"]] = record["count"]
                
                summary_parts.append(f"Graph Overview: {sum(node_stats.values())} total nodes")
                summary_parts.append(f"Node Distribution: {', '.join([f'{k}: {v}' for k, v in node_stats.items()])}")
                summary_parts.append(f"Top Relationships: {', '.join([f'{k}: {v}' for k, v in list(rel_stats.items())[:5]])}")
                
            elif target.startswith("community_"):
                # Community summary
                community_id = target.replace("community_", "")
                
                comm_result = await session.run("""
                    MATCH (c:Community {id: $comm_id})
                    MATCH (e:Entity)-[:BELONGS_TO]->(c)
                    WITH c, collect(e.name) as members, count(e) as size
                    MATCH (e1:Entity)-[r]-(e2:Entity)
                    WHERE e1.name IN members AND e2.name IN members
                    RETURN c.name as name, c.description as description, 
                           members, size, count(r) as internal_connections
                """, comm_id=community_id)
                
                comm_data = await comm_result.single()
                if comm_data:
                    summary_parts.append(f"Community: {comm_data['name']}")
                    summary_parts.append(f"Size: {comm_data['size']} entities")
                    summary_parts.append(f"Internal Connections: {comm_data['internal_connections']}")
                    summary_parts.append(f"Key Members: {', '.join(comm_data['members'][:5])}")
                    if comm_data['description']:
                        summary_parts.append(f"Description: {comm_data['description']}")
                
            else:
                # Entity-specific summary
                entity_result = await session.run("""
                    MATCH (e:Entity {name: $target})
                    OPTIONAL MATCH (e)-[r]-(connected:Entity)
                    WITH e, type(r) as rel_type, count(connected) as conn_count
                    RETURN e.name as name, e.type as type, e.description as description,
                           collect({relationship: rel_type, count: conn_count}) as connections
                """, target=target)
                
                entity_data = await entity_result.single()
                if entity_data:
                    summary_parts.append(f"Entity: {entity_data['name']} ({entity_data['type']})")
                    if entity_data['description']:
                        summary_parts.append(f"Description: {entity_data['description']}")
                    
                    connections = [c for c in entity_data['connections'] if c['relationship']]
                    if connections:
                        conn_summary = ', '.join([f"{c['relationship']}: {c['count']}" for c in connections[:3]])
                        summary_parts.append(f"Connections: {conn_summary}")
        
        # Combine and truncate summary
        full_summary = ". ".join(summary_parts)
        if len(full_summary) > max_length:
            full_summary = full_summary[:max_length-3] + "..."
        
        summary_result = {
            "target": target,
            "summary_type": summary_type,
            "summary": full_summary,
            "length": len(full_summary),
            "components": summary_parts
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(summary_result, indent=2))]
        )
    
    async def close(self):
        """Close connections"""
        if self.neo4j_driver:
            await self.neo4j_driver.close()

async def main():
    """Main entry point"""
    import os
    
    config = GraphRAGConfig(
        neo4j_uri=os.getenv("NEO4J_URI", "neo4j+s://your-instance.databases.neo4j.io"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "your-password"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.7")),
        max_hop_distance=int(os.getenv("MAX_HOP_DISTANCE", "3"))
    )
    
    graphrag_server = GraphRAGServer(config)
    
    try:
        # Initialize the server
        await graphrag_server.initialize()
        
        # Run the MCP server
        async with stdio_server() as (read_stream, write_stream):
            await graphrag_server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="graphrag-server",
                    server_version="1.0.0",
                    capabilities=graphrag_server.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    )
                )
            )
    finally:
        await graphrag_server.close()

if __name__ == "__main__":
    asyncio.run(main())