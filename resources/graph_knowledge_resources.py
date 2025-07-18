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
        Register a new knowledge graph resource.
        
        Args:
            resource_id: Unique resource identifier
            user_id: User ID who owns the resource
            resource_data: Resource metadata and information
            
        Returns:
            Dict containing registration result
        """
        try:
            # Create MCP resource entry
            mcp_resource = {
                'resource_id': resource_id,
                'user_id': user_id,
                'type': 'knowledge_graph',
                'address': f"mcp://graph_knowledge/{resource_id}",
                'registered_at': datetime.now().isoformat(),
                'metadata': resource_data.get('metadata', {}),
                'source_file': resource_data.get('source_file'),
                'access_permissions': {
                    'owner': user_id,
                    'read_access': [user_id],
                    'write_access': [user_id]
                }
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
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get resource statistics."""
        try:
            stats = {
                'total_resources': len(self.resources),
                'total_users': len(self.user_resource_map),
                'resource_types': {},
                'resources_per_user': {}
            }
            
            # Count resource types
            for resource in self.resources.values():
                resource_type = resource['type']
                stats['resource_types'][resource_type] = stats['resource_types'].get(resource_type, 0) + 1
            
            # Count resources per user
            for user_id, resources in self.user_resource_map.items():
                stats['resources_per_user'][str(user_id)] = len(resources)
            
            return stats
            
        except Exception as e:
            logger.error(f"Get resource stats failed: {e}")
            return {'error': str(e)}

# Global instance
graph_knowledge_resources = GraphKnowledgeResources()