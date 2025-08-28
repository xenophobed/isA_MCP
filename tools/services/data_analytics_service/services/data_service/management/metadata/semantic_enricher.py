#!/usr/bin/env python3
"""
AI-Powered Semantic Enricher - Step 2: Enrich metadata with semantic meaning
Uses intelligence_service text_extractor for AI-powered analysis instead of hardcoded methods
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import logging

# Import AI-powered text analysis
try:
    from tools.services.intelligence_service.language.text_extractor import TextExtractor, extract_entities, classify_text, extract_key_information
except ImportError:
    # Try different import paths
    try:
        import sys
        from pathlib import Path
        # Add the root project directory to sys.path
        root_dir = Path(__file__).parent.parent.parent.parent.parent
        sys.path.insert(0, str(root_dir))
        from tools.services.intelligence_service.language.text_extractor import TextExtractor, extract_entities, classify_text, extract_key_information
    except ImportError:
        logger = logging.getLogger(__name__)
        logger.warning("Could not import intelligence_service text_extractor - falling back to hardcoded methods")
        TextExtractor = None
        extract_entities = None
        classify_text = None
        extract_key_information = None

logger = logging.getLogger(__name__)

@dataclass
class SemanticMetadata:
    """Enhanced metadata with AI-powered semantic information"""
    original_metadata: Dict[str, Any]
    business_entities: List[Dict[str, Any]]
    semantic_tags: Dict[str, List[str]]
    data_patterns: List[Dict[str, Any]]
    business_rules: List[Dict[str, Any]]
    domain_classification: Dict[str, Any]
    confidence_scores: Dict[str, float]
    ai_analysis: Dict[str, Any]  # New: AI-powered analysis results

class AISemanticEnricher:
    """Step 2: AI-powered semantic enrichment of metadata"""
    
    def __init__(self):
        self.text_extractor = TextExtractor() if TextExtractor else None
        self.business_keywords = self._load_business_keywords()  # Keep as fallback
        self.domain_categories = [
            "ecommerce", "finance", "healthcare", "education", "hr", "crm", 
            "manufacturing", "logistics", "marketing", "legal", "research"
        ]
        
    async def enrich_metadata(self, metadata: Dict[str, Any]) -> SemanticMetadata:
        """
        Enrich raw metadata with AI-powered semantic information
        
        Args:
            metadata: Raw metadata from step 1
            
        Returns:
            SemanticMetadata with AI-enriched information
        """
        logger.info("Starting AI-powered semantic enrichment")
        
        try:
            # Extract business entities using AI
            business_entities = await self._extract_business_entities_ai(metadata)
            
            # Generate semantic tags using AI
            semantic_tags = await self._generate_semantic_tags_ai(metadata)
            
            # Detect data patterns using AI
            data_patterns = await self._detect_data_patterns_ai(metadata)
            
            # Infer business rules using AI
            business_rules = await self._infer_business_rules_ai(metadata, business_entities)
            
            # Classify domain using AI
            domain_classification = await self._classify_domain_ai(metadata, business_entities)
            
            # AI-powered analysis
            ai_analysis = await self._perform_comprehensive_ai_analysis(metadata)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(
                business_entities, semantic_tags, data_patterns, business_rules
            )
            
            logger.info("AI-powered semantic enrichment completed successfully")
            
            return SemanticMetadata(
                original_metadata=metadata,
                business_entities=business_entities,
                semantic_tags=semantic_tags,
                data_patterns=data_patterns,
                business_rules=business_rules,
                domain_classification=domain_classification,
                confidence_scores=confidence_scores,
                ai_analysis=ai_analysis
            )
            
        except Exception as e:
            logger.error(f"AI semantic enrichment failed: {e}")
            # Fallback to hardcoded methods
            return await self._fallback_enrichment(metadata)
    
    async def _extract_business_entities_ai(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract business entities using AI-powered named entity recognition"""
        entities = []
        
        if not self.text_extractor:
            return self._extract_business_entities_fallback(metadata)
        
        try:
            # Build text content from metadata for AI analysis
            text_content = self._build_metadata_text(metadata)
            
            # Extract entities using AI
            entity_result = await extract_entities(
                text=text_content,
                confidence_threshold=0.6
            )
            
            if entity_result['success']:
                ai_entities = entity_result['data']['entities']
                
                # Process each table with AI-enhanced analysis
                tables = metadata.get('tables', [])
                columns = metadata.get('columns', [])
                
                # Group columns by table
                table_columns = defaultdict(list)
                for col in columns:
                    table_columns[col['table_name']].append(col)
                
                for table in tables:
                    table_name = table['table_name']
                    table_cols = table_columns[table_name]
                    
                    # AI-enhanced entity analysis
                    entity_analysis = await self._analyze_table_with_ai(table, table_cols, ai_entities)
                    
                    entities.append({
                        'entity_name': table_name,
                        'entity_type': entity_analysis.get('entity_type', 'unknown'),
                        'confidence': entity_analysis.get('confidence', 0.5),
                        'key_attributes': entity_analysis.get('key_attributes', []),
                        'relationships': entity_analysis.get('relationships', []),
                        'record_count': table.get('record_count', 0),
                        'business_importance': entity_analysis.get('business_importance', 'medium'),
                        'ai_classification': entity_analysis.get('ai_classification', {}),
                        'detected_entities': entity_analysis.get('detected_entities', [])
                    })
                    
            else:
                logger.warning(f"AI entity extraction failed: {entity_result.get('error')}")
                return self._extract_business_entities_fallback(metadata)
                
        except Exception as e:
            logger.error(f"AI entity extraction error: {e}")
            return self._extract_business_entities_fallback(metadata)
        
        return entities
    
    async def _generate_semantic_tags_ai(self, metadata: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate semantic tags using AI-powered text analysis"""
        tags = {}
        
        if not self.text_extractor:
            return self._generate_semantic_tags_fallback(metadata)
        
        try:
            # Analyze each table/column with AI
            for table in metadata.get('tables', []):
                table_name = table['table_name']
                
                # Build text for AI analysis
                table_text = self._build_table_text(table, metadata.get('columns', []))
                
                # Extract key information for semantic tagging
                schema = {
                    "data_patterns": "What data patterns are present (temporal, reference, transactional, etc.)",
                    "business_domain": "What business domain does this belong to",
                    "data_characteristics": "Key characteristics of the data structure",
                    "usage_context": "How this data might be used in business context"
                }
                
                tag_result = await extract_key_information(
                    text=table_text,
                    schema=schema
                )
                
                if tag_result['success']:
                    ai_tags = []
                    extracted_info = tag_result['data']
                    
                    # Convert AI analysis to semantic tags
                    if 'data_patterns' in extracted_info:
                        patterns = extracted_info['data_patterns']
                        if isinstance(patterns, str):
                            ai_tags.extend([f"pattern:{pattern.strip()}" for pattern in patterns.split(',')[:3]])
                    
                    if 'business_domain' in extracted_info:
                        domain = extracted_info['business_domain']
                        if isinstance(domain, str):
                            ai_tags.append(f"domain:{domain.strip().lower()}")
                    
                    if 'data_characteristics' in extracted_info:
                        characteristics = extracted_info['data_characteristics']
                        if isinstance(characteristics, str):
                            ai_tags.extend([f"characteristic:{char.strip()}" for char in characteristics.split(',')[:2]])
                    
                    tags[f"table:{table_name}"] = ai_tags
                else:
                    # Fallback to basic pattern detection
                    tags[f"table:{table_name}"] = self._generate_basic_tags(table_name)
            
            # Column-level AI analysis
            for column in metadata.get('columns', []):
                col_name = column['column_name']
                table_name = column['table_name']
                
                # AI-powered column analysis
                column_text = f"Column: {col_name}, Type: {column.get('data_type', '')}, Business Type: {column.get('business_type', '')}"
                
                # Quick classification for column semantics
                col_categories = ["identifier", "temporal", "monetary", "categorical", "textual", "numeric", "geospatial"]
                col_classification = await classify_text(
                    text=column_text,
                    categories=col_categories
                )
                
                if col_classification['success']:
                    primary_semantic = col_classification['data']['primary_category']
                    tags[f"column:{table_name}.{col_name}"] = [f"semantic:{primary_semantic}"]
                else:
                    tags[f"column:{table_name}.{col_name}"] = [f"semantic:{column.get('business_type', 'unknown')}"]
                    
        except Exception as e:
            logger.error(f"AI semantic tagging error: {e}")
            return self._generate_semantic_tags_fallback(metadata)
        
        return tags
    
    async def _detect_data_patterns_ai(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect data patterns using AI analysis"""
        patterns = []
        
        if not self.text_extractor:
            return self._detect_data_patterns_fallback(metadata)
        
        try:
            # Build comprehensive metadata text
            metadata_text = self._build_comprehensive_metadata_text(metadata)
            
            # AI-powered pattern detection
            pattern_schema = {
                "data_model_patterns": "What data modeling patterns are used (star schema, normalized, denormalized, etc.)",
                "temporal_patterns": "What temporal data patterns exist (event logs, time series, snapshots, etc.)",
                "relationship_patterns": "What relationship patterns exist between entities",
                "data_flow_patterns": "How data flows through the system",
                "business_process_patterns": "What business processes are reflected in the data structure"
            }
            
            pattern_result = await extract_key_information(
                text=metadata_text,
                schema=pattern_schema
            )
            
            if pattern_result['success']:
                extracted_patterns = pattern_result['data']
                
                for pattern_type, pattern_description in extracted_patterns.items():
                    if pattern_description and isinstance(pattern_description, str):
                        patterns.append({
                            'pattern_type': pattern_type,
                            'description': pattern_description,
                            'confidence': pattern_result.get('confidence', 0.7),
                            'source': 'ai_analysis',
                            'detected_elements': self._extract_pattern_elements(pattern_description)
                        })
            else:
                patterns = self._detect_data_patterns_fallback(metadata)
                
        except Exception as e:
            logger.error(f"AI pattern detection error: {e}")
            patterns = self._detect_data_patterns_fallback(metadata)
        
        return patterns
    
    async def _infer_business_rules_ai(self, metadata: Dict[str, Any], business_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Infer business rules using AI analysis"""
        rules = []
        
        if not self.text_extractor:
            return self._infer_business_rules_fallback(metadata, business_entities)
        
        try:
            # Build business context text
            business_text = self._build_business_context_text(metadata, business_entities)
            
            # AI-powered business rule inference
            rule_schema = {
                "data_constraints": "What data constraints and validation rules are implied",
                "business_constraints": "What business rules and constraints are reflected",
                "referential_integrity": "What referential integrity rules exist",
                "data_quality_rules": "What data quality rules should be applied",
                "business_logic": "What business logic is embedded in the data structure"
            }
            
            rule_result = await extract_key_information(
                text=business_text,
                schema=rule_schema
            )
            
            if rule_result['success']:
                extracted_rules = rule_result['data']
                
                for rule_type, rule_description in extracted_rules.items():
                    if rule_description and isinstance(rule_description, str):
                        rules.append({
                            'rule_type': rule_type,
                            'description': rule_description,
                            'confidence': rule_result.get('confidence', 0.6),
                            'source': 'ai_inference',
                            'applicable_entities': self._extract_applicable_entities(rule_description, business_entities)
                        })
            else:
                rules = self._infer_business_rules_fallback(metadata, business_entities)
                
        except Exception as e:
            logger.error(f"AI business rule inference error: {e}")
            rules = self._infer_business_rules_fallback(metadata, business_entities)
        
        return rules
    
    async def _classify_domain_ai(self, metadata: Dict[str, Any], business_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Classify business domain using AI"""
        if not self.text_extractor:
            return self._classify_domain_fallback(metadata, business_entities)
        
        try:
            # Build domain classification text
            domain_text = self._build_domain_text(metadata, business_entities)
            
            # AI-powered domain classification
            domain_result = await classify_text(
                text=domain_text,
                categories=self.domain_categories,
                multi_label=True
            )
            
            if domain_result['success']:
                classification_data = domain_result['data']
                
                # Get primary domain
                primary_domain = classification_data.get('primary_category', 'general')
                
                # Get all domain scores
                domain_scores = classification_data.get('classification', {})
                
                # Calculate confidence
                confidence = domain_result.get('confidence', 0.5)
                
                return {
                    'primary_domain': primary_domain,
                    'domain_scores': domain_scores,
                    'confidence': confidence,
                    'reasoning': classification_data.get('reasoning', ''),
                    'source': 'ai_classification',
                    'secondary_domains': [domain for domain, score in domain_scores.items() 
                                        if isinstance(score, (int, float)) and score > 0.3 and domain != primary_domain]
                }
            else:
                return self._classify_domain_fallback(metadata, business_entities)
                
        except Exception as e:
            logger.error(f"AI domain classification error: {e}")
            return self._classify_domain_fallback(metadata, business_entities)
    
    async def _perform_comprehensive_ai_analysis(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive AI analysis of the metadata"""
        analysis = {}
        
        if not self.text_extractor:
            return {"source": "fallback", "analysis": "AI analysis not available"}
        
        try:
            # Build comprehensive text for analysis
            full_text = self._build_comprehensive_metadata_text(metadata)
            
            # Comprehensive analysis schema
            analysis_schema = {
                "data_architecture": "Overall data architecture and design patterns",
                "business_value": "Business value and importance of this data",
                "data_maturity": "Data maturity level and quality indicators",
                "usage_recommendations": "Recommended use cases and applications",
                "potential_issues": "Potential data quality or structural issues",
                "integration_opportunities": "Opportunities for data integration or enhancement"
            }
            
            analysis_result = await extract_key_information(
                text=full_text,
                schema=analysis_schema
            )
            
            if analysis_result['success']:
                analysis = {
                    'source': 'ai_comprehensive_analysis',
                    'confidence': analysis_result.get('confidence', 0.7),
                    'analysis': analysis_result['data'],
                    'completeness': analysis_result.get('completeness', 0.8)
                }
            else:
                analysis = {
                    'source': 'fallback',
                    'error': analysis_result.get('error', 'Unknown error'),
                    'analysis': "Comprehensive AI analysis failed"
                }
                
        except Exception as e:
            logger.error(f"Comprehensive AI analysis error: {e}")
            analysis = {
                'source': 'error',
                'error': str(e),
                'analysis': "Analysis failed due to error"
            }
        
        return analysis
    
    # Helper methods for building text content for AI analysis
    def _build_metadata_text(self, metadata: Dict[str, Any]) -> str:
        """Build text content from metadata for AI analysis"""
        text_parts = []
        
        # Add source info
        source_info = metadata.get('source_info', {})
        if source_info:
            text_parts.append(f"Data source: {source_info.get('type', 'unknown')} with {source_info.get('total_rows', 0)} rows and {source_info.get('total_columns', 0)} columns")
        
        # Add table information
        tables = metadata.get('tables', [])
        for table in tables:
            text_parts.append(f"Table: {table['table_name']} ({table.get('record_count', 0)} records)")
        
        # Add column information
        columns = metadata.get('columns', [])
        for column in columns[:10]:  # Limit to first 10 columns
            col_info = f"Column: {column['column_name']} (type: {column.get('data_type', 'unknown')}, business_type: {column.get('business_type', 'unknown')})"
            text_parts.append(col_info)
        
        return " | ".join(text_parts)
    
    def _build_table_text(self, table: Dict[str, Any], columns: List[Dict[str, Any]]) -> str:
        """Build text for a specific table"""
        table_name = table['table_name']
        table_columns = [col for col in columns if col['table_name'] == table_name]
        
        text_parts = [
            f"Table: {table_name}",
            f"Records: {table.get('record_count', 0)}",
            f"Columns: {len(table_columns)}"
        ]
        
        # Add column details
        for col in table_columns[:5]:  # Limit to first 5 columns
            text_parts.append(f"Column {col['column_name']} ({col.get('data_type', 'unknown')})")
        
        return " | ".join(text_parts)
    
    def _build_comprehensive_metadata_text(self, metadata: Dict[str, Any]) -> str:
        """Build comprehensive text for full metadata analysis"""
        text_parts = []
        
        # Source information
        source_info = metadata.get('source_info', {})
        text_parts.append(f"Data source type: {source_info.get('type', 'unknown')}")
        text_parts.append(f"Total tables: {len(metadata.get('tables', []))}")
        text_parts.append(f"Total columns: {len(metadata.get('columns', []))}")
        
        # Table and column summary
        tables = metadata.get('tables', [])
        columns = metadata.get('columns', [])
        
        # Business patterns from original analysis
        business_patterns = metadata.get('business_patterns', {})
        if business_patterns:
            primary_domain = business_patterns.get('primary_domain', 'unknown')
            text_parts.append(f"Detected primary domain: {primary_domain}")
        
        # Data quality info
        data_quality = metadata.get('data_quality', {})
        if data_quality:
            quality_score = data_quality.get('overall_quality_score', 0)
            text_parts.append(f"Data quality score: {quality_score}")
        
        return " | ".join(text_parts)
    
    def _build_business_context_text(self, metadata: Dict[str, Any], business_entities: List[Dict[str, Any]]) -> str:
        """Build business context text for rule inference"""
        text_parts = []
        
        for entity in business_entities:
            entity_info = f"Business entity: {entity['entity_name']} (type: {entity.get('entity_type', 'unknown')}, importance: {entity.get('business_importance', 'medium')})"
            text_parts.append(entity_info)
        
        # Add relationships if available
        for entity in business_entities:
            relationships = entity.get('relationships', [])
            for rel in relationships:
                text_parts.append(f"Relationship: {rel}")
        
        return " | ".join(text_parts)
    
    def _build_domain_text(self, metadata: Dict[str, Any], business_entities: List[Dict[str, Any]]) -> str:
        """Build text for domain classification"""
        text_parts = []
        
        # Add table names
        tables = metadata.get('tables', [])
        table_names = [table['table_name'] for table in tables]
        text_parts.append(f"Tables: {', '.join(table_names)}")
        
        # Add column names that indicate business domain
        columns = metadata.get('columns', [])
        business_columns = [col['column_name'] for col in columns if col.get('business_type') in ['identifier', 'monetary', 'temporal']]
        if business_columns:
            text_parts.append(f"Key business columns: {', '.join(business_columns[:10])}")
        
        # Add entity types
        entity_types = [entity.get('entity_type', 'unknown') for entity in business_entities]
        if entity_types:
            text_parts.append(f"Entity types: {', '.join(set(entity_types))}")
        
        return " | ".join(text_parts)
    
    # Fallback methods (original hardcoded logic)
    async def _fallback_enrichment(self, metadata: Dict[str, Any]) -> SemanticMetadata:
        """Fallback to original hardcoded enrichment when AI is not available"""
        logger.info("Using fallback hardcoded semantic enrichment")
        
        business_entities = self._extract_business_entities_fallback(metadata)
        semantic_tags = self._generate_semantic_tags_fallback(metadata)
        data_patterns = self._detect_data_patterns_fallback(metadata)
        business_rules = self._infer_business_rules_fallback(metadata, business_entities)
        domain_classification = self._classify_domain_fallback(metadata, business_entities)
        
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
            confidence_scores=confidence_scores,
            ai_analysis={"source": "fallback", "reason": "AI service not available"}
        )
    
    def _extract_business_entities_fallback(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback business entity extraction"""
        entities = []
        tables = metadata.get('tables', []) or []
        columns = metadata.get('columns', []) or []
        
        # Group columns by table
        table_columns = defaultdict(list)
        for col in columns:
            if col and 'table_name' in col:
                table_columns[col['table_name']].append(col)
        
        for table in tables:
            if table and 'table_name' in table:
                table_name = table['table_name'].lower()
                table_cols = table_columns[table['table_name']]
                
                entities.append({
                    'entity_name': table['table_name'],
                    'entity_type': self._classify_entity_type_fallback(table_name, table_cols),
                    'confidence': 0.6,
                    'key_attributes': [col.get('column_name', '') for col in table_cols[:3] if col],
                    'relationships': [],
                    'record_count': table.get('record_count', 0),
                    'business_importance': 'medium'
                })
        
        return entities
    
    def _generate_semantic_tags_fallback(self, metadata: Dict[str, Any]) -> Dict[str, List[str]]:
        """Fallback semantic tag generation"""
        tags = {}
        
        tables = metadata.get('tables', []) or []
        for table in tables:
            if table and 'table_name' in table:
                table_name = table['table_name'].lower()
                table_tags = []
                
                # Basic pattern detection
                if 'log' in table_name or 'audit' in table_name:
                    table_tags.append("pattern:temporal")
                if 'ref' in table_name or 'lookup' in table_name:
                    table_tags.append("pattern:reference")
                
                tags[f"table:{table['table_name']}"] = table_tags
        
        return tags
    
    def _detect_data_patterns_fallback(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback data pattern detection"""
        patterns = []
        
        tables = metadata.get('tables', []) or []
        if len(tables) > 5:
            patterns.append({
                'pattern_type': 'complex_schema',
                'description': 'Multiple tables suggesting complex business domain',
                'confidence': 0.7,
                'source': 'fallback'
            })
        
        return patterns
    
    def _infer_business_rules_fallback(self, metadata: Dict[str, Any], business_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback business rule inference"""
        rules = []
        
        # Basic rule inference
        rules.append({
            'rule_type': 'data_quality',
            'description': 'Ensure data completeness and accuracy',
            'confidence': 0.5,
            'source': 'fallback'
        })
        
        return rules
    
    def _classify_domain_fallback(self, metadata: Dict[str, Any], business_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback domain classification"""
        # Use business patterns from metadata if available
        business_patterns = metadata.get('business_patterns', {})
        primary_domain = business_patterns.get('primary_domain', 'general')
        
        return {
            'primary_domain': primary_domain,
            'confidence': 0.5,
            'source': 'fallback'
        }
    
    # Helper methods
    def _classify_entity_type_fallback(self, table_name: str, columns: List[Dict[str, Any]]) -> str:
        """Fallback entity type classification"""
        if 'transaction' in table_name or 'order' in table_name:
            return 'transactional'
        elif 'customer' in table_name or 'user' in table_name:
            return 'entity'
        elif 'product' in table_name or 'item' in table_name:
            return 'catalog'
        else:
            return 'unknown'
    
    def _generate_basic_tags(self, table_name: str) -> List[str]:
        """Generate basic tags for a table"""
        tags = []
        name_lower = table_name.lower()
        
        if 'transaction' in name_lower:
            tags.append("pattern:transactional")
        if 'master' in name_lower:
            tags.append("pattern:master")
        if 'ref' in name_lower:
            tags.append("pattern:reference")
        
        return tags
    
    def _extract_pattern_elements(self, description: str) -> List[str]:
        """Extract pattern elements from AI description"""
        # Simple keyword extraction
        keywords = ['schema', 'pattern', 'relationship', 'temporal', 'transactional']
        found_elements = []
        
        for keyword in keywords:
            if keyword in description.lower():
                found_elements.append(keyword)
        
        return found_elements
    
    def _extract_applicable_entities(self, rule_description: str, business_entities: List[Dict[str, Any]]) -> List[str]:
        """Extract entities applicable to a business rule"""
        applicable = []
        
        for entity in business_entities:
            entity_name = entity['entity_name'].lower()
            if entity_name in rule_description.lower():
                applicable.append(entity['entity_name'])
        
        return applicable
    
    async def _analyze_table_with_ai(self, table: Dict[str, Any], columns: List[Dict[str, Any]], ai_entities: Dict[str, List]) -> Dict[str, Any]:
        """Analyze a table using AI-extracted entities"""
        table_name = table['table_name']
        
        # Look for relevant AI entities
        detected_entities = []
        for entity_type, entities in ai_entities.items():
            for entity in entities:
                if table_name.lower() in entity.get('name', '').lower():
                    detected_entities.append({
                        'type': entity_type,
                        'name': entity.get('name'),
                        'confidence': entity.get('confidence', 0.5)
                    })
        
        # Classify entity type based on AI analysis and table structure
        entity_type = self._classify_entity_type_ai(table_name, columns, detected_entities)
        
        return {
            'entity_type': entity_type,
            'confidence': 0.8 if detected_entities else 0.6,
            'key_attributes': [col['column_name'] for col in columns[:5]],
            'relationships': [],
            'business_importance': 'high' if detected_entities else 'medium',
            'ai_classification': {'detected_entities': detected_entities},
            'detected_entities': detected_entities
        }
    
    def _classify_entity_type_ai(self, table_name: str, columns: List[Dict[str, Any]], detected_entities: List[Dict]) -> str:
        """Classify entity type using AI analysis"""
        name_lower = table_name.lower()
        
        # Check AI-detected entities
        for entity in detected_entities:
            entity_type = entity.get('type', '').lower()
            if entity_type == 'organization':
                return 'organization_entity'
            elif entity_type == 'person':
                return 'person_entity'
            elif entity_type == 'product':
                return 'product_entity'
            elif entity_type == 'money':
                return 'financial_entity'
        
        # Fallback to pattern-based classification
        if 'transaction' in name_lower or 'order' in name_lower:
            return 'transactional'
        elif 'customer' in name_lower or 'user' in name_lower:
            return 'customer_entity'
        elif 'product' in name_lower or 'item' in name_lower:
            return 'catalog_entity'
        else:
            return 'data_entity'
    
    def _calculate_confidence_scores(self, business_entities: List[Dict[str, Any]], 
                                   semantic_tags: Dict[str, List[str]], 
                                   data_patterns: List[Dict[str, Any]], 
                                   business_rules: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate confidence scores for different aspects"""
        scores = {}
        
        # Entity extraction confidence
        if business_entities:
            entity_confidences = [e.get('confidence', 0.5) for e in business_entities]
            scores['entity_extraction'] = sum(entity_confidences) / len(entity_confidences)
        else:
            scores['entity_extraction'] = 0.0
        
        # Semantic tagging confidence
        scores['semantic_tagging'] = 0.8 if semantic_tags else 0.3
        
        # Pattern detection confidence
        if data_patterns:
            pattern_confidences = [p.get('confidence', 0.5) for p in data_patterns]
            scores['pattern_detection'] = sum(pattern_confidences) / len(pattern_confidences)
        else:
            scores['pattern_detection'] = 0.3
        
        # Business rules confidence
        if business_rules:
            rule_confidences = [r.get('confidence', 0.5) for r in business_rules]
            scores['business_rules'] = sum(rule_confidences) / len(rule_confidences)
        else:
            scores['business_rules'] = 0.3
        
        # Overall confidence
        scores['overall'] = sum(scores.values()) / len(scores)
        
        return scores
    
    def _load_business_keywords(self) -> Dict[str, List[str]]:
        """Load business keywords for fallback analysis"""
        return {
            'ecommerce': ['product', 'order', 'cart', 'customer', 'inventory', 'price'],
            'finance': ['account', 'transaction', 'payment', 'balance', 'invoice'],
            'hr': ['employee', 'department', 'salary', 'payroll', 'performance'],
            'crm': ['customer', 'contact', 'lead', 'opportunity', 'campaign'],
            'manufacturing': ['product', 'material', 'production', 'quality', 'inventory'],
            'logistics': ['shipment', 'delivery', 'warehouse', 'tracking', 'carrier']
        }

# Convenience function for backward compatibility
async def enrich_metadata(metadata: Dict[str, Any]) -> SemanticMetadata:
    """
    Convenience function to enrich metadata with AI-powered semantic analysis
    
    Args:
        metadata: Raw metadata from step 1
        
    Returns:
        SemanticMetadata with AI-enriched information
    """
    enricher = AISemanticEnricher()
    return await enricher.enrich_metadata(metadata)