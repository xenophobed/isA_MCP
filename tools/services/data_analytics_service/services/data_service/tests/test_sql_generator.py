#!/usr/bin/env python3
"""
Test suite for LLM SQL Generator - Step 5 of data analytics pipeline
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

class TestLLMSQLGenerator:
    """Test suite for LLM SQL Generator with real data scenarios"""
    
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
                    },
                    {
                        'table_name': 'products',
                        'table_comment': 'Product catalog and inventory',
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
                        'table_name': 'ecommerce_sales',
                        'column_name': 'transaction_date',
                        'data_type': 'DATE',
                        'column_comment': 'Transaction date'
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
                    },
                    {
                        'table_name': 'customers',
                        'column_name': 'city',
                        'data_type': 'VARCHAR',
                        'column_comment': 'Customer city'
                    }
                ],
                'relationships': [
                    {
                        'from_table': 'ecommerce_sales',
                        'from_column': 'customer_id',
                        'to_table': 'customers',
                        'to_column': 'customer_id'
                    },
                    {
                        'from_table': 'ecommerce_sales',
                        'from_column': 'product_id',
                        'to_table': 'products',
                        'to_column': 'product_id'
                    }
                ]
            },
            business_entities=[
                {
                    'entity_name': 'SalesTransaction',
                    'entity_type': 'transactional',
                    'key_attributes': ['transaction_id', 'customer_id', 'total_amount', 'transaction_date'],
                    'business_rules': ['amount must be positive', 'customer must exist', 'date must be valid']
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
    def sample_query_context(self):
        """Create sample query context"""
        return QueryContext(
            entities_mentioned=['customers', 'sales', 'orders'],
            attributes_mentioned=['name', 'total_amount', 'date'],
            operations=['select', 'aggregate', 'filter'],
            filters=[
                {'type': 'numeric', 'operator': 'greater', 'value': 100},
                {'type': 'date', 'operator': 'after', 'value': '2023-01-01'}
            ],
            aggregations=['sum', 'count'],
            temporal_references=['last month', 'recent'],
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
                relevant_attributes=['customer_id', 'total_amount', 'transaction_date'],
                suggested_joins=[],
                metadata={'table_comment': 'E-commerce sales transaction data'}
            ),
            MetadataMatch(
                entity_name='customers',
                entity_type='table',
                match_type='semantic',
                similarity_score=0.8,
                relevant_attributes=['customer_id', 'customer_name', 'email'],
                suggested_joins=[],
                metadata={'table_comment': 'Customer information'}
            )
        ]
    
    @pytest.fixture
    def mock_isa_client(self):
        """Create mock ISA client for LLM calls"""
        mock_client = Mock()
        
        # Mock successful SQL generation response
        mock_response = {
            "sql": "SELECT c.customer_name, SUM(e.total_amount) as total_sales FROM ecommerce_sales e JOIN customers c ON e.customer_id = c.customer_id WHERE e.total_amount > 100 GROUP BY c.customer_name ORDER BY total_sales DESC LIMIT 1000;",
            "explanation": "This query joins sales and customer data to show customer names with their total sales amounts, filtered for amounts greater than 100",
            "confidence": 0.9,
            "complexity": "medium",
            "estimated_rows": "500-1000 rows"
        }
        
        mock_client.return_value = (json.dumps(mock_response), {'cost': 0.002, 'tokens': 150})
        return mock_client
    
    @pytest.fixture
    def sql_generator(self, mock_isa_client):
        """Create LLMSQLGenerator instance"""
        generator = LLMSQLGenerator()
        generator.isa_client = mock_isa_client
        return generator
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test SQL generator initialization"""
        generator = LLMSQLGenerator()
        
        # Test initialization with default ISA client
        await generator.initialize()
        
        # Should have loaded domain templates and patterns
        assert generator.domain_templates is not None
        assert generator.sql_patterns is not None
        assert generator.business_rules is not None
        
        # Should have ISA client reference
        assert generator.isa_client is not None
    
    @pytest.mark.asyncio
    async def test_generate_sql_from_context_with_llm(self, sql_generator, sample_query_context, 
                                                     sample_metadata_matches, sample_semantic_metadata):
        """Test SQL generation using LLM with real context"""
        original_query = "Show me customers with total sales over 100"
        
        # Mock the call_isa_with_billing method
        with patch.object(sql_generator, 'call_isa_with_billing') as mock_call:
            mock_call.return_value = (
                {
                    "sql": "SELECT c.customer_name, SUM(e.total_amount) as total_sales FROM ecommerce_sales e JOIN customers c ON e.customer_id = c.customer_id WHERE e.total_amount > 100 GROUP BY c.customer_name ORDER BY total_sales DESC LIMIT 1000;",
                    "explanation": "Query shows customers with total sales over 100",
                    "confidence": 0.9,
                    "complexity": "medium"
                },
                {'cost': 0.002, 'tokens': 150}
            )
            
            result = await sql_generator.generate_sql_from_context(
                sample_query_context, sample_metadata_matches, sample_semantic_metadata, original_query
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
            assert 'LIMIT' in result.sql.upper()  # Should have safety limit
    
    @pytest.mark.asyncio
    async def test_generate_sql_fallback_without_llm(self, sample_query_context, 
                                                   sample_metadata_matches, sample_semantic_metadata):
        """Test SQL generation fallback without LLM"""
        generator = LLMSQLGenerator()
        generator.llm_model = None  # No LLM available
        
        result = await generator.generate_sql_from_context(
            sample_query_context, sample_metadata_matches, sample_semantic_metadata, 
            "Show customer sales data"
        )
        
        # Should fall back to template-based generation
        assert isinstance(result, SQLGenerationResult)
        assert result.sql is not None
        assert len(result.sql) > 0
        assert result.explanation == "Generated using template matching"
        assert result.confidence_score <= 0.7  # Lower confidence for template-based
    
    @pytest.mark.asyncio
    async def test_enhance_sql_with_business_rules(self, sql_generator):
        """Test SQL enhancement with business rules"""
        base_sql = "SELECT * FROM declarations WHERE company_code = 'TEST'"
        business_domain = "ws8"
        
        result = await sql_generator.enhance_sql_with_business_rules(base_sql, business_domain)
        
        assert isinstance(result, SQLGenerationResult)
        assert result.sql is not None
        assert len(result.sql) > 0
        
        # Should apply business rules for customs domain
        if business_domain in sql_generator.business_rules:
            assert result.confidence_score >= 0.8
    
    @pytest.mark.asyncio
    async def test_chinese_query_processing(self, sql_generator, sample_semantic_metadata):
        """Test Chinese query processing with domain-specific context"""
        
        # Create customs metadata
        customs_metadata = SemanticMetadata(
            original_metadata={
                'tables': [
                    {'table_name': 'declarations', 'table_comment': 'ws3¥U'},
                    {'table_name': 'companies', 'table_comment': 'áo'}
                ],
                'columns': [
                    {'table_name': 'declarations', 'column_name': 'company_code', 'data_type': 'VARCHAR'},
                    {'table_name': 'declarations', 'column_name': 'total_amount', 'data_type': 'DECIMAL'}
                ],
                'relationships': []
            },
            business_entities=[],
            semantic_tags=['customs', 'declaration'],
            domain_classification={'primary_domain': 'customs', 'confidence': 0.9},
            ai_analysis_summary="ws3¥pn",
            confidence_score=0.8
        )
        
        chinese_context = QueryContext(
            entities_mentioned=['', '3¥'],
            attributes_mentioned=['Ñ', 'ã'],
            operations=['select', 'filter'],
            filters=[{'type': 'numeric', 'operator': 'greater', 'value': 100000}],
            aggregations=[],
            temporal_references=[],
            business_intent='lookup',
            confidence_score=0.7
        )
        
        chinese_matches = [
            MetadataMatch(
                entity_name='declarations',
                entity_type='table',
                match_type='semantic',
                similarity_score=0.8,
                relevant_attributes=['company_code', 'total_amount'],
                suggested_joins=[],
                metadata={'table_comment': 'ws3¥U'}
            )
        ]
        
        # Mock Chinese LLM response
        with patch.object(sql_generator, 'call_isa_with_billing') as mock_call:
            mock_call.return_value = (
                {
                    "sql": "SELECT company_code, total_amount FROM declarations WHERE total_amount > 100000 ORDER BY total_amount DESC LIMIT 1000;",
                    "explanation": "åâ3¥Ñ…Ç10„3¥pn",
                    "confidence": 0.85,
                    "complexity": "simple"
                },
                {'cost': 0.001, 'tokens': 80}
            )
            
            result = await sql_generator.generate_sql_from_context(
                chinese_context, chinese_matches, customs_metadata, 
                "åâÛãÑ…Ç10„3¥pn"
            )
            
            assert isinstance(result, SQLGenerationResult)
            assert result.sql is not None
            assert 'declarations' in result.sql.lower()
            assert 'total_amount' in result.sql.lower()
    
    @pytest.mark.asyncio
    async def test_domain_detection(self, sql_generator, sample_semantic_metadata):
        """Test domain detection from metadata"""
        
        # Test ecommerce domain
        ecommerce_matches = [
            MetadataMatch('orders', 'table', 'semantic', 0.8, [], [], {}),
            MetadataMatch('customers', 'table', 'semantic', 0.7, [], [], {})
        ]
        
        domain = sql_generator._detect_domain(sample_semantic_metadata, ecommerce_matches)
        assert domain == '5F'
        
        # Test customs domain
        customs_metadata = SemanticMetadata(
            original_metadata={}, business_entities=[], semantic_tags=[],
            domain_classification={'primary_domain': 'customs', 'confidence': 0.9},
            ai_analysis_summary="", confidence_score=0.8
        )
        
        domain = sql_generator._detect_domain(customs_metadata, [])
        assert domain == 'ws8'
    
    @pytest.mark.asyncio
    async def test_language_detection(self, sql_generator):
        """Test language detection from query text"""
        
        # Test English query
        english_query = "Show me customer sales data"
        language = sql_generator._detect_language(english_query)
        assert language == 'ñ‡'
        
        # Test Chinese query
        chinese_query = "åâ¢7 .pn"
        language = sql_generator._detect_language(chinese_query)
        assert language == '-‡'
        
        # Test mixed query (should detect as Chinese if significant Chinese content)
        mixed_query = "åâcustomer salespn"
        language = sql_generator._detect_language(mixed_query)
        assert language == '-‡'
    
    @pytest.mark.asyncio
    async def test_schema_information_formatting(self, sql_generator, sample_metadata_matches, sample_semantic_metadata):
        """Test schema information formatting for prompt"""
        
        schema_info = sql_generator._format_schema_information(sample_metadata_matches, sample_semantic_metadata)
        
        assert isinstance(schema_info, str)
        assert len(schema_info) > 0
        
        # Should contain table information
        assert 'ecommerce_sales' in schema_info
        assert 'customers' in schema_info
        
        # Should contain column information
        assert 'customer_id' in schema_info
        assert 'total_amount' in schema_info
    
    @pytest.mark.asyncio
    async def test_sql_text_extraction(self, sql_generator):
        """Test SQL extraction from text responses"""
        
        # Test SQL in code block
        text_with_sql_block = """
        Here's the SQL query:
        ```sql
        SELECT * FROM customers WHERE amount > 100;
        ```
        This query finds customers with high amounts.
        """
        
        extracted_sql = sql_generator._extract_sql_from_text(text_with_sql_block)
        assert extracted_sql == "SELECT * FROM customers WHERE amount > 100;"
        
        # Test SQL without code block
        text_with_select = "The query is: SELECT customer_name FROM customers LIMIT 10;"
        extracted_sql = sql_generator._extract_sql_from_text(text_with_select)
        assert "SELECT customer_name FROM customers" in extracted_sql
    
    @pytest.mark.asyncio
    async def test_sql_cleanup_and_safety(self, sql_generator):
        """Test SQL cleanup and safety measures"""
        
        # Test cleanup
        messy_sql = "   SELECT   *   FROM   customers   WHERE   id=1   "
        cleaned_sql = sql_generator._cleanup_sql(messy_sql)
        assert cleaned_sql == "SELECT * FROM customers WHERE id=1;"
        
        # Test safety measures (adding LIMIT)
        unsafe_sql = "SELECT * FROM large_table"
        safe_sql = sql_generator._add_safety_measures(unsafe_sql)
        assert "LIMIT" in safe_sql.upper()
    
    @pytest.mark.asyncio
    async def test_sql_validation_against_schema(self, sql_generator, sample_semantic_metadata):
        """Test SQL validation against schema"""
        
        # Test valid SQL
        valid_sql = "SELECT customer_name FROM customers WHERE customer_id = 1"
        errors = sql_generator._validate_against_schema(valid_sql, sample_semantic_metadata)
        assert len(errors) == 0
        
        # Test invalid SQL (non-existent table)
        invalid_sql = "SELECT * FROM nonexistent_table"
        errors = sql_generator._validate_against_schema(invalid_sql, sample_semantic_metadata)
        assert len(errors) > 0
        assert "does not exist" in errors[0]
    
    @pytest.mark.asyncio
    async def test_sql_error_auto_fix(self, sql_generator, sample_semantic_metadata):
        """Test automatic SQL error fixing"""
        
        # Test table name correction
        sql_with_error = "SELECT * FROM customer"  # Missing 's'
        errors = ["Table 'customer' does not exist"]
        
        fixed_sql = sql_generator._auto_fix_sql_errors(sql_with_error, errors, sample_semantic_metadata)
        
        # Should attempt to fix the table name
        assert fixed_sql != sql_with_error
        # Should replace with a valid table name
        assert "customers" in fixed_sql.lower()
    
    @pytest.mark.asyncio
    async def test_post_process_sql(self, sql_generator, sample_semantic_metadata):
        """Test SQL post-processing"""
        
        original_result = SQLGenerationResult(
            sql="SELECT * FROM customers",
            explanation="Simple customer query",
            confidence_score=0.8,
            complexity_level="simple"
        )
        
        processed_result = await sql_generator._post_process_sql(original_result, sample_semantic_metadata)
        
        assert isinstance(processed_result, SQLGenerationResult)
        assert processed_result.sql is not None
        assert processed_result.sql.endswith(';')  # Should be cleaned up
        assert "LIMIT" in processed_result.sql.upper()  # Should have safety limit
    
    @pytest.mark.asyncio
    async def test_fallback_sql_creation(self, sql_generator):
        """Test fallback SQL creation when generation fails"""
        
        # Test with metadata matches
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
        
        fallback_result = sql_generator._create_fallback_sql(query_context, metadata_matches)
        
        assert isinstance(fallback_result, SQLGenerationResult)
        assert fallback_result.sql is not None
        assert 'customers' in fallback_result.sql.lower()
        assert fallback_result.confidence_score < 0.5
    
    @pytest.mark.asyncio
    async def test_business_rules_application(self, sql_generator):
        """Test business rules application"""
        
        base_sql = "SELECT * FROM declarations WHERE company_code = 'TEST'"
        business_rules = {
            'common_filters': ["status = 'ò>L'", "rmb_amount > 0"]
        }
        
        enhanced_sql = await sql_generator._apply_business_rules(base_sql, business_rules)
        
        assert enhanced_sql != base_sql
        # Should add business rule filters
        assert "status = 'ò>L'" in enhanced_sql
        assert "rmb_amount > 0" in enhanced_sql
    
    @pytest.mark.asyncio
    async def test_template_based_generation(self, sql_generator, sample_query_context, sample_metadata_matches, sample_semantic_metadata):
        """Test template-based SQL generation"""
        
        # Force template-based generation
        result = await sql_generator._generate_with_templates(
            sample_query_context, sample_metadata_matches, sample_semantic_metadata
        )
        
        assert isinstance(result, SQLGenerationResult)
        assert result.sql is not None
        assert result.explanation == "Generated using template matching"
        assert result.confidence_score <= 0.7
    
    @pytest.mark.asyncio
    async def test_billing_information_tracking(self, sql_generator):
        """Test billing information tracking"""
        
        # Test billing info retrieval
        billing_info = sql_generator.get_service_billing_info()
        
        assert isinstance(billing_info, dict)
        # Should contain billing tracking information from BaseService
        assert 'service_name' in billing_info
        assert billing_info['service_name'] == 'LLMSQLGenerator'
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, sql_generator, sample_query_context, sample_metadata_matches, sample_semantic_metadata):
        """Test error handling and recovery mechanisms"""
        
        # Mock LLM call to raise exception
        with patch.object(sql_generator, 'call_isa_with_billing') as mock_call:
            mock_call.side_effect = Exception("LLM service unavailable")
            
            # Should fall back to template generation
            result = await sql_generator.generate_sql_from_context(
                sample_query_context, sample_metadata_matches, sample_semantic_metadata, 
                "test query"
            )
            
            assert isinstance(result, SQLGenerationResult)
            assert result.sql is not None
            assert result.confidence_score <= 0.7  # Lower confidence for fallback


