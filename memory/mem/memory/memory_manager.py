from typing import List, Dict, Optional, Union
from app.config.config_manager import config_manager
from .memory_writer import GraphWriter
from .memory_searcher import GraphSearcher
from app.services.agent.capabilities.contextual.mem.configs.base import MemoryConfig

import logging 

logger = logging.getLogger(__name__)

class GraphManager:
    """
    Coordinates graph operations between GraphWriter and GraphSearcher.
    Provides a unified interface for graph operations.
    """
    # Define class variables
    _instance = None
    _initialized = False
    
    def __new__(cls, config=None):
        if cls._instance is None:
            cls._instance = super(GraphManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config=None):
        # Skip if already initialized
        if GraphManager._initialized:
            return
            
        self.config = config or MemoryConfig.default()
        self.searcher = None
        self.writer = None
        self.graph = None
        self.user_identities = {}  # 存储用户身份映射
        GraphManager._initialized = False
        
    @classmethod
    async def create(cls, config=None):
        """Factory method for async initialization"""
        instance = cls(config)
        if not cls._initialized:
            await instance.setup()
            cls._initialized = True
        return instance

    async def setup(self):
        """Initialize components"""
        try:
            # 1. 初始化数据库连接
            self.graph = await config_manager.get_db('neo4j')
            
            # 2. 初始化搜索器
            self.searcher = GraphSearcher(self.config)
            await self.searcher.setup()
            
            # 3. 初始化写入器，传入搜索器
            self.writer = GraphWriter(self.config, self.searcher)
            await self.writer.setup()
            
        except Exception as e:
            logger.error(f"Failed to setup GraphManager: {e}")
            raise

    async def add(
        self,
        messages: List[Dict[str, str]],
        filters: Dict[str, str],
        memory_ids: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """Add new information to the graph from dialogue."""
        try:
            results = await self.writer.process_dialogue(
                messages=messages,
                filters=filters,
                memory_ids=memory_ids
            )
            return results
        except Exception as e:
            logger.error(f"Error in add operation: {e}")
            return []
            
    async def delete(
        self,
        entity_name: str,
        filters: Dict[str, str]
    ) -> bool:
        """Delete an entity and its relationships."""
        try:
            cypher = """
            MATCH (n {name: $name, user_id: $user_id})
            DETACH DELETE n
            """
            
            await self.graph.query(
                cypher,
                params={
                    "name": entity_name,
                    "user_id": filters["user_id"]
                }
            )
            return True
            
        except Exception as e:
            logger.error(f"Error in delete operation: {e}")
            return False
            
    async def cleanup(self, filters: Dict[str, str]) -> bool:
        """Cleanup orphaned nodes and stale relationships."""
        try:
            # 检查 filters 参数
            if not filters or 'user_id' not in filters:
                logger.warning("No user_id provided for cleanup")
                return False
                
            cypher = """
            MATCH (n {user_id: $user_id})
            WHERE NOT (n)--()
            DELETE n
            """
            
            await self.graph.query(
                cypher,
                params={"user_id": filters["user_id"]}
            )
            return True
            
        except Exception as e:
            logger.error(f"Error in cleanup operation: {str(e)}", exc_info=True)
            if isinstance(e, KeyError) and str(e) == "'user_id'":
                logger.warning("Missing user_id in cleanup filters")
            return False
            
    async def search(
        self,
        query: str,
        filters: Dict[str, str],
        search_type: str = "entity",
        memory_ids: Optional[List[str]] = None,
        time_window: Optional[int] = None,
        limit: int = 10,
        expand_context: bool = False,
        format_as_text: bool = True
    ) -> Union[List[Dict[str, str]], str]:
        """
        Unified search interface with different search strategies.
        
        Args:
            query: Search query
            filters: Must contain 'user_id'
            search_type: Type of search to perform
            memory_ids: Optional memory IDs for context
            time_window: Optional time window in days
            limit: Maximum results
            expand_context: Whether to expand search context
            format_as_text: Whether to format results as readable text
        """
        try:
            results = []
            
            if search_type == "entity":
                # Direct entity search
                entity_results = await self.searcher.find_similar_entities(
                    query=query,
                    filters=filters,
                    limit=limit
                )
                results.extend(entity_results)
                
                # Expand context to include relationships
                if expand_context and entity_results:
                    entities = [r["entity"] for r in entity_results]
                    relationship_results = await self.searcher.expand_context(
                        entities=entities,
                        filters=filters,
                        limit=limit
                    )
                    results.extend(relationship_results)
                    
            elif search_type == "memory":
                # Search within specific memory context
                if not memory_ids:
                    raise ValueError("memory_ids required for memory search")
                    
                results = await self.searcher.find_by_memory_ids(
                    memory_ids=memory_ids,
                    filters=filters
                )
                
            elif search_type == "recent":
                # Search recent interactions
                results = await self.searcher.find_recent_relations(
                    filters=filters,
                    time_window=time_window or 7,  # Default 7 days
                    limit=limit
                )
                
            elif search_type == "global":
                # Remove user_id filter for global search
                results = await self.searcher.find_similar_entities(
                    query=query,
                    filters={},  # No user_id filter
                    limit=limit
                )
                if expand_context:
                    entities = [r["entity"] for r in results]
                    expanded = await self.searcher.expand_context(
                        entities=entities,
                        filters={},  # No user_id filter
                        limit=limit
                    )
                    results.extend(expanded)
                
            # Rank results if we have a query
            if query and results:
                results = self.searcher.rank_results(
                    results=results,
                    query=query,
                    top_n=limit
                )

            # Format results as text if requested
            if format_as_text:
                return self.searcher.format_results_to_text(
                    results=results,
                    filters=filters
                )
                
            return results
            
        except Exception as e:
            logger.error(f"Error in search operation: {e}")
            return [] if not format_as_text else "Error performing search."

    async def add_user_identity(self, user_id: str, primary_name: str, aliases: List[str]):
        """添加用户身份映射"""
        if user_id not in self.user_identities:
            self.user_identities[user_id] = {
                "primary": primary_name.lower(),
                "aliases": set(alias.lower() for alias in aliases)
            }
        else:
            self.user_identities[user_id]["aliases"].update(alias.lower() for alias in aliases)
            
    def get_primary_identity(self, user_id: str, name: str) -> str:
        """获取主要身份标识"""
        if not name:
            return name
        name = str(name).lower()
        if user_id in self.user_identities:
            if name in self.user_identities[user_id]["aliases"]:
                return self.user_identities[user_id]["primary"]
        return name