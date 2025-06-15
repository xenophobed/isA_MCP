import pytest
import weaviate
import os
from typing import List, Dict, Any
from app.services.db.vector.implementations.weaviate_service import WeaviateService
from app.config.vector.weaviate_config import WeaviateConfig
from app.config.vector.base_vector_config import SearchType, DistanceMetric, AlgorithmType

@pytest.fixture
def weaviate_config():
    """Create a test configuration"""
    config = WeaviateConfig()
    # Override settings for testing
    config.connection.host = "localhost"
    config.connection.port = 8080
    config.connection.credentials = {
        "url": "http://localhost:8080",
        "api_key": ""
    }
    config.settings.vector_size = 384  # Using smaller size for testing
    config.settings.collection_name = "test_collection"
    config.settings.distance_metric = DistanceMetric.COSINE
    config.settings.algorithm = AlgorithmType.HNSW
    return config

@pytest.fixture
async def weaviate_client(weaviate_config):
    """Create a test client"""
    client = weaviate.Client(
        url=weaviate_config.connection.credentials["url"],
        auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_config.connection.credentials.get("api_key")),
        timeout_config=weaviate_config.connection.timeout
    )
    return client

@pytest.fixture
async def weaviate_service(weaviate_client, weaviate_config):
    """Create a test service instance"""
    service = WeaviateService(client=weaviate_client, config=weaviate_config)
    yield service
    # Cleanup
    if await service.collection_exists(weaviate_config.settings.collection_name):
        await service.delete_collection(weaviate_config.settings.collection_name)
    await service.close()

@pytest.mark.asyncio
async def test_create_collection(weaviate_service, weaviate_config):
    """Test collection creation"""
    # Create collection
    result = await weaviate_service.create_collection(weaviate_config.settings.collection_name)
    assert result is True
    
    # Verify collection exists
    exists = await weaviate_service.collection_exists(weaviate_config.settings.collection_name)
    assert exists is True

@pytest.mark.asyncio
async def test_delete_collection(weaviate_service, weaviate_config):
    """Test collection deletion"""
    # Create collection first
    await weaviate_service.create_collection(weaviate_config.settings.collection_name)
    
    # Delete collection
    result = await weaviate_service.delete_collection(weaviate_config.settings.collection_name)
    assert result is True
    
    # Verify collection is deleted
    exists = await weaviate_service.collection_exists(weaviate_config.settings.collection_name)
    assert exists is False

@pytest.mark.asyncio
async def test_upsert_points(weaviate_service, weaviate_config):
    """Test upserting points"""
    # Create collection first
    await weaviate_service.create_collection(weaviate_config.settings.collection_name)
    
    # Test data
    points = [
        {
            "text": "This is a test document",
            "metadata": {"source": "test", "id": 1}
        },
        {
            "text": "Another test document",
            "metadata": {"source": "test", "id": 2}
        }
    ]
    
    # Upsert points
    result = await weaviate_service.upsert_points(points)
    assert result is True

@pytest.mark.asyncio
async def test_search(weaviate_service, weaviate_config):
    """Test vector search"""
    # Create collection and insert test data
    await weaviate_service.create_collection(weaviate_config.settings.collection_name)
    
    test_points = [
        {
            "text": "The quick brown fox jumps over the lazy dog",
            "metadata": {"source": "test", "id": 1}
        },
        {
            "text": "A quick brown fox jumps over a lazy dog",
            "metadata": {"source": "test", "id": 2}
        }
    ]
    
    await weaviate_service.upsert_points(test_points)
    
    # Create a test query vector (using the same embedding service)
    embed_service = await weaviate_service._get_embed_service()
    query_vector = await embed_service.create_text_embedding("quick brown fox")
    
    # Search
    results = await weaviate_service.search(
        query=query_vector,
        limit=2,
        filters={"source": "test"}
    )
    
    # Verify results
    assert len(results) > 0
    assert all(isinstance(r, dict) for r in results)
    assert all("id" in r and "score" in r and "document" in r for r in results)

@pytest.mark.asyncio
async def test_invalid_vector_dimensions(weaviate_service, weaviate_config):
    """Test handling of invalid vector dimensions"""
    # Create collection
    await weaviate_service.create_collection(weaviate_config.settings.collection_name)
    
    # Test with invalid vector
    invalid_vector = [0.1] * (weaviate_config.settings.vector_size + 1)
    
    with pytest.raises(ValueError, match="Vector dimension mismatch"):
        await weaviate_service.search(query=invalid_vector)

@pytest.mark.asyncio
async def test_empty_points(weaviate_service, weaviate_config):
    """Test handling of empty points list"""
    # Create collection
    await weaviate_service.create_collection(weaviate_config.settings.collection_name)
    
    # Test with empty points
    with pytest.raises(ValueError, match="Points list cannot be empty"):
        await weaviate_service.upsert_points([])

@pytest.mark.asyncio
async def test_invalid_point_format(weaviate_service, weaviate_config):
    """Test handling of invalid point format"""
    # Create collection
    await weaviate_service.create_collection(weaviate_config.settings.collection_name)
    
    # Test with invalid point format
    invalid_points = [{"metadata": {"source": "test"}}]  # Missing 'text' field
    
    with pytest.raises(ValueError, match="must be a dictionary containing 'text' field"):
        await weaviate_service.upsert_points(invalid_points)
