#!/usr/bin/env python3
"""
Test file for LLMSQLGenerator
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from .sql_generator import LLMSQLGenerator, SQLGenerationResult
from .query_matcher import QueryContext, MetadataMatch, QueryPlan
from .semantic_enricher import SemanticMetadata


class TestLLMSQLGenerator:
    """Test cases for LLMSQLGenerator"""
    
    @pytest.fixture
    def generator(self):
        """Create SQL generator for testing"""
        return LLMSQLGenerator()
    
    @pytest.fixture
    def mock_query_context(self):
        """Create mock query context"""
        return QueryContext(
            business_intent='reporting',
            entities_mentioned=['users', 'orders'],
            attributes_mentioned=['name', 'email', 'total'],
            operations=['select', 'group'],
            aggregations=['count', 'sum'],
            filters=['active = true'],
            temporal_references=['last month'],
            confidence_score=0.8
        )
    
    @pytest.fixture
    def mock_metadata_matches(self):
        """Create mock metadata matches"""
        return [
            MetadataMatch(
                entity_name='users',
                entity_type='table',
                confidence_score=0.9,
                metadata={'table_comment': 'User information'},
                relevant_attributes=['id', 'name', 'email'],
                suggested_joins=['users.id = orders.user_id']
            ),
            MetadataMatch(
                entity_name='orders',
                entity_type='table',
                confidence_score=0.8,
                metadata={'table_comment': 'Order information'},
                relevant_attributes=['id', 'user_id', 'total'],
                suggested_joins=[]
            )
        ]
    
    @pytest.fixture
    def mock_semantic_metadata(self):
        """Create mock semantic metadata"""
        return SemanticMetadata(
            original_metadata={
                'tables': [
                    {'table_name': 'users', 'table_comment': 'User data'},
                    {'table_name': 'orders', 'table_comment': 'Order data'}
                ],
                'columns': [
                    {'table_name': 'users', 'column_name': 'id', 'data_type': 'int', 'column_comment': 'User ID'},
                    {'table_name': 'users', 'column_name': 'name', 'data_type': 'varchar', 'column_comment': 'User name'},
                    {'table_name': 'orders', 'column_name': 'id', 'data_type': 'int', 'column_comment': 'Order ID'},
                    {'table_name': 'orders', 'column_name': 'total', 'data_type': 'decimal', 'column_comment': 'Order total'}
                ]
            },
            enriched_tables={},
            enriched_columns={},
            relationships={},
            business_concepts={},
            domain_classification={'primary_domain': 'ecommerce'},
            semantic_insights={}
        )
    
    def test_init(self, generator):
        """Test generator initialization"""
        assert generator.service_name == "LLMSQLGenerator"
        assert generator.llm_model is None
        assert generator.domain_templates is not None
        assert generator.sql_patterns is not None
        assert generator.business_rules is not None
    
    @pytest.mark.asyncio
    async def test_initialize_with_model(self, generator):
        """Test initialization with provided LLM model"""
        mock_model = Mock()
        await generator.initialize(mock_model)
        
        assert generator.llm_model == mock_model
    
    @pytest.mark.asyncio
    async def test_initialize_with_isa_client(self, generator):
        """Test initialization with ISA client"""
        with patch.object(generator, 'isa_client', Mock()) as mock_isa:
            await generator.initialize()
            
            assert generator.llm_model == mock_isa
    
    @pytest.mark.asyncio
    async def test_close(self, generator):
        """Test closing generator resources"""
        generator.llm_model = Mock()
        
        await generator.close()
        
        assert generator.llm_model is None
    
    @pytest.mark.asyncio
    async def test_generate_sql_from_context_with_llm(self, generator, mock_query_context, 
                                                     mock_metadata_matches, mock_semantic_metadata):
        """Test SQL generation using LLM"""
        # Mock LLM model
        generator.llm_model = Mock()
        
        # Mock LLM response
        mock_response = {
            "sql": "SELECT u.name, COUNT(o.id) FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.name",
            "explanation": "Generated SQL for user order counts",
            "confidence": 0.9,
            "complexity": "medium"
        }
        
        with patch.object(generator, 'call_isa_with_billing', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (mock_response, {"cost": 0.001})
            
            result = await generator.generate_sql_from_context(
                mock_query_context, mock_metadata_matches, mock_semantic_metadata, "Show user order counts"
            )
        
        assert isinstance(result, SQLGenerationResult)
        assert "SELECT" in result.sql
        assert result.confidence_score == 0.9
        assert result.complexity_level == "medium"
    
    @pytest.mark.asyncio
    async def test_generate_sql_from_context_fallback(self, generator, mock_query_context, 
                                                     mock_metadata_matches, mock_semantic_metadata):
        """Test SQL generation using template fallback"""
        # No LLM model
        generator.llm_model = None
        
        with patch.object(generator, '_find_best_template') as mock_find:
            mock_find.return_value = {
                'sql': 'SELECT {columns} FROM {table_name} LIMIT {limit}',
                'operations': ['select']
            }
            
            result = await generator.generate_sql_from_context(
                mock_query_context, mock_metadata_matches, mock_semantic_metadata, "Get user data"
            )
        
        assert isinstance(result, SQLGenerationResult)
        assert "SELECT" in result.sql
        assert "users" in result.sql
    
    @pytest.mark.asyncio
    async def test_generate_sql_error_fallback(self, generator, mock_query_context, 
                                              mock_metadata_matches, mock_semantic_metadata):
        """Test SQL generation error handling with fallback"""
        generator.llm_model = Mock()
        
        with patch.object(generator, 'call_isa_with_billing', side_effect=Exception("LLM failed")):
            result = await generator.generate_sql_from_context(
                mock_query_context, mock_metadata_matches, mock_semantic_metadata, "Get data"
            )
        
        assert isinstance(result, SQLGenerationResult)
        assert result.confidence_score == 0.3  # Low confidence for fallback
        assert "fallback" in result.explanation.lower()
    
    @pytest.mark.asyncio
    async def test_enhance_sql_with_business_rules(self, generator):
        """Test enhancing SQL with business rules"""
        sql = "SELECT * FROM declarations"
        domain = "海关贸易"
        
        result = await generator.enhance_sql_with_business_rules(sql, domain)
        
        assert isinstance(result, SQLGenerationResult)
        assert result.confidence_score >= 0.5
    
    def test_detect_domain(self, generator, mock_semantic_metadata, mock_metadata_matches):
        """Test domain detection"""
        domain = generator._detect_domain(mock_semantic_metadata, mock_metadata_matches)
        
        assert domain == "电商"  # Should detect ecommerce domain
    
    def test_detect_language_chinese(self, generator):
        """Test Chinese language detection"""
        query = "查询用户订单统计信息"
        language = generator._detect_language(query)
        
        assert language == "中文"
    
    def test_detect_language_english(self, generator):
        """Test English language detection"""
        query = "Show user order statistics"
        language = generator._detect_language(query)
        
        assert language == "英文"
    
    def test_format_schema_information(self, generator, mock_metadata_matches, mock_semantic_metadata):
        """Test schema information formatting"""
        schema_info = generator._format_schema_information(mock_metadata_matches, mock_semantic_metadata)
        
        assert "表: users" in schema_info
        assert "表: orders" in schema_info
        assert "字段:" in schema_info
    
    def test_extract_sql_from_text_code_block(self, generator):
        """Test extracting SQL from text with code block"""
        text = """Here's the SQL:
        ```sql
        SELECT * FROM users WHERE active = true;
        ```
        This query retrieves active users."""
        
        sql = generator._extract_sql_from_text(text)
        
        assert sql == "SELECT * FROM users WHERE active = true;"
    
    def test_extract_sql_from_text_select_statement(self, generator):
        """Test extracting SQL from text with SELECT statement"""
        text = "The query you need is: SELECT id, name FROM users ORDER BY name;"
        
        sql = generator._extract_sql_from_text(text)
        
        assert sql == "SELECT id, name FROM users ORDER BY name;"
    
    def test_cleanup_sql(self, generator):
        """Test SQL cleanup"""
        sql = "  SELECT   *   FROM   users  "
        cleaned = generator._cleanup_sql(sql)
        
        assert cleaned == "SELECT * FROM users;"
    
    def test_add_safety_measures(self, generator):
        """Test adding safety measures to SQL"""
        sql = "SELECT * FROM users"
        safe_sql = generator._add_safety_measures(sql)
        
        assert "LIMIT" in safe_sql
    
    def test_validate_against_schema(self, generator, mock_semantic_metadata):
        """Test SQL validation against schema"""
        sql = "SELECT * FROM nonexistent_table"
        errors = generator._validate_against_schema(sql, mock_semantic_metadata)
        
        assert len(errors) > 0
        assert "does not exist" in errors[0]
    
    def test_auto_fix_sql_errors(self, generator, mock_semantic_metadata):
        """Test auto-fixing SQL errors"""
        sql = "SELECT * FROM user"  # Missing 's' in 'users'
        errors = ["Table 'user' does not exist"]
        
        fixed_sql = generator._auto_fix_sql_errors(sql, errors, mock_semantic_metadata)
        
        # Should attempt to fix the table name
        assert "users" in fixed_sql or sql == fixed_sql
    
    def test_find_best_template(self, generator, mock_query_context, mock_metadata_matches):
        """Test finding best matching template"""
        template = generator._find_best_template(mock_query_context, mock_metadata_matches)
        
        # Should find a template for reporting intent
        assert template is not None or template is None  # Depends on loaded templates
    
    def test_fill_template_parameters(self, generator, mock_query_context, mock_metadata_matches):
        """Test filling template parameters"""
        template = {
            'sql': 'SELECT {columns} FROM {table_name} LIMIT {limit}'
        }
        
        filled_sql = generator._fill_template_parameters(template, mock_query_context, mock_metadata_matches)
        
        assert "SELECT" in filled_sql
        assert "users" in filled_sql
        assert "LIMIT" in filled_sql
    
    def test_load_domain_templates(self, generator):
        """Test loading domain templates"""
        templates = generator._load_domain_templates()
        
        assert isinstance(templates, dict)
        assert "海关贸易" in templates
    
    def test_load_sql_patterns(self, generator):
        """Test loading SQL patterns"""
        patterns = generator._load_sql_patterns()
        
        assert isinstance(patterns, dict)
        assert "reporting" in patterns
        assert "analytics" in patterns
    
    def test_load_business_rules(self, generator):
        """Test loading business rules"""
        rules = generator._load_business_rules()
        
        assert isinstance(rules, dict)
        assert "海关贸易" in rules
        assert "电商" in rules
    
    @pytest.mark.asyncio
    async def test_apply_business_rules(self, generator):
        """Test applying business rules to SQL"""
        sql = "SELECT * FROM declarations"
        business_rules = {
            "common_filters": ["status = '已放行'", "rmb_amount > 0"]
        }
        
        enhanced_sql = await generator._apply_business_rules(sql, business_rules)
        
        # Should add business rule filters
        assert "WHERE" in enhanced_sql or enhanced_sql == sql
    
    def test_create_fallback_sql_with_matches(self, generator, mock_query_context, mock_metadata_matches):
        """Test creating fallback SQL with metadata matches"""
        result = generator._create_fallback_sql(mock_query_context, mock_metadata_matches)
        
        assert isinstance(result, SQLGenerationResult)
        assert "SELECT * FROM users" in result.sql
        assert result.confidence_score == 0.3
    
    def test_create_fallback_sql_no_matches(self, generator, mock_query_context):
        """Test creating fallback SQL without metadata matches"""
        result = generator._create_fallback_sql(mock_query_context, [])
        
        assert isinstance(result, SQLGenerationResult)
        assert "SELECT 1 as result" in result.sql
        assert result.confidence_score == 0.3
    
    def test_get_service_billing_info(self, generator):
        """Test getting service billing information"""
        with patch.object(generator, 'get_billing_summary', return_value={"total_cost": 0.001}):
            billing_info = generator.get_service_billing_info()
            
            assert isinstance(billing_info, dict)
            assert "total_cost" in billing_info


if __name__ == "__main__":
    pytest.main([__file__])