import pymysql
import pandas as pd
import time
import socket
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, text

# Database connection parameters
DB_HOST = "rm-wz93vc1683u90x75lko.mysql.rds.aliyuncs.com"
DB_USER = "todennis"
DB_PASSWORD = "Abc@13579"
DB_NAME = "to_dennis"
DB_PORT = 3306  # Default MySQL port

def connect_to_mysql_langchain():
    """
    Connect to MySQL database using LangChain's SQLDatabase
    This is compatible with LangChain's SQLDatabaseToolkit
    
    Returns:
        SQLDatabase: A LangChain SQLDatabase object
    """
    try:
        # Create connection string for MySQL
        connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
        # Create SQLDatabase instance using from_uri method
        db = SQLDatabase.from_uri(
            connection_string,
            sample_rows_in_table_info=2,
            engine_args={
                "connect_args": {
                    "connect_timeout": 10,
                    "read_timeout": 30,
                    "write_timeout": 30
                }
            }
        )
        
        # Add a run method to match our custom class
        def run_method(query):
            """Run a SQL query and return results as a list of tuples"""
            try:
                # Use the execute_query method of SQLDatabase
                result = db.run(query)
                return result
            except Exception as e:
                print(f"Error executing query: {e}")
                return []
        
        # Add the run method to the SQLDatabase instance
        db.run = run_method
        
        return db
    except Exception as e:
        print(f"Error connecting to database with LangChain: {e}")
        raise

class MySQLDatabase:
    """
    A simple MySQL database wrapper that mimics the SQLDatabase interface
    but uses PyMySQL directly for better stability
    """
    
    def __init__(self, host=DB_HOST, user=DB_USER, password=DB_PASSWORD, 
                 database=DB_NAME, port=DB_PORT):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.dialect = "mysql"
        
        # Test connection on initialization
        self._test_connection()
    
    def _test_connection(self):
        """Test the connection to make sure it works"""
        conn = self._get_connection()
        conn.close()
    
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
            cursorclass=pymysql.cursors.Cursor  # Use standard cursor for tuple results
        )
    
    def run(self, query):
        """
        Run a SQL query and return results in the exact same format as the SQLite example:
        [(1, 'AC/DC'), (2, 'Accept'), ...]
        
        Args:
            query: SQL query string
            
        Returns:
            list of tuples containing the query results
        """
        try:
            conn = self._get_connection()
            
            with conn.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                
            conn.close()
            return results
            
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
    
    def get_usable_table_names(self):
        """
        Get a list of all tables in the database
        
        Returns:
            list: List of table names
        """
        try:
            conn = self._get_connection()
            
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]
                
            conn.close()
            return tables
            
        except Exception as e:
            print(f"Error getting table names: {e}")
            return []
    
    def get_table_info(self, table_name):
        """
        Get information about a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            str: Table information
        """
        try:
            conn = self._get_connection()
            
            # Get column information
            with conn.cursor() as cursor:
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
            
            # Get sample data
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                sample_data = cursor.fetchall()
            
            conn.close()
            
            # Format the information
            info = f"Table: {table_name}\n"
            info += "Columns:\n"
            for col in columns:
                info += f"  - {col[0]} ({col[1]})\n"
            
            info += "Sample Data:\n"
            for row in sample_data:
                info += f"  {row}\n"
                
            return info
            
        except Exception as e:
            print(f"Error getting table info: {e}")
            return f"Error getting info for table {table_name}: {e}"

def connect_to_mysql():
    """
    Connect to MySQL database
    
    Returns:
        MySQLDatabase: A database connection object with run method
    """
    try:
        db = MySQLDatabase(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        return db
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise

def run_query_with_retry(query, max_retries=3, delay=2):
    """
    Run a SQL query with retry logic
    
    Args:
        query: SQL query string
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        list of tuples containing the query results
    """
    for attempt in range(max_retries):
        try:
            db = connect_to_mysql()
            return db.run(query)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt+1} failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"All {max_retries} attempts failed. Last error: {e}")
                return []

def check_network_connectivity():
    """
    Check network connectivity to the database server
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        # Get local machine IP
        local_ip = socket.gethostbyname(socket.gethostname())
        print(f"Local IP address: {local_ip}")
        
        # Try to connect to the database server on the MySQL port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((DB_HOST, DB_PORT))
        if result == 0:
            print(f"Successfully connected to {DB_HOST}:{DB_PORT}")
            sock.close()
            return True
        else:
            print(f"Failed to connect to {DB_HOST}:{DB_PORT}. Error code: {result}")
            sock.close()
            return False
    except Exception as e:
        print(f"Network connectivity check failed: {e}")
        return False

def test_connection():
    """
    Test the database connection and print some basic information
    """
    try:
        # Check network connectivity first
        print("Checking network connectivity...")
        check_network_connectivity()
        
        # Try direct connection
        print("\nTesting direct PyMySQL connection...")
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            connect_timeout=10
        )
        print("Direct connection successful!")
        conn.close()
        
        # Connect to the database using our wrapper
        print("\nTesting MySQLDatabase connection...")
        db = connect_to_mysql()
        
        # Print database dialect
        print(f"Database dialect: {db.dialect}")
        
        # Get and print available tables
        tables = db.get_usable_table_names()
        print(f"Available tables: {tables}")
        
        # If there are tables, query the first one as an example
        if tables:
            first_table = tables[0]
            print(f"\nSample data from {first_table} table:")
            query = f"SELECT * FROM {first_table} LIMIT 5;"
            
            # Use our custom function
            result = db.run(query)
            print(f"Result format: {result}")
            
            # Also show as DataFrame for readability
            conn = pymysql.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT
            )
            df = pd.read_sql(query, conn)
            print("\nAs DataFrame:")
            print(df)
            conn.close()
        
        # Test LangChain SQLDatabase
        print("\nTesting LangChain SQLDatabase connection...")
        try:
            langchain_db = connect_to_mysql_langchain()
            print("LangChain connection successful!")
            
            # Test run method on LangChain SQLDatabase
            if tables:
                first_table = tables[0]
                print(f"\nSample data from {first_table} table using LangChain:")
                query = f"SELECT * FROM {first_table} LIMIT 5;"
                result = langchain_db.run(query)
                print(f"Result format: {result}")
        except Exception as e:
            print(f"LangChain connection failed: {e}")
            print("This is expected if using SQLAlchemy with this database has connection issues.")
            print("You can still use the direct PyMySQL connection for your queries.")
            
        return True
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if the database server allows connections from your IP address")
        print("2. Verify the database credentials are correct")
        print("3. Make sure the database server is running and accessible")
        print("4. Check if there are any firewall rules blocking the connection")
        print("5. Check if your VPN is connected (if required)")
        print("6. Verify that the Alibaba Cloud RDS instance is running")
        print("7. Check if the database user has permissions to connect from your IP")
        return False

if __name__ == "__main__":
    test_connection()
    
    # Example of using the run method
    print("\nExample query using db.run():")
    try:
        db = connect_to_mysql()
        example_query = "SHOW TABLES;"
        result = db.run(example_query)
        print(f"Query result: {result}")
        
        # Example with a specific query format like in the SQLite example
        print("\nExample classes query (if table exists):")
        classes_query = "SELECT * FROM classes LIMIT 10;"
        classes_result = db.run(classes_query)
        print(f"Classes query result: {classes_result}")
    except Exception as e:
        print(f"Query failed: {e}")