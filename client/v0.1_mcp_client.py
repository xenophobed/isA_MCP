#!/usr/bin/env python
"""
Enhanced MCP Client v1.2 - FIXED
- Uses custom HTTP client that works with load balancer
- Server-side tool execution with proper load balancing support
- Enhanced security through server-side authorization
- Multiple connection options (direct/load-balanced)
"""
import asyncio
import json
import os
from typing import Dict, List, Any, Annotated, Optional, Union
from datetime import datetime
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from pydantic import SecretStr
from isa_model.inference.ai_factory import AIFactory 

# Import our custom working HTTP client
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mcp_http_client import MCPHTTPClient

# Load environment variables
load_dotenv(".env.local")

# OpenAI configuration
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

config = {
    "api_key": api_key,
    "api_base": api_base
}

llm = AIFactory.get_instance().get_llm("gpt-4o-mini", "openai", config=config)

# State definition for the agent
class AgentState(Dict):
    messages: Annotated[List[Any], "The list of messages in the conversation"]
    next_action: Annotated[str, "The next action to take"]
    mcp_session: Annotated[Any, "MCP session for tool calls"]
    available_tools: Annotated[List[Dict], "Available MCP tools"]
    available_resources: Annotated[List[Dict], "Available MCP resources"]
    available_prompts: Annotated[List[Dict], "Available MCP prompts"]
    user_query: Annotated[str, "Original user query"]

