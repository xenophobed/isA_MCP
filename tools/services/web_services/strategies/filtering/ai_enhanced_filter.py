#!/usr/bin/env python
"""
AI-Enhanced Content Filtering Strategies
Advanced content filtering using LLM and embedding models for intelligent content analysis
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import re

from core.logging import get_logger
from tools.base_service import BaseService
from ..base import FilterStrategy

logger = get_logger(__name__)

class ContentQuality(Enum):
    """Content quality levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPAM = "spam"

class ContentCategory(Enum):
    """Content categories"""
    NEWS = "news"
    TECHNICAL = "technical"
    EDUCATIONAL = "educational"
    COMMERCIAL = "commercial"
    ENTERTAINMENT = "entertainment"
    PERSONAL = "personal"
    SPAM = "spam"
    OTHER = "other"

class Sentiment(Enum):
    """Content sentiment"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class AIRelevanceFilter(FilterStrategy, BaseService):
    """LLM-based content relevance scoring and filtering"""
    
    def __init__(self, user_query: str = "", relevance_threshold: float = 0.6, 
                 llm_config: Dict[str, Any] = None):
        BaseService.__init__(self, "AIRelevanceFilter")
        self.user_query = user_query
        self.relevance_threshold = relevance_threshold
        self.llm_config = llm_config or {"temperature": 0.1, "max_tokens": 200}
        self.llm = None
    
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Filter content based on AI-assessed relevance to user query"""
        try:
            logger.info(f"🧠 Applying AI relevance filter for query: '{self.user_query}'")
            
            if not self.user_query:
                logger.warning("No user query provided, returning original content")
                return content
            
            # Initialize LLM if needed
            if self.llm is None:
                self.llm = self.isa_client  # Use ISA client from BaseService
                logger.info("✅ LLM service initialized for relevance scoring")
            
            # Split content into chunks for processing
            chunks = self._split_content_into_chunks(content)
            logger.info(f"📄 Processing {len(chunks)} content chunks")
            
            # Score each chunk for relevance
            relevant_chunks = []
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:  # Skip very short chunks
                    continue
                
                relevance_score = await self._score_relevance(chunk)
                logger.info(f"   Chunk {i+1}: relevance score {relevance_score:.2f}")
                
                if relevance_score >= self.relevance_threshold:
                    relevant_chunks.append(chunk)
            
            # Combine relevant chunks
            filtered_content = '\n\n'.join(relevant_chunks)
            
            logger.info(f"✅ AI relevance filtering completed")
            logger.info(f"   Original chunks: {len(chunks)}")
            logger.info(f"   Relevant chunks: {len(relevant_chunks)}")
            logger.info(f"   Content reduction: {((len(content) - len(filtered_content)) / len(content) * 100):.1f}%")
            
            return filtered_content if filtered_content else content
            
        except Exception as e:
            logger.error(f"❌ AI relevance filtering failed: {e}")
            return content
    
    async def _score_relevance(self, chunk: str) -> float:
        """Score a content chunk for relevance using LLM"""
        try:
            scoring_prompt = f"""
            Rate the relevance of this content to the user query on a scale of 0.0 to 1.0.
            
            User Query: "{self.user_query}"
            
            Content:
            {chunk[:500]}...
            
            Consider:
            1. How directly the content answers or relates to the query
            2. Quality and depth of information
            3. Usefulness to someone searching for this topic
            
            Respond with only a single number between 0.0 and 1.0 (e.g., 0.85)
            """
            
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=scoring_prompt,
                task="chat",
                service_type="text",
                parameters=self.llm_config,
                operation_name="score_relevance"
            )
            
            response = result_data.get('text', '') if isinstance(result_data, dict) else str(result_data)
            
            # Extract numeric score from response
            import re
            score_match = re.search(r'([0-1]\.?\d*)', response)
            if score_match:
                score = float(score_match.group(1))
                return min(max(score, 0.0), 1.0)  # Clamp to [0,1]
            else:
                logger.warning(f"Could not parse relevance score from: {response}")
                return 0.5  # Default neutral score
                
        except Exception as e:
            logger.error(f"Relevance scoring failed: {e}")
            return 0.5
    
    def get_filter_name(self) -> str:
        """Get filter name"""
        return "AI Relevance Filter"
    
    async def close(self):
        """Clean up LLM resources"""
        if self.llm:
            # ISA client doesn't need explicit close
            pass
    
    def get_service_billing_info(self) -> Dict[str, Any]:
        """Get billing information for this service"""
        return self.get_billing_summary()

