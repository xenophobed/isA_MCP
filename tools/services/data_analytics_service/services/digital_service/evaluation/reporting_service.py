#!/usr/bin/env python3
"""
Evaluation Reporting Service
Generates comprehensive reports, visualizations, and comparisons for RAG evaluations
"""

import json
import statistics
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .evaluation_service import EvaluationResult


class EvaluationReporter:
    """
    Generates reports and visualizations for RAG evaluation results
    Supports multiple output formats: console, JSON, markdown, HTML
    """

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            base_path = Path(__file__).parent.parent / "evaluation_results"
            self.output_dir = base_path
        else:
            self.output_dir = Path(output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def calculate_aggregate_metrics(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Calculate aggregate metrics across multiple evaluations"""
        if not results:
            return {}

        metrics_list = [r.metrics for r in results]

        # Calculate percentiles for latency
        latencies = sorted(m.latency_ms for m in metrics_list)
        n = len(latencies)

        return {
            'summary': {
                'total_tests': len(results),
                'passed': sum(1 for r in results if r.passed),
                'failed': sum(1 for r in results if not r.passed),
                'pass_rate': sum(1 for r in results if r.passed) / len(results),
                'degraded_count': sum(1 for r in results if r.metrics.is_degraded),
                'error_count': sum(1 for r in results if r.error),
            },
            'quality_metrics': {
                'overall_score': {
                    'mean': statistics.mean(m.overall_score() for m in metrics_list),
                    'median': statistics.median(m.overall_score() for m in metrics_list),
                    'min': min(m.overall_score() for m in metrics_list),
                    'max': max(m.overall_score() for m in metrics_list),
                },
                'faithfulness': {
                    'mean': statistics.mean(m.faithfulness for m in metrics_list),
                    'median': statistics.median(m.faithfulness for m in metrics_list),
                },
                'answer_relevance': {
                    'mean': statistics.mean(m.answer_relevance for m in metrics_list),
                    'median': statistics.median(m.answer_relevance for m in metrics_list),
                },
                'context_relevance': {
                    'mean': statistics.mean(m.context_relevance for m in metrics_list),
                    'median': statistics.median(m.context_relevance for m in metrics_list),
                },
                'context_precision': {
                    'mean': statistics.mean(m.context_precision for m in metrics_list),
                    'median': statistics.median(m.context_precision for m in metrics_list),
                },
                'context_recall': {
                    'mean': statistics.mean(m.context_recall for m in metrics_list),
                    'median': statistics.median(m.context_recall for m in metrics_list),
                },
                'answer_correctness': {
                    'mean': statistics.mean(m.answer_correctness for m in metrics_list),
                    'median': statistics.median(m.answer_correctness for m in metrics_list),
                },
                'answer_similarity': {
                    'mean': statistics.mean(m.answer_similarity for m in metrics_list),
                    'median': statistics.median(m.answer_similarity for m in metrics_list),
                },
            },
            'performance_metrics': {
                'latency_ms': {
                    'mean': statistics.mean(m.latency_ms for m in metrics_list),
                    'median': statistics.median(m.latency_ms for m in metrics_list),
                    'min': min(m.latency_ms for m in metrics_list),
                    'max': max(m.latency_ms for m in metrics_list),
                    'p50': latencies[n // 2] if n > 0 else 0,
                    'p95': latencies[int(n * 0.95)] if n > 0 else 0,
                    'p99': latencies[int(n * 0.99)] if n > 0 else 0,
                },
                'avg_tokens': statistics.mean(m.total_tokens for m in metrics_list) if all(m.total_tokens for m in metrics_list) else 0,
                'avg_sources': statistics.mean(m.sources_count for m in metrics_list),
            }
        }

    def generate_console_report(self, results: List[EvaluationResult],
                               title: str = "RAG Evaluation Report") -> str:
        """Generate formatted console report"""
        aggregate = self.calculate_aggregate_metrics(results)

        report = f"""
{'='*80}
{title}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

📊 SUMMARY
----------
Total Tests:        {aggregate['summary']['total_tests']}
Passed:             {aggregate['summary']['passed']} ({aggregate['summary']['pass_rate']:.1%})
Failed:             {aggregate['summary']['failed']}
Degraded:           {aggregate['summary']['degraded_count']}
Errors:             {aggregate['summary']['error_count']}

🎯 QUALITY METRICS
------------------
Overall Score:      {aggregate['quality_metrics']['overall_score']['mean']:.3f} (median: {aggregate['quality_metrics']['overall_score']['median']:.3f})
                    Range: [{aggregate['quality_metrics']['overall_score']['min']:.3f}, {aggregate['quality_metrics']['overall_score']['max']:.3f}]

Faithfulness:       {aggregate['quality_metrics']['faithfulness']['mean']:.3f}  {'✅' if aggregate['quality_metrics']['faithfulness']['mean'] >= 0.7 else '⚠️'}
Answer Relevance:   {aggregate['quality_metrics']['answer_relevance']['mean']:.3f}  {'✅' if aggregate['quality_metrics']['answer_relevance']['mean'] >= 0.7 else '⚠️'}
Context Relevance:  {aggregate['quality_metrics']['context_relevance']['mean']:.3f}  {'✅' if aggregate['quality_metrics']['context_relevance']['mean'] >= 0.6 else '⚠️'}
Context Precision:  {aggregate['quality_metrics']['context_precision']['mean']:.3f}
Context Recall:     {aggregate['quality_metrics']['context_recall']['mean']:.3f}
Answer Correctness: {aggregate['quality_metrics']['answer_correctness']['mean']:.3f}
Answer Similarity:  {aggregate['quality_metrics']['answer_similarity']['mean']:.3f}

⚡ PERFORMANCE METRICS
---------------------
Latency (avg):      {aggregate['performance_metrics']['latency_ms']['mean']:.0f}ms
Latency (median):   {aggregate['performance_metrics']['latency_ms']['median']:.0f}ms
Latency (p95):      {aggregate['performance_metrics']['latency_ms']['p95']:.0f}ms
Latency (p99):      {aggregate['performance_metrics']['latency_ms']['p99']:.0f}ms
Avg Sources:        {aggregate['performance_metrics']['avg_sources']:.1f}

📝 DETAILED RESULTS
-------------------
"""

        for i, result in enumerate(results, 1):
            status = "✅ PASS" if result.passed else "❌ FAIL"
            degraded_marker = " [DEGRADED]" if result.metrics.is_degraded else ""
            error_marker = f" [ERROR: {result.error}]" if result.error else ""

            report += f"\n{i}. {status} - {result.pattern_name} (Test: {result.test_id}){degraded_marker}{error_marker}\n"
            report += f"   Query: {result.query[:100]}{'...' if len(result.query) > 100 else ''}\n"
            report += f"   Overall: {result.metrics.overall_score():.2f} | "
            report += f"Faithful: {result.metrics.faithfulness:.2f} | "
            report += f"Relevant: {result.metrics.answer_relevance:.2f} | "
            report += f"Latency: {result.metrics.latency_ms:.0f}ms\n"

            if result.metrics.is_degraded:
                report += f"   ⚠️  Degraded response detected\n"

        report += f"\n{'='*80}\n"

        return report

    def generate_comparison_report(self,
                                 results_by_pattern: Dict[str, List[EvaluationResult]],
                                 title: str = "Pattern Comparison Report") -> str:
        """Generate comparison report across multiple patterns"""

        report = f"""
{'='*80}
{title}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

"""

        # Calculate aggregates for each pattern
        pattern_stats = {}
        for pattern_name, results in results_by_pattern.items():
            pattern_stats[pattern_name] = self.calculate_aggregate_metrics(results)

        # Summary table
        report += "📊 PATTERN COMPARISON SUMMARY\n"
        report += "-" * 80 + "\n"
        report += f"{'Pattern':<20} {'Tests':<8} {'Pass%':<8} {'Overall':<10} {'Latency':<10}\n"
        report += "-" * 80 + "\n"

        for pattern_name, stats in pattern_stats.items():
            report += f"{pattern_name:<20} "
            report += f"{stats['summary']['total_tests']:<8} "
            report += f"{stats['summary']['pass_rate']:.1%}   "
            report += f"{stats['quality_metrics']['overall_score']['mean']:.3f}     "
            report += f"{stats['performance_metrics']['latency_ms']['mean']:.0f}ms\n"

        # Detailed metrics comparison
        report += f"\n🎯 DETAILED METRICS COMPARISON\n"
        report += "-" * 80 + "\n"

        metrics_to_compare = [
            ('Faithfulness', 'faithfulness'),
            ('Answer Relevance', 'answer_relevance'),
            ('Context Relevance', 'context_relevance'),
            ('Context Precision', 'context_precision'),
            ('Context Recall', 'context_recall'),
            ('Answer Correctness', 'answer_correctness'),
        ]

        for metric_label, metric_key in metrics_to_compare:
            report += f"\n{metric_label}:\n"
            for pattern_name, stats in pattern_stats.items():
                mean_val = stats['quality_metrics'][metric_key]['mean']
                marker = "✅" if mean_val >= 0.7 else ("⚠️" if mean_val >= 0.5 else "❌")
                report += f"  {pattern_name:<20} {mean_val:.3f} {marker}\n"

        # Winner determination
        report += f"\n🏆 WINNERS\n"
        report += "-" * 80 + "\n"

        # Best overall score
        best_overall = max(pattern_stats.items(),
                          key=lambda x: x[1]['quality_metrics']['overall_score']['mean'])
        report += f"Best Overall Score:     {best_overall[0]} ({best_overall[1]['quality_metrics']['overall_score']['mean']:.3f})\n"

        # Fastest
        fastest = min(pattern_stats.items(),
                     key=lambda x: x[1]['performance_metrics']['latency_ms']['mean'])
        report += f"Fastest Response:       {fastest[0]} ({fastest[1]['performance_metrics']['latency_ms']['mean']:.0f}ms)\n"

        # Highest pass rate
        highest_pass = max(pattern_stats.items(),
                          key=lambda x: x[1]['summary']['pass_rate'])
        report += f"Highest Pass Rate:      {highest_pass[0]} ({highest_pass[1]['summary']['pass_rate']:.1%})\n"

        report += f"\n{'='*80}\n"

        return report

    def save_json_report(self, results: List[EvaluationResult],
                        filename: str) -> str:
        """Save evaluation results as JSON"""
        filepath = self.output_dir / filename

        report_data = {
            'generated_at': datetime.now().isoformat(),
            'aggregate_metrics': self.calculate_aggregate_metrics(results),
            'results': [r.to_dict() for r in results]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return str(filepath)

    def save_markdown_report(self, results: List[EvaluationResult],
                           filename: str, title: str = "RAG Evaluation Report") -> str:
        """Save evaluation results as Markdown"""
        filepath = self.output_dir / filename
        aggregate = self.calculate_aggregate_metrics(results)

        md_content = f"""# {title}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {aggregate['summary']['total_tests']} |
| Passed | {aggregate['summary']['passed']} ({aggregate['summary']['pass_rate']:.1%}) |
| Failed | {aggregate['summary']['failed']} |
| Degraded | {aggregate['summary']['degraded_count']} |
| Errors | {aggregate['summary']['error_count']} |

## Quality Metrics

| Metric | Mean | Median | Status |
|--------|------|--------|--------|
| Overall Score | {aggregate['quality_metrics']['overall_score']['mean']:.3f} | {aggregate['quality_metrics']['overall_score']['median']:.3f} | {'✅' if aggregate['quality_metrics']['overall_score']['mean'] >= 0.7 else '⚠️'} |
| Faithfulness | {aggregate['quality_metrics']['faithfulness']['mean']:.3f} | {aggregate['quality_metrics']['faithfulness']['median']:.3f} | {'✅' if aggregate['quality_metrics']['faithfulness']['mean'] >= 0.7 else '⚠️'} |
| Answer Relevance | {aggregate['quality_metrics']['answer_relevance']['mean']:.3f} | {aggregate['quality_metrics']['answer_relevance']['median']:.3f} | {'✅' if aggregate['quality_metrics']['answer_relevance']['mean'] >= 0.7 else '⚠️'} |
| Context Relevance | {aggregate['quality_metrics']['context_relevance']['mean']:.3f} | {aggregate['quality_metrics']['context_relevance']['median']:.3f} | {'✅' if aggregate['quality_metrics']['context_relevance']['mean'] >= 0.6 else '⚠️'} |
| Context Precision | {aggregate['quality_metrics']['context_precision']['mean']:.3f} | {aggregate['quality_metrics']['context_precision']['median']:.3f} | - |
| Context Recall | {aggregate['quality_metrics']['context_recall']['mean']:.3f} | {aggregate['quality_metrics']['context_recall']['median']:.3f} | - |

## Performance Metrics

| Metric | Value |
|--------|-------|
| Avg Latency | {aggregate['performance_metrics']['latency_ms']['mean']:.0f}ms |
| Median Latency | {aggregate['performance_metrics']['latency_ms']['median']:.0f}ms |
| P95 Latency | {aggregate['performance_metrics']['latency_ms']['p95']:.0f}ms |
| P99 Latency | {aggregate['performance_metrics']['latency_ms']['p99']:.0f}ms |
| Avg Sources | {aggregate['performance_metrics']['avg_sources']:.1f} |

## Detailed Results

"""

        for i, result in enumerate(results, 1):
            status_emoji = "✅" if result.passed else "❌"
            md_content += f"\n### {i}. {status_emoji} {result.pattern_name} - Test {result.test_id}\n\n"
            md_content += f"**Query:** {result.query}\n\n"

            if result.metrics.is_degraded:
                md_content += "⚠️ **DEGRADED RESPONSE**\n\n"

            if result.error:
                md_content += f"❌ **ERROR:** {result.error}\n\n"

            md_content += f"**Metrics:**\n"
            md_content += f"- Overall Score: {result.metrics.overall_score():.3f}\n"
            md_content += f"- Faithfulness: {result.metrics.faithfulness:.3f}\n"
            md_content += f"- Answer Relevance: {result.metrics.answer_relevance:.3f}\n"
            md_content += f"- Latency: {result.metrics.latency_ms:.0f}ms\n"
            md_content += f"- Sources: {result.metrics.sources_count}\n\n"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return str(filepath)

    def print_summary(self, results: List[EvaluationResult]):
        """Print quick summary to console"""
        aggregate = self.calculate_aggregate_metrics(results)

        print(f"\n{'='*60}")
        print(f"📊 EVALUATION SUMMARY")
        print(f"{'='*60}")
        print(f"Tests: {aggregate['summary']['total_tests']} | "
              f"Pass: {aggregate['summary']['passed']} ({aggregate['summary']['pass_rate']:.1%}) | "
              f"Fail: {aggregate['summary']['failed']}")
        print(f"Overall Score: {aggregate['quality_metrics']['overall_score']['mean']:.3f} | "
              f"Latency: {aggregate['performance_metrics']['latency_ms']['mean']:.0f}ms")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # Example usage
    reporter = EvaluationReporter()
    print(f"Reports will be saved to: {reporter.output_dir}")
