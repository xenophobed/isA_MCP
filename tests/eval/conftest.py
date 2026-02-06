"""
DeepEval layer test configuration and fixtures.

Layer 5: LLM Quality Tests
- Tests AI output quality using DeepEval metrics
- Uses real AI models
- Evaluates semantic relevance, coherence, accuracy
"""
import pytest
import os
from typing import Any


# ═══════════════════════════════════════════════════════════════
# DeepEval Configuration
# ═══════════════════════════════════════════════════════════════

# Try to import deepeval, skip tests if not available
try:
    from deepeval import evaluate
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        ContextualPrecisionMetric,
        ContextualRecallMetric,
        GEval,
    )
    from deepeval.test_case import LLMTestCase

    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False
    AnswerRelevancyMetric = None
    FaithfulnessMetric = None
    ContextualPrecisionMetric = None
    ContextualRecallMetric = None
    GEval = None
    LLMTestCase = None


def pytest_configure(config):
    """Configure pytest for DeepEval tests."""
    config.addinivalue_line(
        "markers", "eval: mark test as DeepEval LLM quality test"
    )


@pytest.fixture(scope="session", autouse=True)
def check_deepeval():
    """Check if DeepEval is available."""
    if not DEEPEVAL_AVAILABLE:
        pytest.skip("DeepEval not installed. Run: pip install deepeval")


# ═══════════════════════════════════════════════════════════════
# Metric Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def relevancy_metric():
    """Provide answer relevancy metric."""
    if not DEEPEVAL_AVAILABLE:
        pytest.skip("DeepEval not available")
    return AnswerRelevancyMetric(threshold=0.7)


@pytest.fixture
def faithfulness_metric():
    """Provide faithfulness metric."""
    if not DEEPEVAL_AVAILABLE:
        pytest.skip("DeepEval not available")
    return FaithfulnessMetric(threshold=0.7)


@pytest.fixture
def precision_metric():
    """Provide contextual precision metric."""
    if not DEEPEVAL_AVAILABLE:
        pytest.skip("DeepEval not available")
    return ContextualPrecisionMetric(threshold=0.8)


@pytest.fixture
def recall_metric():
    """Provide contextual recall metric."""
    if not DEEPEVAL_AVAILABLE:
        pytest.skip("DeepEval not available")
    return ContextualRecallMetric(threshold=0.7)


@pytest.fixture
def coherence_metric():
    """Provide coherence evaluation metric."""
    if not DEEPEVAL_AVAILABLE:
        pytest.skip("DeepEval not available")
    return GEval(
        name="Coherence",
        criteria="Is the output coherent and well-structured?",
        evaluation_params=["coherence", "fluency"],
        threshold=0.7
    )


@pytest.fixture
def grammar_metric():
    """Provide grammar evaluation metric."""
    if not DEEPEVAL_AVAILABLE:
        pytest.skip("DeepEval not available")
    return GEval(
        name="Grammar",
        criteria="Is the output grammatically correct?",
        evaluation_params=["grammar", "spelling"],
        threshold=0.8
    )


# ═══════════════════════════════════════════════════════════════
# Test Case Builders
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def create_test_case():
    """Provide test case builder."""
    if not DEEPEVAL_AVAILABLE:
        pytest.skip("DeepEval not available")

    def _create(
        input: str,
        actual_output: str,
        expected_output: str = None,
        context: list = None,
        retrieval_context: list = None
    ) -> LLMTestCase:
        return LLMTestCase(
            input=input,
            actual_output=actual_output,
            expected_output=expected_output,
            context=context or [],
            retrieval_context=retrieval_context or []
        )
    return _create


# ═══════════════════════════════════════════════════════════════
# Intelligence Service Fixtures (Real for Eval)
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
async def text_generator_tool():
    """Provide real text generator tool for evaluation."""
    try:
        from tools.intelligent_tools.language.text_generator import TextGenerator
        return TextGenerator()
    except ImportError:
        pytest.skip("Text generator not available")


@pytest.fixture
async def summarizer_tool():
    """Provide real summarizer tool for evaluation."""
    try:
        from tools.intelligent_tools.language.text_summarizer import TextSummarizer
        return TextSummarizer()
    except ImportError:
        pytest.skip("Summarizer not available")


@pytest.fixture
async def embedding_generator():
    """Provide real embedding generator for evaluation."""
    try:
        from tools.intelligent_tools.language.embedding_generator import EmbeddingGenerator
        return EmbeddingGenerator()
    except ImportError:
        pytest.skip("Embedding generator not available")


@pytest.fixture
async def vision_analyzer():
    """Provide real vision analyzer for evaluation."""
    try:
        from tools.intelligent_tools.vision.image_analyzer import ImageAnalyzer
        return ImageAnalyzer()
    except ImportError:
        pytest.skip("Vision analyzer not available")


