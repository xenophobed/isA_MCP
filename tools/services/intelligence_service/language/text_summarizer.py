#!/usr/bin/env python3
"""
Text Summarizer - Atomic Intelligence Service
Provides intelligent text summarization with multiple styles and length options
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from core.logging import get_logger

logger = get_logger(__name__)

class SummaryStyle(Enum):
    """Text summary styles for different use cases"""
    EXECUTIVE = "executive"      # High-level strategic focus
    DETAILED = "detailed"        # Comprehensive with all details
    TECHNICAL = "technical"      # Technical focus and precision
    ABSTRACT = "abstract"        # Academic-style structured format
    BULLET_POINTS = "bullets"    # Concise bullet format
    NARRATIVE = "narrative"      # Story-telling style
    COMPARATIVE = "comparative"  # Comparison focused

class SummaryLength(Enum):
    """Summary length options"""
    BRIEF = "brief"        # 1-2 paragraphs
    MEDIUM = "medium"      # 3-5 paragraphs
    DETAILED = "detailed"  # 6+ paragraphs

class TextSummarizer:
    """
    Intelligent text summarization service using ISA client
    
    Features:
    - Multiple summary styles (executive, technical, narrative, etc.)
    - Configurable length options (brief, medium, detailed)
    - Key points extraction
    - Custom focus areas
    - Quality scoring and metrics
    """
    
    def __init__(self):
        self._client = None
        self._init_templates()
        
    async def _get_client(self):
        """Lazy load ISA client"""
        if self._client is None:
            from core.clients.model_client import get_isa_client
            self._client = await get_isa_client()
        return self._client
    
    def _init_templates(self):
        """Initialize summary templates for different styles"""
        self.summary_templates = {
            SummaryStyle.EXECUTIVE: """Create an executive summary focusing on:
1. Key findings and insights
2. Strategic implications  
3. Recommendations or next steps
4. Main conclusions
5. Critical points

Format as a professional summary with clear structure.""",
            
            SummaryStyle.DETAILED: """Create a detailed summary including:
1. All major topics and themes
2. Supporting details and evidence
3. Important data and statistics
4. Key relationships and connections
5. Comprehensive conclusions

Organize with clear sections and maintain all critical information.""",
            
            SummaryStyle.TECHNICAL: """Create a technical summary focusing on:
1. Technical details and specifications
2. Methods and approaches used
3. Technical findings and results
4. Implementation considerations
5. Technical conclusions

Use precise technical language and maintain accuracy.""",
            
            SummaryStyle.ABSTRACT: """Create an academic-style abstract including:
1. Purpose and objectives
2. Methods or approach
3. Key findings and results
4. Main conclusions
5. Significance and implications

Format as a structured academic abstract.""",
            
            SummaryStyle.BULLET_POINTS: """Create a bullet-point summary with:
• Main topics (3-5 bullets)
• Key findings (3-5 bullets)  
• Important details (3-5 bullets)
• Main conclusions (2-3 bullets)

Use clear, concise bullet points for easy scanning.""",
            
            SummaryStyle.NARRATIVE: """Create a narrative summary that:
1. Tells the story of the content
2. Flows logically from beginning to end
3. Highlights key developments
4. Explains relationships and connections
5. Concludes with main outcomes

Write in an engaging, story-like format.""",
            
            SummaryStyle.COMPARATIVE: """Create a comparative summary focusing on:
1. Different approaches or options presented
2. Comparisons and contrasts
3. Advantages and disadvantages
4. Similarities and differences
5. Comparative conclusions

