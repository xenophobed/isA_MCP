from isa_model.inference.ai_factory import AIFactory
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv('.env.local')

async def main():
    # Get LLM service
    llm = AIFactory.get_instance().get_llm(
        model_name="gpt-4o-mini", 
        provider="openai", 
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    response = await llm.ainvoke("Hello!")
    print("LLM Response:", response)

    # Get embedding service
    embed_service = AIFactory.get_instance().get_embed_service(model_name="bge-m3", provider="ollama")
    embedding = await embed_service.create_text_embedding("Hello, world!")
    print(f"Embedding: {len(embedding)} dimensions")

if __name__ == "__main__":
    asyncio.run(main())