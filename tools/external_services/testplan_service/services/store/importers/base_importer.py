"""
Base Importer Class

Provides common database connection and logging functionality for all importers.
"""

import duckdb
import logging
import sys
from pathlib import Path
from typing import Optional

# Add base path for config import
base_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(base_path))

from config import config

logger = logging.getLogger(__name__)


class BaseImporter:
    """Base class for all data importers"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize base importer with database connection
        
        Args:
            db_path: Path to DuckDB database file (defaults to config setting)
        """
        # Get absolute path to testplan_service root
        current_file = Path(__file__).resolve()
        self.base_path = current_file.parent.parent.parent.parent  # importers/ -> store/ -> services/ -> testplan_service/
        
        # Use config path or provided path
        if db_path is None:
            self.db_path = Path(config.duckdb_absolute_path)
        else:
            self.db_path = Path(db_path)
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = duckdb.connect(str(self.db_path))
        logger.info(f"Connected to DuckDB: {self.db_path}")
        logger.info(f"Base path set to: {self.base_path}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Closed DuckDB connection")
    
    def commit(self):
        """Commit current transaction"""
        self.conn.commit()
    
    def execute(self, query: str, params: tuple = None):
        """Execute a query with optional parameters"""
        if params:
            return self.conn.execute(query, params)
        else:
            return self.conn.execute(query)
    
    def fetch_one(self, query: str, params: tuple = None):
        """Execute query and fetch one result"""
        result = self.execute(query, params)
        return result.fetchone() if result else None
    
    def fetch_all(self, query: str, params: tuple = None):
        """Execute query and fetch all results"""
        result = self.execute(query, params)
        return result.fetchall() if result else []