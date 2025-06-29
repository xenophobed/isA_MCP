#!/usr/bin/env python
"""
测试 crawl_and_extract 工具功能
测试我们在 tools/web_tools.py 中实现的 MCP 工具
"""
import asyncio
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

# 导入我们的MCP工具注册器
from tools.web_tools import register_web_tools
from core.logging import get_logger
from core.security import initialize_security

logger = get_logger(__name__)


class MockMCP:
    """模拟MCP服务器用于测试"""
    def __init__(self):
        self.tools = {}
    
    def tool(self):
        """装饰器用于注册工具"""
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator
    
    async def call_tool(self, tool_name, **kwargs):
        """调用注册的工具"""
        if tool_name in self.tools:
            return await self.tools[tool_name](**kwargs)
        else:
            raise ValueError(f"Tool {tool_name} not found")


async def test_crawl_extract_tool():
    """测试我们的crawl_and_extract MCP工具"""
    print("🚀 测试crawl_and_extract MCP工具")
    print("=" * 60)
    
    # 初始化安全管理器
    initialize_security()
    
    # 创建模拟MCP服务器
    mock_mcp = MockMCP()
    
    # 注册我们的web工具
    register_web_tools(mock_mcp)
    
    print("✅ Web工具已注册到MCP服务器")
    print(f"📋 可用工具: {list(mock_mcp.tools.keys())}")
    
    try:
        # 测试1: Wikipedia文章提取
        print("\n📖 测试1: Wikipedia文章提取")
        wikipedia_urls = [
            "https://en.wikipedia.org/wiki/Artificial_intelligence"
        ]
        
        result1 = await mock_mcp.call_tool(
            "crawl_and_extract",
            urls=json.dumps(wikipedia_urls),
            extraction_schema="article",
            filter_query="",
            max_urls=1,
            user_id="test_user"
        )
        
        print("✅ Wikipedia测试结果:")
        result1_data = json.loads(result1)
        if result1_data["status"] == "success":
            items = result1_data["data"]["extracted_items"]
            print(f"   提取了 {len(items)} 个数据项")
            if items:
                item = items[0]
                print(f"   标题: {item.get('title', 'N/A')}")
                print(f"   内容: {str(item.get('content', 'N/A'))[:150]}...")
        else:
            print(f"   ❌ 失败: {result1_data.get('error', 'Unknown error')}")
        
        # 测试2: Amazon产品提取
        print("\n🛍️ 测试2: Amazon JBL耳机产品提取")
        amazon_url = "https://www.amazon.com/JBL-Endurance-Race-Waterproof-Cancelling/dp/B0DVTGBCBL/?_encoding=UTF8&pd_rd_w=t5IWN&content-id=amzn1.sym.27713fe8-b8c8-4a62-8381-8d094618df19&pf_rd_p=27713fe8-b8c8-4a62-8381-8d094618df19&pf_rd_r=6KJGBZZ66FH7B63HYX20&pd_rd_wg=c00mx&pd_rd_r=f638579d-46a7-44c8-ab46-9097fe59a690&ref_=pd_hp_d_atf_dealz_cs&th=1"
        
        result2 = await mock_mcp.call_tool(
            "crawl_and_extract",
            urls=json.dumps([amazon_url]),
            extraction_schema="product",
            filter_query="price review rating",
            max_urls=1,
            user_id="test_user"
        )
        
        print("✅ Amazon产品测试结果:")
        result2_data = json.loads(result2)
        if result2_data["status"] == "success":
            items = result2_data["data"]["extracted_items"]
            print(f"   提取了 {len(items)} 个产品项")
            if items:
                item = items[0]
                print(f"   产品名: {item.get('name', 'N/A')}")
                print(f"   价格: {item.get('price', 'N/A')}")
                print(f"   原价: {item.get('original_price', 'N/A')}")
                print(f"   评分: {item.get('rating', 'N/A')}")
                print(f"   评论数: {item.get('reviews_count', 'N/A')}")
                print(f"   库存: {item.get('availability', 'N/A')}")
                print(f"   描述: {str(item.get('description', 'N/A'))[:200]}...")
        else:
            print(f"   ❌ 失败: {result2_data.get('error', 'Unknown error')}")
        
        # 测试3: 多URL提取
        print("\n🔗 测试3: 多URL提取")
        multi_urls = [
            "https://en.wikipedia.org/wiki/Machine_learning",
            "https://en.wikipedia.org/wiki/Deep_learning"
        ]
        
        result3 = await mock_mcp.call_tool(
            "crawl_and_extract",
            urls=json.dumps(multi_urls),
            extraction_schema="research",
            filter_query="machine learning AI neural network",
            max_urls=2,
            user_id="test_user"
        )
        
        print("✅ 多URL测试结果:")
        result3_data = json.loads(result3)
        if result3_data["status"] == "success":
            items = result3_data["data"]["extracted_items"]
            stats = result3_data["data"]["processing_stats"]
            print(f"   提取了 {len(items)} 个数据项")
            print(f"   处理统计: {stats['successful_extractions']}/{stats['total_urls']} 成功")
            print(f"   成功率: {stats['success_rate']}%")
            print(f"   平均处理时间: {stats['average_processing_time_seconds']}秒")
        else:
            print(f"   ❌ 失败: {result3_data.get('error', 'Unknown error')}")
        
        # 测试4: 自定义schema
        print("\n⚙️ 测试4: 自定义schema提取")
        custom_schema = {
            "name": "Product Review Extractor",
            "content_type": "product",
            "fields": [
                {"name": "product_name", "description": "Product name"},
                {"name": "current_price", "description": "Current selling price"},
                {"name": "customer_rating", "description": "Customer rating score"},
                {"name": "review_summary", "description": "Summary of customer reviews"}
            ]
        }
        
        result4 = await mock_mcp.call_tool(
            "crawl_and_extract",
            urls=json.dumps([amazon_url]),
            extraction_schema=json.dumps(custom_schema),
            filter_query="",
            max_urls=1,
            user_id="test_user"
        )
        
        print("✅ 自定义schema测试结果:")
        result4_data = json.loads(result4)
        if result4_data["status"] == "success":
            items = result4_data["data"]["extracted_items"]
            print(f"   提取了 {len(items)} 个数据项")
            if items:
                item = items[0]
                print(f"   产品名: {item.get('product_name', 'N/A')}")
                print(f"   当前价格: {item.get('current_price', 'N/A')}")
                print(f"   客户评分: {item.get('customer_rating', 'N/A')}")
                print(f"   评论摘要: {str(item.get('review_summary', 'N/A'))[:150]}...")
        else:
            print(f"   ❌ 失败: {result4_data.get('error', 'Unknown error')}")
        
        print("\n🎉 所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🔥 启动crawl_and_extract MCP工具测试...")
    asyncio.run(test_crawl_extract_tool())