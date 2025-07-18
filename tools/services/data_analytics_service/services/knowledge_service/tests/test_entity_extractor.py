#!/usr/bin/env python3
"""
Comprehensive Tests for Entity Extractor Service

Tests the simplified entity extractor that uses intelligence service for AI-powered extraction.
"""

import pytest
import asyncio
from typing import List

from tools.services.data_analytics_service.services.knowledge_service.entity_extractor import (
    EntityExtractor, 
    Entity, 
    EntityType
)

@pytest.fixture
def entity_extractor():
    """Create EntityExtractor instance for testing"""
    return EntityExtractor()

@pytest.fixture
def sample_texts():
    """Sample texts for testing"""
    return {
        "corporate": "Apple Inc. was founded in 1976 by Steve Jobs in Cupertino, California. The company developed the iPhone and generated $365 billion in revenue.",
        "academic": "Dr. Sarah Johnson from MIT published a paper on machine learning at the ICML 2024 conference in Vienna, Austria.",
        "financial": "Goldman Sachs reported $12.3 billion in quarterly earnings on October 15, 2024, exceeding analyst expectations.",
        "simple": "John Smith works at Google in Mountain View.",
        "empty": "",
        "no_entities": "This text contains no recognizable named entities just random words and numbers.",
        "mixed": "The COVID-19 pandemic started in Wuhan, China in December 2019. WHO declared it a global health emergency on January 30, 2020."
    }

class TestEntityExtractorInitialization:
    """Test entity extractor initialization"""
    
    def test_default_initialization(self):
        """Test extractor initializes with default config"""
        extractor = EntityExtractor()
        assert extractor.confidence_threshold == 0.7
        assert extractor.use_llm == True
    
    def test_custom_config_initialization(self):
        """Test extractor initializes with custom config"""
        config = {
            'confidence_threshold': 0.8,
            'use_llm': False
        }
        extractor = EntityExtractor(config)
        assert extractor.confidence_threshold == 0.8
        assert extractor.use_llm == False

class TestEntityExtraction:
    """Test entity extraction functionality"""
    
    @pytest.mark.asyncio
    async def test_corporate_text_extraction(self, entity_extractor, sample_texts):
        """Test extraction from corporate text"""
        entities = await entity_extractor.extract_entities(sample_texts["corporate"])
        
        # Should extract multiple entities
        assert len(entities) >= 4
        
        # Check for expected entity types
        entity_types = [e.entity_type for e in entities]
        assert EntityType.ORGANIZATION in entity_types  # Apple Inc.
        assert EntityType.PERSON in entity_types       # Steve Jobs
        assert EntityType.LOCATION in entity_types     # Cupertino, California
        assert EntityType.DATE in entity_types         # 1976
        
        # Check confidence scores
        for entity in entities:
            assert 0.0 <= entity.confidence <= 1.0
            assert entity.confidence >= entity_extractor.confidence_threshold
    
    @pytest.mark.asyncio
    async def test_academic_text_extraction(self, entity_extractor, sample_texts):
        """Test extraction from academic text"""
        entities = await entity_extractor.extract_entities(sample_texts["academic"])
        
        # Should extract academic entities
        assert len(entities) >= 3
        
        # Look for specific entities
        entity_texts = [e.text.lower() for e in entities]
        
        # Should find person, organization, location, event
        found_person = any("sarah" in text or "johnson" in text for text in entity_texts)
        found_org = any("mit" in text for text in entity_texts)
        found_location = any("vienna" in text or "austria" in text for text in entity_texts)
        
        assert found_person or found_org or found_location
    
    @pytest.mark.asyncio
    async def test_financial_text_extraction(self, entity_extractor, sample_texts):
        """Test extraction from financial text"""
        entities = await entity_extractor.extract_entities(sample_texts["financial"])
        
        # Should extract financial entities
        assert len(entities) >= 3
        
        # Check for expected types
        entity_types = [e.entity_type for e in entities]
        assert EntityType.ORGANIZATION in entity_types  # Goldman Sachs
        assert EntityType.MONEY in entity_types         # $12.3 billion
        assert EntityType.DATE in entity_types          # October 15, 2024
    
    @pytest.mark.asyncio
    async def test_simple_text_extraction(self, entity_extractor, sample_texts):
        """Test extraction from simple text"""
        entities = await entity_extractor.extract_entities(sample_texts["simple"])
        
        # Should extract basic entities
        assert len(entities) >= 2
        
        # Check for person and organization
        entity_types = [e.entity_type for e in entities]
        assert EntityType.PERSON in entity_types        # John Smith
        assert EntityType.ORGANIZATION in entity_types  # Google
    
    @pytest.mark.asyncio
    async def test_empty_text_handling(self, entity_extractor, sample_texts):
        """Test handling of empty text"""
        entities = await entity_extractor.extract_entities(sample_texts["empty"])
        assert len(entities) == 0
    
    @pytest.mark.asyncio
    async def test_no_entities_text(self, entity_extractor, sample_texts):
        """Test text with no recognizable entities"""
        entities = await entity_extractor.extract_entities(sample_texts["no_entities"])
        # May return 0 or very few entities with low confidence
        assert len(entities) <= 2

