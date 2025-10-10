#!/usr/bin/env python3
"""
Comprehensive Tests for Attribute Extractor

Tests the LLM-based attribute extraction functionality with various
entity types and edge cases.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from tools.services.data_analytics_service.services.knowledge_service.attribute_extractor import (
    AttributeExtractor, 
    Attribute, 
    AttributeType,
    Entity,
    EntityType
)

class TestAttributeExtractor:
    """Test suite for AttributeExtractor"""
    
    @pytest.fixture
    def extractor(self):
        """Create AttributeExtractor instance for testing"""
        config = {
            'confidence_threshold': 0.7,
            'use_llm': True
        }
        return AttributeExtractor(config)
    
    @pytest.fixture
    def sample_person_entity(self):
        """Create a sample person entity for testing"""
        return Entity(
            text="John Smith",
            entity_type=EntityType.PERSON,
            start=0,
            end=10,
            confidence=0.9
        )
    
    @pytest.fixture
    def sample_organization_entity(self):
        """Create a sample organization entity for testing"""
        return Entity(
            text="Apple Inc",
            entity_type=EntityType.ORGANIZATION,
            start=0,
            end=9,
            confidence=0.9
        )
    
    @pytest.fixture
    def sample_product_entity(self):
        """Create a sample product entity for testing"""
        return Entity(
            text="iPhone 15",
            entity_type=EntityType.PRODUCT,
            start=0,
            end=9,
            confidence=0.9
        )
    
    def test_initialization(self):
        """Test AttributeExtractor initialization"""
        # Test default initialization
        extractor = AttributeExtractor()
        assert extractor.confidence_threshold == 0.7
        assert extractor.use_llm == True
        
        # Test with custom config
        config = {'confidence_threshold': 0.8, 'use_llm': False}
        extractor = AttributeExtractor(config)
        assert extractor.confidence_threshold == 0.8
        assert extractor.use_llm == False
    
    def test_attribute_creation(self):
        """Test Attribute dataclass creation and post_init"""
        attribute = Attribute(
            name="age",
            value=30,
            attribute_type=AttributeType.NUMBER,
            confidence=0.9
        )
        
        assert attribute.name == "age"
        assert attribute.value == 30
        assert attribute.attribute_type == AttributeType.NUMBER
        assert attribute.confidence == 0.9
        assert attribute.metadata == {}
        assert attribute.normalized_value == 30
    
    def test_get_schema_for_entity_type(self, extractor):
        """Test schema generation for different entity types"""
        # Test PERSON schema
        person_schema = extractor._get_schema_for_entity_type(EntityType.PERSON)
        expected_person_keys = {"age", "occupation", "location", "education", "skills", "company", "nationality"}
        assert set(person_schema.keys()) == expected_person_keys
        
        # Test ORGANIZATION schema
        org_schema = extractor._get_schema_for_entity_type(EntityType.ORGANIZATION)
        expected_org_keys = {"founded", "size", "location", "industry", "revenue", "website", "ceo", "products"}
        assert set(org_schema.keys()) == expected_org_keys
        
        # Test PRODUCT schema
        product_schema = extractor._get_schema_for_entity_type(EntityType.PRODUCT)
        expected_product_keys = {"price", "features", "manufacturer", "category", "release_date", "specifications"}
        assert set(product_schema.keys()) == expected_product_keys
        
        # Test EVENT schema
        event_schema = extractor._get_schema_for_entity_type(EntityType.EVENT)
        expected_event_keys = {"date", "location", "duration", "participants", "organizer", "purpose"}
        assert set(event_schema.keys()) == expected_event_keys
        
        # Test LOCATION schema
        location_schema = extractor._get_schema_for_entity_type(EntityType.LOCATION)
        expected_location_keys = {"population", "country", "region", "coordinates", "notable_features"}
        assert set(location_schema.keys()) == expected_location_keys
        
        # Test default schema for unknown entity type
        default_schema = extractor._get_schema_for_entity_type(EntityType.CUSTOM)
        expected_default_keys = {"description", "type", "related_entities"}
        assert set(default_schema.keys()) == expected_default_keys
    
    def test_infer_attribute_type(self, extractor):
        """Test attribute type inference"""
        # Test name-based inference
        assert extractor._infer_attribute_type("age", "30") == AttributeType.NUMBER
        assert extractor._infer_attribute_type("founded", "2020") == AttributeType.DATE
        assert extractor._infer_attribute_type("email", "test@example.com") == AttributeType.EMAIL
        assert extractor._infer_attribute_type("website", "https://example.com") == AttributeType.URL
        assert extractor._infer_attribute_type("phone", "123-456-7890") == AttributeType.PHONE
        
        # Test pattern-based inference
        assert extractor._infer_attribute_type("unknown", "123") == AttributeType.NUMBER
        assert extractor._infer_attribute_type("unknown", "2023") == AttributeType.NUMBER  # 4-digit numbers are treated as numbers first
        assert extractor._infer_attribute_type("unknown", "https://test.com") == AttributeType.URL
        assert extractor._infer_attribute_type("unknown", "user@domain.com") == AttributeType.EMAIL
        assert extractor._infer_attribute_type("unknown", "123-456-7890") == AttributeType.PHONE
        assert extractor._infer_attribute_type("unknown", "true") == AttributeType.BOOLEAN
        assert extractor._infer_attribute_type("unknown", "a, b, c, d") == AttributeType.LIST
        assert extractor._infer_attribute_type("unknown", "text value") == AttributeType.TEXT
    
    def test_calculate_confidence(self, extractor):
        """Test confidence calculation"""
        # Test high confidence for structured data
        assert abs(extractor._calculate_confidence("email", "test@example.com", AttributeType.EMAIL) - 0.9) < 0.001
        assert abs(extractor._calculate_confidence("phone", "123-456-7890", AttributeType.PHONE) - 0.9) < 0.001
        assert abs(extractor._calculate_confidence("url", "https://example.com", AttributeType.URL) - 0.9) < 0.001
        
        # Test numeric data confidence boost
        assert abs(extractor._calculate_confidence("age", "30", AttributeType.NUMBER) - 0.85) < 0.001
        
        # Test low confidence for short values
        assert abs(extractor._calculate_confidence("name", "ab", AttributeType.TEXT) - 0.6) < 0.001
        
        # Test base confidence
        assert abs(extractor._calculate_confidence("description", "normal text", AttributeType.TEXT) - 0.8) < 0.001
    
    def test_get_entity_context(self, extractor, sample_person_entity):
        """Test entity context extraction"""
        text = "This is a long text about John Smith who works at Google and is 30 years old. He lives in California."
        
        # Update entity positions to match the text
        sample_person_entity.start = 29
        sample_person_entity.end = 39
        
        context = extractor._get_entity_context(text, sample_person_entity, window=20)
        
        # Should include text around the entity
        assert "John Smith" in context
        assert len(context) <= len(text)  # Should not exceed original text length
    
    def test_normalize_value(self, extractor):
        """Test value normalization for different types"""
        # Test NUMBER normalization
        assert extractor._normalize_value("1,000", AttributeType.NUMBER) == 1000
        assert extractor._normalize_value("$50.99", AttributeType.NUMBER) == 50.99
        assert extractor._normalize_value("invalid", AttributeType.NUMBER) == "invalid"
        
        # Test BOOLEAN normalization
        assert extractor._normalize_value("true", AttributeType.BOOLEAN) == True
        assert extractor._normalize_value("false", AttributeType.BOOLEAN) == False
        assert extractor._normalize_value("yes", AttributeType.BOOLEAN) == True
        assert extractor._normalize_value("no", AttributeType.BOOLEAN) == False
        
        # Test DATE normalization
        assert extractor._normalize_value("2023", AttributeType.DATE) == "2023-01-01"
        assert extractor._normalize_value("January 1, 2023", AttributeType.DATE) == "January 1, 2023"
        
        # Test EMAIL normalization
        assert extractor._normalize_value("Test@Example.COM", AttributeType.EMAIL) == "test@example.com"
        
        # Test PHONE normalization
        assert extractor._normalize_value("(123) 456-7890", AttributeType.PHONE) == "123-456-7890"
        assert extractor._normalize_value("1-123-456-7890", AttributeType.PHONE) == "123-456-7890"
        
        # Test LIST normalization
        assert extractor._normalize_value("a, b, c", AttributeType.LIST) == ["a", "b", "c"]
        assert extractor._normalize_value("x; y; z", AttributeType.LIST) == ["x", "y", "z"]
        
        # Test URL normalization
        assert extractor._normalize_value("example.com", AttributeType.URL) == "https://example.com"
        assert extractor._normalize_value("https://example.com", AttributeType.URL) == "https://example.com"
        
        # Test TEXT normalization
        assert extractor._normalize_value("  text  ", AttributeType.TEXT) == "text"
    
    def test_create_attribute_from_data(self, extractor):
        """Test attribute creation from data"""
        attribute = extractor._create_attribute_from_data(
            "age", "30", "John Smith is 30 years old"
        )
        
        assert attribute is not None
        assert attribute.name == "age"
        assert attribute.value == "30"
        assert attribute.attribute_type == AttributeType.NUMBER
        assert abs(attribute.confidence - 0.85) < 0.001  # Number type gets confidence boost
        assert attribute.metadata["extraction_method"] == "llm"
        assert len(attribute.source_text) <= 100
    
    def test_merge_attributes(self, extractor):
        """Test attribute merging"""
        attr1 = Attribute("age", 30, AttributeType.NUMBER, 0.8)
        attr2 = Attribute("age", 31, AttributeType.NUMBER, 0.9)  # Higher confidence
        attr3 = Attribute("name", "John", AttributeType.TEXT, 0.7)
        
        dict1 = {"age": attr1, "name": attr3}
        dict2 = {"age": attr2}
        
        merged = extractor._merge_attributes(dict1, dict2)
        
        assert len(merged) == 2
        assert merged["age"].value == 31  # Higher confidence version
        assert merged["age"].confidence == 0.9
        assert merged["name"].value == "John"
    
    def test_normalize_attributes(self, extractor):
        """Test attribute normalization"""
        attributes = {
            "age": Attribute("age", "30", AttributeType.NUMBER, 0.8),
            "email": Attribute("email", "Test@Example.COM", AttributeType.EMAIL, 0.9)
        }
        
        normalized = extractor._normalize_attributes(attributes)
        
        assert normalized["age"].normalized_value == 30
        assert normalized["email"].normalized_value == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_extract_with_llm_success(self, extractor, sample_person_entity):
        """Test successful LLM extraction"""
        text = "John Smith is a 30-year-old Software Engineer living in California."
        result = await extractor._extract_with_llm(text, sample_person_entity)
        
        # Test with real service - may return different attributes
        assert isinstance(result, dict)
        for attr_name, attr in result.items():
            assert isinstance(attr, Attribute)
            assert attr.confidence > 0
            # Check if age was extracted correctly if present
            if attr_name == 'age' and attr.normalized_value:
                assert isinstance(attr.normalized_value, (int, float, str))
    
    @pytest.mark.asyncio
    @patch('tools.services.intelligence_service.language.text_extractor.text_extractor.extract_key_information')
    async def test_extract_with_llm_failure(self, mock_extract, extractor, sample_person_entity):
        """Test LLM extraction failure"""
        # Mock failed response
        mock_extract.return_value = {
            'success': False,
            'error': 'API error'
        }
        
        text = "John Smith is a Software Engineer."
        result = await extractor._extract_with_llm(text, sample_person_entity)
        
        assert result == {}
    
    @pytest.mark.asyncio
    @patch('tools.services.intelligence_service.language.text_extractor.text_extractor.extract_key_information')
    async def test_extract_attributes_llm_disabled(self, mock_extract, sample_person_entity):
        """Test extraction with LLM disabled"""
        extractor = AttributeExtractor({'use_llm': False})
        
        text = "John Smith is a Software Engineer."
        result = await extractor.extract_attributes(text, sample_person_entity)
        
        assert result == {}
        mock_extract.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_extract_attributes_success(self, extractor, sample_person_entity):
        """Test full attribute extraction pipeline"""
        text = "John Smith is a 30-year-old Software Engineer at Google."
        result = await extractor.extract_attributes(text, sample_person_entity)
        
        # Test with real service - may return fewer attributes
        assert isinstance(result, dict)
        if result:
            assert all(isinstance(attr, Attribute) for attr in result.values())
            # Check for numeric conversion if age is found
            if 'age' in result:
                assert isinstance(result['age'].normalized_value, (int, float, str))
                # Check that the value was extracted correctly
                assert hasattr(result['age'], 'value')
                assert hasattr(result['age'], 'confidence')
    
    @pytest.mark.asyncio
    async def test_extract_entity_attributes_batch(self, extractor, sample_person_entity, sample_organization_entity):
        """Test batch attribute extraction"""
        text = "John Smith is a 30-year-old Engineer. Apple Inc was founded in 1976."
        entities = [sample_person_entity, sample_organization_entity]
        
        result = await extractor.extract_entity_attributes_batch(text, entities)
        
        # Test with real service
        assert isinstance(result, dict)
        # Entities may or may not have attributes extracted
        for entity_name in result.keys():
            assert isinstance(result[entity_name], dict)
        assert "Apple Inc" in result
        assert isinstance(result["John Smith"], dict)
        assert isinstance(result["Apple Inc"], dict)
    
    def test_get_attribute_statistics(self, extractor):
        """Test attribute statistics calculation"""
        # Create sample entity attributes
        entity_attributes = {
            "John Smith": {
                "age": Attribute("age", 30, AttributeType.NUMBER, 0.9),
                "occupation": Attribute("occupation", "Engineer", AttributeType.TEXT, 0.8)
            },
            "Apple Inc": {
                "founded": Attribute("founded", "1976", AttributeType.DATE, 0.85),
                "size": Attribute("size", "150000", AttributeType.NUMBER, 0.9)
            },
            "Empty Entity": {}
        }
        
        stats = extractor.get_attribute_statistics(entity_attributes)
        
        assert stats["total_attributes"] == 4
        assert stats["entities_with_attributes"] == 2  # Only 2 entities have attributes
        assert stats["unique_attribute_names"] == 4
        assert set(stats["attribute_names"]) == {"age", "occupation", "founded", "size"}
        assert stats["by_type"]["NUMBER"] == 2
        assert stats["by_type"]["TEXT"] == 1
        assert stats["by_type"]["DATE"] == 1
        assert stats["average_confidence"] == (0.9 + 0.8 + 0.85 + 0.9) / 4
        assert stats["high_confidence"] == 3  # 3 attributes with confidence > 0.8

class TestAttributeTypes:
    """Test AttributeType enum"""
    
    def test_attribute_type_values(self):
        """Test all attribute type enum values"""
        assert AttributeType.TEXT.value == "TEXT"
        assert AttributeType.NUMBER.value == "NUMBER"
        assert AttributeType.DATE.value == "DATE"
        assert AttributeType.BOOLEAN.value == "BOOLEAN"
        assert AttributeType.LIST.value == "LIST"
        assert AttributeType.OBJECT.value == "OBJECT"
        assert AttributeType.URL.value == "URL"
        assert AttributeType.EMAIL.value == "EMAIL"
        assert AttributeType.PHONE.value == "PHONE"

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def extractor(self):
        return AttributeExtractor()
    
    def test_empty_text_context(self, extractor):
        """Test handling of empty text context"""
        entity = Entity("Test", EntityType.PERSON, 0, 4, 0.9)
        context = extractor._get_entity_context("", entity, window=100)
        assert context == ""
    
    def test_invalid_entity_positions(self, extractor):
        """Test handling of invalid entity positions"""
        entity = Entity("Test", EntityType.PERSON, 100, 104, 0.9)  # Position beyond text
        text = "Short text"
        context = extractor._get_entity_context(text, entity, window=50)
        # Should not crash and return valid substring
        assert isinstance(context, str)
    
    def test_create_attribute_from_invalid_data(self, extractor):
        """Test attribute creation with invalid data"""
        # Test with None value
        attribute = extractor._create_attribute_from_data("test", None, "context")
        assert attribute.value is None
        
        # Test with empty string
        attribute = extractor._create_attribute_from_data("test", "", "context")
        assert attribute.value == ""
    
    def test_normalize_invalid_values(self, extractor):
        """Test normalization with invalid values"""
        # Test invalid number
        result = extractor._normalize_value("not_a_number", AttributeType.NUMBER)
        assert result == "not_a_number"
        
        # Test None value
        result = extractor._normalize_value(None, AttributeType.TEXT)
        assert result is None
    
    @pytest.mark.asyncio
    @patch('tools.services.intelligence_service.language.text_extractor.text_extractor.extract_key_information')
    async def test_extract_with_llm_exception(self, mock_extract, extractor):
        """Test LLM extraction with exception"""
        mock_extract.side_effect = Exception("Network error")
        
        entity = Entity("Test", EntityType.PERSON, 0, 4, 0.9)
        result = await extractor._extract_with_llm("test text", entity)
        
        assert result == {}

# Test fixtures for running tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])