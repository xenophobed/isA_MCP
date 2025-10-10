#!/usr/bin/env python3
"""
Graph Knowledge Resources - MCP Resource Registration

Handles MCP resource registration and management for knowledge graphs.
Provides resource discovery and access control for graph analytics service.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class GraphKnowledgeResources:
    """
    MCP Resource Manager for Knowledge Graph resources.
    
    Features:
    - Resource registration and discovery
    - User permission management
    - Resource metadata management
    - Access control for graph resources
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Graph Knowledge Resources.
        
        Args:
            config: Resource manager configuration
        """
        self.config = config or {}
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.user_resource_map: Dict[int, List[str]] = {}
        
        logger.info("Graph Knowledge Resources initialized")
    
    async def register_resource(self,
                              resource_id: str,
                              user_id: int,
                              resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new knowledge graph resource with Neo4j synchronization.
        
        Args:
            resource_id: Unique resource identifier
            user_id: User ID who owns the resource
            resource_data: Resource metadata and information
            
        Returns:
            Dict containing registration result
        """
        try:
            # Extract metadata with proper Neo4j data mapping
            metadata = resource_data.get('metadata', {})
            
            # Ensure we have actual storage numbers (not extraction estimates)
            entities_count = metadata.get('neo4j_nodes', metadata.get('entities_count', 0))
            relationships_count = metadata.get('neo4j_relationships', metadata.get('relationships_count', 0))
            
            # Create MCP resource entry with synchronized data
            mcp_resource = {
                'resource_id': resource_id,
                'user_id': user_id,
                'type': 'knowledge_graph',
                'address': f"mcp://graph_knowledge/{resource_id}",
                'registered_at': datetime.now().isoformat(),
                'metadata': {
                    'entities_count': entities_count,
                    'relationships_count': relationships_count,
                    'topics': metadata.get('topics', []),
                    'neo4j_nodes': entities_count,
                    'neo4j_relationships': relationships_count,
                    'source_file': resource_data.get('source_file'),
                    'source_metadata': resource_data.get('source_metadata', {})
                },
                'source_file': resource_data.get('source_file'),
                'source_metadata': resource_data.get('source_metadata', {}),
                'access_permissions': {
                    'owner': user_id,
                    'read_access': [user_id],
                    'write_access': [user_id]
                },
                'capabilities': ['query', 'graphrag', 'search', 'retrieve']
            }
            
            # Store resource
            self.resources[resource_id] = mcp_resource
            
            # Update user resource mapping
            if user_id not in self.user_resource_map:
                self.user_resource_map[user_id] = []
            self.user_resource_map[user_id].append(resource_id)
            
            logger.info(f"Resource registered: {resource_id} for user {user_id}")
            
            return {
                'success': True,
                'resource_id': resource_id,
                'mcp_address': mcp_resource['address'],
                'user_id': user_id
            }
            
        except Exception as e:
            logger.error(f"Resource registration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'resource_id': resource_id,
                'user_id': user_id
            }
    
    async def get_resource(self,
                          resource_id: str,
                          user_id: int) -> Dict[str, Any]:
        """
        Get resource information with permission check.
        
        Args:
            resource_id: Resource identifier
            user_id: User requesting the resource
            
        Returns:
            Dict containing resource information
        """
        try:
            if resource_id not in self.resources:
                return {
                    'success': False,
                    'error': 'Resource not found',
                    'resource_id': resource_id
                }
            
            resource = self.resources[resource_id]
            
            # Check read permissions
            if user_id not in resource['access_permissions']['read_access']:
                return {
                    'success': False,
                    'error': 'Access denied',
                    'resource_id': resource_id,
                    'user_id': user_id
                }
            
            return {
                'success': True,
                'resource': resource,
                'user_id': user_id
            }
            
        except Exception as e:
            logger.error(f"Get resource failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'resource_id': resource_id,
                'user_id': user_id
            }
    
    async def get_user_resources(self, user_id: int) -> Dict[str, Any]:
        """
        Get all resources for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict containing user's resources
        """
        try:
            user_resources = []
            
            if user_id in self.user_resource_map:
                for resource_id in self.user_resource_map[user_id]:
                    if resource_id in self.resources:
                        user_resources.append(self.resources[resource_id])
            
            return {
                'success': True,
                'user_id': user_id,
                'resource_count': len(user_resources),
                'resources': user_resources
            }
            
        except Exception as e:
            logger.error(f"Get user resources failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def delete_resource(self,
                            resource_id: str,
                            user_id: int) -> Dict[str, Any]:
        """
        Delete a resource with permission check.
        
        Args:
            resource_id: Resource identifier
            user_id: User requesting deletion
            
        Returns:
            Dict containing deletion result
        """
        try:
            if resource_id not in self.resources:
                return {
                    'success': False,
                    'error': 'Resource not found',
                    'resource_id': resource_id
                }
            
            resource = self.resources[resource_id]
            
            # Check write permissions
            if user_id not in resource['access_permissions']['write_access']:
                return {
                    'success': False,
                    'error': 'Access denied',
                    'resource_id': resource_id,
                    'user_id': user_id
                }
            
            # Remove from resources
            del self.resources[resource_id]
            
            # Remove from user mapping
            if user_id in self.user_resource_map:
                self.user_resource_map[user_id].remove(resource_id)
            
            logger.info(f"Resource deleted: {resource_id} by user {user_id}")
            
            return {
                'success': True,
                'resource_id': resource_id,
                'user_id': user_id
            }
            
        except Exception as e:
            logger.error(f"Delete resource failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'resource_id': resource_id,
                'user_id': user_id
            }
    
    async def update_resource_metadata(self,
                                     resource_id: str,
                                     user_id: int,
                                     metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update resource metadata with permission check.
        
        Args:
            resource_id: Resource identifier
            user_id: User requesting update
            metadata: New metadata to update
            
        Returns:
            Dict containing update result
        """
        try:
            if resource_id not in self.resources:
                return {
                    'success': False,
                    'error': 'Resource not found',
                    'resource_id': resource_id
                }
            
            resource = self.resources[resource_id]
            
            # Check write permissions
            if user_id not in resource['access_permissions']['write_access']:
                return {
                    'success': False,
                    'error': 'Access denied',
                    'resource_id': resource_id,
                    'user_id': user_id
                }
            
            # Update metadata
            resource['metadata'].update(metadata)
            resource['updated_at'] = datetime.now().isoformat()
            
            logger.info(f"Resource metadata updated: {resource_id} by user {user_id}")
            
            return {
                'success': True,
                'resource_id': resource_id,
                'user_id': user_id,
                'updated_metadata': resource['metadata']
            }
            
        except Exception as e:
            logger.error(f"Update resource metadata failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'resource_id': resource_id,
                'user_id': user_id
            }
    
    async def list_all_resources(self, user_id: int) -> Dict[str, Any]:
        """
        List all resources accessible to a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict containing accessible resources
        """
        try:
            accessible_resources = []
            
            for resource_id, resource in self.resources.items():
                # Check if user has read access
                if user_id in resource['access_permissions']['read_access']:
                    accessible_resources.append({
                        'resource_id': resource_id,
                        'address': resource['address'],
                        'type': resource['type'],
                        'source_file': resource.get('source_file'),
                        'registered_at': resource['registered_at'],
                        'metadata': resource['metadata'],
                        'is_owner': resource['access_permissions']['owner'] == user_id
                    })
            
            return {
                'success': True,
                'user_id': user_id,
                'accessible_resources': accessible_resources,
                'total_count': len(accessible_resources)
            }
            
        except Exception as e:
            logger.error(f"List all resources failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def search_resources(self,
                             user_id: int,
                             query: str,
                             resource_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Search resources by query and type.
        
        Args:
            user_id: User identifier
            query: Search query
            resource_type: Optional resource type filter
            
        Returns:
            Dict containing search results
        """
        try:
            matching_resources = []
            
            for resource_id, resource in self.resources.items():
                # Check if user has read access
                if user_id not in resource['access_permissions']['read_access']:
                    continue
                
                # Type filter
                if resource_type and resource['type'] != resource_type:
                    continue
                
                # Search in resource metadata
                search_text = json.dumps(resource, ensure_ascii=False).lower()
                if query.lower() in search_text:
                    matching_resources.append({
                        'resource_id': resource_id,
                        'address': resource['address'],
                        'type': resource['type'],
                        'source_file': resource.get('source_file'),
                        'registered_at': resource['registered_at'],
                        'metadata': resource['metadata'],
                        'is_owner': resource['access_permissions']['owner'] == user_id
                    })
            
            return {
                'success': True,
                'user_id': user_id,
                'query': query,
                'resource_type': resource_type,
                'matching_resources': matching_resources,
                'result_count': len(matching_resources)
            }
            
        except Exception as e:
            logger.error(f"Search resources failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query
            }
    
    async def sync_with_neo4j(self, user_id: int) -> Dict[str, Any]:
        """
        Synchronize MCP resources with actual Neo4j data.
        
        Args:
            user_id: User ID to sync resources for
            
        Returns:
            Dict containing sync results
        """
        try:
            # Try to import Neo4j client for verification
            try:
                import sys
                from pathlib import Path
                project_root = Path(__file__).parent.parent
                sys.path.insert(0, str(project_root))
                
                from tools.services.data_analytics_service.services.knowledge_service.neo4j_client import Neo4jClient
                from core.config import get_settings
                
                settings = get_settings()
                neo4j_client = Neo4jClient({
                    'uri': settings.graph_analytics.neo4j_uri or 'bolt://localhost:7687',
                    'username': settings.graph_analytics.neo4j_username or 'neo4j',
                    'password': settings.graph_analytics.neo4j_password or 'password',
                    'database': settings.graph_analytics.neo4j_database or 'neo4j'
                })
                
                # Get actual Neo4j data for user
                neo4j_result = await neo4j_client.get_user_resources(user_id)
                
                if neo4j_result.get('success'):
                    neo4j_entities = neo4j_result['resources'].get('entities', 0)
                    
                    # Update MCP resource metadata to match Neo4j reality
                    updated_resources = 0
                    for resource_id in self.user_resource_map.get(user_id, []):
                        if resource_id in self.resources:
                            resource = self.resources[resource_id]
                            old_count = resource['metadata'].get('entities_count', 0)
                            
                            # Update with actual Neo4j data
                            resource['metadata']['entities_count'] = neo4j_entities
                            resource['metadata']['neo4j_nodes'] = neo4j_entities
                            resource['updated_at'] = datetime.now().isoformat()
                            
                            if old_count != neo4j_entities:
                                updated_resources += 1
                                logger.info(f"Updated resource {resource_id}: {old_count} -> {neo4j_entities} entities")
                    
                    return {
                        'success': True,
                        'user_id': user_id,
                        'neo4j_entities': neo4j_entities,
                        'resources_updated': updated_resources,
                        'sync_timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Neo4j sync failed: {neo4j_result.get('error')}",
                        'user_id': user_id
                    }
                    
            except Exception as neo4j_error:
                logger.warning(f"Neo4j sync not available: {neo4j_error}")
                return {
                    'success': False,
                    'error': f"Neo4j connection failed: {neo4j_error}",
                    'user_id': user_id
                }
                
        except Exception as e:
            logger.error(f"Resource sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get resource statistics."""
        try:
            stats = {
                'total_resources': len(self.resources),
                'total_users': len(self.user_resource_map),
                'resource_types': {},
                'resources_per_user': {},
                'total_entities': 0,
                'total_relationships': 0
            }
            
            # Count resource types and aggregate data
            for resource in self.resources.values():
                resource_type = resource['type']
                stats['resource_types'][resource_type] = stats['resource_types'].get(resource_type, 0) + 1
                
                # Aggregate knowledge graph data
                metadata = resource.get('metadata', {})
                stats['total_entities'] += metadata.get('entities_count', 0)
                stats['total_relationships'] += metadata.get('relationships_count', 0)
            
            # Count resources per user
            for user_id, resources in self.user_resource_map.items():
                stats['resources_per_user'][str(user_id)] = len(resources)
            
            return stats
            
        except Exception as e:
            logger.error(f"Get resource stats failed: {e}")
            return {'error': str(e)}

# Global instance
graph_knowledge_resources = GraphKnowledgeResources()