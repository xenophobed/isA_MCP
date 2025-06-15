from dataclasses import dataclass

@dataclass
class ConversationQueries:
    """Neo4j queries for conversation knowledge management"""
    
    CREATE_ENTITY = """
    MERGE (e:Entity {entity_id: $entity_id})
    SET e.content = $content,
        e.vector = $vector
    RETURN e
    """
    
    CREATE_FACT = """
    MERGE (f:Fact {fact_id: $fact_id})
    SET f.content = $content,
        f.confidence = $confidence,
        f.timestamp = $timestamp,
        f.vector = $vector
    RETURN f
    """
    
    CREATE_FACT_ENTITY_RELATION = """
    MATCH (f:Fact {fact_id: $fact_id})
    MATCH (e:Entity {entity_id: $entity_id})
    MERGE (f)-[r:MENTIONS]->(e)
    SET r.confidence = $confidence
    RETURN r
    """
    
    GET_SIMILAR_FACTS = """
    MATCH (f1:Fact {fact_id: $fact_id})
    MATCH (f2:Fact)
    WHERE f1 <> f2
    MATCH (f1)-[:MENTIONS]->(e)<-[:MENTIONS]-(f2)
    WITH f2, count(e) as common_entities, f2.confidence as confidence
    RETURN f2, common_entities, confidence
    ORDER BY common_entities DESC
    LIMIT $limit
    """
    
    UPDATE_FACT_CONFIDENCE = """
    MATCH (f:Fact {fact_id: $fact_id})
    SET f.confidence = $confidence,
        f.last_updated = $metadata
    RETURN f
    """
    
    SEARCH_SIMILAR_ENTITIES = """
    MATCH (e:Entity)
    WHERE gds.similarity.cosine(e.vector, $query_vector) > $min_similarity
    RETURN e.content as content,
           e.entity_id as entity_id,
           gds.similarity.cosine(e.vector, $query_vector) as similarity
    ORDER BY similarity DESC
    LIMIT $limit
    """
    
    SEARCH_SIMILAR_FACTS = """
    MATCH (f:Fact)
    WHERE f.vector IS NOT NULL
    WITH f, gds.similarity.cosine($query_vector, f.vector) AS similarity
    WHERE similarity > $min_similarity
    RETURN {
        score: similarity,
        payload: {
            content: f.content,
            confidence: f.confidence,
            timestamp: f.timestamp
        },
        entities: [(f)-[:MENTIONS]->(e) | e.content]
    } AS result
    ORDER BY similarity DESC
    LIMIT $limit
    """

    SEARCH_SIMILAR_FACTS_FALLBACK = """
    MATCH (f:Fact)
    WHERE f.vector IS NOT NULL
    WITH f, 
         $query_vector AS qvec,
         [x IN f.vector | toFloat(x)] AS fvec
    WHERE size(fvec) = size(qvec)
    WITH f,
         reduce(dot = 0.0, i IN range(0, size(fvec)-1) | 
             dot + fvec[i] * qvec[i]
         ) / (
             sqrt(reduce(norm1 = 0.0, i IN range(0, size(fvec)-1) | 
                 norm1 + fvec[i] * fvec[i]
             )) * 
             sqrt(reduce(norm2 = 0.0, i IN range(0, size(qvec)-1) | 
                 norm2 + qvec[i] * qvec[i]
             ))
         ) AS similarity
    WHERE similarity > $min_similarity
    RETURN {
        score: similarity,
        payload: {
            content: f.content,
            confidence: f.confidence,
            timestamp: f.timestamp
        },
        entities: [(f)-[:MENTIONS]->(e) | e.content]
    } AS result
    ORDER BY similarity DESC
    LIMIT $limit
    """
