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
        request_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> str:
        """
        Function 1: Data Ingestion (Steps 1-3)
        Process data source and store in SQLite database + pgvector embeddings
        
        Args:
            source_path: Path to data source (CSV, Excel, JSON, database)
            database_name: Name of the analytics database
            source_type: Optional source type override ("csv", "json", etc.)
            request_id: Optional custom request identifier
            user_id: Optional user ID for resource isolation and tracking
        """
        print(f"Starting data ingestion: {source_path}")
        
        # Use user_id to generate database name if provided
        if user_id:
            database_name = f"user_{user_id}_analytics"
        
        try:
            service = self._get_service(database_name)
            
            result = await service.ingest_data_source(
                source_path=source_path,
                source_type=source_type,
                request_id=request_id,
                user_id=user_id
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
        sqlite_database_path: Optional[str] = None,
        pgvector_database: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> str:
        """
        Function 2: Query Processing (Steps 4-6)
        Process natural language query using SQLite database + pgvector embeddings
        
        Args:
            natural_language_query: User's natural language query
            sqlite_database_path: Path to SQLite database with the data
            pgvector_database: Name of pgvector database (defaults to service database)
            request_id: Optional custom request identifier
            user_id: Optional user ID for resource isolation and tracking
        """
        print(f"Processing query: {natural_language_query}")
        
        try:
            # Use user_id to generate database name if provided, otherwise use pgvector_database
            if user_id:
                database_name = f"user_{user_id}_analytics"
                
                # Auto-detect SQLite path from user resources if not provided
                if not sqlite_database_path:
                    try:
                        from resources.data_analytics_resource import data_analytics_resources
                        user_resources = await data_analytics_resources.get_user_resources(user_id)
                        
                        if user_resources['success'] and user_resources['resources']:
                            # Find the most recent data source
                            data_sources = [r for r in user_resources['resources'] if r['type'] == 'data_source']
                            if data_sources:
                                latest_source = data_sources[-1]
                                sqlite_database_path = latest_source['metadata']['sqlite_database_path']
                                print(f"Auto-detected SQLite path: {sqlite_database_path}")
                    except Exception as e:
                        print(f"Warning: Could not auto-detect SQLite path: {e}")
            else:
                database_name = pgvector_database or "default_analytics"
                
            service = self._get_service(database_name)
            
            result = await service.query_with_language(
                natural_language_query=natural_language_query,
                sqlite_database_path=sqlite_database_path,
                pgvector_database=pgvector_database,
                request_id=request_id,
                user_id=user_id
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
        user_id: int,
        source_type: str = None,
        request_id: str = None,
        database_name: str = None
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
            user_id: User ID for resource isolation and database naming (required)
            source_type: Optional source type override ("csv", "json", "excel", etc.)
            request_id: Optional custom request identifier
            database_name: Optional database name override (auto-generated from user_id if not provided)
        
        Returns:
            JSON with success status, SQLite database path, pgvector database name, and processing metrics
        """
        # Auto-generate database name from user_id if not provided
        if not database_name:
            database_name = f"user_{user_id}_analytics"
        
        return await analytics_tool.ingest_data_source(
            source_path, database_name, source_type, request_id, user_id
        )
    
    @mcp.tool()
    async def query_with_language(
        natural_language_query: str,
        user_id: int,
        sqlite_database_path: str = None,
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
            user_id: User ID for database identification and resource isolation (required)
            sqlite_database_path: Path to SQLite database (optional, auto-detected from user resources)
            pgvector_database: Name of pgvector database (optional, auto-generated from user_id)
            request_id: Optional custom request identifier
        
        Returns:
            JSON with success status, generated SQL, query results, and processing metrics
        """
        # Auto-generate database name from user_id if not provided
        if not pgvector_database:
            pgvector_database = f"user_{user_id}_analytics"
        
        # Auto-detect SQLite path from user resources if not provided
        if not sqlite_database_path:
            try:
                from resources.data_analytics_resource import data_analytics_resources
                user_resources = await data_analytics_resources.get_user_resources(user_id)
                
                if user_resources['success'] and user_resources['resources']:
                    # Find the most recent data source
                    data_sources = [r for r in user_resources['resources'] if r['type'] == 'data_source']
                    if data_sources:
                        latest_source = data_sources[-1]
                        sqlite_database_path = latest_source['metadata']['sqlite_database_path']
            except Exception as e:
                # If resource lookup fails, we'll let the query fail with appropriate error
                pass
        
        return await analytics_tool.query_with_language(
            natural_language_query, sqlite_database_path, pgvector_database, request_id, user_id
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
    async def perform_eda_analysis(
        data_path: str,
        target_column: str = None,
        include_ai_insights: bool = True,
        request_id: str = None
    ) -> str:
        """
        Perform comprehensive exploratory data analysis (EDA) on any dataset
        
        This tool analyzes datasets to understand data patterns, relationships, and quality:
        - Statistical analysis and correlations
        - Feature importance and contribution analysis  
        - Data quality assessment
        - AI-generated insights and recommendations
        
        Perfect for: understanding data patterns, finding key factors, data quality checks
        
        Keywords: eda, analysis, explore, statistics, correlation, features, insights, patterns
        Category: data_analytics
        
        Args:
            data_path: Path to data file (CSV, Excel, JSON, etc.)
            target_column: Optional target column to focus analysis on (e.g., "sales", "revenue")
            include_ai_insights: Whether to include AI-generated insights (default: True)
            request_id: Optional custom request identifier
        
        Returns:
            JSON with comprehensive EDA results including statistics, correlations, and insights
        """
        analytics_tool = DataAnalyticsTool()
        service = analytics_tool._get_service("default_analytics")
        
        result = await service.perform_exploratory_data_analysis(
            data_path=data_path,
            target_column=target_column,
            include_ai_insights=include_ai_insights,
            request_id=request_id
        )
        
        return analytics_tool.create_response(
            "success" if result["success"] else "error",
            "perform_eda_analysis", 
            result,
            result.get("error_message") if not result["success"] else None
        )

    @mcp.tool()
    async def develop_ml_model(
        data_path: str,
        target_column: str,
        problem_type: str = None,
        include_feature_engineering: bool = True,
        include_ai_guidance: bool = True,
        request_id: str = None
    ) -> str:
        """
        Develop machine learning models for prediction and forecasting
        
        This tool builds ML models for various prediction tasks:
        - Time series forecasting (Prophet, ARIMA) for sales/revenue prediction
        - Classification models for categorical predictions
        - Regression models for numerical predictions
        - Automatic feature engineering and model selection
        
        Perfect for: sales forecasting, demand prediction, trend analysis, predictive modeling
        
        Keywords: model, prediction, forecast, prophet, time series, ml, machine learning
        Category: data_analytics
        
        Args:
            data_path: Path to data file (CSV, Excel, JSON, etc.)
            target_column: Target variable to predict (e.g., "sales", "revenue", "demand")
            problem_type: Type of problem - "regression", "classification", "time_series", or auto-detect
            include_feature_engineering: Whether to perform automatic feature engineering (default: True)
            include_ai_guidance: Whether to include AI modeling guidance (default: True)
            request_id: Optional custom request identifier
        
        Returns:
            JSON with model results including performance metrics, predictions, and recommendations
        """
        analytics_tool = DataAnalyticsTool()
        service = analytics_tool._get_service("default_analytics")
        
        result = await service.develop_machine_learning_model(
            data_path=data_path,
            target_column=target_column,
            problem_type=problem_type,
            include_feature_engineering=include_feature_engineering,
            include_ai_guidance=include_ai_guidance,
            request_id=request_id
        )
        
        return analytics_tool.create_response(
            "success" if result["success"] else "error",
            "develop_ml_model",
            result, 
            result.get("error_message") if not result["success"] else None
        )

    @mcp.tool()
    async def perform_statistical_analysis(
        data_path: str,
        analysis_type: str = "comprehensive",
        target_columns: str = None,
        request_id: str = None
    ) -> str:
        """
        Perform comprehensive statistical analysis including hypothesis testing, correlations, and distributions
        
        This tool provides advanced statistical analysis capabilities:
        - Hypothesis testing (t-tests, Mann-Whitney U, chi-square tests)
        - Correlation analysis (Pearson, Spearman, Kendall)
        - Distribution analysis and normality testing
        - Outlier detection using multiple methods
        - Categorical variable analysis
        
        Perfect for: understanding data relationships, validating assumptions, detecting patterns
        
        Keywords: statistics, hypothesis, correlation, distribution, significance, testing, analysis
        Category: data_analytics
        
        Args:
            data_path: Path to data file (CSV, Excel, JSON, etc.)
            analysis_type: Type of analysis ("comprehensive", "hypothesis_testing", "correlations", "distributions")
            target_columns: Optional comma-separated list of specific columns to analyze
            request_id: Optional custom request identifier
        
        Returns:
            JSON with comprehensive statistical analysis results including tests, correlations, and insights
        """
        analytics_tool = DataAnalyticsTool()
        service = analytics_tool._get_service("default_analytics")
        
        # Parse target columns if provided
        target_columns_list = None
        if target_columns:
            target_columns_list = [col.strip() for col in target_columns.split(",")]
        
        result = await service.perform_statistical_analysis(
            data_path=data_path,
            analysis_type=analysis_type,
            target_columns=target_columns_list,
            request_id=request_id
        )
        
        return analytics_tool.create_response(
            "success" if result["success"] else "error",
            "perform_statistical_analysis",
            result,
            result.get("error_message") if not result["success"] else None
        )

    @mcp.tool()
    async def perform_ab_testing(
        data_path: str,
        control_group_column: str,
        treatment_group_column: str,
        metric_column: str,
        confidence_level: float = 0.95,
        request_id: str = None
    ) -> str:
        """
        Perform A/B testing analysis with statistical significance testing and confidence intervals
        
        This tool provides comprehensive A/B testing capabilities:
        - Statistical significance testing (t-test, Mann-Whitney U)
        - Effect size calculation (Cohen's d)
        - Confidence intervals for differences
        - Power analysis and sample size assessment
        - Business impact interpretation
        
        Perfect for: experiment evaluation, treatment effectiveness, business decision support
        
        Keywords: ab testing, experiment, significance, treatment, control, hypothesis, effect
        Category: data_analytics
        
        Args:
            data_path: Path to data file containing experiment data
            control_group_column: Column name identifying control group (should contain 1 for control group members)
            treatment_group_column: Column name identifying treatment group (should contain 1 for treatment group members)
            metric_column: Column name containing the metric to test (e.g., conversion_rate, revenue)
            confidence_level: Confidence level for statistical tests (default: 0.95)
            request_id: Optional custom request identifier
        
        Returns:
            JSON with A/B testing results including statistical tests, effect sizes, and business recommendations
        """
        analytics_tool = DataAnalyticsTool()
        service = analytics_tool._get_service("default_analytics")
        
        result = await service.perform_ab_testing(
            data_path=data_path,
            control_group_column=control_group_column,
            treatment_group_column=treatment_group_column,
            metric_column=metric_column,
            confidence_level=confidence_level,
            request_id=request_id
        )
        
        return analytics_tool.create_response(
            "success" if result["success"] else "error",
            "perform_ab_testing",
            result,
            result.get("error_message") if not result["success"] else None
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