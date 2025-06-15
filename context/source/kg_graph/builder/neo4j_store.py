from typing import Dict, List, Optional, Any
from neo4j import AsyncGraphDatabase
from datetime import datetime
import logging
import os
import hashlib

from app.config.config_manager import config_manager

config_manager.set_log_level("INFO")
logger = config_manager.get_logger(__name__)

def encode_md5(text: str) -> str:
    """Generate MD5 hash for text"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()

class Neo4jStore:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "admin@123")
        self.driver = AsyncGraphDatabase.driver(uri, auth=(username, password))
        
    async def init_constraints(self):
        """初始化数据库约束"""
        async with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:User) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Conversation) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Intent) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Product) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Topic) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:AtomicFact) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:KeyElement) REQUIRE n.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                await session.run(constraint)

    async def close(self):
        await self.driver.close()
        
    async def clear_test_data(self):
        """清理测试数据"""
        async with self.driver.session() as session:
            # 清理所有以test_开头的实体和它们的关系
            await session.run("""
                MATCH (n)
                WHERE n.id STARTS WITH 'test_'
                DETACH DELETE n
            """)
                
    async def store_knowledge(self, knowledge: Dict):
        """存储转换后的知识到Neo4j"""
        try:
            async with self.driver.session() as session:
                # 1. 存储实体
                for entity in knowledge.get("entities", []):
                    await self._create_or_update_entity(session, entity)
                
                # 2. 存储关系
                for relation in knowledge.get("relations", []):
                    await self._create_relation(session, relation)
                    
        except Exception as e:
            logger.error(f"Error storing knowledge: {str(e)}")
            raise

    async def _create_or_update_entity(self, session, entity: Dict):
        """创建或更新实体节点"""
        query = """
        MERGE (n:{label} {{id: $id}})
        SET n += $properties
        SET n.last_updated = datetime()
        """.format(label=entity["type"])
        
        # 将所有metadata的键值展平存储
        properties = {
            "id": entity["id"],
            **entity["properties"]
        }
        # 处理metadata，将其键值平铺到properties中，添加meta_前缀
        for key, value in entity["metadata"].items():
            if isinstance(value, (str, int, float, bool)) or (isinstance(value, list) and all(isinstance(x, (str, int, float, bool)) for x in value)):
                properties[f"meta_{key}"] = value
        
        await session.run(query, {"id": entity["id"], "properties": properties})

    async def _create_relation(self, session, relation: Dict):
        """创建关系"""
        query = """
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r += $properties
        SET r.last_updated = datetime()
        """.format(rel_type=relation["type"])
        
        # 将所有metadata的键值展平存储
        properties = {
            **relation["properties"]
        }
        # 处理metadata，将其键值平铺到properties中，添加meta_前缀
        for key, value in relation["metadata"].items():
            if isinstance(value, (str, int, float, bool)) or (isinstance(value, list) and all(isinstance(x, (str, int, float, bool)) for x in value)):
                properties[f"meta_{key}"] = value
        
        await session.run(
            query,
            {
                "source_id": relation["source_id"],
                "target_id": relation["target_id"],
                "properties": properties
            }
        )

    async def get_entity(self, entity_id: str) -> Optional[Dict]:
        """获取实体详情"""
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (n {id: $id}) RETURN n",
                {"id": entity_id}
            )
            record = await result.single()
            return record.value("n") if record else None

    async def get_entity_relations(self, entity_id: str) -> List[Dict]:
        """获取实体的所有关系"""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (n {id: $id})-[r]->(m)
                RETURN type(r) as type, r as properties, m.id as target_id, null as source_id
                UNION
                MATCH (m)-[r]->(n {id: $id})
                RETURN type(r) as type, r as properties, null as target_id, m.id as source_id
            """, {"id": entity_id})
            
            # 处理结果，重建metadata结构
            relations = []
            async for record in result:
                relation = dict(record)
                properties = dict(relation["properties"])
                
                # 重建metadata结构
                metadata = {}
                props_to_delete = []
                for key, value in properties.items():
                    if key.startswith('meta_'):
                        real_key = key[5:]  # 移除'meta_'前缀
                        metadata[real_key] = value
                        props_to_delete.append(key)
                
                # 从properties中删除meta_前缀的属性
                for key in props_to_delete:
                    properties.pop(key)
                    
                # 重新设置properties，包含重建的metadata
                relation["properties"] = {
                    key: value 
                    for key, value in properties.items() 
                    if key not in ('id', 'last_updated')
                }
                relation["properties"]["metadata"] = metadata
                
                # 处理source_id和target_id
                if relation["source_id"] is not None:
                    relation.pop("target_id")
                else:
                    relation.pop("source_id")
                    
                relations.append(relation)
                
            return relations

    async def search_entities(self, 
                            entity_type: Optional[str] = None,
                            properties: Optional[Dict] = None) -> List[Dict]:
        """搜索实体"""
        async with self.driver.session() as session:
            conditions = []
            params = {}
            
            if entity_type:
                label_clause = f":{entity_type}"
            else:
                label_clause = ""
                
            if properties:
                for key, value in properties.items():
                    conditions.append(f"n.{key} = ${key}")
                    params[key] = value
                    
            where_clause = " AND ".join(conditions)
            if where_clause:
                where_clause = f"WHERE {where_clause}"
                
            query = f"""
            MATCH (n{label_clause})
            {where_clause}
            RETURN n
            """
            
            result = await session.run(query, params)
            return [dict(record.value("n")) async for record in result]

    async def delete_entity(self, entity_id: str):
        """删除实体及其关系"""
        async with self.driver.session() as session:
            await session.run(
                "MATCH (n {id: $id}) DETACH DELETE n",
                {"id": entity_id}
            )

    async def import_conversation_knowledge(self, conversation_id: str, extraction_data: Dict):
        """导入会话知识"""
        query = """
        MERGE (c:Conversation {id: $conversation_id})
        WITH c
        UNWIND $atomic_facts AS af
        MERGE (a:AtomicFact {id: af.id})
        SET a.text = af.atomic_fact
        MERGE (c)-[:HAS_ATOMIC_FACT]->(a)
        WITH c, a, af
        UNWIND af.key_elements AS ke
        MERGE (k:KeyElement {id: ke})
        MERGE (a)-[:HAS_KEY_ELEMENT]->(k)
        """
        
        async with self.driver.session() as session:
            await session.run(
                query,
                {
                    "conversation_id": conversation_id,
                    "atomic_facts": extraction_data["atomic_facts"]
                }
            )

    async def store_atomic_facts(self, conversation_id: str, atomic_facts: List[Dict]):
        """存储原子事实和关键元素"""
        try:
            async with self.driver.session() as session:
                query = """
                // 1. 创建会话节点
                MERGE (c:Conversation {id: $conversation_id})
                
                WITH c
                UNWIND $atomic_facts as fact
                
                // 2. 创建原子事实节点
                MERGE (af:AtomicFact {id: fact.id})
                SET af.content = fact.atomic_fact,
                    af.created_at = datetime()
                
                // 3. 创建会话到原子事实的关系
                MERGE (c)-[r:HAS_ATOMIC_FACT]->(af)
                
                WITH af, fact
                UNWIND fact.key_elements as element
                
                // 4. 创建关键元素节点
                MERGE (ke:KeyElement {id: element})
                SET ke.content = element
                
                // 5. 创建原子事实到关键元素的关系
                MERGE (af)-[r2:HAS_KEY_ELEMENT]->(ke)
                """
                
                await session.run(
                    query,
                    {
                        "conversation_id": conversation_id,
                        "atomic_facts": [
                            {
                                "id": encode_md5(af["atomic_fact"]),
                                "atomic_fact": af["atomic_fact"],
                                "key_elements": af["key_elements"]
                            }
                            for af in atomic_facts
                        ]
                    }
                )
                
        except Exception as e:
            logger.error(f"Error storing atomic facts: {str(e)}")
            raise