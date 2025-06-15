# test_entry_processing_flow.py
import os 
os.environ['ENV'] = 'local'

import asyncio
import logging
from datetime import datetime, UTC
from typing import Dict, Any, List
from app.services.knowledge.entry_service import EntryService, Entry
from app.services.knowledge.processor_service import ProcessorService
from app.services.knowledge.index_service import IndexService
from app.capability.registry.knowledge_graph_manager import KnowledgeGraphManager
from app.config.config_manager import config_manager
from app.services.ai.rag.vector_factory import VectorFactory
from app.config.vector.qdrant_config import QdrantConfig
from app.models.knowledge.entry import ProcessingStatus

logger = config_manager.get_logger(__name__)

class MockFileService:
    async def extract_text(self, file_id: str) -> str:
        return """
        # Python Exception Handling Guide
        
        This guide covers Python's exception handling mechanisms and best practices.
        
        ## Basic Try-Except
        The most basic form of exception handling uses try-except blocks:        ```python
        try:
            result = 10 / 0
        except ZeroDivisionError:
            print("Cannot divide by zero")        ```
        
        ## Common Exception Types
        - ValueError: Invalid value or argument
        - TypeError: Operation on incompatible types
        - FileNotFoundError: Accessing non-existent file
        
        ## Best Practices
        1. Always catch specific exceptions
        2. Use finally blocks for cleanup
        3. Create custom exceptions for your applications
        """

class MockRepository:
    async def update(self, entry_id: str, data: Dict[str, Any]):
        logger.info(f"Updating entry {entry_id} with data: {data}")
        
    async def find_one(self, query: Dict) -> Dict:
        return {"id": "test_id"}
        
    async def create_index(self, index_data: Dict) -> str:
        return "test_index_id"

class MockVectorService:
    """Mock implementation of vector service interface"""
    async def initialize(self):
        pass
        
    async def create_collection(self, collection_name: str, vectors_config: Dict):
        pass
        
    async def upsert_points(self, points: List[Dict], collection_name: str):
        logger.info(f"Upserting {len(points)} points to collection {collection_name}")
        
    async def search(self, query: List[float], limit: int = 5, **kwargs):
        return []
        
    def collection_exists(self, name: str) -> bool:
        return True

