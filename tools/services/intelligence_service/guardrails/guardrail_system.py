#!/usr/bin/env python3
"""
Guardrail System for RAG Post-Generation Validation

Implements LLM-as-Judge patterns and rule-based validation for ensuring quality
and safety of RAG-generated responses.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class GuardrailLevel(Enum):
    """Guardrail enforcement levels"""
    STRICT = "strict"     # Block responses that fail any check
    MODERATE = "moderate"  # Block responses that fail critical checks
    LENIENT = "lenient"   # Log warnings but allow most responses
    DISABLED = "disabled"  # No guardrail enforcement

class ValidationType(Enum):
    """Types of validation checks"""
    RELEVANCE = "relevance"           # Query-response relevance
    HALLUCINATION = "hallucination"   # Factual accuracy check
    SAFETY = "safety"                 # Safety and toxicity check
    QUALITY = "quality"               # Response quality metrics
    COHERENCE = "coherence"           # Logical coherence
    COMPLETENESS = "completeness"     # Response completeness

@dataclass
class GuardrailConfig:
    """Configuration for guardrail system"""
    level: GuardrailLevel = GuardrailLevel.MODERATE
    confidence_threshold: float = 0.7
    enabled_validators: List[ValidationType] = field(default_factory=lambda: [
        ValidationType.RELEVANCE,
        ValidationType.SAFETY,
        ValidationType.QUALITY
    ])
    
    # Relevance validation settings
    relevance_threshold: float = 0.6
    
    # Hallucination detection settings
    hallucination_threshold: float = 0.8
    enable_fact_checking: bool = True
    
    # Safety settings
    safety_threshold: float = 0.9
    block_unsafe_content: bool = True
    
    # Quality settings
    min_response_length: int = 10
    max_response_length: int = 5000
    require_coherence: bool = True
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl_minutes: int = 60
    parallel_validation: bool = True

class GuardrailSystem:
    """
    Comprehensive guardrail system for RAG quality control
    
    Provides multiple layers of validation:
    1. Relevance checking (query-response alignment)
    2. Hallucination detection (factual accuracy)
    3. Safety filtering (toxicity, harmful content)
    4. Quality assurance (coherence, completeness)
    """
    
    def __init__(self, config: Optional[GuardrailConfig] = None):
        """
        Initialize guardrail system
        
        Args:
            config: Guardrail configuration
        """
        self.config = config or GuardrailConfig()
        self._validators = {}
        self._isa_client = None
        self._validation_cache = {}
        
        # Initialize validators based on configuration
        self._initialize_validators()
        
        logger.info(f"GuardrailSystem initialized with level: {self.config.level.value}")
    
    @property
    def isa_client(self):
        """Lazy load ISA client for LLM-as-Judge validation"""
        if self._isa_client is None:
            try:
                from core.isa_client_factory import get_isa_client
                self._isa_client = get_isa_client()
            except ImportError:
                logger.warning("ISA client not available, some validations may be limited")
        return self._isa_client
    
    def _initialize_validators(self):
        """Initialize enabled validators"""
        try:
            from .validators import (
                RelevanceValidator,
                HallucinationValidator,
                SafetyValidator,
                QualityValidator
            )
            
            if ValidationType.RELEVANCE in self.config.enabled_validators:
                self._validators[ValidationType.RELEVANCE] = RelevanceValidator(
                    threshold=self.config.relevance_threshold
                )
            
            if ValidationType.HALLUCINATION in self.config.enabled_validators:
                self._validators[ValidationType.HALLUCINATION] = HallucinationValidator(
                    threshold=self.config.hallucination_threshold,
                    enable_fact_checking=self.config.enable_fact_checking
                )
            
            if ValidationType.SAFETY in self.config.enabled_validators:
                self._validators[ValidationType.SAFETY] = SafetyValidator(
                    threshold=self.config.safety_threshold
                )
            
            if ValidationType.QUALITY in self.config.enabled_validators:
                self._validators[ValidationType.QUALITY] = QualityValidator(
                    min_length=self.config.min_response_length,
                    max_length=self.config.max_response_length,
                    require_coherence=self.config.require_coherence
                )
            
            logger.info(f"Initialized {len(self._validators)} validators")
            
        except ImportError as e:
            logger.error(f"Failed to initialize validators: {e}")
            self._validators = {}
    
    async def validate_content(self, content: str) -> Dict[str, Any]:
        """
        Validate content quality and safety
        
        Args:
            content: Text content to validate
            
        Returns:
            Dict with validation results
        """
        if self.config.level == GuardrailLevel.DISABLED:
            return {'passed': True, 'confidence': 1.0, 'warnings': [], 'compliance_score': 1.0}
        
        try:
            # Use validate_result method internally
            result = {'text': content}
            passed = await self.validate_result("", result)
            
            return {
                'passed': passed,
                'confidence': 0.8 if passed else 0.3,
                'warnings': [] if passed else ['Content validation failed'],
                'compliance_score': 0.9 if passed else 0.4
            }
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            return {
                'passed': False,
                'confidence': 0.1,
                'warnings': [str(e)],
                'compliance_score': 0.1
            }
    
    async def validate_result(
        self,
        query: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validate a search result or generated response
        
        Args:
            query: Original query/question
            result: Result to validate (with 'text' field)
            context: Additional context for validation
            
        Returns:
            True if result passes all enabled validations
        """
        if self.config.level == GuardrailLevel.DISABLED:
            return True
        
        try:
            response_text = result.get('text', result.get('content', ''))
            if not response_text:
                logger.warning("Empty response text, failing validation")
                return False
            
            # Check cache first
            cache_key = self._get_cache_key(query, response_text)
            if self.config.enable_caching and cache_key in self._validation_cache:
                cached_result = self._validation_cache[cache_key]
                if not self._is_cache_expired(cached_result):
                    return cached_result['is_valid']
            
            # Run validations
            validation_results = {}
            
            if self.config.parallel_validation:
                validation_results = await self._run_parallel_validations(
                    query, response_text, result, context
                )
            else:
                validation_results = await self._run_sequential_validations(
                    query, response_text, result, context
                )
            
            # Determine overall result based on level
            is_valid = self._evaluate_validation_results(validation_results)
            
            # Cache result
            if self.config.enable_caching:
                self._validation_cache[cache_key] = {
                    'is_valid': is_valid,
                    'validation_results': validation_results,
                    'timestamp': datetime.now(),
                    'query': query,
                    'response_length': len(response_text)
                }
            
            # Log validation details
            self._log_validation_results(query, validation_results, is_valid)
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            # Fail-safe: allow response if validation fails in lenient mode
            return self.config.level == GuardrailLevel.LENIENT
    
    async def _run_parallel_validations(
        self,
        query: str,
        response: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[ValidationType, Dict[str, Any]]:
        """Run validations in parallel"""
        import asyncio
        
        validation_tasks = []
        validator_types = []
        
        for validator_type, validator in self._validators.items():
            task = validator.validate(query, response, result, context)
            validation_tasks.append(task)
            validator_types.append(validator_type)
        
        if not validation_tasks:
            return {}
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        validation_results = {}
        for validator_type, result in zip(validator_types, results):
            if isinstance(result, Exception):
                logger.error(f"Validator {validator_type.value} failed: {result}")
                validation_results[validator_type] = {
                    'passed': self.config.level == GuardrailLevel.LENIENT,
                    'confidence': 0.0,
                    'error': str(result)
                }
            else:
                validation_results[validator_type] = result
        
        return validation_results
    
    async def _run_sequential_validations(
        self,
        query: str,
        response: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[ValidationType, Dict[str, Any]]:
        """Run validations sequentially"""
        validation_results = {}
        
        for validator_type, validator in self._validators.items():
            try:
                validation_result = await validator.validate(query, response, result, context)
                validation_results[validator_type] = validation_result
                
                # Early exit for strict mode on critical failures
                if (self.config.level == GuardrailLevel.STRICT and 
                    not validation_result.get('passed', False)):
                    logger.info(f"Early exit due to failed {validator_type.value} validation")
                    break
                    
            except Exception as e:
                logger.error(f"Validator {validator_type.value} failed: {e}")
                validation_results[validator_type] = {
                    'passed': self.config.level == GuardrailLevel.LENIENT,
                    'confidence': 0.0,
                    'error': str(e)
                }
        
        return validation_results
    
    def _evaluate_validation_results(
        self,
        validation_results: Dict[ValidationType, Dict[str, Any]]
    ) -> bool:
        """Evaluate validation results based on guardrail level"""
        if not validation_results:
            return True  # No validators, allow by default
        
        failed_validators = []
        critical_failures = []
        
        for validator_type, result in validation_results.items():
            passed = result.get('passed', False)
            confidence = result.get('confidence', 0.0)
            
            if not passed:
                failed_validators.append(validator_type)
                
                # Critical failures
                if validator_type in [ValidationType.SAFETY, ValidationType.HALLUCINATION]:
                    critical_failures.append(validator_type)
        
        if self.config.level == GuardrailLevel.STRICT:
            return len(failed_validators) == 0
        
        elif self.config.level == GuardrailLevel.MODERATE:
            return len(critical_failures) == 0
        
        elif self.config.level == GuardrailLevel.LENIENT:
            # Only block if majority of validators fail
            return len(failed_validators) < len(validation_results) * 0.6
        
        else:  # DISABLED
            return True
    
    def _get_cache_key(self, query: str, response: str) -> str:
        """Generate cache key for validation result"""
        import hashlib
        combined = f"{query}:{response}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _is_cache_expired(self, cached_result: Dict[str, Any]) -> bool:
        """Check if cached validation result is expired"""
        if not self.config.enable_caching:
            return True
        
        timestamp = cached_result.get('timestamp')
        if not timestamp:
            return True
        
        elapsed_minutes = (datetime.now() - timestamp).total_seconds() / 60
        return elapsed_minutes > self.config.cache_ttl_minutes
    
    def _log_validation_results(
        self,
        query: str,
        validation_results: Dict[ValidationType, Dict[str, Any]],
        is_valid: bool
    ):
        """Log validation results for monitoring"""
        if logger.isEnabledFor(logging.DEBUG):
            summary = {
                'query_length': len(query),
                'is_valid': is_valid,
                'validations': {}
            }
            
            for validator_type, result in validation_results.items():
                summary['validations'][validator_type.value] = {
                    'passed': result.get('passed', False),
                    'confidence': result.get('confidence', 0.0)
                }
            
            logger.debug(f"Guardrail validation: {summary}")
        elif not is_valid:
            failed_validators = [
                vtype.value for vtype, result in validation_results.items()
                if not result.get('passed', False)
            ]
            logger.info(f"Guardrail blocked response - failed validators: {failed_validators}")
    
    async def validate_generation(
        self,
        query: str,
        generated_response: str,
        source_documents: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Comprehensive validation for generated responses
        
        Args:
            query: Original query
            generated_response: Generated response to validate
            source_documents: Source documents used for generation
            **kwargs: Additional validation parameters
            
        Returns:
            Detailed validation results
        """
        try:
            # Create result object for validation
            result = {
                'text': generated_response,
                'source_documents': source_documents,
                'metadata': kwargs.get('metadata', {})
            }
            
            context = {
                'source_documents': source_documents,
                'generation_metadata': kwargs
            }
            
            # Run standard validation
            is_valid = await self.validate_result(query, result, context)
            
            # Additional generation-specific checks
            attribution_score = await self._check_source_attribution(
                generated_response, source_documents
            )
            
            factual_consistency = await self._check_factual_consistency(
                generated_response, source_documents
            )
            
            return {
                'is_valid': is_valid,
                'query': query,
                'response_length': len(generated_response),
                'source_document_count': len(source_documents),
                'attribution_score': attribution_score,
                'factual_consistency': factual_consistency,
                'guardrail_level': self.config.level.value,
                'validation_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Generation validation failed: {e}")
            return {
                'is_valid': self.config.level == GuardrailLevel.LENIENT,
                'error': str(e)
            }
    
    async def _check_source_attribution(
        self,
        response: str,
        source_documents: List[Dict[str, Any]]
    ) -> float:
        """Check how well the response is attributed to source documents"""
        try:
            if not source_documents or not self.isa_client:
                return 0.5  # Neutral score when unable to check
            
            # Use ISA for attribution scoring
            source_texts = [doc.get('text', '') for doc in source_documents]
            combined_sources = ' '.join(source_texts[:3])  # Use top 3 sources
            
            attribution_prompt = f"""
            Please evaluate how well the following response is supported by the given source texts.
            Rate from 0.0 (no support) to 1.0 (fully supported).
            
            Response: {response}
            
            Source texts: {combined_sources}
            
            Provide only a numeric score between 0.0 and 1.0.
            """
            
            result = await self.isa_client.invoke(
                input_data=attribution_prompt,
                task="chat",
                service_type="text"
            )
            
            if result.get('success'):
                score_text = result.get('result', '0.5').strip()
                try:
                    return float(score_text)
                except ValueError:
                    # Try to extract number from response
                    import re
                    numbers = re.findall(r'0\.\d+|1\.0', score_text)
                    return float(numbers[0]) if numbers else 0.5
            
            return 0.5
            
        except Exception as e:
            logger.error(f"Attribution check failed: {e}")
            return 0.5
    
    async def _check_factual_consistency(
        self,
        response: str,
        source_documents: List[Dict[str, Any]]
    ) -> float:
        """Check factual consistency between response and sources"""
        try:
            if not source_documents or not self.isa_client:
                return 0.5
            
            # Use ISA for consistency checking
            source_texts = [doc.get('text', '') for doc in source_documents]
            combined_sources = ' '.join(source_texts[:3])
            
            consistency_prompt = f"""
            Check if the following response contains any factual claims that contradict the source texts.
            Rate consistency from 0.0 (major contradictions) to 1.0 (fully consistent).
            
            Response: {response}
            
            Source texts: {combined_sources}
            
            Provide only a numeric score between 0.0 and 1.0.
            """
            
            result = await self.isa_client.invoke(
                input_data=consistency_prompt,
                task="chat",
                service_type="text"
            )
            
            if result.get('success'):
                score_text = result.get('result', '0.5').strip()
                try:
                    return float(score_text)
                except ValueError:
                    import re
                    numbers = re.findall(r'0\.\d+|1\.0', score_text)
                    return float(numbers[0]) if numbers else 0.5
            
            return 0.5
            
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            return 0.5
    
    def get_stats(self) -> Dict[str, Any]:
        """Get guardrail system statistics"""
        return {
            'config': {
                'level': self.config.level.value,
                'confidence_threshold': self.config.confidence_threshold,
                'enabled_validators': [v.value for v in self.config.enabled_validators]
            },
            'validators': {
                'count': len(self._validators),
                'types': [v.value for v in self._validators.keys()]
            },
            'cache': {
                'enabled': self.config.enable_caching,
                'size': len(self._validation_cache),
                'ttl_minutes': self.config.cache_ttl_minutes
            }
        }

# Global instance
_guardrail_system = None

def get_guardrail_system(config: Optional[GuardrailConfig] = None) -> GuardrailSystem:
    """Get singleton guardrail system instance"""
    global _guardrail_system
    if _guardrail_system is None:
        _guardrail_system = GuardrailSystem(config)
    return _guardrail_system