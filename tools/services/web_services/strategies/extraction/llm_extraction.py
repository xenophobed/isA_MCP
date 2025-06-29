#!/usr/bin/env python
"""
LLM-based Data Extraction Strategy
Advanced data extraction using Large Language Models for intelligent content understanding
Based on isa_model inference framework
"""
import json
from typing import Dict, Any, List, Optional
from playwright.async_api import Page

from core.logging import get_logger
from isa_model.inference import AIFactory
from ..base import ExtractionStrategy

logger = get_logger(__name__)

class LLMExtractionStrategy(ExtractionStrategy):
    """Extract structured data using Large Language Models for intelligent content understanding"""
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize LLM extraction strategy
        
        Args:
            schema: Extraction schema with LLM configuration
                   Format: {
                       "name": "Schema Name",
                       "content_type": "article|product|contact|table|general",
                       "fields": [
                           {"name": "title", "description": "Main title or heading"},
                           {"name": "content", "description": "Main content or description"},
                           {"name": "price", "description": "Price information", "type": "currency"}
                       ],
                       "extraction_prompt": "Custom extraction prompt (optional)",
                       "llm_config": {
                           "model": "gpt-4.1-nano",
                           "temperature": 0.1,
                           "max_tokens": 2000
                       }
                   }
        """
        self.schema = schema
        self.name = schema.get("name", "LLM Extraction")
        self.content_type = schema.get("content_type", "general")
        self.fields = schema.get("fields", [])
        self.extraction_prompt = schema.get("extraction_prompt")
        self.llm_config = schema.get("llm_config", {"temperature": 0.1, "max_tokens": 2000})
        
        self.ai_factory = AIFactory()
        self.llm = None
    
    async def extract(self, page: Page, html: str) -> List[Dict[str, Any]]:
        """Extract data using LLM-based intelligent analysis"""
        logger.info(f"🧠 Extracting data using LLM strategy: {self.name}")
        
        try:
            # Initialize LLM service
            if self.llm is None:
                self.llm = self.ai_factory.get_llm(config=self.llm_config)
                logger.info(f"✅ LLM service initialized: {self.llm.get_model_info()['name']}")
            
            # Get clean text content from page
            clean_text = await self._extract_clean_text(page)
            
            if not clean_text or len(clean_text.strip()) < 50:
                logger.warning("⚠️ Insufficient text content for LLM extraction")
                return []
            
            # Build extraction prompt
            extraction_prompt = self._build_extraction_prompt(clean_text)
            
            logger.info(f"📝 Sending extraction request to LLM...")
            logger.info(f"   Content length: {len(clean_text)} characters")
            logger.info(f"   Fields to extract: {[f['name'] for f in self.fields]}")
            
            # Get LLM response
            response = await self.llm.ainvoke(extraction_prompt)
            
            # Parse LLM response into structured data
            extracted_data = await self._parse_llm_response(response)
            
            logger.info(f"✅ LLM extraction completed: {len(extracted_data)} items extracted")
            
            # Get token usage statistics
            usage = self.llm.get_last_token_usage()
            cost = self.llm.get_last_usage_with_cost()
            logger.info(f"💰 Token usage: {usage['total_tokens']} tokens, Cost: ${cost['cost_usd']:.6f}")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ LLM extraction failed: {e}")
            return []
    
    async def _extract_clean_text(self, page: Page) -> str:
        """Extract clean text content from page for LLM processing"""
        try:
            # Extract main content, removing scripts, styles, and navigation
            clean_text = await page.evaluate('''
                () => {
                    // Remove unwanted elements
                    const unwanted = document.querySelectorAll('script, style, nav, header, footer, .ad, .advertisement, .sidebar');
                    unwanted.forEach(el => el.remove());
                    
                    // Get main content
                    const main = document.querySelector('main, .main, .content, article, .article, #content');
                    if (main) {
                        return main.innerText || main.textContent || '';
                    }
                    
                    // Fallback to body content
                    return document.body.innerText || document.body.textContent || '';
                }
            ''')
            
            # Basic cleaning
            lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
            clean_text = '\n'.join(lines)
            
            # Limit text length to avoid token limits (roughly 3000 tokens = 12000 chars)
            if len(clean_text) > 10000:
                clean_text = clean_text[:10000] + "...\n[Content truncated for LLM processing]"
                logger.info(f"📝 Content truncated to {len(clean_text)} characters")
            
            return clean_text
            
        except Exception as e:
            logger.error(f"Failed to extract clean text: {e}")
            return ""
    
    def _build_extraction_prompt(self, content: str) -> str:
        """Build optimized extraction prompt for LLM"""
        
        # Use custom prompt if provided
        if self.extraction_prompt:
            return self.extraction_prompt.format(content=content)
        
        # Build schema description
        fields_description = []
        for field in self.fields:
            field_desc = f"- {field['name']}: {field.get('description', 'Extract relevant information')}"
            if 'type' in field:
                field_desc += f" (format: {field['type']})"
            fields_description.append(field_desc)
        
        fields_text = '\n'.join(fields_description)
        
        # Content type specific instructions
        type_instructions = {
            "article": "Focus on extracting article content including title, author, date, and main content.",
            "product": "Focus on extracting product information including name, price, description, and specifications.",
            "contact": "Focus on extracting contact information including names, emails, phones, and addresses.",
            "table": "Focus on extracting tabular data with proper structure and relationships.",
            "general": "Extract the most relevant and structured information from the content."
        }
        
        instruction = type_instructions.get(self.content_type, type_instructions["general"])
        
        prompt = f"""You are an expert data extraction AI. {instruction}

