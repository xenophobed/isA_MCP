#!/usr/bin/env python3
"""
Evaluation Dataset Manager
Manages test cases, ground truth data, and evaluation datasets for RAG systems
"""

import json
import yaml
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime


@dataclass
class TestCase:
    """Single test case for RAG evaluation"""
    id: str
    query: str
    document: str
    expected_answer: Optional[str] = None
    ground_truth_contexts: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    category: str = "general"
    difficulty: str = "medium"  # easy, medium, hard
    language: str = "zh"  # zh, en, mixed

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'TestCase':
        return cls(**data)


class EvaluationDatasetManager:
    """
    Manages evaluation datasets for RAG testing
    Supports loading, saving, and organizing test cases
    """

    def __init__(self, dataset_dir: Optional[str] = None):
        if dataset_dir is None:
            # Default to config/eval_datasets under digital_service
            base_path = Path(__file__).parent.parent / "config" / "eval_datasets"
            self.dataset_dir = base_path
        else:
            self.dataset_dir = Path(dataset_dir)

        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.test_cases: List[TestCase] = []

    def load_dataset(self, dataset_name: str) -> List[TestCase]:
        """Load test cases from a dataset file"""
        dataset_path = self.dataset_dir / f"{dataset_name}.json"

        if not dataset_path.exists():
            # Try YAML
            dataset_path = self.dataset_dir / f"{dataset_name}.yaml"

        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_name}")

        with open(dataset_path, 'r', encoding='utf-8') as f:
            if dataset_path.suffix == '.json':
                data = json.load(f)
            else:
                data = yaml.safe_load(f)

        test_cases = [TestCase.from_dict(tc) for tc in data.get('test_cases', [])]
        self.test_cases.extend(test_cases)
        return test_cases

    def save_dataset(self, dataset_name: str, test_cases: List[TestCase],
                    format: str = "json"):
        """Save test cases to a dataset file"""
        if format == "json":
            dataset_path = self.dataset_dir / f"{dataset_name}.json"
            with open(dataset_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'name': dataset_name,
                    'created_at': datetime.now().isoformat(),
                    'test_cases': [tc.to_dict() for tc in test_cases]
                }, f, indent=2, ensure_ascii=False)
        else:
            dataset_path = self.dataset_dir / f"{dataset_name}.yaml"
            with open(dataset_path, 'w', encoding='utf-8') as f:
                yaml.dump({
                    'name': dataset_name,
                    'created_at': datetime.now().isoformat(),
                    'test_cases': [tc.to_dict() for tc in test_cases]
                }, f, allow_unicode=True)

    def create_default_datasets(self):
        """Create default evaluation datasets"""

        # Basic functionality dataset
        basic_cases = [
            TestCase(
                id="basic_001",
                query="什么是人工智能？",
                document="""人工智能(AI)是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。
                这些任务包括学习、推理、问题解决、感知和语言理解。AI系统可以从数据中学习模式，做出决策，并随着时间的推移改进其性能。""",
                expected_answer="人工智能是计算机科学的一个分支，专注于创建能执行需要人类智能的任务的系统，如学习、推理和问题解决。",
                category="definition",
                difficulty="easy"
            ),
            TestCase(
                id="basic_002",
                query="机器学习和深度学习有什么区别？",
                document="""机器学习是人工智能的一个子集，使计算机能够从数据中学习而无需显式编程。
                深度学习是机器学习的一个分支，使用多层神经网络来建模和理解复杂模式。
                深度学习特别适合处理图像、语音和自然语言等非结构化数据。""",
                expected_answer="机器学习是让计算机从数据中学习的技术，而深度学习是机器学习的一个分支，使用多层神经网络处理复杂模式。",
                category="comparison",
                difficulty="medium"
            ),
            TestCase(
                id="basic_003",
                query="神经网络的训练过程是怎样的？",
                document="""神经网络的训练过程包括以下步骤：
                1. 前向传播：输入数据通过网络层，产生预测输出
                2. 损失计算：比较预测输出和实际标签，计算误差
                3. 反向传播：计算损失相对于每个参数的梯度
                4. 参数更新：使用优化算法（如SGD或Adam）更新网络权重
                5. 迭代：重复以上步骤直到模型收敛""",
                expected_answer="神经网络训练包括前向传播产生预测、计算损失、反向传播计算梯度、更新参数，并迭代这些步骤直到收敛。",
                category="process",
                difficulty="medium"
            )
        ]

        # Multi-hop reasoning dataset
        multihop_cases = [
            TestCase(
                id="multihop_001",
                query="如果AI可以进行学习和推理，那么它能否完全替代人类工作？",
                document="""人工智能在许多任务上表现出色，包括数据分析、模式识别和自动化流程。
                然而，AI在创造力、情感理解、道德判断和复杂社交互动方面仍然受限。
                许多专家认为，AI更适合增强人类能力而非完全替代，尤其是在需要同理心、创新思维和伦理决策的领域。
                未来的工作模式可能是人机协作，充分利用AI的效率和人类的独特能力。""",
                category="reasoning",
                difficulty="hard"
            )
        ]

        # Multilingual dataset
        multilingual_cases = [
            TestCase(
                id="multilingual_001",
                query="What are the main applications of natural language processing?",
                document="""Natural Language Processing (NLP) has numerous applications including:
                - Machine translation (e.g., Google Translate)
                - Sentiment analysis for social media monitoring
                - Chatbots and virtual assistants
                - Text summarization for news and documents
                - Named entity recognition in information extraction
                - Question answering systems""",
                expected_answer="Main NLP applications include machine translation, sentiment analysis, chatbots, text summarization, and question answering systems.",
                category="application",
                difficulty="easy",
                language="en"
            )
        ]

        # Save datasets
        self.save_dataset("basic_functionality", basic_cases)
        self.save_dataset("multihop_reasoning", multihop_cases)
        self.save_dataset("multilingual", multilingual_cases)

        print(f"✅ Created default datasets in {self.dataset_dir}")
        return {
            'basic_functionality': basic_cases,
            'multihop_reasoning': multihop_cases,
            'multilingual': multilingual_cases
        }

    def filter_by_category(self, category: str) -> List[TestCase]:
        """Filter test cases by category"""
        return [tc for tc in self.test_cases if tc.category == category]

    def filter_by_difficulty(self, difficulty: str) -> List[TestCase]:
        """Filter test cases by difficulty"""
        return [tc for tc in self.test_cases if tc.difficulty == difficulty]

    def filter_by_language(self, language: str) -> List[TestCase]:
        """Filter test cases by language"""
        return [tc for tc in self.test_cases if tc.language == language]

    def get_test_case(self, test_id: str) -> Optional[TestCase]:
        """Get a specific test case by ID"""
        for tc in self.test_cases:
            if tc.id == test_id:
                return tc
        return None

    def list_datasets(self) -> List[str]:
        """List all available datasets"""
        datasets = []
        for path in self.dataset_dir.glob("*.json"):
            datasets.append(path.stem)
        for path in self.dataset_dir.glob("*.yaml"):
            if path.stem not in datasets:
                datasets.append(path.stem)
        return datasets

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded test cases"""
        if not self.test_cases:
            return {}

        return {
            'total_cases': len(self.test_cases),
            'by_category': {
                cat: len([tc for tc in self.test_cases if tc.category == cat])
                for cat in set(tc.category for tc in self.test_cases)
            },
            'by_difficulty': {
                diff: len([tc for tc in self.test_cases if tc.difficulty == diff])
                for diff in set(tc.difficulty for tc in self.test_cases)
            },
            'by_language': {
                lang: len([tc for tc in self.test_cases if tc.language == lang])
                for lang in set(tc.language for tc in self.test_cases)
            },
            'with_ground_truth': len([tc for tc in self.test_cases if tc.expected_answer])
        }


if __name__ == "__main__":
    # Create default datasets
    manager = EvaluationDatasetManager()
    manager.create_default_datasets()

    # Load and display statistics
    manager.load_dataset("basic_functionality")
    stats = manager.get_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
