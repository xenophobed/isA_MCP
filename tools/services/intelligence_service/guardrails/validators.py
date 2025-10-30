#!/usr/bin/env python3
"""
Validation Components for Guardrail System

Implements specific validators for different aspects of RAG quality control.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseValidator(ABC):
    """Base class for all validators"""
    
    def __init__(self, threshold: float = 0.5):
        """
        Initialize validator
        
        Args:
            threshold: Minimum score threshold for passing validation
        """
        self.threshold = threshold
        self._isa_client = None
    
    async def _get_client(self):
        """Lazy load ISA client"""
        if self._isa_client is None:
            try:
                from core.clients.model_client import get_isa_client
                self._isa_client = await get_isa_client()
            except ImportError:
                logger.warning("ISA client not available for validation")
        return self._isa_client
    
    @abstractmethod
    async def validate(
        self,
        query: str,
        response: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate a query-response pair
        
        Args:
            query: Original query
            response: Response to validate
            result: Full result object
            context: Additional context
            
        Returns:
            Validation result with 'passed', 'confidence', and optional details
        """
        pass

class RelevanceValidator(BaseValidator):
    """Validates query-response relevance using semantic similarity"""
    
    def __init__(self, threshold: float = 0.6):
        super().__init__(threshold)
    
    async def validate(
        self,
        query: str,
        response: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate relevance between query and response"""
        try:
            # Method 1: Use embedding similarity if available
            semantic_score = result.get('semantic_score', result.get('score', 0.0))
            
            if semantic_score > 0:
                confidence = semantic_score
                passed = confidence >= self.threshold
                
                return {
                    'passed': passed,
                    'confidence': confidence,
                    'method': 'embedding_similarity',
                    'threshold': self.threshold,
                    'details': {
                        'semantic_score': semantic_score,
                        'threshold_met': passed
                    }
                }
            
            # Method 2: Use ISA for relevance scoring
            client = await self._get_client()
            if client:
                confidence = await self._isa_relevance_check(query, response)
                passed = confidence >= self.threshold

                return {
                    'passed': passed,
                    'confidence': confidence,
                    'method': 'isa_relevance',
                    'threshold': self.threshold
                }
            
            # Method 3: Simple keyword-based relevance
            confidence = self._keyword_relevance(query, response)
            passed = confidence >= self.threshold
            
            return {
                'passed': passed,
                'confidence': confidence,
                'method': 'keyword_relevance',
                'threshold': self.threshold
            }
            
        except Exception as e:
            logger.error(f"Relevance validation failed: {e}")
            return {
                'passed': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    async def _isa_relevance_check(self, query: str, response: str) -> float:
        """Use ISA to check query-response relevance"""
        try:
            relevance_prompt = f"""
            Rate the relevance of this response to the given query on a scale of 0.0 to 1.0.
            
            Query: {query}
            Response: {response}
            
            Consider:
            - Does the response answer the query?
            - Is the response on-topic?
            - Does it address the main intent?
            
            Provide only a numeric score between 0.0 and 1.0.
            """

            client = await self._get_client()
            result = await client._underlying_client.invoke(
                input_data=relevance_prompt,
                task="chat",
                service_type="text"
            )
            
            if result.get('success'):
                score_text = result.get('result', '0.5').strip()
                try:
                    return float(score_text)
                except ValueError:
                    # Extract number from response
                    import re
                    numbers = re.findall(r'0\.\d+|1\.0', score_text)
                    return float(numbers[0]) if numbers else 0.5
            
            return 0.5
            
        except Exception as e:
            logger.error(f"ISA relevance check failed: {e}")
            return 0.5
    
    def _keyword_relevance(self, query: str, response: str) -> float:
        """Simple keyword-based relevance scoring"""
        try:
            # Extract meaningful words from query (remove stopwords)
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
            
            query_words = set(re.findall(r'\b\w+\b', query.lower()))
            response_words = set(re.findall(r'\b\w+\b', response.lower()))
            
            # Remove stopwords
            query_words = query_words - stopwords
            response_words = response_words - stopwords
            
            if not query_words:
                return 0.5
            
            # Calculate overlap
            overlap = len(query_words & response_words)
            return min(overlap / len(query_words), 1.0)
            
        except Exception as e:
            logger.error(f"Keyword relevance failed: {e}")
            return 0.5

class HallucinationValidator(BaseValidator):
    """Validates responses for hallucinations and factual accuracy"""
    
    def __init__(self, threshold: float = 0.8, enable_fact_checking: bool = True):
        super().__init__(threshold)
        self.enable_fact_checking = enable_fact_checking
    
    async def validate(
        self,
        query: str,
        response: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate response for hallucinations"""
        try:
            # Check for obvious hallucination patterns
            pattern_score = self._check_hallucination_patterns(response)
            
            # If fact checking is enabled and we have sources
            fact_check_score = 1.0
            if self.enable_fact_checking and context and context.get('source_documents'):
                fact_check_score = await self._check_factual_grounding(
                    response, context['source_documents']
                )
            
            # Use ISA for advanced hallucination detection
            isa_score = 1.0
            client = await self._get_client()
            if client:
                isa_score = await self._isa_hallucination_check(query, response)
            
            # Combine scores (weighted average)
            combined_score = (pattern_score * 0.3 + fact_check_score * 0.4 + isa_score * 0.3)
            passed = combined_score >= self.threshold
            
            return {
                'passed': passed,
                'confidence': combined_score,
                'threshold': self.threshold,
                'details': {
                    'pattern_score': pattern_score,
                    'fact_check_score': fact_check_score,
                    'isa_score': isa_score,
                    'combined_score': combined_score
                }
            }
            
        except Exception as e:
            logger.error(f"Hallucination validation failed: {e}")
            return {
                'passed': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _check_hallucination_patterns(self, response: str) -> float:
        """Check for common hallucination patterns"""
        try:
            hallucination_indicators = [
                r'\b(?:I think|I believe|I assume|probably|maybe|might be)\b',
                r'\b(?:as far as I know|to my knowledge|I recall)\b',
                r'\b(?:fictional|imaginary|hypothetical)\b',
                r'\b(?:I don\'t have|I cannot access|I\'m not sure)\b'
            ]
            
            response_lower = response.lower()
            penalty = 0.0
            
            for pattern in hallucination_indicators:
                matches = len(re.findall(pattern, response_lower))
                penalty += matches * 0.1  # Each match reduces confidence
            
            # Check for overly specific claims without context
            specific_numbers = len(re.findall(r'\b\d{4,}\b', response))  # 4+ digit numbers
            if specific_numbers > 2:
                penalty += 0.2
            
            # Check for definitive statements about uncertain topics
            definitive_patterns = [
                r'\b(?:definitely|certainly|absolutely|guaranteed)\b'
            ]
            for pattern in definitive_patterns:
                matches = len(re.findall(pattern, response_lower))
                penalty += matches * 0.05
            
            return max(0.0, 1.0 - penalty)
            
        except Exception as e:
            logger.error(f"Pattern check failed: {e}")
            return 0.5
    
    async def _check_factual_grounding(
        self,
        response: str,
        source_documents: List[Dict[str, Any]]
    ) -> float:
        """Check if response is grounded in source documents"""
        try:
            if not source_documents:
                return 0.5
            
            # Extract key claims from response
            claims = self._extract_factual_claims(response)
            if not claims:
                return 0.8  # No specific claims to verify
            
            # Check each claim against source documents
            source_texts = [doc.get('text', '') for doc in source_documents]
            combined_sources = ' '.join(source_texts)
            
            supported_claims = 0
            for claim in claims:
                if self._is_claim_supported(claim, combined_sources):
                    supported_claims += 1
            
            return supported_claims / len(claims) if claims else 0.8
            
        except Exception as e:
            logger.error(f"Factual grounding check failed: {e}")
            return 0.5
    
    def _extract_factual_claims(self, response: str) -> List[str]:
        """Extract factual claims from response"""
        # Simple sentence splitting for factual claims
        sentences = re.split(r'[.!?]+', response)
        claims = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Minimum length for a claim
                # Filter out questions and commands
                if not sentence.endswith('?') and not sentence.startswith(('please', 'try', 'consider')):
                    claims.append(sentence)
        
        return claims[:5]  # Limit to top 5 claims
    
    def _is_claim_supported(self, claim: str, source_text: str) -> bool:
        """Check if a claim is supported by source text"""
        # Simple keyword overlap check
        claim_words = set(re.findall(r'\b\w+\b', claim.lower()))
        source_words = set(re.findall(r'\b\w+\b', source_text.lower()))
        
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        claim_words = claim_words - stopwords
        source_words = source_words - stopwords
        
        if not claim_words:
            return True
        
        overlap = len(claim_words & source_words)
        return overlap / len(claim_words) >= 0.3  # 30% keyword overlap
    
    async def _isa_hallucination_check(self, query: str, response: str) -> float:
        """Use ISA to detect hallucinations"""
        try:
            hallucination_prompt = f"""
            Evaluate this response for potential hallucinations or unfounded claims.
            Rate from 0.0 (many hallucinations) to 1.0 (no hallucinations).
            
            Query: {query}
            Response: {response}
            
            Look for:
            - Unsupported factual claims
            - Made-up information
            - Overconfident statements without evidence
            - Fictional details
            
            Provide only a numeric score between 0.0 and 1.0.
            """

            client = await self._get_client()
            result = await client._underlying_client.invoke(
                input_data=hallucination_prompt,
                task="chat",
                service_type="text"
            )
            
            if result.get('success'):
                score_text = result.get('result', '0.5').strip()
                try:
                    return float(score_text)
                except ValueError:
                    numbers = re.findall(r'0\.\d+|1\.0', score_text)
                    return float(numbers[0]) if numbers else 0.5
            
            return 0.5
            
        except Exception as e:
            logger.error(f"ISA hallucination check failed: {e}")
            return 0.5

class SafetyValidator(BaseValidator):
    """Validates responses for safety and toxicity"""
    
    def __init__(self, threshold: float = 0.9):
        super().__init__(threshold)
    
    async def validate(
        self,
        query: str,
        response: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate response for safety"""
        try:
            # Rule-based safety check
            rule_score = self._rule_based_safety_check(response)
            
            # ISA-based safety check
            isa_score = 1.0
            client = await self._get_client()
            if client:
                isa_score = await self._isa_safety_check(response)
            
            # Combined score
            combined_score = (rule_score + isa_score) / 2
            passed = combined_score >= self.threshold
            
            return {
                'passed': passed,
                'confidence': combined_score,
                'threshold': self.threshold,
                'details': {
                    'rule_score': rule_score,
                    'isa_score': isa_score
                }
            }
            
        except Exception as e:
            logger.error(f"Safety validation failed: {e}")
            return {
                'passed': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _rule_based_safety_check(self, response: str) -> float:
        """Rule-based safety checking"""
        try:
            response_lower = response.lower()
            
            # List of safety concerns
            harmful_patterns = [
                r'\b(?:kill|murder|suicide|self-harm|violence|attack)\b',
                r'\b(?:bomb|weapon|explosive|terrorist)\b',
                r'\b(?:hate|racist|sexist|discriminat)\w*\b',
                r'\b(?:illegal|fraud|scam|steal|hack)\b',
                r'\b(?:drug|cocaine|heroin|meth)\b'
            ]
            
            penalty = 0.0
            for pattern in harmful_patterns:
                matches = len(re.findall(pattern, response_lower))
                penalty += matches * 0.3  # Heavy penalty for harmful content
            
            return max(0.0, 1.0 - penalty)
            
        except Exception as e:
            logger.error(f"Rule-based safety check failed: {e}")
            return 0.5
    
    async def _isa_safety_check(self, response: str) -> float:
        """Use ISA for safety checking"""
        try:
            safety_prompt = f"""
            Evaluate this text for safety concerns on a scale of 0.0 to 1.0.
            0.0 = Very unsafe (harmful, toxic, dangerous)
            1.0 = Completely safe
            
            Text: {response}
            
            Check for:
            - Harmful instructions
            - Toxic language
            - Dangerous content
            - Illegal activities
            - Hate speech
            
            Provide only a numeric score between 0.0 and 1.0.
            """

            client = await self._get_client()
            result = await client._underlying_client.invoke(
                input_data=safety_prompt,
                task="chat",
                service_type="text"
            )
            
            if result.get('success'):
                score_text = result.get('result', '0.5').strip()
                try:
                    return float(score_text)
                except ValueError:
                    numbers = re.findall(r'0\.\d+|1\.0', score_text)
                    return float(numbers[0]) if numbers else 0.5
            
            return 0.5
            
        except Exception as e:
            logger.error(f"ISA safety check failed: {e}")
            return 0.5

class QualityValidator(BaseValidator):
    """Validates response quality, coherence, and completeness"""
    
    def __init__(
        self,
        threshold: float = 0.6,
        min_length: int = 10,
        max_length: int = 5000,
        require_coherence: bool = True
    ):
        super().__init__(threshold)
        self.min_length = min_length
        self.max_length = max_length
        self.require_coherence = require_coherence
    
    async def validate(
        self,
        query: str,
        response: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate response quality"""
        try:
            # Length check
            length_score = self._check_length(response)
            
            # Coherence check
            coherence_score = 1.0
            if self.require_coherence:
                coherence_score = self._check_coherence(response)
            
            # Completeness check
            completeness_score = self._check_completeness(query, response)
            
            # Language quality check
            language_score = self._check_language_quality(response)
            
            # Combined score
            combined_score = (
                length_score * 0.2 +
                coherence_score * 0.3 +
                completeness_score * 0.3 +
                language_score * 0.2
            )
            
            passed = combined_score >= self.threshold
            
            return {
                'passed': passed,
                'confidence': combined_score,
                'threshold': self.threshold,
                'details': {
                    'length_score': length_score,
                    'coherence_score': coherence_score,
                    'completeness_score': completeness_score,
                    'language_score': language_score,
                    'response_length': len(response)
                }
            }
            
        except Exception as e:
            logger.error(f"Quality validation failed: {e}")
            return {
                'passed': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _check_length(self, response: str) -> float:
        """Check if response length is appropriate"""
        length = len(response)
        
        if length < self.min_length:
            return 0.0
        elif length > self.max_length:
            return 0.3  # Too long but not completely invalid
        else:
            # Optimal length range
            if self.min_length <= length <= 1000:
                return 1.0
            else:
                # Gradually decrease score for very long responses
                return max(0.5, 1.0 - (length - 1000) / (self.max_length - 1000) * 0.5)
    
    def _check_coherence(self, response: str) -> float:
        """Check response coherence and structure"""
        try:
            sentences = re.split(r'[.!?]+', response)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) < 2:
                return 0.8  # Single sentence is usually coherent
            
            # Check for proper sentence structure
            well_formed = 0
            for sentence in sentences:
                if len(sentence) > 10 and ' ' in sentence:  # Basic sentence check
                    well_formed += 1
            
            structure_score = well_formed / len(sentences)
            
            # Check for repetition (sign of poor coherence)
            unique_sentences = len(set(sentences))
            repetition_score = unique_sentences / len(sentences)
            
            return (structure_score + repetition_score) / 2
            
        except Exception as e:
            logger.error(f"Coherence check failed: {e}")
            return 0.5
    
    def _check_completeness(self, query: str, response: str) -> float:
        """Check if response adequately addresses the query"""
        try:
            # Simple heuristic: longer responses tend to be more complete
            # but adjust based on query complexity
            
            query_length = len(query)
            response_length = len(response)
            
            # Expected response length based on query
            expected_min = max(50, query_length * 2)
            expected_max = query_length * 10
            
            if response_length < expected_min:
                return response_length / expected_min
            elif response_length > expected_max:
                return 0.8  # Very long responses might be verbose
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Completeness check failed: {e}")
            return 0.5
    
    def _check_language_quality(self, response: str) -> float:
        """Check basic language quality"""
        try:
            # Check for basic language quality indicators
            score = 1.0
            
            # Check for proper capitalization
            sentences = re.split(r'[.!?]+', response)
            capitalized = sum(1 for s in sentences if s.strip() and s.strip()[0].isupper())
            if sentences and capitalized / len(sentences) < 0.7:
                score -= 0.2
            
            # Check for excessive repetition of words
            words = re.findall(r'\b\w+\b', response.lower())
            if words:
                unique_ratio = len(set(words)) / len(words)
                if unique_ratio < 0.5:  # Too much repetition
                    score -= 0.3
            
            # Check for excessive punctuation or symbols
            punct_ratio = len(re.findall(r'[^\w\s]', response)) / len(response) if response else 0
            if punct_ratio > 0.2:  # More than 20% punctuation
                score -= 0.2
            
            return max(0.0, score)
            
        except Exception as e:
            logger.error(f"Language quality check failed: {e}")
            return 0.5