#!/usr/bin/env python3
"""
Semantic Enricher - Step 2: Enrich metadata with semantic meaning
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class SemanticMetadata:
    """Enhanced metadata with semantic information"""
    original_metadata: Dict[str, Any]
    business_entities: List[Dict[str, Any]]
    semantic_tags: Dict[str, List[str]]
    data_patterns: List[Dict[str, Any]]
    business_rules: List[Dict[str, Any]]
    domain_classification: Dict[str, Any]
    confidence_scores: Dict[str, float]

class SemanticEnricher:
    """Step 2: Enrich metadata with semantic meaning"""
    
    def __init__(self):
        self.business_keywords = self._load_business_keywords()
        self.pattern_detectors = self._init_pattern_detectors()
        
    def enrich_metadata(self, metadata: Dict[str, Any]) -> SemanticMetadata:
        """
        Enrich raw metadata with semantic information
        
        Args:
            metadata: Raw metadata from step 1
            
        Returns:
            SemanticMetadata with enriched information
        """
        # Extract business entities
        business_entities = self._extract_business_entities(metadata)
        
        # Generate semantic tags
        semantic_tags = self._generate_semantic_tags(metadata)
        
        # Detect data patterns
        data_patterns = self._detect_data_patterns(metadata)
        
        # Infer business rules
        business_rules = self._infer_business_rules(metadata, business_entities)
        
        # Classify domain
        domain_classification = self._classify_domain(metadata, business_entities)
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(
            business_entities, semantic_tags, data_patterns, business_rules
        )
        
        return SemanticMetadata(
            original_metadata=metadata,
            business_entities=business_entities,
            semantic_tags=semantic_tags,
            data_patterns=data_patterns,
            business_rules=business_rules,
            domain_classification=domain_classification,
            confidence_scores=confidence_scores
        )
    
    def _extract_business_entities(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract business entities from table and column names"""
        entities = []
        tables = metadata.get('tables', [])
        columns = metadata.get('columns', [])
        
        # Group columns by table
        table_columns = defaultdict(list)
        for col in columns:
            table_columns[col['table_name']].append(col)
        
        for table in tables:
            table_name = table['table_name'].lower()
            table_cols = table_columns[table['table_name']]
            
            # Detect entity type based on table name and structure
            entity_type = self._classify_entity_type(table_name, table_cols)
            
            # Extract key attributes
            key_attributes = self._extract_key_attributes(table_cols)
            
            # Detect relationships
            relationships = self._detect_entity_relationships(table, table_cols, tables)
            
            entities.append({
                'entity_name': table['table_name'],
                'entity_type': entity_type,
                'confidence': self._calculate_entity_confidence(table_name, table_cols),
                'key_attributes': key_attributes,
                'relationships': relationships,
                'record_count': table.get('record_count', 0),
                'business_importance': self._assess_business_importance(table, table_cols)
            })
        
        return entities
    
    def _generate_semantic_tags(self, metadata: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate semantic tags for tables and columns"""
        tags = {}
        
        for table in metadata.get('tables', []):
            table_tags = []
            table_name = table['table_name'].lower()
            
            # Business domain tags
            for domain, keywords in self.business_keywords.items():
                if any(keyword in table_name for keyword in keywords):
                    table_tags.append(f"domain:{domain}")
            
            # Data pattern tags
            if 'log' in table_name or 'audit' in table_name:
                table_tags.append("pattern:temporal")
            if 'ref' in table_name or 'lookup' in table_name:
                table_tags.append("pattern:reference")
            if 'master' in table_name or 'dim' in table_name:
                table_tags.append("pattern:dimension")
            if 'fact' in table_name or 'transaction' in table_name:
                table_tags.append("pattern:fact")
            
            tags[f"table:{table['table_name']}"] = table_tags
        
        # Column-level tags
        for column in metadata.get('columns', []):
            col_tags = []
            col_name = column['column_name'].lower()
            data_type = column.get('data_type', '').lower()
            
            # Data type semantic tags
            if 'timestamp' in data_type or 'date' in data_type:
                col_tags.append("semantic:temporal")
            if 'id' in col_name:
                col_tags.append("semantic:identifier")
            if any(geo_word in col_name for geo_word in ['address', 'city', 'country', 'location']):
                col_tags.append("semantic:geospatial")
            if any(money_word in col_name for money_word in ['price', 'cost', 'amount', 'value']):
                col_tags.append("semantic:monetary")
            
            # Business context tags
            for domain, keywords in self.business_keywords.items():
                if any(keyword in col_name for keyword in keywords):
                    col_tags.append(f"business:{domain}")
            
            tags[f"column:{column['table_name']}.{column['column_name']}"] = col_tags
        
        return tags
    
    def _detect_data_patterns(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect data patterns in the schema"""
        patterns = []
        
        # Temporal patterns
        temporal_tables = []
        for table in metadata.get('tables', []):
            table_name = table['table_name'].lower()
            if any(word in table_name for word in ['log', 'history', 'audit', 'event']):
                temporal_tables.append(table['table_name'])
        
        if temporal_tables:
            patterns.append({
                'pattern_type': 'temporal',
                'description': 'Time-series data pattern detected',
                'tables_involved': temporal_tables,
                'confidence': 0.8
            })
        
        # Hierarchical patterns
        hierarchical_indicators = []
        for column in metadata.get('columns', []):
            col_name = column['column_name'].lower()
            if any(word in col_name for word in ['parent_id', 'parent', 'level', 'hierarchy']):
                hierarchical_indicators.append(f"{column['table_name']}.{column['column_name']}")
        
        if hierarchical_indicators:
            patterns.append({
                'pattern_type': 'hierarchical',
                'description': 'Hierarchical data structure detected',
                'columns_involved': hierarchical_indicators,
                'confidence': 0.7
            })
        
        # Master-detail patterns
        master_detail_pairs = self._detect_master_detail_patterns(metadata)
        for pair in master_detail_pairs:
            patterns.append({
                'pattern_type': 'master_detail',
                'description': f'Master-detail relationship: {pair["master"]} -> {pair["detail"]}',
                'tables_involved': [pair['master'], pair['detail']],
                'confidence': pair['confidence']
            })
        
        return patterns
    
    def _infer_business_rules(self, metadata: Dict[str, Any], entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Infer business rules from metadata and entities"""
        rules = []
        
        # Referential integrity rules
        relationships = metadata.get('relationships', [])
        for rel in relationships:
            rules.append({
                'rule_type': 'referential_integrity',
                'description': f'{rel["from_table"]}.{rel["from_column"]} must reference valid {rel["to_table"]}.{rel["to_column"]}',
                'confidence': 0.9,
                'tables_involved': [rel['from_table'], rel['to_table']],
                'sql_constraint': f'FOREIGN KEY ({rel["from_column"]}) REFERENCES {rel["to_table"]}({rel["to_column"]})'
            })
        
        # Uniqueness rules
        for column in metadata.get('columns', []):
            unique_pct = column.get('unique_percentage', 0)
            if (unique_pct is not None and unique_pct > 0.95 and 
                not column.get('is_nullable', True) and
                'id' in column['column_name'].lower()):
                rules.append({
                    'rule_type': 'uniqueness',
                    'description': f'{column["table_name"]}.{column["column_name"]} should be unique',
                    'confidence': 0.85,
                    'tables_involved': [column['table_name']],
                    'sql_constraint': f'UNIQUE ({column["column_name"]})'
                })
        
        # Data validation rules
        for column in metadata.get('columns', []):
            col_name = column['column_name'].lower()
            if 'email' in col_name:
                rules.append({
                    'rule_type': 'data_validation',
                    'description': f'{column["table_name"]}.{column["column_name"]} should be valid email format',
                    'confidence': 0.8,
                    'tables_involved': [column['table_name']],
                    'validation_pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                })
            elif 'phone' in col_name:
                rules.append({
                    'rule_type': 'data_validation',
                    'description': f'{column["table_name"]}.{column["column_name"]} should be valid phone format',
                    'confidence': 0.8,
                    'tables_involved': [column['table_name']],
                    'validation_pattern': r'^\+?[\d\s\-\(\)]+$'
                })
        
        return rules
    
    def _classify_domain(self, metadata: Dict[str, Any], entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Classify the business domain of the dataset"""
        domain_scores = defaultdict(float)
        
        # Analyze table names
        table_names = [t['table_name'].lower() for t in metadata.get('tables', [])]
        all_names = ' '.join(table_names)
        
        # E-commerce indicators
        ecommerce_keywords = ['order', 'product', 'customer', 'cart', 'payment', 'inventory', 'category']
        ecommerce_score = sum(1 for keyword in ecommerce_keywords if keyword in all_names)
        domain_scores['ecommerce'] = ecommerce_score / len(ecommerce_keywords)
        
        # HR/Employee management indicators
        hr_keywords = ['employee', 'user', 'department', 'salary', 'role', 'permission']
        hr_score = sum(1 for keyword in hr_keywords if keyword in all_names)
        domain_scores['hr'] = hr_score / len(hr_keywords)
        
        # Financial indicators
        finance_keywords = ['transaction', 'account', 'balance', 'invoice', 'payment', 'ledger']
        finance_score = sum(1 for keyword in finance_keywords if keyword in all_names)
        domain_scores['finance'] = finance_score / len(finance_keywords)
        
        # CRM indicators
        crm_keywords = ['customer', 'contact', 'lead', 'opportunity', 'campaign', 'activity']
        crm_score = sum(1 for keyword in crm_keywords if keyword in all_names)
        domain_scores['crm'] = crm_score / len(crm_keywords)
        
        # Determine primary domain
        primary_domain = max(domain_scores.items(), key=lambda x: x[1]) if domain_scores else ('unknown', 0)
        
        return {
            'primary_domain': primary_domain[0],
            'confidence': primary_domain[1],
            'domain_scores': dict(domain_scores),
            'is_multi_domain': len([score for score in domain_scores.values() if score > 0.3]) > 1
        }
    
    def _calculate_confidence_scores(self, entities, semantic_tags, patterns, rules) -> Dict[str, float]:
        """Calculate confidence scores for different aspects of semantic analysis"""
        scores = {}
        
        # Entity extraction confidence
        entity_confidences = [e.get('confidence', 0) for e in entities]
        scores['entity_extraction'] = sum(entity_confidences) / len(entity_confidences) if entity_confidences else 0
        
        # Semantic tagging confidence
        tag_counts = sum(len(tags) for tags in semantic_tags.values())
        scores['semantic_tagging'] = min(tag_counts / (len(semantic_tags) * 3), 1.0) if semantic_tags else 0
        
        # Pattern detection confidence
        pattern_confidences = [p.get('confidence', 0) for p in patterns]
        scores['pattern_detection'] = sum(pattern_confidences) / len(pattern_confidences) if pattern_confidences else 0
        
        # Business rules confidence
        rule_confidences = [r.get('confidence', 0) for r in rules]
        scores['business_rules'] = sum(rule_confidences) / len(rule_confidences) if rule_confidences else 0
        
        # Overall confidence
        scores['overall'] = sum(scores.values()) / len(scores) if scores else 0
        
        return scores
    
    def _load_business_keywords(self) -> Dict[str, List[str]]:
        """Load business domain keywords"""
        return {
            'customer': ['customer', 'client', 'buyer', 'user', 'account'],
            'product': ['product', 'item', 'inventory', 'catalog', 'sku'],
            'order': ['order', 'purchase', 'transaction', 'sale', 'booking'],
            'financial': ['price', 'cost', 'amount', 'value', 'payment', 'invoice', 'billing'],
            'temporal': ['date', 'time', 'created', 'updated', 'modified', 'timestamp'],
            'location': ['address', 'city', 'country', 'region', 'location', 'postal'],
            'identifier': ['id', 'code', 'number', 'reference', 'key', 'uuid'],
            'status': ['status', 'state', 'condition', 'flag', 'active', 'enabled']
        }
    
    def _init_pattern_detectors(self) -> Dict[str, callable]:
        """Initialize pattern detection functions"""
        return {
            'temporal': self._detect_temporal_pattern,
            'hierarchical': self._detect_hierarchical_pattern,
            'categorical': self._detect_categorical_pattern,
            'numerical': self._detect_numerical_pattern
        }
    
    def _classify_entity_type(self, table_name: str, columns: List[Dict]) -> str:
        """Classify the entity type of a table"""
        col_names = [col['column_name'].lower() for col in columns]
        
        # Master data entities
        if any(word in table_name for word in ['master', 'dim', 'ref', 'lookup']):
            return 'reference'
        
        # Transaction entities
        if any(word in table_name for word in ['transaction', 'order', 'payment', 'invoice']):
            return 'transaction'
        
        # Event/Log entities
        if any(word in table_name for word in ['log', 'audit', 'history', 'event']):
            return 'event'
        
        # Configuration entities
        if any(word in table_name for word in ['config', 'setting', 'parameter']):
            return 'configuration'
        
        # Bridge/Junction entities
        if len([col for col in col_names if col.endswith('_id')]) >= 2:
            return 'bridge'
        
        return 'entity'
    
    def _extract_key_attributes(self, columns: List[Dict]) -> List[str]:
        """Extract key attributes from column list"""
        key_attrs = []
        
        for col in columns:
            col_name = col['column_name'].lower()
            
            # Primary identifiers
            if ('id' in col_name and col_name != 'id') or col_name.endswith('_id'):
                key_attrs.append(col['column_name'])
            
            # Business keys
            elif any(word in col_name for word in ['code', 'number', 'reference', 'key']):
                key_attrs.append(col['column_name'])
            
            # Names and descriptions
            elif any(word in col_name for word in ['name', 'title', 'description']):
                key_attrs.append(col['column_name'])
        
        return key_attrs[:5]  # Limit to top 5 key attributes
    
    def _detect_entity_relationships(self, table: Dict, columns: List[Dict], all_tables: List[Dict]) -> List[Dict]:
        """Detect relationships for an entity"""
        relationships = []
        table_names = [t['table_name'] for t in all_tables]
        
        for col in columns:
            col_name = col['column_name'].lower()
            
            # Foreign key indicators
            if col_name.endswith('_id') and col_name != 'id':
                # Try to find referenced table
                potential_table = col_name[:-3]  # Remove '_id'
                for table_name in table_names:
                    if potential_table in table_name.lower():
                        relationships.append({
                            'type': 'foreign_key',
                            'target_table': table_name,
                            'column': col['column_name'],
                            'confidence': 0.8
                        })
                        break
        
        return relationships
    
    def _assess_business_importance(self, table: Dict, columns: List[Dict]) -> str:
        """Assess business importance of an entity"""
        table_name = table['table_name'].lower()
        record_count = table.get('record_count', 0)
        
        # High importance indicators
        if any(word in table_name for word in ['customer', 'order', 'product', 'user', 'account']):
            return 'high'
        
        # Medium importance indicators
        elif any(word in table_name for word in ['transaction', 'payment', 'inventory', 'category']):
            return 'medium'
        
        # Low importance (reference/config tables)
        elif any(word in table_name for word in ['config', 'setting', 'lookup', 'ref']):
            return 'low'
        
        # Based on record count
        elif record_count > 10000:
            return 'high'
        elif record_count > 1000:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_entity_confidence(self, table_name: str, columns: List[Dict]) -> float:
        """Calculate confidence score for entity classification"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for clear naming patterns
        if any(word in table_name for word in ['master', 'dim', 'fact', 'ref']):
            confidence += 0.2
        
        # Boost confidence for proper structure
        has_id = any('id' in col['column_name'].lower() for col in columns)
        has_timestamps = any('created' in col['column_name'].lower() or 'updated' in col['column_name'].lower() for col in columns)
        
        if has_id:
            confidence += 0.1
        if has_timestamps:
            confidence += 0.1
        
        # Boost confidence for business relevance
        business_indicators = sum(1 for word in ['customer', 'order', 'product', 'user'] if word in table_name)
        confidence += business_indicators * 0.05
        
        return min(confidence, 1.0)
    
    def _detect_master_detail_patterns(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect master-detail relationship patterns"""
        patterns = []
        tables = metadata.get('tables', [])
        relationships = metadata.get('relationships', [])
        
        # Group relationships by referenced table
        ref_groups = defaultdict(list)
        for rel in relationships:
            ref_groups[rel['to_table']].append(rel['from_table'])
        
        # Find tables with multiple referencing tables (potential masters)
        for master_table, detail_tables in ref_groups.items():
            if len(detail_tables) >= 2:
                for detail_table in detail_tables:
                    patterns.append({
                        'master': master_table,
                        'detail': detail_table,
                        'confidence': 0.7
                    })
        
        return patterns
    
    def _detect_temporal_pattern(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Detect temporal data patterns"""
        temporal_tables = []
        
        for table in metadata.get('tables', []):
            table_name = table['table_name'].lower()
            if any(word in table_name for word in ['log', 'history', 'audit', 'event', 'activity']):
                temporal_tables.append(table['table_name'])
        
        return {
            'pattern_type': 'temporal',
            'tables': temporal_tables,
            'confidence': 0.8 if temporal_tables else 0.0
        }
    
    def _detect_hierarchical_pattern(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Detect hierarchical data patterns"""
        hierarchical_columns = []
        
        for col in metadata.get('columns', []):
            col_name = col['column_name'].lower()
            if any(word in col_name for word in ['parent_id', 'parent', 'level', 'path']):
                hierarchical_columns.append(f"{col['table_name']}.{col['column_name']}")
        
        return {
            'pattern_type': 'hierarchical',
            'columns': hierarchical_columns,
            'confidence': 0.9 if hierarchical_columns else 0.0
        }
    
    def _detect_categorical_pattern(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Detect categorical data patterns"""
        categorical_tables = []
        
        for table in metadata.get('tables', []):
            table_name = table['table_name'].lower()
            if any(word in table_name for word in ['category', 'type', 'status', 'lookup', 'ref']):
                categorical_tables.append(table['table_name'])
        
        return {
            'pattern_type': 'categorical',
            'tables': categorical_tables,
            'confidence': 0.7 if categorical_tables else 0.0
        }
    
    def _detect_numerical_pattern(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Detect numerical data patterns"""
        numerical_columns = []
        
        for col in metadata.get('columns', []):
            data_type = col.get('data_type', '').lower()
            col_name = col['column_name'].lower()
            
            if (any(word in data_type for word in ['int', 'decimal', 'float', 'numeric']) and
                any(word in col_name for word in ['amount', 'price', 'cost', 'value', 'quantity', 'count'])):
                numerical_columns.append(f"{col['table_name']}.{col['column_name']}")
        
        return {
            'pattern_type': 'numerical',
            'columns': numerical_columns,
            'confidence': 0.8 if numerical_columns else 0.0
        }