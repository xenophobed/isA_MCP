#!/usr/bin/env python
"""
Enhanced MCP Client v1.3 - Event Sourcing & Ambient Agent
- Tests Event-Driven MCP services
- Background task management
- Proactive notification system
- Agent feedback processing
"""
import asyncio
import json
import os
from typing import Dict, List, Any, Annotated, Optional, Union
from datetime import datetime
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

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

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=SecretStr(api_key) if api_key else None,
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
    event_feedback: Annotated[Optional[Dict], "Event feedback from background tasks"]

class EventDrivenMCPClient:
    def __init__(self, use_load_balancer: bool = True):
        self.session: Optional[MCPHTTPClient] = None
        self.graph = None
        self.conversation_history = []
        self.use_load_balancer = use_load_balancer
        self.background_tasks = []
        
        # Connection URLs for different servers
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
        print("🔌 Connecting to Event-Driven MCP server...")
        
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
            
            # Check for Event Sourcing tools
            event_tools = [t for t in capabilities['tools'] if 
                         'background' in t['name'].lower() or 
                         'event' in t['name'].lower() or
                         t['name'] in ['create_background_task', 'list_background_tasks', 
                                     'pause_background_task', 'resume_background_task', 
                                     'delete_background_task', 'get_event_sourcing_status']]
            if event_tools:
                print(f"🎯 Event Sourcing tools found: {[t['name'] for t in event_tools]}")
            else:
                print("⚠️ No Event Sourcing tools found. Make sure Event Sourcing server is running.")
                print(f"📋 Available tools: {[t['name'] for t in capabilities['tools']]}")
            
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
            
            # Handle special tool responses
            if tool_name == "create_background_task":
                self._handle_background_task_created(result)
            elif tool_name == "list_background_tasks":
                self._handle_background_tasks_listed(result)
            
            return str(result)
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error: {error_msg}")
            return json.dumps({"error": f"Tool call failed: {error_msg}"})
    
    def _handle_background_task_created(self, result: str):
        """Handle background task creation response"""
        try:
            result_data = json.loads(result)
            if result_data.get("status") == "success":
                task_data = result_data.get("data", {})
                self.background_tasks.append(task_data)
                print(f"📝 Background task registered: {task_data.get('task_id', 'unknown')}")
        except:
            pass
    
    def _handle_background_tasks_listed(self, result: str):
        """Handle background tasks list response"""
        try:
            result_data = json.loads(result)
            if result_data.get("status") == "success":
                tasks = result_data.get("data", {}).get("tasks", [])
                self.background_tasks = tasks
                print(f"📋 Background tasks updated: {len(tasks)} tasks")
        except:
            pass
    
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
    
    def build_agent_graph(self):
        """Build the LangGraph agent with Event Sourcing support"""
        print("🏗️ Building Event-Driven LangGraph agent...")
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("call_model", self.call_model)
        workflow.add_node("should_continue", self.should_continue)
        workflow.add_node("execute_tools", self.execute_tools)
        workflow.add_node("process_event_feedback", self.process_event_feedback)
        
        # Add edges
        workflow.set_entry_point("call_model")
        workflow.add_edge("call_model", "should_continue")
        workflow.add_conditional_edges(
            "should_continue",
            lambda state: state["next_action"],
            {
                "execute_tools": "execute_tools",
                "process_event_feedback": "process_event_feedback",
                "end": END
            }
        )
        workflow.add_edge("execute_tools", "call_model")
        workflow.add_edge("process_event_feedback", "call_model")
        
        # Compile the graph
        self.graph = workflow.compile()
        print("✅ Event-Driven LangGraph agent built successfully")
    
    async def call_model(self, state: AgentState) -> AgentState:
        """Call the language model with Event Sourcing integration"""
        print("🧠 Calling language model...")
        
        messages = state["messages"]
        
        # Create tools for LLM
        available_tools = self.create_tools_for_llm(state)
        
        # Enhanced system prompt for Event Sourcing
        system_prompt = f"""You are an intelligent Event-Driven Assistant with comprehensive MCP server access and background task capabilities.

🎯 EVENT SOURCING CAPABILITIES:
Available MCP Tools ({len(state['available_tools'])}):
{', '.join([tool['name'] for tool in state['available_tools']])}

🔍 BACKGROUND TASK TYPES:
- web_monitor: Monitor websites for content changes with keywords
- schedule: Run tasks on daily/interval schedules  
- news_digest: Generate daily news summaries from multiple sources
- threshold_watch: Monitor metrics and alert on threshold breaches

📊 CURRENT BACKGROUND TASKS: {len(self.background_tasks)} active tasks

Current query: {state['user_query']}

🚀 EVENT-DRIVEN WORKFLOW:
1. **Task Creation**: Use create_background_task to set up monitoring
2. **Task Management**: Use list/pause/resume/delete_background_task for control
3. **Event Processing**: Analyze event feedback and determine user notifications
4. **Proactive Notifications**: Use send_sms/send_email for important updates

📋 TASK CONFIGURATION EXAMPLES:

Web Monitor:
{{
  "urls": ["https://techcrunch.com", "https://news.ycombinator.com"],
  "keywords": ["artificial intelligence", "AI", "machine learning"],
  "check_interval_minutes": 30,
  "notification": {{
    "method": "send_sms",
    "phone_number": "+1234567890"
  }}
}}

Daily Schedule:
{{
  "type": "daily",
  "hour": 8,
  "minute": 0,
  "action": "news_digest",
  "notification": {{
    "method": "send_sms",
    "phone_number": "+1234567890"
  }}
}}

News Digest:
{{
  "news_urls": ["https://techcrunch.com", "https://bbc.com/news"],
  "hour": 8,
  "categories": ["technology", "business"],
  "notification": {{
    "method": "send_sms",
    "phone_number": "+1234567890"
  }}
}}

🎯 ENHANCED CAPABILITIES:
- **Memory Management**: remember, forget, search_memories for persistent data
- **Weather Information**: get_weather for current conditions
- **Communication**: send_sms, send_email for notifications
- **Security & Monitoring**: Built-in authorization and audit trails
- **Dynamic Resources**: Access specialized prompts and data sources

CRITICAL INSTRUCTIONS:
1. When users request monitoring/scheduling, create appropriate background tasks
2. Always include notification preferences in task config
3. Use callback_url: "http://localhost:8000/process_background_feedback" for event callbacks
4. Explain what the background task will do and how notifications will work
5. For urgent events, use immediate notifications via SMS/email
6. Provide clear status updates on background task management

The Event Sourcing system runs independently and will proactively notify users when conditions are met.
Focus on creating meaningful, actionable background tasks that provide real value to users."""

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
        
        # Check for event feedback to process
        if state.get("event_feedback"):
            print("📥 Event feedback detected, processing...")
            state["next_action"] = "process_event_feedback"
        elif hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print(f"🔄 Tool calls detected: {len(last_message.tool_calls)} tools to execute")
            state["next_action"] = "execute_tools"
        else:
            print("🏁 No tool calls or events, ending conversation")
            state["next_action"] = "end"
        
        return state
    
    async def execute_tools(self, state: AgentState) -> AgentState:
        """Execute all MCP tool calls"""
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
    
    async def process_event_feedback(self, state: AgentState) -> AgentState:
        """Process event feedback from background tasks"""
        print("📥 Processing event feedback...")
        
        event_feedback = state.get("event_feedback")
        if not event_feedback:
            return state
        
        # Create a message about the event feedback
        feedback_message = f"""
Event feedback received from background task:

Task ID: {event_feedback.get('task_id', 'unknown')}
Event Type: {event_feedback.get('event_type', 'unknown')}
Priority: {event_feedback.get('priority', 1)}
Timestamp: {event_feedback.get('timestamp', 'unknown')}

Data:
{json.dumps(event_feedback.get('data', {}), indent=2)}

Please analyze this event feedback and determine:
1. Is this information relevant and actionable?
2. Should the user be notified immediately?
3. What summary or action should be taken?
4. If notification is needed, use appropriate communication tools.
"""
        
        # Add the feedback as a human message for processing
        state["messages"].append(HumanMessage(content=feedback_message))
        
        # Clear the event feedback
        state["event_feedback"] = None
        
        return state
    
    async def run_conversation(self, user_input: str, event_feedback: Optional[Dict] = None):
        """Run a complete conversation with optional event feedback"""
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
            "user_query": user_input,
            "event_feedback": event_feedback
        }
        
        if self.graph:
            print(f"🚀 Running Event-Driven LangGraph agent...")
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
    
    async def simulate_event_feedback(self, task_id: str, event_type: str, data: Dict):
        """Simulate event feedback for testing"""
        event_feedback = {
            "task_id": task_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "priority": 3
        }
        
        print(f"📥 Simulating event feedback: {event_type}")
        response = await self.run_conversation(
            "Process this background task event feedback",
            event_feedback=event_feedback
        )
        return response
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

