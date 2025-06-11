# src/mongo_watcher.py
from typing import Callable
from app.config.config_manager import config_manager

logger = config_manager.get_logger(__name__)

class MongoWatcher:
    def __init__(self, callback: Callable):
        self.callback = callback
        self.client = None
        
    async def initialize(self):
        """Initialize MongoDB connection"""
        self.client = await config_manager.get_db('mongodb')
        logger.info("MongoDB watcher initialized")

    async def watch_collection(self, db_name: str, collection_name: str):
        """Watch a collection for changes."""
        if not self.client:
            await self.initialize()
            
        collection = self.client[collection_name]
        
        pipeline = [
            {'$match': {
                'operationType': {
                    '$in': ['insert', 'update', 'delete', 'drop']
                }
            }}
        ]
        
        try:
            async with collection.watch(pipeline) as stream:
                async for change in stream:
                    logger.info(f"Detected change in {db_name}.{collection_name}")
                    await self.callback(db_name, collection_name)
        except Exception as e:
            logger.error(f"Error watching collection: {e}")
            raise
