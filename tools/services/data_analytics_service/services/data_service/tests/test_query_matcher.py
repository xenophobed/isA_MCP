#!/usr/bin/env python3
"""
Test suite for Query Matcher - Step 4 of data analytics pipeline
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

class TestQueryMatcher:
    """Test suite for QueryMatcher with real data scenarios"""
    
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
                    },
                    {
                        'table_name': 'products',
                        'table_comment': 'Product catalog',
                        'record_count': 800
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
                        'column_name': 'product_id',
                        'data_type': 'INTEGER',
                        'column_comment': 'Product identifier'
                    },
                    {
                        'table_name': 'ecommerce_sales',
                        'column_name': 'quantity',
                        'data_type': 'INTEGER',
                        'column_comment': 'Quantity purchased'
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
                    },
                    {
                        'table_name': 'customers',
                        'column_name': 'email',
                        'data_type': 'VARCHAR',
                        'column_comment': 'Customer email address'
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
                },
                {
                    'entity_name': 'Customer',
                    'entity_type': 'master_data',
                    'key_attributes': ['customer_id', 'customer_name', 'email'],
                    'business_rules': ['email must be unique', 'name is required']
                }
            ],
            semantic_tags=['ecommerce', 'sales', 'customer', 'transaction'],
            domain_classification={'primary_domain': 'ecommerce', 'confidence': 0.9},
            ai_analysis_summary="E-commerce sales data with customer and product relationships",
            confidence_score=0.85
        )
    
    @pytest.fixture
    def mock_embedding_storage(self):
        """Create mock embedding storage with realistic search results"""
        mock_storage = Mock(spec=EmbeddingStorage)
        
        # Mock search results for different query types
        mock_results = [
            SearchResult(
                entity_name='ecommerce_sales',
                entity_type='table',
                similarity_score=0.8,
                content='Sales transaction data with customer and product information',
                metadata={'table_comment': 'E-commerce sales transaction data'}
            ),
            SearchResult(
                entity_name='customers',
                entity_type='table',
                similarity_score=0.7,
                content='Customer master data with personal information',
                metadata={'table_comment': 'Customer information'}
            ),
            SearchResult(
                entity_name='ecommerce_sales.total_amount',
                entity_type='column',
                similarity_score=0.75,
                content='Total transaction amount in decimal format',
                metadata={'data_type': 'DECIMAL'}
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
        query = "Show me total sales amount for customers who purchased more than 100 items last month"
        
        context = await query_matcher._extract_query_context(query)
        
        assert context.business_intent == 'reporting'
        assert 'customers' in context.entities_mentioned
        assert 'sales' in context.entities_mentioned
        assert 'amount' in context.attributes_mentioned
        assert 'total' in context.attributes_mentioned
        assert 'select' in context.operations
        assert 'aggregate' in context.operations
        assert len(context.filters) > 0
        assert context.confidence_score > 0.5
    
    @pytest.mark.asyncio
    async def test_chinese_query_context_extraction(self, query_matcher):
        """Test context extraction from Chinese queries (customs data)"""
        query = "����ѝ'�10�3�pn"
        
        context = await query_matcher._extract_query_context(query)
        
        assert '' in context.entities_mentioned
        assert '3�' in context.entities_mentioned
        assert 'ѝ' in context.attributes_mentioned
        assert 'select' in context.operations
        assert 'filter' in context.operations
        assert len(context.filters) > 0
        assert context.confidence_score > 0.3
    
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
        
        # Should suggest joins for customer data
        if len(query_plan.primary_tables) > 1:
            assert len(query_plan.required_joins) > 0
    
    @pytest.mark.asyncio
    async def test_find_related_entities(self, query_matcher):
        """Test finding related entities"""
        entity_name = "customers"
        
        related_entities = await query_matcher.find_related_entities(entity_name, 'any')
        
        # Mock returns predefined results
        assert len(related_entities) > 0
        assert all(isinstance(entity, SearchResult) for entity in related_entities)
    
    @pytest.mark.asyncio
    async def test_suggest_query_improvements(self, query_matcher):
        """Test query improvement suggestions"""
        query = "SELECT * FROM customers"
        
        # Create a simple query plan
        query_plan = QueryPlan(
            primary_tables=['customers'],
            required_joins=[],
            select_columns=['*'],
            where_conditions=[],
            aggregations=[],
            order_by=[],
            confidence_score=0.6,
            alternative_plans=[]
        )
        
        suggestions = await query_matcher.suggest_query_improvements(query, query_plan)
        
        assert len(suggestions) > 0
        assert any('specific' in suggestion.lower() for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_entity_extraction_patterns(self, query_matcher):
        """Test entity extraction patterns for different languages"""
        
        # Test English entities
        english_query = "show customer orders and product sales data"
        english_entities = query_matcher._extract_entities(english_query.lower())
        
        assert 'customer' in english_entities
        assert 'orders' in english_entities
        assert 'product' in english_entities
        assert 'sales' in english_entities
        
        # Test Chinese entities
        chinese_query = "查询公司申报的货物信息"
        chinese_entities = query_matcher._extract_entities(chinese_query.lower())
        
        assert '公司' in chinese_entities
        assert '申报' in chinese_entities
        assert '货物' in chinese_entities
    
    @pytest.mark.asyncio
    async def test_attribute_extraction_patterns(self, query_matcher):
        """Test attribute extraction patterns"""
        
        # Test English attributes
        english_query = "get customer name, email, and total amount"
        english_attrs = query_matcher._extract_attributes(english_query.lower())
        
        assert 'name' in english_attrs
        assert 'email' in english_attrs
        assert 'amount' in english_attrs
        assert 'total' in english_attrs
        
        # Test Chinese attributes
        chinese_query = ">:�T���3�ѝ"
        chinese_attrs = query_matcher._extract_attributes(chinese_query.lower())
        
        assert '�' in chinese_attrs
        assert 'T��' in chinese_attrs
        assert 'ѝ' in chinese_attrs
    
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
            for expected_op in expected_ops:
                assert expected_op in operations
    
    @pytest.mark.asyncio
    async def test_filter_extraction(self, query_matcher):
        """Test filter condition extraction"""
        
        test_cases = [
            ("show customers where amount > 100", [{'type': 'numeric', 'operator': 'greater', 'value': 100}]),
            ("find orders after 2023-01-01", [{'type': 'date', 'operator': 'after', 'value': '2023-01-01'}]),
            ("get customers where status = 'active'", [{'type': 'text', 'field': 'status', 'value': 'active'}])
        ]
        
        for query, expected_filters in test_cases:
            filters = query_matcher._extract_filters(query.lower())
            assert len(filters) >= len(expected_filters)
            
            for expected_filter in expected_filters:
                matching_filter = next((f for f in filters if f['type'] == expected_filter['type']), None)
                assert matching_filter is not None
    
    @pytest.mark.asyncio
    async def test_aggregation_extraction(self, query_matcher):
        """Test aggregation function extraction"""
        
        test_cases = [
            ("count all customers", ['count']),
            ("sum total amounts", ['sum']),
            ("average order value", ['average']),
            ("maximum price", ['max']),
            ("minimum quantity", ['min'])
        ]
        
        for query, expected_aggs in test_cases:
            aggregations = query_matcher._extract_aggregations(query.lower())
            for expected_agg in expected_aggs:
                assert expected_agg in aggregations
    
    @pytest.mark.asyncio
    async def test_temporal_reference_extraction(self, query_matcher):
        """Test temporal reference extraction"""
        
        test_cases = [
            ("sales data from last month", ['last month']),
            ("orders from 2023-01-01", ['2023-01-01']),
            ("recent customer activity", ['recent']),
            ("this year's revenue", ['this year'])
        ]
        
        for query, expected_refs in test_cases:
            temporal_refs = query_matcher._extract_temporal_references(query.lower())
            for expected_ref in expected_refs:
                assert any(expected_ref in ref for ref in temporal_refs)
    
    @pytest.mark.asyncio
    async def test_business_intent_determination(self, query_matcher):
        """Test business intent determination"""
        
        test_cases = [
            ("generate sales report", 'reporting'),
            ("analyze customer trends", 'analytics'),
            ("find customer by id", 'lookup'),
            ("monitor order status", 'monitoring'),
            ("recommend best products", 'optimization')
        ]
        
        for query, expected_intent in test_cases:
            intent = query_matcher._determine_business_intent(query.lower())
            assert intent == expected_intent
    
    @pytest.mark.asyncio
    async def test_direct_query_matching(self, query_matcher, sample_semantic_metadata):
        """Test direct query matching using embeddings"""
        
        # Test with complex query that doesn't extract clear entities
        complex_query = "What are the purchasing patterns of our highest value customers?"
        
        # Mock the embedding search to return relevant results
        mock_results = [
            SearchResult(
                entity_name='customers',
                entity_type='table',
                similarity_score=0.7,
                content='Customer information and purchasing data',
                metadata={'table_comment': 'Customer information'}
            ),
            SearchResult(
                entity_name='ecommerce_sales',
                entity_type='table',
                similarity_score=0.6,
                content='Sales transaction data',
                metadata={'table_comment': 'E-commerce sales transaction data'}
            )
        ]
        
        query_matcher.embedding_storage.search_similar_entities.return_value = mock_results
        
        context, matches = await query_matcher.match_query_to_metadata(complex_query, sample_semantic_metadata)
        
        # Should find matches through direct query search
        assert len(matches) > 0
        
        # Should have direct_query match types
        direct_matches = [m for m in matches if m.match_type == 'direct_query']
        assert len(direct_matches) > 0
    
    @pytest.mark.asyncio
    async def test_match_deduplication(self, query_matcher):
        """Test deduplication of matches"""
        
        # Create duplicate matches
        matches = [
            MetadataMatch(
                entity_name='customers',
                entity_type='table',
                match_type='exact',
                similarity_score=0.9,
                relevant_attributes=[],
                suggested_joins=[],
                metadata={}
            ),
            MetadataMatch(
                entity_name='customers',
                entity_type='table',
                match_type='semantic',
                similarity_score=0.7,
                relevant_attributes=[],
                suggested_joins=[],
                metadata={}
            ),
            MetadataMatch(
                entity_name='products',
                entity_type='table',
                match_type='exact',
                similarity_score=0.8,
                relevant_attributes=[],
                suggested_joins=[],
                metadata={}
            )
        ]
        
        deduplicated = query_matcher._deduplicate_matches(matches)
        
        # Should keep only the best match for each entity
        assert len(deduplicated) == 2
        
        # Should keep the higher scoring match for customers
        customer_match = next(m for m in deduplicated if m.entity_name == 'customers')
        assert customer_match.similarity_score == 0.9
        assert customer_match.match_type == 'exact'
    
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

class TestQueryMatcherIntegration:
    """Integration tests with real data scenarios"""
    
    @pytest.mark.asyncio
    async def test_ecommerce_query_scenario(self):
        """Test complete ecommerce query scenario"""
        
        # Create realistic ecommerce metadata
        ecommerce_metadata = SemanticMetadata(
            original_metadata={
                'tables': [
                    {'table_name': 'orders', 'table_comment': 'Customer orders'},
                    {'table_name': 'customers', 'table_comment': 'Customer information'},
                    {'table_name': 'products', 'table_comment': 'Product catalog'}
                ],
                'columns': [
                    {'table_name': 'orders', 'column_name': 'order_id', 'data_type': 'INTEGER'},
                    {'table_name': 'orders', 'column_name': 'customer_id', 'data_type': 'INTEGER'},
                    {'table_name': 'orders', 'column_name': 'total_amount', 'data_type': 'DECIMAL'},
                    {'table_name': 'customers', 'column_name': 'customer_name', 'data_type': 'VARCHAR'}
                ],
                'relationships': [
                    {'from_table': 'orders', 'from_column': 'customer_id', 'to_table': 'customers', 'to_column': 'customer_id'}
                ]
            },
            business_entities=[
                {'entity_name': 'Order', 'entity_type': 'transactional', 'key_attributes': ['order_id', 'total_amount']},
                {'entity_name': 'Customer', 'entity_type': 'master_data', 'key_attributes': ['customer_id', 'customer_name']}
            ],
            semantic_tags=['ecommerce', 'sales'],
            domain_classification={'primary_domain': 'ecommerce'},
            ai_analysis_summary="E-commerce order management system",
            confidence_score=0.9
        )
        
        # Mock embedding storage
        mock_storage = Mock(spec=EmbeddingStorage)
        mock_storage.search_similar_entities = AsyncMock(return_value=[
            SearchResult('orders', 'table', 0.85, 'Order transaction data', {}),
            SearchResult('customers', 'table', 0.8, 'Customer information', {})
        ])
        
        matcher = QueryMatcher(mock_storage)
        
        # Test complex ecommerce query
        query = "Find top 10 customers by total order amount in the last 6 months"
        
        context, matches = await matcher.match_query_to_metadata(query, ecommerce_metadata)
        plan = await matcher.generate_query_plan(context, matches, ecommerce_metadata)
        
        # Verify results
        assert len(matches) > 0
        assert len(plan.primary_tables) > 0
        assert plan.confidence_score > 0.5
        
        # Should identify aggregation and filtering needs
        assert 'aggregate' in context.operations or len(context.aggregations) > 0
        assert len(context.temporal_references) > 0
    
    @pytest.mark.asyncio
    async def test_customs_query_scenario(self):
        """Test customs/trade data query scenario"""
        
        # Create realistic customs metadata
        customs_metadata = SemanticMetadata(
            original_metadata={
                'tables': [
                    {'table_name': 'declarations', 'table_comment': 'ws3�U'},
                    {'table_name': 'companies', 'table_comment': '�o'},
                    {'table_name': 'goods', 'table_comment': ''i�o'}
                ],
                'columns': [
                    {'table_name': 'declarations', 'column_name': 'declaration_id', 'data_type': 'VARCHAR'},
                    {'table_name': 'declarations', 'column_name': 'company_code', 'data_type': 'VARCHAR'},
                    {'table_name': 'declarations', 'column_name': 'total_amount', 'data_type': 'DECIMAL'},
                    {'table_name': 'companies', 'column_name': 'company_name', 'data_type': 'VARCHAR'}
                ],
                'relationships': [
                    {'from_table': 'declarations', 'from_column': 'company_code', 'to_table': 'companies', 'to_column': 'company_code'}
                ]
            },
            business_entities=[
                {'entity_name': 'Declaration', 'entity_type': 'transactional', 'key_attributes': ['declaration_id', 'total_amount']},
                {'entity_name': 'Company', 'entity_type': 'master_data', 'key_attributes': ['company_code', 'company_name']}
            ],
            semantic_tags=['customs', 'trade', 'declaration'],
            domain_classification={'primary_domain': 'customs'},
            ai_analysis_summary="ws3�pn���",
            confidence_score=0.9
        )
        
        # Mock embedding storage
        mock_storage = Mock(spec=EmbeddingStorage)
        mock_storage.search_similar_entities = AsyncMock(return_value=[
            SearchResult('declarations', 'table', 0.9, 'ws3�Upn', {}),
            SearchResult('companies', 'table', 0.8, '�@�o', {})
        ])
        
        matcher = QueryMatcher(mock_storage)
        
        # Test Chinese customs query
        query = "����ѝ��100�3��U"
        
        context, matches = await matcher.match_query_to_metadata(query, customs_metadata)
        plan = await matcher.generate_query_plan(context, matches, customs_metadata)
        
        # Verify Chinese query processing
        assert len(matches) > 0
        assert len(plan.primary_tables) > 0
        assert plan.confidence_score > 0.3
        
        # Should identify filtering needs
        assert 'filter' in context.operations or len(context.filters) > 0


# Test runner
if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])