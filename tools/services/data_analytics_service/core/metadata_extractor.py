#!/usr/bin/env python3
"""
Core metadata extractor with data models
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class TableInfo:
    """Table metadata information"""
    table_name: str
    schema_name: str
    table_type: str
    record_count: int
    table_comment: str
    created_date: str
    last_modified: str
    business_category: Optional[str] = None
    update_frequency: Optional[str] = None
    data_quality_score: Optional[float] = None
    key_columns: Optional[List[str]] = None

@dataclass
class ColumnInfo:
    """Column metadata information"""
    table_name: str
    column_name: str
    data_type: str
    max_length: Optional[int]
    is_nullable: bool
    default_value: Optional[str]
    column_comment: str
    ordinal_position: int
    business_type: Optional[str] = None
    value_range: Optional[Dict[str, Any]] = None
    null_percentage: Optional[float] = None
    unique_percentage: Optional[float] = None
    sample_values: Optional[List[Any]] = None

@dataclass
class RelationshipInfo:
    """Relationship metadata information"""
    constraint_name: str
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    constraint_type: str
    relationship_strength: Optional[float] = None
    cardinality: Optional[str] = None

@dataclass
class IndexInfo:
    """Index metadata information"""
    index_name: str
    table_name: str
    column_names: List[str]
    is_unique: bool
    index_type: str
    is_primary: bool

class MetadataExtractor(ABC):
    """Abstract base class for metadata extraction"""
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Establish connection to data source"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to data source"""
        pass
    
    @abstractmethod
    def get_tables(self, schema_filter: Optional[List[str]] = None) -> List[TableInfo]:
        """Get table information"""
        pass
    
    @abstractmethod
    def get_columns(self, table_name: Optional[str] = None) -> List[ColumnInfo]:
        """Get column information"""
        pass
    
    @abstractmethod
    def get_relationships(self) -> List[RelationshipInfo]:
        """Get relationship information"""
        pass
    
    @abstractmethod
    def get_indexes(self, table_name: Optional[str] = None) -> List[IndexInfo]:
        """Get index information"""
        pass
    
    @abstractmethod
    def analyze_data_distribution(self, table_name: str, column_name: str, sample_size: int = 1000) -> Dict[str, Any]:
        """Analyze data distribution for a specific column"""
        pass
    
    @abstractmethod
    def get_sample_data(self, table_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from table"""
        pass
    
    def extract_full_metadata(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete metadata information"""
        if not self.connect(config):
            raise ConnectionError(f"Failed to connect to data source")
        
        try:
            # Get basic metadata
            tables = self.get_tables(config.get('schema_filter'))
            columns = self.get_columns()
            relationships = self.get_relationships()
            indexes = self.get_indexes()
            
            # Analyze data characteristics
            data_analysis = {}
            include_analysis = config.get('include_data_analysis', False)
            
            if include_analysis:
                data_analysis = self._analyze_data_characteristics(
                    tables, 
                    columns, 
                    config.get('sample_size', 1000)
                )
            
            # Discover business patterns
            business_patterns = self._discover_business_patterns(tables, columns, relationships)
            
            return {
                "source_info": {
                    "type": self.__class__.__name__.replace('Adapter', '').lower(),
                    "extraction_time": datetime.now().isoformat(),
                    "total_tables": len(tables),
                    "total_columns": len(columns),
                    "total_relationships": len(relationships),
                    "total_indexes": len(indexes)
                },
                "tables": [self._table_to_dict(t) for t in tables],
                "columns": [self._column_to_dict(c) for c in columns],
                "relationships": [self._relationship_to_dict(r) for r in relationships],
                "indexes": [self._index_to_dict(i) for i in indexes],
                "data_analysis": data_analysis,
                "business_patterns": business_patterns
            }
        finally:
            self.disconnect()
    
    def _analyze_data_characteristics(self, tables: List[TableInfo], columns: List[ColumnInfo], sample_size: int) -> Dict[str, Any]:
        """Analyze data characteristics for tables"""
        analysis = {}
        
        # Limit analysis to avoid performance issues
        tables_to_analyze = tables[:10]  # Analyze first 10 tables
        
        for table in tables_to_analyze:
            table_analysis = {}
            table_columns = [c for c in columns if c.table_name == table.table_name]
            
            # Analyze key columns first
            columns_to_analyze = table_columns[:5]  # Analyze first 5 columns
            
            for column in columns_to_analyze:
                try:
                    column_stats = self.analyze_data_distribution(
                        table.table_name, 
                        column.column_name, 
                        sample_size
                    )
                    table_analysis[column.column_name] = column_stats
                except Exception as e:
                    table_analysis[column.column_name] = {
                        "error": str(e),
                        "analysis_failed": True
                    }
            
            analysis[table.table_name] = table_analysis
        
        return analysis
    
    def _discover_business_patterns(self, tables: List[TableInfo], columns: List[ColumnInfo], relationships: List[RelationshipInfo]) -> Dict[str, Any]:
        """Discover business patterns in the data"""
        return {
            "naming_conventions": self._analyze_naming_patterns(tables, columns),
            "table_categories": self._categorize_tables(tables, columns),
            "relationship_patterns": self._analyze_relationship_patterns(relationships),
            "data_type_patterns": self._analyze_datatype_patterns(columns)
        }
    
    def _analyze_naming_patterns(self, tables: List[TableInfo], columns: List[ColumnInfo]) -> Dict[str, Any]:
        """Analyze naming patterns in tables and columns"""
        table_prefixes = {}
        table_suffixes = {}
        column_prefixes = {}
        column_suffixes = {}
        
        for table in tables:
            name = table.table_name.lower()
            if '_' in name:
                parts = name.split('_')
                if len(parts) >= 2:
                    prefix = parts[0]
                    suffix = parts[-1]
                    table_prefixes[prefix] = table_prefixes.get(prefix, 0) + 1
                    table_suffixes[suffix] = table_suffixes.get(suffix, 0) + 1
        
        for column in columns:
            name = column.column_name.lower()
            if '_' in name:
                parts = name.split('_')
                if len(parts) >= 2:
                    prefix = parts[0]
                    suffix = parts[-1]
                    column_prefixes[prefix] = column_prefixes.get(prefix, 0) + 1
                    column_suffixes[suffix] = column_suffixes.get(suffix, 0) + 1
        
        return {
            "table_prefixes": sorted(table_prefixes.items(), key=lambda x: x[1], reverse=True)[:10],
            "table_suffixes": sorted(table_suffixes.items(), key=lambda x: x[1], reverse=True)[:10],
            "column_prefixes": sorted(column_prefixes.items(), key=lambda x: x[1], reverse=True)[:10],
            "column_suffixes": sorted(column_suffixes.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def _categorize_tables(self, tables: List[TableInfo], columns: List[ColumnInfo]) -> Dict[str, List[str]]:
        """Categorize tables based on naming and structure patterns"""
        categories = {
            "master_data": [],
            "transaction_data": [],
            "reference_data": [],
            "log_data": [],
            "configuration": [],
            "audit": []
        }
        
        for table in tables:
            table_name = table.table_name.lower()
            table_columns = [c.column_name.lower() for c in columns if c.table_name == table.table_name]
            
            # Master data indicators
            if any(keyword in table_name for keyword in ['master', 'base', 'main', 'entity']):
                categories["master_data"].append(table.table_name)
            # Transaction data indicators
            elif any(keyword in table_name for keyword in ['transaction', 'order', 'payment', 'invoice', 'detail']):
                categories["transaction_data"].append(table.table_name)
            # Reference data indicators
            elif any(keyword in table_name for keyword in ['ref', 'lookup', 'code', 'type', 'status']):
                categories["reference_data"].append(table.table_name)
            # Log data indicators
            elif any(keyword in table_name for keyword in ['log', 'audit', 'history', 'trace']):
                categories["log_data"].append(table.table_name)
            # Configuration indicators
            elif any(keyword in table_name for keyword in ['config', 'setting', 'parameter', 'option']):
                categories["configuration"].append(table.table_name)
            # Audit indicators based on columns
            elif any(col in table_columns for col in ['created_at', 'updated_at', 'created_by', 'updated_by']):
                categories["audit"].append(table.table_name)
        
        return categories
    
    def _analyze_relationship_patterns(self, relationships: List[RelationshipInfo]) -> Dict[str, Any]:
        """Analyze relationship patterns"""
        if not relationships:
            return {"total_relationships": 0}
        
        constraint_types = {}
        table_connections = {}
        
        for rel in relationships:
            # Count constraint types
            constraint_types[rel.constraint_type] = constraint_types.get(rel.constraint_type, 0) + 1
            
            # Count table connections
            from_table = rel.from_table
            to_table = rel.to_table
            
            if from_table not in table_connections:
                table_connections[from_table] = {"incoming": 0, "outgoing": 0}
            if to_table not in table_connections:
                table_connections[to_table] = {"incoming": 0, "outgoing": 0}
            
            table_connections[from_table]["outgoing"] += 1
            table_connections[to_table]["incoming"] += 1
        
        # Find most connected tables
        most_connected = sorted(
            table_connections.items(),
            key=lambda x: x[1]["incoming"] + x[1]["outgoing"],
            reverse=True
        )[:10]
        
        return {
            "total_relationships": len(relationships),
            "constraint_types": constraint_types,
            "most_connected_tables": most_connected,
            "table_connections": table_connections
        }
    
    def _analyze_datatype_patterns(self, columns: List[ColumnInfo]) -> Dict[str, Any]:
        """Analyze data type usage patterns"""
        type_counts = {}
        nullable_counts = {"nullable": 0, "not_nullable": 0}
        
        for column in columns:
            data_type = column.data_type.lower()
            type_counts[data_type] = type_counts.get(data_type, 0) + 1
            
            if column.is_nullable:
                nullable_counts["nullable"] += 1
            else:
                nullable_counts["not_nullable"] += 1
        
        return {
            "data_type_distribution": sorted(type_counts.items(), key=lambda x: x[1], reverse=True),
            "nullable_distribution": nullable_counts,
            "total_columns": len(columns)
        }
    
    def _table_to_dict(self, table: TableInfo) -> Dict[str, Any]:
        """Convert TableInfo to dictionary"""
        return {
            "table_name": table.table_name,
            "schema_name": table.schema_name,
            "table_type": table.table_type,
            "record_count": table.record_count,
            "table_comment": table.table_comment,
            "created_date": table.created_date,
            "last_modified": table.last_modified,
            "business_category": table.business_category,
            "update_frequency": table.update_frequency,
            "data_quality_score": table.data_quality_score,
            "key_columns": table.key_columns
        }
    
    def _column_to_dict(self, column: ColumnInfo) -> Dict[str, Any]:
        """Convert ColumnInfo to dictionary"""
        return {
            "table_name": column.table_name,
            "column_name": column.column_name,
            "data_type": column.data_type,
            "max_length": column.max_length,
            "is_nullable": column.is_nullable,
            "default_value": column.default_value,
            "column_comment": column.column_comment,
            "ordinal_position": column.ordinal_position,
            "business_type": column.business_type,
            "value_range": column.value_range,
            "null_percentage": column.null_percentage,
            "unique_percentage": column.unique_percentage,
            "sample_values": column.sample_values
        }
    
    def _relationship_to_dict(self, relationship: RelationshipInfo) -> Dict[str, Any]:
        """Convert RelationshipInfo to dictionary"""
        return {
            "constraint_name": relationship.constraint_name,
            "from_table": relationship.from_table,
            "from_column": relationship.from_column,
            "to_table": relationship.to_table,
            "to_column": relationship.to_column,
            "constraint_type": relationship.constraint_type,
            "relationship_strength": relationship.relationship_strength,
            "cardinality": relationship.cardinality
        }
    
    def _index_to_dict(self, index: IndexInfo) -> Dict[str, Any]:
        """Convert IndexInfo to dictionary"""
        return {
            "index_name": index.index_name,
            "table_name": index.table_name,
            "column_names": index.column_names,
            "is_unique": index.is_unique,
            "index_type": index.index_type,
            "is_primary": index.is_primary
        }