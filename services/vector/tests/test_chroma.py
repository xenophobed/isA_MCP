import asyncio
import logging
import os
import shutil
from typing import List, Dict
from app.services.ai.models.ai_factory import AIFactory
from app.services.db.vector.vector_factory import VectorFactory
from app.config.vector.chroma_config import ChromaConfig

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestChromaConfig(ChromaConfig):
    """Test configuration for ChromaDB"""
    
    def __init__(self):
        super().__init__()
        # Override settings for testing
        self.settings.collection_name = "test_collection"
        self.persist_directory = "./test_chroma_data"
        # Set vector size to match the embedding model's output
        self.settings.vector_size = 1024  # bge-m3 model outputs 1024-dimensional vectors
        
    def setup(self) -> None:
        """Setup test environment"""
        if os.path.exists(self.persist_directory):
            shutil.rmtree(self.persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)

async def test_vector_service():
    """Test ChromaDB vector service functionality"""
    vector_service = None
    embed_service = None
    config = TestChromaConfig()
    
    try:
        logger.info("\n=== Starting ChromaDB Service Tests ===")
        
        # Test 1: Service Creation
        logger.info("\n1. Testing Service Creation")
        
        # Set test configuration
        vector_factory = VectorFactory.get_instance()
        vector_factory.set_config(config)
        
        vector_service = await vector_factory.get_vector("chroma")
        assert vector_service is not None
        logger.info("✓ Successfully created ChromaDB service")

        # Get embedding service
        ai_factory = AIFactory.get_instance()
        embed_service = ai_factory.get_embedding(
            model_name="bge-m3",
            provider="ollama"
        )
        assert embed_service is not None
        logger.info("✓ Successfully created embedding service")

        # Test 2: Collection Management
        logger.info("\n2. Testing Collection Management")
        collection_name = "test_collection"
        
        # Check if collection exists
        exists = await vector_service.collection_exists(collection_name)
        if exists:
            success = await vector_service.delete_collection(collection_name)
            assert success, "Failed to delete existing collection"
            logger.info("✓ Successfully deleted existing collection")
        
        # Create new collection
        collection = await vector_service.create_collection(collection_name)
        assert collection is not None
        logger.info("✓ Successfully created new collection")

        # Test 3: Point Insertion
        logger.info("\n3. Testing Point Insertion")
        test_points = [
            {
                "text": "Python is a high-level programming language known for its simplicity.",
                "metadata": {
                    "category": "programming",
                    "language": "Python",
                    "difficulty": "beginner"
                }
            },
            {
                "text": "Neural networks are computing systems inspired by biological neural networks.",
                "metadata": {
                    "category": "machine_learning",
                    "topic": "neural_networks",
                    "difficulty": "advanced"
                }
            },
            {
                "text": "Vector databases are optimized for storing and searching vector embeddings.",
                "metadata": {
                    "category": "database",
                    "topic": "vector_db",
                    "difficulty": "intermediate"
                }
            }
        ]
        
        success = await vector_service.upsert_points(test_points)
        assert success, "Failed to insert points"
        logger.info("✓ Successfully inserted test points")

        # Test 4: Basic Search
        logger.info("\n4. Testing Basic Search")
        query_text = "Tell me about programming languages"
        query_vector = await embed_service.create_text_embedding(query_text)
        
        results = await vector_service.search(
            query=query_vector,
            limit=2
        )
        
        assert len(results) > 0, "No search results found"
        logger.info(f"✓ Found {len(results)} results")
        
        for result in results:
            logger.info(f"\nScore: {result['score']:.4f}")
            logger.info(f"Document: {result['document']}")
            logger.info(f"Metadata: {result['metadata']}")

        # Test 5: Filtered Search
        logger.info("\n5. Testing Filtered Search")
        results = await vector_service.search(
            query=query_vector,
            limit=2,
            filters={"category": "programming"}
        )
        
        assert len(results) > 0, "No filtered results found"
        assert all(r['metadata'].get('category') == 'programming' for r in results), \
            "Filter not working correctly"
        logger.info("✓ Successfully tested filtered search")

        # Test 6: Error Handling
        logger.info("\n6. Testing Error Handling")
        
        # Test invalid collection name
        try:
            await vector_service.collection_exists("")
            assert False, "Should raise error for empty collection name"
        except ValueError:
            logger.info("✓ Successfully caught invalid collection name error")
        
        # Test invalid search parameters
        try:
            await vector_service.search(
                query=[0] * (len(query_vector) + 1),  # Wrong vector size
                limit=2
            )
            assert False, "Should raise error for invalid vector size"
        except ValueError:
            logger.info("✓ Successfully caught invalid vector size error")

        logger.info("\n=== All tests completed successfully! ===")
        return True

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        # Cleanup
        logger.info("\nCleaning up resources...")
        if vector_service:
            await VectorFactory.get_instance().cleanup()
        
        # Remove test directory
        if os.path.exists("./test_chroma_data"):
            shutil.rmtree("./test_chroma_data")

if __name__ == "__main__":
    try:
        asyncio.run(test_vector_service())
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Tests failed: {str(e)}")
        raise
