from .base import BaseQuery, QueryType
from typing import Dict

class EntityQueries:
    """Collection of entity-related queries"""

    CREATE_ENTITY = BaseQuery(
        name="create_entity",
        query="""
        MERGE (n:Entity {name: $name, user_id: $user_id})
        ON CREATE SET 
            n.created_at = datetime(),
            n.embedding = $embedding,
            n.type = $type
        ON MATCH SET 
            n.updated_at = datetime(),
            n.embedding = $embedding
        RETURN n
        """,
        query_type=QueryType.WRITE,
        parameters={
            "name": str,
            "user_id": str,
            "embedding": list,
            "type": str
        }
    )

    FIND_SIMILAR_ENTITIES = BaseQuery(
        name="find_similar_entities",
        query="""
        MATCH (n:Entity {user_id: $user_id})
        WHERE n.embedding IS NOT NULL
        WITH n, 
             $query_embedding AS qvec,
             [x IN n.embedding | toFloat(x)] AS nvec
        WHERE size(nvec) = $expected_dimension
        WITH n,
             gds.similarity.cosine(nvec, qvec) AS score
        WHERE score >= $threshold
        RETURN 
            n.name AS entity,
            n.type AS type,
            score
        ORDER BY score DESC
        LIMIT $limit
        """,
        query_type=QueryType.READ,
        cacheable=True,
        parameters={
            "user_id": str,
            "query_embedding": list,
            "expected_dimension": int,
            "threshold": float,
            "limit": int
        }
    )

    LINK_ENTITIES = BaseQuery(
        name="link_entities",
        query="""
        MATCH (source:Entity {name: $source_name, user_id: $user_id})
        MATCH (target:Entity {name: $target_name, user_id: $user_id})
        MERGE (source)-[r:$relationship_type]->(target)
        ON CREATE SET r.created_at = datetime()
        RETURN source.name as source, type(r) as relationship, target.name as target
        """,
        query_type=QueryType.WRITE,
        parameters={
            "source_name": str,
            "target_name": str,
            "user_id": str,
            "relationship_type": str
        }
    )

    CREATE_VECTOR_ENTITY = BaseQuery(
        name="create_vector_entity",
        query="""
        MERGE (n:Entity {name: $name, user_id: $user_id})
        ON CREATE SET 
            n.created_at = datetime(),
            n.embedding = $embedding,
            n.type = $type,
            n.vector_id = randomUUID()
        ON MATCH SET 
            n.updated_at = datetime(),
            n.embedding = $embedding
        RETURN n
        """,
        query_type=QueryType.WRITE,
        parameters={
            "name": str,
            "user_id": str,
            "embedding": list,
            "type": str
        }
    )

    VECTOR_SIMILARITY_SEARCH = BaseQuery(
        name="vector_similarity_search",
        query="""
        MATCH (n:Entity {user_id: $user_id})
        WHERE n.embedding IS NOT NULL
        WITH n, 
             $query_vector AS qvec,
             [x IN n.embedding | toFloat(x)] AS nvec
        WHERE size(nvec) = $dimension
        WITH n,
             gds.similarity.cosine(nvec, qvec) AS score
        WHERE score >= $threshold
        RETURN 
            n.name AS entity,
            n.type AS type,
            score,
            n.vector_id AS vector_id
        ORDER BY score DESC
        LIMIT $limit
        """,
        query_type=QueryType.READ,
        cacheable=True
    )

    @staticmethod
    def register_all(registry):
        """Register all entity queries"""
        registry.register_query(EntityQueries.CREATE_ENTITY)
        registry.register_query(EntityQueries.FIND_SIMILAR_ENTITIES)
        registry.register_query(EntityQueries.LINK_ENTITIES)
        registry.register_query(EntityQueries.CREATE_VECTOR_ENTITY)
        registry.register_query(EntityQueries.VECTOR_SIMILARITY_SEARCH)