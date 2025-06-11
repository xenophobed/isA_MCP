from typing import List, Dict, Optional
from pydantic import BaseModel
from app.services.ai.models.ai_factory import AIFactory
from app.config.config_manager import config_manager
from app.services.agent.agent_manager import AgentManager

logger = config_manager.get_logger(__name__)

class SemanticVector(BaseModel):
    core_concepts: List[str]
    domain: List[str]
    business_entity: List[str]

class FunctionalVector(BaseModel):
    common_operations: List[str]
    query_patterns: List[str]
    sample_queries: List[str]

class ContextualVector(BaseModel):
    usage_scenarios: List[str]
    data_sensitivity: str
    update_frequency: str

class DatabaseMetadata(BaseModel):
    table_id: str
    semantic_vector: SemanticVector
    functional_vector: FunctionalVector
    contextual_vector: ContextualVector

class DBMetaExtractor:
    """Extracts structured metadata from database content"""
    
    def __init__(self):
        self.agent_manager = AgentManager.get_instance()
        self.llm_service = None
        self.embed_service = None
        self.agent = None
        
    async def initialize(self):
        """Initialize required services"""
        if not self.llm_service:
            llm_config = config_manager.get_config('llm')
            ai_factory = AIFactory.get_instance()
            self.llm_service = ai_factory.get_llm(
                model_name="llama3.1",
                provider="ollama",
                config=llm_config
            )
            self.embed_service = ai_factory.get_embedding(
                model_name="bge-m3",
                provider="ollama",
                config=llm_config
            )
        
        if not self.agent:
            config = {
                "model": {
                    "model_name": "llama3.1",
                    "provider": "ollama",
                    "config": {
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                },
                "system_prompt": "你是一个专业的数据库分析专家，能够提取数据库元数据并生成结构化输出。",
                "capabilities": {
                    "interactive": {
                        "structured": {
                            "output_format": "json"
                        }
                    }
                }
            }
            
            self.agent = await self.agent_manager.create_agent(
                agent_type="structured", 
                name="DB Metadata Extractor",
                description="提取数据库元数据的结构化代理",
                config=config,
                persist=False
            )
        
    async def extract_from_database(self, database_content: Dict) -> DatabaseMetadata:
        """Extract metadata from database content"""
        await self.initialize()  # Ensure services are initialized
        try:
            if not database_content:
                raise ValueError("Empty database content provided")
            
            # 1. Get sample records (first 10)
            sample_records = database_content["content"][:10]
            
            # 2. Format database info and sample records
            formatted_content = {
                "database_info": database_content["database_info"],
                "sample_records": sample_records
            }
            
            # 3. Extract metadata using structured agent
            prompt = f"""
            请分析以下数据库内容并提取元数据:
            
            数据库信息:
            {formatted_content['database_info']}
            
            示例记录:
            {formatted_content['sample_records']}
            
            提取并返回以下格式的元数据:
            - table_id: 表标识符
            - semantic_vector: 语义向量，包含core_concepts(核心概念)、domain(领域)、business_entity(业务实体)
            - functional_vector: 功能向量，包含common_operations(常见操作)、query_patterns(查询模式)、sample_queries(示例查询)
            - contextual_vector: 上下文向量，包含usage_scenarios(使用场景)、data_sensitivity(数据敏感度)、update_frequency(更新频率)
            """
            
            result = await self.agent.execute(prompt)
            
            # 从结构化能力中获取结构化数据
            structured_data = None
            if hasattr(self.agent, "get_structured_data"):
                structured_data = self.agent.get_structured_data()
            
            if not structured_data:
                # 尝试从响应中解析JSON
                import re
                import json
                
                response = result.get("output")
                response_text = response.content if hasattr(response, "content") else str(response)
                
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    structured_data = json.loads(json_match.group(0))
            
            # 转换为DatabaseMetadata模型
            metadata = DatabaseMetadata(**structured_data)
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting database metadata: {str(e)}")
            raise
