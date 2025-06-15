# app/kg/builder/tests/test_transformer.py
import pytest
from datetime import datetime, UTC
from ..transformers import KnowledgeTransformer, EntityNode, RelationShip

class TestKnowledgeTransformer:
    @pytest.fixture
    def transformer(self):
        return KnowledgeTransformer()
        
    @pytest.fixture
    def sample_knowledge(self):
        """提供一个典型的知识提取结果样本"""
        return {
            "entities": [
                {
                    "id": "u1",
                    "type": "User",
                    "properties": {
                        "name": "用户A",
                        "features": ["关注价格", "对产品感兴趣"]
                    },
                    "metadata": {
                        "timestamp": datetime.now(UTC),
                        "source": "conversation"
                    }
                },
                {
                    "id": "c1",
                    "type": "Conversation",
                    "properties": {
                        "topic": "产品咨询",
                        "status": "completed"
                    },
                    "metadata": {
                        "timestamp": datetime.now(UTC),
                        "source": "conversation"
                    }
                },
                {
                    "id": "i1",
                    "type": "Intent",
                    "properties": {
                        "type": "产品咨询",
                        "priority": "medium"
                    },
                    "metadata": {
                        "timestamp": datetime.now(UTC),
                        "source": "conversation"
                    }
                }
            ],
            "relations": [
                {
                    "source_id": "u1",
                    "target_id": "c1",
                    "type": "HAS_CONVERSATION",
                    "properties": {
                        "timestamp": datetime.now(UTC)
                    },
                    "metadata": {
                        "confidence": 0.9
                    }
                },
                {
                    "source_id": "c1",
                    "target_id": "i1", 
                    "type": "HAS_INTENT",
                    "properties": {
                        "timestamp": datetime.now(UTC)
                    },
                    "metadata": {
                        "confidence": 0.8
                    }
                }
            ]
        }

    def test_transform_entities(self, transformer, sample_knowledge):
        """测试实体转换"""
        result = transformer.transform_extracted_knowledge(sample_knowledge)
        
        # 验证基本结构
        assert "entities" in result
        assert "relations" in result
        
        # 验证实体转换
        entities = result["entities"]
        assert len(entities) == 3
        
        # 验证具体实体
        user_entity = next(e for e in entities if e["type"] == "User")
        assert user_entity["properties"]["name"] == "用户A"
        assert "features" in user_entity["properties"]
        assert "metadata" in user_entity
        
        # 验证实体缓存
        assert len(transformer.entity_cache) == 3
        assert "u1" in transformer.entity_cache

    def test_transform_relations(self, transformer, sample_knowledge):
        """测试关系转换"""
        result = transformer.transform_extracted_knowledge(sample_knowledge)
        relations = result["relations"]
        
        # 验证关系数量
        assert len(relations) == 2
        
        # 验证具体关系
        conv_relation = next(r for r in relations if r["type"] == "HAS_CONVERSATION")
        assert conv_relation["source_id"] == "u1"
        assert conv_relation["target_id"] == "c1"
        assert "properties" in conv_relation
        assert "metadata" in conv_relation

    def test_invalid_entity_type(self, transformer):
        """测试无效实体类型处理"""
        invalid_knowledge = {
            "entities": [
                {
                    "id": "x1",
                    "type": "InvalidType",
                    "properties": {},
                    "metadata": {}
                }
            ],
            "relations": []
        }
        
        result = transformer.transform_extracted_knowledge(invalid_knowledge)
        assert len(result["entities"]) == 0

    def test_invalid_relation(self, transformer):
        """测试无效关系处理"""
        invalid_knowledge = {
            "entities": [
                {
                    "id": "u1",
                    "type": "User",
                    "properties": {},
                    "metadata": {}
                }
            ],
            "relations": [
                {
                    "source_id": "u1",
                    "target_id": "non_existent",
                    "type": "HAS_CONVERSATION",
                    "properties": {},
                    "metadata": {}
                }
            ]
        }
        
        result = transformer.transform_extracted_knowledge(invalid_knowledge)
        assert len(result["relations"]) == 0

    def test_entity_update(self, transformer):
        """测试实体更新"""
        # 第一次添加实体
        initial_knowledge = {
            "entities": [
                {
                    "id": "u1",
                    "type": "User",
                    "properties": {"name": "用户A"},
                    "metadata": {}
                }
            ],
            "relations": []
        }
        
        transformer.transform_extracted_knowledge(initial_knowledge)
        
        # 更新实体
        updated_knowledge = {
            "entities": [
                {
                    "id": "u1",
                    "type": "User",
                    "properties": {"age": "30"},
                    "metadata": {}
                }
            ],
            "relations": []
        }
        
        result = transformer.transform_extracted_knowledge(updated_knowledge)
        updated_entity = next(e for e in result["entities"] if e["id"] == "u1")
        
        # 验证属性合并
        assert "name" in updated_entity["properties"]
        assert "age" in updated_entity["properties"]
        
    def test_error_handling(self, transformer):
        """测试错误处理"""
        invalid_knowledge = {
            "entities": None,
            "relations": None
        }
        
        result = transformer.transform_extracted_knowledge(invalid_knowledge)
        assert "entities" in result
        assert "relations" in result
        assert len(result["entities"]) == 0
        assert len(result["relations"]) == 0
        
    @pytest.mark.asyncio
    async def test_batch_transform(self, transformer):
        """测试批量转换"""
        batch_knowledge = [
            {
                "entities": [
                    {
                        "id": f"u{i}",
                        "type": "User",
                        "properties": {"name": f"用户{i}"},
                        "metadata": {}
                    }
                ],
                "relations": []
            }
            for i in range(3)
        ]
        
        results = [
            transformer.transform_extracted_knowledge(k)
            for k in batch_knowledge
        ]
        
        # 验证批量处理结果
        assert len(results) == 3
        assert len(transformer.entity_cache) == 3
        
        # 验证每个结果
        for i, result in enumerate(results):
            assert len(result["entities"]) == 1
            assert result["entities"][0]["properties"]["name"] == f"用户{i}"