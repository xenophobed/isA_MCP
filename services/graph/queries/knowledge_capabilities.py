from .base import BaseQuery, QueryType

class KnowledgeCapabilitiesQueries:
    CREATE_KNOWLEDGE_CAPABILITY = BaseQuery(
        name="create_knowledge_capability",
        query="""
        MERGE (k:KnowledgeCapability {capability_id: $capability_id})
        ON CREATE SET
            k.metadata = $metadata,
            k.semantic_vector = $semantic_vector,
            k.functional_vector = $functional_vector,
            k.contextual_vector = $contextual_vector
        ON MATCH SET
            k.metadata = $metadata,
            k.semantic_vector = $semantic_vector,
            k.functional_vector = $functional_vector,
            k.contextual_vector = $contextual_vector
        RETURN k.capability_id as capability_id
        """,
        query_type=QueryType.WRITE
    )
    
    CREATE_KNOWLEDGE_CHUNK = BaseQuery(
        name="create_knowledge_chunk",
        query="""
        MATCH (k:KnowledgeCapability {capability_id: $capability_id})
        CREATE (c:ContentChunk {
            chunk_id: $chunk_id,
            text: $text,
            metadata: $metadata,
            vector: $vector
        })
        CREATE (k)-[:HAS_CHUNK]->(c)
        RETURN c.chunk_id as chunk_id
        """,
        query_type=QueryType.WRITE
    )
    
    SEARCH_KNOWLEDGE = BaseQuery(
        name="search_knowledge",
        query="""
        MATCH (k:KnowledgeCapability)
        WITH k,
            CASE 
                WHEN k.semantic_vector IS NOT NULL 
                THEN gds.similarity.cosine($query_vector, k.semantic_vector) * $weights.semantic
                ELSE 0
            END +
            CASE 
                WHEN k.functional_vector IS NOT NULL 
                THEN gds.similarity.cosine($query_vector, k.functional_vector) * $weights.functional
                ELSE 0
            END +
            CASE 
                WHEN k.contextual_vector IS NOT NULL 
                THEN gds.similarity.cosine($query_vector, k.contextual_vector) * $weights.contextual
                ELSE 0
            END AS score
        WHERE score >= $threshold
        RETURN k.capability_id as capability_id,
               k.metadata as metadata,
               score
        ORDER BY score DESC
        LIMIT $limit
        """,
        query_type=QueryType.READ
    )
    
    SEARCH_CHUNKS = BaseQuery(
        name="search_chunks",
        query="""
        MATCH (k:KnowledgeCapability)-[:HAS_CHUNK]->(c:ContentChunk)
        WHERE k.id = $capability_id
        WITH c, gds.similarity.cosine($query_vector, c.vector) as score
        WHERE score >= $threshold
        RETURN c.id as chunk_id,
               c.text as text,
               score
        ORDER BY score DESC
        LIMIT $limit
        """,
        query_type=QueryType.READ
    ) 