class AIQualityFilter(FilterStrategy, BaseService):
    """AI-based content quality assessment and filtering"""
    
    def __init__(self, min_quality: ContentQuality = ContentQuality.MEDIUM,
                 llm_config: Dict[str, Any] = None):
        BaseService.__init__(self, "AIQualityFilter")
        self.min_quality = min_quality
        self.llm_config = llm_config or {"temperature": 0.1, "max_tokens": 150}
        self.llm = None
        
        # Quality threshold mapping
        self.quality_thresholds = {
            ContentQuality.HIGH: 0.8,
            ContentQuality.MEDIUM: 0.6,
            ContentQuality.LOW: 0.4,
            ContentQuality.SPAM: 0.0
        }
    
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Filter content based on AI-assessed quality"""
        try:
            logger.info(f"🎯 Applying AI quality filter (min quality: {self.min_quality.value})")
            
            # Initialize LLM if needed
            if self.llm is None:
                self.llm = self.isa_client  # Use ISA client from BaseService
                logger.info("✅ LLM service initialized for quality assessment")
            
            # Split and assess content chunks
            chunks = self._split_content_into_chunks(content)
            high_quality_chunks = []
            
            min_threshold = self.quality_thresholds[self.min_quality]
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 30:
                    continue
                
                quality_score = await self._assess_quality(chunk)
                logger.info(f"   Chunk {i+1}: quality score {quality_score:.2f}")
                
                if quality_score >= min_threshold:
                    high_quality_chunks.append(chunk)
            
            filtered_content = '\n\n'.join(high_quality_chunks)
            
            logger.info(f"✅ AI quality filtering completed")
            logger.info(f"   Original chunks: {len(chunks)}")
            logger.info(f"   High-quality chunks: {len(high_quality_chunks)}")
            
            return filtered_content if filtered_content else content
            
        except Exception as e:
            logger.error(f"❌ AI quality filtering failed: {e}")
            return content
    
    async def _assess_quality(self, chunk: str) -> float:
        """Assess content quality using LLM"""
        try:
            quality_prompt = f"""
            Assess the quality of this content on a scale of 0.0 to 1.0.
            
            Content:
            {chunk[:400]}...
            
            Consider:
            1. Accuracy and factual correctness
            2. Clarity and readability
            3. Depth and informativeness
            4. Grammar and writing quality
            5. Whether it appears to be spam or low-effort content
            
            High quality (0.8-1.0): Well-written, informative, accurate
            Medium quality (0.6-0.8): Decent content with some value
            Low quality (0.4-0.6): Poor writing or limited value
            Spam/junk (0.0-0.4): Nonsensical, misleading, or spam
            
            Respond with only a single number between 0.0 and 1.0 (e.g., 0.75)
            """
            
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=quality_prompt,
                task="chat",
                service_type="text",
                parameters=self.llm_config,
                operation_name="assess_quality"
            )
            
            response = result_data.get('text', '') if isinstance(result_data, dict) else str(result_data)
            
            # Extract numeric score
            import re
            score_match = re.search(r'([0-1]\.?\d*)', response)
            if score_match:
                return float(score_match.group(1))
            else:
                return 0.6  # Default medium quality
                
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return 0.6
    
    def get_filter_name(self) -> str:
        """Get filter name"""
        return "AI Quality Filter"
    
    async def close(self):
        """Clean up LLM resources"""
        if self.llm:
            # ISA client doesn't need explicit close
            pass
    
    def get_service_billing_info(self) -> Dict[str, Any]:
        """Get billing information for this service"""
        return self.get_billing_summary()

class AITopicClassificationFilter(FilterStrategy, BaseService):
    """AI-based topic classification and filtering"""
    
    def __init__(self, target_categories: List[ContentCategory] = None,
                 llm_config: Dict[str, Any] = None):
        BaseService.__init__(self, "AITopicClassificationFilter")
        self.target_categories = target_categories or [ContentCategory.NEWS, ContentCategory.TECHNICAL, ContentCategory.EDUCATIONAL]
        self.llm_config = llm_config or {"temperature": 0.1, "max_tokens": 100}
        self.llm = None
    
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Filter content based on AI topic classification"""
        try:
            logger.info(f"📚 Applying AI topic classification filter")
            logger.info(f"   Target categories: {[cat.value for cat in self.target_categories]}")
            
            # Initialize LLM if needed
            if self.llm is None:
                self.llm = self.isa_client  # Use ISA client from BaseService
                logger.info("✅ LLM service initialized for topic classification")
            
            # Split and classify content chunks
            chunks = self._split_content_into_chunks(content)
            relevant_chunks = []
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:
                    continue
                
                category = await self._classify_topic(chunk)
                logger.info(f"   Chunk {i+1}: classified as {category.value}")
                
                if category in self.target_categories:
                    relevant_chunks.append(chunk)
            
            filtered_content = '\n\n'.join(relevant_chunks)
            
            logger.info(f"✅ AI topic classification completed")
            logger.info(f"   Original chunks: {len(chunks)}")
            logger.info(f"   Relevant chunks: {len(relevant_chunks)}")
            
            return filtered_content if filtered_content else content
            
        except Exception as e:
            logger.error(f"❌ AI topic classification failed: {e}")
            return content
    
    async def _classify_topic(self, chunk: str) -> ContentCategory:
        """Classify content topic using LLM"""
        try:
            categories_list = [cat.value for cat in ContentCategory]
            
            classification_prompt = f"""
            Classify this content into one of these categories: {', '.join(categories_list)}
            
            Content:
            {chunk[:300]}...
            
            Categories:
            - news: Current events, breaking news, journalism
            - technical: Programming, technology, engineering, how-to guides
            - educational: Learning materials, tutorials, academic content
            - commercial: Marketing, sales, product promotions
            - entertainment: Movies, games, sports, celebrity news
            - personal: Blogs, personal stories, opinions
            - spam: Low-quality, nonsensical, or promotional spam
            - other: Anything that doesn't fit above categories
            
            Respond with only the category name (e.g., "technical")
            """
            
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=classification_prompt,
                task="chat",
                service_type="text",
                parameters=self.llm_config,
                operation_name="classify_topic"
            )
            
            response = result_data.get('text', '') if isinstance(result_data, dict) else str(result_data)
            category_name = response.strip().lower()
            
            # Map response to enum
            for category in ContentCategory:
                if category.value in category_name:
                    return category
            
            return ContentCategory.OTHER  # Default fallback
            
        except Exception as e:
            logger.error(f"Topic classification failed: {e}")
            return ContentCategory.OTHER
    
    def get_filter_name(self) -> str:
        """Get filter name"""
        return "AI Topic Classification Filter"
    
    async def close(self):
        """Clean up LLM resources"""
        if self.llm:
            # ISA client doesn't need explicit close
            pass

