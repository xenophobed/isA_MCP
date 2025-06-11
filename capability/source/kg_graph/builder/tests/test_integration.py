import pytest
from datetime import datetime
from app.services.graphs.kg_graph.builder.builder import KnowledgeBuilder
from app.services.graphs.kg_graph.builder.neo4j_store import Neo4jStore

class TestKnowledgeGraphIntegration:
    @pytest.fixture
    async def builder(self):
        """初始化KnowledgeBuilder"""
        builder = KnowledgeBuilder()
        await builder.initialize(
            mongodb_host="localhost",
            mongodb_port=27017,
            mongodb_db="test_db",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="admin@123"
        )
        try:
            yield builder
        finally:
            await builder.close()
    
    @pytest.fixture
    def sample_messages(self):
        """测试用的对话消息"""
        return [
            {
                "conversation_id": "test_conv_1",
                "sender": {"user_id": "user_1", "type": "customer"},
                "content": "我想了解一下你们的AI助手产品",
                "timestamp": datetime.now(),
                "message_id": "msg_1"
            },
            {
                "conversation_id": "test_conv_1",
                "sender": {"user_id": "agent_1", "type": "agent"},
                "content": "我们的AI助手提供智能对话、知识管理等功能，基础版每年5万起",
                "timestamp": datetime.now(),
                "message_id": "msg_2"
            }
        ]

    @pytest.mark.asyncio
    async def test_full_extraction_process(self, builder, sample_messages):
        """测试完整的提取过程"""
        try:
            # 获取初始化后的builder
            builder_instance = await builder
            
            # 1. 提取知识
            extracted_data = await builder_instance.extractor.process_conversation(sample_messages)
            
            # 验证提取的数据结构
            assert "atomic_facts" in extracted_data
            assert len(extracted_data["atomic_facts"]) > 0
            
            # 验证原子事实的结构
            for fact in extracted_data["atomic_facts"]:
                assert "atomic_fact" in fact
                assert "key_elements" in fact
                assert len(fact["key_elements"]) > 0
                
            # 2. 存储到Neo4j
            await builder_instance.neo4j_store.store_atomic_facts(
                "test_conv_1",
                extracted_data["atomic_facts"]
            )
            
            # 3. 验证存储结果
            conversation = await builder_instance.neo4j_store.get_entity("test_conv_1")
            assert conversation is not None
            
            facts = await builder_instance.neo4j_store.search_entities("AtomicFact")
            assert len(facts) > 0
            
            elements = await builder_instance.neo4j_store.search_entities("KeyElement")
            assert len(elements) > 0
            
        finally:
            # 清理测试数据
            await (await builder).neo4j_store.clear_test_data()
            await (await builder).close()

    @pytest.mark.asyncio
    async def test_knowledge_quality(self, builder, sample_messages):
        """测试知识提取的质量"""
        extracted_data = await builder.extractor.process_conversation(sample_messages)
        
        # 验证是否提取了产品信息
        product_found = False
        price_found = False
        
        for fact in extracted_data["atomic_facts"]:
            if "AI助手" in fact["atomic_fact"]:
                product_found = True
            if "5万" in fact["atomic_fact"]:
                price_found = True
                
        assert product_found, "未能提取产品信息"
        assert price_found, "未能提取价格信息" 