#!/usr/bin/env python3
"""
Base database adapter abstract class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    from ...processors.data_processors.management.metadata.metadata_extractor import MetadataExtractor
except ImportError:
    # Fallback minimal MetadataExtractor
    class MetadataExtractor:
        def extract_metadata(self, source_path: str, source_type: Optional[str] = None, **kwargs) -> Dict[str, Any]:
            return {"error": "MetadataExtractor not available"}

# Define missing data classes
@dataclass
class TableInfo:
    name: str
    schema: str = None
    row_count: int = 0
    
@dataclass 
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool = True
    
@dataclass
class RelationshipInfo:
    from_table: str
    to_table: str
    relationship_type: str = "unknown"
    
@dataclass
class IndexInfo:
    name: str
    table: str
    columns: List[str]

class DatabaseAdapter(MetadataExtractor):
    """Abstract base class for database adapters"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.config = None
    
    @abstractmethod
    def _create_connection(self, config: Dict[str, Any]):
        """Create database connection - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute query and return results - must be implemented by subclasses"""
        pass
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Establish database connection"""
        try:
            self.config = config
            self.connection = self._create_connection(config)
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
        except Exception as e:
            print(f"Error closing database connection: {e}")
        finally:
            self.cursor = None
            self.connection = None
    
    def test_connection(self) -> bool:
        """Test if database connection is active"""
        if not self.connection:
            return False
        
        try:
            # Simple test query
            self._execute_query("SELECT 1")
            return True
        except Exception:
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get basic database information"""
        try:
            info = {
                "database_type": self.__class__.__name__.replace('Adapter', ''),
                "connected": self.test_connection()
            }
            
            if self.config:
                info.update({
                    "host": self.config.get('host', 'unknown'),
                    "port": self.config.get('port', 'unknown'),
                    "database": self.config.get('database', 'unknown')
                })
            
            return info
        except Exception as e:
            return {"error": str(e), "connected": False}
    
    def execute_custom_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a custom query"""
        if not self.connection:
            raise ConnectionError("No active database connection")
        
        return self._execute_query(query, params)
    
    def get_table_count(self) -> int:
        """Get total number of tables"""
        try:
            tables = self.get_tables()
            return len(tables)
        except Exception:
            return 0
    
    def get_table_names(self, schema_filter: Optional[List[str]] = None) -> List[str]:
        """Get list of table names"""
        try:
            tables = self.get_tables(schema_filter)
            return [table.table_name for table in tables]
        except Exception:
            return []
    
    def get_column_names(self, table_name: str) -> List[str]:
        """Get column names for a specific table"""
        try:
            columns = self.get_columns(table_name)
            return [column.column_name for column in columns]
        except Exception:
            return []
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get complete schema information for a table"""
        try:
            # Get table info
            tables = self.get_tables()
            table_info = next((t for t in tables if t.table_name == table_name), None)
            
            if not table_info:
                return {"error": f"Table {table_name} not found"}
            
            # Get columns
            columns = self.get_columns(table_name)
            
            # Get indexes
            indexes = self.get_indexes(table_name)
            
            # Get relationships
            relationships = self.get_relationships()
            table_relationships = [
                r for r in relationships 
                if r.from_table == table_name or r.to_table == table_name
            ]
            
            return {
                "table": self._table_to_dict(table_info),
                "columns": [self._column_to_dict(c) for c in columns],
                "indexes": [self._index_to_dict(i) for i in indexes],
                "relationships": [self._relationship_to_dict(r) for r in table_relationships]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def validate_table_access(self, table_name: str) -> bool:
        """Validate if table exists and is accessible"""
        try:
            # Try to get basic info about the table
            result = self._execute_query(f"SELECT COUNT(*) as count FROM {table_name} LIMIT 1")
            return len(result) > 0
        except Exception:
            return False
    
    def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """Get basic statistics for a table"""
        try:
            stats = {}
            
            # Get row count
            count_result = self._execute_query(f"SELECT COUNT(*) as total_rows FROM {table_name}")
            if count_result:
                stats["total_rows"] = count_result[0]["total_rows"]
            
            # Get column count
            columns = self.get_columns(table_name)
            stats["total_columns"] = len(columns)
            
            # Get nullable columns count
            nullable_count = sum(1 for c in columns if c.is_nullable)
            stats["nullable_columns"] = nullable_count
            stats["not_nullable_columns"] = len(columns) - nullable_count
            
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    @abstractmethod
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get table information - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get column information - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get relationship information - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get index information - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze data distribution - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data - must be implemented by subclasses"""
        pass