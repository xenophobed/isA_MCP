#!/usr/bin/env python3
"""
Data Analytics Tools
Intelligent data analytics tools based on BaseTool
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from tools.base_tool import BaseTool
from tools.services.data_analytics_service.services.data_analytics_service import DataAnalyticsService, get_analytics_service
from core.logging import get_logger

logger = get_logger(__name__)

class DataAnalyticsTool(BaseTool):
    """Data analytics tool for processing data sources and natural language queries"""
    
    def __init__(self):
        super().__init__()
        self.services = {}  # Cache for service instances
    
    def _get_service(self, database_name: str = "default_analytics") -> DataAnalyticsService:
        """Get or create service instance"""
        if database_name not in self.services:
            self.services[database_name] = get_analytics_service(database_name)
        return self.services[database_name]
    
    async def ingest_data_source(
        self,
        source_path: str,
        database_name: str = "default_analytics",
        source_type: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> str:
        """
        Function 1: Data Ingestion (Steps 1-3)
        Process data source and store in SQLite database + pgvector embeddings
        
        Args:
            source_path: Path to data source (CSV, Excel, JSON, database)
            database_name: Name of the analytics database
            source_type: Optional source type override ("csv", "json", etc.)
            request_id: Optional custom request identifier
        """
        print(f"Starting data ingestion: {source_path}")
        
        try:
            service = self._get_service(database_name)
            
            result = await service.ingest_data_source(
                source_path=source_path,
                source_type=source_type,
                request_id=request_id
            )
            
            if result["success"]:
                print(f"Data ingestion completed: {result['metadata_pipeline']['embeddings_stored']} embeddings stored")
            else:
                print(f"Data ingestion failed: {result['error_message']}")
            
            return self.create_response(
                "success" if result["success"] else "error",
                "ingest_data_source",
                result,
                result.get("error_message") if not result["success"] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "ingest_data_source",
                {},
                f"Data ingestion failed: {str(e)}"
            )
    
    async def query_with_language(
        self,
        natural_language_query: str,
        sqlite_database_path: str,
        pgvector_database: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> str:
        """
        Function 2: Query Processing (Steps 4-6)
        Process natural language query using SQLite database + pgvector embeddings
        
        Args:
            natural_language_query: User's natural language query
            sqlite_database_path: Path to SQLite database with the data
            pgvector_database: Name of pgvector database (defaults to service database)
            request_id: Optional custom request identifier
        """
        print(f"Processing query: {natural_language_query}")
        
        try:
            # Use pgvector_database as the service name if provided
            database_name = pgvector_database or "default_analytics"
            service = self._get_service(database_name)
            
            result = await service.query_with_language(
                natural_language_query=natural_language_query,
                sqlite_database_path=sqlite_database_path,
                pgvector_database=pgvector_database,
                request_id=request_id
            )
            
            if result["success"]:
                print(f"Query completed: {result['results']['row_count']} rows returned")
            else:
                print(f"Query failed: {result['error_message']}")
            
            return self.create_response(
                "success" if result["success"] else "error",
                "query_with_language",
                result,
                result.get("error_message") if not result["success"] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "query_with_language",
                {},
                f"Query processing failed: {str(e)}"
            )
    
    async def process_data_source_and_query(
        self,
        source_path: str,
        natural_language_query: str,
        database_name: str = "default_analytics",
        source_type: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> str:
        """
        Convenience method: Combines both functions for end-to-end processing
        First ingests data source, then processes query
        
        Args:
            source_path: Path to data source
            natural_language_query: User's natural language query
            database_name: Name of the analytics database
            source_type: Optional source type override
            request_id: Optional request identifier
        """
        print(f"Starting end-to-end processing: {source_path} -> {natural_language_query}")
        
        try:
            service = self._get_service(database_name)
            
            result = await service.process_data_source_and_query(
                source_path=source_path,
                natural_language_query=natural_language_query,
                source_type=source_type,
                request_id=request_id
            )
            
            if result["success"]:
                print(f"End-to-end processing completed successfully")
            else:
                print(f"End-to-end processing failed: {result['error_message']}")
            
            return self.create_response(
                "success" if result["success"] else "error",
                "process_data_source_and_query",
                result,
                result.get("error_message") if not result["success"] else None
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "process_data_source_and_query",
                {},
                f"End-to-end processing failed: {str(e)}"
            )
    
    async def search_available_data(
        self,
        search_query: str,
        database_name: str = "default_analytics",
        limit: int = 10
    ) -> str:
        """
        Search across all processed metadata
        
        Args:
            search_query: Natural language search query
            database_name: Name of the analytics database
            limit: Maximum number of results
        """
        print(f"Searching metadata: {search_query}")
        
        try:
            service = self._get_service(database_name)
            
            results = await service.search_available_data(search_query, limit)
            
            search_result = {
                "success": True,
                "search_query": search_query,
                "database_name": database_name,
                "results_count": len(results),
                "results": results,
                "limit": limit
            }
            
            print(f"Search completed: {len(results)} results found")
            
            return self.create_response(
                "success",
                "search_available_data",
                search_result
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "search_available_data",
                {},
                f"Search failed: {str(e)}"
            )
    
    async def get_service_status(
        self,
        database_name: str = "default_analytics"
    ) -> str:
        """
        Get comprehensive service status and statistics
        
        Args:
            database_name: Name of the analytics database
        """
        print(f"Getting service status for: {database_name}")
        
        try:
            service = self._get_service(database_name)
            
            status = await service.get_service_status()
            
            print(f"Service status retrieved successfully")
            
            return self.create_response(
                "success",
                "get_service_status",
                status
            )
            
        except Exception as e:
            return self.create_response(
                "error",
                "get_service_status",
                {},
                f"Status retrieval failed: {str(e)}"
            )

def register_data_analytics_tools(mcp: FastMCP):
    """Register data analytics tools"""
    analytics_tool = DataAnalyticsTool()
    
    @mcp.tool()
    async def ingest_data_source(
        source_path: str,
        database_name: str = "default_analytics",
        source_type: str = None,
        request_id: str = None
    ) -> str:
        """
        Function 1: Data Ingestion (Steps 1-3)
        Process data source and store in SQLite database + pgvector embeddings for querying
        
        This tool processes data sources (CSV, Excel, JSON, databases) through a 3-step pipeline:
        1. Metadata extraction from the data source
        2. AI semantic enrichment of the metadata
        3. Embedding generation and storage in pgvector database
        
        Keywords: ingest, data, csv, excel, json, database, metadata, embeddings, process
        Category: data_analytics
        
        Args:
            source_path: Path to data source (CSV, Excel, JSON, database)
            database_name: Name of the analytics database (default: "default_analytics")
            source_type: Optional source type override ("csv", "json", "excel", etc.)
            request_id: Optional custom request identifier
        
        Returns:
            JSON with success status, SQLite database path, pgvector database name, and processing metrics
        """
        return await analytics_tool.ingest_data_source(
            source_path, database_name, source_type, request_id
        )
    
    @mcp.tool()
    async def query_with_language(
        natural_language_query: str,
        sqlite_database_path: str,
        pgvector_database: str = None,
        request_id: str = None
    ) -> str:
        """
        Function 2: Query Processing (Steps 4-6)
        Process natural language queries against ingested data using SQLite database + pgvector embeddings
        
        This tool processes natural language queries through a 3-step pipeline:
        4. Query context extraction and metadata matching using pgvector embeddings
        5. AI-powered SQL generation from the natural language query
        6. SQL execution against the SQLite database with fallback mechanisms
        
        Keywords: query, language, sql, natural, search, ask, find, show, list, get
        Category: data_analytics
        
        Args:
            natural_language_query: User's natural language query (e.g., "Show customers from China")
            sqlite_database_path: Path to SQLite database with the data
            pgvector_database: Name of pgvector database (optional, defaults to service database)
            request_id: Optional custom request identifier
        
        Returns:
            JSON with success status, generated SQL, query results, and processing metrics
        """
        return await analytics_tool.query_with_language(
            natural_language_query, sqlite_database_path, pgvector_database, request_id
        )
    
    @mcp.tool()
    async def process_data_source_and_query(
        source_path: str,
        natural_language_query: str,
        database_name: str = "default_analytics",
        source_type: str = None,
        request_id: str = None
    ) -> str:
        """
        Convenience Method: Complete End-to-End Data Analytics
        Combines both functions (1+2) for complete processing: data ingestion then query processing
        
        This tool provides complete end-to-end data analytics by:
        1. First calling ingest_data_source() to process the data
        2. Then calling query_with_language() to answer the query
        3. Automatically coordinates database paths between both functions
        
        Keywords: complete, end-to-end, analytics, process, query, data, workflow
        Category: data_analytics
        
        Args:
            source_path: Path to data source (CSV, Excel, JSON, database)
            natural_language_query: User's natural language query
            database_name: Name of the analytics database (default: "default_analytics")
            source_type: Optional source type override ("csv", "json", "excel", etc.)
            request_id: Optional custom request identifier
        
        Returns:
            JSON with combined results from both ingestion and query processing
        """
        return await analytics_tool.process_data_source_and_query(
            source_path, natural_language_query, database_name, source_type, request_id
        )
    
    @mcp.tool()
    async def search_available_data(
        search_query: str,
        database_name: str = "default_analytics",
        limit: int = 10
    ) -> str:
        """
        Search across all processed metadata using AI-powered similarity
        
        This tool searches through all previously ingested data sources using semantic search
        to find relevant metadata, tables, columns, and business entities.
        
        Keywords: search, metadata, find, discover, explore, available, data
        Category: data_analytics
        
        Args:
            search_query: Natural language search query (e.g., "customer contact information")
            database_name: Name of the analytics database (default: "default_analytics")
            limit: Maximum number of results to return (default: 10)
        
        Returns:
            JSON with search results including entity names, types, similarity scores, and metadata
        """
        return await analytics_tool.search_available_data(
            search_query, database_name, limit
        )
    
    @mcp.tool()
    async def get_analytics_status(
        database_name: str = "default_analytics"
    ) -> str:
        """
        Get comprehensive analytics service status and statistics
        
        This tool provides detailed information about the analytics service including:
        - Service configuration and status
        - Processing statistics (requests, success rates, costs)
        - Database summary and available data
        - Recent processing history
        
        Keywords: status, analytics, statistics, service, info, health, summary
        Category: data_analytics
        
        Args:
            database_name: Name of the analytics database (default: "default_analytics")
        
        Returns:
            JSON with comprehensive service status, statistics, and database information
        """
        return await analytics_tool.get_service_status(database_name)
    
    print("Data Analytics tools registered successfully")