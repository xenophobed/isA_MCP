import asyncio
import os
from dotenv import load_dotenv
from app.graphs.kg_graph.builder.register_capabilities import register_initial_capabilities
from app.graphs.P_Graph.contextual_route_node import ContextualRouteNode
from dataclasses import dataclass

@dataclass
class Message:
    content: str

async def test_capability_flow():
    # 加载环境变量
    load_dotenv()
    
    route_node = None
    
    try:
        # 1. 首先注册系统能力
        print("\n=== Registering System Capabilities ===")
        await register_initial_capabilities()
        print("✓ Capabilities registered successfully")

        # 2. 创建路由节点
        route_node = ContextualRouteNode(
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            neo4j_user=os.getenv("NEO4J_USERNAME", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "admin@123")
        )

        # 3. 测试不同类型的问题
        test_cases = [
            {
                "question": "What are the specifications of the latest MacBook?",
                "core_elements": ["product", "specification", "MacBook"]
            },
            {
                "question": "What are the latest news about iPhone 15?",
                "core_elements": ["news", "current events", "iPhone 15"]
            },
            {
                "question": "Where is my order #12345?",
                "core_elements": ["order", "tracking", "delivery"]
            }
        ]

        # 4. 执行测试
        for case in test_cases:
            print(f"\n=== Testing: {case['question']} ===")
            print(f"Core Elements: {case['core_elements']}")
            
            # 构建状态
            state = {
                "messages": [Message(content=case["question"])],
                "plan": {
                    "core_elements": case["core_elements"]
                }
            }
            
            # 处理路由
            result = await route_node.process(state)
            
            # 打印结果
            print("\nRouting Results:")
            print(f"Graph Source: {result['search_results']['graph_source']}")
            print(f"Node Name: {result['search_results']['node_name']}")
            print(f"Combined Confidence: {result['search_results']['combined_confidence']}")
            print(f"Matched Elements: {result['search_results']['matched_elements']}")
            
            if result['search_results']['selected_capability']:
                cap = result['search_results']['selected_capability']
                print("\nSelected Capability:")
                print(f"- Name: {cap['capability']['name']}")
                print(f"  Type: {cap['capability']['type']}")
                print(f"  Graph Source: {cap['capability']['graph_source']}")
                print(f"  Node Name: {cap['capability']['node_name']}")
                print(f"  Matched Elements: {cap['matched_elements']}")
                print(f"  Relevance Score: {cap['relevance_score']}")
            
            if result['search_results']['capabilities']:
                print("\nAll Matched Capabilities:")
                for cap in result['search_results']['capabilities']:
                    print(f"\n- Name: {cap['capability']['name']}")
                    print(f"  Type: {cap['capability']['type']}")
                    print(f"  Graph Source: {cap['capability']['graph_source']}")
                    print(f"  Node Name: {cap['capability']['node_name']}")
                    print(f"  Matched Elements: {cap['matched_elements']}")
                    print(f"  Relevance Score: {cap['relevance_score']}")
            
            if result['search_results']['similar_conversations']:
                print("\nSimilar Conversations:")
                for conv in result['search_results']['similar_conversations']:
                    print(f"\n- Conversation ID: {conv['conversation_id']}")
                    print(f"  Relevance Score: {conv['relevance_score']}")
                    print(f"  Matched Elements: {conv['matched_elements']}")
                    print("  Facts:")
                    for fact in conv['facts']:
                        print(f"    * {fact['content']}")
            
            print("\n" + "="*50)

    except Exception as e:
        print(f"Error during test: {str(e)}")
        raise
    finally:
        if route_node:
            await route_node.close()

if __name__ == "__main__":
    asyncio.run(test_capability_flow())