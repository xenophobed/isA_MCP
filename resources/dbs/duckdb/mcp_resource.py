"""
DuckDB MCP Resource Interface
为MCP系统提供DuckDB数据库资源访问接口

Features:
- MCP标准资源接口实现
- 安全的数据访问控制
- 查询结果缓存
- 实时查询监控
- 多格式数据导出
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from urllib.parse import urlparse, parse_qs

from mcp.types import Resource, TextResourceContents, BlobResourceContents
from mcp.server.session import ServerSession

from .core import (
    DuckDBService, AccessLevel, ConnectionConfig, 
    PoolConfig, SecurityConfig, get_duckdb_service
)


logger = logging.getLogger(__name__)


class DuckDBResourceProvider:
    """DuckDB MCP资源提供器"""
    
    def __init__(self, 
                 service: Optional[DuckDBService] = None,
                 cache_ttl: float = 300.0,  # 5分钟缓存
                 max_cache_size: int = 100):
        self.service = service or get_duckdb_service()
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        
        # 查询结果缓存
        self._query_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_access_times: Dict[str, float] = {}
        
        # 支持的资源URI模式
        self.uri_patterns = [
            "duckdb://query/",      # SQL查询
            "duckdb://table/",      # 表访问
            "duckdb://schema/",     # 模式信息
            "duckdb://stats/",      # 统计信息
            "duckdb://export/"      # 数据导出
        ]
        
        logger.info("DuckDB Resource Provider initialized")
    
    async def list_resources(self, session: ServerSession) -> List[Resource]:
        """列出可用的DuckDB资源"""
        try:
            resources = []
            
            # 基础查询接口
            resources.append(Resource(
                uri="duckdb://query/?sql=SELECT 1 as test",
                name="DuckDB SQL Query",
                description="Execute SQL queries against DuckDB",
                mimeType="application/json"
            ))
            
            # 获取数据库中的表列表
            try:
                tables = self.service.execute_query(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'",
                    access_level=AccessLevel.READ_ONLY
                )
                
                for table_row in tables or []:
                    table_name = table_row[0]
                    resources.append(Resource(
                        uri=f"duckdb://table/{table_name}",
                        name=f"Table: {table_name}",
                        description=f"Access to table {table_name}",
                        mimeType="application/json"
                    ))
                    
                    # 表导出资源
                    resources.append(Resource(
                        uri=f"duckdb://export/{table_name}?format=csv",
                        name=f"Export {table_name} (CSV)",
                        description=f"Export table {table_name} as CSV",
                        mimeType="text/csv"
                    ))
                    
            except Exception as e:
                logger.warning(f"Failed to list tables: {e}")
            
            # 数据库统计信息
            resources.append(Resource(
                uri="duckdb://stats/service",
                name="DuckDB Service Statistics",
                description="Service performance and connection statistics",
                mimeType="application/json"
            ))
            
            # 模式信息
            resources.append(Resource(
                uri="duckdb://schema/",
                name="Database Schema Information",
                description="Information about database structure",
                mimeType="application/json"
            ))
            
            return resources
            
        except Exception as e:
            logger.error(f"Failed to list DuckDB resources: {e}")
            return []
    
    async def read_resource(self, session: ServerSession, uri: str) -> Union[TextResourceContents, BlobResourceContents]:
        """读取DuckDB资源"""
        try:
            parsed_uri = urlparse(uri)
            path_parts = parsed_uri.path.strip('/').split('/')
            query_params = parse_qs(parsed_uri.query)
            
            logger.debug(f"Reading DuckDB resource: {uri}")
            
            if not path_parts or path_parts[0] not in ['query', 'table', 'schema', 'stats', 'export']:
                raise ValueError(f"Invalid DuckDB resource URI: {uri}")
            
            resource_type = path_parts[0]
            
            # 处理不同类型的资源请求
            if resource_type == 'query':
                return await self._handle_query_resource(query_params)
            elif resource_type == 'table':
                return await self._handle_table_resource(path_parts, query_params)
            elif resource_type == 'schema':
                return await self._handle_schema_resource(path_parts, query_params)
            elif resource_type == 'stats':
                return await self._handle_stats_resource(path_parts, query_params)
            elif resource_type == 'export':
                return await self._handle_export_resource(path_parts, query_params)
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")
                
        except Exception as e:
            logger.error(f"Failed to read DuckDB resource {uri}: {e}")
            return TextResourceContents(
                uri=uri,
                mimeType="application/json",
                text=json.dumps({
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, indent=2)
            )
    
    async def _handle_query_resource(self, query_params: Dict[str, List[str]]) -> TextResourceContents:
        """处理SQL查询资源"""
        if 'sql' not in query_params:
            raise ValueError("Missing 'sql' parameter in query")
        
        sql_query = query_params['sql'][0]
        format_type = query_params.get('format', ['json'])[0]
        use_cache = query_params.get('cache', ['true'])[0].lower() == 'true'
        
        # 检查缓存
        cache_key = f"query:{hash(sql_query)}:{format_type}"
        if use_cache and cache_key in self._query_cache:
            cached_data = self._query_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                self._cache_access_times[cache_key] = time.time()
                logger.debug(f"Cache hit for query: {sql_query[:50]}...")
                
                return TextResourceContents(
                    uri=f"duckdb://query/?sql={sql_query}",
                    mimeType="application/json",
                    text=cached_data['content']
                )
        
        # 执行查询
        start_time = time.time()
        
        try:
            if format_type == 'dataframe':
                # 返回DataFrame格式（JSON序列化）
                df = self.service.execute_query_df(
                    sql_query, 
                    framework='pandas',
                    access_level=AccessLevel.READ_ONLY
                )
                result_data = {
                    "query": sql_query,
                    "format": format_type,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                    "row_count": len(df),
                    "columns": df.columns.tolist(),
                    "data": df.to_dict('records'),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # 标准查询结果
                rows = self.service.execute_query(
                    sql_query,
                    access_level=AccessLevel.READ_ONLY
                )
                
                # 获取列信息
                with self.service.pool.get_connection(AccessLevel.READ_ONLY) as conn:
                    conn.execute(sql_query)
                    columns = [desc[0] for desc in conn.connection.description] if conn.connection.description else []
                
                result_data = {
                    "query": sql_query,
                    "format": format_type,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                    "row_count": len(rows) if rows else 0,
                    "columns": columns,
                    "data": rows or [],
                    "timestamp": datetime.now().isoformat()
                }
            
            # 缓存结果
            if use_cache:
                content = json.dumps(result_data, indent=2, default=str)
                self._add_to_cache(cache_key, content)
            else:
                content = json.dumps(result_data, indent=2, default=str)
            
            return TextResourceContents(
                uri=f"duckdb://query/?sql={sql_query}",
                mimeType="application/json",
                text=content
            )
            
        except Exception as e:
            error_data = {
                "error": str(e),
                "query": sql_query,
                "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            return TextResourceContents(
                uri=f"duckdb://query/?sql={sql_query}",
                mimeType="application/json",
                text=json.dumps(error_data, indent=2)
            )
    
    async def _handle_table_resource(self, path_parts: List[str], query_params: Dict[str, List[str]]) -> TextResourceContents:
        """处理表资源访问"""
        if len(path_parts) < 2:
            raise ValueError("Table name required")
        
        table_name = path_parts[1]
        limit = int(query_params.get('limit', ['1000'])[0])
        offset = int(query_params.get('offset', ['0'])[0])
        
        # 构建查询
        query = f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}"
        
        # 获取表信息
        try:
            # 表统计信息
            count_result = self.service.execute_query(
                f"SELECT COUNT(*) FROM {table_name}",
                access_level=AccessLevel.READ_ONLY
            )
            total_rows = count_result[0][0] if count_result else 0
            
            # 表结构信息
            schema_result = self.service.execute_query(
                f"DESCRIBE {table_name}",
                access_level=AccessLevel.READ_ONLY
            )
            
            # 表数据
            data_result = self.service.execute_query(
                query,
                access_level=AccessLevel.READ_ONLY
            )
            
            # 获取列名
            with self.service.pool.get_connection(AccessLevel.READ_ONLY) as conn:
                conn.execute(f"SELECT * FROM {table_name} LIMIT 1")
                columns = [desc[0] for desc in conn.connection.description] if conn.connection.description else []
            
            result_data = {
                "table_name": table_name,
                "total_rows": total_rows,
                "limit": limit,
                "offset": offset,
                "returned_rows": len(data_result) if data_result else 0,
                "schema": [{"column": row[0], "type": row[1]} for row in schema_result] if schema_result else [],
                "columns": columns,
                "data": data_result or [],
                "timestamp": datetime.now().isoformat()
            }
            
            return TextResourceContents(
                uri=f"duckdb://table/{table_name}",
                mimeType="application/json",
                text=json.dumps(result_data, indent=2, default=str)
            )
            
        except Exception as e:
            error_data = {
                "error": str(e),
                "table_name": table_name,
                "timestamp": datetime.now().isoformat()
            }
            
            return TextResourceContents(
                uri=f"duckdb://table/{table_name}",
                mimeType="application/json",
                text=json.dumps(error_data, indent=2)
            )
    
    async def _handle_schema_resource(self, path_parts: List[str], query_params: Dict[str, List[str]]) -> TextResourceContents:
        """处理数据库模式信息"""
        try:
            # 获取所有表
            tables_result = self.service.execute_query(
                """
                SELECT table_name, table_type
                FROM information_schema.tables 
                WHERE table_schema = 'main'
                ORDER BY table_name
                """,
                access_level=AccessLevel.READ_ONLY
            )
            
            schema_info = {
                "database_path": self.service.connection_config.database_path,
                "tables": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # 获取每个表的详细信息
            for table_row in tables_result or []:
                table_name, table_type = table_row
                
                # 表结构
                columns_result = self.service.execute_query(
                    f"DESCRIBE {table_name}",
                    access_level=AccessLevel.READ_ONLY
                )
                
                # 表统计
                count_result = self.service.execute_query(
                    f"SELECT COUNT(*) FROM {table_name}",
                    access_level=AccessLevel.READ_ONLY
                )
                
                table_info = {
                    "name": table_name,
                    "type": table_type,
                    "row_count": count_result[0][0] if count_result else 0,
                    "columns": [
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2] if len(col) > 2 else None,
                            "key": col[3] if len(col) > 3 else None
                        }
                        for col in columns_result or []
                    ]
                }
                
                schema_info["tables"].append(table_info)
            
            return TextResourceContents(
                uri="duckdb://schema/",
                mimeType="application/json",
                text=json.dumps(schema_info, indent=2, default=str)
            )
            
        except Exception as e:
            error_data = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            return TextResourceContents(
                uri="duckdb://schema/",
                mimeType="application/json",
                text=json.dumps(error_data, indent=2)
            )
    
    async def _handle_stats_resource(self, path_parts: List[str], query_params: Dict[str, List[str]]) -> TextResourceContents:
        """处理统计信息资源"""
        try:
            service_stats = self.service.get_service_stats()
            
            # 添加缓存统计
            cache_stats = {
                "cache_size": len(self._query_cache),
                "cache_hit_ratio": self._calculate_cache_hit_ratio(),
                "oldest_cache_entry": min(self._cache_access_times.values()) if self._cache_access_times else None
            }
            
            stats_data = {
                "service_stats": service_stats,
                "cache_stats": cache_stats,
                "timestamp": datetime.now().isoformat()
            }
            
            return TextResourceContents(
                uri="duckdb://stats/service",
                mimeType="application/json",
                text=json.dumps(stats_data, indent=2, default=str)
            )
            
        except Exception as e:
            error_data = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            return TextResourceContents(
                uri="duckdb://stats/service",
                mimeType="application/json",
                text=json.dumps(error_data, indent=2)
            )
    
    async def _handle_export_resource(self, path_parts: List[str], query_params: Dict[str, List[str]]) -> Union[TextResourceContents, BlobResourceContents]:
        """处理数据导出资源"""
        if len(path_parts) < 2:
            raise ValueError("Table name required for export")
        
        table_name = path_parts[1]
        export_format = query_params.get('format', ['csv'])[0].lower()
        
        try:
            if export_format == 'csv':
                # 导出为CSV
                df = self.service.execute_query_df(
                    f"SELECT * FROM {table_name}",
                    framework='pandas',
                    access_level=AccessLevel.READ_ONLY
                )
                
                csv_content = df.to_csv(index=False)
                
                return TextResourceContents(
                    uri=f"duckdb://export/{table_name}?format=csv",
                    mimeType="text/csv",
                    text=csv_content
                )
                
            elif export_format == 'json':
                # 导出为JSON
                df = self.service.execute_query_df(
                    f"SELECT * FROM {table_name}",
                    framework='pandas',
                    access_level=AccessLevel.READ_ONLY
                )
                
                json_content = df.to_json(orient='records', indent=2)
                
                return TextResourceContents(
                    uri=f"duckdb://export/{table_name}?format=json",
                    mimeType="application/json",
                    text=json_content
                )
                
            else:
                raise ValueError(f"Unsupported export format: {export_format}")
                
        except Exception as e:
            error_data = {
                "error": str(e),
                "table_name": table_name,
                "format": export_format,
                "timestamp": datetime.now().isoformat()
            }
            
            return TextResourceContents(
                uri=f"duckdb://export/{table_name}?format={export_format}",
                mimeType="application/json",
                text=json.dumps(error_data, indent=2)
            )
    
    def _add_to_cache(self, key: str, content: str):
        """添加到缓存"""
        # 如果缓存已满，移除最老的条目
        if len(self._query_cache) >= self.max_cache_size:
            oldest_key = min(self._cache_access_times.keys(), 
                           key=lambda k: self._cache_access_times[k])
            del self._query_cache[oldest_key]
            del self._cache_access_times[oldest_key]
        
        self._query_cache[key] = {
            'content': content,
            'timestamp': time.time()
        }
        self._cache_access_times[key] = time.time()
    
    def _calculate_cache_hit_ratio(self) -> float:
        """计算缓存命中率"""
        # 这里需要更复杂的统计逻辑
        # 简化版本，返回0.0
        return 0.0
    
    def clear_cache(self):
        """清空缓存"""
        self._query_cache.clear()
        self._cache_access_times.clear()
        logger.info("DuckDB resource cache cleared")
    
    async def shutdown(self):
        """关闭资源提供器"""
        self.clear_cache()
        logger.info("DuckDB Resource Provider shutdown")


# 全局资源提供器实例
_resource_provider: Optional[DuckDBResourceProvider] = None


def get_duckdb_resource_provider(service: Optional[DuckDBService] = None) -> DuckDBResourceProvider:
    """获取DuckDB资源提供器实例"""
    global _resource_provider
    
    if _resource_provider is None:
        _resource_provider = DuckDBResourceProvider(service)
    
    return _resource_provider