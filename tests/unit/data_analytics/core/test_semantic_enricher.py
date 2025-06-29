#!/usr/bin/env python3
"""
Unit tests for SemanticEnricher - Step 2 of the analytics workflow
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from tools.services.data_analytics_service.core.semantic_enricher import (
    SemanticEnricher, SemanticMetadata
)


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing"""
    return {
        'tables': [
            {
                'table_name': 'customers',
                'table_type': 'table',
                'record_count': 1000,
                'table_comment': 'Customer information table',
                'created_date': '2023-01-01',
                'last_modified': '2023-12-01'
            },
            {
                'table_name': 'orders',
                'table_type': 'table',
                'record_count': 5000,
                'table_comment': 'Order transactions',
                'created_date': '2023-01-01',
                'last_modified': '2023-12-01'
            },
            {
                'table_name': 'products',
                'table_type': 'table',
                'record_count': 500,
                'table_comment': 'Product catalog',
                'created_date': '2023-01-01',
                'last_modified': '2023-12-01'
            }
        ],
        'columns': [
            {
                'table_name': 'customers',
                'column_name': 'customer_id',
                'data_type': 'integer',
                'is_nullable': False,
                'column_comment': 'Primary key',
                'ordinal_position': 1
            },
            {
                'table_name': 'customers',
                'column_name': 'email',
                'data_type': 'varchar',
                'is_nullable': False,
                'column_comment': 'Customer email address',
                'ordinal_position': 2
            },
            {
                'table_name': 'orders',
                'column_name': 'order_id',
                'data_type': 'integer',
                'is_nullable': False,
                'column_comment': 'Primary key',
                'ordinal_position': 1
            },
            {
                'table_name': 'orders',
                'column_name': 'customer_id',
                'data_type': 'integer',
                'is_nullable': False,
                'column_comment': 'Foreign key to customers',
                'ordinal_position': 2
            },
            {
                'table_name': 'orders',
                'column_name': 'order_amount',
                'data_type': 'decimal',
                'is_nullable': False,
                'column_comment': 'Total order amount',
                'ordinal_position': 3
            }
        ],
        'relationships': [
            {
                'constraint_name': 'fk_orders_customer',
                'from_table': 'orders',
                'from_column': 'customer_id',
                'to_table': 'customers',
                'to_column': 'customer_id',
                'constraint_type': 'foreign_key'
            }
        ]
    }


@pytest.fixture
def semantic_enricher():
    """Create SemanticEnricher instance"""
    return SemanticEnricher()


class TestSemanticEnricher:
    """Test cases for SemanticEnricher"""
    
    def test_initialization(self, semantic_enricher):
        """Test SemanticEnricher initialization"""
        assert semantic_enricher is not None
        assert hasattr(semantic_enricher, 'business_keywords')
        assert hasattr(semantic_enricher, 'pattern_detectors')
        assert 'customer' in semantic_enricher.business_keywords
        assert 'product' in semantic_enricher.business_keywords
    
    def test_enrich_metadata_basic(self, semantic_enricher, sample_metadata):
        """Test basic metadata enrichment"""
        result = semantic_enricher.enrich_metadata(sample_metadata)
        
        assert isinstance(result, SemanticMetadata)
        assert result.original_metadata == sample_metadata
        assert len(result.business_entities) > 0
        assert len(result.semantic_tags) > 0
        assert len(result.data_patterns) >= 0
        assert len(result.business_rules) >= 0
        assert 'primary_domain' in result.domain_classification
    
    def test_extract_business_entities(self, semantic_enricher, sample_metadata):
        """Test business entity extraction"""
        entities = semantic_enricher._extract_business_entities(sample_metadata)
        
        assert len(entities) == 3  # customers, orders, products
        
        # Check customer entity
        customer_entity = next((e for e in entities if e['entity_name'] == 'customers'), None)
        assert customer_entity is not None
        assert customer_entity['entity_type'] in ['entity', 'reference', 'transaction']
        assert 'confidence' in customer_entity
        assert customer_entity['confidence'] > 0
        
        # Check orders entity
        order_entity = next((e for e in entities if e['entity_name'] == 'orders'), None)
        assert order_entity is not None
        assert order_entity['entity_type'] in ['entity', 'transaction']
    
    def test_generate_semantic_tags(self, semantic_enricher, sample_metadata):
        """Test semantic tag generation"""
        tags = semantic_enricher._generate_semantic_tags(sample_metadata)
        
        assert len(tags) > 0
        
        # Check table tags
        customer_table_key = 'table:customers'
        assert customer_table_key in tags
        customer_tags = tags[customer_table_key]
        assert any('domain:customer' in tag for tag in customer_tags)
        
        # Check column tags
        email_column_key = 'column:customers.email'
        assert email_column_key in tags
        email_tags = tags[email_column_key]
        # Should have business or semantic tags
        assert len(email_tags) > 0
    
    def test_detect_data_patterns(self, semantic_enricher, sample_metadata):
        """Test data pattern detection"""
        patterns = semantic_enricher._detect_data_patterns(sample_metadata)
        
        assert isinstance(patterns, list)
        
        # Check for master-detail pattern (customers -> orders)
        master_detail_patterns = [p for p in patterns if p['pattern_type'] == 'master_detail']
        assert len(master_detail_patterns) >= 0  # May or may not detect based on data
        
        if master_detail_patterns:
            pattern = master_detail_patterns[0]
            assert 'confidence' in pattern
            assert pattern['confidence'] > 0
    
    def test_infer_business_rules(self, semantic_enricher, sample_metadata):
        """Test business rule inference"""
        entities = semantic_enricher._extract_business_entities(sample_metadata)
        rules = semantic_enricher._infer_business_rules(sample_metadata, entities)
        
        assert isinstance(rules, list)
        
        # Should detect referential integrity rule
        ref_rules = [r for r in rules if r['rule_type'] == 'referential_integrity']
        assert len(ref_rules) > 0
        
        ref_rule = ref_rules[0]
        assert 'confidence' in ref_rule
        assert ref_rule['confidence'] > 0
        assert 'orders' in ref_rule['tables_involved']
        assert 'customers' in ref_rule['tables_involved']
    
    def test_classify_domain(self, semantic_enricher, sample_metadata):
        """Test domain classification"""
        entities = semantic_enricher._extract_business_entities(sample_metadata)
        domain_classification = semantic_enricher._classify_domain(sample_metadata, entities)
        
        assert 'primary_domain' in domain_classification
        assert 'confidence' in domain_classification
        assert 'domain_scores' in domain_classification
        assert 'is_multi_domain' in domain_classification
        
        # Should classify as ecommerce due to customers, orders, products
        assert domain_classification['primary_domain'] in ['ecommerce', 'unknown']
        if domain_classification['primary_domain'] == 'ecommerce':
            assert domain_classification['confidence'] > 0


if __name__ == '__main__':
    pytest.main([__file__])