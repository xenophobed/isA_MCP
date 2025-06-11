import asyncio
import logging
import sys
import json

import os 
os.environ["ENV"] = "local"

from app.capability.source.knowledge_extractor import KnowledgeExtractor
from app.capability.source.knowledge_embedder import KnowledgeVectorEmbedder
from app.capability.registry.knowledge_graph_manager import KnowledgeGraphManager
from app.config.config_manager import config_manager
from pydantic import BaseModel
from typing import Dict

class ChunkInfo(BaseModel):
    chunk_id: str
    text: str
    metadata: Dict

logger = config_manager.get_logger(__name__)

async def test_knowledge_flow():
    """Test the complete knowledge processing and search flow"""
    
    # Test content
    test_content = """
    # Python Exception Handling Guide
    
    This guide covers Python's exception handling mechanisms and best practices.
    
    ## Basic Try-Except
    The most basic form of exception handling uses try-except blocks:    ```python
    try:
        result = 10 / 0
    except ZeroDivisionError:
        print("Cannot divide by zero")    ```
    
    ## Common Exception Types
    - ValueError: Invalid value or argument
    - TypeError: Operation on incompatible types
    - FileNotFoundError: Accessing non-existent file
    
    ## Best Practices
    1. Always catch specific exceptions
    2. Use finally blocks for cleanup
    3. Create custom exceptions for your applications
    """
    
    try:
        # Initialize components
        extractor = KnowledgeExtractor()
        embedder = KnowledgeVectorEmbedder()
        graph_manager = KnowledgeGraphManager()
        
        await extractor.initialize()
        await embedder.initialize()
        await graph_manager.initialize()
        
        # Extract and store knowledge
        logger.info("Extracting and storing knowledge...")
        metadata = await extractor.extract_from_content(test_content)
        vectors = await embedder.generate_vectors(metadata)
        await graph_manager.store_knowledge(metadata, vectors)
        
        # Test search scenarios
        search_queries = [
            {
                "query": "How to handle division by zero in Python?",
                "weights": {"semantic": 0.3, "functional": 0.4, "contextual": 0.3}
            },
            {
                "query": "What are Python's exception types?",
                "weights": {"semantic": 0.5, "functional": 0.3, "contextual": 0.2}
            },
            {
                "query": "Best practices for error handling",
                "weights": {"semantic": 0.2, "functional": 0.3, "contextual": 0.5}
            }
        ]
        
        for search_case in search_queries:
            logger.info(f"\nSearch Query: {search_case['query']}")
            results = await graph_manager.comprehensive_search(
                search_case["query"], 
                search_case["weights"]
            )
            
            # Log capability results
            logger.info("\nTop Capability Matches:")
            for result in results["capabilities"][:2]:  # Show top 2
                logger.info(f"- Score: {result['score']:.3f}")
                logger.info(f"  ID: {result['capability_id']}")
                logger.info(f"  Core Concepts: {', '.join(result['core_concepts'])}")
            
            # Log chunk results
            logger.info("\nTop Content Matches:")
            for result in results["chunks"][:2]:  # Show top 2
                logger.info(f"- Score: {result['score']:.3f}")
                logger.info(f"  Summary: {result['summary']}")
            
            logger.info("-" * 80)
                
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run test
    asyncio.run(test_knowledge_flow())
