#!/usr/bin/env python3
"""
RAG Evaluation Service
Automated evaluation pipeline for RAG patterns
Orchestrates metrics computation, dataset management, and result tracking
"""

import asyncio
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime

from .metrics_service import RAGMetricsService, EvaluationMetrics
from .dataset_manager import EvaluationDatasetManager, TestCase


@dataclass
class EvaluationResult:
    """Complete evaluation result for a single test case"""
    test_id: str
    pattern_name: str
    query: str
    expected_answer: Optional[str]
    actual_answer: str
    contexts: List[str]
    metrics: EvaluationMetrics
    passed: bool
    timestamp: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        result = asdict(self)
        result['metrics'] = asdict(self.metrics)
        return result


class RAGEvaluationService:
    """
    Main evaluation service for RAG patterns
    Provides automated evaluation pipeline and result management
    """

    def __init__(self, model: str = "gpt-4.1-nano"):
        self.metrics_service = RAGMetricsService(model=model)
        self.dataset_manager = EvaluationDatasetManager()
        self.results_history: List[EvaluationResult] = []

    async def evaluate_single_query(
        self,
        pattern_name: str,
        query: str,
        actual_answer: str,
        contexts: List[str],
        expected_answer: Optional[str] = None,
        ground_truth_contexts: Optional[List[str]] = None,
        latency_ms: float = 0.0,
        retrieval_time_ms: float = 0.0,
        generation_time_ms: float = 0.0,
        total_tokens: int = 0,
        test_id: str = "manual"
    ) -> EvaluationResult:
        """
        Evaluate a single RAG query result
        Computes all metrics and determines pass/fail
        """
        try:
            # Compute all metrics
            metrics = await self.metrics_service.compute_all_metrics(
                query=query,
                answer=actual_answer,
                contexts=contexts,
                expected_answer=expected_answer,
                ground_truth_contexts=ground_truth_contexts,
                latency_ms=latency_ms,
                retrieval_time_ms=retrieval_time_ms,
                generation_time_ms=generation_time_ms,
                total_tokens=total_tokens
            )

            # Determine if passed
            passed = metrics.is_passing()

            result = EvaluationResult(
                test_id=test_id,
                pattern_name=pattern_name,
                query=query,
                expected_answer=expected_answer,
                actual_answer=actual_answer,
                contexts=contexts,
                metrics=metrics,
                passed=passed,
                timestamp=datetime.now().isoformat()
            )

            self.results_history.append(result)
            return result

        except Exception as e:
            # Create error result
            error_metrics = EvaluationMetrics(
                faithfulness=0.0,
                answer_relevance=0.0,
                context_relevance=0.0,
                context_precision=0.0,
                context_recall=0.0,
                answer_correctness=0.0,
                answer_similarity=0.0,
                latency_ms=latency_ms,
                retrieval_time_ms=0.0,
                generation_time_ms=0.0,
                total_tokens=0,
                sources_count=0,
                is_degraded=True
            )

            result = EvaluationResult(
                test_id=test_id,
                pattern_name=pattern_name,
                query=query,
                expected_answer=expected_answer,
                actual_answer=actual_answer,
                contexts=contexts,
                metrics=error_metrics,
                passed=False,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )

            self.results_history.append(result)
            return result

    async def evaluate_test_case(
        self,
        pattern_service: Any,  # RAG service instance
        test_case: TestCase,
        pattern_name: str
    ) -> EvaluationResult:
        """
        Evaluate a RAG service on a single test case
        Handles document processing and query execution
        """
        user_id = f"eval-{pattern_name.lower().replace(' ', '-')}-{test_case.id}"

        try:
            # Process document
            doc_start = time.time()
            doc_result = await pattern_service.process_document(
                content=test_case.document,
                user_id=user_id,
                metadata={'source': 'evaluation', 'test_id': test_case.id}
            )
            doc_time = (time.time() - doc_start) * 1000

            if not doc_result.success:
                raise Exception(f"Document processing failed: {doc_result.message}")

            # Execute query
            query_start = time.time()
            query_result = await pattern_service.query(
                query=test_case.query,
                user_id=user_id
            )
            query_time = (time.time() - query_start) * 1000

            if not query_result.success:
                raise Exception(f"Query failed: {query_result.message}")

            # Extract contexts
            contexts = []
            if query_result.sources:
                contexts = [
                    s.get('text', s.get('content', '')) if isinstance(s, dict) else str(s)
                    for s in query_result.sources
                ]

            # Evaluate
            result = await self.evaluate_single_query(
                pattern_name=pattern_name,
                query=test_case.query,
                actual_answer=query_result.content,
                contexts=contexts,
                expected_answer=test_case.expected_answer,
                ground_truth_contexts=test_case.ground_truth_contexts,
                latency_ms=query_time,
                retrieval_time_ms=0,  # Would need instrumentation
                generation_time_ms=query_time,  # Approximate
                total_tokens=0,  # Would need instrumentation
                test_id=test_case.id
            )

            return result

        except Exception as e:
            # Return error result
            error_metrics = EvaluationMetrics(
                faithfulness=0.0,
                answer_relevance=0.0,
                context_relevance=0.0,
                context_precision=0.0,
                context_recall=0.0,
                answer_correctness=0.0,
                answer_similarity=0.0,
                latency_ms=0.0,
                retrieval_time_ms=0.0,
                generation_time_ms=0.0,
                total_tokens=0,
                sources_count=0,
                is_degraded=True
            )

            return EvaluationResult(
                test_id=test_case.id,
                pattern_name=pattern_name,
                query=test_case.query,
                expected_answer=test_case.expected_answer,
                actual_answer="",
                contexts=[],
                metrics=error_metrics,
                passed=False,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )

    async def evaluate_pattern_on_dataset(
        self,
        pattern_service: Any,
        pattern_name: str,
        dataset_name: str
    ) -> List[EvaluationResult]:
        """
        Evaluate a RAG pattern on an entire dataset
        Returns list of evaluation results
        """
        # Load dataset
        test_cases = self.dataset_manager.load_dataset(dataset_name)

        print(f"\n📊 Evaluating {pattern_name} on {dataset_name} ({len(test_cases)} test cases)")

        # Evaluate all test cases
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"   [{i}/{len(test_cases)}] Testing: {test_case.id}...", end=' ')

            result = await self.evaluate_test_case(
                pattern_service=pattern_service,
                test_case=test_case,
                pattern_name=pattern_name
            )

            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} (overall: {result.metrics.overall_score():.2f})")

            results.append(result)

        return results

    async def compare_patterns_on_dataset(
        self,
        patterns: Dict[str, Any],  # pattern_name -> service instance
        dataset_name: str
    ) -> Dict[str, List[EvaluationResult]]:
        """
        Compare multiple RAG patterns on the same dataset
        Returns results grouped by pattern
        """
        results_by_pattern = {}

        for pattern_name, pattern_service in patterns.items():
            results = await self.evaluate_pattern_on_dataset(
                pattern_service=pattern_service,
                pattern_name=pattern_name,
                dataset_name=dataset_name
            )
            results_by_pattern[pattern_name] = results

        return results_by_pattern

    async def benchmark_patterns(
        self,
        patterns: Dict[str, Any],
        datasets: List[str]
    ) -> Dict[str, Dict[str, List[EvaluationResult]]]:
        """
        Comprehensive benchmark of multiple patterns across multiple datasets
        Returns: {dataset_name: {pattern_name: [results]}}
        """
        all_results = {}

        for dataset_name in datasets:
            print(f"\n{'='*80}")
            print(f"DATASET: {dataset_name}")
            print(f"{'='*80}")

            dataset_results = await self.compare_patterns_on_dataset(
                patterns=patterns,
                dataset_name=dataset_name
            )

            all_results[dataset_name] = dataset_results

        return all_results

    def get_pattern_statistics(self, pattern_name: str) -> Dict[str, Any]:
        """Get statistics for a specific pattern from history"""
        pattern_results = [
            r for r in self.results_history
            if r.pattern_name == pattern_name
        ]

        if not pattern_results:
            return {}

        import statistics

        return {
            'total_evaluations': len(pattern_results),
            'passed': sum(1 for r in pattern_results if r.passed),
            'failed': sum(1 for r in pattern_results if not r.passed),
            'pass_rate': sum(1 for r in pattern_results if r.passed) / len(pattern_results),
            'degraded_count': sum(1 for r in pattern_results if r.metrics.is_degraded),
            'avg_overall_score': statistics.mean(r.metrics.overall_score() for r in pattern_results),
            'avg_faithfulness': statistics.mean(r.metrics.faithfulness for r in pattern_results),
            'avg_answer_relevance': statistics.mean(r.metrics.answer_relevance for r in pattern_results),
            'avg_context_relevance': statistics.mean(r.metrics.context_relevance for r in pattern_results),
            'avg_latency_ms': statistics.mean(r.metrics.latency_ms for r in pattern_results),
        }

    def clear_history(self):
        """Clear evaluation history"""
        self.results_history.clear()


async def example_usage():
    """Example of using the evaluation service"""
    from tools.services.data_analytics_service.services.digital_service.patterns.simple_rag_service import SimpleRAGService
    from tools.services.data_analytics_service.services.digital_service.base.base_rag_service import RAGConfig

    # Initialize evaluation service
    evaluator = RAGEvaluationService()

    # Create default datasets
    evaluator.dataset_manager.create_default_datasets()

    # Initialize pattern
    config = RAGConfig(chunk_size=500, overlap=50, top_k=3)
    simple_rag = SimpleRAGService(config)

    # Evaluate on dataset
    results = await evaluator.evaluate_pattern_on_dataset(
        pattern_service=simple_rag,
        pattern_name="Simple RAG",
        dataset_name="basic_functionality"
    )

    # Get statistics
    stats = evaluator.get_pattern_statistics("Simple RAG")
    print(f"\n📈 Statistics:")
    print(f"   Pass Rate: {stats['pass_rate']:.1%}")
    print(f"   Avg Overall Score: {stats['avg_overall_score']:.2f}")
    print(f"   Avg Latency: {stats['avg_latency_ms']:.0f}ms")


if __name__ == "__main__":
    asyncio.run(example_usage())
