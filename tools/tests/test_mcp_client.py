from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import asyncio
from app.services.ai.models.ai_factory import AIFactory

model = AIFactory.get_instance().get_llm(
            model_name="llama3.1",
            provider="ollama" 
        ).get_runnable()

async def main():
    async with MultiServerMCPClient(
        {
            "math": {
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["/Users/xenodennis/Documents/Fun/HaleyAI/app/services/ai/tools/mcp_server/math_server.py"],
                "transport": "stdio",
            },
            "weather": {
                # make sure you start your weather server on port 8000
                "url": "http://localhost:8000/sse",
                "transport": "sse",
            },
            "stripe": {
                # Use the official Stripe MCP server
                "command": "npx",
                "args": [
                    "-y",
                    "@smithery/cli",
                    "install",
                    "@atharvagupta2003/mcp-stripe",
                    "--client",
                    "claude"
                ],
                "env": {
                    "STRIPE_API_KEY": "your_stripe_secret_key"  # Replace with your actual Stripe API key
                },
                "transport": "stdio",
            }
        }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        
        # Test math functionality
        math_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
        print(f"Math response: {math_response}")
        
        # Test weather functionality
        weather_response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
        print(f"Weather response: {weather_response}")
        
        # Test Stripe functionality
        stripe_response = await agent.ainvoke({"messages": "Create a new customer with email test@example.com and name Test User"})
        print(f"Stripe response: {stripe_response}")

if __name__ == "__main__":
    asyncio.run(main())
