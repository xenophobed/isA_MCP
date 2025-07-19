#!/usr/bin/env python3
"""
Query Matcher - Step 4: Find related metadata to support SQL generation
"""

import re
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import logging

from .metadata_embedding import AIMetadataEmbeddingService, SearchResult
from .semantic_enricher import SemanticMetadata

logger = logging.getLogger(__name__)

@dataclass
class QueryContext:
    """Context information extracted from a query"""
    entities_mentioned: List[str]
    attributes_mentioned: List[str]
    operations: List[str]
    filters: List[Dict[str, Any]]
    aggregations: List[str]
    temporal_references: List[str]
    business_intent: str
    confidence_score: float

@dataclass
class MetadataMatch:
    """A match between query context and metadata"""
    entity_name: str
    entity_type: str
    match_type: str  # 'exact', 'semantic', 'fuzzy'
    similarity_score: float
    relevant_attributes: List[str]
    suggested_joins: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@dataclass
class QueryPlan:
    """Generated query execution plan"""
    primary_tables: List[str]
    required_joins: List[Dict[str, Any]]
    select_columns: List[str]
    where_conditions: List[str]
    aggregations: List[str]
    order_by: List[str]
    confidence_score: float
    alternative_plans: List[Dict[str, Any]]

class QueryMatcher:
    """Step 4: Find related metadata to support SQL generation"""
    
    def __init__(self, embedding_service: AIMetadataEmbeddingService):
        self.embedding_service = embedding_service
        self.business_terms = self._load_business_terms()
        self.sql_patterns = self._load_sql_patterns()
        self.entity_synonyms = self._load_entity_synonyms()
        
    async def match_query_to_metadata(self, query: str, semantic_metadata: SemanticMetadata) -> Tuple[QueryContext, List[MetadataMatch]]:
        """
        Match natural language query to available metadata
        
        Args:
            query: Natural language query
            semantic_metadata: Available semantic metadata
            
        Returns:
            Tuple of (query context, metadata matches)
        """
        # Extract query context
        query_context = await self._extract_query_context(query)
        
        # Find metadata matches
        metadata_matches = await self._find_metadata_matches(query, query_context, semantic_metadata)
        
        # Rank and filter matches
        filtered_matches = self._rank_and_filter_matches(metadata_matches, query_context)
        
        logger.info(f"Found {len(filtered_matches)} metadata matches for query")
        
        return query_context, filtered_matches
    
    async def generate_query_plan(self, query_context: QueryContext, 
                                metadata_matches: List[MetadataMatch],
                                semantic_metadata: SemanticMetadata) -> QueryPlan:
        """
        Generate query execution plan from context and matches
        
        Args:
            query_context: Extracted query context
            metadata_matches: Matched metadata entities
            semantic_metadata: Full semantic metadata
            
        Returns:
            Query execution plan
        """
        # Identify primary tables
        primary_tables = self._identify_primary_tables(metadata_matches, query_context)
        
        # Determine required joins
        required_joins = self._determine_joins(primary_tables, metadata_matches, semantic_metadata)
        
        # Map query attributes to columns
        select_columns = self._map_select_columns(query_context, metadata_matches)
        
        # Generate where conditions
        where_conditions = self._generate_where_conditions(query_context, metadata_matches)
        
        # Handle aggregations
        aggregations = self._handle_aggregations(query_context, metadata_matches)
        
        # Generate order by
        order_by = self._generate_order_by(query_context, metadata_matches)
        
        # Calculate confidence
        confidence_score = self._calculate_plan_confidence(
            primary_tables, required_joins, select_columns, metadata_matches
        )
        
        # Generate alternative plans
        alternative_plans = self._generate_alternative_plans(
            query_context, metadata_matches, semantic_metadata
        )
        
        return QueryPlan(
            primary_tables=primary_tables,
            required_joins=required_joins,
            select_columns=select_columns,
            where_conditions=where_conditions,
            aggregations=aggregations,
            order_by=order_by,
            confidence_score=confidence_score,
            alternative_plans=alternative_plans
        )
    
    async def find_related_entities(self, entity_name: str, relationship_type: str = 'any') -> List[SearchResult]:
        """
        Find entities related to a given entity
        
        Args:
            entity_name: Name of the entity to find relations for
            relationship_type: Type of relationship to look for
            
        Returns:
            List of related entities
        """
        # Search for similar entities using embeddings
        related_entities = await self.embedding_service.search_similar_entities(
            f"related to {entity_name} {relationship_type}",
            entity_type=None,
            limit=10,
            similarity_threshold=0.6
        )
        
        return related_entities
    
    async def suggest_query_improvements(self, query: str, query_plan: QueryPlan) -> List[str]:
        """
        Suggest improvements to the query based on available metadata
        
        Args:
            query: Original query
            query_plan: Generated query plan
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check for missing filters
        if query_plan.confidence_score < 0.7:
            suggestions.append("Consider adding more specific filters to improve query accuracy")
        
        # Suggest additional columns
        if len(query_plan.select_columns) < 3:
            suggestions.append("You might want to include additional columns for more comprehensive results")
        
        # Suggest performance optimizations
        if len(query_plan.required_joins) > 3:
            suggestions.append("Consider breaking this into multiple queries for better performance")
        
        # Suggest temporal filters
        temporal_entities = [match for match in query_plan.primary_tables 
                           if 'temporal' in str(match).lower()]
        if temporal_entities and not any('date' in condition.lower() for condition in query_plan.where_conditions):
            suggestions.append("Consider adding date filters to limit the time range")
        
        return suggestions
    
    async def _extract_query_context(self, query: str) -> QueryContext:
        """Extract context information from natural language query"""
        query_lower = query.lower()
        
        # Extract entities mentioned
        entities_mentioned = self._extract_entities(query_lower)
        
        # Extract attributes mentioned
        attributes_mentioned = self._extract_attributes(query_lower)
        
        # Extract operations
        operations = self._extract_operations(query_lower)
        
        # Extract filters
        filters = self._extract_filters(query_lower)
        
        # Extract aggregations
        aggregations = self._extract_aggregations(query_lower)
        
        # Extract temporal references
        temporal_references = self._extract_temporal_references(query_lower)
        
        # Determine business intent
        business_intent = self._determine_business_intent(query_lower)
        
        # Calculate confidence
        confidence_score = self._calculate_context_confidence(
            entities_mentioned, attributes_mentioned, operations
        )
        
        return QueryContext(
            entities_mentioned=entities_mentioned,
            attributes_mentioned=attributes_mentioned,
            operations=operations,
            filters=filters,
            aggregations=aggregations,
            temporal_references=temporal_references,
            business_intent=business_intent,
            confidence_score=confidence_score
        )
    
    async def _find_metadata_matches(self, query: str, query_context: QueryContext, 
                                   semantic_metadata: SemanticMetadata) -> List[MetadataMatch]:
        """Find metadata that matches the query context"""
        matches = []
        
        # Search for entity matches using embeddings
        for entity in query_context.entities_mentioned:
            # Exact name matches
            exact_matches = await self._find_exact_entity_matches(entity, semantic_metadata)
            matches.extend(exact_matches)
            
            # Semantic matches using embeddings
            semantic_matches = await self._find_semantic_entity_matches(entity, semantic_metadata)
            matches.extend(semantic_matches)
            
            # Fuzzy matches
            fuzzy_matches = self._find_fuzzy_entity_matches(entity, semantic_metadata)
            matches.extend(fuzzy_matches)
        
        # Search for attribute matches
        for attribute in query_context.attributes_mentioned:
            attribute_matches = await self._find_attribute_matches(attribute, semantic_metadata)
            matches.extend(attribute_matches)
        
        # Fallback: If no entities or attributes found, do direct embedding search with full query
        if not query_context.entities_mentioned and not query_context.attributes_mentioned:
            logger.info(f"No entities/attributes extracted, using full query embedding search")
            fallback_matches = await self._find_direct_query_matches(query, semantic_metadata)
            matches.extend(fallback_matches)
        
        # Always try direct query search for better coverage
        direct_matches = await self._find_direct_query_matches(query, semantic_metadata)
        matches.extend(direct_matches)
        
        # Remove duplicates and rank
        unique_matches = self._deduplicate_matches(matches)
        
        return unique_matches
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract potential entity names from query"""
        entities = []
        
        # English business entities
        english_entities = [
            'customer', 'customers', 'client', 'clients', 'user', 'users',
            'order', 'orders', 'purchase', 'purchases', 'sale', 'sales',
            'product', 'products', 'item', 'items', 'inventory',
            'payment', 'payments', 'transaction', 'transactions',
            'account', 'accounts', 'invoice', 'invoices',
            'employee', 'employees', 'staff', 'department', 'departments'
        ]
        
        # Chinese business entities (customs/trade specific)
        chinese_entities = [
            '公司', '企业', '公司企业', '企业公司',
            '申报', '申报单', '报关', '报关单', '海关申报',
            '货物', '商品', '物品', '商品编码', 'HS编码',
            '进口', '出口', '贸易', '进出口',
            '金额', '总金额', '价值', '价格', '费用',
            '数量', '重量', '单价',
            '客户', '用户', '买家', '卖家'
        ]
        
        # Check English entities
        for entity in english_entities:
            if entity in query:
                entities.append(entity)
        
        # Check Chinese entities
        for entity in chinese_entities:
            if entity in query:
                entities.append(entity)
        
        # Extract quoted entities
        quoted_pattern = r'"([^"]*)"'
        quoted_entities = re.findall(quoted_pattern, query)
        entities.extend(quoted_entities)
        
        # Extract potential table names (words ending with 's' or containing '_')
        potential_tables = re.findall(r'\b[a-z]+_[a-z]+\b|\b[a-z]+s\b', query)
        entities.extend(potential_tables)
        
        return list(set(entities))
    
    def _extract_attributes(self, query: str) -> List[str]:
        """Extract potential attribute/column names from query"""
        attributes = []
        
        # English attributes
        english_attributes = [
            'name', 'id', 'email', 'phone', 'address', 'city', 'state', 'country',
            'price', 'cost', 'amount', 'value', 'quantity', 'count', 'total',
            'date', 'time', 'created', 'updated', 'modified',
            'status', 'type', 'category', 'description'
        ]
        
        # Chinese attributes (customs/trade specific)
        chinese_attributes = [
            '名称', '姓名', '公司名称', '企业名称',
            '代码', '编码', '公司代码', '企业代码', 'HS编码',
            '金额', '总金额', '价值', '价格', '单价', '费用',
            '数量', '重量', '体积',
            '日期', '时间', '申报日期', '创建时间',
            '状态', '类型', '贸易类型', '进出口类型',
            '地址', '联系方式', '电话', '邮箱',
            '描述', '说明', '备注'
        ]
        
        # Check English attributes
        for attr in english_attributes:
            if attr in query:
                attributes.append(attr)
        
        # Check Chinese attributes
        for attr in chinese_attributes:
            if attr in query:
                attributes.append(attr)
        
        # Extract words that might be column names (snake_case or camelCase)
        potential_columns = re.findall(r'\b[a-z]+_[a-z]+\b|\b[a-z]+[A-Z][a-z]*\b', query)
        attributes.extend(potential_columns)
        
        return list(set(attributes))
    
    def _extract_operations(self, query: str) -> List[str]:
        """Extract operation types from query"""
        operations = []
        
        operation_patterns = {
            'select': ['show', 'get', 'find', 'list', 'display', 'retrieve'],
            'filter': ['where', 'with', 'having', 'filter', 'criteria'],
            'sort': ['order', 'sort', 'arrange', 'rank'],
            'group': ['group', 'categorize', 'bucket'],
            'join': ['join', 'combine', 'merge', 'link', 'relate'],
            'aggregate': ['count', 'sum', 'average', 'max', 'min', 'total']
        }
        
        for operation, keywords in operation_patterns.items():
            if any(keyword in query for keyword in keywords):
                operations.append(operation)
        
        return operations
    
    def _extract_filters(self, query: str) -> List[Dict[str, Any]]:
        """Extract filter conditions from query"""
        filters = []
        
        # Date filters
        date_pattern = r'(after|before|since|until|on|in)\s+(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})'
        date_matches = re.findall(date_pattern, query)
        for operator, date_value in date_matches:
            filters.append({
                'type': 'date',
                'operator': operator,
                'value': date_value
            })
        
        # Numeric filters
        numeric_pattern = r'(greater|less|more|fewer|above|below|equal)\s+than\s+(\d+)'
        numeric_matches = re.findall(numeric_pattern, query)
        for operator, value in numeric_matches:
            filters.append({
                'type': 'numeric',
                'operator': operator,
                'value': int(value)
            })
        
        # Text filters
        equals_pattern = r'(\w+)\s+(is|equals?|=)\s+["\']?([^"\']+)["\']?'
        equals_matches = re.findall(equals_pattern, query)
        for field, operator, value in equals_matches:
            filters.append({
                'type': 'text',
                'field': field,
                'operator': 'equals',
                'value': value.strip()
            })
        
        return filters
    
    def _extract_aggregations(self, query: str) -> List[str]:
        """Extract aggregation functions from query"""
        aggregations = []
        
        agg_patterns = {
            'count': r'\b(count|number of|how many)\b',
            'sum': r'\b(sum|total|add up)\b',
            'average': r'\b(average|avg|mean)\b',
            'max': r'\b(max|maximum|highest|largest)\b',
            'min': r'\b(min|minimum|lowest|smallest)\b'
        }
        
        for agg_type, pattern in agg_patterns.items():
            if re.search(pattern, query):
                aggregations.append(agg_type)
        
        return aggregations
    
    def _extract_temporal_references(self, query: str) -> List[str]:
        """Extract temporal references from query"""
        temporal_refs = []
        
        temporal_patterns = [
            r'\b(yesterday|today|tomorrow)\b',
            r'\b(last|this|next)\s+(week|month|year|quarter)\b',
            r'\b\d{4}[-/]\d{2}[-/]\d{2}\b',
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b(recent|latest|current|historical)\b'
        ]
        
        for pattern in temporal_patterns:
            matches = re.findall(pattern, query)
            if matches:
                if isinstance(matches[0], str):
                    temporal_refs.extend(matches)
                else:
                    temporal_refs.extend([' '.join(m) if isinstance(m, (list, tuple)) else str(m) for m in matches])
        
        return temporal_refs
    
    def _determine_business_intent(self, query: str) -> str:
        """Determine the business intent of the query"""
        intent_patterns = {
            'reporting': ['report', 'dashboard', 'summary', 'overview', 'analysis'],
            'analytics': ['analyze', 'trend', 'pattern', 'insight', 'correlation'],
            'lookup': ['find', 'get', 'show', 'display', 'lookup'],
            'monitoring': ['monitor', 'track', 'watch', 'alert', 'status'],
            'optimization': ['optimize', 'improve', 'recommend', 'suggest', 'best']
        }
        
        for intent, keywords in intent_patterns.items():
            if any(keyword in query for keyword in keywords):
                return intent
        
        return 'general'
    
    def _calculate_context_confidence(self, entities: List[str], attributes: List[str], operations: List[str]) -> float:
        """Calculate confidence score for extracted context"""
        base_confidence = 0.3
        
        # Boost confidence based on extracted elements
        if entities:
            base_confidence += 0.3 * min(len(entities) / 3, 1.0)
        
        if attributes:
            base_confidence += 0.2 * min(len(attributes) / 5, 1.0)
        
        if operations:
            base_confidence += 0.2 * min(len(operations) / 3, 1.0)
        
        return min(base_confidence, 1.0)
    
    async def _find_exact_entity_matches(self, entity: str, semantic_metadata: SemanticMetadata) -> List[MetadataMatch]:
        """Find exact matches for entity names"""
        matches = []
        
        # Check table names
        for table in semantic_metadata.original_metadata.get('tables', []):
            table_name = table['table_name'].lower()
            if entity in table_name or table_name in entity:
                matches.append(MetadataMatch(
                    entity_name=table['table_name'],
                    entity_type='table',
                    match_type='exact',
                    similarity_score=1.0 if entity == table_name else 0.8,
                    relevant_attributes=[],
                    suggested_joins=[],
                    metadata=table
                ))
        
        # Check business entities
        for business_entity in semantic_metadata.business_entities:
            entity_name = business_entity['entity_name'].lower()
            if entity in entity_name or entity_name in entity:
                matches.append(MetadataMatch(
                    entity_name=business_entity['entity_name'],
                    entity_type='entity',
                    match_type='exact',
                    similarity_score=1.0 if entity == entity_name else 0.8,
                    relevant_attributes=business_entity.get('key_attributes', []),
                    suggested_joins=[],
                    metadata=business_entity
                ))
        
        return matches
    
    async def _find_semantic_entity_matches(self, entity: str, semantic_metadata: SemanticMetadata) -> List[MetadataMatch]:
        """Find semantic matches using embeddings"""
        matches = []
        
        # Search using embeddings
        search_results = await self.embedding_service.search_similar_entities(
            f"entity {entity} table database",
            entity_type=None,
            limit=5,
            similarity_threshold=0.3
        )
        
        for result in search_results:
            matches.append(MetadataMatch(
                entity_name=result.entity_name,
                entity_type=result.entity_type,
                match_type='semantic',
                similarity_score=result.similarity_score,
                relevant_attributes=[],
                suggested_joins=[],
                metadata=result.metadata
            ))
        
        return matches
    
    async def _find_direct_query_matches(self, query: str, semantic_metadata: SemanticMetadata) -> List[MetadataMatch]:
        """Find matches by searching embeddings directly with the full query"""
        matches = []
        
        try:
            # Search with full query - lower threshold for better coverage
            search_results = await self.embedding_service.search_similar_entities(
                query,
                entity_type=None,
                limit=10,
                similarity_threshold=0.3  # Lower threshold for better Chinese query coverage
            )
            
            for result in search_results:
                matches.append(MetadataMatch(
                    entity_name=result.entity_name,
                    entity_type=result.entity_type,
                    match_type='direct_query',
                    similarity_score=result.similarity_score,
                    relevant_attributes=[],
                    suggested_joins=[],
                    metadata=result.metadata
                ))
                
            logger.info(f"Direct query search found {len(matches)} matches")
            
        except Exception as e:
            logger.error(f"Direct query search failed: {e}")
        
        return matches
    
    def _find_fuzzy_entity_matches(self, entity: str, semantic_metadata: SemanticMetadata) -> List[MetadataMatch]:
        """Find fuzzy matches using string similarity"""
        matches = []
        
        # Check against synonyms
        for synonym_group in self.entity_synonyms.values():
            if entity in synonym_group:
                for synonym in synonym_group:
                    if synonym != entity:
                        # Find tables/entities matching this synonym
                        for table in semantic_metadata.original_metadata.get('tables', []):
                            if synonym in table['table_name'].lower():
                                matches.append(MetadataMatch(
                                    entity_name=table['table_name'],
                                    entity_type='table',
                                    match_type='fuzzy',
                                    similarity_score=0.6,
                                    relevant_attributes=[],
                                    suggested_joins=[],
                                    metadata=table
                                ))
        
        return matches
    
    async def _find_attribute_matches(self, attribute: str, semantic_metadata: SemanticMetadata) -> List[MetadataMatch]:
        """Find matches for attributes/columns"""
        matches = []
        
        # Search columns using embeddings
        search_results = await self.embedding_service.search_similar_entities(
            f"column attribute {attribute} field",
            entity_type='column',
            limit=5,
            similarity_threshold=0.3
        )
        
        for result in search_results:
            # Extract table name from column entity name
            if '.' in result.entity_name:
                table_name = result.entity_name.split('.')[0]
                matches.append(MetadataMatch(
                    entity_name=table_name,
                    entity_type='table',
                    match_type='semantic',
                    similarity_score=result.similarity_score,
                    relevant_attributes=[result.entity_name.split('.')[1]],
                    suggested_joins=[],
                    metadata=result.metadata
                ))
        
        return matches
    
    def _deduplicate_matches(self, matches: List[MetadataMatch]) -> List[MetadataMatch]:
        """Remove duplicate matches and keep best scores"""
        entity_matches = {}
        
        for match in matches:
            key = (match.entity_name, match.entity_type)
            if key not in entity_matches or match.similarity_score > entity_matches[key].similarity_score:
                entity_matches[key] = match
        
        return list(entity_matches.values())
    
    def _rank_and_filter_matches(self, matches: List[MetadataMatch], query_context: QueryContext) -> List[MetadataMatch]:
        """Rank and filter matches based on relevance"""
        # Sort by similarity score
        sorted_matches = sorted(matches, key=lambda x: x.similarity_score, reverse=True)
        
        # Filter by minimum threshold
        filtered_matches = [m for m in sorted_matches if m.similarity_score >= 0.3]
        
        # Limit to top N matches
        return filtered_matches[:10]
    
    def _identify_primary_tables(self, matches: List[MetadataMatch], query_context: QueryContext) -> List[str]:
        """Identify primary tables for the query"""
        # Get highest scoring table matches
        table_matches = [m for m in matches if m.entity_type in ['table', 'entity']]
        table_matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Return top 3 tables
        return [m.entity_name for m in table_matches[:3]]
    
    def _determine_joins(self, primary_tables: List[str], matches: List[MetadataMatch], 
                        semantic_metadata: SemanticMetadata) -> List[Dict[str, Any]]:
        """Determine required joins between tables"""
        joins = []
        
        if len(primary_tables) < 2:
            return joins
        
        # Find relationships between primary tables
        relationships = semantic_metadata.original_metadata.get('relationships', [])
        
        for i, table1 in enumerate(primary_tables):
            for table2 in primary_tables[i+1:]:
                # Find direct relationship
                for rel in relationships:
                    if ((rel['from_table'] == table1 and rel['to_table'] == table2) or
                        (rel['from_table'] == table2 and rel['to_table'] == table1)):
                        joins.append({
                            'type': 'inner',
                            'left_table': rel['from_table'],
                            'right_table': rel['to_table'],
                            'left_column': rel['from_column'],
                            'right_column': rel['to_column'],
                            'confidence': 0.9
                        })
        
        return joins
    
    def _map_select_columns(self, query_context: QueryContext, matches: List[MetadataMatch]) -> List[str]:
        """Map query attributes to actual column names"""
        select_columns = []
        
        # Use relevant attributes from matches
        for match in matches:
            if match.relevant_attributes:
                for attr in match.relevant_attributes:
                    if match.entity_type == 'table':
                        select_columns.append(f"{match.entity_name}.{attr}")
                    else:
                        select_columns.append(attr)
        
        # If no specific attributes, use common ones
        if not select_columns and matches:
            primary_table = matches[0].entity_name
            common_columns = ['id', 'name', 'created_at', 'updated_at']
            for col in common_columns:
                select_columns.append(f"{primary_table}.{col}")
        
        return select_columns[:10]  # Limit number of columns
    
    def _generate_where_conditions(self, query_context: QueryContext, matches: List[MetadataMatch]) -> List[str]:
        """Generate WHERE conditions from query filters"""
        conditions = []
        
        for filter_condition in query_context.filters:
            if filter_condition['type'] == 'date':
                conditions.append(f"date_column {filter_condition['operator']} '{filter_condition['value']}'")
            elif filter_condition['type'] == 'numeric':
                operator_map = {
                    'greater': '>',
                    'less': '<',
                    'more': '>',
                    'fewer': '<',
                    'above': '>',
                    'below': '<',
                    'equal': '='
                }
                op = operator_map.get(filter_condition['operator'], '=')
                conditions.append(f"numeric_column {op} {filter_condition['value']}")
            elif filter_condition['type'] == 'text':
                conditions.append(f"{filter_condition['field']} = '{filter_condition['value']}'")
        
        return conditions
    
    def _handle_aggregations(self, query_context: QueryContext, matches: List[MetadataMatch]) -> List[str]:
        """Handle aggregation functions"""
        aggregations = []
        
        for agg in query_context.aggregations:
            if agg == 'count':
                aggregations.append('COUNT(*)')
            elif agg in ['sum', 'average', 'max', 'min']:
                # Try to find a numeric column
                numeric_column = 'amount'  # Default
                aggregations.append(f'{agg.upper()}({numeric_column})')
        
        return aggregations
    
    def _generate_order_by(self, query_context: QueryContext, matches: List[MetadataMatch]) -> List[str]:
        """Generate ORDER BY clause"""
        order_by = []
        
        if 'sort' in query_context.operations:
            # Default to ID or created_at
            if matches:
                table_name = matches[0].entity_name
                order_by.append(f"{table_name}.created_at DESC")
        
        return order_by
    
    def _calculate_plan_confidence(self, primary_tables: List[str], joins: List[Dict], 
                                 select_columns: List[str], matches: List[MetadataMatch]) -> float:
        """Calculate confidence score for the query plan"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on matched entities
        if matches:
            avg_match_score = sum(m.similarity_score for m in matches) / len(matches)
            confidence += 0.3 * avg_match_score
        
        # Boost confidence for having primary tables
        if primary_tables:
            confidence += 0.1
        
        # Boost confidence for having columns
        if select_columns:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_alternative_plans(self, query_context: QueryContext, matches: List[MetadataMatch], 
                                  semantic_metadata: SemanticMetadata) -> List[Dict[str, Any]]:
        """Generate alternative query plans"""
        alternatives = []
        
        # Alternative with different table combinations
        if len(matches) > 3:
            alt_tables = [m.entity_name for m in matches[1:4] if m.entity_type in ['table', 'entity']]
            if alt_tables:
                alternatives.append({
                    'description': 'Alternative table selection',
                    'primary_tables': alt_tables,
                    'confidence': 0.6
                })
        
        # Alternative with aggregation if not present
        if not query_context.aggregations and matches:
            alternatives.append({
                'description': 'Add aggregation for summary view',
                'aggregations': ['COUNT(*)'],
                'confidence': 0.5
            })
        
        return alternatives
    
    def _load_business_terms(self) -> Dict[str, List[str]]:
        """Load business terminology mappings"""
        return {
            'customer': ['client', 'buyer', 'purchaser', 'consumer', 'user'],
            'product': ['item', 'merchandise', 'good', 'inventory', 'sku'],
            'order': ['purchase', 'transaction', 'sale', 'booking', 'request'],
            'payment': ['transaction', 'charge', 'billing', 'invoice'],
            'employee': ['staff', 'worker', 'personnel', 'team_member'],
            'account': ['profile', 'record', 'entry']
        }
    
    def _load_sql_patterns(self) -> Dict[str, str]:
        """Load common SQL patterns"""
        return {
            'count_all': 'SELECT COUNT(*) FROM {table}',
            'list_recent': 'SELECT * FROM {table} ORDER BY created_at DESC LIMIT 10',
            'find_by_id': 'SELECT * FROM {table} WHERE id = {value}',
            'aggregate_by_group': 'SELECT {group_column}, COUNT(*) FROM {table} GROUP BY {group_column}'
        }
    
    def _load_entity_synonyms(self) -> Dict[str, List[str]]:
        """Load entity synonym mappings"""
        return {
            'customers': ['customer', 'client', 'buyer', 'user', 'account'],
            'products': ['product', 'item', 'inventory', 'catalog', 'sku'],
            'orders': ['order', 'purchase', 'sale', 'transaction', 'booking'],
            'payments': ['payment', 'transaction', 'billing', 'invoice'],
            'employees': ['employee', 'staff', 'worker', 'personnel']
        }