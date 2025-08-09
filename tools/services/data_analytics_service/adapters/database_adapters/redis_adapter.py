#!/usr/bin/env python3
"""
Redis database adapter
"""

import json
from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class RedisAdapter(DatabaseAdapter):
    """Redis database adapter"""
    
    def __init__(self):
        super().__init__()
        if not REDIS_AVAILABLE:
            raise ImportError("redis is required for Redis adapter. Install with: pip install redis")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create Redis connection"""
        connection = redis.Redis(
            host=config['host'],
            port=config.get('port', 6379),
            db=config.get('database', 0),
            password=config.get('password'),
            decode_responses=True,  # Automatically decode responses to strings
            socket_timeout=config.get('timeout', 30)
        )
        
        # Test the connection
        connection.ping()
        return connection
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute Redis command"""
        try:
            # Parse Redis commands (simplified)
            parts = query.strip().split()
            if not parts:
                return []
            
            command = parts[0].upper()
            args = parts[1:]
            
            if command == 'KEYS':
                pattern = args[0] if args else '*'
                keys = self.connection.keys(pattern)
                return [{"key": key, "type": self.connection.type(key)} for key in keys]
            
            elif command == 'GET':
                if args:
                    value = self.connection.get(args[0])
                    return [{"key": args[0], "value": value}]
            
            elif command == 'HGETALL':
                if args:
                    hash_data = self.connection.hgetall(args[0])
                    return [{"key": args[0], "hash_data": hash_data}]
            
            elif command == 'LRANGE':
                if len(args) >= 3:
                    list_data = self.connection.lrange(args[0], int(args[1]), int(args[2]))
                    return [{"key": args[0], "list_data": list_data}]
            
            elif command == 'SMEMBERS':
                if args:
                    set_data = list(self.connection.smembers(args[0]))
                    return [{"key": args[0], "set_data": set_data}]
            
            elif command == 'ZRANGE':
                if len(args) >= 3:
                    sorted_set_data = self.connection.zrange(args[0], int(args[1]), int(args[2]), withscores=True)
                    return [{"key": args[0], "sorted_set_data": sorted_set_data}]
            
            return []
        except Exception as e:
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get Redis key patterns (equivalent to tables)"""
        tables = []
        
        try:
            # Get all keys and group by pattern
            all_keys = self.connection.keys('*')
            key_patterns = {}
            
            for key in all_keys:
                key_type = self.connection.type(key)
                
                # Extract pattern (everything before first colon or full key if no colon)
                if ':' in key:
                    pattern = key.split(':')[0] + ':*'
                else:
                    pattern = key
                
                if pattern not in key_patterns:
                    key_patterns[pattern] = {
                        'count': 0,
                        'types': set(),
                        'sample_keys': []
                    }
                
                key_patterns[pattern]['count'] += 1
                key_patterns[pattern]['types'].add(key_type)
                if len(key_patterns[pattern]['sample_keys']) < 5:
                    key_patterns[pattern]['sample_keys'].append(key)
            
            # Convert to table info
            for pattern, info in key_patterns.items():
                tables.append(TableInfo(
                    table_name=pattern,
                    schema_name='redis',
                    table_type='KEY_PATTERN',
                    record_count=info['count'],
                    table_comment=f"Redis keys matching pattern {pattern}. Types: {', '.join(info['types'])}",
                    created_date='',
                    last_modified=''
                ))
        
        except Exception as e:
            # Add error table if we can't get keys
            tables.append(TableInfo(
                table_name='error',
                schema_name='redis',
                table_type='ERROR',
                record_count=0,
                table_comment=f'Error retrieving keys: {str(e)}',
                created_date='',
                last_modified=''
            ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get Redis key structure (equivalent to columns)"""
        columns = []
        
        try:
            if table_name and table_name != 'error':
                # Get keys matching the pattern
                keys = self.connection.keys(table_name.replace('*', '*'))[:100]  # Limit sample size
                
                field_analysis = {}
                
                for key in keys:
                    key_type = self.connection.type(key)
                    
                    if key_type == 'string':
                        # String value
                        if 'value' not in field_analysis:
                            field_analysis['value'] = {'types': set(), 'samples': []}
                        field_analysis['value']['types'].add('string')
                        
                        value = self.connection.get(key)
                        if len(field_analysis['value']['samples']) < 3:
                            field_analysis['value']['samples'].append(value)
                    
                    elif key_type == 'hash':
                        # Hash fields
                        hash_fields = self.connection.hkeys(key)
                        for field in hash_fields:
                            if field not in field_analysis:
                                field_analysis[field] = {'types': set(), 'samples': []}
                            field_analysis[field]['types'].add('hash_field')
                    
                    elif key_type == 'list':
                        # List elements
                        if 'list_elements' not in field_analysis:
                            field_analysis['list_elements'] = {'types': set(), 'samples': []}
                        field_analysis['list_elements']['types'].add('list')
                    
                    elif key_type == 'set':
                        # Set members
                        if 'set_members' not in field_analysis:
                            field_analysis['set_members'] = {'types': set(), 'samples': []}
                        field_analysis['set_members']['types'].add('set')
                    
                    elif key_type == 'zset':
                        # Sorted set members and scores
                        if 'zset_members' not in field_analysis:
                            field_analysis['zset_members'] = {'types': set(), 'samples': []}
                        field_analysis['zset_members']['types'].add('zset')
                
                # Convert to column info
                for i, (field_name, info) in enumerate(field_analysis.items(), 1):
                    data_types = ','.join(info['types'])
                    sample_data = ', '.join(str(s) for s in info.get('samples', [])[:3])
                    
                    columns.append(ColumnInfo(
                        table_name=table_name,
                        column_name=field_name,
                        data_type=data_types,
                        max_length=0,  # Not applicable for Redis
                        is_nullable=True,  # Redis values can be None
                        default_value='',
                        column_comment=f'Sample data: {sample_data}',
                        ordinal_position=i
                    ))
            
            else:
                # Get all key patterns
                tables = self.get_tables()
                for table in tables:
                    if table.table_type != 'ERROR':
                        table_columns = self.get_columns(table.table_name)
                        columns.extend(table_columns)
        
        except Exception as e:
            columns.append(ColumnInfo(
                table_name=table_name or 'unknown',
                column_name='_error',
                data_type='error',
                max_length=0,
                is_nullable=True,
                default_value=str(e),
                column_comment='Error analyzing Redis structure',
                ordinal_position=1
            ))
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get Redis relationships (very limited)"""
        # Redis doesn't have formal relationships
        # We could analyze key patterns for references
        relationships = []
        
        try:
            all_keys = self.connection.keys('*')
            
            # Look for common reference patterns
            for key in all_keys:
                if ':' in key:
                    parts = key.split(':')
                    if len(parts) >= 2:
                        # Check if the referenced key exists
                        potential_ref = parts[0]
                        if potential_ref in all_keys or self.connection.exists(potential_ref):
                            relationships.append(RelationshipInfo(
                                constraint_name=f"{key}_ref_{potential_ref}",
                                from_table=key,
                                from_column='key',
                                to_table=potential_ref,
                                to_column='key',
                                constraint_type='REFERENCE_PATTERN'
                            ))
        
        except Exception:
            pass  # Relationship discovery is best-effort
        
        return relationships
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get Redis indexes (Redis doesn't have traditional indexes)"""
        indexes = []
        
        # Redis doesn't have indexes in the traditional sense
        # But we can report key patterns as "indexes"
        try:
            if table_name:
                indexes.append(IndexInfo(
                    index_name=f"key_pattern_{table_name}",
                    table_name=table_name,
                    column_names=['key'],
                    is_unique=True,  # Redis keys are unique
                    index_type='KEY_PATTERN',
                    is_primary=True
                ))
            else:
                tables = self.get_tables()
                for table in tables:
                    if table.table_type != 'ERROR':
                        indexes.extend(self.get_indexes(table.table_name))
        
        except Exception:
            pass
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze Redis data distribution"""
        try:
            keys = self.connection.keys(table_name)[:sample_size]
            
            if not keys:
                return {"error": "No keys found"}
            
            value_types = {}
            sample_values = []
            
            for key in keys:
                key_type = self.connection.type(key)
                
                if key_type not in value_types:
                    value_types[key_type] = 0
                value_types[key_type] += 1
                
                # Get sample values based on type
                if len(sample_values) < 10:
                    if key_type == 'string':
                        value = self.connection.get(key)
                        sample_values.append(value)
                    elif key_type == 'hash':
                        hash_sample = dict(list(self.connection.hgetall(key).items())[:3])
                        sample_values.append(hash_sample)
                    elif key_type == 'list':
                        list_sample = self.connection.lrange(key, 0, 2)
                        sample_values.append(list_sample)
            
            return {
                "total_count": len(keys),
                "unique_count": len(keys),  # All keys are unique
                "null_count": 0,  # Redis doesn't store null keys
                "null_percentage": 0.0,
                "unique_percentage": 1.0,
                "type_distribution": value_types,
                "sample_values": sample_values
            }
        
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from Redis"""
        try:
            keys = self.connection.keys(table_name)[:limit]
            samples = []
            
            for key in keys:
                key_type = self.connection.type(key)
                
                sample_data = {
                    "key": key,
                    "type": key_type,
                    "ttl": self.connection.ttl(key)
                }
                
                if key_type == 'string':
                    sample_data["value"] = self.connection.get(key)
                elif key_type == 'hash':
                    sample_data["hash_data"] = self.connection.hgetall(key)
                elif key_type == 'list':
                    sample_data["list_data"] = self.connection.lrange(key, 0, 4)
                elif key_type == 'set':
                    sample_data["set_data"] = list(self.connection.smembers(key))[:5]
                elif key_type == 'zset':
                    sample_data["zset_data"] = self.connection.zrange(key, 0, 4, withscores=True)
                
                samples.append(sample_data)
            
            return samples
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get Redis database information"""
        try:
            info = self.connection.info()
            return {
                "database_type": "Redis",
                "connected": True,
                "version": info.get('redis_version', 'Unknown'),
                "memory_used": info.get('used_memory_human', 'Unknown'),
                "total_keys": info.get('db0', {}).get('keys', 0),
                "uptime": info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            return {"error": str(e), "connected": False}
    
    def get_database_version(self) -> str:
        """Get Redis version"""
        try:
            info = self.connection.info()
            return info.get('redis_version', 'Unknown')
        except Exception:
            return "Unknown"