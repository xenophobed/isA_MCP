# conv_extractor_test.py
import os
os.environ['ENV'] = 'local'

import asyncio
from datetime import datetime
from app.config.config_manager import config_manager
from app.capability.source.conv_extractor import ConversationExtractor
from app.models.chat import MessageType, TextMessageContent
import json

logger = config_manager.get_logger(__name__)

def print_conversation_structure(messages: list):
    """Print the cleaned conversation structure"""
    logger.info("\n=== Conversation Structure ===")
    logger.info("Sequential messages after cleaning and preprocessing:")
    
    for msg in messages:
        timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"\n[{timestamp}] {msg['sender_type'].upper()}")
        logger.info(f"Content: {msg['content']}")

def print_extracted_knowledge(facts: list):
    """Print the extracted facts and entities"""
    logger.info("\n=== Extracted Knowledge ===")
    logger.info(f"Total Facts: {len(facts)}")
    
    for i, fact in enumerate(facts, 1):
        logger.info(f"\nFact {i}:")
        logger.info(f"Entities: {', '.join(fact.entities)}")
        logger.info(f"Atomic Fact: {fact.atomic_fact}")

async def test_conversation_extraction():
    try:
        # Initialize extractor
        extractor = ConversationExtractor()
        await extractor.initialize()
        
        # Test conversation ID
        test_conv_id = 'conv_iphone_support_123'
        
        # Extract conversation
        logger.info(f"\nProcessing conversation: {test_conv_id}")
        result = await extractor.extract_conversation(test_conv_id)
        
        if result:
            # Print the conversation structure
            print_conversation_structure(result["messages"])
            
            # Print the extracted knowledge
            if result.get("atomic_facts"):
                print_extracted_knowledge(result["atomic_facts"])
            else:
                logger.info("\nNo facts extracted")
                
            # Save results for debugging
            debug_output = {
                "conversation_id": test_conv_id,
                "messages": [
                    {
                        "timestamp": msg["timestamp"].isoformat(),
                        "sender_type": msg["sender_type"],
                        "content": msg["content"]
                    }
                    for msg in result["messages"]
                ],
                "atomic_facts": [
                    {
                        "entities": fact.entities,
                        "atomic_fact": fact.atomic_fact
                    }
                    for fact in result["atomic_facts"]
                ]
            }
            
                
        else:
            logger.error("No results returned from extraction")
            
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
    finally:
        await config_manager.cleanup()

if __name__ == "__main__":
    # Set log level to INFO
    config_manager.set_log_level("INFO")
    
    # Run the test
    asyncio.run(test_conversation_extraction())
