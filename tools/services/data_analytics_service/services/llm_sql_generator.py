#!/usr/bin/env python3
"""
LLM SQL Generator - Enhanced SQL generation using LLM
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from .query_matcher import QueryContext, MetadataMatch, QueryPlan
from .semantic_enricher import SemanticMetadata

logger = logging.getLogger(__name__)

@dataclass
class SQLGenerationResult:
    """Result of LLM SQL generation"""
    sql: str
    explanation: str
    confidence_score: float
    complexity_level: str  # 'simple', 'medium', 'complex'
    estimated_execution_time: Optional[str] = None
    estimated_rows: Optional[str] = None
    alternative_sqls: List[str] = None

class LLMSQLGenerator:
    """LLM-powered SQL generation with domain expertise"""
    
    def __init__(self):
        self.llm_model = None
        self.domain_templates = self._load_domain_templates()
        self.sql_patterns = self._load_sql_patterns()
        self.business_rules = self._load_business_rules()
    
    async def close(self):
        """Close LLM model resources"""
        if self.llm_model:
            try:
                await self.llm_model.close()
            except Exception as e:
                logger.warning(f"Error closing LLM model: {e}")
            finally:
                self.llm_model = None
        
    async def initialize(self, llm_model=None):
        """Initialize with LLM model"""
        if llm_model:
            self.llm_model = llm_model
        else:
            # Use isa_model AIFactory
            try:
                from isa_model.inference import AIFactory
                self.llm_model = AIFactory().get_llm(
                    model_name="gpt-4o-mini",
                    config={"temperature": 0.1, "streaming": False}  # 低温度确保准确性
                )
                logger.info("LLM model initialized successfully with isa_model AIFactory")
            except ImportError:
                logger.warning("isa_model not available, using fallback generation")
                self.llm_model = None
    
    async def generate_sql_from_context(self, query_context: QueryContext, 
                                       metadata_matches: List[MetadataMatch],
                                       semantic_metadata: SemanticMetadata,
                                       original_query: str) -> SQLGenerationResult:
        """
        Generate SQL using LLM with enhanced context
        
        Args:
            query_context: Extracted query context
            metadata_matches: Matched metadata entities
            semantic_metadata: Full semantic metadata
            original_query: Original user query
            
        Returns:
            SQL generation result
        """
        try:
            # Build enhanced prompt
            prompt = await self._build_enhanced_prompt(
                original_query, query_context, metadata_matches, semantic_metadata
            )
            
            # Generate SQL using LLM
            if self.llm_model:
                sql_result = await self._generate_with_llm(prompt)
            else:
                sql_result = await self._generate_with_templates(
                    query_context, metadata_matches, semantic_metadata
                )
            
            # Post-process and validate
            processed_result = await self._post_process_sql(sql_result, semantic_metadata)
            
            logger.info(f"SQL generated successfully with confidence: {processed_result.confidence_score}")
            return processed_result
            
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return self._create_fallback_sql(query_context, metadata_matches)
    
    async def enhance_sql_with_business_rules(self, sql: str, 
                                            business_domain: str) -> SQLGenerationResult:
        """
        Enhance generated SQL with domain-specific business rules
        
        Args:
            sql: Base SQL query
            business_domain: Business domain (e.g., 'customs', 'finance', 'ecommerce')
            
        Returns:
            Enhanced SQL with business rules applied
        """
        try:
            business_rules = self.business_rules.get(business_domain, {})
            
            if not business_rules:
                return SQLGenerationResult(
                    sql=sql,
                    explanation="No domain-specific rules applied",
                    confidence_score=0.6,
                    complexity_level="medium"
                )
            
            # Apply business rules
            enhanced_sql = await self._apply_business_rules(sql, business_rules)
            
            return SQLGenerationResult(
                sql=enhanced_sql,
                explanation=f"Applied {business_domain} business rules",
                confidence_score=0.8,
                complexity_level="medium"
            )
            
        except Exception as e:
            logger.error(f"Business rule enhancement failed: {e}")
            return SQLGenerationResult(
                sql=sql,
                explanation=f"Enhancement failed: {str(e)}",
                confidence_score=0.5,
                complexity_level="medium"
            )
    
    async def _build_enhanced_prompt(self, original_query: str, 
                                   query_context: QueryContext,
                                   metadata_matches: List[MetadataMatch],
                                   semantic_metadata: SemanticMetadata) -> str:
        """Build comprehensive prompt for LLM"""
        
        # Detect domain and language
        domain = self._detect_domain(semantic_metadata, metadata_matches)
        language = self._detect_language(original_query)
        
        # Build table schema information
        schema_info = self._format_schema_information(metadata_matches, semantic_metadata)
        
        # Get relevant examples
        examples = self._get_relevant_examples(query_context, domain)
        
        # Build business context
        business_context = self._build_business_context(domain, metadata_matches)
        
        prompt = f"""你是一个专业的SQL查询生成专家，专门处理{domain}数据分析。