EXTRACTION SCHEMA:
{fields_text}

INSTRUCTIONS:
1. Analyze the content carefully and extract information for each field in the schema
2. If multiple items exist (like multiple products), extract each as a separate object
3. If a field is not found, use an empty string or appropriate null value
4. Ensure extracted data is accurate and follows the specified format
5. Return results as a JSON array of objects

CONTENT TO ANALYZE:
{content}

RESPONSE FORMAT:
Return only a valid JSON array in this format:
[
    {{
        "{self.fields[0]['name'] if self.fields else 'data'}": "extracted value",
        ...
    }}
]"""

        return prompt
    
    async def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into structured data"""
        try:
            # Clean response to extract JSON
            response = response.strip()
            
            # Try to find JSON array in response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
            else:
                # Try to find JSON object and wrap in array
                obj_match = re.search(r'\{.*\}', response, re.DOTALL)
                if obj_match:
                    json_str = f"[{obj_match.group()}]"
                else:
                    logger.warning("⚠️ No valid JSON found in LLM response")
                    return []
            
            # Parse JSON
            try:
                parsed_data = json.loads(json_str)
                if isinstance(parsed_data, dict):
                    parsed_data = [parsed_data]
                elif not isinstance(parsed_data, list):
                    logger.warning("⚠️ LLM response is not a list or dict")
                    return []
                
                # Validate and clean data
                cleaned_data = []
                for item in parsed_data:
                    if isinstance(item, dict) and any(value for value in item.values() if value):
                        cleaned_data.append(item)
                
                return cleaned_data
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse JSON from LLM response: {e}")
                logger.error(f"Response content: {response[:200]}...")
                
                # Fallback: try to extract key-value pairs manually
                return self._fallback_parse(response)
        
        except Exception as e:
            logger.error(f"❌ Failed to parse LLM response: {e}")
            return []
    
    def _fallback_parse(self, response: str) -> List[Dict[str, Any]]:
        """Fallback parser for non-JSON responses"""
        try:
            # Simple key-value extraction for common patterns
            result = {}
            lines = response.split('\n')
            
            for line in lines:
                line = line.strip()
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        # Match against schema fields
                        for field in self.fields:
                            if field['name'].lower() in key or key in field['name'].lower():
                                result[field['name']] = value
                                break
            
            return [result] if result else []
            
        except Exception as e:
            logger.error(f"❌ Fallback parsing failed: {e}")
            return []
    
    def get_strategy_name(self) -> str:
        return f"llm_extraction_{self.name.lower().replace(' ', '_')}"
    
    async def close(self):
        """Clean up LLM service"""
        if self.llm:
            await self.llm.close()
            self.llm = None