async def analyze_embedding_flow():
    """Test and analyze the embedding flow"""
    try:
        # Initialize configurations
        vector_config = QdrantConfig()
        
        # Initialize services with real implementations
        file_service = MockFileService()
        repository = MockRepository()
        
        # Initialize processor service and its dependencies
        processor_service = ProcessorService()
        await processor_service.knowledge_extractor.initialize()
        await processor_service.knowledge_embedder.initialize()
        await processor_service.graph_manager.initialize()
        
        # Create vector service
        vector_service = await VectorFactory.create_vector_service("qdrant", vector_config)
        
        # Initialize index service
        index_service = IndexService(
            repository=repository,
            vector_service=vector_service
        )
        
        # Initialize entry service
        entry_service = EntryService(
            repository=repository,
            file_service=file_service,
            processor_service=processor_service,
            index_service=index_service
        )

        # Create test entry with more substantial content
        test_content = """
        # Python Exception Handling Guide
        
        This guide covers Python's exception handling mechanisms and best practices.
        
        ## Basic Try-Except
        The most basic form of exception handling uses try-except blocks:        ```python
        try:
            result = 10 / 0
        except ZeroDivisionError:
            print("Cannot divide by zero")        ```
        
        ## Common Exception Types
        - ValueError: Invalid value or argument
        - TypeError: Operation on incompatible types
        - FileNotFoundError: Accessing non-existent file
        
        ## Best Practices
        1. Always catch specific exceptions
        2. Use finally blocks for cleanup
        3. Create custom exceptions for your applications
        """
        
        entry = Entry(
            entry_id="test_entry_001",
            knowledge_id="test_knowledge_001",
            title="Python Exception Handling",
            type="markdown",
            content=test_content,
            url="https://example.com/python-guide",
            file_id="test_file_001",
            status=ProcessingStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )

        # Process the entry
        logger.info("\nStarting entry processing...")
        logger.info("1. Initializing services...")
        logger.info("2. Processing content...")
        
        # Add chunk format verification
        logger.info("3. Verifying chunk format...")
        chunks, doc_semantics = await processor_service.process_content(entry.content)
        for chunk in chunks:
            assert "chunk_id" in chunk, "Chunk missing chunk_id"
            assert "content" in chunk, "Chunk missing content"
            assert "embedding" in chunk, "Chunk missing embedding"
            assert "metadata" in chunk, "Chunk missing metadata"
            
        await entry_service._process_entry(entry)
        
        # Storage verification
        logger.info("\n=== Storage Verification ===")
        
        # 1. Neo4j Verification
        logger.info("\n1. Neo4j Storage:")
        neo4j_results = await processor_service.graph_manager.search_capabilities(
            query_text="Python exception handling",
            weights={"semantic": 0.3, "functional": 0.4, "contextual": 0.3}
        )
        
        # Add more detailed verification
        logger.info(f"Found {len(neo4j_results)} capabilities")
        if len(neo4j_results) > 0:
            logger.info("✓ Neo4j storage successful")
            for result in neo4j_results[:2]:
                logger.info(f"- Capability: {result['capability_id']}")
                logger.info(f"  Score: {result['score']:.3f}")
                logger.info(f"  Core Concepts: {result['core_concepts']}")
        else:
            logger.warning("⚠️ No results found in Neo4j")
            
        # 2. Vector Store Verification
        logger.info("\n2. Vector Store:")
        vector_results = await processor_service.graph_manager.search_chunks(
            query_text="Python exception handling",
            threshold=0.3
        )
        
        # Add more detailed verification
        logger.info(f"Found {len(vector_results)} chunks")
        if len(vector_results) > 0:
            logger.info("✓ Vector store storage successful")
            for result in vector_results[:2]:
                logger.info(f"- Score: {result['score']:.3f}")
                logger.info(f"  Summary: {result['summary']}")
        else:
            logger.warning("⚠️ No results found in vector store")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

async def test_search_flow():
    """Test the search capabilities"""
    try:
        # Initialize services
        processor_service = ProcessorService()
        graph_manager = KnowledgeGraphManager()
        await processor_service._init_services()
        await graph_manager.initialize()
        
        # Test query
        query = "How to handle division by zero in Python?"
        
        logger.info(f"\nTesting search for: {query}")
        
        # 1. Test ProcessorService search
        logger.info("\n1. ProcessorService Search:")
        logger.info("- Uses direct vector similarity")
        logger.info("- Searches in chunk vectors")
        
        # 2. Test Knowledge Graph search
        logger.info("\n2. Knowledge Graph Search:")
        search_results = await graph_manager.comprehensive_search(
            query_text=query,
            weights={"semantic": 0.3, "functional": 0.4, "contextual": 0.3}
        )
        
        logger.info("\nSearch Comparison:")
        logger.info("1. ProcessorService Search:")
        logger.info("- Pros: Direct content matching")
        logger.info("- Cons: No semantic understanding")
        
        logger.info("\n2. Knowledge Graph Search:")
        logger.info("- Pros: Semantic understanding")
        logger.info("- Cons: More complex, requires more processing")
        
        logger.info("\nRecommendations:")
        logger.info("1. Combine both search approaches")
        logger.info("2. Use semantic search for high-level matching")
        logger.info("3. Use vector search for specific content")

    except Exception as e:
        logger.error(f"Search test failed: {str(e)}")
        raise

async def main():
    """Run all tests"""
    logger.info("Starting tests...")
    
    # Test embedding flow
    await analyze_embedding_flow()
    
    # Test search flow
    await test_search_flow()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())