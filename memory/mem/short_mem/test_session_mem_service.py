import asyncio
import logging
import sys
import os
import uuid
from typing import Dict, List, Any, Optional, TypedDict, Literal, Union
from datetime import datetime, timezone
import json
import langgraph

os.environ["ENV"] = "local"

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from app.services.ai.mem.short_mem.session_mem_service import SessionMemoryService
from app.services.ai.tools.tools_manager import tools_manager

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import CheckpointTuple

# LangChain imports
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SessionMemoryTest")

# 定义图状态
class GraphState(TypedDict):
    """图状态定义"""
    messages: List[Any]  # 消息列表
    user_id: str
    thread_id: str
    timestamp: str

# 工具定义
@tools_manager.register_tool()
def get_weather(city: str) -> str:
    """获取指定城市的天气信息"""
    if city.lower() in ["北京", "beijing"]:
        return "北京今天晴朗，气温25°C，微风。"
    elif city.lower() in ["上海", "shanghai"]:
        return "上海今天多云，气温28°C，有轻微降雨可能。"
    elif city.lower() in ["sf", "san francisco"]:
        return "It's always sunny in San Francisco!"
    else:
        return f"{city}今天天气晴朗，气温适宜。"

async def setup():
    """设置测试环境"""
    await tools_manager.initialize(test_mode=True)
    logger.info("工具管理器初始化完成")

async def test_session_memory_service():
    """测试SessionMemoryService基本功能"""
    logger.info("=== 开始测试SessionMemoryService基本功能 ===")
    
    # 初始化SessionMemoryService
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    session_memory = SessionMemoryService(
        mongo_uri=mongo_uri,
        db_name="haley_ai_test",
        collection_name="session_memory_test"
    )
    
    try:
        # 初始化服务
        await session_memory.initialize()
        logger.info("SessionMemoryService初始化完成")
        
        # 创建一个测试会话
        thread_id = f"test-{uuid.uuid4()}"
        logger.info(f"创建测试会话: {thread_id}")
        
        # 创建一些测试消息
        test_messages = [
            HumanMessage(content="你好，我想知道北京的天气", id=str(uuid.uuid4())),
            AIMessage(content="北京今天晴朗，气温25°C，微风。", id=str(uuid.uuid4())),
            HumanMessage(content="谢谢，上海呢？", id=str(uuid.uuid4())),
            AIMessage(content="上海今天多云，气温28°C，有轻微降雨可能。", id=str(uuid.uuid4()))
        ]
        
        # 创建一个测试checkpoint
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = {
            "channel_values": {
                "messages": test_messages
            }
        }
        checkpoint_tuple = CheckpointTuple(config=config, checkpoint=checkpoint, metadata={})
        
        # 转换checkpoint到消息
        messages = await session_memory.convert_checkpoint_to_messages(checkpoint_tuple)
        logger.info(f"转换checkpoint到消息: {len(messages)} 条消息")
        
        # 清理测试数据
        await session_memory.delete_session(thread_id)
        logger.info(f"清理测试会话: {thread_id}")
        
        # 关闭服务
        await session_memory.cleanup()
        logger.info("SessionMemoryService清理完成")
        
    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)
        await session_memory.cleanup()