用户查询：{original_query}
语言：{language}

查询分析结果：
- 业务意图：{query_context.business_intent}
- 涉及实体：{', '.join(query_context.entities_mentioned)}
- 涉及属性：{', '.join(query_context.attributes_mentioned)}
- 操作类型：{', '.join(query_context.operations)}
- 聚合函数：{', '.join(query_context.aggregations)}
- 过滤条件：{len(query_context.filters)}个
- 时间引用：{', '.join(query_context.temporal_references)}

可用数据表结构：
{schema_info}

业务上下文：
{business_context}

相似查询示例：
{examples}

请生成准确的SQL查询，要求：
1. 使用正确的表连接关系
2. 确保字段名称准确无误
3. 正确处理时间范围和过滤条件
4. 使用合适的聚合函数和分组
5. 添加必要的性能优化（如LIMIT、索引提示）
6. 遵循{domain}业务规则和数据完整性约束

请返回JSON格式：
{{
    "sql": "生成的SQL查询",
    "explanation": "SQL查询解释",
    "confidence": 0.0-1.0,
    "complexity": "simple/medium/complex",
    "estimated_rows": "预估结果行数",
    "optimizations": ["优化建议列表"]
}}
"""
        
        return prompt
    
    async def _generate_with_llm(self, prompt: str) -> SQLGenerationResult:
        """Generate SQL using LLM model"""
        try:
            # Call LLM model using isa_model interface
            response = await self.llm_model.ainvoke(prompt)
            
            # Parse response - isa_model returns string
            if isinstance(response, str):
                try:
                    # Try to parse as JSON first
                    response_data = json.loads(response)
                except json.JSONDecodeError:
                    # If not JSON, extract SQL from text
                    sql = self._extract_sql_from_text(response)
                    response_data = {
                        "sql": sql,
                        "explanation": "Generated from LLM text response",
                        "confidence": 0.8,
                        "complexity": "medium"
                    }
            else:
                response_data = response
            
            return SQLGenerationResult(
                sql=response_data.get("sql", ""),
                explanation=response_data.get("explanation", ""),
                confidence_score=response_data.get("confidence", 0.8),
                complexity_level=response_data.get("complexity", "medium"),
                estimated_rows=response_data.get("estimated_rows"),
                alternative_sqls=response_data.get("alternatives", [])
            )
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    async def _generate_with_templates(self, query_context: QueryContext,
                                     metadata_matches: List[MetadataMatch],
                                     semantic_metadata: SemanticMetadata) -> SQLGenerationResult:
        """Fallback template-based generation"""
        
        # Find best matching template
        template = self._find_best_template(query_context, metadata_matches)
        
        if not template:
            raise Exception("No suitable template found")
        
        # Fill template parameters
        sql = self._fill_template_parameters(template, query_context, metadata_matches)
        
        return SQLGenerationResult(
            sql=sql,
            explanation="Generated using template matching",
            confidence_score=0.6,
            complexity_level="medium"
        )
    
    async def _post_process_sql(self, sql_result: SQLGenerationResult, 
                              semantic_metadata: SemanticMetadata) -> SQLGenerationResult:
        """Post-process and validate generated SQL"""
        
        sql = sql_result.sql
        
        # Basic validation and cleanup
        sql = self._cleanup_sql(sql)
        
        # Add safety measures
        sql = self._add_safety_measures(sql)
        
        # Validate against schema
        validation_errors = self._validate_against_schema(sql, semantic_metadata)
        
        if validation_errors:
            logger.warning(f"SQL validation errors: {validation_errors}")
            # Try to auto-fix
            sql = self._auto_fix_sql_errors(sql, validation_errors, semantic_metadata)
        
        # Update confidence based on validation
        confidence = sql_result.confidence_score
        if validation_errors:
            confidence *= 0.8  # Reduce confidence if there were errors
        
        return SQLGenerationResult(
            sql=sql,
            explanation=sql_result.explanation,
            confidence_score=confidence,
            complexity_level=sql_result.complexity_level,
            estimated_execution_time=sql_result.estimated_execution_time,
            estimated_rows=sql_result.estimated_rows,
            alternative_sqls=sql_result.alternative_sqls
        )
    
    def _detect_domain(self, semantic_metadata: SemanticMetadata, 
                      metadata_matches: List[MetadataMatch]) -> str:
        """Detect business domain from metadata"""
        
        domain_classification = semantic_metadata.domain_classification
        primary_domain = domain_classification.get('primary_domain', 'general')
        
        # Map domains to known business types
        domain_mapping = {
            'ecommerce': '电商',
            'finance': '金融',
            'hr': '人力资源',
            'crm': '客户关系',
            'customs': '海关贸易',
            'logistics': '物流',
            'manufacturing': '制造业'
        }
        
        return domain_mapping.get(primary_domain, '通用业务')
    
    def _detect_language(self, query: str) -> str:
        """Detect query language"""
        # Simple language detection
        chinese_chars = sum(1 for char in query if '\u4e00' <= char <= '\u9fff')
        if chinese_chars > len(query) * 0.3:
            return '中文'
        return '英文'
    
    def _format_schema_information(self, metadata_matches: List[MetadataMatch],
                                 semantic_metadata: SemanticMetadata) -> str:
        """Format schema information for prompt"""
        
        schema_lines = []
        
        # Group matches by table
        tables = {}
        for match in metadata_matches:
            if match.entity_type == 'table':
                tables[match.entity_name] = {
                    'metadata': match.metadata,
                    'attributes': match.relevant_attributes
                }
        
        # Format each table
        for table_name, table_info in tables.items():
            schema_lines.append(f"\n表: {table_name}")
            
            # Add table description if available
            table_metadata = table_info['metadata']
            if table_metadata.get('table_comment'):
                schema_lines.append(f"  描述: {table_metadata['table_comment']}")
            
            # Add columns
            columns = []
            for col in semantic_metadata.original_metadata.get('columns', []):
                if col['table_name'] == table_name:
                    col_desc = f"{col['column_name']} ({col['data_type']})"
                    if col.get('column_comment'):
                        col_desc += f" - {col['column_comment']}"
                    columns.append(f"    {col_desc}")
            
            if columns:
                schema_lines.append("  字段:")
                schema_lines.extend(columns[:10])  # Limit to 10 columns
        
        return '\n'.join(schema_lines)
    
    def _get_relevant_examples(self, query_context: QueryContext, domain: str) -> str:
        """Get relevant SQL examples"""
        
        examples = self.domain_templates.get(domain, {}).get('examples', [])
        
        if not examples:
            return "暂无相关示例"
        
        # Filter examples by query intent
        relevant_examples = []
        for example in examples[:3]:  # Limit to 3 examples
            relevant_examples.append(f"示例: {example.get('description', '')}")
            relevant_examples.append(f"SQL: {example.get('sql', '')}")
            relevant_examples.append("")
        
        return '\n'.join(relevant_examples)
    
    def _build_business_context(self, domain: str, metadata_matches: List[MetadataMatch]) -> str:
        """Build business context information"""
        
        context_lines = [f"业务领域: {domain}"]
        
        # Add domain-specific business rules
        domain_rules = self.business_rules.get(domain, {})
        if domain_rules:
            context_lines.append("\n业务规则:")
            for rule_name, rule_desc in list(domain_rules.items())[:5]:
                context_lines.append(f"- {rule_name}: {rule_desc}")
        
        # Add table relationships
        if len(metadata_matches) > 1:
            context_lines.append("\n表关系:")
            for match in metadata_matches:
                if match.suggested_joins:
                    for join in match.suggested_joins:
                        context_lines.append(f"- {join}")
        
        return '\n'.join(context_lines)
    
    def _extract_sql_from_text(self, text: str) -> str:
        """Extract SQL from text response"""
        import re
        
        # Look for SQL in code blocks
        sql_pattern = r'```sql\s*(.*?)\s*```'
        match = re.search(sql_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # Look for SELECT statements
        select_pattern = r'(SELECT\s+.*?;?)'
        match = re.search(select_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # Return original text if no SQL found
        return text.strip()
    
    def _find_best_template(self, query_context: QueryContext,
                          metadata_matches: List[MetadataMatch]) -> Optional[Dict]:
        """Find best matching SQL template"""
        
        # Simple template matching based on operations and intent
        intent = query_context.business_intent
        operations = query_context.operations
        
        templates = self.sql_patterns.get(intent, [])
        
        for template in templates:
            if any(op in template.get('operations', []) for op in operations):
                return template
        
        return None
    
    def _fill_template_parameters(self, template: Dict, query_context: QueryContext,
                                metadata_matches: List[MetadataMatch]) -> str:
        """Fill template with actual parameters"""
        
        sql_template = template.get('sql', '')
        
        # Basic parameter substitution
        params = {
            'table_name': metadata_matches[0].entity_name if metadata_matches else 'table',
            'columns': ', '.join(query_context.attributes_mentioned) or '*',
            'limit': '100'
        }
        
        # Simple string replacement
        for key, value in params.items():
            sql_template = sql_template.replace(f'{{{key}}}', str(value))
        
        return sql_template
    
    def _cleanup_sql(self, sql: str) -> str:
        """Clean up generated SQL"""
        # Remove extra whitespace
        sql = ' '.join(sql.split())
        
        # Ensure semicolon at end
        if not sql.endswith(';'):
            sql += ';'
        
        return sql
    
    def _add_safety_measures(self, sql: str) -> str:
        """Add safety measures to SQL"""
        # Add LIMIT if not present
        if 'LIMIT' not in sql.upper() and 'TOP' not in sql.upper():
            sql = sql.rstrip(';') + ' LIMIT 1000;'
        
        return sql
    
    def _validate_against_schema(self, sql: str, 
                               semantic_metadata: SemanticMetadata) -> List[str]:
        """Validate SQL against schema"""
        errors = []
        
        # Simple validation - could be enhanced
        available_tables = [t['table_name'] for t in semantic_metadata.original_metadata.get('tables', [])]
        available_columns = [(c['table_name'], c['column_name']) 
                           for c in semantic_metadata.original_metadata.get('columns', [])]
        
        # Check if referenced tables exist (basic check)
        import re
        table_refs = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql, re.IGNORECASE)
        for match in table_refs:
            table_name = match[0] or match[1]
            if table_name not in available_tables:
                errors.append(f"Table '{table_name}' does not exist")
        
        return errors
    
    def _auto_fix_sql_errors(self, sql: str, errors: List[str], 
                           semantic_metadata: SemanticMetadata) -> str:
        """Auto-fix common SQL errors"""
        
        available_tables = [t['table_name'] for t in semantic_metadata.original_metadata.get('tables', [])]
        
        # Fix table name errors
        for error in errors:
            if "does not exist" in error:
                # Extract table name from error
                import re
                match = re.search(r"Table '(\w+)' does not exist", error)
                if match:
                    wrong_table = match.group(1)
                    # Find similar table name
                    for table in available_tables:
                        if wrong_table.lower() in table.lower() or table.lower() in wrong_table.lower():
                            sql = sql.replace(wrong_table, table)
                            break
        
        return sql
    
    def _create_fallback_sql(self, query_context: QueryContext,
                           metadata_matches: List[MetadataMatch]) -> SQLGenerationResult:
        """Create simple fallback SQL"""
        
        if metadata_matches:
            table_name = metadata_matches[0].entity_name
            sql = f"SELECT * FROM {table_name} LIMIT 10;"
        else:
            sql = "SELECT 1 as result;"
        
        return SQLGenerationResult(
            sql=sql,
            explanation="Fallback SQL generated due to errors",
            confidence_score=0.3,
            complexity_level="simple"
        )
    
    async def _apply_business_rules(self, sql: str, business_rules: Dict) -> str:
        """Apply domain-specific business rules to SQL"""
        
        # Example business rules application
        enhanced_sql = sql
        
        # Add common business filters
        common_filters = business_rules.get('common_filters', [])
        for filter_rule in common_filters:
            if filter_rule not in enhanced_sql:
                # Add filter to WHERE clause
                if 'WHERE' in enhanced_sql.upper():
                    enhanced_sql = enhanced_sql.replace('WHERE', f'WHERE {filter_rule} AND', 1)
                else:
                    enhanced_sql = enhanced_sql.replace('FROM', f'FROM') + f' WHERE {filter_rule}'
        
        return enhanced_sql
    
    def _load_domain_templates(self) -> Dict[str, Any]:
        """Load domain-specific SQL templates"""
        return {
            '海关贸易': {
                'examples': [
                    {
                        'description': '查询企业进口数据',
                        'sql': 'SELECT c.company_name, SUM(d.rmb_amount) as total FROM declarations d JOIN companies c ON d.company_code = c.company_code WHERE d.trade_type = \'进口\' GROUP BY c.company_name ORDER BY total DESC LIMIT 10;'
                    },
                    {
                        'description': '查询商品进口统计',
                        'sql': 'SELECT h.hs_description_cn, COUNT(*) as count FROM goods_details g JOIN hs_codes h ON g.hs_code = h.hs_code GROUP BY h.hs_description_cn ORDER BY count DESC LIMIT 20;'
                    }
                ]
            }
        }
    
    def _load_sql_patterns(self) -> Dict[str, List[Dict]]:
        """Load SQL patterns by business intent"""
        return {
            'reporting': [
                {
                    'operations': ['select', 'group'],
                    'sql': 'SELECT {columns}, COUNT(*) FROM {table_name} GROUP BY {columns} ORDER BY COUNT(*) DESC LIMIT {limit};'
                }
            ],
            'analytics': [
                {
                    'operations': ['select', 'aggregate'],
                    'sql': 'SELECT {columns}, SUM({metric}) FROM {table_name} GROUP BY {columns} ORDER BY SUM({metric}) DESC LIMIT {limit};'
                }
            ],
            'lookup': [
                {
                    'operations': ['select'],
                    'sql': 'SELECT {columns} FROM {table_name} WHERE {conditions} LIMIT {limit};'
                }
            ]
        }
    
    def _load_business_rules(self) -> Dict[str, Dict]:
        """Load business rules by domain"""
        return {
            '海关贸易': {
                '数据完整性': '确保报关单号唯一且格式正确',
                '时间范围': '查询时间不超过3年',
                '金额有效性': '交易金额必须大于0',
                'common_filters': [
                    'status = \'已放行\'',
                    'rmb_amount > 0'
                ]
            },
            '电商': {
                '订单状态': '只查询有效订单',
                '用户隐私': '不显示敏感用户信息',
                'common_filters': [
                    'order_status IN (\'completed\', \'shipped\')'
                ]
            }
        }