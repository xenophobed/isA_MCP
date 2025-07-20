#!/usr/bin/env python3
"""
Text Extractor - Atomic Intelligence Service
Extracts and understands text from various sources using AI
"""

from typing import Dict, Any, List, Optional
import json
from core.logging import get_logger

logger = get_logger(__name__)

class TextExtractor:
    """
    Atomic service for AI-powered text extraction and understanding
    
    Capabilities:
    - Named Entity Recognition (NER)
    - Text classification
    - Key information extraction
    - Text summarization
    - Sentiment analysis
    """
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        """Lazy load ISA client"""
        if self._client is None:
            from core.isa_client_factory import get_isa_client
            self._client = get_isa_client()
        return self._client
    
    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        confidence_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Extract named entities from text using AI
        
        Args:
            text: Text to analyze
            entity_types: Specific entity types to extract (optional)
            confidence_threshold: Minimum confidence score
            
        Returns:
            Dictionary with extracted entities and metadata
        """
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a non-empty string")
            
            # Prepare extraction prompt
            text_content = text[:3000] if len(text) > 3000 else text
            
            prompt = f"""Extract named entities from the following text. Return a JSON object with entities categorized by type.

Text: {text_content}

Extract entities for these categories:
- PERSON: People's names
- ORGANIZATION: Companies, institutions
- LOCATION: Places, addresses, countries
- DATE: Dates and time expressions
- MONEY: Monetary amounts
- PRODUCT: Products and services
- EVENT: Events and activities

Return format:
{{
    "entities": {{
        "PERSON": [{{"name": "entity", "confidence": 0.95, "position": [start, end]}}],
        "ORGANIZATION": [...],
        ...
    }},
    "total_entities": number,
    "confidence_scores": {{"entity_type": "avg_confidence"}}
}}"""

            # Call ISA for entity extraction
            response = await self.client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text",
                temperature=0.1,
                stream=False  # 禁用流式输出，获取完整响应
            )
            
            if not response.get('success'):
                raise Exception(f"ISA generation failed: {response.get('error', 'Unknown error')}")
            
            # Process complete response (streaming disabled)
            result = response.get('result', '')
            billing_info = response.get('metadata', {}).get('billing', {})
            
            # Handle AIMessage object
            if hasattr(result, 'content'):
                result_text = result.content
            elif isinstance(result, str):
                result_text = result
            else:
                result_text = str(result)
            
            if not result_text:
                raise Exception("No result found in response")
            
            # Parse JSON response
            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                # Try to extract JSON from text
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group())
                else:
                    raise Exception("Failed to parse entity extraction response")
            
            # Filter by confidence threshold if specified
            if confidence_threshold > 0:
                filtered_entities = {}
                for entity_type, entities in result_data.get("entities", {}).items():
                    filtered_entities[entity_type] = [
                        entity for entity in entities 
                        if entity.get("confidence", 0) >= confidence_threshold
                    ]
                result_data["entities"] = filtered_entities
            
            # Calculate overall confidence
            all_confidences = []
            for entities in result_data.get("entities", {}).values():
                for entity in entities:
                    if "confidence" in entity:
                        all_confidences.append(entity["confidence"])
            
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            
            # Log billing info
            if billing_info:
                logger.info(f"💰 Entity extraction cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            return {
                'success': True,
                'data': result_data,
                'confidence': avg_confidence,
                'billing_info': billing_info,
                'total_entities': result_data.get('total_entities', 0)
            }
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0,
                'total_entities': 0
            }
    
    async def classify_text(
        self,
        text: str,
        categories: List[str],
        multi_label: bool = False
    ) -> Dict[str, Any]:
        """
        Classify text into predefined categories
        
        Args:
            text: Text to classify
            categories: List of possible categories
            multi_label: Whether text can belong to multiple categories
            
        Returns:
            Dictionary with classification results
        """
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a non-empty string")
            
            # Prepare classification prompt
            text_content = text[:3000] if len(text) > 3000 else text
            categories_str = ", ".join(categories)
            mode = "multiple categories" if multi_label else "single category"
            
            prompt = f"""Classify the following text into {mode} from the given options.

Text: {text_content}

Categories: {categories_str}

