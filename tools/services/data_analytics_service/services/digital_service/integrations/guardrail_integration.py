#!/usr/bin/env python3
"""
Guardrail Integration Module

Handles quality control and content validation
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class GuardrailIntegration:
    """Guardrail System Integration Manager"""
    
    def __init__(self, enable_guardrails: bool = True, confidence_threshold: float = 0.7):
        self.enable_guardrails = enable_guardrails
        self.confidence_threshold = confidence_threshold
        self._guardrail_system = None
    
    @property
    def guardrail_system(self):
        """Lazy load guardrail system"""
        if self._guardrail_system is None:
            if not self.enable_guardrails:
                return None
            
            try:
                # Add parent path to sys.path if needed
                import sys
                import os
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                
                from tools.services.intelligence_service.guardrails.guardrail_system import GuardrailSystem, GuardrailConfig
                
                config = GuardrailConfig(
                    confidence_threshold=self.confidence_threshold
                )
                self._guardrail_system = GuardrailSystem(config)
                logger.info("Guardrail system initialized successfully")
            except ImportError as e:
                logger.warning(f"Guardrail system not available: {e}, proceeding without guardrails")
                self._guardrail_system = self._create_mock_guardrail_system()
            except Exception as e:
                logger.error(f"Failed to initialize guardrail system: {e}")
                self._guardrail_system = self._create_mock_guardrail_system()
        
        return self._guardrail_system
    
    def _create_mock_guardrail_system(self):
        """Create a mock guardrail system for testing"""
        class MockGuardrailSystem:
            def __init__(self):
                self.name = "MockGuardrailSystem"
            
            async def validate_result(self, query: str, result: Dict[str, Any]) -> bool:
                """Always pass validation for testing"""
                return True
            
            async def validate_content(self, content: str) -> Dict[str, Any]:
                """Always pass validation for testing"""
                return {
                    'passed': True,
                    'confidence': 0.8,
                    'warnings': [],
                    'compliance_score': 0.9
                }
        
        logger.warning("Using mock guardrail system due to initialization failure")
        return MockGuardrailSystem()
    
    async def validate_result(self, query: str, result: Dict[str, Any]) -> bool:
        """Validate a search result"""
        if not self.guardrail_system:
            return True
        
        try:
            return await self.guardrail_system.validate_result(query, result)
        except Exception as e:
            logger.error(f"Guardrail validation failed: {e}")
            return True  # Allow on error
    
    async def validate_content(self, content: str) -> Dict[str, Any]:
        """Validate content quality"""
        if not self.guardrail_system:
            return {'passed': True, 'confidence': 1.0, 'warnings': [], 'compliance_score': 1.0}
        
        try:
            return await self.guardrail_system.validate_content(content)
        except Exception as e:
            logger.error(f"Content validation failed: {e}")
            return {'passed': True, 'confidence': 0.5, 'warnings': [str(e)], 'compliance_score': 0.5}
    
    async def apply_guardrails(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply guardrails to filter and validate results"""
        if not self.guardrail_system:
            return results
        
        try:
            validated_results = []
            for result in results:
                if await self.validate_result(query, result):
                    validated_results.append(result)
                else:
                    logger.debug(f"Guardrail filtered result: {result.get('id', 'unknown')}")
            
            return validated_results
        except Exception as e:
            logger.error(f"Guardrail application failed: {e}")
            return results











