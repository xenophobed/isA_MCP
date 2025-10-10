#!/usr/bin/env python3
"""
RAG Metrics Service
Core evaluation metrics based on RAGAS, TruLens, and industry best practices

Key Metrics:
1. Faithfulness - Answer grounded in retrieved context
2. Answer Relevance - Answer addresses the question
3. Context Relevance - Retrieved contexts are relevant
4. Context Precision - Top-ranked contexts are more relevant
5. Context Recall - All relevant information retrieved
6. Answer Correctness - Factual accuracy vs ground truth
7. Answer Similarity - Semantic similarity to expected answer
"""

import asyncio
import statistics
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from tools.services.intelligence_service.language.text_generator import TextGenerator
from tools.services.intelligence_service.language.embedding_generator import EmbeddingGenerator


@dataclass
class EvaluationMetrics:
    """Complete metrics for a single RAG evaluation"""
    # Quality Metrics (0.0-1.0)
    faithfulness: float
    answer_relevance: float
    context_relevance: float
    context_precision: float
    context_recall: float
    answer_correctness: float
    answer_similarity: float

    # Performance Metrics
    latency_ms: float
    retrieval_time_ms: float
    generation_time_ms: float
    total_tokens: int

    # Metadata
    sources_count: int
    is_degraded: bool

    def overall_score(self) -> float:
        """Calculate weighted overall quality score"""
        return (
            self.faithfulness * 0.25 +
            self.answer_relevance * 0.25 +
            self.context_relevance * 0.20 +
            self.context_precision * 0.15 +
            self.answer_correctness * 0.15
        )

    def is_passing(self, thresholds: Optional[dict] = None) -> bool:
        """Check if metrics pass quality thresholds"""
        if thresholds is None:
            thresholds = {
                'faithfulness': 0.7,
                'answer_relevance': 0.7,
                'context_relevance': 0.6,
                'overall': 0.7
            }

        return (
            self.faithfulness >= thresholds.get('faithfulness', 0.7) and
            self.answer_relevance >= thresholds.get('answer_relevance', 0.7) and
            self.context_relevance >= thresholds.get('context_relevance', 0.6) and
            self.overall_score() >= thresholds.get('overall', 0.7) and
            not self.is_degraded
        )


