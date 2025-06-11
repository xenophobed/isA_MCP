import sys
import os
import pymysql
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.engine import Engine
from langchain_community.utilities import SQLDatabase

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.services.graph.mysql_connection import connect_to_mysql, MySQLDatabase, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

class MySQLDatabaseAdapter(SQLDatabase):
    """
    A custom adapter that extends LangChain's SQLDatabase class
    but uses direct PyMySQL connection for better stability.
    This allows it to be used with SQLDatabaseToolkit.
    """
    
    def __init__(self, 
                 host=DB_HOST, 
                 user=DB_USER, 
                 password=DB_PASSWORD, 
                 database=DB_NAME, 
                 port=DB_PORT,
                 sample_rows_in_table_info: int = 3):
        """
        Initialize the adapter with connection parameters.
        
        Args:
            host: MySQL host
            user: MySQL user
            password: MySQL password
            database: MySQL database name
            port: MySQL port
            sample_rows_in_table_info: Number of sample rows to include in table info
        """
        # Store connection parameters
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        
        # Create a connection string for SQLAlchemy
        connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        
        # Create a dummy engine for SQLDatabase initialization
        try:
            engine = create_engine(connection_string)
            super().__init__(engine, sample_rows_in_table_info=sample_rows_in_table_info)
        except Exception as e:
            print(f"Warning: SQLAlchemy engine creation failed: {e}")
            print("Creating a minimal engine for compatibility...")
            
            # Create a minimal engine-like object with required attributes
            class DummyEngine:
                class DummyDialect:
                    name = "mysql"
                dialect = DummyDialect()
                url = connection_string
            
            engine = DummyEngine()
            self._engine = engine
            self._metadata = None
            self._sample_rows_in_table_info = sample_rows_in_table_info
            # We can't set dialect directly as it's a property, but we can override the property
        
        # Create a direct MySQL connection wrapper
        # Use the existing connect_to_mysql function which creates a MySQLDatabase instance
        self.direct_db = MySQLDatabase(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
    
    # Override the dialect property
    @property
    def dialect(self) -> str:
        """Return string representation of dialect to use."""
        return "mysql"
    
    def _get_connection(self):
        """Get a new database connection"""
        return pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            port=self.port,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.Cursor
        )
    
    def run(self, command: str, fetch: str = "all", include_columns: bool = False, parameters: Optional[List[Any]] = None) -> Union[str, List[Dict[str, Any]]]:
        """
        Execute a SQL command and return the results.
        
        Args:
            command: SQL command to execute
            fetch: Whether to fetch "all" or "one" result
            include_columns: Whether to include column names in the results
            parameters: Parameters to pass to the SQL command
            
        Returns:
            Results as a string or list of dictionaries
        """
        try:
            # Use direct PyMySQL connection for better stability
            # Ignore parameters for now as our direct_db.run doesn't support them
            result = self.direct_db.run(command)
            
            # Format results as string if not returning dictionaries
            if not include_columns:
                return str(result)
            
            # If include_columns is True, convert to dictionaries
            if result and len(result) > 0:
                # Get column names
                conn = self._get_connection()
                with conn.cursor() as cursor:
                    cursor.execute(command)
                    column_names = [desc[0] for desc in cursor.description]
                conn.close()
                
                # Convert to dictionaries
                if fetch == "all":
                    results_with_columns = []
                    for row in result:
                        results_with_columns.append(dict(zip(column_names, row)))
                    return results_with_columns
                else:  # fetch == "one"
                    return dict(zip(column_names, result[0])) if result else None
            
            return result
            
        except Exception as e:
            return f"Error executing query: {e}"
    
    def run_no_throw(self, command: str, fetch: str = "all", include_columns: bool = False, parameters: Optional[List[Any]] = None) -> Union[str, List[Dict[str, Any]]]:
        """
        Execute a SQL command and return the results without throwing an exception.
        
        Args:
            command: SQL command to execute
            fetch: Whether to fetch "all" or "one" result
            include_columns: Whether to include column names in the results
            parameters: Parameters to pass to the SQL command
            
        Returns:
            Results as a string or list of dictionaries
        """
        try:
            return self.run(command, fetch, include_columns, parameters)
        except Exception as e:
            return f"Error executing query: {e}"
    
    def get_usable_table_names(self) -> List[str]:
        """Get names of tables available."""
        return self.direct_db.get_usable_table_names()
    
    def get_table_info(self, table_names: Optional[Union[List[str], str]] = None) -> str:
        """Get info about specified tables."""
        if table_names is None:
            table_names = self.get_usable_table_names()
        elif isinstance(table_names, str):
            table_names = [table_names]
        
        tables_info = []
        for table_name in table_names:
            tables_info.append(self.direct_db.get_table_info(table_name))
        
        return "\n\n".join(tables_info)

def get_langchain_db():
    """
    Get a LangChain-compatible SQLDatabase instance that uses direct PyMySQL connection.
    This can be used with SQLDatabaseToolkit.
    
    Returns:
        MySQLDatabaseAdapter: A LangChain-compatible SQLDatabase instance
    """
    try:
        db = MySQLDatabaseAdapter(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        return db
    except Exception as e:
        print(f"Error creating MySQLDatabaseAdapter: {e}")
        raise 