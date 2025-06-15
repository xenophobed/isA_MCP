# app/kg/builder/extractors.py
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.services.ai.models.ai_factory import AIFactory
from app.config.config_manager import config_manager
import json

config_manager.set_log_level("INFO")
logger = config_manager.get_logger(__name__)

class AtomicFact(BaseModel):
    key_elements: List[str] = Field(description="The essential elements that are pivotal to the atomic fact")
    atomic_fact: str = Field(description="The smallest, indivisible facts from the conversation")

class Extraction(BaseModel):
    atomic_facts: List[AtomicFact] = Field(description="List of atomic facts")

class KnowledgeExtractor:
    def __init__(self):
        self.llm = None
        self.extraction_prompt = None
        
    async def initialize(self):
        """Async initialization method"""
        if self.llm is None:
            llm_config = config_manager.get_config('llm')
            self.llm = AIFactory.get_instance().get_llm(
                model_name="llama3.1",
                provider="ollama",
                config=llm_config
            )
            self.extraction_prompt = ChatPromptTemplate.from_template("""
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
""")

    async def process_conversation(self, messages: List) -> Dict:
        """处理完整对话"""
        try:
            # Ensure LLM is initialized
            await self.initialize()
            
            # 按时间排序消息
            sorted_messages = sorted(messages, key=lambda x: x.timestamp)
            
            # 提取对话基本信息
            conversation_id = sorted_messages[0].conversation_id
            start_time = sorted_messages[0].timestamp
            participants = set()
            
            # 构建完整对话文本
            conversation_text = []
            for msg in sorted_messages:
                if hasattr(msg, 'sender') and msg.sender.get('user_id'):
                    participants.add(msg.sender.get('user_id'))
                timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                user_id = msg.sender.get('user_id', 'system')
                conversation_text.append(f"[{timestamp}] {user_id}: {msg.content}")
            
            # 准备提示词参数
            prompt_params = {
                "conversation_id": conversation_id,
                "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "participants": ", ".join(participants),
                "conversation_text": "\n".join(conversation_text)
            }
            
            # 调用LLM提取知识
            messages = [{"role": "user", "content": self.extraction_prompt.format(**prompt_params)}]
            response = await self.llm.agenerate(messages)
            
            # 解析响应 (response is now a list with one item)
            result = json.loads(response[0])
            
            # 验证结果结构
            assert "atomic_facts" in result, "Response missing atomic_facts"
            assert isinstance(result["atomic_facts"], list), "atomic_facts should be a list"
            
            for fact in result["atomic_facts"]:
                assert "key_elements" in fact, "Fact missing key_elements"
                assert "atomic_fact" in fact, "Fact missing atomic_fact"
                assert isinstance(fact["key_elements"], list), "key_elements should be a list"
                assert isinstance(fact["atomic_fact"], str), "atomic_fact should be a string"
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing conversation {conversation_id}: {str(e)}")
            raise