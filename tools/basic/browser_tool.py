import asyncio
import logging
import json
from typing import Dict, Any, Optional, ClassVar, NoReturn
from app.services.agent.tools.tools_manager import tools_manager
from browser_use import Agent as BrowserAgent
from app.services.ai.models.ai_factory import AIFactory
from app.config.browser_config import (
    CHROME_INSTANCE_PATH,
    CHROME_HEADLESS,
    CHROME_PROXY_SERVER,
    CHROME_PROXY_USERNAME,
    CHROME_PROXY_PASSWORD,
    BROWSER_HISTORY_DIR,
)
import uuid
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

class LLMWrapper:
    """Wrapper class to provide structured output functionality for browser-use."""
    
    def __init__(self, llm):
        self.llm = llm
        
    async def __call__(self, *args, **kwargs):
        return await self.llm(*args, **kwargs)
        
    def with_structured_output(self):
        """Required by browser-use to handle structured outputs."""
        return self

def browser_error_handler(state):
    """Handle browser tool errors"""
    error = state.get("error")
    return {
        "messages": [{
            "content": f"Browser automation error: {error}. Please try again later.",
            "type": "error"
        }]
    }

class BrowserTool(BaseTool):
    """Browser automation tool that supports async invocation."""
    
    name: ClassVar[str] = "browse"
    description: ClassVar[str] = "Execute browser automation tasks based on natural language instructions."
    
    def _run(self, instruction: str) -> NoReturn:
        """Sync version is not supported."""
        raise NotImplementedError("BrowserTool only supports async operations")
    
    async def _arun(self, instruction: str) -> Dict[str, Any]:
        """Execute browser automation tasks asynchronously."""
        try:
            # Get LLM from factory
            ai_factory = AIFactory.get_instance()
            llm = ai_factory.get_llm(model_name="gpt-4o-mini", provider="yyds")
            
            # Create browser agent
            agent = BrowserAgent(
                task=instruction,
                llm=llm
            )
            
            result = await agent.run()
            
            # Handle different result types
            if isinstance(result, dict):
                return {
                    "content": result.get("content", str(result)),
                    "gif_path": result.get("gif_path")
                }
            else:
                return {
                    "content": str(result),
                    "gif_path": None
                }
                
        except Exception as e:
            logger.error(f"Error executing browser task: {str(e)}")
            raise

# Create and register the tool instance
browser_tool = BrowserTool()
tools_manager.register_tool(browser_tool)
