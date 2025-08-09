#!/usr/bin/env python3
"""
Elasticsearch database adapter
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    from elasticsearch import Elasticsearch
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False

class ElasticsearchAdapter(DatabaseAdapter):
    """Elasticsearch database adapter"""
    
    def __init__(self):
        super().__init__()
        if not ELASTICSEARCH_AVAILABLE:
            raise ImportError("elasticsearch is required for Elasticsearch adapter. Install with: pip install elasticsearch")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create Elasticsearch connection"""
        # Build connection parameters
        connection_params = {
            'hosts': [{'host': config['host'], 'port': config.get('port', 9200)}],
            'timeout': config.get('timeout', 30)
        }
        
        # Add authentication if provided
        if 'username' in config and 'password' in config:
            connection_params['http_auth'] = (config['username'], config['password'])
        
        # Add SSL/TLS support
        if config.get('use_ssl', False):
            connection_params['use_ssl'] = True
            connection_params['verify_certs'] = config.get('verify_certs', True)
        
        # Add API key support
        if 'api_key' in config:
            connection_params['api_key'] = config['api_key']
        
        client = Elasticsearch(**connection_params)
        
        # Test the connection
        if not client.ping():
            raise ConnectionError("Failed to connect to Elasticsearch")
        
        self.client = client
        return client
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute Elasticsearch query"""
        try:
            # Parse different types of queries
            if query.startswith('{'):
                # JSON query (DSL)
                import json
                query_body = json.loads(query)
                
                # Extract index from query or use default
                index = query_body.pop('index', '_all')
                
                response = self.client.search(index=index, body=query_body)
                
                # Extract hits
                hits = response.get('hits', {}).get('hits', [])
                results = []
                
                for hit in hits:
                    result = hit.get('_source', {})
                    result['_id'] = hit.get('_id')
                    result['_index'] = hit.get('_index')
                    result['_score'] = hit.get('_score')
                    results.append(result)
                
                return results
            
            else:
                # Simple query string
                response = self.client.search(
                    index='_all',
                    body={"query": {"query_string": {"query": query}}},
                    size=100
                )
                
                hits = response.get('hits', {}).get('hits', [])
                results = []
                
                for hit in hits:
                    result = hit.get('_source', {})
                    result['_id'] = hit.get('_id')
                    result['_index'] = hit.get('_index')
                    result['_score'] = hit.get('_score')
                    results.append(result)
                
                return results
        
        except Exception as e:
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get Elasticsearch indices (equivalent to tables)"""
        tables = []
        
        try:
            # Get all indices
            indices_response = self.client.cat.indices(format='json')
            
            for index_info in indices_response:
                index_name = index_info['index']
                
                # Skip system indices unless specifically requested
                if index_name.startswith('.') and (not schema_filter or index_name not in schema_filter):
                    continue
                
                # Get index statistics
                try:
                    stats = self.client.indices.stats(index=index_name)
                    index_stats = stats['indices'].get(index_name, {})
                    primaries = index_stats.get('primaries', {})
                    
                    doc_count = primaries.get('docs', {}).get('count', 0)
                    store_size = primaries.get('store', {}).get('size_in_bytes', 0)
                    
                except Exception:
                    doc_count = int(index_info.get('docs.count', 0))
                    store_size = 0
                
                tables.append(TableInfo(
                    table_name=index_name,
                    schema_name='elasticsearch',
                    table_type='INDEX',
                    record_count=doc_count,
                    table_comment=f'Elasticsearch index: {index_name} (Size: {store_size} bytes)',
                    created_date='',
                    last_modified=''
                ))
        
        except Exception as e:
            # Add error table
            tables.append(TableInfo(
                table_name='error',
                schema_name='elasticsearch',
                table_type='ERROR',
                record_count=0,
                table_comment=f'Error retrieving indices: {str(e)}',
                created_date='',
                last_modified=''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get Elasticsearch field mappings (equivalent to columns)"""
        columns = []
        
        try:
            indices_to_analyze = [table_name] if table_name else [idx.table_name for idx in self.get_tables()]
            
            for index_name in indices_to_analyze:
                if index_name == 'error':
                    continue
                
                try:
                    # Get mapping for the index
                    mapping_response = self.client.indices.get_mapping(index=index_name)
                    
                    for idx, mapping_data in mapping_response.items():
                        properties = mapping_data.get('mappings', {}).get('properties', {})
                        
                        self._extract_fields_from_properties(properties, columns, index_name)
                
                except Exception as e:
                    columns.append(ColumnInfo(
                        table_name=index_name,
                        column_name='_error',
                        data_type='error',
                        max_length=0,
                        is_nullable=True,
                        default_value=str(e),
                        column_comment='Error retrieving mapping',
                        ordinal_position=1
                    ))
        
        except Exception as e:
            columns.append(ColumnInfo(
                table_name=table_name or 'unknown',
                column_name='_global_error',
                data_type='error',
                max_length=0,
                is_nullable=True,
                default_value=str(e),
                column_comment='Error analyzing Elasticsearch mappings',
                ordinal_position=1
            ))
        
        return columns
    
    def _extract_fields_from_properties(self, properties: Dict[str, Any], columns: List[ColumnInfo], 
                                      index_name: str, parent_path: str = '', position: int = 1) -> int:
        """Recursively extract fields from Elasticsearch mapping properties"""
        for field_name, field_mapping in properties.items():
            full_field_name = f"{parent_path}.{field_name}" if parent_path else field_name
            
            field_type = field_mapping.get('type', 'object')
            
            columns.append(ColumnInfo(
                table_name=index_name,
                column_name=full_field_name,
                data_type=field_type,
                max_length=0,  # Not applicable for Elasticsearch
                is_nullable=True,  # Elasticsearch fields are optional by default
                default_value='',
                column_comment=f"ES field type: {field_type}",
                ordinal_position=position
            ))
            
            position += 1
            
            # Handle nested objects
            if 'properties' in field_mapping:
                position = self._extract_fields_from_properties(
                    field_mapping['properties'], columns, index_name, full_field_name, position
                )
        
        return position
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get Elasticsearch relationships (very limited)"""
        # Elasticsearch doesn't have formal relationships
        # We could analyze join fields or parent-child relationships
        relationships = []
        
        try:
            indices = self.get_tables()
            
            for index in indices:
                if index.table_type == 'ERROR':
                    continue
                
                try:
                    # Check for join fields or parent-child mappings
                    mapping_response = self.client.indices.get_mapping(index=index.table_name)
                    
                    for idx_name, mapping_data in mapping_response.items():
                        properties = mapping_data.get('mappings', {}).get('properties', {})
                        
                        for field_name, field_mapping in properties.items():
                            if field_mapping.get('type') == 'join':
                                # Found a join field - indicates parent-child relationship
                                relations = field_mapping.get('relations', {})
                                for parent, children in relations.items():
                                    if isinstance(children, list):
                                        for child in children:
                                            relationships.append(RelationshipInfo(
                                                constraint_name=f"{idx_name}_{field_name}_{parent}_{child}",
                                                from_table=f"{idx_name}_{child}",
                                                from_column=field_name,
                                                to_table=f"{idx_name}_{parent}",
                                                to_column=field_name,
                                                constraint_type='JOIN_FIELD'
                                            ))
                                    else:
                                        relationships.append(RelationshipInfo(
                                            constraint_name=f"{idx_name}_{field_name}_{parent}_{children}",
                                            from_table=f"{idx_name}_{children}",
                                            from_column=field_name,
                                            to_table=f"{idx_name}_{parent}",
                                            to_column=field_name,
                                            constraint_type='JOIN_FIELD'
                                        ))
                
                except Exception:
                    continue
        
        except Exception:
            pass  # Relationship discovery is best-effort
        
        return relationships
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get Elasticsearch index settings and aliases"""
        indexes = []
        
        try:
            indices_to_analyze = [table_name] if table_name else [idx.table_name for idx in self.get_tables()]
            
            for index_name in indices_to_analyze:
                if index_name == 'error':
                    continue
                
                try:
                    # Get index settings
                    settings_response = self.client.indices.get_settings(index=index_name)
                    
                    for idx_name, settings_data in settings_response.items():
                        settings = settings_data.get('settings', {}).get('index', {})
                        
                        # Primary index entry
                        indexes.append(IndexInfo(
                            index_name=idx_name,
                            table_name=idx_name,
                            column_names=['_all'],  # Elasticsearch searches across all fields
                            is_unique=False,  # Elasticsearch doesn't enforce uniqueness
                            index_type='ELASTICSEARCH',
                            is_primary=True
                        ))
                        
                        # Get aliases
                        try:
                            aliases_response = self.client.indices.get_alias(index=idx_name)
                            aliases = aliases_response.get(idx_name, {}).get('aliases', {})
                            
                            for alias_name in aliases.keys():
                                indexes.append(IndexInfo(
                                    index_name=alias_name,
                                    table_name=idx_name,
                                    column_names=['_all'],
                                    is_unique=False,
                                    index_type='ALIAS',
                                    is_primary=False
                                ))
                        except Exception:
                            pass
                
                except Exception:
                    # Add basic index info
                    indexes.append(IndexInfo(
                        index_name=index_name,
                        table_name=index_name,
                        column_names=['_all'],
                        is_unique=False,
                        index_type='ELASTICSEARCH',
                        is_primary=True
                    ))
        
        except Exception:
            pass
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze Elasticsearch field distribution"""
        try:
            # Use aggregations to analyze field distribution
            agg_query = {
                "size": 0,
                "aggs": {
                    "field_stats": {
                        "terms": {
                            "field": column_name,
                            "size": min(sample_size, 100)
                        }
                    },
                    "missing_count": {
                        "missing": {"field": column_name}
                    }
                }
            }
            
            response = self.client.search(index=table_name, body=agg_query)
            
            # Extract statistics
            total_docs = response['hits']['total']['value']
            field_buckets = response['aggregations']['field_stats']['buckets']
            missing_count = response['aggregations']['missing_count']['doc_count']
            
            unique_values = [bucket['key'] for bucket in field_buckets]
            unique_count = len(unique_values)
            
            # Calculate percentages
            non_null_count = total_docs - missing_count
            null_percentage = missing_count / total_docs if total_docs > 0 else 0
            unique_percentage = unique_count / non_null_count if non_null_count > 0 else 0
            
            return {
                "total_count": total_docs,
                "unique_count": unique_count,
                "null_count": missing_count,
                "null_percentage": round(null_percentage, 4),
                "unique_percentage": round(unique_percentage, 4),
                "sample_values": unique_values[:10]
            }
        
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from Elasticsearch index"""
        try:
            response = self.client.search(
                index=table_name,
                body={"query": {"match_all": {}}},
                size=limit
            )
            
            hits = response.get('hits', {}).get('hits', [])
            samples = []
            
            for hit in hits:
                sample = hit.get('_source', {})
                sample['_id'] = hit.get('_id')
                sample['_index'] = hit.get('_index')
                sample['_score'] = hit.get('_score')
                samples.append(sample)
            
            return samples
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_database_version(self) -> str:
        """Get Elasticsearch version"""
        try:
            info = self.client.info()
            return info.get('version', {}).get('number', 'Unknown')
        except Exception:
            return "Unknown"
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get Elasticsearch cluster information"""
        try:
            cluster_health = self.client.cluster.health()
            cluster_stats = self.client.cluster.stats()
            
            return {
                "cluster_name": cluster_health.get('cluster_name', 'Unknown'),
                "status": cluster_health.get('status', 'Unknown'),
                "number_of_nodes": cluster_health.get('number_of_nodes', 0),
                "number_of_indices": cluster_health.get('active_indices', 0),
                "total_docs": cluster_stats.get('indices', {}).get('docs', {}).get('count', 0),
                "store_size": cluster_stats.get('indices', {}).get('store', {}).get('size_in_bytes', 0)
            }
        except Exception as e:
            return {"error": str(e)}