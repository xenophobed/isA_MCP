#!/usr/bin/env python3
"""
Unit tests for QueryMatcher - Step 4 of the analytics workflow
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from tools.services.data_analytics_service.core.query_matcher import (
    QueryMatcher, QueryContext, MetadataMatch, QueryPlan
)
from tools.services.data_analytics_service.core.embedding_storage import EmbeddingStorage, SearchResult
from tools.services.data_analytics_service.core.semantic_enricher import SemanticMetadata


@pytest.fixture
def mock_embedding_storage():
    """Mock EmbeddingStorage for testing"""
    mock_storage = Mock(spec=EmbeddingStorage)
    mock_storage.search_similar_entities = AsyncMock(return_value=[
        SearchResult(
            entity_name='customers',
            entity_type='table',
            similarity_score=0.9,
            content='customer data table',
            metadata={'table_name': 'customers'},
            semantic_tags=['domain:customer']
        )
    ])
    return mock_storage


@pytest.fixture
def query_matcher(mock_embedding_storage):
    """Create QueryMatcher instance with mock storage"""
    return QueryMatcher(mock_embedding_storage)


@pytest.fixture
def sample_semantic_metadata():
    """Sample semantic metadata for testing"""
    return SemanticMetadata(
        original_metadata={
            'tables': [
                {
                    'table_name': 'customers',
                    'table_type': 'table',
                    'record_count': 1000,
                    'table_comment': 'Customer data'
                },
                {
                    'table_name': 'orders',
                    'table_type': 'table',
                    'record_count': 5000,
                    'table_comment': 'Order data'
                }
            ],
            'columns': [
                {
                    'table_name': 'customers',
                    'column_name': 'customer_id',
                    'data_type': 'integer',
                    'is_nullable': False
                },
                {
                    'table_name': 'customers',
                    'column_name': 'email',
                    'data_type': 'varchar',
                    'is_nullable': False
                },
                {
                    'table_name': 'orders',
                    'column_name': 'order_id',
                    'data_type': 'integer',
                    'is_nullable': False
                },
                {
                    'table_name': 'orders',
                    'column_name': 'customer_id',
                    'data_type': 'integer',
                    'is_nullable': False
                }
            ],
            'relationships': [
                {
                    'from_table': 'orders',
                    'from_column': 'customer_id',
                    'to_table': 'customers',
                    'to_column': 'customer_id',
                    'constraint_type': 'foreign_key'
                }
            ]
        },
        business_entities=[
            {
                'entity_name': 'customers',
                'entity_type': 'entity',
                'confidence': 0.9,
                'key_attributes': ['email'],
                'relationships': [],
                'business_importance': 'high'
            }
        ],
        semantic_tags={},
        data_patterns=[],
        business_rules=[],
        domain_classification={},
        confidence_scores={}
    )


class TestQueryMatcher:
    """Test cases for QueryMatcher"""
    
    def test_initialization(self, query_matcher, mock_embedding_storage):
        """Test QueryMatcher initialization"""
        assert query_matcher is not None
        assert query_matcher.embedding_storage == mock_embedding_storage
        assert hasattr(query_matcher, 'business_terms')
        assert hasattr(query_matcher, 'sql_patterns')
        assert hasattr(query_matcher, 'entity_synonyms')
    
    def test_extract_entities(self, query_matcher):
        """Test entity extraction from queries"""
        query = "show me all customers and their orders"
        entities = query_matcher._extract_entities(query)
        
        assert 'customers' in entities
        assert 'orders' in entities
    
    def test_extract_entities_quoted(self, query_matcher):
        """Test entity extraction with quoted entities"""
        query = 'find data in "user_profiles" table'
        entities = query_matcher._extract_entities(query)
        
        assert 'user_profiles' in entities
    
    def test_extract_attributes(self, query_matcher):
        """Test attribute extraction from queries"""
        query = "get customer name, email and phone numbers"
        attributes = query_matcher._extract_attributes(query)
        
        assert 'name' in attributes
        assert 'email' in attributes
        assert 'phone' in attributes
    
    def test_extract_operations(self, query_matcher):
        """Test operation extraction from queries"""
        query = "show customers ordered by name and group by city"
        operations = query_matcher._extract_operations(query)
        
        assert 'select' in operations
        assert 'sort' in operations
        assert 'group' in operations
    
    def test_extract_filters(self, query_matcher):
        """Test filter extraction from queries"""
        query = "customers created after 2023-01-01 with age greater than 25"
        filters = query_matcher._extract_filters(query)
        
        # Should extract date and numeric filters
        date_filters = [f for f in filters if f['type'] == 'date']
        numeric_filters = [f for f in filters if f['type'] == 'numeric']
        
        assert len(date_filters) > 0
        assert len(numeric_filters) > 0
    
    def test_extract_aggregations(self, query_matcher):
        """Test aggregation extraction from queries"""
        query = "count customers and sum their total orders"
        aggregations = query_matcher._extract_aggregations(query)
        
        assert 'count' in aggregations
        assert 'sum' in aggregations
    
    def test_extract_temporal_references(self, query_matcher):
        """Test temporal reference extraction"""
        query = "orders from last month and yesterday's sales"
        temporal_refs = query_matcher._extract_temporal_references(query)
        
        assert len(temporal_refs) > 0
        assert any('last month' in ref for ref in temporal_refs)
        assert any('yesterday' in ref for ref in temporal_refs)
    
    def test_determine_business_intent(self, query_matcher):
        """Test business intent determination"""
        # Reporting intent
        report_query = "generate monthly sales report"
        intent = query_matcher._determine_business_intent(report_query)
        assert intent == 'reporting'
        
        # Analytics intent
        analytics_query = "analyze customer trends and patterns"
        intent = query_matcher._determine_business_intent(analytics_query)
        assert intent == 'analytics'
        
        # Lookup intent
        lookup_query = "find customer john smith"
        intent = query_matcher._determine_business_intent(lookup_query)
        assert intent == 'lookup'
    
    @pytest.mark.asyncio
    async def test_extract_query_context(self, query_matcher):
        """Test complete query context extraction"""
        query = "show me customers from orders placed after 2023-01-01 with total amount greater than 100"
        
        context = await query_matcher._extract_query_context(query)
        
        assert isinstance(context, QueryContext)
        assert 'customers' in context.entities_mentioned
        assert 'orders' in context.entities_mentioned
        assert len(context.filters) > 0
        assert context.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_find_exact_entity_matches(self, query_matcher, sample_semantic_metadata):
        """Test finding exact entity matches"""
        matches = await query_matcher._find_exact_entity_matches('customers', sample_semantic_metadata)
        
        assert len(matches) > 0
        customer_match = matches[0]
        assert customer_match.entity_name == 'customers'
        assert customer_match.match_type == 'exact'
        assert customer_match.similarity_score >= 0.8
    
    @pytest.mark.asyncio
    async def test_find_semantic_entity_matches(self, query_matcher, sample_semantic_metadata):
        """Test finding semantic entity matches using embeddings"""
        matches = await query_matcher._find_semantic_entity_matches('users', sample_semantic_metadata)
        
        # Should use embedding storage to find matches
        query_matcher.embedding_storage.search_similar_entities.assert_called()
        assert isinstance(matches, list)
    
    def test_find_fuzzy_entity_matches(self, query_matcher, sample_semantic_metadata):
        """Test finding fuzzy entity matches"""
        # Test with synonym
        matches = query_matcher._find_fuzzy_entity_matches('client', sample_semantic_metadata)
        
        assert isinstance(matches, list)
        # Should find matches based on synonyms if customer table exists
    
    @pytest.mark.asyncio
    async def test_match_query_to_metadata(self, query_matcher, sample_semantic_metadata):
        """Test complete query to metadata matching"""
        query = "show all customers with their orders"
        
        context, matches = await query_matcher.match_query_to_metadata(query, sample_semantic_metadata)
        
        assert isinstance(context, QueryContext)
        assert isinstance(matches, list)
        assert context.confidence_score > 0
    
    def test_identify_primary_tables(self, query_matcher):
        """Test primary table identification"""
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
                entity_name='orders',
                entity_type='table',
                match_type='exact',
                similarity_score=0.8,
                relevant_attributes=[],
                suggested_joins=[],
                metadata={}
            )
        ]
        
        context = QueryContext([], [], [], [], [], [], 'general', 0.8)
        primary_tables = query_matcher._identify_primary_tables(matches, context)
        
        assert 'customers' in primary_tables
        assert 'orders' in primary_tables
        assert len(primary_tables) <= 3
    
    def test_determine_joins(self, query_matcher, sample_semantic_metadata):
        """Test join determination"""
        primary_tables = ['customers', 'orders']
        matches = []
        
        joins = query_matcher._determine_joins(primary_tables, matches, sample_semantic_metadata)
        
        assert isinstance(joins, list)
        if len(joins) > 0:
            join = joins[0]
            assert 'type' in join
            assert 'left_table' in join
            assert 'right_table' in join
            assert 'confidence' in join
    
    def test_map_select_columns(self, query_matcher):
        """Test mapping query attributes to columns"""
        context = QueryContext(
            entities_mentioned=['customers'],
            attributes_mentioned=['email', 'name'],
            operations=[],
            filters=[],
            aggregations=[],
            temporal_references=[],
            business_intent='lookup',
            confidence_score=0.8
        )
        
        matches = [
            MetadataMatch(
                entity_name='customers',
                entity_type='table',
                match_type='exact',
                similarity_score=0.9,
                relevant_attributes=['email', 'customer_name'],
                suggested_joins=[],
                metadata={}
            )
        ]
        
        columns = query_matcher._map_select_columns(context, matches)
        
        assert len(columns) > 0
        assert any('email' in col for col in columns)
    
    def test_generate_where_conditions(self, query_matcher):
        """Test WHERE condition generation"""
        context = QueryContext(
            entities_mentioned=[],
            attributes_mentioned=[],
            operations=[],
            filters=[
                {'type': 'date', 'operator': 'after', 'value': '2023-01-01'},
                {'type': 'numeric', 'operator': 'greater', 'value': 100}
            ],
            aggregations=[],
            temporal_references=[],
            business_intent='lookup',
            confidence_score=0.8
        )
        
        matches = []
        conditions = query_matcher._generate_where_conditions(context, matches)
        
        assert len(conditions) > 0
        assert any('2023-01-01' in cond for cond in conditions)
        assert any('100' in cond for cond in conditions)
    
    def test_handle_aggregations(self, query_matcher):
        """Test aggregation handling"""
        context = QueryContext(
            entities_mentioned=[],
            attributes_mentioned=[],
            operations=[],
            filters=[],
            aggregations=['count', 'sum'],
            temporal_references=[],
            business_intent='reporting',
            confidence_score=0.8
        )
        
        matches = []
        aggregations = query_matcher._handle_aggregations(context, matches)
        
        assert 'COUNT(*)' in aggregations
        assert any('SUM(' in agg for agg in aggregations)
    
    @pytest.mark.asyncio
    async def test_generate_query_plan(self, query_matcher, sample_semantic_metadata):
        """Test complete query plan generation"""
        context = QueryContext(
            entities_mentioned=['customers'],
            attributes_mentioned=['email'],
            operations=['select'],
            filters=[],
            aggregations=[],
            temporal_references=[],
            business_intent='lookup',
            confidence_score=0.8
        )
        
        matches = [
            MetadataMatch(
                entity_name='customers',
                entity_type='table',
                match_type='exact',
                similarity_score=0.9,
                relevant_attributes=['email'],
                suggested_joins=[],
                metadata={}
            )
        ]
        
        plan = await query_matcher.generate_query_plan(context, matches, sample_semantic_metadata)
        
        assert isinstance(plan, QueryPlan)
        assert len(plan.primary_tables) > 0
        assert plan.confidence_score > 0
        assert isinstance(plan.alternative_plans, list)
    
    def test_calculate_plan_confidence(self, query_matcher):
        """Test query plan confidence calculation"""
        primary_tables = ['customers']
        joins = []
        select_columns = ['customers.email']
        matches = [
            MetadataMatch(
                entity_name='customers',
                entity_type='table',
                match_type='exact',
                similarity_score=0.9,
                relevant_attributes=[],
                suggested_joins=[],
                metadata={}
            )
        ]
        
        confidence = query_matcher._calculate_plan_confidence(
            primary_tables, joins, select_columns, matches
        )
        
        assert 0 <= confidence <= 1
        assert confidence > 0.5  # Should have reasonable confidence
    
    @pytest.mark.asyncio
    async def test_find_related_entities(self, query_matcher):
        """Test finding related entities"""
        related = await query_matcher.find_related_entities('customers', 'foreign_key')
        
        # Should use embedding storage
        query_matcher.embedding_storage.search_similar_entities.assert_called()
        assert isinstance(related, list)
    
    @pytest.mark.asyncio
    async def test_suggest_query_improvements(self, query_matcher):
        """Test query improvement suggestions"""
        query = "simple query"
        
        plan = QueryPlan(
            primary_tables=['customers'],
            required_joins=[],
            select_columns=['id'],
            where_conditions=[],
            aggregations=[],
            order_by=[],
            confidence_score=0.6,  # Low confidence
            alternative_plans=[]
        )
        
        suggestions = await query_matcher.suggest_query_improvements(query, plan)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # Should suggest improvements for low confidence
        assert any('specific' in suggestion.lower() for suggestion in suggestions)


class TestQueryContext:
    """Test cases for QueryContext dataclass"""
    
    def test_query_context_creation(self):
        """Test QueryContext creation"""
        context = QueryContext(
            entities_mentioned=['customers'],
            attributes_mentioned=['email'],
            operations=['select'],
            filters=[],
            aggregations=[],
            temporal_references=[],
            business_intent='lookup',
            confidence_score=0.8
        )
        
        assert context.entities_mentioned == ['customers']
        assert context.attributes_mentioned == ['email']
        assert context.business_intent == 'lookup'
        assert context.confidence_score == 0.8


class TestMetadataMatch:
    """Test cases for MetadataMatch dataclass"""
    
    def test_metadata_match_creation(self):
        """Test MetadataMatch creation"""
        match = MetadataMatch(
            entity_name='customers',
            entity_type='table',
            match_type='exact',
            similarity_score=0.9,
            relevant_attributes=['email'],
            suggested_joins=[],
            metadata={'table_name': 'customers'}
        )
        
        assert match.entity_name == 'customers'
        assert match.entity_type == 'table'
        assert match.match_type == 'exact'
        assert match.similarity_score == 0.9


class TestQueryPlan:
    """Test cases for QueryPlan dataclass"""
    
    def test_query_plan_creation(self):
        """Test QueryPlan creation"""
        plan = QueryPlan(
            primary_tables=['customers'],
            required_joins=[],
            select_columns=['customers.email'],
            where_conditions=[],
            aggregations=[],
            order_by=[],
            confidence_score=0.8,
            alternative_plans=[]
        )
        
        assert plan.primary_tables == ['customers']
        assert plan.select_columns == ['customers.email']
        assert plan.confidence_score == 0.8


@pytest.mark.asyncio
class TestQueryMatcherIntegration:
    """Integration tests for QueryMatcher"""
    
    async def test_full_matching_workflow(self, query_matcher, sample_semantic_metadata):
        """Test complete matching workflow"""
        query = "show me customers and their order amounts"
        
        context, matches = await query_matcher.match_query_to_metadata(query, sample_semantic_metadata)
        plan = await query_matcher.generate_query_plan(context, matches, sample_semantic_metadata)
        
        # Verify complete workflow
        assert isinstance(context, QueryContext)
        assert isinstance(matches, list)
        assert isinstance(plan, QueryPlan)
        
        assert len(context.entities_mentioned) > 0
        assert context.confidence_score > 0
        assert plan.confidence_score > 0


if __name__ == '__main__':
    pytest.main([__file__])