async def main():
    """Main function to run the Event-Driven client"""
    print("🎯 Event-Driven MCP Client v1.3")
    print("=" * 60)
    print("🌟 FEATURES:")
    print("  - Background Task Management")
    print("  - Event-Driven Monitoring")
    print("  - Proactive Notifications")
    print("  - Web Content Monitoring")
    print("  - Scheduled Task Execution")
    print("  - News Digest Generation")
    
    while True:
        choice = input("\n🤔 Choose connection type (1=Load Balancer, 2=Direct): ").strip()
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
    
    client = EventDrivenMCPClient(use_load_balancer=use_load_balancer)
    
    try:
        print("\n🎮 Interactive mode:")
        print("  quit - Exit the client")
        print("  demo - Run demo scenarios")
        print("  tasks - Show background tasks")
        print("  simulate - Simulate event feedback")
        
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'demo':
                    await run_demo_scenarios(client)
                elif user_input.lower() == 'tasks':
                    await show_background_tasks(client)
                elif user_input.lower() == 'simulate':
                    await simulate_event_scenarios(client)
                elif user_input:
                    await client.run_conversation(user_input)
                    print("-" * 60)
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
    
    finally:
        await client.cleanup()

async def run_demo_scenarios(client):
    """Run demo scenarios for Event Sourcing"""
    print("\n🎬 Running Event Sourcing Demo Scenarios...")
    
    # Demo 1: Web Monitoring
    print("\n📊 Demo 1: Web Content Monitoring")
    await client.run_conversation(
        "Set up a background task to monitor TechCrunch for new articles about artificial intelligence. "
        "Check every 30 minutes and send me SMS notifications when new AI content is found. "
        "My phone number is +1234567890."
    )
    
    # Demo 2: Daily News Digest
    print("\n📰 Demo 2: Daily News Digest")
    await client.run_conversation(
        "Create a daily news digest task that summarizes the latest technology news from TechCrunch and Hacker News. "
        "Send me the digest every morning at 8 AM via SMS to +1234567890."
    )
    
    # Demo 3: Scheduled Reminder
    print("\n⏰ Demo 3: Scheduled Reminder")
    await client.run_conversation(
        "Set up a daily reminder to check my project status every day at 9 AM. "
        "Send the reminder via SMS to +1234567890."
    )

