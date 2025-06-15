from typing import Dict, List, Optional
from redis.asyncio import Redis
from ..base.provider import MetadataProvider
from ..base.metadata import CapabilityMetadata
from .publisher import RedisMetadataPublisher
from datetime import datetime
import asyncio
from app.config.config_manager import config_manager
from .neo_sync import neo_sync
from app.capability.base.metadata import KnowledgeMetadata, ToolMetadata, DatabaseMetadata

config_manager.set_log_level("INFO")
logger = config_manager.get_logger(__name__)

class CapabilityRegistry:
    def __init__(self, redis: Redis, neo4j_uri: str = None, neo4j_user: str = None, neo4j_password: str = None):
        self.redis = redis
        self.publisher = RedisMetadataPublisher(redis)
        # 使用 SystemCapabilityBuilder 替代 Neo4jStore
        self.neo_sync = neo_sync(neo4j_uri, neo4j_user, neo4j_password)
        self.providers: Dict[str, MetadataProvider] = {}
        self.last_sync: Dict[str, datetime] = {}
        
    async def register_provider(self, provider: MetadataProvider):
        """注册新的元数据提供者"""
        metadata = await provider.get_metadata()
        logger.info(f"Registering provider with type: {metadata.type}")
        self.providers[metadata.capability_id] = provider
        await self.publisher.publish_metadata(metadata)
        
        # 根据能力类型注册到Neo4j
        if metadata.type == "knowledge_base":
            logger.info("Syncing knowledge source to Neo4j")
            knowledge_source = KnowledgeMetadata(
                capability_id=metadata.capability_id,
                name=metadata.name,
                type=metadata.type,
                description=metadata.description,
                last_updated=metadata.last_updated,
                status=metadata.status,
                source_type=metadata.source_type,
                content_types=metadata.content_types,
                update_frequency=metadata.update_frequency,
                collections=metadata.collections,  
                document_semantics=metadata.document_semantics,  
                entries=metadata.entries,  
                key_elements=metadata.key_elements,
                example_queries=metadata.example_queries,
                node_name=metadata.node_name,
                graph_source=metadata.graph_source
            )
            await self.neo_sync.sync_knowledge_source(knowledge_source)
            
        elif metadata.type == "api_tool":
            tool = ToolMetadata(
                capability_id=metadata.capability_id,
                name=metadata.name,
                type=metadata.type,
                description=metadata.description,
                last_updated=metadata.last_updated,
                status=metadata.status,
                api_endpoint=metadata.api_endpoint,
                input_schema=metadata.input_schema,
                output_schema=metadata.output_schema,
                rate_limits=metadata.rate_limits,
                key_elements=metadata.key_elements,
                example_uses=metadata.example_uses,
                node_name=metadata.node_name,
                graph_source=metadata.graph_source
            )
            await self.neo_sync.sync_tool_capability(tool)

        elif metadata.type == "database":
            database = DatabaseMetadata(
                capability_id=metadata.capability_id,
                name=metadata.name,
                type=metadata.type,
                description=metadata.description,
                last_updated=metadata.last_updated,
                status=metadata.status,
                database_type=metadata.database_type,
                tables=metadata.tables,
                schema=metadata.schema,
                order_data=metadata.order_data,
                key_elements=metadata.key_elements,
                example_queries=metadata.example_queries
            )
            await self.neo_sync.sync_database_capability(database)
        
    async def start_monitoring(self):
        """Start monitoring Redis streams for metadata updates"""
        last_id = "$"  # 从最新的消息开始监听
        
        while True:
            try:
                # Read from Redis stream
                updates = await self.redis.xread(
                    {self.publisher.stream_key: last_id},
                    count=100,
                    block=10000  # 10秒超时
                )
                
                if updates:
                    for stream, messages in updates:
                        for msg_id, fields in messages:
                            metadata = CapabilityMetadata.parse_raw(
                                fields[b"metadata"].decode()
                            )
                            await self._handle_update(metadata)
                            last_id = msg_id  # 更新最后处理的消息ID
                            
                await asyncio.sleep(10)  # 每10秒检查一次
                    
            except Exception as e:
                logger.error(f"Error monitoring updates: {str(e)}")
                await asyncio.sleep(30)  # 错误时延长等待时间
                
    async def _handle_update(self, metadata: CapabilityMetadata):
        """Handle metadata updates"""
        capability_id = metadata.capability_id
        
        # Check if update is needed
        last_update = self.last_sync.get(capability_id)
        if last_update and last_update >= metadata.last_updated:
            return
            
        # Sync to Neo4j
        await self._sync_to_neo4j(metadata)
        self.last_sync[capability_id] = metadata.last_updated
        
        # Update provider if exists
        if capability_id in self.providers:
            await self.providers[capability_id].update_metadata(metadata)
            
    async def get_capability(self, capability_id: str) -> Optional[CapabilityMetadata]:
        """Get capability metadata"""
        if capability_id in self.providers:
            return await self.providers[capability_id].get_metadata()
        return None
        
    async def list_capabilities(self) -> List[CapabilityMetadata]:
        """List all registered capabilities"""
        return [
            await provider.get_metadata() 
            for provider in self.providers.values()
        ]
