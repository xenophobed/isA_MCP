from pydantic import BaseModel, Field
from typing import Optional
from app.config.config_manager import config_manager
from app.services.ai.models.ai_factory import AIFactory
from app.services.ai.prompt.prompt_service import PromptService
from langchain_core.output_parsers import PydanticOutputParser

class ToolQueryMetadata(BaseModel):
    """Structured metadata extracted from natural language query"""
    core_concept: str = Field(
        description="The main capability being requested",
        example="weather"
    )
    domain: str = Field(
        description="The domain of the capability",
        example="weather-service"
    )
    service_type: str = Field(
        description="Type of service",
        example="real-time"
    )
    operation: str = Field(
        description="The operation type",
        example="get"
    )
    usage_context: str = Field(
        description="The context of usage",
        example="real-time-query"
    )
    description: str = Field(
        description="A clear description of the capability being requested",
        example="Get current weather conditions for a specific location"
    )

class ToolQueryParser:
    """Parses natural language queries into structured tool metadata"""
    
    def __init__(self):
        self.chain = None
        
    async def initialize(self):
        """Initialize the parser chain"""
        # Get LLM config and create service
        llm = AIFactory.get_instance().get_llm(
            model_name="llama3.1",
            provider="ollama",
        )
        
        # Setup prompt and parser
        prompt_service = PromptService({"template_path": "app/services/ai/prompt/templates"})
        prompt = await prompt_service.get_prompt("tool/query_parser", output_model=ToolQueryMetadata)
        parser = PydanticOutputParser(pydantic_object=ToolQueryMetadata)
        
        # Create the chain
        self.chain = prompt | llm.client | parser
    
    async def parse_query(self, query_text: str) -> ToolQueryMetadata:
        """Parse natural language query into structured metadata"""
        if not self.chain:
            await self.initialize()
        return await self.chain.ainvoke({"query": query_text}) 