class AISentimentFilter(FilterStrategy, BaseService):
    """AI-based sentiment analysis and filtering"""
    
    def __init__(self, target_sentiments: List[Sentiment] = None,
                 llm_config: Dict[str, Any] = None):
        BaseService.__init__(self, "AISentimentFilter")
        self.target_sentiments = target_sentiments or [Sentiment.POSITIVE, Sentiment.NEUTRAL]
        self.llm_config = llm_config or {"temperature": 0.1, "max_tokens": 50}
        self.llm = None
    
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Filter content based on sentiment analysis"""
        try:
            logger.info(f"😊 Applying AI sentiment filter")
            logger.info(f"   Target sentiments: {[s.value for s in self.target_sentiments]}")
            
            # Initialize LLM if needed
            if self.llm is None:
                self.llm = self.isa_client  # Use ISA client from BaseService
                logger.info("✅ LLM service initialized for sentiment analysis")
            
            # Split and analyze sentiment of chunks
            chunks = self._split_content_into_chunks(content)
            positive_chunks = []
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 30:
                    continue
                
                sentiment = await self._analyze_sentiment(chunk)
                logger.info(f"   Chunk {i+1}: sentiment {sentiment.value}")
                
                if sentiment in self.target_sentiments:
                    positive_chunks.append(chunk)
            
            filtered_content = '\n\n'.join(positive_chunks)
            
            logger.info(f"✅ AI sentiment filtering completed")
            logger.info(f"   Original chunks: {len(chunks)}")
            logger.info(f"   Positive sentiment chunks: {len(positive_chunks)}")
            
            return filtered_content if filtered_content else content
            
        except Exception as e:
            logger.error(f"❌ AI sentiment filtering failed: {e}")
            return content
    
    async def _analyze_sentiment(self, chunk: str) -> Sentiment:
        """Analyze sentiment using LLM"""
        try:
            sentiment_prompt = f"""
            Analyze the sentiment of this content. Classify as: positive, neutral, or negative
            
            Content:
            {chunk[:200]}...
            
            - positive: Optimistic, happy, encouraging, constructive
            - neutral: Factual, balanced, objective, informational
            - negative: Pessimistic, angry, critical, discouraging
            
            Respond with only one word: "positive", "neutral", or "negative"
            """
            
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=sentiment_prompt,
                task="chat",
                service_type="text",
                parameters=self.llm_config,
                operation_name="analyze_sentiment"
            )
            
            response = result_data.get('text', '') if isinstance(result_data, dict) else str(result_data)
            sentiment_text = response.strip().lower()
            
            if "positive" in sentiment_text:
                return Sentiment.POSITIVE
            elif "negative" in sentiment_text:
                return Sentiment.NEGATIVE
            else:
                return Sentiment.NEUTRAL
                
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return Sentiment.NEUTRAL
    
    def get_filter_name(self) -> str:
        """Get filter name"""
        return "AI Sentiment Filter"
    
    async def close(self):
        """Clean up LLM resources"""
        if self.llm:
            # ISA client doesn't need explicit close
            pass

class AILanguageFilter(FilterStrategy, BaseService):
    """AI-based language detection and filtering"""
    
    def __init__(self, target_languages: List[str] = None,
                 llm_config: Dict[str, Any] = None):
        BaseService.__init__(self, "AILanguageFilter")
        self.target_languages = target_languages or ['english', 'chinese']
        self.llm_config = llm_config or {"temperature": 0.1, "max_tokens": 30}
        self.llm = None
    
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Filter content based on language detection"""
        try:
            logger.info(f"🌍 Applying AI language filter")
            logger.info(f"   Target languages: {self.target_languages}")
            
            # Initialize LLM if needed
            if self.llm is None:
                self.llm = self.isa_client  # Use ISA client from BaseService
                logger.info("✅ LLM service initialized for language detection")
            
            # Split and detect language of chunks
            chunks = self._split_content_into_chunks(content)
            language_matched_chunks = []
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 20:
                    continue
                
                detected_language = await self._detect_language(chunk)
                logger.info(f"   Chunk {i+1}: detected language {detected_language}")
                
                if detected_language.lower() in [lang.lower() for lang in self.target_languages]:
                    language_matched_chunks.append(chunk)
            
            filtered_content = '\n\n'.join(language_matched_chunks)
            
            logger.info(f"✅ AI language filtering completed")
            logger.info(f"   Original chunks: {len(chunks)}")
            logger.info(f"   Language-matched chunks: {len(language_matched_chunks)}")
            
            return filtered_content if filtered_content else content
            
        except Exception as e:
            logger.error(f"❌ AI language filtering failed: {e}")
            return content
    
    async def _detect_language(self, chunk: str) -> str:
        """Detect language using LLM"""
        try:
            language_prompt = f"""
            Detect the language of this text. Common languages include:
            English, Chinese, Spanish, French, German, Japanese, Korean, Russian, Portuguese, Italian
            
            Text:
            {chunk[:150]}...
            
            Respond with only the language name (e.g., "English")
            """
            
            result_data, billing_info = await self.call_isa_with_billing(
                input_data=language_prompt,
                task="chat",
                service_type="text",
                parameters=self.llm_config,
                operation_name="detect_language"
            )
            
            response = result_data.get('text', '') if isinstance(result_data, dict) else str(result_data)
            return response.strip()
                
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "unknown"
    
    def get_filter_name(self) -> str:
        """Get filter name"""
        return "AI Language Filter"
    
    async def close(self):
        """Clean up LLM resources"""
        if self.llm:
            # ISA client doesn't need explicit close
            pass

