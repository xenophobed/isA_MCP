#!/usr/bin/env python3
"""
Graph Analytics Tools for MCP Server
Simplified AI Agent-friendly interface with two core tools:
1. Build knowledge graphs from files
2. Intelligent query and analysis
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from core.logging import get_logger
from tools.base_tool import BaseTool

# Import new service layer
from tools.services.graph_analytics_service.services.file_processor import get_file_processor
from tools.services.graph_analytics_service.services.batch_builder import get_batch_builder
from tools.services.graph_analytics_service.services.query_aggregator import get_query_aggregator

logger = get_logger(__name__)

class GraphAnalyticsTools(BaseTool):
    """
    Simplified Graph Analytics Tools for AI Agents
    
    Only two core tools:
    1. build_knowledge_graph_from_files - 🏗️ Build graphs from any file source
    2. intelligent_query - 🔍 Smart query with auto-routing and analysis
    """
    
    def __init__(self):
        super().__init__()
        self.file_processor = None
        self.batch_builder = None  
        self.query_aggregator = None
        
    async def _initialize_services(self):
        """Initialize services lazily."""
        if self.file_processor is None:
            self.file_processor = get_file_processor()
            self.batch_builder = get_batch_builder()
            self.query_aggregator = get_query_aggregator()
            
            # Ensure query aggregator is also initialized
            await self.query_aggregator._initialize_services()
    
    def register_all_tools(self, mcp):
        """Register the two core graph analytics tools."""
        
        async def build_knowledge_graph_from_files(
            source: str,
            graph_name: Optional[str] = None,
            file_patterns: Optional[List[str]] = None,
            recursive: bool = True
        ) -> str:
            """
            🏗️ Build knowledge graph from files, directories, or file lists
            
            This is the ONE tool for all knowledge graph construction needs.
            Automatically detects source type and processes accordingly.
            
            Args:
                source: Can be:
                    - Single file path: "/path/to/document.pdf"
                    - Directory path: "/path/to/documents/"  
                    - JSON list of files: '["file1.txt", "file2.pdf"]'
                graph_name: Optional name for the knowledge graph
                file_patterns: File patterns like ["*.txt", "*.md"] (for directories)
                recursive: Whether to process subdirectories (for directories)
                
            Returns:
                JSON string with build results, progress, and statistics
                
            Keywords: build, knowledge, graph, files, documents, extract, neo4j
            Category: graph
            """
            try:
                await self._initialize_services()
                
                logger.info(f"Starting knowledge graph build from source: {source}")
                
                # Determine source type and route to appropriate method
                if isinstance(source, str):
                    # Try to parse as JSON list first
                    try:
                        file_list = json.loads(source)
                        if isinstance(file_list, list):
                            logger.info(f"Processing as file list: {len(file_list)} files")
                            result = await self.batch_builder.build_from_file_list(
                                file_paths=file_list,
                                graph_name=graph_name
                            )
                        else:
                            raise ValueError("Invalid JSON format")
                    except (json.JSONDecodeError, ValueError):
                        # Not JSON, treat as path
                        source_path = Path(source)
                        
                        if source_path.is_file():
                            logger.info(f"Processing single file: {source}")
                            result = await self.batch_builder.build_from_file_list(
                                file_paths=[source],
                                graph_name=graph_name
                            )
                        elif source_path.is_dir():
                            logger.info(f"Processing directory: {source}")
                            result = await self.batch_builder.build_from_directory(
                                directory_path=source,
                                recursive=recursive,
                                file_patterns=file_patterns,
                                graph_name=graph_name
                            )
                        else:
                            raise FileNotFoundError(f"Source not found: {source}")
                else:
                    raise ValueError(f"Invalid source type: {type(source)}")
                
                # Enhance result with build summary
                if result.get("status") == "success":
                    build_summary = result.get("build_summary", {})
                    result["message"] = (
                        f"Knowledge graph built successfully! "
                        f"Processed {build_summary.get('successful_documents', 0)} documents, "
                        f"created {build_summary.get('total_entities_created', 0)} entities and "
                        f"{build_summary.get('total_relationships_created', 0)} relationships."
                    )
                
                return self.create_service_response(
                    status=result.get("status", "error"),
                    operation="build_knowledge_graph_from_files",
                    data=result
                )
                
            except Exception as e:
                logger.error(f"Knowledge graph build failed: {e}")
                return self.create_service_response(
                    status="error",
                    operation="build_knowledge_graph_from_files",
                    data={"source": source, "error": str(e)},
                    error_message=str(e)
                )

        async def intelligent_query(
            query: str,
            max_results: int = 20,
            include_analysis: bool = True,
            context: Optional[str] = None
        ) -> str:
            """
            🔍 Intelligent query with automatic strategy selection and result aggregation
            
            This is the ONE tool for all graph querying and analysis needs.
            Automatically routes queries to the best search methods and aggregates results.
            
            Supports:
            - Semantic similarity search
            - Entity and relationship queries  
            - Path finding and neighborhood analysis
            - Graph structure analysis
            - Hybrid multi-method search
            
            Args:
                query: Natural language query or specific search terms
                max_results: Maximum number of results to return
                include_analysis: Whether to include graph analysis insights
                context: Optional context to guide the search strategy
                
            Returns:
                JSON string with comprehensive query results and analysis
                
            Keywords: query, search, semantic, entity, relationship, analysis, graphrag
            Category: graph
            """
            try:
                await self._initialize_services()
                
                logger.info(f"Starting intelligent query: {query[:100]}...")
                
                # Parse context if provided
                context_dict = {}
                if context:
                    try:
                        context_dict = json.loads(context) if isinstance(context, str) else context
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid context JSON, ignoring: {context}")
                
                # Execute intelligent query
                result = await self.query_aggregator.intelligent_query(
                    query=query,
                    context=context_dict,
                    max_results=max_results,
                    include_analysis=include_analysis
                )
                
                # Enhance result with user-friendly summary
                if result.get("status") == "success":
                    results_count = len(result.get("results", []))
                    strategy = result.get("strategy", {})
                    
                    # Create summary message
                    strategy_info = []
                    if strategy.get("has_entities"):
                        strategy_info.append("entity-focused")
                    if strategy.get("has_relationships"):
                        strategy_info.append("relationship-focused") 
                    if strategy.get("is_analytical"):
                        strategy_info.append("analytical")
                    
                    strategy_text = " and ".join(strategy_info) if strategy_info else "semantic"
                    
                    result["message"] = (
                        f"Found {results_count} results using {strategy_text} search strategy. "
                        f"Query execution took {result.get('execution_time', 0):.2f} seconds."
                    )
                
                return self.create_service_response(
                    status=result.get("status", "error"),
                    operation="intelligent_query", 
                    data=result
                )
                
            except Exception as e:
                logger.error(f"Intelligent query failed: {e}")
                return self.create_service_response(
                    status="error",
                    operation="intelligent_query",
                    data={"query": query, "error": str(e)},
                    error_message=str(e)
                )

        # Register both tools
        self.register_tool(mcp, build_knowledge_graph_from_files)
        self.register_tool(mcp, intelligent_query)
        
        logger.info("✅ Graph Analytics Tools registered: build_knowledge_graph_from_files, intelligent_query")

    def create_service_response(
        self,
        status: str,
        operation: str,
        data: Dict[str, Any],
        error_message: Optional[str] = None
    ) -> str:
        """Create a service response with enhanced formatting."""
        
        # Add service metadata
        enhanced_data = {
            **data,
            "service_info": {
                "service": "GraphAnalyticsService",
                "operation": operation,
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0"
            }
        }
        
        # Create response using base tool method
        return self.create_response(
            status=status,
            action=operation,
            data=enhanced_data,
            error_message=error_message
        )

# Create global instance
graph_analytics_tools = GraphAnalyticsTools()

def register_graph_analytics_tools(mcp):
    """Register graph analytics tools with the MCP server."""
    logger.info("🚀 Registering Graph Analytics Tools v2.0...")
    graph_analytics_tools.register_all_tools(mcp)
    logger.info("🎉 Graph Analytics Tools v2.0 registered successfully!")
    logger.info("📊 Available tools:")
    logger.info("   🏗️  build_knowledge_graph_from_files - Build graphs from any file source")
    logger.info("   🔍  intelligent_query - Smart query with auto-routing and analysis")