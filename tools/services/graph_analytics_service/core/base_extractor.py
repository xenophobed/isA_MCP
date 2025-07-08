#!/usr/bin/env python3
"""
Base extractor class with shared functionality
"""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

from core.logging import get_logger
from tools.base_service import BaseService
from ..utils.json_utils import JSONUtils
from core.config import get_settings

logger = get_logger(__name__)

class BaseExtractor(BaseService, ABC):
    """Base class for entity and relationship extractors"""
    
    def __init__(self, service_name: str):
        """Initialize base extractor"""
        super().__init__(service_name)
        self.settings = get_settings()
        
    async def extract_with_llm(
        self, 
        text: str, 
        prompt: str, 
        expected_wrapper: str,
        operation_name: str
    ) -> List[Dict[str, Any]]:
        """
        Common LLM extraction method with standardized error handling
        
        Args:
            text: Text to extract from
            prompt: LLM prompt
            expected_wrapper: Expected JSON wrapper key (e.g., "entities", "relations")
            operation_name: Name for billing/logging
            
        Returns:
            List of extracted items
        """
        try:
            response, billing_info = await self.call_isa_with_billing(
                input_data=prompt,
                task="chat",
                service_type="text",
                parameters={
                    "max_tokens": self.settings.graph_analytics.max_tokens,
                    "temperature": self.settings.graph_analytics.temperature,
                    "response_format": {"type": "json_object"}
                },
                operation_name=operation_name
            )
            
            if not isinstance(response, str):
                logger.error(f"Unexpected response type: {type(response)}")
                return self._fallback_extraction(text)
            
            return self._parse_llm_response(response, expected_wrapper, text)
            
        except Exception as e:
            logger.error(f"LLM {operation_name} failed: {e}")
            return self._fallback_extraction(text)
    
    def _parse_llm_response(
        self, 
        response_text: str, 
        expected_wrapper: str, 
        original_text: str
    ) -> List[Dict[str, Any]]:
        """Parse LLM response with comprehensive error handling"""
        try:
            # Parse structured output format
            parsed_data = JSONUtils.safe_parse_json(
                response_text, 
                expected_wrapper, 
                fallback={}
            )
            
            # Handle different response formats
            if isinstance(parsed_data, dict) and expected_wrapper in parsed_data:
                items_data = parsed_data[expected_wrapper]
            elif isinstance(parsed_data, list):
                items_data = parsed_data
            else:
                logger.warning(f"Unexpected response format: {type(parsed_data)}")
                return self._fallback_extraction(original_text)
            
            # Validate items data
            if not isinstance(items_data, list):
                logger.error(f"Items data is not a list: {type(items_data)}")
                return self._fallback_extraction(original_text)
            
            # Process and validate each item
            processed_items = []
            for item_data in items_data:
                if self._validate_item_data(item_data):
                    processed_item = self._process_item_data(item_data)
                    if processed_item:
                        processed_items.append(processed_item)
            
            logger.info(f"✅ Successfully extracted {len(processed_items)} items using structured output")
            return processed_items
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response text: {response_text[:500]}...")
            return self._fallback_extraction(original_text)
    
    def should_use_llm_for_text(self, text: str) -> bool:
        """Determine if LLM should be used for given text length"""
        if len(text) > self.settings.graph_analytics.long_text_threshold:
            logger.info(f"🧠 Long text ({len(text):,} chars), using LLM long context processing")
            return True
        return True  # Default to LLM for better accuracy
    
    @abstractmethod
    def _validate_item_data(self, item_data: Dict[str, Any]) -> bool:
        """Validate individual item data from LLM response"""
        pass
    
    @abstractmethod 
    def _process_item_data(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and transform individual item data"""
        pass
    
    @abstractmethod
    def _fallback_extraction(self, text: str) -> List[Dict[str, Any]]:
        """Fallback extraction method when LLM fails"""
        pass
    
    def _standardize_confidence(self, confidence: Any) -> float:
        """Standardize confidence scores"""
        if isinstance(confidence, (int, float)):
            return max(0.0, min(1.0, float(confidence)))
        return self.settings.graph_analytics.default_confidence
    
    def _clean_text_field(self, text: Any) -> str:
        """Clean and validate text fields"""
        if not text:
            return ""
        return str(text).strip()
    
    def _get_safe_field(self, data: Dict[str, Any], field: str, default: Any = None) -> Any:
        """Safely get field from data dict"""
        return data.get(field, default) if isinstance(data, dict) else default