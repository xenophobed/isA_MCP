import asyncio
from app.config.config_manager import config_manager
from ..memory.utils import get_fact_retrieval_messages, parse_messages
from ..memory.utils import parse_messages

async def test_llm_response():
    # Initialize LLM service
    llm = await config_manager.get_service('llm')
    
    # Test messages
    messages = [
        {"role": "user", "content": "My order #12345 hasn't arrived yet. It's been 5 days."},
        {"role": "assistant", "content": "I understand your concern. Let me check the status for you."},
        {"role": "user", "content": "The tracking shows it's still in transit."},
    ]
    
    # Parse messages and get prompts
    parsed_messages = parse_messages(messages)
    system_prompt, user_prompt = get_fact_retrieval_messages(parsed_messages)
    
    print("\nSystem Prompt:")
    print(system_prompt)
    print("\nUser Prompt:")
    print(user_prompt)
    
    try:
        # Generate response with explicit JSON format request
        response = await llm.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        print("\nRaw LLM Response:")
        print(response)
        
        # Check response type
        print("\nResponse Type:", type(response))
        
        # If response is string, try parsing as JSON
        if isinstance(response, str):
            try:
                import json
                json_response = json.loads(response)
                print("\nParsed JSON Response:")
                print(json_response)
            except json.JSONDecodeError as e:
                print("\nFailed to parse as JSON:", e)
        
    except Exception as e:
        print(f"\nError generating response: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_llm_response())