class TestEntityTypeMapping:
    """Test entity type mapping functionality"""
    
    def test_person_mapping(self, entity_extractor):
        """Test person entity type mapping"""
        assert entity_extractor._map_entity_type("PERSON") == EntityType.PERSON
        assert entity_extractor._map_entity_type("PEOPLE") == EntityType.PERSON
    
    def test_organization_mapping(self, entity_extractor):
        """Test organization entity type mapping"""
        assert entity_extractor._map_entity_type("ORGANIZATION") == EntityType.ORGANIZATION
        assert entity_extractor._map_entity_type("ORG") == EntityType.ORGANIZATION
        assert entity_extractor._map_entity_type("COMPANY") == EntityType.ORGANIZATION
    
    def test_location_mapping(self, entity_extractor):
        """Test location entity type mapping"""
        assert entity_extractor._map_entity_type("LOCATION") == EntityType.LOCATION
        assert entity_extractor._map_entity_type("LOC") == EntityType.LOCATION
        assert entity_extractor._map_entity_type("PLACE") == EntityType.LOCATION
    
    def test_unknown_mapping(self, entity_extractor):
        """Test unknown entity type mapping"""
        assert entity_extractor._map_entity_type("UNKNOWN") == EntityType.CUSTOM
        assert entity_extractor._map_entity_type("WEIRD_TYPE") == EntityType.CUSTOM

class TestEntityMerging:
    """Test entity merging functionality"""
    
    def test_empty_entities_merge(self, entity_extractor):
        """Test merging empty entity list"""
        merged = entity_extractor._merge_entities([])
        assert len(merged) == 0
    
    def test_non_overlapping_entities_merge(self, entity_extractor):
        """Test merging non-overlapping entities"""
        entities = [
            Entity("Apple", EntityType.ORGANIZATION, 0, 5, 0.9),
            Entity("Steve", EntityType.PERSON, 10, 15, 0.8)
        ]
        merged = entity_extractor._merge_entities(entities)
        assert len(merged) == 2
    
    def test_overlapping_entities_merge(self, entity_extractor):
        """Test merging overlapping entities"""
        entities = [
            Entity("Apple Inc", EntityType.ORGANIZATION, 0, 9, 0.9),
            Entity("Apple", EntityType.ORGANIZATION, 0, 5, 0.7)
        ]
        merged = entity_extractor._merge_entities(entities)
        assert len(merged) == 1
        assert merged[0].text == "Apple Inc"  # Higher confidence entity kept

class TestEntityStatistics:
    """Test entity statistics functionality"""
    
    def test_empty_entities_statistics(self, entity_extractor):
        """Test statistics for empty entity list"""
        stats = entity_extractor.get_entity_statistics([])
        assert stats["total"] == 0
    
    def test_entity_statistics_calculation(self, entity_extractor):
        """Test statistics calculation"""
        entities = [
            Entity("Apple", EntityType.ORGANIZATION, 0, 5, 0.9),
            Entity("Steve", EntityType.PERSON, 6, 11, 0.8),
            Entity("Google", EntityType.ORGANIZATION, 12, 18, 0.95)
        ]
        
        stats = entity_extractor.get_entity_statistics(entities)
        
        assert stats["total"] == 3
        assert stats["by_type"]["ORGANIZATION"] == 2
        assert stats["by_type"]["PERSON"] == 1
        assert stats["average_confidence"] == pytest.approx(0.883, abs=0.01)
        assert stats["high_confidence"] == 2  # > 0.8
        assert stats["unique_entities"] == 3

