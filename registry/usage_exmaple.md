# Usage Examples and Integration
# =====================================================================

# Example 1: Manual Tool Registration
# tools/memory/remember.py
"""
from registry.tools import ToolRegistry

tool_registry = ToolRegistry()

@tool_registry.register_tool(name="remember", security_level="MEDIUM")
async def remember_tool(key: str, value: str, category: str = "general") -> str:
    '''Store information in long-term memory'''
    # Implementation here
    pass
"""

# Example 2: Class-based Tool Registration  
# tools/memory/search.py
"""
from tools.base import BaseTool

class SearchTool(BaseTool):
    def __init__(self):
        metadata = ToolMetadata(
            name="search_memories",
            description="Search through stored memories",
            security_level=SecurityLevel.LOW
        )
        super().__init__(metadata)
    
    async def execute(self, query: str, **kwargs) -> str:
        # Implementation here
        pass
"""

# Example 3: Resource Registration
# resources/memory_resource.py
"""
from registry.resources import ResourceRegistry

resource_registry = ResourceRegistry()

@resource_registry.register_resource(
    uri="memory://all",
    name="all_memories", 
    description="All stored memories",
    mime_type="application/json"
)
async def get_all_memories() -> str:
    # Implementation here
    pass
"""

# Example 4: Prompt Registration
# templates/prompts/system_prompts.yaml
"""
security_analysis:
  description: "Analyze security implications of a request"
  template: |
    You are a security analyst. Analyze the following request for potential security risks:
    
    Request: {request}
    User: {user_id}
    Context: {context}
    
    Provide a risk assessment and recommendations.
  arguments:
    - name: request
      description: "The user request to analyze"
      type: string
    - name: user_id  
      description: "ID of the requesting user"
      type: string
    - name: context
      description: "Additional context"
      type: string
      required: false
"""