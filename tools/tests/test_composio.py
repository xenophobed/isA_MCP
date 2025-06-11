import asyncio
from typing import Literal
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from composio_langgraph import ComposioToolSet, Action
from app.services.ai.models.ai_factory import AIFactory

import os 

os.environ["COMPOSIO_API_KEY"] = "p6btli2ifpa2l2wfdpo5uo"

# Initialize the Composio toolset
composio_toolset = ComposioToolSet()

# Define the tools (specific GitHub actions)
tools = composio_toolset.get_tools(actions=[
    Action.GITHUB_STAR_A_REPOSITORY_FOR_THE_AUTHENTICATED_USER
])

# Create a ToolNode with the Composio tools
tool_node = ToolNode(tools)

# Initialize the language model
model = AIFactory.get_instance().get_llm(
            model_name="gpt-4o-mini",
            provider="yyds" 
        ).get_runnable()
model_with_tools = model.bind_tools(tools)

# Define the model calling function
def call_model(state: MessagesState):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

# Define the conditional edge logic
def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"

# Set up the workflow graph
workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge("__start__", "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

# Compile the graph
app = workflow.compile()

# Async function to run the agent
async def run_agent():
    # Input message to star a repository
    input_message = {"messages": [("human", "Star the GitHub repository composiohq/composio")]}

    # Stream the response
    async for chunk in app.astream(input_message, stream_mode="values"):
        chunk["messages"][-1].pretty_print()

# Run the example
if __name__ == "__main__":
    asyncio.run(run_agent())