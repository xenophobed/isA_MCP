from app.services.graphs.kg_graph.builder.capability_builder import SystemCapabilityBuilder, KnowledgeSource, ToolCapability
from datetime import datetime
import os
from dotenv import load_dotenv

async def register_initial_capabilities():
    """初始化系统所有基础能力"""
    load_dotenv()
    
    builder = SystemCapabilityBuilder(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
        neo4j_user=os.getenv("NEO4J_USERNAME", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "admin@123")
    )

    # 1. 注册向量存储知识库
    vector_kb = KnowledgeSource(
        capability_id="kb_vector_store",
        name="Vector Knowledge Base",
        type="knowledge_base",
        description="General knowledge base for product information and FAQs",
        last_updated=datetime.now(),
        source_type="vectorstore",
        content_types=["text", "pdf", "webpage"],
        update_frequency="daily",
        key_elements=["product", "specification", "FAQ", "documentation"],
        example_queries=[
            "What are the system requirements?",
            "How do I setup the product?"
        ],
        node_name="Retrieval_Node",
        graph_source="search_graph"
    )
    await builder.register_knowledge_source(vector_kb)

    # 2. 注册Web搜索能力
    web_search = ToolCapability(
        capability_id="tool_web_search",
        name="Web Search",
        type="search_tool",
        description="Search the web for real-time information",
        last_updated=datetime.now(),
        api_endpoint="/api/web-search",
        input_schema={"query": "string", "max_results": "int"},
        output_schema={"results": "List[SearchResult]"},
        rate_limits={"requests_per_minute": 30},
        key_elements=["news", "current events", "real-time", "web"],
        example_uses=[
            "What are the latest updates about product X?",
            "Find recent news about technology Y"
        ],
        node_name="Web_Search_Node",
        graph_source="search_graph"
    )
    await builder.register_tool(web_search)

    # 3. 注册API工具
    tracking_tool = ToolCapability(
        capability_id="tool_tracking",
        name="Order Tracking",
        type="api_tool",
        description="Track order status and delivery information",
        last_updated=datetime.now(),
        api_endpoint="/api/tracking",
        input_schema={"order_id": "string"},
        output_schema={"status": "string", "location": "string", "eta": "datetime"},
        rate_limits={"requests_per_minute": 100},
        key_elements=[
            "order", "tracking", "delivery", "shipping",
            "ship", "date", "schedule",  # 添加船期相关元素
            "vessel", "arrival", "departure",  # 添加更多相关元素
        ],
        example_uses=[
            "Where is my order?",
            "When will my package arrive?",
            "What's the status of my shipment?",
            "When will the vessel arrive?",
            "What's the schedule for STAR-V6KESEDZHWXU2?"
        ],
        node_name="Tool_API_Node",
        graph_source="search_graph"
    )
    await builder.register_tool(tracking_tool)

if __name__ == "__main__":
    import asyncio
    asyncio.run(register_initial_capabilities())