class TestSQLGeneratorIntegration:
    """Integration tests with real data scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_ecommerce_sql_generation(self):
        """Test complete ecommerce SQL generation scenario"""
        
        generator = LLMSQLGenerator()
        await generator.initialize()
        
        # Create realistic ecommerce scenario
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
                    {'table_name': 'orders', 'column_name': 'order_date', 'data_type': 'DATE'},
                    {'table_name': 'customers', 'column_name': 'customer_name', 'data_type': 'VARCHAR'}
                ],
                'relationships': [
                    {'from_table': 'orders', 'from_column': 'customer_id', 'to_table': 'customers', 'to_column': 'customer_id'}
                ]
            },
            business_entities=[],
            semantic_tags=['ecommerce', 'orders'],
            domain_classification={'primary_domain': 'ecommerce'},
            ai_analysis_summary="E-commerce order system",
            confidence_score=0.9
        )
        
        context = QueryContext(
            entities_mentioned=['customers', 'orders'],
            attributes_mentioned=['name', 'total_amount'],
            operations=['select', 'aggregate', 'join'],
            filters=[],
            aggregations=['sum'],
            temporal_references=[],
            business_intent='reporting',
            confidence_score=0.8
        )
        
        matches = [
            MetadataMatch('orders', 'table', 'semantic', 0.9, ['total_amount'], [], {}),
            MetadataMatch('customers', 'table', 'semantic', 0.8, ['customer_name'], [], {})
        ]
        
        # Mock LLM response
        with patch.object(generator, 'call_isa_with_billing') as mock_call:
            mock_call.return_value = (
                {
                    "sql": "SELECT c.customer_name, SUM(o.total_amount) as total_orders FROM orders o JOIN customers c ON o.customer_id = c.customer_id GROUP BY c.customer_name ORDER BY total_orders DESC LIMIT 1000;",
                    "explanation": "Shows customers with their total order amounts",
                    "confidence": 0.92,
                    "complexity": "medium"
                },
                {'cost': 0.003, 'tokens': 200}
            )
            
            result = await generator.generate_sql_from_context(
                context, matches, ecommerce_metadata, 
                "Show customers with their total order amounts"
            )
            
            # Verify comprehensive result
            assert isinstance(result, SQLGenerationResult)
            assert 'JOIN' in result.sql.upper()
            assert 'customers' in result.sql.lower()
            assert 'orders' in result.sql.lower()
            assert 'SUM' in result.sql.upper()
            assert result.confidence_score > 0.8
    
    @pytest.mark.asyncio
    async def test_customs_domain_chinese_generation(self):
        """Test customs domain with Chinese query generation"""
        
        generator = LLMSQLGenerator()
        await generator.initialize()
        
        # Create customs metadata
        customs_metadata = SemanticMetadata(
            original_metadata={
                'tables': [
                    {'table_name': 'declarations', 'table_comment': 'ws3¥U'},
                    {'table_name': 'companies', 'table_comment': 'áo'},
                    {'table_name': 'goods', 'table_comment': ''iáo'}
                ],
                'columns': [
                    {'table_name': 'declarations', 'column_name': 'declaration_id', 'data_type': 'VARCHAR'},
                    {'table_name': 'declarations', 'column_name': 'company_code', 'data_type': 'VARCHAR'},
                    {'table_name': 'declarations', 'column_name': 'rmb_amount', 'data_type': 'DECIMAL'},
                    {'table_name': 'declarations', 'column_name': 'trade_type', 'data_type': 'VARCHAR'},
                    {'table_name': 'companies', 'column_name': 'company_name', 'data_type': 'VARCHAR'}
                ],
                'relationships': [
                    {'from_table': 'declarations', 'from_column': 'company_code', 'to_table': 'companies', 'to_column': 'company_code'}
                ]
            },
            business_entities=[],
            semantic_tags=['customs', 'trade', 'declaration'],
            domain_classification={'primary_domain': 'customs'},
            ai_analysis_summary="ws3¥pn¡",
            confidence_score=0.9
        )
        
        context = QueryContext(
            entities_mentioned=['', '3¥'],
            attributes_mentioned=['Ñ', 'ð'],
            operations=['select', 'filter'],
            filters=[{'type': 'numeric', 'operator': 'greater', 'value': 1000000}],
            aggregations=[],
            temporal_references=[],
            business_intent='lookup',
            confidence_score=0.7
        )
        
        matches = [
            MetadataMatch('declarations', 'table', 'semantic', 0.9, ['rmb_amount'], [], {}),
            MetadataMatch('companies', 'table', 'semantic', 0.8, ['company_name'], [], {})
        ]
        
        # Mock Chinese LLM response
        with patch.object(generator, 'call_isa_with_billing') as mock_call:
            mock_call.return_value = (
                {
                    "sql": "SELECT c.company_name, d.rmb_amount FROM declarations d JOIN companies c ON d.company_code = c.company_code WHERE d.rmb_amount > 1000000 ORDER BY d.rmb_amount DESC LIMIT 1000;",
                    "explanation": "åâ3¥Ñ…Ç100„pn",
                    "confidence": 0.88,
                    "complexity": "medium"
                },
                {'cost': 0.002, 'tokens': 120}
            )
            
            result = await generator.generate_sql_from_context(
                context, matches, customs_metadata, 
                "åâ3¥Ñ…Ç100„pn"
            )
            
            # Verify Chinese domain handling
            assert isinstance(result, SQLGenerationResult)
            assert 'declarations' in result.sql.lower()
            assert 'companies' in result.sql.lower()
            assert 'rmb_amount > 1000000' in result.sql
            assert result.confidence_score > 0.8
    
    @pytest.mark.asyncio
    async def test_performance_and_safety_measures(self):
        """Test performance and safety measures in generated SQL"""
        
        generator = LLMSQLGenerator()
        await generator.initialize()
        
        # Test with large dataset metadata
        large_dataset_metadata = SemanticMetadata(
            original_metadata={
                'tables': [
                    {'table_name': 'large_transactions', 'table_comment': 'Large transaction dataset', 'record_count': 10000000}
                ],
                'columns': [
                    {'table_name': 'large_transactions', 'column_name': 'transaction_id', 'data_type': 'BIGINT'},
                    {'table_name': 'large_transactions', 'column_name': 'amount', 'data_type': 'DECIMAL'}
                ],
                'relationships': []
            },
            business_entities=[],
            semantic_tags=['transactions'],
            domain_classification={'primary_domain': 'finance'},
            ai_analysis_summary="Large transaction dataset",
            confidence_score=0.8
        )
        
        # Mock response without LIMIT
        with patch.object(generator, 'call_isa_with_billing') as mock_call:
            mock_call.return_value = (
                {
                    "sql": "SELECT * FROM large_transactions WHERE amount > 1000",
                    "explanation": "Query for large transactions",
                    "confidence": 0.7,
                    "complexity": "simple"
                },
                {'cost': 0.001, 'tokens': 50}
            )
            
            result = await generator.generate_sql_from_context(
                QueryContext([], [], ['select'], [], [], [], 'lookup', 0.6),
                [MetadataMatch('large_transactions', 'table', 'exact', 0.9, [], [], {})],
                large_dataset_metadata,
                "Show large transactions"
            )
            
            # Should add safety LIMIT
            assert 'LIMIT' in result.sql.upper()
            assert result.sql.endswith(';')


# Test runner
if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])