class TestBatchProcessing:
    """Test batch processing functionality"""
    
    @pytest.mark.asyncio
    async def test_batch_attribute_extraction(self, entity_extractor):
        """Test batch attribute extraction"""
        entities = [
            Entity("Apple Inc", EntityType.ORGANIZATION, 0, 9, 0.9),
            Entity("Steve Jobs", EntityType.PERSON, 10, 20, 0.8)
        ]
        
        text = "Apple Inc was founded by Steve Jobs"
        batch_attributes = await entity_extractor.extract_entity_attributes_batch(text, entities)
        
        assert len(batch_attributes) == 2
        assert "Apple Inc" in batch_attributes
        assert "Steve Jobs" in batch_attributes
        
        # Check attribute structure
        apple_attrs = batch_attributes["Apple Inc"]
        assert apple_attrs["type"] == "ORGANIZATION"
        assert apple_attrs["confidence"] == 0.9
        assert apple_attrs["position"] == [0, 9]

class TestConfiguration:
    """Test configuration options"""
    
    @pytest.mark.asyncio
    async def test_llm_disabled_extraction(self):
        """Test extraction with LLM disabled"""
        config = {'use_llm': False}
        extractor = EntityExtractor(config)
        
        entities = await extractor.extract_entities("Apple Inc. was founded by Steve Jobs.")
        # Should return empty list when LLM is disabled
        assert len(entities) == 0
    
    def test_confidence_threshold_setting(self):
        """Test confidence threshold configuration"""
        config = {'confidence_threshold': 0.9}
        extractor = EntityExtractor(config)
        assert extractor.confidence_threshold == 0.9
    
    def test_should_use_llm_logic(self, entity_extractor):
        """Test LLM usage decision logic"""
        # Short text
        assert entity_extractor.should_use_llm_for_text("Hi") == False
        
        # Long text
        long_text = "This is a much longer text " * 10
        assert entity_extractor.should_use_llm_for_text(long_text) == True

class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_invalid_text_handling(self, entity_extractor):
        """Test handling of invalid text input"""
        # None input
        entities = await entity_extractor.extract_entities(None)
        assert len(entities) == 0
        
        # Non-string input (should be handled gracefully)
        entities = await entity_extractor.extract_entities(123)
        assert len(entities) == 0

class TestEntityDataStructure:
    """Test Entity data structure"""
    
    def test_entity_creation(self):
        """Test Entity creation with all fields"""
        entity = Entity(
            text="Apple Inc",
            entity_type=EntityType.ORGANIZATION,
            start=0,
            end=9,
            confidence=0.95,
            properties={"founded": "1976"},
            canonical_form="Apple Inc.",
            aliases=["Apple"]
        )
        
        assert entity.text == "Apple Inc"
        assert entity.entity_type == EntityType.ORGANIZATION
        assert entity.start == 0
        assert entity.end == 9
        assert entity.confidence == 0.95
        assert entity.properties["founded"] == "1976"
        assert entity.canonical_form == "Apple Inc."
        assert entity.aliases == ["Apple"]
    
    def test_entity_default_values(self):
        """Test Entity creation with default values"""
        entity = Entity(
            text="Test",
            entity_type=EntityType.CUSTOM,
            start=0,
            end=4,
            confidence=0.8
        )
        
        assert entity.properties == {}
        assert entity.aliases == []
        assert entity.canonical_form == "Test"

# Integration test
class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, entity_extractor, sample_texts):
        """Test full extraction pipeline"""
        text = sample_texts["corporate"]
        
        # Extract entities
        entities = await entity_extractor.extract_entities(text)
        assert len(entities) > 0
        
        # Get statistics
        stats = entity_extractor.get_entity_statistics(entities)
        assert stats["total"] == len(entities)
        
        # Batch process
        batch_attrs = await entity_extractor.extract_entity_attributes_batch(text, entities)
        assert len(batch_attrs) == len(entities)
        
        # Merge entities (test with duplicates)
        duplicate_entities = entities + entities[:2]  # Add some duplicates
        merged = entity_extractor._merge_entities(duplicate_entities)
        assert len(merged) <= len(duplicate_entities)

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])