class AICompositeFilter(FilterStrategy):
    """Composite AI filter that combines multiple AI filtering strategies"""
    
    def __init__(self, filters: List[FilterStrategy]):
        self.filters = filters
    
    async def filter(self, content: str, criteria: Optional[Dict[str, Any]] = None) -> str:
        """Apply multiple AI filters in sequence"""
        try:
            logger.info(f"🔗 Applying composite AI filter with {len(self.filters)} strategies")
            
            filtered_content = content
            original_length = len(content)
            
            for i, filter_strategy in enumerate(self.filters):
                filter_name = filter_strategy.__class__.__name__
                logger.info(f"   Step {i+1}: Applying {filter_name}")
                
                before_length = len(filtered_content)
                filtered_content = await filter_strategy.filter(filtered_content, criteria)
                after_length = len(filtered_content)
                
                reduction = ((before_length - after_length) / before_length * 100) if before_length > 0 else 0
                logger.info(f"   {filter_name}: {reduction:.1f}% content reduction")
            
            total_reduction = ((original_length - len(filtered_content)) / original_length * 100) if original_length > 0 else 0
            logger.info(f"✅ Composite AI filtering completed: {total_reduction:.1f}% total reduction")
            
            return filtered_content
            
        except Exception as e:
            logger.error(f"❌ Composite AI filtering failed: {e}")
            return content
    
    def get_filter_name(self) -> str:
        """Get filter name"""
        return "AI Composite Filter"
    
    async def close(self):
        """Clean up all filter resources"""
        for filter_strategy in self.filters:
            if hasattr(filter_strategy, 'close'):
                await filter_strategy.close()

# Base class method for content chunking
def _split_content_into_chunks(self, content: str, max_chunk_size: int = 1000) -> List[str]:
    """Split content into manageable chunks for AI processing"""
    # Split by paragraphs first
    paragraphs = content.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        if len(current_chunk) + len(paragraph) + 2 <= max_chunk_size:
            current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

# Add the chunking method to all filter classes
for filter_class in [AIRelevanceFilter, AIQualityFilter, AITopicClassificationFilter, AISentimentFilter, AILanguageFilter]:
    filter_class._split_content_into_chunks = _split_content_into_chunks