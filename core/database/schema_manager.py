#!/usr/bin/env python
"""
Database Schema Manager
Manages database schema validation, creation, and updates
"""
import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from core.logging import get_logger
from .connection_manager import get_database_manager

logger = get_logger(__name__)

class SchemaManager:
    """Manages database schema operations"""
    
    def __init__(self):
        self.schema_dir = Path(__file__).parent / "schemas"
        self.migration_dir = Path(__file__).parent / "migrations"
    
    async def validate_schema(self) -> Dict[str, Any]:
        """Validate current database schema against expected schema"""
        try:
            db = await get_database_manager()
            
            # Get current schema from database
            current_schema = await self._get_current_schema(db)
            
            # Load expected schema
            expected_schema = self._load_expected_schema()
            
            # Compare schemas
            validation_result = self._compare_schemas(current_schema, expected_schema)
            
            return {
                'valid': validation_result['valid'],
                'missing_tables': validation_result['missing_tables'],
                'missing_columns': validation_result['missing_columns'],
                'extra_tables': validation_result['extra_tables'],
                'schema_issues': validation_result['issues']
            }
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {'valid': False, 'error': str(e)}
    
    async def _get_current_schema(self, db) -> Dict[str, Any]:
        """Get current database schema"""
        try:
            # Query information_schema to get table and column information
            tables_query = """
            SELECT table_name, table_type
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
            
            columns_query = """
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
            
            tables = await db.execute_query(tables_query)
            columns = await db.execute_query(columns_query)
            
            # Organize schema data
            schema = {'tables': {}}
            
            for table in tables:
                table_name = table['table_name']
                schema['tables'][table_name] = {
                    'type': table['table_type'],
                    'columns': {}
                }
            
            for column in columns:
                table_name = column['table_name']
                if table_name in schema['tables']:
                    schema['tables'][table_name]['columns'][column['column_name']] = {
                        'type': column['data_type'],
                        'nullable': column['is_nullable'] == 'YES'
                    }
            
            return schema
        except Exception as e:
            logger.error(f"Error getting current schema: {e}")
            return {'tables': {}}
    
    def _load_expected_schema(self) -> Dict[str, Any]:
        """Load expected schema from schema files"""
        schema_file = self.schema_dir / "expected_schema.json"
        
        if not schema_file.exists():
            # Generate expected schema from SQL files
            return self._generate_expected_schema()
        
        try:
            with open(schema_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading expected schema: {e}")
            return {'tables': {}}
    
    def _generate_expected_schema(self) -> Dict[str, Any]:
        """Generate expected schema from known table definitions"""
        # Define expected tables and their key columns
        expected_tables = {
            'memories': {
                'columns': ['key', 'value', 'category', 'importance', 'created_by', 'created_at', 'updated_at']
            },
            'users': {
                'columns': ['user_id', 'email', 'phone', 'shipping_addresses', 'payment_methods', 'preferences', 'created_at', 'updated_at']
            },
            'user_sessions': {
                'columns': ['session_id', 'user_id', 'cart_data', 'checkout_data', 'created_at', 'expires_at']
            },
            'models': {
                'columns': ['model_id', 'model_type', 'metadata', 'created_at', 'updated_at']
            },
            'model_capabilities': {
                'columns': ['model_id', 'capability']
            },
            'weather_cache': {
                'columns': ['city', 'weather_data', 'created_at', 'updated_at']
            },
            'audit_log': {
                'columns': ['timestamp', 'tool_name', 'user_id', 'success', 'execution_time', 'security_level', 'details']
            },
            'authorization_requests': {
                'columns': ['id', 'tool_name', 'arguments', 'user_id', 'timestamp', 'security_level', 'reason', 'expires_at', 'status']
            },
            'rag_documents': {
                'columns': ['id', 'content', 'embedding', 'collection_name', 'metadata', 'source', 'created_at', 'updated_at']
            },
            'db_metadata_embedding': {
                'columns': ['id', 'entity_type', 'entity_name', 'entity_full_name', 'content', 'embedding', 'metadata', 'semantic_tags', 'confidence_score', 'source_step', 'database_source', 'created_at', 'updated_at']
            },
            'prompt_embeddings': {
                'columns': ['prompt_name', 'embedding', 'created_at', 'updated_at']
            },
            'resource_embeddings': {
                'columns': ['resource_uri', 'embedding', 'created_at', 'updated_at']
            },
            'tool_embeddings': {
                'columns': ['tool_name', 'embedding', 'created_at', 'updated_at']
            },
            'selection_history': {
                'columns': ['id', 'selection_type', 'query', 'selected_items', 'user_id', 'created_at']
            }
        }
        
        return {'tables': expected_tables}
    
    def _compare_schemas(self, current: Dict, expected: Dict) -> Dict[str, Any]:
        """Compare current and expected schemas"""
        result = {
            'valid': True,
            'missing_tables': [],
            'missing_columns': {},
            'extra_tables': [],
            'issues': []
        }
        
        current_tables = set(current.get('tables', {}).keys())
        expected_tables = set(expected.get('tables', {}).keys())
        
        # Find missing tables
        missing_tables = expected_tables - current_tables
        result['missing_tables'] = list(missing_tables)
        
        # Find extra tables (not necessarily an issue)
        extra_tables = current_tables - expected_tables
        result['extra_tables'] = list(extra_tables)
        
        # Check columns for existing tables
        for table_name in expected_tables.intersection(current_tables):
            expected_cols = set(expected['tables'][table_name].get('columns', []))
            current_cols = set(current['tables'][table_name].get('columns', {}).keys())
            
            missing_cols = expected_cols - current_cols
            if missing_cols:
                result['missing_columns'][table_name] = list(missing_cols)
        
        # Determine if schema is valid
        if result['missing_tables'] or result['missing_columns']:
            result['valid'] = False
            result['issues'].append("Missing required tables or columns")
        
        return result
    
    async def create_missing_tables(self, validation_result: Dict) -> bool:
        """Create missing tables based on validation result"""
        try:
            db = await get_database_manager()
            
            # Load SQL creation scripts
            sql_scripts = self._load_creation_scripts()
            
            for table_name in validation_result.get('missing_tables', []):
                if table_name in sql_scripts:
                    logger.info(f"Creating missing table: {table_name}")
                    await db.execute_query(sql_scripts[table_name])
                else:
                    logger.warning(f"No creation script found for table: {table_name}")
            
            return True
        except Exception as e:
            logger.error(f"Error creating missing tables: {e}")
            return False
    
    def _load_creation_scripts(self) -> Dict[str, str]:
        """Load table creation SQL scripts"""
        # This would load from schema files or define inline
        scripts = {
            'memories': """
            CREATE TABLE IF NOT EXISTS memories (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance INTEGER DEFAULT 1,
                created_by TEXT DEFAULT 'default',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
            """,
            # Add other table creation scripts as needed
        }
        return scripts
    
    async def backup_schema(self) -> str:
        """Create a backup of current schema"""
        try:
            db = await get_database_manager()
            current_schema = await self._get_current_schema(db)
            
            backup_file = self.schema_dir / f"schema_backup_{int(datetime.now().timestamp())}.json"
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_file, 'w') as f:
                json.dump(current_schema, f, indent=2)
            
            logger.info(f"Schema backup created: {backup_file}")
            return str(backup_file)
        except Exception as e:
            logger.error(f"Schema backup failed: {e}")
            raise 