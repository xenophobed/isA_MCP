#!/usr/bin/env python3
"""
Simple test suite for LLM SQL Generator - Step 5 of data analytics pipeline
Tests LLM-powered SQL generation with real data scenarios
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

from tools.services.data_analytics_service.services.data_service.sql_generator import (
    LLMSQLGenerator, SQLGenerationResult
)
from tools.services.data_analytics_service.services.data_service.query_matcher import (
    QueryContext, MetadataMatch, QueryPlan
)
from tools.services.data_analytics_service.services.data_service.semantic_enricher import (
    SemanticMetadata
)

class TestLLMSQLGeneratorSimple:
    """Simplified test suite for LLM SQL Generator with real data scenarios"""
    
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
                        'table_comment': 'Customer information and profiles',
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
    def sample_query_context(self):
        """Create sample query context"""
        return QueryContext(
            entities_mentioned=['customers', 'sales', 'orders'],
            attributes_mentioned=['name', 'total_amount', 'date'],
            operations=['select', 'aggregate', 'filter'],
            filters=[
                {'type': 'numeric', 'operator': 'greater', 'value': 100}
            ],
            aggregations=['sum', 'count'],
            temporal_references=['last month'],
            business_intent='reporting',
            confidence_score=0.8
        )
    
    @pytest.fixture
    def sample_metadata_matches(self):
        """Create sample metadata matches"""
        return [
            MetadataMatch(
                entity_name='ecommerce_sales',
                entity_type='table',
                match_type='semantic',
                similarity_score=0.85,
                relevant_attributes=['customer_id', 'total_amount'],
                suggested_joins=[],
                metadata={'table_comment': 'E-commerce sales transaction data'}
            ),
            MetadataMatch(
                entity_name='customers',
                entity_type='table',
                match_type='semantic',
                similarity_score=0.8,
                relevant_attributes=['customer_id', 'customer_name'],
                suggested_joins=[],
                metadata={'table_comment': 'Customer information'}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test SQL generator initialization"""
        generator = LLMSQLGenerator()
        
        # Test initialization
        await generator.initialize()
        
        # Should have loaded templates and patterns
        assert generator.domain_templates is not None
        assert generator.sql_patterns is not None
        assert generator.business_rules is not None
    
    @pytest.mark.asyncio
    async def test_generate_sql_with_mocked_llm(self, sample_query_context, 
                                               sample_metadata_matches, 
                                               sample_semantic_metadata):
        """Test SQL generation using mocked LLM"""
        generator = LLMSQLGenerator()
        await generator.initialize()
        
        original_query = "Show me customers with total sales over 100"
        
        # Mock the LLM call
        with patch.object(generator, 'call_isa_with_billing') as mock_call:
            mock_call.return_value = (
                {
                    "sql": "SELECT c.customer_name, SUM(e.total_amount) as total_sales FROM ecommerce_sales e JOIN customers c ON e.customer_id = c.customer_id WHERE e.total_amount > 100 GROUP BY c.customer_name ORDER BY total_sales DESC LIMIT 1000;",
                    "explanation": "Query shows customers with total sales over 100",
                    "confidence": 0.9,
                    "complexity": "medium"
                },
                {'cost': 0.002, 'tokens': 150}
            )
            
            result = await generator.generate_sql_from_context(
                sample_query_context, sample_metadata_matches, 
                sample_semantic_metadata, original_query
            )
            
            # Verify result structure
            assert isinstance(result, SQLGenerationResult)
            assert result.sql is not None
            assert len(result.sql) > 0
            assert result.explanation is not None
            assert 0.0 <= result.confidence_score <= 1.0
            assert result.complexity_level in ['simple', 'medium', 'complex']
            
            # Verify SQL contains expected elements
            assert 'SELECT' in result.sql.upper()
            assert 'customers' in result.sql.lower() or 'ecommerce_sales' in result.sql.lower()
            assert 'LIMIT' in result.sql.upper()
    
    @pytest.mark.asyncio
    async def test_generate_sql_fallback_without_llm(self, sample_query_context, 
                                                   sample_metadata_matches, 
                                                   sample_semantic_metadata):
        """Test SQL generation fallback without LLM"""
        generator = LLMSQLGenerator()
        generator.llm_model = None  # No LLM available
        
        result = await generator.generate_sql_from_context(
            sample_query_context, sample_metadata_matches, 
            sample_semantic_metadata, "Show customer sales data"
        )
        
        # Should fall back to template-based generation
        assert isinstance(result, SQLGenerationResult)
        assert result.sql is not None
        assert len(result.sql) > 0
        assert result.confidence_score <= 0.7
    
    @pytest.mark.asyncio
    async def test_domain_detection(self, sample_semantic_metadata):
        """Test domain detection from metadata"""
        generator = LLMSQLGenerator()
        
        # Test ecommerce domain
        ecommerce_matches = [
            MetadataMatch('orders', 'table', 'semantic', 0.8, [], [], {}),
            MetadataMatch('customers', 'table', 'semantic', 0.7, [], [], {})
        ]
        
        domain = generator._detect_domain(sample_semantic_metadata, ecommerce_matches)
        assert domain == '电商'
    
    @pytest.mark.asyncio
    async def test_language_detection(self):
        """Test language detection from query text"""
        generator = LLMSQLGenerator()
        
        # Test English query
        english_query = "Show me customer sales data"
        language = generator._detect_language(english_query)
        assert language == '英文'
        
        # Test Chinese query
        chinese_query = "查询客户销售数据"
        language = generator._detect_language(chinese_query)
        assert language == '中文'
    
    @pytest.mark.asyncio
    async def test_sql_text_extraction(self):
        """Test SQL extraction from text responses"""
        generator = LLMSQLGenerator()
        
        # Test SQL in code block
        text_with_sql_block = """
        Here's the SQL query:
        ```sql
        SELECT * FROM customers WHERE amount > 100;
        ```
        This query finds customers with high amounts.
        """
        
        extracted_sql = generator._extract_sql_from_text(text_with_sql_block)
        assert extracted_sql == "SELECT * FROM customers WHERE amount > 100;"
        
        # Test SQL without code block
        text_with_select = "The query is: SELECT customer_name FROM customers LIMIT 10;"
        extracted_sql = generator._extract_sql_from_text(text_with_select)
        assert "SELECT customer_name FROM customers" in extracted_sql
    
    @pytest.mark.asyncio
    async def test_sql_cleanup_and_safety(self):
        """Test SQL cleanup and safety measures"""
        generator = LLMSQLGenerator()
        
        # Test cleanup
        messy_sql = "   SELECT   *   FROM   customers   WHERE   id=1   "
        cleaned_sql = generator._cleanup_sql(messy_sql)
        assert cleaned_sql == "SELECT * FROM customers WHERE id=1;"
        
        # Test safety measures (adding LIMIT)
        unsafe_sql = "SELECT * FROM large_table"
        safe_sql = generator._add_safety_measures(unsafe_sql)
        assert "LIMIT" in safe_sql.upper()
    
    @pytest.mark.asyncio
    async def test_sql_validation_against_schema(self, sample_semantic_metadata):
        """Test SQL validation against schema"""
        generator = LLMSQLGenerator()
        
        # Test valid SQL
        valid_sql = "SELECT customer_name FROM customers WHERE customer_id = 1"
        errors = generator._validate_against_schema(valid_sql, sample_semantic_metadata)
        assert len(errors) == 0
        
        # Test invalid SQL (non-existent table)
        invalid_sql = "SELECT * FROM nonexistent_table"
        errors = generator._validate_against_schema(invalid_sql, sample_semantic_metadata)
        assert len(errors) > 0
        assert "does not exist" in errors[0]
    
    @pytest.mark.asyncio
    async def test_fallback_sql_creation(self):
        """Test fallback SQL creation when generation fails"""
        generator = LLMSQLGenerator()
        
        query_context = QueryContext(
            entities_mentioned=['customers'],
            attributes_mentioned=['name'],
            operations=['select'],
            filters=[], aggregations=[], temporal_references=[],
            business_intent='lookup', confidence_score=0.5
        )
        
        metadata_matches = [
            MetadataMatch('customers', 'table', 'exact', 0.9, [], [], {})
        ]
        
        fallback_result = generator._create_fallback_sql(query_context, metadata_matches)
        
        assert isinstance(fallback_result, SQLGenerationResult)
        assert fallback_result.sql is not None
        assert 'customers' in fallback_result.sql.lower()
        assert fallback_result.confidence_score < 0.5

# Test runner
if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])