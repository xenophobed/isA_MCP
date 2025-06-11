from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any

class CapabilityQueryService:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = AsyncGraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )
        
    async def get_capabilities_by_elements(self, elements: List[str]):
        """根据关键元素查找相关能力"""
        query = """
        MATCH (ke:KeyElement)
        WHERE ke.content IN $elements
        MATCH (c)-[:RELATES_TO]->(ke)
        WHERE c:KnowledgeSource OR c:Tool
        WITH c, collect(ke.content) as matched_elements,
             count(DISTINCT ke) as relevance_score
        WHERE c.status = 'active'
        RETURN c, matched_elements, relevance_score
        ORDER BY relevance_score DESC
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, elements=elements)
            return await result.data()
            
    async def get_capability_by_id(self, capability_id: str):
        """根据ID获取能力详情"""
        query = """
        MATCH (c {capability_id: $capability_id})
        WHERE c:KnowledgeSource OR c:Tool
        OPTIONAL MATCH (c)-[:RELATES_TO]->(ke:KeyElement)
        OPTIONAL MATCH (c)-[:HAS_EXAMPLE]->(e)
        RETURN c, collect(DISTINCT ke.content) as elements,
               collect(DISTINCT e.content) as examples
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, capability_id=capability_id)
            return await result.single() 