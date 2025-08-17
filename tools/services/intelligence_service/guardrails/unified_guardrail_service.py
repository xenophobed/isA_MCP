#!/usr/bin/env python3
"""
Unified Guardrail Service - Integration of Quality and Compliance Checks

Combines the RAG quality validation system with PII/medical compliance checking
to provide comprehensive guardrail coverage for all AI-generated content.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from .guardrail_system import GuardrailSystem, GuardrailConfig, GuardrailLevel
from resources.guardrail_resources import GuardrailChecker, GuardrailConfig as ComplianceConfig

logger = logging.getLogger(__name__)

@dataclass
class UnifiedGuardrailConfig:
    """Unified configuration for both quality and compliance guardrails"""
    
    # Quality guardrails (from guardrail_system)
    quality_level: GuardrailLevel = GuardrailLevel.MODERATE
    enable_quality_checks: bool = True
    quality_threshold: float = 0.7
    
    # Compliance guardrails (from guardrail_resources)
    compliance_mode: str = "moderate"  # "strict", "moderate", "permissive"
    enable_compliance_checks: bool = True
    enable_pii_detection: bool = True
    enable_medical_compliance: bool = True
    
    # Integration settings
    fail_on_any_violation: bool = False  # If True, fail if either quality OR compliance fails
    priority_mode: str = "compliance_first"  # "compliance_first", "quality_first", "balanced"
    enable_sanitization: bool = True

class UnifiedGuardrailService:
    """
    Unified service that combines RAG quality validation with compliance checking.
    
    Provides comprehensive guardrail coverage:
    1. RAG Quality Control (relevance, hallucination, safety, quality)
    2. Compliance Checking (PII, medical, GDPR, HIPAA)
    3. Intelligent integration and conflict resolution
    """
    
    def __init__(self, config: Optional[UnifiedGuardrailConfig] = None):
        """
        Initialize unified guardrail service
        
        Args:
            config: Unified guardrail configuration
        """
        self.config = config or UnifiedGuardrailConfig()
        
        # Initialize quality guardrail system
        if self.config.enable_quality_checks:
            quality_config = GuardrailConfig(
                level=self.config.quality_level,
                confidence_threshold=self.config.quality_threshold
            )
            self.quality_system = GuardrailSystem(quality_config)
            logger.info(f"Quality guardrails initialized: {self.config.quality_level.value}")
        else:
            self.quality_system = None
        
        # Initialize compliance checker
        if self.config.enable_compliance_checks:
            compliance_config = ComplianceConfig()
            self.compliance_checker = GuardrailChecker(compliance_config)
            logger.info(f"Compliance guardrails initialized: {self.config.compliance_mode}")
        else:
            self.compliance_checker = None
        
        logger.info("Unified Guardrail Service initialized")
    
    async def validate_content(
        self,
        content: str,
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive content validation using both quality and compliance checks.
        
        Args:
            content: Content to validate (response, generated text, etc.)
            query: Original query/prompt (for quality validation)
            context: Additional context (source documents, etc.)
            metadata: Content metadata
            
        Returns:
            Comprehensive validation result
        """
        try:
            validation_start = datetime.now()
            
            # Initialize result structure
            result = {
                'content': content,
                'query': query,
                'validation_timestamp': validation_start.isoformat(),
                'overall_status': 'APPROVED',
                'overall_message': 'Content approved',
                'sanitized_content': content,
                'quality_validation': {},
                'compliance_validation': {},
                'recommendations': [],
                'risk_assessment': {
                    'overall_risk': 'LOW',
                    'quality_risk': 'LOW',
                    'compliance_risk': 'LOW'
                }
            }
            
            # Step 1: Run validations based on priority mode
            if self.config.priority_mode == "compliance_first":
                result = await self._compliance_first_validation(content, query, context, result)
            elif self.config.priority_mode == "quality_first":
                result = await self._quality_first_validation(content, query, context, result)
            else:  # balanced
                result = await self._balanced_validation(content, query, context, result)
            
            # Step 2: Determine overall status
            result = self._determine_overall_status(result)
            
            # Step 3: Apply sanitization if needed
            if self.config.enable_sanitization and result['overall_status'] == 'SANITIZED':
                result = self._apply_sanitization(result)
            
            # Step 4: Generate final recommendations
            result['recommendations'] = self._generate_recommendations(result)
            
            # Timing
            validation_end = datetime.now()
            result['validation_duration_ms'] = int((validation_end - validation_start).total_seconds() * 1000)
            
            logger.info(f"Unified validation completed: {result['overall_status']} ({result['validation_duration_ms']}ms)")
            return result
            
        except Exception as e:
            logger.error(f"Unified validation failed: {e}")
            return {
                'content': content,
                'overall_status': 'ERROR',
                'overall_message': f'Validation failed: {str(e)}',
                'error': str(e),
                'validation_timestamp': datetime.now().isoformat()
            }
    
    async def _compliance_first_validation(
        self,
        content: str,
        query: Optional[str],
        context: Optional[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run compliance checks first, then quality if compliance passes"""
        
        # Step 1: Compliance validation
        if self.compliance_checker:
            compliance_result = self.compliance_checker.apply_guardrails(
                content, self.config.compliance_mode
            )
            result['compliance_validation'] = compliance_result
            
            # If compliance fails critically, don't run quality checks
            if compliance_result['action'] == 'BLOCK':
                result['overall_status'] = 'BLOCKED'
                result['overall_message'] = 'Content blocked due to compliance violations'
                result['risk_assessment']['compliance_risk'] = 'HIGH'
                result['risk_assessment']['overall_risk'] = 'HIGH'
                return result
            
            elif compliance_result['action'] == 'SANITIZE':
                result['sanitized_content'] = compliance_result['sanitized_text']
                result['overall_status'] = 'SANITIZED'
                result['risk_assessment']['compliance_risk'] = 'MEDIUM'
        
        # Step 2: Quality validation (only if compliance didn't block)
        if self.quality_system and query:
            try:
                # Use sanitized content for quality checks if available
                content_to_check = result.get('sanitized_content', content)
                quality_result = {
                    'text': content_to_check,
                    'metadata': context or {}
                }
                
                quality_passed = await self.quality_system.validate_result(
                    query, quality_result, context
                )
                
                result['quality_validation'] = {
                    'passed': quality_passed,
                    'content_checked': content_to_check,
                    'method': 'post_compliance'
                }
                
                if not quality_passed:
                    result['risk_assessment']['quality_risk'] = 'HIGH'
                    
                    # If we're in fail-on-any mode, block the content
                    if self.config.fail_on_any_violation:
                        result['overall_status'] = 'BLOCKED'
                        result['overall_message'] = 'Content blocked due to quality issues'
                        result['risk_assessment']['overall_risk'] = 'HIGH'
                        
            except Exception as e:
                logger.error(f"Quality validation failed in compliance-first mode: {e}")
                result['quality_validation'] = {'error': str(e), 'passed': False}
        
        return result
    
    async def _quality_first_validation(
        self,
        content: str,
        query: Optional[str],
        context: Optional[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run quality checks first, then compliance"""
        
        # Step 1: Quality validation
        if self.quality_system and query:
            try:
                quality_result = {
                    'text': content,
                    'metadata': context or {}
                }
                
                quality_passed = await self.quality_system.validate_result(
                    query, quality_result, context
                )
                
                result['quality_validation'] = {
                    'passed': quality_passed,
                    'method': 'pre_compliance'
                }
                
                # If quality fails critically, consider blocking
                if not quality_passed and self.config.fail_on_any_violation:
                    result['overall_status'] = 'BLOCKED'
                    result['overall_message'] = 'Content blocked due to quality issues'
                    result['risk_assessment']['quality_risk'] = 'HIGH'
                    result['risk_assessment']['overall_risk'] = 'HIGH'
                    return result
                    
            except Exception as e:
                logger.error(f"Quality validation failed in quality-first mode: {e}")
                result['quality_validation'] = {'error': str(e), 'passed': False}
        
        # Step 2: Compliance validation
        if self.compliance_checker:
            compliance_result = self.compliance_checker.apply_guardrails(
                content, self.config.compliance_mode
            )
            result['compliance_validation'] = compliance_result
            
            if compliance_result['action'] == 'BLOCK':
                result['overall_status'] = 'BLOCKED'
                result['overall_message'] = 'Content blocked due to compliance violations'
                result['risk_assessment']['compliance_risk'] = 'HIGH'
                result['risk_assessment']['overall_risk'] = 'HIGH'
            
            elif compliance_result['action'] == 'SANITIZE':
                result['sanitized_content'] = compliance_result['sanitized_text']
                if result['overall_status'] != 'BLOCKED':
                    result['overall_status'] = 'SANITIZED'
                result['risk_assessment']['compliance_risk'] = 'MEDIUM'
        
        return result
    
    async def _balanced_validation(
        self,
        content: str,
        query: Optional[str],
        context: Optional[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run both validations in parallel and combine results"""
        import asyncio
        
        tasks = []
        
        # Quality validation task
        if self.quality_system and query:
            async def quality_task():
                try:
                    quality_result = {
                        'text': content,
                        'metadata': context or {}
                    }
                    
                    quality_passed = await self.quality_system.validate_result(
                        query, quality_result, context
                    )
                    
                    return {
                        'passed': quality_passed,
                        'method': 'parallel'
                    }
                except Exception as e:
                    logger.error(f"Quality validation failed in balanced mode: {e}")
                    return {'error': str(e), 'passed': False}
            
            tasks.append(('quality', quality_task()))
        
        # Compliance validation task (synchronous, so wrap in async)
        if self.compliance_checker:
            async def compliance_task():
                try:
                    return self.compliance_checker.apply_guardrails(
                        content, self.config.compliance_mode
                    )
                except Exception as e:
                    logger.error(f"Compliance validation failed in balanced mode: {e}")
                    return {'action': 'ERROR', 'error': str(e)}
            
            tasks.append(('compliance', compliance_task()))
        
        # Run tasks in parallel
        if tasks:
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            for i, (task_type, _) in enumerate(tasks):
                task_result = results[i]
                
                if isinstance(task_result, Exception):
                    logger.error(f"{task_type} validation failed: {task_result}")
                    if task_type == 'quality':
                        result['quality_validation'] = {'error': str(task_result), 'passed': False}
                    else:
                        result['compliance_validation'] = {'action': 'ERROR', 'error': str(task_result)}
                else:
                    if task_type == 'quality':
                        result['quality_validation'] = task_result
                        if not task_result.get('passed', False):
                            result['risk_assessment']['quality_risk'] = 'HIGH'
                    else:
                        result['compliance_validation'] = task_result
                        if task_result.get('action') == 'BLOCK':
                            result['risk_assessment']['compliance_risk'] = 'HIGH'
                        elif task_result.get('action') == 'SANITIZE':
                            result['risk_assessment']['compliance_risk'] = 'MEDIUM'
                            result['sanitized_content'] = task_result.get('sanitized_text', content)
        
        return result
    
    def _determine_overall_status(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Determine overall validation status based on all results"""
        
        quality_passed = result.get('quality_validation', {}).get('passed', True)
        compliance_action = result.get('compliance_validation', {}).get('action', 'ALLOW')
        
        # Check if already determined (e.g., early blocking)
        if result['overall_status'] in ['BLOCKED', 'ERROR']:
            return result
        
        # Determine based on validation results
        if compliance_action == 'BLOCK':
            result['overall_status'] = 'BLOCKED'
            result['overall_message'] = 'Content blocked due to compliance violations'
            result['risk_assessment']['overall_risk'] = 'HIGH'
        
        elif not quality_passed and self.config.fail_on_any_violation:
            result['overall_status'] = 'BLOCKED'
            result['overall_message'] = 'Content blocked due to quality issues'
            result['risk_assessment']['overall_risk'] = 'HIGH'
        
        elif compliance_action == 'SANITIZE':
            result['overall_status'] = 'SANITIZED'
            result['overall_message'] = 'Content sanitized to remove compliance issues'
            
            # Upgrade risk if quality also failed
            if not quality_passed:
                result['risk_assessment']['overall_risk'] = 'MEDIUM'
            else:
                result['risk_assessment']['overall_risk'] = 'LOW'
        
        elif not quality_passed:
            result['overall_status'] = 'WARNING'
            result['overall_message'] = 'Content approved with quality warnings'
            result['risk_assessment']['overall_risk'] = 'MEDIUM'
        
        else:
            result['overall_status'] = 'APPROVED'
            result['overall_message'] = 'Content fully approved'
            result['risk_assessment']['overall_risk'] = 'LOW'
        
        return result
    
    def _apply_sanitization(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply additional sanitization if needed"""
        if 'sanitized_content' not in result:
            result['sanitized_content'] = result['content']
        
        # Could add additional sanitization logic here
        # For now, we rely on the compliance checker's sanitization
        
        return result
    
    def _generate_recommendations(self, result: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on validation results"""
        recommendations = []
        
        # Add compliance recommendations
        compliance_recs = result.get('compliance_validation', {}).get('recommendations', [])
        recommendations.extend(compliance_recs)
        
        # Add quality recommendations
        quality_validation = result.get('quality_validation', {})
        if not quality_validation.get('passed', True):
            recommendations.append("Review content for relevance, accuracy, and quality")
        
        # Add integration-specific recommendations
        if result['overall_status'] == 'BLOCKED':
            recommendations.append("Content must be revised before approval")
        elif result['overall_status'] == 'SANITIZED':
            recommendations.append("Review sanitized content for accuracy")
        elif result['overall_status'] == 'WARNING':
            recommendations.append("Consider manual review for quality assurance")
        
        # Risk-based recommendations
        risk_level = result['risk_assessment']['overall_risk']
        if risk_level == 'HIGH':
            recommendations.append("High risk content - requires immediate attention")
        elif risk_level == 'MEDIUM':
            recommendations.append("Medium risk content - review recommended")
        
        return list(set(recommendations))  # Remove duplicates
    
    async def validate_rag_response(
        self,
        query: str,
        response: str,
        source_documents: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Specialized validation for RAG-generated responses.
        
        Args:
            query: Original query
            response: Generated response
            source_documents: Source documents used
            **kwargs: Additional validation parameters
            
        Returns:
            Comprehensive RAG validation result
        """
        context = {
            'source_documents': source_documents,
            'generation_metadata': kwargs
        }
        
        # Run unified validation
        validation_result = await self.validate_content(
            content=response,
            query=query,
            context=context,
            metadata={'type': 'rag_response', 'source_count': len(source_documents)}
        )
        
        # Add RAG-specific analysis
        if self.quality_system:
            try:
                generation_validation = await self.quality_system.validate_generation(
                    query, response, source_documents, **kwargs
                )
                validation_result['rag_specific_validation'] = generation_validation
            except Exception as e:
                logger.error(f"RAG-specific validation failed: {e}")
                validation_result['rag_specific_validation'] = {'error': str(e)}
        
        return validation_result
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            'unified_config': {
                'quality_enabled': self.config.enable_quality_checks,
                'compliance_enabled': self.config.enable_compliance_checks,
                'quality_level': self.config.quality_level.value if self.config.enable_quality_checks else None,
                'compliance_mode': self.config.compliance_mode,
                'priority_mode': self.config.priority_mode,
                'fail_on_any_violation': self.config.fail_on_any_violation
            },
            'components': {}
        }
        
        if self.quality_system:
            status['components']['quality_system'] = self.quality_system.get_stats()
        
        if self.compliance_checker:
            status['components']['compliance_checker'] = {
                'pii_patterns': len(self.compliance_checker.config.pii_patterns),
                'medical_keywords': len(self.compliance_checker.config.medical_keywords),
                'compliance_rules': len(self.compliance_checker.config.compliance_rules)
            }
        
        return status

# Global instance
_unified_guardrail_service = None

def get_unified_guardrail_service(config: Optional[UnifiedGuardrailConfig] = None) -> UnifiedGuardrailService:
    """Get singleton unified guardrail service instance"""
    global _unified_guardrail_service
    if _unified_guardrail_service is None:
        _unified_guardrail_service = UnifiedGuardrailService(config)
    return _unified_guardrail_service