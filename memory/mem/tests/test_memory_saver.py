import pytest
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any

def test_read_memory_from_memory_saver():
    # 创建 MemorySaver 实例
    memory_saver = MemorySaver()
    
    # 假设我们有一个会话ID
    session_id = "test_session"
    
    # 从 MemorySaver 读取特定会话的记忆
    # get_memory 方法返回该会话的所有存储的状态
    session_memory = memory_saver.get_memory(session_id)
    
    # 如果需要读取最新的状态
    latest_state = memory_saver.get_latest(session_id)
    
    # 读取所有会话的历史记录
    all_sessions = memory_saver.list_runs()
    
    # 读取特定会话的所有步骤
    steps = memory_saver.list_steps(session_id)
    
    # 读取特定步骤的状态
    step_state = memory_saver.get_step(session_id, step_id="step_1")

def test_read_specific_memory():
    memory_saver = MemorySaver()
    session_id = "test_session"
    
    # 读取特定会话的特定键值
    # 假设状态中包含 'messages' 键
    state = memory_saver.get_latest(session_id)
    if state:
        messages = state.get('messages', [])
        # 处理消息列表

def test_memory_saver_with_mock_data():
    # 创建 MemorySaver 实例
    memory_saver = MemorySaver()
    session_id = "chat_123"

    # 模拟对话数据
    mock_messages = [
        {"role": "human", "content": "你好，请问今天天气如何？"},
        {"role": "ai", "content": "今天天气晴朗，气温25度。"},
        {"role": "human", "content": "谢谢，那我需要带伞吗？"},
        {"role": "ai", "content": "今天不需要带伞，天气很好。"}
    ]

    # 模拟状态数据
    mock_state = {
        "messages": mock_messages,
        "metadata": {
            "timestamp": "2024-03-20 10:00:00",
            "user_id": "user_001"
        }
    }

    # 存储模拟数据 - 使用 save 方法
    memory_saver.save(session_id, mock_state)

    # 测试读取数据
    # 1. 读取最新状态
    latest_state = memory_saver.get_latest(session_id)
    assert latest_state is not None
    assert len(latest_state["messages"]) == 4
    
    # 2. 读取所有会话
    all_sessions = memory_saver.list_runs()
    assert session_id in all_sessions
    
    # 3. 读取特定会话的所有消息
    session_memory = memory_saver.get_memory(session_id)
    assert session_memory is not None

    # 打印消息历史
    print("\n=== 消息历史 ===")
    for msg in latest_state["messages"]:
        print(f"{msg['role']}: {msg['content']}")

def test_multiple_chat_sessions():
    memory_saver = MemorySaver()
    
    # 模拟多个会话
    sessions = {
        "chat_001": [
            {"role": "human", "content": "我想学习Python"},
            {"role": "ai", "content": "Python是一个很好的选择！让我们开始吧。"}
        ],
        "chat_002": [
            {"role": "human", "content": "如何使用LangGraph？"},
            {"role": "ai", "content": "LangGraph是一个强大的工具，首先你需要..."}
        ]
    }

    # 存储多个会话的数据 - 使用 save 方法
    for session_id, messages in sessions.items():
        state = {
            "messages": messages,
            "metadata": {
                "timestamp": "2024-03-20 10:00:00",
                "session_type": "learning"
            }
        }
        memory_saver.save(session_id, state)

    # 测试读取多个会话
    all_sessions = memory_saver.list_runs()
    assert len(all_sessions) >= 2

    # 打印所有会话的最新消息
    print("\n=== 所有会话的最新消息 ===")
    for session_id in sessions.keys():
        latest = memory_saver.get_latest(session_id)
        if latest and latest["messages"]:
            last_message = latest["messages"][-1]
            print(f"Session {session_id} - {last_message['role']}: {last_message['content']}")

if __name__ == "__main__":
    # 运行测试并打印结果
    print("\n=== 运行单个会话测试 ===")
    test_memory_saver_with_mock_data()
    
    print("\n=== 运行多会话测试 ===")
    test_multiple_chat_sessions()
