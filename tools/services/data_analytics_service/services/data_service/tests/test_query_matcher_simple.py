#!/usr/bin/env python3
"""
Simple test suite for Query Matcher - Step 4 of data analytics pipeline
Tests query context extraction and metadata matching with real data
"""

import asyncio
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

from tools.services.data_analytics_service.services.data_service.query_matcher import (
    QueryMatcher, QueryContext, MetadataMatch, QueryPlan
)
from tools.services.data_analytics_service.services.data_service.embedding_storage import (
    EmbeddingStorage, SearchResult
)
from tools.services.data_analytics_service.services.data_service.semantic_enricher import (
    SemanticMetadata
)

class TestQueryMatcherSimple:
    """Simplified test suite for QueryMatcher with real data scenarios"""
    
    @pytest.fixture
    def sample_semantic_metadata(self):
        """Create sample semantic metadata based on real CSV data"""
        return SemanticMetadata(
            original_metadata={
                'tables': [
                    {
                        'table_name': 'ecommerce_sales',
                        'table_comment': 'E-commerce sales transaction data',
                        'record_count': 5000
                    },
                    {
                        'table_name': 'customers',
                        'table_comment': 'Customer information',
                        'record_count': 1200
                    }
                ],
                'columns': [
                    {
                        'table_name': 'ecommerce_sales',
                        'column_name': 'transaction_id',
                        'data_type': 'VARCHAR',
                        'column_comment': 'Unique transaction identifier'
                    },
                    {
                        'table_name': 'ecommerce_sales',
                        'column_name': 'customer_id',
                        'data_type': 'INTEGER',
                        'column_comment': 'Customer identifier'
                    },
                    {
                        'table_name': 'ecommerce_sales',
                        'column_name': 'total_amount',
                        'data_type': 'DECIMAL',
                        'column_comment': 'Total transaction amount'
                    },
                    {
                        'table_name': 'customers',
                        'column_name': 'customer_id',
                        'data_type': 'INTEGER',
                        'column_comment': 'Unique customer identifier'
                    },
                    {
                        'table_name': 'customers',
                        'column_name': 'customer_name',
                        'data_type': 'VARCHAR',
                        'column_comment': 'Customer full name'
                    }
                ],
                'relationships': [
                    {
                        'from_table': 'ecommerce_sales',
                        'from_column': 'customer_id',
                        'to_table': 'customers',
                        'to_column': 'customer_id'
                    }
                ]
            },
            business_entities=[
                {
                    'entity_name': 'SalesTransaction',
                    'entity_type': 'transactional',
                    'key_attributes': ['transaction_id', 'customer_id', 'total_amount'],
                    'business_rules': ['amount must be positive', 'customer must exist']
                }
            ],
            semantic_tags={'ecommerce': ['sales', 'customer', 'transaction']},
            data_patterns=[{'pattern': 'transactional', 'confidence': 0.8}],
            business_rules=[{'rule': 'amount_positive', 'description': 'amounts must be positive'}],
            domain_classification={'primary_domain': 'ecommerce', 'confidence': 0.9},
            confidence_scores={'overall': 0.85, 'entities': 0.8},
            ai_analysis={'summary': 'E-commerce sales data with customer relationships'}
        )
    
    @pytest.fixture
    def mock_embedding_storage(self):
        """Create mock embedding storage with realistic search results"""
        mock_storage = Mock(spec=EmbeddingStorage)
        
        mock_results = [
            SearchResult(
                entity_name='ecommerce_sales',
                entity_type='table',
                similarity_score=0.8,
                content='Sales transaction data with customer information',
                metadata={'table_comment': 'E-commerce sales transaction data'}
            ),
            SearchResult(
                entity_name='customers',
                entity_type='table',
                similarity_score=0.7,
                content='Customer master data with personal information',
                metadata={'table_comment': 'Customer information'}
            )
        ]
        
        mock_storage.search_similar_entities = AsyncMock(return_value=mock_results)
        return mock_storage
    
    @pytest.fixture
    def query_matcher(self, mock_embedding_storage):
        """Create QueryMatcher instance with mock storage"""
        return QueryMatcher(mock_embedding_storage)
    
    @pytest.mark.asyncio
    async def test_english_query_context_extraction(self, query_matcher):
        """Test context extraction from English queries"""
        query = "Show me total sales amount for customers who purchased more than 100 items"
        
        context = await query_matcher._extract_query_context(query)
        
        assert context.business_intent in ['reporting', 'lookup', 'analytics']
        assert 'customers' in context.entities_mentioned
        assert 'sales' in context.entities_mentioned
        assert 'amount' in context.attributes_mentioned
        assert 'total' in context.attributes_mentioned
        assert 'select' in context.operations
        assert context.confidence_score > 0.5
    
    @pytest.mark.asyncio
    async def test_match_query_to_metadata(self, query_matcher, sample_semantic_metadata):
        """Test complete query matching to metadata"""
        query = "Find customers with high sales amounts"
        
        context, matches = await query_matcher.match_query_to_metadata(query, sample_semantic_metadata)
        
        # Check context extraction
        assert context.business_intent in ['lookup', 'reporting']
        assert 'customers' in context.entities_mentioned
        assert 'sales' in context.entities_mentioned
        
        # Check metadata matches
        assert len(matches) > 0
        
        # Should find table matches
        table_matches = [m for m in matches if m.entity_type == 'table']
        assert len(table_matches) > 0
        
        # Should have similarity scores
        for match in matches:
            assert 0.0 <= match.similarity_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_generate_query_plan(self, query_matcher, sample_semantic_metadata):
        """Test query plan generation"""
        query = "Show customer names and their total purchase amounts"
        
        context, matches = await query_matcher.match_query_to_metadata(query, sample_semantic_metadata)
        query_plan = await query_matcher.generate_query_plan(context, matches, sample_semantic_metadata)
        
        # Check plan structure
        assert len(query_plan.primary_tables) > 0
        assert len(query_plan.select_columns) > 0
        assert 0.0 <= query_plan.confidence_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_entity_extraction_patterns(self, query_matcher):
        """Test entity extraction patterns for English"""
        
        # Test English entities
        english_query = "show customer orders and product sales data"
        english_entities = query_matcher._extract_entities(english_query.lower())
        
        assert 'customer' in english_entities
        assert 'orders' in english_entities
        assert 'product' in english_entities
        assert 'sales' in english_entities
    
    @pytest.mark.asyncio
    async def test_operation_extraction(self, query_matcher):
        """Test operation extraction from queries"""
        
        test_cases = [
            ("show me all customers", ['select']),
            ("find customers where amount > 100", ['select', 'filter']),
            ("count total orders by customer", ['select', 'aggregate', 'group']),
            ("sort customers by name", ['select', 'sort']),
            ("join customers with orders", ['select', 'join'])
        ]
        
        for query, expected_ops in test_cases:
            operations = query_matcher._extract_operations(query.lower())
            # Check that at least one expected operation is found
            assert any(op in operations for op in expected_ops), f"None of {expected_ops} found in {operations} for query: {query}"
    
    @pytest.mark.asyncio
    async def test_confidence_scoring(self, query_matcher):
        """Test confidence scoring for context extraction"""
        
        # High confidence query with clear entities and attributes
        high_conf_query = "select customer name and total amount from sales where amount > 100"
        high_context = await query_matcher._extract_query_context(high_conf_query)
        
        # Low confidence query with ambiguous terms
        low_conf_query = "show some data"
        low_context = await query_matcher._extract_query_context(low_conf_query)
        
        assert high_context.confidence_score > low_context.confidence_score
        assert high_context.confidence_score > 0.6
        assert low_context.confidence_score < 0.5

# Test runner
if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])