async def show_background_tasks(client):
    """Show current background tasks"""
    print("\n📋 Current Background Tasks:")
    await client.run_conversation("List all my background tasks and their status")

async def simulate_event_scenarios(client):
    """Simulate event feedback scenarios"""
    print("\n🎭 Simulating Event Scenarios...")
    
    # Simulate web content change
    await client.simulate_event_feedback(
        task_id="demo-task-1",
        event_type="web_content_change",
        data={
            "url": "https://techcrunch.com",
            "content": "New breakthrough in artificial intelligence: GPT-5 announced with revolutionary capabilities...",
            "keywords_found": ["artificial intelligence", "GPT-5"],
            "description": "Monitor TechCrunch for AI news",
            "user_id": "default"
        }
    )
    
    # Simulate daily news digest
    await client.simulate_event_feedback(
        task_id="demo-task-2",
        event_type="daily_news_digest",
        data={
            "digest_date": datetime.now().date().isoformat(),
            "news_summaries": [
                {
                    "source": "https://techcrunch.com",
                    "headlines": [
                        "AI startup raises $100M Series A",
                        "New quantum computing breakthrough",
                        "Apple announces AI-powered features"
                    ]
                },
                {
                    "source": "https://news.ycombinator.com",
                    "headlines": [
                        "Show HN: My AI coding assistant",
                        "The future of programming with AI",
                        "Building scalable AI infrastructure"
                    ]
                }
            ],
            "description": "Daily tech news digest",
            "user_id": "default"
        }
    )

if __name__ == "__main__":
    asyncio.run(main())
