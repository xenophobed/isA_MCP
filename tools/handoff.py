from typing import Annotated, Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command

def create_custom_handoff_tool(agent_name: str, description: str = None):
    """Create a tool that transfers control to another agent in the swarm.
    
    Args:
        agent_name: The name of the agent to transfer control to
        description: The description of the tool
    
    Returns:
        A tool function that can be added to an agent's tools list
    """
    name = f"transfer_to_{agent_name}"
    
    if description is None:
        description = f"Ask agent '{agent_name}' for help"
    
    # Create tool without description parameter
    @tool(name)
    def handoff_to_agent(
        state: Dict[str, Any],
        tool_call_id: str,
    ):
        """Transfer control to another agent in the swarm."""
        tool_message = ToolMessage(
            content=f"Successfully transferred to {agent_name}",
            name=name,
            tool_call_id=tool_call_id,
        )
        return Command(
            goto=agent_name,
            graph=Command.PARENT,
            update={"messages": state["messages"] + [tool_message], "active_agent": agent_name},
        )
    
    # Set description manually
    handoff_to_agent.description = description
    
    return handoff_to_agent 