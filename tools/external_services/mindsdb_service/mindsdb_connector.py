#!/usr/bin/env python3
"""
MindsDB Service Connector

Integrates MindsDB AI analytics platform with the MCP system.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..base_external_service import BaseExternalService, ExternalServiceConfig, ServiceTool, ServiceResource, ServicePrompt

logger = logging.getLogger(__name__)

# Optional MindsDB SDK import with graceful fallback
MINDSDB_AVAILABLE = False
try:
    import mindsdb_sdk
    MINDSDB_AVAILABLE = True
    logger.info("MindsDB SDK is available")
except ImportError:
    logger.warning("MindsDB SDK not available. Install with: pip install mindsdb-sdk")
    mindsdb_sdk = None

class MindsDBService(BaseExternalService):
    """MindsDB AI analytics service integration"""
    
    def __init__(self, config: ExternalServiceConfig):
        super().__init__(config)
        self.mindsdb_client = None
        self.databases = {}
        self.models = {}
        self.projects = {}
    
    async def connect(self) -> bool:
        """Connect to MindsDB service"""
        if not MINDSDB_AVAILABLE:
            error_msg = "MindsDB SDK not available. Install with: pip install mindsdb-sdk"
            self._log_connection_attempt(False, error_msg)
            return False
        
        try:
            connection_url = self.config.connection_params.get('url', 'https://cloud.mindsdb.com')
            auth_config = self.config.auth_config or {}
            
            # Connect based on authentication method
            if auth_config.get('method') == 'api_key':
                api_key = self._resolve_env_var(auth_config.get('api_key'))
                self.mindsdb_client = mindsdb_sdk.connect(connection_url, api_key=api_key)
            elif auth_config.get('method') == 'login':
                login = self._resolve_env_var(auth_config.get('login'))
                password = self._resolve_env_var(auth_config.get('password'))
                self.mindsdb_client = mindsdb_sdk.connect(connection_url, login=login, password=password)
            else:
                # Anonymous connection
                self.mindsdb_client = mindsdb_sdk.connect(connection_url)
            
            # Test connection by listing databases
            self.databases = {db.name: db for db in self.mindsdb_client.databases.list()}
            self.projects = {proj.name: proj for proj in self.mindsdb_client.projects.list()}
            
            self._log_connection_attempt(True)
            return True
            
        except Exception as e:
            error_msg = f"MindsDB connection failed: {str(e)}"
            self._log_connection_attempt(False, error_msg)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from MindsDB service"""
        if self.mindsdb_client:
            self.mindsdb_client = None
        self.databases.clear()
        self.models.clear()
        self.projects.clear()
        self.is_connected = False
        logger.info(f"Disconnected from MindsDB service: {self.service_name}")
    
    async def health_check(self) -> bool:
        """Perform health check on MindsDB service"""
        if not self.is_connected or not self.mindsdb_client:
            return False
        
        try:
            # Simple health check - list databases
            databases = self.mindsdb_client.databases.list()
            return len(databases) >= 0  # Even 0 databases is a valid response
        except Exception as e:
            logger.error(f"MindsDB health check failed: {e}")
            return False
    
    async def discover_capabilities(self) -> Dict[str, List[str]]:
        """Discover MindsDB capabilities"""
        if not self.is_connected:
            return {"tools": [], "resources": [], "prompts": []}
        
        # Define available tools
        tools = [
            "natural_language_query",
            "create_predictive_model", 
            "query_model",
            "list_databases",
            "list_models",
            "execute_sql",
            "create_knowledge_base",
            "query_knowledge_base"
        ]
        
        # Define available resources  
        resources = [
            "connected_databases",
            "trained_models",
            "projects",
            "knowledge_bases"
        ]
        
        # Define available prompts
        prompts = [
            "sql_generation_prompt",
            "data_analysis_prompt",
            "model_creation_prompt"
        ]
        
        # Create tool objects
        for tool_name in tools:
            self.available_tools[tool_name] = self._create_tool_definition(tool_name)
        
        # Create resource objects
        for resource_name in resources:
            self.available_resources[resource_name] = self._create_resource_definition(resource_name)
        
        # Create prompt objects
        for prompt_name in prompts:
            self.available_prompts[prompt_name] = self._create_prompt_definition(prompt_name)
        
        return {
            "tools": tools,
            "resources": resources, 
            "prompts": prompts
        }
    
    def _create_tool_definition(self, tool_name: str) -> ServiceTool:
        """Create tool definition for MindsDB tools"""
        tool_definitions = {
            "natural_language_query": ServiceTool(
                name="natural_language_query",
                description="Execute natural language queries against MindsDB",
                parameters={"query": "Natural language query string"},
                handler=self._handle_natural_language_query,
                service_name=self.service_name
            ),
            "create_predictive_model": ServiceTool(
                name="create_predictive_model", 
                description="Create a predictive model in MindsDB",
                parameters={
                    "model_name": "Name for the new model",
                    "target_column": "Column to predict",
                    "data_source": "Source data for training"
                },
                handler=self._handle_create_model,
                service_name=self.service_name
            ),
            "query_model": ServiceTool(
                name="query_model",
                description="Query a trained MindsDB model for predictions", 
                parameters={
                    "model_name": "Name of the model to query",
                    "input_data": "Input data for prediction"
                },
                handler=self._handle_query_model,
                service_name=self.service_name
            ),
            "list_databases": ServiceTool(
                name="list_databases",
                description="List all connected databases in MindsDB",
                parameters={},
                handler=self._handle_list_databases,
                service_name=self.service_name
            ),
            "list_models": ServiceTool(
                name="list_models", 
                description="List all trained models in MindsDB",
                parameters={"project_name": "Optional project name to filter models"},
                handler=self._handle_list_models,
                service_name=self.service_name
            ),
            "execute_sql": ServiceTool(
                name="execute_sql",
                description="Execute SQL query directly on MindsDB",
                parameters={"sql_query": "SQL query to execute"},
                handler=self._handle_execute_sql,
                service_name=self.service_name
            ),
            "create_knowledge_base": ServiceTool(
                name="create_knowledge_base",
                description="Create a knowledge base from documents",
                parameters={
                    "kb_name": "Name for the knowledge base",
                    "documents": "Documents or data source for the KB"
                },
                handler=self._handle_create_knowledge_base,
                service_name=self.service_name
            ),
            "query_knowledge_base": ServiceTool(
                name="query_knowledge_base",
                description="Query a knowledge base with natural language",
                parameters={
                    "kb_name": "Name of the knowledge base",
                    "question": "Natural language question"
                },
                handler=self._handle_query_knowledge_base,
                service_name=self.service_name
            )
        }
        
        return tool_definitions.get(tool_name)
    
    def _create_resource_definition(self, resource_name: str) -> ServiceResource:
        """Create resource definition for MindsDB resources"""
        resource_definitions = {
            "connected_databases": ServiceResource(
                name="connected_databases",
                description="List of databases connected to MindsDB",
                resource_type="data",
                uri=f"mindsdb://{self.service_name}/databases"
            ),
            "trained_models": ServiceResource(
                name="trained_models",
                description="List of trained ML models in MindsDB", 
                resource_type="data",
                uri=f"mindsdb://{self.service_name}/models"
            ),
            "projects": ServiceResource(
                name="projects",
                description="List of MindsDB projects",
                resource_type="data", 
                uri=f"mindsdb://{self.service_name}/projects"
            ),
            "knowledge_bases": ServiceResource(
                name="knowledge_bases",
                description="List of knowledge bases in MindsDB",
                resource_type="data",
                uri=f"mindsdb://{self.service_name}/knowledge_bases"
            )
        }
        
        return resource_definitions.get(resource_name)
    
    def _create_prompt_definition(self, prompt_name: str) -> ServicePrompt:
        """Create prompt definition for MindsDB prompts"""
        prompt_definitions = {
            "sql_generation_prompt": ServicePrompt(
                name="sql_generation_prompt",
                description="Generate SQL queries from natural language",
                template="Convert this natural language query to SQL: {query}\nAvailable tables: {tables}",
                parameters=["query", "tables"]
            ),
            "data_analysis_prompt": ServicePrompt(
                name="data_analysis_prompt", 
                description="Generate data analysis insights",
                template="Analyze this data and provide insights: {data}\nFocus on: {analysis_type}",
                parameters=["data", "analysis_type"]
            ),
            "model_creation_prompt": ServicePrompt(
                name="model_creation_prompt",
                description="Generate model creation recommendations",
                template="Recommend a predictive model for: {use_case}\nData: {data_description}\nTarget: {target}",
                parameters=["use_case", "data_description", "target"]
            )
        }
        
        return prompt_definitions.get(prompt_name)
    
    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Invoke a MindsDB tool"""
        if not self.is_connected:
            raise RuntimeError(f"MindsDB service {self.service_name} is not connected")
        
        if tool_name not in self.available_tools:
            raise ValueError(f"Tool '{tool_name}' not available in MindsDB service")
        
        tool = self.available_tools[tool_name]
        
        try:
            result = await tool.handler(params)
            self._log_tool_invocation(tool_name, True)
            return result
        except Exception as e:
            error_msg = f"Tool invocation failed: {str(e)}"
            self._log_tool_invocation(tool_name, False, error_msg)
            raise
    
    # Tool handler methods
    async def _handle_natural_language_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle natural language query"""
        query = params.get('query')
        if not query:
            raise ValueError("Query parameter is required")
        
        # Use MindsDB's query functionality
        # This is a simplified implementation - actual implementation would depend on MindsDB's NL query capabilities
        try:
            # Execute the query (MindsDB can handle natural language in some contexts)
            result = self.mindsdb_client.query(query)
            return {
                "success": True,
                "query": query,
                "result": result.fetch() if hasattr(result, 'fetch') else str(result),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_create_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model creation"""
        model_name = params.get('model_name')
        target_column = params.get('target_column')
        data_source = params.get('data_source')
        
        if not all([model_name, target_column, data_source]):
            raise ValueError("model_name, target_column, and data_source are required")
        
        try:
            # Get the default project or create one
            project = self.mindsdb_client.projects.get('mindsdb') or self.mindsdb_client.projects.create('mindsdb')
            
            # Create the model
            model = project.models.create(
                name=model_name,
                predict=target_column,
                query=f"SELECT * FROM {data_source}"
            )
            
            return {
                "success": True,
                "model_name": model_name,
                "status": "created",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_query_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model querying"""
        model_name = params.get('model_name')
        input_data = params.get('input_data', {})
        
        if not model_name:
            raise ValueError("model_name is required")
        
        try:
            # Build prediction query
            where_clause = " AND ".join([f"{k}='{v}'" for k, v in input_data.items()])
            query = f"SELECT * FROM {model_name}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            result = self.mindsdb_client.query(query)
            predictions = result.fetch() if hasattr(result, 'fetch') else []
            
            return {
                "success": True,
                "model_name": model_name,
                "predictions": predictions,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_list_databases(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle database listing"""
        try:
            databases = [{"name": db.name, "type": getattr(db, 'type', 'unknown')} 
                        for db in self.mindsdb_client.databases.list()]
            
            return {
                "success": True,
                "databases": databases,
                "count": len(databases),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_list_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model listing"""
        project_name = params.get('project_name', 'mindsdb')
        
        try:
            project = self.mindsdb_client.projects.get(project_name)
            if not project:
                return {
                    "success": False,
                    "error": f"Project '{project_name}' not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            models = [{"name": model.name, "status": getattr(model, 'status', 'unknown')}
                     for model in project.models.list()]
            
            return {
                "success": True,
                "models": models,
                "count": len(models),
                "project": project_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_execute_sql(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle direct SQL execution"""
        sql_query = params.get('sql_query')
        if not sql_query:
            raise ValueError("sql_query parameter is required")
        
        try:
            result = self.mindsdb_client.query(sql_query)
            data = result.fetch() if hasattr(result, 'fetch') else str(result)
            
            return {
                "success": True,
                "query": sql_query,
                "result": data,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "query": sql_query,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_create_knowledge_base(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle knowledge base creation"""
        kb_name = params.get('kb_name')
        documents = params.get('documents')
        
        if not kb_name:
            raise ValueError("kb_name parameter is required")
        
        # This is a placeholder - actual implementation depends on MindsDB's knowledge base API
        return {
            "success": True,
            "knowledge_base": kb_name,
            "status": "created",
            "note": "Knowledge base creation is a placeholder - implement based on MindsDB API",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _handle_query_knowledge_base(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle knowledge base querying"""
        kb_name = params.get('kb_name')
        question = params.get('question')
        
        if not all([kb_name, question]):
            raise ValueError("kb_name and question parameters are required")
        
        # This is a placeholder - actual implementation depends on MindsDB's knowledge base API
        return {
            "success": True,
            "knowledge_base": kb_name,
            "question": question,
            "answer": "Knowledge base querying is a placeholder - implement based on MindsDB API",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _fetch_resource(self, resource: ServiceResource, params: Dict[str, Any]) -> Any:
        """Fetch resource data from MindsDB"""
        if resource.name == "connected_databases":
            return [{"name": db.name, "type": getattr(db, 'type', 'unknown')} 
                   for db in self.mindsdb_client.databases.list()]
        elif resource.name == "trained_models":
            models = []
            for project in self.mindsdb_client.projects.list():
                for model in project.models.list():
                    models.append({
                        "name": model.name,
                        "project": project.name,
                        "status": getattr(model, 'status', 'unknown')
                    })
            return models
        elif resource.name == "projects":
            return [{"name": proj.name} for proj in self.mindsdb_client.projects.list()]
        elif resource.name == "knowledge_bases":
            # Placeholder - implement based on MindsDB API
            return []
        else:
            raise ValueError(f"Unknown resource: {resource.name}")
    
    def _resolve_env_var(self, value: str) -> str:
        """Resolve environment variable references in configuration values"""
        if value and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]  # Remove ${ and }
            return os.environ.get(env_var, value)
        return value