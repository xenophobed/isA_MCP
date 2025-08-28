#!/usr/bin/env python3
"""
MongoDB database adapter
"""

from typing import Dict, List, Any, Optional
from .base_adapter import DatabaseAdapter
from ...processors.data_processors.metadata_extractor import TableInfo, ColumnInfo, RelationshipInfo, IndexInfo

try:
    import pymongo
    from bson import ObjectId
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

class MongoDBAdapter(DatabaseAdapter):
    """MongoDB database adapter"""
    
    def __init__(self):
        super().__init__()
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo is required for MongoDB adapter. Install with: pip install pymongo")
    
    def _create_connection(self, config: Dict[str, Any]):
        """Create MongoDB connection"""
        # Build connection string
        if 'connection_string' in config:
            connection_string = config['connection_string']
        else:
            auth_part = ""
            if 'username' in config and 'password' in config:
                auth_part = f"{config['username']}:{config['password']}@"
            
            connection_string = f"mongodb://{auth_part}{config['host']}:{config.get('port', 27017)}"
        
        client = pymongo.MongoClient(connection_string)
        self.db = client[config['database']]
        self.client = client
        return client
    
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute MongoDB query - Note: MongoDB uses different query syntax"""
        # This is a simplified implementation
        # In practice, MongoDB queries would be JSON/dict objects
        try:
            # Parse simple find operations
            if query.startswith("db."):
                # Extract collection name and operation
                parts = query.split(".")
                if len(parts) >= 3:
                    collection_name = parts[1]
                    operation = parts[2]
                    
                    collection = self.db[collection_name]
                    
                    if operation.startswith("find"):
                        # Simple find operation
                        cursor = collection.find()
                        results = []
                        for doc in cursor:
                            # Convert ObjectId to string for JSON serialization
                            if '_id' in doc and isinstance(doc['_id'], ObjectId):
                                doc['_id'] = str(doc['_id'])
                            results.append(doc)
                        return results
                    elif operation.startswith("count"):
                        # Count operation
                        count = collection.count_documents({})
                        return [{"count": count}]
            
            return []
        except Exception as e:
            raise e
    
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get MongoDB collections (equivalent to tables)"""
        collections = self.db.list_collection_names()
        tables = []
        
        for collection_name in collections:
            try:
                collection = self.db[collection_name]
                
                # Get collection stats
                stats = self.db.command("collStats", collection_name)
                count = stats.get('count', 0)
                size = stats.get('size', 0)
                
                tables.append(TableInfo(
                    table_name=collection_name,
                    schema_name=self.db.name,
                    table_type='COLLECTION',
                    record_count=count,
                    table_comment=f'MongoDB collection: {collection_name} (Size: {size} bytes)',
                    created_date='',
                    last_modified=''
                ))
            except Exception as e:
                # If stats fail, still add the collection with basic info
                tables.append(TableInfo(
                    table_name=collection_name,
                    schema_name=self.db.name,
                    table_type='COLLECTION',
                    record_count=0,
                    table_comment=f'MongoDB collection: {collection_name}',
                    created_date='',
                    last_modified=''
                ))
        
        return tables
    
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get MongoDB collection fields (equivalent to columns)"""
        columns = []
        
        collections_to_analyze = [table_name] if table_name else self.db.list_collection_names()
        
        for collection_name in collections_to_analyze:
            try:
                collection = self.db[collection_name]
                
                # Sample documents to infer schema
                sample_docs = list(collection.find().limit(100))
                field_types = {}
                
                for doc in sample_docs:
                    for field, value in doc.items():
                        field_type = type(value).__name__
                        if field not in field_types:
                            field_types[field] = set()
                        field_types[field].add(field_type)
                
                # Convert to column info
                for i, (field_name, types) in enumerate(field_types.items(), 1):
                    data_type = ','.join(sorted(types))  # Multiple types possible in MongoDB
                    
                    columns.append(ColumnInfo(
                        table_name=collection_name,
                        column_name=field_name,
                        data_type=data_type,
                        max_length=0,  # Not applicable for MongoDB
                        is_nullable=True,  # MongoDB fields are always optional
                        default_value='',
                        column_comment=f'Inferred from {len(sample_docs)} sample documents',
                        ordinal_position=i
                    ))
            
            except Exception as e:
                # Add error info as a column
                columns.append(ColumnInfo(
                    table_name=collection_name,
                    column_name='_error',
                    data_type='error',
                    max_length=0,
                    is_nullable=True,
                    default_value=str(e),
                    column_comment='Error analyzing collection schema',
                    ordinal_position=1
                ))
        
        return columns
    
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get MongoDB relationships (limited - mostly manual references)"""
        # MongoDB doesn't have formal foreign keys like SQL databases
        # This would require custom analysis of document references
        relationships = []
        
        try:
            # Look for common reference patterns like ObjectId references
            collections = self.db.list_collection_names()
            
            for collection_name in collections:
                collection = self.db[collection_name]
                sample_docs = list(collection.find().limit(50))
                
                for doc in sample_docs:
                    for field, value in doc.items():
                        # Look for ObjectId references that might indicate relationships
                        if isinstance(value, ObjectId) and field.endswith('_id') and field != '_id':
                            # Potential reference field
                            referenced_collection = field.replace('_id', '')
                            if referenced_collection in collections:
                                relationships.append(RelationshipInfo(
                                    constraint_name=f"{collection_name}_{field}_ref",
                                    from_table=collection_name,
                                    from_column=field,
                                    to_table=referenced_collection,
                                    to_column='_id',
                                    constraint_type='REFERENCE'
                                ))
        
        except Exception:
            pass  # Relationship discovery is best-effort
        
        return relationships
    
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get MongoDB indexes"""
        indexes = []
        
        collections_to_analyze = [table_name] if table_name else self.db.list_collection_names()
        
        for collection_name in collections_to_analyze:
            try:
                collection = self.db[collection_name]
                index_info = collection.list_indexes()
                
                for index in index_info:
                    # Extract index information
                    index_name = index.get('name', '')
                    index_keys = index.get('key', {})
                    
                    # Convert index keys to column names
                    column_names = list(index_keys.keys())
                    
                    # Check if unique
                    is_unique = index.get('unique', False)
                    is_primary = index_name == '_id_'  # _id index is primary
                    
                    indexes.append(IndexInfo(
                        index_name=index_name,
                        table_name=collection_name,
                        column_names=column_names,
                        is_unique=is_unique,
                        index_type='BTREE',  # MongoDB default
                        is_primary=is_primary
                    ))
            
            except Exception:
                # Add default _id index if collection exists
                indexes.append(IndexInfo(
                    index_name='_id_',
                    table_name=collection_name,
                    column_names=['_id'],
                    is_unique=True,
                    index_type='BTREE',
                    is_primary=True
                ))
        
        return indexes
    
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze MongoDB data distribution"""
        try:
            collection = self.db[table_name]
            
            # Aggregation pipeline for statistics
            pipeline = [
                {"$match": {column_name: {"$exists": True, "$ne": None}}},
                {"$group": {
                    "_id": None,
                    "total_count": {"$sum": 1},
                    "unique_values": {"$addToSet": f"${column_name}"}
                }},
                {"$project": {
                    "total_count": 1,
                    "unique_count": {"$size": "$unique_values"},
                    "sample_values": {"$slice": ["$unique_values", 10]}
                }}
            ]
            
            result = list(collection.aggregate(pipeline))
            if not result:
                return {"error": "No data found"}
            
            stats = result[0]
            
            # Get total document count (including nulls)
            total_docs = collection.count_documents({})
            null_count = total_docs - stats['total_count']
            null_percentage = null_count / total_docs if total_docs > 0 else 0
            unique_percentage = stats['unique_count'] / stats['total_count'] if stats['total_count'] > 0 else 0
            
            return {
                "total_count": total_docs,
                "unique_count": stats['unique_count'],
                "null_count": null_count,
                "null_percentage": round(null_percentage, 4),
                "unique_percentage": round(unique_percentage, 4),
                "sample_values": stats.get('sample_values', [])
            }
        
        except Exception as e:
            return {"error": str(e), "analysis_failed": True}
    
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from MongoDB collection"""
        try:
            collection = self.db[table_name]
            documents = []
            
            for doc in collection.find().limit(limit):
                # Convert ObjectId to string
                if '_id' in doc and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
                
                # Convert other non-serializable types
                for key, value in doc.items():
                    if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        doc[key] = str(value)
                
                documents.append(doc)
            
            return documents
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_database_version(self) -> str:
        """Get MongoDB version"""
        try:
            server_info = self.client.server_info()
            return server_info.get('version', 'Unknown')
        except Exception:
            return "Unknown"
    
    def execute_aggregation(self, collection_name: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute MongoDB aggregation pipeline"""
        try:
            collection = self.db[collection_name]
            results = []
            
            for doc in collection.aggregate(pipeline):
                # Convert ObjectId to string
                if '_id' in doc and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
                results.append(doc)
            
            return results
        except Exception as e:
            return [{"error": str(e)}]