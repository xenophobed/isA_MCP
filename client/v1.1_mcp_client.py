#!/usr/bin/env python
"""
Optimized LangGraph React Agent MCP Client
- Removed hardcoded logic
- Dynamic prompt selection via MCP
- Human-in-the-loop support
- Fixed AnyUrl handling
"""
import asyncio
import json
import os
from typing import Dict, List, Any, Annotated, Literal, Optional
from datetime import datetime
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
    human_input_needed: Annotated[bool, "Whether human input is needed"]
    pending_authorization: Annotated[Optional[Dict], "Pending tool authorization"]

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
                # Convert AnyUrl to string properly
                uri_str = str(resource.uri)
                capabilities["resources"].append({
                    "uri": uri_str,
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
    
    def create_dynamic_tools_for_llm(self, state: AgentState) -> List[Dict]:
        """Create dynamic tools for LLM including prompts and resources"""
        tools = []
        
        # Add MCP tools
        for tool_info in state["available_tools"]:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_info["name"],
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"]
                }
            })
        
        # Add prompt access tools
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
        
        # Add resource access tools
        for resource_info in state["available_resources"]:
            # Safely handle URI conversion to string
            uri_str = resource_info["uri"]
            if "://" in uri_str:
                resource_name = uri_str.split("://")[-1]
            else:
                resource_name = uri_str
            
            # Create safe function name
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
        
        # Add human interaction tools
        tools.append({
            "type": "function",
            "function": {
                "name": "ask_human",
                "description": "Ask the human for additional information or clarification",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to ask the human"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context for the question"
                        }
                    },
                    "required": ["question"]
                }
            }
        })
        
        # Add authorization request tool
        tools.append({
            "type": "function",
            "function": {
                "name": "request_authorization",
                "description": "Request human authorization before executing a tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the tool requiring authorization"
                        },
                        "tool_args": {
                            "type": "object",
                            "description": "Arguments for the tool"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason why authorization is needed"
                        }
                    },
                    "required": ["tool_name", "tool_args", "reason"]
                }
            }
        })
        
        # Add monitoring and security tools
        tools.append({
            "type": "function",
            "function": {
                "name": "check_security_status",
                "description": "Check the security and monitoring status of the system",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_metrics": {
                            "type": "boolean",
                            "description": "Whether to include detailed metrics"
                        }
                    }
                }
            }
        })
        
        # Add formatted output tool
        tools.append({
            "type": "function",
            "function": {
                "name": "format_response",
                "description": "Format responses with enhanced structure and guardrails",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Content to format"
                        },
                        "format_type": {
                            "type": "string",
                            "enum": ["json", "markdown", "structured", "security_summary"],
                            "description": "Type of formatting to apply"
                        }
                    },
                    "required": ["content"]
                }
            }
        })
        
        return tools
    
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
    
    async def ask_human(self, question: str, context: str = "") -> str:
        """Ask human for input"""
        print(f"\n🤔 {question}")
        if context:
            print(f"Context: {context}")
        
        response = input("👤 Your response: ").strip()
        return response
    
    async def request_authorization(self, tool_name: str, tool_args: Dict, reason: str) -> bool:
        """Request authorization from human with enhanced security display"""
        print(f"\n🔐 SECURITY AUTHORIZATION REQUEST")
        print("=" * 50)
        print(f"🎯 Tool: {tool_name}")
        print(f"📋 Arguments: {json.dumps(tool_args, indent=2)}")
        print(f"❓ Reason: {reason}")
        
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
                return True
            elif response in ['n', 'no']:
                print("❌ Authorization DENIED")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no")
    
    async def check_security_status(self, include_metrics: bool = False) -> str:
        """Check security and monitoring status through MCP tools"""
        try:
            # Try to get monitoring metrics if available
            result = await self.call_mcp_tool("get_monitoring_metrics", {"user_id": "admin"})
            
            if include_metrics:
                # Also get audit log
                audit_result = await self.call_mcp_tool("get_audit_log", {"limit": 10, "user_id": "admin"})
                return f"Security Status:\n{result}\n\nRecent Audit Log:\n{audit_result}"
            
            return f"Security Status: {result}"
            
        except Exception as e:
            return f"Security status check failed: {str(e)}"
    
    async def format_response(self, content: str, format_type: str = "structured") -> str:
        """Format responses with enhanced structure and guardrails"""
        if format_type == "json":
            try:
                # Try to parse and reformat as JSON
                if content.startswith('{') or content.startswith('['):
                    parsed = json.loads(content)
                    return json.dumps(parsed, indent=2)
                else:
                    return json.dumps({"content": content, "formatted_at": datetime.now().isoformat()})
            except:
                return json.dumps({"raw_content": content, "format_error": "Could not parse as JSON"})
        
        elif format_type == "security_summary":
            lines = content.split('\n')
            summary = "🔒 SECURITY SUMMARY\n" + "=" * 30 + "\n"
            for line in lines[:10]:  # Limit to first 10 lines
                if line.strip():
                    summary += f"• {line.strip()}\n"
            if len(lines) > 10:
                summary += f"... and {len(lines) - 10} more items\n"
            return summary
        
        elif format_type == "markdown":
            # Basic markdown formatting
            formatted = f"## Response\n\n{content}\n\n---\n*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            return formatted
        
        else:  # structured
            return f"📋 STRUCTURED RESPONSE\n{'=' * 25}\n{content}\n{'=' * 25}\nTimestamp: {datetime.now().isoformat()}"
    
    def build_agent_graph(self):
        """Build the LangGraph agent"""
        print("🏗️ Building LangGraph agent...")
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("call_model", self.call_model)
        workflow.add_node("should_continue", self.should_continue)
        workflow.add_node("call_mcp", self.call_mcp)
        workflow.add_node("handle_human_interaction", self.handle_human_interaction)
        
        # Add edges
        workflow.set_entry_point("call_model")
        workflow.add_edge("call_model", "should_continue")
        workflow.add_conditional_edges(
            "should_continue",
            lambda state: state["next_action"],
            {
                "call_mcp": "call_mcp",
                "human_interaction": "handle_human_interaction",
                "end": END
            }
        )
        workflow.add_edge("call_mcp", "call_model")
        workflow.add_edge("handle_human_interaction", "call_model")
        
        # Compile the graph
        self.graph = workflow.compile()
        print("✅ LangGraph agent built successfully")
    
    async def call_model(self, state: AgentState) -> AgentState:
        """Call the language model with dynamic prompt selection"""
        print("🧠 Calling language model...")
        
        messages = state["messages"]
        
        # Create dynamic tools including prompts and resources
        available_tools = self.create_dynamic_tools_for_llm(state)
        
        # Enhanced meta-prompt with security and monitoring awareness
        meta_prompt = f"""You are an intelligent assistant with access to dynamic MCP tools, resources, and prompts.
You operate with enhanced security guardrails and monitoring capabilities.

Available capabilities:
- Tools: {[tool['function']['name'] for tool in available_tools if not tool['function']['name'].startswith('get_')]}
- Prompts: {[prompt['name'] for prompt in state['available_prompts']]}
- Resources: {[resource['name'] for resource in state['available_resources']]}

Current conversation context: {state['user_query']}

SECURITY AND MONITORING GUIDELINES:
1. For sensitive operations (remember, forget, admin functions), ALWAYS use request_authorization first
2. High-security tools require explicit human approval before execution
3. All actions are monitored and logged for security auditing
4. Use format_response to provide structured, clear outputs
5. Check security status with check_security_status when relevant

WORKFLOW INSTRUCTIONS:
1. Assess if the request involves sensitive data or operations
2. If sensitive, use request_authorization before proceeding
3. Determine if you need a specific prompt template by calling get_prompt_[name]
4. Access additional context using get_resource_[name] if needed
5. Ask for clarification using ask_human when requirements are unclear
6. Execute the appropriate MCP tools to fulfill the request
7. Format the final response appropriately using format_response

ALWAYS prioritize security, transparency, and user safety in your responses."""
        
        # Build the full message list
        full_messages = [SystemMessage(content=meta_prompt)] + messages
        
        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(available_tools)
        
        # Get response
        response = await llm_with_tools.ainvoke(full_messages)
        
        # Add AI response to messages
        state["messages"].append(response)
        
        print(f"🤖 Model response: {response.content[:100] if response.content else 'Tool calls requested'}...")
        
        return state
    
    async def should_continue(self, state: AgentState) -> AgentState:
        """Decide whether to continue with tool calls, human interaction, or end"""
        last_message = state["messages"][-1]
        
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            # Check if any tool calls require human interaction
            human_interaction_tools = ["ask_human", "request_authorization"]
            
            for tool_call in last_message.tool_calls:
                if tool_call['name'] in human_interaction_tools:
                    print(f"👤 Human interaction needed: {tool_call['name']}")
                    state["next_action"] = "human_interaction"
                    return state
            
            print(f"🔄 Tool calls detected: {len(last_message.tool_calls)} tools to call")
            state["next_action"] = "call_mcp"
        else:
            print("🏁 No tool calls, ending conversation")
            state["next_action"] = "end"
        
        return state
    
    async def handle_human_interaction(self, state: AgentState) -> AgentState:
        """Handle human-in-the-loop interactions"""
        print("👤 Handling human interaction...")
        
        last_message = state["messages"][-1]
        
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_call_id = tool_call['id']
                
                if tool_name == "ask_human":
                    question = tool_args.get("question", "")
                    context = tool_args.get("context", "")
                    response = await self.ask_human(question, context)
                    
                    # Add human response to messages
                    state["messages"].append(ToolMessage(
                        content=f"Human response: {response}",
                        tool_call_id=tool_call_id
                    ))
                
                elif tool_name == "request_authorization":
                    tool_to_authorize = tool_args.get("tool_name", "")
                    args_to_authorize = tool_args.get("tool_args", {})
                    reason = tool_args.get("reason", "")
                    
                    authorized = await self.request_authorization(tool_to_authorize, args_to_authorize, reason)
                    
                    if authorized:
                        # Store pending authorization
                        state["pending_authorization"] = {
                            "tool_name": tool_to_authorize,
                            "tool_args": args_to_authorize
                        }
                        
                        state["messages"].append(ToolMessage(
                            content="Authorization granted. You may proceed with the tool call.",
                            tool_call_id=tool_call_id
                        ))
                    else:
                        state["messages"].append(ToolMessage(
                            content="Authorization denied. The tool call has been cancelled.",
                            tool_call_id=tool_call_id
                        ))
        
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
                
                # Skip human interaction tools (handled in different node)
                if tool_name in ["ask_human", "request_authorization"]:
                    continue
                
                # Check if authorization is required and has been granted
                if state.get("pending_authorization"):
                    pending = state["pending_authorization"]
                    if pending["tool_name"] == tool_name and pending["tool_args"] == tool_args:
                        print("✅ Using pre-authorized tool call")
                        # Clear the pending authorization
                        state["pending_authorization"] = None
                
                # Execute the appropriate MCP operation
                if tool_name in [tool['name'] for tool in state['available_tools']]:
                    # Standard MCP tool call
                    result = await self.call_mcp_tool(tool_name, tool_args)
                elif tool_name.startswith("get_prompt_"):
                    # Prompt access
                    prompt_name = tool_name.replace("get_prompt_", "")
                    prompt_args = tool_args.get("arguments", {})
                    result = await self.get_mcp_prompt(prompt_name, prompt_args)
                elif tool_name.startswith("get_resource_"):
                    # Resource access - need to map back to original URI
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
                elif tool_name == "check_security_status":
                    # Call security status check
                    include_metrics = tool_args.get("include_metrics", False)
                    result = await self.check_security_status(include_metrics)
                elif tool_name == "format_response":
                    # Call response formatter
                    content = tool_args.get("content", "")
                    format_type = tool_args.get("format_type", "structured")
                    result = await self.format_response(content, format_type)
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
            "user_query": user_input,
            "human_input_needed": False,
            "pending_authorization": None
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
        print("🎯 Optimized LangGraph React Agent MCP Client")
        print("=" * 50)
        
        # Interactive mode
        print("\n🎮 Interactive mode - Type 'quit' to exit")
        print("Features:")
        print("- Dynamic prompt selection")
        print("- Human-in-the-loop interactions")
        print("- Authorization requests")
        print("- Dynamic tool/resource discovery")
        
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