class EnhancedMCPClient:
    def __init__(self, use_load_balancer: bool = True):
        self.session: Optional[MCPHTTPClient] = None
        self.graph = None
        self.conversation_history = []
        self.use_load_balancer = use_load_balancer
        
        # Connection URLs in priority order
        if use_load_balancer:
            self.connection_urls = [
                "http://localhost/mcp",        # Load balancer first
                "http://localhost:8001/mcp",   # Fallback to direct
                "http://localhost:8002/mcp",   # Alternative direct
                "http://localhost:8003/mcp"    # Another alternative
            ]
        else:
            self.connection_urls = [
                "http://localhost:8001/mcp",   # Direct first
                "http://localhost:8002/mcp",   # Alternative direct
                "http://localhost:8003/mcp",   # Another alternative
                "http://localhost/mcp"         # Load balancer as fallback
            ]
    
    async def initialize_mcp_session(self):
        """Initialize MCP session with fallback connections"""
        print("🔌 Connecting to enhanced MCP server...")
        
        # Try each connection URL until one works
        for i, url in enumerate(self.connection_urls):
            try:
                connection_type = "load-balanced" if "localhost/mcp" in url else f"direct (port {url.split(':')[-1].split('/')[0]})"
                print(f"🔄 Attempting {connection_type} connection: {url}")
                
                # Create and test connection
                self.session = MCPHTTPClient(url)
                await self.session.__aenter__()
                
                # Test with initialization
                await asyncio.wait_for(self.session.initialize(), timeout=10.0)
                print(f"✅ MCP session initialized via {connection_type}")
                
                return self.session
                
            except asyncio.TimeoutError:
                print(f"⏰ Connection timeout for {url}")
                await self._cleanup_failed_connection()
                continue
            except Exception as e:
                print(f"❌ Connection failed for {url}: {e}")
                await self._cleanup_failed_connection()
                continue
        
        raise Exception("❌ All connection attempts failed. Please check if MCP servers are running.")
    
    async def _cleanup_failed_connection(self):
        """Clean up failed connection attempts"""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
        except:
            pass
        finally:
            self.session = None
    
    async def discover_mcp_capabilities(self) -> Dict[str, List]:
        """Dynamically discover all MCP capabilities"""
        print("🔍 Discovering MCP capabilities...")
        
        capabilities = {
            "tools": [],
            "resources": [],
            "prompts": []
        }
        
        if not self.session:
            print("❌ No MCP session available")
            return capabilities
        
        try:
            # Discover tools
            tools = await self.session.list_tools()
            for tool in tools:
                capabilities["tools"].append({
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"]
                })
            
            # Discover resources
            resources = await self.session.list_resources()
            for resource in resources:
                capabilities["resources"].append({
                    "uri": resource["uri"],
                    "name": resource["name"],
                    "description": resource["description"],
                    "mimeType": resource["mimeType"]
                })
            
            # Discover prompts
            prompts = await self.session.list_prompts()
            for prompt in prompts:
                capabilities["prompts"].append({
                    "name": prompt["name"],
                    "description": prompt["description"],
                    "arguments": prompt.get("arguments", [])
                })
            
            print(f"📊 Discovered: {len(capabilities['tools'])} tools, {len(capabilities['resources'])} resources, {len(capabilities['prompts'])} prompts")
            return capabilities
            
        except Exception as e:
            print(f"❌ Error discovering capabilities: {e}")
            return capabilities
    
    def create_tools_for_llm(self, state: AgentState) -> List[Dict]:
        """Create tool definitions for LLM based on available MCP tools"""
        tools = []
        
        # Add all MCP tools directly
        for tool_info in state["available_tools"]:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_info["name"],
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"]
                }
            })
        
        # Add dynamic prompt access
        for prompt_info in state["available_prompts"]:
            tools.append({
                "type": "function",
                "function": {
                    "name": f"get_prompt_{prompt_info['name']}",
                    "description": f"Get prompt: {prompt_info['description']}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "arguments": {
                                "type": "object",
                                "description": "Arguments for the prompt",
                                "additionalProperties": True
                            }
                        }
                    }
                }
            })
        
        # Add dynamic resource access
        for resource_info in state["available_resources"]:
            uri_str = resource_info["uri"]
            if "://" in uri_str:
                resource_name = uri_str.split("://")[-1]
            else:
                resource_name = uri_str
            
            safe_name = resource_name.replace('/', '_').replace('-', '_')
            
            tools.append({
                "type": "function",
                "function": {
                    "name": f"get_resource_{safe_name}",
                    "description": f"Access resource: {resource_info['description']}",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            })
        
        return tools
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict) -> str:
        """Call an MCP tool and return the result"""
        if not self.session:
            return json.dumps({"error": "No MCP session available"})
            
        try:
            print(f"🔧 Calling MCP tool: {tool_name}({arguments})")
            result = await self.session.call_tool(tool_name, arguments)
            
            print(f"✅ Tool result: {str(result)[:100]}...")
            return str(result)
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error: {error_msg}")
            
            # Check if this is an authorization error
            if "Authorization required" in error_msg and "Request ID:" in error_msg:
                return await self.handle_authorization_error(error_msg, tool_name, arguments)
            
            return json.dumps({"error": f"Tool call failed: {error_msg}"})
    
    async def get_mcp_resource(self, resource_uri: str) -> str:
        """Get an MCP resource"""
        if not self.session:
            return json.dumps({"error": "No MCP session available"})
            
        try:
            print(f"📁 Fetching MCP resource: {resource_uri}")
            result = await self.session.read_resource(resource_uri)
            
            print(f"✅ Resource fetched: {len(str(result))} characters")
            return str(result)
            
        except Exception as e:
            error_msg = f"Resource fetch failed: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
    
    async def get_mcp_prompt(self, prompt_name: str, arguments: Optional[Dict] = None) -> str:
        """Get an MCP prompt"""
        if not self.session:
            return json.dumps({"error": "No MCP session available"})
            
        try:
            print(f"📝 Fetching MCP prompt: {prompt_name}")
            if arguments is None:
                arguments = {}
            
            result = await self.session.get_prompt(prompt_name, arguments)
            
            print(f"✅ Prompt fetched: {len(str(result))} characters")
            return str(result)
            
        except Exception as e:
            error_msg = f"Prompt fetch failed: {str(e)}"
            print(f"❌ {error_msg}")
            return json.dumps({"error": error_msg})
    
    async def handle_authorization_error(self, error_msg: str, tool_name: str, arguments: Dict) -> str:
        """Handle authorization error by extracting details and prompting user"""
        try:
            # Create authorization request through the server with the ORIGINAL tool arguments
            auth_response = await self.call_mcp_tool("request_authorization", {
                "tool_name": tool_name,
                "reason": f"User requested to execute {tool_name}",
                "tool_args": arguments  # Pass the original tool arguments
            })
            
            # Handle the authorization response, but override tool_args with original arguments
            return await self.handle_authorization_response(auth_response, arguments)
            
        except Exception as e:
            print(f"❌ Error handling authorization: {e}")
            return f"Authorization error: {error_msg}"

    async def handle_ask_human_response(self, server_response: str) -> str:
        """Handle ask_human tool response by prompting the user"""
        try:
            response_data = json.loads(server_response)
            if response_data.get("status") == "human_input_requested":
                data = response_data.get("data", {})
                question = data.get("question", "Please provide input:")
                context = data.get("context", "")
                
                print(f"\n🤔 {question}")
                if context:
                    print(f"Context: {context}")
                
                user_input = input("👤 Your response: ").strip()
                return f"Human response: {user_input}"
            else:
                return server_response
        except Exception as e:
            print(f"❌ Error handling human input: {e}")
            return server_response
    
    async def handle_authorization_response(self, server_response: str, tool_args: dict) -> str:
        """Handle authorization request by prompting the user"""
        try:
            response_data = json.loads(server_response)
            if response_data.get("status") == "authorization_requested":
                data = response_data.get("data", {})
                tool_name = data.get("tool_name", "unknown")
                reason = data.get("reason", "No reason provided")
                security_level = data.get("security_level", "MEDIUM")
                
                print(f"\n🔐 SECURITY AUTHORIZATION REQUEST")
                print("=" * 50)
                print(f"🎯 Tool: {tool_name}")
                print(f"📋 Arguments: {json.dumps(tool_args, indent=2)}")
                print(f"❓ Reason: {reason}")
                print(f"🔒 Security Level: {security_level}")
                
                # Check if this is a high-security operation
                high_security_tools = ["forget", "delete", "modify", "admin"]
                is_high_security = any(sec_tool in tool_name.lower() for sec_tool in high_security_tools)
                
                if is_high_security:
                    print("\n⚠️  HIGH SECURITY OPERATION DETECTED ⚠️")
                    print("This operation may have significant impact.")
                    print("Please review carefully before proceeding.")
                
                print("\n🔍 Security Impact Assessment:")
                if "remember" in tool_name.lower():
                    print("  - Will store information in persistent memory")
                    print("  - Data will be retrievable in future sessions")
                elif "forget" in tool_name.lower():
                    print("  - Will permanently delete information")
                    print("  - This action cannot be undone")
                elif "search" in tool_name.lower():
                    print("  - Will access stored information")
                    print("  - Low security impact")
                
                print("=" * 50)
                
                while True:
                    response = input("👤 Authorize this action? (y/n): ").strip().lower()
                    if response in ['y', 'yes']:
                        print("✅ Authorization GRANTED")
                        # Approve the authorization on the server side
                        request_id = data.get("request_id")
                        if request_id:
                            print(f"🔧 Approving authorization request: {request_id}")
                            approval_result = await self.call_mcp_tool("approve_authorization", {
                                "request_id": request_id,
                                "approved_by": "human_user"
                            })
                            print(f"✅ Approval result: {approval_result[:100]}...")
                            
                            # Now execute the actual tool - fix tool name if it has "functions." prefix
                            actual_tool_name = data.get("tool_name")
                            # Use the original tool_args passed to this method, not from server response
                            actual_tool_args = tool_args if tool_args else data.get("tool_args", {})
                            if actual_tool_name:
                                # Remove "functions." prefix if present
                                if actual_tool_name.startswith("functions."):
                                    actual_tool_name = actual_tool_name.replace("functions.", "")
                                
                                # Debug: Print the arguments being passed
                                print(f"🔧 Executing authorized tool: {actual_tool_name} with args: {actual_tool_args}")
                                result = await self.call_mcp_tool(actual_tool_name, actual_tool_args)
                                return f"Authorization granted and executed: {result}"
                            else:
                                return "Authorization granted, but no tool specified to execute."
                        else:
                            return "Authorization granted, but no request ID found."
                    elif response in ['n', 'no']:
                        print("❌ Authorization DENIED")
                        return "Authorization denied. The tool call has been cancelled."
                    else:
                        print("Please enter 'y' for yes or 'n' for no")
            else:
                return server_response
        except Exception as e:
            print(f"❌ Error handling authorization: {e}")
            return server_response
    
    def build_agent_graph(self):
        """Build the LangGraph agent"""
        print("🏗️ Building enhanced LangGraph agent...")
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("call_model", self.call_model)
        workflow.add_node("should_continue", self.should_continue)
        workflow.add_node("execute_tools", self.execute_tools)
        
        # Add edges
        workflow.set_entry_point("call_model")
        workflow.add_edge("call_model", "should_continue")
        workflow.add_conditional_edges(
            "should_continue",
            lambda state: state["next_action"],
            {
                "execute_tools": "execute_tools",
                "end": END
            }
        )
        workflow.add_edge("execute_tools", "call_model")
        
        # Compile the graph
        self.graph = workflow.compile()
        print("✅ Enhanced LangGraph agent built successfully")
    
    async def call_model(self, state: AgentState) -> AgentState:
        """Call the language model with enhanced MCP integration"""
        print("🧠 Calling language model...")
        
        messages = state["messages"]
        
        # Create tools for LLM
        available_tools = self.create_tools_for_llm(state)
        
        # Enhanced system prompt
        system_prompt = f"""You are an intelligent assistant with access to a comprehensive MCP server via LOAD BALANCER.

Available MCP Tools ({len(state['available_tools'])}):
{', '.join([tool['name'] for tool in state['available_tools']])}

Available Prompts ({len(state['available_prompts'])}):
{', '.join([prompt['name'] for prompt in state['available_prompts']])}

Available Resources ({len(state['available_resources'])}):
{', '.join([resource['name'] for resource in state['available_resources']])}

Current query: {state['user_query']}

🎯 CONNECTION STATUS: Using load-balanced MCP servers for high availability and performance.

ENHANCED CAPABILITIES:
1. **Memory Management**: Use remember, forget, update_memory, search_memories for persistent data
2. **Weather Information**: Use get_weather for current weather data
3. **Human Interaction**: 
   - Use ask_human ONLY to get additional information or clarification from the user
   - Use request_authorization ONLY when a tool requires explicit authorization before execution
4. **Security & Monitoring**: Use check_security_status, admin tools for system oversight
5. **Response Formatting**: Use format_response for structured outputs
6. **Dynamic Prompts**: Access specialized prompts via get_prompt_[name]
7. **Resource Access**: Get additional context via get_resource_[name]

IMPORTANT DISTINCTION:
- ask_human: For getting MORE INFORMATION from the user (questions, clarifications, etc.)
- request_authorization: For getting PERMISSION to execute sensitive operations (forget, admin tools, etc.)

WORKFLOW:
1. Analyze the user's request and determine required capabilities
2. If you need more information from the user, use ask_human
3. For memory operations:
   - remember: Call directly (auto-approved)
   - update_memory: Call directly (auto-approved) 
   - search_memories: Call directly (no authorization needed)
   - forget: Call directly with proper arguments (authorization will be handled automatically)
4. Use appropriate MCP tools to gather information or perform actions
5. Format responses appropriately for clarity and structure
6. Leverage prompts and resources for enhanced context when needed

CRITICAL: ALWAYS call tools directly with their required arguments. 
- For forget tool: ALWAYS include the 'key' parameter with the specific key to delete
- For remember tool: ALWAYS include 'key' and 'value' parameters
- Never call request_authorization manually - the system handles authorization automatically

The authorization system will handle security automatically when needed.
Focus on providing helpful, accurate responses using the available tools."""

        # Build the full message list
        full_messages = [SystemMessage(content=system_prompt)] + messages
        
        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(available_tools)
        
        # Get response
        response = await llm_with_tools.ainvoke(full_messages)
        
        # Add AI response to messages
        state["messages"].append(response)
        
        print(f"🤖 Model response: {response.content[:100] if response.content else 'Tool calls requested'}...")
        
        return state
    
    async def should_continue(self, state: AgentState) -> AgentState:
        """Decide whether to continue with tool calls or end"""
        last_message = state["messages"][-1]
        
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print(f"🔄 Tool calls detected: {len(last_message.tool_calls)} tools to execute")
            state["next_action"] = "execute_tools"
        else:
            print("🏁 No tool calls, ending conversation")
            state["next_action"] = "end"
        
        return state
    
    async def execute_tools(self, state: AgentState) -> AgentState:
        """Execute all MCP tool calls with human interaction support"""
        print("🛠️ Executing MCP tools...")
        
        last_message = state["messages"][-1]
        
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_call_id = tool_call['id']
                
                print(f"📋 Processing: {tool_name} with args {tool_args}")
                
                # Execute the appropriate operation
                if tool_name in [tool['name'] for tool in state['available_tools']]:
                    # Standard MCP tool call
                    result = await self.call_mcp_tool(tool_name, tool_args)
                    
                    # Handle human interaction responses
                    if tool_name == "ask_human":
                        result = await self.handle_ask_human_response(result)
                    elif tool_name == "request_authorization":
                        result = await self.handle_authorization_response(result, tool_args)
                    
                elif tool_name.startswith("get_prompt_"):
                    # Prompt access
                    prompt_name = tool_name.replace("get_prompt_", "")
                    prompt_args = tool_args.get("arguments", {})
                    result = await self.get_mcp_prompt(prompt_name, prompt_args)
                elif tool_name.startswith("get_resource_"):
                    # Resource access
                    resource_name_safe = tool_name.replace("get_resource_", "")
                    
                    # Find the original resource URI
                    original_uri = None
                    for resource_info in state['available_resources']:
                        uri_str = resource_info["uri"]
                        if "://" in uri_str:
                            uri_resource_name = uri_str.split("://")[-1]
                        else:
                            uri_resource_name = uri_str
                        
                        safe_name = uri_resource_name.replace('/', '_').replace('-', '_')
                        if safe_name == resource_name_safe:
                            original_uri = uri_str
                            break
                    
                    if original_uri:
                        result = await self.get_mcp_resource(original_uri)
                    else:
                        result = f"Resource not found: {resource_name_safe}"
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
        
        # Add new user message to conversation history
        self.conversation_history.append(HumanMessage(content=user_input))
        
        # Create initial state with full conversation history for context
        initial_state = {
            "messages": self.conversation_history.copy(),
            "next_action": "",
            "mcp_session": self.session,
            "available_tools": capabilities["tools"],
            "available_resources": capabilities["resources"],
            "available_prompts": capabilities["prompts"],
            "user_query": user_input
        }
        
        if self.graph:
            print(f"🚀 Running enhanced LangGraph agent with load balancer support...")
            final_state = await self.graph.ainvoke(initial_state)
            
            # Update conversation history with the agent's response
            if final_state["messages"]:
                # Add all new messages from the conversation to history
                new_messages = final_state["messages"][len(self.conversation_history):]
                self.conversation_history.extend(new_messages)
        else:
            print("❌ Agent graph not available")
            return "Error: Agent not properly initialized"
        
        # Extract final response
        final_message = final_state["messages"][-1]
        
        if isinstance(final_message, AIMessage):
            if final_message.content:
                print(f"\n🤖 Assistant: {final_message.content}")
                return final_message.content
            else:
                print("\n🤖 Assistant: (Tool operations completed)")
                return "Tool operations completed successfully"
        else:
            print(f"\n🤖 Assistant: {str(final_message)}")
            return str(final_message)
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

