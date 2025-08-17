#!/usr/bin/env python3
"""
AI Enhanced Processor

Integrates traditional file processing with AI intelligence services
for enhanced understanding and analysis capabilities.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class AIEnhancedResult:
    """AI enhanced processing result"""
    traditional_result: Dict[str, Any]
    ai_enhanced_result: Dict[str, Any]
    confidence: float
    processing_time: float
    enhancement_features: List[str]

class AIEnhancedProcessor:
    """
    Processor that combines traditional methods with AI intelligence services
    for enhanced understanding and analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # AI services (lazy loaded)
        self._image_analyzer = None
        self._audio_analyzer = None
        self._text_generator = None
        self._text_summarizer = None
        
        # Enhancement settings
        self.enable_ai_enhancement = self.config.get('enable_ai_enhancement', True)
        self.ai_confidence_threshold = self.config.get('ai_confidence_threshold', 0.7)
        
        logger.info("AI Enhanced Processor initialized")
    
    @property
    def image_analyzer(self):
        """Lazy load image analyzer"""
        if self._image_analyzer is None:
            from tools.services.intelligence_service.vision.image_analyzer import ImageAnalyzer
            self._image_analyzer = ImageAnalyzer()
        return self._image_analyzer
    
    @property
    def audio_analyzer(self):
        """Lazy load audio analyzer"""
        if self._audio_analyzer is None:
            from tools.services.intelligence_service.audio.audio_analyzer import AudioAnalyzer
            self._audio_analyzer = AudioAnalyzer()
        return self._audio_analyzer
    
    @property
    def text_generator(self):
        """Lazy load text generator"""
        if self._text_generator is None:
            from tools.services.intelligence_service.language.text_generator import TextGenerator
            self._text_generator = TextGenerator()
        return self._text_generator
    
    @property
    def text_summarizer(self):
        """Lazy load text summarizer"""
        if self._text_summarizer is None:
            from tools.services.intelligence_service.language.text_summarizer import TextSummarizer
            self._text_summarizer = TextSummarizer()
        return self._text_summarizer
    
    async def enhance_image_analysis(self, image_path: str, traditional_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance image analysis with AI vision capabilities.
        
        Args:
            image_path: Path to image file
            traditional_result: Result from traditional image processing
            
        Returns:
            AI enhanced analysis
        """
        try:
            if not self.enable_ai_enhancement:
                return traditional_result
            
            start_time = time.time()
            enhanced_result = traditional_result.copy()
            
            # AI-powered comprehensive image understanding
            ai_analysis = await self.image_analyzer.analyze(
                image=image_path,
                prompt="""Analyze this image comprehensively. Provide:
1. Detailed description of the content
2. Objects and their relationships
3. Scene context and setting
4. Any text visible in the image
5. Overall quality and clarity assessment
6. Potential use cases or categories

Format as structured JSON with clear sections."""
            )
            
            if ai_analysis.success:
                enhanced_result['ai_analysis'] = {
                    'comprehensive_description': ai_analysis.response,
                    'model_used': ai_analysis.model_used,
                    'confidence': 0.9,  # AI analysis confidence
                    'processing_time': ai_analysis.processing_time
                }
                
                # AI-powered text extraction enhancement
                if 'text' in traditional_result and traditional_result['text']:
                    text_enhancement = await self.image_analyzer.analyze(
                        image=image_path,
                        prompt=f"""The traditional OCR extracted this text: "{traditional_result['text'][:500]}..."
                        
Please review and enhance:
1. Correct any OCR errors
2. Improve formatting and structure
3. Add context or missing information
4. Identify the document type/purpose"""
                    )
                    
                    if text_enhancement.success:
                        enhanced_result['ai_enhanced_text'] = {
                            'corrected_text': text_enhancement.response,
                            'improvements': 'OCR correction and context enhancement'
                        }
                
                # Scene understanding enhancement
                scene_analysis = await self.image_analyzer.analyze(
                    image=image_path,
                    prompt="""Analyze the scene type and context:
1. Is this a document, photograph, diagram, or other type?
2. What is the primary purpose or function?
3. What industry or domain does this relate to?
4. What actions might someone take with this content?"""
                )
                
                if scene_analysis.success:
                    enhanced_result['scene_understanding'] = {
                        'analysis': scene_analysis.response,
                        'context_type': 'ai_inferred'
                    }
            
            enhanced_result['ai_enhancement_time'] = time.time() - start_time
            return enhanced_result
            
        except Exception as e:
            logger.error(f"AI image enhancement failed: {e}")
            enhanced_result = traditional_result.copy()
            enhanced_result['ai_enhancement_error'] = str(e)
            return enhanced_result
    
    async def enhance_audio_analysis(self, audio_path: str, traditional_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance audio analysis with AI audio capabilities.
        
        Args:
            audio_path: Path to audio file
            traditional_result: Result from traditional audio processing
            
        Returns:
            AI enhanced analysis
        """
        try:
            if not self.enable_ai_enhancement:
                return traditional_result
            
            start_time = time.time()
            enhanced_result = traditional_result.copy()
            
            # Get transcript from traditional processing or generate new one
            transcript = traditional_result.get('transcript', '')
            
            if transcript and len(transcript) > 10:  # Only enhance if we have substantial text
                # AI-powered content analysis
                content_analysis = await self.text_generator.generate(
                    prompt=f"""Analyze this audio transcript comprehensively:

Transcript: "{transcript}"

Provide analysis including:
1. Main topics and themes
2. Sentiment and emotional tone
3. Key insights or important points
4. Speaker characteristics (if identifiable)
5. Content category (meeting, interview, lecture, etc.)
6. Action items or decisions (if any)
7. Overall quality and clarity assessment

Format as structured analysis with clear sections.""",
                    temperature=0.3  # Lower temperature for analytical tasks
                )
                
                enhanced_result['ai_content_analysis'] = {
                    'analysis': content_analysis,
                    'enhancement_type': 'content_understanding'
                }
                
                # AI-powered summarization
                if len(transcript) > 500:  # Only summarize longer content
                    summary = await self.text_summarizer.summarize(
                        text=transcript,
                        max_length=200,
                        style='comprehensive'
                    )
                    
                    enhanced_result['ai_summary'] = {
                        'summary': summary,
                        'compression_ratio': len(summary) / len(transcript)
                    }
                
                # AI-powered speaker analysis
                speaker_analysis = await self.text_generator.generate(
                    prompt=f"""Analyze the speaker characteristics from this transcript:

"{transcript[:1000]}..."

Identify:
1. Communication style (formal, casual, technical, etc.)
2. Expertise level on the topic
3. Emotional state or mood
4. Likely audience or context
5. Key personality traits evident in speech""",
                    temperature=0.2
                )
                
                enhanced_result['ai_speaker_analysis'] = {
                    'analysis': speaker_analysis,
                    'confidence': 0.8
                }
            
            enhanced_result['ai_enhancement_time'] = time.time() - start_time
            return enhanced_result
            
        except Exception as e:
            logger.error(f"AI audio enhancement failed: {e}")
            enhanced_result = traditional_result.copy()
            enhanced_result['ai_enhancement_error'] = str(e)
            return enhanced_result
    
    async def enhance_text_analysis(self, text: str, traditional_result: Dict[str, Any], context: str = '') -> Dict[str, Any]:
        """
        Enhance text analysis with AI language capabilities.
        
        Args:
            text: Text content to analyze
            traditional_result: Result from traditional text processing
            context: Additional context about the text source
            
        Returns:
            AI enhanced analysis
        """
        try:
            if not self.enable_ai_enhancement or not text or len(text) < 10:
                return traditional_result
            
            start_time = time.time()
            enhanced_result = traditional_result.copy()
            
            # AI-powered content understanding
            content_analysis = await self.text_generator.generate(
                prompt=f"""Analyze this text content comprehensively:

Context: {context}
Text: "{text[:2000]}{'...' if len(text) > 2000 else ''}"

Provide detailed analysis:
1. Document type and purpose
2. Main topics and key themes
3. Writing style and tone
4. Target audience
5. Information density and complexity
6. Key insights or important facts
7. Potential use cases or applications
8. Content quality assessment

Format as structured analysis with clear sections.""",
                temperature=0.3
            )
            
            enhanced_result['ai_content_analysis'] = {
                'analysis': content_analysis,
                'text_length': len(text),
                'analysis_coverage': min(2000, len(text))
            }
            
            # AI-powered summarization for longer texts
            if len(text) > 1000:
                summary = await self.text_summarizer.summarize(
                    text=text,
                    max_length=300,
                    style='comprehensive'
                )
                
                enhanced_result['ai_summary'] = {
                    'summary': summary,
                    'compression_ratio': len(summary) / len(text)
                }
                
                # Key points extraction
                key_points = await self.text_generator.generate(
                    prompt=f"""Extract the key points from this text:

"{text}"

Provide:
1. 5-7 most important points
2. Each point should be concise but informative
3. Organize by importance
4. Include any actionable items

Format as numbered list.""",
                    temperature=0.2
                )
                
                enhanced_result['ai_key_points'] = {
                    'points': key_points,
                    'extraction_method': 'ai_analysis'
                }
            
            # Structure and organization analysis
            structure_analysis = await self.text_generator.generate(
                prompt=f"""Analyze the structure and organization of this text:

"{text[:1500]}{'...' if len(text) > 1500 else ''}"

Identify:
1. Document structure (sections, headings, flow)
2. Information hierarchy
3. Logical organization
4. Missing elements or gaps
5. Improvement suggestions""",
                temperature=0.2
            )
            
            enhanced_result['ai_structure_analysis'] = {
                'analysis': structure_analysis,
                'text_sample_size': min(1500, len(text))
            }
            
            enhanced_result['ai_enhancement_time'] = time.time() - start_time
            return enhanced_result
            
        except Exception as e:
            logger.error(f"AI text enhancement failed: {e}")
            enhanced_result = traditional_result.copy()
            enhanced_result['ai_enhancement_error'] = str(e)
            return enhanced_result
    
    async def enhance_document_understanding(self, file_path: str, traditional_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance overall document understanding with AI.
        
        Args:
            file_path: Path to the document file
            traditional_result: Combined traditional processing results
            
        Returns:
            AI enhanced document understanding
        """
        try:
            if not self.enable_ai_enhancement:
                return traditional_result
            
            start_time = time.time()
            enhanced_result = traditional_result.copy()
            
            # Extract all available text from traditional processing
            all_text = []
            
            # Collect text from various sources
            if 'text' in traditional_result:
                all_text.append(traditional_result['text'])
            if 'combined_text' in traditional_result:
                all_text.append(traditional_result['combined_text'])
            if 'transcript' in traditional_result:
                all_text.append(traditional_result['transcript'])
            
            combined_text = '\n\n'.join(filter(None, all_text))
            
            if combined_text and len(combined_text) > 50:
                # AI-powered holistic document analysis
                document_analysis = await self.text_generator.generate(
                    prompt=f"""Analyze this document comprehensively:

File: {Path(file_path).name}
Content: "{combined_text[:3000]}{'...' if len(combined_text) > 3000 else ''}"

Provide comprehensive analysis:
1. Document type and classification
2. Primary purpose and use case
3. Target audience and domain
4. Key information and insights
5. Document quality and completeness
6. Potential improvements or issues
7. Recommended actions or next steps
8. Business/educational/personal value

Format as detailed structured analysis.""",
                    temperature=0.3
                )
                
                enhanced_result['ai_document_understanding'] = {
                    'comprehensive_analysis': document_analysis,
                    'analyzed_content_length': len(combined_text),
                    'file_context': Path(file_path).name
                }
                
                # Content categorization and tagging
                categorization = await self.text_generator.generate(
                    prompt=f"""Categorize and tag this document content:

Content: "{combined_text[:2000]}{'...' if len(combined_text) > 2000 else ''}"

Provide:
1. Primary category (business, academic, legal, technical, etc.)
2. Secondary categories or subcategories
3. Industry or domain tags
4. Content type tags (report, manual, presentation, etc.)
5. Complexity level (beginner, intermediate, advanced)
6. Urgency/importance level if applicable

Format as structured tags and categories.""",
                    temperature=0.2
                )
                
                enhanced_result['ai_categorization'] = {
                    'categories_and_tags': categorization,
                    'classification_confidence': 0.85
                }
            
            enhanced_result['ai_document_enhancement_time'] = time.time() - start_time
            return enhanced_result
            
        except Exception as e:
            logger.error(f"AI document enhancement failed: {e}")
            enhanced_result = traditional_result.copy()
            enhanced_result['ai_document_enhancement_error'] = str(e)
            return enhanced_result
    
    async def generate_insights_and_recommendations(self, enhanced_result: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """
        Generate AI-powered insights and recommendations.
        
        Args:
            enhanced_result: Combined traditional + AI enhanced results
            file_path: Original file path
            
        Returns:
            Final result with insights and recommendations
        """
        try:
            if not self.enable_ai_enhancement:
                return enhanced_result
            
            start_time = time.time()
            final_result = enhanced_result.copy()
            
            # Generate actionable insights
            insights_prompt = f"""Based on the analysis of {Path(file_path).name}, generate actionable insights:

Analysis Summary:
- File type: {Path(file_path).suffix}
- Processing successful: {enhanced_result.get('success', False)}
- Content available: {bool(enhanced_result.get('combined_text') or enhanced_result.get('text'))}

Generate:
1. Key insights about the content
2. Potential use cases or applications  
3. Quality assessment and confidence level
4. Recommended follow-up actions
5. Integration suggestions with other systems
6. Optimization recommendations

Format as practical, actionable recommendations."""
            
            insights = await self.text_generator.generate(
                prompt=insights_prompt,
                temperature=0.4
            )
            
            final_result['ai_insights_and_recommendations'] = {
                'insights': insights,
                'generated_at': time.time(),
                'confidence': 0.8
            }
            
            final_result['total_ai_enhancement_time'] = time.time() - start_time
            return final_result
            
        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")
            final_result = enhanced_result.copy()
            final_result['ai_insights_error'] = str(e)
            return final_result
    
    def get_enhancement_capabilities(self) -> Dict[str, List[str]]:
        """Get available AI enhancement capabilities."""
        return {
            'image_enhancements': [
                'comprehensive_scene_analysis',
                'text_correction_and_enhancement',
                'context_understanding',
                'quality_assessment'
            ],
            'audio_enhancements': [
                'content_analysis',
                'sentiment_analysis',
                'speaker_analysis',
                'summarization'
            ],
            'text_enhancements': [
                'content_understanding',
                'structure_analysis',
                'key_points_extraction',
                'summarization'
            ],
            'document_enhancements': [
                'holistic_analysis',
                'categorization_and_tagging',
                'insights_generation',
                'recommendations'
            ]
        }