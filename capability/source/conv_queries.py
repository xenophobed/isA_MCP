from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ConversationQuery:
    """Neo4j query with parameters"""
    query: str
    params: Dict[str, Any] = None

class ConversationQueries:
    """Conversation knowledge graph queries"""
    
    CREATE_FACT = ConversationQuery(
        query="""
        MERGE (f:Fact {fact_id: $fact_id})
        SET f.content = $content,
            f.conversation_id = $conv_id,
            f.timestamp = $timestamp
        RETURN f
        """
    )
    
    CREATE_ENTITY = ConversationQuery(
        query="""
        MERGE (e:Entity {entity_id: $entity_id})
        SET e.content = $content
        RETURN e
        """
    )
    
    CREATE_FACT_ENTITY_RELATION = ConversationQuery(
        query="""
        MATCH (f:Fact {fact_id: $fact_id})
        MATCH (e:Entity {entity_id: $entity_id})
        MERGE (f)-[r:MENTIONS]->(e)
        RETURN r
        """
    )
    
    CREATE_CONVERSATION_CONTEXT = ConversationQuery(
        query="""
        MERGE (c:Conversation {conversation_id: $conv_id})
        WITH c
        MATCH (f:Fact {conversation_id: $conv_id})
        MERGE (c)-[r:CONTAINS]->(f)
        RETURN c
        """
    )
    
    GET_FACT_ENTITIES = ConversationQuery(
        query="""
        MATCH (f:Fact {fact_id: $fact_id})-[:MENTIONS]->(e:Entity)
        RETURN collect(e.content) as entities
        """
    ) 