async def test_langgraph_with_session_memory():
    """测试LangGraph与SessionMemoryService集成"""
    logger.info("=== 开始测试LangGraph与SessionMemoryService集成 ===")
    
    # 初始化SessionMemoryService
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    session_memory = SessionMemoryService(
        mongo_uri=mongo_uri,
        db_name="haley_ai_test",
        collection_name="session_memory_test"
    )
    
    try:
        # 初始化服务
        await session_memory.initialize()
        logger.info("SessionMemoryService初始化完成")
        
        # 创建一个测试会话ID
        thread_id = f"test-{uuid.uuid4()}"
        logger.info(f"创建测试会话: {thread_id}")
        
        # 创建LLM
        llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0
        )
        
        # 定义agent节点函数
        async def agent_node(state: GraphState) -> GraphState:
            """Agent节点处理函数"""
            # 获取最后一条用户消息
            last_human_message = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    last_human_message = msg
                    break
            
            if not last_human_message:
                logger.warning("没有找到用户消息")
                return state
            
            logger.info(f"处理用户消息: {last_human_message.content}")
            
            # 检查是否包含天气查询
            weather_keywords = ["天气", "weather", "温度", "temperature", "气温"]
            is_weather_query = any(keyword in last_human_message.content.lower() for keyword in weather_keywords)
            
            new_state = state.copy()
            
            if is_weather_query:
                # 提取城市名称 (简化版，实际应用中可能需要更复杂的NER)
                city_keywords = ["北京", "beijing", "上海", "shanghai", "sf", "san francisco"]
                city = "北京"  # 默认城市
                
                for keyword in city_keywords:
                    if keyword.lower() in last_human_message.content.lower():
                        city = keyword
                        break
                
                # 调用天气工具
                weather_info = get_weather.invoke(city)
                
                # 创建工具消息
                tool_message = ToolMessage(
                    content=weather_info,
                    name="get_weather",
                    tool_call_id=f"call_{uuid.uuid4()}",
                    id=str(uuid.uuid4())
                )
                
                # 创建AI响应
                ai_response = f"根据查询，{weather_info}"
                ai_message = AIMessage(content=ai_response, id=str(uuid.uuid4()))
                
                # 更新消息列表
                new_state["messages"] = state["messages"] + [tool_message, ai_message]
            else:
                # 直接使用LLM生成回复
                messages = [SystemMessage(content="你是一个友好的AI助手。", id=str(uuid.uuid4()))] + state["messages"]
                ai_response = await llm.ainvoke(messages)
                
                # 确保 ai_response 有 id
                if not hasattr(ai_response, 'id') or not ai_response.id:
                    ai_response.id = str(uuid.uuid4())
                
                # 更新消息列表
                new_state["messages"] = state["messages"] + [ai_response]
            
            return new_state
        
        # 构建图
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node("agent", agent_node)
        
        # 设置起始节点
        workflow.set_entry_point("agent")
        
        # 添加边
        workflow.add_edge("agent", END)
        
        # 创建checkpointer，添加更多配置
        checkpointer = session_memory.create_checkpointer("weather_agent")
        
        # 编译图
        graph = workflow.compile(checkpointer=checkpointer)
        
        # 手动保存一个测试checkpoint
        logger.info("手动保存一个测试checkpoint")
        checkpoint_id = str(uuid.uuid4())
        manual_config = {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id, "checkpoint_ns": ""}}
        
        # 创建一个符合LangGraph格式的checkpoint
        test_message = HumanMessage(content="手动保存的测试消息", id=str(uuid.uuid4()))
        manual_checkpoint = {
            "id": checkpoint_id,
            "channel_values": {
                "messages": [test_message]
            },
            "channel_versions": {},  # 添加空的channel_versions字段
            "pending_sends": [],     # 添加空的pending_sends字段
            "pending_receives": [],  # 添加空的pending_receives字段
            "pending_tasks": [],     # 添加空的pending_tasks字段
            "versions_seen": {},     # 添加空的versions_seen字段
            "task_counter": 0       # 添加task_counter字段
        }
        
        # 创建一个包含必要元数据的metadata
        metadata = {
            "step": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "graph_id": "weather_agent",
            "source": "manual_test"
        }
        
        # 创建一个空的new_versions字典，表示没有新版本
        new_versions = {}
        
        # 保存checkpoint
        await checkpointer.aput(manual_config, manual_checkpoint, metadata, new_versions)
        logger.info(f"手动保存完成，checkpoint_id: {checkpoint_id}")
        
        # 验证手动保存是否成功，增加等待时间
        logger.info("等待MongoDB保存完成...")
        await asyncio.sleep(1.0)  # 增加等待时间，确保MongoDB有足够时间保存
        
        # 直接查询MongoDB以验证保存是否成功
        checkpoints_collection = session_memory._db["checkpoints_aio"]
        direct_query_docs = await checkpoints_collection.find({"thread_id": thread_id}).to_list(length=100)
        logger.info(f"直接查询MongoDB找到 {len(direct_query_docs)} 个文档")
        
        # 使用服务API获取消息
        manual_saved_messages = await session_memory.get_langchain_messages(thread_id)
        logger.info(f"手动保存后的会话历史: {len(manual_saved_messages)} 条消息")
        
        # 测试场景1: 首次对话
        logger.info("=== 测试场景1: 首次对话 ===")
        
        # 初始状态
        initial_state: GraphState = {
            "messages": [HumanMessage(content="你好，我想知道北京的天气", id=str(uuid.uuid4()))],
            "user_id": "test_user_123",
            "thread_id": thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # 执行图，使用更详细的配置
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": str(uuid.uuid4()),
                "checkpoint_ns": "haley_ai_test",
                "step": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel_versions": {}  # 添加空的channel_versions字段
            }
        }
        result1 = await graph.ainvoke(initial_state, config)
        
        # 添加更长的延迟，确保checkpointer有足够时间保存
        logger.info("等待checkpointer保存...")
        await asyncio.sleep(1.0)
        
        logger.info("首次对话结果:")
        for msg in result1["messages"]:
            logger.info(f"{type(msg).__name__}: {msg.content}")
        
        # 直接查询MongoDB数据库
        logger.info("直接查询MongoDB数据库:")
        # 直接访问checkpoints_aio集合
        checkpoints_collection = session_memory._db["checkpoints_aio"]
        # 修改查询方式，thread_id存储在文档的根级别
        all_docs = await checkpoints_collection.find({"thread_id": thread_id}).to_list(length=100)
        logger.info(f"在集合中找到 {len(all_docs)} 个文档")
        for doc in all_docs:
            logger.info(f"文档ID: {doc.get('_id')}, thread_id: {doc.get('thread_id', 'unknown')}")
        
        # 获取保存的会话历史
        saved_messages = await session_memory.get_langchain_messages(thread_id)
        logger.info(f"保存的会话历史: {len(saved_messages)} 条消息")
        
        # 测试场景2: 继续对话
        logger.info("=== 测试场景2: 继续对话 ===")
        
        # 获取保存的会话历史
        checkpoint = await session_memory.get_checkpoint(thread_id)
        if checkpoint and checkpoint.checkpoint:
            messages = checkpoint.checkpoint.get("channel_values", {}).get("messages", [])
            logger.info(f"从checkpoint获取到 {len(messages)} 条消息")
            
            # 添加新的用户消息
            follow_up_state: GraphState = {
                "messages": messages + [HumanMessage(content="上海的天气怎么样？", id=str(uuid.uuid4()))],
                "user_id": "test_user_123",
                "thread_id": thread_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # 执行图
            result2 = await graph.ainvoke(follow_up_state, config)
            await asyncio.sleep(1.0)  # 等待保存
            
            logger.info("继续对话结果:")
            # 只显示最新的消息
            if len(result2["messages"]) > len(messages):
                new_messages = result2["messages"][len(messages):]
                for msg in new_messages:
                    logger.info(f"{type(msg).__name__}: {msg.content}")
        else:
            logger.warning("未找到保存的会话历史")
        
        # 测试场景3: 列出所有会话
        logger.info("=== 测试场景3: 列出所有会话 ===")
        
        sessions = await session_memory.list_sessions()
        logger.info(f"找到 {len(sessions)} 个会话")
        for session in sessions:
            logger.info(f"会话ID: {session.get('_id')}, 消息数: {session.get('message_count', 0)}")
        
        # 清理测试数据
        await session_memory.delete_session(thread_id)
        logger.info(f"清理测试会话: {thread_id}")
        
        # 关闭服务
        await session_memory.cleanup()
        logger.info("SessionMemoryService清理完成")
        
    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)
        await session_memory.cleanup()

async def test_contextual_service_integration():
    """测试与ContextualService集成"""
    logger.info("=== 开始测试与ContextualService集成 ===")
    
    # 这部分需要在实际集成时实现
    # 这里只是一个示例框架
    
    logger.info("ContextualService集成测试暂未实现")

async def main():
    """主函数"""
    logger.info("启动SessionMemoryService测试脚本")
    
    # 设置测试环境
    await setup()
    
    # 运行基本功能测试
    await test_session_memory_service()
    
    # 运行LangGraph集成测试
    await test_langgraph_with_session_memory()
    
    # 运行ContextualService集成测试
    # await test_contextual_service_integration()
    
    logger.info("测试脚本执行完毕")

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
