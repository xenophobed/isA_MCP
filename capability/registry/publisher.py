from redis.asyncio import Redis
from ..base.metadata import CapabilityMetadata
import json
from datetime import datetime

class RedisMetadataPublisher:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.stream_key = "capability_updates"
        
    def _datetime_handler(self, obj):
        """处理datetime的JSON序列化"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')
        
    async def publish_metadata(self, metadata: CapabilityMetadata):
        """发布元数据更新到Redis流"""
        metadata_dict = metadata.dict()
        # 确保graph_source和node_name存在
        metadata_dict.setdefault('graph_source', 'search_graph')
        metadata_dict.setdefault('node_name', f"{metadata.type}_Node")
        
        await self.redis.xadd(
            self.stream_key,
            {
                "capability_id": metadata.capability_id,
                "type": metadata.type,
                "metadata": json.dumps(metadata_dict, default=self._datetime_handler),
                "timestamp": datetime.now().isoformat(),
                "graph_source": metadata_dict['graph_source'],
                "node_name": metadata_dict['node_name']
            }
        )