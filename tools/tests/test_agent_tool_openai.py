from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from langgraph.prebuilt import ToolNode

@tool
def get_weather(location: str):
    """Call to get the current weather."""
    if location.lower() in ["sf", "san francisco"]:
        return "It's 60 degrees and foggy."
    else:
        return "It's 90 degrees and sunny."


@tool
def get_coolest_cities():
    """Get a list of coolest cities"""
    return "nyc, sf"


tools = [get_weather, get_coolest_cities]
tool_node = ToolNode(tools)


from app.services.ai.models.ai_factory import AIFactory

from langchain_openai import ChatOpenAI

llm = AIFactory.get_instance().get_llm(model_name="gpt-4o-mini", provider="yyds")
#llm = ChatOpenAI(model_name="gpt-4o-mini")

llm_with_tools = llm.bind_tools(tools)

import asyncio



if __name__ == "__main__":
    result = llm_with_tools.invoke("what's the weather in sf?").tool_calls
    result2 = tool_node.invoke({"messages": [ llm_with_tools.invoke("what's the weather in sf?")]})

    print(result)
    print(result2)