import pytest
import pytest_asyncio
from app.kg.builder.neo4j_store import Neo4jStore
from datetime import datetime
from app.core.config import Settings
from typing import AsyncGenerator

@pytest_asyncio.fixture
async def neo4j_store() -> AsyncGenerator:
    """Fixture to create and clean up Neo4jStore instance"""
    store = Neo4jStore(
        uri=Settings.NEO4J_URI,
        username=Settings.NEO4J_USER,
        password=Settings.NEO4J_PASSWORD
    )
    
    # Initialize constraints
    await store.init_constraints()
    
    yield store
    
    # Clean up test data and close connection
    await store.clear_test_data()
    await store.close()

@pytest.mark.asyncio
async def test_store_and_get_entity(neo4j_store):
    """Test storing and retrieving an entity"""
    test_entity = {
        "type": "User",
        "id": "test_user_1",
        "properties": {
            "name": "Test User",
            "email": "test@example.com"
        },
        "metadata": {
            "created_at": datetime.now().isoformat()
        }
    }
    
    # Store the entity
    await neo4j_store.store_knowledge({"entities": [test_entity], "relations": []})
    
    # Retrieve the entity
    stored_entity = await neo4j_store.get_entity("test_user_1")
    
    assert stored_entity is not None
    assert stored_entity["id"] == test_entity["id"]
    assert stored_entity["name"] == test_entity["properties"]["name"]
    assert stored_entity["email"] == test_entity["properties"]["email"]

@pytest.mark.asyncio
async def test_store_and_get_relation(neo4j_store):
    """Test storing and retrieving relations between entities"""
    # Create test entities
    entities = [
        {
            "type": "User",
            "id": "test_user_2",
            "properties": {"name": "User 2"},
            "metadata": {}
        },
        {
            "type": "Product",
            "id": "test_product_1",
            "properties": {"name": "Product 1"},
            "metadata": {}
        }
    ]
    
    # Create test relation
    relation = {
        "type": "PURCHASED",
        "source_id": "test_user_2",
        "target_id": "test_product_1",
        "properties": {
            "purchase_date": "2024-01-01"
        },
        "metadata": {
            "confidence": 0.95
        }
    }
    
    # Store entities and relation
    await neo4j_store.store_knowledge({
        "entities": entities,
        "relations": [relation]
    })
    
    # Get relations for user
    relations = await neo4j_store.get_entity_relations("test_user_2")
    
    assert len(relations) == 1
    assert relations[0]["type"] == "PURCHASED"
    assert relations[0]["properties"]["purchase_date"] == "2024-01-01"
    assert relations[0]["properties"]["metadata"]["confidence"] == 0.95

@pytest.mark.asyncio
async def test_search_entities(neo4j_store):
    """Test searching entities by type and properties"""
    # Create test entities
    test_entities = [
        {
            "type": "Topic",
            "id": "test_topic_1",
            "properties": {
                "name": "Python",
                "category": "Programming"
            },
            "metadata": {}
        },
        {
            "type": "Topic",
            "id": "test_topic_2",
            "properties": {
                "name": "Java",
                "category": "Programming"
            },
            "metadata": {}
        }
    ]
    
    await neo4j_store.store_knowledge({"entities": test_entities, "relations": []})
    
    # Search by type
    topics = await neo4j_store.search_entities(entity_type="Topic")
    assert len(topics) == 2
    
    # Search by properties
    python_topics = await neo4j_store.search_entities(
        entity_type="Topic",
        properties={"name": "Python"}
    )
    assert len(python_topics) == 1
    assert python_topics[0]["name"] == "Python"

@pytest.mark.asyncio
async def test_delete_entity(neo4j_store):
    """Test deleting an entity and its relations"""
    # Create test entity
    test_entity = {
        "type": "User",
        "id": "test_user_3",
        "properties": {"name": "Test User 3"},
        "metadata": {}
    }
    
    await neo4j_store.store_knowledge({"entities": [test_entity], "relations": []})
    
    # Verify entity exists
    stored_entity = await neo4j_store.get_entity("test_user_3")
    assert stored_entity is not None
    
    # Delete entity
    await neo4j_store.delete_entity("test_user_3")
    
    # Verify entity is deleted
    deleted_entity = await neo4j_store.get_entity("test_user_3")
    assert deleted_entity is None

@pytest.mark.asyncio
async def test_clear_test_data(neo4j_store):
    """Test clearing all test data"""
    # Create test entities
    test_entities = [
        {
            "type": "User",
            "id": "test_user_4",
            "properties": {"name": "Test User 4"},
            "metadata": {}
        },
        {
            "type": "Product",
            "id": "test_product_2",
            "properties": {"name": "Test Product 2"},
            "metadata": {}
        }
    ]
    
    await neo4j_store.store_knowledge({"entities": test_entities, "relations": []})
    
    # Clear test data
    await neo4j_store.clear_test_data()
    
    # Verify all test entities are deleted
    for entity in test_entities:
        stored_entity = await neo4j_store.get_entity(entity["id"])
        assert stored_entity is None