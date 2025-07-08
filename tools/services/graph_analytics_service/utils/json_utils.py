#!/usr/bin/env python3
"""
Shared JSON utilities for graph analytics services
"""

import json
import re
from typing import Any
from core.logging import get_logger

logger = get_logger(__name__)

class JSONUtils:
    """Utility class for JSON parsing and fixing"""
    
    @staticmethod
    def fix_structured_json(json_str: str, expected_wrapper: str = None) -> str:
        """
        Fix structured output JSON truncation issues
        
        Args:
            json_str: The potentially malformed JSON string
            expected_wrapper: Expected wrapper key (e.g., "entities", "relations")
            
        Returns:
            Fixed JSON string
        """
        try:
            # First, try to parse as-is
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse error: {e}, attempting to fix...")
            
            # Remove trailing commas
            cleaned = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix unterminated strings
            if '"' in cleaned and cleaned.count('"') % 2 != 0:
                last_quote_pos = cleaned.rfind('"')
                if last_quote_pos > 0:
                    before_quote = cleaned[:last_quote_pos]
                    if before_quote.count('"') % 2 == 0:
                        # This is a start quote, terminate the string
                        cleaned = cleaned[:last_quote_pos + 1]
            
            # Ensure proper structure for expected wrapper
            if not cleaned.strip().startswith('{'):
                cleaned = '{' + cleaned
            
            # Handle truncated arrays in the expected wrapper
            if expected_wrapper and f'"{expected_wrapper}"' in cleaned and '[' in cleaned:
                cleaned = JSONUtils._fix_array_wrapper(cleaned, expected_wrapper)
            
            # Ensure proper JSON object closure
            if not cleaned.rstrip().endswith('}'):
                if cleaned.rstrip().endswith(']'):
                    cleaned = cleaned.rstrip() + '}'
                else:
                    cleaned += ']}'
            
            # Final cleanup
            cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
            
            return cleaned
    
    @staticmethod
    def _fix_array_wrapper(json_str: str, wrapper_key: str) -> str:
        """Fix truncated arrays in JSON wrapper objects"""
        wrapper_start = json_str.find(f'"{wrapper_key}"')
        array_start = json_str.find('[', wrapper_start)
        
        if array_start != -1:
            # Count brackets from array start
            open_brackets = 0
            last_valid_pos = array_start
            
            for i in range(array_start, len(json_str)):
                char = json_str[i]
                if char == '[':
                    open_brackets += 1
                elif char == ']':
                    open_brackets -= 1
                    if open_brackets == 0:
                        last_valid_pos = i + 1
                        break
            
            # If array is not properly closed, close it
            if open_brackets > 0:
                truncated_part = json_str[array_start:]
                open_objects = truncated_part.count('{') - truncated_part.count('}')
                json_str = json_str[:last_valid_pos] + '}' * open_objects + ']'
        
        return json_str
    
    @staticmethod
    def safe_parse_json(json_str: str, expected_wrapper: str = None, fallback: Any = None) -> Any:
        """
        Safely parse JSON with automatic fixing and fallback
        
        Args:
            json_str: JSON string to parse
            expected_wrapper: Expected wrapper key for structured output
            fallback: Fallback value if parsing fails
            
        Returns:
            Parsed JSON object or fallback value
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                fixed_json = JSONUtils.fix_structured_json(json_str, expected_wrapper)
                return json.loads(fixed_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Could not fix JSON: {e}")
                return fallback or {}
    
    @staticmethod
    def extract_json_from_text(text: str, expected_wrapper: str = None) -> Any:
        """
        Extract JSON from text that may contain other content
        
        Args:
            text: Text containing JSON
            expected_wrapper: Expected wrapper key
            
        Returns:
            Parsed JSON object or empty dict
        """
        # Try to find JSON boundaries
        start_chars = ['{', '[']
        end_chars = ['}', ']']
        
        for start_char, end_char in zip(start_chars, end_chars):
            json_start = text.find(start_char)
            json_end = text.rfind(end_char) + 1
            
            if json_start != -1 and json_end != -1:
                json_str = text[json_start:json_end]
                result = JSONUtils.safe_parse_json(json_str, expected_wrapper)
                if result:
                    return result
        
        return {}