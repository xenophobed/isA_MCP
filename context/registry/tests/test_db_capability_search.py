# test_db_capability_search.py
import os 
os.environ["ENV"] = "local"

import asyncio
from app.capability.source.notion_extractor import NotionExtractor
from app.capability.registry.db_graph_manager import DBGraphManager
from app.capability.source.db_meta_extractor import DBMetaExtractor
from app.capability.source.db_meta_embedder import DBMetaEmbedder

async def test_db_capability_search():
    try:
        print("\n=== Testing Database Capability Search ===")
        
        # 1. 初始化 Graph Manager
        print("\n1. Initializing Graph Manager...")
        graph_manager = await DBGraphManager.create()
        
        # 2. 从 Notion 获取数据并注册到图谱
        print("\n2. Registering database from Notion...")
        notion_token = "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"
        database_id = "1625c4da9d1680d78589f4762caf36b8"
        
        # 2.1 获取数据
        notion_extractor = NotionExtractor(notion_token)
        database_content = await notion_extractor.extract_database(database_id)
        
        # 2.2 提取元数据
        extractor = DBMetaExtractor()
        metadata = await extractor.extract_from_database(database_content)
        
        # 2.3 生成向量
        embedder = DBMetaEmbedder()
        vectors = await embedder.generate_vectors(metadata)
        
        # 2.4 存储到图谱
        await graph_manager.store_table_metadata(metadata, vectors)
        
        # 3. 测试搜索功能
        print("\n=== Testing Search Capabilities ===")
        
        # 3.1 工作相关搜索
        print("\nTesting work-related search:")
        work_results = await graph_manager.search_tables(
            "Find tables for managing work meetings and tasks",
            weights={"semantic": 0.4, "functional": 0.4, "contextual": 0.2}
        )
        print_search_results("Work-related Search", work_results)
        
        # 3.2 个人活动搜索
        print("\nTesting personal activities search:")
        personal_results = await graph_manager.search_tables(
            "Find tables for tracking personal health and fitness activities",
            weights={"semantic": 0.3, "functional": 0.3, "contextual": 0.4}
        )
        print_search_results("Personal Activities Search", personal_results)
        
        # 3.3 日程管理搜索
        print("\nTesting schedule management search:")
        schedule_results = await graph_manager.search_tables(
            "Need a database for managing daily schedules and appointments",
            weights={"semantic": 0.5, "functional": 0.3, "contextual": 0.2}
        )
        print_search_results("Schedule Management Search", schedule_results)

    except Exception as e:
        print(f"Error during testing: {str(e)}")
        raise

def print_search_results(search_type: str, results: list):
    print(f"\n{search_type} Results:")
    print(f"Found {len(results)} matches")
    if results:
        top_result = results[0]
        print(f"Top Match (score: {top_result['score']:.3f}):")
        print("Table ID:", top_result["table_id"])
        metadata = top_result["metadata"]
        print("Core Concepts:", metadata["semantic"]["core_concepts"])
        print("Domain:", metadata["semantic"]["domain"])
        print("\nSample Queries:")
        for query in metadata["functional"]["sample_queries"]:
            print(f"- {query}")
        print("\nUsage Scenarios:", metadata["contextual"]["usage_scenarios"])

if __name__ == "__main__":
    asyncio.run(test_db_capability_search())
