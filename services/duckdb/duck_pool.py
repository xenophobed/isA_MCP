# app/services/db/duckdb/duck_pool.py
import duckdb
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DuckDBConnectionPool:
    def __init__(
        self,
        database: str,
        min_connections: int = 1,
        max_connections: int = 10,
        threads: int = 4,
        memory_limit: str = '4GB',
        temp_directory: str = None,
        max_idle_time: int = 300
    ):
        self.database = database
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.threads = threads
        self.memory_limit = memory_limit
        self.temp_directory = temp_directory
        self.max_idle_time = max_idle_time
        
        self._pool = []
        self._in_use = set()
        
        logger.debug(f"Initializing DuckDBConnectionPool with params: "
                    f"database={database}, min_connections={min_connections}, "
                    f"max_connections={max_connections}, threads={threads}, "
                    f"memory_limit={memory_limit}, temp_directory={temp_directory}, "
                    f"max_idle_time={max_idle_time}")
        
        self._initialize_minimum_connections()
    
    def _initialize_minimum_connections(self):
        """初始化最小连接数"""
        try:
            for _ in range(self.min_connections):
                conn = self._create_connection()
                self._pool.append(conn)
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {str(e)}")
            raise
    
    def _create_connection(self):
        """创建新的数据库连接"""
        try:
            config = {
                'threads': self.threads,
                'memory_limit': self.memory_limit
            }
            if self.temp_directory:
                config['temp_directory'] = self.temp_directory
                
            connection = duckdb.connect(
                database=self.database,
                read_only=False,
                config=config
            )
            
            logger.debug(f"Created new DuckDB connection to {self.database}")
            return connection
        except Exception as e:
            logger.error(f"Error creating connection: {str(e)}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        connection = None
        try:
            if self._pool:
                connection = self._pool.pop()
            elif len(self._in_use) < self.max_connections:
                connection = self._create_connection()
            else:
                raise Exception("Connection pool exhausted")
            
            self._in_use.add(connection)
            yield connection
            
        finally:
            if connection:
                if connection in self._in_use:
                    self._in_use.remove(connection)
                # 检查连接是否有效，有效则放回池中，无效则创建新连接
                try:
                    connection.execute("SELECT 1")  # 测试连接是否有效
                    self._pool.append(connection)
                except:
                    try:
                        connection.close()
                    except:
                        pass
                    if len(self._pool) < self.min_connections:
                        self._pool.append(self._create_connection())
    
    def close_all(self):
        """关闭所有连接"""
        for conn in self._pool + list(self._in_use):
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
        
        self._pool.clear()
        self._in_use.clear()