class RAGMetricsService:
    """
    Core service for computing RAG evaluation metrics
    Based on academic research and industry best practices
    """

    def __init__(self, model: str = "gpt-4.1-nano"):
        self.text_generator = TextGenerator()
        self.embedding_generator = EmbeddingGenerator()
        self.model = model

    async def compute_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """
        Faithfulness: Measures if answer is grounded in retrieved context

        Method: Use LLM to verify each claim in the answer against context
        - Extract claims from answer
        - Check if each claim is supported by context
        - Return proportion of supported claims
        """
        if not contexts or not answer:
            return 0.0

        context_text = "\n\n".join(f"[Context {i+1}]\n{ctx}" for i, ctx in enumerate(contexts))

        prompt = f"""Rate the faithfulness of the answer to the contexts on a scale from 0.0 to 1.0.
Faithfulness means the answer only contains information that can be verified from the contexts.

CONTEXTS:
{context_text}

ANSWER:
{answer}

RATING SCALE:
1.0 = All claims fully supported by contexts
0.8 = Most claims supported, minor unsupported details
0.6 = Mix of supported and unsupported claims
0.4 = Some claims supported, many unsupported
0.2 = Few claims supported
0.0 = No claims supported or contradicts contexts

CRITICAL: Your response must be ONLY a single number (e.g., 0.8). Do not include any explanation, reasoning, or additional text. Just the number."""

        try:
            response = await self.text_generator.generate(
                prompt=prompt,
                max_tokens=10,
                temperature=0.0
            )
            # Extract number from response (handles cases where LLM adds text)
            import re
            numbers = re.findall(r'0\.\d+|1\.0|0|1', response)
            if numbers:
                score = float(numbers[-1])  # Take last number found
            else:
                score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            print(f"Faithfulness evaluation error: {e}")
            return 0.5

    async def compute_answer_relevance(self, query: str, answer: str) -> float:
        """
        Answer Relevance: Measures if answer addresses the question

        Method: Check if answer is on-topic and directly addresses query
        Penalize degraded/fallback responses heavily
        """
        if not answer or not query:
            return 0.0

        # Immediate penalty for degraded responses
        if 'Based on your knowledge base' in answer or 'I cannot find' in answer:
            return 0.1

        prompt = f"""Rate how relevant the answer is to the question on a scale from 0.0 to 1.0.

QUESTION: {query}

ANSWER: {answer}

RATING SCALE:
1.0 = Directly and completely answers the question
0.8 = Answers the question with minor irrelevant details
0.6 = Partially answers, some irrelevant content
0.4 = Tangentially related but doesn't answer
0.2 = Minimally related to question
0.0 = Not related or off-topic

OUTPUT FORMAT: Respond with ONLY a single decimal number (e.g., 0.9). No explanation, no text, just the number."""

        try:
            response = await self.text_generator.generate(
                prompt=prompt,
                max_tokens=10,
                temperature=0.0
            )
            # Extract number from response
            import re
            numbers = re.findall(r'0\.\d+|1\.0|0|1', response)
            if numbers:
                score = float(numbers[-1])
            else:
                score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            print(f"Answer relevance evaluation error: {e}")
            return 0.5

    async def compute_context_relevance(self, query: str, contexts: List[str]) -> float:
        """
        Context Relevance: Measures average relevance of retrieved contexts

        Method: Evaluate each context's relevance to the query independently
        Return average relevance score
        """
        if not contexts:
            return 0.0

        async def evaluate_single_context(context: str) -> float:
            prompt = f"""Rate the relevance of this context for answering the query (0.0 to 1.0).

QUERY: {query}

CONTEXT: {context}

SCALE:
1.0 = Highly relevant, directly helps answer query
0.7 = Relevant with useful information
0.5 = Somewhat relevant
0.3 = Minimally relevant
0.0 = Not relevant

CRITICAL: Output ONLY a number (e.g., 0.7). No text, no explanation."""

            try:
                response = await self.text_generator.generate(
                    prompt=prompt,
                    max_tokens=10,
                    temperature=0.0
                )
                import re
                numbers = re.findall(r'0\.\d+|1\.0|0|1', response)
                if numbers:
                    score = float(numbers[-1])
                else:
                    score = float(response.strip())
                return max(0.0, min(1.0, score))
            except:
                return 0.5

        # Evaluate all contexts in parallel
        scores = await asyncio.gather(*[
            evaluate_single_context(ctx) for ctx in contexts
        ])

        return statistics.mean(scores) if scores else 0.0

    async def compute_context_precision(self, query: str, contexts: List[str]) -> float:
        """
        Context Precision: Measures if top-ranked contexts are more relevant

        Method: Calculate precision@k with position-based weighting
        Higher weight for earlier positions (better ranking)
        """
        if not contexts:
            return 0.0

        async def is_context_relevant(context: str) -> bool:
            prompt = f"""Is this context useful for answering the query?

QUERY: {query}
CONTEXT: {context}

Answer with one word only: 'yes' or 'no'"""

            try:
                response = await self.text_generator.generate(
                    prompt=prompt,
                    
                    max_tokens=5,
                    temperature=0.0
                )
                return 'yes' in response.lower()
            except:
                return False

        # Evaluate relevance of each context
        relevance_flags = await asyncio.gather(*[
            is_context_relevant(ctx) for ctx in contexts
        ])

        # Calculate position-weighted precision
        weighted_score = 0.0
        for i, is_relevant in enumerate(relevance_flags):
            weight = 1.0 / (i + 1)  # Decay weight: 1.0, 0.5, 0.33, 0.25...
            if is_relevant:
                weighted_score += weight

        # Normalize by maximum possible score
        max_possible = sum(1.0 / (i + 1) for i in range(len(contexts)))
        return weighted_score / max_possible if max_possible > 0 else 0.0

    async def compute_context_recall(self, query: str, contexts: List[str],
                                    ground_truth_contexts: Optional[List[str]] = None) -> float:
        """
        Context Recall: Proportion of relevant information retrieved

        Method:
        - If ground truth available: compare retrieved vs expected contexts
        - Otherwise: heuristic based on context presence and quality
        """
        if not contexts:
            return 0.0

        # If ground truth contexts provided, compute overlap
        if ground_truth_contexts:
            # Use embedding similarity to match contexts
            try:
                retrieved_embeddings = await asyncio.gather(*[
                    self.embedding_generator.embed(ctx)
                    for ctx in contexts
                ])
                truth_embeddings = await asyncio.gather(*[
                    self.embedding_generator.embed(ctx)
                    for ctx in ground_truth_contexts
                ])

                # For each truth context, check if similar retrieved context exists
                recall_count = 0
                for truth_emb in truth_embeddings:
                    truth_vec = np.array(truth_emb)
                    max_similarity = 0.0

                    for retr_emb in retrieved_embeddings:
                        retr_vec = np.array(retr_emb)
                        similarity = np.dot(truth_vec, retr_vec) / (
                            np.linalg.norm(truth_vec) * np.linalg.norm(retr_vec)
                        )
                        max_similarity = max(max_similarity, similarity)

                    # Consider recalled if similarity > threshold
                    if max_similarity > 0.8:
                        recall_count += 1

                return recall_count / len(ground_truth_contexts)
            except:
                pass

        # Heuristic: assume perfect recall if we have contexts
        # Penalize if degraded or no contexts
        return 1.0 if contexts else 0.0

    async def compute_answer_correctness(self, expected_answer: str,
                                        actual_answer: str) -> float:
        """
        Answer Correctness: Factual accuracy compared to ground truth

        Method: LLM-based comparison of factual content
        Only applicable when ground truth answer is available
        """
        if not expected_answer:
            return 1.0  # No ground truth = assume correct

        prompt = f"""Rate the factual correctness of the actual answer compared to the expected answer (0.0 to 1.0).

EXPECTED ANSWER (Ground Truth): {expected_answer}

ACTUAL ANSWER: {actual_answer}

SCALE:
1.0 = Factually identical or fully equivalent
0.8 = Mostly correct with minor differences
0.6 = Partially correct, some inaccuracies
0.4 = Partially incorrect
0.2 = Mostly incorrect
0.0 = Completely incorrect or contradictory

IMPORTANT: Output ONLY the numeric score (e.g., 0.8). No explanation or additional text."""

        try:
            response = await self.text_generator.generate(
                prompt=prompt,
                max_tokens=10,
                temperature=0.0
            )
            import re
            numbers = re.findall(r'0\.\d+|1\.0|0|1', response)
            if numbers:
                score = float(numbers[-1])
            else:
                score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            print(f"Answer correctness evaluation error: {e}")
            return 0.5

    async def compute_answer_similarity(self, expected_answer: str,
                                       actual_answer: str) -> float:
        """
        Answer Similarity: Semantic similarity to expected answer

        Method: Embedding-based cosine similarity
        Complements correctness with semantic alignment
        """
        if not expected_answer:
            return 1.0

        try:
            # Get embeddings for both answers
            expected_emb, actual_emb = await asyncio.gather(
                self.embedding_generator.embed(expected_answer),
                self.embedding_generator.embed(actual_answer)
            )

            # Compute cosine similarity
            expected_vec = np.array(expected_emb)
            actual_vec = np.array(actual_emb)

            similarity = np.dot(expected_vec, actual_vec) / (
                np.linalg.norm(expected_vec) * np.linalg.norm(actual_vec)
            )

            return float(max(0.0, min(1.0, similarity)))
        except Exception as e:
            print(f"Answer similarity evaluation error: {e}")
            # Fallback to simple word overlap
            expected_words = set(expected_answer.lower().split())
            actual_words = set(actual_answer.lower().split())
            if not expected_words:
                return 0.0
            overlap = len(expected_words & actual_words) / len(expected_words)
            return overlap

    async def compute_all_metrics(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        expected_answer: Optional[str] = None,
        ground_truth_contexts: Optional[List[str]] = None,
        latency_ms: float = 0.0,
        retrieval_time_ms: float = 0.0,
        generation_time_ms: float = 0.0,
        total_tokens: int = 0
    ) -> EvaluationMetrics:
        """
        Compute all evaluation metrics in parallel
        Returns complete EvaluationMetrics object
        """
        # Check if degraded response
        is_degraded = (
            'Based on your knowledge base' in answer or
            'I cannot find' in answer or
            len(contexts) == 0
        )

        # Compute all quality metrics in parallel
        results = await asyncio.gather(
            self.compute_faithfulness(answer, contexts),
            self.compute_answer_relevance(query, answer),
            self.compute_context_relevance(query, contexts),
            self.compute_context_precision(query, contexts),
            self.compute_context_recall(query, contexts, ground_truth_contexts),
            self.compute_answer_correctness(expected_answer or "", answer) if expected_answer else asyncio.sleep(0, result=1.0),
            self.compute_answer_similarity(expected_answer or "", answer) if expected_answer else asyncio.sleep(0, result=1.0)
        )

        faithfulness, answer_relevance, context_relevance, context_precision, \
            context_recall, answer_correctness, answer_similarity = results

        return EvaluationMetrics(
            faithfulness=faithfulness,
            answer_relevance=answer_relevance,
            context_relevance=context_relevance,
            context_precision=context_precision,
            context_recall=context_recall,
            answer_correctness=answer_correctness,
            answer_similarity=answer_similarity,
            latency_ms=latency_ms,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            total_tokens=total_tokens,
            sources_count=len(contexts),
            is_degraded=is_degraded
        )
