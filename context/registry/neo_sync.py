from typing import Dict, Any
from app.capability.base.metadata import KnowledgeMetadata, ToolMetadata, DatabaseMetadata
from app.services.db.neo4j.service import Neo4jService
from app.services.db.neo4j.queries.registry import QueryRegistry
from app.services.db.neo4j.queries.context_expansion_queries import ContextExpansionQueries
from app.config.config_manager import config_manager
import json
from datetime import datetime

logger = config_manager.get_logger(__name__)

class NeoSync:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.service = Neo4jService(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password
        )
        self.registry = QueryRegistry()
        ContextExpansionQueries.register_all(self.registry)

    async def initialize(self):
        """Initialize Neo4j connection"""
        await self.service.initialize()

    async def sync_knowledge_source(self, metadata: KnowledgeMetadata):
        """Register new knowledge source"""
        logger.info(f"Syncing knowledge source: {metadata.capability_id}")
        
        collections_data = [
            {
                "name": col_name,
                "info": col_info,
                "semantics": metadata.document_semantics.get(col_name, {})
            }
            for col_name, col_info in metadata.collections.items()
        ]
        
        params = {
            "capability_id": metadata.capability_id,
            "name": metadata.name,
            "type": metadata.type,
            "description": metadata.description,
            "last_updated": metadata.last_updated.isoformat(),
            "collections": collections_data
        }
        
        await self.registry.execute_query(
            self.service,
            "sync_knowledge_source",
            params
        )
        logger.info("Successfully synced knowledge source")

    async def sync_tool_capability(self, metadata: ToolMetadata):
        """Register new tool capability"""
        try:
            params = {
                "capability_id": metadata.capability_id,
                "name": metadata.name,
                "type": metadata.type,
                "description": metadata.description,
                "last_updated": metadata.last_updated.isoformat(),
                "status": metadata.status,
                "api_endpoint": metadata.api_endpoint,
                "input_schema": json.dumps(metadata.input_schema),
                "output_schema": json.dumps(metadata.output_schema),
                "rate_limits": json.dumps(metadata.rate_limits),
                "node_name": metadata.node_name,
                "graph_source": metadata.graph_source,
                "key_elements": metadata.key_elements
            }
            
            await self.registry.execute_query(
                self.service,
                "sync_tool_capability",
                params
            )
            logger.info(f"Successfully synced tool capability: {metadata.capability_id}")
            
        except Exception as e:
            logger.error(f"Failed to sync tool capability: {str(e)}")
            raise

    async def sync_database_capability(self, metadata: DatabaseMetadata):
        """Register new database capability"""
        try:
            params = {
                "capability_id": metadata.capability_id,
                "name": metadata.name,
                "type": metadata.type,
                "description": metadata.description,
                "last_updated": metadata.last_updated.isoformat(),
                "status": metadata.status,
                "database_type": metadata.database_type,
                "order_data": metadata.order_data
            }
            
            await self.registry.execute_query(
                self.service,
                "sync_database_capability",
                params
            )
            logger.info(f"Successfully synced database capability: {metadata.capability_id}")
            
        except Exception as e:
            logger.error(f"Failed to sync database capability: {str(e)}")
            raise

    async def close(self):
        """Close Neo4j connection"""
        await self.service.close()