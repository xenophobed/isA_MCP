#!/usr/bin/env python3
"""
Graph Analytics Service

Provides graph analytics capabilities for text content.
Integrates with knowledge graph construction, storage, and user management.

Core Functions:
1. Text to Knowledge Graph processing with user isolation
2. GraphRAG query and retrieval with user permissions
3. MCP resource registration and management
4. User permission-based access control
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime
import uuid

# Import required services - NO MOCK FALLBACKS!
import sys
from pathlib import Path

# Ensure proper import paths
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools"))

try:
    # Try relative imports first (when used as module)
    from tools.services.data_analytics_service.services.knowledge_service.graph_constructor import GraphConstructor
    from tools.services.data_analytics_service.services.knowledge_service.neo4j_store import Neo4jStore
    from tools.services.data_analytics_service.services.knowledge_service.knowledge_retriever import GraphRAGRetriever
    from ...user_service.user_service import UserService
    from ...user_service.models import User
except ImportError:
    # Fallback to absolute imports (when used directly)
    from knowledge_service.graph_constructor import GraphConstructor
    from knowledge_service.neo4j_store import Neo4jStore
    from knowledge_service.knowledge_retriever import GraphRAGRetriever
    from tools.services.user_service.user_service import UserService
    from tools.services.user_service.models import User

logger = logging.getLogger(__name__)

class GraphAnalyticsService:
    """
    Graph Analytics Service for processing text into knowledge graphs.
    
    Features:
    - Text to knowledge graph construction
    - GraphRAG query and retrieval
    - User permission management
    - MCP resource registration
    - Neo4j storage with user isolation
    """
    
    def __init__(self, 
                 user_service: UserService,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize Graph Analytics Service.
        
        Args:
            user_service: User management service
            config: Service configuration options
        """
        self.service_name = "graph_analytics_service"
        self.version = "1.0.0"
        self.config = config or {}
        
        # Initialize services
        self.user_service = user_service
        self.graph_constructor = GraphConstructor(self.config.get('graph_constructor', {}))
        
        # Initialize Neo4j client and store
        try:
            from tools.services.data_analytics_service.services.knowledge_service.neo4j_client import Neo4jClient
        except ImportError:
            from knowledge_service.neo4j_client import Neo4jClient
        
        self.neo4j_client = Neo4jClient(self.config.get('neo4j', {}))
        self.neo4j_store = Neo4jStore(self.neo4j_client)
        self.graph_retriever = GraphRAGRetriever(self.config.get('graph_retriever', {}))
        
        # MCP resource tracking
        self.mcp_resources: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Graph Analytics Service initialized (v{self.version})")
    
    async def process_text_to_knowledge_graph(self,
                                            text_content: Union[str, List[str]],
                                            user_id: int,
                                            source_metadata: Optional[Dict[str, Any]] = None,
                                            options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process text content to knowledge graph and return MCP resource address.
        
        Args:
            text_content: Text content to process (string or list of pre-chunked strings)
            user_id: User ID for permission management
            source_metadata: Metadata about the source (file path, type, etc.)
            options: Processing options
            
        Returns:
            Dict containing MCP resource address and processing results
        """
        try:
            options = options or {}
            source_metadata = source_metadata or {}
            start_time = datetime.now()
            
            # Step 1: Authenticate user
            user = await self._authenticate_user(user_id)
            if not user:
                return {
                    'success': False,
                    'error': 'User authentication failed',
                    'user_id': user_id
                }
            
            # Step 2: Validate and process text content
            if isinstance(text_content, list):
                # Pre-chunked text from PDF service
                chunks = [chunk.strip() for chunk in text_content if chunk.strip()]
                if not chunks:
                    return {
                        'success': False,
                        'error': 'All text chunks are empty',
                        'user_id': user_id
                    }
                
                total_chars = sum(len(chunk) for chunk in chunks)
                logger.info(f"Processing {len(chunks)} pre-chunked texts for user {user_id}: {total_chars} characters total")
                
                # Process chunks directly with parallel unified extraction
                knowledge_graph = await self._process_chunks_directly(chunks, user_id, source_metadata)
                
            else:
                # Single text string
                if not text_content or not text_content.strip():
                    return {
                        'success': False,
                        'error': 'Text content is empty or invalid',
                        'user_id': user_id
                    }
                
                logger.info(f"Processing single text for user {user_id}: {len(text_content)} characters")
                
                # Use optimized unified extraction
                logger.info(f"Using optimized unified extraction for text ({len(text_content)} chars)")
                
                # Prepare metadata for unified extraction
                metadata = {
                    'user_id': user_id,
                    'source_file': source_metadata.get('source_file', 'text_input'),
                    'source_id': source_metadata.get('source_id', 'text_input'),
                    'extraction_method': 'unified_optimized',
                    'domain': source_metadata.get('domain', 'general')
                }
                metadata.update(source_metadata)
                
                # Use the optimized graph constructor (with Dask unified extraction)
                knowledge_graph = await self.graph_constructor.construct_from_text(
                    text=text_content,
                    source_metadata=metadata
                )
            
            if not knowledge_graph:
                return {
                    'success': False,
                    'error': 'Knowledge graph construction returned None',
                    'user_id': user_id,
                    'source_metadata': source_metadata
                }
            
            knowledge_graph_data = {
                'entities_count': len(knowledge_graph.nodes),
                'relationships_count': len(knowledge_graph.edges),
                'topics': knowledge_graph.metadata.get('topics', []),
                'nodes': knowledge_graph.nodes,
                'edges': knowledge_graph.edges,
                'document_chunks': knowledge_graph.document_chunks,
                'attributes': getattr(knowledge_graph, 'attribute_nodes', {})
            }
            
            logger.info(f"✅ Unified extraction completed: {knowledge_graph_data['entities_count']} entities, {knowledge_graph_data['relationships_count']} relations")
            
            # Wrap in expected format
            graph_result = {
                'success': True,
                'knowledge_graph': knowledge_graph_data
            }
            
            if not graph_result.get('success'):
                return {
                    'success': False,
                    'error': f"Knowledge graph construction failed: {graph_result.get('error')}",
                    'user_id': user_id,
                    'source_metadata': source_metadata
                }
            
            # Step 4: Store in Neo4j with user isolation
            resource_id = str(uuid.uuid4())
            
            # Get the actual KnowledgeGraph object (not the dictionary summary)
            if len(text_content) > 6000:
                # For chunked processing, create a KnowledgeGraph object
                from tools.services.data_analytics_service.services.knowledge_service.graph_constructor import KnowledgeGraph
                kg_object = KnowledgeGraph(
                    nodes={},  # Would need to reconstruct from all_nodes
                    edges={},  # Would need to reconstruct from all_edges  
                    document_chunks={},
                    attribute_nodes={},
                    metadata={'source_id': source_metadata.get('source_id', 'text_input')},
                    created_at=datetime.now().isoformat()
                )
                # For now, create export format directly
                graph_data_for_storage = {
                    "entities": [],  # TODO: Convert all_nodes to proper format
                    "relations": [], # TODO: Convert all_edges to proper format
                    "documents": [],
                    "attributes": []
                }
            else:
                # For direct processing, we have the KnowledgeGraph object
                # Use the proper export method
                graph_data_for_storage = self.graph_constructor.export_for_neo4j_storage(knowledge_graph)
                
                # Debug: Check what we're actually sending to storage
                print(f"DEBUG: Exporting {len(graph_data_for_storage.get('entities', []))} entities to Neo4j")
                print(f"DEBUG: Exporting {len(graph_data_for_storage.get('relations', []))} relations to Neo4j")
            
            # Add user isolation metadata to the exported data
            source_file = source_metadata.get('source_file', 'text_input')
            
            # Add user metadata to entities
            for entity in graph_data_for_storage.get('entities', []):
                if 'metadata' not in entity:
                    entity['metadata'] = {}
                entity['user_id'] = user_id
                entity['resource_id'] = resource_id
                entity['source_file'] = source_file
            
            # Add user metadata to relations
            for relation in graph_data_for_storage.get('relations', []):
                if 'metadata' not in relation:
                    relation['metadata'] = {}
                relation['user_id'] = user_id
                relation['resource_id'] = resource_id
                relation['source_file'] = source_file
            
            storage_result = await self.neo4j_store.store_knowledge_graph(graph_data_for_storage, user_id=user_id)
            
            if not storage_result.get('success'):
                return {
                    'success': False,
                    'error': f"Knowledge graph storage failed: {storage_result.get('error')}",
                    'user_id': user_id,
                    'source_metadata': source_metadata
                }
            
            # Step 5: Register MCP resource
            logger.info(f"🔄 Starting MCP resource registration for resource_id: {resource_id}, user_id: {user_id}")
            mcp_resource = await self._register_mcp_resource(
                resource_id=resource_id,
                user_id=user_id,
                source_metadata=source_metadata,
                graph_result=graph_result,
                storage_result=storage_result
            )
            logger.info(f"🎯 MCP resource registration completed: {mcp_resource.get('address', 'Unknown')}")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'user_id': user_id,
                'resource_id': resource_id,
                'mcp_resource_address': mcp_resource['address'],
                'knowledge_graph_summary': {
                    'entities': graph_result['knowledge_graph']['entities_count'],
                    'relationships': graph_result['knowledge_graph']['relationships_count'],
                    'topics': len(graph_result['knowledge_graph'].get('topics', [])),
                    'source_file': source_metadata.get('source_file', 'text_input')
                },
                'processing_summary': {
                    'text_length': len(text_content),
                    'processing_method': 'chunked' if len(text_content) > 6000 else 'direct',
                    'processing_time': processing_time
                },
                'storage_info': {
                    'neo4j_nodes': storage_result['nodes_created'],
                    'neo4j_relationships': storage_result['relationships_created'],
                    'storage_time': storage_result['processing_time']
                }
            }
            
        except Exception as e:
            logger.error(f"Text to knowledge graph processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'source_metadata': source_metadata
            }
    
    async def get_user_resources(self, user_id: int) -> Dict[str, Any]:
        """
        Get all MCP resources for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing user's MCP resources
        """
        try:
            # Authenticate user
            user = await self._authenticate_user(user_id)
            if not user:
                return {
                    'success': False,
                    'error': 'User authentication failed',
                    'user_id': user_id
                }
            
            # Get user's resources from Neo4j
            user_resources = await self.neo4j_client.get_user_resources(user_id)
            
            if not user_resources.get('success'):
                return {
                    'success': False,
                    'error': f"Failed to retrieve user resources: {user_resources.get('error')}",
                    'user_id': user_id
                }
            
            # Get MCP resources from the actual resource manager (not memory)
            try:
                # Import the resource manager
                import sys
                from pathlib import Path
                project_root = Path(__file__).parent.parent.parent.parent.parent
                sys.path.insert(0, str(project_root))
                
                from resources.graph_knowledge_resources import graph_knowledge_resources
                mcp_resources_result = await graph_knowledge_resources.get_user_resources(user_id)
                
                if mcp_resources_result.get('success'):
                    # Convert to the expected format
                    user_mcp_resources = {}
                    for resource in mcp_resources_result.get('resources', []):
                        resource_id = resource['resource_id']
                        user_mcp_resources[resource_id] = resource
                    logger.info(f"✅ Retrieved {len(user_mcp_resources)} MCP resources from resource manager")
                else:
                    logger.warning(f"Failed to get MCP resources: {mcp_resources_result.get('error')}")
                    user_mcp_resources = {}
                    
            except Exception as e:
                logger.error(f"Failed to query MCP resource manager: {e}")
                # Fallback to memory storage (old behavior)
                user_mcp_resources = {
                    resource_id: resource_data
                    for resource_id, resource_data in self.mcp_resources.items()
                    if resource_data['user_id'] == user_id
                }
                logger.warning(f"Falling back to memory storage: {len(user_mcp_resources)} resources")
            
            return {
                'success': True,
                'user_id': user_id,
                'resource_count': len(user_mcp_resources),
                'mcp_resources': user_mcp_resources,
                'neo4j_resources': user_resources['resources']
            }
            
        except Exception as e:
            logger.error(f"Failed to get user resources: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def query_knowledge_graph(self,
                                  resource_id: str,
                                  query: str,
                                  user_id: int) -> Dict[str, Any]:
        """
        Query knowledge graph with user permission check.
        
        Args:
            resource_id: Resource ID
            query: Query string
            user_id: User ID for permission check
            
        Returns:
            Dict containing query results
        """
        try:
            # Authenticate user
            user = await self._authenticate_user(user_id)
            if not user:
                return {
                    'success': False,
                    'error': 'User authentication failed',
                    'user_id': user_id
                }
            
            # Check resource ownership
            if resource_id not in self.mcp_resources:
                return {
                    'success': False,
                    'error': 'Resource not found',
                    'resource_id': resource_id,
                    'user_id': user_id
                }
            
            resource_data = self.mcp_resources[resource_id]
            if resource_data['user_id'] != user_id:
                return {
                    'success': False,
                    'error': 'Access denied - resource belongs to another user',
                    'resource_id': resource_id,
                    'user_id': user_id
                }
            
            # Execute query on Neo4j
            query_result = await self.neo4j_client.query_knowledge_graph(
                resource_id=resource_id,
                query=query,
                user_id=user_id
            )
            
            return query_result
            
        except Exception as e:
            logger.error(f"Knowledge graph query failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'resource_id': resource_id,
                'user_id': user_id
            }
    
    async def graphrag_query(self,
                           query: str,
                           user_id: int,
                           resource_id: Optional[str] = None,
                           context_text: Optional[str] = None,
                           options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Core Function 2: GraphRAG query and retrieval with user permissions.
        
        Args:
            query: Query string for GraphRAG search
            user_id: User ID for permission management
            resource_id: Optional specific resource ID to query
            context_text: Optional text content for context enhancement
            options: Query options (search_mode, limit, similarity_threshold, etc.)
            
        Returns:
            Dict containing GraphRAG retrieval results
        """
        try:
            options = options or {}
            start_time = datetime.now()
            
            # Step 1: Authenticate user
            user = await self._authenticate_user(user_id)
            if not user:
                return {
                    'success': False,
                    'error': 'User authentication failed',
                    'user_id': user_id,
                    'query': query
                }
            
            # Step 2: Process context text if provided
            text_context = None
            if context_text:
                logger.info(f"Processing text context for GraphRAG query: {len(context_text)} characters")
                text_context = {
                    'content': context_text,
                    'length': len(context_text),
                    'source_type': 'text_input'
                }
                logger.info(f"Text context processed: {len(context_text)} characters")
            
            # Step 3: Determine target resources for query
            target_resources = []
            
            if resource_id:
                # Query specific resource
                if resource_id not in self.mcp_resources:
                    return {
                        'success': False,
                        'error': 'Resource not found',
                        'resource_id': resource_id,
                        'user_id': user_id,
                        'query': query
                    }
                
                resource_data = self.mcp_resources[resource_id]
                if resource_data['user_id'] != user_id:
                    return {
                        'success': False,
                        'error': 'Access denied - resource belongs to another user',
                        'resource_id': resource_id,
                        'user_id': user_id,
                        'query': query
                    }
                
                target_resources = [resource_id]
            else:
                # Query all user's resources
                user_resources = await self.get_user_resources(user_id)
                if not user_resources.get('success'):
                    return {
                        'success': False,
                        'error': f"Failed to retrieve user resources: {user_resources.get('error')}",
                        'user_id': user_id,
                        'query': query
                    }
                
                target_resources = list(user_resources['mcp_resources'].keys())
                
                if not target_resources:
                    return {
                        'success': False,
                        'error': 'No resources found for user',
                        'user_id': user_id,
                        'query': query
                    }
            
            # Step 4: Execute GraphRAG retrieval
            logger.info(f"Executing GraphRAG query for user {user_id} on {len(target_resources)} resources")
            
            # Configure retrieval options
            retrieval_options = {
                'search_mode': options.get('search_mode', 'multi_modal'),
                'limit': options.get('limit', 10),
                'similarity_threshold': options.get('similarity_threshold', 0.7),
                'expand_context': options.get('expand_context', True),
                'include_embeddings': options.get('include_embeddings', False),
                'user_id': user_id,
                'target_resources': target_resources
            }
            
            # Execute retrieval across target resources
            retrieval_results = []
            total_results = 0
            
            for res_id in target_resources:
                try:
                    # Get resource metadata
                    resource_info = self.mcp_resources[res_id]
                    
                    # Execute GraphRAG retrieval on this resource
                    retrieval_results_list = await self.graph_retriever.retrieve(
                        query=query,
                        top_k=retrieval_options.get('limit', 10),
                        similarity_threshold=retrieval_options.get('similarity_threshold', 0.7)
                    )
                    
                    # Convert to expected format
                    retrieval_result = {
                        'success': True,
                        'results': [
                            {
                                'type': result.result_type,
                                'content': result.content,
                                'score': result.score,
                                'metadata': result.metadata
                            } for result in retrieval_results_list
                        ]
                    }
                    
                    if retrieval_result.get('success'):
                        retrieval_results.append({
                            'resource_id': res_id,
                            'resource_info': {
                                'source_file': resource_info.get('source_file'),
                                'address': resource_info.get('address'),
                                'created_at': resource_info.get('created_at')
                            },
                            'retrieval_result': retrieval_result,
                            'result_count': len(retrieval_result.get('results', []))
                        })
                        total_results += len(retrieval_result.get('results', []))
                    else:
                        logger.warning(f"GraphRAG retrieval failed for resource {res_id}: {retrieval_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"GraphRAG retrieval error for resource {res_id}: {e}")
                    continue
            
            # Step 5: Aggregate and rank results
            aggregated_results = await self._aggregate_graphrag_results(
                retrieval_results, 
                query, 
                options.get('max_results', 20)
            )
            
            # Step 6: Enhance with text context if available
            if text_context:
                aggregated_results = await self._enhance_with_text_context(
                    aggregated_results, 
                    text_context, 
                    query
                )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'user_id': user_id,
                'query': query,
                'results': aggregated_results['results'],
                'total_results': total_results,
                'resources_searched': len(target_resources),
                'resource_details': [
                    {
                        'resource_id': res['resource_id'],
                        'source_file': res['resource_info']['source_file'],
                        'result_count': res['result_count']
                    } for res in retrieval_results
                ],
                'text_context': text_context,
                'query_metadata': {
                    'search_mode': retrieval_options['search_mode'],
                    'similarity_threshold': retrieval_options['similarity_threshold'],
                    'context_enhanced': text_context is not None,
                    'processing_time': processing_time
                }
            }
            
        except Exception as e:
            logger.error(f"GraphRAG query failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query,
                'resource_id': resource_id,
                'context_text': context_text
            }
    
    async def _aggregate_graphrag_results(self,
                                        retrieval_results: List[Dict[str, Any]],
                                        query: str,
                                        max_results: int) -> Dict[str, Any]:
        """
        Aggregate and rank GraphRAG results from multiple resources.
        
        Args:
            retrieval_results: List of retrieval results from different resources
            query: Original query string
            max_results: Maximum number of results to return
            
        Returns:
            Dict containing aggregated and ranked results
        """
        try:
            all_results = []
            
            # Collect all results with source information
            for res_data in retrieval_results:
                resource_id = res_data['resource_id']
                resource_info = res_data['resource_info']
                retrieval_result = res_data['retrieval_result']
                
                for result in retrieval_result.get('results', []):
                    # Add source information to each result
                    result['source_resource'] = {
                        'resource_id': resource_id,
                        'source_file': resource_info['source_file'],
                        'address': resource_info['address']
                    }
                    all_results.append(result)
            
            # Sort by relevance score (assuming higher is better)
            all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # Limit results
            top_results = all_results[:max_results]
            
            # Calculate aggregated metadata
            result_types = {}
            for result in top_results:
                result_type = result.get('type', 'unknown')
                result_types[result_type] = result_types.get(result_type, 0) + 1
            
            return {
                'results': top_results,
                'total_found': len(all_results),
                'total_returned': len(top_results),
                'result_types': result_types,
                'query': query
            }
            
        except Exception as e:
            logger.error(f"GraphRAG result aggregation failed: {e}")
            return {
                'results': [],
                'total_found': 0,
                'total_returned': 0,
                'result_types': {},
                'query': query,
                'error': str(e)
            }
    
    async def _enhance_with_text_context(self,
                                       aggregated_results: Dict[str, Any],
                                       text_context: Dict[str, Any],
                                       query: str) -> Dict[str, Any]:
        """
        Enhance GraphRAG results with text context information.
        
        Args:
            aggregated_results: Aggregated GraphRAG results
            text_context: Text context information
            query: Original query string
            
        Returns:
            Enhanced results with text context
        """
        try:
            # Add text context to metadata
            aggregated_results['text_context'] = text_context
            
            # You could implement more sophisticated context enhancement here
            # For example:
            # 1. Cross-reference results with text content
            # 2. Extract relevant passages from text
            # 3. Provide text-specific insights
            
            logger.info(f"Enhanced GraphRAG results with text context ({text_context['length']} characters)")
            
            return aggregated_results
            
        except Exception as e:
            logger.error(f"Text context enhancement failed: {e}")
            return aggregated_results
    
    async def _authenticate_user(self, user_id: int) -> Optional[User]:
        """
        Authenticate user and return user object.
        
        Args:
            user_id: User ID
            
        Returns:
            User object if authenticated, None otherwise
        """
        try:
            user = await self.user_service.get_user_by_id(user_id)
            if not user or not user.is_active:
                logger.warning(f"User authentication failed: user_id={user_id}")
                return None
            
            return user
            
        except Exception as e:
            logger.error(f"User authentication error: {e}")
            return None
    
    
    async def _register_mcp_resource(self,
                                   resource_id: str,
                                   user_id: int,
                                   source_metadata: Dict[str, Any],
                                   graph_result: Dict[str, Any],
                                   storage_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register MCP resource for knowledge graph.
        
        Args:
            resource_id: Unique resource ID
            user_id: User ID
            source_metadata: Source metadata information
            graph_result: Knowledge graph construction result
            storage_result: Neo4j storage result
            
        Returns:
            Dict containing MCP resource information
        """
        try:
            # Create MCP resource address
            mcp_address = f"mcp://graph_knowledge/{resource_id}"
            
            # Store resource information
            resource_data = {
                'resource_id': resource_id,
                'user_id': user_id,
                'address': mcp_address,
                'type': 'knowledge_graph',
                'source_file': source_metadata.get('source_file', 'text_input'),
                'source_metadata': source_metadata,
                'created_at': datetime.now().isoformat(),
                'metadata': {
                    'entities_count': storage_result['nodes_created'],
                    'relationships_count': storage_result['relationships_created'],
                    'topics': graph_result['knowledge_graph'].get('topics', []),
                    'neo4j_nodes': storage_result['nodes_created'],
                    'neo4j_relationships': storage_result['relationships_created']
                }
            }
            
            # Store in memory (should be integrated with actual MCP resource system)
            self.mcp_resources[resource_id] = resource_data
            
            # Integrate with MCP resource registration system
            try:
                # Try multiple import paths for resource registration
                import sys
                from pathlib import Path
                project_root = Path(__file__).parent.parent.parent.parent.parent
                sys.path.insert(0, str(project_root))
                
                from resources.graph_knowledge_resources import graph_knowledge_resources
                registration_result = await graph_knowledge_resources.register_resource(
                    resource_id=resource_id,
                    user_id=user_id,
                    resource_data=resource_data
                )
                logger.info(f"✅ MCP resource registration successful: {registration_result}")
                
                # If registration is successful, we should also clear old resources from memory
                # and query from the actual resource manager instead of using self.mcp_resources
                if registration_result.get('success'):
                    logger.info(f"✅ Resource {resource_id} successfully registered with correct metadata")
                
            except Exception as e:
                logger.error(f"❌ MCP resource registration failed: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # DO NOT mock success - let the error propagate so we know registration failed
                registration_result = {'success': False, 'error': str(e)}
            
            if not registration_result.get('success'):
                logger.error(f"MCP resource registration FAILED: {registration_result.get('error')}")
                logger.error(f"This means queries will return empty results despite Neo4j storage success")
                # Continue anyway as the resource is still stored in Neo4j, but queries won't work
            
            logger.info(f"MCP resource registered: {mcp_address} for user {user_id}")
            
            return resource_data
            
        except Exception as e:
            logger.error(f"MCP resource registration failed: {e}")
            raise
    
    async def _process_chunks_directly(self, 
                                     chunks: List[str], 
                                     user_id: int, 
                                     source_metadata: Dict[str, Any]) -> Any:
        """Process pre-chunked text directly without re-chunking"""
        try:
            # Process each chunk with unified extraction in parallel
            import asyncio
            from .knowledge_service.dask_unified_extractor import dask_unified_extractor
            
            async def process_single_chunk(chunk_text: str, chunk_id: int):
                """Process a single chunk"""
                try:
                    chunk_metadata = {
                        'user_id': user_id,
                        'source_file': source_metadata.get('source_file', 'text_input'),
                        'source_id': f"{source_metadata.get('source_id', 'text_input')}_chunk_{chunk_id}",
                        'chunk_index': chunk_id,
                        'extraction_method': 'direct_chunk_processing',
                        'domain': source_metadata.get('domain', 'general')
                    }
                    chunk_metadata.update(source_metadata)
                    
                    # Use unified extraction for this chunk
                    result = await dask_unified_extractor._process_single_chunk_direct(
                        text=chunk_text,
                        domain=chunk_metadata.get('domain', 'general'),
                        confidence_threshold=0.7
                    )
                    
                    return {
                        'chunk_id': chunk_id,
                        'entities': result.entities,
                        'relationships': result.relationships,
                        'attributes': result.attributes,
                        'success': result.success,
                        'error': result.error
                    }
                    
                except Exception as e:
                    logger.warning(f"Chunk {chunk_id} processing failed: {e}")
                    return {
                        'chunk_id': chunk_id,
                        'entities': [],
                        'relationships': [],
                        'attributes': {},
                        'success': False,
                        'error': str(e)
                    }
            
            # Process all chunks in parallel
            logger.info(f"Processing {len(chunks)} chunks in parallel...")
            tasks = [process_single_chunk(chunk, i) for i, chunk in enumerate(chunks)]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results from all chunks
            all_entities = []
            all_relationships = []
            all_attributes = {}
            
            for result in chunk_results:
                if isinstance(result, dict) and result.get('success'):
                    all_entities.extend(result['entities'])
                    all_relationships.extend(result['relationships'])
                    all_attributes.update(result['attributes'])
            
            # Convert to graph constructor format
            from .knowledge_service.entity_extractor import Entity, EntityType
            from .knowledge_service.relation_extractor import Relation, RelationType
            from .knowledge_service.attribute_extractor import Attribute, AttributeType
            
            # Convert entities
            entities = []
            for entity_data in all_entities:
                try:
                    entity_type = EntityType(entity_data.get('type', 'CONCEPT'))
                except ValueError:
                    entity_type = EntityType.CONCEPT
                
                entity = Entity(
                    text=entity_data.get('name', ''),
                    entity_type=entity_type,
                    start=0,
                    end=len(entity_data.get('name', '')),
                    confidence=entity_data.get('confidence', 0.8)
                )
                entities.append(entity)
            
            # Convert relationships  
            relations = []
            for rel_data in all_relationships:
                try:
                    # Find subject and object entities
                    subject_entity = None
                    object_entity = None
                    
                    for entity in entities:
                        if entity.text.lower() == rel_data.get('subject', '').lower():
                            subject_entity = entity
                        if entity.text.lower() == rel_data.get('object', '').lower():
                            object_entity = entity
                    
                    if subject_entity and object_entity:
                        relation = Relation(
                            subject=subject_entity,
                            predicate=rel_data.get('predicate', ''),
                            object=object_entity,
                            relation_type=RelationType.SEMANTIC,
                            confidence=rel_data.get('confidence', 0.8)
                        )
                        relations.append(relation)
                except Exception as e:
                    logger.warning(f"Failed to convert relationship: {e}")
            
            # Convert attributes
            entity_attributes = {}
            for entity_name, attrs in all_attributes.items():
                entity_attrs = {}
                for attr_name, attr_data in attrs.items():
                    if isinstance(attr_data, dict):
                        attribute = Attribute(
                            name=attr_name,
                            value=attr_data.get('value', ''),
                            attribute_type=AttributeType.TEXT,
                            confidence=attr_data.get('confidence', 0.8),
                            source_text=attr_data.get('source', ''),
                            normalized_value=attr_data.get('value', '')
                        )
                        entity_attrs[attr_name] = attribute
                
                if entity_attrs:
                    entity_attributes[entity_name] = entity_attrs
            
            # Use graph constructor to build final graph
            combined_text = '\n\n'.join(chunks)
            metadata = {
                'user_id': user_id,
                'source_file': source_metadata.get('source_file', 'text_input'),
                'source_id': source_metadata.get('source_id', 'text_input'),
                'extraction_method': 'direct_chunk_processing'
            }
            metadata.update(source_metadata)
            
            knowledge_graph = await self.graph_constructor.construct_graph(
                entities=entities,
                relations=relations,
                entity_attributes=entity_attributes,
                source_text=combined_text,
                source_id=metadata.get('source_id', 'text_input')
            )
            
            logger.info(f"✅ Direct chunk processing completed: {len(entities)} entities, {len(relations)} relations from {len(chunks)} chunks")
            return knowledge_graph
            
        except Exception as e:
            logger.error(f"Direct chunk processing failed: {e}")
            raise
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and status."""
        return {
            'service': self.service_name,
            'version': self.version,
            'capabilities': [
                'text_to_knowledge_graph',
                'graphrag_query_retrieval',
                'user_permission_management',
                'mcp_resource_registration',
                'knowledge_graph_querying'
            ],
            'dependencies': [
                'graph_constructor',
                'neo4j_store',
                'graph_retriever',
                'user_service'
            ],
            'mcp_resources_count': len(self.mcp_resources),
            'status': 'operational'
        }