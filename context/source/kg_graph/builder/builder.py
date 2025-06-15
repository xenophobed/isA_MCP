# app/graphs/kg_graph/builder/builder.py
from typing import Optional, Dict, List
from app.services.graphs.kg_graph.builder.data_manager import DataManager
from app.services.graphs.kg_graph.builder.extractor import KnowledgeExtractor  
from app.services.graphs.kg_graph.builder.neo4j_store import Neo4jStore
from app.config.config_manager import config_manager
from datetime import datetime, timedelta
import hashlib
import asyncio

config_manager.set_log_level("INFO")
logger = config_manager.get_logger(__name__)

def encode_md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

class KnowledgeBuilder:
    """知识图谱构建器：协调整个知识抽取和存储流程"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.extractor = KnowledgeExtractor()
        self.neo4j_store: Optional[Neo4jStore] = None
        
    async def initialize(self,
                        mongodb_host: str = "localhost",
                        mongodb_port: int = 27017,
                        mongodb_db: str = "chat_db"):
        """初始化所有组件"""
        try:
            logger.info("Initializing KnowledgeBuilder...")
            print(f"[{datetime.now()}] Starting initialization...")
            
            # 初始化 DataManager
            await self.data_manager.initialize(
                host=mongodb_host,
                port=mongodb_port,
                database=mongodb_db
            )
            print(f"[{datetime.now()}] DataManager initialized")
            
            # 初始化 Neo4j存储
            self.neo4j_store = Neo4jStore()
            print(f"[{datetime.now()}] Neo4jStore initialized")
            
            # 创建Neo4j约束
            await self.neo4j_store.init_constraints()
            print(f"[{datetime.now()}] Neo4j constraints created")
            
            logger.info("KnowledgeBuilder initialization completed")
            
        except Exception as e:
            error_msg = f"Error during initialization: {str(e)}"
            logger.error(error_msg)
            raise

    async def build_all_knowledge(self) -> Dict:
        """构建所有知识图谱"""
        build_stats = {
            "start_time": datetime.now(),
            "total_conversations": 0,
            "processed_conversations": 0,
            "failed_conversations": 0,
            "extracted_atomic_facts": 0,
            "extracted_key_elements": 0
        }
        
        try:
            # Load only last 24 hours of data
            yesterday = datetime.now() - timedelta(days=1)
            month = datetime.now() - timedelta(days=30)
            week = datetime.now() - timedelta(days=7)
            logger.info(f"Loading conversations since {week}...")
            await self.data_manager.load_data_since(week)
            
            # Now process the loaded conversations
            conversations = list(self.data_manager.conversations.values())
            build_stats["total_conversations"] = len(conversations)
            logger.info(f"Starting to process {len(conversations)} conversations")
            
            for conv in conversations:
                try:
                    messages = self.data_manager.get_conversation_messages(conv.conversation_id)
                    if not messages:
                        logger.warning(f"No messages found for conversation {conv.conversation_id}")
                        continue
                        
                    logger.info(f"Processing conversation {conv.conversation_id} with {len(messages)} messages")
                    extracted_data = await self.extractor.process_conversation(messages)
                    
                    # Store to Neo4j
                    await self.neo4j_store.store_atomic_facts(
                        conv.conversation_id, 
                        extracted_data["atomic_facts"]
                    )
                    
                    # Update statistics
                    build_stats["processed_conversations"] += 1
                    build_stats["extracted_atomic_facts"] += len(extracted_data["atomic_facts"])
                    build_stats["extracted_key_elements"] += sum(
                        len(fact["key_elements"]) for fact in extracted_data["atomic_facts"]
                    )
                    
                except Exception as e:
                    build_stats["failed_conversations"] += 1
                    logger.error(f"Error processing conversation {conv.conversation_id}: {str(e)}")
                    continue
            
            return build_stats
            
        except Exception as e:
            logger.error(f"Error building knowledge graph: {str(e)}")
            raise

    async def close(self):
        """关闭所有连接"""
        if self.neo4j_store:
            await self.neo4j_store.close()

async def main():
    builder = KnowledgeBuilder()
    try:
        print(f"\n[{datetime.now()}] Starting knowledge graph building process...")
        
        # 1. 初始化
        await builder.initialize(
            mongodb_host="localhost",
            mongodb_port=27017,
            mongodb_db="chat_db"
        )
        
        # 2. 构建所有知识
        build_stats = await builder.build_all_knowledge()
        
        # 3. 打印构建结果
        print(f"\n[{datetime.now()}] Knowledge graph build completed!")
        print("\nBuild Statistics:")
        print(f"Total conversations: {build_stats['total_conversations']}")
        print(f"Processed conversations: {build_stats['processed_conversations']}")
        print(f"Failed conversations: {build_stats['failed_conversations']}")
        print(f"Extracted atomic facts: {build_stats['extracted_atomic_facts']}")
        print(f"Extracted key elements: {build_stats['extracted_key_elements']}")
        print(f"Build duration: {datetime.now() - build_stats['start_time']}")
            
    except Exception as e:
        print(f"\n[{datetime.now()}] ERROR: Process failed: {str(e)}")
    finally:
        # 4. 关闭连接
        await builder.close()
        print(f"\n[{datetime.now()}] Process completed.")

# 运行
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())