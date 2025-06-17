#!/usr/bin/env python
"""
LangGraph React Agent MCP Client
Dynamic agent that fetches all capabilities from MCP server
"""
import asyncio
import json
import os
from typing import Dict, List, Any, Annotated, Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Resource, Tool, Prompt

# Load environment variables
load_dotenv(".env.local")

# OpenAI configuration
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=api_key,
    base_url=api_base
)

# State definition for the agent
class AgentState(Dict):
    messages: Annotated[List[Any], "The list of messages in the conversation"]
    next_action: Annotated[str, "The next action to take"]
    mcp_session: Annotated[Any, "MCP session for tool calls"]
    available_tools: Annotated[List[Dict], "Available MCP tools"]
    available_resources: Annotated[List[Dict], "Available MCP resources"]
    available_prompts: Annotated[List[Dict], "Available MCP prompts"]
    user_query: Annotated[str, "Original user query"]

class DynamicMCPAgent:
    def __init__(self):
        self.session = None
        self.graph = None
        self.client_context = None
        self.session_context = None
    
    async def initialize_mcp_session(self):
        """Initialize MCP session and discover capabilities"""
        print("🔌 Connecting to MCP server...")
        
        # Create streamable HTTP client
        self.client_context = streamablehttp_client("http://localhost:8000/mcp")
        self.read, self.write, _ = await self.client_context.__aenter__()
        
        # Create session
        self.session_context = ClientSession(self.read, self.write)
        self.session = await self.session_context.__aenter__()
        
        # Initialize session
        await self.session.initialize()
        print("✅ MCP session initialized")
        
        return self.session
    
    async def discover_mcp_capabilities(self) -> Dict[str, List]:
        """Dynamically discover all MCP capabilities"""
        print("🔍 Discovering MCP capabilities...")
        
        capabilities = {
            "tools": [],
            "resources": [],
            "prompts": []
        }
        
        try:
            # Discover tools
            tools_response = await self.session.list_tools()
            for tool in tools_response.tools:
                capabilities["tools"].append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                })
            
            # Discover resources
            resources_response = await self.session.list_resources()
            for resource in resources_response.resources:
                capabilities["resources"].append({
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description,
                    "mimeType": resource.mimeType
                })
            
            # Discover prompts
            prompts_response = await self.session.list_prompts()
            for prompt in prompts_response.prompts:
                capabilities["prompts"].append({
                    "name": prompt.name,
                    "description": prompt.description,
                    "arguments": prompt.arguments if hasattr(prompt, 'arguments') else []
                })
            
            print(f"📊 Discovered: {len(capabilities['tools'])} tools, {len(capabilities['resources'])} resources, {len(capabilities['prompts'])} prompts")
            return capabilities
            
        except Exception as e:
            print(f"❌ Error discovering capabilities: {e}")
            return capabilities
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict) -> str:
        """Call an MCP tool"""
        try:
            print(f"🔧 Calling MCP tool: {tool_name}({arguments})")
            result = await self.session.call_tool(tool_name, arguments)
            
            if hasattr(result, 'content') and result.content:
                content = result.content[0].text
                print(f"✅ Tool result: {content[:100]}...")
                return content
            return json.dumps({"result": str(result)})
            
        except Exception as e:
            error_msg = f"Tool call failed: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
    
    async def get_mcp_resource(self, resource_uri: str) -> str:
        """Get an MCP resource"""
        try:
            print(f"📁 Fetching MCP resource: {resource_uri}")
            result = await self.session.read_resource(resource_uri)
            
            if hasattr(result, 'contents') and result.contents:
                content = result.contents[0].text
                print(f"✅ Resource fetched: {len(content)} characters")
                return content
            return json.dumps({"result": str(result)})
            
        except Exception as e:
            error_msg = f"Resource fetch failed: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
    
    async def get_mcp_prompt(self, prompt_name: str, arguments: Dict = None) -> str:
        """Get an MCP prompt"""
        try:
            print(f"📝 Fetching MCP prompt: {prompt_name}")
            if arguments is None:
                arguments = {}
            
            result = await self.session.get_prompt(prompt_name, arguments)
            
            if hasattr(result, 'messages') and result.messages:
                # Extract prompt content from messages
                prompt_content = ""
                for message in result.messages:
                    if hasattr(message, 'content'):
                        if hasattr(message.content, 'text'):
                            prompt_content += message.content.text + "\n"
                        else:
                            prompt_content += str(message.content) + "\n"
                print(f"✅ Prompt fetched: {len(prompt_content)} characters")
                return prompt_content
            
            return json.dumps({"result": str(result)})
            
        except Exception as e:
            error_msg = f"Prompt fetch failed: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
    
    def build_agent_graph(self):
        """Build the LangGraph agent"""
        print("🏗️ Building LangGraph agent...")
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("call_model", self.call_model)
        workflow.add_node("should_continue", self.should_continue)
        workflow.add_node("call_mcp", self.call_mcp)
        
        # Add edges
        workflow.set_entry_point("call_model")
        workflow.add_edge("call_model", "should_continue")
        workflow.add_conditional_edges(
            "should_continue",
            lambda state: state["next_action"],
            {
                "call_mcp": "call_mcp",
                "end": END
            }
        )
        workflow.add_edge("call_mcp", "call_model")
        
        # Compile the graph
        self.graph = workflow.compile()
        print("✅ LangGraph agent built successfully")
    
    async def call_model(self, state: AgentState) -> AgentState:
        """Call the language model"""
        print("🧠 Calling language model...")
        
        messages = state["messages"]
        user_query = state["user_query"]
        
        # Get appropriate prompt from MCP
        if "weather" in user_query.lower():
            # Extract city if mentioned
            city = self.extract_city_from_query(user_query)
            prompt_args = {"user_query": user_query}
            if city:
                prompt_args["city"] = city
            
            system_prompt = await self.get_mcp_prompt("weather_assistant_prompt", prompt_args)
        else:
            system_prompt = await self.get_mcp_prompt("general_assistant_prompt", {"user_query": user_query})
        
        # Build the full message list
        full_messages = [SystemMessage(content=system_prompt)] + messages
        
        # Create tools from MCP capabilities
        available_tools = []
        for tool_info in state["available_tools"]:
            available_tools.append({
                "type": "function",
                "function": {
                    "name": tool_info["name"],
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"]
                }
            })
        
        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(available_tools)
        
        # Get response
        response = await llm_with_tools.ainvoke(full_messages)
        
        # Add AI response to messages
        state["messages"].append(response)
        
        print(f"🤖 Model response: {response.content[:100] if response.content else 'Tool calls requested'}...")
        
        return state
    
    def extract_city_from_query(self, query: str) -> str:
        """Simple city extraction from query"""
        cities = ["beijing", "shanghai", "guangzhou", "new york", "london", "tokyo", "paris"]
        query_lower = query.lower()
        
        for city in cities:
            if city in query_lower:
                return city.title()
        return ""
    
    async def should_continue(self, state: AgentState) -> AgentState:
        """Decide whether to continue with tool calls or end"""
        last_message = state["messages"][-1]
        
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print(f"🔄 Tool calls detected: {len(last_message.tool_calls)} tools to call")
            state["next_action"] = "call_mcp"
        else:
            print("🏁 No tool calls, ending conversation")
            state["next_action"] = "end"
        
        return state
    
    async def call_mcp(self, state: AgentState) -> AgentState:
        """Execute MCP tool calls"""
        print("🛠️ Executing MCP operations...")
        
        last_message = state["messages"][-1]
        
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_call_id = tool_call['id']
                
                print(f"📋 Processing: {tool_name} with args {tool_args}")
                
                # Execute the appropriate MCP operation
                if tool_name in [tool['name'] for tool in state['available_tools']]:
                    # Standard MCP tool call
                    result = await self.call_mcp_tool(tool_name, tool_args)
                elif tool_name.startswith("get_resource_"):
                    # Resource access
                    resource_name = tool_name.replace("get_resource_", "")
                    result = await self.get_mcp_resource(f"memory://{resource_name}")
                elif tool_name.startswith("get_prompt_"):
                    # Prompt access
                    prompt_name = tool_name.replace("get_prompt_", "")
                    result = await self.get_mcp_prompt(prompt_name, tool_args)
                else:
                    result = f"Unknown tool: {tool_name}"
                
                # Add tool result to messages
                state["messages"].append(ToolMessage(
                    content=result,
                    tool_call_id=tool_call_id
                ))
        
        return state
    
    async def run_conversation(self, user_input: str):
        """Run a complete conversation"""
        print(f"\n💬 User: {user_input}")
        
        # Initialize MCP session if not already done
        if not self.session:
            await self.initialize_mcp_session()
        
        # Discover capabilities
        capabilities = await self.discover_mcp_capabilities()
        
        # Build agent if not already built
        if not self.graph:
            self.build_agent_graph()
        
        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "next_action": "",
            "mcp_session": self.session,
            "available_tools": capabilities["tools"],
            "available_resources": capabilities["resources"],
            "available_prompts": capabilities["prompts"],
            "user_query": user_input
        }
        
        # Run the agent
        print("🚀 Running LangGraph agent...")
        final_state = await self.graph.ainvoke(initial_state)
        
        # Extract final response
        final_message = final_state["messages"][-1]
        
        if isinstance(final_message, AIMessage):
            if final_message.content:
                print(f"\n🤖 Assistant: {final_message.content}")
                return final_message.content
            else:
                print("\n🤖 Assistant: (Tool calls executed)")
                return "Tool calls executed successfully"
        else:
            print(f"\n🤖 Assistant: {str(final_message)}")
            return str(final_message)
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.session_context:
                await self.session_context.__aexit__(None, None, None)
            if self.client_context:
                await self.client_context.__aexit__(None, None, None)
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

async def main():
    """Main function to run the agent"""
    agent = DynamicMCPAgent()
    
    try:
        print("🎯 LangGraph React Agent MCP Client")
        print("=" * 50)
        
        # Example conversations
        test_queries = [
            "What's the weather like in Beijing?",
            "Can you help me with a general question?",
            "Show me available resources",
            "What tools do you have access to?"
        ]
        
        for query in test_queries:
            try:
                await agent.run_conversation(query)
                print("-" * 50)
                await asyncio.sleep(1)  # Brief pause between queries
            except Exception as e:
                print(f"❌ Error processing query '{query}': {e}")
                continue
        
        # Interactive mode
        print("\n🎮 Interactive mode - Type 'quit' to exit")
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                if user_input:
                    await agent.run_conversation(user_input)
                    print("-" * 50)
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
    
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())