Return a JSON object:
{{
    "classification": {{"category": "confidence_score"}},
    "primary_category": "most_likely_category",
    "confidence": "overall_confidence_score",
    "reasoning": "brief explanation"
}}"""

            response = await self.client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text",
                temperature=0.1,
                stream=False  # 禁用流式输出，获取完整响应
            )
            
            if not response.get('success'):
                raise Exception(f"ISA generation failed: {response.get('error', 'Unknown error')}")
            
            # Process complete response (streaming disabled)
            result = response.get('result', '')
            billing_info = response.get('metadata', {}).get('billing', {})
            
            # Handle AIMessage object
            if hasattr(result, 'content'):
                result_text = result.content
            elif isinstance(result, str):
                result_text = result
            else:
                result_text = str(result)
            
            if not result_text:
                raise Exception("No result found in response")
            
            # Parse JSON response
            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group())
                else:
                    raise Exception("Failed to parse classification response")
            
            confidence = float(result_data.get("confidence", 0.0)) if result_data.get("confidence") else 0.0
            
            # Log billing info
            if billing_info:
                logger.info(f"💰 Text classification cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            return {
                'success': True,
                'data': result_data,
                'confidence': confidence,
                'billing_info': billing_info,
                'categories': categories,
                'multi_label': multi_label
            }
            
        except Exception as e:
            logger.error(f"Text classification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0,
                'categories': categories
            }
    
    async def extract_key_information(
        self,
        text: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract key information from text based on schema
        
        Args:
            text: Text to analyze
            schema: JSON schema for extraction (optional)
            
        Returns:
            Dictionary with extracted information
        """
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a non-empty string")
            
            # Default schema if none provided
            if not schema:
                schema = {
                    "main_topics": "List of main topics discussed",
                    "key_facts": "Important facts and data points",
                    "action_items": "Actions or tasks mentioned",
                    "dates": "Important dates mentioned",
                    "numbers": "Significant numbers or statistics",
                    "conclusions": "Main conclusions or outcomes"
                }
            
            text_content = text[:3000] if len(text) > 3000 else text
            schema_str = json.dumps(schema, indent=2)
            
            prompt = f"""Extract key information from the following text according to the provided schema.

Text: {text_content}

Schema:
{schema_str}

Return a JSON object that follows the schema structure with the extracted information."""

            response = await self.client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text",
                model="gpt-4.1-mini",  # 使用更强模型处理复杂医疗JSON解析
                temperature=0.1,
                stream=False  # 禁用流式输出，获取完整响应
            )
            
            if not response.get('success'):
                raise Exception(f"ISA generation failed: {response.get('error', 'Unknown error')}")
            
            # Process complete response (streaming disabled)
            result = response.get('result', '')
            billing_info = response.get('metadata', {}).get('billing', {})
            
            # Handle AIMessage object
            if hasattr(result, 'content'):
                result_text = result.content
            elif isinstance(result, str):
                result_text = result
            else:
                result_text = str(result)
            
            if not result_text:
                raise Exception("No result found in response")
            
            # Parse JSON response with enhanced error handling
            try:
                # First try to clean markdown formatting
                clean_text = result_text.strip()
                if clean_text.startswith('```json'):
                    clean_text = clean_text[7:]  # Remove ```json
                if clean_text.startswith('```'):
                    clean_text = clean_text[3:]   # Remove ```
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]  # Remove ```
                clean_text = clean_text.strip()
                
                result_data = json.loads(clean_text)
            except json.JSONDecodeError as e:
                logger.warning(f"Initial JSON parsing failed: {e}")
                try:
                    # Try to extract JSON from text with better regex
                    import re
                    json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        result_data = json.loads(json_str)
                    else:
                        # Try to find and fix common JSON issues
                        cleaned_text = self._clean_malformed_json(result_text)
                        if cleaned_text:
                            result_data = json.loads(cleaned_text)
                        else:
                            # Fallback to basic schema structure
                            logger.warning("Using fallback schema due to JSON parsing failure")
                            result_data = self._create_fallback_response(schema or {})
                except (json.JSONDecodeError, Exception) as fallback_error:
                    logger.error(f"All JSON parsing attempts failed: {fallback_error}")
                    # Return basic structure matching schema
                    result_data = self._create_fallback_response(schema or {})
            
            # Calculate confidence based on completeness
            expected_fields = len(schema)
            filled_fields = len([v for v in result_data.values() if v])
            confidence = filled_fields / expected_fields if expected_fields > 0 else 0.0
            
            # Log billing info
            if billing_info:
                logger.info(f"💰 Key information extraction cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            return {
                'success': True,
                'data': result_data,
                'confidence': confidence,
                'billing_info': billing_info,
                'schema_used': schema,
                'completeness': filled_fields / expected_fields if expected_fields > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Key information extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0,
                'schema_used': schema or {}
            }
    
    async def summarize_text(
        self,
        text: str,
        summary_length: str = "medium",
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate text summary using AI
        
        Args:
            text: Text to summarize
            summary_length: "short", "medium", or "long"
            focus_areas: Specific areas to focus on
            
        Returns:
            Dictionary with summary and metadata
        """
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a non-empty string")
            
            # Set length parameters
            length_settings = {
                "short": "1-2 sentences, highlighting only the most critical points",
                "medium": "1-2 paragraphs, covering main points and key details",
                "long": "3-4 paragraphs, comprehensive coverage with context"
            }
            
            text_content = text[:3000] if len(text) > 3000 else text
            length_instruction = length_settings.get(summary_length, length_settings["medium"])
            focus_instruction = ""
            if focus_areas:
                focus_instruction = f"\nPay special attention to: {', '.join(focus_areas)}"
            
            prompt = f"""Summarize the following text. {length_instruction}{focus_instruction}

Text: {text_content}

Return a JSON object:
{{
    "summary": "the summary text",
    "key_points": ["list", "of", "key", "points"],
    "confidence": "confidence_score",
    "word_count": "summary_word_count"
}}"""

            response = await self.client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text",
                temperature=0.2,
                stream=False  # 禁用流式输出，获取完整响应
            )
            
            if not response.get('success'):
                raise Exception(f"ISA generation failed: {response.get('error', 'Unknown error')}")
            
            # Process complete response (streaming disabled)
            result = response.get('result', '')
            billing_info = response.get('metadata', {}).get('billing', {})
            
            # Handle AIMessage object
            if hasattr(result, 'content'):
                result_text = result.content
            elif isinstance(result, str):
                result_text = result
            else:
                result_text = str(result)
            
            if not result_text:
                raise Exception("No result found in response")
            
            # Parse JSON response
            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group())
                else:
                    raise Exception("Failed to parse summary response")
            
            confidence = float(result_data.get("confidence", 0.8)) if result_data.get("confidence") else 0.8
            
            # Log billing info
            if billing_info:
                logger.info(f"💰 Text summarization cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            return {
                'success': True,
                'data': result_data,
                'confidence': confidence,
                'billing_info': billing_info,
                'summary_length': summary_length,
                'focus_areas': focus_areas or [],
                'original_length': len(text)
            }
            
        except Exception as e:
            logger.error(f"Text summarization failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0,
                'summary_length': summary_length
            }
    
    async def analyze_sentiment(
        self,
        text: str,
        granularity: str = "overall"
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of text
        
        Args:
            text: Text to analyze
            granularity: "overall", "aspect", or "sentence"
            
        Returns:
            Dictionary with sentiment analysis
        """
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a non-empty string")
            
            granularity_instructions = {
                "overall": "Provide overall sentiment for the entire text",
                "aspect": "Identify different aspects and their sentiments",
                "sentence": "Analyze sentiment for each sentence"
            }
            
            text_content = text[:3000] if len(text) > 3000 else text
            instruction = granularity_instructions.get(granularity, granularity_instructions["overall"])
            
            prompt = f"""Analyze the sentiment of the following text. {instruction}

Text: {text_content}

Return a JSON object:
{{
    "overall_sentiment": {{"label": "positive/negative/neutral", "score": "confidence_score"}},
    "detailed_analysis": "sentiment_breakdown",
    "confidence": "overall_confidence",
    "emotional_indicators": ["list", "of", "emotional", "words"]
}}"""

            response = await self.client.invoke(
                input_data=prompt,
                task="chat",
                service_type="text",
                temperature=0.1,
                stream=False  # 禁用流式输出，获取完整响应
            )
            
            if not response.get('success'):
                raise Exception(f"ISA generation failed: {response.get('error', 'Unknown error')}")
            
            # Process complete response (streaming disabled)
            result = response.get('result', '')
            billing_info = response.get('metadata', {}).get('billing', {})
            
            # Handle AIMessage object
            if hasattr(result, 'content'):
                result_text = result.content
            elif isinstance(result, str):
                result_text = result
            else:
                result_text = str(result)
            
            if not result_text:
                raise Exception("No result found in response")
            
            # Parse JSON response
            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group())
                else:
                    raise Exception("Failed to parse sentiment response")
            
            confidence = float(result_data.get("confidence", 0.0)) if result_data.get("confidence") else 0.0
            
            # Log billing info
            if billing_info:
                logger.info(f"💰 Sentiment analysis cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            return {
                'success': True,
                'data': result_data,
                'confidence': confidence,
                'billing_info': billing_info,
                'granularity': granularity,
                'text_length': len(text)
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'confidence': 0.0,
                'granularity': granularity
            }
    
    async def process(self, operation: str, text: str, **kwargs) -> Dict[str, Any]:
        """
        Main processing method - route to specific operations
        
        Args:
            operation: Type of operation (entities, classify, extract, summarize, sentiment)
            text: Text to process
            **kwargs: Operation-specific parameters
            
        Returns:
            Dictionary with operation results
        """
        operations = {
            "entities": self.extract_entities,
            "classify": self.classify_text,
            "extract": self.extract_key_information,
            "summarize": self.summarize_text,
            "sentiment": self.analyze_sentiment
        }
        
        if operation not in operations:
            return {
                'success': False,
                'error': f"Unknown operation: {operation}. Available: {list(operations.keys())}",
                'data': {},
                'confidence': 0.0
            }
        
        return await operations[operation](text, **kwargs)
    
    def _clean_malformed_json(self, text: str) -> Optional[str]:
        """Clean common malformed JSON issues from LLM responses"""
        try:
            import re
            
            # Extract potential JSON block
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if not json_match:
                return None
                
            json_str = json_match.group()
            
            # Common fixes for malformed JSON
            # Fix missing commas between objects/arrays
            json_str = re.sub(r'}\s*{', '},{', json_str)
            json_str = re.sub(r']\s*\[', '],[', json_str)
            json_str = re.sub(r'}\s*\[', '},[', json_str)
            json_str = re.sub(r']\s*{', '],{', json_str)
            
            # Fix missing commas after values
            json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
            json_str = re.sub(r'"\s*\n\s*{', '",\n{', json_str)
            json_str = re.sub(r'}\s*\n\s*"', '},\n"', json_str)
            
            # Fix trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            return json_str
        except Exception:
            return None
    
    def _create_fallback_response(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback response structure based on schema"""
        fallback = {}
        
        for key, description in schema.items():
            # Ensure description is a string
            desc_str = str(description) if description is not None else ""
            
            # Provide reasonable defaults based on description
            if any(word in desc_str.lower() for word in ['list', 'items', 'array']):
                fallback[key] = []
            elif any(word in desc_str.lower() for word in ['count', 'number', 'score']):
                fallback[key] = 0
            elif any(word in desc_str.lower() for word in ['date', 'time']):
                fallback[key] = ""
            else:
                fallback[key] = "Unable to extract due to parsing error"
        
        return fallback


# Global instance for easy import
text_extractor = TextExtractor()

# Convenience functions
async def extract_entities(text: str, **kwargs) -> Dict[str, Any]:
    """Extract named entities from text"""
    return await text_extractor.extract_entities(text, **kwargs)

async def classify_text(text: str, categories: List[str], **kwargs) -> Dict[str, Any]:
    """Classify text into categories"""
    return await text_extractor.classify_text(text, categories, **kwargs)

async def extract_key_information(text: str, **kwargs) -> Dict[str, Any]:
    """Extract key information from text"""
    return await text_extractor.extract_key_information(text, **kwargs)

async def summarize_text(text: str, **kwargs) -> Dict[str, Any]:
    """Summarize text"""
    return await text_extractor.summarize_text(text, **kwargs)

async def analyze_sentiment(text: str, **kwargs) -> Dict[str, Any]:
    """Analyze text sentiment"""
    return await text_extractor.analyze_sentiment(text, **kwargs)