class PredefinedLLMSchemas:
    """Predefined LLM extraction schemas for common content types"""
    
    @staticmethod
    def get_article_extraction_schema() -> Dict[str, Any]:
        """Schema for extracting article/blog content"""
        return {
            "name": "Article Content",
            "content_type": "article",
            "fields": [
                {"name": "title", "description": "Main title or headline of the article"},
                {"name": "author", "description": "Author name or byline"},
                {"name": "date", "description": "Publication date"},
                {"name": "content", "description": "Main article content or summary"},
                {"name": "tags", "description": "Topics, categories, or tags"},
                {"name": "summary", "description": "Brief summary of the article"}
            ],
            "llm_config": {"temperature": 0.1, "max_tokens": 1500}
        }
    
    @staticmethod
    def get_product_extraction_schema() -> Dict[str, Any]:
        """Schema for extracting product information"""
        return {
            "name": "Product Information",
            "content_type": "product",
            "fields": [
                {"name": "name", "description": "Product name or title"},
                {"name": "price", "description": "Current price", "type": "currency"},
                {"name": "original_price", "description": "Original or list price", "type": "currency"},
                {"name": "description", "description": "Product description or features"},
                {"name": "brand", "description": "Brand or manufacturer"},
                {"name": "rating", "description": "Customer rating or score"},
                {"name": "reviews_count", "description": "Number of reviews"},
                {"name": "availability", "description": "Stock status or availability"}
            ],
            "llm_config": {"temperature": 0.1, "max_tokens": 2000}
        }
    
    @staticmethod
    def get_contact_extraction_schema() -> Dict[str, Any]:
        """Schema for extracting contact information"""
        return {
            "name": "Contact Information",
            "content_type": "contact",
            "fields": [
                {"name": "name", "description": "Person or organization name"},
                {"name": "email", "description": "Email address"},
                {"name": "phone", "description": "Phone number"},
                {"name": "address", "description": "Physical address"},
                {"name": "website", "description": "Website URL"},
                {"name": "title", "description": "Job title or position"},
                {"name": "company", "description": "Company or organization"}
            ],
            "llm_config": {"temperature": 0.1, "max_tokens": 1000}
        }
    
    @staticmethod
    def get_event_extraction_schema() -> Dict[str, Any]:
        """Schema for extracting event information"""
        return {
            "name": "Event Information",
            "content_type": "general",
            "fields": [
                {"name": "title", "description": "Event name or title"},
                {"name": "date", "description": "Event date and time"},
                {"name": "location", "description": "Event location or venue"},
                {"name": "description", "description": "Event description or details"},
                {"name": "organizer", "description": "Event organizer or host"},
                {"name": "ticket_price", "description": "Ticket price or cost", "type": "currency"},
                {"name": "registration_url", "description": "Registration or ticket URL"}
            ],
            "llm_config": {"temperature": 0.1, "max_tokens": 1500}
        }
    
    @staticmethod
    def get_research_extraction_schema() -> Dict[str, Any]:
        """Schema for extracting research/academic content"""
        return {
            "name": "Research Content",
            "content_type": "article",
            "fields": [
                {"name": "title", "description": "Research paper or article title"},
                {"name": "authors", "description": "List of authors"},
                {"name": "abstract", "description": "Abstract or summary"},
                {"name": "keywords", "description": "Research keywords or topics"},
                {"name": "methodology", "description": "Research methodology or approach"},
                {"name": "findings", "description": "Key findings or results"},
                {"name": "publication", "description": "Journal or publication venue"},
                {"name": "doi", "description": "DOI or identifier"}
            ],
            "llm_config": {"temperature": 0.1, "max_tokens": 2000}
        }
    
    @staticmethod
    def get_custom_schema(fields: List[Dict[str, str]], content_type: str = "general") -> Dict[str, Any]:
        """Create custom extraction schema"""
        return {
            "name": "Custom Extraction",
            "content_type": content_type,
            "fields": fields,
            "llm_config": {"temperature": 0.1, "max_tokens": 1500}
        }