async def main():
    """Main function to run the enhanced client"""
    print("🎯 Enhanced MCP Client v1.2 - FIXED")
    print("=" * 50)
    print("🔌 Connection Options:")
    print("  1. Load-balanced connection (http://localhost/mcp) - RECOMMENDED")
    print("  2. Direct connection (http://localhost:8001/mcp)")
    
    while True:
        choice = input("\n🤔 Choose connection type (1/2): ").strip()
        if choice == "1":
            use_load_balancer = True
            print("📡 Using load-balanced connection - HIGH AVAILABILITY MODE")
            break
        elif choice == "2":
            use_load_balancer = False
            print("🎯 Using direct connection")
            break
        else:
            print("❌ Please enter 1 or 2")
    
    client = EnhancedMCPClient(use_load_balancer=use_load_balancer)
    
    try:
        print("\n✨ Features:")
        print("  - ✅ WORKING Load Balancer Support")
        print("  - Server-side tool execution")
        print("  - Automatic security & authorization")
        print("  - Dynamic capability discovery")
        print("  - Enhanced MCP integration")
        print("  - High availability failover")
        
        # Interactive mode
        print("\n🎮 Interactive mode:")
        print("  quit - Exit the client")
        
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if user_input:
                    await client.run_conversation(user_input)
                    print("-" * 50)
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
    
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 