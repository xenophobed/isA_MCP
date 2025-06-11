from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

async def main():
    # Initialize the LLM using your OpenAI API key
    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_API_BASE"),
        model=os.getenv("LLM_MODEL"),
        temperature=float(os.getenv("LLM_TEMPERATURE", 0.7))
    )

    # Create the agent with specific task instructions
    agent = Agent(
        task="""Visit this Amazon product page and extract the following information:
            1. Detailed product description
            2. Technical specifications
            3. At least 5 most helpful customer reviews with their ratings
            URL: https://www.amazon.com/ZST-Colorful-Banlance-Armature-Earphone/dp/B01N0782B3
            
            Please format the information clearly and save the reviews in a structured format.
            """,
        llm=llm,
        browser_config={
            "headless": False,  # Set to True in production
            "disable_security": True,  # Helpful for avoiding some Amazon anti-bot measures
            "minimum_wait_page_load_time": 3,  # Give more time for dynamic content
            "wait_for_network_idle_page_load_time": 5
        }
    )

    # Run the agent and get results
    result = await agent.run()
    print("Extraction Results:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
