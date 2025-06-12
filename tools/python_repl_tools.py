from typing import Optional, List, Union, Dict, Any
from .tools_manager import tools_manager
from langchain_experimental.utilities import PythonREPL
import numpy as np
import sympy as sp
import math
import logging

logger = logging.getLogger(__name__)

python_repl = PythonREPL()

def code_error_handler(state):
    """Handle code execution errors"""
    error = state.get("error")
    return {
        "messages": [{
            "content": f"Code execution error: {error}. Please check your inputs.",
            "type": "error"
        }]
    }

@tools_manager.register_tool(error_handler=code_error_handler)
def execute_python_code(
    code_description: str,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """Execute Python code based on description.
    
    @semantic:
        concept: code-execution
        domain: python
        type: computation
        
    @functional:
        operation: execute
        input: code_description:string, additional_context:dict
        output: result:dict
    """
    try:
        # Log the incoming request
        logger.debug(f"Executing code for description: {code_description}")
        if additional_context:
            logger.debug(f"Additional context: {additional_context}")
            
        # Execute the code
        result = python_repl.run(code_description)
        
        # Format response
        return {
            "result": str(result),
            "status": "success",
            "code": code_description
        }
        
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        return {
            "result": str(e),
            "status": "error",
            "code": code_description
        }
