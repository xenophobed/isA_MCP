from typing import Dict, Any, Callable, Optional
import asyncio
import logging
import inspect

logger = logging.getLogger(__name__)

class ToolExecutor:
    """Executes tools with proper parameter handling and result formatting."""
    
    def __init__(self, tools: Dict[str, Callable]):
        self.tools = tools
        
    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the provided parameters.
        
        Args:
            tool_name: The name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            The result of tool execution
        """
        try:
            # Get tool function
            tool_func = self.tools.get(tool_name)
            
            if not tool_func:
                raise ValueError(f"Tool not found: {tool_name}")
            
            # Prepare parameters - filter to only accept valid parameters
            sig = inspect.signature(tool_func)
            valid_params = {}
            
            for param_name, param in sig.parameters.items():
                if param_name in parameters:
                    valid_params[param_name] = parameters[param_name]
                elif param.default is not inspect.Parameter.empty:
                    # Use default value if parameter not provided
                    pass
                else:
                    # Required parameter not provided
                    raise ValueError(f"Missing required parameter: {param_name}")
            
            # Execute tool
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**valid_params)
            else:
                result = tool_func(**valid_params)
                
            # Format result
            if result is None:
                return {"message": "Tool executed successfully with no result"}
            elif isinstance(result, dict):
                return result
            else:
                return {"data": result}
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            raise
