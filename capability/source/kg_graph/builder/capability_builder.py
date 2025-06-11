from typing import List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from neo4j import AsyncGraphDatabase
import json

class SystemCapability(BaseModel):
    """系统能力的基础模型"""
    capability_id: str
    name: str
    type: str
    description: str
    last_updated: datetime
    status: str = "active"  # active, deprecated, testing
    graph_source: str  # 添加图源信息，对应search_graph中的节点名称

class KnowledgeSource(SystemCapability):
    """知识源能力"""
    source_type: str  # vectorstore, database, api
    content_types: List[str]  # text, pdf, webpage, etc
    update_frequency: str  # realtime, daily, weekly, static
    key_elements: List[str]  # 关键元素标签
    example_queries: List[str]
    node_name: str  # search_graph中对应的节点名称

class ToolCapability(SystemCapability):
    """工具能力"""
    api_endpoint: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    rate_limits: Dict[str, Any]
    key_elements: List[str]  # 工具相关的关键元素
    example_uses: List[str]
    node_name: str  # search_graph中对应的节点名称

class SystemCapabilityBuilder:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = AsyncGraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )

    async def register_knowledge_source(self, source: KnowledgeSource):
        """注册新的知识源"""
        query = """
        MERGE (ks:KnowledgeSource {capability_id: $capability_id})
        SET ks.name = $name,
            ks.type = $type,
            ks.description = $description,
            ks.last_updated = $last_updated,
            ks.status = $status,
            ks.source_type = $source_type,
            ks.content_types = $content_types,
            ks.update_frequency = $update_frequency,
            ks.node_name = $node_name,
            ks.graph_source = $graph_source
        
        WITH ks
        
        // 创建或更新关键元素节点并建立关联
        UNWIND $key_elements as element
        MERGE (ke:KeyElement {content: element})
        MERGE (ks)-[:RELATES_TO]->(ke)
        
        // 存储示例查询
        WITH ks
        UNWIND $example_queries as query
        MERGE (eq:ExampleQuery {content: query})
        MERGE (ks)-[:HAS_EXAMPLE]->(eq)
        """
        
        async with self.driver.session() as session:
            await session.run(
                query,
                capability_id=source.capability_id,
                name=source.name,
                type=source.type,
                description=source.description,
                last_updated=source.last_updated.isoformat(),
                status=source.status,
                source_type=source.source_type,
                content_types=source.content_types,
                update_frequency=source.update_frequency,
                key_elements=source.key_elements,
                example_queries=source.example_queries,
                node_name=source.node_name,
                graph_source=source.graph_source
            )

    async def register_tool(self, tool: ToolCapability):
        """注册新的工具能力"""
        query = """
        MERGE (t:Tool {capability_id: $capability_id})
        SET t.name = $name,
            t.type = $type,
            t.description = $description,
            t.last_updated = $last_updated,
            t.status = $status,
            t.api_endpoint = $api_endpoint,
            t.input_schema = $input_schema,
            t.output_schema = $output_schema,
            t.rate_limits = $rate_limits,
            t.node_name = $node_name,
            t.graph_source = $graph_source
        
        WITH t
        
        // 创建或更新关键元素节点并建立关联
        UNWIND $key_elements as element
        MERGE (ke:KeyElement {content: element})
        MERGE (t)-[:RELATES_TO]->(ke)
        
        // 存储示例用法
        WITH t
        UNWIND $example_uses as example
        MERGE (eu:ExampleUse {content: example})
        MERGE (t)-[:HAS_EXAMPLE]->(eu)
        """
        
        async with self.driver.session() as session:
            await session.run(
                query,
                capability_id=tool.capability_id,
                name=tool.name,
                type=tool.type,
                description=tool.description,
                last_updated=tool.last_updated.isoformat(),
                status=tool.status,
                api_endpoint=tool.api_endpoint,
                input_schema=json.dumps(tool.input_schema),
                output_schema=json.dumps(tool.output_schema),
                rate_limits=json.dumps(tool.rate_limits),
                key_elements=tool.key_elements,
                example_uses=tool.example_uses,
                node_name=tool.node_name,
                graph_source=tool.graph_source
            )

    async def update_capability_status(self, capability_id: str, new_status: str):
        """更新能力状态"""
        query = """
        MATCH (c {capability_id: $capability_id})
        WHERE c:KnowledgeSource OR c:Tool
        SET c.status = $new_status,
            c.last_updated = $timestamp
        """
        
        async with self.driver.session() as session:
            await session.run(
                query,
                capability_id=capability_id,
                new_status=new_status,
                timestamp=datetime.now().isoformat()
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