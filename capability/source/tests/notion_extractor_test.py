import asyncio
from app.capability.source.notion_extractor import NotionExtractor

async def main():
    # 替换为你的实际 token 和数据库 ID
    notion_token = "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"
    database_id = "1625c4da9d1680d78589f4762caf36b8"
    
    extractor = NotionExtractor(notion_token)
    data = await extractor.extract_database(database_id)
    
    print("Database Title:", data["database_info"]["title"])
    print("Number of records:", len(data["content"]))
    
    # 打印第一条记录示例
    if data["content"]:
        print("\nFirst record:")
        print(data["content"][0])

if __name__ == "__main__":
    asyncio.run(main())