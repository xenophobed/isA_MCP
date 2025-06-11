from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
import asyncio

async def main():
    # --- Correct Server Configurations ---
    # 1. Your FastAPI server that hosts the tools
    MCP_SERVER_URL = "http://localhost:10000"
    SSE_ENDPOINT = f"{MCP_SERVER_URL}/sse"  # The correct endpoint for the sse_client

    # 2. Your local Ollama server that hosts the LLM
    OLLAMA_SERVER_URL = "http://localhost:11434"

    # --- Corrected Connection Logic ---
    # Connect the sse_client to your MCP server
    print(f"Connecting MCP client to: {SSE_ENDPOINT}")
    async with sse_client(SSE_ENDPOINT) as (read, write):
        async with ClientSession(read, write) as session:
            # Load tools from your MCP server
            tools = await load_mcp_tools(session)
            print(f"Loaded tools: {[tool.name for tool in tools]}")
            
            # Point the LLM client to the Ollama server
            llm = ChatOllama(
                model='llama3.2', # Model name can be simpler
                base_url=OLLAMA_SERVER_URL,
            )
            
            # Create LangGraph agent
            agent = create_react_agent(
                llm,
                tools
            )
            
            # Execute query
            print("Invoking agent...")
            response = await agent.ainvoke({
                "messages": [{
                    "role": "user",
                    "content": "Calculate (15 + 7) multiplied by 3"
                }]
            })
            
            print("Agent Response:", response['messages'][-1].content)

if __name__ == "__main__":
    asyncio.run(main())