Emphasize comparisons and analysis."""
        }
        
        self.length_specs = {
            SummaryLength.BRIEF: "1-2 concise paragraphs",
            SummaryLength.MEDIUM: "3-5 well-developed paragraphs", 
            SummaryLength.DETAILED: "6 or more comprehensive paragraphs"
        }
    
    async def summarize_text(
        self,
        text: str,
        style: SummaryStyle = SummaryStyle.DETAILED,
        length: SummaryLength = SummaryLength.MEDIUM,
        custom_focus: Optional[List[str]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1200
    ) -> Dict[str, Any]:
        """
        Generate intelligent text summary
        
        Args:
            text: Text to summarize
            style: Summary style (executive, technical, narrative, etc.)
            length: Target length (brief, medium, detailed)
            custom_focus: Optional list of specific focus areas
            temperature: Controls creativity (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dictionary with summary results and metrics
        """
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a non-empty string")
            
            # Build comprehensive prompt
            base_prompt = self.summary_templates[style]
            length_instruction = f"Target length: {self.length_specs[length]}"
            
            focus_instruction = ""
            if custom_focus:
                focus_instruction = f"\nPay special attention to: {', '.join(custom_focus)}"
            
            # Smart text truncation
            text_content = text[:4000] if len(text) > 4000 else text
            
            full_prompt = f"""{base_prompt}

{length_instruction}{focus_instruction}

Text to summarize:
{text_content}

Create the summary according to the specified style and length."""

            # Call ISA client for generation using new API
            client = await self._get_client()

            response = await client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": full_prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            # Process complete response
            result = response.choices[0].message.content
            billing_info = {}  # New API doesn't expose billing in same way
            
            # Handle AIMessage object
            if hasattr(result, 'content'):
                summary_text = result.content
            elif isinstance(result, str):
                summary_text = result
            else:
                summary_text = str(result)
            
            if not summary_text:
                raise Exception("No result found in response")
            
            # Calculate quality metrics
            quality_score = self._calculate_summary_quality(summary_text, text, style, length)
            
            # Log billing info
            if billing_info:
                logger.info(f"💰 Text summarization cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            return {
                'success': True,
                'summary': summary_text,
                'style': style.value,
                'length': length.value,
                'word_count': len(summary_text.split()),
                'character_count': len(summary_text),
                'quality_score': quality_score,
                'compression_ratio': len(summary_text) / len(text) if text else 0,
                'billing_info': billing_info,
                'original_length': len(text)
            }
            
        except Exception as e:
            logger.error(f"Text summarization failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'summary': '',
                'style': style.value,
                'length': length.value,
                'word_count': 0,
                'character_count': 0,
                'quality_score': 0.0,
                'compression_ratio': 0.0
            }
    
    async def extract_key_points(
        self,
        text: str,
        max_points: int = 10,
        temperature: float = 0.1,
        max_tokens: int = 800
    ) -> Dict[str, Any]:
        """
        Extract key points from text as structured list
        
        Args:
            text: Text to extract points from
            max_points: Maximum number of points to extract
            temperature: Controls creativity
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dictionary with extracted key points and metadata
        """
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a non-empty string")
            
            # Smart text truncation
            text_content = text[:3000] if len(text) > 3000 else text
            
            prompt = f"""Extract the most important key points from this text. 
            
Return exactly {max_points} key points as a numbered list:
1. [First key point]
2. [Second key point]
...

Focus on the most significant information, insights, and conclusions.

Text:
{text_content}"""

            # Call ISA client
            client = await self._get_client()

            response = await client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            # Process complete response
            points_text = response.choices[0].message.content
            billing_info = {}  # New API doesn't expose billing in same way
            
            if not points_text:
                raise Exception("No result found in response")
            
            # Parse and structure key points
            key_points = self._parse_numbered_list(points_text)
            
            # Log billing info
            if billing_info:
                logger.info(f"💰 Key points extraction cost: ${billing_info.get('cost_usd', 0.0):.6f}")
            
            return {
                'success': True,
                'key_points': key_points,
                'total_points': len(key_points),
                'requested_points': max_points,
                'confidence': 0.9 if key_points else 0.3,
                'billing_info': billing_info,
                'raw_response': points_text
            }
            
        except Exception as e:
            logger.error(f"Key points extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'key_points': [],
                'total_points': 0,
                'confidence': 0.0
            }
    
    async def analyze_content(
        self,
        text: str,
        analysis_type: str = "comprehensive",
        custom_criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive content analysis
        
        Args:
            text: Text to analyze
            analysis_type: Type of analysis (comprehensive, focused, quick)
            custom_criteria: Custom analysis criteria
            
        Returns:
            Dictionary with analysis results
        """
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Text must be a non-empty string")
            
            criteria = custom_criteria or [
                "main themes and topics",
                "key arguments and evidence",
                "writing style and tone",
                "target audience",
                "conclusions and implications"
            ]
            
            criteria_text = "\n".join(f"- {criterion}" for criterion in criteria)
            
            prompt = f"""Analyze the following text according to these criteria:

{criteria_text}

Provide a structured analysis covering each criterion.

Text to analyze:
{text[:3000]}

Return your analysis in a clear, organized format."""

            client = await self._get_client()

            response = await client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
                stream=False
            )

            # Process complete response
            analysis_text = response.choices[0].message.content
            billing_info = {}  # New API doesn't expose billing in same way
            
            if not analysis_text:
                raise Exception("No result found in response")
            
            return {
                'success': True,
                'analysis': analysis_text,
                'analysis_type': analysis_type,
                'criteria_used': criteria,
                'text_length': len(text),
                'billing_info': billing_info
            }
            
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis': '',
                'analysis_type': analysis_type
            }
    
    def _calculate_summary_quality(self, summary: str, original: str, 
                                 style: SummaryStyle, length: SummaryLength) -> float:
        """Calculate summary quality score based on multiple factors"""
        try:
            if not summary or not original:
                return 0.0
            
            quality = 0.0
            summary_words = len(summary.split())
            
            # Length appropriateness scoring
            target_ranges = {
                SummaryLength.BRIEF: (50, 150),
                SummaryLength.MEDIUM: (150, 400),
                SummaryLength.DETAILED: (400, 800)
            }
            
            min_words, max_words = target_ranges[length]
            if min_words <= summary_words <= max_words:
                quality += 0.3
            
            # Compression ratio scoring
            compression = len(summary) / len(original)
            if 0.1 <= compression <= 0.5:
                quality += 0.2
            
            # Content quality indicators
            if len(summary.split('.')) >= 3:  # Multiple sentences
                quality += 0.2
            
            # Style-specific validation
            if style == SummaryStyle.BULLET_POINTS:
                if '•' in summary or summary.count('\n') >= 3:
                    quality += 0.3
            else:
                if summary_words >= 50:
                    quality += 0.3
            
            return min(quality, 1.0)
            
        except Exception:
            return 0.5
    
    def _parse_numbered_list(self, text: str) -> List[str]:
        """Parse numbered list from text into structured format"""
        try:
            points = []
            lines = text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                # Match numbered items: "1. text" or "1) text"
                if line and (line[0].isdigit() and ('. ' in line or ') ' in line)):
                    if '. ' in line:
                        content = line.split('. ', 1)[1]
                    else:
                        content = line.split(') ', 1)[1]
                    points.append(content.strip())
            
            return points
            
        except Exception:
            return []

# Global instance for easy import
text_summarizer = TextSummarizer()

# Convenience functions for direct usage
async def summarize_text(
    text: str, 
    style: SummaryStyle = SummaryStyle.DETAILED, 
    length: SummaryLength = SummaryLength.MEDIUM, 
    **kwargs
) -> Dict[str, Any]:
    """Summarize text with specified style and length"""
    return await text_summarizer.summarize_text(text, style, length, **kwargs)

async def extract_key_points(text: str, max_points: int = 10, **kwargs) -> Dict[str, Any]:
    """Extract key points from text"""
    return await text_summarizer.extract_key_points(text, max_points, **kwargs)

async def analyze_content(text: str, **kwargs) -> Dict[str, Any]:
    """Analyze content comprehensively"""
    return await text_summarizer.analyze_content(text, **kwargs)