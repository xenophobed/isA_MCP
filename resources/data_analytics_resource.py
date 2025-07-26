#!/usr/bin/env python3
"""
Data Analytics Resources - MCP Resource Registration

Handles MCP resource registration and management for data analytics service.
Provides resource discovery and access control for analytical data processing.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import uuid

logger = logging.getLogger(__name__)

class DataAnalyticsResources:
    """
    MCP Resource Manager for Data Analytics resources.
    
    Features:
    - Analytics resource registration and discovery
    - User permission management  
    - Data source metadata management
    - Access control for analytical resources
    - Query history and result management
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Data Analytics Resources.
        
        Args:
            config: Resource manager configuration
        """
        self.config = config or {}
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.user_resource_map: Dict[int, List[str]] = {}
        self.data_source_map: Dict[str, List[str]] = {}  # data_source -> resource_ids
        
        logger.info("Data Analytics Resources initialized")
    
    async def register_analytics_resource(self,
                                        resource_id: str,
                                        user_id: int,
                                        resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new data analytics resource with database synchronization.
        
        Args:
            resource_id: Unique resource identifier
            user_id: User ID who owns the resource
            resource_data: Resource metadata and information
            
        Returns:
            Dict containing registration result
        """
        try:
            # Extract metadata with proper database data mapping
            metadata = resource_data.get('metadata', {})
            
            # Determine resource type based on data
            resource_type = self._determine_resource_type(resource_data)
            
            # Create MCP resource entry with synchronized data
            mcp_resource = {
                'resource_id': resource_id,
                'user_id': user_id,
                'type': resource_type,
                'address': f"mcp://data_analytics/{resource_id}",
                'registered_at': datetime.now().isoformat(),
                'metadata': {
                    'source_path': resource_data.get('source_path'),
                    'database_type': metadata.get('database_type', 'sqlite'),
                    'sqlite_database_path': resource_data.get('sqlite_database_path'),
                    'pgvector_database': resource_data.get('pgvector_database'),
                    'tables_found': metadata.get('tables_found', 0),
                    'columns_found': metadata.get('columns_found', 0),
                    'business_entities': metadata.get('business_entities', 0),
                    'embeddings_stored': metadata.get('embeddings_stored', 0),
                    'processing_time_ms': resource_data.get('processing_time_ms', 0),
                    'cost_usd': resource_data.get('cost_usd', 0.0),
                    'search_ready': metadata.get('search_ready', False),
                    'source_metadata': resource_data.get('source_metadata', {})
                },
                'source_path': resource_data.get('source_path'),
                'source_metadata': resource_data.get('source_metadata', {}),
                'access_permissions': {
                    'owner': user_id,
                    'read_access': [user_id],
                    'write_access': [user_id]
                },
                'capabilities': self._get_resource_capabilities(resource_type)
            }
            
            # Store resource
            self.resources[resource_id] = mcp_resource
            
            # Update user resource mapping
            if user_id not in self.user_resource_map:
                self.user_resource_map[user_id] = []
            self.user_resource_map[user_id].append(resource_id)
            
            # Update data source mapping
            source_path = resource_data.get('source_path')
            if source_path:
                if source_path not in self.data_source_map:
                    self.data_source_map[source_path] = []
                self.data_source_map[source_path].append(resource_id)
            
            logger.info(f"Analytics resource registered: {resource_id} for user {user_id}")
            
            return {
                'success': True,
                'resource_id': resource_id,
                'mcp_address': mcp_resource['address'],
                'user_id': user_id,
                'type': resource_type
            }
            
        except Exception as e:
            logger.error(f"Analytics resource registration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'resource_id': resource_id,
                'user_id': user_id
            }
    
    async def register_query_result(self,
                                  query_id: str,
                                  user_id: int,
                                  query_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a query result as an MCP resource.
        
        Args:
            query_id: Unique query identifier
            user_id: User ID who executed the query
            query_data: Query result data and metadata
            
        Returns:
            Dict containing registration result
        """
        try:
            # Create MCP resource entry for query result
            mcp_resource = {
                'resource_id': query_id,
                'user_id': user_id,
                'type': 'query_result',
                'address': f"mcp://data_analytics/query/{query_id}",
                'registered_at': datetime.now().isoformat(),
                'metadata': {
                    'original_query': query_data.get('original_query'),
                    'generated_sql': query_data.get('generated_sql'),
                    'row_count': query_data.get('row_count', 0),
                    'processing_time_ms': query_data.get('processing_time_ms', 0),
                    'sqlite_database_path': query_data.get('sqlite_database_path'),
                    'pgvector_database': query_data.get('pgvector_database'),
                    'sql_confidence': query_data.get('sql_confidence', 0),
                    'metadata_matches': query_data.get('metadata_matches', 0),
                    'fallback_attempts': query_data.get('fallback_attempts', 0)
                },
                'query_data': query_data,
                'access_permissions': {
                    'owner': user_id,
                    'read_access': [user_id],
                    'write_access': [user_id]
                },
                'capabilities': ['replay', 'analyze', 'export', 'modify']
            }
            
            # Store resource
            self.resources[query_id] = mcp_resource
            
            # Update user resource mapping
            if user_id not in self.user_resource_map:
                self.user_resource_map[user_id] = []
            self.user_resource_map[user_id].append(query_id)
            
            logger.info(f"Query result registered: {query_id} for user {user_id}")
            
            return {
                'success': True,
                'resource_id': query_id,
                'mcp_address': mcp_resource['address'],
                'user_id': user_id,
                'type': 'query_result'
            }
            
        except Exception as e:
            logger.error(f"Query result registration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'resource_id': query_id,
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
            
            # Separate by resource types
            data_sources = [r for r in user_resources if r['type'] == 'data_source']
            query_results = [r for r in user_resources if r['type'] == 'query_result']
            analytics_reports = [r for r in user_resources if r['type'] == 'analytics_report']
            
            return {
                'success': True,
                'user_id': user_id,
                'resource_count': len(user_resources),
                'resources': user_resources,
                'resource_breakdown': {
                    'data_sources': len(data_sources),
                    'query_results': len(query_results),
                    'analytics_reports': len(analytics_reports)
                }
            }
            
        except Exception as e:
            logger.error(f"Get user resources failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def search_data_sources(self,
                                user_id: int,
                                query: str,
                                source_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Search data sources by query and type.
        
        Args:
            user_id: User identifier
            query: Search query
            source_type: Optional source type filter (csv, json, excel, etc.)
            
        Returns:
            Dict containing search results
        """
        try:
            matching_resources = []
            
            for resource_id, resource in self.resources.items():
                # Check if user has read access
                if user_id not in resource['access_permissions']['read_access']:
                    continue
                
                # Only search data sources
                if resource['type'] != 'data_source':
                    continue
                
                # Source type filter
                if source_type:
                    source_path = resource.get('source_path', '')
                    if not source_path.lower().endswith(f'.{source_type.lower()}'):
                        continue
                
                # Search in resource metadata
                search_text = json.dumps(resource, ensure_ascii=False).lower()
                if query.lower() in search_text:
                    matching_resources.append({
                        'resource_id': resource_id,
                        'address': resource['address'],
                        'type': resource['type'],
                        'source_path': resource.get('source_path'),
                        'registered_at': resource['registered_at'],
                        'metadata': resource['metadata'],
                        'is_owner': resource['access_permissions']['owner'] == user_id
                    })
                
                # Limit results
                if len(matching_resources) >= 20:
                    break
            
            return {
                'success': True,
                'user_id': user_id,
                'query': query,
                'source_type_filter': source_type,
                'matching_resources': matching_resources,
                'result_count': len(matching_resources)
            }
            
        except Exception as e:
            logger.error(f"Search data sources failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id,
                'query': query
            }
    
    async def get_query_history(self,
                              user_id: int,
                              limit: int = 50) -> Dict[str, Any]:
        """
        Get query history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of queries to return
            
        Returns:
            Dict containing query history
        """
        try:
            query_resources = []
            
            if user_id in self.user_resource_map:
                for resource_id in self.user_resource_map[user_id]:
                    if resource_id in self.resources:
                        resource = self.resources[resource_id]
                        if resource['type'] == 'query_result':
                            query_resources.append({
                                'resource_id': resource_id,
                                'original_query': resource['metadata'].get('original_query'),
                                'generated_sql': resource['metadata'].get('generated_sql'),
                                'row_count': resource['metadata'].get('row_count', 0),
                                'processing_time_ms': resource['metadata'].get('processing_time_ms', 0),
                                'registered_at': resource['registered_at'],
                                'sql_confidence': resource['metadata'].get('sql_confidence', 0)
                            })
            
            # Sort by registration time (most recent first)
            query_resources.sort(key=lambda x: x['registered_at'], reverse=True)
            
            # Limit results
            query_resources = query_resources[:limit]
            
            return {
                'success': True,
                'user_id': user_id,
                'query_count': len(query_resources),
                'queries': query_resources,
                'limit_applied': limit
            }
            
        except Exception as e:
            logger.error(f"Get query history failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def sync_with_databases(self, user_id: int) -> Dict[str, Any]:
        """
        Synchronize MCP resources with actual database data.
        
        Args:
            user_id: User ID to sync resources for
            
        Returns:
            Dict containing sync results
        """
        try:
            # Try to import analytics service for verification
            try:
                import sys
                from pathlib import Path
                project_root = Path(__file__).parent.parent
                sys.path.insert(0, str(project_root))
                
                from tools.services.data_analytics_service.services.data_analytics_service import get_analytics_service
                
                # Get service status for verification
                service = get_analytics_service("default_analytics")
                service_status = await service.get_service_status()
                
                if service_status:
                    # Update MCP resource metadata to match actual database data
                    updated_resources = 0
                    db_summary = service_status.get('database_summary', {})
                    
                    for resource_id in self.user_resource_map.get(user_id, []):
                        if resource_id in self.resources:
                            resource = self.resources[resource_id]
                            if resource['type'] == 'data_source':
                                # Update with actual database info
                                old_embeddings = resource['metadata'].get('embeddings_stored', 0)
                                new_embeddings = db_summary.get('total_embeddings', 0)
                                
                                if old_embeddings != new_embeddings:
                                    resource['metadata']['embeddings_stored'] = new_embeddings
                                    resource['updated_at'] = datetime.now().isoformat()
                                    updated_resources += 1
                                    logger.info(f"Updated resource {resource_id}: {old_embeddings} -> {new_embeddings} embeddings")
                    
                    return {
                        'success': True,
                        'user_id': user_id,
                        'database_embeddings': db_summary.get('total_embeddings', 0),
                        'resources_updated': updated_resources,
                        'sync_timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'error': "Analytics service status not available",
                        'user_id': user_id
                    }
                    
            except Exception as db_error:
                logger.warning(f"Database sync not available: {db_error}")
                return {
                    'success': False,
                    'error': f"Database connection failed: {db_error}",
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
                'total_data_sources': 0,
                'total_queries': 0,
                'total_processing_time_ms': 0,
                'total_cost_usd': 0.0
            }
            
            # Count resource types and aggregate data
            for resource in self.resources.values():
                resource_type = resource['type']
                stats['resource_types'][resource_type] = stats['resource_types'].get(resource_type, 0) + 1
                
                # Aggregate analytics data
                metadata = resource.get('metadata', {})
                stats['total_processing_time_ms'] += metadata.get('processing_time_ms', 0)
                stats['total_cost_usd'] += metadata.get('cost_usd', 0.0)
                
                if resource_type == 'data_source':
                    stats['total_data_sources'] += 1
                elif resource_type == 'query_result':
                    stats['total_queries'] += 1
            
            # Count resources per user
            for user_id, resources in self.user_resource_map.items():
                stats['resources_per_user'][str(user_id)] = len(resources)
            
            return stats
            
        except Exception as e:
            logger.error(f"Get resource stats failed: {e}")
            return {'error': str(e)}
    
    def _determine_resource_type(self, resource_data: Dict[str, Any]) -> str:
        """Determine resource type based on resource data."""
        # Check if it's a query result
        if 'original_query' in resource_data or 'generated_sql' in resource_data:
            return 'query_result'
        
        # Check if it's an analytics report
        if 'report_type' in resource_data or 'analysis_results' in resource_data:
            return 'analytics_report'
        
        # Default to data source
        return 'data_source'
    
    def _get_resource_capabilities(self, resource_type: str) -> List[str]:
        """Get capabilities based on resource type."""
        if resource_type == 'data_source':
            return ['query', 'search', 'analyze', 'export']
        elif resource_type == 'query_result':
            return ['replay', 'modify', 'export', 'analyze']
        elif resource_type == 'analytics_report':
            return ['view', 'export', 'share', 'update']
        else:
            return ['view', 'export']

# Global instance
data_analytics_resources = DataAnalyticsResources()