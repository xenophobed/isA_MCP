import asyncio
from app.capability.source.notion_extractor import NotionExtractor
from app.capability.source.db_meta_extractor import DBMetaExtractor
import json

async def main():
    try:
        # 1. 初始化 Notion 提取器
        notion_token = "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"
        database_id = "1625c4da9d1680d78589f4762caf36b8"
        notion_extractor = NotionExtractor(notion_token)
        
        # 2. 从 Notion 获取数据
        print("Extracting data from Notion...")
        database_content = await notion_extractor.extract_database(database_id)
        print(f"Found {len(database_content['content'])} records in database")
        
        # 3. 初始化数据库元数据提取器
        db_meta_extractor = DBMetaExtractor()
        
        # 4. 提取元数据
        print("\nExtracting metadata...")
        metadata = await db_meta_extractor.extract_from_database(database_content)
        
        # 5. 打印结果
        print("\nExtracted Metadata:")
        print("------------------")
        print(f"Table ID: {metadata.table_id}")
        
        print("\nSemantic Vector:")
        print("Core Concepts:", metadata.semantic_vector.core_concepts)
        print("Domain:", metadata.semantic_vector.domain)
        print("Business Entity:", metadata.semantic_vector.business_entity)
        
        print("\nFunctional Vector:")
        print("Common Operations:", metadata.functional_vector.common_operations)
        print("Query Patterns:", metadata.functional_vector.query_patterns)
        print("Sample Queries:", metadata.functional_vector.sample_queries)
        
        print("\nContextual Vector:")
        print("Usage Scenarios:", metadata.contextual_vector.usage_scenarios)
        print("Data Sensitivity:", metadata.contextual_vector.data_sensitivity)
        print("Update Frequency:", metadata.contextual_vector.update_frequency)
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())