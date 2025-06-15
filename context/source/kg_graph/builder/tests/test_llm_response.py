from app.services.ai.llm.llm_factory import LLMFactory
from langchain.prompts import ChatPromptTemplate
import json
import asyncio
from datetime import datetime
import pytest
from app.config.config_manager import config_manager

async def test_llm_extraction():
    """Test LLM's knowledge extraction capabilities"""
    # Test conversation data
    test_conversation = {
        "conversation_id": "test_conv_1",
        "timestamp": "2024-01-01 10:00:00",
        "participants": "user_123, agent_456",
        "conversation_text": """
[2024-01-01 10:00:00] user_123: 你们的AI助手产品具体价格是多少？
[2024-01-01 10:00:05] agent_456: 我们的AI助手产品分为基础版和企业版，基础版每年5万起，企业版需要根据具体需求定制。
[2024-01-01 10:00:15] user_123: 基础版都包含哪些功能？
[2024-01-01 10:00:20] agent_456: 基础版包含智能对话、知识库管理、多轮对话等核心功能。
"""
    }

    # Create prompt template with proper JSON formatting
    prompt_template = """
分析以下完整对话内容，提取关键知识信息。

对话背景:
对话ID: {conversation_id}
时间: {timestamp}
参与用户: {participants}

完整对话记录:
{conversation_text}

请严格按照以下JSON格式返回结果:
{{
    "atomic_facts": [
        {{
            "key_elements": ["用户A", "产品X", "购买意向"],
            "atomic_fact": "用户A在2024-01-01表达了对产品X的购买意向"
        }}
    ]
}}

要求：
1. 必须是合法的JSON格式
2. 必须包含 atomic_facts 数组
3. 每个原子事实必须包含 key_elements 和 atomic_fact
4. 不要添加其他字段
5. 不要包含注释或说明
"""

    # Create prompt template
    extraction_prompt = ChatPromptTemplate.from_template(prompt_template)

    try:
        # Call LLM
        llm_config = config_manager.get_config('llm')
        llm = await LLMFactory.create_llm_service("openai", llm_config)
        response = await llm.agenerate([
            extraction_prompt.format_messages(**test_conversation)
        ])
        
        # Get response text
        response_text = response
        print("\n=== Raw LLM Response ===")
        print(response_text)
        print("=======================\n")
        
        # Try to parse JSON
        try:
            result = json.loads(response_text)
            print("\n=== Parsed JSON ===")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("==================\n")
            
            # Validate result structure
            assert "atomic_facts" in result, "Response missing atomic_facts"
            assert isinstance(result["atomic_facts"], list), "atomic_facts should be a list"
            
            for fact in result["atomic_facts"]:
                assert "key_elements" in fact, "Fact missing key_elements"
                assert "atomic_fact" in fact, "Fact missing atomic_fact"
                assert isinstance(fact["key_elements"], list), "key_elements should be a list"
                assert isinstance(fact["atomic_fact"], str), "atomic_fact should be a string"
            
            print("\n=== Validation Passed ===")
            return result
            
        except json.JSONDecodeError as e:
            print("\n=== JSON Parse Error ===")
            print(f"Error: {str(e)}")
            print(f"Position: {e.pos}")
            print(f"Line: {e.lineno}, Column: {e.colno}")
            raise
            
    except Exception as e:
        print(f"\n=== Error ===")
        print(f"Type: {type(e)}")
        print(f"Message: {str(e)}")
        raise

# Add pytest fixture for async testing
@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

if __name__ == "__main__":
    asyncio.run(test_llm_extraction())