@pytest.fixture
async def audio_analyzer():
    """Provide real audio analyzer for evaluation."""
    try:
        from tools.intelligent_tools.audio.audio_analyzer import AudioAnalyzer
        return AudioAnalyzer()
    except ImportError:
        pytest.skip("Audio analyzer not available")


@pytest.fixture
async def search_service():
    """Provide real search service for evaluation."""
    try:
        from services.search_service import SearchService
        from core.clients.postgres_client import get_pool
        from core.clients.qdrant_client import get_qdrant_client

        db_pool = await get_pool()
        qdrant = get_qdrant_client()
        return SearchService(db_pool=db_pool, qdrant_client=qdrant)
    except Exception as e:
        pytest.skip(f"Search service not available: {e}")


# ═══════════════════════════════════════════════════════════════
# Benchmark Data Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def text_generation_benchmark():
    """Provide text generation benchmark data."""
    return [
        {
            "prompt": "Write a professional email requesting a meeting",
            "expected_elements": ["greeting", "purpose", "availability", "closing"],
            "min_length": 50,
            "max_length": 500
        },
        {
            "prompt": "Explain quantum computing in simple terms",
            "expected_elements": ["qubits", "superposition", "practical"],
            "min_length": 100,
            "max_length": 1000
        },
        {
            "prompt": "Generate a product description for wireless headphones",
            "expected_elements": ["features", "benefits", "call-to-action"],
            "min_length": 50,
            "max_length": 300
        }
    ]


@pytest.fixture
def summarization_benchmark():
    """Provide summarization benchmark data."""
    return [
        {
            "input": """
            Artificial intelligence has transformed many industries in recent years.
            In healthcare, AI assists doctors with diagnosis by analyzing medical images
            and patient data. In finance, algorithms detect fraud and automate trading.
            Transportation is being revolutionized by autonomous vehicles. Retail uses
            AI for personalized recommendations and inventory management. Despite these
            advances, challenges remain around ethics, bias, and job displacement.
            """,
            "max_summary_length": 100,
            "required_topics": ["industries", "applications", "challenges"]
        }
    ]


@pytest.fixture
def tool_search_benchmark():
    """Provide tool search benchmark data."""
    return [
        {
            "query": "I need to analyze an image and extract text",
            "expected_tools": ["vision_analyzer", "ocr_extractor", "image_processor"],
            "min_relevance_score": 0.7
        },
        {
            "query": "Generate embeddings for semantic search",
            "expected_tools": ["embedding_generator", "vector_store"],
            "min_relevance_score": 0.7
        },
        {
            "query": "Create calendar events and reminders",
            "expected_tools": ["calendar_tools", "event_tools"],
            "min_relevance_score": 0.7
        }
    ]


@pytest.fixture
def vision_analysis_samples(test_data_path):
    """Provide vision analysis sample images."""
    samples_dir = test_data_path / "documents"
    return {
        "document": samples_dir / "test_document.pdf" if samples_dir.exists() else None,
        "image": samples_dir / "test_image.jpg" if samples_dir.exists() else None
    }


@pytest.fixture
def test_data_path():
    """Provide path to test data directory."""
    from pathlib import Path
    return Path(__file__).parent.parent / "test_data"


# ═══════════════════════════════════════════════════════════════
# Evaluation Helpers
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def evaluate_with_metrics():
    """Provide evaluation helper function."""
    if not DEEPEVAL_AVAILABLE:
        pytest.skip("DeepEval not available")

    async def _evaluate(
        test_case: LLMTestCase,
        metrics: list,
        min_scores: dict = None
    ) -> dict:
        """
        Evaluate a test case with multiple metrics.

        Args:
            test_case: The LLM test case to evaluate
            metrics: List of metrics to apply
            min_scores: Dict of metric_name -> minimum required score

        Returns:
            Dict with metric names and their scores
        """
        results = {}
        min_scores = min_scores or {}

        for metric in metrics:
            try:
                result = metric.measure(test_case)
                results[metric.__class__.__name__] = {
                    "score": result.score,
                    "passed": result.score >= min_scores.get(
                        metric.__class__.__name__, 0.0
                    ),
                    "reason": getattr(result, "reason", None)
                }
            except Exception as e:
                results[metric.__class__.__name__] = {
                    "score": 0.0,
                    "passed": False,
                    "error": str(e)
                }

        return results

    return _evaluate


@pytest.fixture
def calculate_precision_recall():
    """Provide precision/recall calculation helper."""
    def _calculate(predictions: list, ground_truth: list) -> dict:
        """
        Calculate precision and recall.

        Args:
            predictions: List of predicted items
            ground_truth: List of expected items

        Returns:
            Dict with precision, recall, and f1 scores
        """
        pred_set = set(predictions)
        truth_set = set(ground_truth)

        true_positives = len(pred_set & truth_set)
        false_positives = len(pred_set - truth_set)
        false_negatives = len(truth_set - pred_set)

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0 else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0 else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0 else 0.0
        )

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }

    return _calculate
